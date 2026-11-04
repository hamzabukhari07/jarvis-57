"""Antigravity Agent Action Tool.

Transparent, pure human-like CLI bridge for Google Antigravity (agy).
Delegates execution to the background engine in core.engines.antigravity.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from core.engines.antigravity import (
    AntigravityEngineAdapter,
    _resolve_model,
    run_antigravity_task,
)
from core.repo_context import get_unique_project_dir, guard_domain_workspace, remember_repo, resolve
from core.task_manager import get_task_manager

# Direct worker alias
_run_worker = run_antigravity_task
run_antigravity_worker = run_antigravity_task


def _find_antigravity_bin() -> Optional[str]:
    """Discovers the absolute path to the agy binary via AntigravityEngineAdapter."""
    p = AntigravityEngineAdapter().resolve_binary()
    return str(p) if p else None


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

    # PathJail Pre-flight Validation: If explicit path provided, reject root / system paths
    if explicit_path:
        from core.path_jail import SecurityAccessDenied as PathSecurityAccessDenied
        p_obj = Path(explicit_path).resolve()
        # Disallow filesystem drive roots (e.g. C:\) or system directories
        if len(p_obj.parts) <= 1 or p_obj.parent == p_obj:
            raise PathSecurityAccessDenied(f"Access to filesystem root '{explicit_path}' is strictly denied.")
        sys_root = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve()
        try:
            p_obj.relative_to(sys_root)
            raise PathSecurityAccessDenied(f"Access to system directory '{explicit_path}' is strictly denied.")
        except ValueError:
            pass

    # Smart Guard: Detect domain mismatch / context hallucination for new URLs
    domain_guarded_dir = guard_domain_workspace(prompt, explicit_path) if not run_in_place else None

    if domain_guarded_dir:
        repo = domain_guarded_dir
        source = "domain_guard"
        remember_repo(str(repo))
    elif explicit_path:
        repo, source = resolve(explicit=explicit_path)
    elif run_in_place:
        resolved_p, _ = resolve()
        repo = resolved_p or (Path.home() / "Desktop" / "website").resolve()
        source = "run_in_place"
    else:
        repo = get_unique_project_dir(prompt)
        source = "new_project"

    if repo is None or _is_root_dir(Path(repo)):
        repo = get_unique_project_dir(prompt or "project")
        source = "auto_subfolder"
        remember_repo(str(repo))
        logger.info("[antigravity_agent] Auto-resolved root or missing project dir to: %s", repo)

    try:
        from core.pending_intent import set_pending_intent
        set_pending_intent(
            task=prompt,
            action="antigravity_action",
            params={"prompt": prompt, "project_path": str(repo)},
            target_dir=str(repo),
            engine="antigravity",
            status="running",
        )
    except Exception as _e:
        logger.debug("[antigravity_agent] Pending intent set note: %s", _e)

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
        res = run_antigravity_task(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "antigravity_agent",
        run_antigravity_task,
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
    "risk": "local_mutation",
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
                "description": (
                    "Target project directory. CRITICAL: For greenfield tasks, new website builds, "
                    "or when analyzing a NEW external URL, LEAVE THIS EMPTY. The system will auto-generate "
                    "a clean workspace. Only provide an explicit path if the user specifically asked to "
                    "'continue working in [folder_name]' or modify an existing local project."
                ),
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
