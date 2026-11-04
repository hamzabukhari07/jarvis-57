"""actions/opencode_agent.py — Transparent OpenCode Engine Bridge (async).

Standardized pure human-like CLI bridge for OpenCode.
Delegates coding tasks directly to OpenCode CLI via core.engines.opencode.
Returns immediately with a task_id; runs the CLI in a background thread.
Query progress with the task_status tool.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from core.engines.opencode import (
    OpenCodeEngineAdapter,
    run_opencode_task,
)
from core.repo_context import guard_domain_workspace, remember_repo, resolve
from core.task_manager import get_task_manager, TaskContext
from memory.config_manager import get_opencode_model

logger = logging.getLogger("zezo.opencode")

# Direct worker alias
_run_worker = run_opencode_task
run_opencode_worker = run_opencode_task


def _find_opencode_bin() -> Optional[str]:
    """Finds the native OpenCode CLI binary via OpenCodeEngineAdapter."""
    p = OpenCodeEngineAdapter().resolve_binary()
    return str(p) if p else None


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


def opencode_agent(parameters: dict, player=None, speak=None) -> str:
    prompt = (parameters.get("prompt") or parameters.get("task") or "").strip()
    if not prompt:
        return "Please tell me the coding task you want OpenCode to run."

    explicit_path = (
        parameters.get("project_path") or parameters.get("path") or ""
    )
    run_in_place = bool(parameters.get("run_in_place", False))

    # PathJail Pre-flight Validation: If explicit path provided, reject root / system paths
    if explicit_path:
        import os
        from core.path_jail import SecurityAccessDenied as PathSecurityAccessDenied
        p_obj = Path(explicit_path).resolve()
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
    else:
        repo, source = resolve(explicit=explicit_path)

    if repo is None or _is_root_dir(Path(repo)):
        from core.repo_context import get_unique_project_dir, remember_repo
        repo = get_unique_project_dir(prompt or "project")
        source = "auto_subfolder"
        remember_repo(str(repo))
        logger.info("[opencode_agent] Auto-resolved root or missing project dir to: %s", repo)

    try:
        from core.pending_intent import set_pending_intent
        set_pending_intent(
            task=prompt,
            action="opencode_agent",
            params={"prompt": prompt, "project_path": str(repo)},
            target_dir=str(repo),
            engine="opencode",
            status="running",
        )
    except Exception as _e:
        logger.debug("[opencode_agent] Pending intent set note: %s", _e)

    opencode_bin = _find_opencode_bin()
    if not opencode_bin:
        return (
            "OpenCode CLI is not installed. Run: "
            "npm install -g opencode-ai@latest   then   "
            "opencode auth login --provider zen"
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
        "bin": opencode_bin,
    }

    if run_in_place:
        res = run_opencode_task(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "opencode_agent",
        run_opencode_task,
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
        "Background mein run ho raha hai, aap jab chaho status pooch sakte ho."
    )


TOOL = {
    "name": "opencode_run",
    "description": (
        "Run OpenCode CLI for multi-file coding tasks, refactors, and feature builds "
        "inside a specific project directory via the native 'opencode' binary. "
        "Returns a task_id immediately."
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
                "description": "Clear, detailed coding prompt.",
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
                "description": "Optional OpenCode model override.",
            },
        },
        "required": ["prompt"],
    },
    "handler": opencode_agent,
}

handler = opencode_agent
