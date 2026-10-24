"""
actions/code_engines_status.py — Read-only status inspector for coding CLIs.

Inspects the readiness, authentication, and installation status of local
autonomous coding engines (Antigravity CLI, OpenCode, Kilo Code).

Adheres strictly to AGENTS.md:
  - Rule 4: One file per action, exports TOOL declaration and handler()
  - Rule 5: Non-blocking execution
  - Rule 6: Spoken summary is high-level conversational (1-2 sentences)
  - Rule 8: Cyclomatic complexity < 15
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from core.code_engines import (
    ENGINES,
    get_default_engine,
    probe_all_engines,
    probe_engine,
)

logger = logging.getLogger("zezo.actions.code_engines_status")

TOOL: Dict[str, Any] = {
    "name": "code_engines_status",
    "description": (
        "Inspect the status and health of coding agent engines (Antigravity CLI, OpenCode, Kilo Code). "
        "Reports whether each engine is installed, authenticated, or needs sign-in, ensuring tasks "
        "are only dispatched to ready engines."
    ),
    "risk": "read_only",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["list", "check"],
                "description": "'list' to inspect all code engines, or 'check' to probe a specific engine.",
            },
            "engine": {
                "type": "STRING",
                "enum": ["antigravity", "opencode", "kilo"],
                "description": "Optional engine identifier to check when action is 'check'.",
            },
            "force": {
                "type": "BOOLEAN",
                "description": "Set to true to bypass cache and perform a live probe.",
            },
        },
        "required": ["action"],
    },
    "handler": None,  # Populated below
}


def _build_summary_for_engine(engine_status: Dict[str, Any]) -> str:
    """Format a conversational voice summary for a single engine status."""
    label = engine_status.get("label", "Code Engine")
    state = engine_status.get("state", "unknown")

    state_phrases = {
        "ready": f"{label} is installed and authenticated for coding tasks.",
        "sign_in_required": f"{label} is installed, but sign-in is required before it can write code.",
        "not_installed": f"{label} is not installed on this system.",
        "off": f"{label} is installed but currently turned off in settings.",
        "unknown": f"{label} status could not be determined.",
    }
    return state_phrases.get(state, f"{label} is in state {state}.")


def _build_summary_for_all(
    engines: List[Dict[str, Any]], default_engine: str
) -> str:
    """Format a high-level conversational voice summary across all engines."""
    ready = [e["label"] for e in engines if e.get("state") == "ready"]
    needs_auth = [
        e["label"] for e in engines if e.get("state") == "sign_in_required"
    ]
    missing = [e["label"] for e in engines if e.get("state") == "not_installed"]

    parts = []
    if ready:
        parts.append(f"{', '.join(ready)} {'is' if len(ready) == 1 else 'are'} ready")
    if needs_auth:
        parts.append(f"{', '.join(needs_auth)} require{'s' if len(needs_auth) == 1 else ''} sign-in")
    if missing:
        parts.append(f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not installed")

    summary_core = "; ".join(parts) if parts else "No coding engines found"
    default_label = ENGINES.get(default_engine, None)
    default_name = default_label.label if default_label else default_engine

    return f"{summary_core}. Default engine is {default_name}."


def handler(parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Handler for code_engines_status action tool.
    Returns structured engine diagnostics and voice summary.
    """
    action = str(parameters.get("action", "list")).strip().lower()
    engine_id = str(parameters.get("engine", "")).strip().lower()
    force = bool(parameters.get("force", False))
    default_engine = get_default_engine()

    if action == "check" and engine_id:
        if engine_id not in ENGINES:
            return {
                "status": "error",
                "message": f"Engine '{engine_id}' is not recognized. Supported: {list(ENGINES.keys())}",
                "summary": f"Engine {engine_id} is not supported by ZEZO.",
            }
        result = probe_engine(engine_id, force=force)
        summary = _build_summary_for_engine(result)
        return {
            "status": "success",
            "action": "check",
            "engine": result,
            "default_engine": default_engine,
            "summary": summary,
        }

    # Default action: list all engines
    results = probe_all_engines(force=force)
    summary = _build_summary_for_all(results, default_engine)
    ready_ids = [e["id"] for e in results if e.get("state") == "ready"]

    return {
        "status": "success",
        "action": "list",
        "engines": results,
        "ready_engines": ready_ids,
        "default_engine": default_engine,
        "summary": summary,
    }


# Wire handler to declaration schema
TOOL["handler"] = handler
