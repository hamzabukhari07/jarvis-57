# JARVIS — Platform Support

## Overview

JARVIS runs on **Windows 10/11, macOS, and Linux**. Most code is platform-agnostic, but specific features use platform-specific implementations.

## Platform Detection

```python
import platform
OS = platform.system()  # "Windows" | "Darwin" | "Linux"
```

## Push-to-Talk

### Windows
- **Mechanism**: `ctypes.windll.user32.GetAsyncKeyState` polling
- **Scope**: Global (works while any app has focus)
- **Rate**: 30 Hz
- **Debounce**: 60ms
- **Dependencies**: None (pure ctypes)
- **Code**: `core/hotkey.py:_poll_loop()`

### macOS
- **Mechanism**: Qt shortcut (QKeySequence)
- **Scope**: Window-scoped (app must have focus)
- **Limitation**: No global key state without a new package or accessibility permissions
- **Code**: `core/hotkey.py` — falls back to window mode
- **Honesty**: App says "works while this window is focused" in the log

### Linux
- **Mechanism**: Qt shortcut (QKeySequence)
- **Scope**: Window-scoped
- **Same limitation as macOS**

## Audio

### Windows
- **Input host API**: DirectSound
- **Output host API**: MME
- **Device enumeration**: 41 entries filtered to ~8
- **Volume**: `pycaw` or `pyautogui`
- **Special**: Default device moves when headset plugged in

### macOS
- **Host API**: Core Audio (only option)
- **Device enumeration**: Clean, one entry per device
- **Volume**: `osascript` (AppleScript)
- **Brightness**: `osascript`

### Linux
- **Host APIs**: PulseAudio/PipeWire/ALSA/Jack
- **Device enumeration**: Clean with PulseAudio
- **Volume**: `pactl`
- **Brightness**: `brightnessctl`
- **WiFi**: `nmcli`

## System Controls

### Windows
- **Volume**: `pycaw` / `pyautogui.press("volumeup")`
- **Brightness**: `pywinauto` or registry
- **WiFi**: `netsh` / `subprocess`
- **Dark mode**: Registry or `pywinauto`
- **Window management**: `pygetwindow`, `pywin32`
- **Shutdown**: `subprocess` (shutdown command)
- **Auto-start**: Windows Registry

### macOS
- **Volume**: `osascript`
- **Brightness**: `osascript`
- **WiFi**: `networksetup`
- **Dark mode**: `defaults write`
- **Window management**: `subprocess` (AppleScript)
- **Shutdown**: `subprocess` (shutdown command)
- **Auto-start**: LaunchAgent
- **Reminders**: `osascript` + LaunchAgent

### Linux
- **Volume**: `pactl`
- **Brightness**: `brightnessctl`
- **WiFi**: `nmcli`
- **Dark mode**: `gsettings`
- **Window management**: `subprocess`
- **Shutdown**: `subprocess`
- **Auto-start**: `.desktop` file
- **Reminders**: `systemd-run` or `at`

## Browser Automation

| Aspect | All Platforms |
|--------|---------------|
| Library | Playwright |
| Browsers | Chromium + Firefox |
| Installation | `python setup.py` |
| Platform-specific | macOS needs `playwright install webkit` for Safari |

## Auto-Start

### Windows
- Registry entry
- `pywin32_postinstall.py`
- Falls back to slower method if pywin32 not registered

### macOS
- `LaunchAgent` plist
- `osascript` for notifications

### Linux
- `.desktop` file in autostart directory
- `xdg-open` for URLs
- `systemd` or `at` for reminders

## Platform-Specific Libraries

### Windows-Only
- `comtypes` — COM interface
- `pycaw` — Core Audio Windows
- `win10toast` — Toast notifications
- `pywinauto` — UI automation
- `pywin32` — Windows API
- `wmi` — Windows Management Instrumentation

### macOS-Only
- `osascript` — AppleScript (built-in)
- `LaunchAgent` — Built-in

### Linux-Only
- `pactl` — PulseAudio
- `brightnessctl` — Brightness control
- `nmcli` — NetworkManager
- `xdg-utils` — Open URLs

## Summary

```
Windows: Global push-to-talk, DirectSound/MME, pycaw/pywin32, Registry auto-start
macOS: Window-scoped PTT, Core Audio, osascript, LaunchAgent
Linux: Window-scoped PTT, PulseAudio/PipeWire, pactl/brightnessctl, .desktop auto-start
Playwright: Same on all platforms
pywin32: Windows only
All code: Platform-agnostic via platform.system() checks
```