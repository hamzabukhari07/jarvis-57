"""
core/engines/acp_client.py — Agent Client Protocol (ACP) Client & Session Lifecycle.

Implements a lightweight, robust JSON-RPC 2.0 stdio client for coding engines
supporting stdio ACP (e.g. Google Antigravity CLI and OpenCode CLI).
- Handles initialization (handshake with protocolVersion: 1).
- Manages session lifecycle, prompts, and streaming updates.
- Supports graceful cancellation (JSON-RPC cancel notification with 3s timeout
  before terminating the Job Object process tree).
- Encapsulated within Win32 Job Objects via ProcessSupervisor.
- Inactive / experimental by default unless EngineProtocol.ACP_STDIO is explicitly enabled.

Author: Hamza Bukhari
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

from core.engines.process_supervisor import ContainedProcess
from core.task_manager import strip_ansi

logger = logging.getLogger("zezo.engines.acp")


class AcpHandshakeError(Exception):
    """Raised when the ACP server handshake fails or reports unsupported protocol version."""
    pass


class AcpTimeoutError(Exception):
    """Raised when an ACP request or initialization exceeds the timeout threshold."""
    pass


class AcpSessionClient:
    """
    Stdio JSON-RPC 2.0 client for Agent Client Protocol (ACP) servers.
    """

    def __init__(self, contained_proc: ContainedProcess):
        self.proc = contained_proc
        self._next_id = 1
        self._pending_requests: Dict[int, queue.Queue] = {}
        self._unmatched_responses: Dict[int, Dict[str, Any]] = {}
        self._notifications: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._running = True
        self.server_info: Dict[str, Any] = {}
        self.server_capabilities: Dict[str, Any] = {}
        self.session_id: Optional[str] = None

        # Start background reader thread for stdout pipe
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        """Reads newline-delimited JSON-RPC messages from the server's stdout."""
        try:
            assert self.proc.pipe_file is not None
            for raw_line in iter(self.proc.pipe_file.readline, ""):
                if not raw_line or not self._running:
                    break
                line = strip_ansi(raw_line.strip())
                if not line or not line.startswith("{"):
                    continue

                try:
                    msg = json.loads(line)
                    if not isinstance(msg, dict):
                        continue

                    req_id = msg.get("id")
                    if req_id is not None:
                        # Correlate response with pending request or buffer
                        with self._lock:
                            q = self._pending_requests.get(req_id)
                            if q:
                                q.put(msg)
                            else:
                                self._unmatched_responses[req_id] = msg
                    else:
                        # Server notification or streaming event
                        self._notifications.put(msg)
                except Exception as parse_err:
                    logger.debug("[AcpClient] Error parsing JSON-RPC line: %s", parse_err)
        except Exception as e:
            logger.debug("[AcpClient] Reader loop terminated: %s", e)

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Sends a JSON-RPC 2.0 notification (no response expected)."""
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        data = json.dumps(payload) + "\n"
        self._write_stdin(data)

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Sends a synchronous JSON-RPC 2.0 request and awaits the correlated response.
        Raises AcpTimeoutError if timeout expires.
        """
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            if req_id in self._unmatched_responses:
                return self._unmatched_responses.pop(req_id)
            resp_queue: queue.Queue = queue.Queue()
            self._pending_requests[req_id] = resp_queue

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        data = json.dumps(payload) + "\n"
        self._write_stdin(data)

        try:
            resp = resp_queue.get(timeout=timeout)
            return resp
        except queue.Empty:
            raise AcpTimeoutError(f"ACP request '{method}' (id: {req_id}) timed out after {timeout:.1f}s")
        finally:
            with self._lock:
                self._pending_requests.pop(req_id, None)

    def _write_stdin(self, data: str) -> None:
        """Writes raw UTF-8 string to the contained child process stdin."""
        import ctypes
        from ctypes import wintypes
        import platform

        if platform.system() == "Windows" and hasattr(self.proc, "h_stdin_write") and self.proc.h_stdin_write:
            bytes_data = data.encode("utf-8")
            written = wintypes.DWORD(0)
            kernel32 = ctypes.windll.kernel32
            success = kernel32.WriteFile(
                self.proc.h_stdin_write,
                bytes_data,
                len(bytes_data),
                ctypes.byref(written),
                None,
            )
            if not success:
                logger.warning("[AcpClient] WriteFile to stdin pipe failed.")
        elif self.proc._posix_proc and hasattr(self.proc._posix_proc, "stdin") and self.proc._posix_proc.stdin:
            try:
                self.proc._posix_proc.stdin.write(data)
                self.proc._posix_proc.stdin.flush()
            except Exception as e:
                logger.warning("[AcpClient] Fallback stdin write failed: %s", e)

    def initialize(self, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Performs protocol handshake with `protocolVersion: 1`.
        Verifies agentInfo and agentCapabilities.
        """
        params = {
            "protocolVersion": 1,
            "clientInfo": {
                "name": "ZEZO Agent Client",
                "version": "2.0.0",
            },
        }
        resp = self.send_request("initialize", params, timeout=timeout)
        if "error" in resp:
            err = resp["error"]
            raise AcpHandshakeError(f"ACP server returned initialization error: {err}")

        result = resp.get("result", {})
        if result.get("protocolVersion") != 1:
            raise AcpHandshakeError(
                f"Unsupported ACP protocol version {result.get('protocolVersion')}; expected 1."
            )

        self.server_info = result.get("agentInfo", {})
        self.server_capabilities = result.get("agentCapabilities", {})
        logger.info(
            "[AcpClient] Successfully connected to %s (v%s)",
            self.server_info.get("name", "Unknown Server"),
            self.server_info.get("version", "?"),
        )
        return result

    def cancel(self, grace_period_sec: float = 3.0) -> None:
        """
        Gracefully requests cancellation via JSON-RPC, waiting grace_period_sec
        before terminating the process tree.
        """
        logger.info("[AcpClient] Initiating graceful cancellation notification.")
        try:
            self.send_notification("session/cancel", {"sessionId": self.session_id} if self.session_id else {})
            self.send_notification("$/cancelRequest", {})
        except Exception as e:
            logger.debug("[AcpClient] Cancellation notification exception: %s", e)

        # Wait up to grace_period_sec for process exit
        start_wait = time.time()
        while time.time() - start_wait < grace_period_sec:
            if self.proc.poll() is not None:
                logger.info("[AcpClient] Process exited gracefully upon cancellation.")
                return
            time.sleep(0.1)

        # If still running, force terminate the Job Object process tree
        logger.warning("[AcpClient] Process did not exit within %0.1fs; force-terminating Job Object.", grace_period_sec)
        self.proc.terminate_tree()

    def close(self) -> None:
        """Shuts down client and cleans up reader thread."""
        self._running = False
        if self.proc:
            self.proc.terminate_tree()
