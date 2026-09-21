"""
core/log_bus.py — Single funnel for every backend log line in Zezo.

Why this exists
---------------
Before this module, backend log lines had exactly two destinations and neither
one was readable inside the desktop app:

  * ``print(...)`` calls across ``actions/`` and ``core/`` (e.g. ``[Code]``,
    ``[Browser]``, ``[Settings]``, ``[DevAgent]``) went to a console window
    that ``main.py`` deliberately hides on Windows by forcing
    ``CREATE_NO_WINDOW`` onto every subprocess. Written, never seen.
  * ``logging.getLogger(...)`` already appears in ten-plus modules
    (``core/task_manager.py``, ``actions/opencode_agent.py``,
    ``actions/kilo_agent.py``, ``core/repo_context.py``, ...), but nothing in
    the project ever calls ``logging.basicConfig()``, so no handler was ever
    attached. Records below WARNING were discarded outright; WARNING and above
    fell through to Python's ``lastResort`` handler and landed on that same
    hidden console.

This module attaches ONE root handler and wraps ``sys.stdout`` / ``sys.stderr``,
so both streams end up in a bounded in-memory ring buffer that the UI polls.

Design notes
------------
* Never blocks a caller — ``emit()`` appends to a deque under a short lock.
* Never touches Qt — readers poll with ``since(cursor)``, so no widget is ever
  reached from a worker thread (AGENTS.md rule 3, never block the GUI thread).
* Redaction happens HERE, on the way in, so nothing downstream (buffer, console
  panel, or a user-chosen export file) can ever hold a live credential. The
  patterns are reused from ``memory/sqlite_memory.py`` rather than copied, so
  there is exactly one secret-pattern list in the project.
* Importing this module installs the hooks, and installation is idempotent. It
  self-installs deliberately so ``main.py`` needs no edit (develop skill, step 4).

Creator & lead architect: Hamza Bukhari.
"""

from __future__ import annotations

import collections
import logging
import os
import sys
import threading
import time

# Single source of truth for secret patterns — do not duplicate this list.
from memory.sqlite_memory import redact_secrets


# ── Tuning ────────────────────────────────────────────────────────────────────

MAX_LINES      = 20_000   # ring-buffer depth; oldest lines drop first
MAX_LINE_CHARS = 4_000    # a single pathological line cannot eat the buffer

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

_LEVEL_ORDER = {name: idx for idx, name in enumerate(LEVELS)}

# Log records arriving from a stdlib logger need a friendlier tag than the
# dotted module path. Anything not listed keeps its own logger name, which is
# already meaningful (e.g. ``zezo.opencode``, ``core.task_manager``).
_SOURCE_ALIAS = {
    "__main__": "main",
    "root":     "zezo",
}

# Third-party libraries that log per-frame or per-request chatter at DEBUG. The
# ``websockets`` client alone emits a record for every 2.8 KB realtime audio
# chunk plus one per response frame — measured at roughly ten lines a second
# while idle, which rolls the whole 20,000-line buffer over in about half an
# hour and buries every real diagnostic. Their INFO/WARNING/ERROR still pass.
#
# This matters for more than noise: that DEBUG stream is where the Gemini Live
# handshake prints its request headers, so silencing it also stops the API key
# from ever entering the buffer in the first place. Redaction in
# ``memory/sqlite_memory.py`` is the second line of defence, not the first.
_NOISY_LOGGERS = (
    "websockets",
    "asyncio",
    "urllib3",
    "httpcore",
    "httpx",
    "PIL",
    "google.genai",
    "google_genai",
    "grpc",
    "absl",
    "pdfminer",
    "pdfminer.psparser",
    "pdfminer.pdfinterp",
    "pdfminer.cmapdb",
    "pdfminer.pdfpage",
    "pdfminer.pdfdocument",
    "pypdf",
    "pdfplumber",
    "fitz",
    "markitdown",
    "docx",
    "pptx",
    "openpyxl",
)


# ── Ring buffer ───────────────────────────────────────────────────────────────

_lines: collections.deque = collections.deque(maxlen=MAX_LINES)
_lock      = threading.RLock()
_seq       = 0                     # monotonically increasing cursor
_dropped   = 0                     # lines evicted by the maxlen
_installed = False
_local     = threading.local()     # re-entrancy guard for the stdlib handler


def emit(level: str, source: str, message: str) -> None:
    """Append one already-decoded log line.

    ``level`` is normalised to the :data:`LEVELS` vocabulary, ``source`` is the
    emitting module/component, and ``message`` is scrubbed of credentials before
    it is stored. Safe to call from any thread. Never raises.
    """
    global _seq, _dropped

    try:
        lvl = (level or "INFO").strip().upper()
        if lvl not in _LEVEL_ORDER:
            lvl = "INFO"

        text = message if isinstance(message, str) else str(message)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        src = (source or "zezo").strip() or "zezo"
        src = _SOURCE_ALIAS.get(src, src)

        with _lock:
            for raw in text.split("\n"):
                line = raw.rstrip()
                if not line:
                    continue
                if len(line) > MAX_LINE_CHARS:
                    line = line[:MAX_LINE_CHARS] + " ...[truncated]"
                if len(_lines) == _lines.maxlen:
                    _dropped += 1
                _seq += 1
                _lines.append({
                    "seq":   _seq,
                    "ts":    time.strftime("%H:%M:%S"),
                    "level": lvl,
                    "src":   src,
                    "msg":   redact_secrets(line),
                })
    except Exception:
        # A logging path must never be the reason the assistant dies.
        pass


def mark() -> int:
    """Return a cursor for the newest line currently buffered."""
    with _lock:
        return _seq


def since(cursor: int, min_level: str = "DEBUG") -> tuple:
    """Return ``(new_lines, new_cursor)`` for everything after ``cursor``.

    Filters by ``min_level`` so callers can ask for errors only without
    re-scanning the whole buffer.
    """
    with _lock:
        try:
            floor = _LEVEL_ORDER.get((min_level or "DEBUG").upper(), 0)
            fresh = [ln for ln in _lines
                     if ln["seq"] > cursor and _LEVEL_ORDER[ln["level"]] >= floor]
        except Exception:
            return [], cursor
        return fresh, _seq


def snapshot(min_level: str = "DEBUG") -> list:
    """Return every buffered line at or above ``min_level``."""
    with _lock:
        try:
            floor = _LEVEL_ORDER.get((min_level or "DEBUG").upper(), 0)
            return [ln for ln in _lines if _LEVEL_ORDER[ln["level"]] >= floor]
        except Exception:
            return list(_lines)


def sources() -> list:
    """Return the sorted set of distinct source tags seen so far."""
    with _lock:
        return sorted({ln["src"] for ln in _lines})


def stats() -> dict:
    """Buffer counters for the console status bar."""
    with _lock:
        return {
            "buffered": len(_lines),
            "capacity": MAX_LINES,
            "dropped":  _dropped,
            "seq":      _seq,
        }


def clear() -> int:
    """Empty the buffer. Returns how many lines were removed."""
    global _dropped
    with _lock:
        n = len(_lines)
        _lines.clear()
        _dropped = 0
        return n


def export_text(min_level: str = "DEBUG") -> str:
    """Render the buffer as plain text, ready for a user-chosen file."""
    rows = snapshot(min_level)
    return "\n".join(
        f"{ln['ts']}  {ln['level']:<8} {ln['src']:<28} {ln['msg']}" for ln in rows
    )


# ── Capture: stdlib logging ───────────────────────────────────────────────────

class _BusHandler(logging.Handler):
    """Feeds every stdlib log record into the ring buffer.

    This is what finally makes the ``logger.info(...)`` calls that already exist
    across ``core/`` and ``actions/`` visible, with no edit to those modules.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # record.getMessage() applies %-style args. Guarded because a badly
        # written format string must not kill the handler.
        guard = getattr(_local, "in_handler", False)
        if guard:
            return
        _local.in_handler = True
        try:
            emit(record.levelname, record.name, record.getMessage())
        except Exception:
            pass
        finally:
            _local.in_handler = False


# ── Capture: raw stdout / stderr ──────────────────────────────────────────────

class _Tee:
    """A stream proxy that mirrors writes into the bus.

    Line-buffered on purpose: ``print()`` arrives as two writes (text, then
    newline), so emitting per-write would shred every message into fragments.
    Unknown attributes are delegated to the wrapped stream so callers that use
    ``.fileno()``, ``.encoding`` or ``.isatty()`` keep working untouched.

    ``_underlying`` may legitimately be ``None`` — under ``pythonw.exe`` Windows
    gives no console, so ``sys.stdout`` is None. Writing is then simply dropped.
    """

    def __init__(self, underlying, level: str, source: str):
        self._underlying = underlying
        self._level      = level
        self._source     = source
        self._pending    = ""
        self._lock       = threading.Lock()

    # -- internal ----------------------------------------------------------
    def _drain(self, final: bool = False) -> None:
        """Emit complete lines. ``final`` also emits any trailing partial line."""
        with self._lock:
            buf = self._pending
            if final:
                self._pending = ""
            else:
                cut = buf.rfind("\n")
                if cut == -1:
                    return
                self._pending = buf[cut + 1:]
                buf = buf[:cut]
        if buf.strip():
            emit(self._level, self._source, buf)

    # -- stream protocol ---------------------------------------------------
    def write(self, data) -> int:
        if not data:
            return 0
        if not isinstance(data, str):
            data = str(data)
        with self._lock:
            self._pending += data
        if "\n" in data:
            self._drain(final=False)
        if self._underlying is not None:
            try:
                self._underlying.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        self._drain(final=True)
        if self._underlying is not None:
            try:
                self._underlying.flush()
            except Exception:
                pass

    def fileno(self):
        if self._underlying is None:
            raise OSError("no underlying stream")
        return self._underlying.fileno()

    def isatty(self) -> bool:
        try:
            return bool(self._underlying and self._underlying.isatty())
        except Exception:
            return False

    @property
    def encoding(self) -> str:
        return getattr(self._underlying, "encoding", None) or "utf-8"

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def __getattr__(self, name):
        # Only reached for attributes this proxy does not define. Underscore
        # names are refused outright: without this, a lookup for an internal
        # attribute that is not set yet would recurse through __getattr__ until
        # the stack blew.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._underlying, name)


# ── Installation ──────────────────────────────────────────────────────────────

def install() -> bool:
    """Attach the root handler and wrap stdout/stderr. Idempotent.

    Returns True if this call performed the installation, False if the bus was
    already live. Called automatically on import; exported so a caller can
    force it after replacing ``sys.stdout`` itself.
    """
    global _installed

    with _lock:
        if _installed:
            return False
        _installed = True

    try:
        handler = _BusHandler()
        handler.setLevel(logging.DEBUG)          # capture logger.debug too
        root = logging.getLogger()
        if root.level > logging.DEBUG or root.level == logging.NOTSET:
            root.setLevel(logging.DEBUG)
        root.addHandler(handler)
    except Exception:
        pass

    # Quiet the per-frame chatter unless the operator explicitly wants the wire
    # dump. Set ZEZO_LOG_DEBUG=1 to keep every library record.
    if not os.environ.get("ZEZO_LOG_DEBUG"):
        try:
            for name in _NOISY_LOGGERS:
                logging.getLogger(name).setLevel(logging.WARNING)
        except Exception:
            pass

    # stdout/stderr may be None under pythonw.exe — _Tee tolerates that.
    try:
        if not isinstance(sys.stdout, _Tee):
            sys.stdout = _Tee(sys.stdout, "INFO", "stdout")
        if not isinstance(sys.stderr, _Tee):
            sys.stderr = _Tee(sys.stderr, "ERROR", "stderr")
    except Exception:
        pass

    return True


# Self-install on import. Deliberate: the develop skill forbids touching main.py
# unnecessarily, and ui.py is imported by main.py before the action/plugin/skill
# loaders run, so this is early enough to catch boot diagnostics.
install()


def log(level: str, message: str, source: str = "zezo") -> None:
    """Thin convenience wrapper used by UI-side callers."""
    emit(level, source, message)

