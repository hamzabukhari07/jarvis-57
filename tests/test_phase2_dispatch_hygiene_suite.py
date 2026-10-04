import pytest
from core.action_loader import discover_actions, ActionRegistry
from core.governance import get_tool_risk, ToolRisk
from core.circuit_breaker import get_tool_tier

def test_action_loader_risk_and_enabled_attributes():
    from pathlib import Path
    actions_dir = Path(__file__).parent.parent / "actions"
    reg = discover_actions(actions_dir)
    declarations = reg.get_tool_declarations()
    assert len(declarations) > 0, "Expected tool declarations from action loader"

    for decl in declarations:
        name = decl.get("name")
        rec = reg.get(name)
        assert rec is not None, f"Expected record for tool {name}"
        assert rec.risk in ("read_only", "local_mutation", "external_mutation", "code_execution"), f"Invalid risk '{rec.risk}' on tool {name}"
        assert isinstance(rec.enabled, bool), f"Invalid enabled flag on tool {name}"

def test_governance_dynamic_risk_lookup():
    assert get_tool_risk("web_search") == ToolRisk.READ_ONLY
    assert get_tool_risk("file_controller") == ToolRisk.LOCAL_MUTATION
    assert get_tool_risk("send_message") == ToolRisk.EXTERNAL_MUTATION
    assert get_tool_risk("opencode_run") == ToolRisk.CODE_EXECUTION

def test_circuit_breaker_tier_mapping():
    from core.circuit_breaker import RiskTier
    assert get_tool_tier("web_search") == RiskTier.L0_READ_ONLY
    assert get_tool_tier("opencode_run") == RiskTier.L2_DESTRUCTIVE
    assert get_tool_tier("send_message") == RiskTier.L1_LOW_RISK
