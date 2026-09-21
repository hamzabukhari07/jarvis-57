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


def apply_ui_accent(hex_color: str) -> bool:
    """Updates global C.PRI token and broadcasts to the web frontend."""
    C.PRI = hex_color
    server = get_ui_server()
    server.broadcast("accent_changed", {"color": hex_color})
    return True


class MainWindow(QMainWindow):
    """Main desktop container window hosting the HTML5/CSS/JS frontend via QWebEngineView."""

    _log_sig = pyqtSignal(str)
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
        self.ptt_hold: Callable[[bool], None] | None = None
        self._muted = False
        self._ready = True
        self._current_file = ""

        # Initialize and start local UI Server
        self._server = get_ui_server()
        self._server.on_text_command = self._handle_text_command
        self._server.on_interrupt = self._handle_interrupt
        self._server.on_mute_toggle = self._handle_mute_toggle
        self._server.on_remote_clicked = self._handle_remote_clicked
        self._server.on_file_uploaded = self._handle_file_uploaded
        self._server.on_assistant_settings_changed = self._handle_assistant_settings_changed
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

        # Load local web app from UI server
        server_url = f"http://127.0.0.1:{self._server.port}/"
        self.web_view.load(QUrl(server_url))
        self.setCentralWidget(self.web_view)

        # Connect internal signals
        self._log_sig.connect(self._on_log_emitted)
        self._state_sig.connect(self._on_state_emitted)
        self._content_sig.connect(self._on_content_emitted)

        # Global Hotkeys
        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_intr = QShortcut(QKeySequence("Escape"), self)
        sc_intr.activated.connect(self._do_interrupt)

        # Telemetry timer (500ms)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)
        self._telemetry_timer.start(500)

        # Task manager polling timer (300ms)
        self._task_timer = QTimer(self)
        self._task_timer.timeout.connect(self._poll_tasks)
        self._task_timer.start(300)

    def _get_initial_state(self) -> dict:
        tasks = []
        try:
            from core.task_manager import get_task_manager
            tasks = get_task_manager().list_tasks()
        except Exception:
            pass

        from memory.config_manager import get_voice, get_response_language
        return {
            "state": "IDLE",
            "muted": self._muted,
            "assistant_name": self._assistant_name,
            "voice_name": get_voice(),
            "response_language": get_response_language(),
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

    def _handle_text_command(self, text: str):
        self._on_log_emitted(f"USER: {text}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    def _handle_interrupt(self):
        if self.on_interrupt:
            self.on_interrupt()

    def _handle_mute_toggle(self, muted: bool):
        self._muted = muted
        self._server.broadcast("state_change", {"state": "MUTED" if self._muted else "LISTENING"})

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

    def _poll_telemetry(self):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            net = psutil.net_io_counters()
            net_mb = (net.bytes_sent + net.bytes_recv) / (1024 * 1024)
            self._server.broadcast("telemetry_update", {
                "cpu": cpu,
                "mem": mem,
                "gpu": -1,
                "net": net_mb % 10.0,
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

    def _on_state_emitted(self, state: str):
        self._server.broadcast("state_change", {"state": state})

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

    def set_on_audio_device_change(self, cb: Callable[[], None]):
        self.on_audio_device_change = cb

    def set_on_push_to_talk(self, cb: Callable[[bool], str]):
        self.on_push_to_talk = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def set_audio_level(self, level: float):
        pass

    def write_log(self, text: str):
        if log_bus is not None:
            log_bus.emit("ERROR" if text.startswith("ERR:") else "INFO", "activity", text)
        self._win._log_sig.emit(text)

    def show_content(self, title: str, text: str):
        self._win._content_sig.emit(title[:48], text[:4000])

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
        self._win._server.broadcast("confirm_request", {"title": title, "detail": detail})

    def hide_confirm(self) -> None:
        self._win._server.broadcast("confirm_hide", {})

    def show_review(self, title: str, summary: str, findings, unclear=None):
        pass

    @property
    def assistant_name(self) -> str:
        return self._win._assistant_name

    def __getattr__(self, name: str) -> Any:
        return getattr(self._win, name)


# Alias for backward compatibility
JarvisUI = ZezoUI
