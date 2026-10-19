"""
Strict verification test suite for actions/browser_control.py.
Validates security hardening, automatic desktop fallbacks, identity desync guards,
profile.last_used selection, and happy-path host verification.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from actions.browser_control import (
    browser_control,
    _safe_url,
    _find_element_info,
    _exec_ab,
    _resolve_desktop_browser_hwnd,
    _act_verify_page,
    _act_go_to,
    _act_search,
    _act_click,
    _act_locate,
    _act_get_title,
    _act_scroll,
    _act_press,
    _act_get_url,
    _act_list_tabs,
    _extract_label_from_snapshot,
    _try_dismiss_banners,
    _resolve_chrome_profile,
)


class TestBrowserControlStrictVerification(unittest.TestCase):

    # ── Section A: Security Tests ─────────────────────────────────────────────

    def test_injection_rejected(self):
        """browser_control({'action':'go_to','url':'https://x.com; calc'}) returns validation error and subprocess.run is called with a list."""
        res = browser_control({"action": "go_to", "url": "https://x.com; calc"})
        self.assertIn("Validation error", res)
        self.assertIn("prohibited characters", res)

        with patch("subprocess.run") as mock_subproc:
            mock_subproc.return_value = MagicMock(returncode=0)
            _exec_ab("open https://example.com")
            self.assertTrue(mock_subproc.called)
            called_args = mock_subproc.call_args[0][0]
            self.assertIsInstance(called_args, list, f"Expected list argument to subprocess.run, got: {type(called_args)}")
            self.assertFalse(mock_subproc.call_args[1].get("shell", False), "shell=True was found in subprocess.run call")

    def test_safe_url_rejections(self):
        """_safe_url rejects forbidden characters and invalid schemes."""
        bad_urls = [
            "https://example.com; calc",
            "https://example.com & calc",
            "https://example.com | calc",
            "https://example.com$foo",
            "https://example.com(bar)",
            "https://example.com<tag>",
            'https://example.com"test',
            "https://example.com'test",
            "https://example.com\ntest",
            "https://example.com\rtest",
            "https://example.com%20test",
            "https://example.com\\test",
            "javascript:alert(1)",
            "file:///etc/passwd",
        ]
        for url in bad_urls:
            is_safe, err = _safe_url(url)
            self.assertFalse(is_safe, f"Expected {url} to be rejected")
            self.assertTrue(len(err) > 0)

        good_urls = [
            "https://google.com",
            "http://localhost:8080",
            "https://open.spotify.com/search",
        ]
        for url in good_urls:
            is_safe, err = _safe_url(url)
            self.assertTrue(is_safe, f"Expected {url} to be allowed, error: {err}")

    # ── Section B: Automatic Desktop Fallbacks (Live Regression Fix) ──────────

    @patch("actions.browser_control._is_browser_session_active", return_value="Session identity mismatch: daemon bound to isolated target")
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control.input_driver")
    def test_go_to_desktop_fallback_on_identity_mismatch(self, mock_driver, mock_focus, mock_active):
        """When identity mismatches (Chrome running without CDP), go_to must fall back to desktop automation, NOT refuse."""
        res = _act_go_to({"url": "https://www.docker.com"})
        self.assertNotIn("Refused", res)
        self.assertIn("Opened https://www.docker.com in Chrome (desktop fallback).", res)
        mock_driver.hotkey.assert_called_with("ctrl", "l")
        mock_driver.type_safe_unicode.assert_called_with("https://www.docker.com")
        mock_driver.press.assert_called_with("enter")

    @patch("actions.browser_control._is_browser_session_active", return_value="Session identity mismatch")
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control.input_driver")
    def test_search_desktop_fallback_on_identity_mismatch(self, mock_driver, mock_focus, mock_active):
        """When identity mismatches, search falls back to desktop Ctrl+L typing."""
        res = _act_search({"query": "docker compose"})
        self.assertNotIn("Refused", res)
        self.assertIn("desktop fallback", res)
        mock_driver.hotkey.assert_called_with("ctrl", "l")
        mock_driver.type_safe_unicode.assert_called_with("docker compose")
        mock_driver.press.assert_called_with("enter")

    # ── Section C: Desync Guards across 9 Unchecked Functions ───────────────────

    @patch("actions.browser_control._verify_session_identity", return_value="Session identity mismatch: isolated daemon")
    @patch("actions.browser_control._click_desktop", return_value=None)
    def test_click_refuses_daemon_leak(self, mock_desktop, mock_ident):
        """_act_click must never leak to daemon _exec_ab('snapshot -i') or daemon click on identity mismatch."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon _exec_ab leaked!")
            res = _act_click({"text": "Sign in"})
            self.assertIn("Refused: Session identity mismatch", res)
            self.assertFalse(mock_exec.called, "_exec_ab was called despite identity mismatch!")

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    def test_extract_label_from_snapshot_refuses_leak(self, mock_ident):
        """_extract_label_from_snapshot returns None without calling daemon on identity mismatch."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            label = _extract_label_from_snapshot("@e14", isolated=False)
            self.assertIsNone(label)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    def test_try_dismiss_banners_refuses_leak(self, mock_ident):
        """_try_dismiss_banners returns False without calling daemon click on identity mismatch."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            dismissed, msg = _try_dismiss_banners('- button "Accept all" [ref=e1]', isolated=False)
            self.assertFalse(dismissed)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    def test_locate_refuses_daemon_leak(self, mock_ident):
        """_act_locate refuses without evaluating on isolated daemon when identity fails."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_locate({"text": "Sign in"})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    @patch("actions.browser_control._resolve_desktop_browser_hwnd", return_value=None)
    def test_get_title_refuses_daemon_leak(self, mock_hwnd, mock_ident):
        """_act_get_title does not evaluate DOM on isolated daemon when identity fails and no desktop window."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_get_title({})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    def test_verify_page_refuses_daemon_leak(self, mock_ident):
        """_act_verify_page does not query daemon on identity mismatch."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_verify_page({"expected_url": "spotify.com"})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    @patch("actions.browser_control.input_driver", None)
    def test_scroll_refuses_daemon_leak_when_no_driver(self, mock_ident):
        """_act_scroll refuses without calling daemon eval/scroll when identity fails."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_scroll({"direction": "down"})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    @patch("actions.browser_control.input_driver", None)
    def test_press_refuses_daemon_leak_when_no_driver(self, mock_ident):
        """_act_press refuses without calling daemon press when identity fails."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_press({"key": "enter"})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    @patch("actions.browser_control._verify_session_identity", return_value="Identity mismatch")
    @patch("actions.browser_control.input_driver", None)
    def test_get_url_refuses_daemon_leak_when_no_driver(self, mock_ident):
        """_act_get_url refuses without calling daemon get url fallback when identity fails."""
        with patch("actions.browser_control._exec_ab") as mock_exec:
            mock_exec.side_effect = RuntimeError("Daemon leaked!")
            res = _act_get_url({})
            self.assertIn("Refused: Identity mismatch", res)
            self.assertFalse(mock_exec.called)

    # ── Section D: Happy-Path False Success Prevention ────────────────────────

    @patch("actions.browser_control._is_browser_session_active", return_value=True)
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control._ensure_maximized")
    @patch("actions.browser_control._exec_ab")
    def test_go_to_happy_path_detects_url_mismatch(self, mock_exec, mock_max, mock_focus, mock_active):
        """_act_go_to must return a failure if code==0 but get url returns old URL."""
        mock_exec.side_effect = [
            (0, "ok"),                                     # open returns 0
            (0, "https://en.wikipedia.org/wiki/Main_Page"), # get url returns old URL!
        ]
        res = _act_go_to({"url": "https://open.spotify.com"})
        self.assertIn("Failed to open https://open.spotify.com", res)
        self.assertIn("does not match expected host 'open.spotify.com'", res)

    # ── Section E: Profile Selection from Local State ─────────────────────────

    def test_resolve_chrome_profile_reads_local_state(self):
        """_resolve_chrome_profile reads profile.last_used from Local State."""
        profile = _resolve_chrome_profile()
        self.assertIsInstance(profile, str)
        self.assertTrue(len(profile) > 0)
        # On Hamza's machine, Local State has "Profile 7"
        self.assertEqual(profile, "Profile 7")

    # ── Section F: List Tabs Hygiene ──────────────────────────────────────────

    @patch("actions.browser_control._is_isolated", return_value=False)
    @patch("actions.browser_control._resolve_desktop_browser_hwnd", return_value=None)
    @patch("actions.browser_control._is_browser_session_active", return_value=False)
    def test_list_tabs_unable_message(self, mock_active, mock_hwnd, mock_iso):
        """When neither UIA nor daemon returns tabs, return 'Unable to list open tabs.'"""
        res = _act_list_tabs({})
        self.assertEqual(res, "Unable to list open tabs.")

    # ── Section G: Live Desktop Fallback Verification ─────────────────────────

    def test_go_to_desktop_fallback_live(self):
        """
        Live verification of desktop fallback navigation against real Chrome window.
        Uses _resolve_desktop_browser_hwnd and input_driver to execute address bar navigation.
        """
        hwnd = _resolve_desktop_browser_hwnd()
        if not hwnd:
            self.skipTest("No real Chrome desktop window running on input desktop.")

        # Test go_to with desktop fallback against real Chrome
        res = browser_control({"action": "go_to", "url": "https://www.docker.com"})
        self.assertTrue(res.startswith("Opened"), f"Expected result to start with 'Opened', got: {res}")
        self.assertIn("docker.com", res)


if __name__ == "__main__":
    unittest.main()
