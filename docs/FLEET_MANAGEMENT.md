# 👥 Autonomous Fleet Management & The Scranton Office

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Source Modules:** [`core/fleet_manager.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/fleet_manager.py), [`actions/fleet_control.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/actions/fleet_control.py), [`frontend/src/components/office/AutonomousOfficeScreen.tsx`](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/office/AutonomousOfficeScreen.tsx), [`frontend/src/components/office/AgentDirectChatView.tsx`](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/office/AgentDirectChatView.tsx)  
> **Configuration:** [`config/fleet_agents.json`](file:///d:/anitgravity/zezo%20work/jarvis-57/config/fleet_agents.json)  
> **Target OS:** Windows 10/11 (Primary), macOS, Linux  

---

## 📖 Overview

The **Autonomous Fleet Management System** enables ZEZO to orchestrate a distributed team of specialized, autonomous sub-agents. Inspired by classic engineering room dynamics, ZEZO represents this multi-agent fleet visually as **The Scranton Office**—an interactive 2D pixel-art virtual floor where each specialist occupies a dedicated desk coordinate, maintains local state, executes coding and research workloads, and collaborates in real time.

Fleet execution features strict **Git worktree sandboxing**, **3-tier risk gates**, **keyword-driven role inference**, and **direct 1-on-1 chat channels** powered by Assistant-UI.

```mermaid
flowchart TD
    A["User Request:<br/>'Have Verve rebuild the navbar in Tailwind'"] --> B["Action Tool: fleet_control<br/>(actions/fleet_control.py)"]
    B --> C["FleetManager (core/fleet_manager.py)"]
    C --> D["Role & Specialty Inference<br/>(_infer_agent_defaults)"]
    D --> E["Security Risk Check<br/>(L0_READ_ONLY / L1_MUTATION / L2_DESTRUCTIVE)"]
    E --> F["Git Worktree Sandbox Creation<br/>(.agent_worktrees/<task_id>)"]
    F --> G["Execution Dispatch via Dedicated Engine<br/>(Antigravity / OpenCode / Kilo / Groq)"]
    G --> H["Scranton Office HUD State Streaming<br/>(AutonomousOfficeScreen.tsx)"]
    H --> I["Safe 4-Gate Teardown & Merge Lock"]

    classDef core fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff;
    class A,B,C,D,E,F,G,H,I core;
```

---

## 🏢 The Scranton Office & 2D Desk Grid

In the UI ([`frontend/src/components/office/AutonomousOfficeScreen.tsx`](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/office/AutonomousOfficeScreen.tsx)), the office is mapped to a calibrated 2D grid defined in [`core/fleet_manager.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/fleet_manager.py):

```python
OFFICE_DESK_COORDINATES: list[tuple[int, int]] = [
    (180, 160), (320, 160), (460, 160), (600, 160),
    (180, 280), (320, 280), (460, 280), (600, 280),
    (180, 400), (320, 400), (460, 400), (600, 400),
]
```

Each desk position reflects the agent's live operational status:
- **`idle`**: Agent sits quietly at desk; telemetry monitors are dim.
- **`working`**: Agent typing animation active; monitor glows with live terminal telemetry.
- **`reviewing`**: Paused for user verification or review gate.
- **`error` / `blocked`**: Visual alert state indicating failure or circuit breaker intervention.

---

## 🧑‍💻 Specialist Agent Roster

ZEZO includes an out-of-the-box roster of specialized agents defined in [`config/fleet_agents.json`](file:///d:/anitgravity/zezo%20work/jarvis-57/config/fleet_agents.json):

| Agent ID | Name | Role & Specialty | Default Engine / Tool | Risk Tier | Desk Coordinates |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MICHAEL`** | **Michael** | Lead Software Architect & Tech Lead (Structural planning, task breakdown) | `groq` (Llama 3.3 70B) | `L1_MUTATION` | (180, 160) |
| **`VERVE`** | **Verve** | Senior Frontend & UI Specialist (Tailwind, animations, design tokens) | `antigravity_run` | `L1_MUTATION` | (320, 160) |
| **`FLUX`** | **Flux** | Frontend Developer & Overflow Balancer (Component synthesis, UI fixes) | `antigravity_run` | `L1_MUTATION` | (320, 280) |
| **`AHMAD`** | **Nexus (Ahmad)** | Senior Full-Stack & Python Backend Specialist (FastAPI, Postgres, schemas) | `opencode_run` | `L2_DESTRUCTIVE` | (460, 160) |
| **`DWIGHT`** | **Dwight** | Senior Refactoring & QA Specialist (Test suites, audits, complexity reduction) | `kilo_run` | `L1_MUTATION` | (460, 280) |
| **`PAM`** | **Pam** | Design System & Token Architect (Token extraction, palette generation) | `extract_design_system` | `L0_READ_ONLY` | (320, 280) |
| **`DEVDYNAMO`**| **DevDynamo (Haider)** | Autonomous Full-Stack Engineer (End-to-end features, modern web apps) | `opencode_run` | `L1_MUTATION` | (180, 280) |
| **`KELLY`** | **Kelly** | Social & Deep Web Researcher (Reddit, YouTube, content extraction) | `agent_reach` | `L0_READ_ONLY` | (600, 160) |
| **`QUANTUM`** | **Quantum** | Deep Web Researcher & Technical Scraper (Documentation, whitepapers) | `kilo_run` | `L1_MUTATION` | (600, 280) |
| **`RECON`** | **Recon** | Deep Intelligence & OSINT Researcher (Autonomous multi-source research) | `agent_reach` | `L0_READ_ONLY` | (600, 400) |

---

## 🧠 Keyword-Driven Role Inference

When a user issues a high-level instruction without specifying an agent ID, ZEZO's `_infer_agent_defaults` analyzes the query keywords to automatically assign the appropriate specialist:

```python
def _infer_agent_defaults(role: str, specialty: str) -> Dict[str, Any]:
    text = f"{role} {specialty}".lower()

    # Research & Scraping → Kelly / Recon (agent_reach)
    if any(k in text for k in ("research", "web", "scrape", "transcript", "video", "youtube", "media")):
        return {"default_tool": "agent_reach", ...}

    # Frontend & Styling → Verve / Flux (antigravity_run)
    if any(k in text for k in ("frontend", "ui", "design", "css", "tailwind", "layout", "animation", "react")):
        return {"default_tool": "antigravity_run", ...}

    # QA & Refactoring → Dwight (kilo_run)
    if any(k in text for k in ("refactor", "qa", "test", "audit", "clean code", "bug hunt")):
        return {"default_tool": "kilo_run", ...}

    # Backend & Architecture → Ahmad / Nexus (opencode_run)
    return {"default_tool": "opencode_run", ...}
```

---

## 🛡️ Security Risk Tiers & Worktree Isolation

To ensure absolute codebase integrity, agents operate under strict permissions:

### 1. Risk Tiers
- **`L0_READ_ONLY`**: Agent may inspect code, search the web, analyze ASTs, and extract design tokens. File write/delete operations are permanently blocked.
- **`L1_MUTATION`**: Agent may write, edit, and create code files, but only within an isolated Git worktree.
- **`L2_DESTRUCTIVE`**: Agent may perform database migrations, system dependency installations, or file deletions. Requires explicit confirmation gates.

### 2. Git Worktree Sandbox (`core/git_sandbox.py`)
When a mutation task is dispatched:
1. ZEZO creates an isolated Git worktree under `.agent_worktrees/<task_id>/` on a dedicated branch (`agent/<clean_task_id>`).
2. The agent executes all edits, builds, and tests inside this quarantined directory.
3. Once the task succeeds, changes undergo a **4-gate safe teardown and merge check** guarded by `_merge_lock` before merging back into `main`.

---

## 💬 Direct 1-on-1 Chat Channels (`AgentDirectChatView.tsx`)

Users can click on any agent in the Scranton Office to open a dedicated, isolated conversational channel:
- **Independent Conversation Context:** Chats do not pollute the primary voice session memory.
- **Assistant-UI Thread:** Full markdown rendering, code block copy buttons, and turn-by-turn reasoning pills.
- **Dynamic Model Switching:** Allows overriding the agent's default LLM on the fly (e.g., switching between Gemini 3.7 Flash and Claude Sonnet 4.6).
- **Live Soul Editing:** The side panel allows editing the agent's `prompt_prefix`, allowed tools, and capabilities directly from the UI.
