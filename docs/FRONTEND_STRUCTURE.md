# 🖥️ ZEZO — Frontend Structure & Component Reference

> **Creator & Lead Architect:** Hamza Bukhari  
> **System Component:** Modern Single-Page Tactical Interface & Autonomous Office Deck  
> **Frontend Stack:** React 18 / 19, Vite, Tailwind CSS v4, ReUI Component System, Assistant-UI  
> **Backend Integration:** FastAPI WebSocket Server (`core/ui_server.py`), REST API (`/api/*`), Live Gemini Streaming (`main.py`)  

---

## 📖 1. Overview & Architectural Stack

The ZEZO frontend is a high-performance, dark cyberpunk single-page application built on **React and Vite**. It replaces legacy PyQt6 and vanilla DOM architectures with a componentized, reactive interface governed by the **ReUI Component System** and styled with **Tailwind CSS**.

### Core Technology Stack:
- **Framework:** React 18/19 with Vite bundler (`@vitejs/plugin-react`).
- **Design System:** ReUI (`components/reui/*`) providing high-contrast tactical frames, cards, badges, callouts, and confirm dialogs.
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`) with strict semantic tokens (`--background`, `--foreground`, `--primary`, `--border`, etc.).
- **Conversational UI:** Assistant-UI (`@assistant-ui/react`, `@assistant-ui/react-markdown`) powering the streaming chat thread, reasoning collapse, and tool execution cards.
- **3D & Visualizations:** Three.js (`three`), 3D Force Graph (`3d-force-graph`, `react-force-graph-3d`), Qivi holographic point-cloud avatar (`qivi-react`), and Blobatar (`blobatar/react`).
- **Communication:** Bi-directional JSON WebSocket (`ws://127.0.0.1:8765/ws`) via `useZezoSocket` hook plus targeted REST endpoints (`/api/*`).

---

## 📐 2. Application Layout Structure (`frontend/src/App.tsx`)

The root `App.tsx` controls global telemetry, active modals, WebSocket streaming, and master view switching.

### Master View Switching:
The navigation header provides tabs to transition across operational interfaces:
1. **Tactical View (`activeTab === 'tactical'`):** 3-panel command dashboard featuring hardware telemetry, holographic avatar visualizer, live execution canvas, and real-time Assistant-UI chat stream.
2. **Office View (`activeTab === 'office'`):** Autonomous 2D pixel Scranton Office screen displaying specialist agent desks, monitor screens, sprite states, and 1-on-1 direct chat channels.
3. **Workflow View (`activeTab === 'workflow'`):** Interactive node-based agent pipeline execution builder.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            HEADER (Header.tsx)                              │
│  [⚙ SETTINGS] [⧉ LOGS] [⊞ TASKS] [📱 REMOTE]   [TACTICAL | OFFICE | WORKFLOW]│
├───────────────────┬─────────────────────────────────────┬───────────────────┤
│                   │      CENTER COLUMN                  │                   │
│   LEFT TELEMETRY  │  ┌───────────────────────────────┐  │   RIGHT ACTIVITY  │
│   System metrics, │  │   HOLOGRAPHIC AVATAR          │  │   STREAM          │
│   CPU/RAM/GPU/Net │  │   (QiviAvatarVisualizer.tsx)  │  │   (ZezoChatThread)│
│   Gauges, Ingestion│ ├───────────────────────────────┤  │   Spoken turns,   │
│                   │  │   LIVE DISPLAY CANVAS         │  │   Tool executions,│
│                   │  │   (CanvasView.tsx)            │  │   Reasoning steps │
│                   │  └───────────────────────────────┘  │                   │
└───────────────────┴─────────────────────────────────────┴───────────────────┘
```

---

## 🧩 3. Key Component Directory & Specifications

### 3.1. Autonomous Scranton Office (`AutonomousOfficeScreen.tsx`)
- **Path:** `frontend/src/components/office/AutonomousOfficeScreen.tsx`
- **Purpose:** Full-featured 2D pixel desk simulation representing the autonomous fleet in their physical workspace layout.
- **Key Capabilities:**
  - **Workstation Matrix:** 18 workstation slots (`WORKSTATION_SLOTS`) positioned on precise percentage coordinates (Michael, Ali, Haider, Ahmad, Dwight, Pam, Kelly, Quantum, DevDynamo, DataEinstein, Annex desks).
  - **Sprite & Monitor Telemetry:** Real-time agent status states (`idle`, `working`, `thinking`, `speaking`, `offline`) reflected through avatar motion, desk monitor glow, and speech bubbles.
  - **Agent Soul Editor:** Inspect and modify individual agent `SOUL.md` persona files directly in the HUD with persistent saving via `/api/fleet/save_soul`.
  - **Task Dispatch:** Assign tasks to isolated Git worktrees with safety tier verification (`L0_READ_ONLY`, `L1_MUTATION`, `L2_DESTRUCTIVE`).
  - **Zero Fake Simulation:** Renders purely from live WebSocket fleet events (`agent_task_started`, `task_progress`, `task_done`, `fleet_updated`).

### 3.2. Agent Direct 1-on-1 Chat (`AgentDirectChatView.tsx`)
- **Path:** `frontend/src/components/office/AgentDirectChatView.tsx`
- **Purpose:** Isolated, direct conversational thread with a specific fleet agent.
- **Key Capabilities:**
  - **Context Isolation:** Conversations are scoped to the selected specialist agent without polluting the main live voice pipeline context.
  - **Thread Persistence:** Chat threads are stored locally per agent (`zezo_agent_threads_<agent_id>`), allowing multi-session history tracking.
  - **Model & Engine Overrides:** Direct selection of coding engines and LLM models for the specific conversation.
  - **Seamless Floor Navigation:** Toggle between the wide office floor view and deep direct chat.

### 3.3. 3D Memory Knowledge Graph (`MemoryGraphCanvas.tsx`)
- **Path:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`
- **Purpose:** Interactive 3D Force-Directed visualizer for ZEZO's episodic, profile, and knowledge memory.
- **Key Capabilities:**
  - **Force-Directed 3D Graph:** Built on `3d-force-graph` and `three-spritetext`, rendering memory nodes interconnected by `[[wikilinks]]`.
  - **Category Color Coding:** Profile (Purple), Project (Cyan), Preference (Orange), Relationship (Yellow), Knowledge (Emerald), General (Slate).
  - **Viseme & Audio Reactivity:** Node sizes, particle speeds, and rotation oscillate dynamically in response to incoming mic and speech levels.
  - **Inspector Drawer:** Integrated with `MemoryInspectorDrawer.tsx` to read full markdown snippets, tags, timestamps, and connected outbound links upon clicking any node.
  - **Timeline & Filter Controls:** Filter nodes by query or temporal horizons (`all`, `24h`, `7d`, `30d`), and switch between 3D spherical graph and timeline mode.

### 3.4. Background Task Tree Viewer (`TaskManagerModal.tsx`)
- **Path:** `frontend/src/components/tasks/TaskManagerModal.tsx`
- **Purpose:** Centralized inspection dialog for all background processes, workers, and agent jobs.
- **Key Capabilities:**
  - **Hierarchical Task Tree:** Renders parent/child task relationships, showing subtask trees and milestone progress bars.
  - **Live Progress Streaming:** Receives real-time percentage and step updates over WebSocket.
  - **Lifecycle Management:** Supports filtering by state (`ALL`, `RUNNING`, `QUEUED`, `DONE`, `FAILED`) and provides instant recursive task cancellation.
  - **Telemetry Inspection:** Displays process ID (PID), engine type, target paths, start time, and log stream.

### 3.5. Mobile Remote Control Gateway (`MobileRemoteModal.tsx`)
- **Path:** `frontend/src/components/remote/MobileRemoteModal.tsx`
- **Purpose:** Pairing and gateway interface for remote mobile smartphone control.
- **Key Capabilities:**
  - **Cloudflare Quick Tunnel Integration:** Displays the live public secure tunnel URL established via background `cloudflared`.
  - **QR Code Generation:** Generates a real-time QR code using `qrcode` for instant mobile camera pairing.
  - **OTP Security Key:** Displays the rotating one-time pairing key with a 10-minute time-to-live (`REMOTE_KEY_TTL_SECONDS = 600`) and countdown timer.
  - **Status Feedback:** Live indicators for tunnel connection status (`starting`, `active`, `error`, `idle`).

### 3.6. Clipboard Watcher Floating HUD (`ClipPeekOverlay.tsx`)
- **Path:** `frontend/src/components/clipboard/ClipPeekOverlay.tsx`
- **Purpose:** Intelligent HUD overlay that activates when the operating system clipboard updates.
- **Key Capabilities:**
  - **Content Classification:** Distinguishes between code snippets, URLs, long articles, and plain text.
  - **Instant Context Actions:** One-click shortcuts to Explain, Refactor, Run, or Reverse-Engineer captured clipboard text.
  - **Non-Intrusive Floating Interface:** Floats at the bottom corner with smooth enter/exit animations and direct message injection into the ZEZO stream.

### 3.7. Assistant-UI Conversational Thread (`ZezoChatThread.tsx`)
- **Path:** `frontend/src/components/assistant-ui/ZezoChatThread.tsx`
- **Purpose:** Production-grade conversation stream powered by Assistant-UI primitives.
- **Key Capabilities:**
  - **Shimmer Labels & Turn Process Pills:** Dynamic status chips indicating background tool execution and active thinking states.
  - **Reasoning Collapse:** `ChainOfThought` component that renders collapsible step-by-step model reasoning without cluttering the chat view.
  - **Avatar Expression Binding:** `ChatAvatarIcon` dynamically reflects model emotions (`thinking`, `happy`, `talking`, `idle`).
  - **Markdown & Code Rendering:** Syntax-highlighted code blocks with instant copy actions and formatted markdown prose.

### 3.8. Code Engines Management Tab (`CodeEnginesSettingsTab.tsx`)
- **Path:** `frontend/src/components/settings/CodeEnginesSettingsTab.tsx`
- **Purpose:** Engine health status and CLI configuration panel inside the Settings modal.
- **Key Capabilities:**
  - **Health Cards:** Real-time status cards for **Antigravity CLI (`agy`)**, **OpenCode (`opencode`)**, and **Kilo Code (`kilo`)**.
  - **Binary & Version Probes:** Live resolution indicators showing detected binary paths, CLI versions, and authenticated model rosters.
  - **Probing Triggers:** One-click re-probe triggering the backend `/api/code_engines/probe` endpoint with non-blocking feedback.

---

## 🎛️ 4. Settings Modal Architecture (`SettingsModal.tsx`)

The settings interface is housed in `frontend/src/components/settings/SettingsModal.tsx`, implemented as a clean ReUI dialog with 9 modular category tabs:

| Tab ID | Component / Focus | Key Configurations |
| :--- | :--- | :--- |
| `general` | General System Controls | Autostart, Brief Voice Confirmations, Push-to-Talk (`Ctrl+Alt`), Wake Word toggle. |
| `voice` | Audio & Voice Persona | Gemini Live Voice selection (Puck, Charon, Aoede, Fenrir, Kore), Kokoro fallback, Mic bleed monitor. |
| `code-engines` | `CodeEnginesSettingsTab` | Binary resolution, model selection, and auth verification for Antigravity, OpenCode, and Kilo. |
| `skills` | `SkillsSettingsTab` | Declarative skill packages inspection, safety scanner reports, and dynamic skill creation. |
| `appearance` | HUD Aesthetics | Holographic Companion archetype (Qivi WebGL vs. Vortex), particle density, and color accents. |
| `tunnel` | Cloudflare Tunnel Gateway | Background daemon status, quick tunnel initialization, and OTP security controls. |
| `providers` | API Credential Hub | Secure management of Google Gemini, Groq, and ElevenLabs API keys. |
| `memory` | Memory & Brain Explorer | Interactive `MemoryGraphCanvas` 3D graph and Markdown note vault browser. |
| `about` | System Telemetry | Version, creator attribution (**Hamza Bukhari**), and runtime diagnostics. |

---

## ⚡ 5. Performance & Anti-Regression Rules

1. **ReUI Components as Ground Truth:** Always import and utilize canonical ReUI components (`Button`, `Card`, `Badge`, `Frame`, `Dialog`, `Select`, `Switch`) rather than ad-hoc HTML elements.
2. **No Backdrop-Filter Inside Modals:** `.modal-overlay` may apply subtle backdrop blur, but elements *inside* modal panels must maintain solid opaque backgrounds (`#0a0a0a` / `var(--background)`) to prevent GPU rasterization stalls.
3. **Explicit Transitions Only:** Never use `transition: all`. Always list explicit CSS transitions (`transition: border-color 0.15s ease, background-color 0.15s ease`).
4. **Animation Gating:** Background Three.js rendering loops and WebGL animations must gate their render loops when modals or full-screen overlays are active to minimize idle CPU/GPU consumption.
5. **No Legacy DOM Selectors:** Never introduce or reference obsolete PyQt6 DOM IDs (`#vortex-gif`, `#payload-file-input`, `#task-queue-list`, `#stream-box`, or `frontend/js/ui.js`). Everything flows through React state and props.
