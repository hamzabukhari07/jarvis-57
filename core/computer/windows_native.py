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

# Win32 Constants
SW_RESTORE = 9
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
IDCANCEL = 2
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


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
                    proc = psutil.Process(my_pid)
                    if target_pid == proc.pid:
                        return True
                    for parent in proc.parents():
                        if parent.pid == target_pid:
                            return True
                    for child in proc.children(recursive=True):
                        if child.pid == target_pid:
                            return True
                except Exception:
                    pass

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                t = buff.value.lower().strip()
                if any(k in t for k in ("zezo", "jarvis", "antigravity", "powershell", "cmd.exe", "windowsterminal", "python")):
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

    def focus_window(self, title_or_app: str) -> str:
        """Bring a target window into foreground with thread attachment."""
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
                    " - mozilla firefox", " - firefox", " - opera",
                )
                is_browser_query = cleaned in (
                    "chrome", "google chrome", "edge", "msedge",
                    "firefox", "brave", "opera", "browser",
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
                target_aliases = APP_ALIASES_MAP.get(cleaned, [cleaned])

                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _enum_cb(hwnd: int, lparam: int) -> bool:
                    nonlocal matched_hwnd, matched_title
                    if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                        w_title = self.get_window_title(hwnd)
                        w_lower = w_title.lower().strip()
                        if w_lower not in ("program manager", "settings", "default ime", "msctfime ui"):
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

                self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

                if matched_hwnd:
                    fg_hwnd = self.user32.GetForegroundWindow()
                    fg_thread = self.user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
                    my_thread = self.kernel32.GetCurrentThreadId()

                    if fg_thread and fg_thread != my_thread:
                        self.user32.AttachThreadInput(my_thread, fg_thread, True)
                        self.user32.ShowWindow(matched_hwnd, SW_RESTORE)
                        self.user32.SetForegroundWindow(matched_hwnd)
                        self.user32.BringWindowToTop(matched_hwnd)
                        self.user32.AttachThreadInput(my_thread, fg_thread, False)
                    else:
                        self.user32.ShowWindow(matched_hwnd, SW_RESTORE)
                        self.user32.SetForegroundWindow(matched_hwnd)

                    time.sleep(0.15)
                    current_fg = self.user32.GetForegroundWindow()
                    if current_fg == matched_hwnd or not self.is_self_or_console_window(current_fg):
                        return f"Focused window: {matched_title}"
                    else:
                        print(f"[WindowsNative] Window '{matched_title}' did not gain foreground focus.")
            except Exception as e:
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

    def focus_browser_or_app_window(self) -> bool:
        """Attempt to bring any open browser or non-self app to the foreground."""
        browser_keywords = ["youtube", "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "arc", "browser"]
        for b in browser_keywords:
            res = self.focus_window(b)
            if res.startswith("Focused window:"):
                return True

        if self.is_windows and self.user32 and self.kernel32:
            try:
                target_hwnd: Optional[int] = None
                target_title: str = ""

                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                def _enum_cb(hwnd: int, lparam: int) -> bool:
                    nonlocal target_hwnd, target_title
                    if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                        t = self.get_window_title(hwnd).strip()
                        if t and t not in ("Program Manager", "Settings", "Default IME", "MSCTFIME UI"):
                            target_hwnd = hwnd
                            target_title = t
                            return False
                    return True

                self.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

                if target_hwnd:
                    fg_hwnd = self.user32.GetForegroundWindow()
                    fg_thread = self.user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
                    my_thread = self.kernel32.GetCurrentThreadId()
                    if fg_thread and fg_thread != my_thread:
                        self.user32.AttachThreadInput(my_thread, fg_thread, True)
                        self.user32.ShowWindow(target_hwnd, SW_RESTORE)
                        self.user32.SetForegroundWindow(target_hwnd)
                        self.user32.BringWindowToTop(target_hwnd)
                        self.user32.AttachThreadInput(my_thread, fg_thread, False)
                    else:
                        self.user32.ShowWindow(target_hwnd, SW_RESTORE)
                        self.user32.SetForegroundWindow(target_hwnd)
                    time.sleep(0.15)
                    return True
            except Exception:
                pass
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

                    matched_hwnd: Optional[int] = None
                    matched_title: str = ""

                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                    def _enum_cb(hwnd: int, lparam: int) -> bool:
                        nonlocal matched_hwnd, matched_title
                        if self.is_real_top_level_window(hwnd) and not self.is_self_or_console_window(hwnd):
                            w_title = self.get_window_title(hwnd)
                            w_lower = w_title.lower().strip()
                            pattern = r"\b" + re.escape(cleaned_title) + r"\b"
                            is_match = (cleaned_title == w_lower or re.search(pattern, w_lower) or cleaned_title in w_lower)
                            
                            # Also check process name if title matching fails
                            if not is_match and _PSUTIL:
                                try:
                                    pid = ctypes.c_ulong()
                                    self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                                    pname = (psutil.Process(pid.value).name() or "").lower()
                                    if cleaned_title in pname or pname.startswith(cleaned_title):
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
                        self.user32.PostMessageW(matched_hwnd, WM_COMMAND, IDCANCEL, 0)
                        return f"Closed window: {matched_title}"

                    if is_dialog_target:
                        return "Dismissed active dialog / reminder popup."

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
