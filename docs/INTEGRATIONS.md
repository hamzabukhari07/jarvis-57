# JARVIS — Integrations & External Services

## Overview

JARVIS integrates with several external services. All API calls are made over HTTPS.

## Complete Service Inventory

### 1. Google Gemini (Primary AI)

| Property | Value |
|----------|-------|
| Provider | Google AI |
| API | Gemini Live API + Gemini REST API |
| SDK | `google-genai>=2.8.0,<3` |
| Authentication | API key from `config/api_keys.json` |
| Model | `models/gemini-3.1-flash-live-preview` |
| Data sent | Audio (PCM), text, images |
| Data received | Audio (TTS), text (transcript), tool results |
| Failure | Ladder fallback, cooldown, reconnect |

**File**: `main.py`, `core/gemini.py`

### 2. DuckDuckGo (Web Search)

| Property | Value |
|----------|-------|
| Provider | DuckDuckGo |
| SDK | `ddgs>=9,<10` |
| Purpose | Web search fallback |
| Data sent | Search query |
| Data received | Search results |
| Failure | Falls back to `duckduckgo-search` |

**File**: `actions/web_search.py`

### 3. Playwright / Chromium (Browser Automation)

| Property | Value |
|----------|-------|
| Provider | Microsoft Playwright |
| SDK | `playwright>=1.62,<2` |
| Anti-bot fetch | `scrapling[fetchers]>=0.4,<1` (`Fetcher` / `StealthyFetcher`) |
| Browsers | Chromium, Firefox |
| Purpose | Web browsing, navigation, interaction, anti-bot page reads |
| Installed via | `pip install -r requirements.txt` (`ensure_requirements`) |

**File**: `actions/browser_control.py`, `actions/web_reader.py`, `actions/website_cloner.py`

### 4. Weather Services

| Property | Value |
|----------|-------|
| Provider | Various (via Gemini or direct API) |
| Purpose | Live weather data |
| **File** | `actions/weather_report.py` |

### 5. Flight APIs

| Property | Value |
|----------|-------|
| Purpose | Flight price and availability |
| **File** | `actions/flight_finder.py` |

### 6. Messaging APIs

| Property | Value |
|----------|-------|
| Services | WhatsApp, Telegram, etc. |
| **File** | `actions/send_message.py` |

### 7. YouTube

| Property | Value |
|----------|-------|
| Library | `youtube-transcript-api` |
| Purpose | Search, play, control YouTube |
| **File** | `actions/youtube_video.py` |

### 8. Gaming APIs

| Property | Value |
|----------|-------|
| Services | Steam, Epic Games |
| **File** | `actions/game_updater.py` |

### 9. OAuth (Gmail/Calendar)

| Property | Value |
|----------|-------|
| SDK | `google-api-python-client`, `google-auth-oauthlib` |
| **File** | `plugins/_google_core.py` |

### 10. Smart Home (Tuya)

| Property | Value |
|----------|-------|
| SDK | `tinytuya` |
| **File** | `plugins/` (home_assistant plugin) |

### 11. MQTT (Printers)

| Property | Value |
|----------|-------|
| SDK | `paho-mqtt` |
| **File** | `plugins/` (printer_control plugin) |

### 12. Local LLM (Ollama)

| Property | Value |
|----------|-------|
| Backend | Ollama or OpenAI-compatible |
| Default URL | `http://localhost:11434` |
| Default model | `llama3.2` |
| **File** | `core/llm_client.py` |

### 13. EdgeTTS (Optional TTS)

| Property | Value |
|----------|-------|
| Provider | Microsoft |
| SDK | `edge_tts` |
| Purpose | Offline TTS alternative |

### 14. Kokoro (Optional TTS)

| Property | Value |
|----------|-------|
| Provider | HuggingFace |
| SDK | `kokoro>=0.9` |
| Model | ~330 MB |
| Purpose | Fully offline neural TTS |

### 15. ElevenLabs (Optional TTS)

| Property | Value |
|----------|-------|
| Provider | ElevenLabs |
| API | `https://api.elevenlabs.io/v1/text-to-speech/` |
| Model | `eleven_multilingual_v2` |
| Purpose | Cloud TTS (API key required) |

### 16. Dashboard CryptoJS

| Property | Value |
|----------|-------|
| CDN | `https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.2.0/crypto-js.min.js` |
| Auto-download | Served locally after first download |

### 17. Groq LPU (Free-Tier Coprocessor)

| Property | Value |
|----------|-------|
| Provider | Groq |
| API | OpenAI-compatible REST (`api.groq.com`) |
| Auth | `groq_api_key` from `config/api_keys.json` |
| Text model | `qwen/qwen3.8-27b` (`call_groq_text`) |
| Whisper | `whisper-large-v3-turbo` (`transcribe_groq_whisper`, ~25 MB cap) |
| Vision | `groq_vision_model` — **empty by default** (free tier has no multimodal) |
| Purpose | Free, low-latency STT + background text; never used for the realtime voice loop |
| Failure | Falls back to the Gemini ladder / local `faster-whisper` |

**File**: `core/llm_client.py`, `actions/file_processor.py`, `actions/code_helper.py`, `core/file_reader.py`

## Failure Behavior Summary

| Service | Failure Mode | Mitigation |
|---------|-------------|------------|
| Gemini Live | Connection drop | Resumption handle, reconnect |
| Gemini REST | 429 quota | Cooldown, ladder fallback |
| DuckDuckGo | No results | Gemini grounded first, DDG fallback |
| Browser | Not installed | Feature silently disabled |
| Ollama | Not running | Auto-launch, connection retry |
| Wake word | Model not downloaded | UI notification, "WAKE NOW" button |
| Dashboard | Dependencies missing | Graceful error message |

## Summary

```
Primary: Gemini Live API (voice) + Gemini REST (text/search)
Coprocessor: Groq LPU (free-tier Whisper STT + background text; opt-in vision)
Search: Google Grounded + DuckDuckGo
Browser: Playwright/Chromium + Scrapling (anti-bot fetch)
Local LLM: Ollama/OpenAI-compatible
TTS: Gemini Live native (main); EdgeTTS, Kokoro, ElevenLabs (dormant alternatives)
Messaging: WhatsApp, Telegram
Gaming: Steam, Epic
Smart Home: Tuya, Home Assistant
OAuth: Google API
MQTT: Printer support
Dashboard: FastAPI + CryptoJS
```