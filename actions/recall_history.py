"""
actions/recall_history.py — Verifiable Deep Memory Recall & Timeline Expansion.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

Capabilities:
  1. op="search" — Search historical verbatim turns via FTS5 BM25 ranking.
  2. op="expand" — Retrieve contiguous turn sequences across [lo, hi] range.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from memory.sqlite_memory import expand_turns, search_scroll_history

logger = logging.getLogger(__name__)


def _handle_search(params: Dict[str, Any]) -> str:
    query = str(params.get("query") or params.get("text") or "").strip()
    session_id = str(params.get("session_id") or "").strip() or None
    limit = int(params.get("limit") or 5)

    if not query:
        return "Error: query parameter is required for history search."

    results = search_scroll_history(query, limit=limit, session_id=session_id)
    if not results:
        sess_clause = f" in session '{session_id}'" if session_id else ""
        return f"No historical turns found matching '{query}'{sess_clause}."

    lines = [f"Found {len(results)} relevant turns:"]
    for r in results:
        tid = r.get("id")
        ts = r.get("timestamp", "")[:16]
        role = r.get("role", "unknown").upper()
        content = (r.get("content") or "").strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:157] + "..."
        tool_info = f" [Tool: {r.get('tool_name')}]" if r.get("tool_name") else ""
        lines.append(f"• [ID: {tid}] [{ts}] {role}{tool_info}: {content}")

    return "\n".join(lines)


def _handle_expand(params: Dict[str, Any]) -> str:
    lo = params.get("lo") or params.get("start_id") or params.get("from_id")
    hi = params.get("hi") or params.get("end_id") or params.get("to_id")
    session_id = str(params.get("session_id") or "").strip() or None

    if lo is None or hi is None:
        return "Error: both 'lo' (start turn ID) and 'hi' (end turn ID) are required to expand history timeline."

    try:
        lo_int = int(lo)
        hi_int = int(hi)
    except (ValueError, TypeError):
        return "Error: turn IDs 'lo' and 'hi' must be valid integers."

    turns = expand_turns(lo_int, hi_int, session_id=session_id)
    if not turns:
        sess_clause = f" in session '{session_id}'" if session_id else ""
        return f"No turns found in range [{lo_int}..{hi_int}]{sess_clause}."

    lines = [f"Expanded {len(turns)} turns [{lo_int}..{hi_int}]:"]
    for t in turns:
        tid = t.get("id")
        ts = t.get("timestamp", "")[:19]
        role = t.get("role", "unknown").upper()
        content = (t.get("content") or "").strip()
        tool_name = t.get("tool_name")
        tool_result = t.get("tool_result")

        if tool_name:
            res_snippet = f"\n  ↳ Result: {tool_result[:250]}" if tool_result else ""
            lines.append(f"\n[Turn #{tid}] [{ts}] TOOL ({tool_name}): {content}{res_snippet}")
        else:
            lines.append(f"\n[Turn #{tid}] [{ts}] {role}: {content}")

    return "\n".join(lines)


_OP_DISPATCH = {
    "search": _handle_search,
    "find": _handle_search,
    "expand": _handle_expand,
    "fetch_range": _handle_expand,
}


def recall_history(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """Entrypoint for deep verbatim conversation history search and timeline expansion."""
    op = str(parameters.get("op") or parameters.get("action") or "search").strip().lower()
    handler_fn = _OP_DISPATCH.get(op)
    if not handler_fn:
        return f"Unknown recall_history operation '{op}'. Supported ops: search, expand."
    return handler_fn(parameters)


TOOL = {
    "name": "recall_history",
    "description": (
        "Search verbatim past conversation history and expand turn sequences. "
        "Use op='search' to find turn IDs matching keywords. "
        "Use op='expand' with lo and hi turn IDs to retrieve full untruncated past exchanges."
    ),
    "risk": "read_only",
    "enabled": True,
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "op": {
                "type": "STRING",
                "enum": ["search", "expand"],
                "description": "Operation type: 'search' to find matching turns by keyword, or 'expand' to retrieve full sequence between lo and hi IDs.",
            },
            "query": {
                "type": "STRING",
                "description": "Keywords to search across past messages and tool execution history.",
            },
            "lo": {
                "type": "INTEGER",
                "description": "Starting turn ID for expand operation.",
            },
            "hi": {
                "type": "INTEGER",
                "description": "Ending turn ID for expand operation.",
            },
            "session_id": {
                "type": "STRING",
                "description": "Optional composite session ID to scope search or expansion to a specific agent.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Max number of search results (default 5).",
            },
        },
        "required": ["op"],
    },
    "handler": recall_history,
}

handler = recall_history
