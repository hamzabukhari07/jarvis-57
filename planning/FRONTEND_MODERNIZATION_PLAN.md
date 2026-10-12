# 🚀 Plan: ZEZO Full Frontend Modernization (React 19 + Tailwind v4 + Assistant-UI)

> **Goal:** Transform ZEZO's frontend from dark/low-contrast vanilla HTML into a modern, studio-grade AI Operating System UI using React 19, Tailwind CSS v4, shadcn/ui, Assistant-UI, and AI-SDK Elements, while preserving 100% of Python backend functionality (WebSockets, audio streaming, fleet management, and CLI engines).

---

## 🏗️ Architecture Blueprint

```
zezo version 2/
├── frontend/                   # ⚡ NEW Modern Vite + React 19 Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui primitives (Button, Dialog, Dropdown, Tabs)
│   │   │   ├── chat/           # Assistant-UI & AI-SDK Elements (Thread, Message, ToolCard)
│   │   │   ├── fleet/          # Agent Roster, Inspector Panel, Environment Controls
│   │   │   ├── office/         # Embedded Pixel Office / Visual Workflow Canvas (@xyflow/react)
│   │   │   └── telemetry/      # Live Audio Vortex, Hardware Telemetry & Log Console
│   │   ├── hooks/
│   │   │   ├── useZezoSocket.ts# Real-time WebSocket connection hook (state, progress, audio)
│   │   │   └── useFleet.ts     # Fleet agents, status & live mutation state
│   │   ├── lib/
│   │   │   └── api.ts          # REST Client (/api/fleet/*, /api/models, /api/settings)
│   │   ├── App.tsx             # Master Layout: Top HUD Bar, Multi-View Switcher, Side Panels
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts          # Builds into dist/ (or dev proxy to localhost:8000)
│   └── tailwind.config.js      # Tailwind CSS v4 + Studio Zinc/Accent Theme
│
├── core/
│   └── ui_server.py            # Serves frontend/dist/ in production + handles WebSockets & REST APIs
└── main.py                     # PyQt6 Window loads http://127.0.0.1:8000
```

---

## 📋 Phased Implementation Plan

### Phase 1: Vite + React 19 + Tailwind v4 Setup & Build Pipeline
- Initialize `frontend/` as a Vite + React 19 + TypeScript project.
- Configure Tailwind CSS v4 with a clean, high-contrast dark theme (Zinc-900 canvas, Crisp borders `#27272a`, High-contrast typography `#fafafa`, Accent `#f24e1e` / `#a855f7`).
- Install and configure `shadcn/ui`, `lucide-react`, and `@radix-ui` primitives.
- Configure `vite.config.ts` so `npm run build` outputs static assets to `frontend/dist`.
- Update `core/ui_server.py` to seamlessly serve `frontend/dist` with SPA fallback routing.
- **Single-Terminal Guarantee (`main.py`):** Add auto-detection in `main.py` to ensure running `python main.py` boots everything (backend + frontend) in ONE single command/terminal without requiring a separate dev server.

### Phase 2: WebSocket & State Bridge (Zero Backend Regression)
- Build `useZezoSocket.ts` hook connecting to `ws://127.0.0.1:8000/ws`.
- Map all backend events:
  - `state_change` (listening, speaking, thinking, sleeping)
  - `audio_level` & `mic_energy` (for avatar animation)
  - `fleet_updated`, `agent_task_progress`, `task_done`
  - `log_bus` terminal logs ring buffer
- Create REST client `lib/api.ts` mapping all `/api/fleet/*`, `/api/models`, and `/api/settings` endpoints.

### Phase 3: Modern Top HUD & Audio Avatar Bar
- Build sleek top navigation bar:
  - Mode Switcher pills (`Tactical Dashboard`, `Agent Office`, `Flow Canvas`).
  - System status indicators (Groq/Gemini live latency, Memory bus, SQLite FTS5 status).
  - Voice loop toggle (Push-to-Talk, Mute, Volume slider, Settings gear modal).
- Implement interactive 3D / Audio reactive Avatar component (clean canvas wave + vortex visualizer).

### Phase 4: Assistant-UI & AI-SDK Tool Execution Stream
- Implement modern threaded chat interface using `assistant-ui` patterns:
  - Prompt composer with attachment support and model selector badge.
  - Streaming markdown bubbles with syntax-highlighted code blocks (copy + apply buttons).
  - **AI-SDK Elements Tool Cards:** Collapsible, interactive execution cards for:
    - OpenCode / Kilo code diffs (`patch` preview)
    - Bash terminal runs with live stdout/stderr folding
    - Design token extraction results
    - Web search & deep research citations

### Phase 5: Redesigned Agent Fleet Inspector & Workflow Canvas
- Modernize the Agent Roster & Inspector Drawer:
  - High-contrast agent cards with live status pills (`IDLE`, `WORKING`, `MUTATING`).
  - Accordion drawer for Agent Environment (`Engine`, `Workspace`, `Model`, `Safety Tier`).
  - Direct Action buttons (`Chat`, `Edit Profile`, `Soul Files`).
- Embed Scranton Pixel Office and optional `@xyflow/react` node delegation canvas.

### Phase 6: Testing, Polish & 3-Layer Verification
- Run production build (`npm run build`).
- Verify PyQt6 desktop app boots with 0 errors and loads the new UI instantly.
- Test voice loop, chat responses, fleet task dispatch, and settings modals.
- Clean up obsolete code and update documentation.

