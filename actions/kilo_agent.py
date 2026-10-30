"""actions/kilo_agent.py — Transparent Kilo Code Engine Bridge (async).

Standardized pure human-like CLI bridge for Kilo Code.
Delegates coding tasks directly to Kilo Code CLI without synthetic prompt wrappers.
Returns immediately with a task_id; runs the CLI in a background thread.
Query progress with the task_status tool.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Any, Optional

from core.repo_context import resolve
from core.task_manager import get_task_manager, TaskContext
from core.undo import capture_repo_snapshot, register_repo_undo
from memory.config_manager import get_kilo_model

logger = logging.getLogger("zezo.kilo")

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}


def _find_kilo_bin() -> Optional[str]:
    """Finds the native Kilo Code CLI binary."""
    # 1. Project-local tools directory
    local_candidates = [
        Path("tools") / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
        Path.cwd() / "tools" / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
    ]
    for lc in local_candidates:
        if lc.exists() and lc.is_file():
            return str(lc.resolve())

    # 2. System PATH
    for name in ("kilo", "kilo.exe", "kilocode", "kilocode.exe"):
        b = shutil.which(name)
        if b:
            return b

    # 3. Known install directories
    home_bin = Path.home() / ".kilo" / "bin" / (
        "kilo.exe" if platform.system() == "Windows" else "kilo"
    )
    if home_bin.exists():
        return str(home_bin)

    app_data_bin = Path.home() / "AppData" / "Local" / "kilo" / "bin" / (
        "kilo.exe" if platform.system() == "Windows" else "kilo"
    )
    if app_data_bin.exists():
        return str(app_data_bin)

    return None


def _resolve_model(model: Optional[str]) -> str:
    selected = (model or "").strip() or get_kilo_model()
    if not selected.startswith("kilo/"):
        return f"kilo/{selected}"
    return selected


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
    if not hJob or platform.system() != "Windows":
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


def _run_worker(params: dict, ctx: Optional[TaskContext] = None) -> dict:
    """Runs in the background thread. Streams telemetry, respects cancellation."""
    repo_val = params.get("project_path") or params.get("repo") or params.get("repo_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = str(resolved_p or (Path.home() / "Desktop" / "website").resolve())
    else:
        repo = str(Path(repo_val).resolve())

    prompt = (params.get("prompt") or params.get("task") or "").strip()
    model = params.get("model") or get_kilo_model()
    kilo_bin = params.get("bin") or _find_kilo_bin()

    repo_path = Path(repo)
    repo_path.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(repo_path)
    snapshot = capture_repo_snapshot(repo)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if not kilo_bin:
        err_msg = "Kilo Code CLI binary not found"
        if ctx and hasattr(ctx, "on_fail"):
            ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": repo, "model": model}

    cmd = [kilo_bin, "run", prompt, "--model", model, "--auto"]

    if ctx and hasattr(ctx, "report"):
        ctx.report(2, f"Launching Kilo in {repo_path.name}")

    proc = subprocess.Popen(
        cmd,
        cwd=repo,
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

    if ctx and hasattr(ctx, "set_pid"):
        ctx.set_pid(proc.pid)

    hJob = None
    try:
        import psutil
        total = psutil.cpu_count(logical=True) or 4
        cap = max(2, total // 2) if total > 4 else total
        mask = (1 << cap) - 1
        hJob = _create_throttled_job(mask, 0x00000040)
        if hJob:
            _assign_pid_to_job(hJob, proc.pid)
    except Exception as e:
        logger.debug("Could not assign Job Object throttling: %s", e)

    tail: list[str] = []
    line_count = 0

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if ctx and hasattr(ctx, "cancelled") and ctx.cancelled():
                if hJob:
                    try:
                        ctypes.WinDLL("kernel32", use_last_error=True).TerminateJobObject(hJob, 1)
                    except Exception:
                        pass
                else:
                    proc.terminate()
                return {"status": "cancelled", "lines": line_count, "repo": repo}

            text = line.rstrip()
            if not text:
                continue
            line_count += 1
            tail.append(text)
            if len(tail) > 30:
                tail.pop(0)

            pct = min(90, 5 + line_count)
            if ctx and hasattr(ctx, "report"):
                ctx.report(pct, text[:80])
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

        try:
            undo_entry = register_repo_undo(repo, snapshot, "Kilo Code")
            if undo_entry and undo_entry.get("changes"):
                first_file = Path(undo_entry["changes"][0]["path"]).name
                from memory.memory_manager import remember
                remember("active_file", first_file, category="projects")
        except Exception as e:
            logger.debug("Kilo undo registration failed: %s", e)

        is_cancelled = bool(ctx and hasattr(ctx, "cancelled") and ctx.cancelled())
        if proc.returncode == 0:
            if ctx and hasattr(ctx, "on_complete"):
                ctx.on_complete({
                    "status": "success",
                    "return_code": 0,
                    "repo": repo,
                    "model": model,
                    "tail": tail[-10:],
                })
        elif not is_cancelled:
            err_detail = f"Kilo Code process exited with code {proc.returncode}"
            if tail:
                err_detail += f" ({' | '.join(tail[-3:])})"
            if ctx and hasattr(ctx, "on_fail"):
                ctx.on_fail(err_detail)

    return {
        "status": "success" if proc.returncode == 0 else "failed",
        "return_code": proc.returncode,
        "repo": repo,
        "model": model,
        "tail": tail[-10:],
    }


def kilo_agent(parameters: dict, player=None, speak=None) -> str:
    prompt = (parameters.get("prompt") or parameters.get("task") or "").strip()
    if not prompt:
        return "Please tell me the coding task you want Kilo Code to run."

    explicit_path = (
        parameters.get("project_path") or parameters.get("path") or ""
    )
    repo, source = resolve(explicit=explicit_path)

    if repo is None:
        return (
            "I need to know which project to work in. "
            "Which folder should Kilo Code edit? "
            "Give me the path, for example 'E:/projects/myapp'."
        )

    if _is_root_dir(Path(repo)):
        return (
            "Please point me at a specific subfolder, not the Desktop root "
            "(for example 'Desktop/my_project' or a dedicated repo folder)."
        )

    kilo_bin = _find_kilo_bin()
    if not kilo_bin:
        return (
            "Kilo Code CLI is not installed. "
            "Run: npm install -g @kilocode/cli   or install "
            "Kilo Code from https://kilo.ai"
        )

    model = _resolve_model(parameters.get("model") or parameters.get("model_id"))
    run_in_place = bool(parameters.get("run_in_place", False))
    task_ctx = parameters.get("task_ctx")

    worker_params = {
        "repo": str(repo),
        "prompt": prompt,
        "task": prompt,
        "model": model,
        "bin": kilo_bin,
    }

    if run_in_place:
        res = _run_worker(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "kilo_agent",
        _run_worker,
        worker_params,
    )

    try:
        from memory.memory_manager import remember
        remember("active_project", str(repo), category="projects")
        import re
        file_matches = re.findall(r"[\w\-]+\.[a-zA-Z0-9]+", prompt)
        if file_matches:
            remember("active_file", file_matches[0], category="projects")
        remember("recent_task", prompt[:120], category="projects")
    except Exception:
        pass

    task_info = tm.status(task_id) or {}
    is_queued = task_info.get("status") == "queued"

    if player and hasattr(player, "show_content"):
        badge = "ZEZO CODER (QUEUED)" if is_queued else "ZEZO CODER"
        player.show_content(
            badge,
            f"Prompt: {prompt[:160]}\nRepo: {repo}\nID: {task_id}\nSource: {source}\nStatus: {task_info.get('status', 'running')}",
        )

    if is_queued:
        return (
            f"Another coding task is currently running. I have queued ZEZO Coder task {task_id} "
            f"for {repo.name} to run automatically as soon as it finishes."
        )

    return (
        f"ZEZO Coder task {task_id} start ho gaya hai in {repo.name}. "
        "Background mein refactor ho raha hai, aap jab chaho status pooch sakte ho."
    )


TOOL = {
    "name": "kilo_run",
    "description": (
        "Run Kilo Code CLI for multi-file edits, refactors, and feature updates "
        "inside a specific project directory via the native 'kilo' binary. "
        "Returns a task_id immediately."
    ),
    "risk": "code_execution",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "Clear coding prompt explaining what code to edit or build.",
            },
            "task": {
                "type": "STRING",
                "description": "Optional alias for prompt.",
            },
            "project_path": {
                "type": "STRING",
                "description": "Project folder path. If omitted, resolves active workspace repo.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional Kilo model override.",
            },
        },
        "required": ["prompt"],
    },
    "handler": kilo_agent,
}

handler = kilo_agent
kilo_run = kilo_agent
