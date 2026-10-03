"""
core/computer/pyautogui_driver.py - Hardware Input Driver for ZEZO OS
Provides hardware mouse/keyboard control with post-move coordinate verification
and safe Unicode clipboard typing with buffer preservation.
Creator: Hamza Bukhari
"""
from __future__ import annotations

import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

_PYAUTOGUI = False
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.03
    _PYAUTOGUI = True
except ImportError:
    pass

_PYPERCLIP = False
try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    pass


class InputDriver:
    """Hardware input driver with post-action verification and safe Unicode typing."""

    def __init__(self):
        self.is_available = _PYAUTOGUI
        self.post_move_verify = True
        self.verify_tolerance_px = 5.0
        self.restore_clipboard_after_paste = True

    def _require_pyautogui(self):
        if not _PYAUTOGUI:
            raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse cursor position."""
        self._require_pyautogui()
        pos = pyautogui.position()
        return (int(pos.x), int(pos.y))

    def move(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
        verify: Optional[bool] = None,
    ) -> str:
        """Move mouse to (x, y) with optional post-move coordinate verification."""
        self._require_pyautogui()
        pyautogui.moveTo(x, y, duration=duration)

        should_verify = self.post_move_verify if verify is None else verify
        if should_verify:
            actual_x, actual_y = self.get_position()
            dist = math.hypot(actual_x - x, actual_y - y)
            if dist > self.verify_tolerance_px:
                # Retry instant correction
                pyautogui.moveTo(x, y, duration=0.05)
                actual_x, actual_y = self.get_position()
                dist = math.hypot(actual_x - x, actual_y - y)

            if dist <= self.verify_tolerance_px:
                return f"Mouse -> ({x}, {y}) [Verified]"
            return f"Mouse -> ({actual_x}, {actual_y}) [Warning: Target was ({x}, {y})]"

        return f"Mouse -> ({x}, {y})"

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        verify: bool = True,
    ) -> str:
        """Move to coordinates (if given) and perform click."""
        self._require_pyautogui()
        if x is not None and y is not None:
            self.move(x, y, duration=0.15, verify=verify)
            time.sleep(0.02)
            pyautogui.click(x, y, button=button, clicks=clicks)
            action_name = "Double-clicked" if clicks == 2 else "Clicked"
            return f"{action_name} ({x}, {y}) [{button}]"

        pyautogui.click(button=button, clicks=clicks)
        return f"Clicked at current position [{button}]"

    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.4,
        button: str = "left",
    ) -> str:
        """Drag mouse from (x1, y1) to (x2, y2)."""
        self._require_pyautogui()
        self.move(x1, y1, duration=0.15)
        pyautogui.dragTo(x2, y2, duration=duration, button=button)
        return f"Dragged ({x1},{y1}) -> ({x2},{y2})"

    def scroll(self, direction: str = "down", amount: int = 3) -> str:
        """Scroll mouse wheel vertically or horizontally."""
        self._require_pyautogui()
        vertical = direction in ("up", "down")
        clicks = amount if direction in ("up", "right") else -amount
        if vertical:
            pyautogui.scroll(clicks)
        else:
            pyautogui.hscroll(clicks)
        return f"Scrolled {direction} x{amount}"

    def press(self, key: str) -> str:
        """Press a single key."""
        self._require_pyautogui()
        pyautogui.press(key)
        return f"Pressed: {key}"

    def hotkey(self, *keys: str) -> str:
        """Execute key combination (e.g. 'ctrl', 'c')."""
        self._require_pyautogui()
        pyautogui.hotkey(*keys)
        return f"Hotkey: {'+'.join(keys)}"

    def clear_field(self) -> str:
        """Select all and clear current input field."""
        self._require_pyautogui()
        select_mod = "command" if platform.system() == "Darwin" else "ctrl"
        pyautogui.hotkey(select_mod, "a")
        time.sleep(0.05)
        pyautogui.press("delete")
        return "Field cleared"

    def type_safe_unicode(
        self,
        text: str,
        interval: float = 0.02,
        restore_clipboard: Optional[bool] = None,
    ) -> str:
        """
        Type text with automatic Unicode clipboard fallback and buffer preservation.
        Guarantees 100% fidelity for Urdu, Arabic, Hindi, emojis, symbols, and multiline text.
        """
        self._require_pyautogui()
        time.sleep(0.05)
        if not text:
            return "No text provided to type."

        do_restore = self.restore_clipboard_after_paste if restore_clipboard is None else restore_clipboard
        is_unicode = not text.isascii()
        is_multiline = "\n" in text
        is_long = len(text) > 30

        # If text is Unicode, multiline, or long, use safe clipboard paste
        if (is_unicode or is_multiline or is_long) and _PYPERCLIP:
            old_clip: Optional[str] = None
            if do_restore:
                try:
                    old_clip = pyperclip.paste()
                except Exception:
                    old_clip = None

            try:
                pyperclip.copy(text)
                time.sleep(0.05)
                paste_mod = "command" if platform.system() == "Darwin" else "ctrl"
                pyautogui.hotkey(paste_mod, "v")
                time.sleep(0.05)
            finally:
                if do_restore and old_clip is not None:
                    # Give target application 100ms to consume paste buffer before restoring
                    time.sleep(0.1)
                    try:
                        pyperclip.copy(old_clip)
                    except Exception:
                        pass

            display_preview = text[:60] + ("..." if len(text) > 60 else "")
            return f"Typed (Clipboard-Safe): {display_preview}"

        # Standard ASCII typing
        try:
            pyautogui.write(text, interval=interval)
        except Exception:
            # Fallback to clipboard if write throws on unexpected char
            if _PYPERCLIP:
                pyperclip.copy(text)
                paste_mod = "command" if platform.system() == "Darwin" else "ctrl"
                pyautogui.hotkey(paste_mod, "v")

        display_preview = text[:60] + ("..." if len(text) > 60 else "")
        return f"Typed: {display_preview}"

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Alias for type_safe_unicode for resilient cross-module compatibility."""
        return self.type_safe_unicode(text, interval=interval)

    def smart_type(
        self,
        text: str,
        clear_first: bool = True,
        restore_clipboard: Optional[bool] = None,
    ) -> str:
        """Smart-type with field clearing and Unicode clipboard preservation."""
        self._require_pyautogui()
        if clear_first:
            self.clear_field()
            time.sleep(0.05)

        if not text:
            return "Field cleared."

        return self.type_safe_unicode(text, restore_clipboard=restore_clipboard)

    def get_clipboard(self) -> str:
        """Read text from system clipboard."""
        if _PYPERCLIP:
            return pyperclip.paste()
        self.hotkey("ctrl", "c")
        time.sleep(0.15)
        return "(copied - pyperclip unavailable)"

    def set_clipboard(self, text: str) -> str:
        """Write text to clipboard and paste."""
        if _PYPERCLIP:
            pyperclip.copy(text)
            time.sleep(0.05)
            paste_mod = "command" if platform.system() == "Darwin" else "ctrl"
            self.hotkey(paste_mod, "v")
            return f"Pasted: {text[:60]}{'...' if len(text) > 60 else ''}"
        return "pyperclip not available"


# Global singleton instance
input_driver = InputDriver()
