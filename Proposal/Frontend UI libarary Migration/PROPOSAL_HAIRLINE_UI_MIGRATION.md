# 📐 Architectural Proposal: ReUI to Hairline UI Migration for ZEZO

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target Subsystem:** `frontend/` (Tactical Interface, Autonomous Office & Agent Workspaces)  
> **Status:** Proposed / Architectural RFC  
> **Date:** March 2025  

---

## 1. 📖 Executive Summary

This proposal outlines the technical roadmap, architectural impact, file-by-file blast radius, and execution strategy for migrating the ZEZO frontend from its current **ReUI** foundation to **Hairline UI** (`hairlineui.com`), coupled with the **Hairline UI Model Context Protocol (MCP)** server.

### Why Hairline UI?
1. **165+ AI-Native Components:** Ready-made primitives tailored specifically for AI agents, prompt composers, action receipts, streaming answers, chain-of-thought blocks, and status indicators.
2. **Native shadcn/ui Registry Standard:** Hairline UI components install via standard `shadcn` CLI tooling, cleanly coexisting with Tailwind CSS and Radix/Base-UI primitives without proprietary lock-in.
3. **Coding Agent MCP Direct Integration:** Exposes read-only discovery tools (`search_components`, `find_for_screen`, `get_component`, `get_install_command`) directly to coding agents, allowing autonomous discovery and surgical installation of UI components.
4. **Hairline Aesthetic:** Crisp 1px borders, subtle surface elevations, and clean micro-interactions that match ZEZO's dark tactical aesthetic while removing visual clutter.

---

## 2. 🔍 Current Frontend Baseline (Ground Truth)

Based on inspection of the current live repository:

* **Engine:** React 19 (`19.2.8`), Vite (`8.3.0`), TypeScript (`~6.0.2`).
* **Styling:** Tailwind CSS v4 (`4.3.3`) via `@tailwindcss/vite`.
* **Icons:** Free Hugeicons Stroke Rounded via `@hugeicons/react` with aliases in `src/lib/zezo-icons.tsx`.
* **shadcn Registry Config:** `frontend/components.json` is configured with style `base-nova`, using standard aliases (`@/components`, `@/components/ui`, `@/lib/utils`).
* **Current ReUI Footprint:**
  * **Theme Specification:** `frontend/src/index.css` defines ReUI style presets, including Hamza's custom *Tweakcn Copper Dark/Light* themes and custom `--frame-*` density variables.
  * **Core Primitives:** 7 wrapper components in `frontend/src/components/reui/`:
    `badge.tsx`, `callout.tsx`, `card.tsx`, `chat.tsx`, `frame.tsx`, `kbd.tsx`, `confirm-dialog.tsx`.
  * **Dependent Screens:** 17 production application views directly import and rely on ReUI components.

---

## 3. 🗺️ Component Mapping & Replacement Strategy

Based on live codebase auditing, **5 active ReUI primitives** are currently used across the production screens (along with 2 dormant ones). Here is the exact replacement and modernization mapping:

| Current ReUI Component & Sub-components | Hairline UI Replacement | Exact Role in ZEZO & Architectural Advantage |
| :--- | :--- | :--- |
| **`reui/frame.tsx`**<br>`Frame`, `FramePanel`, `FrameHeader`, `FrameTitle` | **`Surface` / `Container`** | Layout bounding shell used in `App.tsx`, `AutonomousOfficeScreen`, `SettingsModal`, and `AgentDirectChatView`. Eliminates ReUI custom `--frame-*` density variables while introducing crisp 1px hairline borders and responsive spacing. |
| **`reui/badge.tsx`**<br>`Badge` | **`StatusBadge` / `Badge`** | Status tags across 14 screens. Hairline adds pre-configured AI states (`idle`, `thinking`, `executing`, `error`) with animated activity pulses for agent worktrees and tasks. |
| **`reui/card.tsx`**<br>`Card`, `CardContent` | **`Card` / `CardHeader` / `CardContent`** | Modular container used in office desks, settings tabs, and file panels. Crisp 1px border styling with integrated header/footer slots and subtle hover transitions. |
| **`reui/callout.tsx`**<br>`Callout` | **`Notice` / `Alert`** | Informational alert strips used in `ToolsSettingsTab`, `SkillsSettingsTab`, and `CodeEnginesSettingsTab`. Replaces heavy background color fills with minimalist 1px border accents. |
| **`reui/confirm-dialog.tsx`**<br>`ConfirmDialog` | **`Dialog` / `ConfirmModal`** | Critical confirmation popups in `App.tsx`, `AutonomousOfficeScreen`, `SkillsSettingsTab`, `MemoryGraphCanvas`, and `SettingsModal`. Standard Radix primitive strictly respecting ZEZO's opaque `#0a0a0a` modal rule. |
| **`reui/chat.tsx`** (Dormant) | **`PromptComposer` & `StreamingAnswer`** | Dedicated AI chat bubble components, smooth token streaming containers, and inline tool execution receipt chips for `AgentDirectChatView` and `ZezoChatThread`. |
| **`reui/kbd.tsx`** (Dormant) | **`Kbd`** | Sleek monospace shortcut pills adhering to 1px hairline aesthetics for keyboard hotkey indicators. |

---

## 4. 📂 Impact Analysis: Affected Files & Verified Blast Radius

Live repository inspection reveals that a full migration will touch **18 frontend files** (plus 3 governance documents):

### A. Main Shell & Autonomous Office (7 Files)
1. `frontend/src/App.tsx` — Replaces `Frame`, `FramePanel`, `Badge`, and `ConfirmDialog` in the root tactical navigation bar and workspace switcher.
2. `frontend/src/components/office/AutonomousOfficeScreen.tsx` — Replaces `Frame`, `FramePanel`, `FrameHeader`, `FrameTitle`, `Card`, `CardContent`, `Badge`, and `ConfirmDialog` across agent desks and office cards.
3. `frontend/src/components/office/AgentWorkspaceView.tsx` — Replaces `Badge` in the agent workbench header and status strip.
4. `frontend/src/components/office/AgentDirectChatView.tsx` — Replaces root `Frame` wrapper surrounding the agent conversation area.
5. `frontend/src/components/office/AgentRosterTable.tsx` — Replaces `Badge` in agent status column (idle/busy/running).
6. `frontend/src/components/office/AgentConfigModal.tsx` — Replaces `Frame`, `FramePanel`, `FrameHeader`, `FrameTitle`, and `Badge` inside the agent parameter configuration panel.
7. `frontend/src/components/office/AgentFilesPanel.tsx` — Replaces `Frame`, `FramePanel`, `Card`, `CardContent`, and `Badge` in the workspace file browser.

### B. Settings Tabs & Modals (5 Files)
8. `frontend/src/components/settings/SettingsModal.tsx` — Replaces `Frame`, `FramePanel`, `Card`, `Badge`, and `ConfirmDialog` in the main settings window.
9. `frontend/src/components/settings/ToolsSettingsTab.tsx` — Replaces `Card`, `Badge`, and `Callout` in the action tools listing.
10. `frontend/src/components/settings/SkillsSettingsTab.tsx` — Replaces `Card`, `Badge`, `Callout`, and `ConfirmDialog` in skill management.
11. `frontend/src/components/settings/CodeEnginesSettingsTab.tsx` — Replaces `Card`, `Badge`, and `Callout` in coding engine status cards.
12. `frontend/src/components/tasks/TaskManagerModal.tsx` — Replaces `Badge` in task scheduler tables and task run logs.

### C. Memory, Remote & Conversational UI (4 Files)
13. `frontend/src/components/memory/MemoryInspectorDrawer.tsx` — Replaces `Badge` and `ConfirmDialog` in memory inspection and entry deletion.
14. `frontend/src/components/memory/MemoryGraphCanvas.tsx` — Replaces `Badge` and `ConfirmDialog` in memory graph controls.
15. `frontend/src/components/remote/MobileRemoteModal.tsx` — Replaces `Badge` in QR code remote device pairing status.
16. `frontend/src/components/assistant-ui/ZezoChatThread.tsx` — Replaces `Badge` in chat thread chips and tool execution labels.

### D. Styling & Primitives Layer (2 Files)
17. `frontend/src/index.css` — Purges obsolete `--frame-*` density variables, integrates Hairline UI 1px border and surface design tokens while keeping Hamza's custom Copper Dark/Light OKLCH color palettes intact.
18. `frontend/src/components/reui/` — Entire directory (7 wrapper files) deprecated and retired once components are installed in `frontend/src/components/ui/` or `frontend/src/components/hairline/`.

### E. Governance & Documentation (3 Files)
19. `AGENTS.md` — Update Frontend Rule 1 to specify Hairline UI as the design system of record.
20. `EXAMPLES.md` — Update component usage patterns and golden UI examples.
21. `docs/FRONTEND_STRUCTURE.md` — Synchronize component folder structure, component registry, and import guidelines.

---

## 5. 👁️ Concrete Visual & Runtime Impact (What Changes & What Stays)

### What Changes Visually:
1. **Ultra-Crisp 1px Borders:** Replaces inconsistent border weights and heavy frames with sharp 1px hairline dividers and subtle surface elevations.
2. **Dynamic AI Status Badges:** Agent cards show live pulsating indicators for active states (`thinking`, `executing`, `idle`, `error`) instead of static tags.
3. **Calm Minimalist Alert Banners:** Callouts become sleek 1px accent-bordered notices without distracting thick background fills.
4. **Enhanced Chat Telemetry:** Agent chat views gain standardized streaming message bubbles and tool execution receipt chips.

### What Remains 100% Preserved (Zero Regressions):
1. **Identical Colors & Theme:** Hamza's custom Copper Dark (`oklch(0.2679 0.0036 106.6427)`) and Copper Light themes remain the core color system.
2. **Strict Modal Invariants:** Modal panel backgrounds remain strictly opaque (`#0a0a0a`), and no `backdrop-filter` is permitted inside modals.
3. **Performance & Animation Throttling:** `window._zezoAnimActive` continues pausing background/avatar animations while modals are open.
4. **Interactive Logic & APIs:** All React state hooks, WebSocket connections, API handlers, and button click behaviors remain completely unchanged.

---

## 6. 🚀 Execution Plan (Phased Roadmap)

To maintain stability and prevent regressions, the migration is structured into **5 sequential phases**:

### Phase 1: Hairline UI MCP & Environment Setup
1. Register Hairline UI MCP with Claude Code:
   ```bash
   claude mcp add --transport http hairline-ui https://hairlineui.com/api/mcp
   ```
2. Verify registry installation inside `frontend/` using shadcn CLI:
   ```bash
   cd frontend && npx shadcn@latest --version
   ```
3. Test compatibility with Tailwind CSS v4 (`@tailwindcss/vite`).

### Phase 2: Theme Token Synthesis
1. Map Hairline UI CSS tokens to ZEZO's current OKLCH color system in `frontend/src/index.css`.
2. Ensure Copper Dark (`oklch(0.2679 0.0036 106.6427)`) and Copper Light palettes seamlessly bind to Hairline UI border, surface, and text variables.
3. Keep `--radius: 0.75rem` or adjust to Hairline UI's signature subtle radii (`0.5rem`).

### Phase 3: Core Primitives Installation & Aliasing
1. Install base Hairline components (`card`, `badge`, `dialog`, `prompt-composer`, `action-receipt`, `kbd`, `notice`).
2. Provide temporary backward-compatible re-exports or migrate callers directly to avoid build breaks during transition.

### Phase 4: Screen Refactoring (Surgical Subsystem Passes)
* **Pass 4.1: Settings & System Modals** (`SettingsModal`, `TaskManagerModal`, `MobileRemoteModal`).
* **Pass 4.2: Autonomous Office & Agent System** (`AutonomousOfficeScreen`, `AgentWorkspaceView`, `AgentRosterTable`).
* **Pass 4.3: Conversational & Assistant UI** (`ZezoChatThread`, chat input pill, action receipts).

### Phase 5: Verification, Cleanup & Rule Synchronization
1. Remove deprecated `frontend/src/components/reui/` folder once all imports are migrated.
2. Run strict 3-layer verification:
   * **Layer 1:** `npm run build` (TypeScript compilation & asset bundling).
   * **Layer 2:** Runtime execution (`npm run dev` / `python main.py --no-audio`) to verify WebSocket & modal actions.
   * **Layer 3:** Invariant check (`_zezoAnimActive`, backdrop filter restrictions, mobile responsiveness).
3. Synchronize `AGENTS.md`, `EXAMPLES.md`, and `docs/FRONTEND_STRUCTURE.md`.

---

## 7. ⚠️ Critical Invariants & Risk Mitigation

During migration, the following ZEZO non-negotiables must remain strictly protected:

1. **Modal Invariants (AGENTS.md Frontend Rule 2):**
   * Elements *inside* modals must **NOT** have `backdrop-filter`. Only `.modal-overlay` may carry `backdrop-filter: blur(12px)`.
   * Modal panel backgrounds must remain strictly opaque (`#0a0a0a` or solid dark OKLCH).
2. **Animation Throttling (`_zezoAnimActive`):**
   * Modal opening/closing lifecycle must continue toggling `window._zezoAnimActive` so Three.js, Qivi holographic avatar, and background animations do not waste CPU while modals are active.
3. **Audio/Voice Pipeline Isolation (AGENTS.md Core Rule 6):**
   * Under no circumstances should any migration script touch `main.py` audio loops, `core/audio_devices.py`, or voice queues.
4. **Hugeicons Aliasing Integrity:**
   * Icon references must continue resolving through `src/lib/zezo-icons.tsx` to prevent broken Lucide vs Hugeicons import mismatches.

---

## 8. ⚖️ Comparison Matrix: ReUI vs. Full Hairline UI Migration

| Evaluation Dimension | Current ReUI Setup | Full Hairline UI Migration |
| :--- | :--- | :--- |
| **Component Variety** | 7 basic primitives + manual Tailwind | 165+ production-grade AI & SaaS components |
| **Agent Tooling** | Manual file authoring & inspection | Agent MCP query (`search_components`, `find_for_screen`) |
| **AI Experience** | Assistant-ui wrappers + custom CSS | Built-in streaming answers, prompt composers, action receipts |
| **Visual Density** | Tactical dark with custom frame paddings | Ultra-crisp 1px hairline borders, calm minimalist hierarchy |
| **Migration Cost** | Zero (already in place) | Medium (~22 files touched, 1-2 focused engineering sessions) |
| **Maintenance Burden** | Custom wrapper code maintained in-repo | Standard shadcn registry components with community updates |

---

## 9. 🎯 Lead Architect Decision Options

Hamza, you have 3 paths forward:

1. **Option 1: Full Migration (Recommended for Long-Term Polish)**  
   Execute the 5-phase plan above, deprecating ReUI entirely in favor of a unified Hairline UI standard.
2. **Option 2: Hybrid Adoption (Zero Risk, Incremental)**  
   Keep ReUI for existing frames and modals. Add Hairline UI MCP to install new specialized AI components (`prompt-composer`, `action-receipt`, `status-button`) as new features are built.
3. **Option 3: Status Quo**  
   Retain ReUI exclusively; reject Hairline UI.
