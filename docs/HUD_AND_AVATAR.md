# JARVIS — HUD and Avatar Architecture

## Overview

The HUD (Heads-Up Display) is built with **PyQt6** and features a holographic animated avatar rendered entirely in software using **QPainter**.

**File**: `ui.py` (5438 lines), `core/avatar.py` (715 lines), `core/avatar_mesh.py` (351 lines)

## PyQt6 Architecture

### Main Window

```python
class JarvisUI(QMainWindow):
    # Left panel: Activity log
    # Center: HUD content (avatar or reactor core)
    # Right panel: Settings drawer
    # Bottom: Content panel (scrollable web results, news, search)
```

### Layout

| Component | Size | Purpose |
|-----------|------|---------|
| Left panel | 148px | Activity log |
| Center | Variable | Avatar/Reactor core |
| Right panel | 340px | Settings drawer |
| Window | 980x700 default | Main HUD |
| Min size | 820x580 | Minimum window size |

### Widgets

- **QMainWindow** — top-level window
- **QSplitter** — panel layout
- **QTextEdit** — activity log
- **QScrollArea** — content panel
- **QProgressBar** — system metrics
- **QComboBox** — voice, device selectors
- **QPushButton** — various controls
- **QLineEdit** — text input
- **QLabel** — status indicators
- **QStackedWidget** — settings pages
- **QShortcut** — keyboard shortcuts

## Avatar Rendering

> **Web frontend note (`frontend/index.html`).** The Fluid Vortex avatar is an animated GIF (`frontend/download.gif`, 600×600, 90 frames) rendered at `.vortex-gif` inside `#avatar-frame .frame-inner`, which uses `backdrop-filter: blur(12px)` over a pure-black background. **Do not add `mix-blend-mode` to this animated element.** `screen` over black is a pixel-identical no-op (verified), but blending an animated layer inside a `backdrop-filter` ancestor forces a per-frame backdrop read and makes the QtWebEngine compositor flicker. Any per-frame animation inside a `backdrop-filter` subtree should likewise be avoided.

### Face Model

**File**: `core/face_model.obj` (25 KB)
- **Source**: MediaPipe canonical face model
- **License**: Apache 2.0
- **Vertices**: 468
- **Triangles**: 898
- **Features**: Eyelids, nostrils, lips, cheekbones (measured anatomy)

### Avatar Mesh

**File**: `core/avatar_mesh.py`

The mesh builds the head around the face model:
- **Cranium**: Swept back over an ellipsoid (closed at occiput)
- **Neck**: Tapering tube fading out
- **Vertex normals**: For lighting
- **Jaw rig**: Pivot between ears, max 0.115 radians drop
- **Landmark rings**: Eye, brow, lip indices for animation

### Renderer

**File**: `core/avatar.py`

```python
# Everything rendered with QPainter
# No OpenGL, no shaders, no GPU driver
# 25 KB asset + formulas

# Key animation systems:
# - Eyes: Saccades between fixation points
# - Brows: Track the phrase (not syllable)
# - Mouth: Viseme-driven (see core/viseme.py)
# - Jaw: Driven by audio openness
# - Head: Nod on stressed syllables
# - Blinking: Natural rhythm
```

### Animation Timing

```python
_TAU_OPEN = 0.022     # Jaw dropping toward vowel
_TAU_SHUT = 0.012     # Lips closing on consonant
_TAU_REST = 0.055     # Settling back to rest
_TAU_SHAPE = 0.018    # Viseme openness following schedule

# Frame-rate independent via _rate(dt, tau):
#   return 1.0 - math.exp(-dt / tau)
```

### Brow and Eye Animation

```python
_BROW_LIFT = 0.14  # Derived from anatomy (brow-to-eye gap * 0.33 * 0.5 rig weight)
# Brows ride the PHRASE, not the syllable
# Slow asymmetry between left and right
# Eyes make real saccades between fixation points
# More saccades while speaking
```

## Lip-Sync System

**Files**: `core/viseme.py`, `main.py:_pcm_visemes()`

The mouth animation uses a **dual-source fusion**:
1. **Audio formants** (20ms slices from FFT) → openness and width
2. **Transcript** (VisemeStream) → which mouth shape

```python
# Blend ratio:
o = 0.72 * t_open + 0.28 * a_open  # Text leads, audio corrects
w = 0.78 * t_wide + 0.22 * a_wide
```

50 mouth shapes per second.

## VisemeStream

**File**: `core/viseme.py`

```python
class VisemeStream:
    def feed_text(text: str):
        # Parse text → list of (viseme, duration_weight) pairs
        # Queue them for playback
    
    def frames(audio, hop: float):
        # For each audio frame, advance through the queue
        # Blend audio shape with transcript shape
        # Return (level, openness, width) for avatar
```

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

| State | Avatar Behavior |
|-------|-----------------|
| **Listening** | Eyes meet yours, mouth ready |
| **Thinking** | Looks away, brows down, blinking suppressed |
| **Speaking** | Lip-sync active, eyes saccade, head nods |
| **Sleeping** | Eyes closed (lids fall) |
| **Content available** | Glances down at content panel |

## Two HUD Styles

1. **Face** (default): The animated holographic head
2. **Core**: A reactor core — gauge ring, three arcs, spectrum driven by audio

```python
# Switch via config:
get_hud_style() → "face" or "core"
save_hud_style(style)
```

Both render in the same QPainter, same cost.

## Theming

```python
# Accent color drives the entire palette:
apply_ui_accent(accent_hex)  # hue shift, brightness/saturation preserved
# Avatar retints with it
# All HUD elements pick up new colors
```

## Rendering Loop

```python
# PyQt6 paintEvent → QPainter
# Frame rate: 60 Hz normal, 30 Hz when idle, 20 Hz when minimized
# Avatar animation steps independently of frame rate
# Time constants (TAU_*) ensure same speed at any FPS
```

## Summary

```
UI: PyQt6 QMainWindow, 980x700 default
Rendering: QPainter only (no GPU)
Face: MediaPipe canonical model (468 vertices, Apache 2.0)
Animations: Eyes, brows, mouth, jaw, head, blink
Lip-sync: 50 shapes/sec, dual-source fusion
Upload: Multi-file drag-and-drop + UploadedFilesBar queue
Activity Log: Copy Bar + Log Bus ring buffer + Redaction
Task Inspector: Live PID telemetry + Cancel action + ANSI stripping
States: Listening, Thinking, Speaking, Sleeping
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