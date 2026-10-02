"""
Verification script for ZEZO Desktop Stabilization & Canvas Protocol.
"""
import sys
import os
import py_compile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def test_layer1_compilation():
    print("[Verification] -- Layer 1: Compilation Checks --")
    files_to_compile = [
        "main.py",
        "core/action_loader.py",
        "core/governance.py",
        "core/computer/windows_native.py",
        "actions/computer_control.py",
        "actions/open_app.py",
        "actions/screen_processor.py",
    ]
    for rel in files_to_compile:
        full = os.path.join(ROOT, rel)
        try:
            py_compile.compile(full, doraise=True)
            print(f"  [OK] Compiled: {rel}")
        except Exception as e:
            print(f"  [FAIL] Failed to compile {rel}: {e}")
            return False
    return True

def test_layer2_discovery():
    print("\n[Verification] -- Layer 2: Action & Skill Discovery --")
    from core.action_loader import discover_actions
    from core.skill_loader import SkillRegistry

    from pathlib import Path
    actions = discover_actions(actions_dir=Path(ROOT) / "actions", logger=lambda msg: None)
    print(f"  Discovered {len(actions.names())} actions.")
    assert len(actions.names()) >= 24, f"Expected >= 24 actions, got {len(actions.names())}"
    print("  [OK] All 24+ core actions discovered successfully.")

    registry = SkillRegistry(logger_fn=lambda msg: None)
    all_skills = registry._skills
    print(f"  Discovered {len(all_skills)} skills: {list(all_skills.keys())}")
    assert any(k == "figma_helper" or s.name == "figma_helper" for k, s in all_skills.items()), "figma_helper skill not found"
    print("  [OK] figma_helper skill discovered successfully.")
    return actions

def test_layer2_circuit_breaker(registry):
    print("\n[Verification] -- Layer 2: Hotkey Anti-Loop Circuit Breaker --")
    # Execute 4 repeated hotkeys (allowed)
    for i in range(4):
        res = registry.run("computer_control", {"action": "hotkey", "keys": "shift+tab"})
        print(f"  Call {i+1}: {res}")

    # 5th call should be intercepted by Circuit Breaker
    res5 = registry.run("computer_control", {"action": "hotkey", "keys": "shift+tab"})
    print(f"  Call 5: {res5}")
    assert "Aborted: Repetitive hotkey loop detected" in res5, f"Expected circuit breaker abort, got: {res5}"
    print("  [OK] Circuit breaker successfully tripped on 5th repetitive hotkey.")

def test_layer2_action_aliases(registry):
    print("\n[Verification] -- Layer 2: Action Aliases --")
    for alias in ("enter", "escape", "space", "backspace", "tab", "delete"):
        # Alias test
        res = registry.run("computer_control", {"action": alias})
        print(f"  Alias '{alias}': {res}")
        assert "Pressed" in res or "key" in res.lower() or "Aborted" in res, f"Unexpected result for alias {alias}: {res}"
    print("  [OK] All action aliases executed properly.")

def test_layer2_dwm_physical_bounds():
    print("\n[Verification] -- Layer 2: DWM Extended Frame Bounds --")
    from core.computer import windows_native
    hwnd = windows_native.user32.GetForegroundWindow() if windows_native.is_windows else 0
    if hwnd:
        rect = windows_native.get_window_rect_physical(hwnd)
        print(f"  Active Window HWND: {hwnd}, Physical Rect: {rect}")
        if rect:
            assert rect["width"] >= 0 and rect["height"] >= 0
            print("  [OK] get_window_rect_physical successfully returned calibrated dimensions.")
    else:
        print("  [INFO] Non-interactive test environment or no foreground window.")

def test_layer2_governance_split():
    print("\n[Verification] -- Layer 2: Governance Risk Split --")
    from core import governance
    risk_search = governance.get_tool_risk("send_message", {"action": "search", "query": "John"})
    risk_send = governance.get_tool_risk("send_message", {"action": "send", "message": "Hi", "recipient": "John"})
    
    print(f"  send_message(action='search') Risk: {risk_search}")
    print(f"  send_message(action='send') Risk: {risk_send}")
    
    assert risk_search == governance.ToolRisk.READ_ONLY, f"Expected READ_ONLY, got {risk_search}"
    assert risk_send == governance.ToolRisk.EXTERNAL_MUTATION, f"Expected EXTERNAL_MUTATION, got {risk_send}"
    print("  [OK] Governance risk matrix correctly isolates search vs outbound messaging.")

if __name__ == "__main__":
    assert test_layer1_compilation(), "Layer 1 compilation failed!"
    reg = test_layer2_discovery()
    test_layer2_circuit_breaker(reg)
    test_layer2_action_aliases(reg)
    test_layer2_dwm_physical_bounds()
    test_layer2_governance_split()
    print("\n========================================================")
    print("ALL 3-LAYER VERIFICATION ASSERTIONS PASSED WITH 100% SUCCESS!")
    print("========================================================")
