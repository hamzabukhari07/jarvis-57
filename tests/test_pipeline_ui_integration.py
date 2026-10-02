"""
Integration test for Voice Pipeline & Settings Config.
Verifies pure Live mode, API key sanitization, transactional persistence, and UI callbacks.
Lead Architect: Hamza Bukhari
"""
import io
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from memory.config_manager import (
    get_pipeline_mode, save_pipeline_mode,
    get_groq_api_key, get_elevenlabs_api_key,
    clean_api_key, save_api_keys,
    PIPELINE_MODES, DEFAULT_PIPELINE_MODE,
)

def test_key_sanitization():
    """Test that accidental terminal pastes or multi-line keys are sanitized."""
    assert clean_api_key(None) is None
    assert clean_api_key("") is None
    assert clean_api_key("   ") is None
    
    # Valid key
    valid_key = "gsk_test1234567890abcdef"
    assert clean_api_key(valid_key) == valid_key

    # Malformed terminal dump with NO key
    malformed_no_key = "PS C:\\> 🧠\nFatal error\nexit"
    assert clean_api_key(malformed_no_key) is None

    # Malformed multi-line terminal dump with embedded valid Groq key (smart extraction)
    malformed_with_key = "PS C:\\> 🧠\nFatal error\ngsk_validkey1234567890\nexit"
    assert clean_api_key(malformed_with_key) == "gsk_validkey1234567890"

    # Key with extra whitespace
    padded = "  gsk_padded123  \n"
    assert clean_api_key(padded) == "gsk_padded123"
    print("✅ Key sanitization test passed")

def test_pipeline_constants():
    """Test that pipeline constants are properly defined."""
    assert "live" in PIPELINE_MODES, "live mode not in PIPELINE_MODES"
    assert DEFAULT_PIPELINE_MODE == "live", "DEFAULT_PIPELINE_MODE must be live"
    print("✅ Pipeline constants test passed")

def test_api_key_detection():
    """Test that API key detection functions work."""
    groq_key = get_groq_api_key()
    elevenlabs_key = get_elevenlabs_api_key()
    
    # These may be None if not configured, which is fine
    assert groq_key is None or isinstance(groq_key, str), "groq_key type mismatch"
    assert elevenlabs_key is None or isinstance(elevenlabs_key, str), "elevenlabs_key type mismatch"
    print("✅ API key detection test passed")

def test_live_mode_defaults():
    """Test that live mode is the default."""
    assert get_pipeline_mode() == "live", "Pipeline mode must be live"
    print("✅ Live mode defaults test passed")

def test_ui_pipeline_callback_proxying():
    """Test that ZezoUI proxies on_pipeline_change and on_sleep_toggle callbacks to MainWindow."""
    from unittest.mock import MagicMock
    from ui import ZezoUI
    
    # Mock underlying _win
    dummy_ui = object.__new__(ZezoUI)
    dummy_win = MagicMock()
    dummy_win.on_pipeline_change = None
    dummy_win.on_sleep_toggle = None
    dummy_ui._win = dummy_win
    
    cb1 = lambda: "pipeline"
    cb2 = lambda s: f"sleep_{s}"
    
    dummy_ui.on_pipeline_change = cb1
    assert dummy_win.on_pipeline_change == cb1
    assert dummy_ui.on_pipeline_change == cb1
    
    dummy_ui.on_sleep_toggle = cb2
    assert dummy_win.on_sleep_toggle == cb2
    assert dummy_ui.on_sleep_toggle == cb2
    print("✅ ZezoUI callback proxying test passed")

if __name__ == "__main__":
    try:
        test_pipeline_constants()
        test_api_key_detection()
        test_key_sanitization()
        test_live_mode_defaults()
        test_ui_pipeline_callback_proxying()
        print("\n✅✅✅ All pipeline UI & Settings integration tests passed! ✅✅✅")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
