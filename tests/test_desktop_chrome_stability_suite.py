"""
tests/test_desktop_chrome_stability_suite.py — Regression suite for the desktop
Chrome stability fixes:

  1. Window focus must NOT un-maximize a maximized window (no more shrinking).
  2. list_tabs must enumerate the REAL desktop tabs via UIA (not the daemon).
  3. scroll must release omnibox/search focus (Escape) before PageDown.
  4. click must resolve URL/nav targets on the desktop before the daemon.

Lead Architect: Hamza Bukhari
Project: ZEZO (Autonomous Desktop AI Operating System v2)
"""

from unittest.mock import MagicMock

import os

import actions.browser_control as bc
from core.computer.windows_native import (
    windows_native,
    SW_RESTORE,
    SW_MAXIMIZE,
    SW_SHOW,
)


class _FakeInputDriver:
    """Records press/hotkey calls so ordering can be asserted."""

    def __init__(self):
        self.calls = []

    def press(self, key):
        self.calls.append(("press", str(key).lower()))
        return f"Pressed: {key}"

    def hotkey(self, *keys):
        self.calls.append(("hotkey", tuple(str(k).lower() for k in keys)))
        return f"Hotkey: {keys}"

    def type_safe_unicode(self, text, *a, **k):
        self.calls.append(("type", text))
        return f"Typed: {text}"


# ── 1. Window State Preserver ────────────────────────────────────────────────

class TestWindowStatePreserver:
    def _driver(self, monkeypatch, iconic, zoomed):
        m = MagicMock()
        m.IsIconic.return_value = bool(iconic)
        m.IsZoomed.return_value = bool(zoomed)
        monkeypatch.setattr(windows_native, "user32", m)
        monkeypatch.setattr(windows_native, "is_windows", True)
        return m

    def test_maximized_window_stays_maximized(self, monkeypatch):
        m = self._driver(monkeypatch, iconic=False, zoomed=True)
        assert windows_native.show_window_preserving_state(1234) is True
        m.ShowWindow.assert_called_once_with(1234, SW_MAXIMIZE)

    def test_minimized_window_is_restored(self, monkeypatch):
        m = self._driver(monkeypatch, iconic=True, zoomed=False)
        assert windows_native.show_window_preserving_state(1234) is True
        m.ShowWindow.assert_called_once_with(1234, SW_RESTORE)

    def test_normal_window_is_shown(self, monkeypatch):
        m = self._driver(monkeypatch, iconic=False, zoomed=False)
        assert windows_native.show_window_preserving_state(1234) is True
        m.ShowWindow.assert_called_once_with(1234, SW_SHOW)

    def test_focus_window_uses_preserver(self, monkeypatch):
        """focus_window must route through the state-preserving helper, not SW_RESTORE."""
        calls = []
        monkeypatch.setattr(
            windows_native, "show_window_preserving_state",
            lambda hwnd: calls.append(hwnd) or True,
        )
        # Patch out the actual window matching so we exercise the ShowWindow path.
        monkeypatch.setattr(windows_native, "is_windows", True)
        monkeypatch.setattr(windows_native, "user32", MagicMock())
        monkeypatch.setattr(windows_native, "kernel32", MagicMock())

        def _fake_enum(_cb, _lparam):
            _cb(4242, 0)

        windows_native.user32.EnumWindows.side_effect = _fake_enum
        windows_native.is_real_top_level_window = lambda hwnd: True
        windows_native.is_self_or_console_window = lambda hwnd=None: False
        windows_native.get_window_title = lambda hwnd: "Notepad"
        windows_native.user32.GetForegroundWindow.return_value = 4242
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        res = windows_native.focus_window("notepad")
        assert calls == [4242], f"preserver not used, calls={calls}"
        assert res.startswith("Focused window:")


# ── 2. Real desktop tab discovery ────────────────────────────────────────────

class TestRealTabDiscovery:
    def test_list_tabs_reads_real_desktop_tabs(self, monkeypatch):
        monkeypatch.setattr(bc, "_resolve_desktop_browser_hwnd", lambda: 111)
        monkeypatch.setattr(bc, "_uia_browser_tabs", lambda hwnd: [
            {"title": "Excalidraw", "index": 1, "selected": False},
            {"title": "Docker", "index": 2, "selected": True},
            {"title": "NotebookLM", "index": 3, "selected": False},
        ])
        monkeypatch.setattr(bc, "_exec_ab", lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("daemon must not be queried in desktop mode")))

        out = bc._act_list_tabs({})
        assert "3 tabs" in out
        assert "Docker" in out and "NotebookLM" in out and "Excalidraw" in out
        assert "tab 2 is active" in out

    def test_list_tabs_falls_back_to_daemon(self, monkeypatch):
        monkeypatch.setattr(bc, "_resolve_desktop_browser_hwnd", lambda: 0)
        monkeypatch.setattr(bc, "_uia_browser_tabs", lambda hwnd: [])
        monkeypatch.setattr(bc, "windows_native", None)
        monkeypatch.setattr(bc, "_is_browser_session_active", lambda: True)
        monkeypatch.setattr(bc, "_exec_ab", lambda *a, **k: (0, "\u2192 [t1] Example Page\n[t2] Other Page\n"))

        out = bc._act_list_tabs({})
        assert "Example Page" in out and "Other Page" in out

    def test_format_tab_list_marks_active(self):
        out = bc._format_real_tab_list([
            {"title": "A", "index": 1, "selected": True},
            {"title": "B", "index": 2, "selected": False},
        ])
        assert "(active)" in out
        assert "tab 1 is active" in out


# ── 3. Scroll focus-trap unblocker ───────────────────────────────────────────

class TestScrollUnblock:
    def test_defocus_and_pagedown(self, monkeypatch):
        driver = _FakeInputDriver()
        monkeypatch.setattr(bc, "input_driver", driver)
        monkeypatch.setattr(bc, "_focus_desktop_browser", lambda: True)
        monkeypatch.setattr(bc, "_wheel_scroll", lambda *a, **k: False)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        out = bc._act_scroll({"direction": "down", "desktop_only": True})
        assert "down" in out.lower()
        # Ensure legacy escape key is removed per item 13 and replaced with DOM eval defocus
        assert ("press", "escape") not in driver.calls
        assert ("press", "pagedown") in driver.calls

    def test_scroll_top_uses_home(self, monkeypatch):
        driver = _FakeInputDriver()
        monkeypatch.setattr(bc, "input_driver", driver)
        monkeypatch.setattr(bc, "_focus_desktop_browser", lambda: True)
        monkeypatch.setattr(bc, "_wheel_scroll", lambda *a, **k: False)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        bc._act_scroll({"direction": "top", "desktop_only": True})
        assert ("press", "home") in driver.calls


# ── 4. Desktop-first tab switching & click ───────────────────────────────────

class TestDesktopNavigation:
    def test_switch_tab_by_name_uses_uia(self, monkeypatch):
        monkeypatch.setattr(bc, "_focus_desktop_browser", lambda: True)
        monkeypatch.setattr(bc, "_resolve_desktop_browser_hwnd", lambda: 111)
        monkeypatch.setattr(bc, "_uia_switch_tab", lambda hwnd, q: q.lower() == "notebooklm")
        monkeypatch.setattr(bc, "input_driver", _FakeInputDriver())
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        out = bc._act_tab_nav({"target": "NotebookLM", "desktop_only": True}, "switch")
        assert "NotebookLM" in out

    def test_switch_unknown_tab_falls_back_to_next(self, monkeypatch):
        driver = _FakeInputDriver()
        monkeypatch.setattr(bc, "_focus_desktop_browser", lambda: True)
        monkeypatch.setattr(bc, "_resolve_desktop_browser_hwnd", lambda: 111)
        monkeypatch.setattr(bc, "_uia_switch_tab", lambda hwnd, q: False)
        monkeypatch.setattr(bc, "input_driver", driver)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        out = bc._act_tab_nav({"target": "Nope", "desktop_only": True}, "switch")
        assert "No tab matched" in out
        assert ("hotkey", ("ctrl", "tab")) not in driver.calls

    def test_click_url_uses_address_bar(self, monkeypatch):
        driver = _FakeInputDriver()
        monkeypatch.setattr(bc, "input_driver", driver)
        monkeypatch.setattr(bc, "_focus_desktop_browser", lambda: True)
        monkeypatch.setattr(bc, "_is_browser_session_active", lambda: False)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        out = bc._click_desktop({"text": "docker.com/pricing"}, "docker.com/pricing")
        assert out is not None and "address bar" in out
        assert ("hotkey", ("ctrl", "l")) in driver.calls

    def test_click_ref_defers_to_daemon(self, monkeypatch):
        monkeypatch.setattr(bc, "input_driver", _FakeInputDriver())
        assert bc._click_desktop({"selector": "@e1"}, "@e1") is None
        assert bc._click_desktop({"ref": "e2"}, "e2") is None

    def test_looks_like_url(self):
        assert bc._looks_like_url("docker.com/pricing")
        assert bc._looks_like_url("https://example.com")
        assert bc._looks_like_url("www.github.com")
        assert not bc._looks_like_url("Pricing")
        assert not bc._looks_like_url("Sign In")


# ── 5. Focus target selection (Step 3: profile lookup caching / direct HWND) ──

class TestFocusTargetSelection:
    """
    "chrome" must keep focusing the SAME HWND as before (profile preference wins),
    while a caller-supplied HWND short-circuits enumeration + profile_lookup.
    """

    _TITLES = {111: "First Window - Google Chrome", 222: "Preferred Profile - Google Chrome"}
    _PIDS = {111: 111, 222: 222}

    def _patch_driver(self, monkeypatch):
        u = MagicMock()
        u.GetForegroundWindow.return_value = 222

        def _enum(_cb, _lparam):
            _cb(111, 0)
            _cb(222, 0)

        def _gwpid(hwnd, out):
            if out is not None:
                out._obj.value = self._PIDS[hwnd]
            return self._PIDS[hwnd]

        u.EnumWindows.side_effect = _enum
        u.GetWindowThreadProcessId.side_effect = _gwpid

        monkeypatch.setattr(windows_native, "is_windows", True)
        monkeypatch.setattr(windows_native, "user32", u)
        monkeypatch.setattr(windows_native, "kernel32", MagicMock())
        monkeypatch.setattr(windows_native, "is_real_top_level_window", lambda hwnd: True)
        monkeypatch.setattr(windows_native, "is_self_or_console_window", lambda hwnd=None: False)
        monkeypatch.setattr(windows_native, "get_window_title", lambda hwnd: self._TITLES.get(hwnd, ""))
        focused = []
        monkeypatch.setattr(
            windows_native, "show_window_preserving_state",
            lambda hwnd: focused.append(hwnd) or True,
        )
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        return u, focused

    def test_chrome_still_focuses_the_profile_preferred_hwnd(self, monkeypatch):
        """Same HWND as before Step 3: the profile-preferred window, not the first one."""
        _u, focused = self._patch_driver(monkeypatch)
        monkeypatch.setattr(windows_native, "_profile_pids_for", lambda app: [222])
        res = windows_native.focus_window("chrome")
        assert res == "Focused window: Preferred Profile - Google Chrome", res
        assert focused == [222], focused

    def test_supplied_hwnd_skips_enum_and_profile_lookup(self, monkeypatch):
        u, focused = self._patch_driver(monkeypatch)
        scanned = []
        monkeypatch.setattr(windows_native, "_profile_pids_for", lambda app: scanned.append(app) or [])
        res = windows_native.focus_window("browser", hwnd=222)
        assert res == "Focused window: Preferred Profile - Google Chrome", res
        assert focused == [222], focused
        assert scanned == [], scanned
        u.EnumWindows.assert_not_called()

    def test_profile_pids_are_cached_per_app_name(self, monkeypatch):
        import importlib
        mod = importlib.import_module("core.computer.windows_native")
        monkeypatch.setattr(mod, "_PROFILE_PIDS_CACHE", {})
        scans = []
        monkeypatch.setattr(windows_native, "_scan_profile_pids", lambda app: scans.append(app) or [os.getpid()])
        assert windows_native._profile_pids_for("zezo-cache-test") == [os.getpid()]
        assert windows_native._profile_pids_for("zezo-cache-test") == [os.getpid()]
        assert scans == ["zezo-cache-test"], scans

