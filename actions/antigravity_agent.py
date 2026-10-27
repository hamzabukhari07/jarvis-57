"""Antigravity Agent Action Tool.

Clean Gemini Action Tool entry point for autonomous project synthesis.
Delegates heavy CLI execution to the background engine in core.antigravity_runner.
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
from core.design_resolver import check_greenfield_gate, is_ui_task, resolve_design
from core.repo_context import get_unique_project_dir, remember_repo, resolve
from core.task_manager import get_task_manager

# Re-export background worker and helpers for backwards compatibility and test suites
_run_worker = run_antigravity_worker

logger = logging.getLogger("zezo.antigravity_agent")


def antigravity_action(parameters: dict, player=None, speak=None, session_memory=None) -> str:
    """Action handler called by core.action_loader and dispatcher."""
    task = (parameters.get("task") or parameters.get("prompt") or "").strip()
    if not task:
        return "Please tell me the coding task or application you want Antigravity to build."

    gate_msg = check_greenfield_gate(task, parameters, caller_tool="antigravity_run")
    if gate_msg:
        return gate_msg

    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    if not explicit_path:
        # Extract folder hints from task prompt if explicitly mentioned
        folder_match = re.search(
            r'\b(?:in\s+(?:the\s+)?(?:folder|directory|dir)|folder|directory|dir)\s*[:=]?\s*["\']?([a-zA-Z0-9_\-\\/]+)["\']?',
            task,
            re.I,
        )
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
    scope_type = parameters.get("scope_type")
    color_theme = parameters.get("color_theme")

    # Opt-in worker flags. They must be forwarded explicitly: this function builds a fresh
    # worker_params dict, so anything not copied here never reaches run_antigravity_worker.
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
        "scope_type": scope_type,
        "entity_content": parameters.get("entity_content"),
        "tech_stack": parameters.get("tech_stack"),
        "color_theme": color_theme,
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
        res = run_antigravity_worker(worker_params, ctx=task_ctx)
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "antigravity_agent",
        run_antigravity_worker,
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
        early_res = resolve_design(task, session_memory=session_memory if isinstance(session_memory, dict) else {}, scope=scope_type, theme=color_theme)
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


# Export standard action handler per Rule 4
handler = antigravity_action


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
