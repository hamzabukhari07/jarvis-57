# 📐 Technical Architecture Plan: Agent Engine Separation, Workspace Management & Dynamic Model Discovery

> **Feature Name:** Agent Engine Separation, Custom Workspace Path & Future-Proof Dynamic Model Discovery  
> **Status:** APPROVED / READY FOR IMPLEMENTATION  
> **Target Subsystems:** `frontend/office.html`, `core/ui_server.py`, `core/models.py`, `core/fleet_manager.py`, `core/prompt.txt`  
> **Author & Lead Architect:** Hamza Bukhari  
> **Creation Date:** 2026-10-05  

---

## 🔍 1. Issue Identification & Root Cause Analysis

During recent fleet delegation and testing, five critical architectural, conceptual, and UX defects were identified:

---

### Issue 1: Conceptual Confusion between "Engines" and "Tools" (Screenshot 3)
* **What's Happening:**
  * In the **Edit Agent Profile** and **Hire Agent** modals, the *Primary Engine* dropdown lists non-engine tools: `Extract Design System`, `Agent Reach (Social/Web)`, `Web Search`, and `Dev Agent`.
* **Root Cause:**
  * These are **Tools & Skills**, not autonomous CLI Engines.
* **Architectural Definition:**
  * **Engines** are strictly autonomous CLI developer agents:
    1. `OpenCode` (`opencode_run`) — Autonomous full-stack coding & CLI execution.
    2. `KiloCode` (`kilo_run`) — Multi-file refactoring and fast editing.
    3. `Antigravity` (`antigravity_run`) — Studio UI, frontend, and web synthesis.
    4. `Tool Specialist (No CLI)` (`none`) — Dedicated persona agents (like Kelly or Pam) that don't need a coding CLI and operate exclusively through tools/skills.
  * All other capabilities (`agent_reach`, `extract_design_system`, `web_search`, `file_processor`, `dev_agent`, etc.) belong strictly under the **Tools & Skills** multi-select grid.

---

### Issue 2: Missing Workspace / Folder Path Assignment (Screenshot 1)
* **What's Happening:**
  * When configuring or editing an agent profile (e.g., Ahmad, Haider, or any newly hired agent), there is no input field to assign, view, or inspect the agent's target working directory or project path.
* **Root Cause:**
  * The frontend modal lacks an input field (`cfgAgentWorktree` / `newAgentWorktree`), and the save handler does not persist the custom worktree path back to `config/fleet_agents.json`.
* **Impact:**
  * You cannot pin an agent to a specific folder (e.g., `D:/projects/my-api` or `Desktop/landing-page`).

---

### Issue 3: Incomplete & Static Model Selection List (Screenshot 1 & Future-Proofing)
* **What's Happening:**
  * The Model dropdown/datalist only shows a hardcoded subset of models (`gemini-3.7-flash`, `mimo-v2.5`, etc.) and misses the rest of ZEZO's supported models.
  * Furthermore, as CLI versions update and models change over time, hardcoded lists get stale and require manual code modifications.
* **Root Cause:**
  * The datalist in `frontend/office.html` was not synced with `core/models.py` (which defines Gemini 3.8/3.6, Claude Sonnet 4.6, Claude Opus 4.6 Thinking, GPT-OSS 120B, Groq LPU models, and Kilo free-tier models).
* **Future-Proof Solution:**
  * Expose `GET /api/models` from the backend to dynamically aggregate all verified model ladders from `core/models.py`.
  * Make the Model input in the UI an intelligent combobox: it auto-suggests verified models for the selected engine while allowing custom free-text typing so any brand-new model can be used immediately without code changes.

---

### Issue 4: Truncated Skills & Tools Roster (Screenshot 1)
* **What's Happening:**
  * The `ADD SKILLS & TOOLS` grid only presents 8 hardcoded checkboxes.
* **Root Cause:**
  * ZEZO has **30 active actions** and **15 declarative skills** discovered in the backend, but the frontend was using a tiny static array.
* **Impact:**
  * You cannot assign rich skills (like `hamza_taste`, `social_research`, `git_workflow`, `figma_helper`, `web_research_pipeline`, etc.) to agents.

---

### Issue 5: False-Positive "✓ DONE" Status & Direct Tool Bypass (Screenshot 2 & Log Bus)
* **What's Happening:**
  * In the Task Queue log:
    1. Kelly was dispatched a task: `"Extract the transcript for this video: https://..."`.
    2. However, the worker in `fleet_manager` did not pass `target: <url>` to `agent_reach`.
    3. `agent_reach` returned `"Please provide a target URL..."` in 0.1ms without doing any extraction.
    4. Despite this missing input/failure, `fleet_manager` unconditionally marked the task as **`100% Completed / ✓ DONE`**.
    5. Because Kelly failed, Gemini Live then bypassed Kelly and directly executed the raw tool `agent_reach(platform='youtube', target=...)`, which created a separate `SOCIAL RESEARCH` card instead of routing through Kelly.

---

## 💡 2. Proposed Architectural Blueprint

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FLEET AGENT ARCHITECTURE                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   1. PRIMARY ENGINE (CLI)               2. ASSIGNED WORKSPACE                          │
│      ├── OpenCode CLI                      └── Custom Folder Path: D:/projects/api     │
│      ├── KiloCode CLI                          [📂 Open in OS File Explorer]           │
│      ├── Antigravity CLI                                                               │
│      └── Tool Specialist (No CLI)       3. COMPLETE MODEL ROSTER                       │
│                                            ├── Live Discovery via /api/models          │
│                                            └── Free-Text Combobox (Zero Lockout)       │
│                                                                                        │
│   4. DYNAMIC SKILLS & TOOLS GRID                                                       │
│      ├── Filters: [ All ]  [ Tools (21) ]  [ Skills (11) ]  [ None ]                   │
│      └── Multi-select checkboxes for all 30 system tools and declarative skills        │
│                                                                                        │
│   5. STRICT ERROR DETECTION IN TASK QUEUE                                              │
│      ├── Parameter Forwarding: Automatically extract URLs/queries for tool agents      │
│      ├── Result Inspection: Check if tool returned Error/Missing Params                │
│      └── UI Accuracy: Show ✗ FAILED (red) on error instead of false ✓ DONE (green)      │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ 3. Architectural Decision Record (ADR)

### ADR-072: CLI Engine Separation, Dynamic Model Discovery & Robust Fleet Failure Handling

- **Context:**
  - Coding CLIs (OpenCode, Antigravity, KiloCode) frequently update their supported models and flags.
  - Hardcoding model lists in frontend templates causes context drift and user lockout.
  - Persona agents (like Kelly and Pam) are specialized tool users, not CLI developers.
- **Decision:**
  - **Single Source of Truth + Live Discovery:** `core/models.py` serves as the base source of truth, exposed via `/api/models` on `core/ui_server.py`.
  - **Dynamic Combobox Pattern:** The UI allows selecting from verified models while allowing free-text custom inputs for brand-new model releases.
  - **Strict Tool Outcome Validation:** Any tool output matching error signatures (`status: "error"`, `success: false`, `Error:...`, `Please provide...`) immediately triggers `task_failed`, marking the task as red `✗ FAILED` rather than green `✓ DONE`.
- **Alternatives Considered:**
  - *Hardcoding fixed select dropdowns:* Rejected due to high maintenance overhead and inability to use newly released CLI models without code changes.
  - *Treating all tools as engines:* Rejected because tools lack standalone REPL loops and autonomous file synthesis capabilities.

---

## 📋 4. Requirements & Invariants

### Functional Requirements (FR)
- `REQ-F-001`: Primary Engine dropdown in `office.html` MUST only list `OpenCode`, `KiloCode`, `Antigravity`, and `Tool Specialist (No CLI)`.
- `REQ-F-002`: Agent Edit & Hire modals MUST provide an `ASSIGNED WORKSPACE / FOLDER PATH` input field with persistent storage in `config/fleet_agents.json` and a button to open the folder in native OS Explorer.
- `REQ-F-003`: Backend MUST expose `GET /api/models` returning categorized model registries, and the frontend MUST dynamically filter models based on selected engine while supporting custom free-text entries.
- `REQ-F-004`: `ADD SKILLS & TOOLS` grid MUST display the full catalog of 30 system tools and 15 declarative skills with filter tabs (`All`, `Tools`, `Skills`, `None`).
- `REQ-F-005`: `core/fleet_manager.py` MUST parse URL/query targets from task prompts, validate tool return values, and broadcast `task_failed` on errors instead of `task_done`.
- `REQ-F-006`: `core/prompt.txt` MUST instruct Gemini Live to route research and video transcript tasks to `KELLY` via `fleet_control(action='dispatch', agent_id='KELLY', task=...)`.

### Non-Functional Requirements & Invariants (NFR)
- `INV-001`: Modals in `frontend/office.html` must remain opaque (`#0a0a0a`), adhering to AGENTS.md Rule 1.
- `INV-002`: Never use `transition: all` in CSS (AGENTS.md Rule 2).
- `INV-003`: No blocking operations on the WebSocket or UI server threads.
- `INV-004`: Cyclomatic complexity of all modified Python functions must stay $< 15$.

---

## 🔄 5. Data Contracts & Component Schemas

### A. Endpoint Contract: `GET /api/models`
```json
{
  "status": "success",
  "default_engine_models": {
    "opencode_run": [
      "opencode/mimo-v2.5-free",
      "opencode/qwen2.5-coder:free",
      "opencode/gemini-2.5-flash:free"
    ],
    "antigravity_run": [
      "gemini-3.7-flash-medium",
      "gemini-3.8-flash-medium",
      "gemini-3.6-flash-medium",
      "gemini-3.1-pro-high",
      "claude-sonnet-4-6",
      "claude-opus-4-6-thinking",
      "gpt-oss-120b-medium"
    ],
    "kilo_run": [
      "kilo/stepfun/step-3.7-flash:free",
      "kilo/deepseek/deepseek-chat:free",
      "kilo/qwen/qwen-2.5-coder-32b-instruct:free",
      "kilo/minimax/minimax-01:free"
    ],
    "groq": [
      "groq/llama-3.3-70b-versatile",
      "groq/deepseek-r1-distill-llama-70b",
      "groq/qwen-2.5-coder-32b"
    ]
  },
  "all_models": [ ... ]
}
```

### B. Agent Profile Save Payload: `POST /api/fleet/save_agent`
```json
{
  "id": "AHMAD",
  "name": "Ahmad",
  "role": "Full-Stack & Backend Specialist",
  "specialty": "FastAPI, PostgreSQL, microservices",
  "default_tool": "opencode_run",
  "risk_tier": "L2_DESTRUCTIVE",
  "model_id": "opencode/mimo-v2.5-free",
  "active_worktree": "D:/projects/my-api",
  "color": "#06b6d4",
  "allowed_tools": ["opencode_run", "code_helper", "file_processor", "file_controller", "dev_agent"],
  "allowed_skills": ["opencode", "multi_agent_collaboration", "make_plan", "git_workflow", "test_fastapi_deploy"],
  "prompt_prefix": "You are Ahmad..."
}
```

---

## 🛠️ 6. Phased Implementation Roadmap

### Phase 1: Backend API & Model Aggregation
- [ ] `TASK-001`: In `core/ui_server.py`, implement `_models_list_handler` (`GET /api/models`) aggregating models from `core/models.py`.
- [ ] `TASK-002`: In `core/fleet_manager.py`, update `save_agent_profile`, `_load_fleet`, and `_save_fleet` to persist `active_worktree`.

### Phase 2: Failure Detection & Parameter Forwarding
- [ ] `TASK-003`: In `core/fleet_manager.py` `dispatch_task`, automatically parse URLs/queries for tool calls and strictly inspect results for failure signatures, dispatching `task_failed` when errors occur.
- [ ] `TASK-004`: In `core/prompt.txt`, update `[AUTONOMOUS FLEET AGENTS & CAPABILITY DISPATCH]` with explicit routing rules for Kelly Kapoor and Pam Beesly.

### Phase 3: Frontend UI/UX Modernization
- [ ] `TASK-005`: In `frontend/office.html`:
  - Restrict Primary Engine dropdowns in `editAgentModal` and `createAgentModal` to CLI engines.
  - Add `ASSIGNED WORKSPACE / FOLDER PATH` input with OS File Explorer trigger.
  - Implement dynamic model fetching and engine-linked filtering from `/api/models`.
  - Expand `FLEET_SKILLS` to the complete 30 tools + 15 declarative skills catalog with category tabs.

---

## 🧪 7. Strict 3-Layer Verification Matrix

| Layer | Target / Component | Verification Command & Assertion |
| :--- | :--- | :--- |
| **Layer 1: Static** | `core/ui_server.py`, `core/fleet_manager.py`, `core/models.py` | `python -m py_compile core/ui_server.py core/fleet_manager.py core/models.py` (0 syntax errors). |
| **Layer 2: Runtime** | `GET /api/models` | Verify endpoint returns valid JSON with all CLI engine models. |
| **Layer 2: Runtime** | `POST /api/fleet/save_agent` | Save agent with custom `active_worktree`, verify persistence in `config/fleet_agents.json`. |
| **Layer 2: Runtime** | Error Handling in `fleet_manager` | Dispatch invalid URL task, verify card shows `✗ FAILED` and NOT `✓ DONE`. |
| **Layer 3: Regression** | Full Test Suite | `python -m pytest tests/ -v` (All 211 tests passing). |

---

## ⚠️ 8. Risk & Rollback Register

| Risk ID | Risk Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| `RISK-001` | Missing model ID prevents CLI launch | Low | Fallback ladder in `core/gemini.py` and default CLI fallbacks. |
| `RISK-002` | Custom worktree path does not exist on disk | Medium | Auto-create target directory with `mkdir(parents=True, exist_ok=True)` in `_fleet_open_folder_handler` and `fleet_manager`. |
| `RISK-003` | Non-JSON response from third-party CLI tool | Low | Safe string matching on return values before JSON parsing. |
