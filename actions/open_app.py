import os
import re
import time
import subprocess
import platform
import shutil
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {

    "chrome":             {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                 "Darwin": "Firefox",              "Linux": "firefox"},
    "edge":               {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                   "Darwin": "Brave Browser",        "Linux": "brave-browser"},
    "safari":             {"Windows": "msedge",                  "Darwin": "Safari",               "Linux": "firefox"},
    "opera":              {"Windows": "opera",                   "Darwin": "Opera",                "Linux": "opera"},
    "whatsapp":           {"Windows": "WhatsApp",                "Darwin": "WhatsApp",             "Linux": "whatsapp"},
    "telegram":           {"Windows": "Telegram",                "Darwin": "Telegram",             "Linux": "telegram"},
    "discord":            {"Windows": "Discord",                 "Darwin": "Discord",              "Linux": "discord"},
    "slack":              {"Windows": "Slack",                   "Darwin": "Slack",                "Linux": "slack"},
    "zoom":               {"Windows": "Zoom",                    "Darwin": "zoom.us",              "Linux": "zoom"},
    "teams":              {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "skype":              {"Windows": "skype",                   "Darwin": "Skype",                "Linux": "skype"},
    "signal":             {"Windows": "signal",                  "Darwin": "Signal",               "Linux": "signal"},
    "spotify":            {"Windows": "Spotify",                 "Darwin": "Spotify",              "Linux": "spotify"},
    "vlc":                {"Windows": "vlc",                     "Darwin": "VLC",                  "Linux": "vlc"},
    "netflix":            {"Windows": "Netflix",                 "Darwin": "Netflix",              "Linux": "firefox"},
    "vscode":             {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "vs code":            {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "visual studio code": {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "code":               {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "terminal":           {"Windows": "wt",                      "Darwin": "Terminal",             "Linux": "x-terminal-emulator"},
    "cmd":                {"Windows": "cmd.exe",                 "Darwin": "Terminal",             "Linux": "bash"},
    "powershell":         {"Windows": "powershell.exe",          "Darwin": "Terminal",             "Linux": "bash"},
    "postman":            {"Windows": "Postman",                 "Darwin": "Postman",              "Linux": "postman"},
    "git":                {"Windows": "git-bash",                "Darwin": "Terminal",             "Linux": "bash"},
    "figma":              {"Windows": "Figma",                   "Darwin": "Figma",                "Linux": "figma"},
    "blender":            {"Windows": "blender",                 "Darwin": "Blender",              "Linux": "blender"},
    "word":               {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice":        {"Windows": "soffice",                 "Darwin": "LibreOffice",          "Linux": "libreoffice"},
    "notepad":            {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "textedit":           {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "explorer":           {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "finder":             {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "task manager":       {"Windows": "taskmgr.exe",             "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",            "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "calculator":         {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "calc":               {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "paint":              {"Windows": "mspaint.exe",             "Darwin": "Preview",              "Linux": "gimp"},
    "control panel":      {"Windows": "control.exe",             "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "instagram":          {"Windows": "Instagram",               "Darwin": "Instagram",            "Linux": "firefox"},
    "tiktok":             {"Windows": "TikTok",                  "Darwin": "TikTok",               "Linux": "firefox"},
    "notion":             {"Windows": "Notion",                  "Darwin": "Notion",               "Linux": "notion"},
    "obsidian":           {"Windows": "Obsidian",                "Darwin": "Obsidian",             "Linux": "obsidian"},
    "capcut":             {"Windows": "CapCut",                  "Darwin": "CapCut",               "Linux": "capcut"},
    "steam":              {"Windows": "steam",                   "Darwin": "Steam",                "Linux": "steam"},
    "epic":               {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},
    "epic games":         {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)

    # Check for multi-word phrase matching (e.g. "open visual studio code please")
    for alias_key, os_map in _APP_ALIASES.items():
        if " " in alias_key and alias_key in key:
            return os_map.get(_SYSTEM, raw)

    return raw  

_WIN_URI_MAP = {
    "whatsapp": "whatsapp:",
    "spotify": "spotify:",
    "telegram": "tg:",
    "discord": "discord:",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "explorer": "explorer.exe",
    "settings": "ms-settings:",
}

def _find_windows_start_menu_shortcut(app_name: str) -> Path | None:
    app_lower = app_name.lower().strip()
    search_dirs = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        search_dirs.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if programdata:
        search_dirs.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

    for s_dir in search_dirs:
        if s_dir.exists():
            for lnk in s_dir.rglob("*.lnk"):
                stem = lnk.stem.lower()
                if app_lower == stem or app_lower in stem:
                    return lnk
    return None

def _resolve_windows_launcher(app_name: str) -> str | None:
    """Resolve a concrete Windows executable for an app so launching is verifiable.

    The old path branch ran `cmd /c start "" "code" "<file>"` and assumed success.
    VS Code's `code` shim is usually NOT on PATH, so the file never opened while we
    still reported success. This finds the real binary (or the code.cmd shim).
    """
    key = (app_name or "").lower().strip()
    if key in ("code", "vscode", "vs code", "visual studio code"):
        candidates: list[Path] = []
        for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
            if base:
                candidates.append(Path(base) / "Programs" / "Microsoft VS Code" / "Code.exe")
                candidates.append(Path(base) / "Microsoft VS Code" / "Code.exe")
        for c in candidates:
            if c.exists():
                return str(c)
        return shutil.which("code.cmd") or shutil.which("code")
    return shutil.which(app_name) or shutil.which((app_name or "").split(".")[0])


def _launch_windows(app_name: str) -> bool:
    clean_name = app_name.lower().strip()

    # 1. System PATH or direct binary
    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(
                app_name,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] subprocess failed: {e}")

    # 2. Known UWP / URI protocol
    uri = _WIN_URI_MAP.get(clean_name) or (app_name if ":" in app_name else None)
    if uri:
        try:
            os.startfile(uri)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] startfile uri {uri} failed: {e}")

    # 3. Start Menu shortcut (.lnk)
    shortcut = _find_windows_start_menu_shortcut(app_name)
    if shortcut:
        try:
            os.startfile(str(shortcut))
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] startfile shortcut {shortcut} failed: {e}")

    # 4. Fallback: Start Menu key search
    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(app_name, interval=0.03)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Start Menu search failed: {e}")

    return False


def _launch_macos(app_name: str) -> bool:

    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["open", "-a", f"{app_name}.app"],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Spotlight failed: {e}")

    return False


_LINUX_TERMINAL_FALLBACKS = [
    "x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
    "xterm", "lxterminal", "mate-terminal", "tilix", "alacritty", "kitty",
]

def _launch_linux(app_name: str) -> bool:

    # terminal emulators: try common ones in order
    if app_name in ("x-terminal-emulator", "gnome-terminal", "terminal"):
        for term in _LINUX_TERMINAL_FALLBACKS:
            if shutil.which(term):
                try:
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    continue

    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-")) or
        shutil.which(app_name.lower().replace(" ", "_"))
    )
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(
            ["xdg-open", app_name],
            capture_output=True, timeout=5
        )
        return True
    except Exception:
        pass

    for desktop_name in [
        app_name.lower(),
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", ""),
    ]:
        try:
            result = subprocess.run(
                ["gtk-launch", desktop_name],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}

def close_application_by_name(app_name: str) -> bool:
    target = _normalize(app_name).lower()
    clean_name = app_name.lower().strip()

    # Never allow closing self through open_app
    if clean_name in ("zezo", "jarvis", "zezo os"):
        return False

    my_pid = os.getpid()

    # Special handling for Windows Explorer to avoid killing Windows Desktop Shell
    if _SYSTEM == "Windows" and clean_name in ("explorer", "file explorer", "folder"):
        try:
            script = "(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.Quit() }"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if _SYSTEM == "Windows" else 0,
            )
            return True
        except Exception:
            return False

    if _SYSTEM == "Windows":
        candidates = [target]
        if not target.endswith(".exe"):
            candidates.append(f"{target}.exe")
        if clean_name == "control panel":
            candidates.append("control.exe")

        for exe_name in candidates:
            try:
                res = subprocess.run(["taskkill", "/IM", exe_name, "/F"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        if _PSUTIL:
            try:
                killed = False
                for p in psutil.process_iter(['name', 'pid']):
                    if p.info.get('pid') == my_pid:
                        continue
                    pname = (p.info.get('name') or '').lower()
                    if clean_name in pname or target in pname or (clean_name == "control panel" and "control.exe" in pname):
                        p.kill()
                        killed = True
                if killed:
                    return True
            except Exception:
                pass

    elif _SYSTEM in ("Darwin", "Linux"):
        try:
            res = subprocess.run(["pkill", "-f", clean_name], capture_output=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # Window closing fallback
    try:
        from actions.computer_control import _safe_close_window
        res = _safe_close_window(app_name)
        if res.startswith("Closed window:"):
            return True
    except Exception:
        pass

    return False


def _format_open_confirmation(app_name: str) -> str:
    try:
        from core.computer import windows_native
        from actions.screen_processor import get_active_window_context
        # Post-Launch Focus Guard: poll for up to 500ms to ensure the launched app gains focus
        for _ in range(5):
            ctx = get_active_window_context()
            title = ctx.get("foreground_title", "")
            proc = ctx.get("foreground_process", "")
            if not windows_native.is_self_or_console_window(ctx.get("hwnd")):
                if title:
                    return f"Opened {app_name} (Focused: '{title}' [{proc}])."
            time.sleep(0.1)

        # If still not focused, attempt explicit focus attachment
        windows_native.focus_window(app_name)
        ctx = get_active_window_context()
        title = ctx.get("foreground_title", "")
        proc = ctx.get("foreground_process", "")
        if title:
            return f"Opened {app_name} (Focused: '{title}' [{proc}])."
    except Exception:
        pass
    return f"Opened {app_name}."


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    app_name = params.get("app_name", "").strip()
    action = params.get("action", "open").lower().strip()

    if not app_name:
        return "No application name provided."

    clean_token = re.sub(r"[\s_\-]+", "", (app_name or "").lower())

    # ── Scranton Agent Office Screen Voice Navigation (Full Main Screen) ──
    if clean_token in ("officeview", "officefloor", "agentview", "agentsview", "agentviews", "fleet", "fleetdeck", "fleetview", "scrantonoffice", "scranton", "agents", "office"):
        if action in ("close", "exit", "stop", "hide", "back"):
            try:
                from core.ui_server import get_ui_server
                get_ui_server().broadcast("switch_view", {"view": "home"})
                if player:
                    player.write_log("[open_app] Closed Scranton Agent Office Floor and returned to Tactical Dashboard")
                return "Closed office view and returned to Tactical Dashboard."
            except Exception as e:
                return f"Failed to switch to dashboard: {e}"

        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast("switch_view", {"view": "office"})
            if player:
                player.write_log("[open_app] Switched to Scranton Agent Office Floor screen")
            return "Switched display to Scranton Agent Office Floor screen."
        except Exception as e:
            return f"Failed to switch to office view: {e}"

    # ── Tactical Dashboard / Home Screen Voice Navigation (Full Main Screen) ──
    if clean_token in ("homeview", "homescreen", "dashboard", "tacticalview", "tactical", "home"):
        try:
            from core.ui_server import get_ui_server
            get_ui_server().broadcast("switch_view", {"view": "home"})
            if player:
                player.write_log("[open_app] Switched to Tactical Dashboard screen")
            return "Switched display to Tactical Dashboard screen."
        except Exception as e:
            return f"Failed to switch to home view: {e}"

    if action in ("close", "exit", "kill", "terminate", "stop"):
        if close_application_by_name(app_name):
            if player:
                player.write_log(f"[close_app] {app_name}")
            return f"Closed {app_name}."
        return f"Could not find or close {app_name}."

    normalized = _normalize(app_name)

    path_arg = params.get("path") or params.get("target") or ""

    if path_arg:
        raw_p = str(path_arg).strip().strip("\"'")
        norm_p = raw_p.replace("\\", "/")
        parts = [x for x in norm_p.split("/") if x]

        p = Path(raw_p).expanduser()
        if not p.is_absolute():
            if parts and parts[0].lower() in ("desktop", "downloads", "documents"):
                if len(parts) > 1:
                    p = Path.home() / parts[0].capitalize() / Path(*parts[1:])
                else:
                    p = Path.home() / parts[0].capitalize()
            else:
                desk_cand = Path.home() / "Desktop" / raw_p
                cwd_cand = Path.cwd() / raw_p
                if desk_cand.exists():
                    p = desk_cand
                elif cwd_cand.exists():
                    p = cwd_cand
                else:
                    p = desk_cand

        try:
            if _SYSTEM == "Windows":
                exe = _resolve_windows_launcher(normalized)
                if exe:
                    proc = subprocess.Popen([exe, str(p)])
                    time.sleep(1.2)
                    if proc.poll() is None:
                        if player:
                            player.write_log(f"[open_app] {app_name} → {p}")
                        return f"Opened {p.name} in {app_name}."
                # Could not resolve the requested app — open with the OS default so
                # the file still opens, and report the truth instead of claiming success.
                os.startfile(str(p))
                if player:
                    player.write_log(f"[open_app] {p} → default app")
                return f"Opened {p.name} with the default application (could not confirm {app_name})."
            if _SYSTEM == "Darwin":
                subprocess.Popen(["open", "-a", normalized, str(p)])
                return f"Opened {p.name} in {app_name}."
            subprocess.Popen([normalized, str(p)])
            return f"Opened {p.name} in {app_name}."
        except Exception as e:
            print(f"[open_app] Error launching with path: {e}")
            try:
                os.startfile(str(p))
                return f"Opened {p.name} with the default application."
            except Exception as e2:
                return f"Failed to open {p}: {e2}"

    if not path_arg:
        try:
            from actions.computer_control import _focus_window
            for cand in (app_name, normalized):
                if cand:
                    res = _focus_window(cand)
                    if res.startswith("Focused window:"):
                        if player:
                            player.write_log(f"[open_app] Focused existing window: {app_name}")
                        print(f"[open_app] Brought existing window to foreground: {res}")
                        return _format_open_confirmation(app_name)
        except Exception as e:
            print(f"[open_app] Existing window check error: {e}")

    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    print(f"[open_app] Launching: '{app_name}' -> '{normalized}' ({_SYSTEM})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        if launcher(normalized):
            return _format_open_confirmation(app_name)
        if normalized.lower() != app_name.lower():
            if launcher(app_name):
                return _format_open_confirmation(app_name)
        return (
            f"Could not confirm that {app_name} launched. "
            f"It may still be loading, or it might not be installed."
        )
    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "open_app",
    "description": "Opens or closes any application or opens specific files/folders with an app (e.g. open folder 'in' in VS Code). Always call this tool.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {
                "type": "STRING",
                "description": "Exact name of the application (e.g. 'Visual Studio Code', 'Notepad', 'Chrome', 'Spotify')"
            },
            "path": {
                "type": "STRING",
                "description": "Optional file or folder path to open directly in the app (e.g. 'C:/Users/Hamza/Desktop/in' or 'Desktop/in')"
            },
            "action": {
                "type": "STRING",
                "enum": ["open", "close"],
                "description": "Whether to 'open' (default) or 'close' the application."
            }
        },
        "required": [
            "app_name"
        ]
    },
    "handler": open_app,
}
