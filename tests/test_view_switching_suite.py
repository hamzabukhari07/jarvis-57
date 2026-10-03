"""
tests/test_view_switching_suite.py — View Switching & Window Close Protection Unit Tests.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from unittest.mock import patch, MagicMock
from actions.open_app import open_app
from actions.computer_control import _safe_close_window


class TestViewSwitchingSuite:
    def test_open_office_view(self):
        with patch("core.ui_server.get_ui_server") as mock_server:
            mock_inst = MagicMock()
            mock_server.return_value = mock_inst

            res = open_app({"app_name": "office_view", "action": "open"})
            assert "Scranton Agent Office Floor screen" in res
            mock_inst.broadcast.assert_called_with("switch_view", {"view": "office"})

    def test_close_office_view_returns_to_dashboard(self):
        with patch("core.ui_server.get_ui_server") as mock_server:
            mock_inst = MagicMock()
            mock_server.return_value = mock_inst

            res = open_app({"app_name": "office_view", "action": "close"})
            assert "Closed office view and returned to Tactical Dashboard" in res
            mock_inst.broadcast.assert_called_with("switch_view", {"view": "home"})

    def test_switch_to_dashboard(self):
        with patch("core.ui_server.get_ui_server") as mock_server:
            mock_inst = MagicMock()
            mock_server.return_value = mock_inst

            res = open_app({"app_name": "dashboard", "action": "open"})
            assert "Tactical Dashboard screen" in res
            mock_inst.broadcast.assert_called_with("switch_view", {"view": "home"})

    def test_safe_close_window_protects_zezo_main(self):
        res = _safe_close_window("ZEZO")
        assert "Cannot close ZEZO main OS window" in res

        res_jarvis = _safe_close_window("jarvis")
        assert "Cannot close ZEZO main OS window" in res_jarvis

    def test_safe_close_window_empty_input(self):
        res = _safe_close_window("")
        assert "No window title provided" in res
