"""Antigravity Execution Engine Worker.

Runs Antigravity CLI (agy) tasks asynchronously with hardware throttling,
live progress reporting, recursive tree snapshot diffing, and smart previews.
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
from typing import Any, Dict, List, Optional, Tuple

from core.design_resolver import is_ui_task, resolve_design
from core.prompts.prompt_synthesizer import (
    DASHBOARD,
    LANDING_PAGE,
    PORTFOLIO,
    SURGICAL_EDIT,
    detect_archetype,
    synthesize_prompt,
)
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


# ── Pre-flight Asset Provisioning ─────────────────────────────────────────────

def _provision_blueprint_and_template(
    resolved_design: Any,
    repo: Path,
    ctx: Optional[TaskContext] = None,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Provisions reference.html, DESIGN.md (<design-context> DSL), and master-template.html (< 40 KB)."""
    md_dst = repo / "DESIGN.md"
    mt_dst = repo / "master-template.html"
    ref_dst = repo / "reference.html"

    # 1. Determine reference source & write reference.html
    ref_source_path: Optional[Path] = None
    if getattr(resolved_design, "source_path", None) and resolved_design.source_path.exists():
        ref_source_path = resolved_design.source_path
        try:
            shutil.copy2(ref_source_path, ref_dst)
        except Exception as e:
            logger.debug("Failed copying source_path to reference.html: %s", e)
    elif getattr(resolved_design, "full_raw_html", None) and resolved_design.full_raw_html.strip():
        ref_dst.write_text(resolved_design.full_raw_html, encoding="utf-8")
        ref_source_path = ref_dst
    elif getattr(resolved_design, "raw_html", None) and resolved_design.raw_html.strip():
        ref_dst.write_text(resolved_design.raw_html, encoding="utf-8")
        ref_source_path = ref_dst

    if not ref_source_path or not ref_source_path.exists():
        return None, None

    # 2. Call core.design_resolver.generate_blueprint_and_template (which caches DESIGN.md & master-template.html)
    try:
        from core.design_resolver import generate_blueprint_and_template
        res = generate_blueprint_and_template(ref_source_path, repo)
        if isinstance(res, (tuple, list)) and len(res) >= 2:
            md_candidate, mt_candidate = Path(res[0]), Path(res[1])
            if md_candidate.exists() and mt_candidate.exists():
                md_dst, mt_dst = md_candidate, mt_candidate
    except Exception as e:
        logger.debug("design_resolver.generate_blueprint_and_template fallback: %s", e)

    # 3. Deterministic inline fallback if DESIGN.md or master-template are missing
    if not (md_dst.exists() and md_dst.stat().st_size > 0 and mt_dst.exists() and mt_dst.stat().st_size > 0):
        try:
            import re
            raw_text = ref_source_path.read_text(encoding="utf-8", errors="replace")
            # Strip heavy base64 data URIs
            clean_html = re.sub(
                r'data:image/[^"\'\s>]+',
                'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23222" width="100" height="100"/></svg>',
                raw_text,
            )

            # Master Template: functional interactive clone with semantic slots (< 40 KB)
            if not (mt_dst.exists() and mt_dst.stat().st_size > 0):
                slot_html = clean_html
                if "<!-- SLOT:" not in slot_html:
                    if "<main" in slot_html:
                        slot_html = slot_html.replace("<main", "<!-- SLOT:HERO_START -->\n<main", 1)
                    if "</main>" in slot_html:
                        slot_html = slot_html.replace("</main>", "</main>\n<!-- SLOT:HERO_END -->", 1)
                    else:
                        slot_html = f"<!-- SLOT:MAIN_START -->\n{slot_html}\n<!-- SLOT:MAIN_END -->"

                if len(slot_html.encode("utf-8")) > 40 * 1024:
                    slot_html = slot_html[: 38 * 1024] + "\n<!-- [Truncated to stay < 40 KB] -->\n</body>\n</html>"
                mt_dst.write_text(slot_html, encoding="utf-8")

            # DESIGN.md fallback
            if not (md_dst.exists() and md_dst.stat().st_size > 0):
                from core.design_extractor import generate_design_md
                md_content = generate_design_md(raw_text, title=ref_source_path.stem)
                md_dst.write_text(md_content, encoding="utf-8")
        except Exception as e:
            logger.warning("Fallback DESIGN.md/template generation failed: %s", e)

    md_ready = md_dst.exists() and md_dst.stat().st_size > 0
    mt_ready = mt_dst.exists() and mt_dst.stat().st_size > 0

    if md_ready and mt_ready and ctx:
        md_kb = md_dst.stat().st_size / 1024
        mt_kb = mt_dst.stat().st_size / 1024
        ctx.report(8, f"DESIGN.md ({md_kb:.1f} KB) & Master Template ({mt_kb:.1f} KB) provisioned")

    return (md_dst if md_ready else None, mt_dst if mt_ready else None)



# ── Core Background Worker ───────────────────────────────────────────────────

def run_antigravity_worker(payload: dict, ctx: Optional[TaskContext] = None) -> dict:
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

    agy_bin = _find_antigravity_bin()
    if not agy_bin:
        err_msg = "Antigravity CLI binary (agy) not found. Install the Antigravity CLI to use this engine."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    repo.mkdir(parents=True, exist_ok=True)
    session_mem = payload.get("session_memory") or {}
    model_override = payload.get("model")
    skip_design = bool(payload.get("skip_design", False))
    skip_preview = bool(payload.get("skip_preview", False))
    is_verbatim = str(payload.get("prompt_mode") or "").strip().lower() == "verbatim"
    owns_task = bool(payload.get("owns_task", True))
    scope_type = payload.get("scope_type")
    color_theme = payload.get("color_theme")

    if not is_verbatim:
        _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)

    is_ui = is_ui_task(task) and not is_verbatim and not skip_design
    resolved_design = None
    if is_ui:
        resolved_design = resolve_design(task, session_memory=session_mem, repo_path=repo, scope=scope_type, theme=color_theme)
        if resolved_design and resolved_design.is_active():
            ctx.report(5, f"Design resolved: {resolved_design.source_name} ({resolved_design.source_type})")
        else:
            ctx.report(5, f"Planning architecture for '{repo.name}'...")
    else:
        ctx.report(5, f"Planning architecture for '{repo.name}'...")

    resolved_model = _resolve_model(model_override)
    model_display = resolved_model or "default"
    ctx.report(8, f"Launching Antigravity CLI ({model_display}) in {repo.name}...")

    reference_provisioned = False
    if is_ui and resolved_design and resolved_design.is_active():
        bp_file, mt_file = _provision_blueprint_and_template(resolved_design, repo, ctx)
        reference_provisioned = (repo / "reference.html").exists() or bool(bp_file and mt_file)

    target_file = payload.get("target_file") or "index.html"
    color_theme = payload.get("color_theme")
    theme_val = color_theme or "dark_obsidian"
    entity_content = payload.get("entity_content")
    tech_stack = payload.get("tech_stack")
    key_sections = payload.get("key_sections")

    if is_verbatim:
        prompt = task
    else:
        # 1. Detect archetype from scope_type or task text
        scope_lower = (scope_type or "").lower().strip()
        if scope_lower == "portfolio":
            archetype = PORTFOLIO
        elif scope_lower in ("dashboard", "admin", "analytics"):
            archetype = DASHBOARD
        elif scope_lower in ("component", "surgical"):
            archetype = SURGICAL_EDIT
        elif scope_lower in ("landing_page", "saas", "business_site"):
            archetype = LANDING_PAGE
        else:
            archetype = detect_archetype(task)

        # 2. Build structured specifications & content block
        spec_lines = []
        if scope_type:
            spec_lines.append(f"Scope Type: {scope_type}")
        if tech_stack:
            spec_lines.append(f"Tech Stack: {tech_stack}")
        if color_theme:
            spec_lines.append(f"Color Theme: {color_theme}")
        if key_sections:
            spec_lines.append(f"Key Sections: {key_sections}")
        if scope_type == "portfolio" and entity_content:
            spec_lines.append(f"Entity/Candidate Content & Projects:\n{entity_content}")

        content_parts = [f"Project Objective:\n{task}"]
        if spec_lines:
            content_parts.append("Build Specifications:\n" + "\n".join(f"- {s}" for s in spec_lines))
        content_str = "\n\n".join(content_parts)

        # 3. Build workspace slots & pre-flight asset directive
        slots_items = []
        if (repo / "DESIGN.md").exists():
            slots_items.append(
                "- 'DESIGN.md': Design System Rules & Tokens specification (<design-context> DSL). Single source of truth for colors, typography, radii, spacing, and component recipes."
            )
        if (repo / "master-template.html").exists():
            slots_items.append(
                "- 'master-template.html': Working interactive master clone with semantic slots (<!-- SLOT:HERO_START -->, <!-- SLOT:PROJECTS_START -->, etc.). "
                f"Adapt this file directly into '{target_file}' preserving all styling, animations, and JS interactions."
            )
        if (repo / "reference.html").exists():
            slots_items.append(
                "- 'reference.html': Original structural reference for visual layout alignment."
            )
        if not slots_items:
            slots_items.append(f"Direct delivery mode: generate clean semantic code into '{target_file}' with complete styling and interactive behaviors.")
        slots_str = "\n".join(slots_items)

        # 4. Synthesize prompt using core.prompts.prompt_synthesizer
        synth_context = {
            "target_file": target_file,
            "theme": theme_val,
            "content": content_str,
            "slots": slots_str,
            "task_directive": task,
        }
        prompt = synthesize_prompt(archetype=archetype, context=synth_context)

        # 5. Non-interactive batch execution directive
        prompt += (
            "\n\nCRITICAL BATCH EXECUTION DIRECTIVE:\n"
            "- USER STATUS: CONFIRMED. The user has already approved this plan and ordered the build.\n"
            "- You are in NON-INTERACTIVE BATCH MODE. DO NOT ask 'Should I proceed?' or wait for user input.\n"
            f"- You MUST immediately write and save all deliverables ('{target_file}') to disk in this turn.\n"
        )

    # 6. Telemetry State Tracking: expose full prompt for UI inspection
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
    mask = (1 << cap_cores) - 1

    hJob = None
    hJob = _create_throttled_job(mask, 0x00000040)
    if hJob:
        _assign_pid_to_job(hJob, proc.pid)

    start_time = time.time()
    last_heartbeat_time = start_time
    heartbeat_cycle = 0
    last_line_idx = 0
    last_pct = 30
    status_msg = f"Running Antigravity CLI ({model_display})..."
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

            time.sleep(0.5)
            now = time.time()
            elapsed = now - start_time

            # Recursive file detection using _tree_snapshot compared against before_tree
            current_tree = _tree_snapshot(repo)
            created_files = [
                rel for rel, mt in current_tree.items()
                if before_tree.get(rel) != mt and not rel.endswith((".gitignore", "reference.html", "DESIGN.md", "master-template.html", "TASK_SPEC.md"))
            ]

            # Dynamic progress based on elapsed time and output line count/activity
            line_count = len(stdout_lines)

            # Smooth progress advancement: 30% -> 50% -> 70% -> 85% -> 95%
            # Uses asymptotic curve for elapsed time so it never hard-freezes at 65% while CLI is generating
            if elapsed <= 30:
                time_pct = elapsed * 1.0  # 0 to 30s -> up to +30%
            elif elapsed <= 90:
                time_pct = 30 + (elapsed - 30) * 0.35  # 30s to 90s -> up to +51%
            else:
                time_pct = min(58, 51 + (elapsed - 90) * 0.1)  # 90s+ -> up to +58%

            activity_factor = min(20, int(line_count * 1.5))
            dynamic_pct = min(88, int(30 + time_pct + activity_factor))

            if created_files:
                # Boost progress when files detected
                file_boost = min(40, len(created_files) * 10)
                dynamic_pct = min(94, max(dynamic_pct, 55 + file_boost))

            dynamic_pct = max(dynamic_pct, last_pct)
            last_pct = dynamic_pct

            # 2.5s time-throttled heartbeat ensuring progress & live stdout updates continue
            has_new_stdout = line_count > last_line_idx
            latest_line = stdout_lines[-1].strip()[:80] if stdout_lines else ""

            if has_new_stdout:
                last_line_idx = line_count
                if latest_line:
                    status_msg = latest_line
                    last_heartbeat_time = now

            if (not has_new_stdout or not latest_line) and (now - last_heartbeat_time >= 2.5):
                last_heartbeat_time = now
                heartbeat_cycle += 1
                elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s" if elapsed >= 60 else f"{int(elapsed)}s"
                if created_files:
                    file_summary = f" ({', '.join(created_files[:3])})"
                    heartbeat_stages = [
                        f"Writing deliverable files{file_summary}...",
                        f"Synthesizing components & assets [{elapsed_str}]...",
                        f"Refining layout & dependencies ({len(created_files)} files created)...",
                    ]
                else:
                    heartbeat_stages = [
                        f"Synthesizing UI components [{elapsed_str}]...",
                        f"Generating layout & styles ({model_display})...",
                        f"Assembling design structure [{elapsed_str}]...",
                        f"Running Antigravity CLI ({model_display})...",
                    ]
                status_msg = heartbeat_stages[heartbeat_cycle % len(heartbeat_stages)]

            ctx.report(dynamic_pct, status_msg)
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

    real_files = [p for p in created_list if p not in (".gitignore", "reference.html", "DESIGN.md", "master-template.html")]
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
        "prompt_full": prompt,
    }
    if owns_task:
        ctx.on_complete(result_payload)
    return result_payload


# Backwards compatibility alias
_run_worker = run_antigravity_worker
