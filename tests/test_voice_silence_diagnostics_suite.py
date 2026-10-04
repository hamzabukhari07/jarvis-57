"""
test_voice_silence_diagnostics_suite.py — Unit test suite verifying voice silence watchdog,
server interruption handling, and proactive audio configuration telemetry.
"""
import asyncio
from unittest.mock import MagicMock, patch
import pytest
from google.genai import types
from main import ZezoLive
from core import log_bus


@pytest.mark.asyncio
async def test_silence_watchdog_arms_and_cancels_on_output():
    mock_ui = MagicMock()
    zezo = ZezoLive(mock_ui)
    zezo._loop = asyncio.get_running_loop()

    # 1. Arm silence watchdog
    zezo._arm_silence_watchdog("Test user prompt")
    assert zezo._silence_watchdog_task is not None
    assert not zezo._silence_watchdog_task.done()

    # 2. Cancel watchdog (simulating model output arriving)
    zezo._cancel_silence_watchdog()
    assert zezo._silence_watchdog_task is None


@pytest.mark.asyncio
async def test_silence_watchdog_fires_on_timeout():
    mock_ui = MagicMock()
    zezo = ZezoLive(mock_ui)
    zezo._loop = asyncio.get_running_loop()

    # Fast-forward asyncio.sleep to test watchdog execution
    with patch("asyncio.sleep", return_value=None):
        with patch.object(log_bus, "emit") as mock_emit:
            await zezo._silence_watchdog("Kese ho Zezo")
            # Verify warning was emitted to log_bus
            mock_emit.assert_called_once()
            args = mock_emit.call_args[0]
            assert args[0] == "WARNING"
            assert args[1] == "audio.silence"
            assert "Kese ho Zezo" in args[2]

            # Verify UI write_log was called
            mock_ui.write_log.assert_called_once()
            assert "Silence Watchdog" in mock_ui.write_log.call_args[0][0]


def test_build_config_telemetry_and_proactivity_flag():
    mock_ui = MagicMock()
    zezo = ZezoLive(mock_ui)
    zezo._enhanced_live = True

    # Test with proactive_audio = False
    with patch("main.get_proactive_audio_enabled", return_value=False):
        cfg_false = zezo._build_config()
        # In types.LiveConnectConfig, proactivity should not be set (or None)
        assert getattr(cfg_false, "proactivity", None) is None

    # Test with proactive_audio = True
    with patch("main.get_proactive_audio_enabled", return_value=True):
        cfg_true = zezo._build_config()
        assert getattr(cfg_true, "proactivity", None) is not None
        assert cfg_true.proactivity.proactive_audio is True
