from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zezo.skill_prompt_engineer")

PROMPT_ENGINEER_SYSTEM = """You are an AI Prompt Architect for autonomous coding engines (Google Antigravity 'agy', OpenCode, Kilo Code).
Your sole purpose is to translate the user's task request and skill guidelines into a clear, direct, and actionable execution prompt for the coding agent.

Core Principles:
1. Natural & Actionable: Tell the coding agent directly what needs to be created, modified, or extracted in the workspace. Avoid artificial personas, theatrical roleplay, or bureaucratic essays.
2. Respect User Scope: Focus strictly on what the user asked for. Do not mandate unrequested extra files, schemas, or arbitrary deliverables.
3. Ground in Actual Files: Refer only to files that actually exist in the workspace directory. Never assume pre-fetched assets exist unless confirmed in the workspace context.
4. Autonomous Execution: Direct the coding agent to complete the task thoroughly and self-contained without asking intermediate questions or leaving placeholder TODOs.
5. Output Format: Output only the instruction prompt text for the coding agent. Never include conversational greetings or meta-commentary."""


def _is_valid_synthesized_prompt(prompt_out: Optional[str]) -> bool:
    """Validates that synthesized prompt is non-empty, substantive, and actionable."""
    if not prompt_out:
        return False
    stripped = prompt_out.strip()
    if len(stripped) <= 40:
        return False
    # Reject accidental one-line shell commands
    if stripped.startswith("agy ") or stripped.startswith("opencode ") or stripped.startswith("kilo "):
        return False
    return True


def _inspect_workspace_state(target_dir: str) -> Dict[str, Any]:
    """Inspect actual workspace files to prevent prompt hallucination."""
    try:
        p = Path(target_dir).resolve() if target_dir else None
        if not p or not p.exists():
            return {
                "exists": False,
                "existing_files": [],
                "summary": "Workspace directory does not exist yet (fresh project).",
            }
        files = [f.name for f in p.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not files:
            return {
                "exists": True,
                "existing_files": [],
                "summary": "Workspace directory is empty (fresh project).",
            }
        return {
            "exists": True,
            "existing_files": files[:25],
            "summary": f"Existing files in workspace: {', '.join(files[:25])}",
        }
    except Exception as e:
        return {
            "exists": False,
            "existing_files": [],
            "summary": f"Could not inspect workspace: {e}",
        }


def _generate_blueprint_fallback(
    skill_name: str,
    skill_sop: str,
    user_task: str,
    target_dir: str,
    context: Optional[Dict[str, Any]] = None,
    engine: str = "antigravity",
) -> str:
    """Deterministic, natural fallback prompt derived from the user task and skill."""
    ws = _inspect_workspace_state(target_dir)
    ws_notes = f"\nWorkspace Status: {ws['summary']}" if ws.get("summary") else ""
    return (
        f"You are an autonomous coding agent ({engine.upper()}) working in: {target_dir}\n\n"
        f"Task: {user_task}\n"
        f"Skill: {skill_name}\n"
        f"{ws_notes}\n\n"
        "Directives:\n"
        "1. Inspect the workspace directory and review any existing files.\n"
        "2. Complete the requested task directly, creating all necessary functional files.\n"
        "3. Ensure the implementation is complete, authentic, self-contained, and free of placeholder TODOs.\n"
    ).strip()


def _extract_agent_directive(sop_text: str, directive_header: Optional[str] = None) -> str:
    """Extracts the agent directive section if specified, else returns safe instructions."""
    if not sop_text:
        return ""
    if directive_header:
        clean_hdr = re.escape(directive_header.strip())
        # Match ## [optional emoji/prefix] <Header> ... until next ## or EOF
        pattern = rf"(?i)(?:^|\n)##\s*[^\n]*?{clean_hdr}[^\n]*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, sop_text, re.DOTALL)
        if match and match.group(1).strip():
            return match.group(1).strip()

        # Smart Fallback: If named header missing, grab the last ## section
        # (where deliverables/prompts are positioned) to prevent CLI leak
        sections = re.findall(r"(?i)(?:^|\n)##\s*[^\n]+\n(.*?)(?=\n##\s|\Z)", sop_text, re.DOTALL)
        if sections:
            return sections[-1].strip()

    return sop_text


def craft_skill_engine_prompt(
    skill_name: str,
    skill_sop: str,
    user_task: str,
    target_dir: str,
    context: Optional[Dict[str, Any]] = None,
    engine: str = "antigravity",
    directive_header: Optional[str] = None,
) -> str:
    """Synthesizes a bespoke execution prompt using live AI models (Groq LPU / Gemini Flash).

    Order of execution:
      1. Primary: Groq LPU (llama-3.3-70b-versatile, ~150-200ms)
      2. Secondary: Google Gemini Flash (gemini-2.5-flash, gemini-2.0-flash)
      3. Fallback: Natural dynamic blueprint prompt based on actual workspace files.
    """
    ctx = context or {}
    start_t = time.time()

    ws = _inspect_workspace_state(target_dir)

    # Filter by agent directive section if specified to prevent pre-flight/CLI leak
    sop_body = _extract_agent_directive((skill_sop or "").strip(), directive_header)
    if len(sop_body) > 6500:
        sop_body = sop_body[:6300] + "\n\n... [SOP truncated for prompt synthesis] ..."

    briefing = (
        f"=== TARGET SKILL: {skill_name.upper()} ===\n"
        f"Target Engine: {engine.upper()}\n"
        f"Target Directory: {target_dir}\n"
        f"Workspace Status: {ws['summary']}\n"
        f"User Task Request: {user_task}\n\n"
        f"Context Details:\n{json.dumps(ctx, indent=2)}\n\n"
        f"=== SKILL GUIDELINES ===\n"
        f"{sop_body}\n\n"
        "Synthesize a clear, direct, natural instruction prompt for the coding agent now:"
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
                "[SkillPromptEngineer] Synthesized natural prompt via Groq LPU in %.2fs (%d chars)",
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

    # ── 2. Secondary Engine: Gemini Flash Fallback ──────────────────────────
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
                        "[SkillPromptEngineer] Synthesized natural prompt via Gemini (%s) in %.2fs",
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

    # ── 3. Natural Fallback on LLM Quota / Network Errors ──────────────────
    logger.warning(
        "[SkillPromptEngineer] Live LLM synthesis unavailable (Groq: %s, Gemini: %s). "
        "Using natural blueprint prompt fallback.",
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
