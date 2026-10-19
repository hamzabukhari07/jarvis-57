"""
Browser Automation Action for ZEZO OS
Powered by agent-browser (100% native Rust CDP client-daemon by Vercel Labs).

Replaces legacy Playwright with:
- Sub-50ms execution speed via persistent Rust daemon
- Ref-based accessibility tree (@e1, @e2) saving ~90% tokens
- Headless execution on isolated private Windows desktop (zero profile lock conflicts)
- Headed execution on user desktop when visual presence is requested
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

_OS = platform.system()

# Debug/profiling output is opt-in. With ZEZO_PROFILE unset nothing prints.
ZEZO_PROFILE = os.environ.get("ZEZO_PROFILE") == "1"


def _prof(stage: str, t0: float) -> None:
    """Emit one [prof] line for a go_to/desktop stage (opt-in via ZEZO_PROFILE)."""
    if ZEZO_PROFILE:
        print(f"[prof] go_to :: {stage:36s} {(time.perf_counter() - t0) * 1000:8.2f}ms")

# Search engine query templates
_SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "yandex": "https://yandex.com/search/?text=",
}

# Mutating action deduplication & serialization
_BROWSER_LOCK = threading.RLock()
_recent: Dict[str, Tuple[float, str]] = {}
_ACTION_TTL: Dict[str, float] = {
    "go_to": 2.0,
    "open": 2.0,
    "search": 2.0,
    "new_tab": 2.0,
    "close_tab": 2.0,
    "scroll": 1.5,
    "click": 1.5,
    "switch_tab": 1.5,
    "press": 1.0,
    "next_tab": 1.0,
    "prev_tab": 1.0,
}

try:
    from core.computer import input_driver, windows_native
except Exception:
    input_driver = None
    windows_native = None


def _attach_input_desktop() -> None:
    """Ensure current thread is attached to the interactive input desktop on Windows."""
    if _OS == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


_cached_hwnd: Dict[str, Any] = {"t": 0.0, "hwnd": None}


def _focus_desktop_browser() -> bool:
    """Ensure user's desktop browser is in the foreground. Skips if already foreground."""
    _attach_input_desktop()
    try:
        if windows_native and windows_native.user32:
            hwnd = _resolve_desktop_browser_hwnd()
            if hwnd:
                fg = windows_native.user32.GetForegroundWindow()
                if fg == hwnd:
                    return True
            # Step 3a: hand the already-resolved HWND over so windows_native focuses it
            # directly instead of re-enumerating windows and re-scanning Chrome profiles.
            if windows_native.focus_browser_or_app_window(hwnd):
                return True
            if hwnd:
                return bool(windows_native.show_window_preserving_state(hwnd))
    except Exception:
        pass
    return False


def _restore_clipboard(text: str) -> None:
    """Write text back to the clipboard WITHOUT pasting it into the focused window."""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass


# Step 3: navigation polling replaces the fixed post-Enter settle. Cadence and bounds
# come from the Step 2 profile: the fixed 500ms settle was the single largest removable
# cost, and the omnibox read (3 keystrokes + 2 sleeps) is only needed when the cheap
# window-title signal cannot confirm the navigation.
_NAV_POLL_INTERVAL = 0.04     # 30-50ms poll cadence
_NAV_TIMEOUT = 1.5            # hard ceiling for the whole verification
_NAV_FIRST_READ = 0.35        # let the title catch up before touching the omnibox
_NAV_READ_GAP = 0.35          # minimum gap between the (at most 2) omnibox reads
_NAV_MAX_READS = 2

# Phase C: after ctrl+v the target consumes the paste buffer asynchronously, so the
# user's clipboard is restored only after this small settle (type_safe_unicode used
# 100ms for the same reason). Measured cost included in the method figures below.
_PASTE_SETTLE = 0.05


def _browser_is_foreground(hwnd: Optional[int]) -> bool:
    """True when `hwnd` is the current foreground window (neutral when unknown)."""
    try:
        if not hwnd or not windows_native or not windows_native.user32:
            return True
        return windows_native.user32.GetForegroundWindow() == hwnd
    except Exception:
        return True


def _poll_foreground(hwnd: Optional[int], timeout: float) -> bool:
    """
    Step 3: input-timing guard as a poll instead of `time.sleep()`.

    Returns immediately (0ms) while the browser still holds the foreground, and only
    spends time — up to `timeout` — when focus was actually lost mid-sequence.
    """
    deadline = time.monotonic() + timeout
    while True:
        if _browser_is_foreground(hwnd):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(_NAV_POLL_INTERVAL)


def _grab_omnibox_url() -> Optional[str]:
    """
    Select the omnibox (ctrl+l), copy it (ctrl+c) and read it from the clipboard.

    The caller owns the clipboard save/restore, so a poll that reads the omnibox more
    than once still performs a single clipboard round-trip (Step 3).
    """
    if not input_driver or not hasattr(input_driver, "get_clipboard"):
        return None
    try:
        input_driver.hotkey("ctrl", "l")
        input_driver.hotkey("ctrl", "c")
        input_driver.press("escape")
        return (input_driver.get_clipboard() or "").strip() or None
    except Exception:
        return None


def _current_title() -> str:
    """Free navigation signal: the desktop browser window title, lowercased."""
    try:
        hwnd = _resolve_desktop_browser_hwnd()
        if hwnd and windows_native:
            return (windows_native.get_window_title(hwnd) or "").lower()
    except Exception:
        pass
    return ""


def _title_matches_host(title: str, expected_url: str) -> bool:
    """
    Pure host/label match against an already-read window title. No subprocess, no UIA,
    no clipboard and no keystroke.
    """
    if not title:
        return False
    host = (urllib.parse.urlparse(expected_url).hostname or "").lower()
    if not host:
        return False
    if host in title:
        return True
    # Most sites (and every search result page) title themselves with the bare site
    # label only ("Example Domain", "... - Google Search"), so accept that label too.
    # A leading "www"/"m" prefix is not the site label: www.google.com -> "google".
    labels = [p for p in host.split(".") if p and p not in ("www", "m", "web", "amp")]
    if len(labels) > 1:
        labels = labels[:-1]  # drop the TLD
    return any(len(label) >= 4 and label in title for label in labels)


def _title_shows_host(expected_url: str) -> bool:
    """Read the current window title and match it against the expected host."""
    return _title_matches_host(_current_title(), expected_url)


def _url_confirms(observed: str, expected_url: str) -> bool:
    """
    Phase B: does a URL read from the omnibox actually confirm the expected URL?

    Host and path must match. When the expected URL carries a query, the observed query
    must carry the same values — that is exactly what tells `...?n=1` apart from `...?n=2`.
    With no query on the expected side, extra parameters appended by the site are fine.
    """
    obs = urllib.parse.urlparse((observed or "").strip())
    exp = urllib.parse.urlparse((expected_url or "").strip())
    if not obs.hostname or not exp.hostname:
        return False
    if obs.hostname.lower() != exp.hostname.lower():
        return False
    if (obs.path or "/").rstrip("/") != (exp.path or "/").rstrip("/"):
        return False
    exp_q = urllib.parse.parse_qsl(exp.query, keep_blank_values=True)
    if not exp_q:
        return True
    obs_q = dict(urllib.parse.parse_qsl(obs.query, keep_blank_values=True))
    return all(obs_q.get(key) == value for key, value in exp_q)


def _verify_desktop_navigation(
    expected_url: str, timeout: float = _NAV_TIMEOUT, prev_title: str = ""
) -> Optional[str]:
    """
    Step 3 + Phase B: verify a desktop keystroke navigation by polling instead of sleeping.

    Tier 1 (every 40ms, free): the window title confirms the host AND is trustworthy —
    the host was absent from the pre-navigation title, or the title changed after Enter.
    A title that merely repeats the previous page's host is NOT accepted (that was the
    false "verified" on repeat navigations to the same site).
    Tier 2 (at most _NAV_MAX_READS): read the omnibox, sharing ONE clipboard
    save/restore pair for the whole poll instead of one per read. The read must confirm
    host + path (+ query) via _url_confirms.

    Returns the observed URL (or `expected_url` when the title confirmed it), else None.
    The caller still reports "verified at <url>" / "dispatched, not verified".
    """
    if not input_driver:
        return None
    host = (urllib.parse.urlparse(expected_url).hostname or "").lower()
    if not host:
        return None
    _t_all = time.perf_counter()
    _t = time.perf_counter()
    orig_clip = None
    saved = False
    reads = 0
    deadline = time.monotonic() + timeout
    next_read = time.monotonic() + _NAV_FIRST_READ
    prev_confirms_host = _title_matches_host(prev_title, expected_url)
    try:
        while time.monotonic() < deadline:
            title = _current_title()
            title_ok = _title_matches_host(title, expected_url) and (
                not prev_confirms_host or title != prev_title
            )
            if title_ok:
                _prof("verify: title confirmed host (no omnibox read)", _t)
                _prof("verify: TOTAL", _t_all)
                return expected_url
            if reads < _NAV_MAX_READS and time.monotonic() >= next_read:
                if not saved:
                    orig_clip = (
                        input_driver.get_clipboard()
                        if hasattr(input_driver, "get_clipboard")
                        else None
                    )
                    saved = True
                    _prof("verify: clipboard save (once)", _t)
                _t = time.perf_counter()
                observed = _grab_omnibox_url()
                reads += 1
                _prof("verify: omnibox read #%d" % reads, _t)
                if observed and _url_confirms(observed, expected_url):
                    _prof("verify: TOTAL", _t_all)
                    return observed
                next_read = time.monotonic() + _NAV_READ_GAP
            time.sleep(_NAV_POLL_INTERVAL)
    except Exception:
        pass
    finally:
        if saved and orig_clip is not None:
            _t = time.perf_counter()
            _restore_clipboard(orig_clip)
            _prof("verify: clipboard restore (once)", _t)
    _prof("verify: TOTAL (unverified)", _t_all)
    return None


def _type_into_omnibox(text: str) -> str:
    """
    Phase C: type into the focused omnibox with the fastest proven method.

    Same 44-char URL, 10 runs each, exact URL re-read from the omnibox every run:
      clipboard save + set/ctrl+v + restore  p50  87ms  10/10 exact
      pyautogui.write interval=0.001s        p50 106ms  10/10 exact (0.005/0.01/0.02 slower)
      type_safe_unicode (did)                p50 289ms  10/10 exact
    The clipboard method wins and is the fidelity-safe one (no keymap dependence,
    Unicode-proof), so it is the default; type_safe_unicode stays as the fallback.
    Returns the method actually used.
    """
    if not input_driver:
        return "no_input"
    orig = None
    if hasattr(input_driver, "get_clipboard") and hasattr(input_driver, "set_clipboard"):
        try:
            orig = input_driver.get_clipboard()
            pasted = str(input_driver.set_clipboard(text) or "")
            if pasted.startswith("Pasted:"):
                time.sleep(_PASTE_SETTLE)
                _restore_clipboard(orig)
                return "clipboard"
        except Exception:
            pass
        if orig is not None:
            _restore_clipboard(orig)
    input_driver.type_safe_unicode(text)
    return "type_safe_unicode"


def _desktop_navigate(text: str, expected_url: str) -> Tuple[str, Optional[str]]:
    """
    Step 3: drive the focused browser through the omnibox and verify by polling.

    `text` is what gets typed (a URL for go_to, the spoken query for search) and
    `expected_url` is the URL that must show up for the action to count as verified.
    Returns ("verified" | "unverified" | "no_input", observed_url).
    """
    _t_all = time.perf_counter()
    _t = time.perf_counter()
    focused = bool(input_driver and _focus_desktop_browser())
    _prof("focus: _focus_desktop_browser", _t)
    if not focused:
        return "no_input", None

    hwnd = _resolve_desktop_browser_hwnd()

    _t = time.perf_counter()
    prev_title = _current_title()  # Phase B: free "before" signal, read before any keystroke
    _prof("title: capture pre-navigation title", _t)

    _t = time.perf_counter()
    input_driver.hotkey("ctrl", "l")
    _prof("key: ctrl+l", _t)

    _t = time.perf_counter()
    _poll_foreground(hwnd, 0.08)  # poll, not sleep: 0ms when focus never left
    _prof("guard: foreground poll after ctrl+l", _t)

    _t = time.perf_counter()
    used = _type_into_omnibox(text)
    _prof(f"type: {used}", _t)

    _t = time.perf_counter()
    _poll_foreground(hwnd, 0.05)  # poll, not sleep
    _prof("guard: foreground poll before enter", _t)

    _t = time.perf_counter()
    input_driver.press("enter")
    _prof("key: enter", _t)

    _t = time.perf_counter()
    _reset_snapshot()
    _prof("_reset_snapshot()", _t)

    _t = time.perf_counter()
    verified = _verify_desktop_navigation(expected_url, prev_title=prev_title)
    _prof("verify: _verify_desktop_navigation", _t)

    _prof("TOTAL desktop branch", _t_all)
    return ("verified" if verified else "unverified"), verified


_BROWSER_TITLE_SUFFIXES = (
    " - google chrome", " - microsoft edge", " - brave",
    " - mozilla firefox", " - firefox", " - opera", " - vivaldi", " - arc",
)
_BROWSER_TITLE_KEYWORDS = ("chrome", "edge", "firefox", "brave", "opera", "vivaldi", "arc")


def _is_isolated(params: dict) -> bool:
    """True when the call targets the isolated background agent-browser daemon."""
    return bool(params.get("isolated") or params.get("backend") == "agent_browser")


# Step 2: per-request context, set by browser_control(). Read by the single _exec_ab
# choke point so it can tell a desktop request apart from an isolated daemon request.
_req_ctx = threading.local()


def _request_is_isolated() -> bool:
    """True when the in-flight browser_control() call targets the isolated daemon."""
    return bool(getattr(_req_ctx, "isolated", False))


def _resolve_desktop_browser_hwnd(force: bool = False) -> Optional[int]:
    """Locate the HWND of the user's live desktop browser window (Chrome preferred). Cached for 2s."""
    now = time.monotonic()
    if not force and _cached_hwnd["hwnd"] is not None and (now - _cached_hwnd["t"] < 2.0):
        if windows_native and windows_native.user32 and windows_native.user32.IsWindow(_cached_hwnd["hwnd"]):
            return _cached_hwnd["hwnd"]

    def _ret(res_val: Optional[int]) -> Optional[int]:
        if res_val is not None:
            _cached_hwnd["t"] = now
            _cached_hwnd["hwnd"] = res_val
        return res_val

    if not windows_native:
        return _ret(None)
    _attach_input_desktop()
    try:
        import ctypes
        import psutil
        user32 = windows_native.user32

        # 1. Immediate check: is the active foreground window already a browser?
        if user32:
            fg = user32.GetForegroundWindow()
            if fg and windows_native.is_real_top_level_window(fg) and not windows_native.is_self_or_console_window(fg):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
                try:
                    pname = (psutil.Process(pid.value).name() or "").lower()
                    if pname in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                        return _ret(fg)
                except Exception:
                    pass

        # 2. Enumerate visible top-level windows checking process name and title
        fallback: Optional[int] = None
        for hwnd, title in windows_native.enum_top_level_windows():
            if user32:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    pname = (psutil.Process(pid.value).name() or "").lower()
                    if pname == "chrome.exe":
                        return _ret(hwnd)
                    if pname in ("msedge.exe", "brave.exe", "firefox.exe") and fallback is None:
                        fallback = hwnd
                except Exception:
                    pass
            tl = title.lower()
            if any(tl.endswith(s) for s in _BROWSER_TITLE_SUFFIXES):
                if "chrome" in tl:
                    return _ret(hwnd)
                if fallback is None:
                    fallback = hwnd
            elif any(k in tl for k in _BROWSER_TITLE_KEYWORDS) and fallback is None:
                fallback = hwnd

        # 3. Direct interactive input desktop enumeration if background runner did not enumerate top-level
        if fallback is None and user32:
            try:
                from ctypes import wintypes
                hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
                if hdesk:
                    DESKTOPENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                    def _cb(h: int, lp: int) -> bool:
                        nonlocal fallback
                        if fallback is not None:
                            return False
                        length = user32.GetWindowTextLengthW(h)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(h, buff, length + 1)
                            tl = buff.value.lower()
                            if any(tl.endswith(s) for s in _BROWSER_TITLE_SUFFIXES) or "google chrome" in tl:
                                fallback = h
                                return False
                        return True
                    user32.EnumDesktopWindows(hdesk, DESKTOPENUMPROC(_cb), 0)
            except Exception:
                pass

        return _ret(fallback)
    except Exception:
        return _ret(None)


def _uia_browser_tabs(hwnd: Optional[int]) -> List[dict]:
    """Read the real open tabs of a desktop browser window via UIA."""
    if not hwnd:
        return []
    _attach_input_desktop()
    try:
        from core.computer import windows_uia
        return windows_uia.get_browser_tabs(hwnd) or []
    except Exception:
        return []


def _uia_switch_tab(hwnd: Optional[int], query: str) -> bool:
    """Switch a desktop browser to the tab whose title matches `query`."""
    if not hwnd or not query:
        return False
    _attach_input_desktop()
    try:
        from core.computer import windows_uia
        if windows_uia.switch_tab_by_title(hwnd, query):
            time.sleep(0.08)
            return True
    except Exception:
        pass
    return False


def _format_real_tab_list(tabs: List[dict]) -> str:
    """Render a UIA tab list into a compact, spoken-friendly summary."""
    lines: List[str] = []
    active: Optional[int] = None
    for t in tabs:
        idx = t.get("index")
        title = (t.get("title") or "(untitled)").strip()
        if t.get("selected"):
            active = idx
            lines.append(f"{idx}. {title} (active)")
        else:
            lines.append(f"{idx}. {title}")
    header = f"There are {len(tabs)} tabs open in the desktop browser"
    if active:
        header += f" (tab {active} is active)"
    return header + ":\n" + "\n".join(lines)


def _looks_like_url(value: str) -> bool:
    """Heuristic: does this label look like a URL / domain / section path?"""
    v = (value or "").strip()
    if not v or " " in v:
        return False
    if "://" in v or v.startswith("www."):
        return True
    return bool(re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?$", v, re.IGNORECASE))


def _normalize_url(url: str) -> str:
    """Normalize bare words or domains into standard https URLs."""
    url = (url or "").strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    if "." not in url:
        url = url + ".com"
    return "https://" + url


# Phase B: a URL now travels to the CLI as ONE argv element (Phase A), so the usual
# query/fragment punctuation (& % ' ; = ? #) no longer has to be banned. What stays
# prohibited everywhere: the metacharacters that are never legitimate in a URL, plus
# control characters, whitespace and backticks.
_PROHIBITED_URL_CHARS = set('|$()<>"\\') | {"`", "\n", "\r", "\t", "\x00"}
_HOST_LABEL_RE = re.compile(r"^[a-z0-9.-]+$", re.IGNORECASE)
_IPV6_HOST_RE = re.compile(r"^[0-9a-fA-F:.]+$")


def _host_error(parsed: urllib.parse.ParseResult) -> str:
    """
    Phase B: the host may only carry letters, digits, dots, hyphens and a port.

    This is what keeps `https://evil.com&calc.exe` out now that `&` is allowed in the
    query: the `&` lands in the netloc, which is not a legal host character.
    """
    netloc = parsed.netloc or ""
    if not netloc:
        return f"URL host is missing in '{parsed.geturl()}'"
    try:
        port = parsed.port
    except ValueError as e:
        return f"Invalid port in URL host '{netloc}': {e}"
    if port is not None and not 0 < port < 65536:
        return f"Invalid port in URL host '{netloc}'"
    host = parsed.hostname or ""
    if not host:
        return f"URL host is missing in '{parsed.geturl()}'"
    if ":" in host:  # bracketed IPv6 literal (urlparse strips the brackets)
        if not _IPV6_HOST_RE.match(host):
            return f"Invalid IPv6 host '{host}'"
        return ""
    if not _HOST_LABEL_RE.match(host):
        return (
            f"Invalid character in URL host '{host}'; only letters, digits, dots and "
            "hyphens are allowed"
        )
    return ""


def _safe_url(s: str) -> Tuple[bool, str]:
    """
    Validate a user-supplied http(s) URL.

    Phase B: query/fragment punctuation (& % ' ; = ? #) is allowed — the URL is handed to
    the CLI as a single argv element, so neither a shell nor cmd.exe can re-parse it.
    Still refused: any non-http(s) scheme, control characters, whitespace, backticks,
    and any host character other than letters, digits, dots, hyphens and a port.
    """
    if not s:
        return True, ""
    val = str(s).strip()
    if any(c in _PROHIBITED_URL_CHARS for c in val):
        return False, f"URL contains prohibited characters: {val}"
    if any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in val):
        return False, f"URL contains prohibited characters: {val}"
    try:
        parsed = urllib.parse.urlparse(val)
    except Exception as e:
        return False, f"Malformed URL: {e}"
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'; only http and https are allowed"
    host_err = _host_error(parsed)
    if host_err:
        return False, host_err
    return True, ""


_SEARCH_QUERY_MAX = 300
_CONTROL_CHARS = ("\r", "\n", "\t", "\x00")


def _clean_query(raw: Any) -> str:
    """
    Step 1b: sanitize spoken search text before it reaches any URL or keystroke.

    Control characters are dropped (turned into word separators), whitespace runs are
    collapsed and the result is capped at _SEARCH_QUERY_MAX characters.
    """
    q = str(raw or "")
    for ch in _CONTROL_CHARS:
        q = q.replace(ch, " ")
    q = " ".join(q.split())
    return q[:_SEARCH_QUERY_MAX].strip()


def _search_url(engine: str, query: str) -> Tuple[bool, str]:
    """
    Step 1a: build the search URL for a spoken query, percent-encoded end to end.

    The query is never interpolated raw: it is quote_plus()-encoded against the FIXED
    engine base, so no URL/shell metacharacter from spoken text (`& | ^ % " ' ; $`) can
    survive into the final URL. Only the fixed base, the final scheme and the final
    hostname are validated — `_safe_url` stays strict for user-supplied go_to URLs.
    Returns (True, url) or (False, error_message).
    """
    base = _SEARCH_ENGINES.get(str(engine or "google").lower(), _SEARCH_ENGINES["google"])
    base_ok, base_err = _safe_url(base)
    if not base_ok:
        return False, f"search engine base is invalid: {base_err}"

    url = base + urllib.parse.quote_plus(query)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'; only http and https are allowed"
    host = (parsed.hostname or "").lower()
    base_host = (urllib.parse.urlparse(base).hostname or "").lower()
    if not host or host != base_host:
        return False, f"search URL hostname '{host}' does not match the search engine base '{base_host}'"
    return True, url


def _open_os_url(url: str) -> None:
    """Launch URL via OS default handler without cmd /c start shell string."""
    if _OS == "Windows":
        os.startfile(url)
    elif _OS == "Darwin":
        subprocess.Popen(["open", url])
    else:
        subprocess.Popen(["xdg-open", url])


_CACHED_AB_CMD: Optional[str] = None
_CACHED_AB_EXE: Optional[str] = None


def _resolve_ab_exe() -> Optional[str]:
    """
    Phase A: locate the native agent-browser binary shipped inside the npm package.

    The npm shim (agent-browser.cmd -> node bin/agent-browser.js) is executed by cmd.exe,
    which re-parses whatever is passed on the command line: parentheses, spaces, quotes,
    & and | are mangled, so eval payloads never reach the page intact. The package ships
    a real win32 executable next to that shim; preferring it means each argv element is
    delivered byte-for-byte.
    """
    global _CACHED_AB_EXE
    if _CACHED_AB_EXE:
        return _CACHED_AB_EXE

    candidates: List[Path] = []
    if _OS == "Windows":
        for root_var in ("APPDATA", "LOCALAPPDATA"):
            root = os.environ.get(root_var, "")
            if not root:
                continue
            pkg_bin = Path(root) / "npm" / "node_modules" / "agent-browser" / "bin"
            candidates.append(pkg_bin / "agent-browser-win32-x64.exe")
            candidates.append(pkg_bin / "agent-browser-win32-arm64.exe")

    for candidate in candidates:
        if candidate.exists():
            _CACHED_AB_EXE = str(candidate)
            return _CACHED_AB_EXE
    return None


def _resolve_ab_cmd() -> Optional[str]:
    """Find the agent-browser executable, resolving npm paths or auto-bootstrapping.

    Phase A: the native binary wins over the .cmd shim so nothing runs through cmd.exe.
    """
    global _CACHED_AB_CMD
    if _CACHED_AB_CMD:
        return _CACHED_AB_CMD

    native = _resolve_ab_exe()
    if native:
        _CACHED_AB_CMD = native
        return native

    b = shutil.which("agent-browser")
    if b:
        _CACHED_AB_CMD = b
        return b

    if _OS == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidate = Path(appdata) / "npm" / "agent-browser.cmd"
            if candidate.exists():
                _CACHED_AB_CMD = str(candidate)
                return _CACHED_AB_CMD

    # Try on-the-fly bootstrap via core.installer
    try:
        from core.installer import ensure_agent_browser
        if ensure_agent_browser():
            b2 = shutil.which("agent-browser")
            if b2:
                _CACHED_AB_CMD = b2
                return b2
            if _OS == "Windows":
                appdata = os.environ.get("APPDATA", "")
                candidate = Path(appdata) / "npm" / "agent-browser.cmd"
                if candidate.exists():
                    _CACHED_AB_CMD = str(candidate)
                    return _CACHED_AB_CMD
    except Exception:
        pass

    # Fallback to npx if npm/npx is present
    if shutil.which("npx") or shutil.which("npx.cmd"):
        npx_bin = shutil.which("npx") or shutil.which("npx.cmd")
        _CACHED_AB_CMD = npx_bin
        return npx_bin

    return None


# ── Chrome CDP Remote Debugging Connection ────────────────────────────────────

CDP_PORT = 9222
_cdp_cache: Dict[str, Any] = {"t": 0.0, "val": False}


def _is_cdp_available(port: int = CDP_PORT, force: bool = False) -> bool:
    """Quick check (<30ms) whether Chrome remote debugging port is answering (cached for 1.0s)."""
    now = time.monotonic()
    if not force and (now - _cdp_cache["t"] < 1.0):
        return _cdp_cache["val"]
    try:
        res = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.15).read().decode()
        ans = bool("webSocketDebuggerUrl" in res)
    except Exception:
        ans = False
    _cdp_cache["t"] = now
    _cdp_cache["val"] = ans
    return ans


_UNSET = object()
_ident: Dict[str, Any] = {"t": 0.0, "val": _UNSET}


def _agent_browser_daemon_alive() -> bool:
    """
    Return True only when the agent-browser daemon is genuinely running.

    A leftover ~/.agent-browser/default.target (and even default.port) survives a
    crashed/killed daemon, which previously produced a false identity mismatch that
    blocked every navigation. The daemon counts as alive when its recorded port
    accepts a TCP connection (0.2s) or its recorded pid is still running.
    """
    ab_dir = Path.home() / ".agent-browser"

    # 1. Port probe: an accepting TCP connection proves a live listener.
    try:
        port_file = ab_dir / "default.port"
        if port_file.exists():
            m = re.search(r"\d+", port_file.read_text(encoding="utf-8", errors="replace"))
            if m:
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.2)
                    if sock.connect_ex(("127.0.0.1", int(m.group()))) == 0:
                        return True
    except Exception:
        pass

    # 2. PID probe: the recorded daemon process must still exist.
    try:
        pid_file = ab_dir / "default.pid"
        if pid_file.exists():
            m = re.search(r"\d+", pid_file.read_text(encoding="utf-8", errors="replace"))
            if m:
                import psutil
                if psutil.pid_exists(int(m.group())):
                    return True
    except Exception:
        pass

    return False


def _verify_session_identity_uncached() -> Optional[str]:
    """
    Verify identity between agent-browser daemon / CDP target and user's desktop browser HWND.
    Returns None if identity matches or no conflict; returns a hard error string on mismatch.
    """
    hwnd = _resolve_desktop_browser_hwnd()
    if not hwnd:
        return None

    # Determine desktop window PID
    desktop_pid: Optional[int] = None
    if windows_native and windows_native.user32:
        try:
            import ctypes
            pid = ctypes.c_ulong()
            windows_native.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            desktop_pid = pid.value
        except Exception:
            pass

    # 1. If CDP is active, compare the target process against the desktop browser HWND
    if _is_cdp_available(CDP_PORT):
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=0.25)
            ver_data = json.loads(req.read().decode())
            import psutil
            cdp_pid: Optional[int] = None
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == CDP_PORT and conn.status == "LISTEN":
                    cdp_pid = conn.pid
                    break

            if cdp_pid is not None and desktop_pid is not None:
                if cdp_pid != desktop_pid:
                    is_related = False
                    try:
                        p_desk = psutil.Process(desktop_pid)
                        p_cdp = psutil.Process(cdp_pid)
                        if p_desk.ppid() == cdp_pid or p_cdp.ppid() == desktop_pid:
                            is_related = True
                        elif any(child.pid == desktop_pid for child in p_cdp.children(recursive=True)):
                            is_related = True
                        elif any(child.pid == cdp_pid for child in p_desk.children(recursive=True)):
                            is_related = True
                    except Exception:
                        pass
                    if not is_related:
                        return (
                            f"Session identity mismatch: Chrome CDP port {CDP_PORT} belongs to PID {cdp_pid}, "
                            f"but desktop browser HWND belongs to PID {desktop_pid}."
                        )
        except Exception as e:
            return f"Session identity verification failed: {e}"
        return None

    # 2. With no CDP session attached there is nothing that can conflict with the
    #    desktop browser: driving the daemon is blocked at the _exec_ab choke point
    #    instead (Step 2), so no refusal is raised for this case. A target file left
    #    behind by a dead daemon is still cleared so it cannot poison later daemon calls.
    ab_target = Path.home() / ".agent-browser" / "default.target"
    if ab_target.exists() and hwnd:
        if not _agent_browser_daemon_alive():
            # Stale leftover from a dead daemon: identity is OK, no CDP.
            _clear_stale_ab_target()

    return None


def _verify_session_identity(force: bool = False) -> Optional[str]:
    """Memoized wrapper around session identity verification with a 3.0s cache."""
    now = time.monotonic()
    if not force and _ident["val"] is not _UNSET and (now - _ident["t"]) < 3.0:
        return _ident["val"]
    val = _verify_session_identity_uncached()
    _ident["t"] = now
    _ident["val"] = val
    return val


def _is_browser_session_active() -> bool | str:
    """True if active and identity verified; returns hard error string on mismatch."""
    err = _verify_session_identity()
    if err:
        return err
    if _is_cdp_available(CDP_PORT):
        return True
    # A leftover default.port alone is not proof of a live daemon.
    return _agent_browser_daemon_alive()


# ── Step 2: desktop vs daemon routing ────────────────────────────────────────

def _cdp_session_up() -> bool:
    """True only when a live Chrome CDP session is attached on CDP_PORT."""
    return _is_cdp_available(CDP_PORT)


def _use_desktop_path(params: dict) -> bool:
    """
    Step 2: a non-isolated request with CDP down must be driven purely on the desktop
    (keystrokes / UIA / clipboard). Driving the background daemon is only ever legal
    when a CDP session is up, which is also what makes the wrong-browser class of bugs
    impossible for desktop requests.
    """
    return not _is_isolated(params) and not _cdp_session_up()


def _identity_gate(params: dict) -> Optional[str]:
    """
    Step 2 route gate shared by every desktop-capable handler.

    Returns a refusal string ONLY when a live CDP session is attached and its target
    does not match the desktop browser window. Returns None otherwise (the request may
    proceed: either the daemon path is verified, or the request is desktop-only).
    """
    if _is_isolated(params) or not _cdp_session_up():
        return None
    return _verify_session_identity()


# ── Step 4: free state returned with every mutating result ───────────────────
# Handlers publish only data they already hold (the URL they just built, a tab list
# they already enumerated, the scroll JSON they already parsed). browser_control()
# then appends one short suffix. Nothing here starts a subprocess or a UIA call.

_STATE_ACTIONS = {
    "go_to", "open",
    "search",
    "scroll", "scroll_bottom", "scroll_top", "bottom", "top",
    "new_tab",
    "close_tab", "close_tab_by_title",
    "switch_tab", "next_tab", "prev_tab", "previous_tab", "last_tab", "first_tab",
}

_ACTION_STATE = threading.local()


def _reset_action_state() -> None:
    """Clear the published free state so a previous action cannot leak into the next."""
    _ACTION_STATE.url = ""
    _ACTION_STATE.tabs = None
    _ACTION_STATE.scroll = None


def _state_label(url: str = "") -> str:
    """`<host>/<path up to 40 chars>` from `url`, else the window title, else '?'."""
    if url:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if host:
            return (host + (parsed.path or ""))[:40]
    if not _request_is_isolated():
        try:
            hwnd = _resolve_desktop_browser_hwnd()
            if hwnd and windows_native:
                title = (windows_native.get_window_title(hwnd) or "").strip()
                lowered = title.lower()
                for suffix in _BROWSER_TITLE_SUFFIXES:
                    if lowered.endswith(suffix):
                        title = title[: -len(suffix)].strip()
                        break
                if title:
                    return title[:40]
        except Exception:
            pass
    return "?"


def _state_suffix() -> str:
    """
    Step 4: one short state suffix for mutating results.

    " | <host>/<path up to 40 chars> | tabs=<N or ?> | scroll=<pct or ?>".
    Values that are not already free are reported as "?".
    """
    url = getattr(_ACTION_STATE, "url", "") or ""
    tabs = getattr(_ACTION_STATE, "tabs", None)
    scroll = getattr(_ACTION_STATE, "scroll", None)
    tabs_s = str(tabs) if isinstance(tabs, int) and tabs >= 0 else "?"
    scroll_s = str(scroll) if isinstance(scroll, int) else "?"
    return f" | {_state_label(url)} | tabs={tabs_s} | scroll={scroll_s}"


def _clear_stale_ab_target(clear_all: bool = False, relaunch: bool = False) -> None:
    """Clear stale daemon target files to prevent 'tab_gone' or disconnected CDP errors."""
    _ident["t"] = 0.0
    _ident["val"] = _UNSET
    try:
        ab_dir = Path.home() / ".agent-browser"
        fnames = ("default.target", "default.pid", "default.port", "default.config") if (clear_all and relaunch) else ("default.target",)
        for fname in fnames:
            f = ab_dir / fname
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def _resolve_chrome_exe() -> Optional[str]:
    """Find the real Google Chrome executable on the system."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return shutil.which("chrome.exe") or shutil.which("chrome") or shutil.which("google-chrome")


def _resolve_chrome_user_data_dir() -> Optional[str]:
    """Resolve the user's real Chrome user-data-dir."""
    if _OS == "Windows":
        real_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        if os.path.exists(real_data):
            return real_data
    return None


def _resolve_chrome_profile() -> str:
    """Read last-used profile from <user-data-dir>/Local State, defaulting to 'Default'."""
    user_data = _resolve_chrome_user_data_dir()
    if user_data:
        try:
            local_state_file = Path(user_data) / "Local State"
            if local_state_file.exists():
                with open(local_state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_used = data.get("profile", {}).get("last_used")
                    if last_used and isinstance(last_used, str):
                        return last_used
        except Exception:
            pass
    return "Default"


CHROME_CDP_USER_DATA_DIR = os.path.expandvars(r"%LOCALAPPDATA%\ZEZO\chrome")
USE_DEDICATED_CDP_PROFILE = False


def _ensure_chrome_cdp(port: int = CDP_PORT, timeout_sec: float = 3.0) -> bool:
    """
    Ensure the user's desktop Chrome is running with --remote-debugging-port using the
    user's real user-data-dir and last-used profile. If it cannot be determined safely or if Chrome is
    already running without CDP, returns False instead of silently launching a parallel browser.
    """
    _ident["t"] = 0.0
    _ident["val"] = _UNSET
    if _is_cdp_available(port):
        return True

    chrome_bin = _resolve_chrome_exe()
    user_data_dir = _resolve_chrome_user_data_dir()
    if not chrome_bin or not user_data_dir:
        return False

    # If Chrome is already running without CDP, launching another instance with the same
    # user-data-dir will fail or connect to the existing non-CDP instance. Return False.
    if _resolve_desktop_browser_hwnd() is not None:
        return False

    _clear_stale_ab_target(clear_all=False, relaunch=False)

    flags = 0
    if _OS == "Windows":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

    profile_dir = _resolve_chrome_profile()
    effective_user_data = CHROME_CDP_USER_DATA_DIR if USE_DEDICATED_CDP_PROFILE else user_data_dir
    args = [
        chrome_bin,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={effective_user_data}",
        f"--profile-directory={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    try:
        subprocess.Popen(
            args,
            creationflags=flags,
            close_fds=True if _OS != "Windows" else False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_cdp_available(port):
            time.sleep(0.1)
            return True
        time.sleep(0.1)

    return _is_cdp_available(port)


_AB_STALE_MARKERS = ("tab_gone", "bound tab is gone", "CDP connection failed")
_AB_RETRY_VERBS = ("get url", "get title", "snapshot", "tab list")


def _ab_verb(args: List[str]) -> str:
    """The agent-browser sub-command of an argv list (a leading --cdp pair is skipped)."""
    parts = [str(a) for a in args]
    if parts[:1] == ["--cdp"]:
        parts = parts[2:]
    return " ".join(parts[:2]).strip().lower()


def _run_ab_process(argv: List[str], timeout: int) -> Tuple[int, str]:
    """
    Run one agent-browser argv with file-redirected output.

    File redirection (not pipes) is kept because the background daemon can hold the
    anonymous pipe handles open on Windows and hang the parent.
    """
    temp_dir = tempfile.gettempdir()
    out_file = os.path.join(temp_dir, f"zezo_ab_{os.getpid()}_{int(time.time() * 1000)}.txt")
    creation_flags = subprocess.CREATE_NO_WINDOW if _OS == "Windows" else 0

    try:
        t0 = time.perf_counter()
        with open(out_file, "wb") as f_out:
            proc = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=f_out,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                creationflags=creation_flags,
            )
        if ZEZO_PROFILE:
            print(f"[ab] {(time.perf_counter()-t0)*1000:.0f}ms {' '.join(argv[1:])[:48]}")
        output = ""
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8", errors="replace") as f:
                output = f.read().strip()
        return proc.returncode, output
    except subprocess.TimeoutExpired:
        return -1, f"agent-browser command timed out after {timeout}s"
    except Exception as e:
        return -1, f"agent-browser execution error: {e}"
    finally:
        try:
            if os.path.exists(out_file):
                os.remove(out_file)
        except Exception:
            pass


def _exec_ab_argv(args: List[str], timeout: int = 25) -> Tuple[int, str]:
    """
    Phase A: execute agent-browser from a real argv list — no shlex, no cmd.exe shim.

    Every element reaches the CLI untouched, which is what eval / fill / keyboard type /
    open / tab new need (the old string path routed the payload through cmd.exe, which
    re-split it on spaces, parentheses, quotes, & and |). Keeps the Step 2c NO_CDP choke
    point and the stale-tab retry for read-only inspection commands.
    """
    verb = _ab_verb(args)
    if (
        not _request_is_isolated()
        and not _cdp_session_up()
        and not verb.startswith(("install", "profiles", "close"))
    ):
        return -1, "NO_CDP: refusing to drive the background browser for a desktop request"

    ab_bin = _resolve_ab_cmd()
    if not ab_bin:
        return -1, (
            "Browser automation requires agent-browser. Node.js or npm was not found. "
            "Please install Node.js and run 'npm install -g agent-browser'."
        )

    plain_args = [str(a) for a in args]
    argv = [ab_bin, *plain_args]

    # Attach to live desktop Chrome via CDP when available
    if (
        _is_cdp_available(CDP_PORT)
        and not verb.startswith(("install", "profiles", "close"))
        and plain_args[:1] != ["--cdp"]
    ):
        argv = [ab_bin, "--cdp", str(CDP_PORT), *plain_args]

    code, output = _run_ab_process(argv, timeout)

    if not any(marker in output for marker in _AB_STALE_MARKERS):
        return code, output

    _ident["t"] = 0.0
    _ident["val"] = _UNSET

    retry_allowed = any(verb.startswith(prefix) for prefix in _AB_RETRY_VERBS)
    if not retry_allowed:
        return code, output

    _clear_stale_ab_target(clear_all=("CDP connection failed" in output), relaunch=False)
    retry_argv = list(argv)
    if "CDP connection failed" in output and not _is_cdp_available(CDP_PORT):
        if retry_argv[1:2] == ["--cdp"]:
            del retry_argv[1:3]
    return _run_ab_process(retry_argv, timeout)


def _exec_ab(args_str: str, timeout: int = 25) -> Tuple[int, str]:
    """
    String variant of _exec_ab_argv, kept for simple commands only (no eval payloads,
    fill values, typed text or URLs — those go through _exec_ab_argv).
    """
    return _exec_ab_argv(shlex.split(args_str.strip()), timeout)


# ── Action Dispatch Functions ────────────────────────────────────────────────

_last_snapshot_text: str = ""


def _reset_snapshot() -> None:
    """Clear cached snapshot text after page navigation or URL state change."""
    global _last_snapshot_text
    _last_snapshot_text = ""


def _ensure_maximized(headed: bool) -> None:
    """If browser was opened in headed mode, ensure it is maximized via Windows native API."""
    if not headed or _OS != "Windows":
        return
    try:
        if windows_native:
            time.sleep(0.35)
            windows_native.maximize_window("chrome")
    except Exception:
        pass


def _act_go_to(params: dict) -> str:
    raw_url = params.get("url") or params.get("target") or ""
    url = _normalize_url(raw_url)

    is_safe, err_msg = _safe_url(url)
    if not is_safe:
        return f"Validation error: {err_msg}"

    _ACTION_STATE.url = url  # Step 4: free state for the result suffix

    is_isolated = _is_isolated(params)

    if not is_isolated:
        # Step 2b: no CDP session -> desktop path only, the daemon is never driven.
        # _ensure_chrome_cdp() may attach the user's own Chrome (only when it is not
        # already running), which legitimately upgrades the request to the CDP path.
        _t = time.perf_counter()
        desktop_only = _use_desktop_path(params)
        _prof("route: _use_desktop_path", _t)
        _t = time.perf_counter()
        cdp_brought_up = _ensure_chrome_cdp()
        _prof("route: _ensure_chrome_cdp", _t)
        if desktop_only and not cdp_brought_up:
            # Step 3: keystroke navigation + polling verification (no fixed sleeps).
            status, verified = _desktop_navigate(url, url)
            if status == "no_input":
                _open_os_url(url)
                _reset_snapshot()
                return f"Opened {url} in default browser."
            if status == "verified":
                return f"Opened {url} in Chrome (desktop fallback, verified at {verified})."
            return f"Opened {url} in Chrome (desktop fallback, dispatched, not verified)."

        # Step 2d: refuse ONLY when a live CDP session is bound to a different browser.
        ident_err = _identity_gate(params)
        if ident_err:
            return f"Refused: {ident_err}"

        # CDP is active and verified
        _focus_desktop_browser()
        code, out = _exec_ab_argv(["open", url])
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")

        if code == 0:
            _ensure_maximized(bool(params.get("headed")))
            _reset_snapshot()
            v_code, v_url = _exec_ab("get url")
            if v_code == 0 and v_url:
                clean_v = "\n".join(l for l in v_url.splitlines() if not l.startswith("[agent-browser]")).strip()
                if (host and host in clean_v.lower()) or (path and len(path) > 1 and path in clean_v):
                    return f"Opened {url} in Chrome (verified at {clean_v})."
                return f"Failed to open {url}: current URL '{clean_v}' does not match expected host '{host}'"
            return f"Opened {url} in Chrome."

        if "EOF while parsing" in out or "Invalid response" in out or "tab_gone" in out:
            time.sleep(0.4)
            v_code, v_url = _exec_ab("get url")
            if v_code == 0 and v_url and "about:blank" not in v_url:
                clean_v = "\n".join(l for l in v_url.splitlines() if not l.startswith("[agent-browser]")).strip()
                if (host and host in clean_v.lower()) or (path and len(path) > 1 and path in clean_v):
                    _ensure_maximized(bool(params.get("headed")))
                    _reset_snapshot()
                    return f"Opened {url} in Chrome (verified at {clean_v})."
                return f"Failed to open {url} in Chrome: verification URL '{clean_v}' does not match expected host '{host}'"
        return f"Failed to open {url} in Chrome: {out}"

    is_headed = bool(params.get("headed") or params.get("visible"))
    code, out = _exec_ab_argv(["open", url, *(["--headed"] if is_headed else [])])
    if code == 0:
        _ensure_maximized(is_headed)
        _reset_snapshot()
        return f"Opened {url} in browser."
    if "EOF while parsing a value" in out or "Invalid response" in out:
        time.sleep(0.5)
        probe_code, probe_url = _exec_ab("get url")
        if probe_code == 0 and probe_url and "about:blank" not in probe_url:
            clean_probe = "\n".join(l for l in probe_url.splitlines() if not l.startswith("[agent-browser]")).strip()
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            path = parsed.path.rstrip("/")
            if (host and host in clean_probe.lower()) or (path and len(path) > 1 and path in clean_probe):
                _ensure_maximized(is_headed)
                _reset_snapshot()
                return f"Opened {url} in browser."
    return f"Failed to open {url}: {out}"


def _act_search(params: dict) -> str:
    query = _clean_query(params.get("query") or params.get("text") or "")
    if not query:
        return "No search query provided."

    engine = params.get("engine", "google").lower()
    is_safe, url_or_err = _search_url(engine, query)
    if not is_safe:
        return f"Validation error: {url_or_err}"
    url = url_or_err
    _ACTION_STATE.url = url  # Step 4: free state for the result suffix

    is_isolated = _is_isolated(params)

    if not is_isolated:
        # Step 2b: no CDP session -> desktop path only, the daemon is never driven.
        if _use_desktop_path(params) and not _ensure_chrome_cdp():
            # Step 3: same shared keystroke navigation + polling verification as go_to.
            status, verified = _desktop_navigate(query, url)
            if status == "no_input":
                _open_os_url(url)
                _reset_snapshot()
                return f"Opened search for '{query}' in default browser."
            if status == "verified":
                return f"Searched for '{query}' on {engine} in Chrome (desktop fallback, verified at {verified})."
            return f"Searched for '{query}' on {engine} in Chrome (desktop fallback, dispatched, not verified)."

        # Step 2d: refuse ONLY when a live CDP session is bound to a different browser.
        ident_err = _identity_gate(params)
        if ident_err:
            return f"Refused: {ident_err}"

        # CDP active and verified
        _focus_desktop_browser()
        code, out = _exec_ab_argv(["open", url])
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()

        if code == 0:
            _ensure_maximized(bool(params.get("headed")))
            _reset_snapshot()
            v_code, v_url = _exec_ab("get url")
            if v_code == 0 and v_url:
                clean_v = "\n".join(l for l in v_url.splitlines() if not l.startswith("[agent-browser]")).strip()
                if host and host in clean_v.lower():
                    return f"Searched for '{query}' on {engine} in Chrome (verified at {clean_v})."
                return f"Failed to search for '{query}': current URL '{clean_v}' does not match expected host '{host}'"
            return f"Searched for '{query}' on {engine} in Chrome."

        if "EOF while parsing" in out or "Invalid response" in out:
            time.sleep(0.4)
            v_code, v_url = _exec_ab("get url")
            if v_code == 0 and v_url:
                clean_v = "\n".join(l for l in v_url.splitlines() if not l.startswith("[agent-browser]")).strip()
                if host and host in clean_v.lower():
                    _ensure_maximized(bool(params.get("headed")))
                    _reset_snapshot()
                    return f"Searched for '{query}' on {engine} in Chrome."
                return f"Failed to search for '{query}': verification URL '{clean_v}' does not match expected host '{host}'"
        return f"Failed to search for '{query}': {out}"

    is_headed = bool(params.get("headed") or params.get("visible"))
    code, out = _exec_ab_argv(["open", url, *(["--headed"] if is_headed else [])])
    if code == 0:
        _ensure_maximized(is_headed)
        _reset_snapshot()
        return f"Searched for '{query}' on {engine}."
    return f"Failed to search for '{query}': {out}"


def _extract_label_from_snapshot(target: str, isolated: bool = False) -> Optional[str]:
    """Extract accessible label/text for a ref (e.g. @e14) or selector from snapshot text."""
    global _last_snapshot_text
    clean_ref = target.lstrip("@").strip()
    if clean_ref.startswith("e") and clean_ref[1:].isdigit():
        if not _last_snapshot_text:
            if not isolated and _verify_session_identity():
                return None
            code, snap = _exec_ab("snapshot -i")
            if code == 0:
                _last_snapshot_text = snap
        if _last_snapshot_text:
            for line in _last_snapshot_text.splitlines():
                if f"[ref={clean_ref}]" in line:
                    m_aria = re.search(r'\baria-label=["\']([^"\']+)["\']', line)
                    m_name = re.search(r'\bname=["\']([^"\']+)["\']', line)
                    if m_aria:
                        return m_aria.group(1).strip()
                    if m_name:
                        return m_name.group(1).strip()
                    m = re.findall(r'["\']([^"\']+)["\']', line)
                    if m:
                        return m[0].strip()
                    before = line.split("[ref=")[0].strip("- ").strip()
                    parts = before.split(maxsplit=1)
                    if len(parts) > 1:
                        return parts[1].strip()
                    return before
    return None


_COOKIE_BANNER_KEYWORDS = (
    "accept all", "accept cookies", "agree and continue", "i agree",
    "allow all", "accept all cookies", "got it", "dismiss", "close banner",
    "close dialog", "close modal"
)


def _try_dismiss_banners(snapshot_text: str, isolated: bool = False) -> Tuple[bool, str]:
    """Auto-detect and click cookie consent or modal overlay dismiss buttons."""
    if not isolated and _verify_session_identity():
        return False, ""
    if not snapshot_text:
        return False, ""
    for kw in _COOKIE_BANNER_KEYWORDS:
        ref = _find_ref_by_text(snapshot_text, kw)
        if ref:
            code, out = _exec_ab(f"click {ref}")
            if code == 0:
                return True, f"Dismissed cookie banner ({kw} -> {ref})"
    return False, ""


def _act_snapshot(params: dict) -> str:
    global _last_snapshot_text
    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            return f"Refused: {ident_err}"

    interactive = "-i" if params.get("interactive", True) else ""
    _exec_ab("wait --load domcontentloaded", timeout=5)
    code, out = _exec_ab(f"snapshot {interactive}".strip())
    if code == 0:
        clean = "\n".join(line for line in out.splitlines() if not line.startswith("[agent-browser]"))
        if not clean.strip() or "(no interactive elements)" in clean.lower():
            time.sleep(0.5)
            retry_code, retry_out = _exec_ab(f"snapshot {interactive}".strip())
            if retry_code == 0:
                clean = "\n".join(line for line in retry_out.splitlines() if not line.startswith("[agent-browser]"))
        res = clean.strip() or "Page has no interactive elements."
        _last_snapshot_text = clean
        return res
    return f"Failed to retrieve snapshot: {out}"


def _click_desktop(params: dict, target: str) -> Optional[str]:
    """
    Desktop click resolution for native windows or non-CDP environments:
      1. If active browser session is active -> defer to DOM engine directly.
      2. Standard URL / section path -> fast address-bar navigation (Ctrl+L).
      3. Interactive in-page control -> UIA InvokePattern by accessible name.
      4. Escalated visual fallback -> L1 UIA -> L1.5 RapidOCR -> L2 Vision coordinates.
    """
    # When live Chrome session is active, defer to DOM engine for exact in-page clicks
    active = _is_browser_session_active()
    if active and not isinstance(active, str):
        return None

    label = (params.get("text") or params.get("description") or "").strip()

    # Address-bar direct navigation
    if _looks_like_url(label or target):
        if input_driver:
            _focus_desktop_browser()
            time.sleep(0.05)
            input_driver.hotkey("ctrl", "l")
            time.sleep(0.06)
            input_driver.type_safe_unicode(_normalize_url(label or target))
            time.sleep(0.03)
            input_driver.press("enter")
            return f"Opened {label or target} via address bar."

    if not input_driver:
        return None

    # Resolve visual label from target if not provided directly
    if not label:
        clean_target = target.lstrip("@").strip()
        if clean_target.startswith("e") and clean_target[1:].isdigit():
            label = _extract_label_from_snapshot(target, isolated=_is_isolated(params)) or ""
        elif not target.startswith(("@", "#", ".")) and "[" not in target:
            label = target.strip()
        elif "[" in target:
            m = re.findall(r'["\']([^"\']+)["\']', target)
            if m:
                label = m[0].replace("-button", "").replace("_button", "").replace("-btn", "").strip()

    if not label:
        return None

    hwnd = _resolve_desktop_browser_hwnd()
    if not hwnd:
        return None

    # L1: Windows UIA InvokePattern by accessible name
    try:
        from core.computer import windows_uia
        _focus_desktop_browser()
        if windows_uia.invoke_element(hwnd, label):
            time.sleep(0.05)
            return f"Clicked '{label}' on the desktop browser."
    except Exception:
        pass

    # Escalated visual fallback for web elements unexposed to standard desktop UIA
    try:
        from actions.computer_control import _find_target_element_escalated
        coords = _find_target_element_escalated(label)
        if coords:
            cx, cy, strategy = coords
            _focus_desktop_browser()
            time.sleep(0.04)
            input_driver.click(cx, cy)
            return f"Clicked '{label}' at ({cx}, {cy}) via {strategy} on desktop Chrome."
    except Exception:
        pass

    return None


def _find_element_info(snapshot_text: str, target_text: str) -> Optional[Tuple[str, str, str]]:
    """
    Search snapshot lines for an interactive element whose accessible name or text
    accurately matches target_text.
    Skips class=, id=, role= values, accepting aria-label=, name=, or trailing text.
    Returns (ref, label, role) if found, else None.
    """
    tgt_lower = target_text.lower().strip()
    if not tgt_lower or not snapshot_text:
        return None

    candidates: List[Tuple[int, str, str, str]] = []
    for line in snapshot_text.splitlines():
        # Element must have an interactive ref
        m_ref = re.search(r"\[.*?\bref=([a-zA-Z0-9_-]+).*?\]", line)
        if not m_ref:
            continue
        ref = f"@{m_ref.group(1)}"

        # Extract role: e.g. "- button 'Log in' ..."
        m_role = re.search(r"^\s*-\s*([a-zA-Z0-9_-]+)", line)
        role = m_role.group(1).lower() if m_role else "element"

        # Extract accessible label skipping class=, id=, role=
        m_aria = re.search(r'\baria-label=["\']([^"\']+)["\']', line)
        m_name = re.search(r'\bname=["\']([^"\']+)["\']', line)
        if m_aria:
            label = m_aria.group(1).strip()
        elif m_name:
            label = m_name.group(1).strip()
        else:
            line_no_attrs = re.sub(r'\b(class|id|role|ref)=["\'][^"\']*["\']', '', line)
            line_no_attrs = re.sub(r'\[ref=[^\]]*\]', '', line_no_attrs)
            rem_quotes = re.findall(r'["\']([^"\']+)["\']', line_no_attrs)
            if rem_quotes:
                label = rem_quotes[0].strip()
            else:
                before_ref = line.split("[ref=")[0].strip("- ").strip()
                parts = before_ref.split(maxsplit=1)
                label = parts[1].strip() if len(parts) > 1 else before_ref

        label_lower = label.lower()
        if not label_lower:
            continue

        # Exact match (case-insensitive)
        if tgt_lower == label_lower:
            candidates.append((100, ref, label, role))
        # Word boundary match
        elif re.search(rf"\b{re.escape(tgt_lower)}\b", label_lower):
            candidates.append((80, ref, label, role))
        # Substring match if target is at least 3 characters
        elif len(tgt_lower) >= 3 and tgt_lower in label_lower:
            candidates.append((50, ref, label, role))

    if candidates:
        def _sort_key(c):
            score, _, _, r = c
            bonus = 10 if r in ("button", "link", "combobox", "textbox", "searchbox", "menuitem") else 0
            return score + bonus

        candidates.sort(key=_sort_key, reverse=True)
        best = candidates[0]
        return (best[1], best[2], best[3])

    return None


def _find_ref_by_text(snapshot_text: str, target_text: str) -> Optional[str]:
    """Search snapshot lines for an interactive element whose text matches target_text."""
    info = _find_element_info(snapshot_text, target_text)
    return info[0] if info else None


def _act_locate(params: dict) -> str:
    """Locate an element on the page using fast DOM evaluation (<150ms)."""
    target = (params.get("selector") or params.get("ref") or params.get("text") or params.get("query") or "").strip()
    if not target:
        return "Missing selector, ref, or text to locate."

    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            hwnd = _resolve_desktop_browser_hwnd()
            if hwnd:
                try:
                    from core.computer import windows_uia
                    tabs = windows_uia.get_browser_tabs(hwnd)
                    for t in tabs:
                        if target.lower() in t.get("title", "").lower():
                            return f"Located tab '{t['title']}' on desktop browser."
                except Exception:
                    pass
            return f"Refused: {ident_err}"

    # Normalize ref format
    if target.startswith("e") and target[1:].isdigit():
        target = f"@{target}"

    js_query = f"""
    (() => {{
        const target = {json.dumps(target.lower())};
        const selector = 'a, button, input, select, textarea, [role], [tabindex], h1, h2, h3, p, span';
        const els = Array.from(document.querySelectorAll(selector));
        const matches = [];
        for (const el of els) {{
            const aria = el.getAttribute('aria-label') || '';
            const name = el.getAttribute('name') || '';
            const text = (el.innerText || el.textContent || '').trim();
            const label = aria || name || text;
            if (label.toLowerCase().includes(target)) {{
                const rect = el.getBoundingClientRect();
                const role = el.getAttribute('role') || el.tagName.toLowerCase();
                matches.push({{
                    role: role,
                    label: label.slice(0, 80),
                    x: Math.round(rect.left + rect.width / 2),
                    y: Math.round(rect.top + rect.height / 2)
                }});
                if (matches.length >= 3) break;
            }}
        }}
        return JSON.stringify(matches);
    }})()
    """.strip().replace('\n', ' ')

    code, out = _exec_ab_argv(["eval", json.dumps(js_query)])
    if code == 0:
        clean = out.strip().strip('"').replace('\\"', '"')
        try:
            items = json.loads(clean)
            if items:
                best = items[0]
                return f"Located {best.get('role', 'element')} '{best.get('label')}' at ({best.get('x')}, {best.get('y')}) on the page without clicking."
        except Exception:
            pass

    return f"I couldn't find an element matching '{target}' on the page."


def _act_click(params: dict) -> str:
    target = (params.get("selector") or params.get("ref") or params.get("text") or "").strip()
    if not target:
        return "Missing selector or ref for click action."

    if not _is_isolated(params):
        ident_err = _identity_gate(params)
        if ident_err or _use_desktop_path(params):
            desktop = _click_desktop(params, target)
            if desktop:
                return desktop
            if ident_err:
                return f"Refused: {ident_err}"

    # Normalize ref format (e.g. e14 -> @e14)
    if target.startswith("e") and target[1:].isdigit():
        target = f"@{target}"

    # If target is plain descriptive text rather than a selector/ref, resolve via snapshot ref
    if not target.startswith(("@", "#", ".")) and "[" not in target:
        snap_code, snap_out = _exec_ab("snapshot -i")
        if snap_code == 0:
            matched_ref = _find_ref_by_text(snap_out, target)
            if matched_ref:
                code, out = _exec_ab(f"click {matched_ref}")
                if code == 0:
                    return f"Clicked '{target}' ({matched_ref})."
                return f"Failed to click '{target}' ({matched_ref}): {out.strip()}"

            # Check if a cookie banner or modal overlay is blocking and dismiss it
            dismissed, d_msg = _try_dismiss_banners(snap_out, isolated=_is_isolated(params))
            if dismissed:
                time.sleep(0.4)
                snap_code, snap_out = _exec_ab("snapshot -i")
                if snap_code == 0:
                    matched_ref = _find_ref_by_text(snap_out, target)
                    if matched_ref:
                        code, out = _exec_ab(f"click {matched_ref}")
                        if code == 0:
                            return f"Clicked '{target}' ({matched_ref}) after dismissing banner."
                        return f"Failed to click '{target}' ({matched_ref}): {out.strip()}"

            return f"I couldn't find a button or element matching '{target}'. I did not click anything."

    tgt_arg = target if target.startswith("@") or " " not in target else f'"{target}"'
    code, out = _exec_ab(f"click {tgt_arg}")
    if code == 0:
        return f"Clicked element {target}."

    # Auto-recovery if ref is unknown or stale (e.g. dynamic DOM change)
    if "Unknown ref:" in out or "not found" in out.lower() or "error" in out.lower() or "✗" in out:
        snap_code, snap_out = _exec_ab("snapshot -i")
        if snap_code == 0:
            matched_ref = _find_ref_by_text(snap_out, target)
            if matched_ref:
                retry_code, retry_out = _exec_ab(f"click {matched_ref}")
                if retry_code == 0:
                    return f"Clicked '{target}' ({matched_ref})."
        return f"Failed to click '{target}': element not found or not clickable on page ({out.strip()})."

    return f"Failed to click {target}: {out.strip()}"


def _act_type(params: dict) -> str:
    if params.get("url"):
        is_safe, err_msg = _safe_url(params["url"])
        if not is_safe:
            return f"Validation error: {err_msg}"

    target = (params.get("selector") or params.get("ref") or params.get("description") or "").strip()
    text = params.get("text") or params.get("query") or ""
    if not text:
        return "No text provided to type."

    if text.startswith(("http://", "https://")):
        is_safe, err_msg = _safe_url(text)
        if not is_safe:
            return f"Validation error: {err_msg}"

    is_isolated = _is_isolated(params)
    if not is_isolated:
        ident_err = _verify_session_identity()
        if ident_err:
            if input_driver and _focus_desktop_browser():
                time.sleep(0.08)
                input_driver.type_safe_unicode(text)
                if params.get("enter") or params.get("press_enter"):
                    time.sleep(0.05)
                    input_driver.press("enter")
                return f"Typed '{text}' into Chrome (desktop fallback)."
            return f"Refused: {ident_err}"

    if not target:
        code, out = _exec_ab_argv(["keyboard", "type", text])
        if code == 0:
            return f"Typed '{text}' into focused element."
        return f"Failed to type '{text}': {out.strip()}"

    if target.startswith("e") and target[1:].isdigit():
        target = f"@{target}"

    if not target.startswith(("@", "#", ".")) and "[" not in target:
        snap_code, snap_out = _exec_ab("snapshot -i")
        if snap_code == 0:
            matched_ref = _find_ref_by_text(snap_out, target)
            if matched_ref:
                target = matched_ref

    code, out = _exec_ab_argv(["fill", target, text])
    if code == 0:
        return f"Typed '{text}' into {target}."

    if "Unknown ref:" in out or "not found" in out.lower() or "✗" in out:
        snap_code, snap_out = _exec_ab("snapshot -i")
        if snap_code == 0:
            matched_ref = _find_ref_by_text(snap_out, target)
            if matched_ref:
                retry_code, retry_out = _exec_ab_argv(["fill", matched_ref, text])
                if retry_code == 0:
                    return f"Typed '{text}' into {target} ({matched_ref})."

    return f"Failed to type into {target}: {out.strip()}"


def _act_fill_form(params: dict) -> str:
    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            return f"Refused: {ident_err}"

    if params.get("url"):
        is_safe, err_msg = _safe_url(params["url"])
        if not is_safe:
            return f"Validation error: {err_msg}"

    fields = params.get("fields", {})
    if not fields or not isinstance(fields, dict):
        return "Missing or invalid 'fields' dictionary for fill_form."

    for val in fields.values():
        val_str = str(val).strip()
        if val_str.startswith(("http://", "https://")):
            is_safe, err_msg = _safe_url(val_str)
            if not is_safe:
                return f"Validation error: {err_msg}"

    results = []
    for sel, val in fields.items():
        ref = f"@{sel}" if sel.startswith("e") and sel[1:].isdigit() else sel
        code, out = _exec_ab_argv(["fill", ref, str(val)])
        if code == 0:
            results.append(f"Filled {ref}")
        else:
            results.append(f"Error {ref}: {out}")
    return "; ".join(results)


def _parse_eval_json(out: str) -> Optional[dict]:
    """
    Parse an agent-browser eval reply into the dict the injected JS returned.

    The CLI JSON-encodes the JS return value, so a `JSON.stringify({...})` payload comes
    back double-encoded ("{\\"moved\\": 472, \\"pct\\": 3}") — decode twice, not once.
    """
    text = out.strip()
    for _ in range(2):
        try:
            value = json.loads(text)
        except Exception:
            break
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            break
        text = value
    try:
        value = json.loads(text.strip('"').strip("'").replace('\\"', '"'))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _act_scroll(params: dict) -> str:
    raw_dir = str(params.get("direction") or "down").lower().strip()
    if raw_dir in ("bottom", "page_bottom", "end", "down_all", "scroll_bottom"):
        mode = "bottom"
    elif raw_dir in ("top", "page_top", "up_all", "scroll_top", "home"):
        mode = "top"
    elif raw_dir == "up":
        mode = "up"
    else:
        mode = "down"

    is_isolated = _is_isolated(params)

    if not is_isolated:
        # Step 2 + Step 4: identical routing/gate to the other desktop handlers.
        ident_err = _identity_gate(params)
        if ident_err:
            return f"Refused: {ident_err}"

        if _use_desktop_path(params):
            if input_driver and _focus_desktop_browser():
                time.sleep(0.01)
                if mode == "bottom":
                    input_driver.press("end")
                    return "Scrolled to the bottom of the page in Chrome (desktop fallback)."
                if mode == "top":
                    input_driver.press("home")
                    return "Scrolled to the top of the page in Chrome (desktop fallback)."
                if mode == "up":
                    input_driver.press("pageup")
                    return "Scrolled up in Chrome (desktop fallback)."
                input_driver.press("pagedown")
                return "Scrolled down in Chrome (desktop fallback)."
            return "Unable to scroll (no CDP session is attached and no desktop browser is focusable)."

    amount = int(params.get("amount", 0))

    js_scroll = (
        "(() => {"
        "if (document.activeElement && document.activeElement.blur) document.activeElement.blur();"
        "const el = document.scrollingElement || document.documentElement || document.body;"
        "const oldTop = el.scrollTop;"
        "const maxScroll = Math.max(0, el.scrollHeight - el.clientHeight);"
        f"let delta = {amount};"
        "if (delta <= 0) delta = Math.round(window.innerHeight * 0.8);"
        f"let targetTop = oldTop;"
        f"const mode = '{mode}';"
        "if (mode === 'top') targetTop = 0;"
        "else if (mode === 'bottom') targetTop = maxScroll;"
        "else if (mode === 'up') targetTop = Math.max(0, oldTop - delta);"
        "else targetTop = Math.min(maxScroll, oldTop + delta);"
        "el.scrollTo({top: targetTop, behavior: 'instant'});"
        "const newTop = el.scrollTop;"
        "const moved = Math.abs(newTop - oldTop);"
        "const pct = maxScroll > 0 ? Math.round((newTop / maxScroll) * 100) : 0;"
        "return JSON.stringify({moved: moved, pct: pct});"
        "})()"
    )

    code, out = _exec_ab_argv(["eval", js_scroll])
    if code != 0:
        return f"Failed to scroll: {out}"

    data = _parse_eval_json(out)
    if data is not None:
        moved = int(data.get("moved", 0))
        pct = int(data.get("pct", 0))
    else:
        m_moved = re.search(r'moved\\?":\s*(\d+)', out)
        m_pct = re.search(r'pct\\?":\s*(\d+)', out)
        moved = int(m_moved.group(1)) if m_moved else 1
        pct = int(m_pct.group(1)) if m_pct else 0

    _ACTION_STATE.scroll = pct  # Step 4: the scroll JSON we already parsed

    if moved == 0:
        if mode in ("top", "up"):
            return "Already at the top (or this page scrolls inside a panel). Nothing moved."
        if mode in ("bottom", "down"):
            return "Already at the bottom (or this page scrolls inside a panel). Nothing moved."
        return "Already at the target position (or this page scrolls inside a panel). Nothing moved."

    return f"Scrolled {mode}. Now {pct}% down the page."


def _act_press(params: dict) -> str:
    key = str(params.get("key", "Enter")).lower().strip()
    is_isolated = _is_isolated(params)

    if not is_isolated:
        ident_err = _identity_gate(params)
        if ident_err or _use_desktop_path(params):
            if input_driver and _focus_desktop_browser():
                time.sleep(0.04)
                input_driver.press(key)
                return f"Pressed {key} in Chrome (desktop fallback)."
            if ident_err:
                return f"Refused: {ident_err}"

    code, out = _exec_ab(f"press {params.get('key', 'Enter')}")
    if code == 0:
        return f"Pressed {params.get('key', 'Enter')}."
    return f"Failed to press {params.get('key', 'Enter')}: {out}"


def _act_screenshot(params: dict) -> str:
    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            return f"Refused: {ident_err}"

    if params.get("url"):
        is_safe, err_msg = _safe_url(params["url"])
        if not is_safe:
            return f"Validation error: {err_msg}"

    path = params.get("path") or ""
    annotate = "--annotate" if params.get("annotate") else ""
    cmd = f"screenshot {path} {annotate}".strip()
    code, out = _exec_ab(cmd)
    if code == 0:
        return f"Captured screenshot{': ' + path if path else ''}."
    return f"Failed to capture screenshot: {out}"


def _act_new_tab(params: dict) -> str:
    url = (params.get("url") or "").strip()
    norm_url = _normalize_url(url) if url else "about:blank"
    _ACTION_STATE.url = norm_url if url else ""  # Step 4: free state for the suffix

    if url:
        is_safe, err_msg = _safe_url(norm_url)
        if not is_safe:
            return f"Validation error: {err_msg}"

    is_isolated = _is_isolated(params)
    session_active = _is_browser_session_active()
    if not is_isolated and _use_desktop_path(params):
        # Step 2 route gate, applied to new_tab (Step 4 needs its mutating result):
        # with no CDP session a desktop request must not drive the daemon — it is
        # blocked at the _exec_ab choke point — so use the desktop fallback.
        session_active = False

    if not is_isolated:
        if isinstance(session_active, str) or not session_active:
            if input_driver and _focus_desktop_browser():
                time.sleep(0.08)
                input_driver.hotkey("ctrl", "t")
                if url:
                    time.sleep(0.1)
                    input_driver.type_safe_unicode(norm_url)
                    time.sleep(0.05)
                    input_driver.press("enter")
                    _reset_snapshot()
                    return f"Opened new tab: {norm_url} in Chrome (desktop fallback)."
                _reset_snapshot()
                return "Opened new tab in Chrome (desktop fallback)."
            if isinstance(session_active, str):
                return f"Refused: {session_active}"
            _open_os_url(norm_url)
            _reset_snapshot()
            return f"Opened Chrome with {norm_url}."

    if is_isolated or (session_active and not isinstance(session_active, str)):
        code, out = _exec_ab_argv(
            ["tab", "new", *([norm_url] if norm_url != "about:blank" else [])]
        )
        if code == 0:
            _reset_snapshot()
            return f"Opened new tab{': ' + norm_url if norm_url != 'about:blank' else ''} in Chrome."
        return f"Failed to open new tab: {out.strip()}"

    return "No active browser session to open new tab."


def _act_close_tab(params: dict) -> str:
    is_isolated = _is_isolated(params)
    target = params.get("index") or params.get("target") or params.get("title") or ""
    target_str = str(target).strip()

    session_active = _is_browser_session_active()
    if not is_isolated and _use_desktop_path(params):
        # Step 2 route gate, applied to close_tab (Step 4 needs its mutating result):
        # no CDP session -> close on the desktop instead of a blocked NO_CDP daemon call.
        session_active = False

    if not is_isolated and (isinstance(session_active, str) or not session_active):
        if input_driver and _focus_desktop_browser():
            time.sleep(0.08)
            input_driver.hotkey("ctrl", "w")
            return "Closed active tab in Chrome (desktop fallback)."
        if isinstance(session_active, str):
            return f"Refused: {session_active}"
        return "No active desktop browser found to close tab."

    if is_isolated or (session_active and not isinstance(session_active, str)):
        if target_str and not (target_str.startswith("t") and target_str[1:].isdigit()) and not target_str.isdigit():
            code, out = _exec_ab("tab list")
            if code == 0:
                lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("[agent-browser]")]
                _ACTION_STATE.tabs = len(lines)  # Step 4: tab list we already fetched
                for line in lines:
                    if target_str.lower() in line.lower():
                        m = re.search(r"\[([a-zA-Z0-9_-]+)\]", line)
                        if m:
                            target_str = m.group(1)
                            break

        cmd = f"tab close {target_str}".strip() if target_str else "tab close"
        code, out = _exec_ab(cmd)
        if code == 0:
            return f"Closed tab{f' {target_str}' if target_str else ''} in Chrome."
        return f"Failed to close tab: {out.strip()}"

    return "No active browser found to close tab."


def _tab_nav_desktop(params: dict, action: str) -> str:
    """Desktop tab navigation: name-based via UIA, position-based via native shortcuts."""
    _focus_desktop_browser()
    time.sleep(0.06)
    target = params.get("target") or params.get("index") or params.get("tab")
    t_str = str(target).strip() if target is not None else ""
    hwnd = _resolve_desktop_browser_hwnd()

    # Named tab (e.g. target="NotebookLM") resolved against the REAL open tabs.
    if t_str and not t_str.isdigit():
        if _uia_switch_tab(hwnd, t_str):
            return f"Switched to tab '{t_str}' in Chrome."
        _focus_desktop_browser()
        if input_driver:
            input_driver.hotkey("ctrl", "tab")
        return f"No tab matched '{t_str}'; switched to the next tab in Chrome."

    # last / first resolved exactly via UIA before falling back to native shortcuts.
    if action in ("last", "last_tab", "first", "first_tab"):
        tabs = _uia_browser_tabs(hwnd)
        if tabs:
            _ACTION_STATE.tabs = len(tabs)  # Step 4: tab list we already enumerated
            pick = tabs[-1] if action in ("last", "last_tab") else tabs[0]
            if _uia_switch_tab(hwnd, pick["title"]):
                return f"Switched to tab '{pick['title']}' in Chrome."

    _focus_desktop_browser()
    time.sleep(0.04)
    if input_driver:
        if t_str.isdigit() and 1 <= int(t_str) <= 8:
            input_driver.hotkey("ctrl", t_str)
            return f"Switched to tab {t_str} in Chrome."
        if action in ("last", "last_tab") or t_str in ("9", "last"):
            input_driver.hotkey("ctrl", "9")
            return "Switched to last tab in Chrome."
        if action in ("first", "first_tab"):
            input_driver.hotkey("ctrl", "1")
            return "Switched to first tab in Chrome."
        if "prev" in action:
            input_driver.hotkey("ctrl", "shift", "tab")
            return "Switched to previous tab in Chrome."
        input_driver.hotkey("ctrl", "tab")
        return "Switched to next tab in Chrome."
    return "Desktop input driver unavailable."


def _tab_nav_daemon(params: dict, action: str) -> str:
    """Tab navigation for agent-browser daemon sessions."""
    target = params.get("target") or params.get("index") or params.get("tab")
    t_str = str(target).strip() if target is not None else ""

    code, out = _exec_ab("tab list")
    if code != 0:
        return f"Could not list tabs: {out.strip()}"

    lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("[agent-browser]")]
    if not lines:
        return "No active tabs found in Chrome."

    tab_map = []
    for i, line in enumerate(lines):
        m = re.search(r"\[([a-zA-Z0-9_-]+)\]", line)
        tab_id = m.group(1) if m else str(i)
        is_active = line.startswith("→") or line.startswith("*")
        content = re.sub(r"^[→* ]*\[[a-zA-Z0-9_-]+\]\s*", "", line).strip()
        tab_map.append((tab_id, content, is_active))

    _ACTION_STATE.tabs = len(tab_map)  # Step 4: tab list we already fetched

    if t_str and action not in ("prev", "next", "last", "first"):
        # Match by direct tab ID (e.g. t1, 0, 1)
        direct_match = next((t[0] for t in tab_map if t[0].lower() == t_str.lower()), None)
        if direct_match:
            code_sw, out_sw = _exec_ab(f"tab {direct_match}")
            if code_sw == 0:
                return f"Switched to tab {direct_match} in Chrome."
            return f"Failed to switch to tab {direct_match}: {out_sw.strip()}"

        # Match by title or url text (e.g. "spotify", "youtube")
        name_match = next((t for t in tab_map if t_str.lower() in t[1].lower()), None)
        if name_match:
            code_sw, out_sw = _exec_ab(f"tab {name_match[0]}")
            if code_sw == 0:
                short_title = name_match[1].split(" - ")[0]
                return f"Switched to tab '{short_title}' ({name_match[0]}) in Chrome."
            return f"Failed to switch to tab '{t_str}': {out_sw.strip()}"

        return f"No tab matched '{t_str}' in Chrome."

    # Index or relative position
    active_idx = next((i for i, t in enumerate(tab_map) if t[2]), 0)
    if action in ("last", "last_tab"):
        target_tab = tab_map[-1]
        label = "last"
    elif action in ("first", "first_tab"):
        target_tab = tab_map[0]
        label = "first"
    elif "prev" in action:
        target_tab = tab_map[(active_idx - 1) % len(tab_map)]
        label = "previous"
    else:
        target_tab = tab_map[(active_idx + 1) % len(tab_map)]
        label = "next"

    code_sw, out_sw = _exec_ab(f"tab {target_tab[0]}")
    if code_sw == 0:
        return f"Switched to {label} tab ({target_tab[0]}) in Chrome."
    return f"Failed to switch tab: {out_sw.strip()}"


def _act_tab_nav(params: dict, action: str) -> str:
    if not _is_isolated(params) and input_driver and _resolve_desktop_browser_hwnd():
        return _tab_nav_desktop(params, action)
    return _tab_nav_daemon(params, action)


def _act_list_tabs(params: dict) -> str:
    # Desktop-first: read the REAL tabs of the user's live browser via UIA
    if not _is_isolated(params):
        tabs = _uia_browser_tabs(_resolve_desktop_browser_hwnd())
        if tabs:
            return _format_real_tab_list(tabs)

    active = _is_browser_session_active()
    if (active and not isinstance(active, str)) or _is_isolated(params):
        code, out = _exec_ab("tab list")
        if code == 0:
            lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("[agent-browser]")]
            if lines:
                return f"There are {len(lines)} tabs open in Chrome:\n" + "\n".join(lines)

    return "Unable to list open tabs."


def _act_get_title(params: dict) -> str:
    """Get the current page title using fast DOM evaluation."""
    if not _is_isolated(params):
        ident_err = _identity_gate(params)
        if ident_err or _use_desktop_path(params):
            hwnd = _resolve_desktop_browser_hwnd()
            if hwnd and windows_native:
                title = windows_native.get_window_title(hwnd)
                if title:
                    clean = re.sub(r' - (Google Chrome|Microsoft Edge|Brave|Mozilla Firefox|Firefox).*$', '', title, flags=re.I).strip()
                    return f"Page title: {clean} (desktop)"
            if ident_err:
                return f"Refused: {ident_err}"

    code, out = _exec_ab("eval document.title")
    if code == 0:
        clean = out.strip().strip('"').strip("'").strip()
        return f"Page title: {clean}"
    return f"Failed to get page title: {out.strip()}"


def _act_verify_page(params: dict) -> str:
    """Verify that the current page matches the expected title, URL hostname, or content."""
    expected_url = (params.get("url") or params.get("expected_url") or "").strip()
    expected_title = (params.get("title") or params.get("expected_title") or "").strip().lower()

    if not _is_isolated(params):
        ident_err = _identity_gate(params)
        if ident_err or _use_desktop_path(params):
            hwnd = _resolve_desktop_browser_hwnd()
            if hwnd and windows_native:
                title = windows_native.get_window_title(hwnd)
                if expected_title and expected_title in title.lower():
                    return f"Page verified successfully: '{title}' (desktop)"
            if ident_err:
                return f"Refused: {ident_err}"

    code_u, out_u = _exec_ab("eval window.location.href")
    code_t, out_t = _exec_ab("eval document.title")

    current_url = out_u.strip().strip('"').strip("'").strip() if code_u == 0 else ""
    current_title = out_t.strip().strip('"').strip("'").strip() if code_t == 0 else ""

    failures = []
    if expected_url:
        exp_parsed = urllib.parse.urlparse(expected_url if "://" in expected_url else f"https://{expected_url}")
        cur_parsed = urllib.parse.urlparse(current_url)
        exp_host = (exp_parsed.hostname or "").lower()
        cur_host = (cur_parsed.hostname or "").lower()
        if not cur_host or not (cur_host == exp_host or cur_host.endswith("." + exp_host)):
            failures.append(f"URL hostname mismatch: expected '{exp_host}' but found '{cur_host}' (full: {current_url})")

    if expected_title and expected_title not in current_title.lower():
        failures.append(f"Title mismatch: expected '{expected_title}' but found '{current_title}'")

    if failures:
        return f"Page verification failed: {'; '.join(failures)} (Current: '{current_title}' - {current_url})"

    return f"Page verified successfully: '{current_title}' ({current_url})"


def _read_desktop_url(settle: float = 0.05) -> Optional[str]:
    """
    Read the focused desktop Chrome omnibox via the clipboard (desktop path only).

    Writes the original clipboard back with _restore_clipboard() — never
    input_driver.set_clipboard(), which would paste it into the page.
    """
    if not input_driver or not hasattr(input_driver, "get_clipboard"):
        return None
    if not _focus_desktop_browser():
        return None
    orig_clip = None
    try:
        orig_clip = input_driver.get_clipboard()
        time.sleep(settle)
        input_driver.hotkey("ctrl", "l")
        time.sleep(settle)
        input_driver.hotkey("ctrl", "c")
        time.sleep(settle)
        input_driver.press("escape")
        url = (input_driver.get_clipboard() or "").strip()
        if url and ("http://" in url or "https://" in url or "www." in url or "chrome://" in url):
            return url
    except Exception:
        return None
    finally:
        if orig_clip is not None:
            _restore_clipboard(orig_clip)
    return None


def _act_get_url(params: dict) -> str:
    is_isolated = _is_isolated(params)
    if not is_isolated:
        # Step 2d: refuse ONLY when a live CDP session is bound to a different browser.
        ident_err = _identity_gate(params)
        if ident_err:
            return f"Refused: {ident_err}"

        # Step 2b: no CDP session -> clipboard read only, never the daemon.
        if _use_desktop_path(params):
            url = _read_desktop_url(settle=0.02)
            if url:
                return f"Current URL: {url}"
            return "Unable to read the current URL (no CDP session is attached)."

    active = _is_browser_session_active()
    if (active and not isinstance(active, str)) or is_isolated:
        code, out = _exec_ab("get url")
        if code == 0:
            clean = "\n".join(line for line in out.splitlines() if not line.startswith("[agent-browser]")).strip()
            if clean and "about:blank" not in clean:
                return f"Current URL: {clean}"
        code_e, out_e = _exec_ab("eval window.location.href")
        if code_e == 0:
            clean = out_e.strip().strip('"').strip("'").strip()
            if clean:
                return f"Current URL: {clean}"

    if not is_isolated and input_driver:
        url = _read_desktop_url(settle=0.08)
        if url:
            return f"Current URL: {url}"

    code, out = _exec_ab("get url")
    if code == 0:
        clean = "\n".join(line for line in out.splitlines() if not line.startswith("[agent-browser]")).strip()
        return f"Current URL: {clean}"
    return f"Failed to get URL: {out}"


def _act_get_text(params: dict) -> str:
    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            return f"Refused: {ident_err}"

    target = params.get("selector") or params.get("ref") or ""
    if target.startswith("e") and target[1:].isdigit():
        target = f"@{target}"
    cmd = f"get text '{target}'" if target else "get text body"
    code, out = _exec_ab(cmd)
    if code == 0:
        clean = "\n".join(line for line in out.splitlines() if not line.startswith("[agent-browser]")).strip()
        return clean or "No text content found."
    return f"Failed to get text: {out}"


def _act_nav_history(action: str, params: Optional[dict] = None) -> str:
    p = params or {}
    if not _is_isolated(p):
        ident_err = _verify_session_identity()
        if ident_err:
            if input_driver and _focus_desktop_browser():
                time.sleep(0.05)
                if action in ("reload", "refresh"):
                    input_driver.hotkey("ctrl", "r")
                    _reset_snapshot()
                    return "Reloaded page in Chrome (desktop fallback)."
                elif action == "back":
                    input_driver.hotkey("alt", "left")
                    _reset_snapshot()
                    return "Navigated back in Chrome (desktop fallback)."
                elif action == "forward":
                    input_driver.hotkey("alt", "right")
                    _reset_snapshot()
                    return "Navigated forward in Chrome (desktop fallback)."
            return f"Refused: {ident_err}"

    code, out = _exec_ab(action)
    if code == 0:
        _reset_snapshot()
        return f"Page {action} complete."
    return f"Failed to {action}: {out}"


def _act_close(params: dict) -> str:
    if not _is_isolated(params):
        ident_err = _verify_session_identity()
        if ident_err:
            return f"Refused: {ident_err}"

    code, out = _exec_ab("close")
    if code == 0:
        return "Closed browser session."
    return f"Failed to close browser: {out}"


# ── Action Dispatch Router (Cyclomatic Complexity < 15) ─────────────────────

_ACTION_DISPATCH = {
    "go_to": _act_go_to,
    "open": _act_go_to,
    "search": _act_search,
    "snapshot": _act_snapshot,
    "get_accessibility_snapshot": _act_snapshot,
    "accessibility_snapshot": _act_snapshot,
    "a11y_tree": _act_snapshot,
    "locate": _act_locate,
    "find": _act_locate,
    "find_element": _act_locate,
    "click": _act_click,
    "smart_click": _act_click,
    "type": _act_type,
    "smart_type": _act_type,
    "fill": _act_type,
    "fill_form": _act_fill_form,
    "scroll": _act_scroll,
    "scroll_bottom": lambda p: _act_scroll({**p, "direction": "bottom"}),
    "scroll_top": lambda p: _act_scroll({**p, "direction": "top"}),
    "bottom": lambda p: _act_scroll({**p, "direction": "bottom"}),
    "top": lambda p: _act_scroll({**p, "direction": "top"}),
    "press": _act_press,
    "screenshot": _act_screenshot,
    "new_tab": _act_new_tab,
    "close_tab": _act_close_tab,
    "close_tab_by_title": _act_close_tab,
    "list_tabs": _act_list_tabs,
    "tabs": _act_list_tabs,
    "tab_list": _act_list_tabs,
    "get_tabs": _act_list_tabs,
    "open_tabs": _act_list_tabs,
    "prev_tab": lambda p: _act_tab_nav(p, "prev"),
    "previous_tab": lambda p: _act_tab_nav(p, "prev"),
    "next_tab": lambda p: _act_tab_nav(p, "next"),
    "last_tab": lambda p: _act_tab_nav(p, "last"),
    "first_tab": lambda p: _act_tab_nav(p, "first"),
    "switch_tab": lambda p: _act_tab_nav(p, "switch"),
    "tab": lambda p: _act_tab_nav(p, "switch"),
    "select_tab": lambda p: _act_tab_nav(p, "switch"),
    "back": lambda p: _act_nav_history("back", p),
    "forward": lambda p: _act_nav_history("forward", p),
    "reload": lambda p: _act_nav_history("reload", p),
    "refresh": lambda p: _act_nav_history("reload", p),
    "get_url": _act_get_url,
    "get_title": _act_get_title,
    "title": _act_get_title,
    "page_title": _act_get_title,
    "verify": _act_verify_page,
    "verify_page": _act_verify_page,
    "get_text": _act_get_text,
    "close": _act_close,
    "close_all": _act_close,
    "list_browsers": lambda p: "agent-browser (active native Rust daemon with CDP)",
}


def browser_control(
    parameters: dict,
    player=None,
    speak=None,
    response=None,
    session_memory=None,
) -> str:
    """Primary handler invoked by core/action_loader.py."""
    params = parameters or {}
    raw_action = params.get("action") or "snapshot"
    action = re.sub(r'(?<!^)(?=[A-Z])', '_', str(raw_action)).lower().strip()

    # Step 2c: publish this request's isolation mode for the _exec_ab choke point.
    _req_ctx.isolated = _is_isolated(params)

    # Step 4: clear the free state this action may publish for the result suffix.
    if action in _STATE_ACTIONS:
        _reset_action_state()

    cache_key = f"{action}:{json.dumps(params, sort_keys=True, default=str)}"
    ttl = _ACTION_TTL.get(action)

    with _BROWSER_LOCK:
        now = time.time()
        if ttl is not None and cache_key in _recent:
            prev_time, prev_result = _recent[cache_key]
            elapsed = now - prev_time
            if elapsed < ttl:
                cached_msg = f"{prev_result} [already done {elapsed:.1f}s ago, do not repeat]"
                _log(player, cached_msg)
                return cached_msg

        handler = _ACTION_DISPATCH.get(action)
        if not handler:
            result = f"Unknown browser action: '{action}'"
        else:
            try:
                result = handler(params)
            except Exception as e:
                result = f"Browser execution error ({action}): {e}"

        # Step 4: append the free state suffix to every mutating result (never to a
        # validation error / refusal / failure, which did not mutate anything).
        if action in _STATE_ACTIONS and not result.startswith(
            ("Validation error", "Refused", "Failed", "No ", "Unknown browser action",
             "Browser execution error", "Unable to ", "I couldn't")
        ):
            result += _state_suffix()

        if ttl is not None:
            is_failure = (
                result.startswith("Failed")
                or result.startswith("Validation error")
                or result.startswith("Refused")
                or result.startswith("I couldn't")
                or "execution error" in result.lower()
            )
            if not is_failure:
                _recent[cache_key] = (now, result)

        _log(player, result)
        return result


def _log(player, text: str):
    short = str(text)[:80]
    safe_short = short.encode("ascii", errors="replace").decode("ascii")
    if ZEZO_PROFILE:
        print(f"[Browser:agent-browser] {safe_short}")
    if player and hasattr(player, "write_log"):
        player.write_log(f"[browser] {short[:60]}")


# ── Tool Declaration (Auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "browser_control",
    "description": (
        "Controls web browsers on the desktop using high-speed native agent-browser (Rust CDP). "
        "Use ONLY when the user explicitly asks to open a website, preview a webpage, click elements, "
        "fill forms, scroll, list/switch tabs, or interact with a desktop browser. "
        "Ref-based interaction (@e1, @e2) is supported: call 'snapshot' to get interactive elements with refs, "
        "then call 'click' or 'type' with the ref. Pass headed=True to show the browser window on desktop. "
        "action='list_tabs' returns the REAL tabs open in the user's live desktop Chrome (via Windows UI Automation), "
        "and 'switch_tab' with target='<tab title>' switches straight to a tab by name. "
        "NEVER use for silent background web searches — use web_search instead."
    ),
    "risk": "local_mutation",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "go_to | search | click | type | locate | get_title | verify_page | scroll | scroll_top | scroll_bottom | fill_form | snapshot | "
                    "get_text | get_url | press | new_tab | close_tab | list_tabs | prev_tab | next_tab | last_tab | first_tab | "
                    "screenshot | back | forward | reload | close | close_all"
                ),
            },
            "url": {
                "type": "STRING",
                "description": "URL for go_to or new_tab action",
            },
            "query": {
                "type": "STRING",
                "description": "Search query for search action",
            },
            "engine": {
                "type": "STRING",
                "description": "Search engine: google | bing | duckduckgo | yandex (default: google)",
            },
            "selector": {
                "type": "STRING",
                "description": "Element ref (e.g. '@e1', '@e2') or CSS selector for click/type",
            },
            "text": {
                "type": "STRING",
                "description": "Text to click, type, or fill into input field",
            },
            "direction": {
                "type": "STRING",
                "description": "up | down for scroll (default: down)",
            },
            "amount": {
                "type": "INTEGER",
                "description": "Scroll amount in pixels (default: 500)",
            },
            "key": {
                "type": "STRING",
                "description": "Key name for press action (e.g. Enter, Escape, Tab)",
            },
            "path": {
                "type": "STRING",
                "description": "Save path for screenshot",
            },
            "headed": {
                "type": "BOOLEAN",
                "description": "Set to true to show Chrome window visibly on user's desktop",
            },
            "annotate": {
                "type": "BOOLEAN",
                "description": "Annotate screenshot with numbered visual labels",
            },
            "desktop_only": {
                "type": "BOOLEAN",
                "description": "Force execution using desktop keyboard/window automation (Ctrl+L, Ctrl+T, Ctrl+W)",
            },
            "fields": {
                "type": "OBJECT",
                "description": "Key-value dictionary of selectors/refs to values for fill_form",
            },
        },
        "required": ["action"],
    },
    "handler": browser_control,
}
