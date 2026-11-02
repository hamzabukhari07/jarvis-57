import json
import os
import queue
import re
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock, RLock
from typing import Callable, Optional

from memory.memory_state import is_memory_paused


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
_env_mem         = os.environ.get("ZEZO_MEMORY_PATH")
MEMORY_PATH      = Path(_env_mem) if _env_mem else BASE_DIR / "memory" / "long_term.json"
JOURNAL_PATH     = MEMORY_PATH.parent / "outbox_journal.jsonl"
CHECKPOINT_PATH  = MEMORY_PATH.parent / "outbox_checkpoint.json"
DEAD_LETTER_PATH = MEMORY_PATH.parent / "outbox_dead_letter.jsonl"
_lock            = RLock()
MAX_VALUE_LENGTH = 380

# ── Outbox & Write-Ahead Journal State ─────────────────────────────────────────
_seq_counter: int = 0
_seq_lock = threading.Lock()
_journal_lock = threading.Lock()
_memory_write_queue: queue.Queue = queue.Queue(maxsize=256)
_uncommitted_overlay: dict[tuple[str, str], tuple[Optional[str], int]] = {}
_overlay_lock = threading.Lock()
_worker_stop_event = threading.Event()
_worker_thread: Optional[threading.Thread] = None
_worker_lock = threading.Lock()
_committed_watermark: int = 0
_activity_callbacks: list[Callable[[dict], None]] = []
_activity_lock = threading.Lock()


# ── Why there are two very different numbers here ────────────────────────────
#
# There used to be one: MEMORY_MAX_CHARS = 2200, applied to the whole store. It
# was a *storage* limit, and it existed only because the entire memory was
# pasted into the system prompt on every connect — so growing the memory grew
# every single request. When it filled, _trim_to_limit() deleted the oldest
# entries and printed one line to a console nobody reads. A memory described as
# "deeply remembers projects, preferences and personal context" was in practice
# two pages long, and quietly forgot your sister's name after a few weeks.
#
# Storage and prompt budget are now separate concerns:
#
#   MEMORY_MAX_CHARS  — a runaway guard, not a feature limit. Nothing normal
#                       reaches it; a bug writing in a loop does.
#   PROMPT_CORE_CHARS — what actually rides in the system prompt every session.
#                       Smaller than the old whole-memory dump, so sessions
#                       start *faster* than before, not slower.
#
# Everything above the core stays on disk and is fetched on demand by the
# recall_memory tool — see search_memory() and format_memory_for_prompt().
MEMORY_MAX_CHARS  = 200_000
PROMPT_CORE_CHARS = 900
PROMPT_INDEX_CHARS = 420
# Most entries any one category may contribute to the core block, so a person
# with forty stored preferences still gets their sister into the prompt.
PROMPT_MAX_PER_CATEGORY = 6

def _empty_memory() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {},
    }

def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        bak = MEMORY_PATH.with_suffix(".json.bak")
        if bak.exists() and bak.stat().st_size > 0:
            try:
                shutil.copy2(bak, MEMORY_PATH)
                print(f"[Memory] 🔄 Restored missing memory file from backup replica.")
            except Exception:
                pass
        else:
            return _empty_memory()

    with _lock:
        try:
            if MEMORY_PATH.exists() and MEMORY_PATH.stat().st_size == 0:
                bak = MEMORY_PATH.with_suffix(".json.bak")
                if bak.exists() and bak.stat().st_size > 0:
                    shutil.copy2(bak, MEMORY_PATH)
                    print(f"[Memory] 🔄 Auto-restored 0-byte memory from backup replica ({bak.stat().st_size} bytes).")
                else:
                    return _empty_memory()
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()

def _all_entries(memory: dict) -> list[tuple]:
    entries = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append((cat, key, entry))
    return entries


# Set by main.py so a trim can reach the activity log. Deleting something a
# person told you and mentioning it only on stdout is how a memory loses trust.
_trim_notifier = None


def set_trim_notifier(fn) -> None:
    """Register a callable(str) that surfaces trims to the user."""
    global _trim_notifier
    _trim_notifier = fn


def _trim_to_limit(memory: dict) -> dict:
    if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory
    entries = _all_entries(memory)
    entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
    dropped = []
    for cat, key, _ in entries:
        if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory[cat][key]
        dropped.append(f"{cat}/{key}")
        print(f"[Memory] 🗑️  Trimmed {cat}/{key}")
    if dropped and _trim_notifier:
        try:
            _trim_notifier(
                f"SYS: Memory full — forgot {len(dropped)} oldest entries "
                f"({', '.join(dropped[:3])}{'…' if len(dropped) > 3 else ''})"
            )
        except Exception:
            pass
    return memory

def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    memory = _trim_to_limit(memory)
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(memory, indent=2, ensure_ascii=False)
    if not serialized or len(serialized.strip()) < 2:
        return
    tmp_path = MEMORY_PATH.with_suffix(f".tmp.{os.getpid()}_{time.time_ns()}")
    with _lock:
        try:
            tmp_path.write_text(serialized, encoding="utf-8")
            if tmp_path.exists() and tmp_path.stat().st_size > 0:
                replaced = False
                for attempt in range(5):
                    try:
                        os.replace(tmp_path, MEMORY_PATH)
                        replaced = True
                        break
                    except (PermissionError, OSError):
                        time.sleep(0.04 * (attempt + 1))
                if replaced:
                    try:
                        shutil.copy2(MEMORY_PATH, MEMORY_PATH.with_suffix(".json.bak"))
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Memory] ⚠️ save_memory error: {e}")
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
    try:
        from memory import sqlite_memory
        sqlite_memory.sync_facts_from_dict(memory)
    except Exception:
        pass


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict) -> bool:
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            new_val  = _truncate_value(str(value["value"] if isinstance(value, dict) else value))
            entry    = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True
    return changed


def update_memory_entry(category: str, key: str, value: str) -> None:
    """Helper to update or create a single memory fact entry by category and key."""
    if not category or not key or value is None:
        return
    update_memory({category: {key: value}})


def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()
    with _lock:
        memory = load_memory()
        if _recursive_update(memory, memory_update):
            save_memory(memory)
            print(f"[Memory] 💾 Saved: {list(memory_update.keys())}")
        return memory


# ── Outbox Engine & Asynchronous Durability ────────────────────────────────────

def register_memory_activity_callback(callback: Callable[[dict], None]) -> None:
    """Register a callback for memory activity notifications (e.g. for UI server WebSocket broadcast)."""
    with _activity_lock:
        if callback not in _activity_callbacks:
            _activity_callbacks.append(callback)


def _broadcast_activity(data: dict) -> None:
    with _activity_lock:
        callbacks = list(_activity_callbacks)
    for cb in callbacks:
        try:
            cb(data)
        except Exception as e:
            print(f"[Memory Outbox] ⚠️ Callback exception: {e}")


def delete_memory_fact(category: str, key: str) -> bool:
    """Directly remove a fact from long_term.json and SQLite facts table."""
    with _lock:
        memory = load_memory()
        if category in memory and isinstance(memory[category], dict):
            if key in memory[category]:
                del memory[category][key]
                save_memory(memory)
    try:
        from memory import sqlite_memory
        sqlite_memory.delete_fact(category, key)
    except Exception:
        pass
    return True


def _compact_journal_under_lock(target_watermark: int) -> None:
    """Filter out committed entries with seq <= target_watermark under _journal_lock mutex."""
    with _journal_lock:
        if not JOURNAL_PATH.exists():
            return
        tmp_path = JOURNAL_PATH.with_suffix(f".tmp.{os.getpid()}_{time.time_ns()}")
        try:
            with open(JOURNAL_PATH, "r", encoding="utf-8") as src, \
                 open(tmp_path, "w", encoding="utf-8") as dst:
                for line in src:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        entry = json.loads(line_str)
                        if entry.get("seq", 0) > target_watermark:
                            dst.write(line_str + "\n")
                    except Exception:
                        pass
            os.replace(tmp_path, JOURNAL_PATH)
        except Exception as e:
            print(f"[Memory Outbox] ⚠️ Journal compaction error: {e}")
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


def _commit_single_item(entry: dict) -> None:
    action = entry.get("action", "learn")
    cat = entry.get("category", "notes")
    key = entry.get("key", "")
    if action == "learn":
        val = entry.get("value", "")
        update_memory({cat: {key: {"value": val}}})
        try:
            from memory import sqlite_memory
            sqlite_memory.record_learn(cat, key, val)
        except Exception:
            pass
    elif action == "forget":
        delete_memory_fact(cat, key)
    else:
        raise ValueError(f"Unknown outbox action: {action}")


def _route_to_dead_letter(entry: dict, error: str) -> None:
    entry_record = dict(entry)
    entry_record["failed_at"] = time.time()
    entry_record["error"] = error
    try:
        DEAD_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEAD_LETTER_PATH, "a", encoding="utf-8") as dl:
            dl.write(json.dumps(entry_record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Memory Outbox] ⚠️ Failed writing dead letter: {e}")
    # Evict corrupt item from uncommitted overlay
    cat = entry.get("category", "")
    key = entry.get("key", "")
    with _overlay_lock:
        _uncommitted_overlay.pop((cat, key), None)
    _broadcast_activity({
        "status": "failed",
        "id": entry.get("id"),
        "category": cat,
        "key": key,
        "value": entry.get("value", ""),
        "reason": f"Dead-lettered: {error}",
    })


def _process_outbox_batch(batch: list[dict]) -> None:
    if not batch:
        return

    # Attempt batch commit with 3 retries (50ms, 150ms, 450ms)
    batch_success = False
    for attempt in range(3):
        try:
            learn_updates: dict = {}
            for item in batch:
                action = item.get("action")
                if action == "learn":
                    cat = item.get("category", "notes")
                    k = item.get("key", "")
                    v = item.get("value", "")
                    if k:
                        learn_updates.setdefault(cat, {})[k] = {"value": v}
                elif action == "forget":
                    delete_memory_fact(item.get("category", "notes"), item.get("key", ""))
                else:
                    raise ValueError(f"Invalid batch action: {action}")
            if learn_updates:
                update_memory(learn_updates)
                try:
                    from memory import sqlite_memory
                    for cat, keys in learn_updates.items():
                        for k, vdict in keys.items():
                            sqlite_memory.record_learn(cat, k, vdict.get("value", ""))
                except Exception:
                    pass
            batch_success = True
            break
        except Exception as batch_err:
            if attempt < 2:
                time.sleep(0.05 * (3 ** attempt))
            else:
                print(f"[Memory Outbox] ⚠️ Batch commit failed 3 times: {batch_err}. Unpacking batch for single-item isolation.")

    if batch_success:
        target_watermark = max(e.get("seq", 0) for e in batch)
        # 1. Compact journal under mutex lock
        _compact_journal_under_lock(target_watermark)
        # 2. Advance committed watermark
        global _committed_watermark
        _committed_watermark = max(_committed_watermark, target_watermark)
        # 3. Persist checkpoint ledger
        try:
            CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            CHECKPOINT_PATH.write_text(
                json.dumps({"committed_seq": _committed_watermark, "checkpoint_ts": time.time()}),
                encoding="utf-8",
            )
        except Exception as cp_err:
            print(f"[Memory Outbox] ⚠️ Checkpoint write error: {cp_err}")
        # 4. Evict stale committed entries from in-memory overlay
        with _overlay_lock:
            stale_keys = [k for k, (val, seq) in _uncommitted_overlay.items() if seq <= _committed_watermark]
            for k in stale_keys:
                del _uncommitted_overlay[k]
        # 5. Broadcast success for all items
        for item in batch:
            _broadcast_activity({
                "status": "persisted",
                "action": "learned" if item.get("action") == "learn" else "forgotten",
                "id": item.get("id"),
                "category": item.get("category"),
                "key": item.get("key"),
                "value": item.get("value", ""),
            })
    else:
        # Poison-pill single-item isolation
        for item in batch:
            try:
                _commit_single_item(item)
                item_seq = item.get("seq", 0)
                _compact_journal_under_lock(item_seq)
                _committed_watermark = max(_committed_watermark, item_seq)
                with _overlay_lock:
                    stale_keys = [k for k, (val, seq) in _uncommitted_overlay.items() if seq <= _committed_watermark]
                    for k in stale_keys:
                        del _uncommitted_overlay[k]
                _broadcast_activity({
                    "status": "persisted",
                    "action": "learned" if item.get("action") == "learn" else "forgotten",
                    "id": item.get("id"),
                    "category": item.get("category"),
                    "key": item.get("key"),
                    "value": item.get("value", ""),
                })
            except Exception as single_err:
                _route_to_dead_letter(item, str(single_err))


def _worker_loop() -> None:
    while not _worker_stop_event.is_set():
        batch = []
        try:
            while len(batch) < 32:
                try:
                    item = _memory_write_queue.get_nowait()
                    batch.append(item)
                except queue.Empty:
                    break
            if batch:
                _process_outbox_batch(batch)
        except Exception as e:
            print(f"[Memory Outbox Worker] ⚠️ Unexpected error: {e}")
        _worker_stop_event.wait(1.5)


def _flush_outbox_batch() -> int:
    """Synchronously drain and process queued outbox items. Useful for testing and immediate flush."""
    batch = []
    while not _memory_write_queue.empty():
        try:
            batch.append(_memory_write_queue.get_nowait())
        except queue.Empty:
            break
    if batch:
        _process_outbox_batch(batch)
    return len(batch)


def _start_worker_if_needed() -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_stop_event.clear()
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="ZezoMemoryOutboxWorker")
            _worker_thread.start()


def stop_memory_worker() -> None:
    """Signal background worker to stop (used for test teardown / graceful shutdown)."""
    _worker_stop_event.set()
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            _worker_thread.join(timeout=2.0)
            _worker_thread = None


def init_memory_subsystem() -> None:
    """Initialize outbox sequence, replay uncommitted journal entries, and start background worker."""
    global _seq_counter, _committed_watermark
    committed_seq = 0
    if CHECKPOINT_PATH.exists():
        try:
            cp = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
            committed_seq = int(cp.get("committed_seq", 0))
        except Exception:
            committed_seq = 0

    entries = []
    if JOURNAL_PATH.exists():
        try:
            with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        try:
                            entries.append(json.loads(line_str))
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Memory Outbox] ⚠️ Journal read error on startup: {e}")

    with _seq_lock:
        max_journal_seq = max([e.get("seq", 0) for e in entries] + [committed_seq], default=0)
        _seq_counter = max_journal_seq
        _committed_watermark = committed_seq

    uncommitted = [e for e in entries if e.get("seq", 0) > committed_seq]
    if uncommitted:
        uncommitted.sort(key=lambda e: e.get("seq", 0))
        print(f"[Memory Outbox] 🔄 Replaying {len(uncommitted)} uncommitted outbox entries...")
        for entry in uncommitted:
            try:
                _commit_single_item(entry)
            except Exception as e:
                print(f"[Memory Outbox] ⚠️ Replay failed for seq {entry.get('seq')}: {e}")
        _committed_watermark = max([e.get("seq", 0) for e in uncommitted] + [_committed_watermark])
        try:
            CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            CHECKPOINT_PATH.write_text(
                json.dumps({"committed_seq": _committed_watermark, "checkpoint_ts": time.time()}),
                encoding="utf-8",
            )
            _compact_journal_under_lock(_committed_watermark)
        except Exception:
            pass

    _start_worker_if_needed()


def queue_memory_write(category: str, key: str, value: str) -> dict:
    """Fast-path ingestion: enqueues memory write and appends to journal (<1ms)."""
    if is_memory_paused():
        return {"status": "paused", "message": "Memory is paused. Fact was not stored."}

    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"

    key = str(key or "").strip()
    value = _truncate_value(str(value or "").strip())
    if not key or not value:
        return {"status": "error", "message": "Key and value are required."}

    # Rollout feature flag check
    if os.environ.get("ZEZO_MEMORY_ASYNC_OUTBOX", "true").lower() == "false":
        update_memory({category: {key: {"value": value}}})
        return {"status": "persisted", "category": category, "key": key, "value": value}

    # Fetch previous value for reversible undo
    prev_val = None
    with _overlay_lock:
        if (category, key) in _uncommitted_overlay:
            prev_val = _uncommitted_overlay[(category, key)][0]
    if prev_val is None:
        current_mem = load_memory()
        prev_val = _entry_value(current_mem.get(category, {}).get(key, "")) or None

    with _seq_lock:
        global _seq_counter
        _seq_counter += 1
        seq = _seq_counter

    fact_id = f"fact_{category}_{key}_{seq}_{uuid.uuid4().hex[:6]}"

    # Update in-memory read-your-writes overlay
    with _overlay_lock:
        _uncommitted_overlay[(category, key)] = (value, seq)

    entry = {
        "seq": seq,
        "action": "learn",
        "id": fact_id,
        "category": category,
        "key": key,
        "value": value,
        "previous_value": prev_val,
        "ts": time.time(),
    }

    # Atomic write to write-ahead journal under mutex
    with _journal_lock:
        try:
            JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as j_err:
            print(f"[Memory Outbox] ⚠️ Journal append failed: {j_err}")

    _start_worker_if_needed()

    try:
        _memory_write_queue.put_nowait(entry)
        res = {
            "status": "queued",
            "id": fact_id,
            "category": category,
            "key": key,
            "value": value,
            "previous_value": prev_val,
        }
        _broadcast_activity(res)
        return res
    except queue.Full:
        # Fallback if queue is saturated
        update_memory({category: {key: {"value": value}}})
        with _overlay_lock:
            _uncommitted_overlay.pop((category, key), None)
        global _committed_watermark
        _committed_watermark = max(_committed_watermark, seq)
        commit_marker = {"seq": seq, "action": "commit_marker", "id": fact_id, "ts": time.time()}
        with _journal_lock:
            try:
                with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(commit_marker, ensure_ascii=False) + "\n")
            except Exception:
                pass
        res = {"status": "persisted", "id": fact_id, "category": category, "key": key, "value": value}
        _broadcast_activity(res)
        return res


def queue_memory_forget(category: str, key: str) -> dict:
    """Enqueue fact deletion to outbox. Permitted even when memory is paused."""
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"

    key = str(key or "").strip()
    if not key:
        return {"status": "error", "message": "Key is required."}

    # Rollout feature flag check
    if os.environ.get("ZEZO_MEMORY_ASYNC_OUTBOX", "true").lower() == "false":
        delete_memory_fact(category, key)
        return {"status": "persisted", "action": "forgotten", "category": category, "key": key}

    with _seq_lock:
        global _seq_counter
        _seq_counter += 1
        seq = _seq_counter

    fact_id = f"fact_{category}_{key}_{seq}_{uuid.uuid4().hex[:6]}"

    # Update in-memory overlay: None suppresses fact in searches immediately
    with _overlay_lock:
        _uncommitted_overlay[(category, key)] = (None, seq)

    entry = {
        "seq": seq,
        "action": "forget",
        "id": fact_id,
        "category": category,
        "key": key,
        "ts": time.time(),
    }

    with _journal_lock:
        try:
            JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as j_err:
            print(f"[Memory Outbox] ⚠️ Journal append failed: {j_err}")

    _start_worker_if_needed()

    try:
        _memory_write_queue.put_nowait(entry)
        res = {
            "status": "queued",
            "action": "forgotten",
            "id": fact_id,
            "category": category,
            "key": key,
        }
        _broadcast_activity(res)
        return res
    except queue.Full:
        delete_memory_fact(category, key)
        with _overlay_lock:
            _uncommitted_overlay.pop((category, key), None)
        global _committed_watermark
        _committed_watermark = max(_committed_watermark, seq)
        res = {"status": "persisted", "action": "forgotten", "id": fact_id, "category": category, "key": key}
        _broadcast_activity(res)
        return res


def clear_pending_outbox() -> int:
    """Purge in-flight queue entries, clear overlay and journal, and broadcast failed events."""
    dropped = []
    while not _memory_write_queue.empty():
        try:
            dropped.append(_memory_write_queue.get_nowait())
        except Exception:
            break

    with _overlay_lock:
        _uncommitted_overlay.clear()

    with _journal_lock:
        try:
            if JOURNAL_PATH.exists():
                JOURNAL_PATH.write_text("", encoding="utf-8")
        except Exception:
            pass

    for item in dropped:
        _broadcast_activity({
            "status": "failed",
            "id": item.get("id"),
            "category": item.get("category"),
            "key": item.get("key"),
            "value": item.get("value", ""),
            "reason": "Memory cleared by user",
        })
    return len(dropped)


def _entry_value(entry) -> str:
    """Accept both the {'value': ..., 'updated': ...} shape and a bare string,
    because early versions of the store wrote plain strings."""
    if isinstance(entry, dict):
        return str(entry.get("value", "") or "").strip()
    return str(entry or "").strip()


def _pretty(key: str) -> str:
    return key.replace("_", " ").strip()


# Identity is always in the prompt; these categories compete for the remaining
# budget by recency.
_CATEGORY_LABELS = {
    "preferences":   "Preferences",
    "projects":      "Active projects / goals",
    "relationships": "People in their life",
    "wishes":        "Wishes / plans",
    "notes":         "Notes",
}

_IDENTITY_FIELDS = ["name", "age", "birthday", "city", "job",
                    "language", "school", "nationality"]

# How many past sessions may appear in the system prompt.
PROMPT_MAX_SESSIONS = 3


def _session_rows(memory: dict) -> list[tuple[str, str, str]]:
    """Flatten memory['sessions'] into (cat, key, value) rows.

    Session summaries are the only condensed record of what a whole
    conversation was about, so they are exactly what "what did we discuss
    yesterday" needs. They live in a LIST rather than a category dict, which
    is why every generic fact walker used to step straight over them — they
    were write-only: saved by save_session_summary(), deleted by
    pop_last_session(), and never reachable by recall_memory or the prompt.
    """
    rows: list[tuple[str, str, str]] = []
    sessions = memory.get("sessions") if isinstance(memory, dict) else None
    if not isinstance(sessions, list):
        return rows
    for entry in sessions:
        if not isinstance(entry, dict):
            continue
        summary = str(entry.get("summary") or "").strip()
        if not summary:
            continue
        date = str(entry.get("date") or "").strip() or "undated"
        # Two sessions can share a date (the app was restarted, or a session
        # ran across midnight). The start time keeps them distinguishable.
        started = str(entry.get("started_at") or "").strip()
        label = f"session {date} {started[11:16]}" if len(started) >= 16 else f"session {date}"
        rows.append(("sessions", label, summary))
    return rows


def _fact_line(cat: str, key: str, val: str) -> str:
    """Render one recall result line. Session summaries get their own shape
    so the model can read them as a dated conversation, not a fact key."""
    if cat == "sessions":
        return f"{_pretty(key).capitalize()}: {val}"
    return f"{cat}/{_pretty(key)}: {val}"


def _recent_session_lines(memory: dict, budget: int) -> list[str]:
    """Render the newest session summaries for the system prompt.

    Newest first (the sessions list is append-only, so the tail is the
    latest), capped at PROMPT_MAX_SESSIONS and by the remaining character
    budget so this block can never blow the prompt up.
    """
    lines: list[str] = []
    for _cat, key, summary in reversed(_session_rows(memory)):
        line = f"  - {_pretty(key).capitalize()}: {summary}"
        if budget - len(line) - 1 < 0:
            break
        lines.append(line)
        budget -= len(line) + 1
        if len(lines) >= PROMPT_MAX_SESSIONS:
            break
    return lines


def format_memory_for_prompt(memory: dict | None) -> str:
    """Build the memory block that goes into the system prompt.

    This used to dump everything. It now sends three things:

      1. IDENTITY  - always, in full. It is small, and it is wrong for the
         assistant to have to look up your name.
      2. RECENT    - the most recently updated entries from every other
         category, up to PROMPT_CORE_CHARS. Recency is the cheapest useful
         relevance signal available without embeddings.
      3. AN INDEX  - the *keys* of everything else, values omitted.

    Point 3 is what makes recall work at all. A model cannot decide to look
    something up if it does not know the thing exists: with only points 1 and 2,
    "who is Ayse?" would get "I don't know" while ayse_sister sat on disk
    unread. The index costs a few hundred characters and turns recall from a
    gamble into a lookup.

    Net effect on latency: this block is SMALLER than the old full dump, so
    every session connects with fewer tokens. Occasionally the model spends one
    extra round trip on recall_memory - covered by the acknowledgment it
    already speaks before any slow step."""
    if not memory:
        return ""

    core_lines: list[str] = []

    # 0. Immutable User Directives (Phase 3 Memory Palace)
    try:
        from memory.sqlite_memory import get_explicit_rules
        rules = get_explicit_rules(active_only=True)
        if rules:
            core_lines.append("IMMUTABLE USER DIRECTIVES:")
            for r in rules[:6]:
                core_lines.append(f"  • {r['rule_text']}")
            core_lines.append("")
    except Exception:
        pass

    # 1. Identity - always, in full
    identity = memory.get("identity", {}) or {}
    for field in _IDENTITY_FIELDS:
        val = _entry_value(identity.get(field))
        if not val:
            continue
        if field == "language":
            # Labelled as an observation, not a setting. A bare "Language:
            # English" line written months ago reads like a standing order and
            # was one of the reasons a Turkish question came back in English.
            core_lines.append(
                f"Has spoken to you in: {val} (an observation about the past — "
                f"always answer in the language of their CURRENT message)")
        else:
            core_lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in _IDENTITY_FIELDS:
            continue
        val = _entry_value(entry)
        if val:
            core_lines.append(f"{_pretty(key).title()}: {val}")

    # 2. Everything else, most recently updated first
    rest: list[tuple[str, str, str, str]] = []   # (updated, cat, key, value)
    for cat in _CATEGORY_LABELS:
        for key, entry in (memory.get(cat, {}) or {}).items():
            val = _entry_value(entry)
            if not val:
                continue
            updated = (entry.get("updated", "") if isinstance(entry, dict) else "") or "0000-00-00"
            rest.append((updated, cat, key, val))
    rest.sort(key=lambda t: t[0], reverse=True)

    used    = sum(len(l) + 1 for l in core_lines)
    shown: dict[str, list[str]] = {}
    overflow: dict[str, list[str]] = {}

    # Recency decides order, but no single category may take the whole budget.
    # Without the cap, someone with forty stored preferences gets a prompt that
    # is forty preferences and not one person's name — the categories that
    # matter most in conversation are also the ones that change least often, so
    # pure recency systematically buries them.
    per_cat_used: dict[str, int] = {}
    for _updated, cat, key, val in rest:
        line = f"  - {_pretty(key).title()}: {val}"
        if (per_cat_used.get(cat, 0) < PROMPT_MAX_PER_CATEGORY
                and used + len(line) + 1 <= PROMPT_CORE_CHARS):
            shown.setdefault(cat, []).append(line)
            per_cat_used[cat] = per_cat_used.get(cat, 0) + 1
            used += len(line) + 1
        else:
            overflow.setdefault(cat, []).append(_pretty(key))

    # The index is a table of contents, so it is interleaved across categories
    # rather than continuing in recency order. Sorted by recency it would list
    # twenty-four preferences before the first relationship, and the one entry
    # the index exists for — the old fact the model has no other way to know
    # about — would fall off the end.
    indexed: list[str] = []
    if overflow:
        cats  = [c for c in _CATEGORY_LABELS if overflow.get(c)]
        cursor = {c: 0 for c in cats}
        while cats:
            for cat in list(cats):
                i = cursor[cat]
                if i >= len(overflow[cat]):
                    cats.remove(cat)
                    continue
                indexed.append(overflow[cat][i])
                cursor[cat] = i + 1

    for cat, label in _CATEGORY_LABELS.items():
        if shown.get(cat):
            core_lines.append("")
            core_lines.append(f"{label}:")
            core_lines.extend(shown[cat])

    # 2b. Recent conversation summaries. Without these the assistant has no
    # idea that a topic was ever discussed, so it cannot recall it by name —
    # it can only say "I do not know". This is what makes "what did we do
    # yesterday" answerable without a tool round trip.
    session_lines = _recent_session_lines(memory, budget=PROMPT_CORE_CHARS - used)
    if session_lines:
        core_lines.append("")
        core_lines.append(
            "RECENT CONVERSATIONS (summaries of past sessions — use these to "
            "recall what was already discussed, and to answer questions about "
            "previous days without guessing):"
        )
        core_lines.extend(session_lines)
        used += sum(len(l) + 1 for l in session_lines)

    if not core_lines and not indexed:
        return ""

    out = [
        "[WHAT YOU KNOW ABOUT THE USER / CREATOR — This is the person talking directly to you right now. NEVER refer to them in 3rd person as an external 'subject'. Never recite their profile unprompted.]",
        *core_lines,
    ]

    # 3. The index of what is on disk but not in this prompt
    if indexed:
        budget, names = PROMPT_INDEX_CHARS, []
        for n in indexed:
            if budget - len(n) - 2 < 0:
                break
            names.append(n)
            budget -= len(n) + 2
        if names:
            out.append("")
            out.append(
                "[ALSO REMEMBERED — values not shown here. Call recall_memory "
                "with a keyword to read any of these before saying you do not know]"
            )
            out.append(", ".join(names)
                       + (f" (+{len(indexed) - len(names)} more)"
                          if len(indexed) > len(names) else ""))

    return "\n".join(out) + "\n"


# ── Recall ────────────────────────────────────────────────────────────────────

def _score(query_words: list[str], cat: str, key: str, value: str) -> int:
    """Cheap lexical relevance. No embeddings, no network, no model call - this
    runs in well under a millisecond, which is the entire point: recall must
    cost one model round trip, never two."""
    hay_key = _pretty(key).lower()
    hay_val = value.lower()
    score   = 0
    for w in query_words:
        if not w:
            continue
        if w == hay_key:
            score += 10
        elif w in hay_key:
            score += 6
        if w in hay_val:
            score += 3
        if w in cat:
            score += 1
    return score


def _search_raw_facts(query: str, limit: int = 8) -> str:
    """Find stored facts matching `query` from local JSON memory and uncommitted overlay."""
    memory = load_memory()

    # Read-Your-Writes In-Memory Overlay Integration (Elite Tweak 1)
    with _overlay_lock:
        for (cat, key), (val, seq) in _uncommitted_overlay.items():
            if val is not None:
                memory.setdefault(cat, {})[key] = {"value": val, "updated": "Just now"}
            else:
                if cat in memory and isinstance(memory[cat], dict) and key in memory[cat]:
                    del memory[cat][key]

    words  = [w for w in re.split(r"[^\w]+", (query or "").lower()) if len(w) > 1]

    rows: list[tuple[int, str, str, str]] = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue                     # other list-valued keys are not facts
        for key, entry in items.items():
            val = _entry_value(entry)
            if not val:
                continue
            s = _score(words, cat, key, val) if words else 1
            if s > 0:
                rows.append((s, cat, key, val))

    # Session summaries are stored in a list, so the category walker above
    # never saw them. They are searchable now — this is the path that lets
    # recall_memory answer "what did we discuss on <date>".
    for cat, key, val in _session_rows(memory):
        s = _score(words, cat, key, val) if words else 1
        if s > 0:
            rows.append((s, cat, key, val))

    if not rows:
        return (f"Nothing stored about '{query}'." if query
                else "I have not stored anything about this person yet.")

    rows.sort(key=lambda r: (-r[0], r[2]))
    lines = [_fact_line(cat, key, val) for _s, cat, key, val in rows[:max(1, limit)]]
    head  = (f"Stored facts matching '{query}':" if query
             else "Everything currently stored:")
    more  = (f"\n(+{len(rows) - len(lines)} more — search with a narrower keyword)"
             if len(rows) > len(lines) else "")
    return head + "\n" + "\n".join(lines) + more


def search_memory(query: str, limit: int = 8) -> str:
    """Find stored facts and verbatim conversation history matching `query`. Backs the recall_memory tool."""
    try:
        from memory import sqlite_memory
        return sqlite_memory.search_unified_memory(query, limit=limit)
    except Exception as e:
        print(f"[Memory] ⚠️ SQLite memory search fallback: {e}")
        return _search_raw_facts(query, limit=limit)


def all_entries_for_ui() -> list[dict]:
    """Flat list for the memory panel: what JARVIS knows, and when it learned it.
    Sorted newest first so the panel opens on what changed most recently."""
    memory = load_memory()
    with _overlay_lock:
        for (cat, key), (val, seq) in _uncommitted_overlay.items():
            if val is not None:
                memory.setdefault(cat, {})[key] = {"value": val, "updated": "Just now"}
            else:
                if cat in memory and isinstance(memory[cat], dict) and key in memory[cat]:
                    del memory[cat][key]

    rows = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            val = _entry_value(entry)
            if not val:
                continue
            rows.append({
                "category": cat,
                "key":      key,
                "value":    val,
                "updated":  (entry.get("updated", "") if isinstance(entry, dict) else ""),
            })
    rows.sort(key=lambda r: (r["updated"] or "0000-00-00"), reverse=True)
    return rows

def remember(key: str, value: str, category: str = "notes") -> str:
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    res = queue_memory_write(category, key, value)
    if res.get("status") == "paused":
        return "Memory is currently paused. Fact was not saved."
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    queue_memory_forget(category, key)
    return f"Forgotten: {category}/{key}"


forget_memory = forget


# ── Session memory ─────────────────────────────────────────────────────────────

_SESSION_MAX = 3   # safety cap — in practice 0-1 entries after pop


def save_session_summary(summary: str, language: str = "",
                         session_date: str = "", started_at: str = "") -> None:
    """Append a 1-2 sentence session summary to long_term.json['sessions'].

    'session_date' is the date the *conversation* happened (YYYY-MM-DD), not
    the date the summary was written. A session that started at 23:50 on the
    21st and was summarised at 00:10 on the 22nd belongs to the 21st — the
    user remembers it as "last night". Falls back to today when omitted.
    'started_at' optionally carries the session's start timestamp.
    """
    summary = (summary or "").strip()
    if not summary:
        return
    memory   = load_memory()
    sessions = memory.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []
    now = datetime.now()
    date = (session_date or "").strip()[:10] or now.strftime("%Y-%m-%d")
    entry: dict = {
        "date":    date,
        "summary": summary[:280],
        "saved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if (started_at or "").strip():
        entry["started_at"] = started_at.strip()[:19]
    if language:
        entry["language"] = language
    sessions.append(entry)
    memory["sessions"] = sessions[-_SESSION_MAX:]
    with _lock:
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_PATH.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(f"[Memory] 📝 Session saved ({entry['date']}): {summary[:60]}…")


def pop_last_session() -> dict | None:
    """
    Return AND remove the most recent session entry.
    Calling this consumes the entry so it is never repeated in future briefings.
    """
    with _lock:
        if not MEMORY_PATH.exists():
            return None
        try:
            memory   = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            sessions = memory.get("sessions", [])
            if not isinstance(sessions, list) or not sessions:
                return None
            entry = sessions.pop()          # remove the last entry
            memory["sessions"] = sessions
            MEMORY_PATH.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return entry
        except Exception as e:
            print(f"[Memory] ⚠️ pop_last_session error: {e}")
            return None


def wipe_all_long_term_json() -> None:
    """Flush memory/long_term.json and replica backup back to empty template."""
    with _lock:
        empty = _empty_memory()
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_PATH.write_text(json.dumps(empty, indent=2, ensure_ascii=False), encoding="utf-8")
        bak = MEMORY_PATH.with_suffix(".json.bak")
        if bak.exists():
            try:
                bak.write_text(json.dumps(empty, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass