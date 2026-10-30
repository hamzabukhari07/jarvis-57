"""Antigravity Agent Action Tool.

Transparent, pure human-like CLI bridge for Google Antigravity (agy).
Delegates execution to the background engine in core.antigravity_runner.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from core.antigravity_runner import (
    _find_antigravity_bin,
    _is_root_dir,
    _resolve_model,
    run_antigravity_worker,
)
from core.repo_context import get_unique_project_dir, remember_repo, resolve
from core.task_manager import get_task_manager

# Re-export background worker for backwards compatibility
_run_worker = run_antigravity_worker

logger = logging.getLogger("zezo.antigravity_agent")


def antigravity_action(parameters: dict, player=None, speak=None, session_memory=None) -> str:
    """Action handler called by core.action_loader and dispatcher."""
    prompt = (parameters.get("prompt") or parameters.get("task") or "").strip()
    if not prompt:
        return "Please tell me the coding task or application you want Antigravity to build."

    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    if not explicit_path:
        # Extract folder hints from task prompt if explicitly mentioned
        folder_match = re.search(
            r'\b(?:in\s+(?:the\s+)?(?:folder|directory|dir)|folder|directory|dir)\s*[:=]?\s*["\']?([a-zA-Z0-9_\-\\/]+)["\']?',
            prompt,
            re.I,
        )
        if folder_match:
            cand = folder_match.group(1).strip().strip("\"'")
            if not any(cand.lower().endswith(ext) for ext in (".html", ".css", ".js", ".py", ".md", ".json")):
                explicit_path = cand

    run_in_place = bool(parameters.get("run_in_place", False))

    if explicit_path:
        repo, source = resolve(explicit=explicit_path)
    elif run_in_place:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
        source = "run_in_place"
    else:
        repo = get_unique_project_dir(prompt)
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

    worker_params = {
        "repo": str(repo),
        "prompt": prompt,
        "task": prompt,
        "model": model,
        "skip_preview": bool(parameters.get("skip_preview", False)),
        "owns_task": not bool(task_ctx),
    }

    if run_in_place:
        res = run_antigravity_worker(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "antigravity_agent",
        run_antigravity_worker,
        worker_params,
    )

    try:
        remember_repo(str(repo))
        from memory.memory_manager import remember
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
            f"for '{Path(repo).name}'. It will start automatically when the current task finishes."
        )

    return (
        f"ZEZO Coder task start ho gaya hai (Task ID: {task_id}) in '{Path(repo).name}'. "
        "Background mein build ho raha hai, aap jab chaho status pooch sakte ho."
    )


# Export standard action handler per Rule 4
handler = antigravity_action


# ── Action Discovery TOOL Schema ─────────────────────────────────────────────
TOOL = {
    "name": "antigravity_run",
    "description": (
        "Invoke the Google Antigravity Agent to autonomously build and edit software projects "
        "inside a specific project folder via the native 'agy' CLI. "
        "Runs asynchronously in background and returns immediately with a task_id."
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
                "description": "Natural user prompt explaining what application, feature, or code to build.",
            },
            "task": {
                "type": "STRING",
                "description": "Optional alias for prompt.",
            },
            "project_path": {
                "type": "STRING",
                "description": "Optional directory path (e.g. 'Desktop/website'). If omitted, resolves active project.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional Antigravity CLI model (e.g. 'gemini-3.8-flash-medium', 'claude-sonnet-4-6').",
            },
        },
        "required": ["prompt"],
    },
    "handler": antigravity_action,
}
