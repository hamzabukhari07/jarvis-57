# 📐 Technical Architecture Plan: Non-Blocking Gemini Voice Loop, Native Windows UIA Desktop Control, & Groq Background Coprocessor

> **Target Goal:** Completely decouple Gemini Live real-time audio session from tool execution, eliminate slow/paid Vision calls for standard desktop automation via native Windows UIA (0ms vision lag, 100% free), and route background LLM synthesis to Groq LPU.  
> **Status:** APPROVED FOR PLANNING  
> **Lead Architect:** Hamza Bukhari  
> **Traceability Standard:** [`feature_planning/SKILL.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/.agents/skills/feature_planning/SKILL.md)  

---

## 🎯 1. Requirements & Invariants

### Functional Requirements
- **REQ-VOICE-001 (Zero Voice Dead-Air):** The Gemini Live WebSocket audio stream must **never freeze or mute** while a tool or sub-agent runs. Immediate verbal acknowledgement must be streamed to the user while work executes asynchronously.
- **REQ-UIA-001 (Direct Desktop Control without Vision):** Desktop UI control (typing into Notepad, clicking Calculator buttons, reading screen values) must execute through **native Windows UI Automation (UIA)** and Win32 accessibility tree before falling back to Vision models.
- **REQ-UIA-002 (Accurate Random Text Generation & Typing):** `computer_control(action='random_data')` must not merely generate a string in memory; if requested in the context of writing/typing, it must directly insert the text into the active focused window.
- **REQ-GROQ-001 (Groq LPU Background Acceleration):** Background text parsing, code analysis, and query synthesis must automatically route through `core/llm_router.py` (Groq LPU @ 800+ tokens/sec) without consuming Gemini tokens.

### Non-Functional & Non-Regression Invariants
- **INV-001 (AGENTS.md Rule 3 & Rule 8):** Audio streaming to Gemini Live must preserve explicit PCM sample rate (`audio/pcm;rate=16000`).
- **INV-002 (Thread Safety):** UI automation calls and Groq requests must run in worker threads (`core.task_manager` / `asyncio` executors) without blocking PyQt6 or the WebSocket reader loop.
- **INV-003 (Anti-Slop):** Cyclomatic complexity must remain `< 15` with clean dictionary dispatch and zero bloated comments.

---

## 🏛️ 2. Architecture: Current vs. Proposed State

```
[CURRENT SYSTEM: Blocking Tool Flow]
User Speech ──► Gemini Live WebSockets ──► Tool Call ('screen_process')
                      │                         │ (Blocks Voice Loop ~2-5s)
                      ▼                         ▼
             [Audio Buffer Freezes] ◄─── Gemini Vision Model (Cloud API)

─────────────────────────────────────────────────────────────────────────

[PROPOSED ARCHITECTURE: 3-Tier Asynchronous OS Flow]
User Speech ──► Gemini Live (Voice Dispatcher) ──► Immediate 1-Word Audio ('On it.')
                      │
                      ▼ Dispatches Non-Blocking Task
             ┌──────────────────────────────────────────────┐
             │         Async Task Orchestrator              │
             └───────┬──────────────────────────────┬───────┘
                     │                              │
                     ▼                              ▼
        [L0/L1 Native Windows UIA]      [Groq LPU Coprocessor]
        • Direct OS Window Access       • 800 tokens/sec Analysis
        • 0ms Vision Lag / 0 MB VRAM    • 100% Free Tier API
        • Instant Click & Type          • Summaries & Code Gen
                     │                              │
                     └──────────────┬───────────────┘
                                    │ Emits Task Result
                                    ▼
                      Gemini Live Voice Summary ('Done.')
```

---

### 📊 Code Graph Breakdown: Before vs. After Mapping

#### 🧠 1. GEMINI: Before vs. After
| Task / Feature | Current System (Before) | Target State (After Plan) | Benefit & Rationale |
| :--- | :--- | :--- | :--- |
| **Realtime Voice Stream** | Gemini Live (`main.py`) | 🌟 **Gemini Live (`main.py`)** | Dedicated voice face — never blocked by background work. |
| **Google Search Grounding** | Gemini Search (`web_search.py`) | 🌟 **Gemini Search (`web_search.py`)** | Live factual grounding metadata directly from Google. |
| **Complex Visual Inspection** | Gemini Vision (`screen_process`) | 🌟 **Gemini Vision (`screen_process`)** | Reserved for chart, diagram & complex photo understanding. |
| **Desktop Element Clicks** | ❌ Gemini Vision (`computer_control.py:185`) | ➡️ **Windows UIA (Zero Gemini)** | 2s lag eliminated, 100% free local Windows API. |
| **Notepad Text Reading** | ❌ Gemini Vision (`screen_process`) | ➡️ **Windows UIA (Zero Gemini)** | Direct UIA text extraction in < 15ms. |
| **Code Exploration Agent** | ❌ Gemini Flash (`dev_agent.py`) | ➡️ **Groq LPU (Zero Gemini)** | Gemini quota preserved; Groq scans at 800+ tok/s. |
| **File Parsing & Summaries**| ❌ Gemini Flash (`file_processor.py`) | ➡️ **Groq LPU (Zero Gemini)** | Fast background file parsing. |
| **YouTube Video Summaries** | ❌ Gemini Flash (`youtube_video.py`) | ➡️ **Groq LPU (Zero Gemini)** | Instant video summary without rate limits. |
| **Flight Info Extraction** | ❌ Gemini Flash (`flight_finder.py`) | ➡️ **Groq LPU (Zero Gemini)** | Quick JSON regex parsing via Groq. |

#### ⚡ 2. GROQ LPU: Before vs. After
| Task / Feature | Current System (Before) | Target State (After Plan) | Performance & Speed |
| :--- | :--- | :--- | :--- |
| **Inline Code Generation** | `actions/code_helper.py` | 🌟 **Groq LPU (`code_helper.py`)** | Sub-second inline code writing. |
| **Autonomous Dev Agent** | ❌ (Gemini dependent) | 🌟 **Groq LPU (`dev_agent.py`)** | Instant codebase bug hunting & file exploration. |
| **File Processor Engine** | ❌ (Gemini dependent) | 🌟 **Groq LPU (`file_processor.py`)** | Batch parsing multiple files in parallel. |
| **Research Synthesis** | `actions/agent_reach.py` | 🌟 **Groq LPU (`agent_reach.py`)** | Fast web/Reddit/GitHub intelligence summaries. |
| **Video & Media Summaries**| ❌ (Gemini dependent) | 🌟 **Groq LPU (`youtube_video.py`)** | Transcript distillation in < 1s. |
| **Flight Search Extraction**| ❌ (Gemini dependent) | 🌟 **Groq LPU (`flight_finder.py`)** | Live flight JSON table generation. |

#### 🖥️ 3. NATIVE WINDOWS UIA: Desktop Control Pillar
| Desktop Action | Current System (Before) | Target State (After Plan) |
| :--- | :--- | :--- |
| **Type into Notepad / Word** | Keystrokes + Vision verify | 🌟 **Multi-tier Text Input:** UIA ValuePattern → Clipboard-Safe Paste → Keystrokes (with foreground target-window guard). |
| **Click Calculator / App Buttons** | Screenshot + Gemini Vision | 🌟 **Direct UIA Element Click** (Win32 Tree invoke in < 15ms local latency, 0 Vision). |
| **Random Data / Mock Typing** | String in memory | 🌟 **Explicit Target Verification + Clipboard-Safe Typing** into verified active window. |
| **Read Window Contents** | Screenshot OCR / Gemini Vision | 🌟 **Direct Control Text Read vs Entire Window Text Read** (< 10ms local extraction). |

---

## 📋 3. Phased Atomic Implementation Roadmap

### Phase 1: Robust Multi-Tier Desktop Control & Input Serialization (`actions/computer_control.py`, `core/computer/windows_uia.py`, `core/computer/input_driver.py`)
- **TASK-101 (Serialized Desktop Input Queue):** Introduce a thread-safe serialized desktop input lock to prevent concurrent tool calls from fighting for mouse/keyboard focus.
- **TASK-102 (Target-Window Focus Guard):** Ensure any typing action verifies the expected application (`hwnd` / process name) is genuinely in the foreground before sending text.
- **TASK-103 (Multi-Tier Text Injection Ladder):** Implement resilient text entry:
  1. `UIA ValuePattern / TextPattern` (Fastest, direct injection).
  2. `Clipboard-Safe Paste (Ctrl+V)` (Universal compatibility across classic Win32 / Electron apps).
  3. `Virtual Keystrokes` (Fallback for custom gaming / raw inputs).
- **TASK-104 (Explicit Typing Intent on `random_data`):** When user intent implies typing, generate the data AND inject it into the active target canvas in one atomic step.

### Phase 2: Non-Blocking Tool Protocol & Audio Pipeline Continuity (`main.py`, `core/task_manager.py`)
- **TASK-201 (Gemini Live Protocol Preservation):** Preserve Google Gemini Live Bidi WebSockets function-calling protocol:
  * Fast tools (< 300ms) return direct tool response.
  * Long-running / Heavy tools (> 1s) immediately return an async `task_id` with verbal acknowledgement, dispatching execution to background workers without starving `_recv_audio()` or `_listen_audio()`.
- **TASK-202 (Audio Continuity & State Telemetry):** Prevent buffer underruns and audio dropouts by decoupling WebSocket write queues from background thread completion.

### Phase 3: Gradual Step-by-Step Groq LPU Task Migration (`core/llm_router.py`)
- **TASK-301 (Step 1 Migration - YouTube & Media):** Migrate `actions/youtube_video.py` summaries to `core.llm_router.generate_text()` (Groq first) and verify latency/quality.
- **TASK-302 (Step 2 Migration - Batch File Parsing):** Migrate `actions/file_processor.py` to Groq LPU with automatic Gemini fallback on context overflow.
- **TASK-303 (Step 3 Migration - Dev Agent Bug Hunter):** Migrate `actions/dev_agent.py` to Groq LPU for rapid codebase exploration.

### Phase 4: Autonomous Specialist Fleet, Dynamic Engine/Model Binding & White-Label "ZEZO Coder" Facade (`core/fleet_manager.py`, `actions/fleet_control.py`, `core/prompt.txt`, `actions/code_helper.py`, `actions/opencode_agent.py`, `actions/antigravity_agent.py`, `core/task_manager.py`, `frontend/office.html`)

```
                               ┌──────────────────────────────────────────────┐
                               │             USER VOICE / PROMPT              │
                               │ "Build full-stack app / research / refactor" │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                                       [ MICHAEL (HEAD MANAGER) ]
                                 • Analyzes requirement & breaks tasks
                                 • Dispatches to specialized team agents
                                                      │
                        ┌─────────────────────────────┼─────────────────────────────┐
                        ▼                             ▼                             ▼
               [ AGENT 1: ALI ]               [ AGENT 2: AHMAD ]            [ AGENT 3: USMAN ]
            Role: Frontend Specialist      Role: Full-Stack / Backend      Role: QA & Bug Hunter
            Engine: Antigravity CLI        Engine: OpenCode CLI           Engine: Kilo Code CLI
            Model: Claude 3.5 Sonnet       Model: DeepSeek Coder          Model: Qwen 2.5 Coder
            Instance: Desktop/app_ui       Instance: Desktop/app_api      Instance: Desktop/tests
                        │                             │                             │
                        └─────────────────────────────┼─────────────────────────────┘
                                                      ▼
                                    ┌───────────────────────────────────┐
                                    │    SCRANTON PIXEL OFFICE FLOOR    │
                                    │ • Live Avatars walking to desks   │
                                    │ • Real-time Task progress cards   │
                                    │ • Git Worktree status & logs      │
                                    └───────────────────────────────────┘
```

- **TASK-401 (Specialist Fleet Manager & Dynamic Engine/Model Matrix):**
  - Implement dynamic binding in `core/fleet_manager.py` and `actions/fleet_control.py`: Each agent (e.g. *Ali*, *Ahmad*, *Dwight*, *Michael*) has a configurable **Role**, **CLI Engine** (Antigravity, OpenCode, Kilo), and **Model ID** (Claude 3.5 Sonnet, DeepSeek Coder, GPT-4o, Qwen 2.5).
  - Enable multiple agents to run parallel tasks concurrently on the same or different CLI engines in isolated Git worktrees.
- **TASK-402 (Michael Master Dispatcher & Task Decomposition):**
  - When given high-level complex prompts (*"Build a full-stack e-commerce app"*), Michael automatically decomposes the task:
    * Dispatches Frontend/UI to `antigravity` specialist (e.g. Ali).
    * Dispatches Backend/API to `opencode` specialist (e.g. Ahmad).
    * Dispatches QA/Testing to `kilo` specialist (e.g. Usman).
- **TASK-403 (Scranton Pixel Office Real-Time Synchronization):**
  - Connect agent lifecycle events (`fleet_control`) to `frontend/office.html` WebSocket stream:
    * Desk assignment and walking pixel avatar animations.
    * Live progress percentages, tool micro-logs, and Git worktree diffs rendered on individual office desks.
- **TASK-404 (100% White-Label Brand Protection & Persona Masking):**
  - Enforce zero-leakage persona rule: Raw engine names (`Antigravity`, `OpenCode`, `Kilo`) are **strictly prohibited** in spoken voice output and front-facing UI task cards.
  - All operations, status cards, and verbal summaries are delivered under the single unified **`ZEZO Coder`** brand.
- **TASK-405 (Retire Redundant In-Memory Scratch Builders):**
  - Transition full-stack and scratch builds from in-memory generator (`dev_agent.py`) to the unified fleet CLI orchestrator.
  - Offload heavy multi-file code generation to dedicated coding models with infinite context, protecting Gemini Live voice quota (0% voice tokens burned for coding).
- **TASK-406 (Dedicated Fast CLI Terminal Runner):**
  - Streamline `actions/code_helper.py` exclusively for instant shell/CLI execution (e.g. `git`, `pip`, `npm`, `uvicorn`, background daemons) without in-memory code generation ladders.
- **TASK-407 (Unified Verification & Deprecation Clean-Up):**
  - Run complete 3-Layer verification test suite and verify end-to-end multi-agent fleet dispatching through background `TaskManager` and live Scranton Office Floor synchronization.

---

## 🧪 4. Traceability & 3-Layer Verification Matrix

| Requirement | Tasks | Code Files | Verification Test (3 Layers) |
| :--- | :--- | :--- | :--- |
| **REQ-UIA-001** | TASK-101, TASK-102, TASK-103 | `core/computer/windows_uia.py`, `actions/computer_control.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Direct text injection into Notepad with target-window validation.<br>**Layer 3:** Calculator button arithmetic verification. |
| **REQ-UIA-002** | TASK-104 | `actions/computer_control.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Verify random string is actively written to Notepad canvas.<br>**Layer 3:** Full pytest run. |
| **REQ-VOICE-001** | TASK-201, TASK-202 | `main.py`, `core/task_manager.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Measure continuous mic packet stream (>500 packets) during background tool execution.<br>**Layer 3:** Zero audio underruns or WebSocket 1011 disconnects. |
| **REQ-GROQ-001** | TASK-301, TASK-302, TASK-303 | `core/llm_router.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Verify YouTube & file processor logs confirm `[LLM] served by Groq`.<br>**Layer 3:** All 22 test suites pass. |
| **REQ-CLI-001** | TASK-401 to TASK-407 | `core/fleet_manager.py`, `actions/fleet_control.py`, `core/prompt.txt`, `actions/code_helper.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Multi-instance specialist fleet executes via unified ZEZO Coder facade, syncing live with Scranton Office Floor without burning Gemini voice quota.<br>**Layer 3:** Zero command blocking & instant task_id returns. |

---

## ⚠️ 5. Risk & Rollback Register

| Risk ID | Description | Severity | Mitigation |
| :--- | :--- | :--- | :--- |
| **RISK-001** | Target window loses focus during typing | High | TASK-102 Foreground Window Guard aborts or re-focuses before keystrokes are sent. |
| **RISK-002** | UIA ValuePattern unsupported by custom editor (e.g. VS Code, Chrome) | Medium | Automatic Tier-2 fallback to Clipboard-Safe Paste (`Ctrl+V`). |
| **RISK-003** | Gemini Live drops session if tool response is delayed | High | Enforce task_id return for long tasks to maintain WebSocket protocol synchronization. |
| **RISK-004** | Groq rate limits on free-tier RPM | Low | Automatic fallback ladder in `core/llm_router.py`: Groq → Gemini Flash → Local Ollama. |
| **RISK-005** | External CLI (OpenCode/Kilo) not installed on host machine | Medium | Graceful fallback error reporting through TaskManager to prompt user installation. |
| **RISK-006** | Engine name leakage in voice output | Low | Strict zero-leakage prompt rules enforce white-label "ZEZO Coder" identity across all speech. |
| **RISK-007** | Parallel fleet tasks colliding on same directory | Medium | Enforce isolated Git worktree or subfolder path for each active agent instance. |



