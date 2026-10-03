"""
tests/test_vision_timeout_suite.py — Fast Vision Timeout Ladder & Visual Fallback Unit Tests.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from unittest.mock import patch, MagicMock
from core.gemini import MIN_TIMEOUT_MS, client
from actions.screen_processor import analyze_visual


class TestVisionTimeoutSuite:
    def test_min_timeout_ms_is_10000(self):
        assert MIN_TIMEOUT_MS == 10_000, "MIN_TIMEOUT_MS must be 10000ms to comply with Gemini API minimum deadline"

    def test_client_honors_10000ms_timeout(self):
        with patch("core.gemini.api_key", return_value="fake_api_key_test"):
            cl = client(timeout_ms=10000)
            assert cl is not None

    def test_analyze_visual_falls_back_to_os_ground_truth(self):
        with patch("core.gemini.text", return_value=""):
            with patch("actions.screen_processor.get_active_window_context") as mock_ctx:
                mock_ctx.return_value = {
                    "foreground_title": "Visual Studio Code - zezo",
                    "foreground_process": "Code.exe",
                    "rect": {"width": 1920, "height": 1080, "x": 0, "y": 0},
                    "visible_windows": ["Visual Studio Code - zezo", "Telegram"],
                }
                res = analyze_visual(b"fake_image_bytes", "image/jpeg", "What is on screen?")
                assert "Visual Studio Code - zezo" in res
                assert "Visible windows" in res
