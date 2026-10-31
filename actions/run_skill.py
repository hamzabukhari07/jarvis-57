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

import importlib
import json
import logging
import re
from pathlib import Path
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
                "description": "Optional fleet agent ID to delegate to (e.g., 'pam', 'verve', 'flux', 'nexus'). Omit or pass 'zezo' for direct execution by Zezo.",
            },
            "executor": {
                "type": "STRING",
                "description": "Optional execution mode: 'zezo' to execute directly without sub-agents, or 'fleet' to delegate.",
            },
            "direct": {
                "type": "BOOLEAN",
                "description": "Set to true to force Zezo to execute the skill directly without fleet delegation.",
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

    fleet_target: Optional[str] = (params.get("fleet_agent") or params.get("agent_id") or "").strip()
    user_task = params.get("task") or f"Execute skill {resolved_name}"
    is_direct: bool = (
        bool(params.get("direct"))
        or str(params.get("executor", "")).lower() in ("zezo", "self", "direct", "local")
        or str(fleet_target).lower() in ("zezo", "none", "self")
        or any(k in user_task.lower() for k in ("khud", "zezo khud", "yourself", "direct"))
    )

    # ── 2. Check for Engine-Only or Fleet Delegation ─────────────────────────
    # Engine skills (generate_design_md, website_build, website_clone) use the Universal Skill Prompt Engineer
    if resolved_name in ("generate_design_md", "website_build", "website_clone"):
        sop_content = skill_reg.read_skill(resolved_name)
        raw_target = (params.get("path") or params.get("project_path") or "").strip()
        url_match = re.search(r"https?://[^\s\"'>]+", f"{user_task} {raw_user_params}")
        target_url = url_match.group(0).rstrip(".,;)") if url_match else None

        if not raw_target or raw_target in (".", "Desktop", "desktop"):
            from core.repo_context import get_unique_project_dir
            if target_url:
                try:
                    import urllib.parse
                    domain_hint = urllib.parse.urlparse(target_url).netloc.replace("www.", "").split(".")[0]
                    target_dir = str(get_unique_project_dir(f"{domain_hint} clone" if resolved_name == "website_clone" else f"{domain_hint} {resolved_name}"))
                except Exception:
                    target_dir = str(get_unique_project_dir(user_task or resolved_name))
            else:
                target_dir = str(get_unique_project_dir(user_task or resolved_name))
        else:
            target_dir = raw_target

        # Generic Pre-Flight Execution Hook (Zero Hardcoding via Dynamic Dispatch)
        pre_flight = getattr(skill_record, "pre_flight_action", None)
        pre_flight_ok = True
        if pre_flight:
            try:
                # Dynamically import handler based on frontmatter tag
                # e.g., if pre_flight is "uncage_capture", it imports actions.uncage_capture_handler
                handler_module = importlib.import_module(f"actions.{pre_flight}_handler")

                td_path = Path(target_dir).resolve()
                td_path.mkdir(parents=True, exist_ok=True)

                if hasattr(handler_module, "execute"):
                    pre_flight_ok = handler_module.execute(url=target_url, output_dir=td_path, params=raw_user_params)
                    if pre_flight_ok:
                        logger.info("[run_skill] Pre-flight action '%s' completed successfully.", pre_flight)
                    else:
                        logger.warning("[run_skill] Pre-flight action '%s' returned failure status.", pre_flight)
            except ImportError:
                logger.warning("[run_skill] No handler found for pre_flight action: %s", pre_flight)
                pre_flight_ok = False
            except Exception as e_pref:
                logger.error("[run_skill] Pre-flight action '%s' failed: %s", pre_flight, e_pref)
                pre_flight_ok = False

        # Resolve optional directive header from skill record
        directive_hdr = getattr(skill_record, "agent_directive_section", None)

        try:
            from core.pending_intent import set_pending_intent
            set_pending_intent(
                task=user_task,
                action="run_skill",
                params=raw_user_params,
                target_dir=str(target_dir),
                skill_name=resolved_name,
                engine="antigravity",
            )
        except Exception as _ep:
            logger.debug("[run_skill] Pending intent note: %s", _ep)

        if is_direct:
            # Direct Zezo execution: reads SKILL.md, invokes coding engine directly without fleet/worktree quarantine
            try:
                from core.skill_prompt_engineer import craft_skill_engine_prompt
                from actions.antigravity_agent import antigravity_action

                full_prompt = craft_skill_engine_prompt(
                    skill_name=resolved_name,
                    skill_sop=sop_content,
                    user_task=user_task,
                    target_dir=target_dir,
                    context=raw_user_params,
                    engine="antigravity",
                    directive_header=directive_hdr,
                )
                logger.info("[run_skill] Executing skill '%s' directly by Zezo", resolved_name)
                direct_res = antigravity_action({
                    "prompt": full_prompt,
                    "project_path": target_dir,
                    "task": user_task,
                }, player=kwargs.get("player"), speak=kwargs.get("speak"))
                return f"Zezo is executing skill '{resolved_name}' directly: {direct_res}"
            except Exception as e_dir:
                logger.warning("[run_skill] Direct engine execution failed, falling back: %s", e_dir)
        else:
            # Fleet delegation to Scranton specialist
            try:
                from core.fleet_manager import get_fleet_manager
                from core.skill_prompt_engineer import craft_skill_engine_prompt

                fm = get_fleet_manager()
                target_agent = fm.get_agent(fleet_target) if fleet_target else fm.resolve_agent_for_skill(resolved_name)
                fallback_agent = "VERVE" if resolved_name == "website_build" else "PAM"
                agent_id = target_agent.id if target_agent else fallback_agent
                engine_name = getattr(target_agent, "engine", "antigravity") if target_agent else "antigravity"

                full_prompt = craft_skill_engine_prompt(
                    skill_name=resolved_name,
                    skill_sop=sop_content,
                    user_task=user_task,
                    target_dir=target_dir,
                    context=raw_user_params,
                    engine=engine_name,
                    directive_header=directive_hdr,
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

