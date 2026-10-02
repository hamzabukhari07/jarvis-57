"""
tests/test_dispatcher.py — Verification suite for ZEZO Dispatcher & TaskManager integration.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from core.dispatcher import (
    get_creation_engine,
    get_edit_engine,
    dispatch_creation,
    dispatch_quick_edit,
    dispatch_coding,
)
from core.task_manager import TaskManager, TaskStatus


def test_dispatcher_engine_resolution():
    """Verify resolution of creation and edit engines against config."""
    with patch("core.dispatcher.get_preferred_creation_agent", return_value="antigravity"):
        assert get_creation_engine() == "antigravity"

    with patch("core.dispatcher.get_preferred_creation_agent", return_value="kilo"):
        assert get_creation_engine() == "kilo"

    with patch("core.dispatcher.get_preferred_creation_agent", return_value="opencode"):
        assert get_creation_engine() == "opencode"

    with patch("core.dispatcher.get_preferred_creation_agent", return_value="unknown_xyz"):
        assert get_creation_engine() == "opencode"  # safe default

    with patch("core.dispatcher.get_preferred_edit_agent", return_value="groq_helper"):
        assert get_edit_engine() == "groq_helper"

    with patch("core.dispatcher.get_preferred_edit_agent", return_value="kilo"):
        assert get_edit_engine() == "kilo"

    with patch("core.dispatcher.get_preferred_edit_agent", return_value="opencode"):
        assert get_edit_engine() == "opencode"


def test_dispatch_creation_routing():
    """Verify dispatch_creation correctly routes to the configured creation engine."""
    with patch("core.dispatcher.get_creation_engine", return_value="antigravity"):
        with patch("actions.antigravity_agent.antigravity_action", return_value="task_agy_123") as mock_agy:
            res = dispatch_creation(task="Build a full stack app", project_path="Desktop/test")
            assert res == "task_agy_123"
            mock_agy.assert_called_once()
            params = mock_agy.call_args[0][0]
            assert params["task"] == "Build a full stack app"
            assert params["project_path"] == "Desktop/test"

    with patch("core.dispatcher.get_creation_engine", return_value="kilo"):
        with patch("actions.kilo_agent.kilo_agent", return_value="task_kilo_456") as mock_kilo:
            res = dispatch_creation(task="Build refactored API", project_path="Desktop/api")
            assert res == "task_kilo_456"
            mock_kilo.assert_called_once()

    with patch("core.dispatcher.get_creation_engine", return_value="opencode"):
        with patch("actions.opencode_agent.opencode_agent", return_value="task_open_789") as mock_open:
            res = dispatch_creation(task="Build CLI utility")
            assert res == "task_open_789"
            mock_open.assert_called_once()


def test_dispatch_quick_edit_routing():
    """Verify dispatch_quick_edit correctly routes to the configured edit engine."""
    with patch("core.dispatcher.get_edit_engine", return_value="groq_helper"):
        with patch("actions.code_helper.code_helper", return_value="Code edited via Groq LPU") as mock_helper:
            res = dispatch_quick_edit(task="Fix typo in calculate()", file_path="calc.py")
            assert res == "Code edited via Groq LPU"
            mock_helper.assert_called_once()
            params = mock_helper.call_args[0][0]
            assert params["action"] == "edit"
            assert params["file_path"] == "calc.py"

    with patch("core.dispatcher.get_edit_engine", return_value="kilo"):
        with patch("actions.kilo_agent.kilo_agent", return_value="task_kilo_edit") as mock_kilo:
            res = dispatch_quick_edit(task="Rename variables in app.py", file_path="app.py")
            assert res == "task_kilo_edit"
            mock_kilo.assert_called_once()


def test_dispatch_coding_entrypoint():
    """Verify dispatch_coding intelligently branches between creation and edit flows."""
    with patch("core.dispatcher.dispatch_creation", return_value="creation_result") as mock_create:
        res = dispatch_coding(task="Create new portfolio", is_creation=True)
        assert res == "creation_result"
        mock_create.assert_called_once()

    with patch("core.dispatcher.dispatch_quick_edit", return_value="edit_result") as mock_edit:
        res = dispatch_coding(task="Fix bug in main", file_path="main.py", is_creation=False)
        assert res == "edit_result"
        mock_edit.assert_called_once()


def test_task_manager_submission_and_lifecycle():
    """Verify TaskManager async submission, status query, and state transitions."""
    tm = TaskManager(max_tasks=10, ttl_sec=60)

    def dummy_worker(params, ctx):
        ctx.report(50, "working halfway")
        time.sleep(0.05)
        return {"status": "success", "tail": ["step 1", "step 2"]}

    task_id = tm.submit(
        tool_name="test_worker",
        fn=dummy_worker,
        params={"task": "Unit test worker"},
    )

    assert task_id is not None
    assert len(task_id) == 8

    # Status check
    st = tm.status(task_id)
    assert st is not None
    assert st["tool"] == "test_worker"

    # Wait for completion
    for _ in range(50):
        st = tm.status(task_id)
        if st and st["status"] == "done":
            break
        time.sleep(0.02)

    assert st["status"] == "done"
    assert st["progress"] == 100
    assert st["result"]["status"] == "success"
