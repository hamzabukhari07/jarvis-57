"""
core/clipboard_watcher.py - Background Clipboard Monitor for Zezo ClipPeek
Creator: Hamza Bukhari
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("zezo.clipboard_watcher")

_PYPERCLIP = False
try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    pass


class ClipboardWatcher:
    """Monitors OS clipboard for changes and notifies subscribers."""

    def __init__(self, callback: Optional[Callable[[dict], None]] = None, interval: float = 1.0):
        self.callback = callback
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()
        self._last_content = ""
        self.is_running = False

    def start(self) -> None:
        if not _PYPERCLIP:
            logger.warning("pyperclip not installed; ClipboardWatcher disabled.")
            return
        if self.is_running:
            return
        self._stopped.clear()
        self._last_content = ""
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ClipboardWatcher")
        self._thread.start()
        self.is_running = True
        logger.info("ClipboardWatcher started.")

    def stop(self) -> None:
        self._stopped.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self.is_running = False
        logger.info("ClipboardWatcher stopped.")

    def _run_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                time.sleep(self.interval)
                if not _PYPERCLIP:
                    continue
                current = pyperclip.paste() or ""
                if current and current != self._last_content:
                    self._last_content = current
                    content_type = self._classify_content(current)
                    payload = {
                        "text": current,
                        "type": content_type,
                        "timestamp": time.time(),
                        "preview": current[:80] + ("..." if len(current) > 80 else "")
                    }
                    logger.debug("Clipboard change detected: type=%s, len=%d", content_type, len(current))
                    if self.callback:
                        try:
                            self.callback(payload)
                        except Exception as e:
                            logger.error("Error in clipboard callback: %s", e)
            except Exception as e:
                logger.debug("Clipboard polling error: %s", e)

    def _classify_content(self, text: str) -> str:
        t = text.strip()
        if t.startswith("http://") or t.startswith("https://") or t.startswith("www."):
            return "url"
        if any(kw in t for kw in ("def ", "class ", "import ", "function ", "const ", "let ", "{", "}", "SELECT *")) and len(t) < 1500:
            return "code"
        if len(t) > 300:
            return "article"
        return "text"
