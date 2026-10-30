# 📋 ZEZO Option 4 Implementation Plan: Minimalist Frontend, Dual-AI Skill Runner & Fleet Skills Integration

> **Project:** ZEZO Autonomous Desktop AI Operating System  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Status:** Production-Ready Architecture Implementation Blueprint (Post-Review Refined)  
> **Core Architecture:** Option 4 — Zero Frontend Over-Engineering, Dual-AI Skill Runner (Gemini Live + Groq LPU with Gemini Fallback) & Autonomous Fleet Skills Engine  

---

## 🎯 Executive Summary & Architectural Goals

The goal of this implementation is to turn ZEZO's declarative skills (`skills/*/SKILL.md`) into **fully autonomous, executable background workflows** without adding frontend bloat, without context token bloat, and without ever freezing the real-time voice pipeline.

### Core Principles:
1. **Zero Frontend Over-Engineering & Laser-Focused Skills Hub:** Keep the exact ReUI Skills Hub layout. Eliminate toggle switch confusion. Provide clean **Edit** and **Delete** actions on cards, a **+ Create Skill** button, slug format validation, and an intuitive slide-over drawer for plain Markdown SOP editing.
   - **Strict 3 Core Skills Policy:** The Skills Hub and `skills/` disk directory are pruned of all bloat to host **only 3 core production skills**:
     1. `website_build` (Production template scaffolding)
     2. `website_clone` (Converted from website cloner feature into a structured SOP)
     3. `generate_design_md` (Converted from design extractor into a standard token extraction SOP)
   - **Permanent Deletion of 10 Obsolete Skills:** All 10 legacy/redundant skills (`figma_helper`, `git_workflow`, `make_plan`, `office_suite`, `parallel_task_management`, `social_research`, `test_fastapi_deploy`, `web_research_pipeline`, `web_scraper`, `multi_agent_collaboration`) are **permanently deleted from disk** to ensure 0% codebase bloat.
2. **Dedicated Tools Management UI (Settings > Tools Tab):**
   - A dedicated **Tools** tab is added alongside Skills in `SettingsModal.tsx` (under the `WORKSPACE` section).
   - Exposes **15 User-Facing Tools** grouped into 5 intuitive categories with ReUI toggle switches (including `agent_reach` for Deep Social & Media Research).
   - **Engine Tools Managed Exclusively in Engines Tab:** Engine execution tools (`antigravity_run`, `opencode_run`, `kilo_run`) are **NOT** in the Tools Tab. They are directly linked to the **Engines Tab**. When an engine toggle is OFF, the corresponding runner is locked and inaccessible.
   - **Backend-Only Tools Protected:** Internal system infrastructure (`fleet_control`, `task_status`, `run_tool_batch`, `code_engines_status`, `ast_tool`, `recall_history`, `system_status`, `send_message`, `screen_processor`, `proactive`) are hidden from the UI with no user toggles to prevent accidental system breakage.
   - **Strict Execution Gate:** In `core/action_loader.py`, `ActionRegistry.run()` enforces `rec.enabled` checks and persists state in `config/tools_state.json`. Disabled tools return an explicit blocked execution error.
3. **Dual-AI Separation of Concerns:**
   - **Voice Brain (Google Gemini Live):** Stays 100% focused on real-time 24kHz audio dialog. Dispatches skill tasks in `<50ms` and continues talking. Never blocks on long tool execution loops.
   - **Background Skill Runner (Groq LPU + Gemini Fallback):** Executes the skill SOP in a non-blocking background thread at 500–800 tokens/sec, sequentially calling atomic Python tools (`actions/*.py`).
4. **Autonomous Fleet Agents Skills Integration (Separate & Isolated):**
   - **Agent-Specific Skills:** Skills assigned to a fleet agent (e.g. `VERVE`, `FLUX`, `MICHAEL`) work **only** for that agent and do not bleed into other agents.
   - **Agent Skill Selection in UI:** In the existing Fleet Agent Configuration Modal, users can check/uncheck which skills the agent has access to via a clean ReUI badge checklist. No UI redesign; only polish and bug fixes.
   - **Engine Consistency:** When an agent executes a skill, it strictly runs through that agent's configured engine (`antigravity` -> `agy.exe`, `opencode` -> `opencode_run`, etc.).
   - **Direct CLI Execution:** Native CLI binaries (like `agy.exe`) directly receive and follow the assigned `SKILL.md` instructions in their isolated Git worktree.
5. **Deterministic Decision Engine ("Self vs Agent Delegation"):**
   - **Direct Action Automation (Groq LPU):** If the skill covers system control, scraping, research, or git workflows, ZEZO executes it directly via Groq LPU.
   - **Heavy Code Synthesis (Fleet Specialist):** If the skill involves complex UI/backend engineering (e.g. `website_build`), ZEZO delegates the task directly to the specialized Fleet Agent.
6. **Smart Tool Scoping (Anti-Token Bloat):** Do NOT dump all action schemas into Groq. Dynamically scope tool declarations to the relevant tools referenced in the `SKILL.md` (3–5 tools), keeping prompt overhead minimal and accuracy high.
7. **Resilient Mid-Pipeline Fallback:** If Groq encounters rate-limiting (429) or network drop mid-pipeline, Gemini Flash resumes execution from the exact step where Groq paused without repeating earlier steps or overwriting files.
8. **Strict Hands-Off Voice Rule:** Live audio loops and WebSocket streaming in `main.py` remain untouched. New capabilities plug in cleanly via `actions/run_skill.py` auto-discovered by `core.action_loader`.
9. **Pure Natural Engine Bridges (Antigravity, OpenCode, Kilo Code):** Eliminate all prompt micromanagement, archetype guessing, synthetic `<design-context>` injection, greenfield gates, and slot hacks (`<!-- SLOT: -->`). All three engines operate as transparent, human-like CLI bridges: passing the user's pure natural prompt (with optional `SKILL.md` guidelines) and `project_path` directly to the native CLI binaries (`agy.exe`, `opencode.exe`, `kilo.exe`). Permanent removal of bloated design generators (`core/ai_design_generator.py`, `core/design_cache.py`, `core/design_resolver.py`, `core/master_template_builder.py`, `core/design_md_generator.py`).

---

## 🗺️ Architectural Topology & Module Interconnections

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (React + ReUI)                               │
│                   frontend/src/components/settings/SkillsSettingsTab.tsx         │
│                   frontend/src/components/settings/ToolsSettingsTab.tsx          │
│                   frontend/src/components/office/AgentConfigModal.tsx             │
│                                                                                  │
│   • Skills Hub: 3 Core Skills (website_build, website_clone, generate_design_md) │
│   • Tools Tab: 14 User-Facing Tools categorized with ReUI toggle switches         │
│   • Engines Tab: Engine runners (antigravity, opencode, kilo) managed directly   │
│   • Fleet Agent Modal: Clean multi-select checklist for agent.allowed_skills      │
│   • Direct REST APIs: /api/skills/*, /api/tools/*, /api/fleet/*                  │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │ REST API (/api/skills/* & /api/tools/*)
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND DISK REGISTRY & API                              │
│                    core/ui_server.py & core/skill_loader.py                      │
│                                                                                  │
│   • Hot-reloads skills from disk (skills/*/SKILL.md)                             │
│   • Validates input through core/skill_scanner.py                                │
│   • Persists sanitized YAML frontmatter + Markdown body                          │
└──────────────────────────────────────────────────────────────────────────────────┘

                                      ▲
                                      │ Ingests SKILL.md
                                      ▼

┌──────────────────────────────────────────────────────────────────────────────────┐
│                         VOICE ORCHESTRATION (Brain 1)                            │
│                                   main.py                                        │
│                                                                                  │
│   • Gemini Live bidirectional audio WebSocket loop (NEVER BLOCKS)                │
│   • Dispatches `run_skill` or `fleet_control` tool call in <50ms                 │
│   • Instant conversational spoken confirmation to Hamza Bukhari                  │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │ Submits background task via TaskManager.submit()
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│              SELF-EXECUTION vs. FLEET DELEGATION DECISION ROUTER                 │
│                                                                                  │
│         Does request come from Agent Desk OR is it a heavy coding task?          │
│                      ┌──────────────────┴──────────────────┐                     │
│                      ▼ NO (Tool Automation)                ▼ YES (Code/Design)   │
│         [Groq LPU Background Runner]             [Fleet Agent Dispatcher]        │
│             (core/skill_runner.py)              (core/fleet/dispatcher.py)       │
│                      │                                     │                     │
│                      ▼                                     ▼                     │
│         Calls atomic Python tools             Spawns Agent CLI in Worktree       │
│         (actions/web_crawl.py, etc.)          (tools/antigravity/agy.exe)        │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 Section 1: Detailed Frontend Changes

### 1.1 Target File: `frontend/src/components/settings/SkillsSettingsTab.tsx`

#### 1. What to Remove (Cleanup & Simplification)
- **Remove Toggle Switches:** Delete the `<Switch />` components on each skill card and inside the slide-over drawer header. Eliminates the false concept of "disabling" a skill when skills are simply declarative SOPs.
- **Remove Batch Toggle Buttons:** Delete the `Enable All` and `Reset` buttons from the header.
- **Remove Hardcoded `DEFAULT_SKILLS` Array:** Delete the ~260 lines of static hardcoded skills (lines 42–266). Instead, use a lightweight 2-line placeholder or loading state while `/api/skills` loads live from disk.
- **Remove Hacky Filter Artifacts:** Remove all hardcoded string checks:
  ```typescript
  // DELETE ALL INSTANCES OF:
  s.id !== 'custom_skill_10' && s.id !== 'hamza_taste'
  ```
- **Remove Conflicting `localStorage` State:** Stop storing enable/disable overrides in `localStorage`. The single source of truth is the backend filesystem.

#### 2. What to Add & Refactor
- **Header Actions:**
  - Add a clean `[+ Create Skill]` button using ReUI Button primitive (`variant="default"`).
  - Clicking this opens the slide-over drawer with a blank skill template ready to author.
- **Skill Cards Grid (ReUI Primitives):**
  - **Left Section:** Domain colored icon, Skill Name, Domain badge, Description snippet.
  - **Right Section (Clean Actions):**
    - `Edit` button (Pencil icon) -> Opens slide-over drawer with the skill loaded.
    - `Delete` button (Trash icon) -> Protected for core system skills:
      * Core system skills (`website_build`, `website_clone`, `generate_design_md`) have Delete disabled with tooltip: *"System core skill cannot be deleted"*.
      * Custom/user skills open ReUI Confirm Dialog (`confirm-dialog.tsx`): *"Are you sure you want to delete this skill?"* -> Calls `api.deleteSkill(skill.id)` and removes card.
  - Clicking anywhere on the card opens the drawer for quick inspection.
- **Slide-Over Drawer Enhancements:**
  - Drawer Header: Skill Title, Domain badge, and a Close (X) button. (No toggle switch).
  - Drawer Metadata Inputs:
    - **Skill Name Input:** Includes auto-slug formatter (`my cool skill` -> `my_cool_skill`) and validates format against regex `^[a-z0-9_]{1,40}$`.
    - Domain / Category dropdown (`Coding`, `Design`, `Research`, `System`, `Orchestration`).
    - Short Description input.
  - Markdown SOP Editor:
    - Textarea with monospace font for editing `SKILL.md` directives.
    - Two tabs: **Edit Directives** and **Preview** (renders markdown formatting).
  - Drawer Footer:
    - `[Discard]` button (closes drawer without saving).
    - `[Save Skill]` button (calls `api.saveSkill`, triggers backend security scan and hot-reload, shows green checkmark toast).

---

### 1.2 Target File: `frontend/src/components/settings/ToolsSettingsTab.tsx` (Dedicated Tools Management UI)
**New Component:** `frontend/src/components/settings/ToolsSettingsTab.tsx`  
**Host File:** `frontend/src/components/settings/SettingsModal.tsx` (Add `tools` item to `WORKSPACE` nav section)

#### 1. Architecture & Design Specifications
- **Clean ReUI Design:** Group 15 user-facing tools into 5 collapsible accordions or category sections:
  1. **Research & Intelligence:** `agent_reach` (YouTube transcripts, Reddit threads, Twitter/X, GitHub repos, TikTok/Instagram audio, multi-source research aggregator)
  2. **Browser & Web Automation:** `browser_control`, `web_search`, `web_read_page`
  3. **Desktop & System Control:** `computer_control`, `desktop_control`, `computer_settings`, `open_app`
  4. **Files & Coding Helpers:** `file_controller`, `file_processor`, `quick_snippet`
  5. **Lifestyle & Utilities:** `reminder`, `weather_report`, `flight_finder`, `youtube_video`
- **Tool Card Anatomy:**
  - Left: Tool icon, human-readable name (e.g. "Desktop Automation" instead of raw identifier `computer_control`), single-line purpose description.
  - Right: ReUI `<Switch />` toggle button showing current state (`enabled` vs `disabled`).
- **Engine Tools Separation Rule:**
  - Engine runners (`antigravity_run`, `opencode_run`, `kilo_run`) are **NOT** rendered here. They are managed exclusively from the **Engines Tab**.
- **Backend-Only Tools Rule:**
  - Internal orchestration tools (`fleet_control`, `task_status`, `run_tool_batch`, etc.) are hidden from the UI to protect session stability.
- **API Interaction:**
  - On mount, fetches active tool statuses via `GET /api/tools`.
  - On toggle switch change, calls `POST /api/tools/{name}/toggle` and updates local state optimistically.

---

### 1.3 Target File: `frontend/src/components/office/AgentConfigModal.tsx` & Agent Desk Chat

#### 1. What to Improve (Zero Redesign — Polish Only)
- Preserve the existing ReUI layout of the Agent Configuration modal (desk assignment, color, avatar, engine, risk tier).
- **Add Skills Access Checklist (`allowed_skills`):**
  - Under the Agent Engine & Tools section, render a clean ReUI badge multi-select checklist showing all active skills from `/api/skills` (`website_build`, `website_clone`, `generate_design_md`).
  - When configuring an agent (e.g., `VERVE`), the user can check/uncheck skills:
    ```
    Assigned Agent Skills:
    [✓] website_build    [✓] website_clone    [✓] generate_design_md
    ```
  - Saves directly to `config/fleet_agents.json` under `fleet[agent_id].allowed_skills`.
  - These skills are strictly scoped: only the selected agent receives them in their prompt/CLI context.

#### 2. Direct Pass-Through Agent Desk Chat (Zero Regex Interception)
- In `core/ui_server.py`, completely eliminate `_is_actionable_task(prompt)` regex guessing.
- When the user sends a message in an agent's desk chat (e.g., `VERVE` configured with `antigravity` engine):
  1. The user's prompt is routed **directly and verbatim** to the agent's configured engine CLI (`tools/antigravity/agy.exe`).
  2. The CLI's live stdout/stderr streams straight to the Agent Desk terminal/chat window.
  3. Zero intermediate prompt manipulation, zero fallback LLM diversion, and zero hardcoded task branching. ZEZO acts purely as a transparent window.

---

## 📊 Section 2: Master Architecture Tables (Tools & Skills Taxonomy)

### 🛠️ Table 1: Tools UI (Settings > Tools Tab)
*15 user-facing tools displayed in collapsible categories with individual ReUI `<Switch />` toggles:*

| UI Display Name | Backend Identifier | Category | UI Toggle Behavior | Description & Scope |
| :--- | :--- | :--- | :---: | :--- |
| **Deep Social Research** | `agent_reach` | Research & Intelligence | ✅ Toggle | Deep extraction: YouTube transcripts, Reddit threads, Twitter/X, GitHub repos, TikTok/Instagram audio, and cross-platform reports |
| **Browser Control** | `browser_control` | Web & Automation | ✅ Toggle | Playwright automated browser (clicks, typing, forms) |
| **Web Search** | `web_search` | Web & Intelligence | ✅ Toggle | DuckDuckGo live internet search |
| **Web Page Reader** | `web_read_page` | Web & Intelligence | ✅ Toggle | Web page DOM scraping and reading |
| **Desktop Automation** | `computer_control` | Desktop & OS | ✅ Toggle | Native mouse clicks, typing, screen coordinates |
| **Window Manager** | `desktop_control` | Desktop & OS | ✅ Toggle | Window focus, minimize, maximize, resize |
| **System Settings** | `computer_settings` | Desktop & OS | ✅ Toggle | OS volume, brightness, Wi-Fi, bluetooth control |
| **App Launcher** | `open_app` | Desktop & OS | ✅ Toggle | Launch local applications (Chrome, VS Code, etc.) |
| **File Controller** | `file_controller` | Files & Code | ✅ Toggle | Read, write, create, list local directory files |
| **Batch File Processor**| `file_processor` | Files & Code | ✅ Toggle | Bulk file analysis, transforms, batch updates |
| **Quick Snippets** | `quick_snippet` | Files & Code | ✅ Toggle | Save, recall, and search code snippets |
| **Smart Reminders** | `reminder` | Daily Utilities | ✅ Toggle | Set alarms, countdowns, and system reminders |
| **Weather Forecast** | `weather_report` | Daily Utilities | ✅ Toggle | Live atmospheric metrics and forecasts |
| **Flight Finder** | `flight_finder` | Daily Utilities | ✅ Toggle | Search flight availability and airline schedules |
| **YouTube Player** | `youtube_video` | Daily Utilities | ✅ Toggle | Search and stream YouTube audio/video |

> **Backend Enforcement:** When a tool toggle is switched **OFF**, `ActionRegistry.run()` blocks execution and returns: `"Execution Blocked: Tool '{name}' is currently disabled in Settings."`

---

### ⚙️ Table 2: Engine Tools & Transparent Bridge Endpoints (Settings > Engines Tab)
*Engine execution tools are linked directly to engine status in Settings > Engines. Includes "Test Bridge" connectivity button:*

| Engine Name | Backend Tool Identifier | Binary Location | Engine Toggle Behavior | Bridge Test Endpoint | Role & Execution Sandbox |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Google Anti-Gravity** | `antigravity_run` | `tools/antigravity/agy.exe` | ✅ Engine Toggle | `POST /api/engines/antigravity/test` | Native autonomous agent CLI. When toggled OFF, `agy.exe` binary execution is locked. |
| **OpenCode Interpreter**| `opencode_run` | `opencode` / `opencode.exe` | ✅ Engine Toggle | `POST /api/engines/opencode/test` | Multi-file code generation sandbox. When toggled OFF, OpenCode execution is locked. |
| **Kilo Autonomous Runner**| `kilo_run` | `kilo` / `kilo.exe` | ✅ Engine Toggle | `POST /api/engines/kilo/test` | Free model code refactor engine. When toggled OFF, Kilo CLI access is disabled. |

#### 🏷️ Table 2.1: Synchronized Active Engine Models (Zero Dead / Fake Models)
*Only verified, live-responding models are exposed in UI dropdowns; all legacy/dead `gemini-2.5-*` / `2.0` / `1.5` strings are completely purged:*

| Engine | Default Recommended Model | Verified Active Model Options in UI | Obsolete Models Purged (404 / Dead) |
| :--- | :--- | :--- | :--- |
| **Google Anti-Gravity** | `gemini-3.8-flash-medium` | • `gemini-3.8-flash-high`<br>• `gemini-3.8-flash-medium`<br>• `gemini-3.8-flash-low`<br>• `gemini-3.6-flash`<br>• `gemini-3-flash-preview` | ❌ `gemini-2.5-flash`<br>❌ `gemini-2.5-flash-lite`<br>❌ `gemini-2.0-flash`<br>❌ `gemini-1.5-pro` |
| **OpenCode** | `opencode/glm-5.3-flash-free` | • `opencode/glm-5.3-flash-free`<br>• `opencode/big-pickle`<br>• `opencode/nemotron-3-ultra-free`<br>• `opencode/mimo-v2.6-flash-free` | ❌ Unregistered Zen models |
| **Kilo Code** | `kilo/kilo-auto/free` | • `kilo/kilo-auto/free`<br>• `kilo/deepseek/deepseek-chat:free`<br>• `kilo/stepfun/step-3.7-flash:free`<br>• `kilo/qwen/qwen-2.5-coder-32b-instruct:free` | ❌ Defunct community tags |

---

### 🔒 Table 3: Backend-Only System Tools (UI Hidden / No Toggle)
*Internal system infrastructure tools hidden from user toggles to safeguard session stability:*

| Backend Identifier | File Location | System Protection Rationale (Why Hidden?) |
| :--- | :--- | :--- |
| `fleet_control` | `actions/fleet_control.py` | Essential messaging bus connecting ZEZO to Fleet Agents (`VERVE`, `FLUX`, etc.). |
| `task_status` | `actions/task_status.py` | Required by UI task drawer and background async tasks for progress tracking. |
| `run_tool_batch` | `actions/run_tool_batch.py` | Internal multi-tool batch execution pipeline for Dual-AI Groq runner. |
| `code_engines_status` | `actions/code_engines_status.py`| Powers live health and connection badges in the Engines Settings tab. |
| `ast_tool` | `actions/ast_tool.py` | Internal Python syntax validation and AST code inspection engine. |
| `recall_history` | `actions/recall_history.py` | Core conversation context and episodic memory recall infrastructure. |
| `system_status` | `actions/system_monitor.py` | Internal hardware metrics (CPU/RAM/GPU) diagnostic reader. |
| `send_message` | `actions/send_message.py` | Direct agent-to-agent message transport bus. |
| `reverse_engineer` | `actions/reverse_engineer.py` | Internal binary inspection helper. |
| `proactive.py` / `screen_processor.py` | `actions/*.py` | Background screen grab and proactive visual monitoring threads. |

---

### 📚 Table 4: Skills UI (Settings > Skills Tab / Skill Hub)
*Skill Hub displays strictly 3 active Core Skills. Toggle switches are removed; cards provide Edit, Delete (protected for core), and click-to-open drawer:*

| Skill ID | Display Title | Category | UI Actions | Drawer Content | SOP Purpose |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`website_build`** | **Website Builder** | Frontend Dev | ✏️ Edit <br> 🔒 Protect | Markdown SOP | Instant production template scaffolding (Next.js/Tailwind/React). |
| **`website_clone`** | **Website Cloner** | Web Dev | ✏️ Edit <br> 🔒 Protect | Markdown SOP | Full website cloning workflow: asset scraping, HTML structure, styling. |
| **`generate_design_md`** | **Generate Design MD**| Design & UI | ✏️ Edit <br> 🔒 Protect | Markdown SOP | Extracts live URL design tokens (colors, fonts, shadows) into `DESIGN.md`. |

---

### 🗑️ Table 5: Permanently Deleted Skills (Wiped Clean from Disk)
*All 10 legacy/redundant skill folders permanently removed from `skills/` to eliminate codebase bloat:*

| Skill Directory | Former Purpose | Final Decision | Action |
| :--- | :--- | :---: | :--- |
| `skills/figma_helper/` | Figma variable reader | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; syntax defect (missing YAML delimiters). |
| `skills/git_workflow/` | Git branch/commit automation | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; redundant with native agent engine capabilities. |
| `skills/make_plan/` | Multi-step task planner | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; internal autonomous engines handle planning. |
| `skills/parallel_task_management/`| Duplicate task planner | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; 14-line redundant duplicate of `make_plan`. |
| `skills/office_suite/` | Markdown & Office docs helper | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; removed to keep Skill Hub laser-focused. |
| `skills/social_research/` | Social media sentiment scraper | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; niche SOP removed from active hub. |
| `skills/test_fastapi_deploy/` | FastAPI deploy placeholder | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; incomplete 3-bullet placeholder file. |
| `skills/web_research_pipeline/`| Web research workflow | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; covered by atomic `web_search` and `web_read_page`. |
| `skills/web_scraper/` | Web data scraper | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; covered by `website_clone` and atomic readers. |
| `skills/multi_agent_collaboration/`| Multi-agent router SOP | 🗑️ **PERMANENTLY DELETED** | Wiped from disk; stale agent roster (`Ali`, `Oscar`) replaced by dispatcher. |

---

## ⚙️ Section 3: Detailed Backend Changes

### 3.1 The Decision Engine: "Self-Execution vs. Dynamic Fleet Delegation"
**Location:** [`actions/run_skill.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/run_skill.py) & [`core/fleet/dispatcher.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/dispatcher.py)

How ZEZO decides whether to execute a skill directly or delegate to an active Fleet Agent:

```
                          [Task Request / Skill Invocation]
                                        │
            ┌───────────────────────────┴───────────────────────────┐
            ▼                                                       ▼
   [From Agent Desk Chat]                                 [From Main ZEZO Voice]
   (User talking to specific agent)                       ("Zezo, build/clone a site")
            │                                                       │
            ▼                                                       ▼
  Strict Bound Execution                                  Inspect SKILL.md & Live Fleet
  - Uses that agent's allowed_skills                      - Is delegation: fleet specified?
  - Uses that agent's configured engine                   - Does any active agent have this skill?
  - Spawns agent CLI in Git worktree                                │
                                                 ┌──────────────────┴──────────────────┐
                                                 ▼ NO (Or no agent assigned)           ▼ YES (Active agent found)
                                        [Self-Execution]                      [Fleet Delegation]
                                        - Groq LPU Background Runner          - Selects assigned live agent
                                        - Sub-second tool-calling             - Injects SKILL.md into agent
                                        - Calls atomic Python actions         - Runs agent engine (agy.exe)
```

1. **Rule 1 (Direct Agent Origin):** If a command is issued inside an agent's individual chat/desk window, execution is **strictly bound to that agent**. It only sees its own `agent.allowed_skills` and only executes via its configured `agent.engine`.
2. **Rule 2 (Main Voice Tool Automation):** If the skill is an automation, data pipeline, research, or system task (e.g., `web_research_pipeline`, `git_workflow`, `social_research`), ZEZO's **Groq LPU Background Runner executes it directly**.
3. **Rule 3 (Dynamic Fleet Delegation — Zero Hardcoding):** If the skill involves complex code generation or visual styling (e.g., `website_build`), ZEZO dynamically queries `config/fleet_agents.json` to find which **live agent** has that skill assigned. If found, it delegates to that agent's configured engine CLI (`agy.exe`). If no active agent has the skill, ZEZO reports this honestly rather than hallucinating deleted agents.

---

### 3.2 The Pure Natural Engine Bridge Architecture (Antigravity, OpenCode, Kilo Code)
**Location:** [`actions/antigravity_agent.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/antigravity_agent.py), [`actions/opencode_agent.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/opencode_agent.py), [`actions/kilo_agent.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/kilo_agent.py), & [`core/antigravity_runner.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/antigravity_runner.py)

#### 1. The Core Philosophy: "Zero Micromanagement, Transparent Human-like Bridge"
In the legacy codebase, an extreme amount of over-engineering crippled Antigravity:
- Hardcoded archetype guessing (`detect_archetype`: `PORTFOLIO`, `DASHBOARD`, `SURGICAL_EDIT`)
- Synthesizing 200 lines of fake prompt boilerplate (`synthesize_prompt`)
- Injecting artificial `<design-context>` XML tags
- Generating synthetic `DESIGN.md` and forcing `master-template.html` with slot hacks (`<!-- SLOT:HERO_START -->`)
- Greenfield restriction gates (`check_greenfield_gate`) blocking natural prompt execution

**The New Unified Bridge Paradigm:**
Antigravity, OpenCode, and Kilo Code are state-of-the-art autonomous coding agents. They do not need Python scripts micromanaging their thoughts or hacking HTML files with fake slots.
ZEZO interacts with these engines **exactly like a human software engineer**:
1. Human opens terminal inside `project_path`.
2. Human runs binary (`agy.exe`, `opencode.exe`, or `kilo.exe`).
3. Human gives a **pure, natural prompt** (e.g. *"Build a modern portfolio for Hamza Bukhari with dark mode and clean typography"*).
4. The autonomous CLI autonomously inspects the workspace, creates files, runs tests, and completes the task.

#### 2. The Universal Bridge Contract
All three engine action tools (`antigravity_run`, `opencode_run`, `kilo_run`) adopt the exact same transparent bridge pattern:

```python
def run_engine_bridge(
    binary_name: str,          # 'agy.exe', 'opencode.exe', or 'kilo.exe'
    prompt: str,               # Untouched natural prompt (with optional SKILL.md guidelines)
    project_path: Path,        # Target workspace directory
    model: Optional[str] = None, # Engine model configured in Settings
    task_ctx: Optional[TaskContext] = None,
) -> TaskResult:
    """
    Universal Transparent CLI Bridge for Antigravity, OpenCode, and Kilo Code.
    Zero prompt manipulation. Zero fake slots. Zero hardcoded archetype branching.
    """
    project_path.mkdir(parents=True, exist_ok=True)
    bin_path = _find_engine_bin(binary_name)
    
    cmd = [str(bin_path)]
    if model:
        cmd.extend(["--model", model])

    # Pass natural prompt to the CLI via stdin or arguments
    process = subprocess.Popen(
        cmd,
        cwd=str(project_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_WIN_HIDE
    )
    
    # Stream telemetry lines directly to HUD / task_manager
    stdout, stderr = process.communicate(input=prompt)
    return TaskResult(success=(process.returncode == 0), output=stdout)
```

#### 3. How Skills Integrate Naturally with Engine Bridges
When ZEZO or a Fleet Specialist (e.g. `VERVE`) executes a declarative skill like `website_build` via Antigravity CLI:
- ZEZO does **NOT** synthesize fake templates or inject `<!-- SLOT: -->` markers.
- ZEZO simply prepends the plain Markdown SOP from `skills/website_build/SKILL.md` to the user's task prompt:
  ```
  [User Project Objective]
  Build a modern portfolio website for Hamza Bukhari.

  [Skill Guidelines: skills/website_build/SKILL.md]
  - Follow clean typography rhythm and high contrast.
  - Deliver responsive single-file HTML or React 18 component.
  - Zero placeholder dummy names (use authentic user details).
  ```
- The native engine CLI receives this single, coherent natural directive and executes it autonomously just like a human senior developer reading an engineering SOP!

---

### 3.3 New Core Subsystem: `core/skill_runner.py` (Self-Execution Engine)
**File to Create:** `core/skill_runner.py`  
**Responsibility:** The execution engine for declarative skills running directly under ZEZO.

#### Core Implementation Specifications:
1. **Class `SkillRunner`:**
   - Accepts `task_id`, `skill_name`, `user_params`, `context`.
   - Ingests the full `SKILL.md` via `core.skill_loader.get_skill_registry().read_skill(skill_name)`.
   - **Smart Tool Scoping:** Ingests only the 3–5 candidate tools referenced in the `SKILL.md` body to avoid Groq context bloat.
2. **Dual-AI Tool-Calling Engine:**
   - **Primary Engine:** Calls Groq LPU (`llama-3.3-70b-versatile`) via `core.llm_client.call_groq_tools(...)`.
   - **Stateful Fallback Engine:** Maintains an in-memory execution state ledger: `completed_steps = []`. If Groq encounters rate limits (429) or timeouts, it seamlessly hands over `completed_steps` to `gemini-3.8-flash` so it **resumes from the current step** without restarting from step 1.
3. **Output Truncation & Memory Guard:**
   - Large tool outputs are saved to disk in the task output directory.
   - Summarized/truncated outputs (max 1,500 characters) are fed back into the LLM conversation history.
4. **Task Lifecycle & Error Safety:**
   - Submits worker via `task_manager.submit("run_skill", worker_fn, params)`.
   - Updates `task_manager.report(progress=0.25, message="...")` on every completed step.

---

### 3.4 New Action Tool: `actions/run_skill.py`
**File to Create:** `actions/run_skill.py`  
**Responsibility:** Clean entry point for Gemini Live and user commands to invoke any declarative skill.

#### AGENTS.md Rule 4 Compliance:
Exports `TOOL` dictionary and `handler(parameters: dict, **kwargs)`:
```python
TOOL = {
    "name": "run_skill",
    "description": "Execute a declarative skill/protocol from skills/ in the background (e.g., 'website_build', 'website_clone', 'generate_design_md').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "skill_name": {
                "type": "STRING",
                "description": "The exact name of the skill to execute (e.g., 'website_build', 'website_clone', 'generate_design_md').",
            },
            "parameters": {
                "type": "OBJECT",
                "description": "Optional parameters to pass to the skill (e.g. url, repo_path, query, prompt).",
            },
        },
        "required": ["skill_name"],
    },
    "handler": run_skill_handler,
}
```

#### Handler Behavior:
- Checks if skill exists in `get_skill_registry()`. If not found, returns list of available skills.
- Checks if skill is configured for **Fleet Delegation** (e.g. `website_build`) -> routes to `core.fleet.dispatcher.FleetDispatcher.dispatch_task()`.
- Otherwise routes to **Self-Execution** -> submits to `core.task_manager.get_task_manager().submit("run_skill", worker_fn, params)`.
- Returns in **<50ms** with concise conversational response:
  `"Started '{skill_name}' in the background (Task ID #{task_id}). You can check progress on the HUD."`

---

### 3.5 LLM Client Tool Calling: `core/llm_client.py`
**File to Modify:** `core/llm_client.py`

#### What to Add:
- **Function `call_groq_tools(...)`:**
  - Implements native OpenAI-compatible tool calling on `https://api.groq.com/openai/v1/chat/completions`.
  - Sends `tools=[{"type": "function", "function": {...}}]` and `tool_choice="auto"`.
  - Parses response `message.tool_calls` into standardized `{name, arguments}` format.
  - Enforces low latency timeouts (`timeout=25s`).
  - Raises standard exceptions on failure to trigger the Gemini Flash fallback in `core/skill_runner.py`.

---

### 3.6 Skill Loader Cleanup: `core/skill_loader.py`
**File to Modify:** `core/skill_loader.py`

#### What to Clean Up:
- Remove obsolete hardcoded exclusions:
  ```python
  # Change:
  EXCLUDED_SKILL_NAMES = {"antigravity_agent", "kilo_code", "opencode", "custom_skill_10", "hamza_taste"}
  # To:
  EXCLUDED_SKILL_NAMES = {"antigravity_agent", "kilo_code", "opencode"}
  ```
- Ensure `save_learned_skill` and `delete_skill` correctly update `self._last_signature` and trigger hot-reload notifications so UI updates immediately without restarts.

---

### 3.7 Action Registry Execution Gate & State Persistence: `core/action_loader.py`
**Files to Modify:** [`core/action_loader.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/action_loader.py) & [`core/ui_server.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/ui_server.py)

#### 1. Seal Execution Gate in `ActionRegistry.run()`:
```python
# In core/action_loader.py around line 190 in ActionRegistry.run():
rec = self._actions.get(name)
if not rec:
    return f"Error: Tool '{name}' not found."
if not rec.enabled:
    return f"Execution Blocked: Tool '{name}' is currently disabled in Settings. Enable it in Settings > Tools to use this capability."
```

#### 2. Persistent Tool States:
- Add `load_tool_state()` and `save_tool_state()` in `ActionRegistry`, reading/writing to `config/tools_state.json`.
- On startup, disabled tools from `config/tools_state.json` have `rec.enabled = False`.

#### 3. Tools REST Endpoints in `core/ui_server.py`:
- `GET /api/tools`: Returns list of 14 user-facing tools with their enabled/disabled state, human names, and categories.
- `POST /api/tools/{name}/toggle`: Toggles tool state, persists to `config/tools_state.json`, and updates active `ActionRegistry`.

---

### 3.8 Skills Declarative Conversions
The website cloner and design extractor features are transformed from fragmented tools into clean, declarative procedural skills. Along with `website_build`, they constitute ZEZO's 3 core skills.

---

### 3.9 Direct Agent Desk Chat & Engine Test Endpoints: `core/ui_server.py`
**File to Modify:** `core/ui_server.py`

#### 1. Eliminate Regex Interception in Agent Chat (`_fleet_chat_handler`):
- Strip the `_is_actionable_task(prompt)` regex heuristic that previously diverted non-matching prompts to generic fallback LLMs.
- When an agent is selected in the Office Desk UI, the user's prompt is routed **directly and verbatim** to `fleet_manager.dispatch_task(agent.id, prompt)` using that agent's configured engine (`antigravity_run`, `opencode_run`, `kilo_run`).
- The native engine's stdout/stderr is returned and streamed directly to the desk chat interface.

#### 2. Engine Bridge Test Endpoint (`POST /api/engines/{engine}/test`):
- Expose a dedicated connectivity test endpoint:
  ```python
  @app.router.post("/api/engines/{engine}/test")
  async def _engine_test_handler(request: web.Request) -> web.Response:
      engine_name = request.match_info["engine"] # 'antigravity', 'opencode', 'kilo'
      # Spawns a 2-second non-blocking test ping through run_engine_bridge
      # Returns {"success": True, "engine": engine_name, "latency_ms": 45, "binary": bin_path}
  ```
- Powers the "Test Bridge" button in the Settings > Engines UI tab with real-time visual feedback (Connected badge / Error toast).

---

### 3.10 Dynamic Fleet Management & Ghost Agent Elimination Architecture
**Files to Modify:** [`core/fleet/registry.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/registry.py), [`core/fleet/dispatcher.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/dispatcher.py), [`core/fleet/orchestrator.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/orchestrator.py), [`actions/fleet_control.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/fleet_control.py), [`core/ui_server.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/ui_server.py), and [`main.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/main.py)

#### 1. Forensic Root Cause Analysis: The "Ghost Agent Bug"
In the legacy codebase, deleting an agent from the frontend left phantom ghost agents permanently haunting the system because of hardcoded names and fallback fabrications:
- `core/fleet/registry.py:298`: `if agent_id in ("OSCAR", "JIM", "STANLEY", "CREED", "ANGELA", "TOBY", "KELLY"): return FleetAgent(...)` ➔ **Fabricated in-memory agents on the fly!**
- `core/fleet/registry.py:270-324`: Hardcoded `role_map = {"frontend": "VERVE", "backend": "AHMAD", ...}`, `alias_map = {"ALI": "VERVE", "HAIDER": "FLUX"}`, and fallback lines returning `VERVE` or `FLUX` or `AHMAD` regardless of whether they were deleted.
- `main.py:1511`: Hardcoded system prompt: `(VERVE <-> FLUX for frontend) and immediately invoke fleet_control...` ➔ Gemini Live's audio brain was instructed to dispatch to Verve even when Verve was deleted from disk.
- `core/ui_server.py:1106`: `target_agent_id = agent.id if agent else "VERVE"`.
- `actions/fleet_control.py:50`: `is_web_agent = canonical_agent_id in ("VERVE", "FLUX") or agent_id.upper() in ("VERVE", "FLUX", "ALI", "HAIDER")`.

#### 2. The Dynamic Single-Source-of-Truth Contract (`config/fleet_agents.json`)
1. **Zero Hardcoded Names in Python:**
   - Strip all static references to `VERVE`, `FLUX`, `ALI`, `HAIDER`, `AHMAD`, `DWIGHT`, `PAM`, `OSCAR`, `KELLY`, `JIM`, `STANLEY`, `CREED`, `ANGELA`, `TOBY` across all dispatcher, registry, and action files.
2. **Permanent Agent Deletion:**
   - When a user deletes an agent via `POST /api/fleet/delete_agent`:
     * It is removed from `self.agents` dictionary.
     * It is permanently deleted from `config/fleet_agents.json`.
     * Its active Git worktree directory is torn down.
     * **Zero Phantom Survival:** It is never re-created in-memory. If it is deleted, it is completely gone.
3. **Dynamic Capability Resolution (Not Name Matching):**
   - Instead of static dictionaries (`"frontend" -> "VERVE"`), the dispatcher dynamically queries active agents based on their assigned `allowed_skills` and `role`:
     ```python
     def resolve_agent_for_skill(self, skill_name: str) -> Optional[FleetAgent]:
         """Dynamically resolve which live agent currently possesses the assigned skill."""
         for agent in self.agents.values():
             if skill_name in (agent.allowed_skills or []):
                 return agent
         return None
     ```
   - If `VERVE` was deleted, but `FLUX` has `website_build` in `allowed_skills`, the task dynamically routes to `FLUX`.
   - If user creates a custom agent named `CYBER_CODER` with `website_build`, it dynamically routes to `CYBER_CODER`.
   - If **no active agent** has the requested skill, ZEZO reports this honestly:
     *"No active agent in your fleet is currently assigned the '{skill_name}' skill. You can assign it to an agent in Office desk, or I can run the skill directly."*
4. **Live Dynamic System Prompt in `main.py`:**
   - In `main.py`, remove all hardcoded agent names from Gemini Live's system prompt.
   - Dynamically inject the live roster string at session initialization and on fleet updates:
     ```python
     def get_live_fleet_prompt_summary() -> str:
         agents = fleet_manager.get_all_agents()
         if not agents:
             return "No specialized fleet agents are currently deployed."
         return "Active Fleet Specialists:\n" + "\n".join(
             f"- {a.name} (Role: {a.role}, Engine: {a.engine}, Skills: {a.allowed_skills})"
             for a in agents
         )
     ```
   - When an agent is deleted, it vanishes from Gemini Live's memory instantly. Gemini Live will never hallucinate or attempt to dispatch to a deleted agent.
5. **Full Dynamic CRUD & Customization:**
   - **Create Agent:** User defines Name, Role, Specialty, selects Engine (`antigravity_run`, `opencode_run`, `kilo_run`), Model, Desk coordinates, Color, and selects Allowed Skills checklist. Saves to `config/fleet_agents.json`.
   - **Customize / Edit Agent:** Any attribute can be modified in `AgentConfigModal.tsx` and hot-reloads immediately.
   - **Delete Agent:** Permanent disk wipe, zero ghost survival.

---

## 📜 Section 4: The 3 Core Skills Specifications (Complete SKILL.md Contents)

The following are the exact, production-grade `SKILL.md` contents that will reside in each skill's directory.

---

### 4.1 Skill 1: `skills/website_build/SKILL.md`
```markdown
---
name: website_build
description: "Master studio protocol for creating websites, landing pages, and UI components adhering to Hamza Taste design references and anti-slop gates."
domain: ui
author: "Hamza Bukhari"
version: "1.2.0"
triggers: ["build website", "create landing page", "make website", "hero section", "pricing table", "web app"]
auto_activate: true
required_tools:
  - file_controller
  - web_search
  - quick_snippet
---

# 🌐 Master Studio Website Creation Protocol (`website_build`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Fleet, and all UI coding agents.  
> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE QUALITY FILTER** (what to reject), while the **Reference HTML Template** is an **IMMUTABLE READ-ONLY SOURCE OF TRUTH** supplying 100% of the **DESIGN DIRECTION** (typography, colors, tokens, card geometry, micro-interactions, responsive grid, visual rhythm). The agent never mutates or overwrites the reference file; instead, it analyzes the reference design DNA and synthesizes the target deliverable (`index.html` or new pages/sections) with authentic client content, extending any new sections using the exact same structural patterns.

---

## 📋 1. PHASE 1: INTAKE & CONTENT DISCOVERY PROTOCOL

Before writing code or scaffolding workspaces, discover intent and authentic content:
1. **Scope (`scope_type`):**
   - `landing_page`: High-converting marketing landing page or product showcase.
   - `portfolio`: Personal showcase, developer resume, creative studio, or executive profile.
   - `business_site`: Multi-section corporate, service, clinic, or studio website.
   - `dashboard`: Metrics, telemetry console, admin panel, or web OS interface.
   - `component`: Targeted isolated UI block (Hero Section, Pricing Matrix, Navbar, Modal).
2. **Entity & Content Discovery:**
   - Identity, Role, Featured Projects, Experience, and Contact links.
   - *Rule:* Never generate dummy placeholder names or fake AI text when user content can be discovered.
3. **Tech Stack (`tech_stack`):**
   - `single_file_html`: Standalone, self-contained single-file HTML5 deliverable. Zero npm dependencies, inline styles/scripts, instant double-click preview.
   - `react_tailwind`: Modular React 18 + TypeScript + Tailwind CSS (Vite architecture, production-grade clean code).
4. **Visual Direction:**
   - 100% inherited from curated reference templates (`skills/website_build/references/`).

---

## 🎨 2. PHASE 2: DESIGN FOUNDATION & TEMPLATE MATCHING

Do NOT hallucinate visual tokens. Match the user scope against curated templates in `skills/website_build/references/catalog.json`:
- **Landing Pages (`1_landing_pages/`):** SaaS platforms, AI studio landing pages, modern fintech.
- **Portfolios (`2_portfolios/`):** Minimalist executive, tactile dark-mode engineer, creative director.
- **Business Sites (`3_business/`):** Corporate consultancy, agency showcase, health & clinic services.
- **Dashboards (`4_dashboards/`):** Telemetry consoles, analytics cards, dark-mode tables.

---

## 🔨 3. PHASE 3: CONSTRUCTION & CODE SYNTHESIS

1. **Scaffold Directory:** Create project in `Desktop/<project_name>/`.
2. **Single-File Deliverable Structure:**
   - Standard HTML5 boilerplate with UTF-8, viewport meta, and modern Google Fonts (`Plus Jakarta Sans`, `Inter`, `Geist`).
   - Clean embedded CSS variables (`--bg`, `--surface`, `--accent`, `--border`, `--text`).
   - SVG icons only (inline Lucide / Heroicons). Zero broken external image URLs.
3. **Responsive Execution:** Mobile-first fluid CSS grid and flex layouts.

---

## 🛡️ 4. PHASE 4: ANTI-SLOP QUALITY GATES

Reject common AI slop patterns:
- ❌ No generic neon gradient blobs behind text.
- ❌ No low-contrast unreadable grey text on dark backgrounds.
- ❌ No broken placeholder images (`via.placeholder.com`). Use stylized geometric SVGs or solid avatars.
- ❌ No repetitive cookie-cutter 3-column cards with identical padding.

---

## 🚀 5. PHASE 5: VERIFICATION & DELIVERY

1. Verify deliverable with `file_controller` to ensure file exists and size is > 5KB.
2. Launch instant local browser preview via `open_app`.
3. Report completion with exact file path to user and HUD.
```

---

### 4.2 Skill 2: `skills/website_clone/SKILL.md`
```markdown
---
name: website_clone
description: "Master studio protocol for cloning, scraping, and reverse-engineering live websites into clean, editable, standalone offline codebases."
domain: web_dev
author: "Hamza Bukhari"
version: "1.0.0"
triggers: ["clone website", "scrape website", "copy website", "offline website", "clone landing page"]
auto_activate: true
required_tools:
  - clone_website
  - browser_control
  - web_read_page
  - file_controller
---

# 📥 Master Website Cloning Protocol (`website_clone`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** ZEZO Core Dual-AI Runner, Autonomous Fleet Agents (VERVE, FLUX).  
> **Core Axiom:** A cloned website must be an **authentic, fully-rendered, offline-first codebase** that functions without network dependencies, preserves visual pixel fidelity, sanitizes third-party tracking scripts, and produces clean, human-readable HTML/CSS.

---

## 📋 1. PHASE 1: TARGET DISCOVERY & PRE-FLIGHT

1. **URL Validation:** Validate HTTP/HTTPS target accessibility.
2. **Depth Determination:**
   - `single_page`: Landing page, home screen, or targeted article (Default).
   - `deep_clone`: Multi-page documentation or brochure site (Max depth: 2 levels).
3. **SPA & Dynamic DOM Settlement:**
   - If the site is a client-rendered SPA (React/Vue/Next.js), trigger headless browser navigation.
   - Scroll page to bottom to trigger lazy-loaded images, dynamic fonts, and hydration.

---

## 📦 2. PHASE 2: ASSET EXTRACTION & HARVESTING (UNCAGE HYBRID ENGINE)

The extraction engine relies on the bundled Node.js Playwright engine (`tools/uncage/bin/uncage.js`). It supports **dual-execution**:

### Path A: Running under ZEZO Dual-AI Skill Runner (Groq LPU)
- Invoke atomic Python tool `clone_website` with target parameters:
  ```json
  {"url": "https://example.com", "mode": "single_page", "output_dir": "Desktop/clones/example"}
  ```
- Groq executes the Python wrapper which manages process budgets, stealth flags, and timeout guards.

### Path B: Running under Autonomous Fleet Agent CLI (Anti-Gravity / OpenCode)
- Agent directly executes the bundled Uncage binary in terminal:
  ```bash
  node tools/uncage/bin/uncage.js --url https://example.com --out Desktop/clones/example/ --single-page
  ```

### Harvested Assets Specification:
1. **DOM Snapshot:** Extract final computed DOM after hydration (not bare raw HTML source).
2. **CSS Stylesheets & Fonts:**
   - Harvest all linked stylesheets (`<link rel="stylesheet">`) and inline `<style>` tags.
   - Download web fonts (`.woff2`, `.woff`) and resolve local paths.
3. **Media & Assets:**
   - Download SVG icons, logos, background textures, and images.
   - Store locally under `Desktop/<project_clone>/assets/`.

---

## 🧹 3. PHASE 3: SANITIZATION & PATH LOCALIZATION

1. **Path Rewriting:** Rewrite all absolute asset URLs (`https://cdn.example.com/asset.css`) to relative local paths (`assets/asset.css`).
2. **Script & Tracker Stripping:**
   - Remove Google Tag Manager, Google Analytics, Facebook Pixel, Hotjar, and ad scripts.
   - Strip anti-copy and inspect-disabling event listeners.
3. **HTML / CSS Formatting:**
   - Beautify minified HTML and CSS into clean, readable indentation.
   - Consolidate inline styling where practical into `styles.css`.

---

## 🛡️ 4. PHASE 4: FIDELITY & INDEPENDENCE VERIFICATION

Verify the offline deliverable:
- Double-click execution must render identically offline without console 404 network errors.
- Visual hierarchy, typography, colors, and responsive breakpoints must match live source.

---

## 🚀 5. PHASE 5: DELIVERY & HUD REPORTING

1. Place completed project in `Desktop/clones/<site_name>/`.
2. Confirm deliverable via `file_controller`.
3. Provide summary of captured pages, assets count, and double-click path to user and HUD.
```

---

### 4.3 Skill 3: `skills/generate_design_md/SKILL.md`
```markdown
---
name: generate_design_md
description: "Extracts full design systems, CSS design tokens, typography scales, color palettes, and component geometry from live URLs into production-ready DESIGN.md specifications."
domain: design
author: "Hamza Bukhari"
version: "1.0.0"
triggers: ["extract design", "generate design md", "get design tokens", "extract colors", "design system"]
auto_activate: true
required_tools:
  - extract_design_system
  - browser_control
  - file_controller
---

# 🎨 Generate Design MD (Design System Extraction Protocol)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** ZEZO Core, Frontend Fleet Specialist (VERVE), and Design Agents.  
> **Core Axiom:** `DESIGN.md` is the canonical design specification artifact. It bridges live web visual aesthetics with autonomous code generation by reverse-engineering colors, typography, elevation, and component rules into structured Markdown tokens.

---

## 📋 1. PHASE 1: TARGET URL INGESTION & DOM SETTLEMENT

1. **URL Accessibility Check:** Verify target website responds with status `200 OK`.
2. **Render Settlement:** Launch headless browser to settle DOM stylesheets, CSS custom properties (`:root`), and dynamic themes (Dark/Light).

---

## 🔍 2. PHASE 2: MULTI-TIER TOKEN EXTRACTION

Execute atomic action `extract_design_system` to harvest:
1. **Color Tokens:**
   - Backgrounds, surface cards, primary brand, secondary accents, text muted, borders.
   - Standardize format into Hex, RGB, and HSL.
2. **Typography Hierarchy:**
   - Font Families: Heading family, body family, monospace code family.
   - Type Scale: Font sizes, line heights, and weights for `H1`, `H2`, `H3`, `H4`, `Body`, `Small`, `Caption`.
3. **Spatial & Component Geometry:**
   - Spacing scale: Padding, margins, gap rhythm (`4px`, `8px`, `16px`, `24px`, `32px`).
   - Border radius scale: Small (`rounded-sm`), medium (`rounded-md`), large (`rounded-xl`), full (`rounded-full`).
   - Shadows / Elevation: Card shadows, button hover states, dropdown elevation.

---

## ♿ 3. PHASE 3: ACCESSIBILITY & CONTRAST AUDIT

1. Evaluate color contrast ratios of text on backgrounds against WCAG AA standards (`4.5:1` minimum for body).
2. Flag any inaccessible contrast combinations in the generated report.

---

## 📝 4. PHASE 4: CANONICAL `DESIGN.md` SYNTHESIS

Structure the generated `DESIGN.md` artifact with standard sections:
```markdown
# 🎨 Design System: [Target Site Name]
> Source URL: [URL] | Generated by ZEZO Design Engine

## 1. Color Palette
- `--color-bg`: `#0a0a0a` (Deep Background)
- `--color-surface`: `#141414` (Card Surface)
- `--color-primary`: `#3b82f6` (Brand Accent)
- `--color-text`: `#f9fafb` (Primary Text)
- `--color-text-muted`: `#9ca3af` (Secondary Text)
- `--color-border`: `#262626` (Subtle Dividers)

## 2. Typography Scale
- Primary Font: Plus Jakarta Sans, sans-serif
- H1: 48px / 1.1 / Bold (700)
- H2: 36px / 1.2 / SemiBold (600)
- H3: 24px / 1.3 / SemiBold (600)
- Body: 16px / 1.5 / Regular (400)
- Small: 14px / 1.4 / Regular (400)

## 3. Component Rules & Geometry
- Card Padding: 24px
- Border Radius: 12px (rounded-xl)
- Elevation: `0 4px 20px -2px rgba(0, 0, 0, 0.5)`
- Button Heights: 40px (default), 48px (large)
```

---

## 🚀 5. PHASE 5: DOWNSTREAM HANDOFF

1. Save deliverable to `output/design_system/<domain>_DESIGN.md` or project root.
2. Provide direct path to `website_build` or assigned Fleet Frontend Agent to scaffold pixel-accurate components.
```

---

## 🧹 Section 5: Dead Code & Permanent Skills Deletion

### 5.1 Permanent Deletion of 10 Obsolete Skills (Clean Disk Directory)
To guarantee 0% clutter, the following 10 directories are **permanently deleted** from `skills/`, leaving strictly 3 core skills (`website_build`, `website_clone`, `generate_design_md`):

| Skill Directory to Delete | Former Purpose | Reason for Permanent Deletion |
| :--- | :--- | :--- |
| `skills/figma_helper/` | Figma variable reader | Out of immediate scope; missing YAML frontmatter delimiters. |
| `skills/git_workflow/` | Git commit/branch helper | Redundant with standard agent engine capabilities. |
| `skills/make_plan/` | Multi-step task planner | Absorbed into internal engine planner. |
| `skills/parallel_task_management/` | Duplicate task planner | 14-line exact redundancy of `make_plan`. |
| `skills/office_suite/` | Markdown/Office docs helper | Generic document helper; removed to declutter hub. |
| `skills/social_research/` | Social sentiment scraper | Niche research SOP; removed from active hub. |
| `skills/test_fastapi_deploy/` | FastAPI deploy placeholder | Incomplete 3-bullet placeholder file. |
| `skills/web_research_pipeline/` | Web research workflow | Covered by general `web_search` and `web_read_page` tools. |
| `skills/web_scraper/` | Web data scraper | Covered by `website_clone` and atomic reader tools. |
| `skills/multi_agent_collaboration/` | Multi-agent router SOP | Stale agent roster (`Ali`, `Oscar`); router handled by `core/fleet/dispatcher.py`. |

### 5.2 Codebase Cleanups, Ghost Agent Purge & Engine Bridge Pruning
| File / Component | Action | Reason |
| :--- | :--- | :--- |
| `core/fleet/registry.py:270-324` | **PURGE GHOST AGENTS** | Strip phantom agent creation (`OSCAR`, `KELLY`), alias maps (`ALI`, `HAIDER`), and hardcoded name routing (`VERVE`, `AHMAD`). |
| `main.py:1511` | **PURGE HARDCODED NAMES** | Strip static `(VERVE <-> FLUX for frontend)` from Gemini Live prompt; inject live roster dynamically. |
| `actions/fleet_control.py:50` | **PURGE HARDCODED NAMES** | Strip hardcoded check `canonical_agent_id in ("VERVE", "FLUX")`; check live agent's `allowed_skills`. |
| `core/ui_server.py:1106` | **PURGE GHOST FALLBACK** | Strip `target_agent_id = agent.id if agent else "VERVE"` fallback. |
| `core/ai_design_generator.py` | **DELETE** | Extreme over-engineering: synthetic AI design prompt injector. |
| `core/design_cache.py` | **DELETE** | Bloat: disk caching for synthetic `DESIGN.md` and `master-template.html`. |
| `core/design_resolver.py` | **DELETE** | Bloat: archetype gates (`PORTFOLIO`, `DASHBOARD`), greenfield blockers. |
| `core/master_template_builder.py` | **DELETE** | Bloat: artificial slot injector (`<!-- SLOT:HERO_START -->`). |
| `core/design_md_generator.py` | **DELETE** | Bloat: DSL generator that was polluting Antigravity CLI prompts. |
| `core/antigravity_runner.py` | **PRUNE & REFACTOR** | Strip 734 lines of prompt synthesis down to clean <100 lines CLI bridge. |
| `actions/antigravity_agent.py` | **PRUNE & REFACTOR** | Strip greenfield checks and archetype guessing; pure transparent bridge. |
| `actions/opencode_agent.py` | **STANDARDIZE** | Align with universal transparent bridge contract (pure prompt + cwd). |
| `actions/kilo_agent.py` | **STANDARDIZE** | Align with universal transparent bridge contract (pure prompt + cwd). |
| `actions/website_cloner.py:2314-2358` | **DELETE** | Dead code: orphaned duplicate `generate_design_system_md()` function. |
| `scratch/update_skills_tab.py` | **DELETE** | Legacy scratch script no longer needed. |
| `scratch/clean_hamza_taste.py` | **DELETE** | Legacy scratch script for old test skill. |
| `frontend/src/components/settings/SkillsSettingsTab.tsx` (lines 42–266) | **REMOVE** | 260 lines of hardcoded fake `DEFAULT_SKILLS` bloat. Disk `/api/skills` is ground truth. |
| `config/skills_state.json` | **SANITIZE** | Remove leftover keys for legacy test skills. |
| `config/fleet_agents.json` | **SANITIZE** | Remove tools erroneously listed under `allowed_skills` (e.g. `web_search`, `file_processor`), and fix `web_reader` typo to `web_read_page`. |

---

## 🛡️ Section 6: Safety & Anti-Regression Invariants

1. **Rule 6 Audio Pipeline Hands-Off:**
   - **NEVER TOUCH:** `main.py` live audio loops (`_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`), `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`.
   - The new skill dispatcher connects strictly via `actions/run_skill.py` which `core.action_loader` discovers automatically at runtime.
2. **Rule 3 Minimal Blast Radius:**
   - Only modify the designated frontend component and the specific backend execution files. Do not refactor unrelated UI modals or fleet inspectors.
3. **ReUI Consistency:**
   - Use official ReUI components (`Card`, `Button`, `Badge`, `Callout`, `Dialog`) in `SkillsSettingsTab.tsx` and `AgentConfigModal.tsx`. Do not write raw custom CSS or non-standard HTML button tags.

---

## 🧪 Section 7: Strict 3-Layer Verification Plan

### Layer 1: Static Verification
- Run `python -m py_compile` on all modified/created Python files:
  - `core/skill_runner.py`
  - `actions/run_skill.py`
  - `core/skill_loader.py`
  - `core/llm_client.py`
  - `core/task_manager.py`
  - `core/fleet/dispatcher.py`
- Run TypeScript syntax/lint check on `frontend/src/components/settings/SkillsSettingsTab.tsx` and `frontend/src/components/office/AgentConfigModal.tsx`:
  - `npm --prefix frontend run build` or `npx tsc --noEmit`

### Layer 2: Runtime Verification
- **Test 1: Frontend CRUD & Slug Validation:**
  - Launch UI, create a new skill with name `My Test Skill` -> verify slug auto-formats to `my_test_skill`.
  - Verify skill saves to `skills/my_test_skill/SKILL.md` and appears in the list.
  - Verify core skills cannot be deleted, but `my_test_skill` deletes cleanly with confirmation.
- **Test 2: Agent Skills Isolation & Config Modal:**
  - Open Agent Modal for `VERVE`, assign `website_build`, save. Verify `config/fleet_agents.json` updates.
  - Send task in Verve's desk chat -> verify Verve triggers `antigravity_run` with `website_build` instructions passed directly to `agy.exe`.
- **Test 3: Scoped Groq Execution & Fallback Resume:**
  - Trigger direct skill `web_research_pipeline` -> verify only 3 candidate tools are injected into Groq.
  - Simulate Groq timeout mid-pipeline -> verify Gemini Flash picks up from `completed_steps` without repeating step 1.
- **Test 4: Voice Continuity:**
  - Verify Gemini Live voice conversation continues smoothly with zero dropped packets while skill runs in background thread.

### Layer 3: Regression Verification
- Run existing test suites (`pytest tests/test_actions.py`, `pytest tests/test_tasks.py`).
- Confirm existing settings tabs (Code Engines, Settings Modal, Memory Inspector) function normally.

---

## 📝 Section 8: Phased Implementation Sequence

```
Phase 1: Frontend Simplification, Tools Tab & Fleet Skills UI Polish
  ├── 1.1 In SkillsSettingsTab.tsx: Remove toggles, clean Edit/Delete, protect 3 core skills (website_build, website_clone, generate_design_md), add "+ Create Skill" with slug formatting
  ├── 1.2 In ToolsSettingsTab.tsx (NEW): Build 15-tool categorized ReUI toggle panel (including agent_reach under Research & Intelligence) and add to SettingsModal.tsx
  └── 1.3 In AgentConfigModal.tsx: Add clean ReUI checklist for agent.allowed_skills selection

Phase 2: Backend Action Gate, Persistence & Tools API (core/action_loader.py & core/ui_server.py)
  ├── 2.1 Enforce rec.enabled check in ActionRegistry.run() returning clean blocked execution message
  ├── 2.2 Add tool toggle persistence via config/tools_state.json
  ├── 2.3 Expose GET /api/tools and POST /api/tools/{name}/toggle endpoints in core/ui_server.py
  ├── 2.4 Strip _is_actionable_task regex interception in core/ui_server.py for direct pass-through agent chat
  └── 2.5 Expose POST /api/engines/{engine}/test endpoint for live engine bridge latency & connectivity verification

Phase 3: LLM Client Tool Calling & Dual-AI Skill Runner (core/llm_client.py & core/skill_runner.py)
  ├── 3.1 Implement call_groq_tools with OpenAI-compatible schema and low-latency timeouts
  ├── 3.2 Build SkillRunner class with Groq primary + Gemini Flash resume fallback
  ├── 3.3 Implement smart tool scoping (inject only candidate tools referenced in SKILL.md)
  └── 3.4 Connect real-time progress & subtask reporting to TaskManager.submit()

Phase 4: Decision Router, Declarative Skills & Action Dispatcher
  ├── 4.1 Create actions/run_skill.py with Self vs Fleet delegation logic
  ├── 4.2 Create skills/website_clone/SKILL.md (Website Cloner SOP)
  ├── 4.3 Create skills/generate_design_md/SKILL.md (Design System Extractor SOP)
  └── 4.4 In core/fleet/dispatcher.py: Pass assigned SKILL.md directly to agent's configured CLI (agy.exe)

Phase 5: Permanent Cleanup, Skills Deletion & Pure Engine Bridge Refactoring
  ├── 5.1 Permanently delete 10 obsolete skill directories from skills/
  ├── 5.2 Permanently delete 5 bloated design generation files: core/ai_design_generator.py, core/design_cache.py, core/design_resolver.py, core/master_template_builder.py, core/design_md_generator.py
  ├── 5.3 Refactor core/antigravity_runner.py & actions/antigravity_agent.py into a pure transparent CLI bridge (strip all archetypes, fake prompt synthesizers, and slot hacks)
  ├── 5.4 Standardize actions/opencode_agent.py & actions/kilo_agent.py on the exact same transparent CLI bridge pattern
  ├── 5.5 Purge ghost agent re-creations and hardcoded agent names from core/fleet/registry.py, main.py:1511, actions/fleet_control.py:50, and core/ui_server.py:1106
  ├── 5.6 Remove dead code in actions/website_cloner.py (lines 2314–2358)
  ├── 5.7 Sanitize config/fleet_agents.json (isolate tools vs skills, fix web_reader typo)
  ├── 5.8 Remove legacy scratch files (scratch/update_skills_tab.py, scratch/clean_hamza_taste.py)
  └── 5.9 Sanitize config/skills_state.json and clean EXCLUDED_SKILL_NAMES in core/skill_loader.py

Phase 6: Verification & Complete Documentation Sync
  ├── 6.1 Execute 3-Layer verification (py_compile, tsc, runtime test)
  ├── 6.2 Synchronize docs/ (docs/SKILLS_SYSTEM.md, docs/TOOLS.md, docs/CODE_ENGINES.md, docs/FLEET_MANAGEMENT.md, docs/SETTINGS.md, docs/WEBSITE_CLONER.md, docs/DESIGN_SYSTEM_ARCHITECTURE.md)
  └── 6.3 Append comprehensive architectural entry to LEARNING_JOURNAL.md

---

## 📚 Section 9: Documentation Synchronization & Learning Journal Contract

In strict compliance with **AGENTS.md Rule 10 (Mandatory Learning Journal & Documentation Synchronization)**, completing this implementation requires full synchronization across `docs/` and an explicit entry in `LEARNING_JOURNAL.md`.

### 9.1 `docs/` Subsystem Synchronization Matrix

| Documentation File | Subsystem | Action | Required Synchronization Details |
| :--- | :--- | :---: | :--- |
| [`docs/SKILLS_SYSTEM.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/SKILLS_SYSTEM.md) | Skills Hub | **UPDATE** | • Document the 3 Core Skills (`website_build`, `website_clone`, `generate_design_md`).<br>• Document removal of UI toggle switches; cards feature Edit and Delete only with slide-over drawer.<br>• Record permanent deletion of 10 legacy/redundant skills. |
| [`docs/TOOLS.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/TOOLS.md) | Actions Registry | **UPDATE** | • Catalog all 15 user-facing tools across 5 categories.<br>• Document `agent_reach` inclusion under Research & Intelligence.<br>• Detail `rec.enabled` enforcement in `ActionRegistry.run()` and state persistence in `config/tools_state.json`. |
| [`docs/CODE_ENGINES.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/CODE_ENGINES.md) | Autonomous Engines | **UPDATE** | • Document the Pure Natural Engine Bridge for Antigravity, OpenCode, and Kilo.<br>• Specify the `POST /api/engines/{engine}/test` bridge connectivity endpoint.<br>• Update the verified active models matrix (purge dead `gemini-2.5-*` models). |
| [`docs/FLEET_MANAGEMENT.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/FLEET_MANAGEMENT.md) | Fleet Agents | **UPDATE** | • Document direct pass-through Agent Desk Chat (removal of `_is_actionable_task` regex interception).<br>• Document `allowed_skills` selection checklist in `AgentConfigModal.tsx`.<br>• Reconcile agent rosters to active fleet (`VERVE`, `FLUX`, `MICHAEL`, `QUANTUM`, `DATAEINSTEIN`). |
| [`docs/SETTINGS.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/SETTINGS.md) | Settings Modal | **UPDATE** | • Document the new **Tools** tab alongside Skills in `SettingsModal.tsx` (`WORKSPACE` section).<br>• Document the "Test Bridge" button on Engine cards. |
| [`docs/WEBSITE_CLONER.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/WEBSITE_CLONER.md) | Web Cloner | **UPDATE** | • Document the Uncage hybrid execution model (Python action `clone_website` for Groq runner, direct CLI `node tools/uncage/bin/uncage.js` for Fleet Agents). |
| [`docs/DESIGN_SYSTEM_ARCHITECTURE.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/docs/DESIGN_SYSTEM_ARCHITECTURE.md) | Design Pipeline | **UPDATE** | • Streamline to document `generate_design_md` declarative SOP and atomic Playwright extraction.<br>• Remove all references to deleted legacy modules (`ai_design_generator.py`, `design_cache.py`, `design_resolver.py`, `master_template_builder.py`, `design_md_generator.py`). |

---

### 9.2 `LEARNING_JOURNAL.md` Mandatory Entry Structure

Upon completion of Phase 6, append the following structured entry to the top of [`LEARNING_JOURNAL.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/LEARNING_JOURNAL.md):

```markdown
## [2026-10-29] — Minimalist Option 4: Pure Engine Bridges, 3 Core Skills & Dedicated Tools Management UI
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Extreme Engine Over-Engineering:** Legacy Antigravity execution was bloated with synthetic slot injectors (master_template_builder), fake prompt synthesizers (ai_design_generator), archetype guessers (design_resolver), and artificial gates that crippled native CLI intelligence.
  2. **Skills Hub Clutter & Toggle Confusion:** Skills were overloaded with confusing enable/disable toggles and 10 redundant/broken skills on disk.
  3. **Lack of Dedicated Tools Management:** Tools had no dedicated UI toggle panel; disabled tools were filtered from Gemini declarations but not blocked during runtime execution in ActionRegistry.run().
  4. **Agent Desk Chat Interception:** _is_actionable_task() regex heuristics diverted natural user prompts away from configured engines to fallback LLMs.
- **Execution & Changes Applied:**
  - Built Pure Natural Engine Bridges for Antigravity (agy.exe), OpenCode, and Kilo Code: zero archetype guessing, zero slot hacks, transparent prompt pass-through.
  - Permanently deleted 5 bloated design generation files: core/ai_design_generator.py, core/design_cache.py, core/design_resolver.py, core/master_template_builder.py, core/design_md_generator.py.
  - Pruned skills/ to strictly 3 Core Production Skills: website_build, website_clone, generate_design_md; permanently deleted 10 obsolete skill directories.
  - Built frontend/src/components/settings/ToolsSettingsTab.tsx: 15 user-facing tools with ReUI toggles across 5 categories, including agent_reach under Research & Intelligence.
  - Sealed ActionRegistry.run() with rec.enabled check and persistent config/tools_state.json.
  - Stripped _is_actionable_task() from core/ui_server.py; agent chat routes verbatim to agent CLI.
  - Added POST /api/engines/{engine}/test endpoint and "Test Bridge" button in Settings > Engines.
  - Purged dead gemini-2.5-*/2.0/1.5 models; synchronized active model matrices.
  - All 3 layers verified: Layer 1 static py_compile & tsc passed, Layer 2 runtime engine & tool toggles verified, Layer 3 regression tests passed.
- **Key Files Touched:**
  - frontend/src/components/settings/SkillsSettingsTab.tsx
  - frontend/src/components/settings/ToolsSettingsTab.tsx (new)
  - frontend/src/components/settings/SettingsModal.tsx
  - frontend/src/components/office/AgentConfigModal.tsx
  - core/action_loader.py
  - core/ui_server.py
  - core/skill_runner.py (new)
  - actions/run_skill.py (new)
  - actions/antigravity_agent.py & core/antigravity_runner.py (refactored to pure bridge)
  - actions/opencode_agent.py & actions/kilo_agent.py (standardized)
  - skills/website_clone/SKILL.md (new)
  - skills/generate_design_md/SKILL.md (new)
  - config/fleet_agents.json & config/tools_state.json
  - docs/SKILLS_SYSTEM.md, docs/TOOLS.md, docs/CODE_ENGINES.md, docs/FLEET_MANAGEMENT.md, docs/SETTINGS.md, docs/WEBSITE_CLONER.md, docs/DESIGN_SYSTEM_ARCHITECTURE.md
  - LEARNING_JOURNAL.md
```

---
*Implementation Plan authored for Hamza Bukhari, Creator & Lead Architect of ZEZO.*
