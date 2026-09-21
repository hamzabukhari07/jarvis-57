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