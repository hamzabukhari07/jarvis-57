"""
tests/test_phase4_agent_capability_registry_suite.py
Verification suite for Phase 4: Dynamic Agent Capability Registry & Per-Agent Tool Permissions.
Tests:
1. Agent schema includes allowed_tools, allowed_skills, and capabilities.
2. FleetManager properly saves and loads allowed_tools, allowed_skills, capabilities.
3. ActionRegistry.get_tool_declarations scopes tools when agent_id is provided.
4. ActionRegistry.get_tool_declarations filters tools by execution mode (coding / safe).
5. ActionRegistry.filter_tools returns diagnostic reasons for allowed and filtered tools.
6. Main orchestrator / unfiltered requests maintain full access to all system tools.
"""

import pytest
from core.fleet_manager import fleet_manager
from core.action_loader import get_action_registry, ActionRegistry


@pytest.fixture(scope="module")
def registry():
    return get_action_registry()


def test_fleet_agent_schema_attributes():
    agent = fleet_manager.get_agent("ALI")
    assert agent is not None
    assert isinstance(agent.allowed_tools, list)
    assert isinstance(agent.allowed_skills, list)
    assert isinstance(agent.capabilities, list)
    assert "antigravity_run" in agent.allowed_tools
    assert "hamza_taste" in agent.allowed_skills
    assert "web_design" in agent.capabilities


def test_agent_to_dict_and_fleet_deck_export():
    state = fleet_manager.get_fleet_deck_state()
    assert len(state) >= 6
    ali_entry = next((a for a in state if a["id"] == "ALI"), None)
    assert ali_entry is not None
    assert "allowed_tools" in ali_entry
    assert "antigravity_run" in ali_entry["allowed_tools"]
    assert "allowed_skills" in ali_entry
    assert "capabilities" in ali_entry


def test_get_tool_declarations_unfiltered(registry):
    # Master orchestrator without agent_id receives all enabled discovered tools
    decls = registry.get_tool_declarations()
    names = {d["name"] for d in decls}
    assert "antigravity_run" in names
    assert "opencode_run" in names
    assert "web_search" in names
    assert "computer_control" in names
    assert len(names) >= 20


def test_get_tool_declarations_scoped_by_agent(registry):
    # Ali: specialized in UI/frontend
    ali_decls = registry.get_tool_declarations(agent_id="ALI")
    ali_names = {d["name"] for d in ali_decls}
    assert "antigravity_run" in ali_names
    assert "extract_design_system" in ali_names
    # Media/weather/gaming tools are not in Ali's allowed_tools
    assert "weather_report" not in ali_names
    assert "game_updater" not in ali_names
    assert "flight_finder" not in ali_names

    # Ahmad: specialized in backend/database
    ahmad_decls = registry.get_tool_declarations(agent_id="AHMAD")
    ahmad_names = {d["name"] for d in ahmad_decls}
    assert "opencode_run" in ahmad_names
    assert "code_helper" in ahmad_names
    assert "weather_report" not in ahmad_names


def test_get_tool_declarations_scoped_by_mode(registry):
    # 'coding' mode excludes entertainment / non-dev tools
    coding_decls = registry.get_tool_declarations(mode="coding")
    coding_names = {d["name"] for d in coding_decls}
    assert "weather_report" not in coding_names
    assert "flight_finder" not in coding_names
    assert "game_updater" not in coding_names
    assert "opencode_run" in coding_names
    assert "antigravity_run" in coding_names


def test_filter_tools_diagnostic_inspection(registry):
    res = registry.filter_tools(agent_id="ALI")
    assert res["agent_id"] == "ALI"
    assert res["agent_name"] == "Ali"
    assert res["allowed_count"] > 0
    assert res["filtered_count"] > 0

    allowed_names = {t["tool"] for t in res["allowed_tools"]}
    assert "antigravity_run" in allowed_names

    filtered_tools = {t["tool"]: t["reason"] for t in res["filtered_tools"]}
    assert "weather_report" in filtered_tools
    assert "not_in_agent_permissions" in filtered_tools["weather_report"]
