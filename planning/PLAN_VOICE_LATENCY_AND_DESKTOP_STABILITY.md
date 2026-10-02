# 🚀 Architecture & Implementation Plan: Voice Latency, Action Keepalive Shield & Desktop Control Stability (v4 — Final Production Blueprint)

> **Project:** ZEZO OS v2 (Autonomous Desktop AI Operating System)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Architectural Invariant:**  
> ⚠️ **No tool, OCR, Vision, browser automation, or OS operation may block the Gemini Live audio/receive loop. All potentially blocking work must execute through an isolated background worker with timeout, cancellation, job/action identity, payload truncation, and stale-action protection.**  
> **Target Objectives:** Sub-600ms Spoken Latency | Live Event Loop Isolation | Instant UIA Clicks (<15ms) | DirectX GPU Screen Grab (`dxcam` ~5ms) | 0ms ROI Hash Cache | Zero WebSocket 1011 Disconnects  
> **Date:** October 2026  

---

## 🎯 Executive Summary & Objectives

This final production blueprint fuses live session performance data, senior architectural reviews, and high-performance native Windows OS libraries (`pywinauto`, `dxcam`, `mss`, `comtypes`, `pywin32`, `keyboard`, `onnxruntime-gpu`) to deliver an ultra-responsive, rock-solid desktop AI assistant:

1. **Live Loop Isolation & 2KB Payload Shield:**  
   - Dispatch tool execution to an isolated background worker pool with a strict 10s cancellation envelope.
   - Enforce `MAX_RESPONSE_SIZE = 2048` (2KB) on all tool returns; large outputs/tracebacks are written to `logs/tool_outputs/{name}_{ts}.log` to **permanently prevent WebSocket frame choke & 1011 disconnects**.
2. **Chrome CDP (Chrome DevTools Protocol) Connection:**  
   - Attempt CDP attach (`http://localhost:9222`) to control existing running Chrome tabs without database lock conflicts; fallback seamlessly to `.jarvis_profiles/chrome`.
3. **High-Speed Native UIA Control via `pywinauto` + `comtypes` (<15ms):**  
   - Replace slow 5.9s visual OCR with direct Windows UI Automation (UIA) tree discovery for buttons, inputs, and ribbons.
4. **DirectX GPU Screen Capture (`dxcam` ~5ms) with `mss` Fallback:**  
   - Utilize DirectX Desktop Duplication API (`dxcam`) for 5–8ms GPU VRAM frame grabs (3x faster than GDI); automatic fallback to `mss` (~12ms) on non-DXGI displays.
   - Apply native Win32 `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` to ZEZO's HUD to eliminate visual hallucination with zero window flicker.
5. **0ms ROI Hash Caching & `onnxruntime-gpu`:**  
   - Hash image regions of interest (ribbon/toolbar MD5 hash); cached bounding boxes resolve in **0ms (instant memory lookup)** on repeated queries.
   - Accelerate uncached OCR via `onnxruntime-gpu` / INT8 quantization (<200ms).
6. **Hardware-Aware Tiered Vision (Local VLM vs Cloud Groq):**  
   - CUDA GPU Systems: Local `Moondream2` / `Qwen2-VL-2B` for local visual grounding (<300ms, $0 cost, 0 network timeouts).
   - CPU-only Systems: Cloud Groq LPU / Gemini REST ladder (~250–400ms).
7. **Context-Aware Dynamic Stale Action Ledger:**  
   - Action ledger enforces action-specific TTL (`press: 1.5s`, `hotkey: 1.5s`, `type: 2.0s`, `click: 2.0s`, `drag: 3.0s`) and target window verification before every state mutation.
8. **Adaptive Language-Aware VAD:**  
   - Dynamic linguistic heuristic: `300ms` for English turns; `400ms` for Urdu/Hindi/bilingual turns to respect natural thinking pauses.

---

## 🏗️ Architectural Flow: Gemini Live Isolation & Tiered Execution

```
                       ┌───────────────────────────────┐
                       │  Gemini Live WebSocket Loop   │ ◄── Pure Audio / Transcripts
                       │   (main.py - NEVER BLOCKED)   │
                       └───────────────┬───────────────┘
                                       │ Tool Call Triggered
                                       ▼
                       ┌───────────────────────────────┐
                       │      Action Dispatcher        │ ◄── Immediate Acknowledgment
                       │  (core/task_manager.py)       │     & Non-Blocking Voice
                       └───────┬───────────────┬───────┘
                               │               │
            ┌──────────────────┴──┐         ┌──┴────────────────────────────────┐
            │   Execution Ledger   │         │  Isolated Worker Pool             │
            │ (action_id / job_id) │         │  • 10s Timeout Shield             │
            │ • Dynamic Action TTL │         │  • MAX_RESPONSE_SIZE = 2KB Cap    │
            └─────────────────────┘         └──────────┬────────────────────────┘
                                                       │
                           ┌───────────────────────────┴───────────────────────────┐
                           │                                                       │
                           ▼                                                       ▼
            ┌─────────────────────────────┐                         ┌─────────────────────────────┐
            │    Computer Control (OS)    │                         │    Perception / Vision      │
            ├─────────────────────────────┤                         ├─────────────────────────────┤
            │ • L0: Win32 API / Hotkeys   │                         │ • dxcam GPU Grab (5-8ms)    │
            │ • L1: pywinauto UIA (<15ms) │                         │ • WDA_EXCLUDEFROMCAPTURE    │
            │ • Universal Window Verify   │                         │ • 0ms ROI Hash Cache        │
            │ • CDP Chrome Attach (:9222) │                         │ • Local VLM / Groq Vision   │
            └─────────────────────────────┘                         └─────────────────────────────┘
```

---

## 🔍 Audit & Problem-to-Solution Mapping Matrix

| Issue Observed in Test Run | Root Cause in Codebase | Architectural Solution & Fix | Target State |
| :--- | :--- | :--- | :--- |
| **Tool Hang causing WebSocket 1011 Disconnect** | Playwright hung on locked Chrome profile (`pid=22644`), running inline in `_receive_audio` and starving the WebSocket keepalive ping. | Move tool execution to isolated worker pool with 10s cancellation envelope; connect via CDP (`:9222`) or dedicated profile. | **Heavy tool execution never blocks the Gemini Live loop** |
| **Large Error Trace Choking WebSocket** | Unbounded tool error tracebacks (>10KB) sent directly in `send_tool_response`, choking WebSocket frames. | Enforce `MAX_RESPONSE_SIZE = 2048` (2KB). Log full output to `logs/tool_outputs/` and return clean truncated summary. | **Zero WebSocket frame overflow crashes** |
| **5.9s OCR Search Delay in Paint** | RapidOCR scanned unscaled full-screen frames on CPU sequentially without region targeting. | Use `pywinauto` UIA tree search first (<15ms); fallback to 0ms ROI Hash Cache + GPU RapidOCR (<200ms). | **UI button clicks under 15ms** |
| **Figma / Paint Drawing Mismatch** | ZEZO sent hotkeys/drags to Paint while Figma had foreground focus; stale keystrokes leaked. | Universal foreground verification for all clicks/types/drags; discard actions if target window changed. | **Zero misdirected keystrokes or mouse actions** |
| **Perception Hallucinations on HUD** | ZEZO's own avatar window and floating widgets were included in full-desktop screenshots. | Win32 `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` applied to PyQt HUD windows via `pywin32`. | **100% clean user-content screenshots** |
| **Slow Screen Capture Latency** | GDI/PIL grab takes 30–45ms per frame. | `dxcam` DirectX GPU capture (~5–8ms) with `mss` CPU fallback (~12ms). | **Sub-10ms screen grab pipeline** |
| **`kilo_run` Refusal on Desktop Root** | Governance rejected `Desktop` path for multi-file refactoring without fallback. | Auto-route single-file desktop edits to `actions/code_helper.py` or scoped workspace subfolder. | **Seamless inline code edits on Desktop** |
| **Stale Actions after Window Closure** | Delayed keypresses arrived after user closed the target application. | Action ledger checks dynamic TTL (`press: 1.5s`, `hotkey: 1.5s`, `type: 2.0s`) and active window handle. | **Stale actions automatically rejected/cancelled** |
| **Speech Cut-Off During Urdu Pauses** | Fixed aggressive VAD cut off natural thinking pauses in bilingual Urdu/English speech. | Adaptive language-aware VAD: `300ms` for English, `400ms` for Urdu/Hindi (linguistic heuristic). | **Natural conversational flow without interruption** |

---

## 📋 Phased Implementation Plan (Ordered by Dependency & Priority)

```
[ Phase 1: Live Loop Isolation, Tool Timeout & 2KB Payload Cap ]   ── (Priority 1)
      │
[ Phase 2: Action Execution Ledger & Context-Aware Stale Discard ]  ── (Priority 2)
      │
[ Phase 3: Universal Window Verification & pywinauto UIA Control ]  ── (Priority 3)
      │
[ Phase 4: dxcam GPU Screen Capture, WDA Exclusion & ROI Cache ]    ── (Priority 4)
      │
[ Phase 5: Adaptive Language-Aware VAD & Audio Batching ]          ── (Priority 5)
      │
[ Phase 6: Verification, Stale-Action Benchmarks & Documentation ] ── (Priority 6)
```

---

---

## 🚨 Critical Edge Cases & Production Mitigations (14 Core Vulnerability Domains)

Following deep architectural analysis of real-world Windows environments, 14 critical edge case domains have been identified and engineered into the plan to guarantee a 100% robust, bug-free implementation:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
14 CRITICAL ARCHITECTURAL EDGE CASE DOMAINS                                                      
├───────────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ 1. Tool Timeout & 2KB Cap     │ 2. Chrome CDP & Multi-Tab       │ 3. pywinauto UIA & Elevated   │
│ • Zombie Process Tree Kill    │ • 200ms Active Probe & Port 9222│ • UIPI Admin Access Handling  │
│ • Structured Path Log Link    │ • Foreground Tab Target Match   │ • Canvas/Flutter Escalation   │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 4. dxcam & Screen Grab        │ 5. Win32 Display Affinity       │ 6. Adaptive VAD Code-Switch   │
│ • Lock Screen / UAC Fallback  │ • Recursive Child Popup WDA     │ • Bilingual Ur-En Pause Relax │
│ • Fullscreen DRM Handling     │ • Dynamic HWND Tracking         │ • 400ms Silence Guard Window  │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 7. Action Ledger & Scaling    │ 8. Audio Echo & Self-Interrupt  │ 9. Audio Device Disconnect    │
│ • Per-Window DPI Awareness    │ • AI Speech VAD Suppression     │ • WM_DEVICECHANGE Event Hook  │
│ • Job Supersede Race Shield   │ • Acoustic Echo Cancellation    │ • 100ms Stream Re-init        │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 10. Virtual Desktops          │ 11. Minimized / Tray Apps       │ 12. App Modal Dialog Block    │
│ • IVirtualDesktopManager      │ • IsIconic(hwnd) Detection      │ • Child IsModal Inspection    │
│ • Desktop Switch Guard        │ • SW_RESTORE Settle Delay       │ • Modal Button Auto-Focus     │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 13. Physical Input Collision  │ 14. Sticky Modifier Keys        │                               │
│ • GetCursorPos Target Verify  │ • Key Release Cleanup Hook      │                               │
│ • Coordinate Delta Validation │ • Mandatory finally: Release    │                               │
└───────────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

### 1. Tool Timeout & 2KB Truncation Shield (Phase 1)
- **Edge Case 1.1: Zombie Subprocesses on Timeout Cancellation**
  - **Risk:** If a tool (e.g. Playwright browser automation, web scraper, or CLI build command) times out at 10.0s and gets cancelled via Python `asyncio.CancelledError`, background child processes (`chrome.exe`, `node.exe`, `python.exe`) can remain running as zombie/orphan processes, consuming high CPU and RAM.
  - **Mitigation:** Tool worker implements a process-tree cancellation hook using Windows process group termination: `taskkill /F /T /PID {pid}` or `psutil.Process(pid).children(recursive=True)` kill tree, guaranteeing zero lingering orphan processes.
- **Edge Case 1.2: Truncation Breaking Critical JSON / Error Payloads**
  - **Risk:** Arbitrarily slicing a string at `MAX_RESPONSE_SIZE = 2048` can cut in the middle of a JSON object or obscure key error details.
  - **Mitigation:** Format outputs through a structured summarizer before truncation. If truncation occurs, cleanly close opened envelopes and append an explicit clickable log path: `"\n...[Truncated at 2KB | Full diagnostic log preserved at: logs/tool_outputs/{name}_{ts}.log]"`.

### 2. Chrome CDP & Profile Contention Edge Cases (Phase 1)
- **Edge Case 2.1: Chrome Running Without Remote Debugging Flag**
  - **Risk:** Most users launch Google Chrome normally without `--remote-debugging-port=9222`. If ZEZO rigidly waits on CDP, it will hang or fail.
  - **Mitigation:** Implement a non-blocking **200ms Quick Probe** via `aiohttp` or raw socket to `http://localhost:9222/json/version`. If connection is refused within 200ms, immediately pivot without blocking to dedicated profile `launch_persistent_context` at `.jarvis_profiles/chrome`.
- **Edge Case 2.2: Multi-Window & Multi-Tab Target Ambiguity**
  - **Risk:** If the user has multiple Chrome windows or 10+ tabs open, CDP could target a background or wrong window.
  - **Mitigation:** Inspect Windows active foreground window handle (`win32gui.GetForegroundWindow()`) and match window title with CDP page targets (`/json/list`) to interact with the exact focused tab the user is looking at.

### 3. pywinauto UIA & Windows Desktop Control Edge Cases (Phase 3)
- **Edge Case 3.1: Elevated (Run as Administrator) Windows & UIPI Barrier**
  - **Risk:** If an application (e.g., Task Manager, Registry Editor, Admin VS Code, Elevated PowerShell) is running as Administrator, Windows User Interface Privilege Isolation (UIPI) silently drops mouse clicks and blocks UIA tree access from non-admin processes.
  - **Mitigation:** Catch `pywinauto.findwindows.ElementNotFoundError` and Win32 `ERROR_ACCESS_DENIED`. Query the target process integrity level; if elevated and ZEZO is running non-elevated, gracefully return a clear spoken voice alert: *"Sir, this window is running with Administrator privileges. Please grant elevated access or run ZEZO as Administrator."*
- **Edge Case 3.2: Custom Canvas & Non-Native Controls (Figma, Flutter, Canvas, WebGL)**
  - **Risk:** Modern desktop tools like Figma, Flutter apps, Blender, and complex web canvases render controls to a single flat canvas and expose empty UIA node trees.
  - **Mitigation:** Standardize a strict 3-tier escalation ladder:
    1. **Tier 1 (UIA Tree):** Query native elements (<15ms).
    2. **Tier 2 (ROI RapidOCR):** If no native element found within 50ms, auto-escalate to regional GPU OCR (<200ms).
    3. **Tier 3 (Local/Cloud VLM):** If OCR text is ambiguous, escalate to visual coordinate grounding.

### 4. `dxcam` & Screen Capture Edge Cases (Phase 4)
- **Edge Case 4.1: Windows Lock Screen, Secure Desktop & UAC Invalidation**
  - **Risk:** When a UAC prompt appears or the system locks (Win+L), DirectX Desktop Duplication API immediately invalidates the desktop duplication context with `DXGI_ERROR_ACCESS_LOST` or `DXGI_ERROR_INVALID_CALL`.
  - **Mitigation:** Wrap `dxcam` capture in a safe retry/reinit handler. Upon catching `DXGI_ERROR_ACCESS_LOST`, fall back instantly to CPU-based `mss` screen grab (~12ms) and queue a background DXGI device recreate when the session returns to normal.
- **Edge Case 4.2: Fullscreen Exclusive Games & Hardware Protected Media (DRM)**
  - **Risk:** Fullscreen exclusive 3D games or protected DRM video playback (e.g. Netflix) can return pitch-black frames.
  - **Mitigation:** Detect uniform black/blank frame outputs and auto-switch to windowed GDI/Win32 PrintWindow API capture.

### 5. `WDA_EXCLUDEFROMCAPTURE` & Overlay Edge Cases (Phase 4)
- **Edge Case 5.1: Child Popups, Tooltips & Secondary HUD Overlays**
  - **Risk:** While the main ZEZO HUD window is excluded with `WDA_EXCLUDEFROMCAPTURE`, secondary transient child popups, modal confirmation dialogs, or notification bubbles might lack the flag and appear in screen captures.
  - **Mitigation:** Register a global window show hook or ensure every PyQt window/dialog/tooltip base class automatically executes `win32gui.SetWindowDisplayAffinity(int(widget.winId()), win32con.WDA_EXCLUDEFROMCAPTURE)` in its `showEvent`.

### 6. Adaptive Language-Aware VAD Edge Cases (Phase 5)
- **Edge Case 6.1: Fast Code-Switching & Bilingual Conversational Pauses (Urdu/Hindi + English)**
  - **Risk:** Bilingual speakers naturally mix languages mid-sentence (e.g., *"Open VS Code and yaar woh scraper file check karo"*). An aggressive 300ms English VAD window triggers mid-sentence right as the speaker pauses before the Urdu clause.
  - **Mitigation:** Implement real-time linguistic token checking. If the ongoing session or partial transcript contains bilingual markers (Roman Urdu/Hindi keywords or non-Latin glyphs), dynamically expand the silence window to `400ms` with high start sensitivity (`start_sensitivity = "high"`, `prefix_ms = 80`) to eliminate premature audio turn cutoffs.

### 7. Action Ledger & Multi-Monitor Scale Edge Cases (Phase 2 & 3)
- **Edge Case 7.1: Multi-Monitor Per-Monitor DPI Scale Drift (e.g. 100% vs 125% vs 150%)**
  - **Risk:** On multi-monitor setups with mixed display scaling, physical screen pixels differ from virtual desktop coordinates, leading to off-target mouse clicks.
  - **Mitigation:** Use `ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)` (Per-Monitor v2 DPI Aware) and query `ctypes.windll.user32.GetDpiForWindow(hwnd)` to normalize coordinate transforms before executing clicks or drags.
- **Edge Case 7.2: Fast Consecutive Spoken Commands (Race Conditions)**
  - **Risk:** User rapidly speaks back-to-back instructions (e.g., *"Close Paint, now open Notepad"*). Delayed actions from command 1 might execute after command 2 has already begun.
  - **Mitigation:** When a new user speech turn / tool job is dispatched, the `ActionLedger` marks all uncompleted actions of prior job IDs as `CANCELLED_SUPERSEDED`, guaranteeing stale commands cannot mutate state after a newer intent arrives.

### 8. Mic Self-Echo Feedback Loop & AI Speech Interruption (Phase 5)
- **Edge Case 8.1: AI Audio Bleed Triggering Self-Cutoff**
  - **Risk:** When ZEZO speaks via speakers/TTS, the microphone picks up AI output. VAD mistakenly identifies this audio bleed as human speech interruption, causing ZEZO to abruptly stop speaking mid-sentence.
  - **Mitigation:** Maintain `is_ai_speaking` state flag in `core/echo.py`. When active, dynamically elevate VAD energy thresholds by 2x or suppress VAD trigger events unless an explicit high-energy user voice pattern is recognized.

### 9. Hot-Plug Audio Device Disconnects (Phase 5)
- **Edge Case 9.1: Headset / Bluetooth Disconnect Mid-Stream**
  - **Risk:** Unplugging headphones or Bluetooth audio disconnects mid-turn causes `sounddevice` / `PyAudio` streams to throw host API exceptions (`PortAudioError`), hanging or crashing the audio loop.
  - **Mitigation:** Wrap mic input/output callbacks in a resilient reconnect handler. Hook Windows `WM_DEVICECHANGE` events to catch audio endpoint switches and seamlessly re-initialize PyAudio streams within 100ms.

### 10. Virtual Desktops Isolation Edge Cases (Phase 3)
- **Edge Case 10.1: Target Application Hosted on Non-Active Virtual Desktop**
  - **Risk:** If the user operates on Virtual Desktop 2 while ZEZO attempts to click or type into an application residing on Virtual Desktop 1, mouse input drops or causes unexpected OS desktop jumps.
  - **Mitigation:** Query `IVirtualDesktopManager::IsWindowOnCurrentVirtualDesktop(hwnd)`. If the target window resides on another desktop, execute a clean virtual desktop focus transition before dispatching UIA or mouse events.

### 11. System Tray Minimized & Hidden Window Edge Cases (Phase 3)
- **Edge Case 11.1: Target App Minimized to Tray (Hidden HWND)**
  - **Risk:** Applications like Discord, Spotify, or VS Code when minimized to the System Tray conceal their primary `HWND`, causing standard `GetForegroundWindow()` and UIA element lookups to fail.
  - **Mitigation:** Check `win32gui.IsIconic(hwnd)`. If minimized or hidden to tray, execute `win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)` followed by a 150ms settle delay prior to element interaction.

### 12. Application Modal Dialog Blockade Edge Cases (Phase 3)
- **Edge Case 12.1: Native Alert Boxes Blocking Main Window Controls**
  - **Risk:** When an application displays an unhandled modal popup (e.g. Notepad *"Do you want to save changes?"*), main window ribbon and input controls freeze, ignoring incoming UI actions.
  - **Mitigation:** Inspect UIA Tree for child elements with `IsModal == True`. If a modal dialog is detected, target actions directly at modal buttons (`Save`, `Don't Save`, `Cancel`) before attempting main window interactions.

### 13. Physical Mouse & Keyboard Input Collision (Phase 3)
- **Edge Case 13.1: User Physical Mouse Movement During AI Coordinate Drag/Click**
  - **Risk:** Physical mouse movement by the user during an automated AI click sequence alters coordinate vectors mid-execution, resulting in misclicks.
  - **Mitigation:** Validate `GetCursorPos()` against expected target coordinates immediately prior to click event. If a significant physical delta is detected, re-verify bounding box before input injection.

### 14. Sticky Synthetic Modifier Keys (`Ctrl`/`Alt`/`Shift`) (Phase 2 & 3)
- **Edge Case 14.1: Interrupted Hotkey Leaving Keys Stuck Down**
  - **Risk:** If a hotkey operation (e.g. `Ctrl+S`, `Alt+Tab`) is interrupted or cancelled midway, `Ctrl` or `Alt` keys can remain stuck in the `DOWN` state in Windows synthetic input buffer, corrupting subsequent user typing.
  - **Mitigation:** Enforce a mandatory `finally:` modifier key cleanup block in `actions/computer_control.py`:
    ```python
    finally:
        for key in ["ctrl", "alt", "shift", "win"]:
            keyboard.release(key)
    ```

---

### 🛡️ Phase 1: Live Loop Isolation, Tool Timeout & 2KB Payload Cap (Priority 1)

- [ ] **Task 1.1: Live Loop Dispatcher Decoupling & Process Tree Kill**
  - **File:** `main.py` (`_receive_audio`, `_execute_tool`), `core/task_manager.py`
  - Ensure the Live WebSocket receive loop **never** blocks on synchronous or long-running tool calls.
  - Dispatch all tool executions to an isolated background task queue with strict `asyncio.wait_for(..., timeout=10.0)` envelopes.
  - **Edge Case 1.1 Mitigation:** On timeout/cancellation, trigger process tree kill (`taskkill /F /T /PID` / `psutil`) to terminate orphan child subprocesses (e.g. headless browsers, runaway python scripts).
  - Receive loop returns immediate acknowledgment or completed result without starving keepalive pings.

- [ ] **Task 1.2: Tool Response Payload Truncation (`MAX_RESPONSE_SIZE = 2048`) & Structured Pathing**
  - **File:** `main.py` (`_execute_tool`)
  - Enforce payload limit on all tool results before constructing `types.FunctionResponse`:
    ```python
    MAX_RESPONSE_SIZE = 2048
    res_str = str(result)
    if len(res_str) > MAX_RESPONSE_SIZE:
        ts = int(time.time())
        log_path = Path("logs/tool_outputs") / f"{name}_{ts}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(res_str, encoding="utf-8")
        # Edge Case 1.2 Mitigation: Structured truncation with absolute file reference
        result = res_str[:MAX_RESPONSE_SIZE] + f"\n...[truncated, full output saved to {log_path.name}]"
    ```

- [ ] **Task 1.3: Chrome CDP Attachment & Profile Conflict Shield**
  - **File:** `actions/browser_control.py`, `actions/flight_finder.py`
  - Implement dual-mode browser connection with **Edge Case 2.1 & 2.2 Mitigations**:
    1. **Option A (CDP):** Run a non-blocking 200ms socket probe to `http://localhost:9222`. If open, attach via `playwright.chromium.connect_over_cdp("http://localhost:9222")` and resolve target tab by matching active foreground window title.
    2. **Option B (Dedicated Profile):** If probe fails/refused within 200ms, immediately launch persistent context on `.jarvis_profiles/chrome` with zero wait and zero profile lock contention.

- [ ] **Task 1.4: Non-Blocking Mic Streaming During Tool Execution**
  - **File:** `main.py` (`callback`, `_receive_audio`)
  - Remove destructive `out_queue` purging (`out_queue.get_nowait()`) on tool execution.
  - Keep mic streaming active so user can issue voice interrupts or follow-up instructions while tools execute.

---

### 📜 Phase 2: Action Execution Ledger & Context-Aware Stale Discard (Priority 2)

- [ ] **Task 2.1: Action Execution Ledger Registry & Supersede Cancellation**
  - **File:** `core/task_manager.py`, `actions/computer_control.py`
  - Implement an in-memory `ActionLedger` tracking every computer control request:
    - `action_id`: UUID string
    - `job_id`: Associated conversational task ID
    - `action_type`: `type` | `press` | `click` | `drag` | `hotkey` | `scroll`
    - `target_app`: Expected foreground window title or process name
    - `status`: `PENDING` | `EXECUTING` | `COMPLETED` | `CANCELLED` | `STALE`
    - `timestamp`: `time.monotonic()` dispatch timestamp
  - **Edge Case 7.2 Mitigation:** New incoming job ID immediately cancels all unexecuted actions of preceding jobs (`CANCELLED_SUPERSEDED`), preventing race conditions from back-to-back speech turns.

- [ ] **Task 2.2: Context-Aware Dynamic Stale Action Thresholds**
  - **File:** `actions/computer_control.py`
  - Check action age against action-specific TTL:
    ```python
    STALE_THRESHOLD_BY_ACTION = {
        "press": 1.5,     # Very fast keystrokes (Enter/Backspace/Esc)
        "hotkey": 1.5,    # Shortcuts (Ctrl+S, Ctrl+A)
        "type": 2.0,      # Text entry
        "click": 2.0,     # Single clicks
        "scroll": 2.5,    # Wheel events
        "drag": 3.0,      # Multi-coordinate drags
    }
    ```
  - If action exceeds its TTL or if the parent job was cancelled, discard with `[Ledger] ⚠️ Discarded stale action: {action_id}` and return immediately.

---

### 🖥️ Phase 3: Universal Window Verification & `pywinauto` UIA Control (Priority 3)

- [ ] **Task 3.1: Enforce Universal Foreground Verification & DPI Awareness**
  - **File:** `actions/computer_control.py`, `core/computer/windows_native.py`
  - Verify foreground window before executing any mutating action (`click`, `type`, `press`, `drag`, `scroll`, `hotkey`).
  - If target window is unfocused or minimized, use `pygetwindow` / `pywin32` to restore and activate it with a 150ms settle delay.
  - **Edge Case 7.1 Mitigation:** Query `GetDpiForWindow(hwnd)` and adjust coordinates according to per-monitor scale factors (e.g. 125% / 150%) before mouse input dispatch.
  - **Edge Case 3.1 Mitigation:** Detect UIPI / Administrator permission errors when sending input to elevated windows; report clear conversational warning to user.

- [ ] **Task 3.2: Native UI Automation (UIA) Integration via `pywinauto` & `comtypes`**
  - **File:** `actions/computer_control.py`, `core/computer/windows_native.py`
  - Implement direct UIA tree element lookup for standard Windows controls (e.g. Paint ribbon tools, Notepad tabs, VS Code menus):
    - Connect to target app via `pywinauto.Application(backend="uia")`.
    - Locate and click UI buttons directly by name / control type in **<15ms** without needing slow OCR.
  - **Edge Case 3.2 Mitigation:** When operating on flat canvas apps (Figma, WebGL, Flutter), automatically escalate from failed UIA (<15ms) to ROI RapidOCR (<200ms) to Visual AI grounding.

- [ ] **Task 3.3: Graceful Desktop Code Edit Auto-Routing**
  - **File:** `actions/kilo_agent.py`, `actions/code_helper.py`
  - When a user asks to edit a single script directly on `Desktop` (e.g. `wiki_scraper.py`), auto-route to `actions/code_helper.py` for direct AST insertion instead of rejecting with `Please point me at a specific subfolder`.

---

### 👁️ Phase 4: `dxcam` GPU Screen Capture, WDA Exclusion & 0ms ROI Hash Cache (Priority 4)

- [ ] **Task 4.1: GPU Desktop Duplication (`dxcam`) with `mss` Fallback**
  - **File:** `actions/screen_processor.py`
  - Implement DirectX GPU capture via `dxcam` (~5–8ms latency).
  - **Edge Case 4.1 & 4.2 Mitigations:** On `DXGI_ERROR_ACCESS_LOST` (lock screen / UAC secure desktop) or DRM black frame output, automatically fall back to CPU `mss` capture (~12ms) or Win32 `PrintWindow` API and reinitialize `dxcam` on session recovery.

- [ ] **Task 4.2: Win32 Self-Window Exclusion (`WDA_EXCLUDEFROMCAPTURE`) Across All HUD Windows**
  - **File:** `ui.py`, `actions/screen_processor.py`
  - Apply `win32gui.SetWindowDisplayAffinity(hwnd, win32con.WDA_EXCLUDEFROMCAPTURE)` to ZEZO's PyQt HUD, holographic overlays, and tooltips via `pywin32`.
  - **Edge Case 5.1 Mitigation:** Ensure all dynamically created child dialogs, modals, and popup widgets inherit or explicitly apply `WDA_EXCLUDEFROMCAPTURE` on display, ensuring 100% clean user-content capture.

- [ ] **Task 4.3: 0ms ROI Hash Caching & GPU Accelerated RapidOCR**
  - **File:** `core/computer/ocr_engine.py`, `actions/computer_control.py`
  - Hash ROI image bytes (MD5); return cached bounding boxes in **0ms** for unchanged application toolbars.
  - Run uncached OCR via `onnxruntime-gpu` / INT8 quantization (<200ms).

- [ ] **Task 4.4: Hardware-Aware Vision Tier (Local VLM vs Groq Cloud)**
  - **File:** `core/llm_router.py`, `actions/screen_processor.py`
  - If CUDA GPU available $\to$ Local `Moondream2` / `Qwen2-VL-2B` (<300ms, offline).
  - If CPU-only $\to$ Groq Cloud LPU / Gemini REST ladder (~250–400ms).

---

### ⚡ Phase 5: Adaptive Language-Aware VAD & Audio Batching (Priority 5)

- [ ] **Task 5.1: Adaptive Linguistic VAD Tuning & Bilingual Code-Switching Guard**
  - **File:** `config/api_keys.json`, `memory/config_manager.py`, `main.py`
  - Implement heuristic language detection from recent conversation tokens:
    - English: `silence_ms = 300`
    - Urdu / Hindi / Mixed (detected via keywords `yaar`, `acha`, `karo`, `dekho`, or script): `silence_ms = 400`
  - **Edge Case 6.1 Mitigation:** Automatically relax silence window to 400ms whenever bilingual markers or code-switching are encountered, preventing cutoffs during natural bilingual thinking pauses.
  - Sensitivity: `start_sensitivity = "high"`, `end_sensitivity = "high"`, `prefix_ms = 80`.

- [ ] **Task 5.2: Audio Output Batching Calibration**
  - **File:** `main.py` (`_play_audio`)
  - Calibrate playback batch size (`2400` bytes / ~50ms vs `4800` bytes / ~100ms) to eliminate thread-pool latency while preventing buffer underruns.

- [ ] **Task 5.3: Context-Aware Telemetry Alert Suppressor**
  - **File:** `main.py` (`_run_system_monitor`), `actions/system_monitor.py`
  - Suppress proactive audio alerts (e.g. CPU 100%) during active conversations (if user spoke in last 15s). Display alerts passively in the HUD.

---

### 🧪 Phase 6: Verification, Stale-Action Benchmarks & Documentation (Priority 6)

- [ ] **Layer 1: Static Architecture & Tool Schema Audit**
  - Run `py_compile` across all modified core engines and actions.
  - Confirm all 24 discovered actions pass signature and schema verification.

- [ ] **Layer 2: Real Runtime Benchmarks**
  - **Benchmark 1 (Turnaround):** Spoken prompt $\to$ First audio packet $<600\text{ms}$.
  - **Benchmark 2 (UIA vs OCR):** `pywinauto` button click $<15\text{ms}$; 0ms ROI cache hit; uncached OCR $<200\text{ms}$.
  - **Benchmark 3 (10s Shield & 2KB Cap):** Trigger a 15s dummy tool + 50KB payload $\to$ Truncated to 2KB and finished within 10s $\to$ Live WebSocket stays 100% connected with zero 1011 errors.
  - **Benchmark 4 (Stale Action Test):**
    `Open Notepad → type → close Notepad → delayed keypress arrives`  
    **Expected Result:** `Delayed keypress = REJECTED by ActionLedger`.
  - **Benchmark 5 (Zombie Process Kill Test):** Cancel long-running tool at 10s $\to$ verify `taskkill /F /T /PID` leaves 0 background orphan subprocesses.
  - **Benchmark 6 (Multi-Monitor DPI & UIPI Test):** Verify coordinate accuracy on 125% DPI secondary monitor and verify graceful UIPI warning on elevated windows.

- [ ] **Layer 3: Regression Suite & Documentation Synchronization**
  - Run full test suite (21+ unit and UIA/OCR regression tests).
  - Update `docs/AUDIO_SYSTEM.md`, `docs/VOICE_PIPELINE.md`, `docs/TOOLS.md`, and record in `LEARNING_JOURNAL.md`.

---

## 🛡️ Risk Assessment & Edge-Case Mitigation Matrix

| Potential Risk / Edge Case | Likelihood | Impact | Architectural Mitigation |
| :--- | :--- | :--- | :--- |
| **Zombie processes on 10s tool timeout** | Medium | High | Cancellation hook triggers tree termination (`taskkill /F /T /PID` or `psutil` recursive kill). |
| **Truncation corrupts JSON/logs** | Medium | Medium | Output formatted cleanly; full logs always written to `logs/tool_outputs/{name}_{ts}.log` with structured fallback. |
| **Chrome not on `:9222` debug port** | High | High | 200ms quick socket probe; if port refused, instantly pivot to dedicated `.jarvis_profiles/chrome` context. |
| **Elevated window blocks clicks (UIPI)** | Medium | High | Catch `ERROR_ACCESS_DENIED` / UIA failure; check process token and notify user via clear voice alert. |
| **Non-standard Canvas apps (Figma/Flutter)**| Medium | Medium | Tiered escalation: UIA Fail (<15ms) $\to$ ROI RapidOCR (<200ms) $\to$ Visual AI grounding. |
| **`dxcam` DXGI lost on Lock / UAC screen** | Medium | Medium | Auto-catch `DXGI_ERROR_ACCESS_LOST`, instantly switch to `mss` CPU grab, and reinit DXGI on session restore. |
| **Secondary HUD popups show in captures** | Low | Low | Apply `WDA_EXCLUDEFROMCAPTURE` across all window classes and dynamic popup/tooltip dialogs. |
| **Bilingual code-switch mid-sentence cut** | High | High | Dynamic language detection: relax silence window to 400ms when Urdu/Hindi tokens or code-switching are detected. |
| **Multi-monitor DPI scaling click offset** | Medium | High | Per-Monitor v2 DPI awareness (`SetProcessDpiAwarenessContext(-4)`) + `GetDpiForWindow(hwnd)` coordinate transforms. |
| **Rapid consecutive voice commands collision**| Medium | Medium | Action Ledger cancels pending actions of older jobs upon arrival of new job (`CANCELLED_SUPERSEDED`). |
| **Mic self-echo triggering AI self-cutoff** | High | High | `is_ai_speaking` state flag suppresses VAD or elevates energy threshold 2x during active TTS playback. |
| **Headset/Bluetooth disconnect mid-stream** | Medium | High | Hook Windows `WM_DEVICECHANGE` events to re-initialize PyAudio streams seamlessly within 100ms. |
| **Target app on secondary Virtual Desktop** | Medium | Medium | `IVirtualDesktopManager::IsWindowOnCurrentVirtualDesktop` check triggers clean desktop switch before input. |
| **System Tray minimized / hidden HWND** | High | Medium | `IsIconic(hwnd)` detection invokes `ShowWindow(SW_RESTORE)` with a 150ms settle delay before interaction. |
| **App Modal Dialog blocking main controls** | Medium | High | UIA `IsModal == True` check targets modal buttons (`Save`/`Cancel`) before attempting main ribbon actions. |
| **User physical mouse collision mid-click** | Low | Medium | Re-verify `GetCursorPos()` target coordinates immediately prior to click event injection. |
| **Interrupted hotkey leaving modifiers stuck**| High | Medium | Enforce mandatory `finally:` cleanup loop calling `keyboard.release(key)` for `ctrl`, `alt`, `shift`, `win`. |

