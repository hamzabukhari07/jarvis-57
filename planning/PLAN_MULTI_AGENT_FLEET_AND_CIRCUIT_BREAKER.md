# 🚀 Architecture & Implementation Plan: Autonomous Multi-Agent Fleet Harness, Circuit Breakers & Memory Palace (v2 — Hardened Production Edition)

> **Project:** ZEZO OS v2 (Autonomous Desktop AI Operating System)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Architectural Pre-requisite / Foundation Invariant:**  
> ⚠️ **The Fleet Harness is a Layer-1 Abstraction. It strictly depends on and requires the completion of Layer-0 Foundational Reliability (`PLAN_VOICE_LATENCY_AND_DESKTOP_STABILITY.md`), including Live-session keepalive, 2KB payload shield, Action Ledger TTL, per-window HWND focus locking, and process tree termination.**  
> **Target Objectives:** Zero Data-Loss Worktree Sandboxing | Risk-Tiered Circuit Breakers | Immutable Provenance Memory Palace | Phonetic STT Guard | Non-Activating Stapler Dictation | Real-time Cost Telemetry  
> **Date:** October 2026  

---

## 🎯 Executive Summary & Objectives

This hardened production blueprint upgrades **ZEZO OS v2** from a single-agent desktop voice assistant into an enterprise-grade **Autonomous Multi-Agent Fleet Harness** while addressing four core safety invariants:

1. **Zero Data-Loss Git Worktree Sandboxing:**
   - Spawns background coding agents (`opencode_agent`, `kilo_agent`) in `.git/worktrees/{task_id}`.
   - **Non-Destructive Teardown:** Never blindly executes `git clean -fdx` or force-deletes locked directories. Inspects running process handles, stashes uncommitted/untracked diffs to a quarantine recovery branch, and safely archives uncertain states.
2. **Named Agent Personas & Scranton Pixel Office Fleet Deck:**
   - Supports fully customizable named subagents (`MICHAEL`, `DWIGHT`, `JIM`, `PAM`, `OSCAR`, etc. or user-defined technical roles) with individual personas, system prompts, git worktrees, and visual pixel aesthetics.
   - Real-time bilateral bridge between the backend task orchestrator and the Scranton Pixel Office command deck (`prototypes/scranton_pixel_office_fleet/index.html`): live walking state, desk focus, monitor glow, and on-demand agent activity inspection.
   - Direct voice agent targeting (e.g. *"Michael, summarize sprint"* / *"Dwight, run security audit"*).
3. **Risk-Aware Tiered Circuit Breaker (`L0 Read-Only → L1 Low-Risk → L2 Destructive`):**
   - Implements strict category-specific permission recovery. Three successful read-only actions **never** restore permissions for destructive mutating operations without explicit human authorization.
4. **Immutable Provenance & Conflict-Aware Memory Palace:**
   - Preserves explicit user directives in an immutable table with full timestamps and source references.
   - Automatically detects semantic preference contradictions, generates conflict resolution graphs, and prompts the user for clarification rather than allowing AI summaries to silently overwrite permanent baselines.
5. **Foundational Reliability Layer Anchoring (Layer 0 $\to$ Layer 1):**
   - Firmly binds fleet orchestration to the Live WebSocket isolation, Action Ledger TTL, duplicate tool response filters, and foreground window identity verification established in `PLAN_VOICE_LATENCY_AND_DESKTOP_STABILITY.md`.
6. **Phonetic & Technical STT Vocabulary Guard:**
   - Normalizes 150+ developer terms (`pywinauto`, `PyQt6`, `dxcam`, `Groq`, `UIA`) and Roman Urdu code-switching tokens within a context-aware programming/OS filter.
7. **Non-Focus-Stealing Desktop "Stapler" Companion:**
   - Global hotkey (`Ctrl+Alt+Space`) overlay using Win32 `WS_EX_NOACTIVATE` and pre-hotkey HWND caching to capture voice instructions + focused target window crops with zero z-order disruption.
8. **Real-time Cost, Token & Latency Telemetry HUD:**
   - 150ms debounced telemetry aggregator rendering live latency, token consumption, and cost estimates on the PyQt6 HUD.

---

## 🏗️ Architectural Flow: Tiered Multi-Agent Fleet & Safety Harness

```
                         ┌──────────────────────────────────────────────┐
                         │   Gemini Live / Groq Voice Orchestrator      │
                         │             (ZEZO Master Brain)              │
                         └──────────────────────┬───────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 │                                                             │
                 ▼                                                             ▼
  ┌───────────────────────────────┐                             ┌───────────────────────────────┐
  │  Phonetic Vocabulary Guard    │                             │  Non-Activating "Stapler"     │
  │ • Context-Aware Token Filter  │                             │ • Pre-hotkey HWND Cache       │
  │ • Roman Urdu Code-Switching   │                             │ • WS_EX_NOACTIVATE Overlay    │
  └──────────────┬────────────────┘                             └──────────────┬────────────────┘
                 │                                                             │
                 └──────────────────────────────┬──────────────────────────────┘
                                                │
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   Action Ledger & Fleet Task Dispatcher      │
                         │  (Layer 0 Foundation: HWND Lock & 2KB Cap)   │
                         └──────────────────────┬───────────────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
  ┌─────────────────────────────┐┌─────────────────────────────┐┌─────────────────────────────┐
  │  Risk-Aware Circuit Breaker ││  Safe Worktree Sandbox      ││  Immutable Memory Palace    │
  │ • L0: Read-Only (DevAgent)  ││ • Process Handle Latch      ││ • Immutable User Rules      │
  │ • L1: Low-Risk Mutation     ││ • Quarantine Stash Branch   ││ • Conflict Resolution Graph │
  │ • L2: Human Gate Required   ││ • Zero Unchecked Pruning    ││ • Full Source Provenance    │
  └─────────────────────────────┘└──────────────┬──────────────┘└─────────────────────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │ Scranton Pixel Fleet Deck   │
                                 │ • 12 Named Agent Personas   │
                                 │ • Live Worktree & File Sync │
                                 │ • A* Movement & Inspector   │
                                 └─────────────────────────────┘
```

---

## 🔍 Capability & Enhancement Mapping Matrix

| Capability Area | Current ZEZO State | Hardened Fleet State | Key File Locations |
| :--- | :--- | :--- | :--- |
| **Named Fleet Personas & Office Deck** | Single assistant identity; generic task workers | **Customizable Multi-Agent Fleet System** with named personas, custom roles/prompts, and bidirectional Scranton Pixel Office sync (`12 Agents + Inspector`). | `config/fleet_agents.json`, `core/fleet_manager.py`, `prototypes/scranton_pixel_office_fleet/index.html`, `ui.py` |
| **Safety & Error Loops** | 10s timeout envelope; binary exception returns | **Risk-Tiered Circuit Breaker** (`L0 Read-Only`, `L1 Low-Risk`, `L2 Destructive`) with explicit human gate for destructive recovery. | `core/circuit_breaker.py`, `core/task_manager.py`, `actions/opencode_agent.py` |
| **Concurrent Coding** | Direct edits inside active repository root; potential file lock / branch collisions | **Zero-Loss Git Worktrees** with quarantine recovery branches, process handle inspection, and single-committer merge locks. | `core/git_sandbox.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py` |
| **Long-Term Memory** | SQLite FTS5 table grows unbounded; raw transcripts queried via BM25 | **Immutable Memory Palace** with conflict detection graphs, source timestamps, and permanent rule preservation. | `memory/memory_condenser.py`, `memory/sqlite_memory.py`, `memory/memory_manager.py` |
| **Voice STT Accuracy** | Raw transcript tokens routed directly; occasional dev term misinterpretation | **Context-Aware Vocabulary Guard** correcting 150+ developer names gated behind programming/OS intent detection. | `core/vocabulary_guard.py`, `core/gemini.py`, `main.py` |
| **Global Desktop Input** | Interactive UI only available when ZEZO HUD has focus | **Non-Activating "Stapler" Snipping & Dictation** (`Ctrl+Alt+Space`) using `WS_EX_NOACTIVATE` without stealing window focus. | `actions/desktop_stapler.py`, `ui.py`, `core/hotkey.py` |
| **Telemetry & Observability** | Console logs and task status queries | **Debounced Live Telemetry Meter** rendered on HUD (`⚡ 320ms • 🪙 1.4k • $0.002`) with zero Qt thread lag. | `ui.py`, `core/log_bus.py`, `core/provider_health.py` |
| **External Event Triggers** | User spoken or hotkey triggers only | **Throttled Inbound Webhook Receiver** (`max=2` concurrency) with HMAC authentication and deduplication. | `core/webhook_server.py`, `core/task_manager.py` |

---

## 📋 Phased Implementation Plan

### 🛡️ Phase 1: Risk-Aware Circuit Breaker Ladder (Priority: High)
- [x] **Task 1.1: Implement `core/circuit_breaker.py` with Risk-Tiered Recovery**
  - Define three distinct capability risk buckets:
    - **L0 (Read-Only Exploration):** `dev_agent`, `grep_search`, `system_status`. Auto-recovers after 1 success.
    - **L1 (Low-Risk Mutation):** `code_helper`, `file_processor.append`. Requires 60s cooldown + 3 consecutive L1 successes.
    - **L2 (High-Risk / Destructive):** `opencode_run`, `file_controller.delete`, `git_push`. **Trips immediately on repeated failure; strictly requires explicit human voice/UI confirmation to re-arm.**
- [x] **Task 1.2: Connect Breaker to `core/task_manager.py` & Agent Handlers**
  - Track error velocity, repeating exception signatures, and token burn per active task ID.
  - Automatically downgrade failing L2 tasks to L0 read-only exploration before prompting the user.

---

### 🌿 Phase 2: Zero Data-Loss Git Worktree Sandboxing (Priority: High)
- [x] **Task 2.1: Implement Safe Worktree Lifecycle in `core/git_sandbox.py`**
  - Create isolated worktrees on dynamic branches: `git worktree add -b agent/{task_id} .agent_worktrees/{task_id}`.
  - **4-Gate Safe Teardown Protocol:**
    1. **Process Inspection:** Check for child processes (`python`, `pytest`, `node`) locking handles; gracefully terminate (`SIGTERM`).
    2. **Uncommitted Work Quarantine:** Run `git status --porcelain`. If modified/untracked files exist, stash to a quarantine branch (`quarantine/task_{task_id}_{ts}`) rather than deleting.
    3. **Unlock & Settle:** Execute `git worktree unlock` and allow a 500ms Windows file release settle delay.
    4. **Preserve Uncertain States:** If removal fails due to persistent OS locks, mark directory as `ORPHAN_PRESERVED` in the task ledger without executing destructive `git clean -fdx`.
- [x] **Task 2.2: Single-Committer Merge Lock & Conflict Protection**
  - Centralized Merge Mutex in `core/git_sandbox.py` to prevent parallel branch collisions on `main`.
  - On merge conflict: Preserve work in `conflict/{task_id}` and alert the user with high-level voice summary.
- [x] **Task 2.3: Named Agent Personas & Scranton Pixel Office Fleet Deck (`config/fleet_agents.json` & `core/fleet_manager.py`)**
  - **Custom Fleet Schema (`config/fleet_agents.json`):** Configurable registry defining agent `name`, `role`, `specialty`, `system_prompt_addon`, `worktree_prefix`, `avatar_palette` (shirt, hair, skin, tie), and default desk coordinates.
  - **Per-Agent Soul & Long-Term Memory On-Disk Layout (`hive/agents/<agent_id>/`):**
    - `soul.md` / `identity.md` — Agent's permanent personality, role constraints, behavioral quirks, and core competencies (loaded at spawn).
    - `memory.md` — Autonomous long-term memory journal updated and appended by the agent after each task/reflection.
    - `inbox/` & `outbox/` — Stigmergic message passing (FIPA-lite speech acts: `request`, `inform`, `agree`, `done`) routed safely by the main orchestrator without process lock collisions.
    - `cursor.json` — Tracks processed message IDs to ensure idempotent, loop-free task execution.
  - **Dynamic Subagent Dispatch & Voice Routing:** Enable targeted voice commands (e.g., *"Michael, summarize active sprint"* $\to$ routes to `MICHAEL` orchestrator, *"Dwight, security lint"* $\to$ routes to `DWIGHT` worker).
  - **Scranton Pixel Office Web Deck Bridge:** Connect backend task manager WebSocket events to `prototypes/scranton_pixel_office_fleet/index.html` (animating real-time desk focus, walking A* paths to server rack/boardroom, and populating right-drawer Inspector with live files, diffs, logs, and agent memory tabs).
  - **Custom User Agent Builder:** Allow users to create, rename, or reassign custom agents directly via voice or HUD settings.
- [x] **Task 2.4: Native Desktop HUD & Voice Integration for Scranton Office Deck**
  - Embed interactive Scranton Office modal (`#office-modal`) inside ZEZO desktop web engine (`frontend/index.html`) with real-time canvas, desk navigation, and live Inspector drawer.
  - Expose `/api/fleet/state` & WebSocket telemetry broadcast in `core/ui_server.py`.
  - Voice intent routing (*"open office view"*, *"show agents"*, *"open agent view"*) and Top Navbar icon trigger (`Ctrl+O`).
  - Dual-monitor standalone route (`/office`) for pop-out window operation.

---

### 🏛️ Phase 3: Immutable Provenance & Conflict-Aware Memory Palace (Priority: Medium)
- [x] **Task 3.1: Implement `memory/memory_condenser.py` with Conflict Graphs**
  - Store explicit user commands in an immutable SQLite table (`user_explicit_rules`) that cannot be modified by AI summaries.
  - Periodic background reaper clusters transcripts every 40 minutes using fast Groq LPU (`llama-3.3-70b-versatile`).
  - **Conflict Detection:** When a newly inferred note contradicts an existing directive, preserve both with exact source timestamps and generate a `CONFLICT_PENDING_RESOLUTION` node.
  - Prompt user at the next natural idle voice turn for explicit conflict resolution.
- [x] **Task 3.2: HUD Memory Palace Snapshot & Integration**
  - Expose snapshot state (active immutable user rules, topic clusters, structured facts, and pending conflict cards) for HUD / Settings consumption.

---

### 🗣️ Phase 4: Context-Aware STT Vocabulary Guard & Non-Activating "Stapler" (Priority: Medium)
- [ ] **Task 4.1: Implement Context-Aware `core/vocabulary_guard.py`**
  - Maintain 150+ developer vocabulary mappings (`{"pie auto guy": "pyautogui", "pi cute six": "PyQt6", "dx cam": "dxcam", "u i a": "UIA", "grock": "Groq"}`).
  - **Intent Gate:** Filter replacements so they only execute when surrounding tokens indicate programming/OS actions, preventing false positive replacements in casual speech.
- [ ] **Task 4.2: Implement Non-Focus-Stealing "Stapler" in `actions/desktop_stapler.py`**
  - Register `Ctrl+Alt+Space` in `core/hotkey.py`.
  - Capture active window handle (`target_hwnd = win32gui.GetForegroundWindow()`) prior to overlay initialization.
  - Apply Win32 `WS_EX_NOACTIVATE` window style so the audio recording overlay never steals foreground focus from the target app.
  - Capture cropped screen region + voice audio and route to `actions/computer_control.py` or `actions/code_helper.py`.

---

### 📊 Phase 5: Real-time Telemetry HUD & Throttled Inbound Webhooks (Priority: Medium)
- [ ] **Task 5.1: Debounced Real-time Telemetry in `ui.py`**
  - 150ms debounced metric aggregator emitting atomic token count, roundtrip latency (ms), and cost estimates to the HUD status bar.
- [ ] **Task 5.2: Secure Inbound Webhook Dispatcher in `core/webhook_server.py`**
  - FastAPI / `aiohttp` endpoint (`/webhook/{source}`) with HMAC secret verification.
  - Strict concurrency cap (`MAX_CONCURRENT_WEBHOOK_TASKS = 2`) and Token Bucket rate limiter (1 trigger / 10s) to prevent API quota and system memory exhaustion.

---

### 🧪 Phase 6: 3-Layer Verification & Documentation (Priority: High)
- [ ] **Layer 1: Static Architecture & Tool Schema Audit**
  - `py_compile` all newly created core modules (`circuit_breaker.py`, `git_sandbox.py`, `memory_condenser.py`, `vocabulary_guard.py`, `webhook_server.py`).
  - Verify action loader discovery across all 24 tools.
- [ ] **Layer 2: Real Runtime Benchmarks**
  - **Benchmark 1 (Risk-Tiered Breaker):** Verify that 3 successful L0 read-only actions do NOT unlock failing L2 destructive mutations without human confirmation.
  - **Benchmark 2 (Zero-Loss Worktree):** Simulate a locked file in `.agent_worktrees/task-101` $\to$ verify changes are safely committed to `quarantine/task-101` with 0 data loss.
  - **Benchmark 3 (Memory Conflict):** Inject conflicting user preferences $\to$ verify immutable rule is preserved and conflict card is queued.
  - **Benchmark 4 (Stapler Non-Activating):** Verify `Ctrl+Alt+Space` captures background app screenshot without losing active focus.
- [ ] **Layer 3: Documentation Synchronization**
  - Update `docs/PROJECT_ARCHITECTURE.md`, `docs/TOOLS.md`, `AGENTS.md`, and log architecture decisions in `LEARNING_JOURNAL.md`.

---

## 🚨 Critical Edge Cases & Production Mitigations (8 Core Fleet Domains)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           8 CRITICAL FLEET HARNESS EDGE CASE DOMAINS                            │
├───────────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ 1. Windows Worktree File Locks│ 2. Risk-Aware Breaker Recovery  │ 3. Memory Conflict & Provenance│
│ • Zero Data Loss Quarantine   │ • L0/L1/L2 Permission Buckets   │ • Immutable User Rules Table  │
│ • No git clean -fdx on error  │ • Human Gate for Destructive    │ • Conflict Resolution Prompts │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 4. Contextual Vocabulary Guard│ 5. Non-Activating Stapler Focus │ 6. Single-Committer Git Mutex │
│ • Code/OS Intent Gating       │ • WS_EX_NOACTIVATE Window Flag  │ • Centralized Merge Mutex     │
│ • Bypassed in General Chat    │ • Pre-hotkey Target HWND Cache  │ • Staged Draft Conflict Branch│
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 7. Webhook Event Bursts       │ 8. Telemetry UI Thread Choke    │                               │
│ • Concurrency Cap (max=2)     │ • 150ms Debounced Signal Batch  │                               │
│ • Token Bucket Rate Limiter   │ • Atomic Counter Rendering      │                               │
└───────────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

### 1. Windows Git Worktree File Locks & Zero Data-Loss Policy
- **Risk:** Background IDEs, linters, or python subprocesses hold file handles in `.git/worktrees/{task_id}`. Blindly running `git clean -fdx` or force-deleting folders destroys untracked/uncommitted developer work.
- **Mitigation:** Enforce non-destructive teardown: inspect locking processes, stash all uncommitted diffs to `quarantine/task_{task_id}_{ts}`, execute `git worktree unlock` with a 500ms settle delay, and archive unresolved directories as `ORPHAN_PRESERVED` without deletion.

### 2. Risk-Aware Circuit Breaker Permission Recovery
- **Risk:** An agent fails a destructive operation (e.g. multi-file overwrite) $\to$ executes 3 simple read-only queries (`grep_search`) $\to$ circuit breaker resets to `NORMAL` $\to$ agent immediately retries and repeats the destructive error.
- **Mitigation:** Partition capabilities into **L0 (Read-Only)**, **L1 (Low-Risk Mutation)**, and **L2 (Destructive)**. Read-only successes only restore L0/L1 permissions. Restoring L2 destructive permissions strictly requires explicit human voice/UI authorization.

### 3. Memory Condensation Conflict Resolution & Provenance
- **Risk:** AI summarizers summarizing session transcripts silently overwrite permanent user preferences or drop original context timestamps.
- **Mitigation:** Maintain explicit user directives in an immutable table. When a contradiction is detected, generate a timestamped conflict graph (`CONFLICT_PENDING_RESOLUTION`) and prompt the user for clarification during the next voice turn rather than silently overwriting.

### 4. Context-Aware Phonetic STT Filtering
- **Risk:** Phonetic replacement dictionary alters natural conversational words (e.g. *"I bought a pie"*) to technical tools (`"pyautogui"`).
- **Mitigation:** Gate phonetic dictionary replacements behind a context intent detector that requires programming or OS command markers before performing replacements.

### 5. Non-Activating Desktop "Stapler" Window Z-Order
- **Risk:** Pressing `Ctrl+Alt+Space` creates an audio overlay that steals active window focus, causing screen capture to grab the overlay rather than the target app.
- **Mitigation:** Cache `target_hwnd = win32gui.GetForegroundWindow()` before showing the overlay, and apply Win32 `WS_EX_NOACTIVATE` window styling so the overlay renders without stealing focus.

### 6. Concurrent Subagent Git Merge Conflicts
- **Risk:** Parallel subagents in separate worktrees simultaneously edit identical files, crashing on branch merge to `main`.
- **Mitigation:** Centralized Merge Mutex in `core/git_sandbox.py`. Subagents merge sequentially; conflicts automatically isolate to `conflict/{task_id}` with voice alerts.

### 7. Inbound Webhook DOS & Rate-Limit Exhaustion
- **Risk:** CI test matrix failures send a burst of 50+ failure webhooks, exhausting system RAM and LLM token budgets.
- **Mitigation:** Enforce `MAX_CONCURRENT_WEBHOOK_TASKS = 2` with a Token Bucket rate limiter (1 trigger / 10s) and deduplication hash ring.

### 8. Real-time Telemetry UI Thread Saturation
- **Risk:** High-frequency parallel streaming tool events emit rapid token and latency signals, saturating the PyQt6 main thread event loop.
- **Mitigation:** Buffer telemetry emissions through a 150ms debounced aggregator that flushes batched metrics atomically to the HUD status bar.

---

## 🛡️ Risk Assessment & Mitigation Matrix

| Potential Risk | Likelihood | Impact | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Worktree Data Loss on Lock** | High | High | Non-destructive quarantine stashing + process handle inspection (No blind `git clean -fdx`). |
| **Breaker Recovery Bypass** | Medium | High | Risk-tiered recovery: L2 destructive actions strictly require human authorization to re-arm. |
| **Memory Overwriting User Rules** | Medium | High | Immutable user directives table + timestamped conflict resolution prompts. |
| **Phonetic STT False Positives** | Medium | Medium | Context-aware intent filter restricting replacements to technical command contexts. |
| **Stapler Overlay Stealing App Focus** | High | High | Pre-hotkey HWND caching + Win32 `WS_EX_NOACTIVATE` window styling on overlay. |
| **Parallel Agent Branch Merge Collisions** | Medium | High | Single-Committer Merge Mutex queue + fallback draft conflict branching. |
| **Webhook Burst / API Quota Exhaustion** | Medium | High | Strict concurrency cap (`max=2`), token bucket rate limiting, and deduplication ring. |
| **Telemetry Signal Flooding PyQt6 UI** | Low | Medium | 150ms debounced batching buffer before triggering Qt status bar repaint signals. |
| **Fleet / Foundation Coupling Drift** | Low | High | Explicit dependency anchoring on `PLAN_VOICE_LATENCY_AND_DESKTOP_STABILITY.md` Layer-0 reliability. |
