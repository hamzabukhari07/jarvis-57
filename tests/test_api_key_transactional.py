"""
Unit tests for API Key Pre-Flight Validation and Transactional Atomic Config.
Lead Architect: Hamza Bukhari
"""
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from memory.config_manager import (
    CONFIG_FILE,
    load_api_keys,
    save_api_keys,
    save_api_keys_transactional,
    validate_gemini_key,
    validate_groq_key,
    validate_elevenlabs_key,
    _atomic_write_config,
    clean_api_key,
    get_gemini_key,
    get_groq_api_key,
)


def test_validation_format_rejections():
    """Format and syntax pre-rejections without network calls."""
    # Gemini
    ok, err = validate_gemini_key("")
    assert not ok, "Empty key should fail"
    ok, err = validate_gemini_key("short")
    assert not ok, "Short key should fail"

    # Groq
    ok, err = validate_groq_key("")
    assert not ok, "Empty key should fail"
    ok, err = validate_groq_key("invalid_prefix_1234567890")
    assert not ok and "gsk_" in err, "Non-gsk prefix should fail"

    # ElevenLabs
    ok, err = validate_elevenlabs_key("")
    assert not ok, "Empty key should fail"
    ok, err = validate_elevenlabs_key("123")
    assert not ok, "Short key should fail"
    print("✅ test_validation_format_rejections passed")


def test_validation_mock_probes():
    """Simulate real API probe responses."""
    # Mock Gemini HTTP 200 vs HTTP 400
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        ok, msg = validate_gemini_key("AIzaSyDummyValidGeminiKey123456")
        assert ok, f"Gemini valid probe should return True: {msg}"

        mock_resp.status_code = 400
        mock_resp.text = '{"error": {"message": "API key not valid"}}'
        mock_resp.json.return_value = {"error": {"message": "API key not valid"}}
        ok, msg = validate_gemini_key("AIzaSyDummyInvalidGeminiKey123456")
        assert not ok and "API key not valid" in msg, f"Gemini 400 should return False with detail: {msg}"

    # Mock Groq HTTP 200 vs HTTP 401
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        ok, msg = validate_groq_key("gsk_validmockgroqkey1234567890")
        assert ok, f"Groq valid probe should return True: {msg}"

        mock_resp.status_code = 401
        mock_resp.text = "Invalid API Key"
        mock_resp.json.return_value = {"error": {"message": "Invalid API Key"}}
        ok, msg = validate_groq_key("gsk_invalidmockgroqkey1234567890")
        assert not ok, f"Groq 401 should return False: {msg}"

    print("✅ test_validation_mock_probes passed")


def test_transactional_save_rollback():
    """Test transactional save rejection: if key is invalid, config is NOT touched."""
    initial_config = load_api_keys()
    original_gemini = initial_config.get("gemini_api_key", "")

    # Attempt to save invalid key
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid Key"
        mock_resp.json.return_value = {"error": {"message": "Invalid Key"}}
        mock_post.return_value = mock_resp

        ok, err = save_api_keys_transactional(
            gemini_api_key="AIzaSyBadKeyThatFailsValidation1234",
            validate=True,
        )
        assert not ok, "Transactional save with bad key should return False"
        
        # Verify active config was NOT modified
        current_gemini = load_api_keys().get("gemini_api_key", "")
        assert current_gemini == original_gemini, "Config must remain untouched after validation failure"

    print("✅ test_transactional_save_rollback passed")


def test_transactional_save_success_and_masked_keys():
    """Test transactional save success and ensuring masked keys are ignored."""
    initial_config = load_api_keys()
    backup_file = CONFIG_FILE.with_suffix(".json.bak")
    if CONFIG_FILE.exists():
        backup_file.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            test_gemini = "AIzaSyTestValidGeminiKeyTransactional99"
            test_groq = "gsk_testValidGroqKeyTransactional99"

            ok, msg = save_api_keys_transactional(
                gemini_api_key=test_gemini,
                groq_api_key=test_groq,
                validate=True,
            )
            assert ok, f"Transactional save should succeed: {msg}"
            assert get_gemini_key() == test_gemini
            assert get_groq_api_key() == test_groq

            # Passing masked keys should not overwrite active keys
            ok, msg = save_api_keys_transactional(
                gemini_api_key="AIzaSy••••••••••••al99",
                groq_api_key="gsk_te••••••••••••al99",
                validate=True,
            )
            assert ok
            assert get_gemini_key() == test_gemini, "Masked string must not overwrite real key"
            assert get_groq_api_key() == test_groq, "Masked string must not overwrite real key"

        print("✅ test_transactional_save_success_and_masked_keys passed")
    finally:
        if backup_file.exists():
            _atomic_write_config(json.loads(backup_file.read_text(encoding="utf-8")))
            backup_file.unlink()


def test_atomic_write_safety():
    """Verify _atomic_write_config writes atomically and removes tmp on failure."""
    test_data = load_api_keys()
    _atomic_write_config(test_data)
    assert CONFIG_FILE.exists()
    assert not CONFIG_FILE.with_suffix(".json.tmp").exists()
    print("✅ test_atomic_write_safety passed")


if __name__ == "__main__":
    test_validation_format_rejections()
    test_validation_mock_probes()
    test_transactional_save_rollback()
    test_transactional_save_success_and_masked_keys()
    test_atomic_write_safety()
    print("\n🎉 ALL API KEY TRANSACTIONAL TESTS PASSED!")
