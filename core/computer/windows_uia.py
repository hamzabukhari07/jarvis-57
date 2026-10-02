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


# Global singleton instance
windows_uia = WindowsUIADriver()
