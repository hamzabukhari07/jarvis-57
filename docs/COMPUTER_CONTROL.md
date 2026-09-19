# JARVIS — Computer Control Architecture

## Overview

JARVIS controls the operating system through a set of tools that use different Python libraries and OS APIs depending on the platform.

## Control Categories

### System Settings (actions/computer_settings.py)

| Action | Windows | macOS | Linux | Library |
|--------|---------|-------|-------|---------|
| Volume up/down | `pyautogui.press("volumeup")` | `osascript` | `pactl` | pyautogui / osascript / pactl |
| Brightness | `pyautogui` | `osascript` | `brightnessctl` | pyautogui / osascript |
| WiFi toggle | `pycaw` / `netsh` | `networksetup` | `nmcli` | pycaw / subprocess |
| Power (shutdown/restart) | `subprocess` | `subprocess` | `subprocess` | subprocess |
| Dark mode | `pywinauto` | `defaults write` | `gsettings` | Platform-specific |
| Undo settings | State capture + restore | State capture + restore | State capture + restore | core/undo.py |

**File:** `actions/computer_settings.py` (962 lines)

### System Control (actions/computer_control.py)

| Action | Windows | macOS | Linux | Library |
|--------|---------|-------|-------|---------|
| Keyboard shortcuts | `pyautogui` | `pyautogui` | `pyautogui` | pyautogui |
| Mouse control | `pyautogui` | `pyautogui` | `pyautogui` | pyautogui |
| Window management | `pygetwindow` | `subprocess` | `subprocess` | pygetwindow |
| Clipboard | `pyperclip` | `pyperclip` | `pyperclip` | pyperclip |
| Taskbar | `pywin32` | `subprocess` | `subprocess` | Platform-specific |
| Desktop organize | `shutil`, `os` | `shutil`, `os` | `shutil`, `os` | Standard library |

**File:** `actions/computer_control.py` (589 lines)

### Application Launching (actions/open_app.py)

```python
# Per-OS name map
APP_NAMES = {
    "Windows": {"chrome": "chrome", "vscode": "code", ...},
    "Darwin":  {"chrome": "Google Chrome", ...},
    "Linux":   {"chrome": "google-chrome", ...},
}
```

Uses `subprocess.Popen` with `CREATE_NO_WINDOW` on Windows.

### Browser Control (actions/browser_control.py)

Uses **Playwright** for browser automation:
```python
from playwright.sync_api import sync_playwright
# Launch Chromium/Firefox, navigate, click, type
```

### Vision (actions/screen_processor.py)

| Source | Library | Format |
|--------|---------|--------|
| Screen capture | `mss` + `PIL` | JPEG (max 1280x720, quality 82) |
| Webcam | `opencv-python` (cv2) | JPEG |
| Compression | `PIL` | Resized, compressed |

### How Vision Works

```python
# Capture
img_b, mime_t = _capture_screen()  # or _capture_camera()
# Returns (bytes, "image/jpeg")
# Inject into Gemini session via send_client_content()
# Image carried with the same exchange as the tool result
```

**Important**: Vision images are labelled with their source. A webcam frame shows the USER; a screen capture shows the COMPUTER.

## Platform-Specific Details

### Windows
- **Volume**: `pycaw` library or `pyautogui`
- **Brightness**: `pywinauto` or registry
- **WiFi**: `netsh` / `subprocess`
- **Window management**: `pygetwindow`, `pywin32`
- **Keyboard/mouse**: `pyautogui`
- **Process control**: `subprocess`, `psutil`
- **Power management**: `subprocess` (shutdown, restart)
- **Special**: `comtypes`, `wmi` for system queries

### macOS
- **Volume**: `osascript` (AppleScript)
- **Brightness**: `osascript`
- **WiFi**: `networksetup`
- **Window management**: `subprocess` (AppleScript)
- **Keyboard/mouse**: `pyautogui`
- **Special**: `LaunchAgent` for auto-start

### Linux
- **Volume**: `pactl` (PulseAudio)
- **Brightness**: `brightnessctl`
- **WiFi**: `nmcli` (NetworkManager)
- **Window management**: `subprocess`
- **Keyboard/mouse**: `pyautogui`
- **Special**: `systemd` for auto-start and reminders

## Safety and Confirmation

**File:** `core/confirm.py`

Irreversible actions go through the confirmation gate:
```python
# shutdown, restart, toggle_wifi → confirm.request()
# UI shows CONFIRM/CANCEL banner
# Only user pressing CONFIRM runs the action
# Model cannot forge confirmation (token issued by UI)
```

## Undo System

**File:** `core/undo.py`

```python
from core.undo import push_undo

# In action handlers:
old = volume_get()
volume_set(new)
push_undo(f"volume → {new}%", lambda: volume_set(old))
```

- Stack depth: 10 entries max
- Covers: file operations, settings changes, desktop organization
- Files over 1 MB excluded from undo (memory limit)
- `organize_desktop` has special journal-based undo

## Summary

```
Control tools: computer_settings, computer_control, open_app, browser_control
Libraries: pyautogui, pycaw, pywin32, pygetwindow, playwright, subprocess
Platform-specific: Each action has per-OS branches
Safety: confirm.py for irreversible actions
Undo: core/undo.py stack for reversible actions
Vision: mss + cv2 + PIL for screen/webcam capture
```