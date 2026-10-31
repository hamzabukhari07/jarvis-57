"""
tests/test_live_reconnect_intent.py — Verification for Session Reconnect Memory & Task Intent Tracking.
"""
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pending_intent import (
    set_pending_intent,
    get_pending_intent,
    clear_pending_intent,
    has_pending_intent,
)


def test_pending_intent_lifecycle():
    print("--> Testing pending_intent lifecycle...")
    clear_pending_intent()
    assert not has_pending_intent()

    # Set intent
    payload = set_pending_intent(
        task="Build context dev portfolio app",
        action="antigravity_action",
        params={"prompt": "Build context dev portfolio app"},
        target_dir="C:/Users/Test/Desktop/context-dev",
        engine="antigravity",
        status="awaiting_confirmation",
    )
    assert has_pending_intent()
    retrieved = get_pending_intent()
    assert retrieved is not None
    assert retrieved["task"] == "Build context dev portfolio app"
    assert retrieved["target_dir"] == "C:/Users/Test/Desktop/context-dev"
    assert retrieved["status"] == "awaiting_confirmation"

    # Status update to running
    set_pending_intent(
        task="Build context dev portfolio app",
        action="antigravity_action",
        status="running",
    )
    retrieved2 = get_pending_intent()
    assert retrieved2["status"] == "running"

    clear_pending_intent()
    assert not has_pending_intent()
    print("✓ pending_intent lifecycle passed.")


def test_auto_subfolder_resolution():
    print("--> Testing auto-subfolder resolution in coding engines...")
    from actions.antigravity_agent import _is_root_dir
    from core.repo_context import get_unique_project_dir

    desktop = Path.home() / "Desktop"
    assert _is_root_dir(desktop) is True

    # Ensure get_unique_project_dir creates a safe subfolder
    subfolder = get_unique_project_dir("build a sleek dashboard for analytics")
    assert _is_root_dir(subfolder) is False
    assert "dashboard" in subfolder.name or "analytics" in subfolder.name
    assert subfolder.parent.exists()
    print(f"✓ Auto-subfolder safely resolved to: {subfolder}")


def test_build_config_history_and_intent_injection():
    print("--> Testing _build_config history & intent prompt injection...")
    from main import ZezoLive

    # Instantiate mock-safe minimal ZezoLive state without initializing full hardware UI
    class MockZezoLive(ZezoLive):
        def __init__(self):
            self._asst_name = "Zezo"
            self._session_log = []
            self._rolling_recent_turns = []
            self._skill_registry = type("MockReg", (), {"format_prompt_block": lambda self: ""})()
            self._action_registry = type("MockAct", (), {"get_tool_declarations": lambda *a, **k: [], "scheduling": lambda *a, **k: None})()
            self._plugin_registry = type("MockPlg", (), {"get_tool_declarations": lambda *a, **k: [], "scheduling": lambda *a, **k: None})()
            self._resume_handle = None
            self._enhanced_live = False
            self._tuned_live = False

    zezo_instance = MockZezoLive()

    # Log 3 turns
    zezo_instance._append_session_log("User: Create a new project called context-dev")
    zezo_instance._append_session_log("Zezo: Sure, I am setting up the folder structure.")
    zezo_instance._append_session_log("User: Do it now")

    assert len(zezo_instance._session_log) == 3
    assert len(zezo_instance._rolling_recent_turns) == 3

    # Set pending intent
    set_pending_intent(
        task="Build context dev website",
        action="antigravity_action",
        target_dir="Desktop/context-dev",
        engine="antigravity",
        status="awaiting_confirmation",
    )

    # Build config
    cfg = zezo_instance._build_config()
    sys_instruction = cfg.system_instruction

    # Verify history block is present
    assert "[RECENT CONVERSATION HISTORY (ACTIVE SESSION RECONNECTED)]" in sys_instruction
    assert "Create a new project called context-dev" in sys_instruction
    assert "Do it now" in sys_instruction

    # Verify pending task block is present
    assert "[ACTIVE PENDING TASK AWAITING CONFIRMATION OR EXECUTION]" in sys_instruction
    assert "Build context dev website" in sys_instruction
    assert "Desktop/context-dev" in sys_instruction

    # Simulate session reconnect after summary reset
    zezo_instance._session_log = []
    # _rolling_recent_turns is preserved!
    assert len(zezo_instance._rolling_recent_turns) == 3

    cfg_reconnect = zezo_instance._build_config()
    sys_instruction_reconnect = cfg_reconnect.system_instruction

    assert "[RECENT CONVERSATION HISTORY (ACTIVE SESSION RECONNECTED)]" in sys_instruction_reconnect
    assert "Create a new project called context-dev" in sys_instruction_reconnect
    print("✓ _build_config history & intent prompt injection verified.")

    clear_pending_intent()


if __name__ == "__main__":
    test_pending_intent_lifecycle()
    test_auto_subfolder_resolution()
    test_build_config_history_and_intent_injection()
    print("\nALL TARGETED RUNTIME TESTS PASSED SUCCESSFULLY! ✅")
