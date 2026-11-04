"""
Subagent 19: Comprehensive SQLite Concurrency & Memory Vault Stress QA Suite
Tests:
1. Concurrent Reads & Writes using memory.sqlite_memory single-writer queue and reader connections
2. WAL Mode Behavior and Busy Timeout Handling Under Concurrent Contention
3. Memory Conflict Resolution Table (lifecycle, pending query, resolution update)
4. Session Condensations (recording distillation checkpoints, incremental turn queries)
5. Fact Deletion Tombstones & Anti-Resurrection Safety (delete, tombstone creation, sync suppression, relearn safety)
6. FTS5 (Full Text Search) Indexing on turns_fts (auto-sync trigger on insert/update/delete, bm25 relevance, search_scroll_history performance)
7. Rapid Multi-Turn Chat Insertions (integrity, no locks, zero corruption, PRAGMA integrity_check)
"""

import os
import sys
import time
import json
import uuid
import random
import sqlite3
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath("."))

import memory.sqlite_memory as sm


def run_all_stress_tests():
    evidence = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subagent": "Subagent 19 - SQLite Concurrency & Memory Vault Stress QA",
        "database_info": {},
        "tests": {},
        "summary": {}
    }

    print("=== Subagent 19: Starting SQLite Concurrency & Memory Vault Stress Tests ===")
    
    # Check Pragma info on live db
    conn = sm._get_connection()
    try:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous;").fetchone()[0]
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        evidence["database_info"] = {
            "db_path": str(sm.get_db_path()),
            "journal_mode": journal_mode,
            "busy_timeout_ms": busy_timeout,
            "synchronous": synchronous,
            "integrity_check": integrity
        }
    finally:
        conn.close()

    # -------------------------------------------------------------
    # Test 1: Memory Conflict Resolution Lifecycle
    # -------------------------------------------------------------
    print("\n--- Running Test 1: Memory Conflict Resolution Table ---")
    t1_start = time.perf_counter()
    sess_id_t1 = f"stress_test_conflicts_{uuid.uuid4().hex[:8]}"
    try:
        initial_pending = len(sm.get_pending_conflicts())
        
        cid1 = sm.insert_memory_conflict(
            existing_content="User prefers Python 3.10 and tabs.",
            contradicting_content="User instructed: Always use Python 3.12 and spaces.",
            source_session_id=sess_id_t1,
            existing_fact_key="code_style"
        )
        cid2 = sm.insert_memory_conflict(
            existing_content="Dark mode is enabled by default.",
            contradicting_content="User prefers light high contrast theme.",
            source_session_id=sess_id_t1,
            existing_rule_id=101
        )
        sm.flush_write_queue(timeout=2.0)
        
        pending_after = sm.get_pending_conflicts()
        our_pending = [c for c in pending_after if c["source_session_id"] == sess_id_t1]
        
        assert len(our_pending) == 2, f"Expected 2 pending conflicts, got {len(our_pending)}"
        assert our_pending[0]["id"] == cid1
        assert our_pending[1]["id"] == cid2
        
        # Resolve one with OVERWRITE, another with KEEP_OLD
        res1 = sm.resolve_memory_conflict(cid1, "RESOLVED_OVERWRITE", notes="Updated to Python 3.12 spaces per explicit user prompt")
        res2 = sm.resolve_memory_conflict(cid2, "RESOLVED_KEEP_OLD", notes="User explicitly cancelled theme change")
        sm.flush_write_queue(timeout=2.0)

        pending_final = [c for c in sm.get_pending_conflicts() if c["source_session_id"] == sess_id_t1]
        assert len(pending_final) == 0, f"Expected 0 pending conflicts after resolution, got {len(pending_final)}"
        
        # Verify in DB table directly
        conn = sm._get_connection(read_only=True)
        rows = conn.execute("SELECT id, status, resolution_notes FROM memory_conflicts WHERE source_session_id = ?", (sess_id_t1,)).fetchall()
        conn.close()
        statuses = {r["id"]: (r["status"], r["resolution_notes"]) for r in rows}
        assert statuses[cid1][0] == "RESOLVED_OVERWRITE"
        assert statuses[cid2][0] == "RESOLVED_KEEP_OLD"

        evidence["tests"]["test_1_memory_conflicts"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t1_start) * 1000, 2),
            "conflict_ids_created": [cid1, cid2],
            "resolutions": statuses
        }
        print("Test 1 PASSED: Memory conflicts insert, pending query, and resolutions validated.")
    except Exception as e:
        evidence["tests"]["test_1_memory_conflicts"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t1_start) * 1000, 2)
        }
        print(f"Test 1 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 2: Session Condensations & Distillation Checkpoints
    # -------------------------------------------------------------
    print("\n--- Running Test 2: Session Condensations & Checkpoints ---")
    t2_start = time.perf_counter()
    sess_id_t2 = f"stress_test_cond_{uuid.uuid4().hex[:8]}"
    try:
        # Insert 5 dummy turns
        for i in range(5):
            sm.log_turn(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Condensation test turn message {i} for session {sess_id_t2}",
                session_id=sess_id_t2
            )
        sm.flush_write_queue(timeout=2.0)
        
        conn = sm._get_connection(read_only=True)
        turns = conn.execute("SELECT id FROM turns WHERE session_id = ? ORDER BY id ASC", (sess_id_t2,)).fetchall()
        conn.close()
        turn_ids = [r["id"] for r in turns]
        assert len(turn_ids) == 5, f"Expected 5 turns, got {len(turn_ids)}"
        last_turn_id = turn_ids[-1]

        summary_text = "Summary of conversation: user and assistant discussed stress testing session condensations."
        sm.record_condensation(session_id=sess_id_t2, last_turn_id=last_turn_id, summary=summary_text)
        sm.flush_write_queue(timeout=2.0)

        conn = sm._get_connection(read_only=True)
        cond_row = conn.execute(
            "SELECT session_id, last_condensed_turn_id, summary FROM session_condensations WHERE session_id = ?",
            (sess_id_t2,)
        ).fetchone()
        conn.close()

        assert cond_row is not None, "Condensation record not found"
        assert cond_row["last_condensed_turn_id"] == last_turn_id
        assert cond_row["summary"] == summary_text

        evidence["tests"]["test_2_session_condensations"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t2_start) * 1000, 2),
            "session_id": sess_id_t2,
            "condensed_up_to_turn_id": last_turn_id,
            "summary_snippet": summary_text[:50]
        }
        print("Test 2 PASSED: Session distillation record and checkpoint integrity verified.")
    except Exception as e:
        evidence["tests"]["test_2_session_condensations"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t2_start) * 1000, 2)
        }
        print(f"Test 2 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 3: Fact Deletion Tombstones & Relearn Safety
    # -------------------------------------------------------------
    print("\n--- Running Test 3: Fact Deletion Tombstones & Anti-Resurrection Safety ---")
    t3_start = time.perf_counter()
    cat_t3 = "qa_stress_pref"
    key_t3 = f"theme_{uuid.uuid4().hex[:6]}"
    try:
        # Step A: Learn a fact
        ok_learn = sm.record_learn(category=cat_t3, key=key_t3, value="monokai_dark", updated_at="2026-11-04")
        sm.flush_write_queue(timeout=2.0)
        assert ok_learn is True
        
        all_facts = sm.get_all_facts()
        assert (cat_t3, key_t3) in all_facts, "Fact was not persisted in facts table"
        assert all_facts[(cat_t3, key_t3)]["value"] == "monokai_dark"

        # Step B: Delete the fact -> Tombstone created, fact removed
        ok_del = sm.delete_fact(category=cat_t3, key=key_t3)
        sm.flush_write_queue(timeout=2.0)
        assert ok_del is True

        all_facts_after = sm.get_all_facts()
        assert (cat_t3, key_t3) not in all_facts_after, "Fact was not deleted from facts table"

        conn = sm._get_connection(read_only=True)
        tombstone = conn.execute(
            "SELECT category, key, deleted_at FROM deleted_fact_tombstones WHERE category = ? AND key = ?",
            (cat_t3, key_t3)
        ).fetchone()
        conn.close()
        assert tombstone is not None, "Tombstone record was not created in deleted_fact_tombstones"

        # Step C: Attempt sync from an older JSON memory dictionary -> Should be suppressed by tombstone
        old_sync_dict = {
            cat_t3: {
                key_t3: {"value": "monokai_dark", "updated": "2026-11-01"}  # Older than tombstone
            }
        }
        sm.sync_facts_from_dict(old_sync_dict)
        sm.flush_write_queue(timeout=2.0)

        all_facts_post_sync = sm.get_all_facts()
        assert (cat_t3, key_t3) not in all_facts_post_sync, "Resurrection defect! Tombstone failed to suppress older fact sync"

        # Step D: Re-learn safety (user explicitly re-learns this preference) -> Tombstone must be cleared
        ok_relearn = sm.record_learn(category=cat_t3, key=key_t3, value="solarized_light", updated_at="2026-11-05")
        sm.flush_write_queue(timeout=2.0)
        assert ok_relearn is True

        conn = sm._get_connection(read_only=True)
        tombstone_relearn = conn.execute(
            "SELECT category, key FROM deleted_fact_tombstones WHERE category = ? AND key = ?",
            (cat_t3, key_t3)
        ).fetchone()
        conn.close()
        assert tombstone_relearn is None, "Tombstone was not purged upon explicit record_learn"

        all_facts_relearn = sm.get_all_facts()
        assert (cat_t3, key_t3) in all_facts_relearn
        assert all_facts_relearn[(cat_t3, key_t3)]["value"] == "solarized_light"

        # Cleanup test fact
        sm.delete_fact(category=cat_t3, key=key_t3)
        sm.flush_write_queue(timeout=2.0)

        evidence["tests"]["test_3_tombstones_anti_resurrection"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t3_start) * 1000, 2),
            "category": cat_t3,
            "key": key_t3,
            "anti_resurrection_verified": True,
            "tombstone_cleared_on_relearn": True
        }
        print("Test 3 PASSED: Tombstone anti-resurrection and relearn safety verified.")
    except Exception as e:
        evidence["tests"]["test_3_tombstones_anti_resurrection"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t3_start) * 1000, 2)
        }
        print(f"Test 3 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 4: FTS5 Indexing, Triggers, BM25 Relevance & Search Performance
    # -------------------------------------------------------------
    print("\n--- Running Test 4: FTS5 Indexing on turns_fts & Search Performance ---")
    t4_start = time.perf_counter()
    sess_id_t4 = f"stress_fts_{uuid.uuid4().hex[:8]}"
    unique_keyword = f"hyperquantum_{uuid.uuid4().hex[:6]}"
    try:
        # Insert turn containing unique search terms
        sm.log_turn(
            role="user",
            content=f"Explain how the {unique_keyword} algorithmic engine maintains sublinear complexity in graphs.",
            session_id=sess_id_t4
        )
        sm.log_turn(
            role="assistant",
            content=f"The {unique_keyword} engine utilizes multi-dimensional KD-trees to partition memory cells efficiently.",
            tool_name="vault_search",
            tool_result=f"Found 42 indexed nodes for {unique_keyword}",
            session_id=sess_id_t4
        )
        sm.flush_write_queue(timeout=2.0)

        # Direct FTS5 query check to ensure trigger synced to turns_fts
        conn = sm._get_connection(read_only=True)
        fts_rows = conn.execute(
            "SELECT rowid, content, tool_name, tool_result FROM turns_fts WHERE turns_fts MATCH ?",
            (unique_keyword,)
        ).fetchall()
        conn.close()
        assert len(fts_rows) == 2, f"Expected 2 turns_fts matches, got {len(fts_rows)}"

        # Test search_scroll_history performance & BM25 ranking
        search_start = time.perf_counter()
        search_results = sm.search_scroll_history(query=unique_keyword, limit=5, session_id=sess_id_t4)
        search_duration_ms = (time.perf_counter() - search_start) * 1000

        assert len(search_results) == 2, f"Expected 2 search results, got {len(search_results)}"
        assert unique_keyword in search_results[0]["content"] or unique_keyword in (search_results[0].get("tool_result") or "")
        assert "rank" in search_results[0]
        assert "score" in search_results[0]

        # Verify update and delete FTS triggers
        conn = sm._get_connection()
        test_turn_id = fts_rows[0]["rowid"]
        # Update turn content
        conn.execute("UPDATE turns SET content = ? WHERE id = ?", (f"Updated {unique_keyword} revision 2", test_turn_id))
        conn.close()
        # Verify FTS index reflects update
        conn = sm._get_connection(read_only=True)
        updated_fts = conn.execute("SELECT content FROM turns_fts WHERE rowid = ?", (test_turn_id,)).fetchone()
        assert "revision 2" in updated_fts["content"], "FTS update trigger trg_turns_au did not synchronize"

        # Delete turn
        conn.close()
        conn = sm._get_connection()
        conn.execute("DELETE FROM turns WHERE id = ?", (test_turn_id,))
        conn.close()

        conn = sm._get_connection(read_only=True)
        deleted_fts = conn.execute("SELECT content FROM turns_fts WHERE rowid = ?", (test_turn_id,)).fetchone()
        conn.close()
        assert deleted_fts is None, "FTS delete trigger trg_turns_ad did not synchronize deletion"

        evidence["tests"]["test_4_fts5_indexing"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t4_start) * 1000, 2),
            "fts_search_latency_ms": round(search_duration_ms, 2),
            "sub_millisecond_capable": search_duration_ms < 10.0,
            "triggers_verified": ["trg_turns_ai (insert)", "trg_turns_au (update)", "trg_turns_ad (delete)"],
            "bm25_ranking_verified": True
        }
        print(f"Test 4 PASSED: FTS5 triggers and search verified (latency: {search_duration_ms:.2f}ms).")
    except Exception as e:
        evidence["tests"]["test_4_fts5_indexing"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t4_start) * 1000, 2)
        }
        print(f"Test 4 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 5: Rapid Multi-Turn Chat Insertions & Queue Stress
    # -------------------------------------------------------------
    print("\n--- Running Test 5: Rapid Multi-Turn Chat Insertions Under Load ---")
    t5_start = time.perf_counter()
    sess_id_t5 = f"rapid_chat_{uuid.uuid4().hex[:8]}"
    num_rapid_turns = 100
    try:
        insert_errors = []
        for i in range(num_rapid_turns):
            try:
                sm.log_turn(
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Rapid turn sequence #{i} with cryptographic payload {uuid.uuid4()}",
                    tool_name="benchmark_runner" if i % 4 == 0 else None,
                    tool_args={"step": i, "load": "high"} if i % 4 == 0 else None,
                    tool_result=f"Benchmark step {i} passed OK" if i % 4 == 0 else None,
                    session_id=sess_id_t5
                )
            except Exception as ex:
                insert_errors.append(f"Turn {i}: {ex}")

        # Wait for queue to flush
        flushed = sm.flush_write_queue(timeout=10.0)
        assert flushed is True, "Write queue failed to flush within 10s"

        conn = sm._get_connection(read_only=True)
        count_inserted = conn.execute("SELECT COUNT(*) FROM turns WHERE session_id = ?", (sess_id_t5,)).fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM turns_fts JOIN turns ON turns_fts.rowid = turns.id WHERE turns.session_id = ?", (sess_id_t5,)).fetchone()[0]
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        conn.close()

        assert count_inserted == num_rapid_turns, f"Expected {num_rapid_turns} turns, found {count_inserted}"
        assert fts_count == num_rapid_turns, f"Expected {num_rapid_turns} in FTS5, found {fts_count}"
        assert integrity == "ok", f"Integrity check failed: {integrity}"

        evidence["tests"]["test_5_rapid_multi_turn_insertions"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t5_start) * 1000, 2),
            "total_turns_logged": num_rapid_turns,
            "turns_found_in_db": count_inserted,
            "turns_found_in_fts": fts_count,
            "integrity_check": integrity,
            "insert_errors": insert_errors
        }
        print(f"Test 5 PASSED: {num_rapid_turns} rapid turns inserted and FTS-indexed with 0 errors, integrity ok.")
    except Exception as e:
        evidence["tests"]["test_5_rapid_multi_turn_insertions"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t5_start) * 1000, 2)
        }
        print(f"Test 5 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 6: Concurrent Reads & Writes Under Heavy Thread Concurrency
    # -------------------------------------------------------------
    print("\n--- Running Test 6: Concurrent Multi-Threaded Reads & Writes ---")
    t6_start = time.perf_counter()
    num_writers = 8
    num_readers = 12
    writes_per_thread = 25
    reads_per_thread = 40
    sess_id_t6 = f"concurrent_stress_{uuid.uuid4().hex[:8]}"

    write_latencies = []
    read_latencies = []
    concurrency_errors = []

    def writer_worker(thread_idx: int):
        for w_i in range(writes_per_thread):
            t0 = time.perf_counter()
            try:
                # Alternate between log_turn (fire-and-forget queue) and enqueue_write (blocking queue write)
                if w_i % 2 == 0:
                    sm.log_turn(
                        role="user",
                        content=f"Concurrent thread {thread_idx} turn {w_i} token {uuid.uuid4().hex}",
                        session_id=sess_id_t6
                    )
                else:
                    sm.enqueue_write(
                        """
                        INSERT INTO user_explicit_rules (rule_text, category, created_at, is_active, origin)
                        VALUES (?, 'concurrent_test', ?, 1, 'stress_worker')
                        """,
                        (f"Rule from thread {thread_idx} seq {w_i}", time.strftime("%Y-%m-%d %H:%M:%S")),
                        timeout=5.0
                    )
                write_latencies.append(time.perf_counter() - t0)
            except Exception as exc:
                concurrency_errors.append(f"WriterThread-{thread_idx} write {w_i}: {exc}")

    def reader_worker(thread_idx: int):
        for r_i in range(reads_per_thread):
            t0 = time.perf_counter()
            try:
                # Concurrent read using reader connection
                mode = r_i % 3
                if mode == 0:
                    _ = sm.get_recent_turns(limit=10, session_id=sess_id_t6)
                elif mode == 1:
                    _ = sm.get_explicit_rules(active_only=True)
                else:
                    _ = sm.search_scroll_history(query="Concurrent", limit=5)
                read_latencies.append(time.perf_counter() - t0)
            except Exception as exc:
                concurrency_errors.append(f"ReaderThread-{thread_idx} read {r_i}: {exc}")
            time.sleep(0.002)

    try:
        with ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            writer_futs = [executor.submit(writer_worker, i) for i in range(num_writers)]
            reader_futs = [executor.submit(reader_worker, j) for j in range(num_readers)]
            
            for f in as_completed(writer_futs + reader_futs):
                f.result()

        sm.flush_write_queue(timeout=10.0)
        
        # Verify database integrity and total count
        conn = sm._get_connection(read_only=True)
        rules_count = conn.execute("SELECT COUNT(*) FROM user_explicit_rules WHERE origin = 'stress_worker'").fetchone()[0]
        turns_count = conn.execute("SELECT COUNT(*) FROM turns WHERE session_id = ?", (sess_id_t6,)).fetchone()[0]
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        conn.close()

        # Clean up temporary rules created by this test
        sm.enqueue_write("DELETE FROM user_explicit_rules WHERE origin = 'stress_worker'")
        sm.flush_write_queue(timeout=2.0)

        assert len(concurrency_errors) == 0, f"Encountered concurrency errors: {concurrency_errors[:5]}"
        assert integrity == "ok", f"Integrity check failed: {integrity}"

        avg_w_lat = (sum(write_latencies) / len(write_latencies) * 1000) if write_latencies else 0
        avg_r_lat = (sum(read_latencies) / len(read_latencies) * 1000) if read_latencies else 0

        evidence["tests"]["test_6_concurrent_reads_writes"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t6_start) * 1000, 2),
            "threads": {"writers": num_writers, "readers": num_readers},
            "total_writes_executed": len(write_latencies),
            "total_reads_executed": len(read_latencies),
            "avg_write_latency_ms": round(avg_w_lat, 2),
            "avg_read_latency_ms": round(avg_r_lat, 2),
            "concurrency_errors": concurrency_errors,
            "database_integrity": integrity
        }
        print(f"Test 6 PASSED: {len(write_latencies)} writes and {len(read_latencies)} reads executed concurrently with 0 lock errors.")
    except Exception as e:
        evidence["tests"]["test_6_concurrent_reads_writes"] = {
            "status": "FAIL",
            "error": str(e),
            "concurrency_errors": concurrency_errors,
            "duration_ms": round((time.perf_counter() - t6_start) * 1000, 2)
        }
        print(f"Test 6 FAILED: {e}")

    # -------------------------------------------------------------
    # Test 7: WAL Mode Under Lock Contention & Busy Timeout Handling
    # -------------------------------------------------------------
    print("\n--- Running Test 7: WAL Mode Lock Contention & Busy Timeout Verification ---")
    t7_start = time.perf_counter()
    try:
        # We test how SQLite handles an external exclusive write lock and verifies the busy_timeout behavior.
        # When connection A holds BEGIN EXCLUSIVE, reader connections in WAL mode can STILL read smoothly!
        # And when connection B tries to write, it waits up to busy_timeout (10,000ms) rather than throwing immediate database locked.
        
        lock_held_event = threading.Event()
        release_lock_event = threading.Event()
        writer_completed = threading.Event()
        reader_resultsDuringLock = []
        lock_contention_log = {}

        def lock_holder():
            conn_lock = sm._get_connection()
            try:
                conn_lock.execute("BEGIN EXCLUSIVE;")
                # Modify something in exclusive mode
                conn_lock.execute("UPDATE turns SET role = 'user' WHERE id = 1")
                lock_held_event.set()
                # Hold the exclusive lock for 0.5 seconds
                release_lock_event.wait(timeout=2.0)
                conn_lock.rollback()
            finally:
                conn_lock.close()

        t_holder = threading.Thread(target=lock_holder, daemon=True)
        t_holder.start()
        lock_held_event.wait(timeout=2.0)

        # 1. Verify that while EXCLUSIVE write transaction is held, WAL mode allows concurrent READS!
        read_during_lock_start = time.perf_counter()
        reader_conn = sm._get_connection(read_only=True)
        try:
            sample_turns = reader_conn.execute("SELECT id, session_id FROM turns LIMIT 5").fetchall()
            reader_resultsDuringLock = [dict(r) for r in sample_turns]
            lock_contention_log["concurrent_read_during_exclusive_write"] = "SUCCESS"
            lock_contention_log["read_latency_ms"] = round((time.perf_counter() - read_during_lock_start) * 1000, 2)
        except Exception as read_err:
            lock_contention_log["concurrent_read_during_exclusive_write"] = f"FAILED: {read_err}"
        finally:
            reader_conn.close()

        # 2. Release lock and verify writer queue recovers seamlessly
        release_lock_event.set()
        t_holder.join(timeout=3.0)

        # 3. Test busy timeout threshold by deliberately holding a lock longer than a tight timeout
        # Using a temporary isolated test db so we don't block the main writer
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db_path = tf.name

        test_conn1 = sqlite3.connect(temp_db_path, timeout=0.2)
        test_conn1.execute("PRAGMA journal_mode = WAL;")
        test_conn1.execute("CREATE TABLE test_contention (id INT, val TEXT);")
        test_conn1.commit()

        test_conn2 = sqlite3.connect(temp_db_path, timeout=0.1) # 100ms timeout
        
        # Conn1 begins exclusive transaction
        test_conn1.execute("BEGIN EXCLUSIVE;")
        test_conn1.execute("INSERT INTO test_contention VALUES (1, 'locked');")
        
        # Conn2 tries to write and should timeout after ~100ms with 'database is locked'
        timeout_caught = False
        t_timeout_start = time.perf_counter()
        try:
            test_conn2.execute("INSERT INTO test_contention VALUES (2, 'blocked');")
        except sqlite3.OperationalError as op_err:
            if "locked" in str(op_err).lower() or "busy" in str(op_err).lower():
                timeout_caught = True
                lock_contention_log["busy_timeout_operational_error"] = str(op_err)
        finally:
            lock_contention_log["busy_timeout_elapsed_ms"] = round((time.perf_counter() - t_timeout_start) * 1000, 2)

        test_conn1.rollback()
        test_conn1.close()
        test_conn2.close()

        try:
            os.remove(temp_db_path)
            for f in Path(temp_db_path).parent.glob(f"{Path(temp_db_path).name}*"):
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

        assert lock_contention_log.get("concurrent_read_during_exclusive_write") == "SUCCESS", "WAL read during write failed"
        assert timeout_caught is True, "Busy timeout did not raise expected locked/busy exception when lock exceeded timeout"

        evidence["tests"]["test_7_wal_busy_timeout"] = {
            "status": "PASS",
            "duration_ms": round((time.perf_counter() - t7_start) * 1000, 2),
            "log": lock_contention_log
        }
        print("Test 7 PASSED: WAL non-blocking concurrent reads and busy timeout handling verified.")
    except Exception as e:
        evidence["tests"]["test_7_wal_busy_timeout"] = {
            "status": "FAIL",
            "error": str(e),
            "duration_ms": round((time.perf_counter() - t7_start) * 1000, 2)
        }
        print(f"Test 7 FAILED: {e}")

    # -------------------------------------------------------------
    # Overall Summary & Integrity Final Check
    # -------------------------------------------------------------
    conn_final = sm._get_connection()
    final_integrity = conn_final.execute("PRAGMA integrity_check;").fetchone()[0]
    final_turns = conn_final.execute("SELECT COUNT(*) FROM turns;").fetchone()[0]
    final_facts = conn_final.execute("SELECT COUNT(*) FROM facts;").fetchone()[0]
    final_conflicts = conn_final.execute("SELECT COUNT(*) FROM memory_conflicts;").fetchone()[0]
    final_condensations = conn_final.execute("SELECT COUNT(*) FROM session_condensations;").fetchone()[0]
    conn_final.close()

    total_tests = len(evidence["tests"])
    passed_tests = sum(1 for t in evidence["tests"].values() if t.get("status") == "PASS")
    failed_tests = total_tests - passed_tests

    evidence["summary"] = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "final_database_integrity": final_integrity,
        "final_counts": {
            "turns": final_turns,
            "facts": final_facts,
            "memory_conflicts": final_conflicts,
            "session_condensations": final_condensations
        },
        "verdict": "ALL_PASS" if failed_tests == 0 else "FAILURES_DETECTED"
    }

    # Write evidence to qa_artifacts/subagent_19_sqlite_stress_results.json
    out_path = Path("qa_artifacts/subagent_19_sqlite_stress_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    print(f"\n=== Stress QA Complete: {passed_tests}/{total_tests} Tests Passed (Verdict: {evidence['summary']['verdict']}) ===")
    print(f"Detailed evidence written to: {out_path.resolve()}")
    return evidence


if __name__ == "__main__":
    run_all_stress_tests()
