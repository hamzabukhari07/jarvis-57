# 🚀 Technical Implementation Plan: Scranton Office Fleet Desks, Model Picker, Dev Agent Deprecation & Quick Snippet Rename

> **Lead Architect:** Hamza Bukhari  
> **Target Subsystems:** `actions/dev_agent.py`, `actions/quick_snippet.py` (renamed from `code_helper.py`), `frontend/office.html`, `core/fleet_manager.py`, `core/ui_server.py`, `config/fleet_agents.json`, `tests/`  
> **Status:** Approved for Implementation  
> **Traceability Index:** [REQ-F-001..007, TASK-001..010, RISK-001..003, TEST-L1-001..TEST-L3-002]  

---

## 🎯 1. Requirements & System Invariants

### Architectural Decisions (ADR Summary)
- **`dev_agent` Deprecation & Complete Removal:** The legacy read-only `actions/dev_agent.py` tool is completely removed from the codebase. Multi-file coding and refactoring are handled exclusively by CLI engines (`OpenCode`, `KiloCode`, `Antigravity`).
- **`code_helper` Renamed to `quick_snippet`:** Renamed to `actions/quick_snippet.py` (`quick_snippet` tool) as a lightweight, non-CLI fast tool (1-second single-file code/command generation for voice loop).
- **Primary Engine Selection:** Agents in Scranton Office can be configured with `opencode_run`, `kilo_run`, `antigravity_run`, or `none` (Tool Specialist / No CLI).

### Functional Requirements (FR)
- **[REQ-F-001] Spatial Desk Allocation & Conflict Prevention (Screenshot 1):** When a new agent (e.g. `AGENT` or `HAIDER`) is added, they must be assigned a unique unoccupied workstation on the floor canvas instead of colliding onto Haider / Ali's desk (`deskX: 38, deskY: 55`).
- **[REQ-F-002] Workstation DOM Completeness (Screenshot 2):** Every agent (including Ahmad at `deskX: 62, deskY: 55` or designated annex room) must have a visible pixel desk (`.desk`), monitor, keyboard, and chair rendered under their assigned coordinates.
- **[REQ-F-003] Dynamic Display Name Synchronization (Screenshot 3):** Agent display name modifications (e.g. changing "Agent" to a custom persona name) must immediately update the Inspector title (`#activeAgentName`), bottom Roster cards, and agent sprite tags without falling back to raw uppercase IDs.
- **[REQ-F-004] Activity Terminal Log Type Sanitization (Screenshot 3):** Activity panel must support both raw string logs (`[SYSTEM] ...`) and structured log objects (`{ timeStr, agentName, text, type }`), completely eliminating `undefined [undefined] undefined` rendering.
- **[REQ-F-005] Clean Primary Engine Dropdown (Screenshot 4):**
  - Dropdown `#cfgAgentToolDropdown` strictly presents:
    1. `opencode_run` — "OpenCode (Autonomous Multi-File Agent)"
    2. `kilo_run` — "KiloCode (Refactoring & Fast Editing Agent)"
    3. `antigravity_run` — "Antigravity (UI & Synthesis Agent)"
    4. `none` — "Tool Specialist (No CLI Engine)"
  - Default fallback in backend is `opencode_run`.
- **[REQ-F-006] Custom Searchable Model Dropdown for QtWebEngine (Screenshot 5):**
  - Replace native HTML5 `<input list="modelIdPresets">` and `<datalist>` with a standardized `.custom-dropdown` searchable menu populated dynamically from `/api/models` for 100% reliable rendering and interaction in `QtWebEngine`.
- **[REQ-F-007] Tool Renaming (`code_helper` -> `quick_snippet`):**
  - Rename `actions/code_helper.py` to `actions/quick_snippet.py` and tool ID to `quick_snippet`. Update `core/prompt.txt`, `core/fleet_manager.py`, and test references.

### Non-Functional Requirements (NFR)
- **[REQ-NF-001] 60 FPS Canvas & DOM Smoothness:** Zero DOM thrashing; all agent movements use A* pathfinding and lightweight CSS transforms.
- **[REQ-NF-002] Zero Regression Guarantee:** All existing 211 pytest test suites must pass 100%.

### Constraints & Invariants (CON / INV)
- **[CON-001]** No `backdrop-filter` inside modals (AGENTS.md Rule 1).
- **[CON-002]** Never use `transition: all` (AGENTS.md Rule 2).
- **[INV-001]** Anti-Slop cyclomatic complexity < 15 per function.

---

## 🏛️ 2. Architecture & Technical Decisions

### Current Architecture vs Proposed Architecture

```
CURRENT (Legacy / Buggy):
[Tool Hierarchy]  ──► dev_agent (duplicate/obsolete) & code_helper (confusing name) & CLI engines
[New Agent Added] ──► Not in DESK_PRESETS ──► Falls back to SPAWN_DESKS[0] (38, 55) ──► Overlaps Haider's Desk!
[Agent Name Edit] ──► Stored in ag.displayName ──► UI renders ag.name (Upper ID) ──► Stale Name Shown!
[Activity Logs]   ──► Array of Strings ['...'] ──► Accesses l.timeStr, l.text ──► 'undefined [undefined] undefined'!
[Model Dropdown]  ──► Native HTML5 <datalist> ──► Clipped / Unstyled in QtWebEngine ──► Dropdown Won't Open!

PROPOSED (Clean & Dynamic):
[Tool Hierarchy]  ──► Pure CLI Engines (OpenCode, KiloCode, Antigravity) + quick_snippet (Fast inline)
[New Agent Added] ──► Dynamic Slot Allocator (finds nearest unassigned desk) ──► Unique Workspace!
[Agent Name Edit] ──► UI renders ag.displayName || ag.name everywhere ──► Immediate Live Name Update!
[Activity Logs]   ──► Normalized parser handles (typeof l === 'string') & objects ──► Clean Formatted Logs!
[Model Dropdown]  ──► Custom Searchable .custom-dropdown attached to /api/models ──► Full Model List Visible!
```

---

## 🔬 3. Code Graph (CGC) & Repository Blast Radius

- **Components Touched:**
  - `actions/dev_agent.py`: Deleted.
  - `actions/code_helper.py` -> `actions/quick_snippet.py`: Renamed.
  - `core/prompt.txt`: Updated tool references.
  - `config/fleet_agents.json`: Update agent tools to `opencode_run` and sync desk presets.
  - `core/fleet_manager.py`: Remove `dev_agent`, rename `code_helper` -> `quick_snippet` in `VALID_TOOLS`, default to `opencode_run`.
  - `frontend/office.html`: Desks markup, `DESK_PRESETS`, `syncBackendState()`, `selectAgent()`, `renderSelectedAgentLogs()`, `openEditAgentModal()`, `#cfgAgentToolDropdown`, `#cfgAgentModelDropdown`.
  - `tests/`: Update any tests asserting `dev_agent` or `code_helper` imports.

### File Modification Matrix

| File Path | Action | Scope / Key Symbols Touched | Traceability |
| :--- | :--- | :--- | :--- |
| `actions/dev_agent.py` | Delete | Deprecated tool file deletion | REQ-F-005 |
| `actions/code_helper.py` -> `actions/quick_snippet.py` | Rename/Modify | Tool rename `code_helper` -> `quick_snippet` | REQ-F-007 |
| `core/prompt.txt` | Modify | Update tool list & routing instructions | REQ-F-007 |
| `config/fleet_agents.json` | Modify | Remove `dev_agent` references, set `AGENT` default tool to `opencode_run` | REQ-F-005 |
| `core/fleet_manager.py` | Modify | `VALID_TOOLS`, default tool fallback, `_allocate_desk()` | REQ-F-001, REQ-F-005, REQ-F-007 |
| `frontend/office.html` | Modify | Desks markup, `DESK_PRESETS`, `selectAgent`, `renderSelectedAgentLogs`, Custom Model Dropdown | REQ-F-001..006 |
| `tests/*` | Modify | Update tests importing `actions.dev_agent` or `actions.code_helper` | REQ-NF-002 |

---

## 📋 4. Phased Implementation Roadmap (Atomic Tasks)

### 🔹 Phase 1: Deprecate `dev_agent`, Rename `code_helper` -> `quick_snippet` & Clean Engine Schemas
- [ ] **[TASK-001]** Delete `actions/dev_agent.py`.
- [ ] **[TASK-002]** Rename `actions/code_helper.py` to `actions/quick_snippet.py` (TOOL dict & handler name -> `quick_snippet`).
- [ ] **[TASK-003]** Update `core/prompt.txt` to replace `code_helper` with `quick_snippet` and remove `dev_agent`.
- [ ] **[TASK-004]** Update `config/fleet_agents.json` and `core/fleet_manager.py` (`VALID_TOOLS` and default fallback `opencode_run`).
- [ ] **[TASK-005]** Update unit tests in `tests/` for clean imports.

### 🔹 Phase 2: Spatial Grid Calibration & Desk Conflict Resolution (Fixes Issues 1 & 2)
- [ ] **[TASK-006]** Expand `DESK_PRESETS` and dynamic desk pool in `frontend/office.html` with distinct coordinates for all agents (`MICHAEL`, `ALI`, `HAIDER`, `AHMAD`, `DWIGHT`, `JIM`, `PAM`, `OSCAR`, `STANLEY`, `RYAN`, `KELLY`, `ANDY`, and custom `AGENT_X`).
- [ ] **[TASK-007]** Add corresponding `.desk` DOM elements for Ahmad and unassigned workstations on the office floor so no agent stands in an empty area without a desk.

### 🔹 Phase 3: Dynamic Name Binding & Activity Log Sanitization (Fixes Issue 3)
- [ ] **[TASK-008]** Update `selectAgent()` and `renderRoster()` in `frontend/office.html` to bind `ag.displayName || ag.name` to the Inspector header `#activeAgentName` and Roster cards.
- [ ] **[TASK-009]** Refactor `renderSelectedAgentLogs()` in `frontend/office.html` to normalize string logs and object logs, eliminating `undefined [undefined] undefined`.

### 🔹 Phase 4: Primary Engine Dropdown & Custom Searchable Model Dropdown (Fixes Issues 4 & 5)
- [ ] **[TASK-010]** Update `#cfgAgentToolDropdown` in `frontend/office.html` to offer clean CLI engines (`opencode_run`, `kilo_run`, `antigravity_run`) and `none`.
- [ ] **[TASK-011]** Replace `<input list="modelIdPresets">` with a custom searchable `.custom-dropdown` in `frontend/office.html` linked to `/api/models` so users can search, scroll, and select all available models in `QtWebEngine`.

---

## 🔗 5. Traceability Matrix

| Requirement ID | Tasks | Modified Files | Verification Checks |
| :--- | :--- | :--- | :--- |
| **REQ-F-001** | TASK-006 | `frontend/office.html`, `config/fleet_agents.json` | TEST-L2-001 |
| **REQ-F-002** | TASK-007 | `frontend/office.html` | TEST-L2-001 |
| **REQ-F-003** | TASK-008 | `frontend/office.html`, `core/fleet_manager.py` | TEST-L2-002 |
| **REQ-F-004** | TASK-009 | `frontend/office.html` | TEST-L2-002 |
| **REQ-F-005** | TASK-001, TASK-004, TASK-010 | `actions/dev_agent.py`, `core/fleet_manager.py`, `frontend/office.html` | TEST-L1-001, TEST-L2-003 |
| **REQ-F-006** | TASK-011 | `frontend/office.html` | TEST-L2-003 |
| **REQ-F-007** | TASK-002, TASK-003, TASK-004, TASK-005 | `actions/quick_snippet.py`, `core/prompt.txt`, `core/fleet_manager.py`, `tests/` | TEST-L1-001 |

---

## 🛡️ 6. Risk Register & Rollback Strategy

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Rollback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-001** | A* Pathfinding collision with new desks | Low | Med | Verify `pointBlocked()` bounding boxes for all desks | Revert new desk coordinates |
| **RISK-002** | Custom dropdown menu clipping in modal | Low | Low | Set `z-index: 100` and `max-height: 180px` with `overflow-y: auto` | Adjust dropdown positioning |
| **RISK-003** | Test breakage after `dev_agent` deletion & rename | Low | Med | Grep all tests for `dev_agent` & `code_helper` and update imports | Restore mocks in tests |

---

## 🧪 7. Strict 3-Layer Verification Plan

### Layer 1: Static Verification
- **[TEST-L1-001]** Python compilation: `python -m py_compile core/fleet_manager.py core/ui_server.py actions/quick_snippet.py`
- **[TEST-L1-002]** Anti-Slop complexity check: all JS/Python functions < 15 complexity.

### Layer 2: Runtime Benchmarks
- **[TEST-L2-001]** Office Desk Verification: Confirm all agents occupy distinct desks without overlaps and Ahmad has a desk rendered.
- **[TEST-L2-002]** Edit Name & Activity Test: Change agent name, verify live update in Inspector & Roster, verify activity logs contain timestamps and messages (no `undefined`).
- **[TEST-L2-003]** Engine & Model Picker Test: Open Edit Agent Modal, confirm engine dropdown lists clean CLI tools and Model Dropdown expands smoothly with all active models.

### Layer 3: Regression Test Suite
- **[TEST-L3-001]** Full regression test suite pass: `pytest -q` (all 211+ tests passing).
- **[TEST-L3-002]** Non-negotiable UI rules check (Rules 1-9 in `AGENTS.md`).
