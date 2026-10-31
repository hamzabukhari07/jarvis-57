"""
core/pending_intent.py — Multi-Turn Task Intent Tracking & Continuation State.

Creator & Lead Architect: Hamza Bukhari

Tracks pending tasks across conversational turns, interruptions, folder preparation,
or WebSocket reconnects so that user confirmations like "do it", "haan karo", "shuru karo",
or "proceed" cleanly resume the active task without asking "do what?".
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("zezo.pending_intent")

_LOCK = threading.Lock()
_CACHE: Optional[Dict[str, Any]] = None
_EXPIRY_SECONDS = 900.0  # 15 minutes TTL

_STATE_FILE = Path(__file__).resolve().parent.parent / "memory" / "pending_intent.json"


def _read_persisted() -> Optional[Dict[str, Any]]:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ts = float(data.get("timestamp", 0.0))
                if time.time() - ts < _EXPIRY_SECONDS:
                    return data
    except Exception as e:
        logger.debug("[pending_intent] Read state note: %s", e)
    return None


def _write_persisted(data: Optional[Dict[str, Any]]) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            if _STATE_FILE.exists():
                _STATE_FILE.unlink(missing_ok=True)
        else:
            _STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("[pending_intent] Write state note: %s", e)


def set_pending_intent(
    task: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    target_dir: Optional[str] = None,
    skill_name: Optional[str] = None,
    engine: Optional[str] = None,
    status: str = "awaiting_confirmation",
) -> Dict[str, Any]:
    """Persist a pending task intent so that subsequent conversational turns can resume it."""
    payload: Dict[str, Any] = {
        "task": task or "",
        "action": action or "run_skill",
        "skill_name": skill_name or "",
        "params": params or {},
        "target_dir": target_dir or "",
        "engine": engine or "antigravity",
        "status": status,
        "timestamp": time.time(),
    }
    with _LOCK:
        global _CACHE
        _CACHE = payload
        _write_persisted(payload)
    logger.info("[pending_intent] Set active pending intent for '%s' (action: %s)", task[:40], action)
    return payload


def get_pending_intent() -> Optional[Dict[str, Any]]:
    """Retrieve the current pending task intent if within the 15-minute TTL."""
    global _CACHE
    with _LOCK:
        if _CACHE is not None:
            if time.time() - float(_CACHE.get("timestamp", 0.0)) < _EXPIRY_SECONDS:
                return dict(_CACHE)
            _CACHE = None
            _write_persisted(None)
            return None

        # Try reading persisted state
        persisted = _read_persisted()
        if persisted:
            _CACHE = persisted
            return dict(_CACHE)
        return None


def clear_pending_intent() -> None:
    """Clear active pending task intent upon completion or explicit cancellation."""
    global _CACHE
    with _LOCK:
        _CACHE = None
        _write_persisted(None)
    logger.info("[pending_intent] Cleared pending intent")


def has_pending_intent() -> bool:
    """Check if an active, unexpired pending intent exists."""
    return get_pending_intent() is not None
