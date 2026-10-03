"""
tests/test_phase4_specialist_fleet_suite.py — Multi-Agent Fleet, Dynamic Engine/Model Binding & Michael Orchestrator Suite.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from pathlib import Path
from actions.fleet_control import fleet_control, TOOL
from core.action_loader import discover_actions
from core.fleet_manager import fleet_manager


class TestPhase4SpecialistFleetSuite:
    def test_fleet_control_discovery_and_schema(self):
        assert TOOL["name"] == "fleet_control"
        assert "dispatch" in TOOL["parameters"]["properties"]["action"]["enum"]
        assert "model_id" in TOOL["parameters"]["properties"]

        registry = discover_actions(Path(__file__).parent.parent / "actions")
        assert "fleet_control" in registry._actions
        assert registry._actions["fleet_control"].valid is True

    def test_roster_contains_ali_ahmad_dwight_michael(self):
        deck = fleet_manager.get_fleet_deck_state()
        agent_names = [a["name"].upper() for a in deck]
        assert any("ALI" in name for name in agent_names)
        assert any("AHMAD" in name for name in agent_names)
        assert any("DWIGHT" in name for name in agent_names)
        assert any("MICHAEL" in name for name in agent_names)

    def test_dynamic_engine_and_model_binding(self):
        ali = fleet_manager.get_agent("ALI")
        assert ali is not None
        assert ali.default_tool == "antigravity_run"
        assert ali.model_id == "gemini-3.7-flash-medium"

        ahmad = fleet_manager.get_agent("AHMAD")
        assert ahmad is not None
        assert ahmad.default_tool == "opencode_run"
        assert ahmad.model_id == "opencode/mimo-v2.5-free"

        dwight = fleet_manager.get_agent("DWIGHT")
        assert dwight is not None
        assert dwight.default_tool == "kilo_run"
        assert dwight.model_id == "kilo/stepfun/step-3.7-flash:free"

    def test_hire_agent_with_custom_model_and_tool(self):
        res = fleet_control({
            "action": "hire",
            "agent_id": "TURING",
            "role": "Algorithmic Specialist",
            "default_tool": "opencode_run",
            "model_id": "opencode/big-pickle",
            "specialty": "Graph algorithms and dynamic programming",
        })
        assert "Hired new fleet agent" in res
        turing = fleet_manager.get_agent("TURING")
        assert turing is not None
        assert turing.default_tool == "opencode_run"
        assert turing.model_id == "opencode/big-pickle"

        # Clean up
        fleet_control({"action": "fire", "agent_id": "TURING"})
        assert fleet_manager.get_agent("TURING") is None

    def test_michael_auto_decomposition(self):
        decomp_res = fleet_manager.decompose_and_dispatch(
            "Build full-stack e-commerce app with frontend UI and backend auth API"
        )
        assert decomp_res["success"] is True
        assert decomp_res["orchestrator"] == "MICHAEL"
        assert decomp_res["decomposed_count"] >= 2
        assert len(decomp_res["tasks"]) >= 2
