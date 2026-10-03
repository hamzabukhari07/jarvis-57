---
name: debug_diagnosis
description: Deep diagnostic root-cause investigation and failure analysis for ZEZO / JARVIS without mutating codebase. Gathers runtime evidence, traces code graph dependencies, isolates exact failure mechanisms, and delivers structured diagnosis reports.
---

# 🔍 Debugging & Root Cause Diagnosis Workflow

This workflow skill is activated to investigate bugs, unexpected crashes, test failures, UI discrepancies, and runtime exceptions across the **ZEZO / JARVIS** ecosystem.

It operates in **strictly read-only mode**: it isolates the exact root cause, maps dependency blast radius, and formulates a remediation plan **without editing or mutating any code files**.

---

## 🛡️ Non-Negotiable Safety Boundary

> [!IMPORTANT]
> **Zero Code Modifications During Diagnosis:**
> Under this skill, the agent MUST NOT edit, replace, or mutate application code, configuration files, or database entries.
> All investigations are purely diagnostic. Implementation of proposed fixes is deferred to the `implementation` skill upon explicit user authorization.

---

## 🎯 When to Trigger

Activate this skill when:
- The user reports a bug, unexpected behavior, or error (e.g. *"Why is this failing?"*, *"Diagnose this log error"*, *"Debug why 12 agents aren't showing"*, *"Check why WebSocket disconnected"*).
- A pytest suite or runtime verification produces failing assertions or unhandled exceptions.
- Investigating system spikes, memory leaks, concurrency locks, or audio stream drops.

---

## 🔄 5-Stage Root Cause Investigation Procedure

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DEBUGGING & DIAGNOSIS PIPELINE (READ-ONLY)                      │
├───────────────────┬───────────────────┬───────────────────┬────────────────────────────┤
│ 1. Symptom & Trace│ 2. Code Graph     │ 3. State & Source │ 4. Root Cause Proof        │
│    Extraction     │    Blast Radius   │    Inspection     │    & Remediation Strategy  │
│ • Log bus parsing │ • Callers/Callees │ • Line-by-line    │ • Mechanism explanation    │
│ • Stack traces    │ • Data flow trace │ • Config & schema │ • Zero-mutation proposal   │
└───────────────────┴───────────────────┴───────────────────┴────────────────────────────┘
```

### Stage 1: Symptom & Evidence Gathering
- Extract exact error messages, stack traces, HTTP/WebSocket status codes, and terminal output.
- Check the log bus (`core/log_bus.py`) and memory databases for recent telemetry:
  ```powershell
  # Search recent logs or test failures
  pytest tests/<target_test_suite>.py -v -s
  ```
- Correlate timestamps with system events (WebSocket connections, tool execution, session renewal).

### Stage 2: Mandatory Code Graph Pre-Flight
Per **AGENTS.md Rule 9**, query the Code Graph before diving into ad-hoc inspection:
1. Locate the failing symbol or exception origin:
   ```powershell
   $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb find name <symbol_or_function>
   ```
2. Trace all callers, callees, and data flow paths to understand the invocation blast radius:
   ```powershell
   $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <failing_function>
   ```
3. *Fallback:* If KùzuDB file lock is held by another process, immediately use `grep_search` and note the fallback in the diagnosis report.

### Stage 3: Source & State Inspection
- View the precise files and line numbers identified in Stages 1 & 2.
- Verify configuration constraints and schemas:
  - `config/api_keys.json`, `config/settings.json`, `config/fleet_agents.json`.
  - SQLite tables and column types (`memory/sqlite_memory.py`).
  - Signal-slot connections and WebSocket event handlers (`core/ui_server.py`, `frontend/`).
- Check for common anti-patterns:
  - Blocking calls inside async loops or PyQt6 GUI thread.
  - Race conditions in multi-threaded background tasks.
  - Type coercion errors (e.g. string vs int ports/coordinates).
  - Unhandled `None` returns or missing dict keys.

### Stage 4: Root Cause Isolation & Proof
- Distinguish between **symptoms** (e.g. UI renders default values) and the **root cause** (e.g. API endpoint returned 500 because of an uncaught key error).
- Formulate a clear, reproducible proof explaining why the error occurs under specific inputs or states.

### Stage 5: Remediation Strategy & Proposal
- Formulate the simplest, most minimal, and anti-slop fix adhering to `.agents/skills/antislop_code/SKILL.md`.
- Estimate blast radius: which files will need changes, and which test suites must verify the fix.
- Output the formal **Diagnosis Report** and ask for user approval to proceed with implementation.

---

## 📋 Standard Diagnosis Report Format

When reporting findings, structure the response cleanly as follows:

```markdown
### 🔍 Diagnosis Report: <Issue Summary>

#### 1. Symptom & Failure Manifestation
- **Observed Behavior:** <What actually happened>
- **Expected Behavior:** <What should have happened>
- **Error / Log Snippet:** <Exact stack trace or log line>

#### 2. Call Graph & Blast Radius
- **Component(s) Affected:** `<file_path>:<function>`
- **Upstream Callers:** `<caller_functions>`
- **Downstream Impact:** `<consumers_or_ui_elements>`

#### 3. Root Cause Analysis
- **Exact Location:** `[filename.py:L123](file:///path/to/filename.py#L123)`
- **Mechanism:** <Step-by-step explanation of why the defect occurs>
- **Contributing Factors:** <Schema mismatches, unhandled async states, etc.>

#### 4. Recommended Remediation Plan
- **Proposed Fix:** <Concise explanation of the minimal fix>
- **Files to Modify:** `<list_of_files>`
- **Verification Strategy:** <Pytest suites & Layer 1-3 verification steps>

> [!NOTE]
> No code modifications have been applied. Awaiting your approval to implement this fix.
```
