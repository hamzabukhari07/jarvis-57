"""
tests/test_concrete_engine_adapters.py — Unit & Integration tests for OpenCode & Kilo Adapters.
"""

import json
from pathlib import Path
import pytest

from core.engines.adapter import EngineLaunchConfig, EngineProtocol
from core.engines.opencode import OpenCodeEngineAdapter
from core.engines.kilo import KiloEngineAdapter


def test_opencode_adapter_binary_discovery():
    adapter = OpenCodeEngineAdapter()
    bin_path = adapter.resolve_binary()
    assert bin_path is not None
    assert bin_path.exists()


def test_opencode_command_building_no_dangerous_flags(tmp_path):
    adapter = OpenCodeEngineAdapter()
    cfg = EngineLaunchConfig(
        engine_id="opencode",
        prompt="Build a navbar in React",
        workspace_path=tmp_path,
        model="opencode/glm-5.3-flash-free",
        auto_approve_edits=True,
    )
    cmd = adapter.build_cli_command(cfg)
    assert "--dangerously-skip-permissions" not in cmd
    assert "run" in cmd
    assert "--dir" in cmd
    assert str(tmp_path.resolve()) in cmd
    assert "--format" in cmd
    assert "json" in cmd
    assert "--auto" in cmd
    assert "--model" in cmd
    assert "opencode/glm-5.3-flash-free" in cmd


def test_opencode_stream_event_parsing_and_thought_suppression():
    adapter = OpenCodeEngineAdapter()

    # Raw NDJSON containing thought block and reasoning
    raw_event = json.dumps({
        "type": "tool_use",
        "name": "edit_file",
        "thought": "I will change lines 1-10 to implement the button",
        "reasoning": "This is optimal because...",
        "content": "<think>Internal deliberation</think>Applying changes",
    })

    event = adapter.parse_stream_event(raw_event)
    assert event is not None
    assert event.event_type == "tool_use"
    assert "thought" not in event.payload
    assert "reasoning" not in event.payload
    assert "<think>" not in event.payload.get("content", "")
    assert "Applying changes" in event.payload.get("content", "")


def test_kilo_adapter_binary_discovery():
    adapter = KiloEngineAdapter()
    bin_path = adapter.resolve_binary()
    assert bin_path is not None
    assert bin_path.exists()


def test_kilo_command_building_no_dangerous_flags(tmp_path):
    adapter = KiloEngineAdapter()
    cfg = EngineLaunchConfig(
        engine_id="kilo",
        prompt="Refactor database schema",
        workspace_path=tmp_path,
        model="kilo/default",
        auto_approve_edits=True,
    )
    cmd = adapter.build_cli_command(cfg)
    assert "--dangerously-skip-permissions" not in cmd
    assert "run" in cmd
    assert "--dir" in cmd
    assert "--format" in cmd
    assert "json" in cmd
    assert "--auto" in cmd


def test_kilo_stream_event_parsing_and_thought_suppression():
    adapter = KiloEngineAdapter()

    raw_event = json.dumps({
        "type": "step_start",
        "title": "Configuring backend routes",
        "reasoning_content": "Hidden secret logic",
    })

    event = adapter.parse_stream_event(raw_event)
    assert event is not None
    assert event.event_type == "step_start"
    assert event.message == "Configuring backend routes"
    assert "reasoning_content" not in event.payload

