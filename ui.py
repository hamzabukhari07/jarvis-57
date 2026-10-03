"""
ZEZO OS — Desktop Window Container & Web Engine Host.
Integrates the Autonomous Traffic Vectors HTML5/CSS/JS frontend with the Python backend.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import psutil

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("zezo.assistant.v2")
    except Exception:
        pass
else:
    _WIN_HIDE: dict = {}

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSizePolicy

# QtWebEngine needs AA_ShareOpenGLContexts BEFORE its own module import, or
# Chromium never starts a GPU process and silently renders the whole page in
# software (SwiftShader) — which pins the host Qt thread and the renderer at
# ~1 core each. This must stay above the QtWebEngineWidgets import below.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# Windows blocklists the GPU for QtWebEngine far too eagerly on multi-GPU
# (Optimus) laptops, which drops the UI into software rasterization. Ask for
# GPU rasterization and ignore the blocklist. setdefault so a user-provided
# QTWEBENGINE_CHROMIUM_FLAGS always wins. Must precede the WebEngine import.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--ignore-gpu-blocklist --enable-gpu-rasterization")

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

try:
    from core import log_bus
except Exception:
    log_bus = None

from core.ui_server import get_ui_server, ZezoUIServer

logger = logging.getLogger("zezo.ui")

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"

APP_VERSION = "ZEZO"
_DEFAULT_W, _DEFAULT_H = 1020, 720
_MIN_W, _MIN_H = 860, 600
_OS = platform.system()


def _read_full_config() -> dict:
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


class C:
    """Design System Token Defaults for Python compatibility."""
    BG = "#050505"
    PANEL = "#0a0a0a"
    PANEL2 = "#111111"
    PRI = "#f24e1e"
    PRI_DIM = "#8a2a0d"
    PRI_GHO = "#2a0d05"
    ACC = "#f24e1e"
    ACC2 = "#f59e0b"
    GREEN = "#22c55e"
    RED = "#ef4444"
    TEXT = "#f4f4f5"
    TEXT_DIM = "#71717a"
    TEXT_MED = "#9ca3af"
    WHITE = "#ffffff"
    DARK = "#070709"


def _apply_dark_title_bar(window: QWidget) -> None:
    """Enables Windows 10/11 native immersive dark title bar and custom dark caption colors."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        dwmapi = ctypes.windll.dwmapi

        # 1. Immersive Dark Mode
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / Windows 10 20H1+), 19 (Windows 10 1809-1909)
        true_val = ctypes.c_int(1)
        res = dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(true_val), ctypes.sizeof(true_val)
        )
        if res != 0:
            dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(true_val), ctypes.sizeof(true_val)
            )

        # 2. Windows 11 Build 22000+ custom caption, text, and border colors (COLORREF 0x00BBGGRR)
        # Caption: Pitch Black Obsidian #050505 (0x00050505)
        caption_color = ctypes.c_int(0x00050505)
        dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
        )

        # Text: Crisp Off-White #E0E0E0 (0x00E0E0E0)
        text_color = ctypes.c_int(0x00E0E0E0)
        dwmapi.DwmSetWindowAttribute(
            hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color)
        )

        # Border: Deep Obsidian Border #151515 (0x00151515)
        border_color = ctypes.c_int(0x00151515)
        dwmapi.DwmSetWindowAttribute(
            hwnd, 34, ctypes.byref(border_color), ctypes.sizeof(border_color)
        )
    except Exception as e:
        logger.debug(f"Dark title bar could not be applied: {e}")


def apply_ui_accent(hex_color: str) -> bool:
    """Updates global C.PRI token and broadcasts to the web frontend."""
    C.PRI = hex_color
    server = get_ui_server()
    server.broadcast("accent_changed", {"color": hex_color})
    return True


class MainWindow(QMainWindow):
    """Main desktop container window hosting the HTML5/CSS/JS frontend via QWebEngineView."""

    _log_sig = pyqtSignal(str)
    _stream_sig = pyqtSignal(str, str, bool)
    _state_sig = pyqtSignal(str)
    _content_sig = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        _cfg = _read_full_config()
        self._assistant_name: str = (_cfg.get("assistant_name") or "Zezo").strip()
        _display = self._assistant_name.upper()

        if _display == "ZEZO" or _display == APP_VERSION:
            self.setWindowTitle(APP_VERSION)
        else:
            self.setWindowTitle(f"{_display} — {APP_VERSION}")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        _apply_dark_title_bar(self)

        # Set App Icon if exists
        ico_path = CONFIG_DIR / "zezo.ico"
        if not ico_path.exists():
            ico_path = CONFIG_DIR / "jarvis.ico"
        if ico_path.exists():
            self.setWindowIcon(QIcon(str(ico_path)))

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width() - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        # External callbacks
        self.on_text_command: Callable[[str], None] | None = None
        self.on_remote_clicked: Callable[[], tuple[str, str] | None] | None = None
        self.on_file_uploaded: Callable[[dict], None] | None = None
        self.on_interrupt: Callable[[], None] | None = None
        self.on_voice_change: Callable[[], None] | None = None
        self.on_audio_device_change: Callable[[], None] | None = None
        self.on_push_to_talk: Callable[[bool], str] | None = None
        self.on_sleep_toggle: Callable[[bool], None] | None = None
        self.ptt_hold: Callable[[bool], None] | None = None
        self._muted = False
        self._sleeping = False
        self._ready = True
        self._current_file = ""

        # Initialize and start local UI Server
        self._server = get_ui_server()
        self._server.on_text_command = self._handle_text_command
        self._server.on_interrupt = self._handle_interrupt
        self._server.on_mute_toggle = self._handle_mute_toggle
        self._server.on_sleep_toggle = self._handle_sleep_toggle
        self._server.on_remote_clicked = self._handle_remote_clicked
        self._server.on_file_uploaded = self._handle_file_uploaded
        self.on_pipeline_change = None
        self._server.on_assistant_settings_changed = self._handle_assistant_settings_changed
        self._server.on_pipeline_settings_changed = self._handle_pipeline_settings_changed
        self._server.on_audio_devices_changed = self._handle_audio_devices_changed
        self._server.on_create_shortcut = self._create_desktop_shortcut
        self._server.on_wake_toggle = lambda en: getattr(self, "on_wake_toggle", lambda x: "ok")(en) if hasattr(self, "on_wake_toggle") else "ok"
        self._server.on_ptt_toggle = lambda en: getattr(self, "on_push_to_talk", lambda x: "ok")(en) if hasattr(self, "on_push_to_talk") else "ok"
        self._server.get_initial_state = self._get_initial_state
        self._server.start()

        # WebEngine View
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background: #050505;")

        # Enable local storage, WebGL, smooth scrolling
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

        # Enable drag & drop accept on Qt container
        self.setAcceptDrops(True)
        self.web_view.setAcceptDrops(True)

        # Load local web app from UI server
        server_url = f"http://127.0.0.1:{self._server.port}/"
        self.web_view.load(QUrl(server_url))
        self.setCentralWidget(self.web_view)

        # Connect internal signals
        self._log_sig.connect(self._on_log_emitted)
        self._stream_sig.connect(self._on_stream_emitted)
        self._state_sig.connect(self._on_state_emitted)
        self._content_sig.connect(self._on_content_emitted)

        # Global Hotkeys
        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_intr = QShortcut(QKeySequence("Escape"), self)
        sc_intr.activated.connect(self._do_interrupt)

        # Telemetry timer (500ms). psutil.net_io_counters() costs ~15 ms on
        # Windows, so _poll_telemetry refreshes it only every 4th tick (2 s)
        # and reuses the cached value in between — the Qt thread never blocks.
        self._net_cache_mb = 0.0
        self._net_tick = 0
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)
        self._telemetry_timer.start(500)

        # Task manager polling timer (1000ms). Listing tasks is a lock + dict
        # walk; 300 ms was 3x more often than the HUD can show a change.
        self._task_timer = QTimer(self)
        self._task_timer.timeout.connect(self._poll_tasks)
        self._task_timer.start(1000)

    def showEvent(self, event):
        super().showEvent(event)
        _apply_dark_title_bar(self)

    def _get_initial_state(self) -> dict:
        tasks = []
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
        except Exception:
            pass

        from memory.config_manager import (
            get_voice, get_response_language,
            get_autostart_enabled, get_brief_enabled,
            get_wake_word_enabled, get_push_to_talk_enabled,
        )
        return {
            "state": "OFFLINE",
            "muted": self._muted,
            "assistant_name": self._assistant_name,
            "voice_name": get_voice(),
            "response_language": get_response_language(),
            "autostart_enabled": get_autostart_enabled(),
            "morning_brief_enabled": get_brief_enabled(),
            "wake_word_enabled": get_wake_word_enabled(),
            "push_to_talk_enabled": get_push_to_talk_enabled(),
            "tasks": tasks,
            "timestamp": time.time(),
        }

    def _handle_assistant_settings_changed(self, name: str, voice: str, lang: str):
        if name:
            self._assistant_name = name
        if self.on_voice_change:
            try:
                self.on_voice_change()
            except Exception as e:
                logger.warning("Error in on_voice_change callback: %s", e)

    def _handle_pipeline_settings_changed(self):
        if getattr(self, "on_pipeline_change", None):
            try:
                self.on_pipeline_change()
            except Exception as e:
                logger.warning("Error in on_pipeline_change callback: %s", e)

    def _handle_audio_devices_changed(self, input_name: str, output_name: str):
        """User picked a microphone/speaker in the AUDIO I/O panel.

        Both streams are opened inside the session TaskGroup, so main.py rebuilds
        the session (keeping conversation context) through the existing
        on_audio_device_change callback. Called from the UI server thread, and
        request_reconnect() is thread-safe."""
        if self.on_audio_device_change:
            try:
                self.on_audio_device_change()
            except Exception as e:
                logger.warning("Error in on_audio_device_change callback: %s", e)

    def _handle_text_command(self, text: str):
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()
        else:
            self._on_log_emitted(f"USER: {text}")

    def _handle_interrupt(self):
        if self.on_interrupt:
            self.on_interrupt()

    def _handle_mute_toggle(self, muted: bool):
        self._muted = muted
        self._server.broadcast("state_change", {"state": "MUTED" if self._muted else ("SLEEPING" if self._sleeping else "LISTENING")})

    def _handle_sleep_toggle(self, sleeping: bool):
        self._sleeping = sleeping
        if self.on_sleep_toggle:
            try:
                self.on_sleep_toggle(sleeping)
            except Exception as e:
                logger.warning("Error in on_sleep_toggle: %s", e)
        self._server.broadcast("state_change", {"state": "SLEEPING" if self._sleeping else ("MUTED" if self._muted else "LISTENING")})

    def _on_state_emitted(self, state: str):
        # If user has muted or put the assistant to sleep, do not overwrite with transient listening states
        s_upper = (state or "").upper()
        if self._muted and s_upper not in ("OFFLINE", "CONNECTING"):
            self._server.broadcast("state_change", {"state": "MUTED"})
            return
        if self._sleeping and s_upper not in ("OFFLINE", "CONNECTING", "MUTED"):
            self._server.broadcast("state_change", {"state": "SLEEPING"})
            return
        self._server.broadcast("state_change", {"state": state})

    def _handle_file_uploaded(self, file_info: dict):
        path = file_info.get("path", "")
        if path:
            self._current_file = str(path)
        if self.on_file_uploaded:
            try:
                self.on_file_uploaded(file_info)
            except Exception as e:
                logger.warning("Error in on_file_uploaded: %s", e)

    def _handle_remote_clicked(self) -> tuple[str, str]:
        if self.on_remote_clicked:
            try:
                res = self.on_remote_clicked()
                if res:
                    return res[0], res[1]
            except Exception:
                pass
        return f"http://127.0.0.1:{self._server.port}", "8F3A-9K2L"

    def _get_initial_state(self) -> dict:
        state_str = "MUTED" if self._muted else ("SLEEPING" if self._sleeping else "LISTENING")
        tasks = []
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
        except Exception:
            pass

        from memory.config_manager import (
            get_assistant_name, get_voice, get_response_language,
            get_autostart_enabled, get_brief_enabled,
            get_wake_word_enabled, get_push_to_talk_enabled,
            get_masked_gemini_key, get_masked_groq_key, is_configured,
            get_opencode_model, get_kilo_model, get_antigravity_model,
        )
        return {
            "state": state_str,
            "muted": self._muted,
            "sleeping": self._sleeping,
            "tasks": tasks,
            "assistant_name": get_assistant_name(),
            "voice_name": get_voice(),
            "response_language": get_response_language(),
            "autostart_enabled": get_autostart_enabled(),
            "morning_brief_enabled": get_brief_enabled(),
            "wake_word_enabled": get_wake_word_enabled(),
            "push_to_talk_enabled": get_push_to_talk_enabled(),
            "has_gemini_key": is_configured(),
            "gemini_api_key_masked": get_masked_gemini_key(),
            "groq_api_key_masked": get_masked_groq_key(),
            "opencode_model": get_opencode_model(),
            "kilo_model": get_kilo_model(),
            "antigravity_model": get_antigravity_model(),
        }

    def _poll_telemetry(self):
        try:
            from actions.system_monitor import _get_gpu_usage
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            # net_io_counters() is the one expensive sample here (~15 ms on
            # Windows). Refresh it every 4th tick (2 s) and reuse the cached
            # value on the rest so this timer never blocks the Qt thread.
            self._net_tick = (self._net_tick + 1) % 4
            if self._net_tick == 1:
                net = psutil.net_io_counters()
                self._net_cache_mb = (net.bytes_sent + net.bytes_recv) / (1024 * 1024)
            gpu_val = _get_gpu_usage()
            self._server.broadcast("telemetry_update", {
                "cpu": cpu,
                "mem": mem,
                "gpu": gpu_val if gpu_val >= 0 else 0,
                "net": self._net_cache_mb % 10.0,
                "tmp": -1
            })
        except Exception:
            pass

    def _poll_tasks(self):
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
            self._server.broadcast("task_list", {"tasks": tasks})
        except Exception:
            pass

    def _on_log_emitted(self, text: str):
        tag = "SYS"
        msg = text
        u_text = text.upper()
        if u_text.startswith("USER:") or u_text.startswith("YOU:"):
            tag, msg = "USER", text[text.find(":") + 1:].strip()
        elif u_text.startswith("AI:") or u_text.startswith("ZEZO:") or (self._assistant_name and u_text.startswith(f"{self._assistant_name.upper()}:")):
            tag, msg = "AI", text[text.find(":") + 1:].strip()
            # Clean internal intent reasoning prefixes if model outputs them
            import re
            msg = re.sub(r"^intent:\s*\w+\s*", "", msg, flags=re.IGNORECASE).strip()
        elif u_text.startswith("FILE:"):
            tag, msg = "FILE", text[5:].strip()
        elif u_text.startswith("TASK:"):
            tag, msg = "TASK", text[5:].strip()
        elif u_text.startswith("ERR:") or u_text.startswith("ERROR:"):
            tag, msg = "ERR", text[text.find(":") + 1:].strip()
        elif u_text.startswith("SYS:"):
            tag, msg = "SYS", text[4:].strip()

        self._server.broadcast("log_entry", {"tag": tag, "message": msg})
        self._server.broadcast("transcript_stream", {"speaker": tag.lower(), "text": msg, "done": True})

    def _on_stream_emitted(self, speaker: str, text: str, done: bool):
        self._server.broadcast("transcript_stream", {
            "speaker": (speaker or "user").lower(),
            "text": text,
            "done": done,
        })

    def _on_content_emitted(self, title: str, text: str):
        self._server.broadcast("content_display", {"title": title, "text": text})

    def _toggle_mute(self):
        self._muted = not self._muted
        self._server.broadcast("state_change", {"state": "MUTED" if self._muted else "LISTENING"})

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _do_interrupt(self):
        if self.on_interrupt:
            self.on_interrupt()

    def _create_desktop_shortcut(self):
        """Creates desktop shortcut on Windows / macOS / Linux."""
        script = Path(__file__).resolve().parent / "main.py"
        python = Path(sys.executable)
        desktop = self._get_desktop_dir()
        ico_path = CONFIG_DIR / "zezo.ico"
        if not ico_path.exists():
            ico_path = CONFIG_DIR / "jarvis.ico"

        try:
            if _OS == "Windows":
                pythonw = python.parent / "pythonw.exe"
                target = str(pythonw if pythonw.exists() else python)
                lnk = str(desktop / "ZEZO.lnk")
                icon_loc = str(ico_path) if ico_path.exists() else f"{target},0"
                self._create_lnk_windows(lnk, target, str(script), str(script.parent), icon_loc)
            self._on_log_emitted("SYS: Desktop shortcut created successfully.")
        except Exception as e:
            self._on_log_emitted(f"ERR: Shortcut creation failed — {e}")

    def _create_lnk_windows(self, lnk: str, target: str, args: str, work_dir: str, icon_loc: str):
        vbs = "\n".join([
            'Set ws = CreateObject("WScript.Shell")',
            f'Set sc = ws.CreateShortcut("{lnk}")',
            f'sc.TargetPath = "{target}"',
            f'sc.Arguments = Chr(34) & "{args}" & Chr(34)',
            f'sc.WorkingDirectory = "{work_dir}"',
            'sc.Description = "ZEZO Autonomous AI Operating System"',
            f'sc.IconLocation = "{icon_loc}"',
            'sc.Save',
        ])
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".vbs")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(vbs)
            proc = subprocess.Popen(
                ["wscript.exe", "/nologo", tmp],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )
            proc.wait(timeout=10)
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    @staticmethod
    def _get_desktop_dir() -> Path:
        home = Path.home()
        if _OS == "Windows":
            try:
                import ctypes
                from ctypes import wintypes
                class _GUID(ctypes.Structure):
                    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
                fid = _GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
                buf = ctypes.c_wchar_p()
                if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                    p = Path(buf.value)
                    ctypes.windll.ole32.CoTaskMemFree(buf)
                    if p.is_dir():
                        return p
            except Exception:
                pass
        return home / "Desktop"


class ZezoUI:
    """Thread-safe public interface for JarvisLive / main.py."""

    def __init__(self, face_path: str = ""):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._win = MainWindow()
        self.root = self
        self.mainloop = self.run

    def show(self):
        self._win.show()

    def run(self):
        self.show()
        sys.exit(self._app.exec())

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, val: bool):
        self._win._muted = val

    @property
    def on_text_command(self) -> Callable[[str], None] | None:
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb: Callable[[str], None] | None):
        self._win.on_text_command = cb

    @property
    def on_interrupt(self) -> Callable[[], None] | None:
        return self._win.on_interrupt

    @on_interrupt.setter
    def on_interrupt(self, cb: Callable[[], None] | None):
        self._win.on_interrupt = cb

    @property
    def on_remote_clicked(self) -> Callable[[], tuple[str, str] | None] | None:
        return self._win.on_remote_clicked

    @on_remote_clicked.setter
    def on_remote_clicked(self, cb: Callable[[], tuple[str, str] | None] | None):
        self._win.on_remote_clicked = cb

    @property
    def on_voice_change(self) -> Callable[[], None] | None:
        return self._win.on_voice_change

    @on_voice_change.setter
    def on_voice_change(self, cb: Callable[[], None] | None):
        self._win.on_voice_change = cb

    @property
    def on_pipeline_change(self) -> Callable[[], None] | None:
        return self._win.on_pipeline_change

    @on_pipeline_change.setter
    def on_pipeline_change(self, cb: Callable[[], None] | None):
        self._win.on_pipeline_change = cb

    @property
    def on_sleep_toggle(self) -> Callable[[bool], None] | None:
        return self._win.on_sleep_toggle

    @on_sleep_toggle.setter
    def on_sleep_toggle(self, cb: Callable[[bool], None] | None):
        self._win.on_sleep_toggle = cb

    @property
    def on_audio_device_change(self) -> Callable[[], None] | None:
        return self._win.on_audio_device_change

    @on_audio_device_change.setter
    def on_audio_device_change(self, cb: Callable[[], None] | None):
        self._win.on_audio_device_change = cb

    @property
    def on_push_to_talk(self) -> Callable[[bool], str] | None:
        return self._win.on_push_to_talk

    @on_push_to_talk.setter
    def on_push_to_talk(self, cb: Callable[[bool], str] | None):
        self._win.on_push_to_talk = cb

    @property
    def current_file(self) -> str:
        return getattr(self._win, "_current_file", "")

    @current_file.setter
    def current_file(self, val: str):
        self._win._current_file = str(val or "")

    @property
    def on_file_uploaded(self) -> Callable[[dict], None] | None:
        return self._win.on_file_uploaded

    @on_file_uploaded.setter
    def on_file_uploaded(self, cb: Callable[[dict], None] | None):
        self._win.on_file_uploaded = cb

    @property
    def ptt_hold(self) -> Callable[[bool], None] | None:
        return self._win.ptt_hold

    @ptt_hold.setter
    def ptt_hold(self, cb: Callable[[bool], None] | None):
        self._win.ptt_hold = cb

    def set_on_command(self, cb: Callable[[str], None]):
        self.on_text_command = cb

    def set_on_remote_clicked(self, cb: Callable[[], tuple[str, str] | None]):
        self.on_remote_clicked = cb

    def set_on_interrupt(self, cb: Callable[[], None]):
        self.on_interrupt = cb

    def set_on_voice_change(self, cb: Callable[[], None]):
        self.on_voice_change = cb

    def set_on_pipeline_change(self, cb: Callable[[], None]):
        self.on_pipeline_change = cb

    def set_on_sleep_toggle(self, cb: Callable[[bool], None]):
        self.on_sleep_toggle = cb

    def set_on_audio_device_change(self, cb: Callable[[], None]):
        self.on_audio_device_change = cb

    def set_on_push_to_talk(self, cb: Callable[[bool], str]):
        self.on_push_to_talk = cb

    def is_alive(self) -> bool:
        if not hasattr(self, "_win") or self._win is None:
            return False
        try:
            from PyQt6 import sip
            return not sip.isdeleted(self._win)
        except Exception:
            return False

    def set_state(self, state: str):
        if not self.is_alive():
            return
        try:
            self._win._state_sig.emit(state)
        except (RuntimeError, AttributeError):
            pass

    def set_audio_level(self, level: float):
        pass

    def set_mic_level(self, level: float):
        """Push the raw microphone level to the web UI's mic meter.

        Kept separate from set_audio_level (which the playback path uses for the
        output waveform) so ZEZO's own voice can never appear as "microphone".
        Called from the sounddevice callback thread, so it must stay cheap and
        never raise. Throttled to ~12 Hz.
        """
        now = time.monotonic()
        if now - getattr(self, "_last_mic_bc", 0.0) < 0.08:
            return
        self._last_mic_bc = now
        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast("mic_level", {"level": float(level)})
        except Exception:
            pass

    def write_log(self, text: str):
        if log_bus is not None:
            log_bus.emit("ERROR" if text.startswith("ERR:") else "INFO", "activity", text)
        if not self.is_alive():
            return
        try:
            self._win._log_sig.emit(text)
        except (RuntimeError, AttributeError):
            pass

    def stream_transcript(self, speaker: str, text: str, done: bool = False):
        if not self.is_alive():
            return
        try:
            self._win._stream_sig.emit(str(speaker), str(text), bool(done))
        except (RuntimeError, AttributeError):
            pass

    def show_content(self, title: str, text: str):
        if not self.is_alive():
            return
        try:
            self._win._content_sig.emit(title[:48], text[:4000])
        except (RuntimeError, AttributeError):
            pass

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def wait_for_api_key(self):
        pass

    def push_visemes(self, frames, hop: float, at: float) -> None:
        pass

    def notify_phone_connected(self) -> None:
        pass

    def prompt_reconfig(self):
        pass

    def show_camera_frame(self, img_bytes: bytes):
        pass

    def start_camera_stream(self):
        pass

    def stop_camera_stream(self):
        pass

    def show_quiz(self, topic: str, questions, grade=None):
        pass

    def hide_quiz(self):
        pass

    def show_confirm(self, title: str, detail: str) -> None:
        if not self.is_alive():
            return
        try:
            self._win._server.broadcast("confirm_request", {"title": title, "detail": detail})
        except (RuntimeError, AttributeError):
            pass

    def hide_confirm(self) -> None:
        if not self.is_alive():
            return
        try:
            self._win._server.broadcast("confirm_hide", {})
        except (RuntimeError, AttributeError):
            pass

    def show_review(self, title: str, summary: str, findings, unclear=None):
        pass

    @property
    def assistant_name(self) -> str:
        if not self.is_alive():
            return "Zezo"
        try:
            return self._win._assistant_name
        except (RuntimeError, AttributeError):
            return "Zezo"

    def __getattr__(self, name: str) -> Any:
        if not hasattr(self, "_win") or self._win is None:
            raise AttributeError(f"'ZezoUI' object has no attribute '{name}'")
        try:
            from PyQt6 import sip
            if sip.isdeleted(self._win):
                raise AttributeError(f"'ZezoUI' underlying window has been deleted, cannot access '{name}'")
            return getattr(self._win, name)
        except (RuntimeError, AttributeError):
            raise AttributeError(f"'ZezoUI' underlying window deleted or invalid, cannot access '{name}'")


# Alias for backward compatibility
JarvisUI = ZezoUI
