"""
SQLite WAL + FTS5 Memory Engine for Zezo (Scroll Context & Full-Text Search).

Provides:
  - Dedicated single-writer thread with bounded queue and backpressure.
  - ACID transaction boundaries with automatic rollback on error.
  - Async-safe request handling (asyncio.Future) with cancellation resilience.
  - Verbatim turn-by-turn history storage with FTS5 BM25 search.
  - Secret & sensitive token redaction before persistence.
  - Unified hybrid search (structured profile facts + historical turns).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import queue
import re
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, Union

from memory.memory_state import is_memory_paused


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()


def get_db_path() -> Path:
    if "DB_PATH" in globals() and DB_PATH is not None:
        return Path(DB_PATH)
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
_REDACT = "[REDACTED_SECRET]"

_SECRET_PATTERNS = [
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{33}", re.IGNORECASE),                      _REDACT),  # Google API Key (legacy AIzaSy)
    (re.compile(r"AQ\.[A-Za-z0-9_-]{20,}", re.IGNORECASE),                       _REDACT),  # Google API Key (current AQ. format)
    (re.compile(r"tvly-[A-Za-z0-9_-]{20,}", re.IGNORECASE),                      _REDACT),  # Tavily Search API Key
    (re.compile(r"sk-[A-Za-z0-9_-]{20,64}", re.IGNORECASE),                      _REDACT),  # OpenAI / Generic Secret
    (re.compile(r"ghp_[A-Za-z0-9]{20,}", re.IGNORECASE),                         _REDACT),  # GitHub Personal Access Token
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{20,}", re.IGNORECASE),      r"\1" + _REDACT),  # Bearer Tokens
    (re.compile(r"((?:x-goog-api-key|x-api-key|api[-_]?key|authorization|x-auth-token)"
                r"\s*[:=]\s*(?:bearer\s+)?)\S+", re.IGNORECASE),            r"\1" + _REDACT),
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


def _get_connection(read_only: bool = False) -> sqlite3.Connection:
    """Create a thread-safe connection configured for high-concurrency WAL mode."""
    target_db = get_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(target_db),
        timeout=10.0,
        check_same_thread=False,
        isolation_level=None,  # Explicit transaction control
    )
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.row_factory = sqlite3.Row
    return conn


# ── Dedicated Single-Writer Queue Subsystem ───────────────────────────────────

@dataclass
class _WriteTask:
    operation: Union[str, Callable[[sqlite3.Connection], Any]]
    params: Optional[Union[tuple, list]] = None
    future: Optional[concurrent.futures.Future] = None
    loop: Optional[asyncio.AbstractEventLoop] = None
    async_future: Optional[asyncio.Future] = None
    is_sentinel: bool = False


_WRITE_QUEUE_MAXSIZE = 1000
_write_queue: queue.Queue[_WriteTask] = queue.Queue(maxsize=_WRITE_QUEUE_MAXSIZE)
_writer_thread: Optional[threading.Thread] = None
_writer_lock = threading.Lock()
_accepting_writes = True
_writer_dead = False
_SHUTDOWN_SENTINEL = _WriteTask(operation="", is_sentinel=True)


def _ensure_writer_started() -> None:
    """Ensure the dedicated SQLite writer thread is alive and operational."""
    global _writer_thread, _accepting_writes, _writer_dead
    if _writer_thread is not None and _writer_thread.is_alive():
        return

    with _writer_lock:
        if _writer_thread is not None and _writer_thread.is_alive():
            return
        if not _accepting_writes:
            raise RuntimeError("Database writer is shutting down and cannot be started")

        _writer_dead = False
        _writer_thread = threading.Thread(
            target=_db_writer_worker,
            daemon=True,
            name="SQLiteMemoryWriter",
        )
        _writer_thread.start()


def _drain_queue(conn: sqlite3.Connection) -> None:
    """Drain all pending tasks up to the sentinel."""
    while not _write_queue.empty():
        try:
            task = _write_queue.get_nowait()
        except queue.Empty:
            break

        if task.is_sentinel:
            _write_queue.task_done()
            break

        _execute_single_write(conn, task)
        _write_queue.task_done()


def _fail_all_pending(exc: Exception) -> None:
    """Fail all pending futures when writer encounters unrecoverable failure."""
    while not _write_queue.empty():
        try:
            task = _write_queue.get_nowait()
        except queue.Empty:
            break

        if task.future is not None and not task.future.done():
            task.future.set_exception(exc)
        if task.async_future is not None and task.loop is not None:
            def _fail_async(f=task.async_future, e=exc):
                if not f.done():
                    try:
                        f.set_exception(e)
                    except (asyncio.InvalidStateError, RuntimeError):
                        pass
            try:
                task.loop.call_soon_threadsafe(_fail_async)
            except RuntimeError:
                pass
        _write_queue.task_done()


def _execute_single_write(conn: sqlite3.Connection, task: _WriteTask) -> None:
    """Execute a single WriteTask inside an atomic BEGIN IMMEDIATE transaction."""
    res = None
    try:
        conn.execute("BEGIN IMMEDIATE;")
        if callable(task.operation):
            res = task.operation(conn)
        else:
            cur = conn.execute(task.operation, task.params or ())
            res = cur.lastrowid or cur.rowcount
        conn.commit()

        # Resolve synchronous future
        if task.future is not None and not task.future.done():
            task.future.set_result(res)

        # Resolve asynchronous future safely (catching cancellation races)
        if task.async_future is not None and task.loop is not None:
            def _resolve_async(f=task.async_future, r=res):
                if not f.done():
                    try:
                        f.set_result(r)
                    except (asyncio.InvalidStateError, RuntimeError):
                        pass
            try:
                task.loop.call_soon_threadsafe(_resolve_async)
            except RuntimeError:
                pass

    except Exception as exc:
        if conn.in_transaction:
            try:
                conn.rollback()
            except Exception:
                pass

        if task.future is not None and not task.future.done():
            task.future.set_exception(exc)

        if task.async_future is not None and task.loop is not None:
            def _fail_async(f=task.async_future, e=exc):
                if not f.done():
                    try:
                        f.set_exception(e)
                    except (asyncio.InvalidStateError, RuntimeError):
                        pass
            try:
                task.loop.call_soon_threadsafe(_fail_async)
            except RuntimeError:
                pass


def _db_writer_worker() -> None:
    """Dedicated background single-writer loop for all SQLite write operations."""
    global _writer_dead
    restart_count = 0
    current_target_db = get_db_path()
    conn: Optional[sqlite3.Connection] = None

    try:
        conn = _get_connection()
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ Failed to open writer connection: {e}")
        _writer_dead = True
        _fail_all_pending(e)
        return

    while True:
        try:
            task = _write_queue.get()
            if task.is_sentinel:
                _drain_queue(conn)
                try:
                    if conn is not None:
                        conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
                except Exception:
                    pass
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
                _write_queue.task_done()
                break

            # Reopen connection if DB_PATH was changed (e.g. by unit test monkeypatch)
            active_db = get_db_path()
            if conn is None or str(active_db) != str(current_target_db):
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
                conn = _get_connection()
                current_target_db = active_db

            _execute_single_write(conn, task)
            _write_queue.task_done()

        except BaseException as fatal_err:
            if isinstance(fatal_err, (SystemExit, KeyboardInterrupt)):
                break

            print(f"[SQLite Memory] ⚠️ Unexpected writer worker exception: {fatal_err}")
            try:
                if conn is not None and conn.in_transaction:
                    conn.rollback()
            except Exception:
                pass

            if restart_count < 1:
                restart_count += 1
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
                try:
                    conn = _get_connection()
                    current_target_db = get_db_path()
                    continue
                except Exception as reconnect_err:
                    print(f"[SQLite Memory] ⚠️ Writer reconnection failed: {reconnect_err}")

            _writer_dead = True
            _fail_all_pending(RuntimeError(f"Database writer thread terminated: {fatal_err}"))
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
            break


def enqueue_write(
    operation: Union[str, Callable[[sqlite3.Connection], Any]],
    params: Optional[Union[tuple, list]] = None,
    timeout: float = 5.0,
) -> Any:
    """
    Synchronously enqueue a write task to the dedicated single-writer queue and block for result.

    Raises:
        RuntimeError: If writer is dead or shutting down.
        queue.Full: If write queue is full and does not drain within timeout.
        Exception: Any sqlite3 or operational exception raised during the transaction.
    """
    if not _accepting_writes:
        raise RuntimeError("Database writer is shutting down")
    if _writer_dead:
        raise RuntimeError("Database writer thread is dead")

    _ensure_writer_started()
    fut = concurrent.futures.Future()
    task = _WriteTask(operation=operation, params=params, future=fut)

    try:
        _write_queue.put(task, block=True, timeout=timeout)
    except queue.Full:
        raise queue.Full(f"SQLite writer queue full (capacity {_WRITE_QUEUE_MAXSIZE})")

    return fut.result(timeout=timeout)


async def enqueue_write_async(
    operation: Union[str, Callable[[sqlite3.Connection], Any]],
    params: Optional[Union[tuple, list]] = None,
    timeout: float = 5.0,
) -> Any:
    """
    Asynchronously enqueue a write task from an asyncio coroutine and await the result.

    Guarantees that Future cancellation does not abort or corrupt a transaction
    already executing on the writer thread.
    """
    if not _accepting_writes:
        raise RuntimeError("Database writer is shutting down")
    if _writer_dead:
        raise RuntimeError("Database writer thread is dead")

    _ensure_writer_started()
    loop = asyncio.get_running_loop()
    async_fut = loop.create_future()
    sync_fut = concurrent.futures.Future()

    task = _WriteTask(
        operation=operation,
        params=params,
        future=sync_fut,
        loop=loop,
        async_future=async_fut,
    )

    try:
        _write_queue.put_nowait(task)
    except queue.Full:
        try:
            await asyncio.to_thread(_write_queue.put, task, True, timeout)
        except queue.Full:
            raise queue.Full(f"SQLite writer queue full (capacity {_WRITE_QUEUE_MAXSIZE})")

    return await asyncio.wait_for(async_fut, timeout=timeout)


def enqueue_write_nowait(
    operation: Union[str, Callable[[sqlite3.Connection], Any]],
    params: Optional[Union[tuple, list]] = None,
    timeout: float = 2.0,
) -> bool:
    """
    Fire-and-forget enqueue for telemetry / turn logging.
    Blocks up to timeout before dropping the item on extreme backpressure.
    """
    if not _accepting_writes or _writer_dead:
        return False

    try:
        _ensure_writer_started()
        task = _WriteTask(operation=operation, params=params)
        _write_queue.put(task, block=True, timeout=timeout)
        return True
    except (queue.Full, RuntimeError):
        print("[SQLite Memory] ⚠️ Write queue full or unavailable, dropped write")
        return False


def shutdown_db_writer(timeout: float = 10.0) -> None:
    """Gracefully drain the write queue, checkpoint WAL, and terminate writer thread."""
    global _accepting_writes
    with _writer_lock:
        if not _accepting_writes:
            return
        _accepting_writes = False

    if _writer_thread is None or not _writer_thread.is_alive():
        return

    try:
        _write_queue.put(_SHUTDOWN_SENTINEL, block=True, timeout=min(timeout, 5.0))
    except queue.Full:
        try:
            _write_queue.get_nowait()
            _write_queue.task_done()
        except Exception:
            pass
        try:
            _write_queue.put_nowait(_SHUTDOWN_SENTINEL)
        except Exception:
            pass

    _writer_thread.join(timeout=timeout)
    if _writer_thread.is_alive():
        print("[SQLite Memory] ⚠️ Writer thread failed to join within timeout")


def reset_db_writer_for_test() -> None:
    """Helper for unit tests to reset writer thread state cleanly."""
    global _accepting_writes, _writer_dead, _writer_thread
    shutdown_db_writer(timeout=2.0)
    with _writer_lock:
        while not _write_queue.empty():
            try:
                _write_queue.get_nowait()
                _write_queue.task_done()
            except Exception:
                break
        _accepting_writes = True
        _writer_dead = False
        _writer_thread = None


def flush_write_queue(timeout: float = 0.5) -> bool:
    """Wait for all currently pending write tasks to be committed to disk."""
    if _write_queue.unfinished_tasks == 0:
        return True
    start = time.monotonic()
    while _write_queue.unfinished_tasks > 0:
        if time.monotonic() - start > timeout:
            return False
        time.sleep(0.002)
    return True


def get_writer_queue_size() -> int:
    """Return current pending write queue depth."""
    return _write_queue.qsize()


def is_writer_alive() -> bool:
    """Return True if writer thread is running and not dead."""
    return _writer_thread is not None and _writer_thread.is_alive() and not _writer_dead


# ── Schema Initialization ─────────────────────────────────────────────────────

def init_agent_runtime_db(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Initialize agent runtime tables, foreign keys, and indexes.

    Creates:
      1. agent_conversations:
         - Columns: id, agent_id, title, created_at, updated_at, is_archived, metadata
         - Index: idx_agent_conv_lookup ON agent_conversations(agent_id, is_archived, updated_at DESC)
      2. agent_messages:
         - Columns: id, conversation_id, agent_id, role, content, tool_name, tool_args, tool_result, status, created_at
         - Foreign key: conversation_id -> agent_conversations(id) ON DELETE CASCADE
         - Indexes: idx_agent_msg_conv_order ON agent_messages(conversation_id, created_at ASC),
                    idx_agent_msg_agent ON agent_messages(agent_id)
      3. internal_task_ledger:
         - Columns: id, agent_id, conversation_id, title, prompt, status, risk_tier, touched_files, error, created_at, updated_at, interrupted_at
         - Index: idx_task_ledger_reconcile ON internal_task_ledger(status)

    Ensures foreign keys are enabled and schema initialization is idempotent.
    Works whether a connection is provided or opened via _get_connection().
    """
    should_close = False
    if conn is None:
        conn = _get_connection()
        should_close = True

    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        # a) agent_conversations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_conversations (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_archived INTEGER NOT NULL DEFAULT 0,
                metadata TEXT
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_conv_lookup
            ON agent_conversations(agent_id, is_archived, updated_at DESC);
        """)

        # b) agent_messages
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_name TEXT,
                tool_args TEXT,
                tool_result TEXT,
                status TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_msg_conv_order
            ON agent_messages(conversation_id, created_at ASC);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_msg_agent
            ON agent_messages(agent_id);
        """)

        # c) internal_task_ledger
        conn.execute("""
            CREATE TABLE IF NOT EXISTS internal_task_ledger (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                conversation_id TEXT,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_tier TEXT NOT NULL,
                touched_files TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                interrupted_at TEXT
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_ledger_reconcile
            ON internal_task_ledger(status);
        """)
    finally:
        if should_close:
            conn.close()


def init_db() -> None:
    """Initialize the SQLite schema, tables, and FTS5 full-text indices."""
    target_db = get_db_path()
    target_db.parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(conn: sqlite3.Connection) -> None:
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
        # 5. Agent runtime schema (agent_conversations, agent_messages, internal_task_ledger)
        init_agent_runtime_db(conn)
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

        # 8. Deleted Fact Tombstones table (Anti-Resurrection & Relearn Safety)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deleted_fact_tombstones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                UNIQUE(category, key)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_tombstones ON deleted_fact_tombstones(category, key);")

    # Initialize directly on startup connection then ensure writer is started
    with _db_lock:
        conn = _get_connection()
        try:
            _init_schema(conn)
            init_agent_runtime_db(conn)
        finally:
            conn.close()

    _ensure_writer_started()


# ── Helper Query and Write Facades ──────────────────────────────────────────

def query_db(sql: str, params: Optional[Union[tuple, list]] = None) -> List[dict]:
    """Execute a read query against SQLite and return results as a list of dicts."""
    flush_write_queue(timeout=0.5)
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute_write(sql: str, params: Optional[Union[tuple, list]] = None, timeout: float = 5.0) -> Any:
    """Execute a single write query via the thread-safe single writer queue."""
    return enqueue_write(sql, params=params, timeout=timeout)


# ── Turn Logging & Facts Persistence ──────────────────────────────────────────

def log_turn(
    role: str,
    content: str,
    tool_name: Optional[str] = None,
    tool_args: Optional[Union[dict, str]] = None,
    tool_result: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Asynchronously persist a conversation turn via the single-writer queue."""
    if is_memory_paused():
        return

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

    sql = """
    INSERT INTO turns (session_id, role, content, tool_name, tool_args, tool_result, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (sess_id, role, clean_content, clean_tool_name, clean_args, clean_result, ts)
    enqueue_write_nowait(sql, params)


def sync_facts_from_dict(memory_dict: dict) -> None:
    """Sync existing JSON dictionary memory structure into SQLite facts table (respecting tombstones)."""
    if not isinstance(memory_dict, dict):
        return
    now_str = datetime.now().strftime("%Y-%m-%d")

    def _sync(conn: sqlite3.Connection) -> None:
        tombstone_rows = conn.execute("SELECT category, key, deleted_at FROM deleted_fact_tombstones").fetchall()
        tombstones = {(r["category"], r["key"]): r["deleted_at"] for r in tombstone_rows}

        valid_pairs = set()
        for cat, items in memory_dict.items():
            if not isinstance(items, dict):
                continue
            for key, entry in items.items():
                val = entry.get("value", "") if isinstance(entry, dict) else str(entry or "")
                updated = (entry.get("updated", "") if isinstance(entry, dict) else "") or now_str
                if val:
                    pair = (cat, key)
                    if pair in tombstones:
                        tomb_dt = tombstones[pair]
                        if str(updated) < str(tomb_dt):
                            continue
                        else:
                            conn.execute("DELETE FROM deleted_fact_tombstones WHERE category = ? AND key = ?", (cat, key))
                            tombstones.pop(pair, None)

                    valid_pairs.add(pair)
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

    try:
        enqueue_write(_sync)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ sync_facts error: {e}")


def get_all_facts() -> dict[tuple[str, str], dict]:
    """Retrieve all facts currently stored in the SQLite facts table."""
    facts = {}
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
            cursor = conn.execute("SELECT category, key, value, updated_at FROM facts")
            for row in cursor.fetchall():
                facts[(row["category"], row["key"])] = {
                    "value": row["value"],
                    "updated_at": row["updated_at"],
                }
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ get_all_facts error: {e}")
    return facts


def delete_fact(category: str, key: str) -> bool:
    """Delete fact from SQLite, create tombstone, and scrub memory tool execution records."""
    deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _delete(conn: sqlite3.Connection) -> bool:
        conn.execute("DELETE FROM facts WHERE category = ? AND key = ?", (category, key))
        conn.execute(
            """
            INSERT INTO deleted_fact_tombstones (category, key, deleted_at)
            VALUES (?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET deleted_at = excluded.deleted_at
            """,
            (category, key, deleted_at),
        )
        conn.execute(
            """
            UPDATE turns SET content = '[Fact removed by user]'
            WHERE (tool_name = 'memory' OR tool_name = 'save_memory')
              AND tool_args LIKE '%"key": "' || ? || '"%'
            """,
            (key,),
        )
        return True

    try:
        return bool(enqueue_write(_delete))
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ delete_fact error: {e}")
        return False


def record_learn(category: str, key: str, value: str, updated_at: Optional[str] = None) -> bool:
    """Upsert fact into SQLite facts table and clear any existing tombstone (relearn-safe)."""
    now_str = updated_at or datetime.now().strftime("%Y-%m-%d")

    def _learn(conn: sqlite3.Connection) -> bool:
        conn.execute("DELETE FROM deleted_fact_tombstones WHERE category = ? AND key = ?", (category, key))
        conn.execute(
            """
            INSERT INTO facts (category, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (category, key, str(value), str(now_str)),
        )
        return True

    try:
        return bool(enqueue_write(_learn))
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ record_learn error: {e}")
        return False


# ── Recency Re-ranking & Search ───────────────────────────────────────────────

def _rerank_by_recency(results: list[dict], weight: float, half_life_days: float) -> list[dict]:
    """Blend BM25 relevance with recency."""
    if not results or weight <= 0:
        return results

    weight = min(1.0, max(0.0, float(weight)))
    half_life = max(1.0, float(half_life_days or 30.0))

    ranks = [float(r.get("rank") or 0.0) for r in results]
    lo, hi = min(ranks), max(ranks)
    span = (hi - lo) or 1.0

    now = datetime.now()
    scored = []
    for res, rk in zip(results, ranks):
        relevance = (hi - rk) / span
        recency = 0.0
        ts = (res.get("timestamp") or "").strip()
        if ts:
            try:
                moment = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                moment = None
            if moment is not None:
                age_days = max(0.0, (now - moment).total_seconds() / 86400.0)
                recency = 0.5 ** (age_days / half_life)
        final = (1.0 - weight) * relevance + weight * recency
        scored.append((final, int(res.get("id") or 0), res))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    for final, _tid, res in scored:
        res["score"] = round(final, 4)
    return [item[2] for item in scored]


def search_scroll_history(
    query: str,
    limit: int = 5,
    session_id: Optional[str] = None,
    recency_weight: float = 0.0,
    recency_half_life_days: float = 30.0,
) -> list[dict]:
    """Search historical verbatim turns and tool executions via FTS5 BM25 ranking."""
    if not query or not query.strip():
        return []

    flush_write_queue(timeout=0.2)

    clean_q = re.sub(r"[^\w\s]", " ", query).strip()
    if not clean_q:
        return []

    terms = clean_q.split()
    fts_query = " OR ".join(f'"{t}"*' for t in terms if len(t) > 1)
    if not fts_query:
        fts_query = f'"{clean_q}"*'

    sql_limit = limit
    if recency_weight > 0:
        sql_limit = min(max(limit * 5, limit + 20), 200)

    results = []
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
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
                    (fts_query, session_id, sql_limit),
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
                    (fts_query, sql_limit),
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
        except Exception:
            try:
                conn = _get_connection(read_only=True)
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
                        (like_term, like_term, like_term, session_id, sql_limit),
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
                        (like_term, like_term, like_term, sql_limit),
                    )
                for row in cursor.fetchall():
                    results.append(dict(row))
                conn.close()
            except Exception as e2:
                print(f"[SQLite Memory] ⚠️ search_scroll_history error: {e2}")

    if recency_weight > 0 and results:
        results = _rerank_by_recency(results, recency_weight, recency_half_life_days)
    else:
        for r in results:
            if "score" not in r:
                raw_rank = abs(float(r.get("rank") or 1.0))
                r["score"] = round(raw_rank, 6) if raw_rank < 0.001 else round(raw_rank, 4)
                if r["score"] == 0.0 and raw_rank > 0:
                    r["score"] = 0.000001

    return results[:limit]


def expand_turns(lo: int, hi: int, session_id: Optional[str] = None) -> list[dict]:
    """Fetch contiguous turn sequences by ID range [lo, hi] inclusive."""
    if lo > hi:
        lo, hi = hi, lo
    if (hi - lo) > 200:
        hi = lo + 200

    results = []
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
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


_PERIOD_DAYS = {
    "today": 1,
    "yesterday": 1,
    "last_3_days": 3,
    "last_7_days": 7,
    "last_14_days": 14,
    "last_30_days": 30,
}


def resolve_period(
    period: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve a (since, until) 'YYYY-MM-DD' window from model-friendly inputs."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    s = str(since or "").strip() or None
    u = str(until or "").strip() or None
    if s or u:
        return s, u

    p = str(period or "").strip().lower().replace("-", "_").replace(" ", "_")
    if p == "yesterday":
        y = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return y, y
    days = _PERIOD_DAYS.get(p)
    if days:
        start = (now - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        return start, today
    return None, None


def _period_clause(since: Optional[str], until: Optional[str], session_id: Optional[str]) -> tuple[str, list]:
    """Build the shared WHERE fragment for date-window / session queries."""
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("substr(timestamp, 1, 10) >= ?")
        params.append(since)
    if until:
        clauses.append("substr(timestamp, 1, 10) <= ?")
        params.append(until)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def list_sessions(
    limit: int = 10,
    since: Optional[str] = None,
    until: Optional[str] = None,
    session_id: Optional[str] = None,
) -> list[dict]:
    """List conversation sessions ordered by recency (most recent first)."""
    limit = max(1, min(int(limit or 10), 50))
    where, params = _period_clause(since, until, session_id)
    sessions: list[dict] = []
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
            cursor = conn.execute(
                """
                SELECT session_id,
                       MIN(timestamp) AS start_time,
                       MAX(timestamp) AS end_time,
                       COUNT(*)       AS turn_count
                FROM turns
                """
                + where
                + """
                GROUP BY session_id
                ORDER BY end_time DESC
                LIMIT ?
                """,
                (*params, limit),
            )
            for row in cursor.fetchall():
                sessions.append(dict(row))
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ list_sessions error: {e}")

    for sess in sessions:
        try:
            head = get_recent_turns(limit=1, session_id=sess["session_id"], newest_first=False)
            sess["topic"] = (head[0].get("content") or "").strip() if head else ""
        except Exception:
            sess["topic"] = ""
    return sessions


def get_recent_turns(
    limit: int = 30,
    since: Optional[str] = None,
    until: Optional[str] = None,
    session_id: Optional[str] = None,
    newest_first: bool = True,
) -> list[dict]:
    """Fetch turns ordered by recency, optionally inside a date window."""
    flush_write_queue(timeout=0.2)
    limit = max(1, min(int(limit or 30), 200))
    where, params = _period_clause(since, until, session_id)
    order = "timestamp DESC, id DESC" if newest_first else "timestamp ASC, id ASC"
    results: list[dict] = []
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
            cursor = conn.execute(
                """
                SELECT id, session_id, role, content, tool_name, tool_args, tool_result, timestamp
                FROM turns
                """
                + where
                + f" ORDER BY {order} LIMIT ?",
                (*params, limit),
            )
            for row in cursor.fetchall():
                results.append(dict(row))
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ get_recent_turns error: {e}")
    return results


def get_session_turn_window(
    after: Optional[str] = None,
    session_id: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return the (first, last) turn timestamps of a session."""
    sess = session_id or _current_session_id
    first: Optional[str] = None
    last: Optional[str] = None
    with _db_lock:
        try:
            conn = _get_connection(read_only=True)
            cursor = conn.execute(
                """
                SELECT MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
                FROM turns
                WHERE session_id = ? AND (? IS NULL OR timestamp > ?)
                """,
                (sess, after, after),
            )
            row = cursor.fetchone()
            if row:
                first = row["first_ts"]
                last = row["last_ts"]
            conn.close()
        except Exception as e:
            print(f"[SQLite Memory] ⚠️ get_session_turn_window error: {e}")
    return first, last


def search_unified_memory(query: str, limit: int = 8) -> str:
    """Unified recall across structured facts and past turns."""
    from memory import memory_manager

    query_str = (query or "").strip()
    facts_result = memory_manager._search_raw_facts(query_str, limit=limit)
    if not query_str:
        return facts_result

    past_turns = search_scroll_history(
        query_str,
        limit=max(limit, 8),
        recency_weight=0.35,
        recency_half_life_days=14.0,
    )

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


# ── Explicit Rules, Conflicts & Summaries ────────────────────────────────────

def insert_explicit_rule(rule_text: str, category: str = "general", source_turn_id: Optional[int] = None) -> int:
    """Store an immutable user directive that cannot be altered or purged by AI summaries."""
    if not rule_text or not rule_text.strip():
        return 0
    clean_rule = redact_secrets(rule_text.strip())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
    INSERT INTO user_explicit_rules (rule_text, category, source_turn_id, created_at, is_active, origin)
    VALUES (?, ?, ?, ?, 1, 'user_explicit')
    """
    params = (clean_rule, category.strip() or "general", source_turn_id, ts)
    try:
        res = enqueue_write(sql, params)
        return int(res or 0)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ insert_explicit_rule error: {e}")
        return 0


def get_explicit_rules(active_only: bool = True) -> list[dict]:
    """Retrieve immutable user-defined directives."""
    with _db_lock:
        conn = _get_connection(read_only=True)
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
    sql = "UPDATE user_explicit_rules SET is_active = ? WHERE id = ?"
    params = (1 if is_active else 0, rule_id)
    try:
        res = enqueue_write(sql, params)
        return bool(res and res > 0)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ set_explicit_rule_status error: {e}")
        return False


def insert_memory_conflict(
    existing_content: str,
    contradicting_content: str,
    source_session_id: str,
    existing_rule_id: Optional[int] = None,
    existing_fact_key: Optional[str] = None,
) -> int:
    """Record a detected factual or directive contradiction for explicit human resolution."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
    INSERT INTO memory_conflicts (
        existing_rule_id, existing_fact_key, existing_content,
        contradicting_content, source_session_id, status, detected_at
    ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
    """
    params = (
        existing_rule_id,
        existing_fact_key,
        redact_secrets(existing_content),
        redact_secrets(contradicting_content),
        source_session_id,
        ts,
    )
    try:
        res = enqueue_write(sql, params)
        return int(res or 0)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ insert_memory_conflict error: {e}")
        return 0


def get_pending_conflicts() -> list[dict]:
    """Fetch all unresolved memory conflicts."""
    with _db_lock:
        conn = _get_connection(read_only=True)
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
    sql = """
    UPDATE memory_conflicts
    SET status = ?, resolved_at = ?, resolution_notes = ?
    WHERE id = ?
    """
    params = (status.upper(), ts, redact_secrets(notes), conflict_id)
    try:
        res = enqueue_write(sql, params)
        return bool(res and res > 0)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ resolve_memory_conflict error: {e}")
        return False


def get_uncondensed_turns(limit: int = 150) -> list[dict]:
    """Retrieve historical turns that have not yet been compacted into session summaries."""
    with _db_lock:
        conn = _get_connection(read_only=True)
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
    sql = """
    INSERT INTO session_condensations (session_id, last_condensed_turn_id, summary, condensed_at)
    VALUES (?, ?, ?, ?)
    """
    params = (session_id, last_turn_id, redact_secrets(summary), ts)
    try:
        enqueue_write(sql, params)
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ record_condensation error: {e}")


def wipe_all_sqlite_memory() -> dict[str, int]:
    """Atomically purge all historical turns, FTS indices, facts, rules, conflicts, and vacuum disk."""
    def _wipe(conn: sqlite3.Connection) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tbl in ["turns", "facts", "user_explicit_rules", "memory_conflicts", "session_condensations"]:
            try:
                cur = conn.execute(f"SELECT COUNT(*) FROM {tbl}")
                counts[tbl] = cur.fetchone()[0]
            except Exception:
                counts[tbl] = 0

        conn.execute("DELETE FROM turns;")
        try:
            conn.execute("DELETE FROM turns_fts;")
        except Exception:
            pass
        conn.execute("DELETE FROM facts;")
        conn.execute("DELETE FROM user_explicit_rules;")
        conn.execute("DELETE FROM memory_conflicts;")
        conn.execute("DELETE FROM session_condensations;")
        conn.execute("VACUUM;")
        return counts

    try:
        return enqueue_write(_wipe) or {}
    except Exception as e:
        print(f"[SQLite Memory] ⚠️ wipe_all_sqlite_memory error: {e}")
        return {}
