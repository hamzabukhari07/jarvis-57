# ZEZO — Codebase Map & Directory Architecture

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## Top-Level Repository Structure

```
ZEZO/
├── main.py                          # Core async engine, ZezoLive orchestrator, Gemini Live loop
├── ui.py                            # PyQt6 host window & WebEngine wrapper for React HUD
├── setup.py                         # OS-aware package installer & post-install setup
├── requirements.txt                 # Backend Python package manifest
├── readme.md                        # User-facing onboarding guide
├── .gitignore                       # Excludes logs, configs, caches, venv
├── LICENSE                          # CC BY-NC 4.0
├── core/                            # Core runtime systems, drivers & dispatchers
│   ├── prompt.txt                   # Production system prompt template (~480 lines)
│   ├── models.py                    # Single source of truth for model identifiers & ladders
│   ├── provider_health.py           # Background health-checker for Gemini & Groq
│   ├── gemini.py                    # One-shot tiered Gemini REST client & fallback ladder
│   ├── llm_client.py                # Local Ollama / OpenAI-compatible REST client
│   ├── llm_router.py                # Fast background text router (Groq → Gemini → Ollama)
│   ├── code_engines.py              # CLI coding engine drivers (Antigravity CLI, OpenCode, Kilo)
│   ├── teardown_engine.py           # REA Teardown Engine via rea-agents@6.7.0 CLI
│   ├── tunnel_manager.py            # Cloudflare Quick Tunnel daemon manager
│   ├── action_loader.py             # Dynamic action discoverer & registry (33 actions)
│   ├── fleet_manager.py             # Autonomous multi-agent fleet orchestrator & workspace isolation
│   ├── plugin_loader.py             # Plugin discoverer & execution sandbox
│   ├── skill_loader.py              # Declarative skill registry (`skills/<name>/SKILL.md`)
│   ├── skill_scanner.py             # Multi-stage security & prompt injection scanner
│   ├── task_manager.py              # Background task execution & subtask streaming
│   ├── clipboard_watcher.py         # Background OS clipboard monitor & classifier
│   ├── ui_server.py                 # aiohttp / FastAPI WebSocket & static UI server
│   ├── audio_devices.py             # Audio I/O device enumerator & resolver
│   ├── echo.py                      # Multi-band energy acoustic echo canceller
│   ├── hotkey.py                    # Push-to-Talk global keyboard hook (Ctrl+Alt)
│   ├── wake_word.py                 # Offline openwakeword detection engine
│   ├── viseme.py                    # Real-time phoneme-to-viseme mouth shape engine
│   ├── loop_gates.py                # Loop iteration guards & tool execution quotas
│   ├── git_sandbox.py               # Isolated Git worktree sandboxing for fleet agents
│   ├── repo_context.py              # Active workspace resolver & desktop project tracker
│   ├── design_resolver.py           # Blueprint injector & adaptive design resolver
│   ├── undo.py                      # Undo stack & contextual GUI undo dispatcher
│   ├── confirm.py                   # Irreversible action confirmation gate
│   ├── installer.py                 # Runtime requirement verifier & Playwright downloader
│   └── computer/                    # 3-Tier Desktop Perception & Automation Engine
│       ├── __init__.py              # Unified perception export
│       ├── windows_native.py        # Win32 APIs, DWM extended frame bounds, DPI awareness
│       ├── windows_uia.py           # Tier 1: Windows UI Automation (STA COM worker)
│       ├── ocr_engine.py            # Tier 1.5: Multilingual RapidOCR (CPU ONNX, 0 MB VRAM)
│       └── pyautogui_driver.py      # Cross-platform mouse & keyboard driver
├── actions/                         # Discrete atomic action tools (33 files)
│   ├── agent_reach.py               # Media metadata & video transcript extraction
│   ├── antigravity_agent.py         # Google Antigravity CLI autonomous coding agent
│   ├── ast_tool.py                  # Abstract Syntax Tree structural code analysis
│   ├── background_monitor.py        # Long-term topic & headline watcher
│   ├── browser_control.py           # Playwright headless browser automation
│   ├── code_engines_status.py       # Probe & health-check for Antigravity, OpenCode, Kilo
│   ├── computer_control.py          # Native OS automation, mouse, keyboard & batch actions
│   ├── computer_settings.py         # Hardware volume, brightness, power & network settings
│   ├── design_extractor.py          # On-demand design system token & CSS extractor
│   ├── desktop.py                   # Desktop workspace & active window controller
│   ├── file_controller.py           # Filesystem mutations, directory navigation, safe trash
│   ├── file_processor.py            # Rich document ingestion (PDF, DOCX, XLSX, PPTX, CSV)
│   ├── fleet_control.py             # Autonomous multi-agent fleet orchestrator
│   ├── flight_finder.py             # Flight schedule & price aggregator
│   ├── game_updater.py              # Gaming platform updates & launcher
│   ├── kilo_agent.py                # Kilo terminal coding engine wrapper
│   ├── opencode_agent.py            # OpenCode autonomous coding agent wrapper
│   ├── open_app.py                  # Native OS application launcher
│   ├── proactive.py                 # Proactive 2.0 conversational check-ins
│   ├── quick_snippet.py             # Fast code snippet generator & syntax validator
│   ├── recall_history.py            # Full-text BM25 search across sqlite_memory
│   ├── reminder.py                  # OS-native scheduled notifications
│   ├── reverse_engineer.py          # REA Teardown Engine browser scenario runner
│   ├── run_tool_batch.py            # Atomic execution of multiple action tools in 1 turn
│   ├── screen_processor.py          # Multi-monitor screenshot & webcam capture
│   ├── send_message.py              # External messaging integration (WhatsApp, Telegram)
│   ├── system_monitor.py            # Real-time hardware telemetry (CPU, RAM, GPU, temp)
│   ├── task_status.py               # Background task telemetry & cancellation
│   ├── weather_report.py            # Real-time weather data & forecasts
│   ├── website_cloner.py            # Offline website cloner using Uncage engine
│   ├── web_reader.py                # Anti-bot web content reader (Scrapling)
│   ├── web_search.py                # Google Grounded + DuckDuckGo search aggregator
│   └── youtube_video.py             # YouTube playback & transcript controller
├── frontend/                        # Modern React 18 / Vite SPA Frontend
│   ├── package.json                 # Modern dependencies (@assistant-ui, Three.js, Tailwind v4)
│   ├── vite.config.ts               # Vite configuration with Tailwind CSS plugin
│   └── src/                         # React component & state architecture
│       ├── App.tsx                  # Root shell hosting office, canvas, chat & modals
│       ├── main.tsx                 # React DOM mount point
│       ├── types/zezo.ts            # Complete TypeScript schema definitions
│       ├── hooks/useZezoSocket.ts   # WebSocket client with auto-reconnect & packet dispatcher
│       ├── lib/api.ts               # REST API fetch client (/api/settings, /api/tasks, etc.)
│       └── components/
│           ├── office/              # Scranton Autonomous Office Screen
│           │   ├── AutonomousOfficeScreen.tsx  # 2D pixel desk grid, sprite rendering, monitor telemetry
│           │   └── AgentDirectChatView.tsx     # 1-on-1 isolated context chat thread per agent
│           ├── memory/              # Knowledge Graph & Vault Visualization
│           │   ├── MemoryGraphCanvas.tsx       # 3D Force-Directed Knowledge Graph (Three.js)
│           │   ├── MemoryInspectorDrawer.tsx   # Markdown node viewer & wikilink inspector
│           │   └── NewMemoryModal.tsx          # Fast manual fact insertion dialog
│           ├── tasks/               # Background Task Management
│           │   └── TaskManagerModal.tsx        # Task tree viewer, output streaming, cancellation
│           ├── remote/              # Mobile Remote Access
│           │   └── MobileRemoteModal.tsx       # Cloudflare Quick Tunnel QR code & OTP token
│           ├── clipboard/           # Live Clipboard Watcher
│           │   └── ClipPeekOverlay.tsx         # Floating quick-action HUD for copied snippets
│           ├── assistant-ui/        # Conversational Chat Thread
│           │   ├── ZezoChatThread.tsx          # Assistant-UI thread with turn pills & shimmer labels
│           │   ├── thinking.tsx                # Reasoning step container
│           │   └── elements/                   # Turn process pills, web search chips
│           ├── canvas/              # WebGL Avatar & Visualizers
│           │   ├── CanvasView.tsx              # Split HUD workspace canvas
│           │   └── QiviAvatarVisualizer.tsx    # Audio-reactive 3D WebGL point-cloud avatar
│           ├── telemetry/           # Real-Time Telemetry & Logs
│           │   ├── BackendLogModal.tsx         # Real-time log bus stream with secret redaction
│           │   └── VortexVisualizer.tsx        # High-performance CSS canvas vortex animation
│           ├── settings/            # Modular ReUI Settings Dialog
│           │   ├── SettingsModal.tsx           # 9-tab settings modal dialog
│           │   ├── CodeEnginesSettingsTab.tsx  # Antigravity/OpenCode/Kilo status & configuration
│           │   └── SkillsSettingsTab.tsx       # Declarative skills viewer & editor
│           ├── fleet/               # Multi-Agent Management & Roster
│           │   ├── FleetRoster.tsx             # Interactive agent roster sidebar
│           │   └── AgentInspector.tsx          # Agent profile, permissions & sandbox inspector
│           ├── avatar/              # Avatar Badges & Icons
│           │   └── ChatAvatarIcon.tsx          # Real-time state-reactive agent avatar badge
│           ├── prompt-kit/          # Advanced Prompting & Thinking Primitives
│           │   ├── chain-of-thought.tsx        # Reasoning disclosure accordion
│           │   ├── code-block.tsx              # Syntax-highlighted code container
│           │   └── message.tsx                 # Base message card primitive
│           ├── layout/              # HUD Application Shell Layout
│           │   └── Header.tsx                  # Top status bar, audio device pill & tunnel indicator
│           ├── reui/                # ReUI Design System Primitives
│           │   ├── frame.tsx                   # Modal panel framing with opaque backgrounds
│           │   ├── confirm-dialog.tsx          # High-risk action confirmation modal
│           │   ├── card.tsx, chat.tsx, badge.tsx, callout.tsx, kbd.tsx
│           └── ui/                  # Headless UI Components (Buttons, Dialogs, Selects, Tabs)
├── memory/                          # Hybrid 3-Tier Memory Engine
│   ├── long_term.json               # Tier 1: User facts, core preferences & session summaries
│   ├── sqlite_memory.py             # Tier 2: SQLite WAL + FTS5 BM25 database (`zezo_brain.db`)
│   ├── vault_engine.py              # Tier 3: Local Markdown Vault (`memory/vault/*.md`) with `[[wikilinks]]`
│   ├── memory_manager.py            # High-level memory coordinator & prompt builder
│   └── config_manager.py            # Thread-safe getters/setters for `config/api_keys.json`
├── skills/                          # Declarative Agent Skills (`skills/<name>/SKILL.md`)
│   ├── hamza_taste/                 # Lead architect UI/UX aesthetic rules & ReUI invariants
│   ├── opencode/                    # OpenCode CLI workflow instructions
│   ├── kilo_code/                   # Kilo terminal refactoring instructions
│   └── figma_helper/                # Design-to-code extraction conventions
└── plugins/                         # Modular Drop-In Feature Extensions
    ├── _template.py                 # Standard plugin blueprint
    ├── _google_core.py              # Google OAuth2 credentials & token management
    ├── home_assistant/              # Tuya & smart home appliance integrations
    └── printer_control/             # Network printer spooling via MQTT
```

---

## Detailed Component Documentation

### 1. Application Core (`main.py`)
- **Key Class:** `ZezoLive`
- **Core Loop:** Connects to Google Gemini Live API via bidirectional WebSocket streaming (`cl.aio.live.connect`). Streams 16/24kHz PCM mic audio, manages turn commits, handles interruptions, and routes tool calls.
- **Background Task Watcher:** `_run_task_completion_watcher()` periodically polls `core.task_manager` to announce completed coding/scraping jobs via natural 1-sentence voice summaries while outputting full reports to the React HUD.
- **Push-to-Talk (PTT):** Controlled strictly via **`Ctrl+Alt`** chord detection in `core/hotkey.py`.

### 2. Frontend Container (`ui.py` & `core/ui_server.py`)
- `ui.py` launches a lightweight, frameless `PyQt6-WebEngine` window serving as the desktop container.
- `core/ui_server.py` hosts an asynchronous `aiohttp` server exposing:
  - Static distribution files built from `frontend/`.
  - WebSocket endpoint `/ws` providing full-duplex communication between Python and React.
  - REST endpoints for settings, task telemetry, skills, and code engine probing.

### 3. Modern React 18 SPA (`frontend/src/`)
- **AutonomousOfficeScreen:** Visualizes the autonomous fleet (Verve, Flux, Ahmad, Michael, Kelly) in an interactive 2D pixel-art office grid. Supports live task telemetry, desk coordinates, and instant 1-on-1 direct chat.
- **MemoryGraphCanvas:** Renders the 3D Force-Directed Knowledge Graph powered by Three.js, visualising memory nodes and wikilink topologies with audio-reactive viseme pulsing.
- **TaskManagerModal:** Provides real-time visibility into background subagents, displaying progress trees, execution logs, and immediate task cancellation buttons.
- **ClipPeekOverlay:** Non-intrusive floating HUD widget that detects clipboard updates and provides 1-click refactoring, explanation, or execution actions.

### 4. Action Tools (33 Discovered Actions)
Every action adheres strictly to `AGENTS.md` Rule 4 (one file per action, exporting `TOOL` and `handler()`). Newly added action tools include:
- `actions/code_engines_status.py`: Health inspector for CLI coding engines (`agy`, `opencode`, `kilo`).
- `actions/reverse_engineer.py`: REA Teardown Engine runner executing browser scenario interceptions.
- `actions/quick_snippet.py`: Instant verified code snippet generation.
- `actions/run_tool_batch.py`: Compound atomic tool execution in a single turn.
- `actions/recall_history.py`: High-speed BM25 full-text search across SQLite memory logs.
- `actions/ast_tool.py`: AST structural code inspector for Python files.

---

## High-Level Execution Dataflow

```
[ User Microphone ] ──(Ctrl+Alt PTT)──> [ core/hotkey.py ]
                                               │
                                               ▼
[ Google Gemini Live WebSocket ] <─── PCM Audio (16kHz) ─── [ main.py (ZezoLive) ]
           │                                                       ▲
           │ (Tool Call Dispatched)                                │ (Tool Result)
           ▼                                                       │
  [ core/action_loader.py ] ───────────────────────────────────────┘
           │
           ├──> [ actions/reverse_engineer.py ] ──> [ rea-agents@6.7.0 ]
           ├──> [ actions/fleet_control.py ]    ──> [ Git Sandboxed Workspaces ]
           ├──> [ actions/code_engines_status.py ] ──> [ agy / opencode / kilo ]
           └──> [ actions/computer_control.py ] ──> [ 3-Tier Perception: UIA / RapidOCR / Vision ]
                                               │
                                               ▼
                              [ core/ui_server.py (/ws) ]
                                               │
                                               ▼
                              [ React HUD: frontend/src/ ]
                               ├── AutonomousOfficeScreen.tsx
                               ├── MemoryGraphCanvas.tsx
                               └── ZezoChatThread.tsx
```
