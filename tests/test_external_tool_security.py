"""
tests/test_external_tool_security.py — Tests for centralized choke point, PathJail & risk-tier gating.
"""

from pathlib import Path
import pytest

from core.path_jail import SecurityAccessDenied as PathSecurityAccessDenied
from core.tool_executor import CallerContext, SecurityAccessDenied, ToolExecutor
from actions.antigravity_agent import antigravity_action
from actions.opencode_agent import opencode_agent
from actions.kilo_agent import kilo_agent


def test_antigravity_action_rejects_filesystem_root():
    with pytest.raises(PathSecurityAccessDenied) as exc:
        antigravity_action({"prompt": "build site", "project_path": "C:\\"})
    assert "strictly denied" in str(exc.value).lower()


def test_opencode_action_rejects_filesystem_root():
    with pytest.raises(PathSecurityAccessDenied) as exc:
        opencode_agent({"prompt": "build site", "project_path": "C:\\"})
    assert "strictly denied" in str(exc.value).lower()


def test_kilo_action_rejects_filesystem_root():
    with pytest.raises(PathSecurityAccessDenied) as exc:
        kilo_agent({"prompt": "build site", "project_path": "C:\\"})
    assert "strictly denied" in str(exc.value).lower()


def test_l0_agent_cannot_invoke_external_engines():
    from core.agents.registry import check_agent_tool_permission, get_agent_registry

    registry = get_agent_registry()
    for agent_id, agent in registry.agents.items():
        if agent.risk_tier == "L0_READ_ONLY":
            for tool in ("antigravity_run", "opencode_run", "kilo_run"):
                allowed, reason = check_agent_tool_permission(agent.id, tool)
                assert not allowed
                low_r = reason.lower()
                assert "not allowed" in low_r or "not in allowed_tools" in low_r or "not permitted" in low_r or "tier" in low_r
            break
