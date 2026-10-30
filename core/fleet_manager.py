"""
core/fleet_manager.py — Backward-Compatible Facade for ZEZO Fleet Subsystem.

Composes:
- FleetRegistry: Storage, CRUD, desk allocation, JSON config persistence.
- FleetDispatcher: Sandboxing, skill injection, task dispatch, telemetry.
- FleetOrchestrator: Multi-agent task decomposition, peer delegation, teardown gates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.fleet.registry import (
    FleetAgent,
    FleetRegistry,
    OFFICE_DESK_COORDINATES,
    VALID_RISK_TIERS,
    CORE_AGENT_IDS,
    VALID_TOOLS,
    _infer_agent_defaults,
)
from core.fleet.dispatcher import FleetDispatcher
from core.fleet.orchestrator import FleetOrchestrator

logger = logging.getLogger("zezo.fleet_manager")


class FleetManager:
    """
    Facade uniting FleetRegistry, FleetDispatcher, and FleetOrchestrator.
    Maintains 100% backward-compatible API for all existing callers.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.registry = FleetRegistry(config_path)
        self.dispatcher = FleetDispatcher(self.registry)
        self.orchestrator = FleetOrchestrator(self.registry, self.dispatcher)

    # -------------------------------------------------------------------------
    # Properties & State Accessors (Transparent Compatibility)
    # -------------------------------------------------------------------------

    @property
    def agents(self) -> Dict[str, FleetAgent]:
        """Direct access to registry agents dictionary."""
        return self.registry.agents

    @agents.setter
    def agents(self, value: Dict[str, FleetAgent]) -> None:
        self.registry.agents = value

    @property
    def _lock(self):
        """Re-entrant lock guarding fleet state."""
        return self.registry._lock

    @property
    def config_path(self) -> Path:
        """Path to fleet_agents.json."""
        return self.registry.config_path

    # -------------------------------------------------------------------------
    # Registry Delegation
    # -------------------------------------------------------------------------

    def refresh_if_modified(self) -> bool:
        """Check mtime of config file and reload if changed."""
        return self.registry.refresh_if_modified()

    def _allocate_desk(self, existing: Optional[FleetAgent], req_x: int, req_y: int) -> Tuple[int, int]:
        return self.registry._allocate_desk(existing, req_x, req_y)

    def _load_fleet(self) -> None:
        """Reload fleet agent definitions from disk."""
        self.registry._load_fleet()

    def _save_fleet(self) -> bool:
        """Persist current fleet state to disk."""
        return self.registry._save_fleet()

    def get_agent(self, name_or_id: str) -> Optional[FleetAgent]:
        """Look up an agent by exact ID, lower ID, or display name."""
        return self.registry.get_agent(name_or_id)

    def resolve_agent_by_mention_or_capability(self, query: str) -> Optional[FleetAgent]:
        """Resolve agent by @mention, name, role keywords, or capability."""
        return self.registry.resolve_agent_by_mention_or_capability(query)

    def resolve_agent_for_skill(self, skill_name: str) -> Optional[FleetAgent]:
        """Dynamically resolve which live agent currently possesses the assigned skill."""
        return self.registry.resolve_agent_for_skill(skill_name)

    def get_all_agents(self) -> List[FleetAgent]:
        """Return list of all currently active agents."""
        return self.registry.get_all_agents()

    def get_agent_active_task_count(self, agent_id: str) -> int:
        """Count how many tasks this agent currently has active in task_manager."""
        return self.registry.get_agent_active_task_count(agent_id)

    def save_agent_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an agent profile with desk assignment and JSON persistence."""
        return self.registry.save_agent_profile(data)

    def save_agent_soul(self, agent_id: str, soul_prompt: str) -> Dict[str, Any]:
        """Update agent soul prompt and sync prompt prefix."""
        return self.registry.save_agent_soul(agent_id, soul_prompt)

    def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent from the fleet, with desk deallocation and worktree cleanup."""
        return self.registry.delete_agent(agent_id)

    def get_agent_full_profile(self, agent_id: str) -> Dict[str, Any]:
        """Return rich dictionary of agent details including desk position and capabilities."""
        return self.registry.get_agent_full_profile(agent_id)

    def get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        """Return array of agent dicts formatted for the UI fleet deck."""
        return self.registry.get_fleet_deck_state()

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return array of agent dicts formatted for the UI fleet deck."""
        return self.registry.get_fleet_deck_state()

    def _agent_to_dict(self, a: FleetAgent) -> Dict[str, Any]:
        """Serialize a FleetAgent instance to UI dictionary representation."""
        return self.registry._agent_to_dict(a)

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast micro-event via log bus / UI websocket."""
        self.registry._broadcast_event(event_type, data)

    # -------------------------------------------------------------------------
    # Dispatcher Delegation
    # -------------------------------------------------------------------------

    def dispatch_task(
        self,
        agent_id: str,
        prompt: str,
        path: Optional[str] = None,
        model_override: Optional[str] = None,
        is_subtask: bool = False,
        group_id: Optional[str] = None,
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Launch an autonomous task executed by this agent's designated tool."""
        return self.dispatcher.dispatch_task(
            agent_id=agent_id,
            prompt=prompt,
            path=path,
            model_override=model_override,
            is_subtask=is_subtask,
            group_id=group_id,
            scope_type=scope_type,
            entity_content=entity_content,
            tech_stack=tech_stack,
            color_theme=color_theme,
            key_sections=key_sections,
            confirmed=confirmed,
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # Orchestrator Delegation
    # -------------------------------------------------------------------------

    def generate_peer_session_id(self, from_agent: str, to_agent: str) -> str:
        """Generate deterministic, collision-resistant peer communication session ID."""
        return self.orchestrator.generate_peer_session_id(from_agent, to_agent)

    def delegate_peer_task(
        self,
        from_agent_id: str = "ZEZO",
        to_agent_id: str = "",
        task: str = "",
        upstream_deliverables: Optional[str] = None,
        path: Optional[str] = None,
        call_chain: Optional[List[str]] = None,
        scope_type: Optional[str] = None,
        entity_content: Optional[str] = None,
        tech_stack: Optional[str] = None,
        color_theme: Optional[str] = None,
        key_sections: Optional[str] = None,
        confirmed: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Delegate peer task with worktree isolation and cycle prevention."""
        return self.orchestrator.delegate_peer_task(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            task=task,
            upstream_deliverables=upstream_deliverables,
            path=path,
            call_chain=call_chain,
            scope_type=scope_type,
            entity_content=entity_content,
            tech_stack=tech_stack,
            color_theme=color_theme,
            key_sections=key_sections,
            confirmed=confirmed,
            **kwargs,
        )

    def decompose_and_dispatch(
        self,
        prompt: str,
        path: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        group_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Decompose a complex multi-faceted goal into subtasks across specialized agents."""
        return self.orchestrator.decompose_and_dispatch(
            prompt,
            path=path,
            parent_task_id=parent_task_id,
            group_id=group_id,
            **kwargs,
        )

    def complete_task(
        self,
        agent_id: str,
        task_id: str,
        merge_changes: bool = False,
        worktree_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark task complete and optionally trigger safe worktree teardown & merge."""
        return self.orchestrator.complete_task(
            agent_id=agent_id,
            task_id=task_id,
            merge_changes=merge_changes,
            worktree_id=worktree_id,
        )


# -----------------------------------------------------------------------------
# Module Singleton & Top-Level Accessors
# -----------------------------------------------------------------------------

_fleet_manager_instance: Optional[FleetManager] = None


def get_fleet_manager(config_path: Optional[Path] = None) -> FleetManager:
    """Singleton instance accessor for FleetManager facade."""
    global _fleet_manager_instance
    if _fleet_manager_instance is None:
        _fleet_manager_instance = FleetManager(config_path)
    return _fleet_manager_instance


# Preserved global instance for backward compatibility
fleet_manager: FleetManager = get_fleet_manager()


def resolve_agent_by_mention_or_capability(query: str) -> Optional[str]:
    """Helper to resolve agent ID by query string."""
    agent = fleet_manager.resolve_agent_by_mention_or_capability(query)
    return agent.id if agent else None


def resolve_agent_for_skill(skill_name: str) -> Optional[FleetAgent]:
    """Helper to resolve agent by assigned skill dynamically."""
    return fleet_manager.resolve_agent_for_skill(skill_name)


def get_all_agents() -> List[FleetAgent]:
    """Helper to retrieve all currently active FleetAgent instances."""
    return fleet_manager.get_all_agents()


def get_agent(name_or_id: str) -> Optional[Dict[str, Any]]:
    """Helper to retrieve agent dict by ID or name."""
    agent = fleet_manager.get_agent(name_or_id)
    return fleet_manager._agent_to_dict(agent) if agent else None


def list_agents() -> List[Dict[str, Any]]:
    """Helper to list all agents in the fleet as dicts."""
    return fleet_manager.get_fleet_deck_state()


def generate_peer_session_id(from_agent: str, to_agent: str) -> str:
    """Helper to generate peer session ID."""
    return fleet_manager.generate_peer_session_id(from_agent, to_agent)


def delegate_peer_task(
    from_agent: str,
    to_agent: str,
    task: str,
    upstream_deliverables: Optional[str] = None,
    path: Optional[str] = None,
    call_chain: Optional[List[str]] = None,
    parent_task_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Helper to delegate peer task through fleet_manager singleton."""
    res = fleet_manager.delegate_peer_task(
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        task=task,
        upstream_deliverables=upstream_deliverables,
        path=path,
        call_chain=call_chain,
        parent_task_id=parent_task_id,
        **kwargs,
    )
    if res.get("success"):
        return {
            "status": "success",
            "task_id": res.get("task_id"),
            "target_agent": res.get("to_agent"),
            "from_agent": res.get("from_agent"),
            "peer_session_id": res.get("peer_session_id"),
            "call_chain": res.get("call_chain"),
            "message": f"Delegated task to {res.get('to_agent')}",
        }
    return {
        "status": "error",
        "error": res.get("error", "Delegation failed"),
    }


__all__ = [
    "FleetManager",
    "fleet_manager",
    "get_fleet_manager",
    "FleetAgent",
    "FleetRegistry",
    "FleetDispatcher",
    "FleetOrchestrator",
    "OFFICE_DESK_COORDINATES",
    "VALID_RISK_TIERS",
    "CORE_AGENT_IDS",
    "VALID_TOOLS",
    "_infer_agent_defaults",
    "resolve_agent_by_mention_or_capability",
    "get_agent",
    "list_agents",
    "generate_peer_session_id",
    "delegate_peer_task",
]
