"""
tests/test_agent_runtime.py - Verification tests for Steps 8, 9, 10, 11:
- AgentRuntime multi-turn execution and context memory.
- Choke point tool routing through ToolExecutor with CallerContext.AGENT.
- Permission enforcement (L0_READ_ONLY cannot execute mutation tools).
- Task persistence, restart reconciliation, and confirmation enforcement.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.agents.runtime import AgentRuntime
from core.agents.provider_adapter import (
    NormalizedResponse,
    ProviderAdapter,
    ProviderType,
    ProviderUsage,
)
from core.agents.context_budget import ContextBudget
from core.agents.registry import AgentProfile
from core.tool_executor import CallerContext, ToolExecutionResult, ToolExecutor
from core.task_manager import (
    reconcile_interrupted_tasks,
    get_interrupted_tasks,
    restart_interrupted_task,
)
from memory.sqlite_memory import execute_write, query_db, reset_db_writer_for_test


@pytest.fixture(autouse=True)
def setup_teardown_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_agent_runtime.db"
    monkeypatch.setattr("memory.sqlite_memory.get_db_path", lambda: test_db)
    monkeypatch.setattr("memory.sqlite_memory.DB_PATH", test_db)
    from memory.sqlite_memory import init_db
    init_db()
    yield
    reset_db_writer_for_test()


def test_agent_runtime_conversation_creation_and_persistence():
    """Verify AgentRuntime creates conversations and persists messages in SQLite."""
    runtime = AgentRuntime(agent_id="MICHAEL")
    conv_id = runtime.get_or_create_conversation(title="Architecture Sync")
    assert conv_id.startswith("conv_")

    # Load empty
    messages = runtime.load_messages()
    assert len(messages) == 0

    # Append user turn
    msg_id = runtime.append_message(role="user", content="Hello Michael!")
    assert msg_id.startswith("msg_")

    messages = runtime.load_messages()
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello Michael!"
    assert messages[0]["role"] == "user"
    assert messages[0]["agent_id"] == "MICHAEL"


def test_agent_runtime_step_execution():
    """Verify single step execution calling provider adapter and recording turns."""
    mock_adapter = MagicMock(spec=ProviderAdapter)
    mock_adapter.context_budget = ContextBudget(provider="gemini", model_name="gemini-2.5-flash")
    mock_adapter.execute.return_value = NormalizedResponse(
        content="Greetings Hamza. Architecture looks solid.",
        tool_calls=[],
        usage=ProviderUsage(prompt_tokens=10, completion_tokens=8, total_tokens=18, is_estimated=False),
    )

    runtime = AgentRuntime(agent_id="MICHAEL", provider_adapter=mock_adapter)
    res = runtime.step(user_input="Review the design plan.")

    assert res["success"] is True
    assert "solid" in res["reply"]
    assert res["agent_id"] == "MICHAEL"

    # Verify both turns are persisted
    history = runtime.load_messages(res["conversation_id"])
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Review the design plan."
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Greetings Hamza. Architecture looks solid."


def test_agent_runtime_tool_execution_loop():
    """Verify model requesting a tool call triggers ToolExecutor and feeds result back."""
    mock_adapter = MagicMock(spec=ProviderAdapter)
    mock_adapter.context_budget = ContextBudget(provider="gemini", model_name="gemini-2.5-flash")

    # First execute call requests a tool, second returns final synthesis
    mock_adapter.execute.side_effect = [
        NormalizedResponse(
            content="Checking web status...",
            tool_calls=[{"name": "web_search", "args": {"query": "ZEZO OS architecture"}}],
        ),
        NormalizedResponse(
            content="Search shows ZEZO OS is progressing smoothly.",
            tool_calls=[],
        ),
    ]

    mock_executor = MagicMock(spec=ToolExecutor)
    mock_executor.execute.return_value = ToolExecutionResult(
        success=True,
        output="Result: ZEZO architecture is high-performance.",
    )

    runtime = AgentRuntime(
        agent_id="MICHAEL",
        provider_adapter=mock_adapter,
        tool_executor=mock_executor,
    )
    res = runtime.step(user_input="Check online references.")

    assert res["success"] is True
    assert "smoothly" in res["reply"]
    assert len(res["tool_executions"]) == 1
    assert res["tool_executions"][0]["tool_name"] == "web_search"
    assert res["tool_executions"][0]["success"] is True

    # Check mock executor called with CallerContext.AGENT and immutable agent_id
    mock_executor.execute.assert_called_once_with(
        tool_name="web_search",
        parameters={"query": "ZEZO OS architecture"},
        caller_context=CallerContext.AGENT,
        agent_id="MICHAEL",
        workspace=None,
    )

    # Verify messages in SQLite: user, tool, assistant
    history = runtime.load_messages(res["conversation_id"])
    roles = [m["role"] for m in history]
    assert "user" in roles
    assert "tool" in roles
    assert "assistant" in roles


def test_agent_runtime_tool_permission_denial_graceful():
    """Verify tool blocked by policy returns graceful explanation without crashing."""
    mock_adapter = MagicMock(spec=ProviderAdapter)
    mock_adapter.context_budget = ContextBudget(provider="gemini", model_name="gemini-2.5-flash")

    # Model requests a destructive tool
    mock_adapter.execute.side_effect = [
        NormalizedResponse(
            content="Attempting file delete...",
            tool_calls=[{"name": "file_controller", "args": {"action": "delete", "path": "test.txt"}}],
        ),
        NormalizedResponse(
            content="I cannot delete that file because my role is restricted to read-only.",
            tool_calls=[],
        ),
    ]

    mock_executor = MagicMock(spec=ToolExecutor)
    mock_executor.execute.return_value = ToolExecutionResult(
        success=False,
        output=None,
        error="Permission denied: agent tier L0_READ_ONLY not allowed tool file_controller",
        blocked_by="permission",
    )

    runtime = AgentRuntime(
        agent_id="MICHAEL",
        provider_adapter=mock_adapter,
        tool_executor=mock_executor,
    )
    res = runtime.step(user_input="Delete file")

    assert res["success"] is True
    assert len(res["tool_executions"]) == 1
    assert res["tool_executions"][0]["success"] is False
    assert res["tool_executions"][0]["blocked_by"] == "permission"


def test_task_interruption_reconciliation_and_restart():
    """Verify interrupted tasks are reconciled on crash recovery and require confirmation for rerun."""
    # Seed task in WORKING state
    execute_write(
        """
        INSERT INTO internal_task_ledger (
            id, agent_id, conversation_id, title, prompt, status, risk_tier,
            touched_files, error, created_at, updated_at
        ) VALUES (
            'task_crashed_1', 'MICHAEL', 'conv_1', 'Critical DB Migration',
            'Run schema changes', 'WORKING', 'L1_MUTATION', '["db.py"]', NULL,
            '2026-11-03T12:00:00Z', '2026-11-03T12:00:00Z'
        )
        """
    )

    # 1. Startup reconciliation
    reconciled = reconcile_interrupted_tasks()
    assert reconciled == 1

    interrupted = get_interrupted_tasks()
    assert len(interrupted) == 1
    assert interrupted[0]["id"] == "task_crashed_1"
    assert interrupted[0]["status"] == "INTERRUPTED"
    assert interrupted[0]["interrupted_at"] is not None

    # 2. Restart without confirmation -> must be rejected with confirmation requirement
    unconfirmed = restart_interrupted_task("task_crashed_1", confirmed=False)
    assert unconfirmed["success"] is False
    assert unconfirmed["requires_confirmation"] is True
    assert "duplicate side effects" in unconfirmed["message"]

    # 3. Restart with confirmation -> marks old task RESTARTED and generates new task
    confirmed = restart_interrupted_task("task_crashed_1", confirmed=True)
    assert confirmed["success"] is True
    assert confirmed["old_task_id"] == "task_crashed_1"
    assert confirmed["new_task_id"].startswith("task_")

    # Verify old task status in DB is RESTARTED
    old_row = query_db("SELECT status FROM internal_task_ledger WHERE id = 'task_crashed_1'")
    assert old_row[0]["status"] == "RESTARTED"

    # Verify new task is WORKING
    new_row = query_db("SELECT status, prompt FROM internal_task_ledger WHERE id = ?", (confirmed["new_task_id"],))
    assert new_row[0]["status"] == "WORKING"
    assert new_row[0]["prompt"] == "Run schema changes"

