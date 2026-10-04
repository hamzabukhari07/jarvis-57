"""
tests/test_phase5_composite_session_and_memory_recall_suite.py
Verification suite for Phase 5: Composite Session Isolation & Deep Memory Recall.
Tests:
1. Composite session ID generation format (<agent_id>:<session_uuid>).
2. Turns isolation by composite session ID in SQLite memory.
3. expand_turns retrieves contiguous turn sequences across [lo, hi] range accurately.
4. actions/recall_history.py handles op="search" and op="expand" properly.
5. memory/memory_condenser.py handles uncondensed turn compaction without schema errors.
"""

import pytest
from memory import sqlite_memory
from memory import memory_condenser
from actions.recall_history import handler as recall_history_handler


def test_composite_session_id_generation():
    sess_id = sqlite_memory.generate_composite_session_id("ALI")
    assert sess_id.startswith("ALI:sess_")
    parts = sess_id.split(":")
    assert len(parts) == 2
    assert parts[0] == "ALI"


def test_turn_logging_and_expand_turns():
    sqlite_memory.init_db()
    sess_ali = sqlite_memory.generate_composite_session_id("ALI", "uuid_test_1")
    sess_ahmad = sqlite_memory.generate_composite_session_id("AHMAD", "uuid_test_2")

    # Log sequential turns synchronously for test inspection
    conn = sqlite_memory._get_connection()
    with conn:
        c1 = conn.execute(
            "INSERT INTO turns (session_id, role, content, tool_name, tool_args, tool_result, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sess_ali, "user", "Phase 5 Test Turn 1 - Ali Landing Page", None, None, None, "2026-10-04 12:00:01")
        )
        t1_id = c1.lastrowid

        c2 = conn.execute(
            "INSERT INTO turns (session_id, role, content, tool_name, tool_args, tool_result, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sess_ali, "assistant", "Phase 5 Test Turn 2 - Building HTML/CSS Hero", "antigravity_run", '{"task": "hero"}', "Hero built.", "2026-10-04 12:00:02")
        )
        t2_id = c2.lastrowid

        c3 = conn.execute(
            "INSERT INTO turns (session_id, role, content, tool_name, tool_args, tool_result, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sess_ahmad, "user", "Phase 5 Test Turn 3 - Ahmad Backend API", None, None, None, "2026-10-04 12:00:03")
        )
        t3_id = c3.lastrowid
    conn.close()

    # Expand turns across [t1_id, t3_id]
    all_expanded = sqlite_memory.expand_turns(t1_id, t3_id)
    assert len(all_expanded) == 3
    ids = [t["id"] for t in all_expanded]
    assert ids == [t1_id, t2_id, t3_id]

    # Expand scoped to Ali session
    ali_expanded = sqlite_memory.expand_turns(t1_id, t3_id, session_id=sess_ali)
    assert len(ali_expanded) == 2
    assert all(t["session_id"] == sess_ali for t in ali_expanded)


def test_recall_history_action_search_and_expand():
    # Test op="search"
    search_res = recall_history_handler({
        "op": "search",
        "query": "Landing Page"
    })
    assert "Found" in search_res
    assert "Ali Landing Page" in search_res or "Turn" in search_res

    # Test op="expand"
    turns = sqlite_memory.get_uncondensed_turns(limit=5)
    if turns:
        lo = turns[0]["id"]
        hi = turns[-1]["id"]
        expand_res = recall_history_handler({
            "op": "expand",
            "lo": lo,
            "hi": hi
        })
        assert f"Expanded {len(turns)} turns" in expand_res


def test_memory_condenser_compaction():
    # Test compaction logic without LLM to verify SQL and table schema integrity
    res = memory_condenser.condense_recent_turns(max_turns=50, use_llm=False)
    assert res["status"] in ("SUCCESS", "NO_NEW_TURNS")
    if res["status"] == "SUCCESS":
        assert res["condensed_count"] > 0
        assert "last_turn_id" in res
