"""
SQLite WAL + FTS5 Memory Engine for Zezo (Scroll Context & Full-Text Search).

Provides:
  - Verbatim turn-by-turn history storage with FTS5 BM25 search.
  - Automatic thread-safe async logging.
  - Secret & sensitive token redaction before persistence.
  - Unified hybrid search (structured profile facts + historical turns).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DB_PATH = BASE_DIR / "memory" / "zezo_brain.db"

_db_lock = threading.Lock()
_current_session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ── Secret Redaction Patterns ───────────────────────────────────────────────
_SECRET_PATTERNS = [
    re.compile(r"(AIzaSy[A-Za-z0-9_-]{33})", re.IGNORECASE),                         # Google API Key
    re.compile(r"(sk-[A-Za-z0-9_-]{20,64})", re.IGNORECASE),                        # OpenAI / Generic Secret
    re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{20,}", re.IGNORECASE),                 # Bearer Tokens
    re.compile(r"(ghp_[A-Za-z0-9]{36})", re.IGNORECASE),                            # GitHub Personal Access Token
    re.compile(r"(password\s*(?:[:=]|is)\s*['\"][^'\"]+['\"])", re.IGNORECASE),   # Password expressions
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, passwords, and API tokens before saving to disk."""
    if not text or not isinstance(text, str):
        return ""
    scrubbed = text
    for pattern in _SECRET_PATTERNS:
        scrubbed = pattern.sub("[REDACTED_SECRET]", scrubbed)
    return scrubbed


def _get_connection() -> sqlite3.Connection:
    """Create a thread-safe connection configured for high-concurrency WAL mode."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite schema, tables, and FTS5 full-text indices."""
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                # 1. Structured facts table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(category, key)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_cat ON facts(category);")

                # 2. Verbatim conversation turns and tool execution table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS turns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tool_name TEXT,
                        tool_args TEXT,
                        tool_result TEXT,
                        timestamp TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON turns(timestamp);")

                # 3. FTS5 Virtual Table for sub-millisecond full-text search
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
                        content,
                        tool_name,
                        tool_result,
                        content='turns',
                        content_rowid='id'
                    );
                """)

                # 4. Triggers to keep FTS5 automatically synchronized with turns table
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS trg_turns_ai AFTER INSERT ON turns BEGIN
                        INSERT INTO turns_fts(rowid, content, tool_name, tool_result)
                        VALUES (new.id, new.content, new.tool_name, new.tool_result);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS trg_turns_ad AFTER DELETE ON turns BEGIN
                        INSERT INTO turns_fts(turns_fts, rowid, content, tool_name, tool_result)
                        VALUES('delete', old.id, old.content, old.tool_name, old.tool_result);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS trg_turns_au AFTER UPDATE ON turns BEGIN
                        INSERT INTO turns_fts(turns_fts, rowid, content, tool_name, tool_result)
                        VALUES('delete', old.id, old.content, old.tool_name, old.tool_result);
                        INSERT INTO turns_fts(rowid, content, tool_name, tool_result)
                        VALUES (new.id, new.content, new.tool_name, new.tool_result);
                    END;
                """)
        finally:
            conn.close()


def log_turn(
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_args: Optional[dict | str] = None,
    tool_result: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Asynchronously / thread-safely persist a conversation turn or tool invocation."""
    sess_id = session_id or _current_session_id
    clean_content = redact_secrets(content or "")
    clean_tool_name = (tool_name or "").strip() or None
    
    clean_args = None
    if tool_args is not None:
        if isinstance(tool_args, dict):
            clean_args = redact_secrets(json.dumps(tool_args, ensure_ascii=False))
        else:
            clean_args = redact_secrets(str(tool_args))

    clean_result = redact_secrets(tool_result or "") if tool_result else None
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _insert():
        with _db_lock:
            try:
                conn = _get_connection()
                with conn:
                    conn.execute(
                        """
                        INSERT INTO turns (session_id, role, content, tool_name, tool_args, tool_result, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (sess_id, role, clean_content, clean_tool_name, clean_args, clean_result, ts),
                    )
                conn.close()
            except Exception as e:
                print(f"[SQLite Memory] ⚠️ log_turn failed: {e}")

    threading.Thread(target=_insert, daemon=True).start()


def sync_facts_from_dict(memory_dict: dict) -> None:
    """Sync existing JSON dictionary memory structure into SQLite facts table."""
    if not isinstance(memory_dict, dict):
        return
    now_str = datetime.now().strftime("%Y-%m-%d")
    with _db_lock:
        try:
            conn = _get_connection()
            with conn:
                for cat, items in memory_dict.items():
                    if not isinstance(items, dict):
                        continue
                    for key, entry in items.items():
                        val = entry.get("value", "") if isinstance(entry, dict) else str(entry or "")
                        updated = (entry.get("updated", "") if isinstance(entry, dict) else "") or now_str
                        if val:
                            conn.execute(
                                """
                                INSERT INTO facts (category, key, value, updated_at)
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(category, key) DO UPDATE SET
                                    value=excluded.value,
                                    updated_at=excluded.updated_at
                                """,
                                (cat, key, str(val), str(updated)),
                            )
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ sync_facts error: {e}")


def search_scroll_history(query: str, limit: int = 5) -> list[dict]:
    """
    Search historical verbatim turns and tool executions via FTS5 BM25 ranking.
    Returns matching snippets, role, timestamp, and tool execution details.
    """
    if not query or not query.strip():
        return []

    # Clean query into terms for FTS5
    clean_q = re.sub(r"[^\w\s]", " ", query).strip()
    if not clean_q:
        return []

    terms = clean_q.split()
    # Match terms with prefix matching
    fts_query = " OR ".join(f'"{t}"*' for t in terms if len(t) > 1)
    if not fts_query:
        fts_query = f'"{clean_q}"*'

    results = []
    with _db_lock:
        try:
            conn = _get_connection()
            cursor = conn.execute(
                """
                SELECT t.id, t.session_id, t.role, t.content, t.tool_name,
                       t.tool_args, t.tool_result, t.timestamp,
                       bm25(turns_fts) AS rank
                FROM turns_fts f
                JOIN turns t ON f.rowid = t.id
                WHERE turns_fts MATCH ?
                ORDER BY rank ASC, t.id DESC
                LIMIT ?
                """,
                (fts_query, limit),
            )
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "tool_name": row["tool_name"],
                    "tool_args": row["tool_args"],
                    "tool_result": row["tool_result"],
                    "timestamp": row["timestamp"],
                    "rank": row["rank"],
                })
            conn.close()
        except Exception as e:
            # Fallback to simple LIKE if FTS syntax error
            try:
                conn = _get_connection()
                like_term = f"%{clean_q}%"
                cursor = conn.execute(
                    """
                    SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp, 0 as rank
                    FROM turns
                    WHERE content LIKE ? OR tool_result LIKE ? OR tool_name LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (like_term, like_term, like_term, limit),
                )
                for row in cursor.fetchall():
                    results.append(dict(row))
                conn.close()
            except Exception as e2:
                print(f"[SQLite Memory] ⚠️ search_scroll_history error: {e2}")

    return results


def search_unified_memory(query: str, limit: int = 8) -> str:
    """
    Unified recall:
      1. Structured Facts from JSON / SQLite Facts (Identity, Preferences, Projects, etc.)
      2. Scroll Context History from SQLite FTS5 (Past conversations, commands, tool results)
    """
    from memory import memory_manager

    query_str = (query or "").strip()
    
    # 1. Fetch structured facts from memory_manager (raw dict search)
    facts_result = memory_manager._search_raw_facts(query_str, limit=limit)
    
    if not query_str:
        return facts_result

    # 2. Fetch past conversation turns & tool actions via FTS5
    past_turns = search_scroll_history(query_str, limit=4)
    
    sections = []
    if facts_result and not facts_result.startswith("Nothing stored about"):
        sections.append(facts_result)

    if past_turns:
        turn_lines = []
        for t in past_turns:
            ts_short = t["timestamp"][:16] if t["timestamp"] else ""
            if t["role"] == "tool" and t["tool_name"]:
                res_preview = (t["tool_result"] or "")[:120].replace("\n", " ")
                turn_lines.append(f"[{ts_short}] [Tool Action] {t['tool_name']} → {res_preview}")
            else:
                cnt_preview = (t["content"] or "")[:140].replace("\n", " ")
                speaker = "User" if t["role"] == "user" else "Assistant"
                turn_lines.append(f"[{ts_short}] {speaker}: {cnt_preview}")

        sections.append(
            f"Relevant past conversation history & actions matching '{query_str}':\n"
            + "\n".join(f"  - {line}" for line in turn_lines)
        )

    if not sections:
        return f"Nothing stored or found in past history about '{query_str}'."

    return "\n\n".join(sections)
