"""
tests/test_tool_choke_point.py — Comprehensive Security & Choke Point Verification.

Tests Phase 1 Step 4 (ToolExecutor Choke Point) and Step 5 (Default Agent Permissions):
  1. Valid agent identity with authorized tool -> succeeds.
  2. Missing agent identity (None or empty string under CallerContext.AGENT) -> raises SecurityAccessDenied.
  3. Invalid / unauthenticated agent identity (agent not in registry) -> raises SecurityAccessDenied.
  4. Unauthorized tool execution (tool not in agent's allowed_tools) -> raises SecurityAccessDenied.
  5. Risk tier mismatch (e.g. L0_READ_ONLY agent attempting local_mutation or code_execution) -> raises SecurityAccessDenied.
  6. Main-session privilege isolation (Caller claiming CallerContext.MAIN_SESSION with invalid/missing token) -> raises SecurityAccessDenied.
  7. Direct execution bypass attempts:
     - Agent cannot forge MAIN_SESSION privileges.
     - Path-bearing tools enforce PathJail workspace containment (traversal, absolute out-of-bounds, unassigned workspace).
  8. Default permissions for newly created agents:
     - Defaults strictly to L0_READ_ONLY and DEFAULT_READ_ONLY_TOOLS.
     - Restricted mutation tools cannot be assigned or executed unless promoted to L1_MUTATION or L2_DESTRUCTIVE.
  9. Main session backward-compatibility:
     - Valid MAIN_SESSION executes tools normally without agent-level restrictions.
 10. raise_on_denial=False graceful degradation.

Author: Hamza Bukhari
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.action_loader import ActionRecord, get_action_registry
from core.agents.registry import (
    DEFAULT_READ_ONLY_TOOLS,
    AgentProfile,
    get_agent_registry,
)
from core.circuit_breaker import circuit_breaker
from core.loop_gates import loop_gates
from core.tool_executor import (
    PATH_ARG_KEYS,
    CallerContext,
    SecurityAccessDenied,
    ToolExecutionResult,
    ToolExecutor,
)


@pytest.fixture
def test_env():
    """Sets up an isolated environment with temporary workspace and executor."""
    loop_gates.reset_session(None)
    with tempfile.TemporaryDirectory() as td:
        root = Path(os.path.realpath(td))
        ws = root / "agent_ws"
        ws.mkdir()
        safe_file = ws / "safe.txt"
        safe_file.write_text("safe content", encoding="utf-8")

        outside = root / "outside"
        outside.mkdir()
        secret_file = outside / "secret.txt"
        secret_file.write_text("super confidential", encoding="utf-8")

        token = "test-super-secret-token-12345"
        executor = ToolExecutor(main_session_secret=token)

        # Register inline mock tools
        executor.register_inline_tool("mock_reader", lambda parameters, **kw: f"Read: {parameters.get('path', '')}")
        executor.register_inline_tool("mock_writer", lambda parameters, **kw: f"Wrote: {parameters.get('path', '')}")
        executor.register_inline_tool("mock_calc", lambda parameters, **kw: parameters.get("a", 0) + parameters.get("b", 0))

        # Register tools in ActionRegistry with explicit risks
        ar = get_action_registry()
        ar._actions["safe_read_tool"] = ActionRecord(
            name="safe_read_tool",
            handler=lambda parameters, **kw: "read_ok",
            parameters={},
            description="Mock safe read tool",
            risk="read_only",
            enabled=True,
            valid=True,
        )
        ar._actions["mutation_tool"] = ActionRecord(
            name="mutation_tool",
            handler=lambda parameters, **kw: "mutation_ok",
            parameters={},
            description="Mock mutation tool",
            risk="local_mutation",
            enabled=True,
            valid=True,
        )
        ar._actions["exec_tool"] = ActionRecord(
            name="exec_tool",
            handler=lambda parameters, **kw: "exec_ok",
            parameters={},
            description="Mock code execution tool",
            risk="code_execution",
            enabled=True,
            valid=True,
        )
        ar._actions["os_priv_tool"] = ActionRecord(
            name="os_priv_tool",
            handler=lambda parameters, **kw: "os_priv_ok",
            parameters={},
            description="Mock OS privileged tool",
            risk="privileged_os",
            enabled=True,
            valid=True,
        )

        yield {
            "executor": executor,
            "token": token,
            "ws": ws,
            "safe_file": safe_file,
            "outside": outside,
            "secret_file": secret_file,
        }

        # Cleanup actions
        for key in ["safe_read_tool", "mutation_tool", "exec_tool", "os_priv_tool"]:
            ar._actions.pop(key, None)
        loop_gates.reset_session(None)


@pytest.fixture
def sample_agents(test_env):
    """Sets up agents with various risk tiers in AgentRegistry."""
    registry = get_agent_registry()
    ws = str(test_env["ws"])

    # L0 Read-Only Agent
    l0_agent = AgentProfile(
        id="AGENT_L0",
        name="L0 Reader",
        role="Researcher",
        specialty="Analysis",
        color="#3b82f6",
        avatar_pixel="🔍",
        default_tool="safe_read_tool",
        risk_tier="L0_READ_ONLY",
        prompt_prefix="L0 Prompt",
        allowed_tools=["safe_read_tool", "mock_reader", "mock_calc"],
        active_worktree=ws,
    )

    # L1 Mutation Agent
    l1_agent = AgentProfile(
        id="AGENT_L1",
        name="L1 Coder",
        role="Developer",
        specialty="Backend",
        color="#10b981",
        avatar_pixel="💻",
        default_tool="mutation_tool",
        risk_tier="L1_MUTATION",
        prompt_prefix="L1 Prompt",
        allowed_tools=["safe_read_tool", "mutation_tool", "exec_tool", "mock_writer", "mock_reader"],
        active_worktree=ws,
    )

    # L2 Destructive Agent
    l2_agent = AgentProfile(
        id="AGENT_L2",
        name="L2 Admin",
        role="System Admin",
        specialty="DevOps",
        color="#ef4444",
        avatar_pixel="⚡",
        default_tool="os_priv_tool",
        risk_tier="L2_DESTRUCTIVE",
        prompt_prefix="L2 Prompt",
        allowed_tools=["safe_read_tool", "mutation_tool", "exec_tool", "os_priv_tool", "mock_writer"],
        active_worktree=ws,
    )

    # Unassigned Workspace Agent
    noworkspace_agent = AgentProfile(
        id="AGENT_NOWS",
        name="No Workspace",
        role="Cloud Agent",
        specialty="General",
        color="#8b5cf6",
        avatar_pixel="☁️",
        default_tool="mock_calc",
        risk_tier="L0_READ_ONLY",
        prompt_prefix="No WS Prompt",
        allowed_tools=["mock_calc", "mock_reader"],
        active_worktree=None,
    )

    agents = [l0_agent, l1_agent, l2_agent, noworkspace_agent]
    with registry._lock:
        for a in agents:
            registry.agents[a.id] = a

    yield {
        "l0": l0_agent,
        "l1": l1_agent,
        "l2": l2_agent,
        "nows": noworkspace_agent,
    }

    with registry._lock:
        for a in agents:
            registry.agents.pop(a.id, None)


# =============================================================================
# 1. Identity & Context Verification Tests
# =============================================================================

def test_authorized_agent_execution_succeeds(test_env, sample_agents):
    """Requirement: Valid agent identity with authorized tool succeeds."""
    executor = test_env["executor"]
    l0 = sample_agents["l0"]

    res = executor.execute(
        tool_name="safe_read_tool",
        parameters={},
        caller_context=CallerContext.AGENT,
        agent_id=l0.id,
    )
    assert res.success is True
    assert res.output == "read_ok"
    assert res.latency_ms >= 0.0


def test_missing_agent_identity_denied(test_env):
    """Requirement: Missing agent identity (None or empty string) raises SecurityAccessDenied."""
    executor = test_env["executor"]

    # agent_id is None
    with pytest.raises(SecurityAccessDenied, match="valid, non-null agent_id") as exc_info:
        executor.execute(
            tool_name="safe_read_tool",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id=None,
        )
    assert exc_info.value.blocked_by == "identity"

    # agent_id is empty or whitespace
    with pytest.raises(SecurityAccessDenied, match="valid, non-null agent_id") as exc_info:
        executor.execute(
            tool_name="safe_read_tool",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id="   ",
        )
    assert exc_info.value.blocked_by == "identity"


def test_invalid_unauthenticated_agent_denied(test_env):
    """Requirement: Invalid / unauthenticated agent identity raises SecurityAccessDenied."""
    executor = test_env["executor"]

    with pytest.raises(SecurityAccessDenied, match="Unknown or unauthenticated agent") as exc_info:
        executor.execute(
            tool_name="safe_read_tool",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id="MALICIOUS_IMPOSTER_AGENT_007",
        )
    assert exc_info.value.blocked_by == "identity"


# =============================================================================
# 2. Permissions Matrix & Risk Tier Boundary Tests
# =============================================================================

def test_unauthorized_tool_execution_denied(test_env, sample_agents):
    """Requirement: Unauthorized tool execution (not in allowed_tools) raises SecurityAccessDenied."""
    executor = test_env["executor"]
    l0 = sample_agents["l0"]

    # 'mock_writer' is not in l0.allowed_tools
    with pytest.raises(SecurityAccessDenied, match="not in allowed_tools") as exc_info:
        executor.execute(
            tool_name="mock_writer",
            parameters={"path": "safe.txt"},
            caller_context=CallerContext.AGENT,
            agent_id=l0.id,
        )
    assert exc_info.value.blocked_by == "permission"


def test_risk_tier_mismatch_l0_denied_mutation(test_env, sample_agents):
    """Requirement: L0_READ_ONLY agent attempting local_mutation or code_execution is blocked."""
    executor = test_env["executor"]
    registry = get_agent_registry()
    l0 = sample_agents["l0"]

    # Even if someone accidentally adds mutation_tool to l0.allowed_tools in memory
    with registry._lock:
        l0.allowed_tools.append("mutation_tool")
        l0.allowed_tools.append("exec_tool")

    try:
        # Attempting local_mutation tool under L0
        with pytest.raises(SecurityAccessDenied, match="is not allowed for agent .* under risk tier 'L0_READ_ONLY'") as exc_info:
            executor.execute(
                tool_name="mutation_tool",
                parameters={},
                caller_context=CallerContext.AGENT,
                agent_id=l0.id,
            )
        assert exc_info.value.blocked_by == "permission"

        # Attempting code_execution tool under L0
        with pytest.raises(SecurityAccessDenied, match="is not allowed for agent .* under risk tier 'L0_READ_ONLY'") as exc_info:
            executor.execute(
                tool_name="exec_tool",
                parameters={},
                caller_context=CallerContext.AGENT,
                agent_id=l0.id,
            )
        assert exc_info.value.blocked_by == "permission"
    finally:
        with registry._lock:
            l0.allowed_tools.remove("mutation_tool")
            l0.allowed_tools.remove("exec_tool")


def test_risk_tier_l1_allowed_mutation_but_denied_os_privileged(test_env, sample_agents):
    """Requirement: L1_MUTATION allows local_mutation/code_execution but denies privileged_os."""
    executor = test_env["executor"]
    registry = get_agent_registry()
    l1 = sample_agents["l1"]

    # 1. L1 running local_mutation succeeds
    res_mut = executor.execute(
        tool_name="mutation_tool",
        parameters={},
        caller_context=CallerContext.AGENT,
        agent_id=l1.id,
    )
    assert res_mut.success is True
    assert res_mut.output == "mutation_ok"

    # 2. L1 running code_execution succeeds
    res_exec = executor.execute(
        tool_name="exec_tool",
        parameters={},
        caller_context=CallerContext.AGENT,
        agent_id=l1.id,
    )
    assert res_exec.success is True
    assert res_exec.output == "exec_ok"

    # 3. L1 attempting privileged_os is denied even if in allowed_tools
    with registry._lock:
        l1.allowed_tools.append("os_priv_tool")

    try:
        with pytest.raises(SecurityAccessDenied, match="is not allowed for agent .* under risk tier 'L1_MUTATION'") as exc_info:
            executor.execute(
                tool_name="os_priv_tool",
                parameters={},
                caller_context=CallerContext.AGENT,
                agent_id=l1.id,
            )
        assert exc_info.value.blocked_by == "permission"
    finally:
        with registry._lock:
            l1.allowed_tools.remove("os_priv_tool")


# =============================================================================
# 3. Main-Session Privilege Isolation & Anti-Spoofing Tests
# =============================================================================

def test_main_session_privilege_isolation(test_env, sample_agents):
    """Requirement: Caller claiming MAIN_SESSION with invalid or missing token is blocked."""
    executor = test_env["executor"]
    token = test_env["token"]
    l1 = sample_agents["l1"]

    # 1. No token provided
    with pytest.raises(SecurityAccessDenied, match="Unauthorized claim of MAIN_SESSION privileges"):
        executor.execute(
            tool_name="mock_calc",
            parameters={"a": 1, "b": 2},
            caller_context=CallerContext.MAIN_SESSION,
            caller_token=None,
        )

    # 2. Wrong token provided
    with pytest.raises(SecurityAccessDenied, match="Unauthorized claim of MAIN_SESSION privileges"):
        executor.execute(
            tool_name="mock_calc",
            parameters={"a": 1, "b": 2},
            caller_context=CallerContext.MAIN_SESSION,
            caller_token="attacker-guess-token",
        )

    # 3. Agent attempts to spoof MAIN_SESSION by passing agent_id but claiming MAIN_SESSION without token
    with pytest.raises(SecurityAccessDenied, match="Unauthorized claim of MAIN_SESSION privileges"):
        executor.execute(
            tool_name="os_priv_tool",
            parameters={},
            caller_context=CallerContext.MAIN_SESSION,
            agent_id=l1.id,
            caller_token="wrong_agent_token",
        )

    # 4. Valid token succeeds
    res = executor.execute(
        tool_name="mock_calc",
        parameters={"a": 5, "b": 7},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res.success is True
    assert res.output == 12


# =============================================================================
# 4. PathJail Workspace Containment & Direct Bypass Prevention Tests
# =============================================================================

def test_agent_path_jail_directory_traversal_blocked(test_env, sample_agents):
    """Requirement: Path-bearing tools block directory traversal escapes."""
    executor = test_env["executor"]
    l0 = sample_agents["l0"]

    # Path traversal ../outside/secret.txt
    traversal_path = "../../outside/secret.txt"
    with pytest.raises(SecurityAccessDenied, match="Path security violation") as exc_info:
        executor.execute(
            tool_name="mock_reader",
            parameters={"path": traversal_path},
            caller_context=CallerContext.AGENT,
            agent_id=l0.id,
        )
    assert exc_info.value.blocked_by == "path_jail"


def test_agent_path_jail_absolute_outside_blocked(test_env, sample_agents):
    """Requirement: Path-bearing tools block absolute paths pointing outside workspace."""
    executor = test_env["executor"]
    l0 = sample_agents["l0"]
    secret_file = test_env["secret_file"]

    with pytest.raises(SecurityAccessDenied, match="Path security violation") as exc_info:
        executor.execute(
            tool_name="mock_reader",
            parameters={"path": str(secret_file)},
            caller_context=CallerContext.AGENT,
            agent_id=l0.id,
        )
    assert exc_info.value.blocked_by == "path_jail"


def test_agent_path_jail_missing_workspace_blocked(test_env, sample_agents):
    """Requirement: Path-bearing tool execution by agent with no workspace is blocked."""
    executor = test_env["executor"]
    nows = sample_agents["nows"]

    # nows agent has no active_worktree
    with pytest.raises(SecurityAccessDenied, match="requires an assigned workspace jail") as exc_info:
        executor.execute(
            tool_name="mock_reader",
            parameters={"path": "somefile.txt"},
            caller_context=CallerContext.AGENT,
            agent_id=nows.id,
        )
    assert exc_info.value.blocked_by == "path_jail"


def test_agent_path_jail_valid_path_succeeds(test_env, sample_agents):
    """Requirement: Safe relative and absolute paths within workspace succeed."""
    executor = test_env["executor"]
    l0 = sample_agents["l0"]
    safe_file = test_env["safe_file"]

    # 1. Absolute safe path
    res1 = executor.execute(
        tool_name="mock_reader",
        parameters={"path": str(safe_file)},
        caller_context=CallerContext.AGENT,
        agent_id=l0.id,
    )
    assert res1.success is True
    assert "safe.txt" in res1.output

    # 2. Relative safe path
    res2 = executor.execute(
        tool_name="mock_reader",
        parameters={"path": "safe.txt"},
        caller_context=CallerContext.AGENT,
        agent_id=l0.id,
    )
    assert res2.success is True
    assert "safe.txt" in res2.output


def test_agent_path_jail_all_path_arg_variants(test_env, sample_agents):
    """Requirement: PathJail inspects all aliases in PATH_ARG_KEYS."""
    executor = test_env["executor"]
    l1 = sample_agents["l1"]
    secret_file = test_env["secret_file"]

    # Test several aliases from PATH_ARG_KEYS
    test_aliases = ["file_path", "target_path", "destination", "source_path", "dir", "directory", "output_dir"]
    for alias in test_aliases:
        with pytest.raises(SecurityAccessDenied, match="Path security violation"):
            executor.execute(
                tool_name="mock_writer",
                parameters={alias: str(secret_file)},
                caller_context=CallerContext.AGENT,
                agent_id=l1.id,
            )


# =============================================================================
# 5. Default Permissions for Newly Created Agents Tests
# =============================================================================

def test_new_agent_defaults_to_l0_read_only():
    """
    Requirement: Newly created agents without explicit config strictly default
    to L0_READ_ONLY and DEFAULT_READ_ONLY_TOOLS (web_search, web_read_page, task_status).
    """
    registry = get_agent_registry()
    agent_id = "NEWBIE_AGENT"

    try:
        # Create agent with bare minimal info
        result = registry.save_agent_profile({
            "id": agent_id,
            "name": "Newbie Agent",
            "role": "General Assistant",
            "specialty": "Tasks",
        })
        assert result["success"] is True
        created_id = result["agent"]["id"]

        agent = registry.get_agent(created_id)
        assert agent is not None
        assert agent.risk_tier == "L0_READ_ONLY"

        # Allowed tools must strictly default to DEFAULT_READ_ONLY_TOOLS
        for expected_tool in DEFAULT_READ_ONLY_TOOLS:
            assert expected_tool in agent.allowed_tools

        # No mutation tools should be in allowed_tools
        assert "file_controller" not in agent.allowed_tools
        assert "opencode_run" not in agent.allowed_tools
        assert "antigravity_run" not in agent.allowed_tools
        assert "computer_control" not in agent.allowed_tools

    finally:
        registry.delete_agent(agent_id)


def test_l0_agent_cannot_be_assigned_restricted_mutation_tools():
    """
    Requirement: Restricted mutation tools cannot be assigned to L0_READ_ONLY agents;
    they are automatically stripped during save_agent_profile.
    """
    registry = get_agent_registry()
    agent_id = "RESTRICT_AGENT"

    try:
        # Malicious or misconfigured payload attempting to grant mutation tools to L0 agent
        result = registry.save_agent_profile({
            "id": agent_id,
            "name": "Restricted Attempt Agent",
            "risk_tier": "L0_READ_ONLY",
            "default_tool": "opencode_run",
            "allowed_tools": ["opencode_run", "file_controller", "web_search", "computer_control"],
        })
        assert result["success"] is True
        created_id = result["agent"]["id"]

        agent = registry.get_agent(created_id)
        assert agent is not None
        assert agent.risk_tier == "L0_READ_ONLY"

        # Default tool must NOT be opencode_run; it must fall back to a safe read-only tool
        assert agent.default_tool == "web_search"

        # Restricted tools must be stripped from allowed_tools
        assert "opencode_run" not in agent.allowed_tools
        assert "file_controller" not in agent.allowed_tools
        assert "computer_control" not in agent.allowed_tools
        assert "web_search" in agent.allowed_tools

    finally:
        registry.delete_agent(agent_id)


def test_promoted_agent_can_execute_mutation_tools(test_env):
    """
    Requirement: Restricted mutation tools can only be assigned and executed
    when an agent is explicitly promoted to L1_MUTATION or L2_DESTRUCTIVE.
    """
    registry = get_agent_registry()
    executor = test_env["executor"]
    ws = test_env["ws"]
    agent_id = "PROMOTED_AGENT"

    try:
        # Create an explicitly promoted L1_MUTATION agent
        result = registry.save_agent_profile({
            "id": agent_id,
            "name": "Promoted Dev Agent",
            "risk_tier": "L1_MUTATION",
            "default_tool": "mutation_tool",
            "allowed_tools": ["mutation_tool", "mock_writer", "safe_read_tool"],
            "active_worktree": str(ws),
        })
        assert result["success"] is True
        created_id = result["agent"]["id"]

        agent = registry.get_agent(created_id)
        assert agent.risk_tier == "L1_MUTATION"
        assert "mutation_tool" in agent.allowed_tools

        # Execution of mutation tool succeeds
        res = executor.execute(
            tool_name="mutation_tool",
            parameters={},
            caller_context=CallerContext.AGENT,
            agent_id=agent.id,
        )
        assert res.success is True
        assert res.output == "mutation_ok"

    finally:
        registry.delete_agent(agent_id)


# =============================================================================
# 6. Main Session Backward-Compatibility & Confirmation Gate
# =============================================================================

def test_main_session_backward_compatibility(test_env):
    """
    Requirement: MAIN_SESSION with valid token executes tools normally without agent restrictions.
    """
    executor = test_env["executor"]
    token = test_env["token"]

    # 1. Read-only tool
    res_read = executor.execute(
        tool_name="safe_read_tool",
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res_read.success is True
    assert res_read.output == "read_ok"

    # 2. Mutation tool
    res_mut = executor.execute(
        tool_name="mutation_tool",
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res_mut.success is True
    assert res_mut.output == "mutation_ok"

    # 3. Inline calculation tool
    res_calc = executor.execute(
        tool_name="mock_calc",
        parameters={"a": 100, "b": 250},
        caller_context=CallerContext.MAIN_SESSION,
        caller_token=token,
    )
    assert res_calc.success is True
    assert res_calc.output == 350


def test_destructive_tool_confirmation_gate(test_env, sample_agents):
    """
    Requirement: L2_DESTRUCTIVE actions require confirmation before execution.
    """
    executor = test_env["executor"]
    token = test_env["token"]
    l2 = sample_agents["l2"]

    # 1. Calling unconfirmed destructive tool under AGENT returns confirmation request
    res = executor.execute(
        tool_name="os_priv_tool",
        parameters={},
        caller_context=CallerContext.AGENT,
        agent_id=l2.id,
    )
    assert res.success is False
    assert res.blocked_by == "confirmation"
    assert "Confirmation pending user approval" in res.error

    # 2. Calling with confirmed flag executes successfully
    res_confirmed = executor.execute(
        tool_name="os_priv_tool",
        parameters={"confirmed": True},
        caller_context=CallerContext.AGENT,
        agent_id=l2.id,
    )
    assert res_confirmed.success is True
    assert res_confirmed.output == "os_priv_ok"


# =============================================================================
# 7. raise_on_denial=False Graceful Error Reporting
# =============================================================================

def test_raise_on_denial_false_returns_result_object(test_env, sample_agents):
    """
    Requirement: When raise_on_denial=False, errors return structured ToolExecutionResult
    without raising unhandled exceptions.
    """
    executor = test_env["executor"]
    l0 = sample_agents["l0"]

    # Identity denial
    res_id = executor.execute(
        tool_name="safe_read_tool",
        caller_context=CallerContext.AGENT,
        agent_id="UNKNOWN_AGENT",
        raise_on_denial=False,
    )
    assert res_id.success is False
    assert res_id.blocked_by == "identity"
    assert "Unknown or unauthenticated agent" in res_id.error

    # Permission denial
    res_perm = executor.execute(
        tool_name="unauthorized_tool",
        caller_context=CallerContext.AGENT,
        agent_id=l0.id,
        raise_on_denial=False,
    )
    assert res_perm.success is False
    assert res_perm.blocked_by == "permission"
    assert "not in allowed_tools" in res_perm.error

    # Path jail denial
    res_path = executor.execute(
        tool_name="mock_reader",
        parameters={"path": "../../outside/secret.txt"},
        caller_context=CallerContext.AGENT,
        agent_id=l0.id,
        raise_on_denial=False,
    )
    assert res_path.success is False
    assert res_path.blocked_by == "path_jail"
    assert "Path security violation" in res_path.error
