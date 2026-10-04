"""
tests/test_phase1_governance_suite.py — Unit & Integration tests for Phase 1 (Security, Confirmation Wire & Governance Integrity)
"""
import pytest
from core import confirm, governance
from core.governance import ToolRisk, PolicyDecision


def test_confirm_resolve_lifecycle():
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

    # Resolve with accepted=True
    confirm.resolve(accepted=True)
    import time
    time.sleep(0.1) # allow worker thread to complete

    assert "executed" in resolved
    assert len(hidden) == 1


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
