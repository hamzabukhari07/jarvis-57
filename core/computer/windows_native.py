"""
core/computer/windows_native.py - Win32 OS Native Driver for ZEZO OS
Handles window enumeration, focus attachment, process telemetry, and safe window lifecycle.
Creator: Hamza Bukhari
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

_PSUTIL = False
try:
    import psutil
    _PSUTIL = True
except ImportError:
    pass

# Debug/profiling output is opt-in. With ZEZO_PROFILE unset nothing prints.
ZEZO_PROFILE = os.environ.get("ZEZO_PROFILE") == "1"

# Win32 Constants
SW_RESTORE = 9
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_SHOW = 5
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
IDCANCEL = 2
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# ctypes.wintypes has no MONITORINFO, so it is defined here. rcWork is the
# usable work area (excludes the taskbar); rcMonitor is the full display.
# HMONITOR/HDC are also not guaranteed in ctypes.wintypes, so they are aliased.
_HMONITOR = getattr(wintypes, "HMONITOR", ctypes.c_void_p)
_HDC = getattr(wintypes, "HDC", ctypes.c_void_p)


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _prof(stage: str, t0: float) -> None:
    """Emit a single [prof] timing line for a focus-pipeline stage (Step 2 profiling)."""
    if ZEZO_PROFILE:
        print(f"[prof] focus :: {stage:38s} {(time.perf_counter() - t0) * 1000:8.2f}ms")


# Step 3b: profile-name -> Chrome PIDs cache (per app name, 30s TTL).
_PROFILE_PIDS_CACHE: Dict[str, Tuple[float, List[int]]] = {}
_PROFILE_PIDS_TTL = 30.0



class WindowsNativeDriver:
    """Encapsulates all direct Win32 User32/Kernel32 native API calls."""

    def __init__(self):
        self.is_windows = (platform.system() == "Windows")
        if self.is_windows:
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32
        else:
            self.user32 = None
            self.kernel32 = None

    def is_self_or_console_window(self, hwnd: Optional[int] = None) -> bool:
        """Check if an HWND belongs to the ZEZO IDE, console, or Python runner."""
        if not self.is_windows or not self.user32:
            return False
        try:
            if not hwnd:
                hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return False

            pid = ctypes.c_ulong()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            target_pid = pid.value
            my_pid = os.getpid()

            if target_pid == my_pid:
                return True

            if _PSUTIL:
                try:
                    if target_pid in self.console_parent_pids():
                        return True
                except Exception:
                    pass

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                t = buff.value.lower().strip()
                if any(k in t for k in ("zezo", "jarvis", "antigravity")):
                    return True
        except Exception:
            pass
        return False

    def is_real_top_level_window(self, hwnd: int) -> bool:
        """Check if an HWND is a real interactive top-level application window."""
        if not self.is_windows or not self.user32:
            return False
        if not self.user32.IsWindowVisible(hwnd):
            return False
        owner = self.user32.GetWindow(hwnd, GW_OWNER)
        ex_style = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            return False
        if owner != 0 and not (ex_style & WS_EX_APPWINDOW):
            return False

        # Filter out cloaked/suspended UWP background windows (DWMWA_CLOAKED = 14)
        try:
            cloaked = ctypes.c_int(0)
            ctypes.windll.dwmapi.DwmGetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(14),  # DWMWA_CLOAKED
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked),
            )
            if cloaked.value != 0:
                return False
        except Exception:
            pass

        return True

    def get_window_title(self, hwnd: int) -> str:
        """Retrieve the Unicode window title for an HWND."""
        if not self.is_windows or not self.user32 or not hwnd:
            return ""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return ""

    def get_window_rect_physical(self, hwnd: int) -> Optional[Dict[str, int]]:
        """
        Get physical bounding rectangle {x, y, width, height, left, top, right, bottom}
        using DwmGetWindowAttribute(hwnd, 9) (DWMWA_EXTENDED_FRAME_BOUNDS) to eliminate
        Windows 10/11 invisible 8px drop-shadow margins (-8, -8 offset).
        """
        if not self.is_windows or not hwnd:
            return None

        # 1. Try DwmGetWindowAttribute with DWMWA_EXTENDED_FRAME_BOUNDS (0x9)
        try:
            rect = wintypes.RECT()
            hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(9),  # DWMWA_EXTENDED_FRAME_BOUNDS
                ctypes.byref(rect),
                ctypes.sizeof(rect),
            )
            if hr == 0:
                width = max(0, rect.right - rect.left)
                height = max(0, rect.bottom - rect.top)
                if width > 0 and height > 0:
                    return {
                        "x": rect.left,
                        "y": rect.top,
                        "width": width,
                        "height": height,
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                    }
        except Exception:
            pass

        # 2. Fallback to standard GetWindowRect
        return self.get_window_rect(hwnd)

    def get_active_window_rect(self) -> Optional[Dict[str, int]]:
        """Get the physical rectangle {x, y, width, height, left, top, right, bottom} of the focused window."""
        if not self.is_windows or not self.user32:
            return None
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd or self.is_self_or_console_window(hwnd):
                return None
            return self.get_window_rect_physical(hwnd)
        except Exception:
            return None

    def get_window_rect(self, hwnd: int) -> Optional[Dict[str, int]]:
        """Get bounding rectangle {x, y, width, height, left, top, right, bottom} in < 0.1ms."""
        if not self.is_windows or not self.user32 or not hwnd:
            return None
        rect = wintypes.RECT()
        if self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return {
                "x": rect.left,
                "y": rect.top,
                "width": max(0, rect.right - rect.left),
                "height": max(0, rect.bottom - rect.top),
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
            }
        return None

    def enum_top_level_windows(self) -> List[Tuple[int, str]]:
        """Enumerate all real top-level application windows and titles."""
        if not self.is_windows or not self.user32:
            return []

        results: List[Tuple[int, str]] = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _enum_cb(hwnd: int, lparam: int) -> bool:
            if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                title = self.get_window_title(hwnd).strip()
                if title and title.lower() not in ("program manager", "settings", "default ime", "msctfime ui"):
                    results.append((hwnd, title))
            return True

        self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        return results

    def show_window_preserving_state(self, hwnd: int) -> bool:
        """
        Bring an HWND on-screen WITHOUT destroying its maximize/fullscreen state.

        Unconditionally calling ShowWindow(SW_RESTORE) un-maximizes a maximized
        browser/window, so Chrome shrank every time a focus/scroll/tab action was
        triggered. Only minimized windows need SW_RESTORE; maximized windows must
        stay maximized (SW_MAXIMIZE); normal floating windows just need SW_SHOW.
        """
        if not self.is_windows or not self.user32 or not hwnd:
            return False
        try:
            if self.user32.IsIconic(hwnd):
                self.user32.ShowWindow(hwnd, SW_RESTORE)
            elif self.user32.IsZoomed(hwnd):
                self.user32.ShowWindow(hwnd, SW_MAXIMIZE)
            else:
                self.user32.ShowWindow(hwnd, SW_SHOW)
            return True
        except Exception:
            try:
                self.user32.ShowWindow(hwnd, SW_SHOW)
            except Exception:
                pass
            return False

    def _settle_foreground(self, hwnd: int, timeout: float = 0.15) -> bool:
        """
        Step 3: early-exit replacement for the fixed `time.sleep(0.15)` on the focus path.

        Returns True the instant `hwnd` is foreground (0ms when the window was already
        focused or when the foreground change lands immediately) and otherwise waits up
        to `timeout` — the exact same worst-case budget the old fixed sleep had, but it
        no longer burns 150ms unconditionally on the success path.
        """
        if not self.user32 or not hwnd:
            return False
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if self.user32.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.005)
        return self.user32.GetForegroundWindow() == hwnd

    def console_parent_pids(self) -> set:
        """
        PIDs of this process's console/terminal ancestors.

        Step 3: `is_self_or_console_window` walked `psutil` parents for EVERY window
        inside every enumeration callback (repeated work, ~10ms per window). The
        ancestor set is constant while enumerating, so it is cached for a short TTL
        and reused. The public 1-arg shape of `is_self_or_console_window` is kept.
        """
        now = time.monotonic()
        cached = getattr(self, "_console_pids_cache", None)
        if cached and (now - cached[0]) < 1.0:
            return cached[1]
        pids: set = set()
        if _PSUTIL:
            try:
                for parent in psutil.Process(os.getpid()).parents():
                    pname = (parent.name() or "").lower()
                    if any(k in pname for k in ("powershell", "cmd", "terminal", "python", "code")):
                        pids.add(parent.pid)
            except Exception:
                pass
        self._console_pids_cache = (now, pids)
        return pids

    def _profile_pids_for(self, app_name: str) -> List[int]:
        """
        Chrome PIDs running the profile whose display name matches `app_name`.

        Step 3b: the scan costs ~0.5-2s (`psutil.process_iter` over ~276 processes), so
        the result is cached per app name for 30s. Cached PIDs that no longer exist are
        dropped, so a Chrome restart cannot pin a stale target.
        """
        now = time.monotonic()
        hit = _PROFILE_PIDS_CACHE.get(app_name)
        if hit and (now - hit[0]) < _PROFILE_PIDS_TTL:
            live = [p for p in hit[1] if not _PSUTIL or psutil.pid_exists(p)]
            if live or not hit[1]:
                return live
        pids = self._scan_profile_pids(app_name)
        _PROFILE_PIDS_CACHE[app_name] = (now, pids)
        return pids

    def _scan_profile_pids(self, app_name: str) -> List[int]:
        """Scan the running Chrome processes for the profile directory matching `app_name`."""
        pids: List[int] = []
        try:
            import json
            local_state_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State")
            if not os.path.exists(local_state_path):
                return pids
            with open(local_state_path, "r", encoding="utf-8") as f:
                ls_data = json.load(f)
            info_cache = ls_data.get("profile", {}).get("info_cache", {})
            dir_to_name = {k.lower(): (v.get("name") or "").lower().strip() for k, v in info_cache.items()}
            target_dir = None
            for p_dir, p_name in dir_to_name.items():
                if app_name == p_name or (len(app_name) >= 3 and app_name in p_name):
                    target_dir = p_dir
                    break
            if target_dir and _PSUTIL:
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        if "chrome" in (proc.info.get("name") or "").lower():
                            cmd = proc.info.get("cmdline") or []
                            for arg in cmd:
                                if f"--profile-directory={target_dir}" in arg.lower():
                                    pids.append(proc.info["pid"])
                    except Exception:
                        pass
        except Exception:
            pass
        return pids

    def focus_window(self, title_or_app: str, hwnd: Optional[int] = None) -> str:
        """
        Bring a target window into foreground with thread attachment.

        Step 3a: when the caller already resolved the target HWND (desktop browser
        requests), pass it in to skip both the window enumeration and profile_lookup.
        """
        if not title_or_app:
            return "No title specified."

        cleaned = title_or_app.lower().strip()
        os_name = platform.system()

        if os_name == "Windows" and self.user32 and self.kernel32:
            try:
                matched_hwnd: Optional[int] = None
                matched_title: str = ""

                browser_suffixes = (
                    " - google chrome", " - microsoft edge", " - brave",
                    " - mozilla firefox", " - firefox", " - opera", " - vivaldi", " - arc",
                )
                is_browser_query = cleaned in (
                    "chrome", "google chrome", "edge", "msedge",
                    "firefox", "brave", "opera", "browser", "youtube",
                )

                APP_ALIASES_MAP = {
                    "vs code": ["visual studio code", " - code", "visual studio"],
                    "vscode": ["visual studio code", " - code", "visual studio"],
                    "code": ["visual studio code", " - code"],
                    "visual studio code": ["visual studio code", " - code"],
                    "calc": ["calculator", "calc"],
                    "calculator": ["calculator", "calc"],
                    "notepad": ["notepad"],
                    "whatsapp": ["whatsapp"],
                    "chrome": ["google chrome", "chrome"],
                    "edge": ["microsoft edge", "msedge", "edge"],
                    "explorer": ["file explorer", " - file explorer", "home", "documents", "downloads", "this pc"],
                    "file explorer": ["file explorer", " - file explorer", "home", "documents", "downloads", "this pc"],
                    "files": ["file explorer", " - file explorer"],
                    "documents": ["documents", "documents - file explorer", "file explorer", "home - file explorer"],
                    "downloads": ["downloads", "downloads - file explorer", "file explorer"],
                    "figma": ["figma", " - figma"],
                    "canva": ["canva", " - canva"],
                    "spotify": ["spotify"],
                    "discord": ["discord"],
                    "telegram": ["telegram"],
                    "terminal": ["terminal", "powershell", "command prompt"],
                }
                # Profile recognition: map names like 'vina', 'james', 'hamza' to Chrome profile directories
                # Step 3: skipped entirely when the caller already resolved the HWND, and
                # the scan result is cached per app name for 30s.
                _t_prof = time.perf_counter()
                profile_pids: list[int] = []
                if not hwnd:
                    profile_pids = self._profile_pids_for(cleaned)
                _prof("focus_window:profile_lookup", _t_prof)

                target_aliases = APP_ALIASES_MAP.get(cleaned, [cleaned])
                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _enum_cb(hwnd: int, lparam: int) -> bool:
                    nonlocal matched_hwnd, matched_title
                    if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                        w_title = self.get_window_title(hwnd)
                        w_lower = w_title.lower().strip()
                        if w_lower not in ("program manager", "settings", "default ime", "msctfime ui"):
                            if profile_pids:
                                p_id = ctypes.c_ulong()
                                self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p_id))
                                if p_id.value in profile_pids:
                                    matched_hwnd = hwnd
                                    matched_title = w_title
                                    return False
                            if not is_browser_query and any(w_lower.endswith(s) for s in browser_suffixes):
                                return True
                            
                            is_match = any(a in w_lower for a in target_aliases)
                            if not is_match:
                                pattern = r"\b" + re.escape(cleaned) + r"\b"
                                is_match = bool(re.search(pattern, w_lower))

                            if is_match:
                                matched_hwnd = hwnd
                                matched_title = w_title
                                return False
                    return True

                _t_prof = time.perf_counter()
                if hwnd:
                    # Step 3a: caller-supplied HWND -> no enumeration, no profile scan.
                    matched_hwnd = hwnd
                    matched_title = self.get_window_title(hwnd)
                else:
                    self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
                _prof("focus_window:EnumWindows", _t_prof)

                if matched_hwnd:
                    _t_prof = time.perf_counter()
                    fg_hwnd = self.user32.GetForegroundWindow()
                    fg_thread = self.user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
                    my_thread = self.kernel32.GetCurrentThreadId()
                    target_thread = self.user32.GetWindowThreadProcessId(matched_hwnd, None) if matched_hwnd else 0
                    _prof("focus_window:fg/thread lookup", _t_prof)

                    try:
                        _t_prof = time.perf_counter()
                        self.user32.AllowSetForegroundWindow(-1)
                    except Exception:
                        pass
                    finally:
                        _prof("focus_window:AllowSetForegroundWindow", _t_prof)

                    try:
                        _t_prof = time.perf_counter()
                        VK_MENU = 0x12
                        KEYEVENTF_KEYUP = 0x0002
                        self.user32.keybd_event(VK_MENU, 0, 0, 0)
                        self.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
                    except Exception:
                        pass
                    finally:
                        _prof("focus_window:keybd_event(alt)", _t_prof)

                    _t_prof = time.perf_counter()
                    attached_fg = False
                    attached_target = False
                    if fg_thread and fg_thread != my_thread:
                        attached_fg = bool(self.user32.AttachThreadInput(my_thread, fg_thread, True))
                    if target_thread and target_thread != my_thread:
                        attached_target = bool(self.user32.AttachThreadInput(my_thread, target_thread, True))
                    _prof("focus_window:AttachThreadInput(on)", _t_prof)

                    _t_prof = time.perf_counter()
                    if self.user32.IsIconic(matched_hwnd):
                        # Step 3: only minimized windows need a ShowWindow(SW_RESTORE).
                        # A visible/maximized window only needs the foreground calls.
                        self.show_window_preserving_state(matched_hwnd)
                    _prof("focus_window:restore-if-minimized", _t_prof)
                    _t_prof = time.perf_counter()
                    self.user32.SetForegroundWindow(matched_hwnd)
                    _prof("focus_window:SetForegroundWindow", _t_prof)
                    _t_prof = time.perf_counter()
                    self.user32.BringWindowToTop(matched_hwnd)
                    _prof("focus_window:BringWindowToTop", _t_prof)

                    _t_prof = time.perf_counter()
                    if attached_target:
                        self.user32.AttachThreadInput(my_thread, target_thread, False)
                    if attached_fg:
                        self.user32.AttachThreadInput(my_thread, fg_thread, False)
                    _prof("focus_window:AttachThreadInput(off)", _t_prof)

                    _t_prof = time.perf_counter()
                    self._settle_foreground(matched_hwnd)
                    _prof("focus_window:settle_foreground", _t_prof)
                    current_fg = self.user32.GetForegroundWindow()
                    is_focused = (
                        current_fg == matched_hwnd
                        or (current_fg and self.user32.GetAncestor(current_fg, 2) == matched_hwnd)
                        or (matched_hwnd and self.user32.GetAncestor(matched_hwnd, 2) == current_fg)
                    )
                    if is_focused:
                        return f"Focused window: {matched_title}"
                    if ZEZO_PROFILE:
                        print(f"[WindowsNative] Window '{matched_title}' (HWND {matched_hwnd}) did not gain foreground focus (Current FG HWND: {current_fg}).")
            except Exception as e:
                if ZEZO_PROFILE:
                    print(f"[WindowsNative] Focus error: {e}")

            return f"Could not focus window: {title_or_app}"

        elif os_name == "Darwin":
            script = (
                f'tell application "System Events" to '
                f'set frontmost of (first process whose name contains "{title_or_app}") to true'
            )
            try:
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
                time.sleep(0.3)
                return f"Focused window: {title_or_app}"
            except Exception as e:
                return f"focus_window (macOS) failed: {e}"

        elif os_name == "Linux":
            try:
                result = subprocess.run(["wmctrl", "-a", title_or_app], capture_output=True, timeout=5)
                if result.returncode == 0:
                    time.sleep(0.3)
                    return f"Focused window: {title_or_app}"
            except FileNotFoundError:
                pass
            try:
                result = subprocess.run(["xdotool", "search", "--name", title_or_app, "windowactivate"], capture_output=True, timeout=5)
                time.sleep(0.3)
                return f"Focused window: {title_or_app}"
            except Exception as e:
                return f"focus_window (Linux) failed: {e}"

        return f"focus_window: unsupported OS '{os_name}'"

    def maximize_window(self, title_or_app: str = "chrome") -> bool:
        """Maximize a window by title or app name (e.g. Chrome)."""
        if not self.is_windows or not self.user32:
            return False
        try:
            matched_hwnd = None
            cleaned = (title_or_app or "chrome").strip().lower()
            APP_ALIASES_MAP = {
                "chrome": ["google chrome", "chrome"],
                "edge": ["microsoft edge", "msedge", "edge"],
                "browser": ["google chrome", "chrome", "edge", "brave", "firefox"],
                "vs code": ["visual studio code", "code"],
                "vscode": ["visual studio code", "code"],
                "code": ["visual studio code", "code"],
            }
            target_aliases = APP_ALIASES_MAP.get(cleaned, [cleaned])

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def _enum_cb(hwnd: int, lparam: int) -> bool:
                nonlocal matched_hwnd
                if self.is_real_top_level_window(hwnd):
                    w_title = self.get_window_title(hwnd).lower().strip()
                    # If target is explicitly VS Code / code, allow matching even if self_or_console (or bypass console check for target apps)
                    if any(a in w_title for a in target_aliases):
                        if any(k in cleaned for k in ("code", "vs code", "vscode")) or not self.is_self_or_console_window(hwnd):
                            matched_hwnd = hwnd
                            return False
                    try:
                        pid = ctypes.c_ulong()
                        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        pname = (psutil.Process(pid.value).name() or "").lower()
                        if any(a in pname for a in target_aliases):
                            if any(k in cleaned for k in ("code", "vs code", "vscode")) or not self.is_self_or_console_window(hwnd):
                                matched_hwnd = hwnd
                                return False
                    except Exception:
                        pass
                return True

            self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
            if matched_hwnd:
                self.user32.ShowWindow(matched_hwnd, SW_MAXIMIZE)
                self.user32.SetForegroundWindow(matched_hwnd)
                return True
        except Exception as e:
            if ZEZO_PROFILE:
                print(f"[WindowsNative] Maximize error: {e}")
        return False

    def minimize_window(self, title_or_app: str = "") -> bool:
        """Minimize a target window by title/process name, or active foreground window."""
        if not self.is_windows or not self.user32:
            return False
        try:
            matched_hwnd = None
            cleaned = (title_or_app or "").strip().lower()
            if not cleaned:
                fg_hwnd = self.user32.GetForegroundWindow()
                if fg_hwnd and not self.is_self_or_console_window(fg_hwnd):
                    self.user32.ShowWindow(fg_hwnd, SW_MINIMIZE)
                    # Verify the window actually became minimized (IsIconic == True)
                    time.sleep(0.05)
                    # Success only if window is now iconic (verified post-condition)
                    if self.user32.IsIconic(fg_hwnd):
                        return True
                    return False
                return False

            APP_ALIASES_MAP = {
                "chrome": ["google chrome", "chrome"],
                "edge": ["microsoft edge", "msedge", "edge"],
                "browser": ["google chrome", "chrome", "edge", "brave", "firefox"],
                "vs code": ["visual studio code", "code"],
                "vscode": ["visual studio code", "code"],
                "code": ["visual studio code", "code"],
            }
            target_aliases = APP_ALIASES_MAP.get(cleaned, [cleaned])

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def _enum_cb(hwnd: int, lparam: int) -> bool:
                nonlocal matched_hwnd
                if self.is_real_top_level_window(hwnd):
                    w_title = self.get_window_title(hwnd).lower().strip()
                    if any(a in w_title for a in target_aliases):
                        if any(k in cleaned for k in ("code", "vs code", "vscode")) or not self.is_self_or_console_window(hwnd):
                            matched_hwnd = hwnd
                            return False
                    try:
                        pid = ctypes.c_ulong()
                        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        pname = (psutil.Process(pid.value).name() or "").lower()
                        if any(a in pname for a in target_aliases):
                            if any(k in cleaned for k in ("code", "vs code", "vscode")) or not self.is_self_or_console_window(hwnd):
                                matched_hwnd = hwnd
                                return False
                    except Exception:
                        pass
                return True

            self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
            if matched_hwnd:
                self.user32.ShowWindow(matched_hwnd, SW_MINIMIZE)
                time.sleep(0.05)
                # Only report success if the window actually became minimized
                return bool(self.user32.IsIconic(matched_hwnd))
        except Exception as e:
            if ZEZO_PROFILE:
                print(f"[WindowsNative] Minimize error: {e}")
        return False

    def list_monitors(self) -> List[Dict[str, int]]:
        """Enumerate the connected monitors with their work-area bounds (index 0 = primary)."""
        if not self.is_windows or not self.user32:
            return []
        out: List[Dict[str, int]] = []
        try:
            handles: List[int] = []
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, _HMONITOR, _HDC,
                ctypes.POINTER(wintypes.RECT), wintypes.LPARAM,
            )

            def _mcb(hmon, hdc, lprc, data):
                try:
                    handles.append(int(hmon))
                except (TypeError, ValueError):
                    pass
                return True

            # Explicit argtypes: without them ctypes passes 32-bit ints and the
            # 64-bit HMONITOR handle is truncated.
            self.user32.EnumDisplayMonitors.argtypes = [
                _HDC, ctypes.c_void_p, MONITORENUMPROC, wintypes.LPARAM,
            ]
            self.user32.EnumDisplayMonitors.restype = wintypes.BOOL
            self.user32.GetMonitorInfoW.argtypes = [
                _HMONITOR, ctypes.POINTER(_MONITORINFO),
            ]
            self.user32.GetMonitorInfoW.restype = wintypes.BOOL

            self.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_mcb), 0)
            for idx, hmon in enumerate(handles):
                mi = _MONITORINFO()
                mi.cbSize = ctypes.sizeof(mi)
                if not self.user32.GetMonitorInfoW(_HMONITOR(hmon), ctypes.byref(mi)):
                    continue
                r = mi.rcWork
                out.append({
                    "index": idx,
                    "left": r.left,
                    "top": r.top,
                    "width": r.right - r.left,
                    "height": r.bottom - r.top,
                })
            return out
        except Exception as e:
            if ZEZO_PROFILE:
                print(f"[WindowsNative] list_monitors error: {e}")
            return []

    def move_window_to_monitor(self, title_or_app: str = "", monitor_index: int = 1) -> bool:
        """
        Move a window onto the monitor at `monitor_index` (0 = primary).

        Without this, a window can only be opened "wherever the OS puts it"; the
        caller has no way to honour a request like "open it on my second monitor".
        """
        if not self.is_windows or not self.user32:
            return False
        try:
            import ctypes
            from ctypes import wintypes

            matched_hwnd = None
            cleaned = (title_or_app or "").strip().lower()
            if not cleaned:
                matched_hwnd = self.user32.GetForegroundWindow()
            else:
                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _cb(hwnd, lp):
                    nonlocal matched_hwnd
                    if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                        if cleaned in (self.get_window_title(hwnd) or "").lower():
                            matched_hwnd = hwnd
                            return False
                    return True

                self.user32.EnumWindows(WNDENUMPROC(_cb), 0)

            if not matched_hwnd:
                return False

            monitors = self.list_monitors()
            if not monitors or monitor_index < 0 or monitor_index >= len(monitors):
                return False
            mon = monitors[monitor_index]

            # Explicit argtypes: the default c_int would truncate a 64-bit HWND.
            self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            self.user32.GetWindowRect.restype = wintypes.BOOL

            r = wintypes.RECT()
            if not self.user32.GetWindowRect(wintypes.HWND(matched_hwnd), ctypes.byref(r)):
                return False
            w = r.right - r.left
            h = r.bottom - r.top
            if w <= 0 or h <= 0:
                return False

            # Bug #7 fix: Only restore if window is maximized. A maximized window
            # reports a screen-sized rect; restore it first so the moved window
            # keeps its real size. If not maximized, skip the restore.
            SW_MAXIMIZE = 3
            SW_RESTORE = 9
            if self.user32.IsZoomed(matched_hwnd):
                self.user32.ShowWindow(matched_hwnd, SW_RESTORE)
                time.sleep(0.05)
                self.user32.GetWindowRect(matched_hwnd, ctypes.byref(r))
                w = r.right - r.left
                h = r.bottom - r.top

            SWP_SHOWWINDOW = 0x0040
            # Explicit argtypes: the default c_int would truncate a 64-bit HWND.
            self.user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
            ]
            self.user32.SetWindowPos.restype = wintypes.BOOL
            return bool(self.user32.SetWindowPos(
                wintypes.HWND(matched_hwnd), None,
                mon["left"] + 40, mon["top"] + 40, w, h,
                SWP_SHOWWINDOW,
            ))
        except Exception as e:
            if ZEZO_PROFILE:
                print(f"[WindowsNative] move_window_to_monitor error: {e}")
            return False

    def focus_browser_or_app_window(self, hwnd: Optional[int] = None) -> bool:
        """
        Attempt to bring any open browser or non-self app to the foreground.

        Step 3a: when the caller already resolved the desktop browser HWND (browser
        requests), pass it in: that HWND is focused directly and both the keyword loop
        and the expensive profile_lookup are skipped. The keyword loop stays as the
        fallback whenever no HWND is known or the direct focus did not take.
        """
        _t_all = time.perf_counter()

        if hwnd:
            _t_prof = time.perf_counter()
            res = self.focus_window("browser", hwnd=hwnd)
            _prof("focus_browser_or_app_window:focus_window(hwnd)", _t_prof)
            if res.startswith("Focused window:"):
                _prof("focus_browser_or_app_window:TOTAL", _t_all)
                return True

        browser_keywords = ["youtube", "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "arc", "browser"]
        for b in browser_keywords:
            _t_prof = time.perf_counter()
            res = self.focus_window(b)
            _prof(f"focus_browser_or_app_window:focus_window({b})", _t_prof)
            if res.startswith("Focused window:"):
                _prof("focus_browser_or_app_window:TOTAL", _t_all)
                return True

        if self.is_windows and self.user32 and self.kernel32:
            try:
                target_hwnd: Optional[int] = None
                target_title: str = ""

                browser_suffixes = (
                    " - google chrome", " - microsoft edge", " - brave",
                    " - mozilla firefox", " - firefox", " - opera", " - vivaldi", " - arc",
                )

                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _enum_cb(hwnd: int, lparam: int) -> bool:
                    nonlocal target_hwnd, target_title
                    if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                        t = self.get_window_title(hwnd).strip()
                        t_lower = t.lower()
                        # Strictly require an actual browser window title to prevent closing non-browser apps like Notepad
                        if any(t_lower.endswith(s) for s in browser_suffixes) or any(k in t_lower for k in ("chrome", "edge", "firefox", "brave", "opera", "youtube")):
                            target_hwnd = hwnd
                            target_title = t
                            return False
                    return True

                _t_prof = time.perf_counter()
                self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
                _prof("focus_browser_or_app_window:EnumWindows", _t_prof)

                if target_hwnd:
                    _t_prof = time.perf_counter()
                    fg_hwnd = self.user32.GetForegroundWindow()
                    fg_thread = self.user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
                    my_thread = self.kernel32.GetCurrentThreadId()
                    _prof("focus_browser_or_app_window:fg/thread lookup", _t_prof)

                    # Step 3: a non-minimized window needs no ShowWindow(SW_RESTORE).
                    _needs_restore = bool(self.user32.IsIconic(target_hwnd))
                    if fg_thread and fg_thread != my_thread:
                        _t_prof = time.perf_counter()
                        self.user32.AttachThreadInput(my_thread, fg_thread, True)
                        _prof("focus_browser_or_app_window:AttachThreadInput(on)", _t_prof)
                        _t_prof = time.perf_counter()
                        if _needs_restore:
                            self.show_window_preserving_state(target_hwnd)
                        _prof("focus_browser_or_app_window:restore-if-minimized", _t_prof)
                        _t_prof = time.perf_counter()
                        self.user32.SetForegroundWindow(target_hwnd)
                        _prof("focus_browser_or_app_window:SetForegroundWindow", _t_prof)
                        _t_prof = time.perf_counter()
                        self.user32.BringWindowToTop(target_hwnd)
                        _prof("focus_browser_or_app_window:BringWindowToTop", _t_prof)
                        _t_prof = time.perf_counter()
                        self.user32.AttachThreadInput(my_thread, fg_thread, False)
                        _prof("focus_browser_or_app_window:AttachThreadInput(off)", _t_prof)
                    else:
                        _t_prof = time.perf_counter()
                        if _needs_restore:
                            self.show_window_preserving_state(target_hwnd)
                        _prof("focus_browser_or_app_window:restore-if-minimized", _t_prof)
                        _t_prof = time.perf_counter()
                        self.user32.SetForegroundWindow(target_hwnd)
                        _prof("focus_browser_or_app_window:SetForegroundWindow", _t_prof)

                    _t_prof = time.perf_counter()
                    self._settle_foreground(target_hwnd)
                    _prof("focus_browser_or_app_window:settle_foreground", _t_prof)
                    _prof("focus_browser_or_app_window:TOTAL", _t_all)
                    return True
            except Exception:
                pass
        _prof("focus_browser_or_app_window:TOTAL(failed)", _t_all)
        return False

    def close_window_by_title_or_active(self, title: str = "") -> str:
        """Safely close target or foreground window without terminating ZEZO."""
        sys_name = platform.system()

        if sys_name == "Windows" and self.user32:
            try:
                if title:
                    cleaned_title = title.lower().strip()
                    # Explorer special handling
                    if cleaned_title in ("explorer", "file explorer", "folder") or "/" in cleaned_title or "\\" in cleaned_title:
                        try:
                            script = "(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.Quit() }"
                            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, **_WIN_HIDE)
                            return "Closed Explorer window(s)."
                        except Exception:
                            pass

                    is_dialog_target = any(k in cleaned_title for k in ("reminder", "popup", "pop-up", "dialog", "alert", "message", "notification", "toast", "modal", "msg"))

                    APP_ALIASES_MAP = {
                        "vs code": ["visual studio code", " - code", "visual studio"],
                        "vscode": ["visual studio code", " - code", "visual studio"],
                        "code": ["visual studio code", " - code"],
                        "visual studio code": ["visual studio code", " - code"],
                        "calc": ["calculator", "calc"],
                        "calculator": ["calculator", "calc"],
                        "notepad": ["notepad", "untitled - notepad"],
                        "whatsapp": ["whatsapp"],
                        "chrome": ["google chrome", "chrome"],
                        "edge": ["microsoft edge", "msedge", "edge"],
                        "explorer": ["file explorer", " - file explorer", "home", "documents", "downloads", "this pc"],
                        "file explorer": ["file explorer", " - file explorer", "home", "documents", "downloads", "this pc"],
                        "terminal": ["terminal", "powershell", "command prompt"],
                    }
                    target_aliases = APP_ALIASES_MAP.get(cleaned_title, [cleaned_title])

                    matched_hwnd: Optional[int] = None
                    matched_title: str = ""

                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                    def _enum_cb(hwnd: int, lparam: int) -> bool:
                        nonlocal matched_hwnd, matched_title
                        if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                            w_title = self.get_window_title(hwnd)
                            w_lower = w_title.lower().strip()
                            pattern = r"\b" + re.escape(cleaned_title) + r"\b"
                            is_match = (
                                any(a in w_lower for a in target_aliases) or
                                cleaned_title == w_lower or
                                re.search(pattern, w_lower) or
                                cleaned_title in w_lower
                            )
                            
                            # Also check process name if title matching fails
                            if not is_match and _PSUTIL:
                                try:
                                    pid = ctypes.c_ulong()
                                    self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                                    pname = (psutil.Process(pid.value).name() or "").lower()
                                    if any(a in pname for a in target_aliases) or cleaned_title in pname:
                                        is_match = True
                                except Exception:
                                    pass

                            if is_match:
                                matched_hwnd = hwnd
                                matched_title = w_title
                                return False
                            if is_dialog_target:
                                if any(k in w_lower for k in ("reminder", "j.a.r.v.i.s reminder", "message from", "alert", "notification", "popup", "dialog", "msg")):
                                    matched_hwnd = hwnd
                                    matched_title = w_title
                                    return False
                        return True

                    self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

                    if matched_hwnd:
                        self.user32.PostMessageW(matched_hwnd, WM_CLOSE, 0, 0)
                        if is_dialog_target:
                            self.user32.PostMessageW(matched_hwnd, WM_COMMAND, IDCANCEL, 0)
                        return f"Closed window: {matched_title}"

                    if is_dialog_target:
                        return "Dismissed active dialog / reminder popup."

                    # When a specific title was requested and not found, never fall through to close unrelated windows
                    return f"Could not find window matching '{title}'."

                # Generic active window closing
                fg_hwnd = self.user32.GetForegroundWindow()
                if self.is_self_or_console_window(fg_hwnd):
                    target_hwnd: Optional[int] = None
                    target_title: str = ""

                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                    def _enum_non_self(hwnd: int, lparam: int) -> bool:
                        nonlocal target_hwnd, target_title
                        if target_hwnd is None and self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                            w_title = self.get_window_title(hwnd).strip()
                            w_lower = w_title.lower()
                            if w_title and w_lower not in ("program manager", "settings", "default ime", "msctfime ui") and not any(k in w_lower for k in ("zezo", "jarvis", "antigravity", "powershell", "cmd.exe", "python")):
                                target_hwnd = hwnd
                                target_title = w_title
                                return False
                        return True

                    self.user32.EnumWindows(WNDENUMPROC(_enum_non_self), 0)

                    if target_hwnd:
                        self.user32.PostMessageW(target_hwnd, WM_CLOSE, 0, 0)
                        return f"Closed window: {target_title}"

                    return "ZEZO window is protected. No other application window found to close."

                w_title = self.get_window_title(fg_hwnd) or "active window"
                self.user32.PostMessageW(fg_hwnd, WM_CLOSE, 0, 0)
                return f"Closed window: {w_title}"

            except Exception as e:
                return f"Windows close error: {e}"

        return "Closed window request sent."


# Global singleton instance
windows_native = WindowsNativeDriver()

# Module-level convenience aliases
focus_window = windows_native.focus_window
get_window_rect = windows_native.get_window_rect
get_window_rect_physical = windows_native.get_window_rect_physical
get_active_window_rect = windows_native.get_active_window_rect
get_window_title = windows_native.get_window_title
is_self_or_console_window = windows_native.is_self_or_console_window
close_window_by_title_or_active = windows_native.close_window_by_title_or_active
enum_top_level_windows = windows_native.enum_top_level_windows
maximize_window = windows_native.maximize_window
minimize_window = windows_native.minimize_window
show_window_preserving_state = windows_native.show_window_preserving_state

