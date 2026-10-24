# ZEZO — Dependencies & Package Manifest

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## Overview

ZEZO relies on a curated ecosystem consisting of:
1. **Python Backend**: Manifested in `requirements.txt` and auto-bootstrapped via `core/installer.py`.
2. **Frontend SPA**: React 18/19 + Vite modern single-page application located in `frontend/package.json`.
3. **CLI & System Engines**: External developer tools, browser agents, and network tunnel binaries.

---

## Auto-Install on Launch (`core/installer.py`)

`core/installer.py` acts as the runtime safety net so executing `python main.py` ensures all requirements are present:

- **`ensure_requirements(log)`**: Installs `requirements.txt`. Execution is stamped with a SHA-256 hash in `config/.deps_stamp`, preventing redundant pip invocations. If an optional heavy wheel fails, it logs cleanly and falls back without aborting core features.
- **`ensure_playwright_browsers(log)`**: Verifies Chromium browser binaries for headless browser automation and downloads them if absent.
- **`install_for_config(config, log)`**: Installs optional offline voice/STT models on demand.

---

## Python Version Compatibility

| Requirement | Value | Notes |
|-------------|-------|-------|
| Minimum | Python 3.11 | Modern async, exception groups |
| Recommended | Python 3.12 / 3.13 | Optimal compatibility for all local OCR and media libraries |
| Python 3.14+ | Warning / Experimental | `audioop-lts` used for Python 3.13+ compatibility |

### Recommended Setup (Virtual Environment):
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

---

## Frontend NPM Dependencies (`frontend/package.json`)

The ZEZO desktop HUD is an ultra-modern React single-page application built on Vite, Tailwind CSS v4, and the ReUI component system.

| Package | Version | Purpose | Component / Usage |
|---------|---------|---------|-------------------|
| `@assistant-ui/react` | `^0.15.26` | Enterprise conversational UI primitives | `ZezoChatThread.tsx`, thinking & thread runtime |
| `@assistant-ui/react-markdown` | `^0.14.20` | Streaming markdown rendering with syntax highlighting | Chat response formatting, code blocks |
| `@tailwindcss/vite` | `^4.3.3` | Tailwind v4 compilation plugin | Modern CSS-first design tokens |
| `tailwindcss` | `^4.3.3` | Utility-first styling framework | ReUI design system, atomic styles |
| `three` | `^0.180.0` | 3D WebGL rendering engine | Particle visualizers, avatar point-cloud |
| `@types/three` | `^0.186.0` | TypeScript definitions for Three.js | Type safety across 3D canvas modules |
| `3d-force-graph` | `^1.80.1` | WebGL 3D force-directed graph | Tier 3 Knowledge Graph visualization |
| `react-force-graph-3d` | `^1.29.2` | React bindings for 3D force graph | `MemoryGraphCanvas.tsx` |
| `react-force-graph-2d` | `^1.29.2` | 2D graph fallback view | Desktop graph layout alternative |
| `lucide-react` | `^1.53.0` | Iconography library | Navigation, toolbars, buttons, status indicators |
| `zustand` | (integrated) | Lightweight client state management | Agent desk coordinates, global HUD state |
| `framer-motion` | (integrated) | Motion & transition animations | Modal overlays, slide-overs, desk animations |
| `@xyflow/react` | `^12.12.0` | Node-based workflow & pipeline editor | Agent workflow decomposition visualizer |
| `qivi-react` | `^0.1.2` | Audio-reactive avatar component | `QiviAvatarVisualizer.tsx` |
| `qrcode` | `^1.5.4` | In-app QR code generation | `MobileRemoteModal.tsx` (Cloudflare tunnel OTP pairing) |
| `@radix-ui/*` | `latest` | Headless accessible UI primitives | Dialog, Tabs, ScrollArea, Tooltip, Select |
| `blobatar` | `^2.7.0` | Generative agent avatar badges | Autonomous office agent profile portraits |

---

## CLI & System Dependencies

ZEZO orchestrates external command-line engines and network services to execute advanced coding, cloning, and remote tunneling tasks.

| Tool / CLI | Version / Spec | Purpose | Integration Module |
|------------|----------------|---------|---------------------|
| **`rea-agents`** | `@6.7.0` (npm) | Headless browser scenario capture & teardown engine | `core/teardown_engine.py`, `actions/reverse_engineer.py` |
| **`cloudflared`** | Latest binary | Zero-config Quick Tunnel for remote HUD mobile access | `core/ui_server.py`, `frontend/src/components/remote/` |
| **`uncage`** | CLI tool | Complete website cloner preserving assets & HTML DOM | `actions/website_cloner.py` |
| **`agy`** (Antigravity CLI) | Latest CLI | High-performance autonomous subagent coding engine | `core/code_engines.py`, `actions/code_engines_status.py` |
| **`opencode`** | CLI / Agent | Multi-file codebase refactoring and coding engine | `core/code_engines.py`, `main.py` task watcher |
| **`kilo`** | CLI | Fast lightweight terminal code editor & refactoring agent | `core/code_engines.py`, `main.py` task watcher |

---

## Python Backend Dependencies (`requirements.txt`)

### 1. Core Runtime, Audio & Gemini Live API
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `PyQt6` | `>=6.6,<7` | Desktop window container, WebEngine host | `ui.py` |
| `PyQt6-WebEngine` | `>=6.6,<7` | Chromium browser container for React HUD | `ui.py` |
| `aiohttp` | `>=3.9,<4` | Desktop WebSocket + static UI server | `core/ui_server.py` |
| `sounddevice` | `>=0.4,<1` | Audio I/O (PortAudio streaming) | `main.py`, `core/audio_devices.py` |
| `numpy` | `>=1.24,<3` | Audio signal processing, RMS levels, echo cancellation | `main.py`, `core/echo.py` |
| `google-genai` | `>=2.8.0,<3` | Gemini Live bidirectional WebSocket audio + REST API | `main.py`, `core/gemini.py` |

### 2. Web Search, Scraping & Automation
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `requests` | `>=2.31,<3` | Synchronous HTTP calls | `core/gemini.py`, `actions/*.py` |
| `beautifulsoup4` | `>=4.12,<5` | HTML parsing and text extraction | `actions/web_search.py`, `actions/web_reader.py` |
| `playwright` | `>=1.62,<2` | Headless browser automation | `actions/browser_control.py` |
| `scrapling[fetchers]` | `>=0.4,<1` | Stealth anti-bot & Cloudflare bypass fetching | `actions/web_reader.py`, `actions/website_cloner.py` |
| `ddgs` | `>=9,<10` | Primary DuckDuckGo search provider | `actions/web_search.py` |
| `duckduckgo-search` | `>=6,<9` | Secondary search fallback | `actions/web_search.py` |

### 3. Desktop Automation & Windows UIA
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `pyautogui` | (any) | Native mouse clicks and keyboard typing | `actions/computer_control.py` |
| `pyperclip` | (any) | OS clipboard access & buffer preservation | `actions/computer_control.py` |
| `pygetwindow` | (any) | Active window handle detection | `actions/computer_control.py` |
| `pywinauto` | (any) | L1 Windows UI Automation (COM tree inspection) | `core/computer/windows_uia.py` |
| `pywin32` / `wmi` | (any) | Windows API, low-level keyboard hooks & WMI | `core/hotkey.py`, `actions/system_monitor.py` |

### 4. Vision & Multilingual OCR
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `rapidocr_onnxruntime` | `>=1.3,<2` | Sub-80ms CPU Multilingual OCR (0 MB GPU VRAM) | `core/computer/ocr_engine.py`, `actions/screen_processor.py` |
| `pillow` | `>=10,<13` | Image manipulation, resizing & compression | `actions/screen_processor.py` |
| `opencv-python` | `>=4.8,<5` | Camera capture & frame transforms | `actions/screen_processor.py` |
| `mss` | `>=9,<11` | High-speed multi-monitor screenshot capture | `actions/screen_processor.py` |

### 5. Document Processing & File Ingestion
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `psutil` | `>=5.9,<8` | System telemetry, CPU/RAM/battery metrics | `actions/system_monitor.py` |
| `send2trash` | (any) | Safe recycling bin deletion | `actions/file_controller.py` |
| `youtube-transcript-api`| (any) | YouTube subtitles and transcript extraction | `actions/youtube_video.py` |
| `yt-dlp` | `>=2024.1.0` | Audio/video extraction & media metadata | `actions/agent_reach.py` |
| `feedparser` | `>=6.0.0` | RSS & Atom feed parser | `actions/agent_reach.py` |
| `python-pptx` | (any) | PowerPoint presentation ingestion | `actions/file_processor.py` |
| `openpyxl` | (any) | Excel workbook reading and modification | `actions/file_processor.py` |
| `python-docx` | (any) | Word document reader/writer | `core/file_reader.py` |
| `reportlab` | `>=4,<6` | PDF generation | `actions/file_processor.py` |
| `pypdf` / `pdfplumber` | (latest) | Local PDF text and table extraction | `core/file_reader.py` |
| `markitdown` | (any) | Multi-format Office-to-Markdown parser | `core/file_reader.py` |
| `pandas` | `>=2,<4` | Tabular data analysis and manipulation | `actions/file_processor.py` |
| `pydub` | `>=0.25,<1` | Audio file chunking and conversions | `actions/file_processor.py` |
| `audioop-lts` | `>=0.2.1` | Restores stdlib `audioop` on Python 3.13+ | `actions/file_processor.py` |
| `py7zr` | `>=0.20,<2` | 7z archive extraction | `core/file_reader.py` |

### 6. Local Speech, Wake-Word & Remote Dashboard
| Package | Version | Purpose | Used By |
|---------|---------|---------|---------|
| `faster-whisper` | `>=1.0,<2` | Video transcription fallback (CTranslate2) | `actions/agent_reach.py` |
| `openwakeword` | `>=0.6,<1` | Offline wake-word detection | `core/wake_word.py` |
| `fastapi` | `>=0.110,<1` | HTTP API server for remote endpoints | `dashboard/server.py` |
| `uvicorn[standard]` | `>=0.27,<1` | ASGI web server | `dashboard/server.py` |
| `cryptography` | `>=42,<50` | AES-256 session token generation | `dashboard/server.py` |

---

## Summary

```
Frontend: React 18/19, Vite, Tailwind v4, ReUI, Assistant-UI, Three.js, Lucide
CLI Tools: rea-agents@6.7.0, cloudflared, uncage, agy, opencode, kilo
Core Python: PyQt6, aiohttp, sounddevice, numpy, google-genai
Automation: pyautogui, pyperclip, pygetwindow, pywinauto, pywin32
Vision: RapidOCR ONNX, Pillow, OpenCV, MSS
Documents: pdfplumber, pypdf, reportlab, python-docx, openpyxl, pandas
Speech: Gemini Live (Primary), Faster-Whisper, OpenWakeWord
```
