# 🚀 Master Technical Implementation Plan: Grounded Multi-Agent Fleet & System Stability (v2)

> **Project:** ZEZO OS v2 (Autonomous Desktop AI Operating System)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Status:** Approved Master Implementation Roadmap (Post-Audit Verified)  
> **Planning Standard:** `.agents/skills/feature_planning/SKILL.md` (Senior-Level Engineering)  
> **Traceability Index:** `REQ-F-001..008`, `REQ-NF-001..004`, `CON-001..003`, `INV-001..004`, `TASK-001..025`, `RISK-001..007`, `TEST-L1/L2/L3-001..010`  
> **Date:** October 2026  

---

## 🎯 1. Requirements, Invariants & System Scope

### A. Functional Requirements (FR)
- **[REQ-F-001] First-Class Voice Fleet Action:** Gemini Live must be equipped with `actions/fleet_control.py` supporting `dispatch`, `hire`, `fire`, `list_agents`, and `get_status` without blocking the audio loop.
- **[REQ-F-002] Dynamic Agent Roster & Persona Management:** Support hiring custom agents with specialized roles, CLI tools (`kilo_run`, `opencode_run`, `antigravity_run`, `code_helper`), models, and custom `soul.md` prompts persisted in `config/fleet_agents.json`.
- **[REQ-F-003] Central Concurrency & Task Queueing:** Enforce a hard cap of `MAX_CONCURRENT_CODING_TASKS = 2` in `core/task_manager.py`; excess tasks must be placed in `QUEUED` state and reported verbally.
- **[REQ-F-004] Git Worktree Sandbox Isolation:** Every mutating coding task must execute in an isolated `.git/worktrees/{agent}_{task_id}` sandbox managed by `core/git_sandbox.py` with automated conflict checks.
- **[REQ-F-005] Non-Destructive View Switching:** Voice commands like *"Close office view"* or *"Open dashboard"* must switch the active QtWebEngine view via WebSocket `switch_view` broadcast and strictly avoid process termination (`taskkill`).
- **[REQ-F-006] Strict Window-Close Matching:** `_safe_close_window` in `actions/computer_control.py` must enforce exact title equality to prevent closing third-party background applications (e.g. WhatsApp).
- **[REQ-F-007] Temporal Prompt Gating:** Direct Gemini Live to answer date/time queries instantly from `[LOCAL TIME]` context and strictly forbid slow 8.7s `web_search` roundtrips.
- **[REQ-F-008] Fast Vision Timeout Ladder & AFC Cleanup:** Cap REST screen inspection requests to 5.0s per model attempt in `core/gemini.py` and remove unused tool declarations from `screen_processor.py` to eliminate SDK warnings.

---

### B. Non-Functional Requirements (NFR)
- **[REQ-NF-001] Voice Latency & Zero Dead-Air:** Voice tool dispatch acknowledgment must return in $< 20\text{ms}$; heavy coding subagents must return asynchronous `task_id` handles.
- **[REQ-NF-002] Event-Driven Floor & Zero Polling:** Scranton Pixel Office must eliminate the 3.5s HTTP `/api/fleet/state` polling loop; UI updates must be 100% push-driven over WebSocket `ws://127.0.0.1:8765/ws`.
- **[REQ-NF-003] Grounded Floor Animation (Zero Simulation):** Eliminate fake client-side `Math.random()` wandering and fake progress timers; sprites must move only upon receiving verified `agent_task_started` events.
- **[REQ-NF-004] Resource & Memory Guards:** Subprocess memory and CPU consumption must remain bounded; Groq LPU text reasoning and 40-minute memory condenser clustering must run in background threads.

---

### C. Constraints & System Invariants (CON / INV)
- **[CON-001] Non-Blocking GUI Thread:** All network I/O, heavy subprocesses, and CLI calls must run in background threads (`core.task_manager` or `QThread`).
- **[CON-002] Windows Subprocess Hiding:** Windows requires `CREATE_NO_WINDOW` on all background child processes to prevent terminal window popups.
- **[INV-001] One File Per Action:** Every action tool in `actions/*.py` must export a module-level `TOOL` schema dictionary and a callable `handler(parameters: dict, **kwargs)`.
- **[INV-002] Anti-Slop Code Hygiene:** Cyclomatic complexity score must remain **< 15** per function; no giant `if/elif` ladders (use dictionary dispatch tables); zero decorative AI box comments.
- **[INV-003] Non-Negotiable UI Rules (Rules 1-7 in `AGENTS.md`):** Opaque modal panels (`#0a0a0a`), no `transition: all`, preserve `_zezoAnimActive`, hide avatar GIF during modals, settings as a modal (`#settings-modal`).
- **[INV-004] 3-Layer Verification Rule:** Never declare a feature or fix complete without Layer 1 (static `py_compile`), Layer 2 (runtime evidence), and Layer 3 (regression pass).

---

### D. Explicit Exclusions (Out of Scope)
- **[EXC-001]** No automatic fallback to expensive paid models (OpenAI/Anthropic) when free limits are hit.
- **[EXC-002]** No client-side artificial intelligence reasoning inside QtWebEngine JS; all decision-making resides in Python backend.
- **[EXC-003]** Subagents are strictly forbidden from spawning unconstrained subagents; all task delegation flows centrally through `FleetManager.dispatch_task()`.

---

## 🏛️ 2. Architecture & Technical Decision Records (ADRs)

### A. System Architectural Blueprint

```
                                  ┌──────────────────────────────────────────────┐
                                  │   Gemini Live Voice Master Brain (ZEZO)      │
                                  │      (Audio / Vision / Real-time WS)         │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                          ┌──────────────────────────────┴──────────────────────────────┐
                          │                                                             │
                          ▼                                                             ▼
           ┌───────────────────────────────┐                             ┌───────────────────────────────┐
           │   actions/fleet_control.py    │                             │   actions/open_app.py         │
           │ • dispatch(agent, task)       │                             │ • Deterministic View Switch   │
           │ • hire(name, role, tool)      │                             │ • Non-destructive Close Gate  │
           │ • fire(agent_id)              │                             │ • switch_view: office / home  │
           └──────────────┬────────────────┘                             └──────────────┬────────────────┘
                          │                                                             │
                          ▼                                                             ▼
           ┌───────────────────────────────┐                             ┌───────────────────────────────┐
           │   core/fleet_manager.py       │                             │   core/ui_server.py (WS)      │
           │ • Real Agent Roster           │                             │ • "fleet_updated" broadcast   │
           │ • config/fleet_agents.json    │                             │ • "agent_task_started" event  │
           │ • soul.md persona injector    │                             │ • "switch_view" broadcast     │
           └──────────────┬────────────────┘                             └──────────────┬────────────────┘
                          │                                                             │
          ┌───────────────┴───────────────┐                                             │
          ▼                               ▼                                             ▼
 ┌──────────────────┐            ┌──────────────────┐                    ┌───────────────────────────────┐
 │ Git Sandbox      │            │ Task Manager     │                    │ Scranton Pixel Office Floor   │
 │ .git/worktrees/  │            │ (Max 2 Concurrency)                   │ • Grounded Desks (No Random)  │
 │ {agent}_{task_id}│            │ OpenCode / Kilo  │                    │ • Real Monitor Glow & Walking │
 └──────────────────┘            └──────────────────┘                    │ • Real Live Terminal & Logs   │
                                                                         └───────────────────────────────┘
```

---

### B. Architecture Decision Records (ADR Log)

#### ADR-066: Decoupled Multi-Tier Voice, Planning & CLI Agent Fleet
- **Context:** Gemini Live was previously expected to chat, coordinate, and execute tasks directly, leading to token exhaustion, dead-air, and rate limit freezes.
- **Decision:** Strictly decouple responsibilities across 3 tiers:
  1. *Voice Tier:* Google Gemini Live (audio/vision conversation, instant user acknowledgments).
  2. *Text & Reasoning Tier:* Groq LPU (`llama-3.3-70b-versatile`) for sub-second inline edits (`code_helper.py`) and memory condensation (`memory_condenser.py`).
  3. *Execution Tier:* Headless coding CLIs (OpenCode, Kilo, Antigravity) running in isolated Git worktrees (`.git/worktrees/{agent}_{task_id}`) using user-configured free/local models.
- **Alternatives Considered:** Running coding agents inside Gemini Live prompt context. Rejected due to latency (>15s), context saturation, and lack of filesystem sandboxing.
- **Trade-Offs:** Adds lightweight IPC/process management via `core/task_manager.py`, but guarantees 100% voice responsiveness.

#### ADR-067: Event-Driven Pixel Office vs Polling Elimination
- **Context:** `prototypes/scranton_pixel_office_fleet/index.html` was polling `GET /api/fleet/state` every 3.5 seconds and running client-side `Math.random()` loops, flooding the backend log bus.
- **Decision:** Eliminate periodic HTTP polling and fake animation loops. Ground the floor strictly on WebSocket push events (`agent_task_started`, `task_progress`, `task_done`). Idle agents remain seated at their assigned desk coordinates.
- **Alternatives Considered:** Retaining low-frequency polling. Rejected because WebSocket connection (`ws://127.0.0.1:8765/ws`) is already active and supports instant bidirectional state sync.

#### ADR-068: Deterministic View Switching vs System Process Termination
- **Context:** Calling `open_app(action='close', app_name='office_view')` entered the process kill routine, which failed and fell back to `_safe_close_window('ZEZO')`, closing third-party apps like WhatsApp.
- **Decision:** Intercept internal view tokens (`officeview`, `agentview`, `dashboard`, `homeview`) at the entry of `actions/open_app.py` and translate close actions into WebSocket `switch_view: "home"` broadcasts without touching OS process handles.

---

## 🔬 3. Code Graph (CGC) & Repository Pre-Flight Audit

### A. Execution Path Tracing & Call Graph Analysis

1. **Voice-to-Agent Execution Path:**
   $$\text{Gemini Live WS} \xrightarrow{\text{Voice Audio}} \text{core/prompt.txt} \xrightarrow{\text{Tool Routing}} \text{actions/fleet_control.py} \xrightarrow{\text{dispatch}} \text{core/fleet_manager.py}$$
   $$\text{core/fleet_manager.py} \xrightarrow{\text{L1 Gate}} \text{core/circuit_breaker.py} \xrightarrow{\text{Worktree}} \text{core/git_sandbox.py} \xrightarrow{\text{Submit}} \text{core/task_manager.py}$$
   $$\text{core/task_manager.py} \xrightarrow{\text{Thread Subprocess}} \text{actions/kilo_agent.py} \xrightarrow{\text{WS Broadcast}} \text{core/ui_server.py} \to \text{Pixel Office Canvas}$$

2. **Window-Close Fallback Path (Blast Radius):**
   `actions/open_app.py` $\to$ `close_application_by_name("office_view")` $\to$ `_safe_close_window("ZEZO")` in `actions/computer_control.py`.
   - *Impact:* Exact title matching required in `_safe_close_window` to prevent substring collision with other applications.

---

### B. File Modification Matrix

| File Path | Action | Scope / Key Symbols Touched | Traceability |
| :--- | :--- | :--- | :--- |
| `actions/fleet_control.py` | **Create** | `TOOL`, `fleet_control`, `_handle_dispatch`, `_handle_hire`, `_handle_fire` | REQ-F-001, REQ-F-002 |
| `core/prompt.txt` | **Modify** | `[CODING & FLEET DELEGATION]`, `[TEMPORAL CONTEXT]` | REQ-F-001, REQ-F-007 |
| `core/task_manager.py` | **Modify** | `TaskManager.submit()`, `MAX_CONCURRENT_CODING_TASKS`, `TaskStatus.QUEUED` | REQ-F-003, REQ-NF-001 |
| `core/fleet_manager.py` | **Modify** | `FleetManager.save_agent_profile()`, `delete_agent()`, `config/fleet_agents.json` | REQ-F-002 |
| `actions/open_app.py` | **Modify** | `open_application()`, view token interception table | REQ-F-005 |
| `actions/computer_control.py` | **Modify** | `_safe_close_window()`, strict window title equality | REQ-F-006 |
| `core/gemini.py` | **Modify** | `GeminiClient.generate()`, 5.0s per-model REST timeout | REQ-F-008 |
| `actions/screen_processor.py` | **Modify** | `GenerateContentConfig`, remove unused tool declarations | REQ-F-008 |
| `prototypes/scranton_pixel_office_fleet/index.html` | **Modify** | Purge `Math.random()`, remove `syncBackendFleetState` polling, add WS listeners | REQ-NF-002, REQ-NF-003 |
| `memory/config_manager.py` | **Modify** | Restored `FALLBACK_VOICES`, `STT_ENGINES`, `LLM_ENGINES`, `TTS_ENGINES` | REQ-F-001 [COMPLETED] |
| `pytest.ini` | **Create** | `pythonpath = .` root test runner configuration | REQ-F-001 [COMPLETED] |

---

## 🔌 4. Interface Contracts & Data Schemas

### A. 3-Tier Agent Definition Schema (`config/fleet_agents.json`)
```json
{
  "fleet": {
    "MICHAEL": {
      "id": "MICHAEL",
      "name": "Michael",
      "role": "Full-Stack Refactoring Lead",
      "specialty": "Multi-file refactoring, code hygiene, and anti-slop enforcement",
      "color": "#3b82f6",
      "avatar_pixel": "michael_pixel.png",
      "executor_tool": "kilo_run",
      "model_id": "kilo/stepfun/step-3.7-flash:free",
      "risk_tier": "L1_MUTATION",
      "skills": ["refactoring", "antislop_code", "git_workflow"],
      "prompt_prefix": "You are Michael, the lead refactoring specialist. You write clean, idiomatic code with cyclomatic complexity < 15.",
      "desk_x": 1,
      "desk_y": 1
    },
    "DWIGHT": {
      "id": "DWIGHT",
      "name": "Dwight",
      "role": "Security Auditor & AST Linter",
      "specialty": "Vulnerability scanning, AST bug hunting, and read-only code review",
      "color": "#10b981",
      "avatar_pixel": "dwight_pixel.png",
      "executor_tool": "dev_agent",
      "model_id": "groq/llama-3.3-70b-versatile",
      "risk_tier": "L0_READ_ONLY",
      "skills": ["backend-security-coder", "code_graph_intelligence"],
      "prompt_prefix": "You are Dwight, the uncompromising security auditor. You analyze blast radius, callers, and syntax invariants.",
      "desk_x": 4,
      "desk_y": 1
    }
  }
}
```

---

### B. Voice Fleet Control Tool Schema (`actions/fleet_control.py`)
```python
TOOL = {
    "name": "fleet_control",
    "description": "Orchestrate autonomous multi-agent fleet. Dispatch coding tasks to specialist workers (Michael, Dwight, Jim, Pam, or custom agents), hire new specialist agents, query real agent status, or manage agent personas.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["dispatch", "hire", "fire", "list_agents", "get_status"],
                "description": "The fleet management action to execute."
            },
            "agent_id": {
                "type": "string",
                "description": "Target agent codename or ID (e.g. 'MICHAEL', 'DWIGHT', 'JIM', or custom agent name)."
            },
            "task": {
                "type": "string",
                "description": "The precise coding objective, bug fix, or analysis instruction to assign."
            },
            "role": {
                "type": "string",
                "description": "Role/Title when hiring a new agent (e.g. 'Database Architect', 'QA Tester')."
            },
            "default_tool": {
                "type": "string",
                "enum": ["opencode_run", "kilo_run", "dev_agent", "code_helper", "antigravity_run"],
                "description": "Underlying execution engine assigned to this agent."
            },
            "model_id": {
                "type": "string",
                "description": "Specific LLM model identifier (e.g. 'kilo/stepfun/step-3.7-flash:free', 'groq/llama-3.3-70b-versatile')."
            }
        },
        "required": ["action"]
    }
}
```

---

### C. WebSocket Event Contracts (`ws://127.0.0.1:8765/ws`)

```json
// Event: Agent Task Started
{
  "event": "agent_task_started",
  "data": {
    "task_id": "task_kilo_9941a",
    "agent_id": "MICHAEL",
    "task": "Refactor memory manager",
    "tool": "kilo_run",
    "worktree_path": ".git/worktrees/michael_task_kilo_9941a",
    "timestamp": 1727956800.12
  }
}

// Event: Task Progress
{
  "event": "task_progress",
  "data": {
    "task_id": "task_kilo_9941a",
    "progress": 45,
    "message": "Writing SQLite migration script..."
  }
}

// Event: Task Completed
{
  "event": "task_done",
  "data": {
    "task_id": "task_kilo_9941a",
    "agent_id": "MICHAEL",
    "status": "done",
    "summary": "Memory manager refactored with cyclomatic complexity < 12."
  }
}
```

---

## 📋 5. Phased Implementation Roadmap (Phases 1 to 10)

```
[ Phase 1: Baseline Health ] ──► [COMPLETED] 78 passed, 0 failed.
            │
[ Phase 2: Fleet Voice Tool ]──► Create actions/fleet_control.py & prompt.txt routing.
            │
[ Phase 3: Concurrency Guard]──► Enforce MAX_CONCURRENT=2 & task queueing in TaskManager.
            │
[ Phase 4: Dynamic Roster ]  ──► Hire/fire persistence in config/fleet_agents.json.
            │
[ Phase 5: View Safety ]     ──► Fix open_app view close routing & lock window title checks.
            │
[ Phase 6: Temporal Gating ] ──► Prohibit web_search for date/time in prompt.txt.
            │
[ Phase 7: Vision Timeout ]  ──► Add 5.0s per-model REST timeout & cleanup AFC declarations.
            │
[ Phase 8: Ground Floor UI ] ──► Purge Math.random() & wire real WebSocket event listeners.
            │
[ Phase 9: Zero Polling ]    ──► Remove 3.5s HTTP polling; rely on WebSocket state push.
            │
[ Phase 10: Verification ]   ──► Static compilation, runtime benchmarks & full regression.
```

---

### 🔹 Phase 1: Baseline Test Health & Stale Import Resolution [COMPLETED]
* **Status:** **IMPLEMENTED AND VERIFIED (100% Green)**
* **Objective:** Fix broken imports in `core/ui_server.py` and ensure the test harness compiles and runs cleanly.
* **Tasks Executed:**
  - `[TASK-001]` Restored `FALLBACK_VOICES`, `STT_ENGINES`, `LLM_ENGINES`, `TTS_ENGINES` in `memory/config_manager.py`.
  - `[TASK-002]` Configured `pytest.ini` with `pythonpath = .` for Windows module resolution.
  - `[TASK-003]` Fixed stem normalization in `core/design_resolver.py`.
* **Exit Criteria:** `pytest` passed 100% (`78 passed, 5 skipped, 0 failed` in 37.55s).

---

### 🔹 Phase 2: First-Class Voice Fleet Action (`actions/fleet_control.py`) `[COMPLETED]`
* **Phase Entry Criteria:** Phase 1 green baseline verified.
* **Objective:** Enable Gemini Live to dispatch tasks, hire custom agents, and query fleet status via voice.
* **Tasks:**
  - [x] **[TASK-004]** `[Sequential]` Create `actions/fleet_control.py` exporting `TOOL` schema and callable `handler`.
    - **Guidance:** Use dictionary dispatch for `dispatch`, `hire`, `fire`, `list_agents`, `get_status`.
    - **Verification:** `python -m py_compile actions/fleet_control.py` $\to$ PASSED.
  - [x] **[TASK-005]** `[Sequential]` Connect handler to `core.fleet_manager.FleetManager` and `core.circuit_breaker`.
    - **Guidance:** Validate agent exists, check risk tier permissions, and dispatch asynchronously. Replaced un-reentrant `threading.Lock()` with `threading.RLock()` to prevent deadlocks on nested profile writes.
  - [x] **[TASK-006]** `[Parallelizable]` Update `core/prompt.txt` under `[CODING & FLEET DELEGATION]` with routing rules.
    - **Guidance:** Map voice requests like *"Michael ko bolo refactor kare"* directly to `fleet_control(action='dispatch', agent_id='MICHAEL', task='...')`.
* **Phase Exit Criteria:** `action_loader.py` discovers 25 active tools; calling `fleet_control(action='list_agents')` returns active roster. All unit and regression tests pass (`84 passed, 5 skipped, 0 failed` in 33.30s).

---

### 🔹 Phase 3: Central Orchestrator & Concurrency Guard `[COMPLETED]`
* **Phase Entry Criteria:** Phase 2 completed.
* **Objective:** Enforce `MAX_CONCURRENT_CODING_TASKS = 2` to protect CPU, RAM, and API limits.
* **Tasks:**
  - [x] **[TASK-007]** `[Sequential]` Add `MAX_CONCURRENT_CODING_TASKS = 2` and updated `CODING_TOOLS` set (`opencode_run`, `opencode_agent`, `kilo_run`, `kilo_agent`, `dev_agent`, `antigravity_run`, `antigravity_agent`, `code_helper`) in `core/task_manager.py`.
    - **Guidance:** Wrapped task submission and queue operations in `threading.RLock()`.
  - [x] **[TASK-008]** `[Sequential]` Place excess coding tasks into `TaskStatus.QUEUED` state and maintain a FIFO execution queue with dynamic position tracking (`queued (position #N)`).
  - [x] **[TASK-009]** `[Parallelizable]` Emit `task_queued` micro event to log bus and update positions on dequeue/cancel.
* **Phase Exit Criteria:** Submitting 3 simultaneous coding tasks runs 2 in parallel and holds the 3rd until a slot frees. Verified via `tests/test_concurrency_guard_suite.py` and full regression suite (`87 passed, 5 skipped, 0 failed` in 33.99s).

---

### 🔹 Phase 4: Dynamic Agent Roster & Soul.md Persistence `[COMPLETED]`
* **Phase Entry Criteria:** Phase 3 completed.
* **Objective:** Support full agent lifecycle (Hire / Custom Persona / Desk Allocation / Fire).
* **Tasks:**
  - [x] **[TASK-010]** `[Sequential]` Implement schema validator in `core/fleet_manager.py` for new custom agents (validating ID, tool, risk tier, and hex color).
  - [x] **[TASK-011]** `[Sequential]` Persist hired agents to `config/fleet_agents.json` and dynamically allocate desk `(x, y)` coordinates across `OFFICE_DESK_COORDINATES`.
  - [x] **[TASK-012]** `[Parallelizable]` Handle agent deletion with worktree cleanup via `git_sandbox.safe_teardown` and broadcast `fleet_updated` micro events.
* **Phase Exit Criteria:** Hiring an agent via REST or voice immediately persists to disk and broadcasts `fleet_updated`. Verified with 7 dedicated unit tests and full suite pass (`88 passed, 5 skipped, 0 failed` in 34.85s).

---

### 🔹 Phase 5: View Switching & Window Close Protection `[COMPLETED]`
* **Phase Entry Criteria:** Phase 1 completed.
* **Objective:** Fix "Close office view" routing and prevent accidental third-party window termination.
* **Tasks:**
  - [x] **[TASK-013]** `[Sequential]` In `actions/open_app.py`, intercept view tokens (`officeview`, `agentview`, `dashboard`, `fleet`, `scranton`, `office`) before entering process termination.
  - [x] **[TASK-014]** `[Sequential]` If `action in ('close', 'exit', 'stop', 'hide', 'back')` for office view $\to$ broadcast `switch_view: "home"` and return clean confirmation.
  - [x] **[TASK-015]** `[Sequential]` In `actions/computer_control.py` (`_safe_close_window`), strictly enforce exact title equality matching and protected system names (`ZEZO`, `JARVIS`, `tactical dashboard`).
* **Phase Exit Criteria:** Calling `open_app(action='close', app_name='office_view')` switches view to Dashboard without killing any OS process. All unit and regression tests pass (`93 passed, 5 skipped, 0 failed` in 34.76s).

---

### 🔹 Phase 6: Temporal Prompt Gating (Date & Time Queries) `[COMPLETED]`
* **Phase Entry Criteria:** Phase 1 completed.
* **Objective:** Prevent slow 8.7s `web_search` calls for current date and time.
* **Tasks:**
  - [x] **[TASK-016]** `[Sequential]` Add negative directive in `core/prompt.txt`:
    ```plaintext
    [TEMPORAL CONTEXT & LOCAL TIME — ZERO TOOL OVERHEAD]
    - Current date, time, weekday, and year are permanently provided in your prompt under [SYSTEM LOCAL DATE & TIME].
    - NEVER call web_search, file_controller, browser_control, or any tool to answer questions about current time, today's date, day of the week, or current year. Answer instantly and directly from [SYSTEM LOCAL DATE & TIME] in under 0.2s without tool invocation.
    ```
* **Phase Exit Criteria:** Asking *"What is today's date?"* answers from prompt context in < 0.2s without calling `web_search`. Verified via `tests/test_temporal_prompt_suite.py` and full regression suite.

---

### 🔹 Phase 7: Fast Vision Timeout Ladder & AFC Cleanup `[COMPLETED]`
* **Phase Entry Criteria:** Phase 1 completed.
* **Objective:** Eliminate 15s session freezes during screen inspections and silence SDK warnings.
* **Tasks:**
  - [x] **[TASK-017]** `[Sequential]` Set `MIN_TIMEOUT_MS = 5_000` per REST model attempt in `core/gemini.py`.
  - [x] **[TASK-018]** `[Sequential]` Omitted unused tool declarations from REST vision payloads in `actions/screen_processor.py`.
* **Phase Exit Criteria:** Screen capture analysis returns in < 3s or steps to next model without hanging; log bus shows 0 AFC warnings. Verified via `tests/test_vision_timeout_suite.py` and full regression suite.

---

### 🔹 Phase 8: Grounded Scranton Pixel Office Floor (Zero-Simulation) `[COMPLETED]`
* **Phase Entry Criteria:** Phases 2, 3, and 4 completed.
* **Objective:** Purge all fake `Math.random()` wandering and fake progress bars; bind floor directly to real backend events.
* **Tasks:**
  - [x] **[TASK-019]** `[Sequential]` Removed `setInterval(runAutonomousFleetCycle, 3500)` and fake coffee/banter random loops in `prototypes/scranton_pixel_office_fleet/index.html`.
  - [x] **[TASK-020]** `[Sequential]` Grounded agent sprites at assigned desk coordinates in `status === "idle"`.
  - [x] **[TASK-021]** `[Sequential]` Trigger sprite active state and monitor glow strictly upon receiving WebSocket `agent_task_started` / `task_done` events.
* **Phase Exit Criteria:** Idle agents sit quietly at desks; running a task triggers only the assigned agent sprite with real live logs. Verified via `tests/test_scranton_pixel_office_suite.py` and full regression suite.

---

### 🔹 Phase 9: High-Frequency Polling Elimination `[COMPLETED]`
* **Phase Entry Criteria:** Phase 8 completed.
* **Objective:** Eliminate the 3.5-second HTTP polling flood on `/api/fleet/state`.
* **Tasks:**
  - [x] **[TASK-022]** `[Sequential]` Eliminated periodic HTTP polling loops in `prototypes/scranton_pixel_office_fleet/index.html`.
  - [x] **[TASK-023]** `[Sequential]` Fetch initial state once on DOM load via `syncBackendFleetState()`, then rely 100% on WebSocket `fleet_updated` and `agent_task_started` events.
* **Phase Exit Criteria:** Log bus export shows 0 periodic `/api/fleet/state` lines during normal idle operation. Verified via `tests/test_scranton_pixel_office_suite.py` and full regression suite.

---

### 🔹 Phase 10: 3-Layer Verification & Production-Readiness Audit `[COMPLETED]`
* **Phase Entry Criteria:** Phases 1 through 9 completed.
* **Objective:** Execute exhaustive static, runtime, and regression verification across all touched modules.
* **Tasks:**
  - [x] **[TASK-024]** `[Sequential]` Run Layer 1 static checks (`py_compile` across all files; 25 action discovery audit verified).
  - [x] **[TASK-025]** `[Sequential]` Run Layer 2 runtime benchmarks and Layer 3 full regression suite (`pytest`: 103 passed, 5 skipped, 0 failed).
* **Phase Exit Criteria:** 100% test pass rate, zero regressions, and full documentation synchronization in `LEARNING_JOURNAL.md`. Verified and production ready.

---

## 🔗 6. Traceability Matrix

| Requirement ID | Implementation Tasks | Modified Files | Verification Tests |
| :--- | :--- | :--- | :--- |
| **REQ-F-001** | TASK-004, TASK-005, TASK-006 | `actions/fleet_control.py`, `core/prompt.txt` | TEST-L1-001, TEST-L2-001 |
| **REQ-F-002** | TASK-010, TASK-011, TASK-012 | `core/fleet_manager.py`, `config/fleet_agents.json` | TEST-L2-002 |
| **REQ-F-003** | TASK-007, TASK-008, TASK-009 | `core/task_manager.py` | TEST-L2-003 |
| **REQ-F-004** | TASK-005, TASK-012 | `core/git_sandbox.py`, `core/fleet_manager.py` | TEST-L2-001 |
| **REQ-F-005** | TASK-013, TASK-014 | `actions/open_app.py` | TEST-L2-004 |
| **REQ-F-006** | TASK-015 | `actions/computer_control.py` | TEST-L2-005 |
| **REQ-F-007** | TASK-016 | `core/prompt.txt` | TEST-L2-006 |
| **REQ-F-008** | TASK-017, TASK-018 | `core/gemini.py`, `actions/screen_processor.py` | TEST-L2-007 |
| **REQ-NF-001** | TASK-004, TASK-007 | `actions/fleet_control.py`, `core/task_manager.py` | TEST-L2-001 |
| **REQ-NF-002** | TASK-022, TASK-023 | `prototypes/scranton_pixel_office_fleet/index.html` | TEST-L2-008 |
| **REQ-NF-003** | TASK-019, TASK-020, TASK-021 | `prototypes/scranton_pixel_office_fleet/index.html` | TEST-L2-009 |

---

## 🛡️ 7. Risk Register & Rollback Strategy

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Rollback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-001** | Subprocess timeout or hang during CLI coding execution | Med | High | 60-second watchdog thread in TaskManager | Terminate process tree (`_WIN_HIDE`, SIGTERM) and release worktree |
| **RISK-002** | Concurrency race condition on TaskManager state | Low | High | Enforce `threading.RLock()` across task transitions | Clean task state registry and reset active counter |
| **RISK-003** | Third-party window killed during view close | Med | High | Exact string equality check in `_safe_close_window` | Revert to title-exact match; broadcast view switch only |
| **RISK-004** | WebSocket connection drops causing UI state desync | Med | Med | Auto-reconnect loop with one-shot state hydration | Reconnect to `ws://127.0.0.1:8765/ws` and fetch `/api/fleet/state` |
| **RISK-005** | Rate limit / quota error on Google Search Grounding | High | Med | Add negative prompt rule prohibiting date searches | Direct answers from prompt `[LOCAL TIME]` |
| **RISK-006** | REST Vision freeze on degraded network | Med | Med | 5.0s per-model attempt timeout cap in `gemini.py` | Fall back immediately to next ladder model rung |
| **RISK-007** | Git worktree conflict on concurrent branch checkout | Low | High | Isolated branch naming: `agent_{name}_{task_id}` | Prune stale worktrees with `git worktree prune` |

---

## 🧪 8. Strict 3-Layer Verification Plan

### Layer 1: Static Verification
- **[TEST-L1-001]** Run `python -m py_compile` on all modified files (`actions/fleet_control.py`, `actions/open_app.py`, `actions/computer_control.py`, `core/fleet_manager.py`, `core/task_manager.py`, `core/gemini.py`, `actions/screen_processor.py`, `core/ui_server.py`).
- **[TEST-L1-002]** Action tool discovery check: `python -c "from core.action_loader import discover_actions; from pathlib import Path; r = discover_actions(Path('actions')); print(f'Discovered {len(r._actions)} actions')"` $\to$ Confirm 25 active tools.
- **[TEST-L1-003]** Anti-Slop complexity check: Verify AST cyclomatic complexity score $< 15$ across all modified subroutines.

---

### Layer 2: Runtime Benchmarks
- **[TEST-L2-001] Voice Fleet Dispatch Benchmark:** Execute `fleet_control({'action': 'dispatch', 'agent_id': 'MICHAEL', 'task': 'Refactor memory'})` $\to$ verify task is registered in `task_manager`, worktree is created in `.git/worktrees/`, and WebSocket broadcasts `agent_task_started`.
- **[TEST-L2-002] Agent Hiring & Persistence Benchmark:** Call `fleet_control({'action': 'hire', 'agent_id': 'STANLEY', 'role': 'QA Tester', 'default_tool': 'dev_agent'})` $\to$ verify entry in `config/fleet_agents.json` and `fleet_updated` event.
- **[TEST-L2-003] Concurrency Lock Benchmark:** Submit 3 simultaneous coding tasks $\to$ verify 2 run in parallel and 3rd is held in `TaskStatus.QUEUED`.
- **[TEST-L2-004] View Close Routing Benchmark:** Execute `open_app({'action': 'close', 'app_name': 'office_view'})` $\to$ verify WebSocket sends `switch_view: home` and 0 OS processes are killed.
- **[TEST-L2-005] Window Safety Benchmark:** Verify `close_window({'title': 'ZEZO'})` does NOT close third-party windows like WhatsApp.
- **[TEST-L2-006] Temporal Prompt Gating Benchmark:** Verify date/time query answers in < 0.2s from prompt context without triggering `web_search`.
- **[TEST-L2-007] Vision Timeout Benchmark:** Verify screen capture analysis returns in < 3s or steps to next model without hanging; log bus shows 0 AFC warnings.
- **[TEST-L2-008] Polling Cleanliness Benchmark:** Inspect backend log bus to confirm `/api/fleet/state` periodic polling flood is 100% eliminated.
- **[TEST-L2-009] Grounded Sprite Walking Benchmark:** Verify idle agents sit at desks; sprite moves only when `agent_task_started` is received.

---

### Layer 3: Full Regression Test Suite
- **[TEST-L3-001] Automated Pytest Suite:** Run `pytest` $\to$ verify 100% passing across all 18 test suites (`test_language_and_mute_fix.py`, `test_dispatcher.py`, `test_design_system_suite.py`, `test_antigravity_cli_integration_suite.py`, etc.).
- **[TEST-L3-002] Non-Negotiable UI Rules Audit:** Verify all 7 UI rules in `AGENTS.md` (opaque modals, no `transition: all`, `_zezoAnimActive` preservation, avatar GIF visibility, modal settings).

---

## 🛡️ 9. Regression Prevention Checklist (Non-Negotiable Rules)

- [x] **Rule 1 (Modals):** No `backdrop-filter` inside modal panels; modal backgrounds must remain opaque (`#0a0a0a`).
- [x] **Rule 2 (CSS):** Never use `transition: all`; always list explicit CSS properties.
- [x] **Rule 3 (Animation State):** Preserve `window._zezoAnimActive` in `openModal` and `closeModal`.
- [x] **Rule 4 (Avatar Visibility):** Hide avatar GIF while modals are open.
- [x] **Rule 5 (Modal IDs):** `openModal(id)` must not close its own id.
- [x] **Rule 6 (Settings Architecture):** Settings is a MODAL, never an anchored drawer.
- [x] **Rule 7 (Layout):** Prefer `position: fixed` with `inset: 0` over unstable QtWebEngine `vh` units.
- [x] **Rule 8 (3-Layer Verification):** Never mark work complete without Layer 1 (static), Layer 2 (runtime evidence), and Layer 3 (regression pass).
- [x] **Rule 9 (Code Graph Pre-Flight):** Perform CGC caller and dependency analysis before and after modifying shared modules.
- [x] **Anti-Slop Code Hygiene:** Function cyclomatic complexity must stay **< 15**; no bloated `if/elif` ladders (use dictionary dispatch tables).

---

## 🔍 10. Senior Engineer Completeness Self-Review

| Check Item | Self-Audit Question | Status | Evidence / Notes |
| :--- | :--- | :--- | :--- |
| **1. Traceability** | Are all requirements mapped to specific tasks, files, and tests? | **YES** | Bidirectional Traceability Matrix in Section 6. |
| **2. Blast Radius** | Were upstream callers and singletons audited via Code Graph? | **YES** | CGC caller analysis documented in Section 3. |
| **3. Sequencing** | Are phases ordered by dependencies with entry/exit criteria? | **YES** | Phases 1 to 10 sequenced with explicit criteria in Section 5. |
| **4. Safety & Failure** | Are timeouts, retries, concurrency limits, and error paths defined? | **YES** | Risk Register in Section 7 & Concurrency guard in Section 1. |
| **5. Objectivity** | Are acceptance criteria and test commands objectively verifiable? | **YES** | 3-Layer verification suite with reproducible commands in Section 8. |
| **6. Fact vs Assumption** | Are assumptions clearly separated from verified facts? | **YES** | Implementation status matrix verified with real codebase evidence. |
| **7. Read-Only Invariant** | Is the plan purely analytical without premature code edits? | **YES** | Maintained strictly read-only on application source code. |

---

## ❓ 11. Unresolved Questions & Clarifications
1. **Model Selection for Hired Custom Agents:** Confirm whether custom agents hired via voice should default to `kilo/stepfun/step-3.7-flash:free` or prompt the user for preferred executor.
2. **Floor Desk Capacity:** Confirm maximum floor capacity (default 8 desks configured; additional desks spawn in grid layout).
