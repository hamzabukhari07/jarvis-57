"""
memory_state.py — Decoupled session-scoped memory state for ZEZO OS.

Creator & Lead Architect: Hamza Bukhari
Prevents circular imports between memory_manager and sqlite_memory.
"""

import threading

_memory_paused: bool = False
_pause_lock = threading.Lock()


def is_memory_paused() -> bool:
    """Return whether memory learning/recording is currently paused (incognito mode)."""
    with _pause_lock:
        return _memory_paused


def set_memory_paused(paused: bool) -> None:
    """Set the memory paused state. Session-scoped; resets to False on restart."""
    global _memory_paused
    with _pause_lock:
        _memory_paused = bool(paused)
