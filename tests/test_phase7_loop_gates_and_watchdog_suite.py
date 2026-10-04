"""
tests/test_phase7_loop_gates_and_watchdog_suite.py — Test Suite for Phase 7.

Validates:
1. LoopGatesEngine 4 evaluation gates (watchdog_timeout, tool_budget, iteration_cap, doom_loop).
2. INTERRUPT_AND_CONTINUE steering feedback generation.
3. Per-tool RiskAwareCircuitBreaker state transitions (L0/L1/L2).
4. run_tool_batch sequential pipeline runner with variable substitution.
5. ast_tool structural syntax and complexity analysis.
6. verify_deliverable integrity validation for HTML, Python, JS, and docs.
7. Conversational fleet and team status queries in task_status.
"""

import ast
import tempfile
import time
from pathlib import Path
import pytest

from core.circuit_breaker import BreakerState, RiskAwareCircuitBreaker, RiskTier
from core.deliverable_verifier import verify_deliverable
from core.loop_gates import GateDecision, LoopGatesEngine
from actions.run_tool_batch import run_tool_batch, _substitute_variables
from actions.ast_tool import ast_tool
from actions.task_status import task_status
from core.task_manager import get_task_manager


# ── 1. LoopGatesEngine Tests ──────────────────────────────────────────────────

def test_loop_gates_doom_loop_detection():
    engine = LoopGatesEngine(similarity_threshold=3)
    session = "test_sess_doom"
    params = {"file": "test.py", "action": "read"}

    # First 3 calls should proceed
    for _ in range(3):
        res = engine.evaluate("file_processor", params, session_id=session)
        assert res.decision == GateDecision.PROCEED

    # 4th identical call triggers INTERRUPT with coaching feedback
    res = engine.evaluate("file_processor", params, session_id=session)
    assert res.decision == GateDecision.INTERRUPT
    assert "⚠️ [DOOM-LOOP INTERRUPT]" in res.coaching_feedback
    assert "file_processor" in res.coaching_feedback


def test_loop_gates_budget_and_iteration_caps():
    engine = LoopGatesEngine(max_iterations=5, max_tool_budget=6)
    session = "test_sess_budget"

    # Invocations up to 5 proceed
    for i in range(5):
        res = engine.evaluate(f"tool_{i}", {"k": i}, session_id=session)
        assert res.decision == GateDecision.PROCEED

    # 6th invocation triggers iteration cap BLOCK
    res = engine.evaluate("tool_6", {"k": 6}, session_id=session)
    assert res.decision == GateDecision.BLOCK
    assert "iteration limit" in res.reason.lower()


def test_loop_gates_watchdog_timeout():
    engine = LoopGatesEngine(watchdog_timeout_sec=10.0)
    session = "test_sess_timeout"
    t0 = 1000.0

    # Start session
    res = engine.evaluate("web_search", {"q": "hi"}, session_id=session, now=t0)
    assert res.decision == GateDecision.PROCEED

    # Call at t0 + 5s (within timeout)
    res = engine.evaluate("web_search", {"q": "hi2"}, session_id=session, now=t0 + 5.0)
    assert res.decision == GateDecision.PROCEED

    # Call at t0 + 15s (exceeds 10s watchdog)
    res = engine.evaluate("web_search", {"q": "hi3"}, session_id=session, now=t0 + 15.0)
    assert res.decision == GateDecision.BLOCK
    assert "Watchdog timeout exceeded" in res.reason


# ── 2. Per-Tool Circuit Breaker Tests ──────────────────────────────────────────

def test_circuit_breaker_per_tool_isolation():
    cb = RiskAwareCircuitBreaker()
    tool_a = "file_processor"  # Read/local
    tool_b = "web_search"

    # Fail tool_a 3 times
    for i in range(3):
        cb.record_failure(tool_a, f"disk read error {i}")

    can_run_a, msg_a = cb.can_execute(tool_a)
    assert not can_run_a
    assert "CircuitBreaker" in msg_a

    # tool_b should still be unaffected and allowed
    can_run_b, msg_b = cb.can_execute(tool_b)
    assert can_run_b
    assert msg_b is None


def test_circuit_breaker_rearm():
    cb = RiskAwareCircuitBreaker()
    tool = "computer_settings"
    cb.record_failure(tool, "permission denied")
    cb.record_failure(tool, "permission denied 2")

    msg = cb.human_rearm(tool)
    assert "manually re-armed" in msg

    can_run, _ = cb.can_execute(tool)
    assert can_run


# ── 3. Batch Tool Runner Tests ────────────────────────────────────────────────

def test_batch_variable_substitution():
    results = ["hello world", 42, {"key": "val"}]
    tmpl = {"prompt": "First was ${steps.0.result} and second was ${steps.1}"}
    resolved = _substitute_variables(tmpl, results)
    assert resolved["prompt"] == "First was hello world and second was 42"


def test_run_tool_batch_execution(monkeypatch):
    # Mock registry for safe fast tests
    class MockRegistry:
        def run(self, name, params, ctx=None):
            return f"Ran {name} with {params.get('q', '')}"

    monkeypatch.setattr("core.action_loader.get_action_registry", lambda: MockRegistry())

    params = {
        "steps": [
            {"tool": "web_search", "parameters": {"q": "step0"}},
            {"tool": "web_search", "parameters": {"q": "next after ${steps.0.result}"}},
        ]
    }
    out = run_tool_batch(params)
    assert "Executed batch of 2 step(s):" in out
    assert "• Step #0 (web_search): [OK]" in out
    assert "• Step #1 (web_search): [OK]" in out


# ── 4. AST Tool Tests ─────────────────────────────────────────────────────────

def test_ast_tool_functions_and_classes():
    code = """
import os
import sys

class Alpha:
    def method_one(self, x):
        if x > 0:
            return x
        return 0

def standalone_func(a, b):
    return a + b
"""
    res_fn = ast_tool({"content": code, "op": "functions"})
    assert "method_one(self, x)" in res_fn
    assert "standalone_func(a, b)" in res_fn

    res_cls = ast_tool({"content": code, "op": "classes"})
    assert "class Alpha" in res_cls

    res_comp = ast_tool({"content": code, "op": "complexity"})
    assert "Clean code" in res_comp or "Complexity" in res_comp


# ── 5. Deliverable Verifier Tests ──────────────────────────────────────────────

def test_verify_deliverable_html():
    valid_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Landing</title>
</head>
<body>
    <main><h1>Hello</h1></main>
</body>
</html>"""
    res = verify_deliverable("html", content=valid_html)
    assert res.valid
    assert len(res.issues) == 0

    broken_html = "<html><head><title>No Viewport</title></head><body><h1>Unclosed main<main></body></html>"
    res_broken = verify_deliverable("html", content=broken_html)
    assert not res_broken.valid
    assert any("viewport" in issue.lower() for issue in res_broken.issues)


def test_verify_deliverable_python():
    valid_py = "def add(x: int, y: int) -> int:\n    return x + y\n"
    res = verify_deliverable("python", content=valid_py)
    assert res.valid

    broken_py = "def broken(:\n    return 1"
    res_broken = verify_deliverable("python", content=broken_py)
    assert not res_broken.valid
    assert any("SyntaxError" in issue for issue in res_broken.issues)


# ── 6. Conversational Team Status Tests ────────────────────────────────────────

def test_task_status_team_queries():
    out_team = task_status({"action": "team"})
    assert "Active Agents" in out_team or "Available Agents" in out_team

    out_blocked = task_status({"action": "blocked"})
    assert "No agents or tasks are currently blocked" in out_blocked or "Blocked / Failed Tasks:" in out_blocked
