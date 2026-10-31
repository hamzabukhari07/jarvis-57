# 🧠 Declarative Skills & Self-Learning Engine

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Source Modules:** [`core/skill_loader.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/skill_loader.py), [`core/skill_scanner.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/skill_scanner.py), [`main.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/main.py), [`frontend/src/components/settings/SkillsSettingsTab.tsx`](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/settings/SkillsSettingsTab.tsx)  
> **Storage Directory:** `skills/<skill_name>/SKILL.md`  
> **Target OS:** Windows 10/11 (Primary), macOS, Linux  

---

## 📖 Overview

The **Declarative Skills System** provides ZEZO with a modular, extensible, and self-learning knowledge architecture. Inspired by the separation between **atomic executable tools** (actions that perform single operations) and **declarative procedural skills** (procedural step-by-step instructions and best practices), ZEZO packages complex multi-step workflows as portable Markdown packages (`SKILL.md`).

The engine includes **dynamic intent indexing**, an **automated multi-stage threat scanner** (blocking prompt injections, obfuscated scripts, and secret leakage), and **runtime self-learning tools** that allow ZEZO to autonomously persist novel procedures learned during execution.

```mermaid
flowchart TD
    A["User Request:<br/>'Troubleshoot my audio devices'"] --> B["Gemini Live Brain / Main Engine"]
    B --> C["Dynamic Trigger Indexing<br/>(core/skill_loader.py)"]
    C --> D{"Trigger Matched in Index?"}
    D -- "Yes" --> E["Inject Skill Summary into Context<br/>([AVAILABLE SKILLS])"]
    D -- "No" --> F["Standard General Response"]
    E --> G["Model Invokes Inline Tool:<br/>read_skill('audio_troubleshoot')"]
    G --> H["Security & Threat Scanner<br/>(core/skill_scanner.py)"]
    H --> I{"Is Safe?"}
    I -- "No" --> J["Block & Log Security Violation"]
    I -- "Yes" --> K["Inject Step-by-Step Instructions<br/>into Active Model Context"]
    K --> L["Execute Calibrated Workflow"]
    L --> M["Novel Workflow Synthesized?<br/>Model Calls save_learned_skill()"]
    M --> N["New Skill Saved to skills/<name>/SKILL.md"]

    classDef core fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff;
    class A,B,C,D,E,F,G,H,I,J,K,L,M,N core;
```

---

## 📦 Declarative Package Format (`SKILL.md`)

Every skill in ZEZO resides in its own isolated directory under `skills/<skill_name>/` and is documented in a standard `SKILL.md` file featuring YAML frontmatter:

```markdown
---
name: website_build
description: Master studio protocol for creating websites, landing pages, and UI components adhering to Hamza Taste design references and anti-slop gates.
domain: ui
author: Hamza Bukhari
version: 1.0.0
triggers:
  - "build website"
  - "create landing page"
  - "make website"
  - "hero section"
  - "pricing table"
  - "web app"
auto_activate: true
---

# 🌐 Website Build — Studio Greenfield Creation Protocol

## Executive Workflow
1. **Phase 1: Intake & Clarification Gate**: Intercepts open-ended queries, prompts for the 4 architectural pillars (`scope_type`, `tech_stack`, `color_theme`, `key_sections`), and enforces a 1-sentence Commitment Read-Back confirmation before workspace allocation.
2. **Phase 2: Deterministic Catalog Resolution**: Queries `skills/website_build/references/catalog.json` across 5 scope folders (`1_landing_pages`, `2_business_sites`, `3_portfolios`, `4_dashboards`, `5_components`) indexing 20 authentic HTML templates. Eliminates pseudo-random modulo string hashing.
3. **Phase 3: Anti-Slop Directive**: Enforces 3 tiers of hard design constraints (anti-slop filter, rhythm/geometry locks, micro-interactions).
4. **Phase 4: Stack Parity**: Supports Single-File HTML and Modular React 18 + Vite architectures with clean dependency resolution.
5. **Phase 5: Smart Live Preview**: Launches ephemeral preview servers (ports 9400-9480) for HTML or background dev servers for React, permanently suppressing blank `file://` popups.
```

### Frontmatter Schema

- **`name`**: Short, snake_case identifier matching directory name.
- **`description`**: High-level summary describing when and why the model should activate this skill.
- **`domain`**: Functional namespace (`ui`, `web_dev`, `design`, `coding`, `system`, `general`).
- **`required_tools`**: List of atomic actions required by the skill (e.g. `[clone_website, browser_control, web_read_page, file_controller]`).
- **`triggers`**: List of intent-matching keywords used by `core/skill_loader.py` to index when the skill should be surfaced.
- **`auto_activate`**: Whether the skill is dynamically eligible for automatic prompt injection upon trigger match.
- **`pre_flight_action`**: (Optional) Action module name dynamically invoked before coding engine dispatch (e.g., `uncage_capture` dynamically loads `actions/uncage_capture_handler.py`, `scrapling_extract` loads `actions/scrapling_extract_handler.py`). Pure dynamic dispatch with zero hardcoded orchestrator branches.
- **`agent_directive_section`**: (Optional) Title of the markdown section (e.g., `"Agent Directive"`) to isolate and extract for autonomous coding engine synthesis (`craft_skill_engine_prompt`), cleanly filtering out CLI commands, environment setup, and reference architecture notes from agent prompts.

---

## ⚡ Two-Phase Engine Skill Pipeline (Dynamic Pre-Flight & Directive Extraction)

To cleanly separate **pre-flight asset preparation** (asset scraping, offline cloning, DOM extraction handled by Python backend tooling) from **autonomous coding engine execution** (AntiGravity, OpenCode, Kilo Code inspecting real files and synthesizing code), ZEZO implements a declarative two-phase pipeline:

```mermaid
flowchart TD
    A["Skill Triggered: website_clone / generate_design_md"] --> B["SkillRegistry.get_skill()"]
    B --> C{"pre_flight_action defined?"}
    C -- "Yes" --> D["Dynamic Module Dispatch:<br/>importlib.import_module('actions.<action>_handler')"]
    D --> E["Handler Executes Ingestion Tooling<br/>(Uncage CLI / Scrapling Asset Prefetch)"]
    E --> F["Assets Ingested to Target Directory"]
    C -- "No" --> G["Bypass Ingestion"]
    F --> H["craft_skill_engine_prompt(..., directive_header=...)"]
    G --> H
    H --> I["_extract_agent_directive()<br/>Isolate '## 🤖 Agent Directive'"]
    I --> J["Groq LPU Prompt Synthesis<br/>(Grounding on real workspace files)"]
    J --> K["Autonomous Coding Engine Dispatched<br/>(AntiGravity / OpenCode / Kilo)"]
```

1. **Zero-Hardcoding Dynamic Dispatch:** `actions/run_skill.py` does not contain any skill-specific branching (`if pre_flight == 'uncage_capture'`). Instead, it dynamically imports `actions.<pre_flight_action>_handler` via `importlib`. New pre-flight handlers can be added without modifying the core orchestrator.
2. **Directive Extraction with Smart Fallback:** `_extract_agent_directive()` in `core/skill_prompt_engineer.py` regex-isolates the specified directive section. If the named header is omitted or missing, it safely falls back to the final markdown section to eliminate CLI command leakage.

---

## 🏛️ The 3 Core Skills Standard

ZEZO standardizes on 3 production core skills, all unified under the declarative two-phase architecture and standardized `agent_directive_section: "Agent Directive"` contract:
1. **`website_build` (`skills/website_build/`)**: Greenfield UI creation protocol with catalog-driven references, anti-slop quality gates, live preview servers, and authoritative taste prompts in `## 🤖 Agent Directive` (Scenario 1: Portfolio, Scenario 2: SaaS Landing Page, Scenario 3: CloudFleet Analytics Dashboard, embedding 6 negative rejection gates and 4 visual authority guards).
2. **`website_clone` (`skills/website_clone/`)**: High-fidelity offline website capture, asset localization, and reverse-engineering rebuilds via the Uncage Ingestion Engine and autonomous coding agents, featuring Phase 1 Uncage CLI ingestion (`pre_flight_action: "uncage_capture"`), physical verification gates, and Phase 2 Master System Directives (Scenario A: Single-File Raw HTML, Scenario B: Clean Modular React/Next.js Framework).
3. **`generate_design_md` (`skills/generate_design_md/`)**: Studio design token extraction and canonical specification generator (`DESIGN.md` & `preview.html`) via Scrapling pre-flight ingestion (`pre_flight_action: "scrapling_extract"`), featuring Scenario A (Live URL Mode via pre-flight ingested assets) and Scenario B (Local Codebase / Workspace Mode).

---

## 🛡️ Multi-Stage Security Scanner (`core/skill_scanner.py`)

To ensure that community-contributed or autonomously synthesized skills do not introduce prompt injections, privilege escalation attacks, or malware, every `SKILL.md` passes through `core/skill_scanner.py`:

### 1. Prompt Injection & Jailbreak Detection
Scans frontmatter and instruction bodies for adversarial pattern tokens:
- System instruction override directives (e.g. `ignore all previous instructions`).
- Raw ChatML role markers (`<|im_start|>system`).
- Llama system enclosure injection (`[INST] <<SYS>>`).
- Persona hijacking and jailbreak phrases (`act as DAN`, `unrestricted mode`).

### 2. Obfuscation & Malicious Execution Detection
Detects stealthy execution vectors:
- Encoded PowerShell evaluation: `iex [System.Text.Encoding]`.
- Dynamic Python evaluation: `eval(compile(...))`.
- Obfuscated inline subprocesses: `__import__('os').system`.

### 3. Secret Token Scrubbing
Runs `sqlite_memory.redact_secrets` over the entire text to scrub API keys, Bearer tokens, and private paths before storing or displaying in the UI.

---

## 🛠️ Inline Tools Reference ([main.py](file:///d:/anitgravity/zezo%20work/jarvis-57/main.py))

ZEZO exposes 3 native inline tools directly to Google Gemini Live and Assistant-UI:

### 1. `read_skill`
```json
{
  "name": "read_skill",
  "description": "Read full step-by-step guidelines and instructions for a skill listed under '[AVAILABLE SKILLS]'. Call this before executing a complex multi-step workflow.",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "skill_name": {
        "type": "STRING",
        "description": "Name of the skill to read (e.g. 'system_diagnostics', 'git_workflow')"
      }
    },
    "required": ["skill_name"]
  }
}
```

### 2. `list_skills`
```json
{
  "name": "list_skills",
  "description": "List all available skills and workflows on disk with their descriptions.",
  "parameters": {
    "type": "OBJECT",
    "properties": {}
  }
}
```

### 3. `save_learned_skill` (Self-Learning Loop)
```json
{
  "name": "save_learned_skill",
  "description": "Autonomously synthesize and persist a new skill after successfully completing a complex or novel multi-step task. This adds a permanent new capability to your skills catalog for future sessions.",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "name": {
        "type": "STRING",
        "description": "Short snake_case name for the skill (e.g. 'docker_cleanup', 'audio_troubleshoot')"
      },
      "description": {
        "type": "STRING",
        "description": "1-2 sentence summary of when to use this skill"
      },
      "instructions": {
        "type": "STRING",
        "description": "Clear step-by-step markdown instructions and best practices"
      }
    },
    "required": ["name", "description", "instructions"]
  }
}
```

---

## ⚙️ In-App Discovery & Editing (`SkillsSettingsTab.tsx`)

Inside the Settings modal (`SkillsSettingsTab.tsx`):
- **Category Filter Tabs:** Filter skills across *Coding*, *Design*, *Research*, *System*, *Media*, and *Orchestration*.
- **Live Search & Tags:** Real-time search across titles, descriptions, and tag pills.
- **In-App Markdown Editor:** Users can view, edit, or create new declarative skills with live syntax highlighting and direct disk persistence.
- **Activation Toggles:** Individual skills can be enabled or disabled instantly without restarting the server.


---

## ⚡ Dual-AI Skill Runner Subsystem (`core/skill_runner.py`)

Procedural declarative skills (`SKILL.md`) are executed by the **Dual-AI Skill Runner**:
- **Smart Tool Scoping**: Ingests `SKILL.md` via `SkillRegistry` and inspects `required_tools` and body tokens, scoping down from 30+ tools to only the 3-5 atomic tools needed for the workflow.
- **Dual-AI Execution Engine**:
  - **Primary**: High-throughput Groq LPU (`llama-3.3-70b-versatile`) performing sequential atomic tool-calling.
  - **Stateful Fallback**: Maintains a live ledger of `completed_steps = []`. If Groq encounters HTTP 429 rate limits or network drops, it immediately hands over to Gemini (`gemini-3.8-flash`) with full execution history so the remaining steps resume without repeating step 1.
- **Output Truncation & Memory Guard**: Large tool returns are truncated and summarized to a maximum of 1500 characters to safeguard the context window.
- **Task Telemetry**: Reports step-by-step progress to `TaskManager` (`task_manager.report(progress=..., message=...)`).
- **Fleet Delegation Routing**: If a skill specifies or requires autonomous fleet execution, `actions/run_skill.py` dispatches to `FleetDispatcher.dispatch_task()` while local execution runs in a non-blocking background thread.

---

## 🛠️ Pure AI-Driven Skill Prompt Synthesizer (core/skill_prompt_engineer.py)

For downstream autonomous coding engines (Google Antigravity CLI gy, OpenCode, Kilo Code), the **Skill Prompt Synthesizer** dynamically constructs clean, natural, tailored instruction prompts using live AI:
- **Zero Hardcoded Bloat**: No artificial personas, theatrical roleplay, rigid 5-block schemas, or ghost file declarations (site_dom.html, site_tokens.json) are hardcoded into the synthesizer.
- **Physical Workspace Disk Grounding**: _inspect_workspace_state(target_dir) inspects the target directory on disk before invoking the AI. It informs the LLM whether the workspace is brand new/empty or contains specific existing files, preventing hallucinated file dependencies that stall coding engines.
- **Dual-AI Live Engine Orchestration**:
  1. **Primary Engine**: Groq LPU (llama-3.3-70b-versatile) with ultra-fast latency (~150–200ms, 	imeout=12s, max_tokens=2048, 	emperature=0.2).
  2. **Secondary Fallback**: Google Gemini Flash (gemini-2.5-flash, gemini-2.0-flash via core.gemini.client) for instant failover if Groq experiences rate limits or network issues.
  3. **Natural Dynamic Fallback**: If live LLMs are unreachable, a minimal, universal fallback derived purely from user_task, skill_name, and actual workspace status is generated.
- **Pre-Flight Asset Extraction Sync**: In ctions/run_skill.py, if a live URL is present in the task/parameters, core.url_prefetch.prefetch_url_assets captures the live DOM and styles into 	arget_dir before prompt generation, ensuring that when the prompt references local files, those files genuinely exist on disk.