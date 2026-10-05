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
        from core.ui_server import get_ui_server
        get_ui_server().broadcast(event, data)
    except Exception as e:
        logger.debug("Failed broadcasting UI server event %s: %s", event, e)
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


def _handle_update(params: Dict[str, Any]) -> str:
    agent_id = str(params.get("agent_id") or params.get("name") or "").strip()
    if not agent_id:
        return "Error: agent_id is required to update an agent persona."

    existing = fleet_manager.get_agent(agent_id)
    if not existing:
        return f"Error: Agent '{agent_id}' not found in the active fleet roster."

    profile_data: Dict[str, Any] = {
        "id": existing.id,
        "name": str(params.get("name") or existing.name).strip(),
        "role": str(params.get("role") or existing.role).strip(),
        "specialty": str(params.get("specialty") or existing.specialty).strip(),
        "default_tool": str(params.get("default_tool") or existing.default_tool).strip(),
        "model_id": str(params.get("model_id") or params.get("model") or existing.model_id).strip(),
        "desk_x": existing.desk_x,
        "desk_y": existing.desk_y,
        "color": existing.color,
        "avatar_pixel": existing.avatar_pixel,
        "prompt_prefix": str(params.get("prompt_prefix") or existing.prompt_prefix).strip(),
    }

    if "allowed_tools" in params:
        raw_tools = params["allowed_tools"]
        profile_data["allowed_tools"] = [t.strip() for t in raw_tools if str(t).strip()] if isinstance(raw_tools, list) else [t.strip() for t in str(raw_tools).split(",") if t.strip()]
    if "allowed_skills" in params:
        raw_skills = params["allowed_skills"]
        profile_data["allowed_skills"] = [s.strip() for s in raw_skills if str(s).strip()] if isinstance(raw_skills, list) else [s.strip() for s in str(raw_skills).split(",") if s.strip()]
    if "capabilities" in params:
        raw_caps = params["capabilities"]
        profile_data["capabilities"] = [c.strip() for c in raw_caps if str(c).strip()] if isinstance(raw_caps, list) else [c.strip() for c in str(raw_caps).split(",") if c.strip()]

    res = fleet_manager.save_agent_profile(profile_data)
    if not res.get("success"):
        return f"Failed to update agent '{existing.name}': {res.get('error', 'Unknown error')}"

    updated = res.get("agent", {})
    _broadcast_ui("fleet_updated", {"action": "update", "agent": updated})
    return f"Successfully updated profile for agent '{existing.name}' (Role: {updated.get('role')}, Tool: {updated.get('default_tool')}, Tools: {', '.join(updated.get('allowed_tools', []))})."


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


def _handle_peer_chat(params: Dict[str, Any]) -> str:
    from_agent = str(params.get("from_agent") or "ZEZO").strip()
    to_agent = str(params.get("to_agent") or params.get("agent_id") or "").strip()
    message = str(params.get("message") or params.get("task") or "").strip()
    upstream = str(params.get("upstream_deliverables") or params.get("context") or "").strip() or None
    path = params.get("path")

    if not to_agent:
        return "Error: to_agent or agent_id is required for peer delegation."
    if not message:
        return "Error: message / task instruction is required for peer delegation."

    res = fleet_manager.delegate_peer_task(
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        task=message,
        upstream_deliverables=upstream,
        path=path,
    )
    if not res.get("success"):
        return f"Peer delegation failed: {res.get('error', 'Unknown error')}"

    task_id = res.get("task_id")
    target_name = res.get("agent_name", to_agent)
    tool = res.get("tool", "agent")
    sess_id = res.get("peer_session_id")

    _broadcast_ui("peer_delegation_started", {
        "task_id": task_id,
        "peer_session_id": sess_id,
        "from_agent": from_agent.upper(),
        "to_agent": res.get("to_agent"),
        "task": message,
        "tool": tool,
    })

    return f"Peer delegation active: {from_agent.upper()} -> {target_name} ({tool}). Task ID: {task_id}."


def _handle_decompose(params: Dict[str, Any]) -> str:
    prompt = str(params.get("task") or params.get("prompt") or "").strip()
    path = params.get("path")
    if not prompt:
        return "Error: task prompt is required for workflow decomposition."

    res = fleet_manager.decompose_and_dispatch(prompt, path=path)
    count = res.get("decomposed_count", 0)
    tasks = res.get("tasks", [])
    task_summaries = [f"• {t.get('agent_name', t.get('agent_id'))} ({t.get('tool')}) [ID: {t.get('task_id')}]" for t in tasks if t.get("success")]
    
    _broadcast_ui("workflow_decomposed", {
        "task": prompt,
        "count": count,
        "tasks": tasks,
    })

    return f"Michael Scott decomposed and dispatched {count} specialist tasks:\n" + "\n".join(task_summaries)


_ACTION_DISPATCH: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "dispatch": _handle_dispatch,
    "hire": _handle_hire,
    "fire": _handle_fire,
    "update": _handle_update,
    "edit": _handle_update,
    "modify": _handle_update,
    "list_agents": _handle_list,
    "list": _handle_list,
    "get_status": _handle_status,
    "status": _handle_status,
    "peer_chat": _handle_peer_chat,
    "delegate": _handle_peer_chat,
    "decompose_workflow": _handle_decompose,
    "decompose": _handle_decompose,
}


def fleet_control(parameters: Dict[str, Any], **kwargs: Any) -> str:
    """Main entrypoint for autonomous fleet control, delegation, and P2P peer routing."""
    action = str(parameters.get("action") or "list_agents").strip().lower()
    handler_fn = _ACTION_DISPATCH.get(action)
    if not handler_fn:
        return f"Unknown fleet_control action '{action}'. Supported actions: {', '.join(sorted(_ACTION_DISPATCH.keys()))}"
    return handler_fn(parameters)


TOOL = {
    "name": "fleet_control",
    "description": (
        "Orchestrate autonomous multi-agent fleet. Dispatch coding/research tasks to named specialist workers "
        "(Ali, Ahmad, Dwight, Pam, Oscar, Kelly, Michael, Quantum), trigger P2P peer handoffs with upstream deliverables, "
        "decompose multi-stage workflows, hire/fire/update agents, or query agent status. "
        "Use action='update' whenever the user wants to change an agent's role, name, specialty, allowed tools, or model. "
        "Use this whenever the user addresses a specific agent ('Tell Ali to build a landing page', 'Kelly/Quantum transcribe and summarize this video', "
        "'Ahmad build the auth API', 'Michael decompose this project') or for peer handoffs between agents."
    ),
    "risk": "local_mutation",
    "enabled": True,
    "behavior": "BLOCKING",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["dispatch", "hire", "fire", "update", "edit", "list_agents", "get_status", "peer_chat", "decompose_workflow"],
                "description": "The fleet management action to execute.",
            },
            "agent_id": {
                "type": "STRING",
                "description": "Target agent name or ID (e.g. 'ALI', 'AHMAD', 'DWIGHT', 'PAM', 'OSCAR', 'KELLY', 'MICHAEL', 'QUANTUM').",
            },
            "from_agent": {
                "type": "STRING",
                "description": "Originating agent ID for P2P delegation (e.g. 'KELLY', 'MICHAEL', 'ZEZO').",
            },
            "to_agent": {
                "type": "STRING",
                "description": "Destination agent ID for P2P delegation (e.g. 'ALI', 'AHMAD', 'DWIGHT').",
            },
            "task": {
                "type": "STRING",
                "description": "The precise coding, research, or analysis objective to assign.",
            },
            "upstream_deliverables": {
                "type": "STRING",
                "description": "Extracted deliverables, analysis findings, or code from an upstream agent to inject into the recipient agent's context.",
            },
            "role": {
                "type": "STRING",
                "description": "Role or title when hiring or updating an agent (e.g. 'Detailed Web Researcher', 'Database Architect', 'QA Tester').",
            },
            "default_tool": {
                "type": "STRING",
                "enum": ["opencode_run", "kilo_run", "quick_snippet", "antigravity_run", "extract_design_system", "agent_reach", "web_search", "web_read_page"],
                "description": "Underlying execution engine assigned to this agent.",
            },
            "allowed_tools": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of specific action tool IDs permitted for this agent (e.g. ['agent_reach', 'web_search', 'web_read_page']).",
            },
            "model_id": {
                "type": "STRING",
                "description": "Specific LLM model identifier (e.g. 'gemini-3.7-flash-medium', 'kilo/stepfun/step-3.7-flash:free').",
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
