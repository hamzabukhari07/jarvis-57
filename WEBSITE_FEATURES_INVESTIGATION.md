# 🌐 ZEZO Website Clone & Website Build: System Investigation Report

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Status:** Read-Only Technical Audit & Architectural Blueprint  
> **Target Subsystems:** `actions/website_cloner.py`, `skills/website_build/`, `core/design_resolver.py`, `core/antigravity_runner.py`, `actions/antigravity_agent.py`, `core/fleet/dispatcher.py`, `core/skill_loader.py`  

---

## 1. Executive Summary

This report provides a factual code-level analysis of ZEZO’s two premier web development features:
1. **Website Clone:** Replicates an existing online website down to pixel, assets, scripts, and responsive layout, with optional full reverse-engineering into modern stacks (React, Next.js, clean HTML).
2. **Website Build:** Generates original, production-grade web applications from conversational prompts using curated references, anti-slop guidelines, and native coding engine integration.

Both subsystems were traced from user utterance down to disk artifacts and browser previews. Key findings show that **Website Clone completely bypasses the Skills System**, while **Website Build reads the Skills directory via direct disk I/O rather than runtime skill tools**, leaving several dead code blocks and path discrepancies.

---

## 2. End-to-End Execution Flows

### 2.1 Website Clone Execution Flow

```
[User Utterance / Prompt] ("Clone https://example.com in React")
                     │
                     ▼
       [Gemini Live Model Ingestion]
                     │
                     ▼ Emits Tool Call
[actions/website_cloner.py: clone_website_action()] (Lines 3142-3243)
   - Gate 1: Checks required params (url, mode, output_format, target_dir)
   - Gate 2: Checks user confirmation (returns verbal read-back if unconfirmed)
                     │
                     ▼ (confirmed == True)
[core/task_manager.py: TaskManager.submit(_clone_worker)] (Lines 3216-3224)
   - Returns task_id immediately to keep UI non-blocking
                     │
                     ▼ (Background Thread Execution)
[_clone_worker()] (Lines 2834-3118)
   1. Target directory allocation & undo snapshot registration (Lines 2854-2863)
   2. Zero-latency tech-stack detection (<200ms) (Lines 2870-2871)
   3. Primary Crawl: tools/uncage/bin/uncage.js via Node subprocess (Lines 2899-2911)
      - Downloads assets, localized CSS/JS, and generates asset-map.json
   4. Post-Crawl Asset Integrity Gate: verify_local_assets() (Lines 2917-2924)
   5. Branch on output_format:
      ├─► "capture_only" / "static":
      │     Cleans raw HTML, registers clone in repo context, skips coding engine.
      └─► "raw_html" / "react" / "nextjs" / "php":
            Calls _run_reverse_engineer() (Lines 2781-2832)
            └─► Invokes actions.antigravity_agent.antigravity_action(run_in_place=True)
            └─► Spawns tools/antigravity/agy.exe CLI to rebuild project
            └─► Verifies deliverables on disk (_verify_re_artifact)
   6. Delivery: _open_deliverable() launches ThreadingHTTPServer on loopback (9400-9480)
      and opens preview in browser.
```

---

### 2.2 Website Build Execution Flow

```
[User Utterance / Fleet Task] ("Build a modern dark-mode SaaS landing page for TaskFlow")
                     │
      ┌──────────────┴──────────────┐
      ▼                             ▼
[Gemini Live Session]         [Fleet Manager Dispatch]
(actions/antigravity_agent.py) (core/fleet/dispatcher.py)
   - check_greenfield_gate()      - Selects VERVE or FLUX
   - Asynchronous TaskManager     - Injects agent.allowed_skills ("website_build")
      │                             - Calls antigravity_run(run_in_place=True)
      └──────────────┬──────────────┘
                     │
                     ▼
[core/antigravity_runner.py: run_antigravity_worker()]
   1. Validates UI task nature via is_ui_task() (Lines 118-124)
   2. Deterministic Design Resolution: core/design_resolver.py (Lines 125-140)
      - Checks explicit template names ("saas", "orbit", "dub")
      - Queries skills/website_build/references/catalog.json
      - Matches semantic route (_SEMANTIC_ROUTES) or tag scoring
      - Fallback: Loads anti-slop rules from skills/website_build/SKILL.md
   3. Template Provisioning:
      - Copies selected template to project target as reference.html
      - Caches DESIGN.md & master-template.html
   4. Prompt Construction:
      - Synthesizes user requirements, entity content, and reference constraints
   5. Native CLI Execution:
      - Launches tools/antigravity/agy.exe with Windows Job Object limits
      - Autonomously crafts final index.html and stylesheets
```

---

## 3. Subsystem Breakdown & File Inventory

| Subsystem | File Path | Current Role |
| :--- | :--- | :--- |
| **Clone** | [`actions/website_cloner.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/website_cloner.py) | Monolithic 3,311 LOC file containing crawler dispatch, asset downloading, HTTP preview server, and reverse-engineering triggers. |
| **Clone** | `tools/uncage/bin/uncage.js` | Node.js Playwright crawler used as the primary static and SPA cloning engine. |
| **Build** | [`skills/website_build/SKILL.md`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/skills/website_build/SKILL.md) | Standard Operating Procedure defining phase-by-phase design guidelines, anti-slop rules, and catalog definitions. |
| **Build** | [`skills/website_build/references/catalog.json`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/skills/website_build/references/catalog.json) | Metadata catalog linking 20 production reference HTML templates to semantic scopes and design tags. |
| **Build** | [`core/design_resolver.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/design_resolver.py) | 954 LOC deterministic design routing engine. Matches user prompt attributes to HTML references and extracts anti-slop rules. |
| **Build** | [`core/antigravity_runner.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/antigravity_runner.py) | Bridge between ZEZO orchestration and native `agy.exe` binary. Handles blueprint copying and process isolation. |
| **Build** | [`actions/antigravity_agent.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/antigravity_agent.py) | Gemini tool definition for `antigravity_run` and entry-point confirmation gates. |
| **Build** | [`actions/design_extractor.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/design_extractor.py) | Extracts color palettes, typography, and layout metadata from existing websites. |
| **Fleet** | [`core/fleet/dispatcher.py`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/dispatcher.py) | Assigns tasks to specialist agents (`VERVE`, `FLUX`) and injects allowed skills into prompts. |

---

## 4. Skills System Integration: Used vs Bypassed

### 4.1 Website Clone: Complete Bypass
* **Static Inspection:** `actions/website_cloner.py` contains **zero imports and zero calls** to `core.skill_loader`, `read_skill`, or `skills/`.
* **Architectural Impact:** The model does not read any SOP or skill when asked to clone a site. The prompt triggers `clone_website` directly. The cloning process is entirely hardcoded in Python.

### 4.2 Website Build: Direct Disk Coupling
* **Direct File Reads:** `core/design_resolver.py` directly reads `skills/website_build/references/catalog.json` ([line 244](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/design_resolver.py#L244)) and `skills/website_build/SKILL.md` ([line 152](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/design_resolver.py#L152)). It does **not** use `SkillRegistry` or the `read_skill` tool.
* **Fleet Prompt Injection:** In `core/fleet/dispatcher.py` ([lines 268–284](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/fleet/dispatcher.py#L268-L284)), the fleet orchestrator queries `SkillRegistry` for `agent.allowed_skills` and injects `[ACTIVE SKILL: website_build]` directly into the subagent prompt.
* **Prompt Stripping Paradox:** When `antigravity_runner.py` receives the fleet prompt, it explicitly runs regex to strip out `[ACTIVE SKILL: ...]` ([lines 123–139](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/antigravity_runner.py#L123-L139)) so the injected text does not pollute the `design_resolver` query.

---

## 5. Confirmed Bugs, Inconsistencies & Duplicated Logic

### 5.1 Confirmed Bugs in Website Cloner
1. **Dead/Shadowed Function `_synthesize_clean_website`:**
   * Defined at [`actions/website_cloner.py:1422-1496`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/website_cloner.py#L1422-L1496).
   * Overwritten with a completely different implementation at [`actions/website_cloner.py:2423-2520`](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/actions/website_cloner.py#L2423-L2520). The first 75 lines are unreachable dead code.
2. **Duplicate Code Block in `_extract_section_signature`:**
   * Lines 2097–2105 and lines 2107–2115 contain the exact same regex search logic placed immediately after a `return` statement. Lines 2107–2115 are unreachable.
3. **Mismatched Return Signature in `_fetch_html_and_visual_data_playwright`:**
   * Type signature at line 2365 specifies a 6-element tuple: `Tuple[str, str, dict, List[dict], List[dict], Optional[Path]]`.
   * Return statement at line 2420 only returns 3 elements: `return html, title, computed_desktop`.
4. **No-op Placeholder Assignment:**
   * Line 2957 executes `sections = capture_section_screenshots_sync  # placeholder guard`, assigning a function object without invoking it, before immediately re-running Playwright browser launch on line 2961.

### 5.2 Confirmed Inconsistencies in Website Build
1. **Broken Regex in `_get_anti_slop_rules()`:**
   * In `core/design_resolver.py:156`: searches for `r"(## 🛑 NON-NEGOTIABLE ANTI-SLOP RULES.*?)(\n## 🎯|\Z)"`.
   * In `skills/website_build/SKILL.md:186`: heading is actually `## 🛑 3. PHASE 3: ANTI-SLOP AS NEGATIVE QUALITY FILTERS (WHAT NOT TO DO)`.
   * **Result:** The regex match fails 100% of the time. `core/design_resolver.py` always falls back to its 5-line hardcoded string and never uses the rich anti-slop guidelines in `SKILL.md`.
2. **File Path & Template Mismatches:**
   * `SKILL.md` (lines 70–101) documents 5 directories and 23 templates (`1_landing_pages/saas.html`, `2_business_sites/`, `4_dashboards/`, `5_components/`).
   * Actual disk layout has **4 directories and 20 HTML files** (`1_landing_pages`, `2_portfolios`, `3_dashboards`, `4_components`). `saas.html` does not exist on disk (it is named `solvine.html`).
3. **Action Tool Naming Drift:**
   * Fleet agent configuration (`config/fleet_agents.json`) and docs list the tool as `extract_design_system`.
   * The actual file in `actions/` is named `actions/design_extractor.py`.

---

## 6. Recommendations: Ideal Architecture

To eliminate bypasses, dead code, and brittle file coupling, the following architectural alignment is recommended:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ZEZO SKILLS SYSTEM LAYER                        │
├───────────────────────────────────┬────────────────────────────────────┤
│   skills/website_clone/SKILL.md   │   skills/website_build/SKILL.md    │
│  - SOP for static & dynamic crawl │  - Anti-slop quality guidelines    │
│  - Tech stack detection rules     │  - Design system tokens & palettes │
│  - Rebuild conversion standards   │  - Component composability rules   │
└─────────────────┬─────────────────┴──────────────────┬─────────────────┘
                  │                                    │
                  ▼                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        ATOMIC TOOLS LAYER (actions/)                   │
├────────────────────────────────────────────────────────────────────────┤
│ • web_crawl (uncage / playwright / scrapling asset localizer)          │
│ • preview_server (serve local directory on dynamic port)               │
│ • resolve_design (match semantic requirements to reference templates)  │
│ • extract_design_system (parse DOM/CSS into design tokens)             │
│ • antigravity_run (execute agy.exe CLI coding engine in isolated env)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENT EXECUTION LAYER                           │
├────────────────────────────────────────────────────────────────────────┤
│ • Gemini Live (High-level intent planning & step-by-step tool calls)   │
│ • Fleet Specialists: VERVE / FLUX (Autonomous coding engines)          │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Transform Website Clone into a Declarative Skill:**
   * Create `skills/website_clone/SKILL.md` capturing the cloning SOP.
   * Break the 3,311-line `actions/website_cloner.py` into focused, reusable action tools: `actions/web_crawler.py` (Uncage/Playwright), `actions/preview_server.py` (HTTP preview), and `actions/reverse_engineer.py`.
2. **Standardize Design Resolver as an Action Tool:**
   * Expose `resolve_design` as an official action tool rather than an internal runner hook, allowing both Gemini Live and fleet agents to query design templates explicitly.
3. **Fix Anti-Slop Rule Header Sync:**
   * Synchronize the regex header in `core/design_resolver.py:156` with `skills/website_build/SKILL.md` so that the real 260-line anti-slop guidelines are dynamically extracted and applied.
4. **Align File Nomenclature:**
   * Rename `actions/design_extractor.py` to `actions/extract_design_system.py` to match its exported tool declaration and fleet configuration.
   * Update `skills/website_build/SKILL.md` to reflect the exact 4 folders and 20 templates on disk.

---
*Verified against active codebase. No files were modified during this investigation.*

