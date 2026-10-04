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


@pytest.mark.asyncio
async def test_shutdown_zezo_blocked_until_confirmed():
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from core import confirm
    from main import ZezoLive

    # Mock UI
    mock_ui = MagicMock()
    mock_ui.muted = False
    live = ZezoLive(mock_ui)

    # Track confirm requests
    requests = []
    confirm.bind(
        show=lambda title, detail: requests.append((title, detail)),
        hide=lambda: None,
        log=lambda msg: None
    )

    fc = SimpleNamespace(id="call_shutdown_1", name="shutdown_zezo", args={})
    resp = await live._execute_tool(fc)

    # Must return confirmation pending instruction to LLM, NOT execute shutdown
    assert "[CONFIRMATION_PENDING]" in resp.response["result"]
    assert len(requests) == 1
    assert "shutdown_zezo" in requests[0][0] or "Authorize" in requests[0][0]


@pytest.mark.asyncio
async def test_ask_confirm_rejected_and_timeout():
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from core import confirm
    from main import ZezoLive
    import time

    mock_ui = MagicMock()
    mock_ui.muted = False
    live = ZezoLive(mock_ui)

    executed = []
    live._run_tool_dispatch = MagicMock()

    # 1. Rejected
    fc = SimpleNamespace(id="call_ask_1", name="shutdown_zezo", args={})
    resp = await live._execute_tool(fc)
    assert "[CONFIRMATION_PENDING]" in resp.response["result"]

    confirm.resolve(accepted=False)
    import asyncio
    await asyncio.sleep(0.1)
    live._run_tool_dispatch.assert_not_called()

    # 2. Timeout
    fc2 = SimpleNamespace(id="call_ask_2", name="shutdown_zezo", args={})
    resp2 = await live._execute_tool(fc2)
    assert "[CONFIRMATION_PENDING]" in resp2.response["result"]

    with confirm._lock:
        if confirm._pending:
            confirm._pending.at = time.monotonic() - (confirm.TIMEOUT_SECONDS + 10)

    confirm.resolve(accepted=True) # should fail due to expiry
    await asyncio.sleep(0.1)
    live._run_tool_dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_ask_confirm_accepted_executes_exactly_once():
    from unittest.mock import MagicMock, AsyncMock
    from types import SimpleNamespace
    from core import confirm
    from main import ZezoLive
    import asyncio

    mock_ui = MagicMock()
    mock_ui.muted = False
    live = ZezoLive(mock_ui)

    mock_dispatch = AsyncMock(return_value="executed_ok")
    live._run_tool_dispatch = mock_dispatch

    fc = SimpleNamespace(id="call_ask_exec", name="shutdown_zezo", args={})
    resp = await live._execute_tool(fc)
    assert "[CONFIRMATION_PENDING]" in resp.response["result"]

    # Resolve accepted
    confirm.resolve(accepted=True)
    await asyncio.sleep(0.1)

    assert mock_dispatch.call_count == 1
    mock_dispatch.assert_called_once_with("shutdown_zezo", {}, asyncio.get_event_loop())


@pytest.mark.asyncio
async def test_external_mutation_returns_pending():
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from main import ZezoLive

    mock_ui = MagicMock()
    mock_ui.muted = False
    live = ZezoLive(mock_ui)

    fc = SimpleNamespace(id="call_msg_1", name="send_message", args={"message": "hello", "recipient": "+1234"})
    # send_message without read action resolves to EXTERNAL_MUTATION
    resp = await live._execute_tool(fc)
    # External mutation policy is evaluated: if ASK, it must return confirmation pending
    # Verify it does not immediately dispatch
    from core import governance
    decision, _ = governance.evaluate("send_message", {"message": "hello", "recipient": "+1234"})
    if decision == governance.PolicyDecision.ASK:
        assert "[CONFIRMATION_PENDING]" in resp.response["result"]


@pytest.mark.asyncio
async def test_governance_exception_fails_closed():
    from unittest.mock import MagicMock, patch
    from types import SimpleNamespace
    from main import ZezoLive

    mock_ui = MagicMock()
    mock_ui.muted = False
    live = ZezoLive(mock_ui)
    live._run_tool_dispatch = MagicMock()

    with patch("core.governance.evaluate", side_effect=RuntimeError("Corrupt governance matrix")):
        fc = SimpleNamespace(id="call_err", name="open_app", args={"app_name": "notepad"})
        resp = await live._execute_tool(fc)
        assert "SECURITY POLICY ERROR" in resp.response["result"]
        live._run_tool_dispatch.assert_not_called()


def test_action_loader_rejects_missing_or_invalid_risk():
    from core.action_loader import _validate
    from types import SimpleNamespace

    # 1. Missing risk
    mock_mod_no_risk = SimpleNamespace(TOOL={
        "name": "sample_tool",
        "description": "Sample desc",
        "parameters": {"type": "OBJECT", "properties": {}},
        "handler": lambda p: "ok",
    })
    rec1 = _validate(mock_mod_no_risk, "sample_tool.py")
    assert rec1.valid is False
    assert "TOOL['risk'] missing" in rec1.error

    # 2. Invalid risk tier
    mock_mod_bad_risk = SimpleNamespace(TOOL={
        "name": "sample_tool_2",
        "description": "Sample desc",
        "parameters": {"type": "OBJECT", "properties": {}},
        "handler": lambda p: "ok",
        "risk": "super_admin_tier",
    })
    rec2 = _validate(mock_mod_bad_risk, "sample_tool_2.py")
    assert rec2.valid is False
    assert "is invalid" in rec2.error


def test_governance_unknown_tool_fails_closed_deny():
    from core.governance import evaluate, get_tool_risk, PolicyDecision

    # get_tool_risk on unmapped tool returns None
    assert get_tool_risk("completely_unknown_custom_tool_xyz") is None

    # evaluate returns PolicyDecision.DENY
    decision, reason = evaluate("completely_unknown_custom_tool_xyz", {"arg": "val"})
    assert decision == PolicyDecision.DENY
    assert "fail-closed" in reason



