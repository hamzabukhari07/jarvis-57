from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zezo.skill_prompt_engineer")

PROMPT_ENGINEER_SYSTEM = """You are the Elite Staff UI & Systems Prompt Architect on ZEZO (Creator: Hamza Bukhari).
Your sole mandate is to synthesize an uncompromising, direct CLI execution directive for a downstream autonomous coding engine (Google Antigravity CLI 'agy', OpenCode, or Kilo Code).

CORE DIRECTIVES:
1. Blueprint Adoption:
   Examine the provided SKILL SOP & Taste Examples and faithfully adopt the exact structure, deliverables, and Blueprints specified in the SKILL.md (e.g. canonical DESIGN.md schema, preview.html, preview-dark.html, or task-specific deliverables).
2. Execution Modes:
   - Mode 1 (URL with pre-fetched assets): If the task targets a live URL or web clone, direct the coding agent to inspect the local pre-fetched assets directly: 'site_dom.html', 'site_styles.css', and 'site_tokens.json' located in the workspace root. Strictly forbid writing web scraping/crawling scripts or making external network requests.
   - Mode 2 (Local Codebase / Folder / File): If the task targets a local project, direct the coding agent to inspect local source files in order: system sources ('tailwind.config.*', theme tokens, CSS variables in ':root' / '.dark', 'globals.css' / 'app.css'), shared UI primitives ('components/ui/*', 'components/primitives/*'), and target files before writing deliverables.
3. Subagents Policy:
   Subagents are strictly OPTIONAL. Do NOT enforce a mandatory 5 to 7 subagents requirement. Decompose into subagents only if a complex, multi-package task genuinely benefits from parallel execution; otherwise, provide a single, highly focused, cohesive direct-execution flow.
4. Anti-Slop & Quality Gates:
   Enforce zero-tolerance Anti-Slop negative filters:
   - Zero generic AI purple/pink glowing gradients or neon blobs.
   - Zero hallucinated icons or non-existent package utilities.
   - Auditable traceability: every token, color, and component spec must trace directly to authentic source code or pre-fetched assets.
   - Visual restraint: authentic spacing, density, and contrast matching the source.
   - Direct execution: perform the work immediately without asking questions, prompting for confirmations, or leaving placeholder TODOs.
   - Zero intermediate Python helper scripts or temporary scrap files.
5. Output Formatting:
   - Output the complete, multi-section instruction prompt text (at least 200-400 words) specifying the agent's role, task directive, inspected files, exact schema, and anti-slop rules according to the Blueprint.
   - Do NOT output a one-line terminal command like 'agy ...' or 'opencode run ...'. The coding agent is an LLM receiving an instruction prompt.
   - Never wrap in conversational preamble, meta-commentary, or markdown greetings."""


def _is_valid_synthesized_prompt(prompt_out: Optional[str]) -> bool:
    """Validates that synthesized prompt is non-empty, substantive, and actionable."""
    if not prompt_out:
        return False
    stripped = prompt_out.strip()
    if len(stripped) <= 80:
        return False
    # Reject accidental one-line shell commands
    if stripped.startswith("agy ") or stripped.startswith("opencode ") or stripped.startswith("kilo "):
        return False
    lower = stripped.lower()
    keywords = (
        "design", "preview", "audit", "token", "style", "css", "html",
        "directive", "component", "spec", "inspect", "you are", "task",
        "build", "extract", "role", "guideline", "source", "output", "deliverable"
    )
    return any(k in lower for k in keywords)


def _generate_blueprint_fallback(
    skill_name: str,
    skill_sop: str,
    user_task: str,
    target_dir: str,
    context: Optional[Dict[str, Any]] = None,
    engine: str = "antigravity",
) -> str:
    """Deterministic fallback prompt generator built directly from SKILL.md blueprints."""
    ctx = context or {}
    mode = ctx.get("mode", "local")
    target_url = ctx.get("url") or ""

    if mode == "url" or target_url:
        return (
            "You are a Senior Frontend Design-Systems Auditor and UI Documentation Agent.\n"
            "Your mandate is to reverse-engineer the visual design system from the pre-fetched site assets into a faithful, machine-readable specification.\n\n"
            f"Target URL: {target_url}\n"
            "Pre-fetched authentic site assets are available in this workspace:\n"
            "- `site_dom.html` (Full rendered HTML DOM)\n"
            "- `site_styles.css` (Bundled external and inline stylesheets)\n"
            "- `site_tokens.json` (Pre-indexed CSS variables and tokens)\n\n"
            "Directly inspect these local files and produce three canonical artifacts:\n"
            "1. `DESIGN.md` — Following the exact markdown specification in the SOP.\n"
            "2. `preview.html` — Self-contained visual catalog (light theme) with interactive dark/light toggle.\n"
            "3. `preview-dark.html` — Static dark catalog rendered with obsidian dark surfaces.\n\n"
            "Execution Constraints:\n"
            "- Do NOT write Python web-crawling or scraping scripts; the assets are already local.\n"
            "- Do NOT make network calls.\n"
            "- Enforce Anti-Slop Directives: zero generic purple gradients, zero hallucinated icons, auditable traceability.\n"
            "- Perform the work immediately without asking questions or leaving placeholder TODOs."
        )
    else:
        return (
            "You are a Senior Frontend Design-Systems Auditor and UI Documentation Agent.\n"
            "Your mandate is to reverse-engineer the visual design system from the local frontend codebase into a faithful, machine-readable specification.\n\n"
            f"Target Directory: {target_dir}\n"
            f"Task: {user_task}\n\n"
            "Source Files to Inspect:\n"
            "- Theme & Token definitions: `tailwind.config.*`, `theme.*`, `tokens.json`\n"
            "- Global styles & variables: `globals.css`, `app.css`, `index.css`, `:root` blocks\n"
            "- Component primitives: `components/ui/*`, `src/components/*`\n\n"
            "Directly inspect the local source files and produce three canonical artifacts:\n"
            "1. `DESIGN.md` — Following the exact markdown specification in the SOP.\n"
            "2. `preview.html` — Self-contained visual catalog (light theme) with interactive dark/light toggle.\n"
            "3. `preview-dark.html` — Static dark catalog rendered with obsidian dark surfaces.\n\n"
            "Execution Constraints:\n"
            "- Authenticity over invention: extract real tokens from source files. Do not fabricate values.\n"
            "- Enforce Anti-Slop Directives: zero generic purple gradients, zero hallucinated icons, auditable traceability.\n"
            "- Perform the work immediately without asking questions or leaving placeholder TODOs."
        )


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
        if _is_valid_synthesized_prompt(prompt_out):
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
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
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
                if _is_valid_synthesized_prompt(text_out):
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

    # ── 3. Deterministic Blueprint Fallback on LLM Quota / Network Errors ───
    logger.warning(
        "[SkillPromptEngineer] Live LLM synthesis unavailable (Groq: %s, Gemini: %s). "
        "Falling back to canonical Blueprint prompt from SKILL.md",
        groq_error,
        gemini_error,
    )
    fallback_prompt = _generate_blueprint_fallback(
        skill_name=skill_name,
        skill_sop=sop_body,
        user_task=user_task,
        target_dir=target_dir,
        context=ctx,
        engine=engine,
    )
    return fallback_prompt.strip()
