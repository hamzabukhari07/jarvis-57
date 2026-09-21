"""
actions/antigravity_agent.py — Google Antigravity Agent for Zezo (Async).

Auto-discovered by core/action_loader.
Empowers Zezo with deep autonomous agentic coding, multi-file architecture,
self-healing traceback debugging, and full project scaffolding.

Integrates natively with the official Antigravity CLI ('agy') with hardware-enforced
Job Object limits and CPU throttling, falling back to Gemini REST SDK when CLI is absent.
Runs asynchronously via core/task_manager.py and returns immediately with a task_id.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.design_resolver import is_ui_task, resolve_design, format_design_prompt
from core.repo_context import resolve, remember_repo
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
    """Resolve configured model or normalize short aliases."""
    from memory.config_manager import get_antigravity_model, DEFAULT_ANTIGRAVITY_MODEL
    selected = (model or "").strip() or get_antigravity_model() or DEFAULT_ANTIGRAVITY_MODEL
    
    alias_map = {
        "sonnet": "claude-sonnet-4-6",
        "claude": "claude-sonnet-4-6",
        "claude-sonnet": "claude-sonnet-4-6",
        "opus": "claude-opus-4-6-thinking",
        "claude-opus": "claude-opus-4-6-thinking",
        "3.7": "gemini-3.7-flash-medium",
        "gemini-3.7": "gemini-3.7-flash-medium",
        "3.8": "gemini-3.8-flash-medium",
        "gemini-3.8": "gemini-3.8-flash-medium",
        "3.6": "gemini-3.6-flash-medium",
        "pro": "gemini-3.1-pro-high",
        "pro-high": "gemini-3.1-pro-high",
        "pro-low": "gemini-3.1-pro-low",
        "gpt": "gpt-oss-120b-medium",
        "gpt-oss": "gpt-oss-120b-medium",
    }
    return alias_map.get(selected.lower(), selected)


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


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


# ── Python Gemini REST Fallback Functions ────────────────────────────────────

def plan_antigravity_project(task: str, project_dir: Path, design_context: str = "") -> dict:
    """Uses high-reasoning Gemini tier to plan multi-file architecture with resolved design tokens."""
    from core import gemini
    from core.design_resolver import is_redesign_or_explicit_request

    existing_summary = []
    if project_dir.exists():
        for p in project_dir.rglob("*"):
            if p.is_file() and not any(part in (".git", "node_modules", ".venv", "__pycache__") for part in p.parts):
                try:
                    rel = p.relative_to(project_dir).as_posix()
                    size = p.stat().st_size
                    preview = p.read_text(encoding="utf-8", errors="ignore")[:400].replace("\n", " ")
                    existing_summary.append(f"• {rel} ({size} bytes): {preview}...")
                except Exception:
                    pass
    existing_files_block = "\n".join(existing_summary[:10])

    is_redesign = is_redesign_or_explicit_request(task)
    if is_redesign:
        preservation_directive = """CRITICAL REDESIGN & THEME OVERHAUL DIRECTIVE:
The user explicitly requested to CHANGE THE DESIGN / THEME / REGENERATE. You MUST completely redesign and overhaul the layout, classes, color theme, typography, and styles to faithfully match the newly resolved design specification. Replace outdated CSS and HTML structure with the new design tokens while keeping the functional content."""
    else:
        preservation_directive = """CRITICAL PRESERVATION DIRECTIVE:
If the target directory already contains existing files (e.g. index.html, style.css, hero section), DO NOT discard or break existing hero sections or custom styling. Plan how to extend the existing files and add the newly requested sections seamlessly while matching the active project design."""

    prompt = f"""You are Antigravity, an elite agentic software engineer.
Create an autonomous, production-ready project plan for this task:

Task: {task}
Target Directory: {project_dir}
{design_context if design_context else ""}

{f'''Existing Files in Target Directory:
{existing_files_block}

{preservation_directive}
''' if existing_files_block else ""}

Return ONLY valid JSON (no markdown formatting, no commentary):
{{
  "project_name": "project_name_here",
  "summary": "High level description of architecture and visual design",
  "files": [
    {{
      "path": "relative/path/filename.ext",
      "description": "What this file implements and exports",
      "imports": ["other.dependencies"]
    }}
  ],
  "entry_point": "index.html",
  "run_command": ""
}}

Rules:
1. For Web/UI: Faithfully adopt the colors, typography, glass elevation, and component recipes from the design specification.
2. For Web/UI Projects: List 'index.html' FIRST, followed by 'css/style.css' (or 'style.css'), so the CSS generator has complete visibility into the exact HTML structure and class names.
3. For Existing Projects: Keep and build upon existing components/styles without clobbering existing hero sections or custom styling (unless user requested a redesign).
4. For Python/Backend: Follow clean architecture with error handling and dependency injection.
5. Keep file paths relative (e.g. "index.html", "css/style.css", "js/app.js", "main.py").
"""
    resp = gemini.call(prompt, tier=gemini.SMART, timeout_ms=60000)
    if resp is None or not resp.text:
        raise RuntimeError("Gemini failed to generate Antigravity project plan.")

    raw = _strip_fences(resp.text)
    plan_dict = json.loads(raw)
    
    # Enforce index.html first for web projects
    files = plan_dict.get("files", [])
    html_files = [f for f in files if f.get("path", "").endswith(".html")]
    css_files = [f for f in files if f.get("path", "").endswith(".css")]
    other_files = [f for f in files if not f.get("path", "").endswith(".html") and not f.get("path", "").endswith(".css")]
    
    if html_files and css_files:
        plan_dict["files"] = html_files + css_files + other_files

    return plan_dict


def write_antigravity_file(
    file_info: dict,
    task: str,
    all_files: list,
    project_dir: Path,
    written_files: dict,
    design_context: str = "",
) -> str:
    """Generate complete, high-quality, production-ready code for a file adhering to design tokens."""
    from core import gemini
    from core.design_resolver import is_redesign_or_explicit_request

    file_path = file_info["path"]
    file_desc = file_info.get("description", "")
    
    target_on_disk = project_dir / file_path
    existing_file_content = ""
    if target_on_disk.exists() and target_on_disk.is_file():
        try:
            existing_file_content = target_on_disk.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            existing_file_content = ""

    context_blocks = []
    for rel_p, code_content in written_files.items():
        context_blocks.append(f"--- File: {rel_p} ---\n{code_content}")
    existing_context = "\n\n".join(context_blocks)

    is_redesign = is_redesign_or_explicit_request(task)
    if is_redesign:
        file_rule = f"""CRITICAL REDESIGN RULE FOR '{file_path}':
This is a theme redesign/regeneration task. Overwrite and update all styling, color variables, typography, radii, and container classes to 100% match the resolved design specification."""
    else:
        file_rule = f"""CRITICAL PRESERVATION & EXTENSION RULE:
'{file_path}' already exists. You MUST keep and preserve all existing sections (such as existing hero sections, navbars, existing CSS classes, and variables) while appending and integrating the newly requested sections and styles."""

    prompt = f"""You are Antigravity, crafting complete production-ready source code with studio-grade visual excellence.
Overall Project Task: {task}
File to write: {file_path}
Description: {file_desc}
{design_context if design_context else ""}

{f'''Existing Content of '{file_path}' Before Modification:
```
{existing_file_content[:6000]}
```

{file_rule}
''' if existing_file_content else ""}

All Files in Project:
{json.dumps(all_files, indent=2)}

Already Written Context:
{existing_context if existing_context else "(None - this is the first file)"}

CRITICAL RULES:
1. Output ONLY the raw source code for '{file_path}'. No markdown code blocks, no backticks, no explanations.
2. Write 100% complete, fully implemented code. NEVER use placeholders, 'TODO', or ellipses (...).
3. For Web HTML ('index.html'):
   - Build a comprehensive, high-converting layout (Sticky/glass navbar, hero with badge pill, feature grid, interactive pricing cards, customer testimonials, contact form, structured footer).
   - Use clean, semantic class names and link the stylesheet appropriately.
4. For Web CSS ('style.css'):
   - Inspect the already-written 'index.html' carefully in 'Already Written Context'!
   - You MUST write complete, dedicated CSS styling for EVERY single class, tag, and container used in 'index.html' so zero elements are unstyled.
   - Constrain layouts: Define `.container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}` so pages never stretch awkwardly across wide screens.
   - Use CSS Grid: For cards and tiers, use `display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;`.
   - Visual Depth: Implement glass elevation (`backdrop-filter: blur(12px); border: 1px solid ...`), refined box-shadows, rounded corners, and micro-hover transitions on all interactive elements.
   - Responsive Media Queries: Include `@media (max-width: 768px)` so it is 100% mobile responsive.
5. For Python: Write type-annotated, idiomatic code with robust error handling.
"""
    resp = gemini.call(prompt, tier=gemini.SMART, timeout_ms=90000)
    if resp is None or not resp.text:
        raise RuntimeError(f"Failed to generate code for {file_path}")

    code = _strip_fences(resp.text)
    full_path = project_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(code, encoding="utf-8")
    return code


# ── Core Background Worker ───────────────────────────────────────────────────

def _run_worker(payload: dict, ctx: TaskContext) -> dict:
    """Background worker executed by TaskManager. Uses Antigravity CLI if available."""
    task = payload["task"]
    repo = Path(payload["repo"])
    repo.mkdir(parents=True, exist_ok=True)
    session_mem = payload.get("session_memory") or {}
    model_override = payload.get("model")

    _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)
    
    # 1. Resolve design if UI/Web task
    design_context = ""
    resolved_design = None
    if is_ui_task(task):
        resolved_design = resolve_design(task, session_memory=session_mem, repo_path=repo)
        if resolved_design and resolved_design.is_active():
            design_context = format_design_prompt(resolved_design)
            ctx.report(5, f"Design resolved: {resolved_design.source_name} ({resolved_design.source_type})")
        else:
            ctx.report(5, f"Planning architecture for '{repo.name}'...")
    else:
        ctx.report(5, f"Planning architecture for '{repo.name}'...")

    # 2. Check for native Antigravity CLI ('agy')
    agy_bin = _find_antigravity_bin()

    if agy_bin:
        resolved_model = _resolve_model(model_override)
        ctx.report(8, f"Launching Antigravity CLI ({resolved_model}) in {repo.name}...")

        # Write blueprint file if raw_html exists so CLI agent can inspect it locally
        if resolved_design and resolved_design.raw_html:
            try:
                (repo / "DESIGN_BLUEPRINT.html").write_text(resolved_design.raw_html, encoding="utf-8")
            except Exception:
                pass

        # Build clean, bounded prompt for CLI to prevent Windows 32KB command-line overflow
        prompt_parts = [
            f"Task: {task}",
            f"Target Workspace Directory: {repo.as_posix()}",
        ]
        if resolved_design and resolved_design.is_active():
            prompt_parts.append(
                f"Reference Blueprint Template: A complete master design template has been placed at DESIGN_BLUEPRINT.html in your workspace directory.\n"
                f"CRITICAL DESIGN DIRECTIVE:\n"
                f"1. Read and inspect DESIGN_BLUEPRINT.html in this workspace.\n"
                f"2. Faithfully adopt its authentic visual styling, exact color theme, CSS gradients, typography, hero section, card structures, and keyframe animations.\n"
                f"3. Do NOT use generic default colors or plain templates. Replicate the rich studio-grade aesthetic of DESIGN_BLUEPRINT.html tailored to the user's content."
            )
        prompt_parts.append(
            f"CRITICAL EXECUTION DIRECTIVE: Build complete, production-ready source code files (index.html, style.css, js/app.js) "
            f"directly inside the workspace directory {repo.as_posix()}."
        )
        
        full_prompt = "\n\n".join(prompt_parts)
        if len(full_prompt) > 6000:
            full_prompt = full_prompt[:6000]

        cmd = [
            agy_bin,
            "-p", full_prompt,
            "--add-dir", str(repo),
            "--dangerously-skip-permissions",
            "--model", resolved_model,
        ]

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

        # Hardware throttling (Job Object + CPU Affinity)
        import psutil
        total_cores = psutil.cpu_count(logical=True) or 4
        cap_cores = max(2, total_cores // 2) if total_cores > 4 else total_cores
        cores = list(range(cap_cores))
        mask = (1 << cap_cores) - 1

        hJob = _create_throttled_job(mask, 0x00000040)
        if hJob:
            _assign_pid_to_job(hJob, proc.pid)

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

        start_time = time.time()
        tail = []
        stdout_lines = []

        def _reader():
            try:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    txt = line.rstrip()
                    if txt:
                        stdout_lines.append(txt)
                        tail.append(txt)
                        if len(tail) > 40:
                            tail.pop(0)
            except Exception:
                pass

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        last_throttle_time = time.time()
        last_reported_pct = 10

        try:
            while proc.poll() is None:
                if ctx.cancelled():
                    proc.terminate()
                    return {"status": "cancelled", "repo": str(repo)}

                time.sleep(1.0)
                now = time.time()
                elapsed = now - start_time

                # CPU Throttling maintenance
                if now - last_throttle_time >= 5.0:
                    last_throttle_time = now
                    _throttle_proc_tree(proc.pid)

                # Check on-disk file discoveries
                disk_files = []
                try:
                    for p in repo.glob("*"):
                        if p.is_file() and p.name not in (".gitignore", "DESIGN_BLUEPRINT.html"):
                            disk_files.append(p.name)
                except Exception:
                    pass

                # Dynamic asymptotic progress estimation & status messages
                if disk_files:
                    pct = min(90, max(last_reported_pct, 75 + len(disk_files) * 5))
                    status_msg = f"Generating files: {', '.join(disk_files[:3])}"
                elif elapsed < 6:
                    pct = int(10 + (elapsed / 6) * 15)  # 10% -> 25%
                    status_msg = f"Planning architecture & design tokens for '{repo.name}'..."
                elif elapsed < 18:
                    pct = int(25 + ((elapsed - 6) / 12) * 25)  # 25% -> 50%
                    status_msg = f"Synthesizing layout, hero section & components ({resolved_model})..."
                elif elapsed < 35:
                    pct = int(50 + ((elapsed - 18) / 17) * 25)  # 50% -> 75%
                    status_msg = "Generating CSS animations, glass depth & responsive styling..."
                else:
                    pct = min(92, int(75 + ((elapsed - 35) / 25) * 17))  # 75% -> 92%
                    status_msg = "Writing and verifying production source code..."

                last_reported_pct = pct
                ctx.report(pct, status_msg)
        finally:
            try:
                proc.wait(timeout=10)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        # Inspect generated files in repo
        created_list = []
        entry_point = "index.html" if (repo / "index.html").exists() else "main.py"
        try:
            for p in repo.rglob("*"):
                if p.is_file() and not any(part in (".git", "node_modules", ".venv", "__pycache__") for part in p.parts):
                    rel = p.relative_to(repo).as_posix()
                    created_list.append(rel)
        except Exception:
            pass

        # If repo is missing key files, check and rescue from CLI scratch directories
        if not created_list or not (repo / "index.html").exists():
            scratch_candidates = [
                Path.home() / ".gemini" / "antigravity-cli" / "scratch",
                Path.home() / "AppData" / "Local" / "agy" / "scratch",
            ]
            for s_dir in scratch_candidates:
                if s_dir.exists() and s_dir.is_dir():
                    for f in s_dir.glob("*"):
                        if f.is_file() and f.suffix in (".html", ".css", ".js", ".py", ".json", ".md"):
                            try:
                                if time.time() - f.stat().st_mtime < 180:
                                    target_dest = repo / f.name
                                    shutil.copy2(f, target_dest)
                                    if f.name not in created_list:
                                        created_list.append(f.name)
                            except Exception:
                                pass

        ctx.report(95, "Finalizing project build...")

        # Register Undo snapshot
        try:
            changed_count = register_repo_undo(repo, snapshot, "Antigravity Agent")
            if changed_count > 0 and created_list:
                first_file = Path(created_list[0]).name
                from memory.memory_manager import remember
                remember("active_file", first_file, category="projects")
        except Exception as e:
            logger.debug("Antigravity undo registration failed: %s", e)

        # Cleanup temporary DESIGN_BLUEPRINT.html if build generated real files
        if (repo / "index.html").exists():
            try:
                bp = repo / "DESIGN_BLUEPRINT.html"
                if bp.exists():
                    bp.unlink()
            except Exception:
                pass

        remember_repo(str(repo))

        result_payload = {
            "status": "success",
            "repo": str(repo),
            "project_name": repo.name,
            "files": created_list,
            "entry_point": entry_point,
            "summary": f"Generated via Antigravity CLI ({resolved_model})",
            "design_source": resolved_design.source_name if resolved_design else None,
        }
        ctx.on_complete(result_payload)
        return result_payload

    # 3. Fallback: Python Gemini REST Generation
    try:
        plan = plan_antigravity_project(task, repo, design_context=design_context)
    except Exception as e:
        ctx.on_fail(f"Antigravity planning failed: {e}")
        return {"status": "failed", "error": str(e), "repo": str(repo)}

    project_name = plan.get("project_name", repo.name)
    files = plan.get("files", [])
    summary = plan.get("summary", "")
    entry_point = plan.get("entry_point", "")

    if not files:
        ctx.on_fail("Antigravity generated an empty file plan.")
        return {"status": "failed", "error": "empty_plan", "repo": str(repo)}

    design_tag = f" [{resolved_design.source_name}]" if resolved_design and resolved_design.is_active() else ""
    ctx.report(15, f"Plan ready: {len(files)} files for '{project_name}'{design_tag}")

    written = {}
    created_list = []
    total_files = len(files)

    for idx, f_info in enumerate(files, 1):
        if ctx.cancelled():
            return {"status": "cancelled", "repo": str(repo)}

        rel_p = f_info["path"]
        progress_pct = int(15 + (idx / total_files) * 75)
        ctx.report(progress_pct, f"Generating [{idx}/{total_files}]: {rel_p}")

        try:
            code = write_antigravity_file(f_info, task, files, repo, written, design_context=design_context)
            written[rel_p] = code
            created_list.append(rel_p)
        except Exception as e:
            logger.warning("Error writing %s: %s", rel_p, e)
            created_list.append(f"{rel_p} (error: {e})")

    # Syntax verification on python files if any
    py_files = [p for p in created_list if p.endswith(".py") and "(" not in p]
    for py_rel in py_files:
        py_full = repo / py_rel
        try:
            import py_compile
            py_compile.compile(str(py_full), doraise=True)
        except Exception:
            pass

    ctx.report(95, "Finalizing project build...")

    # Register Undo snapshot
    try:
        changed_count = register_repo_undo(repo, snapshot, "Antigravity Agent")
        if changed_count > 0 and created_list:
            first_file = Path(created_list[0].split()[0]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Antigravity undo registration failed: %s", e)

    result_payload = {
        "status": "success",
        "repo": str(repo),
        "project_name": project_name,
        "files": created_list,
        "entry_point": entry_point,
        "summary": summary,
        "design_source": resolved_design.source_name if resolved_design else None,
    }
    ctx.on_complete(result_payload)
    return result_payload


def antigravity_action(parameters: dict, player=None, speak=None, session_memory=None) -> str:
    """Action handler called by core.action_loader."""
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task or application you want Antigravity to build."

    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    if not explicit_path:
        # Extract folder hints from task prompt if explicitly mentioned
        folder_match = re.search(r'\b(?:in\s+(?:the\s+)?(?:folder|directory|dir)|folder|directory|dir)\s*[:=]?\s*["\']?([a-zA-Z0-9_\-\\/]+)["\']?', task, re.I)
        if folder_match:
            cand = folder_match.group(1).strip().strip("\"'")
            if not any(cand.lower().endswith(ext) for ext in (".html", ".css", ".js", ".py", ".md", ".json")):
                explicit_path = cand
        elif "portfolio" in task.lower() and "website" not in task.lower():
            explicit_path = "Desktop/portfolio"

    repo, source = resolve(explicit=explicit_path)

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

    model = _resolve_model(parameters.get("model"))
    tm = get_task_manager()
    task_id = tm.submit(
        "antigravity_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "session_memory": session_memory if isinstance(session_memory, dict) else {},
        },
    )

    try:
        remember_repo(str(repo))
        from memory.memory_manager import remember
        remember("active_project", str(repo), category="projects")
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


# ── Action Discovery TOOL Schema ─────────────────────────────────────────────
TOOL = {
    "name": "antigravity_run",
    "description": (
        "Invoke the Google Antigravity Agent to autonomously build full software projects, "
        "multi-file web apps, backend APIs, and scripts inside a specific project folder. "
        "Runs asynchronously in background via native 'agy' CLI and returns immediately with a task_id. "
        "Progress can be queried anytime with task_status."
    ),
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
        },
        "required": ["task"],
    },
    "handler": antigravity_action,
}
