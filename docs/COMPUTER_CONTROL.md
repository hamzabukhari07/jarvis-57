# ZEZO OS — Modular Computer Control Architecture

> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Principle:** *"Observe only when necessary — Escalate perception, don't waterfall it."*

## Overview

ZEZO executes computer control through modular drivers under `core/computer/` with 4-tier escalated perception and execution:
$$\text{L0: Fast Win32 State (1ms)} \longrightarrow \text{L1: Windows UIA (<15ms)} \longrightarrow \text{L1.5: Multilingual RapidOCR (<80ms)} \longrightarrow \text{L2: Gemini Vision (~2.0s)}$$

---

## Driver Modules (`core/computer/`)

| Module | Purpose | Key Capabilities |
| :--- | :--- | :--- |
| `windows_native.py` | Win32 OS Integration | Window enumeration, focus switching (`AttachThreadInput`), physical bounds calibration via `DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS=9)`, safe closing (`WM_CLOSE`), DPI awareness initialization (`SetProcessDPIAware`). |
| `windows_uia.py` | Windows UI Automation (L1 UIA) | Fast accessibility tree inspection (< 15ms, `searchDepth=6`) inside STA COM `ThreadPoolExecutor` worker with strict 0.8s timeout boundaries. Finds native buttons, edits, tabs, and list items. |
| `ocr_engine.py` | Multilingual CPU OCR (L1.5 RapidOCR) | Sub-80ms CPU ONNX text detection and spatial bounding box extraction with **0 MB GPU VRAM footprint** (~80MB RAM). Unicode Urdu/Arabic normalization `normalize_urdu()` (tashkeel stripping, yeh/kaf/heh unification) and fuzzy matching (`fuzzy_threshold=0.75`). |
| `pyautogui_driver.py` | Hardware Input Driver | Mouse/keyboard input with `POST_MOVE_VERIFY`, action aliases (`enter`, `escape`, `space`, `backspace`, `tab`, `delete`), and safe multilingual Unicode typing. |

---

## 3-Tier Perception Escalation (`actions/computer_control.py`)
When targeting an on-screen control or text label (`screen_click`, `click`, `double_click` with a `description`):
1. **Tier 1 (L1 UIA):** Inspects the active window's Windows UI Automation tree (<15ms). Finds native buttons ("Save", "Cancel", "File"), edit controls, and tabs.
2. **Tier 2 (L1.5 RapidOCR):** Runs local CPU RapidOCR on the active window crop (<80ms). Finds rendered text in canvas/web apps (Figma "Width", "Fill", web canvas strings, Urdu text) without cloud round-trips.
3. **Tier 3 (L2 Gemini Multimodal Vision):** Fallback to Gemini Multimodal Vision (~2.0s) only for graphical icons, color swatches, and complex visual scenes.

---

## Hotkey Anti-Loop Circuit Breaker & Safety Directives
- **In-Turn Circuit Breaker (`core/action_loader.py`):** Automatically detects and aborts tight repetitive hotkey loops (>4 identical key actions within 10s, e.g. `shift+tab` spam in canvas editors).
- **Chat App Governance (`core/prompt.txt`):** When typing in WhatsApp/Telegram, ZEZO only types the message text and strictly requires explicit user confirmation ("bhejo", "send it") before pressing enter.
- **Contextual GUI Undo:** Commands to undo in active GUI applications (Figma, VS Code, Browser) map directly to `Ctrl+Z` hotkey dispatches instead of filesystem snapshots.

---

## Safe Unicode Typing & Buffer Preservation
- Automatically detects non-ASCII text (Urdu, Arabic, Hindi, emojis, symbols) or multiline strings.
- Stashes the user's prior clipboard string in memory.
- Writes the text to system clipboard and triggers native paste (`Ctrl+V` / `Cmd+V`).
- Restores the previous user clipboard buffer after paste (`RESTORE_CLIPBOARD_AFTER_PASTE = True`).

**Screen-grounded clicks:** `click`, `double_click`, `right_click` accept either `x,y` OR a `description` — when only a description is given they automatically escalate through L1 UIA ➔ L1.5 RapidOCR ➔ L2 Vision, clicking the found coordinates. `screen_click` / `screen_double_click` are the explicit description-based actions; `smart_click` is accepted as an alias. If the element is not found, the tool returns a clear not-found status rather than clicking blind.

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

**Honest launch (2026-09-25):** opening a file in a named app no longer runs the fragile `cmd /c start "" "code" "<file>"` (which silently failed because VS Code's `code` shim is not on PATH, while the tool still reported success). `_resolve_windows_launcher()` now finds the real executable (e.g. `%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe`) and launches it with the file; if it cannot resolve the app it opens the file with the OS default and says so — it never claims an app opened when it did not.

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