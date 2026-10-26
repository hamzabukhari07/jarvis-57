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


import time

_RECENT_DISPATCHES: Dict[str, tuple[float, str, str]] = {}  # agent_id -> (timestamp, task_text, task_id)


def _handle_dispatch(params: Dict[str, Any]) -> str:
    agent_id = str(params.get("agent_id") or "").strip()
    task = str(params.get("task") or "").strip()
    model_id = str(params.get("model_id") or params.get("model") or "").strip() or None
    target_path = str(params.get("path") or params.get("project_path") or "").strip() or None
    entity_content = str(params.get("entity_content") or "").strip() or None
    if not agent_id:
        return "Error: agent_id is required to dispatch a task. Available agents can be queried with action='list_agents'."
    if not task:
        return "Error: task instruction is required to dispatch work to an agent."

    if not target_path:
        # Do not invent a default here: just make the fallback visible. Without a `path` the
        # dispatch lands in an auto-selected folder instead of the one the user named, which is
        # exactly how a real rebuild ended up running in a stale remembered repo (Issue 7a/10).
        try:
            from core.repo_context import get_last_repo
            remembered = get_last_repo()
        except Exception:
            remembered = None
        logger.warning(
            "[FleetControl] dispatch to %s received no 'path' - falling back to an auto-selected folder "
            "instead of the folder the user meant%s. Pass path=<existing folder> to work in place.",
            agent_id,
            f" (last remembered repo: {remembered})" if remembered else "",
        )

    # ── Stateless Greenfield Intake & Confirmation Gate for Fleet Builds ────
    target_agent = fleet_manager.get_agent(agent_id)
    canonical_agent_id = target_agent.id.upper() if target_agent else agent_id.upper()
    is_web_agent = canonical_agent_id in ("VERVE", "FLUX") or agent_id.upper() in ("VERVE", "FLUX", "ALI", "HAIDER")
    is_web_task = any(k in task.lower() for k in ("build website", "create website", "make a website", "make website", "build a website", "create a website", "build landing page", "create landing page", "build a landing page", "create a landing page", "build portfolio", "create portfolio", "build a portfolio", "create a portfolio", "make a portfolio", "new website", "new landing page", "new portfolio"))
    confirmed = bool(params.get("confirmed", False))
    if (is_web_agent or is_web_task) and not confirmed:
        from actions.antigravity_agent import check_greenfield_gate
        gate_params = dict(params)
        gate_params.pop("path", None)
        gate_params.pop("project_path", None)
        if entity_content:
            gate_params["entity_content"] = entity_content
        gate_msg = check_greenfield_gate(
            task=task,
            parameters=gate_params,
            caller_tool="fleet_control",
        )
        if gate_msg:
            return gate_msg

    # Enrich task with resolved stack/theme parameters upon confirmed dispatch
    stack_info = []
    if params.get("tech_stack"):
        stack_info.append(f"Stack: {params.get('tech_stack')}")
    if params.get("color_theme"):
        stack_info.append(f"Theme: {params.get('color_theme')}")
    if params.get("scope_type"):
        stack_info.append(f"Scope: {params.get('scope_type')}")
    if params.get("key_sections"):
        stack_info.append(f"Sections: {params.get('key_sections')}")
    if entity_content:
        stack_info.append(f"Entity/Content: {entity_content}")
    if stack_info:
        task = f"{task}\n" + "\n".join(f"[{item}]" for item in stack_info)

    # Debounce / deduplication check (12 seconds window for same agent and similar prompt)
    now = time.time()
    agent_key = agent_id.upper()
    if agent_key in _RECENT_DISPATCHES:
        last_time, last_task, existing_task_id = _RECENT_DISPATCHES[agent_key]
        if (now - last_time) < 12.0:
            # Check prompt similarity: identical, substring, or close length
            t1, t2 = task.lower().strip(), last_task.lower().strip()
            if t1 == t2 or t1 in t2 or t2 in t1:
                logger.info(
                    "[FleetControl] Debounced duplicate dispatch to %s within %.1fs (existing task %s)",
                    agent_key,
                    now - last_time,
                    existing_task_id,
                )
                agent_name = (fleet_manager.get_agent(agent_id) or type("Agent", (), {"name": agent_id})).name
                return f"Task already dispatched to {agent_name} and in progress. Task ID: {existing_task_id}."

    res = fleet_manager.dispatch_task(
        agent_id=agent_id,
        prompt=task,
        path=target_path,
        model_override=model_id,
        scope_type=params.get("scope_type"),
        entity_content=entity_content,
        tech_stack=params.get("tech_stack"),
        color_theme=params.get("color_theme"),
        key_sections=params.get("key_sections"),
        confirmed=bool(params.get("confirmed", False)),
    )
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

    if task_id:
        _RECENT_DISPATCHES[agent_key] = (now, task, task_id)

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
        "Orchestrate autonomous multi-agent fleet. Dispatch coding/research tasks to active specialist workers "
        "(e.g. Verve for frontend, Nexus/Ahmad for backend, Michael for architecture, Dwight for testing, Kelly for research), "
        "trigger P2P peer handoffs with upstream deliverables, decompose multi-stage workflows, hire/fire/update agents, or query agent status. "
        "Use action='update' whenever the user wants to change an agent's role, name, specialty, allowed tools, or model. "
        "Use this whenever the user addresses a specific agent ('Tell Verve to build a landing page', 'Kelly transcribe and summarize this video', "
        "'Ahmad build the auth API', 'Michael decompose this project') or for delegating work to the autonomous specialist fleet."
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
                "description": "Target agent name or ID from the active fleet roster (e.g. 'VERVE', 'FLUX', 'MICHAEL', 'AHMAD', 'DWIGHT', 'KELLY').",
            },
            "from_agent": {
                "type": "STRING",
                "description": "Originating agent ID for P2P delegation (e.g. 'KELLY', 'MICHAEL', 'ZEZO').",
            },
            "to_agent": {
                "type": "STRING",
                "description": "Destination agent ID for P2P delegation (e.g. 'VERVE', 'AHMAD', 'DWIGHT').",
            },
            "task": {
                "type": "STRING",
                "description": "The precise coding, research, or analysis objective to assign.",
            },
            "path": {
                "type": "STRING",
                "description": (
                    "Existing project folder the dispatched agent must work in (e.g. 'C:/Users/Hamza/Desktop/linear_cloned_app'). "
                    "ALWAYS pass this when the user points the agent at a folder that already exists - for example continuing a "
                    "failed website-clone rebuild. If omitted, the agent gets a brand-new folder instead."
                ),
            },
            "upstream_deliverables": {
                "type": "STRING",
                "description": "Extracted deliverables, analysis findings, or code from an upstream agent to inject into the recipient agent's context.",
            },
            "name": {
                "type": "STRING",
                "description": "Human-readable display name of the agent (e.g. 'DevDynamo', 'Dwight Schrute'). When the user asks to rename or name an agent ('call them X', 'name this agent X'), pass X as 'name', NEVER as 'role'.",
            },
            "role": {
                "type": "STRING",
                "description": "Functional job title/responsibility (e.g. 'Full-Stack Developer', 'QA Tester', 'Web Researcher'). Do NOT put an agent's proper personal name here; put their job title.",
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
            "scope_type": {
                "type": "STRING",
                "enum": ["landing_page", "portfolio", "full_website", "hero_section", "component"],
                "description": (
                    "Scope of the web build. Set ONLY if user stated (e.g. 'landing page', 'portfolio', 'full website', 'hero section', 'pricing card'). "
                    "Otherwise OMIT it — ZEZO will ask."
                ),
            },
            "entity_content": {
                "type": "STRING",
                "description": (
                    "Biographical info, name, role, projects, or reference to desktop resume for portfolio/personal sites."
                ),
            },
            "tech_stack": {
                "type": "STRING",
                "enum": ["single_file_html", "modular_html_css_js", "react_vite", "nextjs"],
                "description": (
                    "Tech stack for new website creation. Set this ONLY if user explicitly stated a stack. "
                    "Otherwise OMIT it — ZEZO will ask the user. Never invent a default yourself."
                ),
            },
            "color_theme": {
                "type": "STRING",
                "enum": ["dark_obsidian", "clean_minimal", "luxury_gold", "cyber_matrix", "custom"],
                "description": (
                    "Visual design theme / aesthetic. Set this ONLY if stated. Otherwise OMIT it — ZEZO will ask."
                ),
            },
            "key_sections": {
                "type": "STRING",
                "description": (
                    "Comma-separated key sections (e.g. 'hero, features, pricing, contact'). Set ONLY if user stated. Otherwise OMIT it."
                ),
            },
            "confirmed": {
                "type": "BOOLEAN",
                "description": (
                    "Set to true ONLY after the user explicitly hears the plan and confirms ('yes', 'proceed', 'build it'). "
                    "Omit or false on initial request."
                ),
            },
        },
        "required": ["action"],
    },
    "handler": fleet_control,
}

handler = fleet_control
