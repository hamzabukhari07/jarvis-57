from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from core.fleet.orchestrator import FleetOrchestrator, DELIVERABLE_ARCHETYPES


@dataclass
class DummyAgent:
    id: str
    name: str
    role: str = "Specialist"
    status: str = "idle"
    recent_logs: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    active_worktree: Optional[str] = None


class DummyRegistry:
    def __init__(self, agents: Optional[Dict[str, DummyAgent]] = None):
        self.agents: Dict[str, DummyAgent] = agents or {}
        self.events: List[Dict[str, Any]] = []

    def get_agent(self, agent_id: str) -> Optional[DummyAgent]:
        return self.agents.get(agent_id)

    def resolve_agent_by_mention_or_capability(self, agent_id: str) -> Optional[DummyAgent]:
        return self.agents.get(agent_id)

    def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        self.events.append({"type": event_type, "data": data})


class MockDispatcher:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def dispatch_task(
        self,
        agent_id: str,
        prompt: str,
        path: Optional[str] = None,
        is_subtask: bool = False,
        group_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        scope_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        call_record = {
            "agent_id": agent_id,
            "prompt": prompt,
            "path": path,
            "is_subtask": is_subtask,
            "group_id": group_id,
            "parent_task_id": parent_task_id,
            "scope_type": scope_type,
            "kwargs": kwargs,
        }
        self.calls.append(call_record)
        return {
            "success": True,
            "task_id": f"task_{len(self.calls)}",
            "agent_id": agent_id,
            "group_id": group_id,
            "parent_task_id": parent_task_id,
        }


@pytest.fixture
def fleet_setup():
    agents = {
        "VERVE": DummyAgent(id="VERVE", name="Verve"),
        "FLUX": DummyAgent(id="FLUX", name="Flux"),
        "AHMAD": DummyAgent(id="AHMAD", name="Nexus"),
        "DWIGHT": DummyAgent(id="DWIGHT", name="Dwight"),
        "KELLY": DummyAgent(id="KELLY", name="Kelly"),
    }
    registry = DummyRegistry(agents)
    dispatcher = MockDispatcher()
    orchestrator = FleetOrchestrator(registry=registry, dispatcher=dispatcher)
    return orchestrator, dispatcher, registry


@pytest.mark.parametrize("archetype", [
    "portfolio",
    "website",
    "landing page",
    "web app",
    "dashboard",
    "full-stack",
    "fullstack",
    "saas",
])
def test_scranton_fleet_swarm_pipeline_archetypes(fleet_setup, archetype):
    orchestrator, dispatcher, _ = fleet_setup
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt = f"Build a modern {archetype} for an executive"
        res = orchestrator.decompose_and_dispatch(prompt=prompt, path=tmpdir)

        assert res["success"] is True
        assert res["orchestrator"] == "MICHAEL"
        assert res["decomposed_count"] == 4
        assert len(res["tasks"]) == 4
        assert len(dispatcher.calls) == 4

        # Verify shared workflow lineage (parent_task_id / group_id)
        shared_group_id = res.get("group_id")
        assert shared_group_id is not None
        assert res.get("parent_task_id") == shared_group_id

        # Verify subtask partitioning across the fleet
        verve_call = next(c for c in dispatcher.calls if c["agent_id"] == "VERVE")
        flux_call = next(c for c in dispatcher.calls if c["agent_id"] == "FLUX")
        ahmad_call = next(c for c in dispatcher.calls if c["agent_id"] == "AHMAD")
        dwight_call = next(c for c in dispatcher.calls if c["agent_id"] == "DWIGHT")

        # Verify exact prompt specifications
        assert verve_call["prompt"] == "Design and build core responsive page layout, hero section, navigation, and theme styling: " + prompt
        assert flux_call["prompt"] == "Build interactive UI components, project showcase cards, skill badges, and micro-interactions: " + prompt
        assert ahmad_call["prompt"] == "Implement backend contact form API endpoint (/api/contact), input validation, and data schema: " + prompt
        assert dwight_call["prompt"] == "Conduct end-to-end verification, link integrity check, and responsive breakpoint testing: " + prompt

        # Verify folder structure
        base = Path(tmpdir).resolve()
        assert verve_call["path"] == str((base / "frontend").resolve())
        assert flux_call["path"] == str((base / "frontend/components").resolve())
        assert ahmad_call["path"] == str((base / "backend").resolve())
        assert dwight_call["path"] == str((base / "tests").resolve())

        # Verify lineage IDs on all calls
        for c in (verve_call, flux_call, ahmad_call, dwight_call):
            assert c["group_id"] == shared_group_id
            assert c["parent_task_id"] == shared_group_id
            assert c["is_subtask"] is True


def test_swarm_custom_group_lineage(fleet_setup):
    orchestrator, dispatcher, _ = fleet_setup
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt = "Create a portfolio web app"
        custom_id = "custom_parent_lineage_123"
        res = orchestrator.decompose_and_dispatch(
            prompt=prompt,
            path=tmpdir,
            parent_task_id=custom_id,
        )

        assert res["group_id"] == custom_id
        assert res["parent_task_id"] == custom_id
        for c in dispatcher.calls:
            assert c["group_id"] == custom_id
            assert c["parent_task_id"] == custom_id


def test_non_deliverable_targeted_single_agent(fleet_setup):
    orchestrator, dispatcher, _ = fleet_setup
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Research task -> KELLY
        dispatcher.calls.clear()
        res = orchestrator.decompose_and_dispatch("scrape youtube comments and find data", path=tmpdir)
        assert res["decomposed_count"] == 1
        assert dispatcher.calls[0]["agent_id"] == "KELLY"

        # 2. UI fix -> VERVE
        dispatcher.calls.clear()
        res = orchestrator.decompose_and_dispatch("fix css styling for the nav buttons", path=tmpdir)
        assert res["decomposed_count"] == 1
        assert dispatcher.calls[0]["agent_id"] == "VERVE"

        # 3. Backend / API -> AHMAD
        dispatcher.calls.clear()
        res = orchestrator.decompose_and_dispatch("create auth endpoint and database migration", path=tmpdir)
        assert res["decomposed_count"] == 1
        assert dispatcher.calls[0]["agent_id"] == "AHMAD"

        # 4. QA / Testing -> DWIGHT
        dispatcher.calls.clear()
        res = orchestrator.decompose_and_dispatch("run security audit and verify edge cases", path=tmpdir)
        assert res["decomposed_count"] == 1
        assert dispatcher.calls[0]["agent_id"] == "DWIGHT"

        # 5. Fallback -> AHMAD
        dispatcher.calls.clear()
        res = orchestrator.decompose_and_dispatch("optimize the algorithm logic", path=tmpdir)
        assert res["decomposed_count"] == 1
        assert dispatcher.calls[0]["agent_id"] == "AHMAD"
