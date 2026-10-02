# 🏛️ ZEZO OS — Desktop Stabilization, Canvas Control & Lifecycle Hardening Plan



Treat the following architecture plan as the target design. Before modifying anything, deeply inspect the existing ZEZO codebase and map every task to the current implementation. Do not blindly implement the phases. Identify what already exists, what needs to change, what should be reused, and any conflicts or risks. Then propose the safest implementation order. Do not modify code until I explicitly approve the implementation plan

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Principle:** *"Observe only when necessary — Escalate perception, don't waterfall it."*  
> **Status:** 🟡 READY FOR EXECUTION (100% SPEC COMPLETE)  
> **Mandated Execution Order:** `1 ──► 3 ──► 2 ──► 4 ──► 5 ──► 6`

---

## 🎯 Executive Summary & Objectives

Based on the real-world execution transcript and telemetry audit, this plan addresses the next generation of desktop control challenges:
1. **Gemini Live Session Termination (1008, 1006, 1000, 1011, GoAway):** Ensuring seamless, clean reconnections when long-running sessions hit duration limits, policy violation triggers, or abnormal close codes by dropping poisoned resumption handles.
2. **Per-Monitor DPI & Win32 DWM Shadow Margins:** Calling `SetProcessDPIAware()` at startup to resolve virtualized scaling (`1711x931`) and eliminating `(-8, -8)` window offsets via `DwmGetWindowAttribute(hwnd, 9, ...)`.
3. **Hotkey Anti-Loop Circuit Breaker & Aliases:** Programmatically preventing models from issuing blind repetitive keystroke loops (e.g. >4 `shift+tab` spams in 10s) and providing resilient aliases (`action='enter'`, `'escape'`, etc.).
4. **Chat App Auto-Send & Governance Gate:** Restricting automated message submission in WhatsApp/Telegram/Discord without explicit user verbal commands ("send it" / "bhejo").
5. **Canvas & Design App Protocol (Figma, Canva):** Introducing standardized spatial interaction workflows (`t` $\to$ canvas click $\to$ type).
6. **GUI Contextual Undo vs File Undo:** Routing verbal "undo" requests to `Ctrl+Z` in GUI apps while retaining file-level transactions.

---

## 📋 Phased Execution Roadmap

```
[ Phase 1: WebSocket Session Lifecycle & Termination Codes (1008, 1006, 1000, 1011, GoAway) ]
       │
[ Phase 3: Hotkey Anti-Loop Circuit Breaker & Action Aliases (Stops UI Spam First) ]
       │
[ Phase 2: SetProcessDPIAware() Startup & DWM Extended Frame Bounds (Physical Coordinates) ]
       │
[ Phase 4: Chat App Governance, Post-Launch Focus Guard & Contextual GUI Undo ]
       │
[ Phase 5: Canvas Application Interaction Protocol (Figma/Canva Skill Package) ]
       │
[ Phase 6: 3-Layer Verification, Test Suite & Documentation Sync ]
```

---

### 🔹 Phase 1: WebSocket Session Lifecycle & Termination Codes Hardening
- **Objective:** Prevent stale/poisoned session resumption handles from causing reconnection failures when Google Live sessions terminate via `1008 (Policy Violation / GoAway)`, `1006 (Abnormal Closure)`, `1000 (Normal Closure)`, `1011 (Internal Error)`, or server timeouts.
- **Key Modules:** `main.py`
- **Tasks:**
  - [x] Update `_receive_audio` exception handler in `main.py` to identify `1008`, `1006`, `1000`, `1011`, `goaway`, `policy violation`, and `internal error`.
  - [x] Reset `self._resume_handle = None` and raise `_ReconnectSignal(keep_context=False)` on all session termination codes so the subsequent connection starts fresh without delay.
  - [x] Verify that reconnection triggers clean session initialization and preserves memory summaries without looping.

---

### 🔹 Phase 3: Hotkey Anti-Loop Circuit Breaker & Action Aliases
- **Objective:** Block repetitive blind hotkey spam at the runtime level and alias common model syntax mistakes before testing coordinate-heavy workflows.
- **Key Modules:** `core/action_loader.py`, `actions/computer_control.py`
- **Tasks:**
  - [x] Implement an in-turn **Circuit Breaker** in `core/action_loader.py`:
    - Track consecutive identical action signatures per turn (e.g. `hotkey: shift+tab`).
    - If identical hotkey is called > 4 times in a 10s window, abort execution and return:
      `"Aborted: Repetitive hotkey loop detected (>4 calls in 10s). Use spatial coordinate clicks or inspect the UI state."`
  - [x] Add canonical action alias mapping in `actions/computer_control.py`:
    - `action='enter'` $\to$ map to `press('enter')`
    - `action='escape'` $\to$ map to `press('escape')`
    - `action='space'` $\to$ map to `press('space')`
    - `action='backspace'` $\to$ map to `press('backspace')`
    - `action='tab'` $\to$ map to `press('tab')`
    - `action='delete'` $\to$ map to `press('delete')`

---

### 🔹 Phase 2: SetProcessDPIAware() Startup & DWM Extended Frame Bounds
- **Objective:** Fix virtualized desktop scaling (`1711x931` bug) via `SetProcessDPIAware()` and eliminate the Windows 10/11 invisible 8px DWM drop-shadow margin bug that causes top-level windows to report `(-8, -8)` and inflated dimensions (`1936x1048`).
- **Key Modules:** `main.py`, `core/computer/windows_native.py`, `actions/screen_processor.py`
- **Tasks:**
  - [x] Initialize `ctypes.windll.user32.SetProcessDPIAware()` (or `SetProcessDpiAwarenessContext(-4)`) at the very entry point of `main.py`.
  - [x] Import `dwmapi.dll` in `core/computer/windows_native.py`.
  - [x] Implement `get_window_rect_physical(hwnd)` using `DwmGetWindowAttribute` with `DWMWA_EXTENDED_FRAME_BOUNDS` (Attribute ID `0x9`):
    ```python
    import ctypes
    from ctypes import wintypes
    
    rect = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(9), # DWMWA_EXTENDED_FRAME_BOUNDS
        ctypes.byref(rect),
        ctypes.sizeof(rect)
    )
    ```
  - [x] Fall back to standard `GetWindowRect` with shadow margin trimming (8px) if `dwmapi` is unavailable.
  - [x] **Integration into `actions/screen_processor.py`:** Update `get_active_window_context()` and `active_window` screenshot cropping to use `get_window_rect_physical()`, eliminating transparent drop-shadow artifacts from Gemini vision inputs.

---

### 🔹 Phase 4: Chat App Governance, Post-Launch Focus Guard & Contextual GUI Undo
- **Objective:** Eliminate premature automated message sending, prevent focus race conditions during app launches, and map verbal "undo" commands to `Ctrl+Z` in GUI editors.
- **Key Modules:** `core/governance.py`, `actions/send_message.py`, `actions/open_app.py`, `core/prompt.txt`
- **Tasks:**
  - [x] **Post-Launch Focus Guard in `actions/open_app.py`:** After launching an application, poll `GetForegroundWindow()` for up to 500ms. If the launched application does not gain focus automatically, invoke `windows_native.focus_window(app_name)`.
  - [x] Update `core/prompt.txt` with strict chat safety rule:
    - *"When typing in WhatsApp, Telegram, Discord, or chat inputs: ONLY type the text. NEVER press enter or click send unless the user explicitly uses words like 'send it', 'bhejo', 'deliver it'."*
  - [x] Split `send_message` in `core/governance.py`:
    - `action='search'` $\to$ `ToolRisk.READ_ONLY`
    - `action='send'` $\to$ `ToolRisk.EXTERNAL_MUTATION` (Requires explicit confirmation)
  - [x] Add GUI Contextual Undo in `core/prompt.txt` and `actions/computer_control.py`:
    - When active foreground window is an editor/GUI (Figma, Notepad, Code, Browser) and user commands "Undo" / "Revert that", dispatch `computer_control(action='hotkey', keys='ctrl+z')` instead of the file `undo` tool.

---

### 🔹 Phase 5: Canvas Application Interaction Protocol (Figma, Canva)
- **Objective:** Enable reliable manipulation of web/Electron canvas apps without blind keyboard navigation.
- **Key Modules:** `skills/figma_helper/SKILL.md`, `core/prompt.txt`, `actions/computer_control.py`
- **Tasks:**
  - [x] Create declarative skill package [`skills/figma_helper/SKILL.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/zezo%20latest/skills/figma_helper/SKILL.md) with canonical recipes:
    - **Text Placement:** `press('t')` $\to$ `click(x, y)` on canvas $\to$ `type('text')` $\to$ `press('escape')`.
    - **Shapes & Frames:** `press('f')` (frame) / `press('r')` (rect) / `press('o')` (ellipse) $\to$ `drag(start_x, start_y, end_x, end_y)`.
    - **Canvas Zoom:** Use `Shift+1` (zoom to fit) or `Shift+2` (zoom to selection) instead of OS zoom.
    - **No Blind Shift-Tab:** Explicitly forbid blind tab indexing inside canvas viewports.
  - [x] Update `core/prompt.txt` with `[FIGMA CANVAS PROTOCOL]`.

---

### 🔹 Phase 6: 3-Layer Verification, Test Suite & Documentation Sync
- **Objective:** Guarantee zero regressions against `AGENTS.md` rules with automated pass/fail verification criteria.
- **Tasks:**
  - [x] **Layer 1 (Static):** Run `py_compile` across all modified files; verify clean imports and action discovery (24 actions).
  - [x] **Layer 2 (Concrete Runtime Assertions):**
    - **DWM Bounds & DPI Test:** Assert DPI awareness active, `x >= 0`, `y >= 0`, and `width <= screen_width` for standard top-level windows without `(-8, -8)` margins.
    - **Circuit Breaker Test:** Issue 5x identical hotkeys in 10s $\to$ assert execution is aborted on the 5th call with a clear guidance message.
    - **Termination Codes Test:** Verify that `1008`, `1006`, `1000`, `1011`, and `GoAway` trigger `self._resume_handle = None` and `keep_context=False`.
    - **Focus Race Test:** Launch Notepad $\to$ verify foreground window is Notepad before `open_app` returns.
  - [x] **Layer 3 (Regression Checks):** Confirm zero interference with PyQt6 GUI and Gemini Live audio loop.
  - [x] **Documentation Sync:** Update `planning/README.md`, `planning/ZEZO_PROJECT_BLUEPRINT.md`, and `LEARNING_JOURNAL.md`.

---

## 🚦 Phase Status Tracker

| Phase | Description | Key Deliverables | Status | Risk if Skipped |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Session Lifecycle Hardening | 1008, 1006, 1000, 1011, GoAway clean reconnection | ✅ COMPLETED | Termination kills sessions and creates reconnect loops |
| **Phase 3** | Hotkey Circuit Breaker & Aliases | Repetition limiter & friendly action aliases | ✅ COMPLETED | Model spams 16x shift+tab in canvas |
| **Phase 2** | SetProcessDPIAware & DWM Bounds | `SetProcessDPIAware()` + `dwmapi.dll` Frame Bounds | ✅ COMPLETED | Clicks off by 8px, inaccurate crops, 1711x931 scaling |
| **Phase 4** | Chat Governance & Focus Guard | Anti-send rule, launch focus & GUI `Ctrl+Z` | ✅ COMPLETED | Premature message sends; wrong window typing |
| **Phase 5** | Canvas Interaction Protocol | Figma/Canva skill package & tool sequences | ✅ COMPLETED | Text tool fails without canvas click |
| **Phase 6** | 3-Layer Verification & Sync | Automated test assertions & blueprint update | ✅ COMPLETED | Undetected regression across 24 tools |



