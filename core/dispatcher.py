"""
core/dispatcher.py — Central Task & Semantic Action Dispatcher for ZEZO.

Creator & Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

This module decouples conversational intent interpretation (handled by Gemini Live)
from execution engine selection. Based on user preferences stored in config
(and configured via the Settings modal), the Dispatcher routes:
  1. Creation / Scaffolding Tasks -> Preferred Creation Engine (OpenCode / Antigravity / Kilo)
  2. Quick Edits / Inline Fixes   -> Preferred Edit Engine (Groq Code Helper / Kilo / OpenCode)
  3. General Coding Tasks         -> Contextually selected engine
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from memory.config_manager import (
    get_preferred_creation_agent,
    get_preferred_edit_agent,
)

logger = logging.getLogger("zezo.dispatcher")


def get_creation_engine() -> str:
    """Returns normalized active creation engine ('opencode' | 'antigravity' | 'kilo')."""
    engine = (get_preferred_creation_agent() or "opencode").strip().lower()
    if engine not in ("opencode", "antigravity", "kilo"):
        engine = "opencode"
    return engine


def get_edit_engine() -> str:
    """Returns normalized active edit engine ('groq_helper' | 'kilo' | 'opencode')."""
    engine = (get_preferred_edit_agent() or "groq_helper").strip().lower()
    if engine not in ("groq_helper", "kilo", "opencode"):
        engine = "groq_helper"
    return engine


def dispatch_creation(
    task: str,
    project_path: Optional[str] = None,
    model: Optional[str] = None,
    player: Any = None,
    speak: Any = None,
    **kwargs: Any,
) -> str:
    """
    Routes a project creation / multi-file scaffolding task to the user's preferred creation engine.
    Returns immediately with the engine's response (or task_id acknowledgment).
    """
    engine = get_creation_engine()
    logger.info("Dispatching creation task to engine: '%s'", engine)

    params: Dict[str, Any] = {"task": task}
    if project_path:
        params["project_path"] = project_path
    if model:
        params["model"] = model

    try:
        if engine == "antigravity":
            from actions.antigravity_agent import antigravity_action
            return antigravity_action(params, player=player, speak=speak, **kwargs)
        elif engine == "kilo":
            from actions.kilo_agent import kilo_agent
            return kilo_agent(params, player=player, speak=speak, **kwargs)
        else:  # "opencode" (default)
            from actions.opencode_agent import opencode_agent
            return opencode_agent(params, player=player, speak=speak, **kwargs)
    except Exception as e:
        logger.error("Error dispatching creation task to %s: %s", engine, e, exc_info=True)
        # Fallback to OpenCode if another engine threw an unexpected import/execution error
        if engine != "opencode":
            logger.info("Attempting fallback creation dispatch to OpenCode...")
            try:
                from actions.opencode_agent import opencode_agent
                return opencode_agent(params, player=player, speak=speak, **kwargs)
            except Exception as fb_err:
                return f"Failed to execute creation task on {engine} (Error: {e}) and fallback failed (Error: {fb_err})."
        return f"Failed to execute creation task on {engine}: {e}"


def dispatch_quick_edit(
    task: Optional[str] = None,
    file_path: Optional[str] = None,
    description: Optional[str] = None,
    project_path: Optional[str] = None,
    action: Optional[str] = None,
    code: Optional[str] = None,
    player: Any = None,
    speak: Any = None,
    **kwargs: Any,
) -> str:
    """
    Routes an inline fix, single file edit, or quick code generation to the user's preferred edit engine.
    """
    engine = get_edit_engine()
    logger.info("Dispatching quick edit task to engine: '%s'", engine)

    desc = description or task or "Perform code edit"

    try:
        if engine == "kilo":
            from actions.kilo_agent import kilo_agent
            params = {"task": desc}
            if project_path or file_path:
                params["project_path"] = project_path or file_path
            return kilo_agent(params, player=player, speak=speak, **kwargs)

        elif engine == "opencode":
            from actions.opencode_agent import opencode_agent
            params = {"task": desc}
            if project_path or file_path:
                params["project_path"] = project_path or file_path
            return opencode_agent(params, player=player, speak=speak, **kwargs)

        else:  # "groq_helper" (default, sub-second LPU text/code completion)
            from actions.quick_snippet import quick_snippet
            params = {
                "action": action or ("edit" if file_path else "write"),
                "description": desc,
            }
            if file_path:
                params["file_path"] = file_path
            if project_path:
                params["output_path"] = project_path
            if code:
                params["code"] = code
            return quick_snippet(params, player=player, speak=speak, **kwargs)

    except Exception as e:
        logger.error("Error dispatching quick edit to %s: %s", engine, e, exc_info=True)
        # Fallback to quick_snippet if kilo/opencode threw an error
        if engine != "groq_helper":
            try:
                from actions.quick_snippet import quick_snippet
                params = {
                    "action": action or ("edit" if file_path else "write"),
                    "description": desc,
                }
                if file_path:
                    params["file_path"] = file_path
                return quick_snippet(params, player=player, speak=speak, **kwargs)
            except Exception as fb_err:
                return f"Quick edit error on {engine} ({e}); fallback error: {fb_err}"
        return f"Quick edit error on {engine}: {e}"


def dispatch_coding(
    task: str,
    project_path: Optional[str] = None,
    file_path: Optional[str] = None,
    model: Optional[str] = None,
    is_creation: bool = False,
    is_multi_file: bool = True,
    player: Any = None,
    speak: Any = None,
    **kwargs: Any,
) -> str:
    """
    Unified entry point for coding tasks. Decides between creation vs edit workflow.
    """
    if is_creation or (not file_path and is_multi_file):
        return dispatch_creation(
            task=task,
            project_path=project_path,
            model=model,
            player=player,
            speak=speak,
            **kwargs,
        )
    else:
        return dispatch_quick_edit(
            task=task,
            file_path=file_path,
            description=task,
            project_path=project_path,
            player=player,
            speak=speak,
            **kwargs,
        )
