"""actions/kilo_agent.py — Transparent Kilo Code Engine Bridge (async).

Standardized pure human-like CLI bridge for Kilo Code.
Delegates coding tasks directly to Kilo Code CLI via core.kilo_runner.
Returns immediately with a task_id; runs the CLI in a background thread.
Query progress with the task_status tool.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from core.kilo_runner import (
    _find_kilo_bin,
    run_kilo_worker,
)
from core.repo_context import resolve
from core.task_manager import get_task_manager, TaskContext
from memory.config_manager import get_kilo_model

logger = logging.getLogger("zezo.kilo")

# Re-export worker for backwards compatibility
_run_worker = run_kilo_worker


def _resolve_model(model: Optional[str]) -> str:
    selected = (model or "").strip() or get_kilo_model()
    if selected.startswith("zen/"):
        name = selected.replace("zen/", "")
        return f"kilo/{name}"
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
        "project_path": str(repo),
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
                "description": "Clear, detailed coding prompt.",
            },
            "task": {
                "type": "STRING",
                "description": "Optional alias for prompt.",
            },
            "project_path": {
                "type": "STRING",
                "description": (
                    "Absolute or relative path to the project folder. "
                    "If omitted, resolves the active workspace repo."
                ),
            },
            "model": {
                "type": "STRING",
                "description": "Optional Kilo Code model override.",
            },
        },
        "required": ["prompt"],
    },
    "handler": kilo_agent,
}

handler = kilo_agent
