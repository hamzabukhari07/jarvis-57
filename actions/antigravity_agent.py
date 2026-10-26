from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.design_resolver import is_ui_task, resolve_design
from core.repo_context import resolve, remember_repo, get_unique_project_dir
from core.task_manager import get_task_manager, TaskContext
from core.undo import capture_repo_snapshot, register_repo_undo

logger = logging.getLogger("zezo.antigravity_agent")

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": (
            subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
        )
    }
else:
    _WIN_HIDE = {}


def _find_antigravity_bin() -> Optional[str]:
    """Finds the native Antigravity CLI binary (agy.exe / agy / antigravity)."""
    for name in ("agy", "agy.exe", "antigravity", "antigravity.exe"):
        b = shutil.which(name)
        if b:
            return b

    # Check known user and local app data paths
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
    # Alias map is the single source in core/models.py — no local copy.
    canonical = ANTIGRAVITY_MODEL_ALIASES.get(selected.lower(), selected)
    if canonical in ANTIGRAVITY_CLI_MODELS:
        return canonical
    logger.warning(
        "antigravity_agent: model '%s' (resolved from '%s') is not in ANTIGRAVITY_CLI_MODELS; "
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
    """Map of relative path -> mtime_ns for every file under `repo`.

    Used as a before/after diff to detect what a CLI actually wrote. A plain full-tree
    scan cannot tell a freshly written file from one that was already in the folder, which
    made a CLI that exited having written zero bytes look like a success (Issue 3).
    """
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


def _launch_static_preview(repo: Path) -> None:
    """Launches local HTTP preview server on ports 9400-9480 with fallback to file://."""
    import webbrowser
    try:
        from actions.website_cloner import start_local_preview_server
        preview_url, _ = start_local_preview_server(repo)
        webbrowser.open(preview_url)
        logger.info("Preview server opened via HTTP on %s", preview_url)
    except Exception as e:
        logger.warning("Local HTTP preview server failed: %s; falling back to file://", e)
        idx_file = repo / "index.html"
        if idx_file.exists():
            webbrowser.open(idx_file.resolve().as_uri())


def _try_launch_react_preview(repo: Path) -> bool:
    """Detects Vite / Next / React dev server and attempts background launch."""
    pkg = repo / "package.json"
    if not pkg.exists():
        return False
    try:
        cmd = ["npx", "vite", "--open"] if platform.system() != "Windows" else ["cmd.exe", "/c", "npx", "vite", "--open"]
        subprocess.Popen(
            cmd,
            cwd=str(repo),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        logger.info("Triggered React/Vite preview via npx vite --open in %s", repo)
        return True
    except Exception as e:
        logger.warning("Failed to auto-launch React preview: %s", e)
        return False


def _launch_smart_preview(repo: Path) -> None:
    """Routes preview intelligently based on project stack."""
    pkg = repo / "package.json"
    idx = repo / "index.html"

    # 1. If React / Vite / Next app:
    if pkg.exists():
        launched = _try_launch_react_preview(repo)
        if launched:
            return
        logger.info(
            "React/Vite project generated at %s. Suppressed raw file:// launch (run 'npm install && npm run dev' to view).",
            repo,
        )
        return

    # 2. Static HTML / Vanilla Web
    if idx.exists():
        _launch_static_preview(repo)
        return

    logger.debug("No index.html or package.json found in %s; skipping preview launch.", repo)


# ── Core Background Worker ───────────────────────────────────────────────────

def _run_worker(payload: dict, ctx: Optional[TaskContext] = None) -> dict:
    """Background worker executed by TaskManager. Uses Antigravity CLI if available."""
    if ctx is None:
        ctx = _DummyTaskContext()  # type: ignore
    task = payload.get("task", "")
    repo_val = payload.get("repo") or payload.get("project_path") or payload.get("repo_path")
    if not repo_val:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
    else:
        repo = Path(repo_val).resolve()
    repo.mkdir(parents=True, exist_ok=True)
    session_mem = payload.get("session_memory") or {}
    model_override = payload.get("model")
    skip_design = bool(payload.get("skip_design", False))
    skip_preview = bool(payload.get("skip_preview", False))
    is_verbatim = str(payload.get("prompt_mode") or "").strip().lower() == "verbatim"
    owns_task = bool(payload.get("owns_task", True))

    if not is_verbatim:
        _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)

    is_ui = is_ui_task(task) and not is_verbatim and not skip_design
    resolved_design = None
    if is_ui:
        resolved_design = resolve_design(task, session_memory=session_mem, repo_path=repo)
        if resolved_design and resolved_design.is_active():
            ctx.report(5, f"Design resolved: {resolved_design.source_name} ({resolved_design.source_type})")
        else:
            ctx.report(5, f"Planning architecture for '{repo.name}'...")
    else:
        ctx.report(5, f"Planning architecture for '{repo.name}'...")

    agy_bin = _find_antigravity_bin()
    if not agy_bin:
        err_msg = "Antigravity CLI binary (agy) not found. Install the Antigravity CLI to use this engine."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    resolved_model = _resolve_model(model_override)
    model_display = resolved_model or "default"
    ctx.report(8, f"Launching Antigravity CLI ({model_display}) in {repo.name}...")

    reference_provisioned = False
    if is_ui and resolved_design and resolved_design.is_active():
        try:
            ref_dst = repo / "reference.html"
            if getattr(resolved_design, "source_path", None) and resolved_design.source_path.exists():
                shutil.copy2(resolved_design.source_path, ref_dst)
                reference_provisioned = True
            elif getattr(resolved_design, "full_raw_html", None) and resolved_design.full_raw_html.strip():
                ref_dst.write_text(resolved_design.full_raw_html, encoding="utf-8")
                reference_provisioned = True
            elif resolved_design.raw_html and resolved_design.raw_html.strip():
                ref_dst.write_text(resolved_design.raw_html, encoding="utf-8")
                reference_provisioned = True
            if reference_provisioned:
                ctx.report(8, f"Design reference placed at reference.html ({resolved_design.source_name})")
        except Exception as e:
            logger.warning("Failed to provision reference.html: %s", e)

    prompt = task
    scope_type = payload.get("scope_type")
    entity_content = payload.get("entity_content")
    tech_stack = payload.get("tech_stack")
    color_theme = payload.get("color_theme")
    key_sections = payload.get("key_sections")

    pillar_instructions = []
    if scope_type:
        pillar_instructions.append(f"Scope Type: {scope_type}")
    if tech_stack:
        pillar_instructions.append(f"Tech Stack: {tech_stack}")
    if color_theme:
        pillar_instructions.append(f"Color Theme: {color_theme}")
    if key_sections:
        pillar_instructions.append(f"Key Sections: {key_sections}")
    if scope_type == "portfolio" and entity_content:
        pillar_instructions.append(f"Entity/Candidate Content & Projects: {entity_content}")

    if pillar_instructions:
        prompt = f"{prompt}\n\nBuild Specifications:\n" + "\n".join(f"- {p}" for p in pillar_instructions)

    if not is_verbatim and is_ui and reference_provisioned:
        prompt = (
            f"{prompt}\n\n"
            "Design Reference: A curated template has been placed at 'reference.html'. "
            "Inspect it as your read-only source of truth for styles, typography, and layout, and synthesize 'index.html' with authentic content."
        )

    before_tree = _tree_snapshot(repo)

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

    import psutil
    total_cores = psutil.cpu_count(logical=True) or 4
    cap_cores = max(2, total_cores // 2) if total_cores > 4 else total_cores
    cores = list(range(cap_cores))
    mask = (1 << cap_cores) - 1

    hJob = None
    hJob = _create_throttled_job(mask, 0x00000040)
    if hJob:
        _assign_pid_to_job(hJob, proc.pid)

    start_time = time.time()
    stdout_lines = []

    def _reader():
        try:
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

            time.sleep(1.0)
            disk_files = []
            try:
                for p in repo.glob("*"):
                    if p.is_file() and p.name not in (".gitignore", "reference.html", "TASK_SPEC.md"):
                        disk_files.append(p.name)
            except Exception:
                pass

            if disk_files:
                pct = min(90, max(20, 50 + len(disk_files) * 5))
                status_msg = f"Building files: {', '.join(disk_files[:3])}"
            else:
                status_msg = f"Running Antigravity CLI ({model_display})..."
                pct = 30
            ctx.report(pct, status_msg)
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

    real_files = [p for p in created_list if p not in (".gitignore", "reference.html")]
    has_entry = (repo / "index.html").exists() or (repo / "main.py").exists() or (repo / "src").exists()

    if not real_files or not has_entry:
        if ctx.cancelled():
            return {"status": "cancelled", "repo": str(repo)}
        err_msg = f"Antigravity CLI exited without creating valid project deliverables in {repo.name} (found: {created_list})."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    ctx.report(95, "Finalizing project build...")

    try:
        changed_count = register_repo_undo(repo, snapshot, "Antigravity Agent")
        if changed_count > 0 and created_list:
            first_file = Path(created_list[0]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Antigravity undo registration failed: %s", e)

    if not skip_preview:
        _launch_smart_preview(repo)

    result_payload = {
        "status": "success",
        "repo": str(repo),
        "project_name": repo.name,
        "files": created_list,
        "entry_point": entry_point,
        "summary": f"Successfully created {len(created_list)} project files in '{repo.name}'.",
        "design_source": resolved_design.source_name if resolved_design else None,
    }
    if owns_task:
        ctx.on_complete(result_payload)
    return result_payload


def antigravity_action(parameters: dict, player=None, speak=None, session_memory=None) -> str:
    """Action handler called by core.action_loader."""
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task or application you want Antigravity to build."

    gate_msg = check_greenfield_gate(task, parameters, caller_tool="antigravity_run")
    if gate_msg:
        return gate_msg

    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    if not explicit_path:
        # Extract folder hints from task prompt if explicitly mentioned
        folder_match = re.search(r'\b(?:in\s+(?:the\s+)?(?:folder|directory|dir)|folder|directory|dir)\s*[:=]?\s*["\']?([a-zA-Z0-9_\-\\/]+)["\']?', task, re.I)
        if folder_match:
            cand = folder_match.group(1).strip().strip("\"'")
            if not any(cand.lower().endswith(ext) for ext in (".html", ".css", ".js", ".py", ".md", ".json")):
                explicit_path = cand
    # In-place execution for fleet tasks (eliminates phantom ZEZO CODER cards)
    run_in_place = bool(parameters.get("run_in_place", False))

    if explicit_path:
        repo, source = resolve(explicit=explicit_path)
    elif run_in_place:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
        # used by non-in-place HUD badge
        source = "run_in_place"
    else:
        repo = get_unique_project_dir(task)
        source = "new_project"

    if repo is None:
        return (
            "I need to know which project to work in. "
            "Which folder should Antigravity build the code in? "
            "Give me the path, for example 'Desktop/website'."
        )

    if _is_root_dir(Path(repo)):
        return (
            "Please point me at a specific subfolder, not the Desktop root "
            "(for example 'Desktop/website' or a dedicated project folder)."
        )

    model = _resolve_model(parameters.get("model") or parameters.get("model_id"))

    task_ctx = parameters.get("task_ctx")
    # Opt-in worker flags. They must be forwarded explicitly: this function builds a fresh
    # worker_params dict, so anything not copied here never reaches _run_worker.
    #   skip_design  - reproduce an existing design verbatim instead of applying a blueprint
    #   skip_preview - the caller serves its own preview (a Vite tree renders blank over file://)
    #   prompt_mode  - "verbatim" sends `task` to the CLI untouched (no ZEZO directives)
    #   owns_task    - False when the caller passed its own task_ctx: that caller decides when
    #                  the card is complete, because it may still have to verify the artifact.
    extra_flags = {
        "skip_design": bool(parameters.get("skip_design", False)),
        "skip_preview": bool(parameters.get("skip_preview", False)),
        "prompt_mode": str(parameters.get("prompt_mode") or "").strip(),
        "owns_task": not bool(parameters.get("task_ctx")),
        "scope_type": parameters.get("scope_type"),
        "entity_content": parameters.get("entity_content"),
        "tech_stack": parameters.get("tech_stack"),
        "color_theme": parameters.get("color_theme"),
        "key_sections": parameters.get("key_sections"),
        "confirmed": parameters.get("confirmed", False),
    }

    if run_in_place:
        worker_params = {
            "repo": str(repo),
            "task": task,
            "model": model,
            "session_memory": session_memory if isinstance(session_memory, dict) else {},
            **extra_flags,
        }
        res = _run_worker(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "antigravity_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "session_memory": session_memory if isinstance(session_memory, dict) else {},
            **extra_flags,
        },
    )

    try:
        remember_repo(str(repo))
        from memory.memory_manager import remember
        file_matches = re.findall(r"[\w\-]+\.[a-zA-Z0-9]+", task)
        if file_matches:
            remember("active_file", file_matches[0], category="projects")
        remember("recent_task", task[:120], category="projects")
    except Exception:
        pass

    # Check design for instant voice feedback & HUD display
    design_name = "Default"
    design_info = ""
    if is_ui_task(task):
        early_res = resolve_design(task, session_memory=session_memory if isinstance(session_memory, dict) else {})
        if early_res and early_res.is_active():
            design_name = early_res.source_name
            design_info = f" using '{early_res.source_name}' design"

    task_info = tm.status(task_id) or {}
    is_queued = task_info.get("status") == "queued"

    if player and hasattr(player, "show_content"):
        badge = "ZEZO CODER (QUEUED)" if is_queued else "ZEZO CODER"
        player.show_content(
            badge,
            f"Task: {task}\nRepo: {repo}\nDesign: {design_name}\nID: {task_id}\nSource: {source}\nStatus: {task_info.get('status', 'running')}",
        )

    if is_queued:
        return (
            f"Another coding task is currently running. I have queued ZEZO Coder task {task_id} "
            f"for '{Path(repo).name}'{design_info}. It will start automatically when the current task finishes."
        )

    return (
        f"ZEZO Coder task start ho gaya hai (Task ID: {task_id}) in '{Path(repo).name}'{design_info}. "
        "Background mein build ho raha hai, aap jab chaho status pooch sakte ho."
    )


def check_greenfield_gate(task: str, parameters: Dict[str, Any], caller_tool: str = "antigravity_run") -> Optional[str]:
    """Check greenfield gate for web/portfolio builds. Returns None if build can proceed, or a prompt message if clarification is needed."""
    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    run_in_place = bool(parameters.get("run_in_place", False))

    if explicit_path or run_in_place:
        return None

    is_web = is_ui_task(task) or any(k in task.lower() for k in ("build website", "create website", "make website", "build landing page", "create landing page", "build portfolio", "create portfolio", "new website", "new landing page", "dashboard", "app"))
    if not is_web:
        return None

    scope_type = parameters.get("scope_type")
    tech_stack = parameters.get("tech_stack")
    color_theme = parameters.get("color_theme")
    key_sections = parameters.get("key_sections")
    entity_content = parameters.get("entity_content")
    confirmed = parameters.get("confirmed", False)

    missing = []
    if not scope_type:
        missing.append("scope_type (e.g. landing_page, portfolio, business_site, dashboard, component)")
    if scope_type == "portfolio" and not entity_content:
        missing.append("entity_content (candidate name, role, key projects, or attached resume PDF)")
    if not tech_stack:
        missing.append("tech_stack (e.g. single_file_html, modular_html_css_js, react_vite, nextjs)")
    if not color_theme:
        missing.append("color_theme (e.g. dark_obsidian, clean_minimal, luxury_gold, cyber_matrix, custom)")
    if not key_sections:
        missing.append("key_sections (comma-separated section names)")

    if missing:
        missing_str = ", ".join(missing)
        if scope_type == "portfolio":
            return f"Portfolio build clarification required. Please provide: {missing_str}. For portfolio scope, please share your name, role, key projects, or attach your resume PDF."
        return f"Greenfield build clarification required. Please provide: {missing_str}."

    if not confirmed:
        plan_summary = f"1-sentence plan: Build a {scope_type or 'web application'} using {tech_stack or 'single_file_html'} with {color_theme or 'clean_minimal'} theme and sections [{key_sections}]."
        return f"{plan_summary} Please confirm by setting confirmed=true to proceed."

    return None


# ── Action Discovery TOOL Schema ─────────────────────────────────────────────
TOOL = {
    "name": "antigravity_run",
    "description": (
        "Invoke the Google Antigravity Agent to autonomously build full software projects, "
        "multi-file web apps, backend APIs, and scripts inside a specific project folder. "
        "Runs asynchronously in background via native 'agy' CLI and returns immediately with a task_id. "
        "Progress can be queried anytime with task_status. "
        "For web/UI builds the agent honors the STACK requested in the task: it produces a static HTML/CSS/JS site by default, "
        "a single self-contained index.html when the user asks for 'single HTML'/'single-file HTML'/'no framework', "
        "and a React/Next.js project ONLY when the user explicitly asks for React/Next.js. "
        "Always copy the user's exact stack instructions into the task string."
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
                "description": "Comprehensive prompt explaining what application, feature, or code to build.",
            },
            "project_path": {
                "type": "STRING",
                "description": "Optional custom directory path (e.g. 'Desktop/website'). If omitted, resolves active project.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional Antigravity CLI model (e.g. 'gemini-3.7-flash-medium', 'claude-sonnet-4-6', 'gemini-3.8-flash-medium', 'claude-opus-4-6-thinking').",
            },
            "scope_type": {
                "type": "STRING",
                "enum": ["landing_page", "portfolio", "business_site", "dashboard", "component"],
                "description": "Scope type of the web build. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
            "entity_content": {
                "type": "STRING",
                "description": "User profile/bio/projects for portfolio or personal sites. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
            "tech_stack": {
                "type": "STRING",
                "enum": ["single_file_html", "modular_html_css_js", "react_vite", "nextjs"],
                "description": "Desired tech stack. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
            "color_theme": {
                "type": "STRING",
                "enum": ["dark_obsidian", "clean_minimal", "luxury_gold", "cyber_matrix", "custom"],
                "description": "Color theme. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
            "key_sections": {
                "type": "STRING",
                "description": "Comma-separated section names. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
            "confirmed": {
                "type": "BOOLEAN",
                "description": "True only after user hears the 1-sentence read-back and says yes. Set ONLY if user explicitly stated. Otherwise OMIT — ZEZO will ask.",
            },
        },
        "required": ["task"],
    },
    "handler": antigravity_action,
}
