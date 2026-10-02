"""
core/llm_router.py — provider router for BACKGROUND text generation.

LIVE VOICE IS NOT THIS FILE. The realtime conversation always runs on the
Gemini Live API (native audio in/out). This module is only for non-realtime
text work: summaries, short parses, command/code generation, research prose.

WHY
    Gemini's free text pool runs dry under background load, and when it does the
    feature behind it dies. Groq is a free, very fast coprocessor for exactly this
    work. Routing to it first keeps the Gemini text quota for what needs it and
    speeds up everything else.

ORDER (first that answers wins)

    Groq  →  Gemini ladder  →  Ollama (local)

    A provider that is not configured, rate-limited or unreachable is skipped —
    the router moves to the next one rather than failing the task. It only raises
    if every provider fails, so callers keep a real error to report.

    Do NOT route long-form, quality-critical or grounded output here:
      * grounded search needs Gemini's grounding metadata  → core.gemini SEARCH
      * large HTML/doc synthesis can exceed Groq's token cap → keep on Gemini
      * anything multimodal stays on Gemini
"""
from __future__ import annotations

from typing import Callable

# Gemini tiers (strings mirror core.gemini's FAST/SMART/SEARCH).
FAST = "fast"
SMART = "smart"


def _log(log: Callable[[str], None] | None, msg: str) -> None:
    if log:
        try:
            log(msg)
            return
        except Exception:
            pass
    print(msg)


def _try_groq(prompt: str, system: str | None, timeout_ms: int,
              log: Callable[[str], None] | None) -> str | None:
    """Groq LPU text completion. None if not configured or it failed."""
    try:
        from memory.config_manager import get_groq_api_key
        if not get_groq_api_key():
            return None
    except Exception:
        return None
    try:
        from core.llm_client import call_groq_text
        timeout = max(10, min(60, int(timeout_ms / 1000) or 30))
        out = call_groq_text(prompt, system=system, timeout=timeout)
        out = (out or "").strip()
        if out:
            _log(log, "[LLM] served by Groq")
            return out
        _log(log, "[LLM] Groq returned empty — trying Gemini")
    except Exception as e:
        _log(log, f"[LLM] Groq unavailable ({e}) — trying Gemini")
    return None


def _try_gemini(prompt: str, system: str | None, tier: str, timeout_ms: int,
                log: Callable[[str], None] | None) -> str | None:
    """Gemini one-shot ladder. None if it failed."""
    try:
        from core import gemini
        full = f"{system}\n\n{prompt}" if system else prompt
        out = gemini.text(full, tier=(tier or SMART), timeout_ms=timeout_ms)
        out = (out or "").strip()
        if out:
            _log(log, "[LLM] served by Gemini")
            return out
        _log(log, "[LLM] Gemini returned empty — trying local LLM")
    except Exception as e:
        _log(log, f"[LLM] Gemini unavailable ({e}) — trying local LLM")
    return None


def _try_ollama(prompt: str, system: str | None,
                log: Callable[[str], None] | None) -> str | None:
    """Local Ollama / OpenAI-compatible fallback. None if it failed."""
    try:
        from core.llm_client import call_llm_text
        out = call_llm_text(prompt, system=system)
        out = (out or "").strip()
        if out:
            _log(log, "[LLM] served by local LLM")
            return out
    except Exception as e:
        _log(log, f"[LLM] local LLM unavailable ({e})")
    return None


def generate_text(
    prompt: str,
    system: str | None = None,
    tier: str = SMART,
    timeout_ms: int = 60_000,
    allow_groq: bool = True,
    log: Callable[[str], None] | None = None,
) -> str:
    """Background text generation: Groq → Gemini → Ollama.

    Raises RuntimeError only when every provider fails. Callers that need a
    grounded, multimodal or very long answer should call `core.gemini` directly
    (or pass `allow_groq=False` to skip the Groq rung).
    """
    if allow_groq:
        out = _try_groq(prompt, system, timeout_ms, log)
        if out is not None:
            return out
    out = _try_gemini(prompt, system, tier, timeout_ms, log)
    if out is not None:
        return out
    out = _try_ollama(prompt, system, log)
    if out is not None:
        return out
    raise RuntimeError("all text providers failed (Groq, Gemini, Ollama)")
