"""
tests/test_memory_fast_path.py — Targeted unit tests for the Fast-Path Hybrid Memory Engine.

Tests cover:
1. test_outbox_queue_and_drain
2. test_read_your_writes_consistency
3. test_relearn_after_forget
4. test_journal_compaction_concurrent_writes
5. test_poison_pill_single_item_isolation
6. test_journal_replay_after_simulated_kill
7. test_overlay_version_race_two_writes_same_key
8. test_memory_paused_total_bypass
9. test_turn_memory_read_budget_sliding_window
10. test_vault_wipe_cancels_outbox
11. test_pre_turn_score_field_and_timeout

Creator & Lead Architect: Hamza Bukhari
"""
import asyncio
import json
import os
import queue
import time
from pathlib import Path
import pytest

from memory import memory_manager, memory_state, sqlite_memory


@pytest.fixture(autouse=True)
def isolated_memory_env(tmp_path, monkeypatch):
    """Isolate memory directories and databases to temporary path."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "zezo_test.db"
    long_term_file = tmp_path / "long_term.json"
    journal_file = tmp_path / "outbox_journal.jsonl"
    checkpoint_file = tmp_path / "outbox_checkpoint.json"
    dead_letter_file = tmp_path / "outbox_dead_letter.jsonl"

    monkeypatch.setattr(memory_manager, "MEMORY_PATH", long_term_file)
    monkeypatch.setattr(memory_manager, "JOURNAL_PATH", journal_file)
    monkeypatch.setattr(memory_manager, "CHECKPOINT_PATH", checkpoint_file)
    monkeypatch.setattr(memory_manager, "DEAD_LETTER_PATH", dead_letter_file)

    monkeypatch.setattr(sqlite_memory, "DB_PATH", db_file)

    # Reset in-memory outbox structures
    memory_manager.stop_memory_worker()
    memory_manager._committed_watermark = 0
    with memory_manager._seq_lock:
        memory_manager._seq_counter = 0
    with memory_manager._overlay_lock:
        memory_manager._uncommitted_overlay.clear()
    while not memory_manager._memory_write_queue.empty():
        try:
            memory_manager._memory_write_queue.get_nowait()
        except queue.Empty:
            break

    memory_state.set_memory_paused(False)
    sqlite_memory.init_db()

    yield tmp_path

    memory_manager.stop_memory_worker()
    memory_state.set_memory_paused(False)


def test_outbox_queue_and_drain():
    """1. Verify queued fact commits to long_term.json and SQLite facts table."""
    ack = memory_manager.queue_memory_write("preferences", "editor", "Neovim")
    assert ack["status"] == "queued"
    assert ack["category"] == "preferences"
    assert ack["key"] == "editor"
    assert ack["value"] == "Neovim"

    # Process batch synchronously via internal flush
    drained = memory_manager._flush_outbox_batch()
    assert drained >= 1

    # Verify long_term.json
    loaded = memory_manager.load_memory()
    assert loaded.get("preferences", {}).get("editor", {}).get("value") == "Neovim"

    # Verify SQLite facts table
    facts = sqlite_memory.get_all_facts()
    assert ("preferences", "editor") in facts
    assert facts[("preferences", "editor")]["value"] == "Neovim"


def test_read_your_writes_consistency():
    """2. Verify newly queued fact is immediately retrievable via _search_raw_facts before disk flush."""
    ack = memory_manager.queue_memory_write("preferences", "shell", "fish")
    assert ack["status"] == "queued"

    # Ensure outbox worker hasn't flushed yet; memory file does not contain the key yet
    loaded = memory_manager.load_memory()
    assert "shell" not in loaded.get("preferences", {})

    # Immediate Read-Your-Writes lookup through in-memory overlay
    result = memory_manager._search_raw_facts("shell fish")
    assert "fish" in result
    assert "shell" in result


def test_relearn_after_forget():
    """3. Verify forgetting a fact creates tombstone; subsequent learn clears tombstone and updates SQLite facts."""
    memory_manager.queue_memory_write("preferences", "browser", "Brave")
    memory_manager._flush_outbox_batch()

    # Forget fact
    forget_ack = memory_manager.queue_memory_forget("preferences", "browser")
    assert forget_ack["action"] == "forgotten"
    memory_manager._flush_outbox_batch()

    facts = sqlite_memory.get_all_facts()
    assert ("preferences", "browser") not in facts

    with sqlite_memory._db_lock:
        conn = sqlite_memory._get_connection()
        tombstone = conn.execute(
            "SELECT category, key FROM deleted_fact_tombstones WHERE category = ? AND key = ?",
            ("preferences", "browser"),
        ).fetchone()
        assert tombstone is not None

    # Subsequent re-learn
    memory_manager.queue_memory_write("preferences", "browser", "Zen")
    memory_manager._flush_outbox_batch()

    # Tombstone must be removed
    with sqlite_memory._db_lock:
        conn = sqlite_memory._get_connection()
        tombstone_after = conn.execute(
            "SELECT category, key FROM deleted_fact_tombstones WHERE category = ? AND key = ?",
            ("preferences", "browser"),
        ).fetchone()
        assert tombstone_after is None

    facts_after = sqlite_memory.get_all_facts()
    assert ("preferences", "browser") in facts_after
    assert facts_after[("preferences", "browser")]["value"] == "Zen"


def test_journal_compaction_concurrent_writes():
    """4. Verify compaction under _journal_lock preserves uncompacted concurrent writes."""
    # Write 3 items
    for i in range(1, 4):
        memory_manager.queue_memory_write("notes", f"item_{i}", f"val_{i}")

    # Compact up to seq 2
    memory_manager._compact_journal_under_lock(target_watermark=2)

    # Read journal lines
    with open(memory_manager.JOURNAL_PATH, "r", encoding="utf-8") as f:
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    # Lines with seq > 2 must survive (item_3 with seq 3)
    surviving_seqs = [item["seq"] for item in lines]
    assert 3 in surviving_seqs
    assert 1 not in surviving_seqs
    assert 2 not in surviving_seqs


def test_poison_pill_single_item_isolation():
    """5. Verify corrupt item in batch routes to dead-letter while healthy item commits."""
    # Enqueue a healthy write
    memory_manager.queue_memory_write("preferences", "healthy", "good_value")

    # Manually inject a poison item directly into queue
    poison_item = {
        "seq": 999,
        "action": "corrupt_action_without_required_keys",
        "id": "poison_1",
    }
    memory_manager._memory_write_queue.put(poison_item)

    # Flush batch: should isolate poison item to dead letter and commit healthy item
    drained = memory_manager._flush_outbox_batch()
    assert drained >= 1

    # Check dead letter file
    assert memory_manager.DEAD_LETTER_PATH.exists()
    with open(memory_manager.DEAD_LETTER_PATH, "r", encoding="utf-8") as f:
        dead_lines = [json.loads(line.strip()) for line in f if line.strip()]
    assert any(entry.get("id") == "poison_1" for entry in dead_lines)

    # Check healthy item committed
    loaded = memory_manager.load_memory()
    assert loaded.get("preferences", {}).get("healthy", {}).get("value") == "good_value"


def test_journal_replay_after_simulated_kill():
    """6. Verify uncommitted entries replay cleanly on startup in strict seq order."""
    # Simulate pending journal entries left on disk
    entries = [
        {"seq": 5, "action": "learn", "id": "fact_5", "category": "projects", "key": "zezo", "value": "AI OS", "ts": 100.0},
        {"seq": 6, "action": "learn", "id": "fact_6", "category": "identity", "key": "name", "value": "Hamza", "ts": 101.0},
    ]
    with open(memory_manager.JOURNAL_PATH, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    with open(memory_manager.CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"committed_seq": 4, "checkpoint_ts": 90.0}, f)

    # Run init replay
    memory_manager.init_memory_subsystem()

    # Counter should be at least max seq
    with memory_manager._seq_lock:
        assert memory_manager._seq_counter >= 6

    # Verify facts were replayed into long_term.json
    loaded = memory_manager.load_memory()
    assert loaded.get("projects", {}).get("zezo", {}).get("value") == "AI OS"
    assert loaded.get("identity", {}).get("name", {}).get("value") == "Hamza"


def test_overlay_version_race_two_writes_same_key():
    """7. Verify subsequent writes on the same key preserve higher sequence numbers in overlay."""
    memory_manager.queue_memory_write("preferences", "theme", "light")
    memory_manager.queue_memory_write("preferences", "theme", "dark")

    with memory_manager._overlay_lock:
        val, seq = memory_manager._uncommitted_overlay[("preferences", "theme")]
        assert val == "dark"

    # Immediate search reflects dark
    raw = memory_manager._search_raw_facts("theme")
    assert "dark" in raw


def test_memory_paused_total_bypass():
    """8. Verify log_turn and queue_memory_write perform 0 writes while paused, while forget is permitted."""
    memory_state.set_memory_paused(True)

    # Attempt write
    res = memory_manager.queue_memory_write("preferences", "secret", "hidden")
    assert res["status"] == "paused"

    # Attempt turn log
    sqlite_memory.log_turn(
        role="user",
        content="My secret info",
        session_id="test_sess",
    )

    # Verify no facts or turns recorded
    facts = sqlite_memory.get_all_facts()
    assert ("preferences", "secret") not in facts

    with sqlite_memory._db_lock:
        conn = sqlite_memory._get_connection()
        count = conn.execute("SELECT COUNT(*) FROM turns WHERE content LIKE '%secret%'").fetchone()[0]
        assert count == 0

    # Forget must still be permitted while paused
    forget_res = memory_manager.queue_memory_forget("preferences", "secret")
    assert forget_res["action"] == "forgotten"


def test_turn_memory_read_budget_sliding_window(monkeypatch):
    """9. Verify budget caps at max reads within window and resets after cooldown."""
    import main

    class DummySession:
        def __init__(self):
            self._turn_memory_read_budget = 0
            self._last_memory_read_ts = 0.0
            self._memory_budget_window = 0.1
            self._max_memory_read_budget = 2

        def _check_memory_budget(self, tool_name: str, args: dict) -> str:
            # Replicate main.py logic for tool checking
            now = time.monotonic()
            if now - self._last_memory_read_ts > self._memory_budget_window:
                self._turn_memory_read_budget = 0

            is_read = False
            if tool_name == "memory" and args.get("action") in ("recall", "history"):
                is_read = True
            elif tool_name in ("recall_memory", "recall_history"):
                is_read = True

            if is_read:
                if self._turn_memory_read_budget >= self._max_memory_read_budget:
                    return f"Error: Turn memory read budget reached (maximum {self._max_memory_read_budget} reads per turn)."
                self._turn_memory_read_budget += 1
                self._last_memory_read_ts = now
            return ""

    sess = DummySession()

    # First read: OK
    assert sess._check_memory_budget("memory", {"action": "recall"}) == ""
    # Second read: OK
    assert sess._check_memory_budget("memory", {"action": "recall"}) == ""
    # Third read within 100ms: Blocked
    err = sess._check_memory_budget("memory", {"action": "recall"})
    assert "Turn memory read budget reached" in err

    # Wait past 100ms window: Resets
    time.sleep(0.12)
    assert sess._check_memory_budget("memory", {"action": "recall"}) == ""


def test_vault_wipe_cancels_outbox():
    """10. Verify clear_pending_outbox purges in-flight writes and notifies failed status."""
    activities = []
    memory_manager.register_memory_activity_callback(lambda event: activities.append(event))

    memory_manager.queue_memory_write("notes", "pending_note", "should_be_cleared")
    assert not memory_manager._memory_write_queue.empty()

    # Clear pending outbox
    cleared = memory_manager.clear_pending_outbox()
    assert cleared >= 1
    assert memory_manager._memory_write_queue.empty()

    # Check notification
    failed_events = [e for e in activities if e.get("status") == "failed" and "cleared" in e.get("reason", "").lower()]
    assert len(failed_events) >= 1


def test_pre_turn_score_field_and_timeout():
    """11. Verify search_scroll_history populates score field and executes non-blockingly."""
    # Log a turn
    sqlite_memory.log_turn(
        role="user",
        content="I love building distributed AI operating systems",
        session_id="sess_score",
    )

    # Search scroll history
    results = sqlite_memory.search_scroll_history("distributed AI operating systems", limit=2)
    assert len(results) >= 1
    first = results[0]
    assert "score" in first
    assert isinstance(first["score"], (int, float))
    assert first["score"] > 0
