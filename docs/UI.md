# 🖥️ ZEZO — UI & HUD Architecture Specification

> **Creator & Lead Architect:** Hamza Bukhari  
> **System Component:** Tactical Web HUD & Holographic Avatar Interface  
> **Frontend Stack:** HTML5, Modern Vanilla CSS, WebSockets, Vanilla JavaScript  
> **Backend Integration:** `core/ui_server.py`, `ui.py` (QtWebEngine), `main.py`  

---

## 📖 1. Overview & Design Principles

ZEZO features a high-performance, dark cyberpunk tactical HUD built on the **Autonomous Traffic Vectors Design System**.

### Core Tenets:
1. **Zero Slop & Deterministic Palette:** Deep black obsidian backdrop (`#050505`), tactical panel surfaces (`#0a0a0a`), elevated components (`#111111`), and crisp dynamic accenting (`#f24e1e` / `#22c55e` / `#06b6d4` / `#a855f7`).
2. **GPU Compositing Efficiency & Flicker Prevention:**
   - **No Fullscreen Backdrop Blurs:** `backdrop-filter: blur(...)` is forbidden on full-viewport `.modal-overlay` and inner panel containers. Solid high-opacity backgrounds (`rgba(0,0,0,0.92)` / `#0a0a0a`) eliminate GPU blur re-rasterization bottlenecks in fullscreen mode.
   - **GPU Layer Isolation & Containment:** `.modal-overlay` employs `contain: layout paint style;` while `.modal-panel` utilizes `will-change: transform; transform: translateZ(0);` for dedicated hardware compositing.
   - **Strict Explicit Transitions:** `transition: all` is strictly prohibited. All animated components declare exact properties (e.g. `border-color`, `background-color`, `color`, `transform`) to avoid layout invalidation on hover.
   - **Animation & GIF Gating:** When any modal opens, `window._zezoAnimActive` is set to `false` (pausing 2D canvas rAF drawing loops) and `#vortex-gif` is set to `visibility: hidden` (halting background GIF decoding and compositor passes). Both are safely restored upon closing all active modals.
3. **Responsive Frame Layout:** 3-column workspace with adjustable splitters, tactical corner brackets, and dedicated activity streams.

---

## 📐 2. Layout Structure (`frontend/index.html`)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TOP NAVBAR (.top-navbar)                         │
│  [⚙ CONTROLS] [⧉ LOGS] [⊞ MATRIX] [📱 QR]     ZEZO OS 2.0     [14:20 CLOCK] │
├───────────────────┬─────────────────────────────────────┬───────────────────┤
│                   │      CENTER COLUMN (.center-column) │                   │
│   LEFT TELEMETRY  │  ┌───────────────────────────────┐  │   RIGHT ACTIVITY  │
│   (.left-telemetry│  │  AVATAR FRAME (#avatar-frame) │  │   STREAM          │
│   System metrics, │  │  Holographic 3D / Fluid Vortex│  │   (.right-column) │
│   CPU/RAM gauges, │  ├───────────────────────────────┤  │   User prompts,   │
│   Quick Tools)    │  │  COMMAND DOCK (.avatar-dock)  │  │   AI replies,     │
│                   │  ├───────────────────────────────┤  │   Sys logs,       │
│                   │  │  INSPECTOR (#inspector-frame) │  │   Code diffs      │
│                   │  └───────────────────────────────┘  │                   │
├───────────────────┴─────────────────────────────────────┴───────────────────┤
│                          COMMAND INPUT CONTAINER                             │
│                      [MIC] [POWER] [CHAT INPUT] [SEND]                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎛️ 3. Settings & Modal Architecture

### Centered Settings & Controls Dialog (`#settings-modal`)
- **Trigger:** Top-left gear button (`#settings-trigger-btn`) in `.top-navbar` executing `openModal('settings-modal')`.
- **Display Mode:** Standard modal overlay (`.modal-overlay`) with a structured 2-column tactical action matrix, volume/brightness sliders, theme dot picker, and quick engine shortcuts.
- **Safety Guarantee:** Modal open/close actions do not trigger recursive drawer self-cancellation.

### Modal Registry
1. **Full Settings & Quick Controls (`#settings-modal`):** Central command hub for desktop settings, audio/power toggles, system tools, and Default Creation Engine (`OpenCode` / `Antigravity` / `Kilo`) & Quick Edit Engine (`Groq Code Helper` / `Kilo` / `OpenCode`) dropdown selectors.
2. **API Credentials Hub (`#api-keys-modal`):** Independent management of Gemini, Groq, and ElevenLabs API keys with live validation badges.
3. **Persona Customization (`#customise-modal`):** Assistant name, response language, voice persona selection, and Kokoro fallback options.

5. **Log Console (`#log-modal`):** Real-time bus inspection with severity filters and export.
6. **Task Matrix (`#task-modal` & `#task-detail-modal`):** Background task inspector, subagent telemetry, and artifact browser.
7. **Mobile QR Remote (`#qr-modal`):** LAN companion authentication QR code and secret display.
8. **Audio Devices (`#audio-modal`):** Input/output audio device selector.
9. **Memory & Brain Explorer (`#memory-modal`):** SQLite FTS5 database memory viewer.
10. **Skills & Plugins Hub (`#skills-modal` / `#plugin-modal`):** Discovered capabilities and loaded action tools.

---

## ⚡ 4. Animation & Performance Rules

| Component | Allowed Properties | Forbidden Properties | Reason |
| :--- | :--- | :--- | :--- |
| `.modal-overlay` | `background: rgba(0,0,0,0.92)`, `contain` | `backdrop-filter: blur()`, `scale()` | Prevents full-screen compositor stalls and flicker. |
| `.modal-panel` | `translateY(8px) -> 0`, `will-change: transform` | `backdrop-filter`, `transition: all` | Isolate panel to GPU layer; avoid repaint cascade. |
| Button / Interactive Elements | `transition: border-color, background-color, color` | `transition: all` | Eliminates expensive layout and paint invalidations. |
| Background Canvas & Vortex GIF | Gated via `_zezoAnimActive` & `visibility: hidden` | Unconditional rAF / visible GIF decoding | Halts all background compositing passes while modals are active. |
