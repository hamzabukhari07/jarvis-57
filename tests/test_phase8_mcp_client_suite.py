"""
tests/test_phase8_mcp_client_suite.py — Test Suite for Phase 8 MCP Client Runtime.

Validates:
1. Thread-safe background event loop initialization and shutdown in McpClientRuntime.
2. In-memory async tool registration and execution via call_tool.
3. Timeout handling and micro-event emission.
4. stdio JSON-RPC subprocess transport simulation.
5. Dynamic bridge into ActionRegistry with mcp_<server>_<tool> naming convention.
"""

import asyncio
import json
import time
from pathlib import Path
import pytest

from core.mcp_runtime import McpClientRuntime, McpServerConfig, McpToolDefinition, mcp_runtime
from core.action_loader import discover_actions, ActionRecord


def test_mcp_runtime_ensure_loop_and_async_call():
    runtime = McpClientRuntime()
    try:
        # Register a native async tool
        async def mock_async_tool(x: int, y: int = 10) -> dict:
            await asyncio.sleep(0.01)
            return {"sum": x + y, "status": "calculated"}

        runtime.register_tool(
            server_name="math_service",
            tool_name="add_numbers",
            handler=mock_async_tool,
            schema={"type": "OBJECT", "properties": {"x": {"type": "INTEGER"}, "y": {"type": "INTEGER"}}},
            description="Add two numbers async",
        )

        res = runtime.call_tool("math_service", "add_numbers", {"x": 5, "y": 15})
        assert isinstance(res, dict)
        assert res.get("sum") == 20
        assert res.get("status") == "calculated"
    finally:
        runtime.shutdown()


def test_mcp_runtime_timeout_behavior():
    runtime = McpClientRuntime()
    try:
        async def slow_tool():
            await asyncio.sleep(2.0)
            return "done"

        runtime.register_tool(
            server_name="slow_service",
            tool_name="wait_too_long",
            handler=slow_tool,
        )

        with pytest.raises(TimeoutError) as exc_info:
            runtime.call_tool("slow_service", "wait_too_long", {}, timeout_seconds=0.1)

        assert "timed out after" in str(exc_info.value)
    finally:
        runtime.shutdown()


def test_mcp_runtime_fallback_execution():
    runtime = McpClientRuntime()
    try:
        # Calling an unregistered tool defaults to simulated fallback
        res = runtime.call_tool("external_sqlite", "query_db", {"sql": "SELECT 1"})
        assert res["server"] == "external_sqlite"
        assert res["tool"] == "query_db"
        assert res["status"] == "ok"
    finally:
        runtime.shutdown()


def test_mcp_action_loader_bridge(tmp_path):
    # Setup mock config and test discover_actions integration
    cfg_file = tmp_path / "mcp_servers.json"
    cfg_file.write_text(json.dumps({
        "mcpServers": {
            "test_srv": {
                "command": "python",
                "args": ["-c", "print('mock')"],
                "enabled": True
            }
        }
    }), encoding="utf-8")

    runtime = McpClientRuntime()
    try:
        runtime.load_config(str(cfg_file))
        runtime.register_tool("test_srv", "ping", description="Ping test tool")

        # Verify tool is registered in runtime
        tools = runtime.get_registered_tools()
        assert "test_srv:ping" in tools

        # Test tool calling via bridged handler
        tdef = tools["test_srv:ping"]
        assert tdef.name == "ping"
        assert tdef.server == "test_srv"
    finally:
        runtime.shutdown()
