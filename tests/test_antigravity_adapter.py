"""
tests/test_antigravity_adapter.py — Targeted unit and runtime integration tests for
AntigravityEngineAdapter (Step 3).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from core.engines.adapter import EngineLaunchConfig, EngineProtocol
from core.engines.antigravity import AntigravityEngineAdapter


def test_antigravity_adapter_binary_discovery():
    """Verify that Antigravity binary is discovered on current system."""
    adapter = AntigravityEngineAdapter()
    bin_path = adapter.resolve_binary()
    assert bin_path is not None
    assert bin_path.exists()
    assert "agy" in bin_path.name.lower()


def test_antigravity_command_building_no_dangerous_flags(tmp_path):
    """
    Verify command building:
    - Never uses --dangerously-skip-permissions.
    - Uses safe mode --mode accept-edits.
    - Formats argument vector correctly.
    """
    adapter = AntigravityEngineAdapter()
    config = EngineLaunchConfig(
        engine_id="antigravity",
        prompt="Build a clean landing page",
        workspace_path=tmp_path,
        model="gemini-3.8-flash-high",
    )

    cmd = adapter.build_cli_command(config)

    # Invariants
    assert "--dangerously-skip-permissions" not in cmd
    assert "--mode" in cmd
    assert "accept-edits" in cmd
    assert "-p" in cmd
    assert "Build a clean landing page" in cmd
    assert "--add-dir" in cmd
    assert str(tmp_path.resolve()) in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--model" in cmd
    assert "gemini-3.8-flash-high" in cmd


def test_antigravity_stream_event_parsing_and_thought_suppression():
    """
    Verify parsing of agy stream-json lines:
    - Extracts tools, steps, and status messages.
    - Suppresses internal thoughts completely.
    """
    adapter = AntigravityEngineAdapter()

    # 1. Step update line with internal thought embedded
    raw_step = json.dumps({
        "step_update": "Synthesizing React component tree",
        "thought": "Internal LLM reasoning trace that must be dropped",
        "status": "in_progress",
    })
    ev = adapter.parse_stream_event(raw_step)
    assert ev is not None
    assert ev.event_type == "step_start"
    assert "Synthesizing React component tree" in ev.message
    assert "thought" not in ev.payload

    # 2. Tool use line
    raw_tool = json.dumps({
        "tool": "edit_file",
        "description": "components/Header.tsx",
        "chain_of_thought": "Checking imports first",
    })
    ev_tool = adapter.parse_stream_event(raw_tool)
    assert ev_tool is not None
    assert ev_tool.event_type == "tool_use"
    assert "Tool: edit_file (components/Header.tsx...)" in ev_tool.message
    assert "chain_of_thought" not in ev_tool.payload


def test_antigravity_task_delegation_compatibility(tmp_path, monkeypatch):
    """
    Verify that run_antigravity_task delegates cleanly to AntigravityEngineAdapter
    and returns expected payload dictionary.
    """
    from core.engines.antigravity import run_antigravity_task

    # Mock adapter execute method to test delegation contract without invoking full network LLM
    mock_execute = MagicMock(return_value={
        "status": "done",
        "exit_code": 0,
        "workspace": str(tmp_path),
        "milestones": ["DESIGN.md"],
        "stdout_summary": ["Completed design step"],
    })
    monkeypatch.setattr("core.engines.antigravity.AntigravityEngineAdapter.execute", mock_execute)

    payload = {
        "prompt": "Test delegation prompt",
        "project_path": str(tmp_path),
        "skip_preview": True,
    }

    res = run_antigravity_task(payload)
    assert res["status"] == "success"
    assert res["return_code"] == 0
    assert res["repo"] == str(tmp_path)
    assert "Antigravity CLI successfully finished" in res["summary"]
    mock_execute.assert_called_once()

