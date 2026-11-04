"""
tests/test_sqlite_concurrency.py - Concurrency, Transaction, and Shutdown Resilience for SQLite Single-Writer.

Tests:
  1. High concurrency stress test: 20 writer threads x 50 writes + 5 concurrent readers.
  2. Transaction rollback: Constraint violation / callable error rolls back cleanly and propagates.
  3. Async request handling & Future cancellation resilience.
  4. Bounded queue backpressure: queue.Full raised when timeout expires on full queue.
  5. Graceful shutdown: drains all enqueued writes, checkpoints WAL, and joins cleanly.
  6. Rejection after shutdown: subsequent writes raise RuntimeError.
"""

import asyncio
import os
import queue
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import pytest
from memory import sqlite_memory


@pytest.fixture(autouse=True)
def clean_db_env(monkeypatch):
    """Fixture providing an isolated temporary database for each test."""
    with tempfile.TemporaryDirectory() as td:
        db_file = Path(td) / "test_brain.db"
        monkeypatch.setattr(sqlite_memory, "DB_PATH", db_file)
        sqlite_memory.reset_db_writer_for_test()
        sqlite_memory.init_db()

        yield db_file

        sqlite_memory.reset_db_writer_for_test()


def test_concurrent_writers_and_readers(clean_db_env):
    """Test 1: 20 writer threads x 50 writes + 5 concurrent readers. Zero deadlocks or lost rows."""
    num_writers = 20
    writes_per_thread = 50
    total_expected = num_writers * writes_per_thread

    errors = []
    stop_readers = threading.Event()

    def _writer_worker(thread_idx: int):
        for i in range(writes_per_thread):
            try:
                sqlite_memory.log_turn(
                    role="user",
                    content=f"Message {i} from thread {thread_idx}",
                    session_id=f"sess_{thread_idx}",
                )
            except Exception as e:
                errors.append(f"Writer error: {e}")

    def _reader_worker():
        while not stop_readers.is_set():
            try:
                _ = sqlite_memory.get_recent_turns(limit=10)
                _ = sqlite_memory.search_scroll_history("Message", limit=5)
                time.sleep(0.005)
            except Exception as e:
                errors.append(f"Reader error: {e}")

    threads = []
    for w in range(num_writers):
        t = threading.Thread(target=_writer_worker, args=(w,))
        threads.append(t)

    reader_threads = []
    for _ in range(5):
        rt = threading.Thread(target=_reader_worker)
        reader_threads.append(rt)

    for rt in reader_threads:
        rt.start()
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=15.0)

    # Wait for queue to drain completely
    timeout = 10.0
    start = time.time()
    while sqlite_memory.get_writer_queue_size() > 0 and (time.time() - start) < timeout:
        time.sleep(0.05)

    stop_readers.set()
    for rt in reader_threads:
        rt.join(timeout=5.0)

    assert not errors, f"Errors encountered during concurrent execution: {errors[:5]}"

    # Verify all records exist in DB via direct count query
    conn = sqlite3.connect(str(clean_db_env))
    try:
        count = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
        assert count == total_expected, f"Expected {total_expected} turns in DB, got {count}"
    finally:
        conn.close()


def test_transaction_rollback_on_failure(clean_db_env):
    """Test 2: Transaction rolls back cleanly on error, preserves integrity, and continues."""
    # Write valid row
    sqlite_memory.record_learn("identity", "name", "ZEZO")
    facts_before = sqlite_memory.get_all_facts()
    assert ("identity", "name") in facts_before

    # Enqueue a failing operation that raises an exception inside transaction
    def _failing_op(conn: sqlite3.Connection):
        conn.execute("INSERT INTO facts (category, key, value, updated_at) VALUES ('test', 'fail_key', 'val', '2026-11-03')")
        raise ValueError("Simulated database failure inside transaction")

    with pytest.raises(ValueError, match="Simulated database failure"):
        sqlite_memory.enqueue_write(_failing_op)

    # Verify state rolled back (fail_key does not exist)
    facts_after = sqlite_memory.get_all_facts()
    assert ("test", "fail_key") not in facts_after
    assert ("identity", "name") in facts_after

    # Verify writer thread is still healthy and subsequent writes succeed
    success = sqlite_memory.record_learn("identity", "creator", "Hamza Bukhari")
    assert success is True
    facts_final = sqlite_memory.get_all_facts()
    assert ("identity", "creator") in facts_final


def test_async_write_and_cancellation_resilience(clean_db_env):
    """Test 3: enqueue_write_async works cleanly and survives caller cancellation."""
    async def _run_async_test():
        # 1. Normal async write
        sql = "INSERT INTO facts (category, key, value, updated_at) VALUES (?, ?, ?, ?)"
        res = await sqlite_memory.enqueue_write_async(sql, ("project", "codename", "zezo_v2", "2026-11-03"))
        assert res is not None

        facts = sqlite_memory.get_all_facts()
        assert ("project", "codename") in facts
        assert facts[("project", "codename")]["value"] == "zezo_v2"

        # 2. Async write cancellation race
        async def _slow_write():
            def _slow_op(conn: sqlite3.Connection):
                time.sleep(0.05)
                conn.execute("INSERT INTO facts (category, key, value, updated_at) VALUES ('async', 'cancelled_key', 'val', '2026-11-03')")
                return 123
            return await sqlite_memory.enqueue_write_async(_slow_op)

        task = asyncio.create_task(_slow_write())
        await asyncio.sleep(0.01)  # Allow it to enqueue
        task.cancel()  # Cancel caller coroutine

        with pytest.raises(asyncio.CancelledError):
            await task

        # Wait for writer to finish committing the operation
        await asyncio.sleep(0.1)

        # The write still safely committed to the DB despite caller cancellation
        facts_post = sqlite_memory.get_all_facts()
        assert ("async", "cancelled_key") in facts_post

        # Verify writer continues working
        res2 = await sqlite_memory.enqueue_write_async(sql, ("project", "status", "active", "2026-11-03"))
        assert res2 is not None

    asyncio.run(_run_async_test())


def test_queue_backpressure_full(clean_db_env, monkeypatch):
    """Test 4: queue.Full is raised when queue is saturated and timeout expires."""
    # Temporarily set maxsize to tiny value for test
    tiny_queue = queue.Queue(maxsize=2)
    monkeypatch.setattr(sqlite_memory, "_write_queue", tiny_queue)

    # Stop writer thread from consuming by acquiring a long operation
    blocker_event = threading.Event()

    def _blocking_task(conn: sqlite3.Connection):
        blocker_event.wait(timeout=2.0)
        return True

    # Put blocker
    sqlite_memory.enqueue_write_nowait(_blocking_task)
    # Fill remaining slots
    sqlite_memory.enqueue_write_nowait("SELECT 1")
    sqlite_memory.enqueue_write_nowait("SELECT 1")

    # Next synchronous write must time out with queue.Full
    with pytest.raises(queue.Full, match="SQLite writer queue full"):
        sqlite_memory.enqueue_write("SELECT 1", timeout=0.2)

    blocker_event.set()


def test_graceful_shutdown_drains_queue(clean_db_env):
    """Test 5: shutdown_db_writer drains all items and closes cleanly."""
    # Enqueue multiple writes
    for i in range(25):
        sqlite_memory.log_turn(role="user", content=f"Drain test {i}", session_id="sess_drain")

    # Trigger shutdown
    sqlite_memory.shutdown_db_writer(timeout=5.0)

    # Verify writer thread stopped
    assert not sqlite_memory.is_writer_alive()

    # Verify all 25 turns were committed to disk
    turns = sqlite_memory.get_recent_turns(limit=50, session_id="sess_drain")
    assert len(turns) == 25


def test_rejection_after_shutdown(clean_db_env):
    """Test 6: Writes submitted after shutdown are rejected with RuntimeError."""
    sqlite_memory.shutdown_db_writer(timeout=5.0)

    with pytest.raises(RuntimeError, match="shutting down"):
        sqlite_memory.enqueue_write("SELECT 1")
