"""
actions/opencode_agent.py — OpenCode Zen integration (async).

Delegates multi-file coding tasks to OpenCode CLI using Zen free models.
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
from memory.config_manager import get_opencode_model

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}


def _find_opencode_bin() -> Optional[str]:
    b = shutil.which("opencode") or shutil.which("opencode.exe")
    if b:
        return b
    home_bin = Path.home() / ".opencode" / "bin" / (
        "opencode.exe" if platform.system() == "Windows" else "opencode"
    )
    return str(home_bin) if home_bin.exists() else None


def _resolve_model(model: Optional[str]) -> str:
    selected = (model or "").strip() or get_opencode_model()
    if selected.startswith("zen/"):
        name = selected.replace("zen/", "")
        if "nemotron" in name:
            return "opencode/nemotron-3-ultra-free"
        if "pickle" in name:
            return "opencode/big-pickle"
        if "glm" in name:
            return "opencode/glm-5.3-flash-free"
        if "mimo" in name:
            return "opencode/mimo-v2.6-flash-free"
        return f"opencode/{name}"
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

logger = logging.getLogger("zezo.opencode")

MAX_CLI_PROMPT_LEN = 4000


def _prepare_cli_task(task: str, repo_path: Path) -> str:
    """
    Ensure the CLI prompt does not exceed safe command-line buffer limits
    (Windows CreateProcess limit is 32,767 chars; cmd.exe limit is 8,191 chars).
    If the prompt exceeds MAX_CLI_PROMPT_LEN or contains raw HTML blueprints,
    write the full task specification to TASK_SPEC.md in the repo workspace
    and return an instruction pointing OpenCode to that file.
    """
    if not task:
        return ""

    task_lower = task.lower()
    is_large = len(task) > MAX_CLI_PROMPT_LEN
    has_raw_html = "```html" in task_lower or "<html" in task_lower or "<!doctype" in task_lower

    if not (is_large or has_raw_html):
        return task

    try:
        repo_path.mkdir(parents=True, exist_ok=True)
        spec_file = repo_path / "TASK_SPEC.md"
        spec_file.write_text(task, encoding="utf-8")
        logger.info(
            "Task prompt (%d chars, has_raw_html=%s) exceeds safe CLI limit (%d). "
            "Wrote specifications to %s",
            len(task),
            has_raw_html,
            MAX_CLI_PROMPT_LEN,
            spec_file,
        )
        return (
            "Execute the coding task defined in TASK_SPEC.md. "
            "Read TASK_SPEC.md in the workspace first, then implement all specifications, "
            "requirements, and guidelines exactly as described."
        )
    except Exception as e:
        logger.warning(
            "Failed writing TASK_SPEC.md (%s); falling back to truncated prompt for CLI safety",
            e,
        )
        return task[:MAX_CLI_PROMPT_LEN]

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
    """Runs in the background thread. Streams progress, respects cancel."""
    repo_val = params.get("repo") or params.get("project_path") or params.get("repo_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = str(resolved_p or (Path.home() / "Desktop" / "website").resolve())
    else:
        repo = str(Path(repo_val).resolve())

    task = params.get("task", "")
    model = params.get("model") or get_opencode_model()
    opencode_bin = params.get("bin") or _find_opencode_bin()

    repo_path = Path(repo)
    _ensure_gitignore(repo_path)
    snapshot = capture_repo_snapshot(repo)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if not opencode_bin:
        err_msg = "OpenCode CLI binary not found"
        if ctx and hasattr(ctx, "on_fail"):
            ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": repo, "model": model}

    cli_task = _prepare_cli_task(task, repo_path)
    cmd = [opencode_bin, "run", cli_task, "--model", model, "--auto"]

    if ctx and hasattr(ctx, "report"):
        ctx.report(2, f"launching OpenCode in {Path(repo).name}")

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

    hJob = None
    hJob = _create_throttled_job(mask, 0x00000040)
    if hJob:
        _assign_pid_to_job(hJob, proc.pid)

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
                return {"status": "cancelled", "lines": line_count}
            text = line.rstrip()
            if not text:
                continue
            line_count += 1
            tail.append(text)
            if len(tail) > 30:
                tail.pop(0)

            # coarse progress: first 90% based on line count heuristic
            pct = min(90, 5 + line_count)
            if ctx and hasattr(ctx, "report"):
                ctx.report(pct, text)
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
            undo_entry = register_repo_undo(repo, snapshot, "OpenCode")
            if undo_entry and undo_entry.get("changes"):
                first_file = Path(undo_entry["changes"][0]["path"]).name
                from memory.memory_manager import remember
                remember("active_file", first_file, category="projects")
        except Exception as e:
            logger.debug("OpenCode undo registration failed: %s", e)

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
            err_detail = f"OpenCode process exited with code {proc.returncode}"
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


def opencode_agent(parameters: dict, player=None, speak=None) -> str:
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task you want OpenCode to run."

    explicit_path = (
        parameters.get("project_path") or parameters.get("path") or ""
    )
    repo, source = resolve(explicit=explicit_path)

    if repo is None:
        return (
            "I need to know which project to work in. "
            "Which folder should OpenCode edit? "
            "Give me the path, for example 'E:/projects/myapp'."
        )

    if _is_root_dir(Path(repo)):
        return (
            "Please point me at a specific subfolder, not the Desktop root "
            "(for example 'Desktop/my_project' or a dedicated repo folder)."
        )

    opencode_bin = _find_opencode_bin()
    if not opencode_bin:
        return (
            "OpenCode CLI is not installed. Run: "
            "npm install -g opencode-ai@latest   then   "
            "opencode auth login --provider zen"
        )

    model = _resolve_model(parameters.get("model") or parameters.get("model_id"))
    scope_type = parameters.get("scope_type")
    color_theme = parameters.get("color_theme")

    # Resolve design system tokens if UI/Web task
    from core.design_resolver import is_ui_task, resolve_design, format_design_prompt
    resolved_design = None
    task_with_design = task
    if is_ui_task(task):
        resolved_design = resolve_design(task, repo_path=repo, scope=scope_type, theme=color_theme)
        if resolved_design and resolved_design.is_active():
            reference_provisioned = False
            try:
                repo.mkdir(parents=True, exist_ok=True)
                ref_dst = repo / "reference.html"
                if getattr(resolved_design, "source_path", None) and resolved_design.source_path.exists():
                    import shutil
                    shutil.copy2(resolved_design.source_path, ref_dst)
                    reference_provisioned = True
                elif getattr(resolved_design, "full_raw_html", None) and resolved_design.full_raw_html.strip():
                    ref_dst.write_text(resolved_design.full_raw_html, encoding="utf-8")
                    reference_provisioned = True
                elif resolved_design.raw_html and resolved_design.raw_html.strip():
                    ref_dst.write_text(resolved_design.raw_html, encoding="utf-8")
                    reference_provisioned = True
            except Exception as e:
                logger.warning("Failed to provision reference.html for OpenCode: %s", e)

            if reference_provisioned:
                theme_val = color_theme or "dark_obsidian"
                design_directive = (
                    "CRITICAL THEME RE-SKINNING & STRUCTURAL FIDELITY DIRECTIVE:\n"
                    "- A curated design reference has been placed at 'reference.html'. Inspect it as your primary structural blueprint.\n"
                    "- DO NOT invent a new layout from scratch or output generic, unstyled boilerplate.\n"
                    "- 1:1 STRUCTURAL SKELETON ADAPTATION: You MUST preserve the exact section flow, container grids, navigation hierarchy, card framing, and typography scale of 'reference.html'.\n"
                    f"- THEME RE-SKINNING RULE: If 'reference.html' is in light mode or has a different palette, DO NOT discard it! Re-skin its CSS variables and styles into the requested theme ({theme_val}) without discarding the reference skeleton:\n"
                    "  * Transform light backgrounds into deep, refined obsidian/dark void tones (#07080c).\n"
                    "  * Invert typography to high-contrast crisp white and muted grays.\n"
                    "  * Inject glowing accents, subtle neon box-shadows, and gradient borders directly onto the existing card wrappers.\n"
                    "- CONTENT & BRANDING ADAPTATION: Retain the reference's exact geometry and layout, but replace all placeholder copy, titles, logos, and features with authentic content for the requested project.\n"
                    "- DIRECT CODE DELIVERY: Write 'index.html' directly to disk in a single pass.\n"
                    "- FORBIDDEN: Do not write intermediate Python builder scripts (e.g., 'build_*.py', 'cleanup.py') or generation helpers—deliver the complete, production-ready 'index.html' directly."
                )
                task_with_design = f"{task}\n\n{design_directive}"
            else:
                design_prompt = format_design_prompt(resolved_design)
                task_with_design = f"{task}\n\n{design_prompt}"

    # In-place execution for fleet tasks (eliminates phantom ZEZO CODER cards)
    run_in_place = bool(parameters.get("run_in_place", False))
    task_ctx = parameters.get("task_ctx")

    if run_in_place:
        worker_params = {
            "repo": str(repo),
            "task": task_with_design,
            "model": model,
            "bin": opencode_bin,
        }
        res = _run_worker(worker_params, ctx=task_ctx)
        import json
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "opencode_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task_with_design,
            "model": model,
            "bin": opencode_bin,
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
            f"Task: {task[:200] + ('...' if len(task) > 200 else '')}\nRepo: {repo}\nID: {task_id}\nSource: {source}\nStatus: {task_info.get('status', 'running')}",
        )

    if is_queued:
        return (
            f"Another coding task is currently running. I have queued ZEZO Coder task {task_id} "
            f"for {repo.name} to run automatically as soon as it finishes."
        )

    return (
        f"ZEZO Coder task {task_id} start ho gaya hai in {repo.name}. "
        "Background mein run ho raha hai, aap jab chaho status pooch sakte ho."
    )


TOOL = {
    "name": "opencode_run",
    "description": (
        "Run OpenCode CLI for a MULTI-FILE coding task: full features, "
        "refactors, bug fixes that span several files. "
        "DO NOT use for a single function (use code_helper). "
        "DO NOT use for a single-file edit (use kilo_run). "
        "DO NOT use for repo analysis without changes (use dev_agent). "
        "The tool returns a task_id immediately; never wait for the "
        "result in the same turn. Ask the user for the project path "
        "if you do not have one — do not guess."
    ),
    "risk": "code_execution",
    "enabled": True,
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "Clear, detailed coding task.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional OpenCode Zen model override.",
            },
            "project_path": {
                "type": "STRING",
                "description": (
                    "Absolute or user-typed path to the project folder. "
                    "If not given, JARVIS remembers the last used repo."
                ),
            },
        },
        "required": ["task"],
    },
    "handler": opencode_agent,
}

opencode_run = opencode_agent
