"""
Unit and regression tests for Dual-AI Skill Runner Subsystem.
Creator: Hamza Bukhari
"""

import json
import time
from unittest import mock
import pytest
import requests

from core.llm_client import call_groq_tools
from core.skill_runner import SkillRunner, truncate_tool_output
from actions.run_skill import TOOL, handler


def test_call_groq_tools_success():
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Running git status",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "run_command",
                                "arguments": json.dumps({"command": "git status"}),
                            },
                        }
                    ],
                }
            }
        ]
    }

    with mock.patch("memory.config_manager.get_groq_api_key", return_value="dummy_groq_key"):
        with mock.patch("requests.post", return_value=mock_resp) as mock_post:
            tools = [
                {
                    "name": "run_command",
                    "description": "Run shell command",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {"command": {"type": "STRING"}},
                    },
                }
            ]
            res = call_groq_tools([{"role": "user", "content": "status"}], tools)

            assert res["content"] == "Running git status"
            assert len(res["tool_calls"]) == 1
            assert res["tool_calls"][0]["name"] == "run_command"
            assert res["tool_calls"][0]["arguments"] == {"command": "git status"}

            called_json = mock_post.call_args[1]["json"]
            assert called_json["tools"][0]["function"]["parameters"]["type"] == "object"
            assert called_json["tools"][0]["function"]["parameters"]["properties"]["command"]["type"] == "string"


def test_call_groq_tools_429_raises():
    mock_429 = mock.MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate limit reached"

    with mock.patch("memory.config_manager.get_groq_api_key", return_value="dummy_groq_key"):
        with mock.patch("requests.post", return_value=mock_429):
            with pytest.raises(requests.exceptions.HTTPError):
                call_groq_tools([{"role": "user", "content": "hi"}], [])


def test_call_groq_tools_timeout_raises():
    with mock.patch("memory.config_manager.get_groq_api_key", return_value="dummy_groq_key"):
        with mock.patch("requests.post", side_effect=requests.exceptions.Timeout("Timeout")):
            with pytest.raises(requests.exceptions.Timeout):
                call_groq_tools([{"role": "user", "content": "hi"}], [])


def test_truncate_tool_output():
    short = "Hello"
    assert truncate_tool_output(short, 1500) == short

    long_str = "X" * 3000
    res = truncate_tool_output(long_str, 1500)
    assert len(res) <= 1500
    assert "Memory Guard: Output truncated" in res


def test_skill_runner_scoping():
    runner = SkillRunner("website_build", {"prompt": "hero section"})
    content, req_tools = runner._load_skill()
    scoped = runner._resolve_scoped_tools(content, req_tools)
    assert len(scoped) >= 1
    assert any(d["name"] == "browser_control" for d in scoped) or len(scoped) <= 8


def test_skill_runner_stateful_fallback():
    runner = SkillRunner("website_build", {"prompt": "test"})
    runner.completed_steps = [
        {"step": 1, "tool": "step1_tool", "arguments": {}, "result": "step 1 success", "engine": "groq"}
    ]

    mock_resp = mock.MagicMock()
    mock_resp.text = "All steps complete."
    mock_resp.function_calls = None

    mock_client = mock.MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with mock.patch("core.gemini.client", return_value=mock_client):
        step_res = runner._call_gemini_step(
            step_idx=2,
            scoped_declarations=[{"name": "test_tool", "parameters": {}}],
            system_prompt="sys prompt",
        )
        assert step_res["content"] == "All steps complete."
        assert step_res["tool_calls"] == []

        call_args = mock_client.models.generate_content.call_args[1]
        contents = call_args["contents"]
        # Verify step 1 output was passed in context to avoid repetition
        assert "step 1 success" in contents
        assert "DO NOT REPEAT" in contents


def test_run_skill_action_handler():
    # 1. Invalid skill
    res = handler({"skill_name": "unknown_random_skill"})
    assert "not found" in res.lower()

    # 2. Existing skill
    t0 = time.perf_counter()
    res = handler({"skill_name": "website_build", "parameters": {"section": "header"}})
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 50
    assert "Started skill" in res or "Delegated skill" in res
