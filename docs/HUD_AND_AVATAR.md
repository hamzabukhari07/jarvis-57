# ZEZO OS — Tactical HUD & Workspace Architecture

## Overview

The HUD (Heads-Up Display) is built with **PyQt6 QWebEngineView** hosting an ultra-responsive, GPU-accelerated tactical cockpit interface (`frontend/index.html`).

**Files**: `ui.py`, `frontend/index.html`, `frontend/style.css`, `frontend/js/ui.js`

## Tactical Cockpit Architecture

### Master 3-Column Workspace Layout

| Column | Components | Purpose |
|---|---|---|
| **Left Column** | `01 · Hardware Telemetry`<br>`02 · Autonomous Task Queue` | Live CPU, RAM, GPU, and Network meters + Active agent task progress |
| **Center Column** | `Fluid Vortex Core`<br>`Unified Command Dock`<br>`03 · Live Display Canvas` | Visual state indicator, Mic/State/Stop/Power controls, and Expandable Multi-View Inspector |
| **Right Column** | `04 · Activity Log Stream`<br>`Context Actions` | Live conversational exchanges, system actions, and clipboard intelligence |

---

## Center Display & Fluid Vortex Core

The center panel features the Fluid Vortex core (`frontend/download.gif`) and the **Unified Command Dock**:
1. **Mic Mute / Unmute**: Hardware-level mic toggle.
2. **2x3 Phosphor Matrix State Badge**: Real-time standby, listening, thinking, speaking status indicator.
3. **Emergency Stop Button**: Instant abort and task interruption.
4. **Sleep & Power Mode**: Instant voice loop pause and sleep mode.

---

## Multi-File Upload & Queue System

**Files**: `ui.py` — `FileDropZone`, `_UploadedFilesBar`, `_DropCanvas`

### File Drop Zone (`FileDropZone`)
- **Visuals**: 100px dashed bounding box with marching-ants animation during hover/drag.
- **Multi-File Support**: Accepts up to 10 files simultaneously via OS drag-and-drop or multi-select file dialog (`QFileDialog.getOpenFileNames`).
- **Layout Bands**:
  - **Row 1 (Y: 12–34px)**: Up to 6 category emoji icons (`🖼`, `🎬`, `🎵`, `📄`, `📝`, `💻`, `📦`, `🔧`) with `+N` overflow counter.
  - **Row 2 (Y: 40–60px)**: Bold header (`N files loaded`).
  - **Row 3 (Y: 64–82px)**: Monospace summary (`X MB total · Click to add more`).
  - **Top-Right (Y: 8–28px, X: W-28px)**: Constrained `(✕)` clear button click box.
- **Signals**: `file_selected = pyqtSignal(list)` emits full list of paths.

### Upload Queue Bar (`_UploadedFilesBar`)
- **Scrollable Area**: 120px max height, auto-collapsing when empty.
- **Per-File Rows**:
  - Category icon with custom color tint.
  - Elided filename (up to 25 chars + `...`).
  - Metadata tag (`{size} · {EXT}`).
  - Individual `✕` remove button connected to `_on_remove(path)`.
- **Batch Actions**:
  - **📋 SELECT ALL**: Visual multi-select highlight.
  - **🧹 CLEAR ALL**: Clears entire upload queue.
  - **→ SEND ALL**: Dispatches `[FILES_UPLOADED]` command payload to assistant.

---

## Activity Log & Log Console

**Files**: `ui.py` — `LogWidget`, `LogConsoleOverlay`; `core/log_bus.py`

- **Copy Bar**: 24px button strip above activity log with `📋 COPY ALL` (to system clipboard), `🧹 CLEAR` (wipes widget + `log_bus`), `▼ FOLLOW` toggle, and live line count badge.
- **Extended Context Menu**: Standard right-click menu supplemented with `Copy All (Activity Log)` and `Clear Activity Log`.
- **Log Console Overlay (`Ctrl+L`)**: Global debug overlay with level filtering (`ALL`, `INFO`, `WARN`, `ERROR`), pause stream, copy, export, and search.
- **Secret Redaction**: Integrated with `core/log_bus.py` to ensure API keys (`AQ.*`, `AIzaSy*`), bearer tokens, and credentials are scrubbed before reaching any UI sink.
- **Web Frontend Append Semantics (`frontend/index.html`)**: Every activity-stream / log-console card **must** be appended with `insertAdjacentHTML('beforeend', html)` — never `container.innerHTML += html`. Assigning `innerHTML +=` serializes and re-parses the whole container, destroying and recreating every existing card; since `.stream-msg` carries an entrance animation, each new log line replayed the animation on all previous cards and the panel visibly blinked on every backend log. `insertAdjacentHTML('beforeend')` parses only the new fragment and leaves existing nodes untouched.

---

## Task Inspector & Task Queue

**Files**: `ui.py` — `TaskQueueWidget`, `TaskMatrixDrawer`, `_inspect_task_by_id`; `core/task_manager.py`

- **Task Queue Widget**: Real-time slide-out / sidebar cards categorized by `● RUNNING`, `○ QUEUED`, and `✓ DONE`.
- **Task Inspector Overlay**:
  - Displays unified agent badge (`⚡ ZEZO CODER`), task ID, PID, elapsed time, and live progress bar.
  - **100% Saturation on Completion**: When a task reaches DONE status, the progress bar and percentage display instantly saturate to full 100% width.
  - **Task Cancellation**: Active tasks feature a red `✕ CANCEL` button triggering immediate child process tree termination via `task_manager.cancel()`.
  - **ANSI Cleansing**: Status strings and log tails are automatically stripped of raw terminal escape sequences (`\x1b[...]`) via `strip_ansi()` for clean readability.
  - **Task Navigation**: Switch between multiple concurrent/queued tasks with `[TAB]`, `◀`, `▶`.
- **Slide-Out Telemetry Drawer (`TaskMatrixDrawer`)**:
  - Live hardware telemetry (Engine, Model, PID, Job Object limits, CPU Affinity, Child Processes, Timestamps).
  - Quick action buttons: `[🌐 PREVIEW]` (opens browser on `index.html`), `[📁 OPEN FOLDER]` (opens OS explorer), `[✕ CANCEL]`, `[🔍 INSPECT]`, and `[📜 FULL LOG]`.

---

## State Indicators

| State | Phosphor Matrix Badge |
|---|---|
| **STANDBY / READY** | Minimal pulse pattern |
| **LISTENING** | Reactive waveform bars listening to user audio input |
| **THINKING** | Animated scanning sweep |
| **SPEAKING** | Active speech modulation indicator |
| **SLEEPING** | Low-power dormant indicator |

---

## Theming

```javascript
// Accent color drives the entire palette:
applyAccentColor(accentHex) // Retints active borders, badges, progress bars, and glows
```

---

## Summary

```
UI: PyQt6 QWebEngineView + HTML5/CSS/JS Tactical Workspace
Rendering: Chromium GPU-accelerated compositing
Centerpiece: Fluid Vortex Core + Unified Command Dock
Upload: Multi-file drag-and-drop + UploadedFilesBar queue
Activity Log: Copy Bar + Log Bus ring buffer + Secret Redaction
Task Inspector: Live PID telemetry + Cancel action + ANSI stripping
States: Standby, Listening, Thinking, Speaking, Sleeping
Theming: Hex / Preset accent color palette
```
HUD styles: Face or Reactor core
Theming: Hue wheel accent color
```

---

## Web HUD Rendering, CPU Budget & Single Instance (ADR-049 / ADR-056)

Since ADR-049 the desktop HUD is a web app in a `QWebEngineView`. The HUD was
consuming ~2 CPU cores while merely idling. The cost was split between:

- the **full-window Three.js WebGL globe** (`#webgl-bg`, 2000 particles, an
  unconditional `requestAnimationFrame` loop) driving the renderer process, and
- backend polling on the Qt main thread (`psutil.net_io_counters()` ~15 ms every
  500 ms; a WMI CPU-temperature query ~30–160 ms every 10 s) plus a full
  `QApplication.exec()`/IPC load.

### Changes in place

| Change | Purpose |
|--------|---------|
| Three.js globe **fully removed** (script tag, `#webgl-bg` div+CSS, `initGlobe()`, `_updateGlobeAccent`) | eliminates the single heaviest continuous render loop |
| `window._zezoAnimActive` gate + ~30 FPS cap + `visibilitychange` pause on the remaining `initMatrixIcon()` loop | keep the small dot-matrix icon cheap |
| `QApplication.setAttribute(AA_ShareOpenGLContexts)` **before** `QtWebEngineWidgets` import (`ui.py`) | let Chromium start hardware GPU compositing instead of software (SwiftShader) fallback |
| `QTWEBENGINE_CHROMIUM_FLAGS="--ignore-gpu-blocklist --enable-gpu-rasterization"` (setdefault, `ui.py`) | Windows/Optimus laptops blocklist QtWebEngine's GPU far too eagerly |
| `_poll_telemetry` refreshes `net_io_counters()` only every 4th tick (2 s) and caches it | stops a ~15 ms UI-thread block every 500 ms |
| `_poll_tasks` interval 300 ms → 1000 ms | the HUD cannot show a change 3×/second |
| `_get_cpu_temp()` caches its WMI read for 60 s; `_get_gpu_usage()` initialises NVML once | removes repeated slow WMI/NVML setup |
| Single-instance guard (`QLockFile`) at the top of `main()` | a second launch exits instead of doubling every loop, port and audio device (measured ~4 cores for two copies) |

Measured on the author's machine (idle, one instance): `python main.py`
~126% → ~103%, `QtWebEngineProcess` renderer ~81% → ~62%, and duplicate
instances are now impossible. See `LEARNING_JOURNAL.md` for the profile data.

> `_zezoPauseAnim(dragging)` on `dragenter`/`dragover`/`dragend`/`drop`/`dragleave`
> is still wired and remains the fix for the original ADR-056
> `updateDragAction was not called within 3000 ms` drag lag.

---

## Live Display Canvas & Badge Overflow Protection

The Live Display Canvas (`#inspector-frame`) in `frontend/index.html` displays outputs from multi-agent tasks, web searches, comparisons, and document intel.

### Badge Formatting & Overflow Guarantees
- `.badge` is styled with `white-space: nowrap; max-width: 100%; line-height: 1.3;` to prevent text from breaking and wrapping into multiple rows inside header bars.
- `#canvas-context-badge` specifies `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; flex-shrink: 1;`.
- `window.setCanvasContent()` maps query titles to clean category badges (`COMPARISON`, `WEB SEARCH`, `DOCUMENT INTEL`, etc.) and sets the `title` attribute for tooltip query inspection on hover. Uncategorized long titles are cleanly truncated with an ellipsis (`…`) so the header layout never expands vertically.