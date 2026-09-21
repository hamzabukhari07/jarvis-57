# 🧠 AGENTS.md — System Context & Non-Negotiable Rules

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux  
> **Language & Framework:** Python 3.11–3.13, PyQt6, Google Gemini Live API (WebSockets)  

---

## ⚠️ READ THIS BEFORE MAKING ANY CODE CHANGES

This repository is a **Modular Monolith Agent Operating System**.
Every capability is isolated into self-describing action modules or skills.
To maintain system stability, prevent regression, and stop context decay, **all AI coding agents must strictly adhere to the rules below**.

---

## 📁 1. Real Project Directory Structure

```
zezo version 2/
├── main.py                     # ⚡ Application Orchestrator & Gemini Live WebSockets loop
├── ui.py                       # 🖥️ PyQt6 GUI & Holographic 3D Avatar (Software Rasterizer)
│
├── core/                       # 🧠 Core System Engines
│   ├── action_loader.py        # Dynamic action scanner (scans actions/*.py for TOOL dict)
│   ├── plugin_loader.py        # Dynamic user plugin scanner (scans plugins/*.py)
│   ├── skill_loader.py         # Dynamic declarative skill scanner (scans skills/*/)
│   ├── design_extractor.py     # Deterministic HTML/CSS design token & component extractor
│   ├── design_resolver.py      # Reference-first design system token resolver & preset injector
│   ├── task_manager.py         # Thread-safe background task registry & status tracker
│   ├── repo_context.py         # 3-tier active repository resolver & memory persistence
│   ├── prompt.txt              # System prompt injected into Gemini Live session
│   ├── gemini.py               # One-shot Gemini client with model fallback ladder
│   ├── llm_client.py           # Multi-provider LLM interface (Ollama, OpenAI, Groq)
│   ├── viseme.py               # Audio formant & text phoneme extractor for avatar lip-sync
│   ├── avatar.py               # Holographic head rasterizer & face state animator
│   ├── avatar_mesh.py          # 3D vector geometry for facial acting
│   ├── wake_word.py            # Local "Hey Jarvis" detector (openWakeWord)
│   ├── echo.py                 # Self-echo filter & mic bleed suppression
│   ├── hotkey.py               # Global hotkey listener (Ctrl+Space Push-to-Talk)
│   ├── audio_devices.py        # Speaker/Mic discovery & endpoint volume manager
│   ├── tts.py                  # TTS engine fallback (Edge-TTS, Kokoro, ElevenLabs)
│   ├── stt.py                  # STT engine fallback (Faster-Whisper, Vosk)
│   ├── confirm.py              # Safety gate for destructive/irreversible user actions
│   ├── undo.py                 # Action history & reversible state undo stack
│   ├── log_bus.py              # Backend log ring buffer (stdlib logging + stdout/stderr tee)
│   └── governance.py           # Path validation, dangerous-command DENY patterns, policy matrix
│
├── actions/                    # 🛠️ Self-Describing Tools (23 Discovered Actions)
│   ├── opencode_agent.py       # [opencode_run] Autonomous multi-file coding agent
│   ├── kilo_agent.py           # [kilo_run] Multi-file refactoring & editing agent
│   ├── code_helper.py          # [code_helper] Single function / inline snippet generator
│   ├── dev_agent.py            # [dev_agent] Read-only codebase exploration & bug hunter
│   ├── design_extractor.py     # [extract_design_system] HTML/CSS design token extractor
│   ├── task_status.py          # [task_status] Background task status / progress query
│   ├── open_app.py             # [open_app] Launch / terminate desktop apps & open files
│   ├── computer_control.py     # [computer_control] Keyboard shortcuts, clicks, hotkeys
│   ├── computer_settings.py    # [computer_settings] System volume, brightness, power
│   ├── file_controller.py      # [file_controller] File/folder CRUD, search, organization
│   ├── file_processor.py       # [file_processor] File reading, parsing, batch edits
│   ├── screen_processor.py     # [screen_process] Desktop screenshot capture & analysis
│   ├── web_search.py           # [web_search] Google / DuckDuckGo live search
│   ├── web_reader.py           # [web_read_page] Deep web scraping & markdown extraction
│   ├── reminder.py             # [reminder] Scheduled alarms, timers, reminders
│   ├── system_monitor.py       # [system_status] Live CPU, RAM, GPU, battery metrics
│   ├── background_monitor.py   # [background_monitor] Long-running process surveillance
│   ├── send_message.py         # [send_message] Telegram / WhatsApp messaging
│   ├── weather_report.py       # [weather_report] Live weather forecast
│   ├── flight_finder.py        # [flight_finder] Real-time flight search
│   ├── youtube_video.py        # [youtube_video] YouTube search and video playback
│   ├── game_updater.py         # [game_updater] Gaming news and patch notes
│   ├── desktop.py              # [desktop_control] Desktop icons & window positioning
│   ├── antigravity_agent.py    # [antigravity_run] Antigravity workflow runner
│   └── agent_reach.py          # [agent_reach] Social research API & media extraction
│
├── memory/                     # 💾 Persistence & Intelligence Layer
│   ├── sqlite_memory.py        # SQLite FTS5 database (zezo_brain.db) with BM25 search
│   ├── memory_manager.py       # Memory persistence & session summary extractor
│   ├── config_manager.py       # Thread-safe read/write for user config & API keys
│   └── repo_context.json       # Persisted active repository path
│
├── skills/                     # 📚 Declarative Multi-Step Skill Packages (10 Skills)
│   ├── hamza_taste/            # Studio UI aesthetic, anti-slop rules & design presets
│   ├── opencode/               # Full autonomous coding workflow
│   ├── kilo_code/              # Free-tier fast refactoring workflow
│   ├── antigravity_agent/      # Agentic code synthesis workflow
│   ├── git_workflow/           # Professional Git staging & commit workflow
│   ├── social_research/        # YouTube, Reddit & GitHub research pipeline
│   ├── system_diagnostics/     # Hardware telemetry & diagnostic routine
│   ├── web_scraper/            # Anti-bot web extraction pipeline
│   ├── web_research_pipeline/  # Query decomposition & deep research
│   └── test_fastapi_deploy/    # Backend deployment verification
│
├── config/                     # 🔒 User Configuration & Secrets
│   ├── api_keys.json           # API keys, assistant identity, voice configuration
│   └── settings.json           # User UI and audio preferences
│
├── AGENTS.md                   # 🧠 Master AI Agent Context & Rules (This File)
├── decisions.md                # 🏛️ Architecture Decision Records (ADR Log)
├── FUTURE_UPGRADES.md          # 🚀 Groq Hybrid & 7-Layer Agent OS Architecture
└── PROJECT_ARCHITECTURE.md     # 🌐 Standalone Master Architecture Blueprint
```

---

## 🛡️ 2. Non-Negotiable Engineering Rules

1. **One File Per Action in `actions/`:**
   - Every action file must export a module-level `TOOL` dictionary and a callable `handler`.
   - The handler must accept `parameters: dict` and optional keyword arguments (`player`, `speak`, `response`, `session_memory`).
2. **Never Hardcode Tool Logic in `main.py`:**
   - `main.py` only hosts inline tools tied directly to the live WebSocket state (`system_status`, `screen_process`, `manage_monitor`, `shutdown_jarvis`). All other tools must reside in `actions/`.
3. **Never Block the PyQt6 Main GUI Thread:**
   - All network I/O, heavy subprocesses, and CLI calls must run in background threads (using `core.task_manager` or `QThread`).
4. **Coding Agents Must Be Asynchronous (`task_id` pattern):**
   - Heavy agents (`opencode_run`, `kilo_run`) must return a `task_id` immediately so the voice loop remains 100% responsive.
   - Long-running progress must be queried through `task_status`.
5. **Never Speak Code or Raw Tool Output:**
   - Spoken audio must remain high-level conversational summary (1-2 sentences in user's language). Code, syntax, diffs, and large JSON payloads must be routed to the HUD content panel or clipboard.
6. **Synchronize Tool Descriptions & System Prompt:**
   - If a tool's purpose, parameters, or behavior changes, update:
     1. `TOOL["description"]` in the action file.
     2. `core/prompt.txt` under `[CODING DELEGATION]` or `[EXECUTION]` if routing is affected.
7. **Creator Attribution:**
   - Always document and acknowledge **Hamza Bukhari** as the creator and lead architect.
8. **Strict 3-Layer Verification Rule:**
   - After ANY code change, invoke the `verify` skill (`.antigravity/skills/verify.md`).
   - The verify skill requires:
     - **Layer 1:** static checks (compile, import, discovery)
     - **Layer 2:** runtime evidence (actual log lines, real file outputs, API responses)
     - **Layer 3:** regression checks (2+ existing features)
   - You may NOT write "FIXED" until all 3 layers pass.
   - If you cannot run runtime tests, write "UNVERIFIED" with reason — do NOT write "FIXED".

---

## 🔗 3. Inter-Dependency Matrix

| If You Change / Edit... | You MUST Also Verify / Update... | Why |
| :--- | :--- | :--- |
| Any `actions/*.py` | `core/action_loader.py`, `core/prompt.txt` | Ensure `TOOL` schema is valid and routing rules in `prompt.txt` match. |
| `actions/opencode_agent.py` or `actions/kilo_agent.py` | `core/task_manager.py`, `actions/task_status.py`, `core/repo_context.py` | Task submission, live progress reporting, and directory resolution depend on them. |
| `actions/open_app.py` | `actions/browser_control.py`, `actions/computer_control.py` | Window and process termination (`close_application_by_name`) is shared. |
| `memory/config_manager.py` | `actions/opencode_agent.py`, `actions/kilo_agent.py`, `main.py` | Model names (`get_opencode_model()`, `get_voice()`) are retrieved from here. |
| `core/prompt.txt` | `main.py` (`_build_config`) | Ensure prompt tokens `{assistant_name}`, `{platform}`, `{capabilities}`, `{limits}` remain intact. |
| `ui.py` | `main.py` | Signal-slot connections between `JarvisUI` and `JarvisLive` (logs, avatar visemes, waveform). |
| `core/log_bus.py` | `ui.py` (`LogConsoleOverlay`, `Ctrl+L`), `memory/sqlite_memory.py` (`redact_secrets`) | The console renders the bus ring buffer; `redact_secrets` is the sole scrub source and must stay the only secret-pattern list. |

---

## 🔄 4. Standard Feature Workflow

```
[ 1. SCOPE ] ──► Define the feature, inputs, outputs, and constraints.
      │
[ 2. AUDIT ] ──► Inspect existing actions, schemas, and dependencies.
      │
[ 3. DESIGN ] ──► Ensure every generated value has a clear source; check ADRs.
      │
[ 4. DEVELOP ] ──► Write minimum required code; adhere to TOOL contract.
      │
[ 5. VERIFY ] ──► Run py_compile, import checks, and action_loader discovery.
      │
[ 6. DOCUMENT ] ──► Update AGENTS.md, prompt.txt, and decisions.md.
```

---

## 📋 5. Known Quirks & Architectural Constraints

- **Windows Subprocess Hiding:** Windows requires `CREATE_NO_WINDOW` (`_WIN_HIDE`) on background child processes to prevent terminal window popups.
- **PyAutoGUI Fail-Safe:** Set `pyautogui.FAILSAFE = False` for simple key presses to avoid coordinate boundary exceptions.
- **Action Loader Signature Matching:** Handlers receive kwargs dynamically inspected from their function signature (`parameters`, `player`, `speak`, etc.).
- **Windows Volume API:** `pycaw` requires `AudioUtilities.GetSpeakers().EndpointVolume` (not deprecated `.Activate()`).

---

## 📖 6. Learning Journal Convention

After completing each feature, create or append to `LEARNING_JOURNAL.md` at the repo root.

### Format:
```markdown
## [YYYY-MM-DD] — <feature name>
- What was built
- Why this approach was chosen
- What alternatives were considered
- Key files touched
- What to remember for future work
```

Keep it human-readable. Update it as part of the `verify` step.
