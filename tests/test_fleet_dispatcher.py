from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pytest

from core.fleet.dispatcher import FleetDispatcher, VALID_RISK_TIERS


@dataclass
class DummyAgent:
    id: str = "TEST_SPECIALIST"
    name: str = "Test Specialist"
    role: str = "Code Specialist"
    specialty: str = "General Code"
    color: str = "#3b82f6"
    avatar_pixel: str = "pixel.png"
    default_tool: str = "quick_snippet"
    risk_tier: str = "L1_MUTATION"
    prompt_prefix: str = "Prefix:"
    model_id: str = "gemini-3.8-flash-medium"
    engine: str = ""
    status: str = "idle"
    current_task_id: Optional[str] = None
    current_task_title: Optional[str] = None
    task_progress: int = 0
    desk_x: int = 0
    desk_y: int = 0
    active_worktree: Optional[str] = None
    completed_tasks: int = 0
    recent_logs: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    allowed_skills: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    is_core: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": self.task_progress,
        }


class DummyRegistry:
    def __init__(self, agent: Optional[DummyAgent] = None):
        self.agents: Dict[str, DummyAgent] = {}
        if agent:
            self.agents[agent.id] = agent
        self.events: List[Dict[str, Any]] = []

    def get_agent(self, agent_id: str) -> Optional[DummyAgent]:
        return self.agents.get(agent_id)

    def resolve_agent_by_mention_or_capability(self, agent_id: str) -> Optional[DummyAgent]:
        return self.agents.get(agent_id)

    def get_agent_active_task_count(self, agent_id: str) -> int:
        return 0

    def get_fleet_deck_state(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.agents.values()]

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        self.events.append({"type": event_type, "data": data})


def test_dispatcher_init():
    reg = DummyRegistry()
    dispatcher = FleetDispatcher(registry=reg)
    assert dispatcher.registry is reg


def test_dispatcher_agent_not_found():
    reg = DummyRegistry()
    dispatcher = FleetDispatcher(registry=reg)
    res = dispatcher.dispatch_task("UNKNOWN_AGENT", "do something")
    assert res["success"] is False
    assert "not in the active fleet" in res["error"]


def test_dispatcher_successful_dispatch():
    agent = DummyAgent(id="VERVE", name="Verve", risk_tier="L0_READ_ONLY")
    reg = DummyRegistry(agent)
    dispatcher = FleetDispatcher(registry=reg)

    res = dispatcher.dispatch_task(
        agent_id="VERVE",
        prompt="Explain python async patterns",
        skip_git=True,
    )

    assert res["success"] is True
    assert res["agent_id"] == "VERVE"
    assert res["task_id"] is not None
    assert agent.status == "working"


def test_dispatcher_risk_tier_validation():
    assert "L0_READ_ONLY" in VALID_RISK_TIERS
    assert "L1_MUTATION" in VALID_RISK_TIERS
    assert "L2_DESTRUCTIVE" in VALID_RISK_TIERS


def test_dispatcher_complete_task():
    agent = DummyAgent(id="VERVE", name="Verve", status="working", task_progress=50)
    reg = DummyRegistry(agent)
    dispatcher = FleetDispatcher(registry=reg)

    res = dispatcher.complete_task("VERVE", "task_1234", merge_changes=True)
    assert res["success"] is True
    assert agent.status == "idle"
    assert agent.completed_tasks == 1
