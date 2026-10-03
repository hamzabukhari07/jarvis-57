"""
tests/test_uia_desktop_control_suite.py — Unit tests for Phase 1 Windows UIA & Multi-tier Desktop Control.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

import pytest
from unittest.mock import patch, MagicMock
from actions.computer_control import (
    computer_control,
    _handle_mock_data,
    _handle_type,
    _handle_click,
    _DESKTOP_INPUT_LOCK,
)
from core.computer.windows_uia import windows_uia


class TestUIADesktopControlSuite:
    def test_random_data_generation_only(self):
        res = computer_control({"action": "random_data", "type": "name"})
        assert isinstance(res, str)
        assert len(res) > 0

    def test_random_data_with_explicit_typing(self):
        with patch("actions.computer_control.input_driver.type_safe_unicode") as mock_type, \
             patch("actions.computer_control._validate_and_ensure_focus") as mock_focus:
            mock_focus.return_value = (True, 1234, "Untitled - Notepad")
            mock_type.return_value = "Typed (Clipboard-Safe): test_user"

            res = computer_control({
                "action": "random_data",
                "type": "username",
                "type_into_window": True,
            })
            assert "Typed (Clipboard-Safe)" in res
            mock_type.assert_called_once()

    def test_type_action_with_target_window_validation(self):
        with patch("actions.computer_control.input_driver.type_safe_unicode") as mock_type, \
             patch("actions.computer_control._validate_and_ensure_focus") as mock_focus:
            mock_focus.return_value = (True, 5678, "Untitled - Notepad")
            mock_type.return_value = "Typed: Hello World"

            res = computer_control({
                "action": "type",
                "text": "Hello World",
                "title": "Notepad",
            })
            assert "Typed: Hello World" in res
            mock_focus.assert_called_with("Notepad")

    def test_type_action_aborts_if_target_window_cannot_focus(self):
        with patch("actions.computer_control._validate_and_ensure_focus") as mock_focus:
            mock_focus.return_value = (False, 0, "")

            res = computer_control({
                "action": "type",
                "text": "Hello World",
                "title": "NonExistentApp12345",
            })
            assert "Cannot type" in res
            assert "could not be focused" in res

    def test_direct_uia_text_setting(self):
        with patch.object(windows_uia, "set_focused_text", return_value=True), \
             patch("actions.computer_control._validate_and_ensure_focus") as mock_focus:
            mock_focus.return_value = (True, 1234, "Untitled - Notepad")

            res = computer_control({
                "action": "set_text",
                "text": "Direct UIA Text",
            })
            assert "Typed (UIA Direct)" in res

    def test_direct_uia_invoke_click(self):
        with patch.object(windows_uia, "invoke_element", return_value=True), \
             patch("actions.computer_control._get_active_foreground_hwnd", return_value=1234):
            res = computer_control({
                "action": "click",
                "description": "Plus",
            })
            assert "Invoked (UIA Direct)" in res

    def test_read_window_text_uia(self):
        with patch.object(windows_uia, "read_window_text", return_value="Result: 150"), \
             patch("actions.computer_control._get_active_foreground_hwnd", return_value=1234):
            res = computer_control({"action": "read_window_text"})
            assert res == "Result: 150"
