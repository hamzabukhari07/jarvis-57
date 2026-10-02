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
from typing import Any, Dict, Optional, Tuple

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
    """Extract search candidates from descriptive phrases like "'File' menu item" or "Width input field"."""
    queries: List[str] = []
    d = (description or "").strip()
    if not d:
        return []

    # 1. Quoted text e.g. "'File' menu item" -> "File"
    quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", d)
    for q in quoted:
        qc = q.strip()
        if qc and qc not in queries:
            queries.append(qc)

    # 2. Stripped noise suffixes (e.g. " menu item", " button", " in Notepad")
    cleaned = re.sub(r"(?i)\s+(menu\s+item|menu|button|tab|icon|input\s+field|input|field|link|option|header)(\s+in\s+[\w\s\.\*]+)?$", "", d).strip()
    cleaned = re.sub(r"(?i)^(click|find|locate|the|open|select)\s+", "", cleaned).strip()
    cleaned = cleaned.strip("'\"`")
    if cleaned and cleaned not in queries:
        queries.append(cleaned)

    # 3. Individual alphanumeric word tokens if single keyword present
    tokens = [w for w in re.split(r"[^\w\u0600-\u06FF]", d) if len(w) >= 3 and w.lower() not in ("menu", "item", "button", "click", "notepad", "window", "field", "input", "icon", "the")]
    for t in tokens:
        if t not in queries:
            queries.append(t)

    # 4. Original description as fallback
    if d not in queries:
        queries.append(d)

    return queries


def _find_target_element_escalated(description: str) -> Optional[Tuple[int, int, str]]:
    """
    3-Tier Element Finder:
      1. L1 Windows UIA (10ms) -> inspects UI tree of foreground window.
      2. L1.5 Local RapidOCR (60ms) -> locates text/labels on screen via normalized OCR on CPU (0 MB VRAM).
      3. L2 Gemini Multimodal Vision (2s) -> takes screenshot and passes to cloud VLM for non-text icons.
    Returns: (x, y, source_layer)
    """
    if not description:
        return None

    candidates = _clean_target_queries(description)

    # Step 1: L1 Windows UIA Fast Lookup
    try:
        from actions.screen_processor import get_active_window_context
        ctx = get_active_window_context()
        hwnd = ctx.get("hwnd")
        if hwnd:
            for q in candidates:
                el = windows_uia.find_element(hwnd, q, depth=6, timeout_seconds=0.8)
                if el and "center_x" in el and "center_y" in el:
                    print(f"[ComputerControl] Found '{q}' (query: '{description}') via L1 UIA in {el.get('latency_ms')}ms -> ({el['center_x']}, {el['center_y']})")
                    return (el["center_x"], el["center_y"], "l1_uia")
    except Exception as e:
        print(f"[ComputerControl] UIA search error: {e}")

    # Step 2: L1.5 Local RapidOCR Multilingual Text Matching (0 MB VRAM)
    try:
        from core.computer.ocr_engine import ocr_engine
        if ocr_engine.is_available:
            for q in candidates:
                ocr_res = ocr_engine.find_text_coordinates(q, fuzzy_threshold=0.75)
                if ocr_res and "center_x" in ocr_res and "center_y" in ocr_res:
                    print(f"[ComputerControl] Found '{q}' (query: '{description}') via L1.5 RapidOCR in {ocr_res.get('latency_ms')}ms -> ({ocr_res['center_x']}, {ocr_res['center_y']})")
                    return (ocr_res["center_x"], ocr_res["center_y"], "l1.5_ocr")
    except Exception as e:
        print(f"[ComputerControl] OCR text match error: {e}")

    # Step 3: L2 Gemini Multimodal Vision Fallback
    coords = _screen_find_vision(description)
    if coords:
        return (coords[0], coords[1], "l2_vision")

    return None


def _screen_find_vision(description: str) -> Optional[Tuple[int, int]]:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] [warn] No API key for screen_find")
        return None

    try:
        import pyautogui
        from google import genai
        from google.genai import types as gtypes

        w, h = pyautogui.size()
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

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


def _safe_close_tab() -> str:
    if windows_native.is_self_or_console_window():
        focused = windows_native.focus_browser_or_app_window()
        if not focused:
            return "ZEZO window is protected. No active browser or app window found to close tab."
    modifier = "command" if platform.system() == "Darwin" else "ctrl"
    res = input_driver.hotkey(modifier, "w")
    return f"Closed tab ({res})."


def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Dispatch table for all computer control actions with 4-tier escalation.
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] > {action}  {params}")

    try:
        # Typing actions (Safe Unicode Clipboard by default)
        if action in ("type", "type_text", "write", "write_text", "input_text", "typing", "text"):
            text_to_type = (
                params.get("text")
                if params.get("text") is not None
                else (params.get("value") or params.get("input") or params.get("content") or "")
            )
            return input_driver.type_safe_unicode(str(text_to_type))

        if action in ("smart_type", "smart_write", "clear_and_type", "replace_text"):
            text_to_type = (
                params.get("text")
                if params.get("text") is not None
                else (params.get("value") or params.get("input") or params.get("content") or "")
            )
            return input_driver.smart_type(
                str(text_to_type),
                clear_first=params.get("clear_first", True),
            )

        # Mouse Click Actions (Tiered: Coordinates -> L1 UIA -> L2 Vision)
        if action in ("click", "left_click", "smart_click", "screen_click"):
            x, y = params.get("x"), params.get("y")
            desc = params.get("description") or params.get("text") or params.get("target") or params.get("element") or ""
            if (x is None or y is None) and desc:
                target = _find_target_element_escalated(desc)
                if not target:
                    return f"Element not found on screen: '{desc}'"
                x, y, src = target
            return input_driver.click(x, y, "left", 1)

        if action in ("double_click", "screen_double_click", "double_screen_click"):
            x, y = params.get("x"), params.get("y")
            desc = params.get("description") or params.get("text") or params.get("target") or params.get("element") or ""
            if (x is None or y is None) and desc:
                target = _find_target_element_escalated(desc)
                if not target:
                    return f"Element not found on screen: '{desc}'"
                x, y, src = target
            return input_driver.click(x, y, "left", 2)

        if action in ("right_click", "screen_right_click", "context_menu"):
            x, y = params.get("x"), params.get("y")
            desc = params.get("description") or params.get("text") or params.get("target") or ""
            if (x is None or y is None) and desc:
                target = _find_target_element_escalated(desc)
                if not target:
                    return f"Element not found on screen: '{desc}'"
                x, y, src = target
            return input_driver.click(x, y, "right", 1)

        # Mouse Movement Actions (With Post-Move Coordinate Verification)
        if action in ("move", "mouse_move"):
            return input_driver.move(int(params.get("x", 0)), int(params.get("y", 0)))

        if action in ("drag", "mouse_drag"):
            x1 = params.get("x1") if params.get("x1") is not None else (params.get("from_x") or params.get("start_x"))
            y1 = params.get("y1") if params.get("y1") is not None else (params.get("from_y") or params.get("start_y"))
            x2 = params.get("x2") if params.get("x2") is not None else (params.get("to_x") or params.get("end_x"))
            y2 = params.get("y2") if params.get("y2") is not None else (params.get("to_y") or params.get("end_y"))

            # If single coordinate x, y is passed
            if x1 is None and params.get("x") is not None:
                x1 = params.get("x")
            if y1 is None and params.get("y") is not None:
                y1 = params.get("y")

            # Fallback for start position if completely omitted: start at (400, 300)
            if x1 is None:
                x1 = 400
            if y1 is None:
                y1 = 300

            # Fallback for end position: drag a standard 600x400 box if not explicitly specified
            if x2 is None or y2 is None:
                w = params.get("width") or params.get("w") or 600
                h = params.get("height") or params.get("h") or 400
                x2 = int(x1) + int(w)
                y2 = int(y1) + int(h)

            return input_driver.drag(int(x1), int(y1), int(x2), int(y2))

        # Keyboard Actions
        if action in ("hotkey", "shortcut", "press_hotkey", "send_hotkey"):
            raw = params.get("keys", "") or params.get("key", "") or params.get("hotkey", "") or params.get("text", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return input_driver.hotkey(*keys)

        if action in ("press", "key", "press_key", "keypress", "key_press", "send_key"):
            key_to_press = params.get("key") or params.get("text") or params.get("value") or params.get("keys") or "enter"
            return input_driver.press(str(key_to_press))

        # Direct Single-Key Action Aliases
        if action in ("enter", "escape", "space", "backspace", "tab", "delete"):
            return input_driver.press(action)

        if action in ("clear_field", "clear_text", "empty_field"):
            return input_driver.clear_field()

        # Window & Tab Lifecycle Actions
        if action in ("close_tab", "close_current_tab", "close_browser_tab"):
            return _safe_close_tab()

        if action in ("close_window", "close_active_window", "close_current_window"):
            target_t = params.get("title") or params.get("text") or params.get("app") or params.get("app_name") or ""
            return windows_native.close_window_by_title_or_active(target_t)

        if action in ("dismiss_dialog", "close_popup", "dismiss_popup", "close_dialog", "close_reminder", "dismiss_reminder"):
            target_t = params.get("title") or params.get("text") or "reminder"
            return windows_native.close_window_by_title_or_active(target_t)

        if action in ("focus_window", "bring_to_front", "activate_window"):
            target_t = params.get("title") or params.get("app") or params.get("app_name") or params.get("text") or ""
            return windows_native.focus_window(str(target_t))

        # Filesystem & Folder Launch
        if action in ("open_folder", "open_path", "open_in_app"):
            target_path = params.get("path") or params.get("target") or params.get("text", "")
            app = params.get("app") or params.get("app_name", "")
            p = Path(target_path).expanduser()
            if not p.is_absolute():
                desk_p = Path.home() / "Desktop" / target_path
                if desk_p.exists():
                    p = desk_p
            if app:
                subprocess.Popen(f'{app} "{p}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
                return f"Opened {p} in {app}."
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{p}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return f"Opened folder: {p}"

        # Scrolling Actions
        if action in ("scroll", "page_scroll", "mouse_scroll", "scroll_down", "scroll_up"):
            direction = params.get("direction") or ("up" if "up" in action else "down")
            return input_driver.scroll(
                direction=direction,
                amount=int(params.get("amount", 3)),
            )

        # Clipboard Actions
        if action in ("copy", "clipboard_get", "get_clipboard"):
            return input_driver.get_clipboard()

        if action in ("paste", "clipboard_paste"):
            paste_txt = params.get("text") if params.get("text") is not None else (params.get("value") or "")
            return input_driver.set_clipboard(str(paste_txt))

        # Screenshot Action
        if action in ("screenshot", "take_screenshot", "capture_screen"):
            return _screenshot(params.get("path"))

        # Visual / UIA Element Search Action
        if action in ("screen_find", "find_element", "find_on_screen"):
            desc = params.get("description") or params.get("text") or params.get("target") or ""
            target = _find_target_element_escalated(desc)
            if target:
                return f"{target[0]},{target[1]} [Source: {target[2]}]"
            return "NOT_FOUND"

        if action == "wait":
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        # L0 OS State + L1 UIA Telemetry Action
        if action in ("get_active_window_info", "active_window_info", "window_info", "os_state"):
            from actions.screen_processor import get_active_window_context, get_display_metrics
            ctx = get_active_window_context()
            metrics = get_display_metrics()
            r = ctx.get("rect", {})
            hwnd = ctx.get("hwnd", 0)

            # Extract UIA interactive elements preview
            uia_elements = []
            if hwnd:
                try:
                    uia_elements = windows_uia.dump_interactive_elements(hwnd, depth=2, max_elements=5)
                except Exception:
                    pass

            uia_preview = ""
            if uia_elements:
                elements_str = ", ".join(f"{el['control_type']}('{el['name']}')" for el in uia_elements if el['name'])
                if elements_str:
                    uia_preview = f"\nUIA Interactive Elements: {elements_str}"

            return (
                f"Active Window: '{ctx.get('foreground_title')}' (Process: {ctx.get('foreground_process')}, HWND: {hwnd})\n"
                f"Bounds: x={r.get('x')}, y={r.get('y')}, w={r.get('width')}, h={r.get('height')}\n"
                f"Display: {metrics.get('width')}x{metrics.get('height')} (DPI Scale: {metrics.get('dpi_scale')}x)\n"
                f"Visible Windows: {', '.join(ctx.get('visible_windows', []))}"
                f"{uia_preview}"
            )

        # Mock / Long Term Data
        if action == "random_data":
            dt = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] (random {dt}) -> {result}")
            return result

        if action == "user_data":
            field = params.get("field", "name")
            profile = _user_profile()
            value = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] (No '{field}' in memory, using random: {value})")
        # Batch / Compound Macro Action
        if action in ("batch", "sequence", "macro"):
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

                step_res = computer_control(step, response=response, player=player, session_memory=session_memory)
                step_str = str(step_res)
                executed.append(f"Step {idx+1} ({s_action}): {step_str}")
                if "failed" in step_str.lower() or "not_found" in step_str.lower():
                    return f"Batch aborted at step {idx+1} ({s_action}): {step_str}. Executed so far: " + " -> ".join(executed[:-1])

                delay = float(step.get("delay") or 0.08)
                if delay > 0:
                    time.sleep(delay)

            return f"Executed {len(executed)} batch steps successfully: " + " -> ".join(executed)

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] Error in {action}: {e}")
        return f"computer_control '{action}' failed: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "computer_control",
    "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen, inspect active window.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "type | smart_type | click | double_click | right_click | smart_click | drag | mouse_drag | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | close_window | close_tab | dismiss_dialog | close_popup | screen_find | screen_click | screen_double_click | get_active_window_info | random_data | user_data | batch"
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

# ── Backward compatibility aliases for Phase 4 modular driver refactor ────────
_focus_window = windows_native.focus_window
focus_window = windows_native.focus_window
_close_window = windows_native.close_window_by_title_or_active
close_window = windows_native.close_window_by_title_or_active

def _safe_close_tab(app_hint: str = "") -> str:
    """Close active browser tab safely using Ctrl+W."""
    try:
        windows_native.focus_browser_or_app_window()
        input_driver.hotkey("ctrl", "w")
        return "Closed active tab."
    except Exception as e:
        return f"Could not close tab: {e}"

safe_close_tab = _safe_close_tab

