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
| SDK | `playwright>=1.40,<2` |
| Browsers | Chromium, Firefox |
| Purpose | Web browsing, navigation, interaction |
| Installed via | `python setup.py` |

**File**: `actions/browser_control.py`, `setup.py`

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
Search: Google Grounded + DuckDuckGo
Browser: Playwright/Chromium
Local LLM: Ollama/OpenAI-compatible
TTS: EdgeTTS, Kokoro, ElevenLabs (optional)
Messaging: WhatsApp, Telegram
Gaming: Steam, Epic
Smart Home: Tuya, Home Assistant
OAuth: Google API
MQTT: Printer support
Dashboard: FastAPI + CryptoJS
```