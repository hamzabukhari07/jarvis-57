# JARVIS — Codebase Map

## Top-Level Structure

```
JARVIS/
├── main.py                          # Application entry point, JarvisLive class
├── ui.py                            # PyQt6 HUD (5438 lines)
├── setup.py                         # OS-aware installer
├── requirements.txt                 # All Python dependencies
├── readme.md                        # User-facing documentation
├── .gitignore                       # Excludes config, certs, memory
├── LICENSE                          # CC BY-NC 4.0
├── core/
│   ├── __init__.py                  # Core module init
│   ├── prompt.txt                   # System prompt template (160 lines)
│   ├── face_model.obj               # MediaPipe face mesh (25 KB, Apache 2.0)
│   ├── avatar.py                    # Holographic avatar renderer
│   ├── avatar_mesh.py               # Head geometry builder
│   ├── gemini.py                    # One-shot Gemini calls, model ladder
│   ├── llm_client.py                # Local LLM client (Ollama/OpenAI)
│   ├── stt.py                       # Whisper/Vosk STT engines (optional)
│   ├── tts.py                       # EdgeTTS/Kokoro/ElevenLabs TTS engines
│   ├── viseme.py                    # Transcript→mouth shapes fusion
│   ├── echo.py                      # Self-echo detection and cancellation
│   ├── wake_word.py                 # Local "Hey Jarvis" detector
│   ├── hotkey.py                    # Push-to-talk chord detection
│   ├── audio_devices.py             # Mic/speaker enumeration and selection
│   ├── action_loader.py             # Auto-discovers actions/*.py
│   ├── plugin_loader.py             # Auto-discovers plugins/*.py
│   ├── skill_loader.py              # Declarative skill registry & context manager
│   ├── task_manager.py              # Background task execution & status tracker
│   ├── log_bus.py                   # In-memory ring buffer with secret redaction
│   ├── repo_context.py              # Active workspace resolver & persistence
│   ├── design_resolver.py           # Raw HTML blueprint injector & adaptive resolver
│   ├── design_extractor.py          # On-demand HTML/CSS token & component extractor
│   ├── undo.py                      # Shared undo stack
│   ├── confirm.py                   # Irreversible-action confirmation gate
│   └── installer.py                 # OS-specific post-install setup
├── actions/
│   ├── antigravity_agent.py         # Google Antigravity autonomous coding agent
│   ├── opencode_agent.py            # OpenCode CLI multi-file implementation agent
│   ├── kilo_agent.py                # Kilo Code multi-file refactoring agent
│   ├── design_extractor.py          # On-demand design system extractor tool
│   ├── task_status.py               # Background task query and cancellation
│   ├── background_monitor.py        # Background topic monitoring
│   ├── browser_control.py           # Web browser automation
│   ├── code_helper.py               # Code review and generation
│   ├── computer_control.py          # Keyboard, mouse, window management
│   ├── computer_settings.py         # Volume, brightness, WiFi, power
│   ├── desktop.py                   # Desktop and taskbar control
│   ├── dev_agent.py                 # Developer task agent
│   ├── file_controller.py           # File system operations
│   ├── file_processor.py            # Document reading and summarization
│   ├── flight_finder.py             # Flight search
│   ├── game_updater.py              # Steam/Epic game updates
│   ├── open_app.py                  # Application launcher
│   ├── proactive.py                 # Proactive 2.0 check-ins
│   ├── reminder.py                  # OS-native scheduled notifications
│   ├── screen_processor.py          # Screen/webcam capture
│   ├── send_message.py              # Messaging integration
│   ├── system_monitor.py            # CPU/RAM/GPU telemetry
│   ├── weather_report.py            # Live weather data
│   ├── web_search.py                # Gemini + DDG parallel search
│   └── youtube_video.py             # YouTube playback control
├── skills/                          # Declarative skill packages (hamza_taste, opencode, kilo_code, etc.)
├── memory/
│   ├── __init__.py
│   ├── sqlite_memory.py             # SQLite FTS5 database with BM25 indexing
│   ├── memory_manager.py            # Load/save long_term.json, search
│   └── config_manager.py            # api_keys.json read/write, all getters/setters
├── plugins/
│   ├── __init__.py

│   ├── _template.py                 # Copy this to create a new plugin
│   ├── _google_core.py              # Shared OAuth for Gmail/Calendar
│   ├── _printer_core.py             # Shared printer connectivity
│   ├── quiz.py                      # Interactive quiz
│   ├── document_review.py           # Contract/policy review
│   └── ...                          # Drop-in skills
├── dashboard/
│   ├── __init__.py
│   └── server.py                    # FastAPI HTTP dashboard server
├── config/
│   ├── __init__.py
│   └── api_keys.json                # Configuration (git-ignored)
├── docs/                            # This documentation
└── DOCUMENTATION/                   # Previous documentation attempt
```

## File-by-File Documentation

### main.py (2284 lines)

**Purpose**: Application entry point, core engine, Gemini Live session management, audio I/O, tool dispatch.

**Key class**: `JarvisLive`
**Key functions**: `_build_config()`, `_execute_tool()`, `_listen_audio()`, `_send_realtime()`, `_pcm_visemes()`, `_build_config()`

**Dependencies**: `sounddevice`, `numpy`, `google-genai`, `PyQt6`, `memory/memory_manager.py`, `actions/*.py`, `core/*`

**Called by**: `python main.py`

### ui.py (5438 lines)

**Purpose**: PyQt6 HUD — main window, avatar canvas, waveform, activity log, settings drawer, all Qt widgets.

**Key class**: `JarvisUI` (inherits `QMainWindow`)
**Key classes**: `C` (color palette), `apply_ui_accent()`

**Dependencies**: `PyQt6`, `psutil`, `core/avatar.py`, `memory/config_manager.py`

**Called by**: `main.py` creates `JarvisUI()` instance

### core/action_loader.py (221 lines)

**Purpose**: Auto-discovers `actions/*.py` files with `TOOL` dict. Validates and registers actions.

**Key classes**: `ActionRegistry`, `ActionRecord`
**Key functions**: `discover_actions()`, `_validate()`, `_call_handler()`

**Called by**: `main.py` in `JarvisLive.__init__()`

### core/plugin_loader.py (285 lines)

**Purpose**: Auto-discovers `plugins/*.py` files with `PLUGIN` dict. Validates and registers plugins.

**Key classes**: `PluginRegistry`, `PluginRecord`
**Key functions**: `discover_plugins()`, `_validate()`, `_call_run()`

**Called by**: `main.py` in `JarvisLive.__init__()`

### core/undo.py (121 lines)

**Purpose**: Shared undo stack. Actions register reverse functions.

**Key functions**: `push_undo()`, `undo_last()`, `history()`, `clear()`
**Key constant**: `MAX_DEPTH = 10`

**Called by**: `main.py:_execute_tool()` (undo tool), action handlers

### core/confirm.py (161 lines)

**Purpose**: Confirmation gate for irreversible actions. UI-issued tokens.

**Key functions**: `request()`, `resolve()`, `bind()`
**Key constant**: `TIMEOUT_SECONDS = 90.0`

**Called by**: `actions/computer_settings.py` (shutdown, restart, WiFi)

### core/viseme.py (275 lines)

**Purpose**: Transcript-to-mouth-shape fusion. 50 mouth shapes per second.

**Key classes**: `VisemeStream`
**Key functions**: `text_to_visemes()`, `to_latin()`, `coverage()`
**Key data**: `VISEMES` dict, `_LETTER` dict, `_DIGRAPH` dict

**Called by**: `main.py` (viseme extraction), `ui.py` (avatar)

### core/echo.py (288 lines)

**Purpose**: Self-echo detection. Distinguishes user voice from assistant's own echo.

**Key classes**: `EchoGuard`
**Key functions**: `band_energies()`, `note_output()`, `is_user_speech()`

**Called by**: `main.py` (audio callback)

### core/wake_word.py (211 lines)

**Purpose**: Local "Hey Jarvis" detection using openwakeword.

**Key classes**: `WakeWordDetector`
**Key functions**: `is_ready()`, `install_and_download()`, `feed()`
**Key constant**: `WAKE_MODEL = "hey_jarvis"`

**Called by**: `main.py` (audio callback when sleeping)

### core/hotkey.py (173 lines)

**Purpose**: Push-to-talk chord detection (Ctrl+Space).

**Key classes**: `PushToTalk`
**Key functions**: `start()`, `stop()`, `_poll_loop()`

**Called by**: `main.py` (via `set_push_to_talk()`)

### core/audio_devices.py (421 lines)

**Purpose**: Microphone/speaker enumeration, filtering, measurement, resolution by name.

**Key functions**: `list_devices()`, `resolve()`, `prefetch()`, `_query()`
**Key constants**: `DEFAULT_LABEL`, `DEFAULT_VALUE`

**Called by**: `main.py`, `memory/config_manager.py`

### memory/memory_manager.py (479 lines)

**Purpose**: Load/save `long_term.json`, memory indexing, search, session summaries.

**Key functions**: `load_memory()`, `save_memory()`, `update_memory()`, `format_memory_for_prompt()`, `search_memory()`, `save_session_summary()`, `pop_last_session()`
**Key constants**: `MEMORY_MAX_CHARS = 200000`, `PROMPT_CORE_CHARS = 900`, `PROMPT_INDEX_CHARS = 420`

**Called by**: `main.py:_build_config()`, `save_memory` tool, `recall_memory` tool

### memory/config_manager.py (384 lines)

**Purpose**: All configuration getters/setters for `api_keys.json`.

**Key functions**: `get_voice()`, `save_voice()`, `get_wake_word_enabled()`, `save_wake_word_enabled()`, `get_push_to_talk_enabled()`, `get_plugin_enabled()`, `get_input_device()`, `save_input_device()`, etc.
**Key constants**: `AVAILABLE_VOICES`, `DEFAULT_VOICE`

**Called by**: `main.py`, `ui.py`, `core/*`

### core/gemini.py (439 lines)

**Purpose**: One-shot Gemini calls (non-live). Model ladder, quota management.

**Key functions**: `call()`, `text()`, `as_json()`, `client()`
**Key classes**: `_Reply`
**Key constants**: `_LADDERS`, `LIVE`, `FAST`, `SMART`, `SEARCH`

**Called by**: Actions, plugins, `actions/web_search.py`

### core/llm_client.py (586 lines)

**Purpose**: Local LLM client (Ollama/OpenAI-compatible) for planning and agent tasks.

**Key functions**: `call_llm()`, `call_llm_text()`, `call_llm_stream()`, `warmup_model()`, `ensure_ollama_running()`
**Key classes**: None (module-level functions)

**Called by**: `actions/dev_agent.py`, `actions/code_helper.py`

### dashboard/server.py (884 lines)

**Purpose**: FastAPI HTTP server for phone-based remote control.

**Key features**: AES-256-CBC encryption, QR code pairing, WebSocket support
**Key functions**: `new_key()`, `get_url()`, endpoint handlers

**Called by**: User's phone browser

### actions/computer_settings.py (962 lines)

**Purpose**: Volume, brightness, WiFi, power controls. Platform-specific implementations.

**Key functions**: `volume_up()`, `volume_down()`, `toggle_wifi()`, `shutdown()`, `restart()`
**Key import**: `from core import confirm`, `from core.undo import push_undo`

### actions/computer_control.py (589 lines)

**Purpose**: Keyboard shortcuts, mouse control, window management, clipboard.

**Key functions**: Keyboard/mouse/window operations
**Key import**: `pyautogui`, `pyperclip`, `pygetwindow`

### actions/screen_processor.py (183 lines)

**Purpose**: Screen and webcam capture for vision.

**Key functions**: `_capture_screen()`, `_capture_camera()`
**Key imports**: `mss`, `cv2`, `PIL`

### actions/web_search.py

**Purpose**: Web search with Gemini Grounded + DuckDuckGo fallback.

**Key functions**: `_news()`, search handlers
**Key imports**: `ddgs`, `requests`, `beautifulsoup4`

### plugins/_template.py (45 lines)

**Purpose**: Template for creating new plugins. Copy, rename, fill in.

**Shape**: `PLUGIN` dict + `run()` function

### setup.py (129 lines)

**Purpose**: OS-aware installer. Checks Python version, installs deps, fetches Playwright browsers.

**Key functions**: `_check_python()`, `_check_assets()`, `main()`

## Dependency Graph

```
main.py
├── imports: sounddevice, numpy, google-genai, PyQt6
├── ui.py (JarvisUI)
├── memory/memory_manager.py (load_memory, update_memory, etc.)
├── memory/config_manager.py (get_voice, get_wake_word_enabled, etc.)
├── core.action_loader (discover_actions)
├── core.plugin_loader (discover_plugins)
├── core.undo (undo_stack)
├── core.confirm (confirm_gate)
├── core.audio_devices
├── core.echo (EchoGuard)
├── core.viseme (VisemeStream)
├── core.wake_word (WakeWordDetector)
├── core.hotkey (PushToTalk)
├── actions.* (auto-discovered)
└── plugins.* (auto-discovered)

ui.py
├── imports: PyQt6, psutil
├── core.avatar (HoloAvatar)
└── memory.config_manager (config reads)

core/gemini.py
├── imports: google-genai
└── Called by: actions/web_search.py, plugins

core/llm_client.py
├── imports: requests
└── Called by: actions/dev_agent.py, actions/code_helper.py

actions/computer_settings.py
├── imports: core.confirm, core.undo
└── Uses: pyautogui, pyperclip, subprocess

actions/computer_control.py
├── imports: pyautogui, pyperclip
└── Uses: subprocess, platform

actions/screen_processor.py
├── imports: mss, cv2, PIL
└── Uses: config/api_keys.json

dashboard/server.py
├── imports: fastapi, uvicorn, cryptography
└── Uses: config/api_keys.json
```

## Summary

```
Entry: main.py → JarvisLive → JarvisUI
Core: core/*.py (all utility modules)
Actions: actions/*.py (auto-discovered tools)
Plugins: plugins/*.py (auto-discovered skills)
Memory: memory/*.py (persistent storage)
Dashboard: dashboard/server.py (remote control)
Config: memory/config_manager.py (all settings)
Total: ~30 Python files, ~15,000 lines of code
```