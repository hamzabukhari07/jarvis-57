"""
test_tool_collision_and_governance_suite.py — Regression test replicating main.py startup.

Verifies:
1. discover_actions with reserved_names = inline names yields ZERO rejections.
2. Every declared tool (inline + discovered actions) evaluates in governance without unknown-tool DENY.
3. System status and manage_monitor are discovered actions.
4. Screen process is an inline tool.
"""
from pathlib import Path
import pytest
from main import TOOL_DECLARATIONS
from core.action_loader import discover_actions
from core.governance import evaluate, PolicyDecision, INLINE_TOOL_RISKS


def test_main_startup_tool_discovery_zero_rejections():
    base_dir = Path(__file__).resolve().parent.parent
    inline_names = {t["name"] for t in TOOL_DECLARATIONS}
    
    assert "screen_process" in inline_names, "screen_process must remain inline"
    assert "system_status" not in inline_names, "system_status must be a real action, not inline"
    assert "manage_monitor" not in inline_names, "manage_monitor must be a real action, not inline"

    rejected = []
    def record_logger(msg: str):
        if "Action rejected" in msg:
            rejected.append(msg)

    reg = discover_actions(
        actions_dir=base_dir / "actions",
        reserved_names=inline_names,
        logger=record_logger,
    )

    assert len(rejected) == 0, f"Discovered actions had collision or validation rejections: {rejected}"
    assert reg.has("system_status"), "system_status must be registered as an active action"
    assert reg.has("manage_monitor"), "manage_monitor must be registered as an active action"


def test_governance_evaluate_every_declared_tool():
    base_dir = Path(__file__).resolve().parent.parent
    inline_names = {t["name"] for t in TOOL_DECLARATIONS}
    reg = discover_actions(
        actions_dir=base_dir / "actions",
        reserved_names=inline_names,
        logger=lambda _: None,
    )

    all_decls = TOOL_DECLARATIONS + reg.get_tool_declarations()
    declared_names = {(d.get("name") if isinstance(d, dict) else getattr(d, "name", "")) for d in all_decls}

    for name in declared_names:
        assert name, "Tool name cannot be empty"
        decision, reason = evaluate(name, {})
        assert "unknown and unregistered in governance taxonomy" not in reason, (
            f"Tool '{name}' failed closed with unknown tool DENY: {reason}"
        )
