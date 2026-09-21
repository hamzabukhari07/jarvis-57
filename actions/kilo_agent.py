"""
actions/kilo_agent.py — Kilo Code integration (async).

Delegates multi-file edits and refactors to Kilo Code CLI using free models.
Returns immediately with a task_id; runs the CLI in a background thread.
Query progress with the task_status tool.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.repo_context import resolve
from core.task_manager import get_task_manager, TaskContext
from core.undo import capture_repo_snapshot, register_repo_undo
from memory.config_manager import get_kilo_model

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}


def _find_kilo_bin() -> Optional[str]:
    for name in ("kilo", "kilo.exe", "kilocode", "kilocode.exe"):
        b = shutil.which(name)
        if b:
            return b
    home_bin = Path.home() / ".kilo" / "bin" / (
        "kilo.exe" if platform.system() == "Windows" else "kilo"
    )
    return str(home_bin) if home_bin.exists() else None


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


import ctypes
import logging
from ctypes import wintypes

logger = logging.getLogger("zezo.kilo")

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
        info.BasicLimitInformation.LimitFlags = 0x00000010 | 0x00000020  # JOB_OBJECT_LIMIT_AFFINITY | JOB_OBJECT_LIMIT_PRIORITY_CLASS
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


def _run_worker(params: dict, ctx: TaskContext) -> dict:
    repo = params["repo"]
    task = params["task"]
    model = params["model"]
    kilo_bin = params["bin"]

    _ensure_gitignore(Path(repo))
    snapshot = capture_repo_snapshot(repo)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["NODE_OPTIONS"] = "--max-old-space-size=1024 --v8-pool-size=2"
    env["UV_THREADPOOL_SIZE"] = "2"
    env["OMP_NUM_THREADS"] = "2"
    env["V8_NUM_THREADS"] = "2"
    env["PISCINA_THREADS"] = "2"
    env["GOTO_NUM_THREADS"] = "2"
    env["OPENBLAS_NUM_THREADS"] = "2"
    env["MKL_NUM_THREADS"] = "2"

    cmd = [kilo_bin, "run", task, "--model", model, "--auto"]
    ctx.report(2, f"launching Kilo in {Path(repo).name}")

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

    ctx.set_pid(proc.pid)

    import psutil
    total = psutil.cpu_count(logical=True) or 4
    if total <= 4:
        cap = 2
    elif total <= 8:
        cap = total - 2
    else:
        cap = max(4, total // 2)
    cores = list(range(cap))
    mask = (1 << cap) - 1

    # 1. Hardware Job Object Assignment
    hJob = _create_throttled_job(mask, 0x00000040)  # IDLE_PRIORITY_CLASS
    if hJob:
        _assign_pid_to_job(hJob, proc.pid)

    # 2. psutil process tree throttle
    def _throttle_proc_tree(parent_pid: int) -> None:
        try:
            parent = psutil.Process(parent_pid)
            procs = [parent] + parent.children(recursive=True)
            for p in procs:
                try:
                    p.cpu_affinity(cores)
                    p.nice(psutil.IDLE_PRIORITY_CLASS)
                except Exception:
                    pass
        except Exception:
            pass

    _throttle_proc_tree(proc.pid)

    # Diagnostic log at startup
    try:
        p_diag = psutil.Process(proc.pid)
        ch_pids = [c.pid for c in p_diag.children(recursive=True)]
        print(
            f"[Kilo Diagnostic] PID={proc.pid} | affinity={p_diag.cpu_affinity()} | "
            f"nice={p_diag.nice()} | children={ch_pids} | job_assigned={bool(hJob)}"
        )
    except Exception:
        pass

    tail: list[str] = []
    line_count = 0
    import time
    last_diag_time = time.time()

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if ctx.cancelled():
                proc.terminate()
                return {"status": "cancelled", "lines": line_count}
            text = line.rstrip()
            if not text:
                continue
            line_count += 1
            tail.append(text)
            if len(tail) > 30:
                tail.pop(0)

            # Per-process monitoring & diagnostics every 5 seconds
            now = time.time()
            if now - last_diag_time >= 5.0:
                last_diag_time = now
                _throttle_proc_tree(proc.pid)
                try:
                    p = psutil.Process(proc.pid)
                    ch_info = []
                    total_proc_cpu = p.cpu_percent(interval=None)
                    for c in p.children(recursive=True):
                        c_cpu = c.cpu_percent(interval=None)
                        total_proc_cpu += c_cpu
                        ch_info.append(f"{c.name()}({c.pid})={c_cpu:.1f}%[aff={c.cpu_affinity()},nice={c.nice()}]")
                    
                    print(f"[Task {ctx.task_id}] PID={proc.pid} total_proc_cpu={total_proc_cpu:.1f}% | {' '.join(ch_info)}")
                except Exception:
                    pass

            ctx.report(min(90, 5 + line_count), text)
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
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

        if proc.returncode == 0:
            ctx.on_complete({
                "status": "success",
                "return_code": 0,
                "repo": repo,
                "model": model,
                "tail": tail[-10:],
            })
        elif not ctx.cancelled():
            err_detail = f"Kilo Code process exited with code {proc.returncode}"
            if tail:
                err_detail += f" ({' | '.join(tail[-3:])})"
            ctx.on_fail(err_detail)

    return {
        "status": "success" if proc.returncode == 0 else "failed",
        "return_code": proc.returncode,
        "repo": repo,
        "model": model,
        "tail": tail[-10:],
    }


def kilo_agent(parameters: dict, player=None, speak=None) -> str:
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
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

    model = _resolve_model(parameters.get("model"))

    tm = get_task_manager()
    task_id = tm.submit(
        "kilo_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "bin": kilo_bin,
        },
    )

    try:
        from memory.memory_manager import remember
        remember("active_project", str(repo), category="projects")
        import re
        file_matches = re.findall(r"[\w\-]+\.[a-zA-Z0-9]+", task)
        if file_matches:
            remember("active_file", file_matches[0], category="projects")
        remember("recent_task", task[:120], category="projects")
    except Exception:
        pass

    task_info = tm.status(task_id) or {}
    is_queued = task_info.get("status") == "queued"

    if player and hasattr(player, "show_content"):
        badge = "ZEZO CODER (QUEUED)" if is_queued else "ZEZO CODER"
        player.show_content(
            badge,
            f"Task: {task}\nRepo: {repo}\nID: {task_id}\nSource: {source}\nStatus: {task_info.get('status', 'running')}",
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
        "Run Kilo Code CLI for multi-file edits WITHIN one project: "
        "refactors, targeted changes across 2-3 files. "
        "DO NOT use for a single function (use code_helper). "
        "DO NOT use for a full autonomous feature (use opencode_run). "
        "Returns a task_id immediately. Ask the user for the project "
        "path if you do not have one."
    ),
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "Clear coding task."},
            "model": {"type": "STRING", "description": "Optional Kilo model override."},
            "project_path": {
                "type": "STRING",
                "description": "Project folder path.",
            },
        },
        "required": ["task"],
    },
    "handler": kilo_agent,
}
