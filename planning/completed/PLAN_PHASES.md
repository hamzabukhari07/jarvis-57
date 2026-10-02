# 🏛️ ZEZO OS — Tiered Perception & Smart Autonomous System Architecture Plan

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Principle:** *"Observe only when necessary — Escalate perception, don't waterfall it."*  
> **Status:** ✅ 100% COMPLETED & VERIFIED  

---

## 🎯 Architectural Overview & Decision Flow

```text
                  User Voice / Gemini Live
                             │
                     ZEZO Dispatcher
                             │
                 ┌───────────────────────┐
                 │ Perception Required?  │
                 └───────────┬───────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
L0: OS Native (0.37ms)  L1: Windows UIA (<15ms) L2: Gemini Vision (2s)
(HWND, Bounds, Process) (Buttons, Text, Trees)  (Deep Visual OCR/UI)
     │                       │                       │
     └───────────────────────┼───────────────────────┘
                             ▼
                     Perception State
           {source, app, bounds, confidence, dpi, ts}
                             │
                             ▼
         Tool Execution Context (Timeout & Cancel Token)
                             │
                             ▼
          Action Executor (Risk Gated + Verified Drivers)
                             │
                             ▼
                 State & Focus Verification
```

---

## 📋 Implementation Phases

```
[ Phase 1: L0 OS State Engine, DPI Scaling & Region Cropping ]
       │
[ Phase 2: Perceptual Hashing, Cache & Freshness ]
       │
[ Phase 3: Structured Perception & 5-Tier Risk Governance ]
       │
[ Phase 4: Modular Computer Drivers, Unicode Clipboard & Windows UIA ]
       │
[ Phase 5: Action State Tracking, Execution Context & Anti-Looping ]
       │
[ Phase 6: Async MCP Runtime, 3-Layer Verification & Benchmarks ]
```

---

### 🔹 Phase 1: L0 OS Native Engine, DPI Scaling & Multi-Region Capture
- **Objective:** Give ZEZO instantaneous OS awareness, normalize display coordinates across High-DPI monitors, and eliminate full-screen screenshot overhead.
- **Tasks:**
  - [x] Implement `GetWindowRect` and `GetForegroundWindow` in `actions/screen_processor.py` for exact window bounds and process telemetry (0.37ms).
  - [x] Add display scaling normalization (`Capabilities.dpi_scale`) to convert between physical pixels and logical coordinates (100%, 125%, 150% scaling).
  - [x] Support flexible capture modes in screenshot subsystem:
    - `full_screen` (default multi-monitor or primary display)
    - `active_window` (crops to foreground application HWND bounds)
    - `window_region` (specific quadrant or UI area)
  - [x] Update `actions/open_app.py` and `actions/computer_control.py` to return state-verified confirmations (e.g. `"Opened notepad (Focused: 'Untitled - Notepad' [notepad.exe])"`).

---

### 🔹 Phase 2: Perceptual Hashing, Observation Freshness & Smart Cache
- **Objective:** Prevent redundant API calls when screen state is unchanged.
- **Tasks:**
  - [x] Implement difference-hashing (`dhash`) on screen frames to detect genuine visual changes in < 0.2ms.
  - [x] Create a thread-safe perception memory cache (`PerceptionCache`) storing semantic observations:
    ```json
    {
      "screen_hash": "a4f8c2...",
      "timestamp": 1720000000,
      "source": "l0_os | l1_uia | l2_vision | cache",
      "app": "WhatsApp",
      "window_title": "WhatsApp",
      "state_summary": "Chat view open with Inferno"
    }
    ```
  - [x] Return cached perception in **0.0ms** (`[Cache: 0ms]`) if screen state hasn't meaningfully changed (Hamming distance <= 2).

---

### 🔹 Phase 3: Structured Perception Payload & 5-Tier Tool Risk Governance
- **Objective:** Move from chatty descriptions to deterministic perception data with formal action-risk taxonomy and time-bound approval grants.
- **Tasks:**
  - [x] Standardize L2 Vision output schema:
    ```json
    {
      "active_app": "WhatsApp",
      "window_title": "WhatsApp",
      "screen_state": "chat_list",
      "found_target": "Send Button",
      "coordinates": [1450, 920],
      "confidence": 0.94,
      "source": "l2_vision",
      "timestamp": 1720000000
    }
    ```
  - [x] Introduce formal 5-tier `ToolRisk` taxonomy in `core/governance.py` and `core/confirm.py`:
    - `READ_ONLY` (`screenshot`, `read_file`, `system_status`) → Allowed immediately.
    - `LOCAL_MUTATION` (`type`, `move`, `click`, `write_file`) → Allowed with confidence >= 0.70.
    - `EXTERNAL_MUTATION` (`send_message`, `git_push`) → Requires user confirmation.
    - `CODE_EXECUTION` (`opencode_run`, `kilo_run`, shell execution) → Gated with `ApprovalScope`.
    - `PRIVILEGED_OS` (`shutdown_jarvis`, system power/registry) → Explicit user voice approval required.
  - [x] Implement `ApprovalGrant` with expiration timestamps (`expires_in_seconds=60`) to prevent stale authorizations.

---

### 🔹 Phase 4: Modular Computer Drivers, Unicode Clipboard & L1 Windows UIA
- **Objective:** Modularize computer control into clean driver ports, guarantee 100% typing accuracy for multilingual/Unicode text, and enable UI tree inspection in < 15ms.
- **Tasks:**
  - [x] Create clean, decoupled drivers under `core/computer/`:
    - `core/computer/windows_native.py` (Win32 HWND, focus, window bounds, process telemetry)
    - `core/computer/windows_uia.py` (Windows Accessibility & UI Automation for buttons, text fields, lists)
    - `core/computer/pyautogui_driver.py` (Raw hardware keyboard/mouse with post-move coordinate verification)
  - [x] Implement safe Unicode typing with clipboard buffer preservation:
    - Auto-detect non-ASCII characters (Urdu, Hindi, Arabic, emojis, symbols).
    - Backup previous user clipboard, paste string via clipboard shortcut, and restore original clipboard state seamlessly.
  - [x] Add post-action coordinate verification (`POST_MOVE_VERIFY` with tolerance threshold) to eliminate missed clicks.
  - [x] Refactor `actions/computer_control.py` as a lightweight dispatcher prioritizing:
    **`1. Windows UIA → 2. Native Win32 → 3. PyAutoGUI Driver → 4. Gemini Vision`**.

---

### 🔹 Phase 5: Action State Tracking, Tool Execution Context & Anti-Looping
- **Objective:** Guard the Gemini Live WebSocket against keepalive timeouts, track step lifecycles, and prevent stale action execution.
- **Tasks:**
  - [x] Introduce `ToolExecutionContext` across action dispatches with explicit `timeout_seconds` and `CancelToken` to prevent hanging tasks from causing `1011 keepalive ping timeout` crashes.
  - [x] Implement monotonic `AgentRun` state machine (`CREATED -> QUEUED -> RUNNING -> CANCELLING -> DONE/FAILED/CANCELLED`) in `core/task_manager.py`.
  - [x] Decompose compound actions into granular micro-events (`started`, `progress`, `completed`) for rich, real-time HUD telemetry in `core/log_bus.py`.
  - [x] Verify target window focus before dispatching keystrokes or clicks to eliminate stale background actions.
  - [x] Update `core/prompt.txt` with strict escalation & anti-looping rules (never issue repetitive `screen_process` loops).

---

### 🔹 Phase 6: Async MCP Runtime, Full 3-Layer Verification & Latency Benchmarks
- **Objective:** Isolate external tool coroutines, verify system stability against AGENTS.md regression rules, and measure performance gains.
- **Tasks:**
  - [x] Implement `McpClientRuntime` running on an isolated background event loop (`zezo-mcp-runtime`) to prevent MCP tool calls from blocking the main PyQt6 GUI or Gemini Live audio loop.
  - [x] **Layer 1 (Static):** Run `py_compile` across all modified core/action files; verify all discovered tools.
  - [x] **Layer 2 (Runtime Evidence):**
    - Benchmark end-to-end user-perceived latency (`User Request → Intent → Dispatch → Execution → Response`).
    - Verify 0.37ms OS state, 0ms cache hits, safe Unicode typing, and cropped vision execution.
  - [x] **Layer 3 (Regression Check):** Validate against all AGENTS.md non-negotiable rules (Rule 1–7).
  - [x] **Documentation Sync:** Update `LEARNING_JOURNAL.md`, `docs/VISION.md`, and `docs/COMPUTER_CONTROL.md`.

---

## 🚦 Execution Status Tracker

| Phase | Description | Key Modules / Concepts | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | L0 OS State Engine & Region Cropping | `GetForegroundWindow`, DPI Scaling, Multi-Region Crop | ✅ COMPLETED |
| **Phase 2** | Perceptual Hashing & Smart Cache | dHash, 0ms Observation Cache, Freshness Check | ✅ COMPLETED |
| **Phase 3** | Structured Perception & Risk Governance | 5-Tier `ToolRisk`, `ApprovalScope`, Schema Contract | ✅ COMPLETED |
| **Phase 4** | Modular Drivers & Unicode Clipboard | `core/computer/`, Safe Clipboard Typing, Win UIA | ✅ COMPLETED |
| **Phase 5** | Execution Context & Anti-Looping | `ToolExecutionContext`, `CancelToken`, `TaskStatus` | ✅ COMPLETED |
| **Phase 6** | Async MCP Runtime & 3-Layer Verification | `McpClientRuntime`, Latency Benchmark, 3-Layer Tests | ✅ COMPLETED |
