"""
actions/recall_history.py — Verifiable Deep Memory Recall & Timeline Expansion.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

Capabilities:
  1. op="search" — Search historical verbatim turns (BM25 relevance blended with recency).
  2. op="expand" — Retrieve contiguous turn sequences across [lo, hi] range.
  3. op="recent" — List sessions inside a date window (today / yesterday / last N days).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from memory.sqlite_memory import (
    expand_turns,
    get_recent_turns,
    list_sessions,
    resolve_period,
    search_scroll_history,
)

logger = logging.getLogger(__name__)


def _handle_search(params: Dict[str, Any]) -> str:
    query = str(params.get("query") or params.get("text") or "").strip()
    session_id = str(params.get("session_id") or "").strip() or None
    limit = int(params.get("limit") or 8)

    if not query:
        return "Error: query parameter is required for history search."

    results = search_scroll_history(
        query,
        limit=limit,
        session_id=session_id,
        recency_weight=0.35,
        recency_half_life_days=14.0,
    )
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
        return (
            "Error: both 'lo' (start turn ID) and 'hi' (end turn ID) are required to expand "
            "history timeline. If you want the conversation from a given day instead, "
            "use op='recent' with period='yesterday'."
        )

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


def _session_turns(session_id: str, head: int = 2, tail: int = 5) -> list[dict]:
    """Opening + closing turns of a session.

    The first user utterance states the topic; the closing turns show what
    actually happened. The middle of a long session is usually noise.
    """
    merged: dict[int, dict] = {}
    for t in get_recent_turns(limit=head, session_id=session_id, newest_first=False):
        merged[t["id"]] = t
    for t in get_recent_turns(limit=tail, session_id=session_id, newest_first=True):
        merged[t["id"]] = t
    return sorted(merged.values(), key=lambda t: t["id"])


def _handle_recent(params: Dict[str, Any]) -> str:
    """Temporal recall: what was discussed in a given time window."""
    period = str(params.get("period") or "").strip()
    since = str(params.get("since") or "").strip() or None
    until = str(params.get("until") or "").strip() or None
    max_sessions = int(params.get("limit") or 3)
    turns_per = int(params.get("turns_per_session") or 7)

    since, until = resolve_period(period, since, until)

    sessions = list_sessions(limit=max_sessions, since=since, until=until)
    if not sessions:
        window = f"{since} to {until}" if (since or until) else "the recorded history"
        return f"No conversations were recorded in {window}."

    lines = [
        f"Recency view — {len(sessions)} session(s) "
        f"({since or 'earliest'} to {until or 'latest'}), most recent first:",
    ]
    for sess in sessions:
        sid = sess.get("session_id")
        if not sid:
            continue
        start = (sess.get("start_time") or "")[:19]
        end = (sess.get("end_time") or "")[:19]
        topic = (sess.get("topic") or "").strip().replace("\n", " ")
        if len(topic) > 140:
            topic = topic[:137] + "..."
        lines.append(
            f"\n— Session {sid} | {start} → {end} "
            f"| {sess.get('turn_count')} turns"
        )
        if topic:
            lines.append(f"  Topic: {topic}")
        for t in _session_turns(sid, tail=max(1, turns_per - 2)):
            ts = (t.get("timestamp") or "")[:16]
            role = (t.get("role") or "unknown").upper()
            content = (t.get("content") or "").strip().replace("\n", " ")
            if len(content) > 220:
                content = content[:217] + "..."
            tool_info = f" [Tool: {t.get('tool_name')}]" if t.get("tool_name") else ""
            lines.append(f"  • [ID: {t.get('id')}] [{ts}] {role}{tool_info}: {content}")

    return "\n".join(lines)


_OP_DISPATCH = {
    "search": _handle_search,
    "find": _handle_search,
    "expand": _handle_expand,
    "fetch_range": _handle_expand,
    "recent": _handle_recent,
    "sessions": _handle_recent,
    "timeline": _handle_recent,
}


def recall_history(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """Entrypoint for deep verbatim conversation history search and timeline expansion."""
    op = str(parameters.get("op") or parameters.get("action") or "search").strip().lower()
    handler_fn = _OP_DISPATCH.get(op)
    if not handler_fn:
        return (
            f"Unknown recall_history operation '{op}'. "
            "Supported ops: search, expand, recent."
        )
    return handler_fn(parameters)


TOOL = {
    "name": "recall_history",
    "description": (
        "Recall verbatim past conversation history. "
        "Use op='recent' for questions about WHEN something happened "
        "(today, yesterday/kal, last week) — it returns sessions in that date window "
        "with their opening topic and key turns. "
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
                "enum": ["search", "expand", "recent"],
                "description": (
                    "Operation type: 'recent' to list conversations within a date window, "
                    "'search' to find matching turns by keyword, or 'expand' to retrieve "
                    "full sequence between lo and hi IDs."
                ),
            },
            "query": {
                "type": "STRING",
                "description": "Keywords to search across past messages and tool execution history.",
            },
            "period": {
                "type": "STRING",
                "enum": ["today", "yesterday", "last_3_days", "last_7_days", "last_14_days", "last_30_days"],
                "description": (
                    "Time window for op='recent'. Use 'yesterday' for questions about "
                    "'kal' / what we talked about the previous day."
                ),
            },
            "since": {
                "type": "STRING",
                "description": "Explicit inclusive start date (YYYY-MM-DD) for op='recent'. Overrides 'period'.",
            },
            "until": {
                "type": "STRING",
                "description": "Explicit inclusive end date (YYYY-MM-DD) for op='recent'. Overrides 'period'.",
            },
            "turns_per_session": {
                "type": "INTEGER",
                "description": "Max turns shown per session for op='recent' (default 7).",
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
                "description": "Max number of results (default 8 for search, 3 sessions for recent).",
            },
        },
        "required": ["op"],
    },
    "handler": recall_history,
}

handler = recall_history
