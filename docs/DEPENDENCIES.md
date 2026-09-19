# JARVIS — Dependencies

## Overview

JARVIS uses a single `requirements.txt` file with OS-specific markers. `setup.py` installs dependencies filtered by OS.

**Files**: `requirements.txt`, `setup.py`

## Python Version

| Requirement | Value |
|-------------|-------|
| Minimum | Python 3.11 |
| Maximum tested | Python 3.13 |
| Newer versions | Warning, not fatal |

## Dependency Categories

### Core: UI, Audio, Gemini Live

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `PyQt6` | `>=6.6,<7` | HUD, avatar, all UI widgets | `ui.py`, `core/avatar.py` |
| `sounddevice` | `>=0.4,<1` | Audio I/O (PortAudio) | `main.py`, `core/audio_devices.py` |
| `numpy` | `>=1.24,<3` | Audio processing, FFT, avatar math | `main.py`, `core/viseme.py`, `core/echo.py`, `core/avatar.py` |
| `google-genai` | `>=2.8.0,<3` | Gemini Live + REST API | `main.py`, `core/gemini.py` |

### Web Search & Browser Control

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `requests` | `>=2.31,<3` | HTTP requests | `core/gemini.py`, `actions/*.py` |
| `beautifulsoup4` | `>=4.12,<5` | HTML parsing | `actions/web_search.py` |
| `playwright` | `>=1.40,<2` | Browser automation | `actions/browser_control.py` |

### Automation / Input Control

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `pyautogui` | (any) | Keyboard/mouse simulation | `actions/computer_control.py`, `actions/computer_settings.py` |
| `pyperclip` | (any) | Clipboard access | `actions/computer_control.py` |
| `pygetwindow` | (any) | Window management | `actions/computer_control.py` |

### Vision & Media

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `Pillow` | `>=10,<13` | Image processing | `actions/screen_processor.py` |
| `opencv-python` | `>=4.8,<5` | Webcam capture | `actions/screen_processor.py` |
| `mss` | `>=9,<11` | Fast screen capture | `actions/screen_processor.py` |

### System, Files & Documents

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `psutil` | `>=5.9,<8` | System metrics, process info | `actions/system_monitor.py`, `ui.py` |
| `send2trash` | (any) | Safe file deletion | `actions/file_controller.py` |
| `youtube-transcript-api` | (any) | YouTube transcript | `actions/youtube_video.py` |
| `python-pptx` | (any) | PowerPoint reading | `actions/file_processor.py` |
| `openpyxl` | (any) | Excel reading | `actions/file_processor.py` |

### Remote Dashboard

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `fastapi` | `>=0.110,<1` | HTTP server | `dashboard/server.py` |
| `uvicorn[standard]` | `>=0.27,<1` | ASGI server | `dashboard/server.py` |
| `cryptography` | `>=42,<50` | AES-256-CBC encryption | `dashboard/server.py` |
| `python-multipart` | `>=0.0.9,<1` | File uploads | `dashboard/server.py` |
| `qrcode[pil]` | `>=7,<9` | QR code generation | `dashboard/server.py` |

### Plugin Extras

| Package | Purpose | Used By |
|---------|---------|---------|
| `google-api-python-client` | Gmail/Calendar OAuth | `plugins/_google_core.py` |
| `google-auth-oauthlib` | OAuth flow | `plugins/_google_core.py` |
| `tinytuya` | Tuya/Smart Life smart lights | `plugins/` |
| `paho-mqtt` | MQTT printers | `plugins/` |
| `pynvml` | NVIDIA GPU monitoring | `actions/system_monitor.py`, `ui.py` |

### Web Search Fallback

| Package | Version | Purpose |
|---------|---------|---------|
| `ddgs` | `>=9,<10` | DuckDuckGo search |
| `pdfplumber` | (any) | PDF text extraction |
| `PyPDF2` | (any) | PDF fallback reader |
| `python-docx` | (any) | .docx reading |

### Windows-Only

| Package | Purpose |
|---------|---------|
| `comtypes` | Windows COM |
| `pycaw` | Windows volume control |
| `win10toast` | Windows notifications |
| `pywinauto` | Windows UI automation |
| `pywin32` | Windows API |
| `wmi` | Windows WMI queries |

### Optional (Not Installed by Default)

| Package | Purpose | Size |
|---------|---------|------|
| `pandas` | Spreadsheet/CSV analysis | Large |
| `pydub` | Audio metadata/conversion | Medium + ffmpeg |
| `mediapipe` | Push-up counter | Large |
| `openwakeword` | Wake word detection | A few MB |
| `kokoro` | Offline TTS | ~330 MB |
| `faster-whisper` | Offline transcription | ~75-290 MB |
| `ollama` | Local LLM | Model-dependent |

## Why Version Bounds

```
Lower bound: What the app is developed against
Upper bound: Stops next MAJOR release from breaking fresh clones
Minor/patch: Flow in freely
```

## Summary

```
Core: PyQt6, sounddevice, numpy, google-genai
Web: requests, beautifulsoup4, playwright
Automation: pyautogui, pyperclip, pygetwindow
Vision: Pillow, opencv-python, mss
System: psutil, send2trash, youtube-transcript-api, python-pptx, openpyxl
Dashboard: fastapi, uvicorn, cryptography, python-multipart, qrcode
Windows-only: comtypes, pycaw, win10toast, pywinauto, pywin32, wmi
Optional: openwakeword, kokoro, faster-whisper, ollama, pandas, pydub
```