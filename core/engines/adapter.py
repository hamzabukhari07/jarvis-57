"""
core/engines/adapter.py — Unified EngineAdapter Base & Telemetry Normalizer.

Defines the core abstract contract, telemetry data structures, Event Allowlist
(strict thought suppression), safe ephemeral prompt file management, credential
protection, and indeterminate progress tracking for external coding engines.

Author: Hamza Bukhari
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.engines.process_supervisor import ContainedProcess, ProcessSupervisor
from core.task_manager import TaskContext, strip_ansi

logger = logging.getLogger("zezo.engines.adapter")


class EngineProtocol(str, Enum):
    CLI_STREAM = "cli_stream"
    ACP_STDIO = "acp_stdio"


@dataclass
class EngineLaunchConfig:
    engine_id: str
    prompt: str
    workspace_path: Path
    model: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    timeout_sec: int = 600
    risk_tier: str = "L1_MUTATION"
    extra_env: Dict[str, str] = field(default_factory=dict)
    protocol: EngineProtocol = EngineProtocol.CLI_STREAM
    auto_approve_edits: bool = False  # If True, uses non-dangerous auto modes (e.g. --mode auto)


@dataclass
class EngineEvent:
    event_type: str  # "status", "tool_use", "milestone", "output", "error", "complete"
    message: str
    step_label: str
    verified_milestone: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


# ── Event Allowlist & Strict Thought Privacy ──────────────────────────────────
# Only explicitly allowed event types can be emitted to telemetry / UI
ALLOWED_EVENT_TYPES: Set[str] = {
    "status",
    "step_start",
    "step_complete",
    "tool_use",
    "tool_call",
    "tool_result",
    "milestone",
    "status_message",
    "output",
    "error",
    "complete",
}

# Payload keys that must be dropped recursively
DISALLOWED_PAYLOAD_KEYS: Set[str] = {
    "thought",
    "thinking",
    "reasoning",
    "reasoning_content",
    "internal_monologue",
    "chain_of_thought",
}

_REDACT_KEY_PATTERNS = [
    re.compile(r"AIzaSy[A-Za-z0-9_-]{20,}"),       # Gemini API key
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),           # Groq API key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),            # OpenAI / general key
]


def redact_sensitive_tokens(text: str) -> str:
    """Masks API keys and credential tokens in log/telemetry strings."""
    if not text:
        return ""
    masked = text
    for pat in _REDACT_KEY_PATTERNS:
        masked = pat.sub("[REDACTED_API_KEY]", masked)
    return masked


def sanitize_event_payload(payload: Any) -> Any:
    """
    Recursively strips reasoning/thought fields from telemetry dictionaries
    and redacts API keys from string values.
    """
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if str(k).lower() in DISALLOWED_PAYLOAD_KEYS:
                continue
            sanitized[k] = sanitize_event_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_event_payload(item) for item in payload]
    elif isinstance(payload, str):
        # Secondary pass: strip any embedded <think>...</think> tags
        clean_str = re.sub(r"<think>[\s\S]*?</think>", "", payload, flags=re.IGNORECASE).strip()
        return redact_sensitive_tokens(clean_str)
    return payload


# ── Environment Sanitization & Safe Prompts ───────────────────────────────────

def build_sanitized_environment(extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Constructs a clean baseline environment inheriting essential OS variables
    and in-memory API keys from config_manager without disk leakage.
    """
    safe_keys = {
        "SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT",
        "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
        "HOMEDRIVE", "HOMEPATH", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
        "LANG", "LC_ALL", "TERM",
    }
    env: Dict[str, str] = {}
    for k in safe_keys:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v

    env["PYTHONIOENCODING"] = "utf-8"

    # Inject required keys in-memory from memory.config_manager
    try:
        from memory.config_manager import load_api_keys
        cfg_keys = load_api_keys()
        gem_key = os.environ.get("GEMINI_API_KEY") or cfg_keys.get("gemini_api_key", "")
        if gem_key:
            env["GEMINI_API_KEY"] = gem_key
        groq_key = os.environ.get("GROQ_API_KEY") or cfg_keys.get("groq_api_key", "")
        if groq_key:
            env["GROQ_API_KEY"] = groq_key
    except Exception as e:
        logger.debug("Could not resolve config keys: %s", e)

    if extra_env:
        env.update(extra_env)

    return env


class SafePromptManager:
    """
    Manages safe ephemeral temporary prompt files in .zezo_tmp/
    to protect against Win32 CreateProcessW command line limits (32,767 chars / WinError 206).
    Guarantees cleanup in finally: block without modifying user's .gitignore.
    """

    def __init__(self, workspace: Path, task_id: str):
        self.workspace = workspace.resolve()
        self.task_id = task_id
        self.tmp_dir = self.workspace / ".zezo_tmp"
        self.prompt_file: Optional[Path] = None

    def write_prompt_if_needed(self, prompt: str, threshold: int = 800) -> Tuple[str, Optional[Path]]:
        """
        If prompt > threshold, writes it to .zezo_tmp/prompt_<task_id>.md
        Returns (effective_prompt, prompt_file_path).
        """
        if len(prompt) <= threshold:
            return prompt, None

        try:
            self.tmp_dir.mkdir(parents=True, exist_ok=True)
            self.prompt_file = self.tmp_dir / f"prompt_{self.task_id}.md"
            self.prompt_file.write_text(prompt, encoding="utf-8")
            logger.info(
                "[SafePromptManager] Large prompt (%d chars) written to %s",
                len(prompt),
                self.prompt_file.name,
            )
            summary_directive = (
                f"Execute all directives and requirements in {self.prompt_file.as_posix()} "
                f"to complete the requested task."
            )
            return summary_directive, self.prompt_file
        except Exception as e:
            logger.warning("[SafePromptManager] Failed to write temp prompt: %s; using inline prompt", e)
            return prompt, None

    def cleanup(self) -> None:
        """Removes the ephemeral prompt file and deletes .zezo_tmp if empty."""
        try:
            if self.prompt_file and self.prompt_file.exists():
                self.prompt_file.unlink(missing_ok=True)
                self.prompt_file = None
            if self.tmp_dir.exists():
                # Remove directory only if empty
                remaining = list(self.tmp_dir.iterdir())
                if not remaining:
                    shutil.rmtree(self.tmp_dir, ignore_errors=True)
        except Exception as e:
            logger.debug("[SafePromptManager] Cleanup note: %s", e)


# ── Milestone Detector ────────────────────────────────────────────────────────

class MilestoneDetector:
    """
    Dual-track honest telemetry:
    1. Indeterminate activity tracking (elapsed timer, active step label).
    2. Concrete filesystem milestone verification on disk.
    """

    def __init__(self, workspace: Path, initial_files: Set[str]):
        self.workspace = workspace
        self.initial_files = set(initial_files)
        self.achieved_milestones: Set[str] = set()

    def check_milestones(self) -> List[str]:
        """Polls workspace root for verified deliverable files."""
        new_milestones = []
        milestone_candidates = [
            ("DESIGN.md", "Design Specification Generated"),
            ("preview.html", "Live HTML Preview Ready"),
            ("index.html", "Core Application Entry Point Created"),
            ("main.py", "Core Python Application Entry Point Created"),
            ("package.json", "Node Project Manifest Created"),
        ]

        for fname, label in milestone_candidates:
            if fname not in self.achieved_milestones and fname not in self.initial_files:
                fpath = self.workspace / fname
                try:
                    if fpath.is_file() and fpath.stat().st_size > 0:
                        self.achieved_milestones.add(fname)
                        new_milestones.append(f"[✓ {label}]")
                except Exception:
                    pass

        return new_milestones


# ── Abstract EngineAdapter Base ───────────────────────────────────────────────

class EngineAdapter(ABC):
    """
    Abstract interface defining the execution contract for external coding engines.
    """

    @abstractmethod
    def resolve_binary(self) -> Optional[Path]:
        """Discovers the absolute path to the engine binary, verifying existence."""
        pass

    @abstractmethod
    def build_cli_command(self, config: EngineLaunchConfig, prompt_file: Optional[Path] = None) -> List[str]:
        """Builds the secure argument-delimited subprocess command vector."""
        pass

    @abstractmethod
    def parse_stream_event(self, raw_line: str) -> Optional[EngineEvent]:
        """
        Normalizes vendor-specific stdout telemetry into unified EngineEvent instances.
        Treats output as untrusted input and suppresses internal thoughts via Event Allowlist.
        """
        pass

    def execute(self, config: EngineLaunchConfig, ctx: Optional[TaskContext] = None) -> Dict[str, Any]:
        """
        Executes the engine within a contained Win32 Job Object and streams honest telemetry.
        """
        bin_path = self.resolve_binary()
        if not bin_path or not bin_path.exists():
            err = f"Engine binary for '{config.engine_id}' not found."
            logger.warning(err)
            if ctx:
                ctx.on_fail(err)
            return {"status": "failed", "error": err, "workspace": str(config.workspace_path)}

        target_dir = config.workspace_path.resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        task_id = config.task_id or f"task_{int(time.time())}"
        prompt_mgr = SafePromptManager(target_dir, task_id)
        effective_prompt, prompt_file = prompt_mgr.write_prompt_if_needed(config.prompt)

        # Snapshot initial files for verified milestone tracking
        initial_files = {p.name for p in target_dir.iterdir() if p.is_file()} if target_dir.exists() else set()
        detector = MilestoneDetector(target_dir, initial_files)

        # Mode B: ACP Stdio Session with Auto-Fallback to Mode A
        if config.protocol == EngineProtocol.ACP_STDIO:
            acp_success, acp_res = self._try_acp_execution(config, target_dir, ctx, detector)
            if acp_success:
                prompt_mgr.cleanup()
                return acp_res
            logger.warning("[EngineAdapter] ACP execution unviable or failed; failing over to Mode A CLI streaming.")

        cmd = self.build_cli_command(config, prompt_file)
        env = build_sanitized_environment(config.extra_env)

        if ctx:
            ctx.report(-1, f"Launching {config.engine_id} ({config.model or 'default'})...")

        start_time = time.monotonic()
        stdout_lines: List[str] = []
        last_report_time = start_time
        last_step_msg = f"Running {config.engine_id}..."
        proc: Optional[ContainedProcess] = None

        try:
            # 1. Spawn process contained in Windows Job Object
            proc = ProcessSupervisor.spawn(cmd, cwd=target_dir, env=env)
            if ctx:
                ctx.set_pid(proc.pid)

            # 2. Stream output reader loop
            assert proc.pipe_file is not None
            while proc.poll() is None:
                if ctx and ctx.cancelled():
                    logger.info("[EngineAdapter] Task %s cancelled by user, terminating process tree.", task_id)
                    proc.terminate_tree()
                    return {"status": "cancelled", "workspace": str(target_dir)}

                now = time.monotonic()
                elapsed = now - start_time
                if elapsed > config.timeout_sec:
                    err_msg = f"Task timed out after {config.timeout_sec} seconds."
                    logger.warning("[EngineAdapter] %s for task %s", err_msg, task_id)
                    proc.terminate_tree()
                    if ctx:
                        ctx.on_fail(err_msg)
                    return {"status": "failed", "error": err_msg, "workspace": str(target_dir)}

                # Non-blocking line read check
                line = proc.pipe_file.readline()
                if line:
                    clean_line = strip_ansi(line.rstrip())
                    if clean_line:
                        stdout_lines.append(clean_line)
                        event = self.parse_stream_event(clean_line)
                        if event and event.event_type in ALLOWED_EVENT_TYPES:
                            if event.message:
                                last_step_msg = event.message

                # Check verified milestones
                new_milestones = detector.check_milestones()
                if new_milestones and ctx:
                    for ms in new_milestones:
                        ctx.report(-1, f"{ms} {last_step_msg}")

                # Honest indeterminate heartbeat every 2.0s
                if now - last_report_time >= 2.0:
                    mins = int(elapsed) // 60
                    secs = int(elapsed) % 60
                    time_tag = f"[{mins}m {secs:02d}s]" if mins > 0 else f"[{secs}s]"
                    if ctx:
                        ctx.report(-1, f"{last_step_msg} {time_tag}")
                    last_report_time = now

                time.sleep(0.05)

            # Drain any remaining lines
            for rem_line in iter(proc.pipe_file.readline, ""):
                if not rem_line:
                    break
                clean_line = strip_ansi(rem_line.rstrip())
                if clean_line:
                    stdout_lines.append(clean_line)

            exit_code = proc.wait(timeout=2.0)
            if exit_code != 0:
                err_text = f"{config.engine_id} exited with non-zero exit code {exit_code}"
                logger.warning(err_text)
                if ctx:
                    ctx.on_fail(err_text)
                return {
                    "status": "failed",
                    "exit_code": exit_code,
                    "error": err_text,
                    "workspace": str(target_dir),
                    "stdout": stdout_lines[-100:],
                }

            if ctx:
                ctx.report(100, f"{config.engine_id} execution completed successfully.")
                ctx.on_complete({"status": "done", "workspace": str(target_dir)})

            return {
                "status": "done",
                "exit_code": 0,
                "workspace": str(target_dir),
                "milestones": list(detector.achieved_milestones),
                "stdout_summary": stdout_lines[-50:],
            }

        except Exception as e:
            err = f"Execution error in {config.engine_id}: {str(e)}"
            logger.exception(err)
            if ctx:
                ctx.on_fail(err)
            return {"status": "failed", "error": str(e), "workspace": str(target_dir)}
        finally:
            if proc:
                proc.terminate_tree()
            prompt_mgr.cleanup()

    def _try_acp_execution(
        self,
        config: EngineLaunchConfig,
        target_dir: Path,
        ctx: Optional[TaskContext],
        detector: MilestoneDetector,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Attempts execution via ACP stdio client with 5.0s handshake timeout.
        Returns (True, result) on success, or (False, {}) to trigger failover to Mode A.
        """
        bin_path = self.resolve_binary()
        if not bin_path:
            return False, {}

        # Determine ACP CLI launch arguments
        acp_cmd = [str(bin_path), "acp"]
        if config.engine_id == "antigravity":
            acp_cmd.append("--stdio")

        env = build_sanitized_environment(config.extra_env)
        proc: Optional[ContainedProcess] = None
        try:
            from core.engines.acp_client import AcpSessionClient

            logger.info("[EngineAdapter] Spawning ACP process for %s...", config.engine_id)
            proc = ProcessSupervisor.spawn(acp_cmd, cwd=target_dir, env=env, redirect_stdin=True)

            client = AcpSessionClient(proc)
            init_res = client.initialize(timeout=5.0)
            logger.info("[EngineAdapter] ACP handshake established: %s", init_res.get("agentInfo", {}))

            if ctx:
                ctx.report(-1, f"ACP connected to {config.engine_id}.")

            client.send_notification("session/prompt", {
                "prompt": config.prompt,
                "workspace": str(target_dir),
            })

            start_time = time.monotonic()
            last_report_time = start_time
            last_step_msg = "Running ACP session..."

            while proc.poll() is None:
                if ctx and ctx.cancelled():
                    logger.info("[EngineAdapter] ACP task cancelled by user.")
                    client.cancel(grace_period_sec=3.0)
                    return True, {"status": "cancelled", "workspace": str(target_dir)}

                now = time.monotonic()
                elapsed = now - start_time
                if elapsed > config.timeout_sec:
                    client.cancel(grace_period_sec=1.0)
                    return True, {"status": "failed", "error": "ACP task timed out", "workspace": str(target_dir)}

                try:
                    notif = client._notifications.get_nowait()
                    method = notif.get("method") or notif.get("event")
                    if method in ("session/update", "status"):
                        params = sanitize_event_payload(notif.get("params", {}))
                        txt = params.get("message") or params.get("status")
                        if txt:
                            last_step_msg = str(txt)[:80]
                except Exception:
                    pass

                new_ms = detector.check_milestones()
                if new_ms and ctx:
                    for m in new_ms:
                        ctx.report(-1, f"{m} {last_step_msg}")

                if now - last_report_time >= 2.0:
                    mins = int(elapsed) // 60
                    secs = int(elapsed) % 60
                    tag = f"[{mins}m {secs:02d}s]" if mins > 0 else f"[{secs}s]"
                    if ctx:
                        ctx.report(-1, f"{last_step_msg} {tag}")
                    last_report_time = now

                time.sleep(0.05)

            exit_code = proc.wait(timeout=2.0)
            client.close()
            return True, {
                "status": "done" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "workspace": str(target_dir),
                "milestones": list(detector.achieved_milestones),
            }

        except Exception as e:
            logger.warning("[EngineAdapter] ACP execution failed or unsupported (%s); failing over to Mode A.", e)
            if proc:
                proc.terminate_tree()
            return False, {}
