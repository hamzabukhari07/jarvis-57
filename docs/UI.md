# 🖥️ ZEZO — UI & HUD Architecture Specification

> **Creator & Lead Architect:** Hamza Bukhari  
> **System Component:** Tactical Web HUD & Holographic Avatar Interface  
> **Frontend Stack:** React 18 / 19, Vite, Tailwind CSS v4, ReUI Component System, Assistant-UI  
> **Backend Integration:** `core/ui_server.py` (FastAPI / WebSocket Server), `main.py` (Gemini Live Stream)  

---

## 📖 1. Overview & Design Principles

ZEZO features a high-performance, dark cyberpunk tactical HUD built on the **ReUI Design System** and **Autonomous Traffic Vectors**. The interface provides immediate situational awareness, tactile visual feedback, and zero-latency monitoring for autonomous background operations.

### Core Tenets:
1. **Deterministic Cyberpunk Palette:** Deep obsidian backdrop (`--background: #09090b`), tactile panel surfaces (`--card: #121215`), elevated frames (`--popover: #18181b`), and crisp semantic accents (`--primary`, `--accent`, `--border`).
2. **ReUI Component Source of Truth:** Official ReUI primitives (`Frame`, `Card`, `Badge`, `Callout`, `ConfirmDialog`, `Button`, `Input`, `Select`, `Dialog`, `Progress`, `ScrollArea`) serve as the single source of truth across all views.
3. **GPU Layer Isolation & Frame Pacing:**
   - **No Fullscreen Backdrop Blur Stalls:** Fullscreen overlays use solid high-opacity backdrops (`rgba(0, 0, 0, 0.85)` / `var(--background)`) to eliminate GPU re-rasterization bottlenecks in fullscreen mode.
   - **Strict Explicit Transitions:** `transition: all` is strictly forbidden. All animated components declare exact CSS properties (e.g., `border-color`, `background-color`, `opacity`, `transform`) to avoid layout invalidation cascades.
   - **Visualizer Render Gating:** WebGL point-cloud visualizers (`QiviAvatarVisualizer`) and particle canvas loops gate their render loops when modal dialogs are active to preserve CPU and GPU resources.
4. **Multi-View Operational Ergonomics:** Seamless view transitions between the primary **Tactical Workspace**, the **Autonomous Scranton Office Deck**, and the **Workflow Builder**.

---

## 📐 2. Layout Structure & Operational Views

The top-level shell (`App.tsx`) hosts a fixed tactical header and switches dynamically between operational views:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             HEADER (Header.tsx)                             │
│  [⚙ CONTROLS] [⧉ LOGS] [⊞ TASKS] [📱 REMOTE]    ZEZO OS 2.0    [14:20 CLOCK]│
│  Tabs: [ ⚡ TACTICAL ]  [ 🏢 SCRANTON OFFICE ]  [ 🔀 WORKFLOW CANVAS ]       │
├───────────────────┬─────────────────────────────────────┬───────────────────┤
│                   │      CENTER DISPLAY                 │                   │
│   LEFT TELEMETRY  │  ┌───────────────────────────────┐  │   RIGHT ACTIVITY  │
│   CPU, RAM, GPU,  │  │   HOLOGRAPHIC COMPANION       │  │   STREAM          │
│   Network Gauges, │  │   (QiviAvatarVisualizer.tsx)  │  │   (ZezoChatThread)│
│   Active Payload  │  ├───────────────────────────────┤  │   Spoken turns,   │
│   Ingestion       │  │   LIVE EXECUTION CANVAS       │  │   Reasoning tree, │
│                   │  │   (CanvasView.tsx)            │  │   Tool pill cards │
│                   │  └───────────────────────────────┘  │                   │
├───────────────────┴─────────────────────────────────────┴───────────────────┤
│                          COMMAND INPUT CONTAINER                            │
│           [🎤 PUSH-TO-TALK: Ctrl+Alt] [⚡ INTERRUPT] [CHAT INPUT]           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Tactical Workspace View
- **Left Column:** Hardware telemetry gauges (real-time CPU load, memory consumption, GPU metrics, network bandwidth) and payload ingestion dropzone.
- **Center Column:**
  - **Holographic Avatar Visualizer:** Interactive Three.js WebGL point-cloud rendering (`QiviAvatarVisualizer.tsx`) featuring real-time audio viseme amplitude scaling and emotional expressions.
  - **Live Execution Canvas:** Dynamic output viewport (`CanvasView.tsx`) streaming code diffs, reverse-engineered artifacts, and tool outputs.
- **Right Column:** Conversational stream powered by Assistant-UI (`ZezoChatThread.tsx`), providing speech turn transcriptions, collapsible chain-of-thought reasoning, and tool status chips.

### 2. Autonomous Scranton Office View (`AutonomousOfficeScreen.tsx`)
- Dedicated full-screen multi-agent office deck simulating the Scranton Business Park floor plan.
- Real-time agent sprites positioned at distinct desk coordinates (`WORKSTATION_SLOTS`).
- Desk monitor screens glow during active code generation; speech bubbles show task objectives.
- Full agent inspection drawer with live telemetry, Git worktree paths, and `SOUL.md` persona editor.
- Embedded 1-on-1 private chat view (`AgentDirectChatView.tsx`) with dedicated local thread history.

### 3. Workflow Canvas View
- Interactive visual graph view for orchestrating multi-agent pipelines and chained background tasks.

---

## 🎛️ 3. Modals & Overlay Registry

All dialogs and overlays are implemented using modern React component primitives (`@radix-ui/react-dialog` via ReUI):

| Modal Component | Trigger / Invocation | Purpose & Key Features |
| :--- | :--- | :--- |
| `SettingsModal.tsx` | Top navbar gear button / `Ctrl+,` | Central hub with 9 modular tabs: General, Voice, Code Engines, Skills, Appearance, Cloudflare Tunnel, Providers, Memory, About. |
| `TaskManagerModal.tsx` | Top navbar tasks button | Hierarchical process tree viewer, live percentage progress streaming, state filters (`RUNNING`, `QUEUED`, `DONE`, `FAILED`), and recursive cancellation. |
| `MobileRemoteModal.tsx` | Top navbar QR button | Cloudflare Quick Tunnel pairing, dynamic QR code generation, 10-minute rotating OTP security key with countdown timer. |
| `BackendLogModal.tsx` | Top navbar terminal button / `Ctrl+L` | Real-time backend Python log bus viewer with severity filtering (`DEBUG`, `INFO`, `WARN`, `ERROR`), log source filters, and pause/follow controls. |
| `ClipPeekOverlay.tsx` | Automatic clipboard daemon event | Real-time floating HUD presenting instant actions (Refactor, Explain, Run, Reverse-Engineer) when clipboard content changes. |
| `ConfirmDialog.tsx` | Destructive or gating actions | High-contrast confirmation gate with explicit cancel/confirm handlers (used in tasks, cloner, and office operations). |

---

## ⚡ 4. Animation, Audio & Performance Invariants

| Component / Subsystem | Strict Enforcement Rule | Architectural Justification |
| :--- | :--- | :--- |
| **Modal Backdrops** | Opaque backgrounds (`rgba(0,0,0,0.85)` / `var(--background)`) | Eliminates GPU blur re-rasterization bottlenecks during fullscreen rendering. |
| **CSS Transitions** | Explicit transition properties only (e.g. `border-color`, `background-color`) | Prevents browser layout calculation invalidations caused by `transition: all`. |
| **WebGL Avatar Visualizer** | Noise gate applied to mic audio level (`audioLevel < 0.08 ? 0 : ...`) | Suppresses micro-fluctuations and avoids unnecessary 3D vertex mesh recomputations. |
| **Render Gating** | WebGL render loops pause when modals are opened | Saves GPU clock cycles and battery during settings adjustments or log inspections. |
| **Push-to-Talk Shortcut** | Strictly documented and bound to `Ctrl+Alt` | Default universal hotkey ensuring zero conflict with common IDE text editor shortcuts. |
| **Component Hierarchy** | Pure React component state (`useZezoSocket`) | All legacy PyQt6 DOM manipulation (`#vortex-gif`, `#payload-file-input`, `frontend/js/ui.js`) is eliminated. |

---

## 🧑‍💻 5. Creator Attribution

ZEZO's frontend architecture, design system, and component pipeline were conceptualized and architected by **Hamza Bukhari**.
