import unittest
from unittest.mock import patch, MagicMock
from actions.browser_control import (
    _find_ref_by_text,
    _act_click,
    _act_snapshot,
    _act_go_to,
    browser_control as handler,
    TOOL,
)


class TestBrowserControlEnhancements(unittest.TestCase):
    def test_find_ref_by_text(self):
        sample_snapshot = """
- root [ref=e1]
  - navigation [ref=e2]
    - link "Home" [ref=e3]
    - link "Search" [ref=e4]
  - main [ref=e5]
    - button "Log in" [ref=e12]
    - button "Sign up" [ref=e15]
"""
        ref = _find_ref_by_text(sample_snapshot, "Log in")
        self.assertEqual(ref, "@e12")

        ref_case = _find_ref_by_text(sample_snapshot, "log in")
        self.assertEqual(ref_case, "@e12")

        ref_signup = _find_ref_by_text(sample_snapshot, "Sign up")
        self.assertEqual(ref_signup, "@e15")

        self.assertIsNone(_find_ref_by_text(sample_snapshot, "Nonexistent"))

    @patch("actions.browser_control._verify_session_identity", return_value=None)
    @patch("actions.browser_control._use_desktop_path", return_value=False)
    @patch("actions.browser_control._exec_ab")
    def test_snapshot_settle_wait_and_retry(self, mock_exec, mock_desktop_path, mock_ident):
        # First call wait --load, then first snapshot returns (no interactive elements), retry returns elements
        mock_exec.side_effect = [
            (0, "(no interactive elements)"),
            (0, '- button "Log in" [ref=e1]'),
        ]
        res = _act_snapshot({"interactive": True})
        self.assertIn("Log in", res)
        self.assertEqual(mock_exec.call_count, 2)

    @patch("actions.browser_control._verify_session_identity", return_value=None)
    @patch("actions.browser_control._click_desktop")
    @patch("actions.browser_control._use_desktop_path", return_value=False)
    @patch("actions.browser_control._is_cdp_available", return_value=False)
    @patch("actions.browser_control._exec_ab")
    def test_act_click_with_text_resolves_snapshot_ref(self, mock_exec, mock_cdp, mock_desktop_path, mock_desktop, mock_ident):
        mock_desktop.return_value = None
        # Phase F: title-before, snapshot, click, then title-after (the post-click check).
        mock_exec.side_effect = [
            (0, '""'),
            (0, '- button "Log in" [ref=e42]'),
            (0, "Success"),
            (0, '"Home Page"'),
        ]
        res = _act_click({"text": "Log in"})
        self.assertEqual(res, "Clicked 'Log in'. Page is now 'Home Page'.")
        mock_exec.assert_any_call("click @e42")

    @patch("actions.browser_control._cdp_session_up", return_value=True)
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control.input_driver")
    @patch("actions.browser_control._exec_ab")
    @patch("actions.browser_control._exec_ab_argv")
    def test_act_go_to_syncs_daemon(self, mock_argv, mock_exec, mock_driver, mock_focus, mock_cdp):
        # Step 2: the daemon is only driven while a CDP session is attached.
        # Phase A: `open` is dispatched as a real argv list so cmd.exe cannot re-parse it.
        mock_argv.return_value = (0, "ok")
        mock_exec.return_value = (0, "https://open.spotify.com/")
        res = _act_go_to({"url": "https://open.spotify.com"})
        self.assertIn("Opened https://open.spotify.com", res)
        mock_argv.assert_any_call(["open", "https://open.spotify.com"])

    @patch("actions.browser_control._cdp_session_up", return_value=True)
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control.input_driver")
    @patch("actions.browser_control._exec_ab")
    @patch("actions.browser_control._exec_ab_argv")
    def test_go_to_carries_query_url_as_one_argv_item(
        self, mock_argv, mock_exec, mock_driver, mock_focus, mock_cdp
    ):
        """Phase B: the whole URL, query punctuation included, is ONE untouched argv item."""
        url = "https://example.com/?a=1&b=2%203&t=30s"
        mock_argv.return_value = (0, "ok")
        mock_exec.return_value = (0, url)
        res = _act_go_to({"url": url})
        self.assertIn(f"Opened {url}", res)
        mock_argv.assert_any_call(["open", url])

    def test_safe_url_allows_query_punctuation_but_rejects_bad_hosts(self):
        """Phase B: query/fragment punctuation is legal; hosts and schemes stay strict."""
        from actions.browser_control import _normalize_url, _safe_url

        for good in (
            "https://example.com/?a=1&b=2%203&t=30s",
            "https://en.wikipedia.org/wiki/Chrome#History",
            "https://www.google.com/search?q=tom+%26+jerry;code=1",
        ):
            ok, err = _safe_url(good)
            self.assertTrue(ok, f"{good} should be allowed ({err})")

        for bad in (
            "javascript:alert(1)",
            "file:///c:/windows/win.ini",
            "https://evil.com&calc.exe",
            "https://x.com/a`b",
            "https://x.com/a b",
            "https://x.com/\nrm -rf",
            "https://x.com/?q=a|b",
        ):
            ok, err = _safe_url(_normalize_url(bad))
            self.assertFalse(ok, f"{bad} should be rejected")

    @patch.dict("actions.browser_control._ACTION_DISPATCH", {"click": MagicMock(return_value="Clicked element @e5.")})
    def test_handler_dispatch(self):
        res = handler({"action": "click", "selector": "@e5"})
        self.assertEqual(res, "Clicked element @e5.")

    def test_extract_label_from_snapshot(self):
        from actions import browser_control
        browser_control._last_snapshot_text = """
- generic "Spotify" [ref=e1]
  - button "Sign up" [ref=e13]
  - button "Log in" [ref=e14]
"""
        label_login = browser_control._extract_label_from_snapshot("@e14")
        self.assertEqual(label_login, "Log in")

        label_signup = browser_control._extract_label_from_snapshot("e13")
        self.assertEqual(label_signup, "Sign up")

    @patch("actions.browser_control._is_browser_session_active", return_value=False)
    @patch("actions.browser_control._is_cdp_available", return_value=False)
    @patch("actions.browser_control._focus_desktop_browser", return_value=True)
    @patch("actions.browser_control._resolve_desktop_browser_hwnd", return_value=12345)
    @patch("actions.browser_control.input_driver")
    @patch("actions.computer_control._find_target_element_escalated", return_value=(500, 300, "l1.5_ocr"))
    def test_click_desktop_with_ref_uses_ocr(self, mock_find, mock_driver, mock_hwnd, mock_focus, mock_cdp, mock_active):
        from actions import browser_control
        browser_control._last_snapshot_text = '- button "Log in" [ref=e14]'
        res = browser_control._click_desktop({}, "@e14")
        self.assertIsNotNone(res)
        self.assertIn("Clicked 'Log in' at (500, 300) via l1.5_ocr on desktop Chrome.", res)
        mock_driver.click.assert_called_with(500, 300)


class TestPhaseH_Hygiene(unittest.TestCase):
    """Phase H: unit coverage for the verification primitives shipped in phases B/E."""

    def test_url_confirms_six_cases(self):
        from actions.browser_control import _url_confirms

        target = "https://example.com/?n=2&k=v"
        cases = [
            # (observed, expected, want, label)
            (target, target, True, "identical host+path+query"),
            ("https://example.com/?n=1", target, False, "query rewrite (?n=1 vs ?n=2)"),
            ("https://example.com/?n=2&k=v&utm=x", target, True, "site appends extra params"),
            ("https://example.com/other?n=2&k=v", target, False, "different path"),
            ("https://elsewhere.example/?n=2&k=v", target, False, "different host"),
            # Chrome's omnibox elides a leading www. / the scheme (Phase E UIA read)
            ("https://example.com/?n=2&k=v", "https://www.example.com/?n=2&k=v", True, "www elision"),
            ("https://example.com/?n=2", "https://example.com/", True, "no expected query"),
        ]
        self.assertEqual(len(cases), 7)
        for observed, expected, want, label in cases:
            self.assertIs(_url_confirms(observed, expected), want, label)

    def test_safe_url_allow_reject_lists(self):
        from actions.browser_control import _normalize_url, _safe_url

        allow = [
            "https://example.com/?a=1&b=2%203&t=30s",
            "https://en.wikipedia.org/wiki/Chrome#History",
            "https://www.google.com/search?q=tom+%26+jerry;code=1",
            "https://example.com:8443/path?x=1",
            "https://x.com/a'b",
        ]
        reject = [
            "javascript:alert(1)",
            "file:///c:/windows/win.ini",
            "ftp://example.com/f",
            "https://evil.com&calc.exe",
            "https://x.com/a`b",
            "https://x.com/a b",
            "https://x.com/\nrm -rf",
            "https://x.com/?q=a|b",
            "https://about:blank.com",
        ]
        for good in allow:
            ok, err = _safe_url(good)
            self.assertTrue(ok, f"{good} should be allowed ({err})")
        for bad in reject:
            ok, err = _safe_url(_normalize_url(bad))
            self.assertFalse(ok, f"{bad} should be rejected")

    @patch("actions.browser_control._resolve_ab_cmd", return_value=r"C:\fake\agent-browser.exe")
    @patch("actions.browser_control._is_cdp_available", return_value=False)
    @patch("actions.browser_control._run_ab_process", return_value=(0, "ok"))
    def test_exec_ab_argv_passes_url_as_one_argv_item(self, mock_run, mock_cdp, mock_bin):
        from actions import browser_control as bc

        url = "https://example.com/?a=1&b=2%203&t=30s&q='x'"
        bc._req_ctx.isolated = True  # bypass the NO_CDP guard for this argv-shape test
        try:
            code, out = bc._exec_ab_argv(["open", url])
        finally:
            bc._req_ctx.isolated = False
        self.assertEqual((code, out), (0, "ok"))
        argv = mock_run.call_args[0][0]
        self.assertEqual(argv, [r"C:\fake\agent-browser.exe", "open", url])
        self.assertIn(url, argv)  # never split on & ? % ' or = by a shell

    def test_dedup_ignores_failed_results(self):
        from actions import browser_control as bc

        bc._recent.clear()
        with patch.dict("actions.browser_control._ACTION_DISPATCH",
                        {"click": MagicMock(return_value="Failed to click 'boom'")}):
            first = bc.browser_control({"action": "click", "selector": "@e9"})
            second = bc.browser_control({"action": "click", "selector": "@e9"})
        self.assertEqual(first, "Failed to click 'boom'")
        self.assertNotIn("already done", second)
        self.assertEqual(bc._recent, {})

        bc._recent.clear()
        with patch.dict("actions.browser_control._ACTION_DISPATCH",
                        {"click": MagicMock(return_value="Clicked element @e5.")}):
            bc.browser_control({"action": "click", "selector": "@e5"})
            again = bc.browser_control({"action": "click", "selector": "@e5"})


if __name__ == "__main__":
    unittest.main()
