---
name: feature_planning
description: Senior-level technical architecture planning, dependency-ordered phased roadmap creation, requirement-to-test traceability, and blast-radius assessment for ZEZO / JARVIS features before code modification. Grounded in Code Graph analysis and strict 3-Layer verification requirements.
---

# 📐 Senior-Level Feature Planning & Technical Architecture Standard

This workflow skill converts an approved feature concept, architecture proposal, or major refactor into a **production-grade, repository-grounded Technical Implementation Plan**.

It enforces professional software engineering standards: evidence-based architecture, stable requirement traceability, end-to-end integration mapping, risk registers, and strict 3-Layer verification gates.

---

## 🎯 1. Trigger Conditions & Planning Scale

### When to Trigger
- An idea from `vision_suggestions` or an audit from `repo_opportunity_audit` is approved for development.
- The user requests: *"Plan the implementation of [feature]"*, *"Create a roadmap for [subsystem]"*, or *"Design the architecture for [capability]"*.
- A complex bug fix or multi-file refactoring requires architectural blast-radius assessment before writing code.
- Prior to executing `implementation` on any non-trivial feature.

### Proportional Planning Rigor (Engineering Judgment)
Scale the depth of planning to the complexity, risk, and blast radius of the change:
- **Small / Isolated Bug Fix:** Focused plan covering current bug, root cause, exact lines to edit, regression risk, and 3-Layer verification tests.
- **Moderate Single-Module Feature:** Standard plan covering requirements, schemas, task sequence, risk register, and test matrix.
- **Cross-Module / Subsystem Architectural Shift:** Full comprehensive plan covering ADRs, state transitions, concurrency, failure modes, data migrations, and end-to-end sequence flow.

---

## 🔄 2. Senior-Level Planning Workflow (9-Stage Protocol)

```
[ 1. REQUIREMENTS & INVARIANTS ] ──► Define FRs, NFRs, constraints, and assign stable IDs (REQ-XXX).
                │
[ 2. GRAPH & REPO AUDIT ]        ──► Query CGC Graph (callers, callees, complexity) & read ground-truth source.
                │
[ 3. ARCHITECTURE & ADR ]        ──► Document Current vs Proposed architecture; justify design decisions.
                │
[ 4. CONTRACT & STATE DESIGN ]   ──► Define TOOL schemas, data contracts, WebSocket events, and state machines.
                │
[ 5. E2E INTEGRATION & SAFETY ]  ──► Trace full execution path, error handling, timeouts, and concurrency guards.
                │
[ 6. PHASED ATOMIC ROADMAP ]     ──► Break into dependency-ordered phases and atomic tasks (TASK-XXX).
                │
[ 7. TRACEABILITY & VERIFY ]     ──► Map REQ -> TASK -> CODE -> TEST (3-Layer Verification).
                │
[ 8. RISK & ROLLBACK REGISTER ]  ──► Quantify likelihood/impact, mitigations, and rollback steps (RISK-XXX).
                │
[ 9. COMPLETENESS SELF-AUDIT ]   ──► Run senior engineer self-review checklist before finalizing plan.
```

---

## 🏛️ 3. Core Planning Principles & Standards

### A. Architecture & Technical Decision Records (ADRs)
- **Current vs Proposed State:** Contrast existing system behavior with intended architecture.
- **Decision Justification:** State why the chosen approach is necessary and evaluate 1-2 viable alternatives with trade-offs (latency, memory, complexity, maintainability).
- **ADR Recording:** For significant structural decisions, assign an ADR entry (e.g. `ADR-066`) matching repository conventions in `decisions.md`.
- **Architectural Conservatism:** Respect existing established patterns (action loader discovery, PyQt6 non-blocking GUI, SQLite FTS5 persistence, central log bus) unless a justified refactor is explicitly approved.

### B. Requirements & Stable ID Traceability
- Assign permanent, stable identifiers across all sections:
  - **Functional Requirements:** `REQ-F-001`, `REQ-F-002`, ...
  - **Non-Functional Requirements:** `REQ-NF-001` (Latency), `REQ-NF-002` (Concurrency), ...
  - **Constraints & Invariants:** `CON-001`, `INV-001`, ...
  - **Implementation Tasks:** `TASK-001`, `TASK-002`, ...
  - **Risks & Mitigations:** `RISK-001`, `RISK-002`, ...
  - **Verification Tests:** `TEST-L1-001` (Static), `TEST-L2-001` (Runtime), `TEST-L3-001` (Regression).
- Maintain bidirectional traceability so every requirement maps directly to code touchpoints, tasks, and test assertions.
- **Ambiguity Policy:** If requirements are underspecified or contradictory, highlight the exact ambiguity and request clarification rather than inventing behavior.

### C. Repository-Grounded Design
- **Pre-Flight Code Graph Query:** Use `code_graph_intelligence` to map every upstream caller and downstream dependency:
  ```powershell
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <symbol_name>
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb find name <symbol_name>
  ```
- **Ground-Truth Source Inspection:** Always read the active files (`view_file`) to verify parameter types, exceptions, and side effects. Line numbers serve as navigation aids, never as a substitute for reading the code.
- **State & Schema Contracts:** Document exact dictionary schemas, Pydantic models, SQLite DDL changes, and WebSocket JSON payloads.

### D. End-to-End System Integration & Failure Modes
- Map the end-to-end execution path:
  $$\text{User / Voice / UI} \to \text{Action Routing} \to \text{Engine / Sandbox} \to \text{TaskManager} \to \text{Event Broadcast} \to \text{UI State}$$
- Plan for operational edge cases at integration boundaries:
  - **Timeouts:** Bounded timeouts on REST, subprocesses, and network calls.
  - **Concurrency:** Concurrency limits (e.g. `MAX_CONCURRENT_CODING_TASKS = 2`) and race-condition guards.
  - **Cancellation:** Clean task cancellation and process tree termination (`_WIN_HIDE`, SIGTERM).
  - **Resource Cleanup:** Temporary worktree, file descriptor, and thread cleanup via `try/finally` or context managers.
  - **Error Routing:** Graceful voice summaries for users vs detailed tracebacks in `core.log_bus`.

### E. Production Readiness & Non-Functional Verification
- **Security & Permissions:** Enforce least privilege, Circuit Breaker risk tiers (`L0_READ_ONLY`, `L1_MUTATION`, `L2_DANGEROUS`), and API key masking in logs.
- **Performance & Latency:** Ensure Gemini Live voice loop dead-air remains $< 20\text{ms}$; heavy operations run in background daemon threads.
- **Platform Compatibility:** Enforce Windows subprocess hiding (`CREATE_NO_WINDOW`), path handling (`pathlib.Path`), and audio endpoint resolution.
- **Observability:** Centralize all backend logging to `core.log_bus` with ring buffer retention.

---

## 📋 4. Standard Deliverable Template: `planning/PLAN_<NAME>.md`

Generate technical plans adhering to this standardized structure:

```markdown
# 🚀 Technical Implementation Plan: [Feature Name]

> **Lead Architect:** Hamza Bukhari  
> **Target Subsystems:** [e.g. actions/, core/, memory/, ui/]  
> **Status:** Pending Execution Approval  
> **Traceability Index:** [REQ-F-001..N, TASK-001..N, RISK-001..N, TEST-001..N]  

---

## 🎯 1. Requirements & System Invariants

### Functional Requirements (FR)
- **[REQ-F-001]** [Description of functional capability]
- **[REQ-F-002]** [Description of functional capability]

### Non-Functional Requirements (NFR)
- **[REQ-NF-001]** **Latency:** [e.g. Instant voice acknowledgement < 20ms]
- **[REQ-NF-002]** **Concurrency:** [e.g. Max 2 concurrent tasks; excess queued]

### Constraints & Invariants (CON / INV)
- **[CON-001]** Non-blocking PyQt6 GUI thread (all subprocesses in TaskManager threads).
- **[INV-001]** One file per action in `actions/` exporting `TOOL` schema + handler.
- **[INV-002]** Anti-Slop complexity score < 15 per function.

### Explicit Exclusions (Out of Scope)
- [Explicit list of features or refactors deferred or excluded]

---

## 🏛️ 2. Architecture & Technical Decisions

### Current Architecture vs Proposed Architecture
[Mermaid diagram or structured ASCII sequence mapping state transitions and component flows]

### Key Technical Decisions & Justifications (ADR Summary)
1. **[Decision 1 Title]:**
   - **Chosen Approach:** [Summary]
   - **Justification:** [Why necessary]
   - **Alternatives Considered:** [Option B summary and why rejected]
   - **Trade-Offs:** [Latency vs Memory vs Complexity]

---

## 🔬 3. Code Graph (CGC) & Repository Pre-Flight Audit

### Dependency & Blast Radius Analysis
- **Upstream Callers:** [Symbols calling target components]
- **Downstream Consumers:** [Symbols called by target components]
- **Shared State / Singletons Touched:** [e.g. TaskManager, UI Server, SQLite DB]

### File Modification Matrix

| File Path | Action | Scope / Key Symbols Touched | Traceability |
| :--- | :--- | :--- | :--- |
| `actions/new_tool.py` | Create | `TOOL`, `handler` | REQ-F-001 |
| `core/engine.py` | Modify | `EngineClass.method()` | REQ-F-002 |
| `core/prompt.txt` | Modify | System prompt routing directives | REQ-F-001 |
| `docs/TOOLS.md` | Modify | Documentation sync | INV-001 |

---

## 🔌 4. Interface Contracts & Data Schemas

### Action Tool Schema Contract
```python
TOOL = {
    "name": "...",
    "description": "...",
    "parameters": { ... }
}
```

### WebSocket / Event Payloads
```json
{
  "event": "agent_task_started",
  "data": { ... }
}
```

---

## 📋 5. Phased Implementation Roadmap (Atomic Tasks)

### 🔹 Phase 1: [Foundation / Core Models]
* **Phase Entry Criteria:** [Prerequisites]
* **Phase Exit Criteria:** [Testable milestone]

#### Tasks:
- [ ] **[TASK-001]** `[Sequential]` [Task description]
  - **Files:** `core/module.py`
  - **Implementation Guidance:** [Key patterns to follow]
  - **Verification:** [Layer 1 & Layer 2 checks]
- [ ] **[TASK-002]** `[Parallelizable]` [Task description]

---

## 🔗 6. Traceability Matrix

| Requirement ID | Implementation Tasks | Modified Files | Verification Tests |
| :--- | :--- | :--- | :--- |
| **REQ-F-001** | TASK-001, TASK-002 | `actions/new_tool.py` | TEST-L1-001, TEST-L2-001 |
| **REQ-NF-001** | TASK-003 | `core/engine.py` | TEST-L2-002 |

---

## 🛡️ 7. Risk Register & Rollback Strategy

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Rollback Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-001** | Subprocess timeout on Windows | Med | High | Add 30s watchdog thread | Revert to fallback handler |
| **RISK-002** | Concurrency race on TaskManager | Low | High | Use threading.RLock | Kill task and release lock |

---

## 🧪 8. Strict 3-Layer Verification Plan

### Layer 1: Static Verification
- **[TEST-L1-001]** Python compilation: `python -m py_compile <touched_files>`
- **[TEST-L1-002]** Action discovery audit: `discover_actions()` confirms valid schema.
- **[TEST-L1-003]** Anti-Slop complexity check: AST cyclomatic complexity < 15.

### Layer 2: Runtime Benchmarks
- **[TEST-L2-001]** Real invocation: [Exact command and expected return structure].
- **[TEST-L2-002]** Timeout & failure handling: [Simulated error behavior].

### Layer 3: Regression Test Suite
- **[TEST-L3-001]** Full regression pass: `pytest tests/`
- **[TEST-L3-002]** Non-negotiable UI rules check (Rules 1-9 in `AGENTS.md`).

---

## ❓ 9. Unresolved Questions & Clarifications
- [Any open questions requiring user confirmation before execution]
```

---

## 🔍 5. Mandatory Senior Engineer Completeness Review

Before presenting any plan, perform this self-audit:

1. **Traceability:** Is every requirement mapped to a specific task, file, and test?
2. **Blast Radius:** Were upstream callers and shared singletons audited via Code Graph?
3. **Sequencing:** Are phases ordered by dependencies with clear entry and exit criteria?
4. **Safety & Failure:** Are timeouts, retries, concurrency limits, and error paths defined?
5. **Objectivity:** Are acceptance criteria and test commands objectively verifiable?
6. **Fact vs Assumption:** Are assumptions clearly flagged and separated from verified facts?
7. **Read-Only Invariant:** Is the plan purely analytical without premature source code modification?

If any answer is **NO**, refine the plan before submitting.
