# JARVIS — Complete Documentation Index

## What is JARVIS?

JARVIS is a **real-time voice AI assistant** that can hear, see, speak, and control your computer — on any OS (Windows, macOS, Linux). It features a holographic animated avatar rendered in software, real lip-sync, local wake-word detection, and comprehensive computer control capabilities. It runs entirely locally with no telemetry, no accounts, and no cloud server of its own.

## How Does It Work?

JARVIS uses **Google's Gemini Live API** for real-time voice conversation. Audio from the microphone is streamed to Gemini, which performs speech recognition, reasoning, and text-to-speech natively. All local processing (audio I/O, UI rendering, tool execution, memory management) happens on the user's machine.

## Core Architecture

- **Modular monolith**: Single Python process with clearly separated modules
- **Event-driven**: PyQt6 signals/slots for UI, asyncio for Gemini Live, threading for audio
- **Auto-discovery**: Actions and plugins are discovered at startup via `TOOL`/`PLUGIN` dicts
- **Plugin-based**: Drop-in `.py` files extend functionality without modifying core code

## AI Model

```text
Provider: Google
Model: gemini-3.1-flash-live-preview
SDK: google-genai>=2.8.0,<3
Configured in: main.py line 99
Initialized in: main.py:JarvisLive._build_config()
Called by: main.py:_listen_audio() and _send_realtime()
```

## STT (Speech-to-Text)

**JARVIS does not use a separately hosted STT model.** Speech recognition is handled entirely through the Gemini Live API. The `core/stt.py` module contains Whisper and Vosk classes but they are **not used** in the main pipeline — they exist as optional fallbacks.

## TTS (Text-to-Speech)

**JARVIS uses Gemini Live for all TTS in the main conversation.** The model is configured with `response_modalities=["AUDIO"]`, meaning it produces audio directly. Alternative TTS engines (EdgeTTS, Kokoro, ElevenLabs) exist in `core/tts.py` but are **not used** in the main pipeline.

## Voice Pipeline

```text
User speaks → Microphone → Audio gates (wake/echo/PTT) → Gemini Live → STT+LLM+TTS → Speakers + Avatar
```

## Memory

- **Storage**: `memory/long_term.json` (JSON)
- **Categories**: identity, preferences, projects, relationships, wishes, notes, sessions
- **Prompt budget**: 900 chars core + 420 chars index
- **Search**: Lexical (no embeddings, <1ms)
- **Persistence**: File on disk, thread-safe, auto-trimmed at 200k chars

## Tools

- **20+ built-in actions** auto-discovered from `actions/*.py`
- **Plugins** auto-discovered from `plugins/*.py`
- **Inline tools** in `main.py` for live-session state
- **All tools** declared as `function_declarations` and sent to Gemini

## Plugins

Drop-in `.py` files with `PLUGIN` dict + `run()` function. Auto-discovered at startup. No configuration files needed.

## Vision

On-demand screen/webcam capture using `mss` + `cv2` + `PIL`. Images are labelled with source metadata and injected into the same exchange as the tool result.

## Computer Control

Volume, brightness, WiFi, keyboard, mouse, windows, applications, browser, files — all controlled via platform-specific Python libraries (pyautogui, pycaw, pywin32, subprocess, etc.).

## UI/HUD

- **Framework**: PyQt6
- **Rendering**: QPainter only (no GPU, no OpenGL)
- **Avatar**: MediaPipe canonical face model (468 vertices, Apache 2.0)
- **Lip-sync**: ~50 mouth shapes/second from audio formants + transcript
- **Two styles**: Face or reactor core
- **Theming**: Hue wheel accent color

## External Services

| Service | Purpose |
|---------|---------|
| Google Gemini Live API | Voice conversation, STT, TTS, LLM |
| Google Gemini REST API | One-shot calls, search |
| DuckDuckGo | Web search fallback |
| Playwright/Chromium | Browser automation |
| Ollama (optional) | Local LLM backend |
| FastAPI/uvicorn | Dashboard server |
| EdgeTTS/Kokoro/ElevenLabs | Optional TTS alternatives |

## Platform Support

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Push-to-talk | Global (GetAsyncKeyState) | Window-scoped | Window-scoped |
| Audio | DirectSound/MME | Core Audio | PulseAudio/PipeWire |
| Volume | pycaw/pyautogui | osascript | pactl |
| Brightness | pywinauto | osascript | brightnessctl |
| Auto-start | Registry | LaunchAgent | .desktop |

## Security

- No telemetry, no accounts, no MARK server
- API key stored in `config/api_keys.json` (plaintext, git-ignored)
- Confirmation tokens issued by UI, not model
- Memory stored locally
- Wake word audio never leaves machine
- Dashboard uses AES-256-CBC encryption
- Session resumption handle in RAM only

## Important Files

| File | Purpose |
|------|---------|
| `main.py` | Application orchestrator & Gemini Live WebSockets loop |
| `ui.py` | PyQt6 HUD, holographic avatar, multi-file dropzone & task inspector |
| `core/prompt.txt` | System prompt template |
| `core/action_loader.py` | Action auto-discovery (23 actions) |
| `core/skill_loader.py` | Declarative skill loader (10 skills) |
| `core/plugin_loader.py` | Plugin auto-discovery |
| `core/task_manager.py` | Background task registry, process watchdog, CPU throttle, cancellation |
| `core/log_bus.py` | Ring buffer log bus (20,000 lines) with zero-leak secret redaction |
| `core/design_resolver.py` | Design token resolver & anti-slop preset injector |
| `core/design_extractor.py` | Deterministic HTML/Tailwind token extractor |
| `core/viseme.py` | Lip-sync engine |
| `core/echo.py` | Self-echo guard |
| `core/wake_word.py` | Wake word detection |
| `core/undo.py` | Undo stack |
| `core/confirm.py` | Confirmation gate |
| `core/audio_devices.py` | Audio device selection |
| `memory/sqlite_memory.py` | SQLite FTS5 database (`zezo_brain.db`) with BM25 search |
| `memory/memory_manager.py` | Long-term memory storage & session summaries |
| `memory/config_manager.py` | Configuration manager |
| `config/api_keys.json` | User configuration (git-ignored) |
| `actions/*.py` | Built-in action files (antigravity_agent, opencode_agent, kilo_agent, etc.) |
| `skills/*/` | Declarative skill packages (hamza_taste, antigravity_agent, etc.) |
| `plugins/*.py` | Plugin files |
| `dashboard/server.py` | Remote dashboard server |

## Detailed Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Complete architecture overview
- [STARTUP_FLOW.md](STARTUP_FLOW.md) — Detailed startup sequence
- [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) — Gemini Live implementation details
- [STT.md](STT.md) — Speech-to-text analysis
- [TTS.md](TTS.md) — Text-to-speech analysis
- [VOICE_PIPELINE.md](VOICE_PIPELINE.md) — Complete voice interaction flow
- [AUDIO_SYSTEM.md](AUDIO_SYSTEM.md) — Audio implementation details
- [WAKE_WORD.md](WAKE_WORD.md) — Wake word detection
- [PUSH_TO_TALK.md](PUSH_TO_TALK.md) — Push-to-talk system
- [LLM_PIPELINE.md](LLM_PIPELINE.md) — AI reasoning pipeline
- [PROMPT_SYSTEM.md](PROMPT_SYSTEM.md) — System prompt analysis
- [TOOLS.md](TOOLS.md) — Complete tool inventory
- [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) — Plugin architecture
- [MEMORY.md](MEMORY.md) — Memory system deep dive
- [SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md) — Session lifecycle
- [COMPUTER_CONTROL.md](COMPUTER_CONTROL.md) — OS-level capabilities
- [UNDO.md](UNDO.md) — Undo system
- [SAFETY_AND_CONFIRMATION.md](SAFETY_AND_CONFIRMATION.md) — Confirmation gate
- [VISION.md](VISION.md) — Vision system
- [HUD_AND_AVATAR.md](HUD_AND_AVATAR.md) — PyQt6 UI and avatar
- [LIP_SYNC.md](LIP_SYNC.md) — Lip-sync system
- [WEB_SEARCH.md](WEB_SEARCH.md) — Web search system
- [DASHBOARD.md](DASHBOARD.md) — Remote dashboard
- [PROACTIVE_SYSTEM.md](PROACTIVE_SYSTEM.md) — Proactive features
- [STORAGE.md](STORAGE.md) — All local storage
- [INTEGRATIONS.md](INTEGRATIONS.md) — External API/services
- [CONFIGURATION.md](CONFIGURATION.md) — Configuration system
- [DEPENDENCIES.md](DEPENDENCIES.md) — All dependencies
- [PLATFORM_SUPPORT.md](PLATFORM_SUPPORT.md) — Platform-specific behavior
- [DATA_FLOW.md](DATA_FLOW.md) — Complete data flows
- [REQUEST_LIFECYCLE.md](REQUEST_LIFECYCLE.md) — Line-by-line request traces
- [CODEBASE_MAP.md](CODEBASE_MAP.md) — File-by-file map
- [DESIGN_SYSTEM_ARCHITECTURE.md](DESIGN_SYSTEM_ARCHITECTURE.md) — Hamza Taste 3.0 & Anti-Slop Design System Architecture
- [DIAGRAMS.md](DIAGRAMS.md) — 17 Mermaid diagrams

## Quick Start

```bash
git clone https://github.com/FatihMakes/Mark-LIV.git
cd Mark-LIV
python setup.py        # installs deps for YOUR OS
python main.py         # launch the assistant
```

## License

Personal and non-commercial use only. Licensed under Creative Commons BY-NC 4.0.

## Your Data

Everything stays on your machine. There is no MARK server, no telemetry and no account.