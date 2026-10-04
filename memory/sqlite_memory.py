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

def get_db_path() -> Path:
    env_path = os.environ.get("ZEZO_DB_PATH")
    if env_path:
        return Path(env_path)
    return BASE_DIR / "memory" / "zezo_brain.db"

DB_PATH = get_db_path()

_db_lock = threading.Lock()
_current_session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def generate_composite_session_id(agent_id: str, session_uuid: Optional[str] = None) -> str:
    """Generate isolated composite session ID format: <agent_id>:<session_uuid>."""
    aid = (agent_id or "ZEZO").upper().strip()
    suuid = session_uuid or f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(3).hex()}"
    return f"{aid}:{suuid}"


def get_current_session_id() -> str:
    """Return the active session ID."""
    return _current_session_id


def set_current_session_id(session_id: str) -> None:
    """Set the active global session ID."""
    global _current_session_id
    _current_session_id = session_id.strip()

# ── Secret Redaction Patterns ───────────────────────────────────────────────
# Each entry is (compiled pattern, replacement). Most replacements are the
# blanket token, but credential-bearing HEADERS keep their name so a scrubbed
# log line still says which credential was removed.
_REDACT = "[REDACTED_SECRET]"

_SECRET_PATTERNS = [
    # ── Known key shapes ────────────────────────────────────────────────────
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{33}", re.IGNORECASE),                      _REDACT),  # Google API Key (legacy AIzaSy)
    (re.compile(r"AQ\.[A-Za-z0-9_-]{20,}", re.IGNORECASE),                       _REDACT),  # Google API Key (current AQ. format)
    (re.compile(r"tvly-[A-Za-z0-9_-]{20,}", re.IGNORECASE),                      _REDACT),  # Tavily Search API Key
    (re.compile(r"sk-[A-Za-z0-9_-]{20,64}", re.IGNORECASE),                      _REDACT),  # OpenAI / Generic Secret
    (re.compile(r"ghp_[A-Za-z0-9]{20,}", re.IGNORECASE),                         _REDACT),  # GitHub Personal Access Token
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{20,}", re.IGNORECASE),      r"\1" + _REDACT),  # Bearer Tokens

    # ── Format-agnostic: redact by header NAME ──────────────────────────────
    # Matching the credential's shape only protects against formats we already
    # know about. The Gemini Live handshake prints `x-goog-api-key: AQ.…` in the
    # websockets DEBUG stream, and AQ.-prefixed keys were invisible to every
    # shape rule above. Matching the header name instead means any current or
    # future key format behind a known header is scrubbed without a new pattern.
    # The optional `bearer` is consumed here so an Authorization line gets one
    # clean redaction rather than a doubled label.
    (re.compile(r"((?:x-goog-api-key|x-api-key|api[-_]?key|authorization|x-auth-token)"
                r"\s*[:=]\s*(?:bearer\s+)?)\S+", re.IGNORECASE),            r"\1" + _REDACT),

    # ── Session artefacts ───────────────────────────────────────────────────
    (re.compile(r"(set-cookie\s*:\s*)\S+", re.IGNORECASE),                  r"\1" + _REDACT),  # Session cookies
    (re.compile(r"(password\s*(?:[:=]|is)\s*['\"])[^'\"]+(['\"])", re.IGNORECASE),
     r"\1" + _REDACT + r"\2"),                                                                  # Password expressions
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, passwords, and API tokens before saving to disk."""
    if not text or not isinstance(text, str):
        return ""
    scrubbed = text
    for pattern, replacement in _SECRET_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def _get_connection() -> sqlite3.Connection:
    """Create a thread-safe connection configured for high-concurrency WAL mode."""
    target_db = get_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_db), timeout=10.0, check_same_thread=False)
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

                # 5. Immutable User Explicit Rules table (Phase 3 Memory Palace)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_explicit_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_text TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        source_turn_id INTEGER,
                        created_at TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        origin TEXT DEFAULT 'user_explicit'
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_active ON user_explicit_rules(is_active);")

                # 6. Memory Conflict Graph / Pending Resolution table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_conflicts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        existing_rule_id INTEGER,
                        existing_fact_key TEXT,
                        existing_content TEXT NOT NULL,
                        contradicting_content TEXT NOT NULL,
                        source_session_id TEXT NOT NULL,
                        status TEXT DEFAULT 'PENDING',
                        detected_at TEXT NOT NULL,
                        resolved_at TEXT,
                        resolution_notes TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_status ON memory_conflicts(status);")

                # 7. Session Condensation Log table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_condensations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        last_condensed_turn_id INTEGER NOT NULL,
                        summary TEXT NOT NULL,
                        condensed_at TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cond_sess ON session_condensations(session_id);")
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
                valid_pairs = set()
                for cat, items in memory_dict.items():
                    if not isinstance(items, dict):
                        continue
                    for key, entry in items.items():
                        val = entry.get("value", "") if isinstance(entry, dict) else str(entry or "")
                        updated = (entry.get("updated", "") if isinstance(entry, dict) else "") or now_str
                        if val:
                            valid_pairs.add((cat, key))
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
                # Purge facts that no longer exist in memory_dict
                cursor = conn.execute("SELECT category, key FROM facts")
                for row in cursor.fetchall():
                    if (row["category"], row["key"]) not in valid_pairs:
                        conn.execute(
                            "DELETE FROM facts WHERE category = ? AND key = ?",
                            (row["category"], row["key"]),
                        )
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ sync_facts error: {e}")


def search_scroll_history(query: str, limit: int = 5, session_id: Optional[str] = None) -> list[dict]:
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
            if session_id:
                cursor = conn.execute(
                    """
                    SELECT t.id, t.session_id, t.role, t.content, t.tool_name,
                           t.tool_args, t.tool_result, t.timestamp,
                           bm25(turns_fts) AS rank
                    FROM turns_fts f
                    JOIN turns t ON f.rowid = t.id
                    WHERE turns_fts MATCH ? AND t.session_id = ?
                    ORDER BY rank ASC, t.id DESC
                    LIMIT ?
                    """,
                    (fts_query, session_id, limit),
                )
            else:
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
                if session_id:
                    cursor = conn.execute(
                        """
                        SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp, 0 as rank
                        FROM turns
                        WHERE (content LIKE ? OR tool_result LIKE ? OR tool_name LIKE ?) AND session_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (like_term, like_term, like_term, session_id, limit),
                    )
                else:
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


def expand_turns(lo: int, hi: int, session_id: Optional[str] = None) -> list[dict]:
    """
    Fetch contiguous turn sequences by ID range [lo, hi] inclusive.
    Optionally scopes to a specific composite session ID.
    """
    if lo > hi:
        lo, hi = hi, lo

    # Cap range to 200 turns per call to protect memory
    if (hi - lo) > 200:
        hi = lo + 200

    results = []
    with _db_lock:
        try:
            conn = _get_connection()
            if session_id:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp
                    FROM turns
                    WHERE id >= ? AND id <= ? AND session_id = ?
                    ORDER BY id ASC
                    """,
                    (lo, hi, session_id),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp
                    FROM turns
                    WHERE id >= ? AND id <= ?
                    ORDER BY id ASC
                    """,
                    (lo, hi),
                )
            for row in cursor.fetchall():
                results.append(dict(row))
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ expand_turns error: {e}")

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
                turn_lines.append(f"[{ts_short}] [Tool Action] {t['tool_name']} -> {res_preview}")
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


def insert_explicit_rule(rule_text: str, category: str = "general", source_turn_id: Optional[int] = None) -> int:
    """Store an immutable user directive that cannot be altered or purged by AI summaries."""
    if not rule_text or not rule_text.strip():
        return 0
    clean_rule = redact_secrets(rule_text.strip())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO user_explicit_rules (rule_text, category, source_turn_id, created_at, is_active, origin)
                    VALUES (?, ?, ?, ?, 1, 'user_explicit')
                    """,
                    (clean_rule, category.strip() or "general", source_turn_id, ts),
                )
                return cursor.lastrowid or 0
        finally:
            conn.close()


def get_explicit_rules(active_only: bool = True) -> list[dict]:
    """Retrieve immutable user-defined directives."""
    with _db_lock:
        conn = _get_connection()
        try:
            sql = "SELECT id, rule_text, category, source_turn_id, created_at, is_active FROM user_explicit_rules"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY id ASC"
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def set_explicit_rule_status(rule_id: int, is_active: bool) -> bool:
    """Toggle activation state of an explicit rule upon direct human action."""
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE user_explicit_rules SET is_active = ? WHERE id = ?",
                    (1 if is_active else 0, rule_id),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()


def insert_memory_conflict(
    existing_content: str,
    contradicting_content: str,
    source_session_id: str,
    existing_rule_id: Optional[int] = None,
    existing_fact_key: Optional[str] = None,
) -> int:
    """Record a detected factual or directive contradiction for explicit human resolution."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO memory_conflicts (
                        existing_rule_id, existing_fact_key, existing_content,
                        contradicting_content, source_session_id, status, detected_at
                    ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
                    """,
                    (
                        existing_rule_id,
                        existing_fact_key,
                        redact_secrets(existing_content),
                        redact_secrets(contradicting_content),
                        source_session_id,
                        ts,
                    ),
                )
                return cursor.lastrowid or 0
        finally:
            conn.close()


def get_pending_conflicts() -> list[dict]:
    """Fetch all unresolved memory conflicts."""
    with _db_lock:
        conn = _get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, existing_rule_id, existing_fact_key, existing_content,
                       contradicting_content, source_session_id, status, detected_at
                FROM memory_conflicts
                WHERE status = 'PENDING'
                ORDER BY id ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


def resolve_memory_conflict(conflict_id: int, status: str, notes: str = "") -> bool:
    """Resolve a conflict node (RESOLVED_OVERWRITE, RESOLVED_KEEP_OLD, RESOLVED_MERGE)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE memory_conflicts
                    SET status = ?, resolved_at = ?, resolution_notes = ?
                    WHERE id = ?
                    """,
                    (status.upper(), ts, redact_secrets(notes), conflict_id),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()


def get_uncondensed_turns(limit: int = 150) -> list[dict]:
    """Retrieve historical turns that have not yet been compacted into session summaries."""
    with _db_lock:
        conn = _get_connection()
        try:
            cursor = conn.execute("SELECT MAX(last_condensed_turn_id) AS last_id FROM session_condensations")
            row = cursor.fetchone()
            last_id = (row["last_id"] if row and row["last_id"] is not None else 0)

            cursor = conn.execute(
                """
                SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp
                FROM turns
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (last_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()


def record_condensation(session_id: str, last_turn_id: int, summary: str) -> None:
    """Persist session distillation checkpoint."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO session_condensations (session_id, last_condensed_turn_id, summary, condensed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, last_turn_id, redact_secrets(summary), ts),
                )
        finally:
            conn.close()

