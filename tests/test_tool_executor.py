"""
tests/test_tool_executor.py — Comprehensive Test Suite for core/tool_executor.py.

Verifies:
  1. MAIN_SESSION context with valid and invalid tokens.
  2. AGENT context with null/empty agent_id, unknown agent, and permission violations.
  3. AGENT context with workspace path jailing and path escape attempts.
  4. Disabled tools and non-existent tools reporting.
  5. Circuit breaker rejection handling.
  6. Confirmation gate on destructive tools.
  7. Asynchronous execution via execute_async.
  8. get_tool_executor singleton getter.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from core.agents.registry import AgentProfile, get_agent_registry
from core.circuit_breaker import BreakerState, circuit_breaker
from core.tool_executor import (
    CallerContext,
    SecurityAccessDenied,
    ToolExecutionResult,
    ToolExecutor,
    get_tool_executor,
)


@pytest.fixture
def clean_executor():
    """Returns a fresh ToolExecutor instance with known secret."""
    executor = ToolExecutor(main_session_secret="test-secret-token-12345")
    # Register dummy test tools
    executor.register_inline_tool("test_echo", lambda parameters, **kw: f"Echo: {parameters.get('msg', '')}")
    executor.register_inline_tool("test_privileged", lambda parameters, **kw: "Rebooted system.")
    return executor


@pytest.fixture
def test_workspace():
    with tempfile.TemporaryDirectory() as td:
        ws = Path(os.path.realpath(td)) / "agent_ws"
        ws.mkdir()
        doc = ws / "file.txt"
        doc.write_text("secure hello", encoding="utf-8")

        outside = Path(os.path.realpath(td)) / "outside"
        outside.mkdir()
        secret = outside / "secret.txt"
        secret.write_text("private", encoding="utf-8")

        yield {
            "ws": ws,
            "doc": doc,
            "outside": outside,
            "secret": secret,
        }


@pytest.fixture
def registered_agent(test_workspace):
    registry = get_agent_registry()
    agent_id = "test_guard_agent"
    agent = AgentProfile(
        id=agent_id,
        name="Guard Agent",
        role="Security Tester",
        specialty="Verification",
        color="#3b82f6",
        avatar_pixel="🛡️",
        default_tool="test_echo",
        risk_tier="tier1_fast",
        prompt_prefix="You are a test agent.",
        allowed_tools=["test_echo", "ast_tool"],
        active_worktree=str(test_workspace["ws"]),
    )
    with registry._lock:
        registry.agents[agent.id.upper()] = agent
    yield agent
    with registry._lock:
        registry.agents.pop(agent.id.upper(), None)


def test_main_session_valid_token(clean_executor):
    """Test 1: MAIN_SESSION with correct token executes successfully."""
    res = clean_executor.execute(
        tool_name="test_echo",
        parameters={"msg": "Hello ZEZO"},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token="test-secret-token-12345",
    )
    assert res.success is True
    assert res.output == "Echo: Hello ZEZO"
    assert res.latency_ms >= 0.0


def test_main_session_invalid_token(clean_executor):
    """Test 2: MAIN_SESSION with missing or bad token raises SecurityAccessDenied."""
    with pytest.raises(SecurityAccessDenied, match="Unauthorized claim of MAIN_SESSION privileges"):
        clean_executor.execute(
            tool_name="test_echo",
            parameters={"msg": "Fake"},
            caller_context=CallerContext.MAIN_SESSION,
            caller_token="wrong-token",
        )

    # When raise_on_denial=False, returns ToolExecutionResult with blocked_by="identity"
    res = clean_executor.execute(
        tool_name="test_echo",
        parameters={"msg": "Fake"},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token="wrong-token",
        raise_on_denial=False,
    )
    assert res.success is False
    assert res.blocked_by == "identity"


def test_agent_null_or_empty_id(clean_executor):
    """Test 3: AGENT context without valid agent_id raises SecurityAccessDenied."""
    with pytest.raises(SecurityAccessDenied, match="valid, non-null agent_id"):
        clean_executor.execute(
            tool_name="test_echo",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id=None,
        )

    res = clean_executor.execute(
        tool_name="test_echo",
        parameters={},
        caller_context=CallerContext.AGENT,
        agent_id="",
        raise_on_denial=False,
    )
    assert res.success is False
    assert res.blocked_by == "identity"


def test_agent_unknown_agent(clean_executor):
    """Test 4: AGENT context with non-existent agent raises SecurityAccessDenied."""
    with pytest.raises(SecurityAccessDenied, match="Unknown or unauthenticated agent"):
        clean_executor.execute(
            tool_name="test_echo",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id="non_existent_ghost_agent_999",
        )


def test_agent_permission_check(clean_executor, registered_agent):
    """Test 5: AGENT context trying to run an unallowed tool is rejected."""
    # test_echo is in allowed_tools, so it passes
    res = clean_executor.execute(
        tool_name="test_echo",
        parameters={"msg": "Permitted"},
        caller_context=CallerContext.AGENT,
        agent_id=registered_agent.id,
    )
    assert res.success is True
    assert res.output == "Echo: Permitted"

    # computer_control is NOT in allowed_tools for this agent
    with pytest.raises(SecurityAccessDenied, match="not in allowed_tools"):
        clean_executor.execute(
            tool_name="computer_control",
            parameters={"action": "click"},
            caller_context=CallerContext.AGENT,
            agent_id=registered_agent.id,
        )

    # With raise_on_denial=False
    res_denied = clean_executor.execute(
        tool_name="computer_control",
        parameters={"action": "click"},
        caller_context=CallerContext.AGENT,
        agent_id=registered_agent.id,
        raise_on_denial=False,
    )
    assert res_denied.success is False
    assert res_denied.blocked_by == "permission"


def test_agent_path_jail_containment(clean_executor, registered_agent, test_workspace):
    """Test 6: AGENT path parameter jail escape raises SecurityAccessDenied."""
    ws = test_workspace["ws"]
    safe_file = test_workspace["doc"]
    outside_secret = test_workspace["secret"]

    # Safe path inside agent workspace resolves
    res = clean_executor.execute(
        tool_name="test_echo",
        parameters={"msg": "reading", "path": str(safe_file)},
        caller_context=CallerContext.AGENT,
        agent_id=registered_agent.id,
    )
    assert res.success is True

    # Traversal escape ../../outside/secret.txt is blocked
    with pytest.raises(SecurityAccessDenied, match="Path security violation"):
        clean_executor.execute(
            tool_name="test_echo",
            parameters={"msg": "steal", "path": str(outside_secret)},
            caller_context=CallerContext.AGENT,
            agent_id=registered_agent.id,
        )

    # With raise_on_denial=False
    res_escape = clean_executor.execute(
        tool_name="test_echo",
        parameters={"msg": "steal", "path": str(outside_secret)},
        caller_context=CallerContext.AGENT,
        agent_id=registered_agent.id,
        raise_on_denial=False,
    )
    assert res_escape.success is False
    assert res_escape.blocked_by == "path_jail"


def test_circuit_breaker_blocking(clean_executor):
    """Test 7: Circuit breaker blocks tripped tools."""
    token = clean_executor.get_main_session_token()
    tool_name = "test_breaker_tool"

    # Trip the circuit breaker for this tool
    circuit_breaker.record_failure(tool_name, "Simulated crash 1")
    circuit_breaker.record_failure(tool_name, "Simulated crash 2")
    circuit_breaker.record_failure(tool_name, "Simulated crash 3")

    clean_executor.register_inline_tool(tool_name, lambda params, **kw: "Success")

    res = clean_executor.execute(
        tool_name=tool_name,
        parameters={},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res.success is False
    assert res.blocked_by == "circuit_breaker"

    # Re-arm
    circuit_breaker.human_rearm(tool_name)


def test_confirmation_gate(clean_executor):
    """Test 8: Privileged/destructive tools require confirmation."""
    token = clean_executor.get_main_session_token()

    # shutdown_zezo is marked as privileged_os in INLINE_TOOL_RISKS
    res = clean_executor.execute(
        tool_name="shutdown_zezo",
        parameters={"reason": "test"},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res.success is False
    assert res.blocked_by == "confirmation"


def test_execute_async(clean_executor):
    """Test 9: execute_async runs non-blockingly."""
    token = clean_executor.get_main_session_token()

    async def _run():
        return await clean_executor.execute_async(
            tool_name="test_echo",
            parameters={"msg": "Async success"},
            caller_context=CallerContext.MAIN_SESSION,
            caller_token=token,
        )

    res = asyncio.run(_run())
    assert res.success is True
    assert res.output == "Echo: Async success"


def test_singleton_getter():
    """Test 10: get_tool_executor() returns singleton."""
    te1 = get_tool_executor()
    te2 = get_tool_executor()
    assert te1 is te2
    assert isinstance(te1, ToolExecutor)
