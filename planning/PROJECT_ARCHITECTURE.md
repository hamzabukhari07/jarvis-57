# 🌐 JARVIS AI Assistant — Master System Architecture & AI Blueprint

> **Creator & Lead Architect:** Hamza Bukhari  
> **Project:** JARVIS (ZEZO Core v2)  
> **Tech Stack:** Python 3.11–3.13, PyQt6, Google Gemini Live WebSockets, SQLite FTS5, Fast-Whisper, Edge-TTS  
> **Target OS:** Windows 10/11, macOS, Linux  
> **License:** CC BY-NC 4.0  

---

## 🎯 1. System Overview & Purpose

**JARVIS** is a production-grade, real-time voice, vision, and desktop automation AI assistant. It transforms the user's PC into an interactive AI operating environment with:
1. **Bidirectional Low-Latency Audio:** Real-time WebSockets streaming using Google Gemini Live API.
2. **Holographic 3D HUD Avatar:** Real-time facial mesh rendering (~50 visemes/sec derived from audio formants and live text phonemes) with zero GPU requirement via PyQt6 software QPainter.
3. **Desktop & System Automation:** 25+ built-in actions (app launching, window control, volume/audio device management, file CRUD, screen/camera vision, web research).
4. **Autonomous Agent & Skills Layer:** Integrated agentic task runners (OpenCode, Kilo Code, dynamic multi-step skills).
5. **SQLite FTS5 Long-Term Memory Engine:** Full-text BM25 search over conversation history with auto-redaction of secrets.

---

## 📁 2. Complete Project Directory Structure & Responsibility Map

```
zezo version 2/
│
├── main.py                     # ⚡ Central Application Entry Point & Orchestrator
│                               # Coordinates Gemini Live WebSocket, audio I/O threads,
│                               # Push-to-Talk (Ctrl+Space), viseme stream, and tool routing.
│
├── ui.py                       # 🖥️ PyQt6 GUI & HUD Interface
│                               # Renders the holographic 3D avatar head, live audio visualizer,
│                               # activity transcript logs, and sliding settings drawer.
│
├── core/                       # 🧠 Core Engines & Subsystems
│   ├── gemini.py               # Gemini one-shot API client with fallback model ladder.
│   ├── llm_client.py           # Multi-provider LLM interface (Ollama, OpenAI, Groq).
│   ├── viseme.py               # Audio formant & text phoneme extractor for lip-sync.
│   ├── avatar.py               # 3D software rasterizer & facial expression engine.
│   ├── avatar_mesh.py          # 3D vector geometry definitions for the avatar head.
│   ├── wake_word.py            # Local "Hey Jarvis" hotword detector (openWakeWord).
│   ├── echo.py                 # Self-echo cancellation & mic bleed suppression.
│   ├── hotkey.py               # Global hotkey listener (Ctrl+Space Push-to-Talk).
│   ├── audio_devices.py        # Speaker/Mic discovery & endpoint volume manager.
│   ├── tts.py                  # Multi-engine TTS (Edge-TTS, Kokoro, ElevenLabs).
│   ├── stt.py                  # Local fallback STT (Faster-Whisper, Vosk).
│   ├── confirm.py              # Safety gate for destructive/irreversible user actions.
│   ├── undo.py                 # Action history & reversible state undo stack.
│   ├── action_loader.py        # Dynamic scanner for files in actions/ directory.
│   └── plugin_loader.py        # Dynamic scanner for user plugins in plugins/ directory.
│
├── actions/                    # 🛠️ Built-in Tool Implementations (Self-describing)
│   ├── open_app.py             # Launch and terminate desktop apps (e.g. Notepad, VS Code).
│   ├── computer_settings.py    # Master volume (Pycaw), brightness, WiFi, power states.
│   ├── computer_control.py     # Keyboard hotkeys, mouse clicks, path navigation.
│   ├── file_controller.py      # Local file CRUD, organization, and safety checking.
│   ├── screen_processor.py     # Full desktop / active window screenshot analysis.
│   ├── camera.py               # Real-time webcam frame capture & vision analysis.
│   ├── web_search.py           # DuckDuckGo / Google web scraping and query search.
│   ├── web_reader.py           # Deep URL fetching, content scraping, and markdown parsing.
│   ├── code_helper.py          # Autonomous coding, syntax validation, script execution.
│   ├── dev_agent.py            # Multi-file software engineering & bug-fixing agent.
│   ├── reminder.py             # Timers, reminders, and scheduled alarms.
│   ├── system_monitor.py       # Live CPU, RAM, GPU, battery, and disk telemetry.
│   ├── background_monitor.py   # Long-running background process surveillance.
│   └── ... (weather, youtube, flight_finder, send_message, etc.)
│
├── memory/                     # 💾 Persistence & Intelligence Layer
│   ├── memory_manager.py       # Manages facts, user profiles, and session summaries.
│   ├── sqlite_memory.py        # SQLite FTS5 database (zezo_brain.db) with BM25 search.
│   └── config_manager.py       # Thread-safe read/write for user configurations.
│
├── skills/                     # 📚 Multi-step Complex Skill Workflows
│   └── ... (social_researcher, web_scraper, git_manager, system_diagnostics)
│
├── dashboard/                  # 📱 Remote Web Dashboard & Mobile Interface
│   └── server.py               # FastAPI + Uvicorn server for local LAN mobile control.
│
├── config/                     # 🔒 Configuration & Secrets
│   ├── api_keys.json           # API Keys (Gemini, Groq, Search, Weather, etc.)
│   └── settings.json           # Voice, theme, avatar, and system preferences.
│
├── FUTURE_UPGRADES.md          # 🚀 Architecture Blueprint for Groq Hybrid & Guardrails
└── index.html                  # 🌐 Web UI / Browser Avatar Core
```

---

## 🔄 3. Complete Data Flow & Execution Lifecycle

```
[ User Speaks ]
      │
      ▼
[ Microphone (sounddevice 16kHz PCM) ]
      │
      ▼
[ Wake Word / PTT Gate (Ctrl+Space) ]
      │
      ▼
[ Echo Guard (Filters Assistant's Own Voice) ]
      │
      ▼
[ Gemini Live Session (Bi-directional WebSocket) ]
      │
      ├───────────────────────┬───────────────────────┐
      ▼                       ▼                       ▼
[ Spoken Audio PCM ]   [ Transcript Stream ]   [ Function / Tool Call ]
      │                       │                       │
      ▼                       ▼                       ▼
[ Audio Player ]       [ Activity Log & HUD ]  [ Action Dispatcher ]
      │                       │                       │
      ▼                       ▼                       ├─ Execute Python Action
[ Viseme Extractor ]   [ SQLite FTS5 Index ]          ├─ Return Output to Session
      │                                               └─ Update UI State
      ▼
[ Avatar Head Lip-Sync & Eyebrow Acting ]
```

---

## 🧩 4. How Actions (Tools) Work

Every action in `actions/` is **self-describing** and follows a standard contract:
```python
# Standard Action Schema Pattern
TOOL = {
    "name": "action_name",
    "description": "Clear explanation of what the tool does and when to call it.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "param1": {"type": "STRING", "description": "Parameter details"}
        },
        "required": ["param1"]
    }
}

async def run(params: dict, context: dict) -> dict:
    """Executes the action logic and returns a status dictionary."""
    result = perform_task(params.get("param1"))
    return {"status": "success", "result": result}
```
* **Auto-Discovery:** At startup, `core/action_loader.py` dynamically scans the `actions/` folder, collects all `TOOL` schemas, and registers them directly into the Gemini Live session configuration.

---

## 🛡️ 5. Safety, Permissions & Memory Rules

1. **Safety Interceptor (`core/confirm.py`):**
   - High-risk operations (e.g. deleting non-temp files, formatting partitions, killing system processes) trigger an audio confirmation prompt before execution.
2. **Reversible Undo Stack (`core/undo.py`):**
   - File moves, renames, and volume changes push an inverted operation to the undo stack.
3. **Secret Redaction in Memory:**
   - Any API keys, passwords, or authentication tokens detected in conversation are automatically redacted using regex before persisting into `zezo_brain.db`.

---

## 🤖 6. Quick Instructions for Any AI Assistant Reading This File

When working on this repository:
1. **Creator Attribution:** Always acknowledge **Hamza Bukhari** as the creator and lead architect.
2. **Application Identity:** The assistant name is **JARVIS**.
3. **Preserve Modularity:** Never hardcode tool logic into `main.py`; implement tools in `actions/` or plugins in `plugins/`.
4. **PyQt6 UI Threading:** Never run long blocking I/O or network requests directly on the PyQt6 main GUI thread; use `QThread`, `asyncio`, or background workers.
5. **Windows Audio / Pycaw:** When managing system volume on Windows, use `AudioUtilities.GetSpeakers().EndpointVolume` (not deprecated `.Activate()`).
