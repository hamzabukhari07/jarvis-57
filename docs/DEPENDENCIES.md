# JARVIS — Dependencies

## Overview

JARVIS uses a single `requirements.txt` file with OS-specific markers. `setup.py` installs dependencies filtered by OS.

**Files**: `requirements.txt`, `setup.py`, `core/installer.py`

## Auto-Install on Launch

`core/installer.py` is the runtime safety net so a normal `python main.py` gets
the baseline without the user having to remember `python setup.py`:

- **`ensure_requirements(log)`** — installs the entire `requirements.txt` (a
  comprehensive "everything by default" manifest). Success is stamped by a
  SHA-256 of the manifest in `config/.deps_stamp`, so pip runs exactly once per
  manifest revision and is a no-op afterwards. If the full install fails — one
  heavy package (e.g. `docling` → `antlr4-python3-runtime`) can abort the rest —
  it logs the real error and falls back to installing only the sentinel packages
  the app needs, so a single bad sdist cannot disable unrelated features. The
  first run installs the full voice stack (`torch`, `faster-whisper`,
  `openai-whisper`, …) so it can be large and slow; it runs on a daemon thread
  and the next launch picks the packages up.
- **`ensure_playwright_browsers(log)`** — asks Python Playwright where its
  Chromium is and downloads it if absent. This is now always checked, not only
  when the `playwright` package was just installed — a later `pip install -U
  playwright` used to leave the browser stale and every browser action failed
  with "Executable doesn't exist".
- **`install_for_config(config, log)`** — installs the STT/TTS engine packages
  for the selected engines (unchanged).

`main.py::runner` starts this on a daemon thread right after the API key is
entered, concurrent with the live session, so a first run fills in missing
packages without freezing the UI. The next launch picks them up.

## Python Version

| Requirement | Value |
|-------------|-------|
| Minimum | Python 3.11 |
| Maximum tested | Python 3.13 |
| Newer versions | Warning, not fatal |

> On Python 3.14 the install still succeeds; only `kokoro` is skipped (its
> `spacy`/`blis` dependency chain has no 3.14 wheels yet). See
> [Everything Installs by Default](#everything-installs-by-default).

### Running on a dedicated Python 3.12 / 3.13 venv (recommended if you want Kokoro)

Kokoro installs on Python 3.10–3.13 but **not 3.14**. Do **not** change the
system Python — create a virtual environment instead so the machine and other
projects are untouched:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

- The ZEZO **code** is unchanged (it targets 3.11–3.13).
- Each Python version keeps its own `site-packages`, so the venv needs its own
  install (downloads are cached).
- `.venv/` is already in `.gitignore`.
- Playwright/Patchright browsers live in the shared
  `%LOCALAPPDATA%\ms-playwright` cache, so they are **not** re-downloaded.
- On 3.12/3.13 the `kokoro` marker passes and offline TTS is available; the
  `audioop-lts` marker (`python_version >= "3.13"`) correctly stays off on 3.12.

## Dependency Categories

### Core: UI, Audio, Gemini Live

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `PyQt6` | `>=6.6,<7` | Desktop window container, WebEngine host | `ui.py` |
| `sounddevice` | `>=0.4,<1` | Audio I/O (PortAudio) | `main.py`, `core/audio_devices.py` |
| `numpy` | `>=1.24,<3` | Audio processing, level & echo math | `main.py`, `core/echo.py` |
| `google-genai` | `>=2.8.0,<3` | Gemini Live + REST API | `main.py`, `core/gemini.py` |
| `aiohttp` | `>=3.9,<4` | Desktop WebSocket + static UI server | `core/ui_server.py` |

### Web Search & Browser Control

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `requests` | `>=2.31,<3` | HTTP requests | `core/gemini.py`, `actions/*.py` |
| `beautifulsoup4` | `>=4.12,<5` | HTML parsing | `actions/web_search.py`, `actions/web_reader.py` |
| `playwright` | `>=1.62,<2` | Browser automation | `actions/browser_control.py` |
| `scrapling[fetchers]` | `>=0.4,<1` | Anti-bot HTTP/2 & Cloudflare-stealth fetching | `actions/web_reader.py`, `actions/website_cloner.py` |
| `ddgs` | `>=9,<10` | DuckDuckGo search (primary) | `actions/web_search.py` |
| `duckduckgo-search` | `>=6,<9` | DuckDuckGo search (legacy fallback) | `actions/web_search.py` |

### Automation / Input Control & Windows UIA

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `pyautogui` | (any) | Keyboard/mouse simulation, screen coordinates | `actions/computer_control.py`, `actions/computer_settings.py` |
| `pyperclip` | (any) | Clipboard access & preserve buffer | `actions/computer_control.py` |
| `pywinauto` | (any) | Windows UI Automation (L1 UIA accessibility tree) | `core/computer/windows_uia.py` |
| `pygetwindow` | (any) | Window management & handle lookups | `actions/computer_control.py` |

### Vision, Media & Multilingual RapidOCR

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `rapidocr_onnxruntime` | `>=1.2,<2` | Sub-80ms CPU ONNX Multilingual OCR (0 MB GPU VRAM) | `core/computer/ocr_engine.py`, `actions/screen_processor.py` |
| `Pillow` | `>=10,<13` | Image processing & synthetic crops | `actions/screen_processor.py`, `core/computer/ocr_engine.py` |
| `opencv-python` | `>=4.8,<5` | Webcam capture | `actions/screen_processor.py` |
| `mss` | `>=9,<11` | Fast multi-monitor screen capture | `actions/screen_processor.py` |

### System, Files & Documents

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `psutil` | `>=5.9,<8` | System metrics, process info | `actions/system_monitor.py`, `ui.py` |
| `send2trash` | (any) | Safe file deletion | `actions/file_controller.py` |
| `youtube-transcript-api` | (any) | YouTube transcript | `actions/youtube_video.py` |
| `yt-dlp` | `>=2024.1.0` | Media/social extraction | `actions/agent_reach.py` |
| `feedparser` | `>=6.0.0` | RSS/Atom feeds | `actions/agent_reach.py` |
| `python-pptx` | (any) | PowerPoint reading | `actions/file_processor.py` |
| `openpyxl` | (any) | Excel reading | `actions/file_processor.py` |
| `python-docx` | (any) | .docx reading | `core/file_reader.py` |
| `PyPDF2` | (any) | PDF fallback reader | `actions/file_processor.py` |
| `pdfplumber` | (any) | Local text-layer PDF extraction | `core/file_reader.py` |
| `markitdown` | (any) | Office/PDF → Markdown fast path | `core/file_reader.py` |
| `docling` | `>=2,<3` | Offline OCR/layout for scanned docs | `core/file_reader.py` |
| `pandas` | `>=2,<4` | Spreadsheet/CSV analysis | `actions/file_processor.py` |
| `pydub` | `>=0.25,<1` | Audio metadata/conversion | `actions/file_processor.py` |
| `audioop-lts` | `>=0.2.1` (py≥3.13) | Restores stdlib `audioop` removed in Python 3.13 (PEP 594); required by pydub | `actions/file_processor.py` |
| `py7zr` | `>=0.20,<2` | .7z archive extraction | `core/file_reader.py` |
| `pynvml` | (any) | NVIDIA GPU monitoring | `actions/system_monitor.py`, `ui.py` |

### Local Speech & Wake Word

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `faster-whisper` | `>=1.0,<2` | Local video transcription (CTranslate2) | `actions/agent_reach.py` |
| `openwakeword` | `>=0.6,<1` | "Hey Jarvis" wake-word detection | `core/wake_word.py` |

### Remote Dashboard

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `fastapi` | `>=0.110,<1` | HTTP server | `dashboard/server.py` |
| `uvicorn[standard]` | `>=0.27,<1` | ASGI server | `dashboard/server.py` |
| `cryptography` | `>=42,<50` | AES-256-CBC encryption | `dashboard/server.py` |
| `python-multipart` | `>=0.0.9,<1` | File uploads | `dashboard/server.py` |
| `qrcode[pil]` | `>=7,<9` | QR code generation | `dashboard/server.py` |

### Windows-Only

| Package | Purpose |
|---------|---------|
| `comtypes` | Windows COM |
| `pycaw` | Windows volume control |
| `win10toast` | Windows notifications |
| `pywinauto` | Windows UI automation |
| `pywin32` | Windows API |
| `wmi` | Windows WMI queries |

### Dev / Test

| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `pytest` | `>=8,<10` | Test suite runner | `tests/` |

## Why Version Bounds

```
Lower bound: What the app is developed against
Upper bound: Stops next MAJOR release from breaking fresh clones
Minor/patch: Flow in freely
```

## Summary

```
Core: PyQt6, PyQt6-WebEngine, aiohttp, sounddevice, numpy, google-genai
Web: requests, beautifulsoup4, playwright, scrapling[fetchers], ddgs, duckduckgo-search
Automation: pyautogui, pyperclip, pygetwindow
Vision: Pillow, opencv-python, mss
Documents: youtube-transcript-api, yt-dlp, feedparser, python-pptx, openpyxl,
           python-docx, PyPDF2, pdfplumber, markitdown, pandas, pydub,
           audioop-lts (py>=3.13), py7zr, pynvml
Voice: faster-whisper, openwakeword
Dashboard: fastapi, uvicorn, cryptography, python-multipart, qrcode
Windows-only: comtypes, pycaw, win10toast, pywinauto, pywin32, wmi
Dev: pytest
```