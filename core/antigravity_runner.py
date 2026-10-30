"""Antigravity Execution Engine Worker.

Transparent, pure human-like CLI bridge for Google Antigravity (agy).
Spawns the native CLI binary, streams live stdout/stderr telemetry to the task
manager, enforces polite Windows Job Object CPU throttling, and tracks created
deliverables via before/after tree diffing.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.repo_context import resolve
from core.task_manager import TaskContext
from core.undo import capture_repo_snapshot, register_repo_undo

logger = logging.getLogger("zezo.antigravity_runner")

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}


def _find_antigravity_bin() -> Optional[str]:
    """Finds the native Antigravity CLI binary (tools/antigravity/agy.exe, agy on PATH)."""
    # 1. Project-local tools directory
    local_candidates = [
        Path("tools") / "antigravity" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        Path.cwd() / "tools" / "antigravity" / ("agy.exe" if platform.system() == "Windows" else "agy"),
    ]
    for lc in local_candidates:
        if lc.exists() and lc.is_file():
            return str(lc.resolve())

    # 2. System PATH
    for name in ("agy", "agy.exe", "antigravity", "antigravity.exe"):
        b = shutil.which(name)
        if b:
            return b

    # 3. Known user and local app data paths
    candidates = [
        Path.home() / "AppData" / "Local" / "agy" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        Path.home() / ".antigravity" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        Path.home() / ".agy" / "bin" / ("agy.exe" if platform.system() == "Windows" else "agy"),
        Path.home() / "AppData" / "Local" / "antigravity" / "bin" / ("antigravity.exe" if platform.system() == "Windows" else "antigravity"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)

    return None


def _resolve_model(model: Optional[str]) -> str:
    """Resolve configured model or normalize short aliases.

    Validates against ANTIGRAVITY_CLI_MODELS. If invalid or unrecognized, logs a warning
    and returns empty string so the caller omits --model and agy uses its default.
    """
    from memory.config_manager import get_antigravity_model, DEFAULT_ANTIGRAVITY_MODEL
    from core.models import ANTIGRAVITY_MODEL_ALIASES, ANTIGRAVITY_CLI_MODELS
    selected = (model or "").strip() or get_antigravity_model() or DEFAULT_ANTIGRAVITY_MODEL
    if not selected:
        return ""
    canonical = ANTIGRAVITY_MODEL_ALIASES.get(selected.lower(), selected)
    if canonical in ANTIGRAVITY_CLI_MODELS:
        return canonical
    logger.warning(
        "antigravity_runner: model '%s' (resolved from '%s') is not in ANTIGRAVITY_CLI_MODELS; "
        "omitting --model so agy uses its default.",
        canonical,
        selected,
    )
    return ""


def _is_root_dir(path: Path) -> bool:
    """Check if the path is Desktop root, Home root, or Drive root."""
    try:
        resolved = path.resolve()
        desktop = (Path.home() / "Desktop").resolve()
        home = Path.home().resolve()
        if resolved in (desktop, home) or len(resolved.parts) <= 1 or resolved.parent == resolved:
            return True
        return False
    except Exception:
        return False


def _ensure_gitignore(repo_path: Path) -> None:
    """Ensure minimal .gitignore exists in repo so scanners don't index huge dependencies."""
    try:
        if not repo_path.exists():
            return
        gi = repo_path / ".gitignore"
        ignore_entries = [
            "node_modules/",
            ".venv/",
            "venv/",
            "__pycache__/",
            ".next/",
            "dist/",
            "build/",
            "*.log",
        ]
        if not gi.exists():
            gi.write_text("\n".join(ignore_entries) + "\n", encoding="utf-8")
        else:
            existing = gi.read_text(encoding="utf-8", errors="ignore")
            missing = [entry for entry in ignore_entries if entry.strip("/") not in existing]
            if missing:
                with open(gi, "a", encoding="utf-8") as f:
                    f.write("\n# Auto-added ignore rules\n" + "\n".join(missing) + "\n")
    except Exception:
        pass


def _tree_snapshot(repo: Path) -> dict[str, int]:
    """Map of relative path -> mtime_ns for every file under `repo`."""
    out: dict[str, int] = {}
    skip = (".git", "node_modules", ".venv", "__pycache__")
    try:
        for p in repo.rglob("*"):
            if p.is_file() and not any(part in skip for part in p.parts):
                out[p.relative_to(repo).as_posix()] = p.stat().st_mtime_ns
    except Exception:
        pass
    return out


# ── Windows Job Object Throttling (Hardware-Enforced) ─────────────────────────

def _create_throttled_job(mask: int, priority: int = 0x00000040):
    if platform.system() != "Windows":
        return None
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hJob = kernel32.CreateJobObjectW(None, None)
        if not hJob:
            return None

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryLimit", ctypes.c_size_t),
                ("PeakJobMemoryLimit", ctypes.c_size_t),
            ]

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x00000010 | 0x00000020
        info.BasicLimitInformation.Affinity = mask
        info.BasicLimitInformation.PriorityClass = priority

        ret = kernel32.SetInformationJobObject(
            hJob, 9, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ret:
            kernel32.CloseHandle(hJob)
            return None
        return hJob
    except Exception as e:
        logger.debug("Could not create Windows Job Object: %s", e)
        return None


def _assign_pid_to_job(hJob, pid: int) -> bool:
    if not hJob or platform.system() != "Windows" or not isinstance(pid, int):
        return False
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hProc = kernel32.OpenProcess(0x1F0FFF, False, pid)
        if not hProc:
            return False
        ret = kernel32.AssignProcessToJobObject(hJob, hProc)
        kernel32.CloseHandle(hProc)
        return bool(ret)
    except Exception:
        return False


class _DummyTaskContext:
    def report(self, pct: int, msg: str = "") -> None:
        pass
    def set_pid(self, pid: int) -> None:
        pass
    def on_complete(self, payload: Any) -> None:
        pass
    def on_fail(self, error: str) -> None:
        pass
    def cancelled(self) -> bool:
        return False


def _launch_smart_preview(repo: Path) -> None:
    """Smart preview opener when deliverables are generated."""
    idx = repo / "index.html"
    if idx.exists():
        import webbrowser
        try:
            from actions.website_cloner import start_local_preview_server
            preview_url, _ = start_local_preview_server(repo)
            webbrowser.open(preview_url)
            logger.info("Preview server opened via HTTP on %s", preview_url)
        except Exception:
            webbrowser.open(idx.resolve().as_uri())


# ── Transparent CLI Bridge Worker ─────────────────────────────────────────────

def run_antigravity_worker(payload: dict, ctx: Optional[TaskContext] = None) -> dict:
    """Background worker executed by TaskManager or direct caller.

    Transparent, human-like bridge to native Antigravity CLI (agy).
    Delivers user prompt directly to the CLI binary, streams live telemetry,
    and returns output upon completion.
    """
    if ctx is None:
        ctx = _DummyTaskContext()  # type: ignore

    prompt = (payload.get("prompt") or payload.get("task") or "").strip()
    repo_val = payload.get("project_path") or payload.get("repo") or payload.get("repo_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
    else:
        repo = Path(repo_val).resolve()

    agy_bin = _find_antigravity_bin()
    if not agy_bin:
        err_msg = "Antigravity CLI binary (agy.exe) not found. Please ensure agy is in tools/antigravity or on PATH."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    repo.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)

    model_override = payload.get("model") or payload.get("model_id")
    resolved_model = _resolve_model(model_override)
    model_display = resolved_model or "default"
    skip_preview = bool(payload.get("skip_preview", False))
    owns_task = bool(payload.get("owns_task", True))

    ctx.report(5, f"Launching Antigravity CLI ({model_display}) in {repo.name}...")

    # Record telemetry prompt state
    payload["prompt_full"] = prompt
    try:
        if hasattr(ctx, "_mgr") and hasattr(ctx, "task_id"):
            with ctx._mgr._lock:
                ts = ctx._mgr._tasks.get(ctx.task_id)
                if ts and isinstance(ts.params, dict):
                    ts.params["prompt_full"] = prompt
    except Exception as e:
        logger.debug("Failed to set prompt_full on TaskState: %s", e)

    before_tree = _tree_snapshot(repo)

    # CLI Invocation: direct prompt passed via -p argument
    cmd = [agy_bin, "-p", prompt, "--add-dir", str(repo), "--dangerously-skip-permissions"]
    if resolved_model:
        cmd.extend(["--model", resolved_model])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        cmd,
        cwd=str(repo),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
        **_WIN_HIDE,
    )

    ctx.set_pid(proc.pid)

    # Windows Job Object CPU throttling
    hJob = None
    try:
        import psutil
        total_cores = psutil.cpu_count(logical=True) or 4
        cap_cores = max(2, total_cores // 2) if total_cores > 4 else total_cores
        mask = (1 << cap_cores) - 1
        hJob = _create_throttled_job(mask, 0x00000040)
        if hJob:
            _assign_pid_to_job(hJob, proc.pid)
    except Exception as e:
        logger.debug("Could not assign Job Object throttling: %s", e)

    start_time = time.time()
    last_pct = 10
    stdout_lines: List[str] = []

    def _reader():
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                txt = line.rstrip()
                if txt:
                    stdout_lines.append(txt)
        except Exception:
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    try:
        while proc.poll() is None:
            if ctx.cancelled():
                if hJob:
                    try:
                        ctypes.WinDLL("kernel32", use_last_error=True).TerminateJobObject(hJob, 1)
                    except Exception:
                        pass
                else:
                    proc.terminate()
                return {"status": "cancelled", "repo": str(repo)}

            time.sleep(0.5)
            now = time.time()
            elapsed = now - start_time

            line_count = len(stdout_lines)
            latest_line = stdout_lines[-1][:80] if stdout_lines else f"Running Antigravity CLI ({model_display})..."

            # Incremental progress reporting based on elapsed time and line output
            pct = min(92, int(15 + min(50, elapsed * 0.8) + min(25, line_count * 0.5)))
            pct = max(pct, last_pct)
            last_pct = pct

            ctx.report(pct, latest_line)
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        if hJob:
            try:
                ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(hJob)
            except Exception:
                pass

    if ctx.cancelled():
        return {"status": "cancelled", "repo": str(repo)}

    cli_output = "\n".join(stdout_lines)
    if "not logged into Antigravity" in cli_output or "not logged in" in cli_output.lower():
        err_msg = "Antigravity CLI is not signed in. Please sign in to the Antigravity CLI and retry."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    after_tree = _tree_snapshot(repo)
    created_list = [rel for rel, mt in after_tree.items() if before_tree.get(rel) != mt]
    entry_point = "index.html" if (repo / "index.html").exists() else "main.py"

    ctx.report(95, "Finalizing project build...")

    try:
        changed_count = register_repo_undo(repo, snapshot, "Antigravity Agent")
        if changed_count > 0 and created_list:
            first_file = Path(created_list[0]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Antigravity undo registration failed: %s", e)

    if not skip_preview and (repo / "index.html").exists():
        _launch_smart_preview(repo)

    is_success = proc.returncode == 0
    summary = (
        f"Antigravity CLI successfully finished in '{repo.name}'."
        if is_success
        else f"Antigravity CLI exited with code {proc.returncode}."
    )

    result_payload = {
        "status": "success" if is_success else "failed",
        "return_code": proc.returncode,
        "repo": str(repo),
        "project_name": repo.name,
        "files": created_list,
        "entry_point": entry_point,
        "summary": summary,
        "output": "\n".join(stdout_lines[-30:]),
        "prompt_full": prompt,
    }

    if owns_task:
        if is_success:
            ctx.on_complete(result_payload)
        else:
            ctx.on_fail(summary)

    return result_payload


# Backwards compatibility alias
_run_worker = run_antigravity_worker
