"""
core/computer/windows_uia.py - Hardened Windows UI Automation (L1 UIA) Driver for ZEZO OS
Inspects accessibility trees, finds interactive controls, buttons, and inputs in < 15ms.
Uses dedicated STA COM thread isolation with strict 0.8s timeout boundaries.
Creator: Hamza Bukhari
"""
from __future__ import annotations

import concurrent.futures
import ctypes
import platform
import re
import time
from typing import Any, Dict, List, Optional, Tuple

_PYWINAUTO = False
try:
    from pywinauto.application import Application
    from pywinauto.findwindows import ElementNotFoundError
    _PYWINAUTO = True
except ImportError:
    pass

_INTERACTIVE_CONTROL_TYPES = {
    "button", "edit", "tabitem", "tab", "menuitem", "menu",
    "hyperlink", "link", "checkbox", "radiobutton", "combobox",
    "listitem", "treeitem", "pane", "custom", "text"
}

_UIA_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="zezo_uia_worker")


def _init_com_sta():
    """Ensure Single-Threaded Apartment (STA) COM is initialized for the current thread."""
    try:
        ctypes.windll.ole32.CoInitialize(None)
    except Exception:
        pass


class WindowsUIADriver:
    """Hardened Windows UI Automation driver with STA COM threading and strict timeout guards."""

    def __init__(self):
        self.is_available = _PYWINAUTO and (platform.system() == "Windows")

    def find_element(
        self,
        hwnd: int,
        query: str,
        depth: int = 6,
        timeout_seconds: float = 0.8,
    ) -> Optional[Dict[str, Any]]:
        """
        Locate a UI element inside a window by title/text/name or automation ID.
        Runs in an isolated STA threadpool with strict timeout guards.
        """
        if not self.is_available or not hwnd or not query:
            return None

        def _worker() -> Optional[Dict[str, Any]]:
            _init_com_sta()
            cleaned_query = query.lower().strip()
            t0 = time.perf_counter()

            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                descendants = win.descendants(depth=depth)

                best_match = None
                best_score = 0.0

                for el in descendants:
                    try:
                        ctrl_type = (el.friendly_class_name() or "").strip().lower()
                        # Skip pure layout container nodes if not relevant
                        if ctrl_type and ctrl_type not in _INTERACTIVE_CONTROL_TYPES and "button" not in ctrl_type:
                            continue

                        name = (el.window_text() or "").strip()
                        auto_id = str(getattr(el.element_info, "automation_id", "") or "").strip()

                        name_lower = name.lower()
                        auto_id_lower = auto_id.lower()

                        if not name_lower and not auto_id_lower:
                            continue

                        # Exact match
                        if cleaned_query == name_lower or cleaned_query == auto_id_lower:
                            rect = el.rectangle()
                            if rect.width() > 0 and rect.height() > 0:
                                return {
                                    "name": name or auto_id,
                                    "control_type": ctrl_type,
                                    "automation_id": auto_id,
                                    "x": rect.left,
                                    "y": rect.top,
                                    "width": rect.width(),
                                    "height": rect.height(),
                                    "center_x": rect.left + rect.width() // 2,
                                    "center_y": rect.top + rect.height() // 2,
                                    "source": "l1_uia",
                                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                                }

                        # Substring match (bidirectional)
                        if cleaned_query in name_lower or cleaned_query in auto_id_lower or (name_lower and name_lower in cleaned_query):
                            score = min(len(cleaned_query), len(name_lower or auto_id_lower)) / max(len(cleaned_query), len(name_lower or auto_id_lower), 1)
                            if score > best_score:
                                rect = el.rectangle()
                                if rect.width() > 0 and rect.height() > 0:
                                    best_score = score
                                    best_match = {
                                        "name": name or auto_id,
                                        "control_type": ctrl_type,
                                        "automation_id": auto_id,
                                        "x": rect.left,
                                        "y": rect.top,
                                        "width": rect.width(),
                                        "height": rect.height(),
                                        "center_x": rect.left + rect.width() // 2,
                                        "center_y": rect.top + rect.height() // 2,
                                        "source": "l1_uia",
                                        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                                    }
                    except Exception:
                        continue

                return best_match

            except Exception:
                return None

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds + 0.2)
        except (concurrent.futures.TimeoutError, Exception) as e:
            return None

    def invoke_element(
        self,
        hwnd: int,
        query: str,
        depth: int = 6,
        timeout_seconds: float = 0.8,
    ) -> bool:
        """Directly invoke/click a control via UIA InvokePattern / TogglePattern without moving mouse."""
        if not self.is_available or not hwnd or not query:
            return False

        def _worker() -> bool:
            _init_com_sta()
            cleaned_query = query.lower().strip()
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                for el in win.descendants(depth=depth):
                    try:
                        name = (el.window_text() or "").strip().lower()
                        auto_id = str(getattr(el.element_info, "automation_id", "") or "").strip().lower()
                        if cleaned_query in (name, auto_id) or (name and cleaned_query in name):
                            if hasattr(el, "invoke"):
                                el.invoke()
                                return True
                            if hasattr(el, "click_input"):
                                el.click_input()
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return bool(future.result(timeout=timeout_seconds + 0.2))
        except Exception:
            return False

    def set_focused_text(
        self,
        hwnd: int,
        text: str,
        timeout_seconds: float = 0.8,
    ) -> bool:
        """Set text in active/focused UIA Edit control via ValuePattern or set_edit_text."""
        if not self.is_available or not hwnd:
            return False

        def _worker() -> bool:
            _init_com_sta()
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                # First check if focused element is an edit
                for el in win.descendants(depth=4):
                    try:
                        ctrl_type = (el.friendly_class_name() or "").strip().lower()
                        if "edit" in ctrl_type or "document" in ctrl_type:
                            if hasattr(el, "set_edit_text"):
                                el.set_edit_text(text)
                                return True
                            if hasattr(el, "set_text"):
                                el.set_text(text)
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return bool(future.result(timeout=timeout_seconds + 0.2))
        except Exception:
            return False

    def read_window_text(
        self,
        hwnd: int,
        focused_only: bool = False,
        depth: int = 6,
        timeout_seconds: float = 0.8,
    ) -> Optional[str]:
        """Directly extract text from window controls via UIA without OCR or screenshot."""
        if not self.is_available or not hwnd:
            return None

        def _worker() -> Optional[str]:
            _init_com_sta()
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                texts = []
                for el in win.descendants(depth=depth):
                    try:
                        ctrl_type = (el.friendly_class_name() or "").strip().lower()
                        t = (el.window_text() or "").strip()
                        if t and ctrl_type in ("edit", "document", "text", "static"):
                            if t not in texts:
                                texts.append(t)
                                if focused_only:
                                    break
                    except Exception:
                        continue
                if texts:
                    return "\n".join(texts)
            except Exception:
                pass
            return None

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds + 0.2)
        except Exception:
            return None

    def dump_interactive_elements(
        self,
        hwnd: int,
        depth: int = 6,
        max_elements: int = 20,
        timeout_seconds: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """Extract all visible interactive elements (Buttons, Edits, Checkboxes, Tabs)."""
        if not self.is_available or not hwnd:
            return []

        def _worker() -> List[Dict[str, Any]]:
            _init_com_sta()
            results = []
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                elements = win.descendants(depth=depth)

                for el in elements:
                    try:
                        name = (el.window_text() or "").strip()
                        ctrl_type = (el.friendly_class_name() or "").strip()
                        ctrl_lower = ctrl_type.lower()
                        if not name and ctrl_lower not in ("edit", "button", "combobox", "tabitem", "checkbox"):
                            continue

                        rect = el.rectangle()
                        if rect.width() > 0 and rect.height() > 0:
                            results.append({
                                "name": name,
                                "control_type": ctrl_type,
                                "center_x": rect.left + rect.width() // 2,
                                "center_y": rect.top + rect.height() // 2,
                                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                            })
                            if len(results) >= max_elements:
                                break
                    except Exception:
                        continue
            except Exception:
                pass
            return results

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds + 0.2)
        except Exception:
            return []

    def get_browser_tabs(
        self,
        hwnd: int,
        depth: int = 14,
        timeout_seconds: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Enumerate the REAL open tabs inside a live desktop browser window via UIA.

        Chrome/Edge/Brave expose each tab as a TabItem control with its page title,
        so we can read the user's actual session (~30 tabs) instead of the isolated
        background agent-browser daemon.
        """
        if not self.is_available or not hwnd:
            return []

        def _worker() -> List[Dict[str, Any]]:
            _init_com_sta()
            tabs: List[Dict[str, Any]] = []
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)

                tab_elements = []
                try:
                    tab_elements = win.descendants(control_type="TabItem")
                except Exception:
                    pass

                if not tab_elements:
                    try:
                        tab_elements = [
                            el for el in win.descendants(depth=depth)
                            if (el.friendly_class_name() or "").strip().lower() == "tabitem"
                        ]
                    except Exception:
                        tab_elements = []

                for el in tab_elements:
                    try:
                        name = (el.window_text() or "").strip()
                        if not name:
                            continue
                        try:
                            selected = bool(el.is_selected())
                        except Exception:
                            selected = False
                        rect = el.rectangle()
                        tabs.append({
                            "title": name,
                            "index": len(tabs) + 1,
                            "selected": selected,
                            "center_x": rect.left + rect.width() // 2,
                            "center_y": rect.top + rect.height() // 2,
                            "source": "l1_uia",
                        })
                    except Exception:
                        continue
            except Exception:
                return []
            return tabs

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds + 0.3)
        except Exception:
            return []

    def switch_tab_by_title(
        self,
        hwnd: int,
        query: str,
        depth: int = 14,
        timeout_seconds: float = 2.0,
    ) -> bool:
        """
        Switch to a browser tab by (fuzzy) title via UIA SelectPattern/click_input,
        instead of blind Ctrl+Tab jumping.
        """
        if not self.is_available or not hwnd or not query:
            return False

        cleaned = query.lower().strip()

        def _worker() -> bool:
            _init_com_sta()
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)
                best_el = None
                best_score = 0.0

                tab_elements = []
                try:
                    tab_elements = win.descendants(control_type="TabItem")
                except Exception:
                    pass

                if not tab_elements:
                    try:
                        tab_elements = [
                            el for el in win.descendants(depth=depth)
                            if (el.friendly_class_name() or "").strip().lower() == "tabitem"
                        ]
                    except Exception:
                        tab_elements = []

                for el in tab_elements:
                    try:
                        name = (el.window_text() or "").strip().lower()
                        if not name:
                            continue
                        if cleaned == name:
                            best_el, best_score = el, 1.0
                            break
                        if cleaned in name or name in cleaned:
                            score = min(len(cleaned), len(name)) / max(len(cleaned), len(name), 1)
                            if score > best_score:
                                best_el, best_score = el, score
                    except Exception:
                        continue

                if best_el is None:
                    return False
                for method in ("select", "click_input", "invoke"):
                    fn = getattr(best_el, method, None)
                    if callable(fn):
                        try:
                            fn()
                            return True
                        except Exception:
                            continue
                return False
            except Exception:
                return False

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return bool(future.result(timeout=timeout_seconds + 0.3))
        except Exception:
            return False


    # Calculator state tracking - cache for continuation calculations
    _calculator_cache: Optional[str] = None

    def read_calculator_display(
        self,
        hwnd: int,
        timeout_seconds: float = 0.8,
    ) -> Optional[str]:
        """Read the current value shown in the Windows Calculator result display via UIA."""
        if not self.is_available or not hwnd:
            return None

        def _worker() -> Optional[str]:
            _init_com_sta()
            try:
                app = Application(backend="uia").connect(handle=hwnd, timeout=timeout_seconds)
                win = app.window(handle=hwnd)

                # Try multiple fallback patterns for robustness (Bug #8, #9)
                candidates = []

                # Pattern 1: Standard automation_ids (UWP Calculator)
                for el in win.descendants(depth=8):
                    try:
                        auto_id = str(getattr(el.element_info, "automation_id", "") or "").strip().lower()
                        name = (el.window_text() or "").strip()
                        if auto_id in ("calculatorresults", "normaloutput", "resulttext"):
                            txt = name.strip()
                            if txt.lower().startswith("display is "):
                                txt = txt[len("display is "):].strip()
                            if txt:
                                candidates.append((1, auto_id, txt))
                    except Exception:
                        continue

                # Pattern 2: Look for any Text/Static with numeric content
                for el in win.descendants(depth=8):
                    try:
                        ctrl = (el.friendly_class_name() or "").strip().lower()
                        if ctrl not in ("text", "static", "edit"):
                            continue
                        txt = (el.window_text() or "").strip()
                        if txt and re.search(r"[\d.+\-*/=]", txt):
                            candidates.append((2, ctrl, txt))
                    except Exception:
                        continue

                # Pattern 3: Try window_text() directly on the window itself
                try:
                    win_txt = win.window_text()
                    if win_txt and re.search(r"[\d.+\-*/=]", win_txt):
                        candidates.append((3, "window", win_txt))
                except Exception:
                    pass

                # Pattern 4: Try to find any element containing calculation results
                for el in win.descendants(depth=6):
                    try:
                        name = (el.window_text() or "").strip()
                        auto_id = str(getattr(el.element_info, "automation_id", "") or "").strip()
                        # Check for any element with digits that could be a result
                        if name and re.search(r"[\d.+\-*/=]", name) and not auto_id:
                            candidates.append((4, "name_match", name))
                    except Exception:
                        continue

                # Return best candidate (highest pattern priority)
                if candidates:
                    # Sort by priority (lower pattern number = higher priority)
                    candidates.sort(key=lambda x: x[0])
                    best = candidates[0][2]
                    self._calculator_cache = best
                    return best

            except Exception:
                pass

            # Bug #9: Graceful fallback - return None if calculator is not running
            return None

        future = _UIA_EXECUTOR.submit(_worker)
        try:
            return future.result(timeout=timeout_seconds + 0.3)
        except Exception:
            return None


# Global singleton instance
windows_uia = WindowsUIADriver()

