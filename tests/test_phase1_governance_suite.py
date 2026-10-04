"""
tests/test_phase1_governance_suite.py — Unit & Integration tests for Phase 1 (Security, Confirmation Wire & Governance Integrity)
"""
import pytest
from core import confirm, governance
from core.governance import ToolRisk, PolicyDecision


@pytest.mark.asyncio
async def test_confirm_resolve_lifecycle():
    resolved = []
    
    def sample_action():
        resolved.append("executed")
        return "Action completed successfully."

    # Bind dummy callbacks
    shown = []
    hidden = []
    confirm.bind(
        show=lambda title, detail: shown.append((title, detail)),
        hide=lambda: hidden.append(True),
        log=lambda msg: None
    )

    msg = confirm.request("test_act", "Test Action", "Detail string", sample_action)
    assert "[CONFIRMATION_PENDING]" in msg
    assert len(shown) == 1
    assert shown[0][0] == "Test Action"

    # Route accepted=True through ui_server._handle_client_message
    from core.ui_server import ZezoUIServer
    server = ZezoUIServer()
    class DummyWS:
        pass
    dummy_ws = DummyWS()
    await server._handle_client_message(dummy_ws, {"type": "confirm_response", "accepted": True})
    
    import asyncio
    await asyncio.sleep(0.1) # allow worker thread to complete

    assert "executed" in resolved
    assert len(hidden) == 1


@pytest.mark.asyncio
async def test_confirm_response_reject_and_timeout():
    resolved = []
    
    def sample_action():
        resolved.append("executed")
        return "ok"

    shown = []
    hidden = []
    confirm.bind(
        show=lambda title, detail: shown.append((title, detail)),
        hide=lambda: hidden.append(True),
        log=lambda msg: None
    )

    from core.ui_server import ZezoUIServer
    server = ZezoUIServer()
    class DummyWS:
        pass
    dummy_ws = DummyWS()

    # 1. Test accepted=False via WebSocket message
    msg = confirm.request("test_reject", "Reject Test", "Detail", sample_action)
    assert "[CONFIRMATION_PENDING]" in msg
    await server._handle_client_message(dummy_ws, {"type": "confirm_response", "accepted": False})
    import asyncio, time
    await asyncio.sleep(0.1)
    assert "executed" not in resolved
    assert len(hidden) == 1

    # 2. Test timeout expiration via WebSocket message
    msg2 = confirm.request("test_timeout", "Timeout Test", "Detail", sample_action)
    assert "[CONFIRMATION_PENDING]" in msg2
    # Simulate timeout by adjusting start time in pending record
    with confirm._lock:
        if confirm._pending:
            confirm._pending.at = time.monotonic() - (confirm.TIMEOUT_SECONDS + 5)
    
    await server._handle_client_message(dummy_ws, {"type": "confirm_response", "accepted": True}) # Should fail because expired
    await asyncio.sleep(0.1)
    assert "executed" not in resolved


def test_governance_risk_classification():
    # Verify shutdown_zezo is classified as PRIVILEGED_OS
    risk = governance.get_tool_risk("shutdown_zezo")
    assert risk == ToolRisk.PRIVILEGED_OS

    # Verify sensitive action returns ASK
    decision, reason = governance.evaluate("shutdown_zezo", {})
    assert decision == PolicyDecision.ASK

    # Verify screen_process is READ_ONLY and ALLOW
    decision, _ = governance.evaluate("screen_process", {})
    assert decision == PolicyDecision.ALLOW

    # Verify dangerous pattern is DENY
    decision, reason = governance.evaluate("computer_control", {"cmd": "format c:"})
    assert decision == PolicyDecision.DENY


def test_governance_protected_paths():
    # Attempting to access C:\Windows system files should be blocked
    decision, reason = governance.evaluate("file_controller", {"file_path": r"C:\Windows\System32\drivers\etc\hosts"})
    assert decision == PolicyDecision.DENY
