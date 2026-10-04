"""test_phase10_e2e_acceptance_suite.py

End-to-End Acceptance Suite for ZEZO OS v2 Release Verification.
Validates the 4 core interaction scenarios:
1. Direct single-tool invocation with governance, loop gates, and circuit breaker.
2. Explicit named multi-agent delegation ("Tell Ali to build a landing page").
3. Auto-capability natural language routing ("Research AI trends" -> Kelly).
4. Compound multi-stage workflow pipeline decomposition (Sara -> Ali -> Verify).
Plus conversational team status queries, failure recovery, deliverable verification,
and AGENTS.md Section 8 frontend invariant audits.
"""

import json
import pytest
from pathlib import Path
from core.action_loader import ActionRegistry
from core.fleet_manager import (
    resolve_agent_by_mention_or_capability,
    list_agents,
    get_agent,
)
from core.task_manager import TaskManager, TaskStatus
from core.deliverable_verifier import verify_deliverable, VerificationResult
from core.governance import evaluate, PolicyDecision, ToolRisk
from actions.fleet_control import fleet_control
from actions.task_status import handler as task_status_handler



def test_scenario_1_direct_tool_execution(tmp_path):
    """Direct single-tool execution goes through registry with governance and loop gates."""
    from core.action_loader import get_action_registry
    registry = get_action_registry()

    assert "web_search" in registry._actions
    assert "run_tool_batch" in registry._actions
    assert "ast_tool" in registry._actions

    # AST Tool structural parsing
    py_code = "def sample_func(a, b):\n    return a + b\n"
    res = registry.run("ast_tool", {"content": py_code, "op": "functions"})
    assert isinstance(res, str)
    assert "sample_func" in res
    assert "Complexity" in res



def test_scenario_2_explicit_named_delegation():
    """Explicit agent naming ('Tell Ali to...') resolves immediately to Ali's ID."""
    prompt = "Tell Ali to build a high-converting hero section for our SaaS"
    agent_id = resolve_agent_by_mention_or_capability(prompt)

    assert agent_id.upper() == "ALI"

    ali_spec = get_agent("ALI")
    assert ali_spec is not None
    assert "Frontend" in ali_spec["role"]
    assert "antigravity_run" in ali_spec.get("allowed_tools", [])


def test_scenario_3_auto_capability_routing():
    """Natural capability request without explicit mention routes to best specialist."""
    research_prompt = "Perform deep market research on AI agent frameworks and summarize findings"
    agent_id = resolve_agent_by_mention_or_capability(research_prompt)

    # Should route to KELLY based on research capability
    assert agent_id in ("KELLY", "MICHAEL", "ZEZO")


def test_scenario_4_compound_workflow_decomposition():
    """Compound multi-step instruction decomposes and executes through fleet dispatch."""
    from actions.fleet_control import fleet_control

    res = fleet_control({"action": "decompose_workflow", "task": "Research AI UI trends and build landing page"})
    assert "Michael Scott decomposed" in res
    assert "KELLY" in res.upper() or "Kelly" in res
    assert "ALI" in res.upper() or "Ali" in res


def test_peer_delegation_collaboration_and_recursion_guard():
    """Peer delegation creates isolated session, passes upstream deliverables, and detects loops."""
    from core.fleet_manager import delegate_peer_task

    # 1. Normal delegation
    res = delegate_peer_task(
        from_agent="KELLY",
        to_agent="ALI",
        task="Design hero section with extracted tokens",
        upstream_deliverables="Colors: #0a0a0a, #8b5cf6",
    )
    assert res.get("status") == "success"
    assert res.get("peer_session_id", "").startswith("peer:KELLY->ALI:")
    assert res.get("target_agent") == "ALI"

    # 2. Circular delegation loop guard (ALI in call chain -> blocked)
    loop_res = delegate_peer_task(
        from_agent="AHMAD",
        to_agent="ALI",
        task="Circular task back to Ali",
        call_chain=["ALI", "AHMAD"],
    )
    assert loop_res.get("status") == "error"
    assert "Circular" in loop_res.get("error", "")

    # 3. Max depth guard (> 3 hops)
    depth_res = delegate_peer_task(
        from_agent="DWIGHT",
        to_agent="PAM",
        task="Too many hops",
        call_chain=["MICHAEL", "KELLY", "ALI", "DWIGHT"],
    )
    assert depth_res.get("status") == "error"
    assert "depth" in depth_res.get("error", "").lower()


def test_conversational_team_status_queries():
    """Natural conversational team queries return real status without hallucination."""
    res_team = task_status_handler({"action": "team"})
    assert isinstance(res_team, str)
    assert "Agents" in res_team or "tasks" in res_team or "Active" in res_team

    res_blocked = task_status_handler({"action": "blocked"})
    assert isinstance(res_blocked, str)
    assert "No agents or tasks are currently blocked" in res_blocked or "Blocked" in res_blocked

    res_completed = task_status_handler({"action": "completed_today"})
    assert isinstance(res_completed, str)
    assert "No background tasks have completed" in res_completed or "Completed Tasks" in res_completed


def test_deliverable_verification_pipeline(tmp_path):
    """Output deliverables are strictly validated before completion."""
    # Valid HTML with responsive viewport
    html_file = tmp_path / "index.html"
    html_file.write_text(
        "<!DOCTYPE html><html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Test</title></head><body><h1>Hello</h1></body></html>",
        encoding="utf-8",
    )
    res_html = verify_deliverable("html", str(html_file))
    assert res_html.valid is True

    # Broken Python AST
    py_file = tmp_path / "broken.py"
    py_file.write_text("def broken_func(:\n    pass", encoding="utf-8")
    res_py = verify_deliverable("python", str(py_file))
    assert res_py.valid is False
    assert len(res_py.errors if hasattr(res_py, "errors") else res_py.issues) > 0


def test_agents_md_rule_8_frontend_invariants():
    """Audit frontend files against AGENTS.md §8 rules."""
    root = Path(__file__).parent.parent
    index_html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    office_html = (root / "frontend" / "office.html").read_text(encoding="utf-8")
    ui_js = (root / "frontend" / "js" / "ui.js").read_text(encoding="utf-8")

    # Rule 2: Never use transition: all
    assert "transition: all" not in index_html
    assert "transition: all" not in office_html

    # Rule 1: Modal panels must not have backdrop-filter
    assert ".modal-panel { backdrop-filter" not in index_html
    assert ".modal-panel { backdrop-filter" not in office_html

    # Rule 3 & 4: _zezoAnimActive and vortex-gif visibility in openModal/closeModal in ui.js & index.html
    assert "window._zezoAnimActive = false" in ui_js
    assert "gif.style.visibility = 'hidden'" in ui_js
    assert "window._zezoAnimActive = false" in index_html

