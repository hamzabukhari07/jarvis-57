"""core/skill_prompt_engineer.py — Universal AI Skill Prompt Engineer.

Creator & Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)

Synthesizes bespoke, high-performance CLI execution directives for coding agents
(Antigravity CLI 'agy', OpenCode, Kilo, Claude Code, Cursor, Windsurf) strictly using
live AI inference: Groq LPU (~150-200ms) with stateful Gemini 3.8 Flash failover.
Zero hardcoded or dummy prompts allowed.

Standard Enforced Prompt Schema:
  [TASK DIRECTIVE]
  [DESIGN REFERENCES]
  [USER REQUIREMENTS & AUTHENTIC CONTENT]
  [SUBAGENTS WORKSPACE DECOMPOSITION] (5-7 parallel subagents)
  [CRITICAL DIRECT-EXECUTION CONSTRAINTS & ANTI-SLOP GATES]
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zezo.skill_prompt_engineer")

PROMPT_ENGINEER_SYSTEM = """You are the Elite Staff UI & Systems Prompt Architect on ZEZO (Creator: Hamza Bukhari).
Your sole mandate is to synthesize an uncompromising, direct CLI execution directive for a downstream autonomous coding engine (Google Antigravity CLI 'agy', OpenCode, or Kilo Code).

CORE DIRECTIVES:
1. Examine the provided SKILL SOP & Taste Examples and extract the architectural patterns, rules, and constraints.
2. Tailor 100% of the directive to the user's EXACT scope, requested tech stack, authentic content, and target folder.
3. Structure the output strictly into these 5 standard execution blocks:
   [TASK DIRECTIVE]
   [DESIGN REFERENCES]
   [USER REQUIREMENTS & AUTHENTIC CONTENT]
   [SUBAGENTS WORKSPACE DECOMPOSITION]
   [CRITICAL DIRECT-EXECUTION CONSTRAINTS & ANTI-SLOP GATES]

4. ALWAYS enforce:
   - 5 to 7 parallel subagents decomposition under [SUBAGENTS WORKSPACE DECOMPOSITION] for maximum velocity.
   - Complete Anti-Slop negative filters (no muddy black drop-shadows, no cheap scale-105 jumps, no broken # anchors, no generic lorem ipsum, 100% visual authority to reference templates).
   - Direct execution without asking questions or waiting for confirmation.
   - Zero intermediate Python helper scripts or temporary scrap files.
5. Output ONLY the raw executable prompt text with these 5 blocks. Never wrap in conversational preamble or markdown chat greetings."""


def craft_skill_engine_prompt(
    skill_name: str,
    skill_sop: str,
    user_task: str,
    target_dir: str,
    context: Optional[Dict[str, Any]] = None,
    engine: str = "antigravity",
) -> str:
    """Synthesizes a bespoke execution prompt strictly using live AI models.

    Order of execution:
      1. Primary: Groq LPU (llama-3.3-70b-versatile, ~150-200ms)
      2. Secondary: Google Gemini Flash (gemini-3.8-flash, gemini-3.6-flash)
    
    If both fail, raises RuntimeError. No dummy or hardcoded prompts are ever returned.
    """
    ctx = context or {}
    start_t = time.time()

    # Build prompt crafting briefing
    sop_body = (skill_sop or "").strip()
    if len(sop_body) > 6500:
        sop_body = sop_body[:6300] + "\n\n... [SOP truncated for prompt synthesis] ..."

    briefing = (
        f"=== TARGET SKILL: {skill_name.upper()} ===\n"
        f"Target Engine: {engine.upper()}\n"
        f"Target Directory: {target_dir}\n"
        f"User Task Request: {user_task}\n\n"
        f"Context Details:\n{json.dumps(ctx, indent=2)}\n\n"
        f"=== SKILL SOP & TASTE GUIDELINES ===\n"
        f"{sop_body}\n\n"
        "Synthesize the complete, surgical master directive for the coding agent now:"
    )

    groq_error: Optional[Exception] = None

    # ── 1. Primary Engine: Groq LPU (~150-200ms) ───────────────────────────
    try:
        from core.llm_client import call_groq_text

        prompt_out = call_groq_text(
            prompt=briefing,
            system=PROMPT_ENGINEER_SYSTEM,
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            timeout=12,
            max_tokens=2048,
        )
        if prompt_out and (
            "[TASK DIRECTIVE]" in prompt_out
            or "[SUBAGENTS WORKSPACE DECOMPOSITION]" in prompt_out
            or "You are an expert" in prompt_out
        ):
            logger.info(
                "[SkillPromptEngineer] Synthesized prompt via Groq LPU in %.2fs (%d chars)",
                time.time() - start_t,
                len(prompt_out),
            )
            return prompt_out.strip()
    except Exception as e:
        groq_error = e
        logger.warning(
            "[SkillPromptEngineer] Groq synthesis failed (%s), falling back to Gemini Flash...",
            e,
        )

    # ── 2. Secondary Engine: Gemini 3.8 Flash Fallback ──────────────────────
    gemini_error: Optional[Exception] = None
    try:
        from core.gemini import client as get_gemini_client
        from google.genai import types as gtypes

        cl = get_gemini_client(timeout_ms=12000)
        cfg = gtypes.GenerateContentConfig(
            system_instruction=PROMPT_ENGINEER_SYSTEM,
            temperature=0.2,
            max_output_tokens=2048,
        )
        candidate_models = [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3-flash-preview",
            "gemini-flash-latest",
        ]
        for model_name in candidate_models:
            try:
                resp = cl.models.generate_content(
                    model=model_name,
                    contents=briefing,
                    config=cfg,
                )
                text_out = getattr(resp, "text", "") or ""
                if text_out and (
                    "[TASK DIRECTIVE]" in text_out
                    or "[SUBAGENTS WORKSPACE DECOMPOSITION]" in text_out
                    or "You are an expert" in text_out
                ):
                    logger.info(
                        "[SkillPromptEngineer] Synthesized prompt via Gemini (%s) in %.2fs",
                        model_name,
                        time.time() - start_t,
                    )
                    return text_out.strip()
            except Exception as e_mod:
                gemini_error = e_mod
                logger.debug(
                    "[SkillPromptEngineer] Gemini candidate %s failed: %s",
                    model_name,
                    e_mod,
                )
                continue
    except Exception as e:
        gemini_error = e
        logger.error(
            "[SkillPromptEngineer] Gemini synthesis failed (%s).",
            e,
        )

    # ── 3. Strict Failure: No Dummy Prompts Allowed ─────────────────────────
    raise RuntimeError(
        f"AI Prompt Synthesis failed for '{skill_name}': Both live Groq LPU and Gemini Flash "
        f"failed to generate the prompt. (Groq Error: {groq_error}; Gemini Error: {gemini_error})"
    )
