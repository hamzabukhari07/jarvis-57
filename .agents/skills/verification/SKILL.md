---
name: verification
description: Multi-layer static, runtime, benchmark, and regression verification for ZEZO / JARVIS. Enforces strict 3-Layer verification protocol (AGENTS.md Rule 8), regression checklists, test execution, and Learning Journal documentation.
---

# 🧪 Verification & Quality Assurance Workflow

This workflow skill is activated to execute **3-Layer verification**, regression testing, and quality assurance on newly implemented code, bug fixes, or system modifications in **ZEZO / JARVIS**.

It operates in **strictly read-only mode** during verification-only requests, never claiming a test passed without real execution evidence.

---

## 🎯 When to Trigger

Activate this skill when:
- The user requests: *"Verify the changes"*, *"Run the tests"*, *"Check if [feature] works"*, or *"Audit the codebase for regressions"*.
- The `implementation` skill has completed a phase of development and requires verification before declaring completion.
- Debugging an issue to gather hard runtime evidence before formulating a fix.

---

## 🔬 Strict 3-Layer Verification Protocol (AGENTS.md Rule 8)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              STRICT 3-LAYER VERIFICATION                               │
├───────────────────────────────┬─────────────────────────────────┬───────────────────────┤
│ Layer 1: Static Verification  │ Layer 2: Runtime Benchmarks     │ Layer 3: Regression   │
│ • python -m py_compile        │ • Real Tool & Engine Execution  │ • Full Pytest Suite   │
│ • core/action_loader.py audit │ • Real Subprocess & Worktrees   │ • Live Audio Check    │
│ • AST Cyclomatic Complexity<15│ • Real API & WebSocket Response │ • Memory FTS5 Search  │
└───────────────────────────────┴─────────────────────────────────┴───────────────────────┘
```

---

## 🔄 Step-by-Step Verification Procedure

### 1. Scope & Change Assessment
- Identify all touched files and functions using `git diff --name-only` or file logs.
- Use `code_graph_intelligence` to map all callers and downstream consumers that could be impacted:
  ```powershell
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <modified_function>
  ```

### 2. Layer 1 — Static Verification
- Run Python byte-compilation on every touched file:
  ```powershell
  python -m py_compile <path_to_file>
  ```
- Verify dynamic action tool discovery:
  ```powershell
  python -c "from core.action_loader import discover_actions; from pathlib import Path; r = discover_actions(Path('actions')); print(f'Discovered {len(r.list_actions())} actions')"
  ```
- Check AST complexity compliance (< 15):
  ```powershell
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze complexity
  ```

### 3. Layer 2 — Runtime Evidence & Benchmarks
- Run real test invocations against the modified components.
- Capture actual stdout/stderr, returned JSON dictionaries, or HTTP/WebSocket response codes.
- **Strict Rule:** Never synthesize or fake test output. If a hardware device (e.g. microphone/speaker) is unavailable, state: *"UNVERIFIED: Requires physical microphone input on target hardware."*

### 4. Layer 3 — Regression Test Suite
- Run automated unit and integration tests:
  ```powershell
  pytest tests/
  ```
- Check regression invariants:
  - Memory FTS5 BM25 search remains functional (`memory/sqlite_memory.py`).
  - Desktop control and safe window close protection (`actions/computer_control.py`).
  - WebSocket broadcasts deliver to connected clients (`core/ui_server.py`).

### 5. Non-Negotiable UI & Architectural Regression Checklist
Verify all rules from `AGENTS.md` Section 6:
- [ ] **Rule 1:** No `backdrop-filter` inside modal panels; modal backgrounds must remain opaque (`#0a0a0a`).
- [ ] **Rule 2:** Never use `transition: all` in CSS rules.
- [ ] **Rule 3:** Preserve `window._zezoAnimActive` in `openModal` and `closeModal`.
- [ ] **Rule 4:** Hide avatar GIF (`vortex-gif`) while modals are open.
- [ ] **Rule 5:** `openModal(id)` must not close its own id.
- [ ] **Rule 6:** Settings is a MODAL (`#settings-modal`), not an anchored drawer.
- [ ] **Rule 7:** No unstable `vh` heights in QtWebEngine without resize fallbacks.

### 6. Learning Journal Documentation
Upon successful verification of all 3 layers, append a clean entry to `LEARNING_JOURNAL.md`:
```markdown
## [YYYY-MM-DD] — <Feature or Bugfix Name>
- What was built / fixed
- Why this approach was chosen
- What alternatives were considered
- Key files touched
- Verification evidence (Layer 1, Layer 2, Layer 3 passing logs)
- What to remember for future work
```

---

## 📋 Output Format: Verification Report

Present findings using this structured markdown format:

```markdown
# 🧪 Verification Report: [Feature / Target Subsystem]

### 1. Verification Scope
- **Files Touched:** [List of modified files]
- **Dependent Modules Checked:** [List from Code Graph analysis]

### 2. 3-Layer Verification Results

| Layer | Check / Benchmark | Command Executed | Result | Evidence Snippet |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1** | Python Syntax Compile | `python -m py_compile ...` | **PASSED** | Exit code 0 |
| **Layer 1** | Action Tool Discovery | `discover_actions()` | **PASSED** | 25 tools discovered |
| **Layer 2** | Runtime Execution | `python -m pytest tests/...` | **PASSED** | 4 passed in 0.8s |
| **Layer 3** | Full Regression Suite | `pytest tests/` | **PASSED** | All green |

### 3. Non-Negotiable Regression Checklist Status
- All applicable AGENTS.md rules checked and confirmed compliant.

### 4. Verdict & Status
- **Status:** `FIXED` (if all 3 layers passed with real evidence) OR `UNVERIFIED` (if runtime test could not be executed, with reason provided).
```

---

## 🛡️ Safety & Execution Boundaries

- **Verification-Only Requests Are Strictly Read-Only:** Do NOT edit source files to fix issues discovered during verification.
- **Reporting Gate:** If an unexpected failure or regression is uncovered, document the exact failing test output and await user authorization before attempting a fix.
