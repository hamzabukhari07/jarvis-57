# JARVIS — System Architecture

> Project: JARVIS (JARVIS AI Assistant) | Version: JARVIS (54) | Python 3.11-3.13 | Windows/macOS/Linux | CC BY-NC 4.0

## 1. Overview
JARVIS is a real-time voice AI assistant that hears, sees, speaks, and controls your computer. Runs as a native desktop application with PyQt6 HUD, connects to Google Gemini Live API, and features a holographic 3D avatar with real-time lip-sync.

## 2. Component Map

### Entry Points
- main.py: Core loop — Gemini Live session, audio I/O, viseme extraction, tool dispatch
- ui.py: PyQt6 HUD — avatar canvas, waveform, log panel, settings drawer
- setup.py: OS-aware installer
- dashboard/server.py: FastAPI remote control server

### Core Modules
- core/llm_client.py: Local LLM client (Ollama/OpenAI)
- core/gemini.py: One-shot Gemini calls with model ladder
- core/wake_word.py: Local Hey Jarvis detection
- core/tts.py: Text-to-Speech engines
- core/stt.py: Speech-to-Text engines
- core/audio_devices.py: Audio device management
- core/viseme.py: Lip-sync engine
- core/echo.py: Self-echo guard
- core/confirm.py: Irreversible action gate
- core/undo.py: Shared undo stack
- core/hotkey.py: Push-to-talk
- core/plugin_loader.py: Plugin discovery
- core/action_loader.py: Action discovery
- core/avatar.py: Holographic avatar renderer
- core/avatar_mesh.py: Head geometry
- memory/memory_manager.py: Persistent memory
- memory/config_manager.py: Configuration access

### Built-in Actions (24+)
web_search, screen_processor, background_monitor, proactive, system_monitor, computer_settings, computer_control, open_app, browser_control, file_controller, file_processor, send_message, weather_report, flight_finder, youtube_video, game_updater, code_helper, dev_agent, desktop, reminder, camera

### Plugins
drop-in .py files in plugins/ with PLUGIN dict and run()

## 3. Data Flow
User Speaks -> Mic -> Wake Word Gate -> Echo Guard -> Gemini Live API -> Transcription + Visemes + Tool Calls -> Audio Playback -> Speaker -> Avatar

## 4. Session Lifecycle
Startup -> Wait for API Key -> Build Live Config -> Connect Gemini -> Main Loop (Mic, Receive, Play, Tool Dispatch, Background Tasks) -> Shutdown Summary -> Exit

## 5. Concurrency Model
- Asyncio for core event loop
- Threading for blocking I/O
- Sounddevice callbacks for real-time audio
- Separate event loop for dashboard

## 6. Key Design Principles
1. Auto-Discovery: Every action/plugin self-describes
2. Runtime Self-Knowledge: Identity assembled from live system
3. Memory Budgeting: Identity in prompt, rest on-demand
4. Graceful Degradation: Missing packages disable one feature
5. Cross-Platform: Same code on all OSes
6. Non-Blocking by Default
7. User-Confirmed Irreversible Actions
8. Undo First