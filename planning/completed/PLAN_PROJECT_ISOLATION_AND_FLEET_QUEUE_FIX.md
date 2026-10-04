# 🚀 Technical Implementation Plan: ZEZO Autonomous Agent Orchestrator & Project Isolation (Vision 1.0)

> **Lead Architect:** Hamza Bukhari  
> **Target Subsystems:** `core/`, `actions/`, `config/`, `frontend/`, `planning/`, `docs/`  
> **Status:** Pending Execution Approval  
> **Vision Document Grounding:** [`vision 1.0.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/vision%201.0.md)  
> **Traceability Index:** [REQ-V1-001..008, REQ-NF-001..003, CON-001..003, INV-001..003, TASK-001..012, RISK-001..004, TEST-L1-001..003, TEST-L2-001..004, TEST-L3-001..002]  

---

## 🎯 1. Requirements & System Invariants (Vision 1.0 Grounding)

### Core Paradigm: "ZEZO Manages the Work. Agents Execute the Work."
ZEZO functions as an intelligent orchestrator and project manager. Direct coding execution via standalone "ZEZO Coder" is deprecated; tasks are analyzed, scoped, and dispatched to specialized fleet agents (**Ali**, **Haider**, **Ahmad**, **Michael**) who execute using their configured tools.

### Functional Requirements (FR)
- **[REQ-V1-001] Semantic Target Directory Isolation:** Every independent project must have its own isolated workspace (e.g., `Desktop/hamza-portfolio/`, `Desktop/real-estate-landing-page/`, `Desktop/dental-landing-page/`). No project ever shares or overwrites another project's folder.
- **[REQ-V1-002] Collision-Safe Disambiguation (`get_unique_project_dir`):** If a target directory exists with content, generate a non-colliding suffixed folder (e.g. `Desktop/real-estate-landing-page_1`) unless the user explicitly requested edits to the existing repository.
- **[REQ-V1-003] Pre-Flight Project Clarification:** For substantial new projects (websites, web applications, full-stack apps), ZEZO must clarify missing requirements (tech stack, key pages, design style) with 1–2 concise questions before assigning the build, unless details were already provided.
- **[REQ-V1-004] Automatic Agent Capability Selection:** ZEZO automatically selects the most suitable agent based on configured responsibilities:
  - **Ali:** Frontend & UI Design Specialist (HTML/CSS, React, Tailwind, animations, landing pages).
  - **Haider:** Frontend Specialist (takes overflow when Ali is at capacity).
  - **Ahmad:** Backend & Full-Stack Specialist (FastAPI, PostgreSQL, schemas, microservices).
  - **Michael:** Manager & Multi-Task Workflow Decomposition.
- **[REQ-V1-005] Agent Concurrency & Overflow Load Balancing (Max 3 Tasks/Agent):** Each agent can handle up to **3 concurrent tasks**. If an agent is at capacity (3 active tasks), ZEZO automatically routes the new task to an available matching peer (e.g., Ali $\to$ Haider).
- **[REQ-V1-006] Single-Task Fleet Dispatch Contract (Zero Ghost Cards):** Fleet agent execution via `fleet_manager` must run within the dispatched task's lifecycle (`run_in_place=True`) without spawning a second disconnected `ZEZO CODER` task in `TaskManager`.
- **[REQ-V1-007] Clear Task Ownership & Informative UI Cards:** The Task Queue in `frontend/index.html` must clearly display the **Assigned Agent** (e.g., `ALI`, `HAIDER`, `AHMAD`) as the owner, display the project title (e.g., `"Hamza Bukhari Portfolio"`), show real-time progress (0% $\to$ 100%), and render clean relative target paths (`Target: Desktop/hamza-portfolio`).
- **[REQ-V1-008] Scoped Live Browser Preview:** Browser preview launches (`webbrowser.open`) must target the specific isolated project's `index.html` and never open an outdated or clobbered directory.

### Non-Functional Requirements (NFR)
- **[REQ-NF-001] Instant Turn Latency:** Agent selection and path resolution must complete in $< 50\text{ms}$ to ensure zero stutter in the Gemini Live voice loop.
- **[REQ-NF-002] True Progress Telemetry:** Tasks must stream real progress percentages (0% $\to$ 100%) rather than terminating prematurely at 82ms with a disconnected child task.
- **[REQ-NF-003] Safe Memory & Context Isolation:** Projects are decoupled from stale `last_active_repo` memory cache when starting new builds.

### Constraints & Invariants (CON / INV)
- **[CON-001] Non-blocking PyQt6 GUI Thread:** All file I/O, LLM generation, and CLI sub-agents must run in daemon worker threads managed by `core.task_manager`.
- **[CON-002] Anti-Slop Code Hygiene:** Maximum function cyclomatic complexity $< 15$, zero redundant boilerplate, zero echo comments, and dictionary dispatch for conditionals.
- **[INV-001] One File Per Action:** Action definitions in `actions/` remain self-describing, exporting `TOOL` schema and callable `handler`.
- **[INV-002] Modal & CSS Regressions Protected:** Preserve all rules from `AGENTS.md` (no `backdrop-filter` inside modals, no `transition: all`, preserve `_zezoAnimActive`).

---

## 🏛️ 2. Architecture & Technical Decisions

### End-to-End Orchestrator Workflow (Vision 1.0)
```
[User Request]
       │
       ▼
1. UNDERSTAND ────► Parse intent, extract entities & existing attachments
       │
       ▼
2. CLARIFY ───────► Ambiguous/broad new project? Ask 1-2 focused questions (stack/pages)
       │           (Skip if stack/details are already provided)
       ▼
3. PLAN ──────────► Determine deliverables & derive semantic project slug (e.g. 'hamza-portfolio')
       │
       ▼
4. SELECT AGENT ──► Inspect active agent task counts:
       │           - Frontend task: Ali active < 3 ? Assign ALI : Assign HAIDER
       │           - Backend task: Assign AHMAD
       │           - Multi-agent fullstack: Assign MICHAEL (decomposes to Ali + Ahmad)
       ▼
5. ALLOCATE DIR ──► get_unique_project_dir(slug) ──► Desktop/hamza-portfolio
       │
       ▼
6. ASSIGN & EXEC ─► fleet_manager.dispatch_task(agent_id, path=project_dir, run_in_place=True)
       │           - Runs worker in-place inside TaskManager
       │           - ZERO ghost ZEZO CODER cards spawned
       ▼
7. VERIFY & REPORT► Confirm index.html exists, launch preview, notify user of deliverables
```

### Key Technical Decisions & Justifications (ADR-066)
1. **Semantic Project Path Isolation:**
   - Add `get_unique_project_dir(topic_or_task, base_parent=None) -> Path` in `core/repo_context.py` that extracts a slug (e.g. `portfolio`, `real-estate`, `dental-landing`) and creates collision-safe folders (`Desktop/<slug>`, `Desktop/<slug>_1`).
2. **In-Place Fleet Worker Execution:**
   - Pass `run_in_place=True` and `task_ctx` from `fleet_manager._worker_fn` into `antigravity_action()`. The build executes synchronously inside the agent's task thread, streaming progress straight to the agent's card (`ALI: 0% -> 100%`).
3. **Agent Concurrency Tracking & Overflow Balancing:**
   - In `core/fleet_manager.py`, maintain active task tracking. Add helper `get_agent_active_task_count(agent_id)`. If an agent has 3 active running tasks, auto-route to an eligible peer (`HAIDER` for frontend).
4. **Registration of Haider in Fleet Roster:**
   - Add `HAIDER` to `config/fleet_agents.json` as Frontend Developer with avatar, desk location, and `antigravity_run` capability.
5. **System Prompt Alignment (`core/prompt.txt`):**
   - Replace directives telling ZEZO to use `antigravity_run` directly with instructions to dispatch through `fleet_control(action='dispatch', ...)` to appropriate specialist agents.

---

## 🔬 3. Code Graph (CGC) & Repository Pre-Flight Audit

### Dependency & Blast Radius Analysis
- `core.repo_context::resolve` & `get_unique_project_dir` (Called by `antigravity_agent.py`, `fleet_manager.py`).
- `actions.antigravity_agent::antigravity_action` (Called by `action_loader.py`, `fleet_manager.py`).
- `core.fleet_manager::FleetManager.dispatch_task` (Called by `actions/fleet_control.py`, `core/ui_server.py`).
- `frontend/index.html::renderTasks` (WebSocket-fed UI task queue).

### File Modification Matrix

| File Path | Action | Scope / Key Symbols Touched | Traceability |
| :--- | :--- | :--- | :--- |
| `core/repo_context.py` | Modify | `get_unique_project_dir()`, `extract_project_slug()`, decouple sticky cache | REQ-V1-001, REQ-V1-002 |
| `actions/antigravity_agent.py` | Modify | Accept `run_in_place`, call `get_unique_project_dir()`, prevent duplicate submit | REQ-V1-001, REQ-V1-006 |
| `core/fleet_manager.py` | Modify | Active task tracking (max 3/agent), overflow to Haider, pass `run_in_place=True` | REQ-V1-004, REQ-V1-005, REQ-V1-006 |
| `config/fleet_agents.json` | Modify | Register `HAIDER` with frontend capabilities and desk coordinates | REQ-V1-004 |
| `frontend/index.html` | Modify | `renderTasks()` to show Assigned Agent badge, project title, and clean relative target path | REQ-V1-007 |
| `core/prompt.txt` | Modify | Update coding delegation to prioritize fleet agents over direct tool calls | REQ-V1-003, REQ-V1-004 |
| `planning/decisions.md` | Modify | Document ADR-066 | INV-001 |
| `docs/TOOLS.md` | Modify | Synchronize tool descriptions for `antigravity_run` and `fleet_control` | INV-001 |

---

## 📋 4. Phased Implementation Roadmap & Master TODO List

```
Phase 1: Project Isolation & In-Place Execution (Immediate Foundation)
Phase 2: Fleet Agent Registration & Auto-Capability Routing
Phase 3: Agent Concurrency & Dynamic Overflow Balancing (Max 3 Tasks)
Phase 4: Prompt Architecture & Pre-Flight Clarification
Phase 5: 3-Layer Verification & Documentation Sync
```

### ✅ Master TODO List

#### 🔹 Phase 1: Workspace Folder Isolation & In-Place Execution
- [x] **[TASK-001]** Implement `extract_project_slug(prompt: str) -> str` in [`core/repo_context.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/repo_context.py).
- [x] **[TASK-002]** Implement `get_unique_project_dir(topic_or_task: str, base_parent: Optional[Path] = None) -> Path` in [`core/repo_context.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/repo_context.py) ensuring collision-safe incrementing (`Desktop/<slug>`, `Desktop/<slug>_1`).
- [x] **[TASK-003]** Decouple sticky `get_last_repo()` in `core/repo_context.py::resolve()` when a brand-new project build is explicitly initiated.
- [x] **[TASK-004]** Update [`actions/antigravity_agent.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/actions/antigravity_agent.py) to accept `run_in_place=True` / `task_ctx` and execute `_run_worker` directly without re-submitting to `TaskManager`.

#### 🔹 Phase 2: Fleet Agent Registration & Auto-Capability Routing
- [x] **[TASK-005]** Register `HAIDER` in [`config/fleet_agents.json`](file:///d:/anitgravity/zezo%20work/jarvis-57/config/fleet_agents.json) as a Frontend Developer (`role="Frontend Specialist"`, `default_tool="antigravity_run"`, desk coordinates adjacent to Ali).
- [x] **[TASK-006]** Enhance `resolve_agent_by_mention_or_capability()` in [`core/fleet_manager.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/fleet_manager.py) so that `fleet_control(action='dispatch')` without an explicit `agent_id` automatically routes to Ali or Ahmad.

#### 🔹 Phase 3: Agent Concurrency Limits & Load Balancing (Max 3 Tasks)
- [x] **[TASK-007]** Implement `get_agent_active_task_count(agent_id: str) -> int` in [`core/fleet_manager.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/fleet_manager.py) querying `TaskManager` for active running tasks.
- [x] **[TASK-008]** Implement overflow logic: if Ali has $\ge 3$ active tasks, auto-route incoming frontend tasks to Haider; if both are busy, queue or notify user.

#### 🔹 Phase 4: UI Task Queue Clarity & System Prompt Alignment
- [x] **[TASK-009]** Update `renderTasks()` in [`frontend/index.html`](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/index.html) to render the descriptive task title (`taskTitle`), assigned agent badge, and formatted clean relative target path (`Desktop/...`).
- [x] **[TASK-010]** Update [`core/prompt.txt`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/prompt.txt):
  - Instruct ZEZO to dispatch tasks to fleet agents (Ali for Frontend, Ahmad for Backend, Michael for Fullstack) rather than calling coding tools directly as ZEZO Coder.
  - Add the pre-flight clarification guard: ask 1–2 focused questions (stack/pages) for broad projects before dispatching.

#### 🔹 Phase 5: Verification, ADR-066 & Documentation Sync
- [x] **[TASK-011]** Append **ADR-066** to [`planning/decisions.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/planning/decisions.md) and synchronize [`docs/TOOLS.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/TOOLS.md).
- [x] **[TASK-012]** Execute 3-Layer verification suite (Static compile, runtime multi-directory dispatch test, regression test suite).

---

## 🔗 5. Traceability Matrix

| Requirement ID | Implementation Tasks | Touched Files | Verification Tests |
| :--- | :--- | :--- | :--- |
| **REQ-V1-001** | TASK-001, TASK-002, TASK-004 | `core/repo_context.py`, `actions/antigravity_agent.py` | TEST-L1-001, TEST-L2-001 |
| **REQ-V1-002** | TASK-002 | `core/repo_context.py` | TEST-L2-001 |
| **REQ-V1-003** | TASK-010 | `core/prompt.txt` | TEST-L2-003 |
| **REQ-V1-004** | TASK-005, TASK-006, TASK-010 | `config/fleet_agents.json`, `core/fleet_manager.py` | TEST-L2-002 |
| **REQ-V1-005** | TASK-007, TASK-008 | `core/fleet_manager.py` | TEST-L2-004 |
| **REQ-V1-006** | TASK-004 | `actions/antigravity_agent.py`, `core/fleet_manager.py` | TEST-L2-002 |
| **REQ-V1-007** | TASK-009 | `frontend/index.html` | TEST-L2-003, TEST-L3-002 |
| **REQ-V1-008** | TASK-004 | `actions/antigravity_agent.py` | TEST-L2-001 |

---

## 🛡️ 6. Risk Register & Rollback Strategy

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Rollback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-001** | Slug generator defaults to generic name on obscure prompt | Low | Low | Fallback to `Desktop/website_app` with incrementing counter | Revert to fallback default |
| **RISK-002** | Concurrency race during agent capacity check | Low | Med | Wrap active count check and submission in `threading.Lock` in `fleet_manager` | Task queued in TaskManager |
| **RISK-003** | `run_in_place=True` blocks calling thread | Low | High | Ensure caller is already inside a background worker thread | Submit async task if not in worker |
| **RISK-004** | User asks for stack change during clarification | Low | Low | Prompt captures tech stack and injects verbatim into agent task prompt | Default to single HTML |

---

## 🧪 7. Strict 3-Layer Verification Plan

### Layer 1: Static Verification
- **[TEST-L1-001]** Python compilation: `python -m py_compile core/repo_context.py actions/antigravity_agent.py core/fleet_manager.py`
- **[TEST-L1-002]** Action discovery audit: Verify all actions load with 0 collisions via `discover_actions()`.
- **[TEST-L1-003]** Anti-Slop complexity check: Verify cyclomatic complexity of all modified functions is $< 15$.

### Layer 2: Runtime Benchmarks
- **[TEST-L2-001]** Isolated Directory Generation: Simulate 3 requests ("portfolio", "real estate landing page", "dental clinic") and verify 3 distinct non-colliding folders created under `Desktop/`.
- **[TEST-L2-002]** Fleet Single Task Assertion: Dispatch Ali and verify TaskManager creates exactly 1 task (`ALI`) with 0 phantom `ZEZO CODER` tasks.
- **[TEST-L2-003]** UI Task Card Verification: Verify task card renders project name and clean relative target path.
- **[TEST-L2-004]** Concurrency Overflow: Submit 4 concurrent frontend tasks and assert 3 assigned to Ali, 1 automatically assigned to Haider.

### Layer 3: Regression Test Suite
- **[TEST-L3-001]** Core test suite regression pass: `pytest tests/test_tool_collision_and_governance_suite.py tests/test_actions.py`
- **[TEST-L3-002]** Non-negotiable UI rules check (Rules 1-9 in `AGENTS.md`).
