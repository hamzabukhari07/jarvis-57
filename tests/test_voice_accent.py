"""
tests/test_voice_accent.py — Unit & Integration tests for Voice Accent & Dialect feature.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.config_manager import (
    AVAILABLE_VOICE_ACCENTS,
    DEFAULT_VOICE_ACCENT,
    get_voice_accent,
    save_voice_accent,
    load_api_keys,
    _atomic_write_config,
)
from main import _build_accent_directive, ZezoLive


def test_accent_constants():
    assert "auto" in AVAILABLE_VOICE_ACCENTS
    assert "american" in AVAILABLE_VOICE_ACCENTS
    assert "british" in AVAILABLE_VOICE_ACCENTS
    assert "pakistani" in AVAILABLE_VOICE_ACCENTS
    assert "australian" in AVAILABLE_VOICE_ACCENTS
    assert DEFAULT_VOICE_ACCENT == "auto"


def test_save_and_get_voice_accent():
    initial = get_voice_accent()
    try:
        for acc in ["american", "british", "pakistani", "australian", "auto"]:
            save_voice_accent(acc)
            assert get_voice_accent() == acc

        # Test case insensitivity & trimming
        save_voice_accent("  PAKISTANI  ")
        assert get_voice_accent() == "pakistani"

        # Invalid value collapses to default ("auto")
        save_voice_accent("klingon")
        assert get_voice_accent() == "auto"

        # None/empty collapses to default
        save_voice_accent("")
        assert get_voice_accent() == "auto"
    finally:
        save_voice_accent(initial)


def test_voice_accent_self_healing():
    initial = get_voice_accent()
    try:
        # Intentionally corrupt config directly on disk
        data = load_api_keys()
        data["voice_accent"] = "corrupted_accent_xyz"
        _atomic_write_config(data)

        # get_voice_accent should self-heal and reset to DEFAULT_VOICE_ACCENT
        healed = get_voice_accent()
        assert healed == DEFAULT_VOICE_ACCENT

        # Verify disk was actually healed
        fresh_data = load_api_keys()
        assert fresh_data.get("voice_accent") == DEFAULT_VOICE_ACCENT
    finally:
        save_voice_accent(initial)


def test_build_accent_directive():
    us_dir = _build_accent_directive("american")
    assert "[VOICE PROTOCOL: US ACCENT]" in us_dir
    assert "General American (GA)" in us_dir

    uk_dir = _build_accent_directive("british")
    assert "[VOICE PROTOCOL: UK ACCENT]" in uk_dir
    assert "Received Pronunciation (RP)" in uk_dir

    pk_dir = _build_accent_directive("pakistani")
    assert "[VOICE PROTOCOL: PAKISTANI / SOUTH ASIAN ACCENT]" in pk_dir
    assert "dental plosives" in pk_dir
    assert "Urdu and English" in pk_dir

    au_dir = _build_accent_directive("australian")
    assert "[VOICE PROTOCOL: AUSTRALIAN ACCENT]" in au_dir
    assert "Australian English cadence" in au_dir

    auto_dir = _build_accent_directive("auto")
    assert "[VOICE PROTOCOL: ADAPTIVE]" in auto_dir

    unknown_dir = _build_accent_directive("some_unknown")
    assert "[VOICE PROTOCOL: ADAPTIVE]" in unknown_dir


def test_main_on_accent_change_delta_guard():
    # Mock ZezoUI
    mock_ui = MagicMock()
    mock_ui.write_log = MagicMock()

    live = ZezoLive(ui=mock_ui)
    live.request_reconnect = MagicMock()

    # Initial accent
    current = get_voice_accent()
    live._active_voice_accent = current

    # Triggering with the SAME accent should be delta-guarded (no reconnect)
    live._on_accent_change(current)
    assert live.request_reconnect.call_count == 0

    # Triggering with a DIFFERENT accent should trigger reconnect
    different = "british" if current != "british" else "american"
    live._on_accent_change(different)
    assert live.request_reconnect.call_count == 1
    assert live._active_voice_accent == different
    live.request_reconnect.assert_called_with(
        keep_context=False,
        reason=f"voice accent set to {different}"
    )


def test_main_on_language_change_starts_fresh_session():
    mock_ui = MagicMock()
    live = ZezoLive(ui=mock_ui)
    live.request_reconnect = MagicMock()
    live._active_language = "auto"

    live._on_language_change("English Strict")

    live.request_reconnect.assert_called_once_with(
        keep_context=False,
        reason="response language set to English Strict",
    )
    assert live._active_language == "English Strict"


def test_ui_accent_callback_bridge():
    from ui import ZezoUI, MainWindow

    mock_win = MagicMock()
    mock_win._assistant_name = "Zezo"
    mock_win.on_voice_change = None
    mock_win.on_language_change = None
    mock_win.on_assistant_name_change = None
    mock_win.on_accent_change = MagicMock()

    # Call unbound method with mock_win as self
    MainWindow._handle_assistant_settings_changed(
        mock_win, "Zezo", "Charon", "auto", "pakistani"
    )
    mock_win.on_accent_change.assert_called_once_with("pakistani")

    # Test ZezoUI property wrapper
    ui = ZezoUI.__new__(ZezoUI)
    ui._win = mock_win

    ui_called = []
    ui.on_accent_change = lambda acc: ui_called.append(acc)
    assert ui.on_accent_change is not None
    ui.on_accent_change("australian")
    assert ui_called == ["australian"]


def test_ui_server_handlers():
    import asyncio
    import json
    from core.ui_server import ZezoUIServer

    async def _run():
        server = ZezoUIServer.__new__(ZezoUIServer)
        server.on_assistant_settings_changed = MagicMock()
        server.on_accent_change = MagicMock()
        server.broadcast = MagicMock()
        server._collect_audio_state = MagicMock(return_value={})

        # 1. Test _get_config_handler returns voice_accent and available_accents
        mock_req = MagicMock()
        resp = await server._get_config_handler(mock_req)
        assert resp.status == 200
        body = json.loads(resp.text)
        assert "voice_accent" in body
        assert "available_accents" in body
        assert "pakistani" in body["available_accents"]

        # 2. Test _save_assistant_settings_handler with valid accent
        mock_save_req = MagicMock()
        mock_save_req.json = AsyncMock(return_value={
            "assistant_name": "Zezo",
            "voice_name": "Charon",
            "response_language": "auto",
            "voice_accent": "pakistani",
        })
        save_resp = await server._save_assistant_settings_handler(mock_save_req)
        assert save_resp.status == 200
        save_body = json.loads(save_resp.text)
        assert save_body["status"] == "success"
        assert save_body["data"]["voice_accent"] == "pakistani"
        assert get_voice_accent() == "pakistani"
        assert server.broadcast.called

        # 3. Test _save_assistant_settings_handler with invalid accent -> HTTP 400
        mock_bad_req = MagicMock()
        mock_bad_req.json = AsyncMock(return_value={
            "voice_accent": "invalid_accent_123",
        })
        bad_resp = await server._save_assistant_settings_handler(mock_bad_req)
        assert bad_resp.status == 400
        bad_body = json.loads(bad_resp.text)
        assert bad_body["status"] == "error"
        assert "Invalid voice accent" in bad_body["message"]

        # Reset to auto
        save_voice_accent("auto")

    asyncio.run(_run())
