"""
actions/fleet_control.py — Autonomous Multi-Agent Fleet Orchestration Tool.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from core.fleet_manager import fleet_manager

logger = logging.getLogger(__name__)


def _broadcast_ui(event: str, data: Dict[str, Any]) -> None:
    try:
        from core.log_bus import emit_tool_micro_event
        emit_tool_micro_event(event, "fleet_control", data)
    except Exception as e:
        logger.debug("Failed broadcasting fleet UI event %s: %s", event, e)


def _handle_dispatch(params: Dict[str, Any]) -> str:
    agent_id = str(params.get("agent_id") or "").strip()
    task = str(params.get("task") or "").strip()
    model_id = str(params.get("model_id") or params.get("model") or "").strip() or None
    if not agent_id:
        return "Error: agent_id is required to dispatch a task. Available agents can be queried with action='list_agents'."
    if not task:
        return "Error: task instruction is required to dispatch work to an agent."

    res = fleet_manager.dispatch_task(agent_id=agent_id, prompt=task, model_override=model_id)
    if not res.get("success"):
        return f"Fleet dispatch failed: {res.get('error', 'Unknown error')}"

    # Handle Michael multi-task decomposition result
    if res.get("orchestrator") == "MICHAEL":
        count = res.get("decomposed_count", 0)
        return f"Michael Scott decomposed and dispatched {count} specialist tasks to the fleet."

    task_id = res.get("task_id")
    agent_name = res.get("agent_name", agent_id)
    tool = res.get("tool", "agent")
    worktree = res.get("worktree")

    _broadcast_ui("agent_task_started", {
        "task_id": task_id,
        "agent_id": agent_id.upper(),
        "task": task,
        "tool": tool,
        "model_id": model_id,
        "worktree": worktree,
    })

    loc_str = f" in sandbox worktree '{worktree}'" if worktree else ""
    return f"Dispatched task to {agent_name} ({tool}){loc_str}. Task ID: {task_id}."


def _handle_hire(params: Dict[str, Any]) -> str:
    name = str(params.get("agent_id") or params.get("name") or "Agent").strip()
    role = str(params.get("role") or "Autonomous Specialist").strip()
    tool = str(params.get("default_tool") or "kilo_run").strip()
    model_id = str(params.get("model_id") or params.get("model") or "").strip()
    specialty = str(params.get("specialty") or role).strip()

    profile_data = {
        "id": name.upper(),
        "name": name.title(),
        "role": role,
        "specialty": specialty,
        "default_tool": tool,
        "model_id": model_id,
        "risk_tier": "L1_MUTATION" if tool in ("kilo_run", "opencode_run", "antigravity_run") else "L0_READ_ONLY",
    }
    res = fleet_manager.save_agent_profile(profile_data)
    if not res.get("success"):
        return f"Failed to hire agent: {res.get('error', 'Unknown error')}"

    _broadcast_ui("fleet_updated", {"action": "hire", "agent": res.get("agent")})
    return f"Hired new fleet agent '{name.title()}' as {role} utilizing {tool}."


def _handle_fire(params: Dict[str, Any]) -> str:
    agent_id = str(params.get("agent_id") or "").strip()
    if not agent_id:
        return "Error: agent_id is required to decommission an agent."

    res = fleet_manager.delete_agent(agent_id)
    if not res.get("success"):
        return f"Failed to remove agent: {res.get('error', 'Agent not found')}"

    _broadcast_ui("fleet_updated", {"action": "fire", "deleted_id": res.get("deleted_id")})
    return f"Decommissioned agent '{agent_id.upper()}' from the active fleet."


def _handle_list(params: Dict[str, Any]) -> str:
    deck = fleet_manager.get_fleet_deck_state()
    if not deck:
        return "No agents currently registered in the active fleet."

    lines = [f"Active Fleet Roster ({len(deck)} agents):"]
    for a in deck:
        status_str = f"[{a['status'].upper()}]"
        if a.get("task_title"):
            status_str += f" - {a['task_title'][:30]}"
        lines.append(f"• {a['name']} ({a['role']}) -> Tool: {a['default_tool']} {status_str}")

    return "\n".join(lines)


def _handle_status(params: Dict[str, Any]) -> str:
    agent_id = str(params.get("agent_id") or "").strip()
    if not agent_id:
        return _handle_list(params)

    profile = fleet_manager.get_agent_full_profile(agent_id)
    if not profile.get("success"):
        return f"Error: {profile.get('error', 'Agent not found')}"

    agent = profile.get("agent", {})
    task_info = profile.get("task_info")
    status = agent.get("status", "idle")

    if task_info:
        return (
            f"Agent {agent.get('name')} is currently {status.upper()} on task: '{task_info.get('title')}' "
            f"({task_info.get('progress', 0)}% complete, elapsed: {task_info.get('elapsed', '0s')})."
        )
    return f"Agent {agent.get('name')} ({agent.get('role')}) is currently {status.upper()} and ready for assignments."


_ACTION_DISPATCH: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "dispatch": _handle_dispatch,
    "hire": _handle_hire,
    "fire": _handle_fire,
    "list_agents": _handle_list,
    "list": _handle_list,
    "get_status": _handle_status,
    "status": _handle_status,
}


def fleet_control(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """Main entrypoint for autonomous fleet control and delegation."""
    action = str(parameters.get("action") or "list_agents").strip().lower()
    handler_fn = _ACTION_DISPATCH.get(action)
    if not handler_fn:
        return f"Unknown fleet_control action '{action}'. Supported actions: {', '.join(sorted(_ACTION_DISPATCH.keys()))}"
    return handler_fn(parameters)


TOOL = {
    "name": "fleet_control",
    "description": (
        "Orchestrate autonomous multi-agent fleet. Dispatch coding tasks to named specialist workers "
        "(Michael, Dwight, Jim, Pam, or custom agents), hire new specialist agents, query agent status "
        "and active tasks, or manage agent personas. "
        "Use this whenever the user asks a specific agent to do something ('Michael ko bolo...', 'Dwight assign this task', "
        "'Pam check UI', 'Hire new QA agent Stanley') or asks for fleet status ('fleet status kya hai', 'kaun kaun se agents hain')."
    ),
    "risk": "local_mutation",
    "enabled": True,
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["dispatch", "hire", "fire", "list_agents", "get_status"],
                "description": "The fleet management action to execute.",
            },
            "agent_id": {
                "type": "STRING",
                "description": "Target agent codename or ID (e.g. 'MICHAEL', 'DWIGHT', 'JIM', 'PAM', or custom name).",
            },
            "task": {
                "type": "STRING",
                "description": "The precise coding objective, bug fix, or analysis instruction to assign.",
            },
            "role": {
                "type": "STRING",
                "description": "Role or title when hiring a new agent (e.g. 'Database Architect', 'QA Tester').",
            },
            "default_tool": {
                "type": "STRING",
                "enum": ["opencode_run", "kilo_run", "dev_agent", "code_helper", "antigravity_run"],
                "description": "Underlying execution engine assigned to this agent.",
            },
            "model_id": {
                "type": "STRING",
                "description": "Specific LLM model identifier (e.g. 'kilo/stepfun/step-3.7-flash:free').",
            },
            "specialty": {
                "type": "STRING",
                "description": "Agent technical specialty or focus area.",
            },
        },
        "required": ["action"],
    },
    "handler": fleet_control,
}

handler = fleet_control
