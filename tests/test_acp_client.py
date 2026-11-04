"""
tests/test_acp_client.py — Unit and integration tests for ACP client and handshake.
"""

import json
from pathlib import Path
import pytest

from core.engines.acp_client import AcpHandshakeError, AcpSessionClient, AcpTimeoutError
from core.engines.adapter import EngineLaunchConfig, EngineProtocol
from core.engines.antigravity import AntigravityEngineAdapter
from core.engines.process_supervisor import ProcessSupervisor


def test_acp_live_handshake_antigravity():
    """Performs real ACP handshake against installed agy.exe binary."""
    adapter = AntigravityEngineAdapter()
    bin_path = adapter.resolve_binary()
    assert bin_path is not None, "agy binary must be installed for live ACP handshake test"

    cmd = [str(bin_path), "acp", "--stdio"]
    proc = ProcessSupervisor.spawn(cmd, cwd=Path.cwd(), redirect_stdin=True)
    try:
        client = AcpSessionClient(proc)
        result = client.initialize(timeout=5.0)
        assert result.get("protocolVersion") == 1
        assert "agentInfo" in result
        assert "name" in result["agentInfo"]
        assert "Antigravity" in result["agentInfo"]["name"]
    finally:
        proc.terminate_tree()


def test_acp_handshake_invalid_protocol_version():
    class DummyProc:
        def __init__(self):
            import io
            self.pipe_file = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": 99}}) + "\n")
            self._posix_proc = None
            self.h_stdin_write = None

        def poll(self):
            return None

        def terminate_tree(self):
            pass

    client = AcpSessionClient(DummyProc())
    with pytest.raises(AcpHandshakeError) as exc:
        client.initialize(timeout=2.0)
    assert "protocol version 99" in str(exc.value).lower()


def test_acp_graceful_cancel():
    class DummyProc:
        def __init__(self):
            import io
            self.pipe_file = io.StringIO()
            self._posix_proc = None
            self.h_stdin_write = None
            self.terminated = False

        def poll(self):
            return 0 if self.terminated else None

        def terminate_tree(self):
            self.terminated = True

    proc = DummyProc()
    client = AcpSessionClient(proc)
    client.cancel(grace_period_sec=0.2)
    assert proc.terminated

