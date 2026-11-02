"""
actions/memory_tool.py — Unified Canonical Memory Action for ZEZO OS.

Creator & Lead Architect: Hamza Bukhari
Consolidates recall, learn, forget, and history into a single canonical tool declaration.
Strictly adheres to AGENTS.md Core Rule 4.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from memory.memory_manager import (
    queue_memory_forget,
    queue_memory_write,
    search_memory,
)
from memory.sqlite_memory import (
    expand_turns,
    list_sessions,
    resolve_period,
    search_scroll_history,
)

logger = logging.getLogger(__name__)


def _handle_learn(params: Dict[str, Any]) -> str:
    category = str(params.get("category") or "notes").strip().lower()
    key = str(params.get("key") or "").strip()
    value = str(params.get("value") or "").strip()

    if not key or not value:
        return "Error: Both 'key' and 'value' are required when action='learn'."

    res = queue_memory_write(category, key, value)
    status = res.get("status")
    if status == "paused":
        return "Memory is currently paused. Fact was not saved."
    if status == "queued":
        return f"Remembered silently: {category}/{key} = {value}"
    if status == "persisted":
        return f"Saved: {category}/{key} = {value}"
    return f"Memory update result: {status}"


def _handle_forget(params: Dict[str, Any]) -> str:
    category = str(params.get("category") or "notes").strip().lower()
    key = str(params.get("key") or "").strip()

    if not key:
        return "Error: 'key' is required when action='forget'."

    queue_memory_forget(category, key)
    return f"Fact removed from memory: {category}/{key}."


def _handle_recall(params: Dict[str, Any]) -> str:
    query = str(params.get("query") or params.get("key") or "").strip()
    limit = int(params.get("limit") or 8)
    return search_memory(query, limit=limit)


def _handle_history(params: Dict[str, Any]) -> str:
    sub_op = str(params.get("op") or "search").strip().lower()
    query = str(params.get("query") or "").strip()
    period = str(params.get("period") or "").strip()
    lo = params.get("lo")
    hi = params.get("hi")
    turn_range = params.get("turn_range")

    if turn_range and isinstance(turn_range, str) and "-" in turn_range:
        parts = turn_range.split("-")
        try:
            lo, hi = int(parts[0]), int(parts[1])
            sub_op = "expand"
        except ValueError:
            pass

    if sub_op == "expand" or (lo is not None and hi is not None):
        try:
            lo_int = int(lo or 0)
            hi_int = int(hi or 0)
            turns = expand_turns(lo_int, hi_int)
            if not turns:
                return f"No turns found in range [{lo_int}, {hi_int}]."
            lines = [f"Turn sequence [{lo_int} → {hi_int}] ({len(turns)} turns):"]
            for t in turns:
                ts = (t.get("timestamp") or "")[:16]
                role = (t.get("role") or "unknown").upper()
                content = (t.get("content") or "").strip().replace("\n", " ")
                tool_info = f" [Tool: {t.get('tool_name')}]" if t.get("tool_name") else ""
                lines.append(f"• [ID: {t.get('id')}] [{ts}] {role}{tool_info}: {content}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error expanding turns: {e}"

    if period or sub_op in ("recent", "sessions", "timeline"):
        since, until = resolve_period(period or "today")
        sessions = list_sessions(since=since, until=until, limit=10)
        if not sessions:
            return f"No conversations recorded in {period or 'today'}."
        lines = [f"Found {len(sessions)} session(s) in {period or 'today'}:"]
        for s in sessions:
            sid = s.get("session_id", "")
            topic = s.get("topic", "") or "No topic"
            tcount = s.get("turn_count", 0)
            lines.append(f"• Session {sid} ({tcount} turns): {topic}")
        return "\n".join(lines)

    # Default to search
    if not query:
        return "Error: 'query' is required for action='history' search."

    results = search_scroll_history(
        query,
        limit=int(params.get("limit") or 8),
        recency_weight=0.35,
        recency_half_life_days=14.0,
    )
    if not results:
        return f"No historical turns found matching '{query}'."

    lines = [f"Found {len(results)} relevant turns matching '{query}':"]
    for r in results:
        tid = r.get("id")
        ts = (r.get("timestamp") or "")[:16]
        role = (r.get("role") or "unknown").upper()
        content = (r.get("content") or "").strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:157] + "..."
        tool_info = f" [Tool: {r.get('tool_name')}]" if r.get("tool_name") else ""
        lines.append(f"• [ID: {tid}] [{ts}] {role}{tool_info}: {content}")
    return "\n".join(lines)


_ACTION_DISPATCH = {
    "learn": _handle_learn,
    "remember": _handle_learn,
    "save": _handle_learn,
    "forget": _handle_forget,
    "delete": _handle_forget,
    "recall": _handle_recall,
    "search": _handle_recall,
    "history": _handle_history,
}


def handler(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """Entrypoint for unified memory operations: recall, learn, forget, and history."""
    action = str(parameters.get("action") or "recall").strip().lower()
    fn = _ACTION_DISPATCH.get(action)
    if not fn:
        return (
            f"Unknown memory action '{action}'. "
            "Supported actions: recall, learn, forget, history."
        )
    return fn(parameters)


# Export canonical TOOL schema
TOOL = {
    "name": "memory",
    "description": (
        "Unified memory engine: recall facts, learn new context, forget outdated facts, "
        "or search verbatim conversation history. "
        "Use action='learn' to silently remember user facts (category, key, value). "
        "Use action='recall' with query to search stored facts. "
        "Use action='forget' with category and key to remove a fact. "
        "Use action='history' with query or period ('today', 'yesterday') to search past conversation transcripts."
    ),
    "risk": "local_mutation",
    "enabled": os.environ.get("ZEZO_UNIFIED_MEMORY_TOOL", "true").lower() != "false",
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["recall", "learn", "forget", "history"],
                "description": "Operation type: 'recall' to find facts, 'learn' to store, 'forget' to delete, 'history' for past transcripts.",
            },
            "query": {
                "type": "STRING",
                "description": "Keywords or search phrase for recall or history search.",
            },
            "category": {
                "type": "STRING",
                "enum": ["identity", "preferences", "projects", "relationships", "wishes", "notes"],
                "description": "Memory category for learn or forget.",
            },
            "key": {
                "type": "STRING",
                "description": "Specific fact identifier (e.g. 'favorite_editor', 'sister_name').",
            },
            "value": {
                "type": "STRING",
                "description": "The fact value to store when action='learn'.",
            },
            "period": {
                "type": "STRING",
                "enum": ["today", "yesterday", "last_3_days", "last_7_days", "last_14_days", "last_30_days"],
                "description": "Time window for action='history' when asking when something happened.",
            },
            "turn_range": {
                "type": "STRING",
                "description": "Turn range e.g. '120-135' to expand verbatim dialog history.",
            },
        },
        "required": ["action"],
    },
    "handler": handler,
}
