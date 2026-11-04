"""
tests/test_schema_ddl.py - Unit tests for Phase 1 Step 3 Schema DDL & Migrations.

Covers:
  1. Creation of agent_conversations, agent_messages, and internal_task_ledger tables and specified indexes.
  2. Idempotency: multiple invocations of init_agent_runtime_db() and init_db() do not error or duplicate data.
  3. Foreign key enforcement and ON DELETE CASCADE on agent_messages -> agent_conversations.
  4. Preservation of existing tables (facts, turns, user_explicit_rules, etc.) and their data.
  5. Schema verification via PRAGMA table_info, PRAGMA index_list, and PRAGMA foreign_key_list.
  6. Invocation modes: explicit conn, default conn=None, and enqueue_write(init_agent_runtime_db).
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from memory import sqlite_memory


@pytest.fixture
def clean_db(monkeypatch):
    """Provide an isolated temporary database for each test."""
    with tempfile.TemporaryDirectory() as td:
        db_file = Path(td) / "test_brain.db"
        monkeypatch.setattr(sqlite_memory, "DB_PATH", db_file)
        sqlite_memory.reset_db_writer_for_test()
        sqlite_memory.init_db()

        yield db_file

        sqlite_memory.reset_db_writer_for_test()


def _get_columns(conn: sqlite3.Connection, table_name: str) -> dict[str, dict]:
    """Inspect columns of a table via PRAGMA table_info."""
    cur = conn.execute(f"PRAGMA table_info({table_name});")
    cols = {}
    for row in cur.fetchall():
        cols[row[1]] = {
            "cid": row[0],
            "name": row[1],
            "type": row[2].upper(),
            "notnull": bool(row[3]),
            "dflt_value": row[4],
            "pk": bool(row[5]),
        }
    return cols


def _get_indexes(conn: sqlite3.Connection, table_name: str) -> dict[str, list[str]]:
    """Inspect user indexes and their columns via PRAGMA index_list and PRAGMA index_info."""
    cur = conn.execute(f"PRAGMA index_list({table_name});")
    indexes = {}
    for row in cur.fetchall():
        idx_name = row[1]
        # Ignore autoindex created for PRIMARY KEY / UNIQUE constraints
        if idx_name.startswith("sqlite_autoindex_"):
            continue
        info_cur = conn.execute(f"PRAGMA index_info({idx_name});")
        cols = [col_row[2] for col_row in info_cur.fetchall()]
        indexes[idx_name] = cols
    return indexes


def _get_foreign_keys(conn: sqlite3.Connection, table_name: str) -> list[dict]:
    """Inspect foreign key constraints via PRAGMA foreign_key_list."""
    cur = conn.execute(f"PRAGMA foreign_key_list({table_name});")
    fks = []
    for row in cur.fetchall():
        fks.append({
            "id": row[0],
            "seq": row[1],
            "table": row[2],
            "from": row[3],
            "to": row[4],
            "on_update": row[5],
            "on_delete": row[6],
            "match": row[7],
        })
    return fks


def test_schema_tables_and_columns_created(clean_db):
    """Test 1: Verify that the 3 new tables exist and columns match the blueprint exactly."""
    conn = sqlite3.connect(str(clean_db))
    try:
        # Check table existence in sqlite_master
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        assert "agent_conversations" in tables
        assert "agent_messages" in tables
        assert "internal_task_ledger" in tables

        # a) agent_conversations columns
        conv_cols = _get_columns(conn, "agent_conversations")
        assert "id" in conv_cols and conv_cols["id"]["pk"] is True and conv_cols["id"]["type"] == "TEXT"
        assert "agent_id" in conv_cols and conv_cols["agent_id"]["notnull"] is True and conv_cols["agent_id"]["type"] == "TEXT"
        assert "title" in conv_cols and conv_cols["title"]["notnull"] is True and conv_cols["title"]["type"] == "TEXT"
        assert "created_at" in conv_cols and conv_cols["created_at"]["notnull"] is True and conv_cols["created_at"]["type"] == "TEXT"
        assert "updated_at" in conv_cols and conv_cols["updated_at"]["notnull"] is True and conv_cols["updated_at"]["type"] == "TEXT"
        assert "is_archived" in conv_cols and conv_cols["is_archived"]["notnull"] is True and conv_cols["is_archived"]["type"] == "INTEGER"
        assert str(conv_cols["is_archived"]["dflt_value"]) == "0"
        assert "metadata" in conv_cols and conv_cols["metadata"]["type"] == "TEXT"

        # b) agent_messages columns
        msg_cols = _get_columns(conn, "agent_messages")
        assert "id" in msg_cols and msg_cols["id"]["pk"] is True and msg_cols["id"]["type"] == "TEXT"
        assert "conversation_id" in msg_cols and msg_cols["conversation_id"]["notnull"] is True and msg_cols["conversation_id"]["type"] == "TEXT"
        assert "agent_id" in msg_cols and msg_cols["agent_id"]["notnull"] is True and msg_cols["agent_id"]["type"] == "TEXT"
        assert "role" in msg_cols and msg_cols["role"]["notnull"] is True and msg_cols["role"]["type"] == "TEXT"
        assert "content" in msg_cols and msg_cols["content"]["notnull"] is True and msg_cols["content"]["type"] == "TEXT"
        assert "tool_name" in msg_cols and msg_cols["tool_name"]["type"] == "TEXT"
        assert "tool_args" in msg_cols and msg_cols["tool_args"]["type"] == "TEXT"
        assert "tool_result" in msg_cols and msg_cols["tool_result"]["type"] == "TEXT"
        assert "status" in msg_cols and msg_cols["status"]["type"] == "TEXT"
        assert "created_at" in msg_cols and msg_cols["created_at"]["notnull"] is True and msg_cols["created_at"]["type"] == "TEXT"

        # c) internal_task_ledger columns
        task_cols = _get_columns(conn, "internal_task_ledger")
        assert "id" in task_cols and task_cols["id"]["pk"] is True and task_cols["id"]["type"] == "TEXT"
        assert "agent_id" in task_cols and task_cols["agent_id"]["notnull"] is True and task_cols["agent_id"]["type"] == "TEXT"
        assert "conversation_id" in task_cols and task_cols["conversation_id"]["type"] == "TEXT"
        assert "title" in task_cols and task_cols["title"]["notnull"] is True and task_cols["title"]["type"] == "TEXT"
        assert "prompt" in task_cols and task_cols["prompt"]["notnull"] is True and task_cols["prompt"]["type"] == "TEXT"
        assert "status" in task_cols and task_cols["status"]["notnull"] is True and task_cols["status"]["type"] == "TEXT"
        assert "risk_tier" in task_cols and task_cols["risk_tier"]["notnull"] is True and task_cols["risk_tier"]["type"] == "TEXT"
        assert "touched_files" in task_cols and task_cols["touched_files"]["type"] == "TEXT"
        assert "error" in task_cols and task_cols["error"]["type"] == "TEXT"
        assert "created_at" in task_cols and task_cols["created_at"]["notnull"] is True and task_cols["created_at"]["type"] == "TEXT"
        assert "updated_at" in task_cols and task_cols["updated_at"]["notnull"] is True and task_cols["updated_at"]["type"] == "TEXT"
        assert "interrupted_at" in task_cols and task_cols["interrupted_at"]["type"] == "TEXT"
    finally:
        conn.close()


def test_schema_indexes_created(clean_db):
    """Test 2: Verify that specified indexes exist on the 3 tables with correct indexed columns."""
    conn = sqlite3.connect(str(clean_db))
    try:
        conv_indexes = _get_indexes(conn, "agent_conversations")
        assert "idx_agent_conv_lookup" in conv_indexes
        assert conv_indexes["idx_agent_conv_lookup"] == ["agent_id", "is_archived", "updated_at"]

        msg_indexes = _get_indexes(conn, "agent_messages")
        assert "idx_agent_msg_conv_order" in msg_indexes
        assert msg_indexes["idx_agent_msg_conv_order"] == ["conversation_id", "created_at"]
        assert "idx_agent_msg_agent" in msg_indexes
        assert msg_indexes["idx_agent_msg_agent"] == ["agent_id"]

        task_indexes = _get_indexes(conn, "internal_task_ledger")
        assert "idx_task_ledger_reconcile" in task_indexes
        assert task_indexes["idx_task_ledger_reconcile"] == ["status"]
    finally:
        conn.close()


def test_foreign_key_and_cascade_delete(clean_db):
    """Test 3: Verify foreign key enforcement and ON DELETE CASCADE on agent_messages -> agent_conversations."""
    conn = sqlite3.connect(str(clean_db))
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        # Check foreign key configuration
        fks = _get_foreign_keys(conn, "agent_messages")
        assert len(fks) >= 1
        fk_conv = next((fk for fk in fks if fk["table"] == "agent_conversations"), None)
        assert fk_conv is not None
        assert fk_conv["from"] == "conversation_id"
        assert fk_conv["to"] == "id"
        assert fk_conv["on_delete"] == "CASCADE"

        # 1. Attempt insert with invalid conversation_id -> IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO agent_messages (id, conversation_id, agent_id, role, content, created_at)
                VALUES ('msg_fail', 'nonexistent_conv', 'agent_a', 'user', 'hello', '2026-11-03T00:00:00Z');
            """)

        # 2. Insert valid conversation and messages
        conn.execute("""
            INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at)
            VALUES ('conv_1', 'agent_a', 'Test Session', '2026-11-03T00:00:00Z', '2026-11-03T00:00:00Z');
        """)
        conn.execute("""
            INSERT INTO agent_messages (id, conversation_id, agent_id, role, content, created_at)
            VALUES ('msg_1', 'conv_1', 'agent_a', 'user', 'Hello agent', '2026-11-03T00:00:01Z');
        """)
        conn.execute("""
            INSERT INTO agent_messages (id, conversation_id, agent_id, role, content, created_at)
            VALUES ('msg_2', 'conv_1', 'agent_a', 'assistant', 'Hello user', '2026-11-03T00:00:02Z');
        """)
        conn.commit()

        # Confirm rows exist
        cur = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE conversation_id='conv_1';")
        assert cur.fetchone()[0] == 2

        # 3. Delete parent conversation -> cascade deletes child messages
        conn.execute("DELETE FROM agent_conversations WHERE id='conv_1';")
        conn.commit()

        cur = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE conversation_id='conv_1';")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_idempotency_multiple_calls_and_data_preservation(clean_db):
    """Test 4: Verify idempotency; multiple calls to init_agent_runtime_db and init_db do not error or mutate data."""
    conn = sqlite3.connect(str(clean_db))
    try:
        # Populate tables with sample records
        conn.execute("""
            INSERT INTO agent_conversations (id, agent_id, title, created_at, updated_at, metadata)
            VALUES ('conv_idem_1', 'agent_coder', 'Coding Task', '2026-11-03T10:00:00Z', '2026-11-03T10:00:00Z', '{"k":"v"}');
        """)
        conn.execute("""
            INSERT INTO agent_messages (id, conversation_id, agent_id, role, content, tool_name, created_at)
            VALUES ('msg_idem_1', 'conv_idem_1', 'agent_coder', 'assistant', 'Working on it', 'read_file', '2026-11-03T10:00:01Z');
        """)
        conn.execute("""
            INSERT INTO internal_task_ledger (id, agent_id, conversation_id, title, prompt, status, risk_tier, created_at, updated_at)
            VALUES ('task_idem_1', 'agent_coder', 'conv_idem_1', 'Refactor module', 'Do the refactor', 'RUNNING', 'MEDIUM', '2026-11-03T10:00:00Z', '2026-11-03T10:00:00Z');
        """)
        conn.commit()
    finally:
        conn.close()

    # Call init_agent_runtime_db multiple times with both explicit conn and default conn
    for _ in range(3):
        sqlite_memory.init_agent_runtime_db()
        sqlite_memory.init_db()

    conn = sqlite3.connect(str(clean_db))
    try:
        cur = conn.execute("SELECT id, title, metadata FROM agent_conversations WHERE id='conv_idem_1';")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "conv_idem_1"
        assert row[1] == "Coding Task"
        assert row[2] == '{"k":"v"}'

        cur = conn.execute("SELECT id, tool_name FROM agent_messages WHERE id='msg_idem_1';")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "msg_idem_1"
        assert row[1] == "read_file"

        cur = conn.execute("SELECT id, status, risk_tier FROM internal_task_ledger WHERE id='task_idem_1';")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "task_idem_1"
        assert row[1] == "RUNNING"
        assert row[2] == "MEDIUM"
    finally:
        conn.close()


def test_existing_tables_and_data_intact(clean_db):
    """Test 5: Verify that existing tables (facts, turns, rules, etc.) remain intact with data preserved."""
    conn = sqlite3.connect(str(clean_db))
    try:
        # Populate facts
        conn.execute("""
            INSERT INTO facts (category, key, value, updated_at)
            VALUES ('pref', 'theme', 'dark', '2026-11-03T00:00:00Z');
        """)
        # Populate turns
        conn.execute("""
            INSERT INTO turns (session_id, role, content, timestamp)
            VALUES ('sess_test', 'user', 'Hello Zezo', '2026-11-03T00:00:00Z');
        """)
        # Populate user_explicit_rules
        conn.execute("""
            INSERT INTO user_explicit_rules (rule_text, category, created_at)
            VALUES ('Always use python', 'coding', '2026-11-03T00:00:00Z');
        """)
        # Populate memory_conflicts
        conn.execute("""
            INSERT INTO memory_conflicts (existing_content, contradicting_content, source_session_id, detected_at)
            VALUES ('old rule', 'new rule', 'sess_test', '2026-11-03T00:00:00Z');
        """)
        # Populate session_condensations
        conn.execute("""
            INSERT INTO session_condensations (session_id, last_condensed_turn_id, summary, condensed_at)
            VALUES ('sess_test', 1, 'Summary test', '2026-11-03T00:00:00Z');
        """)
        # Populate deleted_fact_tombstones
        conn.execute("""
            INSERT INTO deleted_fact_tombstones (category, key, deleted_at)
            VALUES ('pref', 'old_key', '2026-11-03T00:00:00Z');
        """)
        conn.commit()
    finally:
        conn.close()

    # Run init_agent_runtime_db and init_db again
    sqlite_memory.init_agent_runtime_db()
    sqlite_memory.init_db()

    conn = sqlite3.connect(str(clean_db))
    try:
        assert conn.execute("SELECT value FROM facts WHERE key='theme';").fetchone()[0] == "dark"
        assert conn.execute("SELECT content FROM turns WHERE session_id='sess_test';").fetchone()[0] == "Hello Zezo"
        assert conn.execute("SELECT rule_text FROM user_explicit_rules;").fetchone()[0] == "Always use python"
        assert conn.execute("SELECT contradicting_content FROM memory_conflicts;").fetchone()[0] == "new rule"
        assert conn.execute("SELECT summary FROM session_condensations;").fetchone()[0] == "Summary test"
        assert conn.execute("SELECT key FROM deleted_fact_tombstones;").fetchone()[0] == "old_key"
    finally:
        conn.close()


def test_invocation_modes(clean_db):
    """Test 6: Verify init_agent_runtime_db works with explicit conn, conn=None, and via enqueue_write."""
    # 1. Mode: explicit connection
    direct_conn = sqlite_memory._get_connection()
    try:
        sqlite_memory.init_agent_runtime_db(direct_conn)
    finally:
        direct_conn.close()

    # 2. Mode: default conn=None
    sqlite_memory.init_agent_runtime_db()

    # 3. Mode: enqueued through dedicated single-writer
    res = sqlite_memory.enqueue_write(sqlite_memory.init_agent_runtime_db)
    assert res is None

    # Verify tables still operational
    conn = sqlite_memory._get_connection()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM agent_conversations;")
        assert cur.fetchone()[0] >= 0
    finally:
        conn.close()
