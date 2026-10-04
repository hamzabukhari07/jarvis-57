"""
tests/test_phase3_multi_agent_mesh_suite.py
Verification suite for Phase 3: Multi-Agent Peer Mesh, Named Routing & Workflow Decomposition.
Tests:
1. Natural alias & capability resolution (Dwight, Ali, Ahmad, Kelly, Michael, Oscar, keywords)
2. Peer session ID generation format
3. P2P Delegation with upstream deliverable handoffs
4. Circular delegation loop detection (A -> B -> A)
5. Max recursion depth limit enforcement (depth > 3)
6. Workflow decomposition into subtasks and fleet dispatch
"""

import pytest
from core.fleet_manager import (
    FleetManager,
    fleet_manager,
    resolve_agent_by_mention_or_capability,
    generate_peer_session_id,
    delegate_peer_task,
)
from actions.fleet_control import handler as fleet_control_handler


def test_agent_resolution_by_alias():
    assert resolve_agent_by_mention_or_capability("Can Dwight audit the backend?") == "DWIGHT"
    assert resolve_agent_by_mention_or_capability("Ali please build the landing page") == "ALI"
    assert resolve_agent_by_mention_or_capability("Ask Ahmad to create the auth models") == "AHMAD"
    assert resolve_agent_by_mention_or_capability("Kelly summarize competitor reels") == "KELLY"
    assert resolve_agent_by_mention_or_capability("Oscar check complexity") == "OSCAR"
    assert resolve_agent_by_mention_or_capability("Michael break down this app") == "MICHAEL"


def test_agent_resolution_by_capability_keyword():
    # Frontend keywords -> Ali
    assert resolve_agent_by_mention_or_capability("Build a landing page hero with CSS animations") == "ALI"
    # Backend / DB / API -> Ahmad
    assert resolve_agent_by_mention_or_capability("Create a FastAPI postgresql endpoint") == "AHMAD"
    # QA / Audit / Security -> Dwight
    assert resolve_agent_by_mention_or_capability("Run a security audit and penetration test") == "DWIGHT"
    # Research / Social -> Kelly
    assert resolve_agent_by_mention_or_capability("Perform social research and scrape trends") == "KELLY"
    # Tokens / Design system -> Pam
    assert resolve_agent_by_mention_or_capability("Extract design tokens and palette") == "PAM"


def test_generate_peer_session_id():
    session_id = generate_peer_session_id("ALI", "AHMAD")
    assert session_id.startswith("peer:ALI->AHMAD:")
    assert len(session_id.split(":")) == 3


def test_delegate_peer_task_success(monkeypatch):
    dispatched_calls = []

    def mock_dispatch(agent_id, prompt, path=None, model_override=None):
        dispatched_calls.append({
            "agent_id": agent_id,
            "prompt": prompt,
            "path": path,
            "model_override": model_override,
        })
        return {
            "success": True,
            "task_id": "task_peer_123",
            "agent_id": agent_id,
            "agent_name": agent_id.capitalize(),
            "message": f"Dispatched {agent_id}"
        }

    monkeypatch.setattr(fleet_manager, "dispatch_task", mock_dispatch)

    res = delegate_peer_task(
        from_agent="ALI",
        to_agent="AHMAD",
        task="Create user API endpoint",
        upstream_deliverables="UI form with fields: username, email",
        parent_task_id="task_parent_001",
        call_chain=["ALI"]
    )

    assert res["status"] == "success"
    assert res["task_id"] == "task_peer_123"
    assert res["target_agent"] == "AHMAD"
    assert len(dispatched_calls) == 1
    call = dispatched_calls[0]
    assert call["agent_id"] == "AHMAD"
    assert "UPSTREAM DELIVERABLE HANDOFF FROM ALI" in call["prompt"]
    assert "UI form with fields: username, email" in call["prompt"]


def test_delegate_peer_task_cycle_detection():
    # Attempting A -> B -> A should fail closed with loop error
    res = delegate_peer_task(
        from_agent="AHMAD",
        to_agent="ALI",
        task="Check UI update",
        call_chain=["ALI", "AHMAD"]
    )
    assert res["status"] == "error"
    assert "Circular peer delegation loop detected" in res["error"]


def test_delegate_peer_task_max_depth():
    # Attempting depth > 3 (chain with 4 items already)
    res = delegate_peer_task(
        from_agent="DWIGHT",
        to_agent="KELLY",
        task="Deep research",
        call_chain=["MICHAEL", "ALI", "AHMAD", "DWIGHT"]
    )
    assert res["status"] == "error"
    assert "Maximum peer delegation depth" in res["error"]


def test_fleet_control_peer_chat_action(monkeypatch):
    def mock_dispatch(agent_id, prompt, path=None, model_override=None):
        return {
            "success": True,
            "task_id": "task_peer_999",
            "agent_id": agent_id,
            "agent_name": agent_id.capitalize(),
            "message": "Task queued"
        }

    monkeypatch.setattr(fleet_manager, "dispatch_task", mock_dispatch)

    result = fleet_control_handler({
        "action": "peer_chat",
        "from_agent": "ALI",
        "to_agent": "AHMAD",
        "task": "Build backend auth for login page",
        "upstream_deliverables": "index.html with login modal"
    })

    assert "Peer delegation active: ALI -> Ahmad" in result
    assert "Task ID: task_peer_999" in result


def test_fleet_control_decompose_workflow(monkeypatch):
    dispatched = []

    def mock_dispatch(agent_id, prompt, path=None, model_override=None):
        dispatched.append(agent_id)
        return {
            "success": True,
            "task_id": f"task_{agent_id.lower()}",
            "agent_id": agent_id,
            "agent_name": agent_id.capitalize(),
            "message": f"{agent_id} queued"
        }

    monkeypatch.setattr(fleet_manager, "dispatch_task", mock_dispatch)

    res = fleet_control_handler({
        "action": "decompose_workflow",
        "task": "Build a landing page with backend FastAPI auth and write security test suite"
    })

    assert "Michael Scott decomposed and dispatched" in res
    assert "ALI" in dispatched
    assert "AHMAD" in dispatched
    assert "DWIGHT" in dispatched
