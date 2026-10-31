"""Kilo Code Execution Engine Worker.

Transparent CLI bridge for Kilo Code.
Spawns the native Kilo Code CLI binary, streams live stdout/stderr telemetry to the
task manager with asymptotic progress calculation, tracks created deliverables via
fast file checks, and executes without artificial CPU throttling.
"""
from __future__ import annotations

import json
import logging
import math
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.repo_context import resolve
from core.task_manager import TaskContext
from core.undo import capture_repo_snapshot, register_repo_undo
from memory.config_manager import get_kilo_model

logger = logging.getLogger("zezo.kilo_runner")

if platform.system() == "Windows":
    _WIN_HIDE = {
        "creationflags": subprocess.CREATE_NO_WINDOW
    }
else:
    _WIN_HIDE = {}


def _find_kilo_bin() -> Optional[str]:
    """Finds the native Kilo Code CLI binary."""
    # 1. Project-local tools directory
    local_candidates = [
        Path("tools") / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
        Path.cwd() / "tools" / "kilo" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
        Path("tools") / "kilo" / "kilo.cmd",
    ]
    for lc in local_candidates:
        if lc.exists() and lc.is_file():
            return str(lc.resolve())

    # 2. System PATH
    for name in ("kilo", "kilo.exe", "kilo.cmd", "kilocode", "kilocode.cmd"):
        b = shutil.which(name)
        if b:
            return b

    # 3. Known user and npm global paths
    candidates = [
        Path.home() / ".kilo" / "bin" / ("kilo.exe" if platform.system() == "Windows" else "kilo"),
        Path.home() / "AppData" / "Roaming" / "npm" / "kilo.cmd",
        Path.home() / "AppData" / "Local" / "kilo" / "bin" / "kilo.exe",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)

    return None


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
    """Map of relative path -> mtime_ns for files under repo."""
    out: dict[str, int] = {}
    skip = (".git", "node_modules", ".venv", "__pycache__")
    try:
        for p in repo.rglob("*"):
            if p.is_file() and not any(part in skip for part in p.parts):
                out[p.relative_to(repo).as_posix()] = p.stat().st_mtime_ns
    except Exception:
        pass
    return out


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


def run_kilo_worker(payload: dict, ctx: Optional[TaskContext] = None) -> dict:
    """Background worker for Kilo Code CLI execution.

    Streams live telemetry, enforces full CPU performance, and handles pre-flight assets.
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

    kilo_bin = payload.get("bin") or _find_kilo_bin()
    if not kilo_bin:
        err_msg = "Kilo Code CLI binary not found. Please ensure kilo is on PATH or installed globally."
        logger.warning(err_msg)
        ctx.on_fail(err_msg)
        return {"status": "failed", "error": err_msg, "repo": str(repo)}

    repo.mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(repo)
    snapshot = capture_repo_snapshot(repo)

    model = payload.get("model") or payload.get("model_id") or get_kilo_model() or "kilo/free"
    owns_task = bool(payload.get("owns_task", True))

    ctx.report(5, f"Launching Kilo Code ({model}) in {repo.name}...")

    # Pre-fetch fallback hook: if prompt contains an HTTP/HTTPS URL and site_dom.html missing
    url_match = re.search(r"https?://[^\s\"'>]+", prompt)
    if url_match and not (repo / "site_dom.html").exists():
        target_url = url_match.group(0).rstrip(".,;)")
        try:
            from core.url_prefetch import prefetch_url_assets
            prefetch_url_assets(target_url, repo, ctx)
        except ImportError:
            logger.debug("core.url_prefetch not available to prefetch assets for %s", target_url)
        except Exception as e_pref:
            logger.warning("prefetch_url_assets failed for %s: %s", target_url, e_pref)

    before_tree = _tree_snapshot(repo)

    # Protect against Win32 CreateProcessW 32,767 character limit ([WinError 206])
    effective_prompt = prompt
    extra_flags: list[str] = []
    if len(prompt) > 800:
        try:
            instr_path = repo / ".zezo_task_instructions.md"
            instr_path.write_text(prompt, encoding="utf-8")
            effective_prompt = (
                "Execute all directives and requirements in .zezo_task_instructions.md to complete the task in this workspace."
            )
            extra_flags = ["--file", ".zezo_task_instructions.md"]
            logger.info(
                "[KiloRunner] Large prompt (%d chars) written to .zezo_task_instructions.md to protect against WinError 206",
                len(prompt),
            )
        except Exception as e_write:
            logger.warning("[KiloRunner] Could not write .zezo_task_instructions.md: %s", e_write)

    cmd = [kilo_bin, "run", effective_prompt] + extra_flags + ["--model", model, "--auto"]

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

    start_time = time.time()
    last_pct = 10
    last_reported_pct = 0
    last_report_time = start_time
    last_diff_time = start_time
    stdout_lines: List[str] = []

    def _reader():
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                txt = line.rstrip()
                if not txt:
                    continue
                stdout_lines.append(txt)
        except Exception:
            pass

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    try:
        while proc.poll() is None:
            if ctx.cancelled():
                proc.terminate()
                return {"status": "cancelled", "repo": str(repo)}

            time.sleep(0.5)
            now = time.time()
            elapsed = now - start_time

            line_count = len(stdout_lines)
            latest_line = stdout_lines[-1][:80] if stdout_lines else f"Running Kilo Code ({model})..."

            # Asymptotic progress curve
            time_pct = 15.0 + 67.0 * (1.0 - math.exp(-elapsed / 85.0))
            line_pct = min(10.0, line_count * 0.2)
            pct = min(92, int(time_pct + line_pct))
            pct = max(pct, last_pct)

            # Fast deliverable check every 2.0s
            if now - last_diff_time >= 2.0:
                last_diff_time = now
                deliverable_names = ("DESIGN.md", "preview.html", "preview-dark.html", "index.html")
                found_deliverables = [
                    name for name in deliverable_names
                    if (repo / name).is_file() and name not in before_tree
                ]
                if found_deliverables:
                    boost = min(92, 88 + len(found_deliverables))
                    pct = max(pct, boost)
                    latest_line = f"Created deliverable: {found_deliverables[-1]}"

            pct = max(pct, last_pct)

            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            time_tag = f"[{mins}m {secs:02d}s]" if mins > 0 else f"[{secs}s]"

            if (pct > last_reported_pct) or (now - last_report_time >= 3.5):
                ctx.report(pct, f"{latest_line} {time_tag}")
                last_reported_pct = pct
                last_report_time = now

            last_pct = pct
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    if ctx.cancelled():
        return {"status": "cancelled", "repo": str(repo)}

    after_tree = _tree_snapshot(repo)
    created_list = [rel for rel, mt in after_tree.items() if before_tree.get(rel) != mt]
    entry_point = "index.html" if (repo / "index.html").exists() else "main.py"

    ctx.report(95, "Finalizing project build...")

    try:
        undo_entry = register_repo_undo(str(repo), snapshot, "Kilo Code")
        if undo_entry and undo_entry.get("changes"):
            first_file = Path(undo_entry["changes"][0]["path"]).name
            from memory.memory_manager import remember
            remember("active_file", first_file, category="projects")
    except Exception as e:
        logger.debug("Kilo undo registration failed: %s", e)

    is_success = proc.returncode == 0
    summary = (
        f"Kilo Code successfully finished in '{repo.name}'."
        if is_success
        else f"Kilo Code exited with code {proc.returncode}."
    )

    result_payload = {
        "status": "success" if is_success else "failed",
        "return_code": proc.returncode,
        "repo": str(repo),
        "project_name": repo.name,
        "files": created_list,
        "entry_point": entry_point,
        "summary": summary,
        "model": model,
        "tail": stdout_lines[-15:],
    }

    if owns_task:
        if is_success:
            ctx.on_complete(result_payload)
        else:
            ctx.on_fail(summary)

    return result_payload


# Backwards compatibility alias
_run_worker = run_kilo_worker
