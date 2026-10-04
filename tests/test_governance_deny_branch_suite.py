"""
test_governance_deny_branch_suite.py — Verifies governance DENY branches return only FunctionResponse without calling self.speak().
"""
import pytest
from unittest.mock import MagicMock
from google.genai import types
from main import ZezoLive
from core import governance


@pytest.mark.asyncio
async def test_execute_tool_deny_returns_function_response_without_speak():
    # Mock UI
    mock_ui = MagicMock()
    mock_ui.muted = False
    
    zezo = ZezoLive(mock_ui)
    zezo.speak = MagicMock()
    zezo.speak_error = MagicMock()

    # Function call with dangerous pattern (e.g., format c: or rm -rf)
    fc = types.FunctionCall(
        id="call_test_123",
        name="computer_control",
        args={"command": "rmdir /s /q c:\\windows\\system32"}
    )

    resp = await zezo._execute_tool(fc)

    # 1. Assert self.speak was NEVER called
    zezo.speak.assert_not_called()
    zezo.speak_error.assert_not_called()

    # 2. Assert return value is a valid FunctionResponse
    assert isinstance(resp, types.FunctionResponse)
    assert resp.id == "call_test_123"
    assert resp.name == "computer_control"
    assert "blocked by security governance" in resp.response["result"]

    # 3. Assert UI received log and state was reset
    mock_ui.write_log.assert_called_once()
    assert "Security Block" in mock_ui.write_log.call_args[0][0]
    assert mock_ui.set_state.call_args_list[-1][0][0] == "LISTENING"
