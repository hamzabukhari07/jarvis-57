# ZEZO — Integrations & External Services

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## Overview

ZEZO integrates with core artificial intelligence platforms, local CLI coding engines, browser automation drivers, network tunneling solutions, and external web services. All network operations communicate over TLS/HTTPS or encrypted WebSockets.

---

## Core AI & Conversational Services

### 1. Google Gemini Live & REST API (Primary Conversational Brain)

| Property | Value |
|----------|-------|
| Provider | Google DeepMind / Google AI |
| API | Gemini Live API (Bidirectional WebSocket PCM) + Gemini REST API |
| SDK | `google-genai>=2.8.0,<3` |
| Authentication | API key from `config/api_keys.json` (`gemini_api_key`) |
| Live Voice Model | `models/gemini-2.0-flash-exp` / `gemini-3.1-flash-live-preview` |
| REST Tiered Engine | `gemini-3.8-flash-tiered` (Multi-tier dynamic fallback ladder) |
| Streaming Format | Raw PCM audio (`audio/pcm;rate=16000` / `24000`) |
| Failure Mitigation | RAM-only resumption handle, automatic reconnection, backoff ladder |

**Files**: `main.py`, `core/gemini.py`

### 2. Groq LPU (High-Speed Coprocessor)

| Property | Value |
|----------|-------|
| Provider | Groq Inc. |
| API | OpenAI-compatible REST endpoint (`api.groq.com`) |
| Auth | `groq_api_key` in `config/api_keys.json` |
| Text Model | `qwen/qwen3.8-27b` (`call_groq_text`) |
| STT Engine | `whisper-large-v3-turbo` (`transcribe_groq_whisper`, 25MB file cap) |
| Role | Fast background extraction, document parsing & fallback STT; never used for the realtime voice loop |

**Files**: `core/llm_client.py`, `actions/file_processor.py`, `core/file_reader.py`

### 3. Local LLM via Ollama (Offline Engine)

| Property | Value |
|----------|-------|
| Backend | Ollama or local OpenAI-compatible server |
| Default URL | `http://localhost:11434` |
| Default Model | `llama3.2` |
| Role | Complete offline privacy fallback for text tasks |

**Files**: `core/llm_client.py`

---

## Autonomous Code Engines

ZEZO orchestrates external CLI coding agents through a unified engine driver interface in `core/code_engines.py` and the `code_engines_status` tool.

| Engine | Binary / Command | Architecture & Role |
|--------|------------------|---------------------|
| **Antigravity CLI** | `agy` | Google DeepMind agentic coding CLI. Executes multi-step repo modifications, branch isolated tasks, and agent skill loading. |
| **OpenCode** | `opencode` | Autonomous open-source coding agent. Performs large multi-file refactorings, test sweeps, and directory scans. |
| **Kilo** | `kilo` | Lightweight terminal coding agent for swift scripts, targeted bugfixes, and code transforms. |

- **Probe & Health Checks:** `actions/code_engines_status.py` inspects CLI readiness, CLI authentication, and PATH availability.
- **Frontend Settings:** Configured via `frontend/src/components/settings/CodeEnginesSettingsTab.tsx`.

---

## Website Cloning & Reverse Engineering

### 1. REA Teardown Engine (`rea-agents@6.7.0`)
- **Binary:** `rea capture-browser-scenario`
- **Role:** Headless Chrome CDP interception capturing live DOM, CSS computed styles, network assets, and full user interaction flows into 0-LLM evidence envelopes (`evidence.json`, `blueprint.md`, `ledger.json`).
- **Files:** `core/teardown_engine.py`, `actions/reverse_engineer.py`

### 2. Uncage Website Cloner (`actions/website_cloner.py`)
- **CLI Engine:** `uncage`
- **Role:** Complete website offline cloner downloading raw HTML, stylesheets, scripts, media assets, and fonts.
- **Output:** Preserves untouched raw captures in external directory folders (`~/Desktop/ZEZO_Clones/`), supporting single-file HTML compilation (`rebuilt.html`) or full app scaffolding (`rebuilt_app/`).
- **Safety Gate:** Enforces stateless two-step confirmation (`confirmed=True`) before executing download pipelines.

---

## Remote Access & Cloudflare Quick Tunnels

ZEZO features a zero-config secure mobile bridge that exposes the desktop UI to mobile devices without port forwarding or firewall adjustments.

| Property | Value |
|----------|-------|
| Provider | Cloudflare Inc. |
| Binary | `cloudflared` |
| Command | `cloudflared tunnel --url http://127.0.0.1:8765` |
| Public URL | Ephemeral TLS tunnel (`https://*.trycloudflare.com`) |
| Security | Time-limited AES-256 OTP pairing token |
| Mobile Access | Scan QR code in `frontend/src/components/remote/MobileRemoteModal.tsx` |
| Capabilities | Remote touch controls, two-way mic streaming, telemetry viewer |

**Files**: `core/ui_server.py`, `frontend/src/components/remote/MobileRemoteModal.tsx`

---

## Web Search, Scraping & Browser Automation

### 1. DuckDuckGo Search
- **Primary SDK:** `ddgs>=9,<10`
- **Fallback SDK:** `duckduckgo-search>=6,<9`
- **Integration:** `actions/web_search.py`

### 2. Playwright & Scrapling
- **Headless Browser:** Chromium via `playwright>=1.62,<2`
- **Anti-Bot Fetching:** `scrapling[fetchers]>=0.4,<1` (`StealthyFetcher` bypassing Cloudflare / Akamai challenges)
- **Integration:** `actions/browser_control.py`, `actions/web_reader.py`

---

## Operating System & Hardware Integrations

| Subsystem | Service / Library | Role |
|-----------|-------------------|------|
| **Windows UIA** | `pywinauto`, `comtypes` | Sub-15ms COM accessibility tree inspection |
| **Multilingual OCR**| `rapidocr_onnxruntime` | Sub-80ms CPU ONNX spatial text locator (0 VRAM) |
| **Display Capture** | `mss`, `opencv-python` | Multi-monitor high-speed screen and webcam capture |
| **Input Synthesis** | `pyautogui`, `pywin32` | Native clicks, keyboard hooks (`Ctrl+Alt` PTT) |
| **Hardware Telemetry** | `psutil`, `pynvml` | CPU, RAM, battery, and NVIDIA GPU statistics |
| **Reminders** | OS Task Scheduler / LaunchAgents | Native scheduled tasks running independently of the process |

---

## Peripheral & Home Automation Integrations

- **YouTube:** `youtube-transcript-api` and `yt-dlp` for video extraction and transcripts (`actions/youtube_video.py`, `actions/agent_reach.py`).
- **Messaging:** Direct URL scheme & API messaging for WhatsApp, Telegram (`actions/send_message.py`).
- **Smart Home:** Tuya device control via `tinytuya` (`plugins/home_assistant/`).
- **Office & Printers:** Network printer spooling via MQTT (`plugins/printer_control/`).
- **OAuth Services:** Google Workspace (Gmail, Calendar) integration (`plugins/_google_core.py`).

---

## Failure Behavior & Resilience Matrix

| Integration | Failure Mode | Mitigation Strategy |
|-------------|--------------|---------------------|
| **Gemini Live** | Network drop / WebSocket close | RAM resumption handle replayed; immediate seamless reconnect |
| **Gemini REST** | 429 Quota / Rate limit | Dynamic backoff cooldown, auto-downgrade across model ladder |
| **Code Engines** | CLI binary missing from PATH | Health probe marks engine uninstalled; UI offers install instructions |
| **Cloudflare Tunnel**| Binary missing or tunnel timeout | Logs clear warning; falls back to local LAN IP QR code |
| **Browser Driver** | Chromium binary absent | `core.installer.ensure_playwright_browsers()` downloads headless binary |
| **Hardware Audio** | Mic / Speaker unplugged | Enters graceful silent/remote mode; avoids crashing session `TaskGroup` |
