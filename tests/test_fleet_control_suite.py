"""
tests/test_fleet_control_suite.py — Multi-Agent Fleet Control & Orchestration Unit Test Suite.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from pathlib import Path
from actions.fleet_control import fleet_control, TOOL
from core.action_loader import discover_actions
from core.fleet_manager import fleet_manager


class TestFleetControlSuite:
    def test_tool_schema_and_discovery(self):
        assert TOOL["name"] == "fleet_control"
        assert TOOL["behavior"] == "BLOCKING"
        assert TOOL["parameters"]["type"] == "OBJECT"
        assert callable(TOOL["handler"])

        registry = discover_actions(Path(__file__).parent.parent / "actions")
        assert "fleet_control" in registry._actions
        assert registry._actions["fleet_control"].valid is True

    def test_list_agents(self):
        res = fleet_control({"action": "list_agents"})
        assert "Active Fleet Roster" in res
        assert "Michael Scott" in res or "MICHAEL" in res.upper()

    def test_get_status_existing_and_fallback(self):
        res = fleet_control({"action": "get_status", "agent_id": "MICHAEL"})
        assert "Michael Scott" in res or "IDLE" in res or "WORKING" in res

        res_empty = fleet_control({"action": "get_status"})
        assert "Active Fleet Roster" in res_empty

    def test_hire_and_fire_lifecycle(self):
        hire_res = fleet_control({
            "action": "hire",
            "agent_id": "TEST_BOT",
            "role": "Integration Test Specialist",
            "default_tool": "opencode_run",
        })
        assert "Hired new fleet agent" in hire_res
        assert "Test_Bot" in hire_res or "TEST_BOT" in hire_res.upper()

        status_res = fleet_control({"action": "get_status", "agent_id": "TEST_BOT"})
        assert "Test_Bot" in status_res or "TEST_BOT" in status_res.upper()

        fire_res = fleet_control({"action": "fire", "agent_id": "TEST_BOT"})
        assert "Decommissioned agent 'TEST_BOT'" in fire_res

    def test_schema_validation_and_desk_allocation(self):
        # Empty name/id validation
        invalid_res = fleet_manager.save_agent_profile({"id": "   "})
        assert invalid_res["success"] is False
        assert "cannot be empty" in invalid_res["error"]

        # Valid custom agent hire with auto desk allocation
        agent_data = {
            "name": "Stanley Hudson QA",
            "role": "AST Quality Assurance",
            "default_tool": "kilo_run",
            "color": "#invalid_color",  # Should fallback to #3b82f6
        }
        res = fleet_manager.save_agent_profile(agent_data)
        assert res["success"] is True
        agent = res["agent"]
        assert agent["color"] == "#3b82f6"
        assert agent["risk_tier"] == "L1_MUTATION"
        assert agent["desk_x"] > 0
        assert agent["desk_y"] > 0

        # Soul update
        soul_res = fleet_manager.save_agent_soul(agent["id"], "Custom QA persona prompt")
        assert soul_res["success"] is True
        assert soul_res["soul"] == "Custom QA persona prompt"

        # Cleanup
        del_res = fleet_manager.delete_agent(agent["id"])
        assert del_res["success"] is True

    def test_dispatch_validation_errors(self):
        res_no_agent = fleet_control({"action": "dispatch", "task": "some task"})
        assert "Error: agent_id is required" in res_no_agent

        res_no_task = fleet_control({"action": "dispatch", "agent_id": "MICHAEL"})
        assert "Error: task instruction is required" in res_no_task

    def test_update_agent_profile(self):
        # Hire temporary agent
        fleet_control({"action": "hire", "agent_id": "ALAN", "role": "Full-Stack Dev"})
        
        # Update agent to research role and custom tools
        up_res = fleet_control({
            "action": "update",
            "agent_id": "ALAN",
            "role": "Lead Researcher",
            "default_tool": "agent_reach",
            "allowed_tools": ["agent_reach", "web_search", "web_read_page"],
        })
        assert "Successfully updated profile for agent" in up_res
        assert "agent_reach" in up_res

        agent = fleet_manager.get_agent("ALAN")
        assert agent is not None
        assert agent.role == "Lead Researcher"
        assert agent.default_tool == "agent_reach"
        assert "agent_reach" in agent.allowed_tools
        assert "web_search" in agent.allowed_tools

        # Cleanup
        fleet_control({"action": "fire", "agent_id": "ALAN"})

    def test_smart_role_tool_inference(self):
        # Research role without explicit default tool
        res = fleet_manager.save_agent_profile({
            "id": "RESEARCH_BOT",
            "role": "Detailed Web Researcher",
            "specialty": "deep web research and analysis",
        })
        assert res["success"] is True
        agent = res["agent"]
        assert agent["default_tool"] == "agent_reach"
        assert "agent_reach" in agent["allowed_tools"]
        assert "web_search" in agent["allowed_tools"]

        # UI role without explicit default tool
        res_ui = fleet_manager.save_agent_profile({
            "id": "UI_BOT",
            "role": "Senior Frontend Designer",
            "specialty": "modern responsive UI and Tailwind CSS",
        })
        assert res_ui["success"] is True
        agent_ui = res_ui["agent"]
        assert agent_ui["default_tool"] == "antigravity_run"
        assert "antigravity_run" in agent_ui["allowed_tools"]

        # Cleanup
        fleet_manager.delete_agent("RESEARCH_BOT")
        fleet_manager.delete_agent("UI_BOT")

    def test_unknown_action_error(self):
        res = fleet_control({"action": "fly_to_mars"})
        assert "Unknown fleet_control action 'fly_to_mars'" in res

    def test_kilo_and_opencode_run_in_place_handling(self, monkeypatch, tmp_path):
        import actions.kilo_agent as ka
        import actions.opencode_agent as oa

        test_dir = tmp_path / "test_proj"
        test_dir.mkdir()

        # Mock workers so we don't spawn real binaries in unit tests
        kilo_called = []
        opencode_called = []

        monkeypatch.setattr(ka, "_find_kilo_bin", lambda: "fake_kilo")
        monkeypatch.setattr(ka, "_run_worker", lambda params, ctx: kilo_called.append((params, ctx)) or {"status": "success"})

        monkeypatch.setattr(oa, "_find_opencode_bin", lambda: "fake_opencode")
        monkeypatch.setattr(oa, "_run_worker", lambda params, ctx: opencode_called.append((params, ctx)) or {"status": "success"})

        # Call with run_in_place=True
        dummy_ctx = object()
        res_k = ka.kilo_agent({
            "task": "refactor foo.py",
            "project_path": str(test_dir),
            "run_in_place": True,
            "task_ctx": dummy_ctx,
        })
        assert "success" in res_k
        assert len(kilo_called) == 1
        assert kilo_called[0][1] is dummy_ctx

        res_o = oa.opencode_agent({
            "task": "build feature bar.py",
            "project_path": str(test_dir),
            "run_in_place": True,
            "task_ctx": dummy_ctx,
        })
        assert "success" in res_o
        assert len(opencode_called) == 1
        assert opencode_called[0][1] is dummy_ctx
