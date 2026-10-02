# 🖥️ ZEZO — Frontend Structure Reference

> **Purpose:** Complete DOM structure, element IDs, modal registry, CSS class directory, and JavaScript function reference. AI agents must consult this document before modifying `frontend/index.html`, `frontend/style.css`, or `frontend/js/ui.js`.

---

## 1. Top-Level Layout (`frontend/index.html`)

### Body Structure
- `<div class="container-lines">` — Background grid corner accents
- `<div class="app-shell">` — Outer application wrapper (`height: 100vh; width: 100vw; display: flex; flex-direction: column; overflow: hidden;`)
  - `<header class="top-navbar">` — Fixed top bar (`height: 48px; position: relative; z-index: 100;`)
  - `<main class="workspace-grid">` — Master 3-column tactical workspace (`height: calc(100vh - 58px); display: grid; grid-template-columns: minmax(210px, 250px) minmax(0, 1fr) minmax(260px, 300px);`)
    - `<aside>` (Left Column) — Hardware Telemetry (Panel 01) & Autonomous Task Queue (Panel 02)
    - `<section class="center-column-wrapper" id="center-column">` (Center Column) — Avatar Frame + Drag Splitter + Live Display Canvas / Inspector (Panel 03)
    - `<aside>` (Right Column) — Payload Ingestion (Panel 04) & Activity Log / Prompt Input (Panel 05)

### Top Navbar Elements (`.top-navbar`)
- **Left Actions (`.header-left-actions`):**
  - `#settings-trigger-btn` — Button (`onclick="openModal('settings-modal')"`, `title="Full Settings & Quick Controls"`)
  - `button` — Log Console Button (`onclick="openModal('log-modal')"`, `title="Backend Log Console (Ctrl+L)"`)
  - `button` — Task Matrix Button (`onclick="openModal('task-modal')"`, `title="Task Matrix & Registry"`)
  - `button` — QR Remote Button (`onclick="openModal('qr-modal')"`, `title="Mobile Remote Control & Key"`)
- **Center Branding (`.header-center-branding`):**
  - `.header-brand-title` — "ZEZO" brand text
  - `.header-brand-divider` — Dynamic accent underbar
- **Right Digital Clock (`.header-right-clock`):**
  - `#header-clock-time` — Monospace time readout (e.g. `18:50:38`)
  - `#header-clock-date` — Date readout (e.g. `MON 21 SEP 2026`)

---

## 2. Left Column — Telemetry & Task Queue

### Panel 01 — Hardware Telemetry
- **Section Label:** `01 · Hardware Telemetry`
- **CPU Core Load:** `#val_cpu` (percentage text) & `#bar_cpu` (progress fill track)
- **RAM Usage:** `#val_mem` (percentage text) & `#bar_mem` (progress fill track)
- **System GPU:** `#val_gpu` (percentage text) & `#bar_gpu` (progress fill track)
- **Net Bandwidth:** `#val_net` (throughput text) & `#bar_net` (progress fill track)

### Panel 02 — Autonomous Task Queue
- **Header:** `02 · Task Queue`
- **Active Badge:** `#task-count-badge` (e.g. `0 ACTIVE`)
- **Task List Container:** `#task-queue-list` — Dynamic list rendered via `renderTasks(taskList)` containing task cards (`#task-card-{id}`) with subtask trees and live progress bars.

---

## 3. Center Column — Avatar & Live Display Canvas

### Panel — Avatar Frame (`#avatar-frame`)
- **Container:** `#avatar-container`
- **Fluid Vortex Avatar:** `#vortex-gif` (`<img src="download.gif" class="vortex-gif" id="vortex-gif">`)
- **Unified Avatar Command Dock (`#avatar-command-dock`):**
  - **Microphone Control:** `#dock-mic-btn`, `#dock-mic-icon`, `#dock-mic-label` (`onclick="toggleMic()"`)
  - **State Phosphor Matrix Badge (`#dock-state-badge`):**
    - `#state-matrix-icon` — 2x3 Canvas (`width="16" height="18"`)
    - `#state-heading-text` — State label (`Standby...`, `Listening...`, `Thinking...`, `Speaking...`, `Executing...`, `Muted...`, `Halted...`)
  - **Emergency Halt:** `#dock-stop-btn` (`onclick="emergencyStop()"`)
  - **Power / Sleep Toggle:** `#dock-power-btn`, `#dock-power-icon`, `#dock-power-label` (`onclick="togglePowerSleep()"`)

### Drag Splitter
- `#drag-splitter` — Interactive splitter bar with `.splitter-grip` to resize avatar viewport vs inspector canvas.

### Panel 03 — Live Display Canvas (`#inspector-frame`)
- **Frame Header:** `#inspector-header` (`03 · LIVE DISPLAY CANVAS`)
- **Context Badge:** `#canvas-context-badge` — Dynamic context badge (e.g. `ZEZO CODER`, `WEB EXTRACTION`)
- **Header Actions:**
  - Copy Button (`onclick="copyCanvasContent(this)"`)
  - Clear Button (`onclick="clearCanvasContent()"`)
  - Expand/Fullscreen Focus Button: `#canvas-expand-btn` (`onclick="toggleCanvasExpand()"`)
- **Body Container:** `#inspector-body`
  - **Empty State:** `#canvas-empty-state` (Autonomous Execution Engine Ready placeholder)
  - **Active Content Wrapper:** `#canvas-active-content`
    - `#canvas-content-text` — Pre-wrap monospace output for code, web scraping, diffs, and tool results.

---

## 4. Right Column — Payload & Activity

### Panel 04 — Payload Ingestion
- **Section Label:** `04 · Payload Ingestion`
- **Hidden Inputs:**
  - `#payload-file-input` — `<input type="file" multiple>` (`onchange="uploadPayloadFiles(this.files)"`)
  - `#payload-folder-input` — `<input type="file" webkitdirectory directory multiple>` (`onchange="uploadPayloadFolder(this.files)"`)
- **Dropzone Area:** `#dropzone-box` (Drag and drop target)
- **Ingested Files Container:** `#payload-items-container`
  - `#payload-count-label` (e.g. `INGESTED PAYLOADS (0)`)
  - `#payload-list-items` (Scrollable list of files with remove actions)

### Panel 05 — Activity Log & Command Bar
- **Section Label:** `05 · Activity Log`
- **Header Actions:**
  - `#copy-stream-btn` (`onclick="copyEntireStream(this)"`)
  - Clear Button (`onclick="clearStream()"`)
- **Activity Log Stream:** `#stream-box` (Container for `.stream-msg` user/assistant cards)
- **Command Input Bar (`.command-input-container`):**
  - `#user-input` — `<input type="text" class="command-input-field">` (`onkeydown="if(event.key==='Enter') executeCommand()"`)
  - `.command-send-btn` — Action button (`onclick="executeCommand()"`)

---

## 5. Modal Registry

All modals use standard `.modal-overlay` structure (`background: rgba(0,0,0,0.92); contain: layout paint style;`) and `.modal-panel.frame` (`will-change: transform; transform: translateZ(0);`).

| Modal ID | Trigger / Opened By | Purpose | Key Inner Element IDs | Close Action |
| :--- | :--- | :--- | :--- | :--- |
| `settings-modal` | `#settings-trigger-btn` | Full Desktop Settings, Toggles & Quick Controls Hub | `#drawer-keys-btn`, `#drawer-autostart-btn`, `#autostart-switch`, `#drawer-brief-btn`, `#brief-mode-switch`, `#drawer-wake-btn`, `#wake-word-switch`, `#drawer-ptt-btn`, `#ptt-switch`, `#drawer-fallback-btn`, `#fallback-switch`, `#drawer-hud-btn`, `#hud-style-label`, `#color-dot-*` | `closeModal('settings-modal')` |
| `log-modal` | Top navbar log button / `Ctrl+L` | Real-time Python Log Bus terminal viewer | `#log-stats-badge`, `#log-follow-btn`, `#log-pause-btn`, `#log-search-filter`, `#log-level-filter`, `#log-source-filter`, `#log-modal-buffer` | `closeModal('log-modal')` |
| `task-modal` | Top navbar task button | Autonomous Process Registry & KPI matrix | `#task-modal-running-count`, `#task-modal-queued-count`, `#task-modal-done-count`, `#task-modal-list` | `closeModal('task-modal')` |
| `task-detail-modal` | Card click on `#task-queue-list` or `#task-modal-list` | Deep subagent telemetry, parameters & logs | `#task-detail-badge`, `#task-detail-id`, `#task-detail-title`, `#task-detail-target`, `#task-detail-status-badge`, `#task-detail-progress-bar`, `#task-detail-engine`, `#task-detail-model`, `#task-detail-pid`, `#task-detail-started`, `#task-detail-elapsed`, `#task-detail-log-stream`, `#task-detail-cancel-btn`, `#btn-copy-task-logs` | `closeModal('task-detail-modal')` |
| `qr-modal` | Top navbar QR button / `#settings-modal` | LAN Mobile Remote Control Gateway & OTP Key | `#remote-url-display`, `#remote-qr-img`, `#pairing-key-display`, `#copy-pairing-key-btn`, `#remote-timer-value` | `closeModal('qr-modal')` |
| `api-keys-modal` | `#settings-modal` / `#pipeline-modal` | Secure API Key Credential Manager (Gemini, Groq, ElevenLabs) | `#keys-gemini-input`, `#keys-gemini-status`, `#keys-groq-input`, `#keys-groq-status`, `#keys-elevenlabs-input`, `#keys-elevenlabs-status`, `#btn-save-api-keys` | `closeModal('api-keys-modal')` |
| `customise-modal` | `#settings-modal` | Persona Name, Language, Voice Persona & Kokoro Fallback | `#customise-asst-name`, `#customise-voice-select`, `#btn-preview-voice`, `#customise-lang-select`, `#customise-fallback-switch`, `#customise-fallback-voice-select` | `closeModal('customise-modal')` |
| `pipeline-modal` | `#settings-modal` | Voice Engine Mode (Live vs. Cascade) & STT/LLM/TTS selectors | `name="pipeline-mode"`, `#pipeline-fallback-switch`, `#cascade-engines-section`, `#stt-engine-select`, `#llm-engine-select`, `#tts-engine-select`, `#tts-voice-select`, `#pipeline-gemini-status-tag`, `#pipeline-groq-status-tag`, `#pipeline-elevenlabs-status-tag` | `closeModal('pipeline-modal')` |
| `audio-modal` | `#settings-modal` | Audio Input/Output Endpoint selection & Mic bleed monitor | `#audio-input-select`, `#audio-mic-bar`, `#audio-mic-status`, `#audio-output-select`, `#audio-echo-state` | `closeModal('audio-modal')` |
| `memory-modal` | `#settings-modal` | SQLite FTS5 Memory Engine & BM25 search interface | Search input & scrollable memory history list | `closeModal('memory-modal')` |
| `plugin-modal` | `#settings-modal` | Discovered plugins & ecosystem extension status | Cards for Git Workflow, YouTube Intel, Design Extractor, System Telemetry | `closeModal('plugin-modal')` |
| `skills-modal` | `#settings-modal` | Discovered Declarative Skill Packages list | Discovered skills cards (`hamza_taste`, `opencode`, `social_research`, etc.) | `closeModal('skills-modal')` |
| `onboarding-modal` | Startup initial probe (when Gemini key is missing) | First-launch onboarding gate for Gemini API Key | `#onboarding-gemini-key` | `saveOnboardingKey()` |

---

## 6. Core JavaScript Function Reference

### Modal & Overlay Management (`frontend/js/ui.js` & `frontend/index.html`)
- `window.openModal(id)`: Adds `.open` class to target element, sets `window._zezoAnimActive = false`, and sets `#vortex-gif` to `visibility = 'hidden'`. Dispatches background log requests if `id === 'log-modal'` or remote key requests if `id === 'qr-modal'`.
- `window.closeModal(id)`: Removes `.open` class. If no other `.modal-overlay.open` exists, restores `window._zezoAnimActive` and sets `#vortex-gif` to `visibility = 'visible'`.
- `window.toggleSettingsDrawer(e)`: Legacy-compatible wrapper; opens `#settings-modal`.
- `window.closeSettingsDrawer(e)`: Legacy-compatible wrapper; closes `#settings-modal`.

### UI Notifications & Utilities (`frontend/js/ui.js`)
- `window.showToast(msg, type, duration)`: Appends a floating toast badge into `#zezo-toast-container` with severity styling (`info`, `success`, `error`).
- `window.showHudToast(msg)`: Auto-detects status emojis (`❌` -> `error`, `✅` -> `success`) and triggers toast.
- `window.copyToClipboard(text, btnEl)`: Safe navigator clipboard writer with visual feedback on the triggering button.

### Assistant State & Telemetry (`frontend/index.html`)
- `setAssistantState(stateKey)`: Switches assistant state (`standby`, `listening`, `thinking`, `speaking`, `executing`, `muted`, `interrupted`, `offline`), updating the matrix dot canvas palette, dock button labels, and `#state-heading-text`.
- `renderTasks(taskList)`: Renders full task queue in `#task-queue-list` and `#task-modal-list`, including progress bars, subtask trees, and statuses (`running`, `done`, `failed`, `queued`).
- `openTaskDetail(taskId, showModal)`: Populates `#task-detail-modal` with internal metadata (PID, Engine, Model, Elapsed time, Logs) and optionally displays the dialog.
- `setCanvasContent(text, contextTitle)`: Streams textual and code payloads directly into `#inspector-body` and `#canvas-content-text`.

---

## 7. CSS Class Reference (`frontend/style.css`)

- **Modals:**
  - `.modal-overlay`: Fullscreen fixed container (`background: rgba(0,0,0,0.92); z-index: 200; contain: layout paint style;`).
  - `.modal-overlay.open`: `display: flex; align-items: center; justify-content: center;`.
  - `.modal-panel`: Centered dialog panel (`box-shadow: 0 25px 60px -12px rgba(0,0,0,0.98); will-change: transform; transform: translateZ(0); animation: modalIn 0.2s ease-out;`).
- **Frames & Tactical Borders:**
  - `.frame`: Tactical panel container with relative positioning and subtle border.
  - `.frame-inner`: Inner container with opaque background (`#0a0a0a`).
  - `.corner`, `.corner-v`: Absolute corner bracket decorations (`rgba(255,255,255,0.4)`).
- **Cards & Badges:**
  - `.card`: Surface card container (`background: var(--bg-surface); border: 1px solid var(--border-subtle);`).
  - `.card-interactive`: Clickable card with explicit hover transitions (`transition: border-color 0.2s ease, background-color 0.2s ease;`).
  - `.badge`: Monospace indicator pill (`.badge-accent`, `.badge-success`, `.badge-warn`, `.badge-danger`).
- **Buttons:**
  - `.btn`: Standard button base with explicit property transitions (`transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;`).
  - `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.btn-outline`, `.btn-sm`, `.btn-icon`.
  - `.dock-btn`: Transparent command dock buttons with explicit hover transitions.
- **Activity Stream:**
  - `.stream-msg`: Chat bubble container (`.stream-msg.user`, `.stream-msg.ai`, `.stream-msg.system`).
  - `.stream-msg-tag`: Origin tag pill (`USER`, `ZEZO`, `SYSTEM`, `TOOL`).
- **HUD Switches:**
  - `.hud-switch`: Custom toggle pill (`.hud-switch.active`, `.hud-switch.active-accent`).
  - `.hud-switch .switch-knob`: Animated knob sliding via explicit `left` and `background-color` transitions.

---

## 8. Regression Rules (Strict Enforcement)

1. **No `backdrop-filter` on Modal Panels or Overlays:** Fullscreen overlays use solid `rgba(0,0,0,0.92)` to eliminate GPU compositor stalls in fullscreen mode.
2. **Never Use `transition: all`:** Always declare explicit CSS transitions to prevent hover-induced layout invalidations.
3. **Always Maintain `_zezoAnimActive`:** `openModal` must pause rAF loops (`_zezoAnimActive = false`) and `closeModal` must resume them if no modals remain open.
4. **Hide Avatar GIF During Modals:** `#vortex-gif` style must be set to `visibility: 'hidden'` on open, and restored to `'visible'` on close.
5. **No Recursive Self-Close in `openModal`:** `openModal(id)` must never call any function that invokes `closeModal` for the same ID.
6. **Settings is a Modal:** The settings panel is `#settings-modal` (never reintroduce anchored dropdown drawers).
7. **QtWebEngine Viewport Handling:** Avoid un-fallback `vh` calculations on critical modal wrappers; use `position: fixed` with explicit `inset: 0` or bounded `max-height`.
