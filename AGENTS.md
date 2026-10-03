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
│   ├── models.py               # Single source of truth for model ids (Gemini / Antigravity / Groq)
│   ├── provider_health.py      # Startup provider & model health-check (marks dead models)
│   ├── gemini.py               # One-shot Gemini client with model fallback ladder
│   ├── llm_client.py           # Multi-provider LLM interface (Ollama, OpenAI, Groq)
│   ├── llm_router.py           # Background text router: Groq → Gemini → Ollama (live voice untouched)
│   ├── voice_fallback.py       # Offline fallback voice loop (VAD → STT → LLM → TTS) when Gemini Live is down
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
├── actions/                    # 🛠️ Self-Describing Tools (25 Discovered Actions)
│   ├── opencode_agent.py       # [opencode_run] Autonomous multi-file coding agent
│   ├── kilo_agent.py           # [kilo_run] Multi-file refactoring & editing agent
│   ├── antigravity_agent.py    # [antigravity_run] Studio UI & Antigravity synthesis agent
│   ├── code_helper.py          # [code_helper] Single function / inline snippet generator
│   ├── dev_agent.py            # [dev_agent] Read-only codebase exploration & bug hunter
│   ├── fleet_control.py        # [fleet_control] Autonomous named multi-agent fleet orchestrator
│   ├── design_extractor.py     # [extract_design_system] HTML/CSS design token extractor
│   ├── task_status.py          # [task_status] Background task status / progress query
│   ├── website_cloner.py       # [clone_website] Offline site cloner & asset localizer
│   ├── browser_control.py      # [browser_control] Browser tab navigation & interactions
│   ├── open_app.py             # [open_app] Launch / terminate desktop apps & open files
│   ├── computer_control.py     # [computer_control] Keyboard shortcuts, clicks, hotkeys
│   ├── computer_settings.py    # [computer_settings] System volume, brightness, power
│   ├── file_controller.py      # [file_controller] File/folder CRUD, search, organization
│   ├── file_processor.py       # [file_processor] File reading, parsing, batch edits
│   ├── screen_processor.py     # [screen_process] Desktop screenshot capture & analysis
│   ├── web_search.py           # [web_search] Google / DuckDuckGo live search
│   ├── web_reader.py           # [web_read_page] Deep web scraping & markdown extraction
│   ├── agent_reach.py          # [agent_reach] Multi-platform intelligence & Whisper transcription
│   ├── reminder.py             # [reminder] Scheduled alarms, timers, reminders
│   ├── system_monitor.py       # [system_status] Live CPU, RAM, GPU, battery metrics
│   ├── background_monitor.py   # [background_monitor] Long-running process surveillance
│   ├── send_message.py         # [send_message] Telegram / WhatsApp messaging
│   ├── weather_report.py       # [weather_report] Live weather forecast
│   ├── flight_finder.py        # [flight_finder] Real-time flight search
│   ├── youtube_video.py        # [youtube_video] YouTube search and video playback
│   ├── game_updater.py         # [game_updater] Gaming news and patch notes
│   └── desktop.py              # [desktop_control] Desktop icons & window positioning
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
   - After ANY code change, verify all 3 layers yourself before reporting success:
     - **Layer 1 (static):** `python -m py_compile` on every touched file, plus `core/action_loader.py` discovery if `actions/` changed.
     - **Layer 2 (runtime):** real evidence — actual log lines, real file outputs, real API responses. Never claim a run you did not perform.
     - **Layer 3 (regression):** confirm 2+ existing features still work.
   - You may NOT write "FIXED" until all 3 layers pass.
   - If you cannot run runtime tests, write "UNVERIFIED" with reason — do NOT write "FIXED".
9. **Mandatory Code Graph (CGC) Pre-Flight Query:**
   - Before modifying, refactoring, or **debugging** any module, you MUST query the Code Graph first to inspect callers, callees, and dependency blast radius.
   - The graph is exposed as MCP tools prefixed `codegraph_` (opencode namespace):
     | Tool | Use for |
     | :--- | :--- |
     | `codegraph_find_code` | locate a symbol / search code content |
     | `codegraph_analyze_code_relationships` | **callers & callees — the main blast-radius tool** |
     | `codegraph_calculate_cyclomatic_complexity` | complexity of one function |
     | `codegraph_find_most_complex_functions` | hunt complexity hotspots |
     | `codegraph_find_dead_code` | find unused code |
     | `codegraph_execute_cypher_query` | custom Cypher when the above are not enough |
     | `codegraph_list_indexed_repositories` | confirm the graph actually covers this repo |
   - **Debugging protocol (follow in order, do not skip to grep):**
     1. `codegraph_find_code` — find the symbol and confirm the graph is not stale.
     2. `codegraph_analyze_code_relationships` — enumerate every caller before you edit.
     3. Read only the files that query points to.
     4. Edit, then re-run the caller query to confirm you did not miss a call site.
   - **CLI fallback** (when MCP tools are absent): `cgc -db kuzudb analyze callers <fn>`, `cgc -db kuzudb find name <symbol>`, `cgc -db kuzudb find content "<query>"`, `cgc -db kuzudb analyze complexity`.
   - **If you see `Could not set lock on file`:** the embedded KùzuDB is single-owner and another process (e.g. an IDE's own CGC server) holds it. Do NOT retry — fall back to `grep`/`glob` immediately and say so in your summary. Only one IDE can hold the KùzuDB graph at a time.
   - Refresh a stale graph with `cgc -db kuzudb update` (auto-watch is enabled, so this is usually unnecessary).

10. **Anti-Slop Code Hygiene Enforcement:**
   - All code changes must strictly adhere to `.agents/skills/antislop_code/SKILL.md`:
     - Function cyclomatic complexity must stay **< 15**.
     - No massive `if/elif` ladders (use dictionary dispatch).
     - No bloated boilerplate or obvious echo comments.

---

## 🔗 3. Inter-Dependency Matrix

| If You Change / Edit... | You MUST Also Verify / Update... | Why |
| :--- | :--- | :--- |
| Any `actions/*.py` | `core/action_loader.py`, `core/prompt.txt`, `docs/TOOLS.md` | Ensure `TOOL` schema is valid, routing rules match, and `docs/TOOLS.md` is synced. |
| `actions/opencode_agent.py` or `actions/kilo_agent.py` | `core/task_manager.py`, `actions/task_status.py`, `core/repo_context.py` | Task submission, live progress reporting, and directory resolution depend on them. |
| `actions/open_app.py` | `actions/browser_control.py`, `actions/computer_control.py` | Window and process termination (`close_application_by_name`) is shared. |
| `memory/config_manager.py` | `actions/opencode_agent.py`, `actions/kilo_agent.py`, `main.py`, `docs/CONFIGURATION.md` | Model names & API key masking config are retrieved here; `docs/CONFIGURATION.md` must stay synced. |
| Any Core Engine / Feature | `docs/<FILE>.md`, `docs/README.md` | **Mandatory Documentation Sync Rule:** Every feature build/bug fix must update `docs/`. |
| `core/prompt.txt` | `main.py` (`_build_config`) | Ensure prompt tokens `{assistant_name}`, `{platform}`, `{capabilities}`, `{limits}` remain intact. |
| `ui.py` / `frontend/index.html` | `main.py`, `core/ui_server.py` | Signal-slot / WebSocket connections between UI, server, and live audio engines. |
| `core/log_bus.py` | `ui.py` (`LogConsoleOverlay`, `Ctrl+L`), `memory/sqlite_memory.py` (`redact_secrets`) | The console renders the bus ring buffer; `redact_secrets` is the sole scrub source and must stay the only secret-pattern list. |

---

## 🔄 4. Integrated Skill System & Automatic Workflow Routing

The ZEZO development ecosystem operates through an integrated two-tier skill architecture located in `.agents/skills/`.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       WORKFLOW SKILLS (STAGES)                                         │
├───────────────────┬─────────────────────────┬───────────────────┬───────────────────┬──────────────────┤
│ vision_suggestions│ repo_opportunity_audit  │ debug_diagnosis   │ feature_planning  │ implementation   │
│ • Idea exploration│ • External repo audit   │ • Bug root cause  │ • Architecture doc│ • Code authoring │
│ • UX brainstorming│ • Feature extraction    │ • Log diagnosis   │ • Dependency steps│ • Schema & docs  │
│ • Read-only       │ • Target comparison     │ • Read-only       │ • Read-only       │ • Active mutation│
└─────────┬─────────┴───────────┬─────────────┴─────────┬─────────┴─────────┬─────────┴────────┬─────────┘
          │                     │                       │                   │                  │
          ▼                     ▼                       ▼                   ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     FOUNDATIONAL SKILLS (PILLARS)                                      │
├─────────────────────────────────────────────────────┬──────────────────────────────────────────────────┤
│ code_graph_intelligence                             │ antislop_code                                    │
│ • KùzuDB CGC graph pre-flight                       │ • Cyclomatic complexity < 15                     │
│ • Caller & callee blast radius                      │ • Dictionary dispatch tables                     │
│ • Symbol definition & complexity hotspots           │ • Zero decorative/echo comments                  │
└─────────────────────────────────────────────────────┴──────────────────────────────────────────────────┘
```

### Automatic Request Routing Table

| User Intent / Request Pattern | Active Workflow Skill | Foundational Skills Applied | Execution Boundary |
| :--- | :--- | :--- | :--- |
| Exploring an idea, clarifying vision, or asking "how could we build X?" | `vision_suggestions` | `code_graph_intelligence` | **Strictly Read-Only** (No code changes) |
| Investigating a cloned repo or third-party project for reusable features | `repo_opportunity_audit` | `code_graph_intelligence` | **Strictly Read-Only** (No copying code) |
| Debugging an error, diagnosing logs, or investigating "why is X failing?" | `debug_diagnosis` | `code_graph_intelligence` | **Strictly Read-Only** (No code edits) |
| Turning an approved idea into a technical roadmap or architecture plan | `feature_planning` | `code_graph_intelligence` | **Strictly Read-Only** (Generates plan only) |
| Implementing an approved feature, coding a phase, or authorized refactor | `implementation` | `antislop_code` + `code_graph_intelligence` | **Authorized Mutation** (Requires prior plan/approval) |
| Checking if something works, running tests, or hunting regressions | `verification` | `code_graph_intelligence` | **Strictly Read-Only** (3-Layer verification evidence) |
| Authoring or modifying any code file (`.py`, `.js`, `.css`) | (Auto-Enforced) | `antislop_code` | **Mandatory Quality Standard** |
| Assessing blast radius, callers, or refactoring impact | (Auto-Enforced) | `code_graph_intelligence` | **Structural Navigation & Invariants** |

---

## 🛡️ 5. Approval & Safety Boundaries

1. **Discovery is Read-Only:** `vision_suggestions` and `repo_opportunity_audit` produce analysis and options. They MUST NOT modify project files or install packages without authorization.
2. **Planning is Read-Only:** `feature_planning` creates structured roadmap documents in `planning/`. It MUST NOT modify application source code until implementation is explicitly authorized.
3. **Implementation Requires Explicit Authorization:** The agent must only modify code when the user explicitly instructs execution (e.g. *"Implement Phase 1"*, *"Apply the approved plan"*).
4. **Verification-Only is Read-Only:** When asked to verify, test, or check status, report test results and failures. Do NOT silently apply code fixes without authorization.
5. **Clean-Room Integration:** `repo_opportunity_audit` must never copy third-party code directly. Re-implement cleanly following ZEZO's architecture and Anti-Slop principles.
6. **Material Scope Change Gate:** If an unexpected roadblock or breaking change is discovered during implementation, STOP and seek user alignment before expanding scope.

---

## 📋 6. Known Quirks & Architectural Constraints

- **Windows Subprocess Hiding:** Windows requires `CREATE_NO_WINDOW` (`_WIN_HIDE`) on background child processes to prevent terminal window popups.
- **PyAutoGUI Fail-Safe:** Set `pyautogui.FAILSAFE = False` for simple key presses to avoid coordinate boundary exceptions.
- **Action Loader Signature Matching:** Handlers receive kwargs dynamically inspected from their function signature (`parameters`, `player`, `speak`, etc.).
- **Windows Volume API:** `pycaw` requires `AudioUtilities.GetSpeakers().EndpointVolume` (not deprecated `.Activate()`).

---

## 📖 7. Learning Journal Convention

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

---

## 🚨 8. Regression Rules — DO NOT BREAK

These rules exist because bugs were fixed. Breaking any of them will
reintroduce a previously-fixed bug.

### Rule 1: No backdrop-filter inside modals
- `.modal-overlay` may have `backdrop-filter: blur(12px)`.
- Elements inside the modal (`.modal-panel`, `.modal-panel .frame-inner`,
  any nested card/badge/button) MUST NOT have `backdrop-filter`.
- Modal panel backgrounds must be OPAQUE (`#0a0a0a`, not `rgba(...,0.95)`).

### Rule 2: Never use `transition: all`
- Always list explicit properties:
  `transition: border-color 0.15s ease, background-color 0.15s ease;`
- Never write `transition: all ...` in any CSS rule.

### Rule 3: Never remove `_zezoAnimActive` from openModal
- `window.openModal` in `frontend/js/ui.js` MUST set
  `window._zezoAnimActive = false;`
- `function openModal` in the inline `<script>` in `frontend/index.html`
  MUST set `window._zezoAnimActive = false;`
- `closeModal` in BOTH files MUST contain:
  `const anyOpen = document.querySelector('.modal-overlay.open');`
  `if (!anyOpen) { window._zezoAnimActive = !document.hidden && !window._zezoDragging; }`
- These lines MUST NEVER be removed during refactoring.

### Rule 4: Hide avatar GIF while modal is open
- `openModal` MUST set:
  `document.getElementById('vortex-gif').style.visibility = 'hidden';`
- `closeModal` MUST set:
  `document.getElementById('vortex-gif').style.visibility = 'visible';`
- `id="vortex-gif"` on the avatar MUST NEVER be renamed.

### Rule 5: openModal must not close its own id
- `openModal(id)` MUST NOT call `closeModal(id)` for the same id.
- `openModal(id)` MUST NOT call any function that closes the same id.

### Rule 6: Settings is a MODAL, not a drawer
- The settings panel is `<div class="modal-overlay" id="settings-modal">`.
- Do NOT reintroduce `.settings-dropdown-drawer` or anchored drawers.
- Gear button onclick is `openModal('settings-modal')`.

### Rule 7: QtWebEngine does not support `vh` reliably
- Prefer `position: fixed` with `inset: 0` over `vh`-based heights.
- If you must use `vh`, add a JS fallback on `window.resize`.

### Rule 8: Gemini Live Audio Streaming Requires Explicit Sample Rate
- `main.py` streaming mic audio blobs to Google Gemini Live API (`gemini-3.1-flash-live-preview`) MUST always specify the explicit sample rate parameter:
  `types.Blob(data=..., mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")` (e.g. `audio/pcm;rate=16000`).
- NEVER send bare `audio/pcm` without `rate=` — omitting it triggers gateway 1011 internal server disconnects.
- `send_realtime_input()` must use `audio=types.Blob(...)` keyword format.



**Code Graph is available in this project. Use it before making any code changes.**

1. Analyze the Code Graph to trace the relevant functions, dependencies, callers, and affected files.
2. Use the graph to identify the complete execution flow before modifying anything.
3. Cross-check graph findings against the actual source code. Do not assume the graph is fully up to date.
4. Identify potential side effects and regression risks in connected modules.
5. Make only the changes required for Phase 1. Avoid unrelated refactoring.
6. After implementation, run relevant tests and report the exact files changed and test results.

Do not skip Code Graph analysis, and do not modify code until you have completed the dependency analysis.