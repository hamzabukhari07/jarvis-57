"""
memory/memory_condenser.py — Immutable Provenance & Conflict-Aware Memory Palace.

Key Architecture:
  1. Immutable Rules: Direct human instructions stored in `user_explicit_rules`
     that cannot be overwritten or purged by automated summaries.
  2. Conflict Resolution Graph: When new knowledge contradicts existing facts/rules,
     both are preserved with source timestamps as PENDING conflicts for user resolution.
  3. Periodic Session Reaper: Distills uncompacted turns every 40 minutes using fast
     Groq/Gemini LPU without blocking the main voice or GUI loop.
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from memory.sqlite_memory import (
    get_explicit_rules,
    get_pending_conflicts,
    get_uncondensed_turns,
    init_db,
    insert_explicit_rule,
    insert_memory_conflict,
    record_condensation,
    resolve_memory_conflict,
    set_explicit_rule_status,
)


_reaper_thread: Optional[threading.Thread] = None
_stop_reaper_event = threading.Event()
_condenser_lock = threading.Lock()

# Explicit directive trigger prefixes from user speech
_DIRECTIVE_PATTERNS = [
    re.compile(r"^(?:always|never|remember that|make sure that|from now on|rule:)\s+(.+)", re.IGNORECASE),
    re.compile(r"^(?:always use|never use|strictly use|do not use)\s+(.+)", re.IGNORECASE),
    re.compile(r"^hamesha\s+(.+)", re.IGNORECASE),
    re.compile(r"^kabhi bhi\s+(.+)", re.IGNORECASE),
    re.compile(r"^yaad rakh(?:na)?\s+(.+)", re.IGNORECASE),
]

_NEGATION_TERMS = {
    "not", "never", "dont", "don't", "avoid", "disable", "stop", "kabhi", "nahi", "mat"
}


def add_user_explicit_rule(rule_text: str, category: str = "general", source_turn_id: Optional[int] = None) -> int:
    """Register an immutable user directive that AI summarizers cannot alter."""
    init_db()
    return insert_explicit_rule(rule_text, category, source_turn_id)


def list_active_rules() -> list[dict]:
    """Retrieve all active immutable user rules."""
    init_db()
    return get_explicit_rules(active_only=True)


def toggle_rule(rule_id: int, is_active: bool) -> bool:
    """Human-initiated toggle for an explicit rule."""
    init_db()
    return set_explicit_rule_status(rule_id, is_active)


def extract_explicit_directive(text: str) -> Optional[str]:
    """Extract directive string if text matches an explicit rule trigger."""
    cleaned = (text or "").strip()
    for pat in _DIRECTIVE_PATTERNS:
        m = pat.search(cleaned)
        if m:
            return m.group(1).strip()
    return None


def _detect_simple_contradiction(new_claim: str, existing_claim: str) -> bool:
    """Lightweight heuristic check for direct polarity conflict between two statements."""
    if not new_claim or not existing_claim:
        return False
    
    tokens_new = set(re.findall(r"\w+", new_claim.lower()))
    tokens_old = set(re.findall(r"\w+", existing_claim.lower()))
    
    # Check shared subject/verbs
    shared = tokens_new.intersection(tokens_old) - _NEGATION_TERMS
    if len(shared) < 2:
        return False

    has_neg_new = bool(tokens_new.intersection(_NEGATION_TERMS))
    has_neg_old = bool(tokens_old.intersection(_NEGATION_TERMS))
    
    return has_neg_new != has_neg_old


def check_and_record_conflict(
    candidate_fact: str,
    source_session_id: str,
    active_rules: list[dict],
    existing_facts: dict,
) -> Optional[int]:
    """Compare candidate against existing rules/facts; record conflict if contradictory."""
    # 1. Compare against immutable explicit rules
    for rule in active_rules:
        r_text = rule.get("rule_text", "")
        if _detect_simple_contradiction(candidate_fact, r_text):
            return insert_memory_conflict(
                existing_content=r_text,
                contradicting_content=candidate_fact,
                source_session_id=source_session_id,
                existing_rule_id=rule.get("id"),
            )

    # 2. Compare against existing category facts
    for cat, items in existing_facts.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            val = entry.get("value", "") if isinstance(entry, dict) else str(entry)
            if _detect_simple_contradiction(candidate_fact, val):
                return insert_memory_conflict(
                    existing_content=f"{cat}.{key}: {val}",
                    contradicting_content=candidate_fact,
                    source_session_id=source_session_id,
                    existing_fact_key=f"{cat}.{key}",
                )

    return None


def _distill_transcript_with_llm(turns_text: str) -> Optional[dict]:
    """Run non-blocking Groq/Gemini distillation to extract facts and directives."""
    prompt = (
        "Extract long-term memory updates from these conversation turns in valid JSON format.\n"
        "Return ONLY a JSON object with this exact shape:\n"
        "{\n"
        '  "summary": "1-2 sentence session summary",\n'
        '  "explicit_rules": ["List of strict user rules or directives stated"],\n'
        '  "new_facts": [\n'
        '    {"category": "projects|preferences|identity|wishes", "key": "short_key", "value": "fact value"}\n'
        "  ]\n"
        "}\n\n"
        f"TURNS:\n{turns_text}"
    )

    try:
        from core.llm_router import FAST, call_background_text
        raw_res = call_background_text(prompt, system="You are ZEZO Memory Condenser. Respond ONLY in valid JSON.", tier=FAST)
        if not raw_res:
            return None
        
        cleaned = raw_res.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        return json.loads(cleaned)
    except Exception as e:
        print(f"[Memory Condenser] Distillation parse notice: {e}")
        return None


def condense_recent_turns(max_turns: int = 120, use_llm: bool = True) -> dict:
    """Compact unprocessed turns into immutable rules, facts, and session summaries."""
    with _condenser_lock:
        init_db()
        turns = get_uncondensed_turns(limit=max_turns)
        if not turns:
            return {"status": "NO_NEW_TURNS", "condensed_count": 0}

        from memory.memory_manager import load_memory, update_memory_entry
        existing_facts = load_memory()
        active_rules = get_explicit_rules(active_only=True)

        session_id = turns[-1]["session_id"]
        last_turn_id = turns[-1]["id"]
        
        extracted_rules = []
        conflicts_recorded = []

        # 1. Deterministic heuristic scan on raw user turns
        for t in turns:
            if t["role"] == "user":
                directive = extract_explicit_directive(t["content"])
                if directive:
                    cid = check_and_record_conflict(directive, session_id, active_rules, existing_facts)
                    if cid:
                        conflicts_recorded.append(cid)
                    else:
                        rid = add_user_explicit_rule(directive, category="spoken_rule", source_turn_id=t["id"])
                        extracted_rules.append(rid)

        # 2. LLM-assisted distillation if enabled
        summary_text = f"Compacted {len(turns)} turns up to ID {last_turn_id}"
        if use_llm:
            formatted_turns = "\n".join(
                f"[{t['timestamp']}] {t['role'].upper()}: {t['content'][:200]}"
                for t in turns if t.get("content")
            )
            distilled = _distill_transcript_with_llm(formatted_turns[:4000])
            if distilled and isinstance(distilled, dict):
                summary_text = distilled.get("summary") or summary_text
                
                # Ingest newly distilled facts
                for item in distilled.get("new_facts", []):
                    if isinstance(item, dict) and item.get("key") and item.get("value"):
                        cat = item.get("category", "notes")
                        k = item.get("key")
                        v = item.get("value")
                        cid = check_and_record_conflict(f"{k}: {v}", session_id, active_rules, existing_facts)
                        if cid:
                            conflicts_recorded.append(cid)
                        else:
                            update_memory_entry(cat, k, v)

        # 3. Record session condensation checkpoint
        record_condensation(session_id, last_turn_id, summary_text)

        return {
            "status": "SUCCESS",
            "condensed_count": len(turns),
            "last_turn_id": last_turn_id,
            "explicit_rules_added": len(extracted_rules),
            "conflicts_found": len(conflicts_recorded),
            "summary": summary_text,
        }


def get_memory_palace_snapshot() -> dict:
    """Return comprehensive structured state of the Memory Palace."""
    init_db()
    from memory.memory_manager import load_memory
    
    return {
        "explicit_rules": get_explicit_rules(active_only=True),
        "pending_conflicts": get_pending_conflicts(),
        "structured_facts": load_memory(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def resolve_conflict_item(conflict_id: int, choice: str, notes: str = "") -> bool:
    """
    Resolve pending conflict:
      - 'OVERWRITE': Accept contradicting claim and update facts.
      - 'KEEP_OLD': Discard contradicting claim and retain existing fact/rule.
      - 'MERGE': Retain both with explicit note.
    """
    valid_choices = {"OVERWRITE", "KEEP_OLD", "MERGE"}
    norm_choice = choice.upper()
    if norm_choice not in valid_choices:
        return False

    status_str = f"RESOLVED_{norm_choice}"
    return resolve_memory_conflict(conflict_id, status_str, notes)


def _reaper_worker_loop(interval_seconds: int = 2400) -> None:
    """Periodic reaper running every 40 minutes (2400 seconds)."""
    while not _stop_reaper_event.is_set():
        try:
            condense_recent_turns(max_turns=150, use_llm=True)
        except Exception as e:
            print(f"[Memory Condenser] Reaper periodic sweep notice: {e}")
        _stop_reaper_event.wait(timeout=interval_seconds)


def start_background_reaper(interval_seconds: int = 2400) -> None:
    """Start daemon thread for periodic session consolidation."""
    global _reaper_thread
    if _reaper_thread and _reaper_thread.is_alive():
        return
    _stop_reaper_event.clear()
    _reaper_thread = threading.Thread(
        target=_reaper_worker_loop,
        args=(interval_seconds,),
        daemon=True,
        name="MemoryCondenserReaper",
    )
    _reaper_thread.start()


def stop_background_reaper() -> None:
    """Signal reaper thread to terminate."""
    _stop_reaper_event.set()
