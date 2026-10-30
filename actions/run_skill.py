"""
actions/run_skill.py — Dual-AI Skill Runner Action.

Creator & Lead Architect: Hamza Bukhari

Orchestrates declarative procedural skills (skills/<skill_name>/SKILL.md) through
either:
  1. Dual-AI Sequential Execution (Groq LPU with stateful Gemini-3.8-Flash fallback).
  2. Autonomous Fleet Delegation (FleetDispatcher) when configured for specialized agents.

Returns immediately (<50ms) with conversational acknowledgment while coordinating
work in background worker threads via TaskManager.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

TOOL = {
    "name": "run_skill",
    "description": (
        "Execute a procedural skill workflow using the Dual-AI Skill Runner. "
        "Coordinates atomic tool sequences via Groq LPU with stateful Gemini-3.8-Flash fallback, "
        "or routes to an autonomous fleet agent if fleet delegation is configured."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "skill_name": {
                "type": "STRING",
                "description": "Identifier of the skill to execute (e.g., 'git_workflow', 'make_plan', 'office_suite', 'website_build').",
            },
            "parameters": {
                "type": "OBJECT",
                "description": "Execution parameters, variables, or user intent passed to the skill.",
            },
            "task": {
                "type": "STRING",
                "description": "Optional textual description of the specific task to perform under this skill.",
            },
            "fleet_agent": {
                "type": "STRING",
                "description": "Optional fleet agent ID to delegate to (e.g., 'verve', 'flux', 'nexus').",
            },
        },
        "required": ["skill_name"],
    },
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
}


def _execute_skill_worker(params: dict, task_ctx: Any) -> dict:
    """Background worker function executed by TaskManager daemon thread."""
    from core.skill_runner import SkillRunner

    runner = SkillRunner(
        skill_name=params.get("skill_name", ""),
        user_params=params.get("user_params") or {},
        context=params.get("context") or {},
        task_ctx=task_ctx,
    )
    return runner.run()


def handler(parameters: dict, **kwargs: Any) -> str:
    """Dispatches the skill to either FleetDispatcher or SkillRunner."""
    params = parameters or {}
    skill_name = (params.get("skill_name") or params.get("skill") or "").strip()
    if not skill_name:
        return "Please specify the name of the skill you want me to execute."

    from core.skill_loader import get_skill_registry

    skill_reg = get_skill_registry()

    # ── 1. Check if Skill Exists in Registry ─────────────────────────────────
    skill_record = None
    resolved_name = skill_name

    if hasattr(skill_reg, "_skills"):
        if skill_name in skill_reg._skills:
            skill_record = skill_reg._skills[skill_name]
            resolved_name = skill_name
        else:
            for k, s in skill_reg._skills.items():
                if skill_name.lower() in k.lower() or k.lower() in skill_name.lower():
                    skill_record = s
                    resolved_name = k
                    break

    if not skill_record:
        # Fall back to read_skill check
        content = skill_reg.read_skill(skill_name)
        if "not found" in content.lower():
            available = list(skill_reg._skills.keys()) if hasattr(skill_reg, "_skills") else []
            preview = ", ".join(available[:8]) if available else "None"
            return f"Skill '{skill_name}' was not found in the registry. Available skills include: {preview}."

    # Consolidate user parameters & task description
    raw_user_params = params.get("parameters") or {}
    if not isinstance(raw_user_params, dict):
        raw_user_params = {"input": str(raw_user_params)}

    if params.get("task"):
        raw_user_params["task"] = params.get("task")

    # ── 2. Check for Engine-Only or Fleet Delegation ─────────────────────────
    # Engine skills (generate_design_md, website_build, website_clone) use the Universal Skill Prompt Engineer
    if resolved_name in ("generate_design_md", "website_build", "website_clone"):
        try:
            from core.fleet_manager import get_fleet_manager
            from core.skill_prompt_engineer import craft_skill_engine_prompt

            fm = get_fleet_manager()
            target_agent = fm.resolve_agent_for_skill(resolved_name)
            fallback_agent = "VERVE" if resolved_name == "website_build" else "PAM"
            agent_id = target_agent.id if target_agent else fallback_agent
            engine_name = getattr(target_agent, "engine", "antigravity") if target_agent else "antigravity"

            sop_content = skill_reg.read_skill(resolved_name)
            target_dir = params.get("path") or params.get("project_path") or "."
            user_task = params.get("task") or f"Execute skill {resolved_name}"

            full_prompt = craft_skill_engine_prompt(
                skill_name=resolved_name,
                skill_sop=sop_content,
                user_task=user_task,
                target_dir=target_dir,
                context=raw_user_params,
                engine=engine_name,
            )

            dispatch_res = fm.dispatcher.dispatch_task(
                agent_id=agent_id,
                prompt=full_prompt,
                path=target_dir,
                session_memory=kwargs.get("session_memory"),
            )
            task_id = dispatch_res.get("task_id") or "active"
            return (
                f"Dispatched engine skill '{resolved_name}' to agent '{agent_id}' via coding engine "
                f"(task: {task_id})."
            )
        except Exception as e:
            logger.warning("[run_skill] Engine delegation for %s failed: %s", resolved_name, e)

    fleet_target: Optional[str] = (params.get("fleet_agent") or params.get("agent_id") or "").strip()

    if not fleet_target:
        # Check if fleet agents have this skill configured in allowed_skills
        try:
            from core.fleet_manager import get_fleet_manager

            fm = get_fleet_manager()
            for aid, agent in fm.agents.items():
                allowed = getattr(agent, "allowed_skills", []) or []
                if resolved_name in allowed:
                    tags = getattr(skill_record, "tags", []) or []
                    domain = getattr(skill_record, "domain", "")
                    if "fleet" in tags or domain == "fleet" or params.get("delegate") is True:
                        fleet_target = aid
                        break
        except Exception as e:
            logger.debug("[run_skill] Fleet delegation check note: %s", e)

    if fleet_target:
        try:
            from core.fleet_manager import get_fleet_manager

            fm = get_fleet_manager()
            prompt = (
                params.get("task")
                or json.dumps(raw_user_params)
                or f"Execute procedural skill: {resolved_name}"
            )
            dispatch_res = fm.dispatcher.dispatch_task(
                agent_id=fleet_target,
                prompt=f"Execute skill '{resolved_name}': {prompt}",
                session_memory=kwargs.get("session_memory"),
            )
            task_id = dispatch_res.get("task_id") or "active"
            return (
                f"Delegated skill '{resolved_name}' to autonomous fleet agent '{fleet_target}' "
                f"(task: {task_id})."
            )
        except Exception as e:
            logger.warning("[run_skill] Fleet dispatch failed, falling back to local runner: %s", e)

    # ── 3. Route to SkillRunner via Background TaskManager ───────────────────
    from core.task_manager import get_task_manager

    tm = get_task_manager()
    worker_payload = {
        "skill_name": resolved_name,
        "user_params": raw_user_params,
        "context": kwargs.get("context") or {},
    }

    task_id = tm.submit(
        "run_skill",
        _execute_skill_worker,
        worker_payload,
        group_title=f"Skill: {resolved_name}",
    )

    return (
        f"Started skill '{resolved_name}' in the background (task {task_id}). "
        "The Dual-AI engine is coordinating the atomic steps now."
    )


TOOL["handler"] = handler
TOOL["risk"] = "local_mutation"

