"""
actions/computer_control.py - Computer Control & UI Automation for ZEZO OS
Dispatches mouse, keyboard, window, and screen automation across 4 escalated layers:
  L1: Windows UIA (10ms) -> L0: Win32 Native (1ms) -> Hardware Input (20ms) -> L2: Gemini Vision (2s)
Creator: Hamza Bukhari
"""
from __future__ import annotations

import io
import json
import os
import platform
import random
import re
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.computer import (
    WindowsNativeDriver,
    windows_native,
    WindowsUIADriver,
    windows_uia,
    InputDriver,
    input_driver,
)

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"
_MEMORY_PATH = _BASE / "memory" / "long_term.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_api_key() -> str:
    return _load_config().get("gemini_api_key", "")


_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)


def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    return fallback


_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)
    if dt == "last_name":
        return random.choice(_LAST_NAMES)
    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last = random.choice(_LAST_NAMES).lower()
        num = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"
    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"
    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))
    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"
    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"
    if dt == "address":
        num = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"
    if dt == "zip_code":
        return str(random.randint(10000, 99999))
    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{data_type}_{random.randint(1000, 9999)}"


def _user_profile() -> dict:
    try:
        if _MEMORY_PATH.exists():
            data = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}


def _screenshot(save_path: str | None = None) -> str:
    path = _safe_screenshot_path(save_path)
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(str(path))
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"Screenshot failed: {e}"


def _clean_target_queries(description: str) -> List[str]:
    queries: List[str] = []
    d = (description or "").strip()
    if not d:
        return []

    quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", d)
    for q in quoted:
        qc = q.strip()
        if qc and qc not in queries:
            queries.append(qc)

    cleaned = re.sub(r"(?i)\s+(menu\s+item|menu|button|tab|icon|input\s+field|input|field|link|option|header)(\s+in\s+[\w\s\.\*]+)?$", "", d).strip()
    cleaned = re.sub(r"(?i)^(click|find|locate|the|open|select)\s+", "", cleaned).strip()
    cleaned = cleaned.strip("'\"`")
    if cleaned and cleaned not in queries:
        queries.append(cleaned)

    tokens = [w for w in re.split(r"[^\w\u0600-\u06FF]", d) if len(w) >= 3 and w.lower() not in ("menu", "item", "button", "click", "notepad", "window", "field", "input", "icon", "the")]
    for t in tokens:
        if t not in queries:
            queries.append(t)

    if d not in queries:
        queries.append(d)

    return queries


def _screen_find_vision(description: str) -> Optional[Tuple[int, int]]:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] [warn] No API key for screen_find")
        return None

    try:
        from core.computer.screen_capture import capture_screen_bytes
        import pyautogui

        w, h = pyautogui.size()
        image_bytes = capture_screen_bytes()
        if not image_bytes:
            return None

        prompt = (
            f"This is a screenshot of a {w}x{h} pixel screen. "
            f"Locate the UI element described as: '{description}'. "
            f"Reply with ONLY the center coordinates as: x,y "
            f"If the element is not visible, reply: NOT_FOUND"
        )

        from core import gemini
        response = gemini.call(
            [gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"), prompt],
            tier=gemini.FAST, timeout_ms=20_000,
        )
        if response is None:
            return None

        text = (response.text or "").strip()
        if "NOT_FOUND" in text.upper():
            return None

        match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if match:
            return int(match.group(1)), int(match.group(2))

    except Exception as e:
        print(f"[ComputerControl] [warn] screen_find failed: {e}")

    return None


def _find_target_element_escalated(description: str) -> Optional[Tuple[int, int, str]]:
    if not description:
        return None

    candidates = _clean_target_queries(description)

    # L1: Windows UIA Fast Lookup
    try:
        from actions.screen_processor import get_active_window_context
        ctx = get_active_window_context()
        hwnd = ctx.get("hwnd")
        if hwnd:
            for q in candidates:
                el = windows_uia.find_element(hwnd, q, depth=6, timeout_seconds=0.8)
                if el and "center_x" in el and "center_y" in el:
                    print(f"[ComputerControl] Found '{q}' via L1 UIA in {el.get('latency_ms')}ms -> ({el['center_x']}, {el['center_y']})")
                    return (el["center_x"], el["center_y"], "l1_uia")
    except Exception as e:
        print(f"[ComputerControl] UIA search error: {e}")

    # L1.5: Local RapidOCR Multilingual Text Matching (0 MB VRAM)
    try:
        from core.computer.ocr_engine import ocr_engine
        if ocr_engine.is_available:
            for q in candidates:
                ocr_res = ocr_engine.find_text_coordinates(q, fuzzy_threshold=0.75)
                if ocr_res and "center_x" in ocr_res and "center_y" in ocr_res:
                    print(f"[ComputerControl] Found '{q}' via L1.5 RapidOCR in {ocr_res.get('latency_ms')}ms -> ({ocr_res['center_x']}, {ocr_res['center_y']})")
                    return (ocr_res["center_x"], ocr_res["center_y"], "l1.5_ocr")
    except Exception as e:
        print(f"[ComputerControl] OCR text match error: {e}")

    # L2: Gemini Multimodal Vision Fallback
    coords = _screen_find_vision(description)
    if coords:
        return (coords[0], coords[1], "l2_vision")

    return None


def _extract_text_field(params: dict) -> str:
    if params.get("text") is not None:
        return str(params.get("text"))
    for key in ("value", "input", "content"):
        if params.get(key) is not None:
            return str(params.get(key))
    return ""


import threading

_DESKTOP_INPUT_LOCK = threading.RLock()


def _get_active_foreground_hwnd() -> int:
    """Get active foreground window HWND safely."""
    if platform.system() == "Windows":
        try:
            import ctypes
            return int(ctypes.windll.user32.GetForegroundWindow() or 0)
        except Exception:
            return 0
    return 0


def _validate_and_ensure_focus(target_win: Optional[str]) -> Tuple[bool, int, str]:
    """
    Validates if the target window is in the foreground. If not, attempts to focus it.
    Returns (success, hwnd, title).
    """
    if not target_win:
        hwnd = _get_active_foreground_hwnd()
        title = windows_native.get_window_title(hwnd) if hwnd else "active window"
        return True, hwnd, title

    target_str = str(target_win).strip()
    focus_res = windows_native.focus_window(target_str)
    time.sleep(0.15)
    hwnd = _get_active_foreground_hwnd()
    title = windows_native.get_window_title(hwnd) if hwnd else ""
    return bool("focused" in focus_res.lower() or hwnd), hwnd, title


def _handle_type(params: dict, action: str, **_) -> str:
    text = _extract_text_field(params)
    target_win = params.get("title") or params.get("app") or params.get("window")

    with _DESKTOP_INPUT_LOCK:
        ok, hwnd, current_title = _validate_and_ensure_focus(target_win)
        if target_win and not ok:
            return f"Cannot type: Target window '{target_win}' could not be focused."

        # Tier 1: Windows UIA Direct Edit Control Injection (< 10ms, no focus stealing)
        if hwnd and action in ("set_text", "set_window_text", "direct_type"):
            if windows_uia.set_focused_text(hwnd, text):
                return f"Typed (UIA Direct): {text[:60]}{'...' if len(text) > 60 else ''}"

        # Tier 2: Smart Clear & Type or Formula Direct Input
        if action in ("smart_type", "smart_write", "clear_and_type", "replace_text"):
            if any(op in text for op in ("+", "-", "*", "/", "=")):
                return input_driver.type_safe_unicode(text)
            return input_driver.smart_type(text, clear_first=params.get("clear_first", True))

        # Tier 3: Universal Clipboard-Safe Unicode Injection with Buffer Preservation
        return input_driver.type_safe_unicode(text)


def _handle_click(params: dict, action: str, **_) -> str:
    x, y = params.get("x"), params.get("y")
    desc = params.get("description") or params.get("text") or params.get("target") or params.get("element") or ""

    with _DESKTOP_INPUT_LOCK:
        if (x is None or y is None) and desc:
            # Check if UIA Direct Invoke is possible for button/control
            hwnd = _get_active_foreground_hwnd()
            if hwnd and windows_uia.is_available:
                if windows_uia.invoke_element(hwnd, desc):
                    return f"Invoked (UIA Direct): '{desc}'"

            target = _find_target_element_escalated(desc)
            if not target:
                return f"Element not found on screen: '{desc}'"
            x, y, _ = target

        button = "right" if "right" in action or action == "context_menu" else "left"
        clicks = 2 if "double" in action else 1
        return input_driver.click(x, y, button, clicks)


def _handle_mouse_move(params: dict, **_) -> str:
    return input_driver.move(int(params.get("x", 0)), int(params.get("y", 0)))


def _handle_mouse_drag(params: dict, **_) -> str:
    x1 = params.get("x1") if params.get("x1") is not None else (params.get("from_x") or params.get("start_x") or params.get("x") or 400)
    y1 = params.get("y1") if params.get("y1") is not None else (params.get("from_y") or params.get("start_y") or params.get("y") or 300)
    x2 = params.get("x2") if params.get("x2") is not None else (params.get("to_x") or params.get("end_x"))
    y2 = params.get("y2") if params.get("y2") is not None else (params.get("to_y") or params.get("end_y"))

    if x2 is None or y2 is None:
        w = params.get("width") or params.get("w") or 600
        h = params.get("height") or params.get("h") or 400
        x2 = int(x1) + int(w)
        y2 = int(y1) + int(h)

    return input_driver.drag(int(x1), int(y1), int(x2), int(y2))


def _handle_hotkey(params: dict, **_) -> str:
    raw = params.get("keys", "") or params.get("key", "") or params.get("hotkey", "") or params.get("text", "")
    keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
    return input_driver.hotkey(*keys)


def _handle_press(params: dict, action: str, **_) -> str:
    if action in ("enter", "escape", "space", "backspace", "tab", "delete"):
        return input_driver.press(action)
    key_to_press = params.get("key") or params.get("text") or params.get("value") or params.get("keys") or "enter"
    return input_driver.press(str(key_to_press))


def _handle_window(params: dict, action: str, **_) -> str:
    target_title = params.get("title") or params.get("text") or params.get("app") or params.get("app_name") or ""
    if action in ("close_tab", "close_current_tab", "close_browser_tab"):
        return _safe_close_tab()
    if action in ("close_window", "close_active_window", "close_current_window"):
        return windows_native.close_window_by_title_or_active(target_title)
    if action in ("dismiss_dialog", "close_popup", "dismiss_popup", "close_dialog", "close_reminder", "dismiss_reminder"):
        return windows_native.close_window_by_title_or_active(target_title or "reminder")
    if action in ("focus_window", "bring_to_front", "activate_window"):
        return windows_native.focus_window(str(target_title))
    return f"Unknown window action: {action}"


def _handle_open_folder(params: dict, **_) -> str:
    target_path = params.get("path") or params.get("target") or params.get("text", "")
    app = params.get("app") or params.get("app_name", "")
    p = Path(target_path).expanduser()
    if not p.is_absolute():
        desk_p = Path.home() / "Desktop" / target_path
        if desk_p.exists():
            p = desk_p

    if app:
        # Prevent terminal window popups on Windows
        creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        subprocess.Popen(f'{app} "{p}"', shell=True, creationflags=creationflags)
        return f"Opened {p} in {app}."

    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{p}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(["xdg-open", str(p)])
    return f"Opened folder: {p}"


def _handle_scroll(params: dict, action: str, **_) -> str:
    direction = params.get("direction") or ("up" if "up" in action else "down")
    return input_driver.scroll(direction=direction, amount=int(params.get("amount", 3)))


def _handle_clipboard(params: dict, action: str, **_) -> str:
    if action in ("copy", "clipboard_get", "get_clipboard"):
        return input_driver.get_clipboard()
    paste_txt = _extract_text_field(params)
    return input_driver.set_clipboard(paste_txt)


def _handle_active_window_info(**_) -> str:
    from actions.screen_processor import get_active_window_context, get_display_metrics
    ctx = get_active_window_context()
    metrics = get_display_metrics()
    r = ctx.get("rect", {})
    hwnd = ctx.get("hwnd", 0)

    uia_preview = ""
    if hwnd:
        try:
            uia_elements = windows_uia.dump_interactive_elements(hwnd, depth=2, max_elements=5)
            if uia_elements:
                elements_str = ", ".join(f"{el['control_type']}('{el['name']}')" for el in uia_elements if el.get("name"))
                if elements_str:
                    uia_preview = f"\nUIA Interactive Elements: {elements_str}"
        except Exception:
            pass

    return (
        f"Active Window: '{ctx.get('foreground_title')}' (Process: {ctx.get('foreground_process')}, HWND: {hwnd})\n"
        f"Bounds: x={r.get('x')}, y={r.get('y')}, w={r.get('width')}, h={r.get('height')}\n"
        f"Display: {metrics.get('width')}x{metrics.get('height')} (DPI Scale: {metrics.get('dpi_scale')}x)\n"
        f"Visible Windows: {', '.join(ctx.get('visible_windows', []))}"
        f"{uia_preview}"
    )


def _handle_mock_data(params: dict, action: str, **_) -> str:
    should_type = bool(params.get("type_into_window") or params.get("write") or params.get("type_text") or params.get("insert"))
    target_win = params.get("title") or params.get("app") or params.get("window")

    if action == "random_data":
        dt = params.get("type", "name")
        res = _random_data(dt)
        print(f"[ComputerControl] (random {dt}) -> {res}")
        if should_type:
            with _DESKTOP_INPUT_LOCK:
                _validate_and_ensure_focus(target_win)
                typed_res = input_driver.type_safe_unicode(res)
                return f"{res} ({typed_res})"
        return res

    field = params.get("field", "name")
    val = _user_profile().get(field, "")
    if not val:
        val = _random_data(field)
        print(f"[ComputerControl] (No '{field}' in memory, using random: {val})")

    if should_type:
        with _DESKTOP_INPUT_LOCK:
            _validate_and_ensure_focus(target_win)
            typed_res = input_driver.type_safe_unicode(val)
            return f"{val} ({typed_res})"
    return val


def _handle_batch(params: dict, dispatcher_fn: Callable, **kwargs) -> str:
    steps = params.get("sequence") or params.get("steps") or params.get("actions") or []
    if not isinstance(steps, list) or not steps:
        return "Error: 'batch' action requires a non-empty 'sequence' list of action steps."

    executed = []
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        s_action = step.get("action", "")
        if not s_action or s_action in ("batch", "sequence", "macro"):
            continue

        step_res = dispatcher_fn(step, **kwargs)
        step_str = str(step_res)
        executed.append(f"Step {idx+1} ({s_action}): {step_str}")
        if "failed" in step_str.lower() or "not_found" in step_str.lower():
            return f"Batch aborted at step {idx+1} ({s_action}): {step_str}. Executed so far: " + " -> ".join(executed[:-1])

        delay = float(step.get("delay") or 0.08)
        if delay > 0:
            time.sleep(delay)

    return f"Executed {len(executed)} batch steps successfully: " + " -> ".join(executed)


# Dispatch map routing action strings to modular sub-handlers
_ACTION_ROUTER: Dict[str, Callable] = {
    # Typing
    "type": _handle_type,
    "type_text": _handle_type,
    "write": _handle_type,
    "write_text": _handle_type,
    "input_text": _handle_type,
    "typing": _handle_type,
    "text": _handle_type,
    "smart_type": _handle_type,
    "smart_write": _handle_type,
    "clear_and_type": _handle_type,
    "replace_text": _handle_type,
    # Mouse clicks
    "click": _handle_click,
    "left_click": _handle_click,
    "smart_click": _handle_click,
    "screen_click": _handle_click,
    "double_click": _handle_click,
    "screen_double_click": _handle_click,
    "double_screen_click": _handle_click,
    "right_click": _handle_click,
    "screen_right_click": _handle_click,
    "context_menu": _handle_click,
    # Mouse movements
    "move": _handle_mouse_move,
    "mouse_move": _handle_mouse_move,
    "drag": _handle_mouse_drag,
    "mouse_drag": _handle_mouse_drag,
    # Keyboard
    "hotkey": _handle_hotkey,
    "shortcut": _handle_hotkey,
    "press_hotkey": _handle_hotkey,
    "send_hotkey": _handle_hotkey,
    "press": _handle_press,
    "key": _handle_press,
    "press_key": _handle_press,
    "keypress": _handle_press,
    "key_press": _handle_press,
    "send_key": _handle_press,
    "enter": _handle_press,
    "escape": _handle_press,
    "space": _handle_press,
    "backspace": _handle_press,
    "tab": _handle_press,
    "delete": _handle_press,
    "clear_field": lambda **_: input_driver.clear_field(),
    "clear_text": lambda **_: input_driver.clear_field(),
    "empty_field": lambda **_: input_driver.clear_field(),
    # Window management
    "close_tab": _handle_window,
    "close_current_tab": _handle_window,
    "close_browser_tab": _handle_window,
    "close_window": _handle_window,
    "close_active_window": _handle_window,
    "close_current_window": _handle_window,
    "dismiss_dialog": _handle_window,
    "close_popup": _handle_window,
    "dismiss_popup": _handle_window,
    "close_dialog": _handle_window,
    "close_reminder": _handle_window,
    "dismiss_reminder": _handle_window,
    "focus_window": _handle_window,
    "bring_to_front": _handle_window,
    "activate_window": _handle_window,
    # Filesystem & Launch
    "open_folder": _handle_open_folder,
    "open_path": _handle_open_folder,
    "open_in_app": _handle_open_folder,
    # Scrolling
    "scroll": _handle_scroll,
    "page_scroll": _handle_scroll,
    "mouse_scroll": _handle_scroll,
    "scroll_down": _handle_scroll,
    "scroll_up": _handle_scroll,
    # Clipboard
    "copy": _handle_clipboard,
    "clipboard_get": _handle_clipboard,
    "get_clipboard": _handle_clipboard,
    "paste": _handle_clipboard,
    "clipboard_paste": _handle_clipboard,
    # Screenshot & Vision
    "screenshot": lambda params, **_: _screenshot(params.get("path")),
    "take_screenshot": lambda params, **_: _screenshot(params.get("path")),
    "capture_screen": lambda params, **_: _screenshot(params.get("path")),
    "screen_find": lambda params, **_: (lambda t: f"{t[0]},{t[1]} [Source: {t[2]}]" if t else "NOT_FOUND")(_find_target_element_escalated(params.get("description") or params.get("text") or params.get("target") or "")),
    "find_element": lambda params, **_: (lambda t: f"{t[0]},{t[1]} [Source: {t[2]}]" if t else "NOT_FOUND")(_find_target_element_escalated(params.get("description") or params.get("text") or params.get("target") or "")),
    "find_on_screen": lambda params, **_: (lambda t: f"{t[0]},{t[1]} [Source: {t[2]}]" if t else "NOT_FOUND")(_find_target_element_escalated(params.get("description") or params.get("text") or params.get("target") or "")),
    # Direct UIA Text Setting & Reading
    "set_text": _handle_type,
    "set_window_text": _handle_type,
    "direct_type": _handle_type,
    "read_text": lambda **_: (lambda h: windows_uia.read_window_text(h) if h else "No active window")(_get_active_foreground_hwnd()),
    "read_window_text": lambda **_: (lambda h: windows_uia.read_window_text(h) if h else "No active window")(_get_active_foreground_hwnd()),
    # Sleep / Delay
    "wait": lambda params, **_: (lambda s: (time.sleep(s), f"Waited {s}s")[1])(min(float(params.get("seconds", 1.0)), 30.0)),
    # OS State
    "get_active_window_info": lambda **_: _handle_active_window_info(),
    "active_window_info": lambda **_: _handle_active_window_info(),
    "window_info": lambda **_: _handle_active_window_info(),
    "os_state": lambda **_: _handle_active_window_info(),
    # Mock data
    "random_data": _handle_mock_data,
    "user_data": _handle_mock_data,
}


def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Modular dispatch table for all computer control actions with 4-tier escalation.
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] > {action}  {params}")

    try:
        if action in ("batch", "sequence", "macro"):
            return _handle_batch(params, computer_control, response=response, player=player, session_memory=session_memory)

        handler = _ACTION_ROUTER.get(action)
        if handler:
            return handler(params=params, action=action, response=response, player=player, session_memory=session_memory)

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] Error in {action}: {e}")
        return f"computer_control '{action}' failed: {e}"


# Tool declaration (auto-discovered by core/action_loader.py)
TOOL = {
    "name": "computer_control",
    "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen, inspect active window.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "type | smart_type | direct_type | set_text | read_window_text | click | double_click | right_click | smart_click | drag | mouse_drag | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | close_window | close_tab | dismiss_dialog | close_popup | screen_find | screen_click | screen_double_click | get_active_window_info | random_data | user_data | batch"
            },
            "sequence": {
                "type": "ARRAY",
                "description": "List of step objects to execute sequentially for action='batch' (e.g. [{'action': 'screen_click', 'description': 'Width'}, {'action': 'type', 'text': '400'}, {'action': 'press', 'key': 'tab'}, {'action': 'type', 'text': '400'}, {'action': 'press', 'key': 'enter'}])",
                "items": {"type": "OBJECT"}
            },
            "text": {
                "type": "STRING",
                "description": "Text to type or paste"
            },
            "x": {
                "type": "INTEGER",
                "description": "X coordinate"
            },
            "y": {
                "type": "INTEGER",
                "description": "Y coordinate"
            },
            "x1": {
                "type": "INTEGER",
                "description": "Start X coordinate for drag"
            },
            "y1": {
                "type": "INTEGER",
                "description": "Start Y coordinate for drag"
            },
            "x2": {
                "type": "INTEGER",
                "description": "End X coordinate for drag"
            },
            "y2": {
                "type": "INTEGER",
                "description": "End Y coordinate for drag"
            },
            "width": {
                "type": "INTEGER",
                "description": "Width for drag box or shape"
            },
            "height": {
                "type": "INTEGER",
                "description": "Height for drag box or shape"
            },
            "keys": {
                "type": "STRING",
                "description": "Key combination e.g. 'ctrl+c'"
            },
            "key": {
                "type": "STRING",
                "description": "Single key e.g. 'enter'"
            },
            "direction": {
                "type": "STRING",
                "description": "up | down | left | right"
            },
            "amount": {
                "type": "INTEGER",
                "description": "Scroll amount (default: 3)"
            },
            "seconds": {
                "type": "NUMBER",
                "description": "Seconds to wait"
            },
            "title": {
                "type": "STRING",
                "description": "Window title for focus_window or close_window"
            },
            "description": {
                "type": "STRING",
                "description": "Element description for screen_find/screen_click"
            },
            "type": {
                "type": "STRING",
                "description": "Data type for random_data"
            },
            "field": {
                "type": "STRING",
                "description": "Field for user_data: name|email|city"
            },
            "clear_first": {
                "type": "BOOLEAN",
                "description": "Clear field before typing (default: true)"
            },
            "path": {
                "type": "STRING",
                "description": "Save path for screenshot"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": computer_control,
}

# Compatibility aliases
_focus_window = windows_native.focus_window
focus_window = windows_native.focus_window
_close_window = windows_native.close_window_by_title_or_active
close_window = windows_native.close_window_by_title_or_active


def _safe_close_tab(app_hint: str = "") -> str:
    try:
        windows_native.focus_browser_or_app_window()
        input_driver.hotkey("ctrl", "w")
        return "Closed active tab."
    except Exception as e:
        return f"Could not close tab: {e}"


safe_close_tab = _safe_close_tab


def _safe_close_window(title_or_name: str = "") -> str:
    """Safely close a window strictly enforcing exact or specific title matching to prevent closing unrelated apps."""
    if not title_or_name or not str(title_or_name).strip():
        return "No window title provided to close."

    target = str(title_or_name).strip().lower()

    # Never close ZEZO / JARVIS main shell window
    if target in ("zezo", "jarvis", "zezo os", "zezo_main", "tactical dashboard"):
        return "Cannot close ZEZO main OS window."

    try:
        from core.computer import windows_native
        return windows_native.close_window_by_title_or_active(target)
    except Exception as e:
        return f"Could not close window '{title_or_name}': {e}"


safe_close_window = _safe_close_window
