"""
core/provider_health.py — startup provider/model health check.

WHY THIS EXISTS
    Model names get retired (the old `gemini-2.5-*` names now 404). When a model
    dies, a feature used to break silently: the user saw "it didn't work", not
    "the model is gone". This module pings each configured provider/model once at
    startup (off the GUI thread, cheaply — model lookup, not generation), logs a
    one-line summary, and marks dead Gemini models so the one-shot ladder in
    `core/gemini.py` skips them instead of paying for a 404 on every call.

    It never blocks or raises into the caller: every failure is captured in the
    returned status dict.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Callable

_lock = threading.Lock()
_started = threading.Event()
_status: dict = {
    "checked": False,
    "ts": 0.0,
    "gemini": {},
    "groq": {},
    "summary": "not checked yet",
}


# ── Gemini ───────────────────────────────────────────────────────────────────

def _gemini_model_state(cl, name: str) -> str:
    """ok | missing | quota | busy | unknown — never raises."""
    try:
        cl.models.get(model=name)
        return "ok"
    except Exception as e:
        low = str(e).lower()
        if "404" in low or "not found" in low or "not_found" in low:
            return "missing"
        if "429" in low or "resource_exhausted" in low or "quota" in low:
            return "quota"
        if "503" in low or "unavailable" in low or "overloaded" in low:
            return "busy"
        return "unknown"


def _gemini_check() -> dict:
    try:
        from core.gemini import api_key, client, mark_unavailable
        from core.models import GEMINI_CHECK_MODELS, GEMINI_LIVE_MODEL
    except Exception as e:
        return {"error": f"import failed: {e}"}

    if not api_key():
        return {"error": "no Gemini API key configured"}
    try:
        cl = client()
    except Exception as e:
        return {"error": str(e)}

    out: dict[str, str] = {}
    for name in GEMINI_CHECK_MODELS:
        out[name] = _gemini_model_state(cl, name)
    out[GEMINI_LIVE_MODEL] = _gemini_model_state(cl, GEMINI_LIVE_MODEL)

    # A retired model must not keep getting tried by the one-shot ladder.
    for name, state in out.items():
        if state == "missing":
            try:
                mark_unavailable(name)
            except Exception:
                pass
    return out


# ── Groq ─────────────────────────────────────────────────────────────────────

def _groq_check() -> dict:
    try:
        from memory.config_manager import (
            get_groq_api_key, get_groq_model,
            get_groq_whisper_model, get_groq_vision_model,
        )
    except Exception as e:
        return {"error": f"import failed: {e}"}

    key = get_groq_api_key()
    if not key or not isinstance(key, str) or not key.strip():
        return {"error": "no Groq API key configured"}
    key = key.strip()
    if any(ord(c) >= 128 or c in "\r\n" for c in key):
        return {"error": "invalid Groq API key (must be clean ASCII token)"}

    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                # Groq's edge returns 403 to the default urllib User-Agent.
                "User-Agent": "ZEZO/1.0 (+https://groq.com)",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        ids = {str(m.get("id")) for m in data.get("data", [])}
    except Exception as e:
        return {"error": str(e)}

    whisper = get_groq_whisper_model()
    vision = get_groq_vision_model()
    res = {
        "reachable": True,
        "model_count": len(ids),
        get_groq_model(): "ok" if get_groq_model() in ids else "missing",
        whisper: "ok" if whisper in ids else "missing",
    }
    if vision:
        res[vision] = "ok" if vision in ids else "missing"
    return res


# ── Public API ───────────────────────────────────────────────────────────────

def _summarize(gem: dict, groq: dict) -> str:
    if "error" in gem:
        g = f"Gemini: {gem['error']}"
    else:
        ok = [k for k, v in gem.items() if v == "ok"]
        dead = [k for k, v in gem.items() if v == "missing"]
        g = f"Gemini {len(ok)}/{len(gem)} ok"
        if dead:
            g += f" — DEAD: {', '.join(dead)}"
    if "error" in groq:
        q = f"Groq: {groq['error']}"
    else:
        dead_q = [k for k, v in groq.items() if v == "missing"]
        q = "Groq: reachable" + (f" — missing: {', '.join(dead_q)}" if dead_q else "")
    return f"{g} | {q}"


def run_health_check(log: Callable[[str], None] | None = None) -> dict:
    """Check every provider once. Blocking — call from a background thread."""
    def _log(msg: str) -> None:
        if log:
            try:
                log(msg)
                return
            except Exception:
                pass
        print(msg)

    _log("SYS: Provider health-check starting…")
    gem = _gemini_check()
    groq = _groq_check()
    summary = _summarize(gem, groq)
    with _lock:
        _status.update({
            "checked": True, "ts": time.time(),
            "gemini": gem, "groq": groq, "summary": summary,
        })
    _log(f"SYS: Provider health — {summary}")
    return get_status()


def start_background_check(log: Callable[[str], None] | None = None) -> None:
    """Run the check once, off the caller's thread. Safe to call repeatedly."""
    if _started.is_set():
        return
    _started.set()
    threading.Thread(target=run_health_check, args=(log,),
                     daemon=True, name="provider-health").start()


def get_status() -> dict:
    """Last health-check result (a copy). `checked=False` until it has run."""
    with _lock:
        return json.loads(json.dumps(_status))
