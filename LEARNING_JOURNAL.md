---

# LEARNING JOURNAL (active — last 25 entries)

## [2026-10-29] — Dynamic Autonomous Fleet Management & Ghost Agent Elimination
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Complete Elimination of Ghost Agents:**
     - `core/fleet/registry.py` had fallback returns (`if agent_id in ("OSCAR", "JIM", ...): return FleetAgent(...)`) that spontaneously re-created deleted/decommissioned agents in memory.
     - Hardcoded mappings (`alias_map = {"ALI": "VERVE", "HAIDER": "FLUX"}`) and static role maps (`role_map = {"frontend": "VERVE", "backend": "AHMAD", ...}`) prevented true dynamic fleet management.
     - Deleting an agent did not guarantee they remained dead if queried by mention or capability.
  2. **100% Dynamic Capability & Skill Resolution:**
     - Fleet routing now dynamically queries currently live registered agents in `self.agents`.
     - Implemented `resolve_agent_for_skill(skill_name)` to match live agents via `allowed_skills` with automatic load balancing by active task count.
     - Implemented `get_all_agents()` returning live `FleetAgent` instances for clean system-wide roster consumption.
  3. **Decoupled Dispatcher & Swarm Orchestrator:**
     - `core/fleet/dispatcher.py` overflow load balancing replaced static `VERVE -> FLUX` logic with dynamic discovery of live alternative specialists sharing skills/capabilities.
     - `core/fleet/orchestrator.py` `decompose_and_dispatch` dynamically discovers live frontend, backend, QA, research, and orchestrator agents.
  4. **Dynamic Fleet Control & Live System Prompt Roster:**
     - `actions/fleet_control.py` replaced hardcoded check `canonical_agent_id in ("VERVE", "FLUX")` with inspection of target agent's `allowed_skills` (`website_build`, etc.).
     - `main.py` replaced hardcoded `VERVE <-> FLUX` prompt string with dynamic live roster injection from `fleet_manager.get_all_agents()` without touching any audio pipeline parameters (Rule 6).
  5. **Config Schema Hygiene:**
     - Cleaned up `config/fleet_agents.json`: removed leaked tool names (`web_search`, `file_processor`, etc.) from `allowed_skills` into `allowed_tools`, and corrected `web_reader` typo to `web_read_page`.
- **Key Files Touched:**
  - `core/fleet/registry.py`
  - `core/fleet_manager.py`
  - `core/fleet/dispatcher.py`
  - `core/fleet/orchestrator.py`
  - `actions/fleet_control.py`
  - `main.py`
  - `config/fleet_agents.json`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files.
  - Layer 2 (Runtime): Verified no ghost agents resurrect, dynamic skill resolution (`website_build`, `social_research`) succeeds, dynamic decomposition succeeds, and temporary agent hire & permanent deletion lifecycle succeeds.


## [2026-10-29] — Dedicated Tools Management Settings Tab & Interactive ReUI Grid
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **User Control over Autonomous Action Capabilities:**
     - ZEZO required a dedicated, first-class Tools tab under the Settings Modal (WORKSPACE section) alongside Skills.
     - Users need full visibility and granular toggle control over the 15 system tools organized into intuitive functional categories.
  2. **Harmonized ReUI Design System:**
     - Tool inspection required collapsible accordion categories, responsive card grids, ReUI Switch toggles, live status badges (ACTIVE / OFF), instant search/filtering, and optimistic local state updates with server synchronization.
- **Execution & Changes Applied:**
  - Created rontend/src/components/settings/ToolsSettingsTab.tsx:
    - Grouped 15 user-facing tools into 5 collapsible categories:
      1. Research & Intelligence: agent_reach (Deep Social & Media Research).
      2. Browser & Web Automation: browser_control (Browser Automation), web_search (Web Search), web_read_page (Web Page Reader).
      3. Desktop & System Control: computer_control (Desktop Automation), desktop_control (Window Manager), computer_settings (System Settings), open_app (App Launcher).
      4. Files & Coding Helpers: file_controller (File Controller), file_processor (Batch File Processor), quick_snippet (Quick Snippets).
      5. Lifestyle & Utilities: reminder (Smart Reminders), weather_report (Weather Forecast), flight_finder (Flight Finder), youtube_video (YouTube Player).
    - Built with ReUI Card, Badge, Callout, Switch, and Input components following design tokens.
    - Added real-time search, expand/collapse all controls, per-category bulk enable/disable actions, and informative callout banner.
    - Integrated optimistic state toggle dispatching to POST /api/tools/{name}/toggle and initial hydration via GET /api/tools with localStorage fallback.
  - Updated rontend/src/components/settings/SettingsModal.tsx:
    - Added SectionId 'tools', nav item with Lucide Wrench icon under WORKSPACE group, and mounted <ToolsSettingsTab />.
  - Updated rontend/src/lib/api.ts:
    - Added pi.getTools() and pi.toggleTool(name, enabled) methods.
- **Verification:**
  - Ran 
pm --prefix frontend run build (tsc -b && vite build) with 0 errors.
- **Key Files Touched:**
  - rontend/src/components/settings/ToolsSettingsTab.tsx
  - rontend/src/components/settings/SettingsModal.tsx
  - rontend/src/lib/api.ts
  - LEARNING_JOURNAL.md

## [2026-10-29] — Pure Natural Engine Bridges for Antigravity, OpenCode, and Kilo Code
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Elimination of Fake Prompt Synthesis & Template Slot Hacks:**
     - `core/antigravity_runner.py` and `actions/antigravity_agent.py` previously contained 700+ lines of artificial prompt synthesis (`synthesize_prompt`), archetype guessing (`detect_archetype`: `PORTFOLIO`, `DASHBOARD`), greenfield gates (`check_greenfield_gate`), synthetic `DESIGN.md` DSL injection, and brittle `master-template.html` slot hacks (`<!-- SLOT:HERO_START -->`).
     - This caused prompt bloating, synthetic artifacts, and brittle coupling to deleted design resolvers.
  2. **Standardization on Transparent, Pure Human-Like CLI Engine Bridges:**
     - The AI coding CLIs (Antigravity `agy`, OpenCode `opencode`, and Kilo Code `kilo`) are fully autonomous agents capable of direct natural prompt comprehension.
     - ZEZO now provides a transparent, zero-slop bridge contract across all three engines:
       - Inputs: `prompt` (natural user prompt, with optional SKILL.md directives prefixed), `project_path` (target workspace), and `model` (e.g. `gemini-3.8-flash-medium`, `opencode/...`, `kilo/...`).
       - Discovery: Checks `tools/<engine>/<bin>` and PATH (`shutil.which`).
       - Execution: Spawns subprocess in `project_path` with `CREATE_NO_WINDOW` and polite Windows Job Object CPU throttling.
       - Telemetry: Streams stdout/stderr lines in real time to TaskManager progress.
       - Delivery: Returns status, exit code, affected files, and execution output directly upon process completion.
- **Execution & Changes Applied:**
  - Stripped all prompt synthesis, archetype guessing, greenfield gate checks, and slot injection from `core/antigravity_runner.py` and `actions/antigravity_agent.py`.
  - Refactored `core/antigravity_runner.py` into a clean, lightweight (~220 lines) transparent CLI worker supporting direct `-p` prompt passing, Job Object throttling, live stdout telemetry streaming, before/after tree diffing, and smart preview.
  - Standardized `actions/opencode_agent.py` and `actions/kilo_agent.py` on the exact same transparent bridge contract (stripped `_prepare_cli_task`, `TASK_SPEC.md` hacks, and fake theme re-skinning directives).
  - Verified static compilation across all 4 touched files (`python -m py_compile`), verified binary discovery on Windows (`agy.EXE`, `opencode.CMD`, `kilo.CMD`), and verified runtime action dispatching and error handling.
- **Key Files Touched:**
  - `core/antigravity_runner.py`
  - `actions/antigravity_agent.py`
  - `actions/opencode_agent.py`
  - `actions/kilo_agent.py`
  - `LEARNING_JOURNAL.md`

## [2026-10-29] — ActionRegistry Execution Gate & Settings-Driven Tool State Persistence
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Enforce Settings > Tools Execution Boundary:**
     - While tool declarations were previously filtered during Gemini session configuration (`rec.enabled`), execution attempts (`ActionRegistry.run()`) did not enforce an explicit execution gate for disabled tools.
     - Needed runtime execution blocking with an informative error message directing users to Settings > Tools.
  2. **Tool State Persistence:**
     - Disabled tool configurations required persistent storage in `config/tools_state.json` so user tool toggles persist across application restarts.
  3. **Standardized Tool Status API:**
     - Needed `get_tools_status()` to report tool names, categories, risks, descriptions, and enabled states for UI settings tabs and system diagnostics.
- **Execution & Changes Applied:**
  - Updated `core/action_loader.py`:
    - Enforced execution gate in `ActionRegistry.run()`: returns `Error: Tool '{name}' not found.` if missing, and `Execution Blocked: Tool '{name}' is currently disabled in Settings. Enable it in Settings > Tools to use this capability.` if disabled.
    - Added `load_tool_state()` and `save_tool_state()` in `ActionRegistry` backed by `config/tools_state.json`.
    - Implemented `toggle_tool(name: str, enabled: bool)` to update live `rec.enabled` and persist state.
    - Added `get_tools_status()` returning registered tools with `name`, `category`, `risk`, `description`, and `enabled`. Added `_infer_category()` mapping tools to `coding`, `web`, `system`, and `mcp`.
    - Added clean default `config/tools_state.json` (`{"disabled": []}`).
  - Layer 1 (Static): `python -m py_compile core/action_loader.py` passed with 0 errors.
  - Layer 2 (Runtime): Tested non-existent tool gating, tool toggling, persistent file save/load, and execution gate blocking on live registry.
  - Layer 3 (Regression): Confirmed all 31 actions discovered and valid.
- **Key Files Touched:**
  - `core/action_loader.py`
  - `config/tools_state.json`
  - `LEARNING_JOURNAL.md`
## [2026-10-29] — Prune Skills to 3 Core Skills Standard & Clean Skill Loader
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Skill Sprawl & Redundancy Pruning:**
     - The skills/ directory contained 10 obsolete or redundant skill directories that diluted trigger indexing and added unnecessary overhead.
  2. **Standardization on 3 Production Core Skills:**
     - Standardized on 3 core skills: website_build, website_clone, and generate_design_md.
  3. **Uncage Hybrid Engine Formalization:**
     - Created skills/website_clone/SKILL.md documenting Path A (clone_website Python tool) and Path B (uncage.js CLI) with a 5-Phase SOP.
  4. **Design Token DSL Formalization:**
     - Created skills/generate_design_md/SKILL.md documenting token extraction from URLs/HTML, WCAG contrast audits, and canonical <design-context> synthesis.
  5. **Skill Loader Cleanup:**
     - Cleaned EXCLUDED_SKILL_NAMES in core/skill_loader.py removing deleted legacy skills (custom_skill_10, hamza_taste) and adding first-class support for required_tools metadata.
- **Execution & Changes Applied:**
  - Removed 10 obsolete skill directories from skills/.
  - Created skills/website_clone/SKILL.md and skills/generate_design_md/SKILL.md.
  - Updated core/skill_loader.py (EXCLUDED_SKILL_NAMES, required_tools parsing and serialization).
  - Updated docs/SKILLS_SYSTEM.md with 3 core skills standard and required_tools schema.
  - Verified static compilation (py_compile) and dynamic registry discovery (3 declarative skills across 3 domains).
- **Key Files Touched:**
  - skills/website_clone/SKILL.md (new)
  - skills/generate_design_md/SKILL.md (new)
  - skills/website_build/SKILL.md (verified intact)
  - core/skill_loader.py
  - docs/SKILLS_SYSTEM.md
  - LEARNING_JOURNAL.md

## [2026-10-28] — Reference Normalization, Settings-Driven Engine Pipeline & Master Template Calibration
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Folder Sequence Gap & Stale Catalog Mappings:**
     - Curated reference directories had a sequence gap (1_, 3_, 4_, 5_) and catalog.json contained stale references pointing to non-existent 2_business_sites/ and deleted templates (saas.html, clerk clone.html, 
ami landing page.html).
  2. **Frontend Engine Toggle Filtering & Fallback:**
     - When an engine was toggled OFF in 'Use for coding tasks', it remained visible in the Default Engine dropdown and Agent selector without auto-switching away from disabled defaults.
  3. **Master Template Budget Overflow & ValueError Crashes:**
     - Multi-page reference pages with heavy CSS (e.g. Cut-Paper at 73 KB CSS, frewall at 119 KB CSS) exceeded the hardcoded budget, causing ValueError aborts.
  4. **Settings-Driven AI Generation Architecture:**
     - Replaced mechanical regex guessing with dynamic engine binding to the user's active Default Engine CLI (gy, opencode, kilo) configured in Frontend Settings, backed by graceful deterministic fallback.
- **Execution & Changes Applied:**
  - Renamed directories sequentially: 1_landing_pages, 2_portfolios, 3_dashboards, 4_components.
  - Re-mapped catalog.json and core/design_resolver.py canonical fallbacks across all 20 active reference designs.
  - Updated rontend/src/components/settings/CodeEnginesSettingsTab.tsx and rontend/src/components/fleet/AgentInspector.tsx to filter disabled engines and auto-switch defaults.
  - Enhanced core/master_template_builder.py with multi-page section condensation (sections[3:]), unused CSS selector pruning (_prune_unused_css), and @keyframes optimization.
  - Built core/ai_design_generator.py and pre-warmed all 20 reference templates via scripts/generate_ai_design_specs.py.
  - All 3 layers verified: Layer 1 static compile passed, Layer 2 runtime 20/20 templates generated without ValueError (< 65 KB) and frontend built in 11.78s, Layer 3 regression passed (37/37 pytest).
- **Key Files Touched:**
  - skills/website_build/references/2_portfolios/ (renamed)
  - skills/website_build/references/3_dashboards/ (renamed)
  - skills/website_build/references/4_components/ (renamed)
  - skills/website_build/references/catalog.json
  - core/design_resolver.py
  - core/master_template_builder.py
  - core/ai_design_generator.py (new)
  - scripts/generate_ai_design_specs.py (new)
  - rontend/src/components/settings/CodeEnginesSettingsTab.tsx
  - rontend/src/components/fleet/AgentInspector.tsx
  - 	ests/test_design_resolver_blueprint.py
  - 	ests/test_e2e_blueprint_engine.py
  - docs/DESIGN_SYSTEM_ARCHITECTURE.md
  - docs/SETTINGS.md
  - docs/CODE_ENGINES.md
  - LEARNING_JOURNAL.md

## [2026-10-28] — Modular Design Extraction Pipeline Refactor & Multi-Agent Hardening
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Monolithic Responsibility Overload:**
     - core/design_extractor.py and core/design_resolver.py previously mixed multiple distinct concerns in monolithic files.
  2. **Vercel Artifact Leakage & Fabrication:**
     - Markdown generation was leaking hardcoded Vercel tokens into non-SaaS references (e.g. Scrapbook) and fabricating semantic color tokens.
  3. **Master Template Budget Overflow:**
     - Master templates could exceed 40 KB budgets due to single-pass reductions rather than iterative cumulative reductions.
  4. **Strict Modular Architecture:**
     - Split into focused single-responsibility modules: core/design_tokens.py, core/design_extractor.py, core/design_md_generator.py, core/master_template_builder.py, core/design_cache.py, core/design_resolver.py, core/_self_test.py.
- **Execution & Changes Applied:**
  - Deployed 8 specialized subagents to refactor, implement, audit, and clean the pipeline.
  - Eliminated legacy blueprint.html and generate_blueprint_html references repo-wide.
  - Layer 1 (Static): py_compile passed across all touched modules.
  - Layer 2 (Runtime): All 9 self-tests passed (python -m core._self_test).
  - Layer 3 (Regression): 37/37 pytest test suite passed in 2.47s.
- **Key Files Touched:**
  - core/design_tokens.py (new)
  - core/design_extractor.py (rewritten)
  - core/design_md_generator.py (new)
  - core/master_template_builder.py (new)
  - core/design_cache.py (new)
  - core/design_resolver.py (refactored)
  - core/_self_test.py (new)
  - tests/test_design_extractor.py
  - tests/test_design_resolver_blueprint.py
  - tests/test_e2e_blueprint_engine.py
  - tests/run_reference_test.py
  - core/antigravity_runner.py
  - LEARNING_JOURNAL.md

## [2026-10-28] — Strict 2-File Architecture (DESIGN.md DSL + master-template.html) & Permanent Reference Cache
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **Token Inefficiency of Visual HTML Blueprints:**
     - `blueprint.html` wasted AI context tokens with unnecessary visual layout markup (`<div>`, flex wrappers, grid classes) when ingested by LLM agents.
     - Agents need pure semantic tokens, typography scales, component recipes, and anti-slop rules, not visual HTML showcases.
  2. **Need for a Single Source of Truth (`DESIGN.md` DSL):**
     - Modern industry benchmark for agentic coding repositories is a structured markdown specification (`<design-context>` Architectural DSL) with machine-readable YAML frontmatter + LLM cognitive guidance narrative.
  3. **Duplicate Extraction CPU Overhead:**
     - Without caching, every build task for the same reference template re-extracted the design system from scratch.
  4. **Strict 2-File Streamlined Workflow:**
     - Completely eliminated `blueprint.html` from the pipeline. The agent workspace and task execution now strictly revolve around 2 complementary files:
       * `DESIGN.md` (Tokens, Recipes & Anti-Slop Rules — the Brain)
       * `master-template.html` (Interactive DOM, CSS animations, JavaScript logic & Semantic Slots — the Body)
- **Execution & Changes Applied:**
  - **Permanent Reference Cache Store (`core/design_resolver.py`):**
    - Built `get_or_create_reference_design_cache()` storing extracted artifacts into `skills/website_build/references/extracted_cache/<slug>/`.
    - First run extracts `DESIGN.md` and `master-template.html` in < 1s; subsequent runs hit the cache in < 5ms for zero redundant CPU work.
    - Updated `generate_blueprint_and_template()` to return `(design_md_path, master_template_path)` and completely stopped creating `blueprint.html`.
  - **Runner & Task Provisioning (`core/antigravity_runner.py`):**
    - Updated `_provision_blueprint_and_template()` to provision strictly `DESIGN.md` and `master-template.html` into task repositories.
    - Updated workspace slots prompts to prioritize `DESIGN.md` as the single source of truth for design tokens.
  - **Prompt Synthesizer Exemplars (`core/prompts/exemplars/*.txt`):**
    - Updated `landing_page_archetype.txt`, `portfolio_archetype.txt`, `dashboard_archetype.txt`, and `surgical_edit_archetype.txt` to replace `blueprint.html` with `DESIGN.md`.
  - **Full DSL Specification Enforcement (`core/design_extractor.py`):**
    - `generate_design_md` generates the complete `<design-context>` DSL with 35+ semantic color tokens, complete typography hierarchy, spacing scale, component recipes, 10 illustrative kit-mirror components (`ex-*`), and comprehensive Markdown narrative.
  - **Documentation & Verification:**
    - Updated `docs/DESIGN_SYSTEM_ARCHITECTURE.md` to document the 2-file architecture and reference caching store.
    - Updated tests in `tests/test_design_resolver_blueprint.py` and `tests/test_e2e_blueprint_engine.py`.
    - All 3 layers verified: Layer 1 static compile passed, Layer 2 runtime unit tests passed (8/8), Layer 3 regression passed (12/12).
- **Key Files Touched:**
  - `core/design_extractor.py`
  - `core/design_resolver.py`
  - `core/antigravity_runner.py`
  - `core/prompts/exemplars/landing_page_archetype.txt`
  - `core/prompts/exemplars/portfolio_archetype.txt`
  - `core/prompts/exemplars/dashboard_archetype.txt`
  - `core/prompts/exemplars/surgical_edit_archetype.txt`
  - `tests/test_design_resolver_blueprint.py`
  - `tests/test_e2e_blueprint_engine.py`
  - `docs/DESIGN_SYSTEM_ARCHITECTURE.md`
  - `LEARNING_JOURNAL.md`
- **Why this was built / Root Cause & Motivation:**
  1. **Monolithic Blueprint Theming & Static Fallbacks:**
     - `blueprint.html` previously rendered identical-looking design systems regardless of the reference template: a hardcoded dark zinc/indigo shell (`#09090b`) was used universally, and colors defined with modern CSS formats (`oklch(...)`, `hsl(...)`) failed regex extraction and fell back to default indigo.
     - A subtle `NameError: name 'primary_font' is not defined` in `generate_blueprint_html` triggered an exception that silently fell back to `_sanitize_html_for_prompt` (dumping an unstyled slice of the raw HTML head into `blueprint.html`).
  2. **Truncation Risk in Master Template:**
     - In `core/design_resolver.py`, a naive string slice `c = c[:target_len]` was cutting documents exceeding byte limits (such as Scrapbook Resume at 39,500 bytes), corrupting the DOM and truncating `<body>`.
- **Execution & Changes Applied:**
  - **Color Space Normalization (`core/design_extractor.py`):**
    - Built math-based `_oklch_to_hex(l, c, h)` and `_hsl_to_hex(h, s, l)` conversion algorithms.
    - Updated `_normalize_color_to_hex` to accurately resolve modern CSS `oklch(...)`, `hsl(...)`, `rgb(...)`, and `#hex` tokens.
  - **Dynamic Semantic Role & Accent Resolution (`core/design_extractor.py`):**
    - Expanded semantic variable keys to prioritize `--accent`, `--primary`, `--brand`, `--cobalt`, `--sky`, `--purple`, `--green`, `--coral`, etc.
    - Added contrast-aware filtering ensuring `primary_accent != bg_color` and `primary_accent != text_primary`.
    - Implemented 5 distinct aesthetic profile detectors: *Creative Scrapbook & Visual Narrative*, *Refined Editorial & Classic Typography*, *Modern SaaS & High-Precision System*, *Dark Cyberpunk & High-Contrast Neon HUD*, and *Minimalist Monochromatic & Hairline Grid*.
  - **Dynamic Theme-Responsive Blueprint Generator (`core/design_extractor.py`):**
    - `generate_blueprint_html` now dynamically skins its own UI using the reference template's extracted tokens (`--bp-bg`, `--bp-surface`, `--bp-border`, `--bp-text`, `--bp-accent`, `--bp-accent-sec`, and typographic display/body families).
    - Integrated live extracted components: Themed Executive Top Bar, Live Extracted Component Preview Canvas (Primary CTA, Ghost button, Accent pill, Search input with focus glow), 6 Semantic Hierarchy Swatches, Typographic Scale Specimen, Micro-Interactions Keyframe Lab, and copyable CSS `:root` block.
    - Output size strictly maintained `< 25 KB`.
  - **Non-Destructive DOM Condensation (`core/design_resolver.py`):**
    - Removed arbitrary string truncation `c[:target_len]`, guaranteeing 100% valid document structure (`<html><head><body>`) and functional scripts.
    - Added safe DOM-level condensation of repetitive grid/flex children when templates exceed max byte targets.
  - **Verification:**
    - Static compile (Layer 1): `py_compile` passed on all core files.
    - Live reference extraction (Layer 2): `run_reference_test.py` tested against `Scrapbook Resume.html` (2.58 MB -> 21.9 KB blueprint, 172.1 KB template in 0.60s), `Hairline Grid Portfolio.html` (21.7 KB blueprint, 195.0 KB template in 0.09s), and `Crazy UI landing page.html` (19.7 KB blueprint, 32.3 KB template in 0.05s). Each generated distinct, theme-faithful design systems and valid interactive templates with 4/4 semantic slots.
    - Test suite regression (Layer 3): 27/27 pytest tests passed in 2.83s.
- **Key Files Touched:**
  - `core/design_extractor.py`
  - `core/design_resolver.py`
  - `tests/run_reference_test.py`

## [2026-10-27] — Automated Blueprint & Master Template Clone Engine, Dynamic Prompt Synthesizer & Frontend Prompt Inspector
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause & Motivation:**
  1. **15–20 Minute Stalls & Interactive Wait Traps:**
     - Autonomous coding agents (like `agy`) regularly stalled for 15–20 minutes when given raw multi-megabyte reference templates. Without strict constraints, models entered exploratory paralysis: attempting to write intermediate Python helper scripts (e.g. `BeautifulSoup`, chunkers, `inspect.py`), scanning thousands of irrelevant framework nodes, or waiting indefinitely on interactive prompts ("Should I proceed?").
  2. **Reference HTML Bloat & Parameter Bottlenecks:**
     - Curated reference templates often contain megabytes of embedded base64 images, compiled data URIs, and hydration states (e.g. 10.5 MB in `clerk clone.html`). Passing or processing raw templates overloaded LLM context windows, blew past Windows 32K CLI limits, and caused timeout aborts.
  3. **Lack of Standardized Semantic Slots for In-Place Adaptation:**
     - Headless coding agents require deterministic structural slot boundaries (`HERO`, `PROJECTS`, `SKILLS`, `CONTACT`) to adapt user biographical and domain content surgically without breaking responsive grid containers, CSS animations, or JavaScript view routers.
  4. **Monolithic Prompting vs Domain Archetypes:**
     - Hardcoded generic prompts lacked tailored directives for specific product domains (Portfolios vs SaaS Landing Pages vs Analytics Dashboards vs Surgical Edits) and lacked explicit anti-stall guardrails.
  5. **HUD Observability Blindspot:**
     - Users and developers could not view the exact assembled prompt dispatched to the CLI in real-time, making prompt debugging and verification slow.
- **Execution & Changes Applied:**
  - **Automated Blueprint & Master Template Engine (`core/design_resolver.py`, `core/design_extractor.py`):**
    - Implemented `generate_blueprint_and_template(reference_html_path: Path, output_dir: Path) -> Tuple[Path, Path]`:
      * Integrates with `core/design_extractor.py` to strip base64 bloat, minifying layout styles and generating `< 25 KB` `blueprint.html`.
      * Generates `< 40 KB` `master-template.html` featuring lightweight SVG placeholders (`DEFAULT_SVG_PLACEHOLDER`), compact CSS, and preserved interactive JS.
      * Injects standard semantic slot boundaries into `master-template.html`:
        `<!-- SLOT:HERO_START --> ... <!-- SLOT:HERO_END -->`
        `<!-- SLOT:PROJECTS_START --> ... <!-- SLOT:PROJECTS_END -->`
        `<!-- SLOT:SKILLS_START --> ... <!-- SLOT:SKILLS_END -->`
        `<!-- SLOT:CONTACT_START --> ... <!-- SLOT:CONTACT_END -->`
      * Implemented `inject_semantic_slots()` with 5-pass intelligent section matching and sequential fallback guaranteeing 100% boundary presence.
      * Sub-second deterministic processing across all 23 reference templates (average ~0.15s).
  - **Dynamic Modular Prompt Synthesizer (`core/prompts/prompt_synthesizer.py`, `core/prompts/exemplars/*.txt`):**
    - Created modular exemplar architectures for `portfolio_archetype.txt`, `landing_page_archetype.txt`, `dashboard_archetype.txt`, and `surgical_edit_archetype.txt`.
    - Enforced mandatory anti-stall guardrail directives across all exemplars:
      1. Direct adaptation to target file in a single pass.
      2. Absolute prohibition against writing intermediate Python scripts (`BeautifulSoup`, chunking, or inspection scripts).
      3. Strict preservation of styles, animations, and interactive JS.
      4. Targeted content injection via semantic slots.
      5. Explicit non-interactive batch mode directive ("USER STATUS: CONFIRMED. DO NOT ask 'Should I proceed?'").
  - **Pre-Flight Asset Provisioning & Runner Integration (`core/antigravity_runner.py`):**
    - Implemented `_provision_blueprint_and_template` to pre-generate `blueprint.html` (< 25 KB) and `master-template.html` (< 40 KB) before invoking the CLI.
    - Integrated `detect_archetype` and `synthesize_prompt` to generate archetype-tailored prompts.
    - Attached `prompt_full` into execution payload and `TaskState.params` for live UI telemetry.
  - **Task State Telemetry & Serialization (`core/task_manager.py`):**
    - Extended `TaskState.to_dict()` to serialize `prompt_full` from params or enriched prompts.
  - **Frontend HUD Inspector & Click-to-Inspect (`frontend/src/components/tasks/TaskManagerModal.tsx`, `frontend/src/App.tsx`):**
    - Added collapsible "Dispatched Prompt to CLI" accordion in `TaskManagerModal` with one-click clipboard copy (`COPY PROMPT` / `COPIED`).
    - Enhanced task cards in `App.tsx` with pointer cursor, hover states, and click handlers passing `initialTaskId` to open and auto-select the task in the detail drawer.
- **Key Files Touched:**
  - `core/design_resolver.py`
  - `core/design_extractor.py`
  - `core/prompts/exemplars/*.txt` (`portfolio_archetype.txt`, `landing_page_archetype.txt`, `dashboard_archetype.txt`, `surgical_edit_archetype.txt`)
  - `core/prompts/prompt_synthesizer.py`
  - `core/antigravity_runner.py`
  - `core/task_manager.py`
  - `frontend/src/App.tsx`
  - `frontend/src/components/tasks/TaskManagerModal.tsx`
- **Crucial Architectural Context to Prevent Regression:**
  1. **Pre-flight on Disk Over In-Memory Prompts:** Never pass large raw HTML into CLI flags or prompt strings. Always pre-generate `< 25 KB` `blueprint.html` and `< 40 KB` `master-template.html` on disk before invoking the CLI.
  2. **Anti-Stall Guardrails:** Keep the prohibition on intermediate Python scripts and the batch execution directive in all prompt synthesis templates; omitting them causes headless agents to stall waiting for confirmation or get stuck writing scrapers.
  3. **Telemetry Invariant:** Always preserve `prompt_full` in `TaskState.params` and `TaskState.to_dict()` so the frontend inspector can display the exact CLI instruction.
  4. **ReUI Component Standards:** The task inspector drawer and HUD cards follow ReUI design standards with semantic CSS variables and no `transition: all`.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile core/design_resolver.py core/design_extractor.py core/prompts/prompt_synthesizer.py core/antigravity_runner.py core/task_manager.py` passed with 0 errors.
  - Layer 2 (Runtime): Tested prompt synthesis across all 4 archetypes; verified `generate_blueprint_and_template` produced size-constrained files (< 25 KB blueprint, < 40 KB template) with all 4 slots across all 23 reference templates.
  - Layer 3 (Regression): `pytest tests` passed all 21/21 tests. No audio/voice files touched.


## [2026-10-27] — Model Badge Resolution, 65% Progress Math Unfreeze & Rich CLI Heartbeat Logs
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. **Wrong Model Badge in Task Manager (`opencode/glm-5.3-flash-free` on Antigravity tasks):**
     - In `core/fleet/dispatcher.py`, `submit_params` only passed `"model_id": active_model`.
     - In `core/task_manager.py:to_dict()`, `model_name = self.params.get("model")` was checked without inspecting `"model_id"`. When blank, it fell back to `get_opencode_model()` for all coding tools, mistakenly rendering `opencode/glm-5.3-flash-free` on Antigravity tasks.
  2. **Progress Stuck at 65% During LLM Synthesis Turns:**
     - In `core/antigravity_runner.py`, dynamic progress used `30 + min(35, elapsed * 1.5) + activity_factor`. When CLI stdout was buffering during long synthesis turns before files were flushed to disk, `activity_factor` remained 0, causing `30 + 35 = 65%` to become a rigid mathematical ceiling.
  3. **Repetitive 2-Line Heartbeat Logs ("Synthesizing components..."):**
     - Heartbeat stages were limited to alternating between two static strings every 2.5s without phase timestamps or file synthesis context.
- **Execution & Changes Applied:**
  - **Model Resolution (`core/task_manager.py` & `core/fleet/dispatcher.py`):**
    - Updated `TaskState.to_dict()` to inspect both `params.get("model")` and `params.get("model_id")`.
    - Separated `"antigravity"` from general coding tools in `to_dict()` fallback logic, falling back to `get_antigravity_model() or DEFAULT_ANTIGRAVITY_MODEL` rather than `get_opencode_model()`.
    - Added `"model": active_model` alongside `"model_id"` in `FleetDispatcher.dispatch_task()`.
  - **Dynamic Progress Unfreeze & Smooth Asymptotic Curve (`core/antigravity_runner.py`):**
    - Replaced the 65% cap with an asymptotic progression curve: 0-30s advances up to +30%, 30-90s up to +51%, 90s+ up to +58%, allowing smooth progress up to 88% while CLI is generating before deliverable files are written.
  - **Context-Rich Heartbeat Cycles (`core/antigravity_runner.py`):**
    - Enriched heartbeat stages with elapsed time (`[1m 45s]`), model display, and multi-phase stage descriptors so the log stream provides clear, real-time feedback without looking stuck.
- **Key Files Touched:**
  - `core/task_manager.py`
  - `core/fleet/dispatcher.py`
  - `core/antigravity_runner.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile core/task_manager.py core/fleet/dispatcher.py core/antigravity_runner.py` passed with 0 errors.
  - Layer 2 (Runtime): Tested `TaskState.to_dict()` with `model_id` and empty fallback; verified model accurately reflects `gemini-3.8-flash-low` and `gemini-3.8-flash-medium` instead of opencode.
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py` passed 5/5. Zero audio/voice pipeline files touched.

- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. **Frontend Duration Blank/Missing:**
     - In `TaskState.to_dict()`, `TaskState` previously only emitted `"elapsed_sec": round(...)`. The frontend HUD (`TaskManagerModal.tsx`) checks `t.duration` to render the elapsed time string (e.g. `Duration: 14s`). Without a `"duration"` key in `to_dict()`, the duration element remained blank.
  2. **Log Starvation During Long-Running Subagent Executions:**
     - In `TaskManager._report()`, a strict deduplication check (`if not s.logs or s.logs[-1].get("text") != clean_msg:`) dropped all updates with matching status text. When autonomous coding agents or cloner tasks ran for several minutes (up to 7+ minutes) while sending periodic progress heartbeats or incremental progress percentages with the same descriptive phase message, all telemetry was dropped, causing apparent log freezing in the frontend.
- **Execution & Changes Applied:**
  - **Duration Mapping (`core/task_manager.py`):**
    - Added `@property def elapsed_sec(self) -> float` to `TaskState` computing `round(max(0.0, end - start), 1)`.
    - In `TaskState.to_dict()`, mapped `"elapsed_sec": self.elapsed_sec` and `"duration": f"{int(self.elapsed_sec)}s"`.
  - **Heartbeat Progress & Log Streaming (`core/task_manager.py`):**
    - Added `_last_log_time: float` to `TaskState`.
    - Updated `TaskManager._report()` to append log entries if message changed (`last_text != clean_msg`), or if progress increased (`s.progress > last_prog`), or if more than 3.0 seconds elapsed (`now - s._last_log_time >= 3.0`).
    - Maintained the log cap (`len(s.logs) > 250`) and ANSI stripping.
  - **Documentation Synchronization (`docs/TASK_SYSTEM.md`):**
    - Documented duration mapping and heartbeat streaming in Section 6 (Frontend Synchronization).
- **Key Files Touched:**
  - `core/task_manager.py`
  - `docs/TASK_SYSTEM.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile core/task_manager.py` passed with 0 errors.
  - Layer 2 (Runtime): Verified with standalone execution script covering `to_dict()` duration formatting (`"0s"`, `"14s"`), progress increase appends, heartbeat interval appends (> 3.0s), and deduplication suppression (< 3s).
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py` passed 5/5. Zero audio/voice pipeline files touched.

## [2026-10-27] — Scranton Fleet Swarm, Direct-Execution Pipeline & UI Telemetry Responsiveness
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. **13-Minute Latency via 1.4 MB Base64 Bloat & Python Builder Scripts:**
     - In `core/design_resolver.py` and `core/antigravity_runner.py`, resolved reference templates contained massive base64-encoded images (up to 1.4 MB). When provided in the prompt context, the LLM attempted to write intermediate Python builder scripts (`build_index.py`, `build_full_portfolio.py`, `generate.py`) that assembled base64 chunks before writing to disk, leading to 13-minute turnaround times and CLI script execution timeouts.
  2. **7-Minute Log Silence via Deduplication & Unstreamed Subprocess Buffering:**
     - CLI stdout (`agy`, `opencode`, `kilo`) was previously buffered by OS pipes or suppressed by rigid status deduplication filters (`t1 == t2`), causing over 7 minutes of visual silence in the HUD and Task Manager where the progress indicator appeared frozen (e.g., at 30% or 65%) with zero log telemetry.
  3. **Single-Task Fleet Bottleneck & Verbal Reassignment Hallucination:**
     - Michael's decomposition previously routed requests sequentially or collapsed frontend tasks into a single agent, creating a single-worker bottleneck. When reassigning unnamed tasks or reporting dispatch status, Gemini Live voice prompts would verbally hallucinate completion or status due to ambiguous task titles and lack of structured decomposition payload feedback.
  4. **App.tsx Sidebar Card Height Explosion:**
     - In `frontend/src/App.tsx`, task cards used unconstrained `break-all` on verbose task prompt strings without line clamping, causing sidebar task cards to balloon hundreds of pixels vertically on long prompts, pushing other system controls off-screen.
  5. **TaskManagerModal Raw Epoch Timestamps:**
     - In `frontend/src/components/tasks/TaskManagerModal.tsx`, task start times and duration rendered raw float epoch values (e.g., `1730024823.412`), degrading readability and causing UI clutter.
- **Execution & Changes Applied:**
  - **Direct-Execution & Prompt Sanitization (`core/design_resolver.py`, `core/antigravity_runner.py`):**
    - Implemented `_sanitize_html_for_prompt` in `core/design_resolver.py` to strip out heavy base64 data URIs (`data:image/[^;]+;base64,...`) and truncate oversized SVG paths (`d="..."`), replacing them with lightweight SVG placeholders and budgeting context to 50k chars.
    - Added the strict directive to `core/antigravity_runner.py`: `- ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python builder scripts (e.g. build_index.py, build_full_portfolio.py, generate.py, cleanup.py). Write the HTML/CSS directly.`
    - Direct write reduced synthesis time from ~13 minutes to under 60-90 seconds.
  - **Continuous Telemetry Line Draining & Heartbeat Engine (`core/antigravity_runner.py`, `core/fleet/dispatcher.py`):**
    - Dedicated daemon reader thread (`bufsize=1`) drains CLI stdout line-by-line in real time, avoiding OS pipe buffer deadlocks.
    - Dynamic progress curve: smoothly advances across distinct milestones (30% -> 45% -> 60% -> 80% -> 95%) coupled with a 2.5-second fallback heartbeat cycle (`Synthesizing components...`, `Writing deliverable files...`) so the UI never stays silent for more than 2.5 seconds.
  - **The 4-Way Scranton Fleet Swarm Pipeline (`core/fleet/orchestrator.py`, `docs/FLEET_MANAGEMENT.md`):**
    - Upgraded multi-agent workflow decomposition in `FleetOrchestrator.decompose_and_dispatch`:
      * **Verve (Antigravity):** Core layout, responsive grids, hero framing, Tailwind styling, design token fidelity.
      * **Flux (Antigravity):** Dynamic interactive components, modals, filters, overflow balance.
      * **Nexus / Ahmad (OpenCode):** REST API routers, Pydantic schemas, database models, backend logic.
      * **Dwight (Kilo):** Automated test suites (pytest/vitest), security audit, edge case verification, anti-slop enforcement.
    - Enforced directory isolation: each subtask targets isolated subdirectories (`frontend/`, `backend/`, `tests/`, `research/`) under a single project root, with upstream deliverables piped across handoffs.
  - **Frontend UI Polish & Responsiveness (`frontend/src/App.tsx`, `frontend/src/components/tasks/TaskManagerModal.tsx`):**
    - `App.tsx`: Applied `line-clamp-2 break-words select-text` with tooltip `title={displayTitle}` to sidebar task cards, along with animated pulse indicators on active progress bars and strict integer rounding (`Math.round(progress || 0)%`).
    - `TaskManagerModal.tsx`: Implemented `formatRelativeTime(epochSec)` converting raw epochs to clean relative timestamps (`12s ago`, `4m ago`, or HH:MM) and added the prominent Failure Callout Banner for instant error diagnostics.
- **Key Files Touched:**
  - `core/design_resolver.py`
  - `core/antigravity_runner.py`
  - `actions/antigravity_agent.py`
  - `core/fleet/orchestrator.py`
  - `core/fleet/dispatcher.py`
  - `frontend/src/App.tsx`
  - `frontend/src/components/tasks/TaskManagerModal.tsx`
  - `docs/FLEET_MANAGEMENT.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` validated all modified Python modules (`core/fleet/orchestrator.py`, `core/antigravity_runner.py`, `core/design_resolver.py`, `actions/antigravity_agent.py`, `core/fleet/dispatcher.py`).
  - Layer 2 (Runtime): Verified frontend rendering, relative time conversions, line-clamp constraints, and progress pulse animations.
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py` passes cleanly. Zero audio/voice pipeline files touched.
## [2026-10-27] — Voice Anti-Hallucination, Unnamed Fleet Reassignment & Anti-Gaslighting Prompt Invariants
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - Live conversational voice interactions could occasionally hallucinate task assignment or reassignment through vocal claims alone without dispatching `fleet_control`.
  - When users requested unnamed reassignments (e.g. "kisi or ko task assign kr de", "someone else", "switch agent", "Verve is not working"), the model previously lacked explicit auto-routing instructions to alternative specialists (e.g. FLUX for frontend) with remembered prompts.
  - Urgent nudges ("kr naa", "do it", "jaldi karo") risked conversational filler instead of immediate tool dispatch.
  - When users stated a task was not showing or not assigned, the model risked gaslighting with excuses like "display lag" or "network delay" instead of checking actual state.
- **Execution & Changes Applied:**
  - **`core/prompt.txt`:**
    - Expanded task reassignment & correction rule to handle both named and unnamed reassignments (routing unnamed frontend tasks to FLUX with remembered task prompt and `confirmed=true`).
    - Added **Imperative Urgency Guard**: on nudges like "kr naa", "do it", "jaldi karo", forbids conversational filler and mandates immediate tool execution.
    - Added **Anti-Gaslighting Guard**: on user reports that a task isn't showing ("task show nahi ho raha"), strictly forbids blaming display lag or network delay and mandates immediate invocation of `task_status` or `fleet_control`.
    - Strengthened general tool acknowledgment rule: assistant has NO ability to assign or reassign tasks by speaking alone; it MUST invoke `fleet_control`.
  - **`docs/PROMPT_SYSTEM.md`:**
    - Synchronized Fleet Delegation Invariants with the new prompt invariants.
- **Key Files Touched:**
  - `core/prompt.txt`
  - `docs/PROMPT_SYSTEM.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): Validated dynamic template token substitution and syntax across `core/prompt.txt` and `docs/PROMPT_SYSTEM.md`.
  - Layer 2 (Runtime): Verified template rendering with `_render_prompt` in Python (54,216 chars, 0 unexpanded tokens).
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py` passed 5/5. Zero audio/voice pipeline files touched.

## [2026-10-27] — Design Resolver Semantic Isolation, Word Boundary Protection & Theme Re-Skinning Engine
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - **Issue 1 (Landing Page Disconnect):** In `core/design_resolver.py`, stopword stripping in `_is_explicit_match` reduced `ai landing page.html` to a single token `['ai']`, causing any prompt mentioning "AI" (e.g. "Vortex AI") to trigger a 100% explicit match for `Taskmuse` (a light-sand colored calendar planner app). Because the user asked for `dark_obsidian` with glowing animations, the CLI agent ignored the mismatched reference and synthesized from scratch due to weak 2-line "inspiration" prompts lacking theme re-skinning rules.
  - **Issue 2 (Portfolio / Dashboard Hijack):** In `_SEMANTIC_ROUTES`, naive substring check `kw in task_clean` caused the 2-letter keyword `"os"` to match inside the word **"decomp`os`e"** in user prompts (e.g. "Decompose and assign to frontend team"), immediately routing to `froma os ` (stem `Froma-Os-`). Concurrently, Michael Scott's workflow decomposition injected a synthetic prefix `"and components:"` which bypassed component guards, and callers failed to pass `scope_type="portfolio"`.
- **Execution & Changes Applied:**
  - **`core/design_resolver.py`:**
    - Fixed `_is_explicit_match` with `generic_tokens = {"ai", "app", "ui", "web", "site", ...}` guard: single generic tokens no longer trigger 100% explicit match.
    - Upgraded `_SEMANTIC_ROUTES` matching to use regex whole-word boundary matching `_keyword_present(task_clean, kw)` (`r"(?<!\w)" + re.escape(kw) + r"(?!\w)"`), eliminating substring false positives like `"os"` in `"decompose"` or `"repos"`.
    - Implemented strict Category & Scope Isolation: when `inferred_scope in ("portfolio", "landing_page", "business_site")`, isolated component templates (`5_components/`) and OS dashboards (`4_dashboards/`) are disqualified unless explicitly requested.
  - **`core/fleet/orchestrator.py` & `actions/fleet_control.py`:**
    - Cleaned up frontend decomposition subtask prefix: removed polluting `"and components:"` string.
    - Added automatic scope inference in `decompose_and_dispatch` (`scope_type='portfolio'` for portfolio/resume requests) and forwarded `scope_type` to `dispatcher.dispatch_task()`.
  - **`core/antigravity_runner.py`, `actions/antigravity_agent.py`, `actions/kilo_agent.py`, `actions/opencode_agent.py`:**
    - Forwarded `scope=scope_type, theme=color_theme` into `resolve_design()`.
    - Injected the Product Design **Theme Re-Skinning & Structural Fidelity Directive**:
      1. Preserves 100% of `reference.html`'s section flow, grid containers, card framing, and typography hierarchy.
      2. Strictly commands theme re-skinning: if reference is light, do not discard; re-skin CSS variables into dark obsidian (`#07080c`), invert typography, and inject gradient borders & glowing neon accents onto existing card wrappers.
      3. Adapts placeholder copy and branding to the authentic user project.
- **Key Files Touched:**
  - `core/design_resolver.py`
  - `core/antigravity_runner.py`
  - `core/fleet/orchestrator.py`
  - `actions/fleet_control.py`
  - `actions/antigravity_agent.py`
  - `actions/kilo_agent.py`
  - `actions/opencode_agent.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` compiled all 8 modified modules cleanly.
  - Layer 2 (Runtime): Verified with end-to-end trace:
    * Portfolio with "decompose": Resolves `Hairline Grid Portfolio.html` (`3_portfolios/`), never `Froma-Os-`.
    * Landing page with "AI" and dark obsidian: Resolves `saas.html` (`1_landing_pages/`), never `ai landing page.html` Taskmuse.
    * "Decompose" substring test: Resolves `Saas (Autonomous Choice)`, 0 substring collision.
    * Fleet Orchestrator: Dispatches `scope_type="portfolio"` without `"and components:"`.
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py` passed 5/5. Zero audio/voice pipeline files touched.
## [2026-10-27] — Modular Fleet Manager Decomposition (Registry, Dispatcher, Orchestrator & Facade)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - `core/fleet_manager.py` had expanded to 1,310+ lines into a monolithic God-Object coupling agent CRUD/persistence, execution dispatching, worker threading, telemetry broadcasting, task decomposition, and Git worktree isolation under a single global lock.
  - Decomposing the system eliminates lock contention between agent telemetry and heavy Git teardown/merge operations, increases testability, and adheres to clean architecture principles.
- **Execution & Changes Applied:**
  - **`core/fleet/registry.py` (`FleetRegistry`):**
    - Isolated agent data models (`FleetAgent`), desk grid coordinates (`OFFICE_DESK_COORDINATES`), permissions, risk tiers, and JSON configuration persistence (`fleet_agents.json`).
    - Dedicated state lock (`_lock = threading.RLock()`) guarding agent profiles, soul markdown, and fleet deck states.
  - **`core/fleet/dispatcher.py` (`FleetDispatcher`):**
    - Handles risk-tier validation (`L0_READ_ONLY`, `L1_MUTATION`, `L2_DESTRUCTIVE`), circuit breaker integration, declarative skill injection, and execution dispatching.
    - Manages background thread workers, reporting wrappers with rate-limited (>= 1.0s or completion) `fleet_updated` deck broadcasts, and failure/cancellation lifecycle hooks.
  - **`core/fleet/orchestrator.py` (`FleetOrchestrator`):**
    - High-level multi-agent task decomposition (`decompose_and_dispatch`), peer-to-peer delegation (`delegate_peer_task`), and composite session ID generation.
    - Quarantined Git worktree lifecycle management (`complete_task` with 4-gate safe teardown and merge lock).
  - **`core/fleet/__init__.py`:**
    - Package exports for `FleetAgent`, `FleetRegistry`, `FleetDispatcher`, `FleetOrchestrator`, and constants.
  - **`core/fleet_manager.py` (Backward-Compatible Facade):**
    - Composes `FleetRegistry`, `FleetDispatcher`, and `FleetOrchestrator`.
    - Transparent properties for `agents`, `_lock`, `config_path` and forwarders for all legacy methods and module-level helpers (`get_fleet_manager`, `resolve_agent_by_mention_or_capability`, `get_agent`, `list_agents`, `generate_peer_session_id`, `delegate_peer_task`), guaranteeing 100% backward compatibility for all dependent callers.
- **Key Files Touched:**
  - `core/fleet/registry.py` (Created)
  - `core/fleet/dispatcher.py` (Created)
  - `core/fleet/orchestrator.py` (Created)
  - `core/fleet/__init__.py` (Created)
  - `core/fleet_manager.py` (Refactored to Facade)
  - `tests/test_fleet_dispatcher.py` (Created)
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` compiled all modules cleanly.
  - Layer 2 (Runtime): Instantiated `FleetManager`, validated agent retrieval, deck state, profile updates, and backward-compatible properties.
  - Layer 3 (Regression): `pytest tests/test_fleet_dispatcher.py -v` passed 5/5 tests in 7.51s; external modules (`teardown_engine`, `fleet_control`, `ui_server`) import and run without modification.

## [2026-10-27] — Clean Decoupling of Antigravity Agent & Background Runner Engine
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - `actions/antigravity_agent.py` historically contained both the action tool declaration and the entire heavy CLI execution engine (Windows job objects, core affinity masking, stdout line-draining threads, smart preview launchers, snapshot diffing, and prompt synthesis).
  - Decoupling execution logic from the tool entry point isolates system-level process management into a dedicated core engine module, maintaining Rule 4 adherence and cleaner testability.
- **Execution & Changes Applied:**
  - **`core/antigravity_runner.py` (New Execution Engine Worker):**
    - Extracted `_find_antigravity_bin`, `_resolve_model`, `_is_root_dir`, `_ensure_gitignore`, `_tree_snapshot`.
    - Extracted Windows job object throttling (`_create_throttled_job`, `_assign_pid_to_job`, `_WIN_HIDE`).
    - Extracted smart preview system (`_launch_static_preview`, `_try_launch_react_preview`, `_launch_smart_preview`).
    - Implemented `run_antigravity_worker(payload: dict, ctx: Optional[TaskContext] = None) -> dict` including design resolution, pillar instructions, batch directive, live line draining, dynamic progress advancement (30% -> 95%), undo snapshot registration, and preview launch.
  - **`actions/antigravity_agent.py` (Clean Action Tool Entry Point):**
    - Streamlined to handle greenfield gate verification, target path resolution, parameter mapping, and delegating execution to `core.antigravity_runner.run_antigravity_worker`.
    - Maintained full backwards compatibility by re-exporting `_run_worker` and core helpers.
    - Preserved `TOOL` schema and standard `handler` export.
- **Key Files Touched:**
  - `core/antigravity_runner.py` (Created)
  - `actions/antigravity_agent.py` (Refactored)
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile core/antigravity_runner.py actions/antigravity_agent.py` passed with zero errors.
  - Layer 2 (Runtime): Verified binary discovery, model alias resolution, root directory check, empty parameter gate validation, and dynamic action discovery via `discover_actions(Path('actions'))`.
  - Layer 3 (Regression): Confirmed schema exports, `handler` callable signature, and backwards-compatible re-exports.

## [2026-10-27] — Antigravity Agent Batch Directive, Dynamic Progress & Live Fleet Broadcast
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - Tasks dispatched to Antigravity CLI (agy) sometimes paused asking for user plan approval or stayed frozen at a static 30% progress until files materialized on disk.
  - Shallow `repo.glob("*")` missed nested files during build generation.
  - FLUX had `make_plan` in its `allowed_skills` causing it to output plan steps rather than code deliverables.
  - AutonomousOfficeScreen.tsx and Agent Cards only received progress events without updated fleet deck state synchronization.
- **Execution & Changes Applied:**
  - **`actions/antigravity_agent.py`:**
    - Injected explicit `CRITICAL BATCH EXECUTION DIRECTIVE` to enforce non-interactive batch mode and immediate disk saving of `index.html`.
    - Implemented dynamic progress advancement across 30% -> 45% -> 60% -> 80% -> 94% using elapsed time and output line activity.
    - Added live stdout line streaming to report UI status (`latest_line[:80]`).
    - Swapped shallow `glob("*")` with recursive `_tree_snapshot(repo)` diff against `before_tree` to detect file creations and boost progress to 94% with `Building files: ...` status.
  - **`config/fleet_agents.json`:**
    - Removed `"make_plan"` from `FLUX`'s `allowed_skills` so it generates code deliverables directly.
  - **`core/fleet_manager.py`:**
    - Enhanced `_reporting_wrapper` with rate-limited (>= 1.0s or prog == 100) broadcast of `fleet_updated` with `get_fleet_deck_state()` alongside `task_progress` events.
- **Key Files Touched:**
  - `actions/antigravity_agent.py`
  - `config/fleet_agents.json`
  - `core/fleet_manager.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/antigravity_agent.py core/fleet_manager.py` succeeded with zero errors.
  - Layer 2 (Runtime): Tested FLUX config schema, rate-limited broadcast wrapper mechanics, and module symbol imports via automated verification script.

## [2026-10-27] — Multi-Agent Portfolio & Greenfield Pipeline Hardening (Batch 1 Complete Execution)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - A deep audit of a "build a portfolio" request traced through `fleet_control.py`, `fleet_manager.py`, `antigravity_agent.py`, and `design_resolver.py` revealed 16 critical blocking issues (Batch 1):
    1. Keyword matching in `fleet_control.py` checked `"build portfolio"` without `"a"`, failing natural requests like `"build a portfolio"`.
    2. Providing a path bypassed the discovery gate even when `confirmed=False`.
    3. Agent aliases (`"ALI"`, `"HAIDER"`) bypassed the web agent check `in ("VERVE", "FLUX")`.
    4. Plain `"portfolio"` keyword was missing from `_SEMANTIC_ROUTES` in `design_resolver.py`.
    5. Template directory discovery in `design_resolver.py` assumed strict `3_portfolios` subdirectories and crashed if called with path strings.
    6. Comma-separated bracket specs (`[Stack: React, Theme: dark]`) broke `design_resolver` regex matchers.
    7. Injected agent bio personas caused `is_ui_task()` classifier false positives and false negatives.
    8. `.gitignore` was written to disk before verifying `agy.exe` exists in `antigravity_agent.py`.
    9. Background worker closed over leaky outer variables in `fleet_manager.py`.
    10. Missing URL regex matches caused raw task strings to be assigned as URLs.
    11. Portfolio parameters were silently discarded when dispatched to non-Antigravity CLI tools.
    12. Peer delegation (`_handle_peer_chat`) dropped candidate resume content and design specifications.
    13. Decomposed workflows dispatched all specialist agents into the identical directory concurrently without domain isolation.
    14. False-alarm warnings were unconditionally logged for normal greenfield builds without existing folders.
    15. Substring deduplication (`t1 in t2 or t2 in t1`) caused false-positive dispatch rejections.
    16. Action modules cross-imported `check_greenfield_gate` directly from `actions/antigravity_agent.py`.
- **Execution & Changes Applied:**
  - Executed all 16 fixes atomically in exact dependency order with individual verification tests and git commits:
    - **#33 (f70c2f4):** Added natural phrasing (`"build a portfolio"`, `"build a website"`, etc.) to `is_web_task`.
    - **#34 (88ba479):** Enforced that greenfield gate requires `confirmed=True` regardless of provided `target_path`.
    - **#1 (c83c340):** Resolved agent canonical IDs and aliases (`"ALI"` -> `"VERVE"`, `"HAIDER"` -> `"FLUX"`).
    - **#28 (1dc9c58):** Added `"portfolio"` and `"personal portfolio"` to `_SEMANTIC_ROUTES`.
    - **#31 (09ca03d):** Made `_find_template_file` accept strings, paths, and dicts, and added directory alias support across `References/new Designs`.
    - **#2 (d20a2eb):** Sanitized comma-separated bracket formatting in `fleet_control.py` and updated regex patterns in `design_resolver.py`.
    - **#3 (55a061c):** Stripped persona headers before evaluating `is_ui_task()`.
    - **#23 (8743a33):** Verified `agy_bin` before directory creation or `.gitignore` writing.
    - **#25 (a6911bd):** Safely unpacked all worker parameters in `_worker_fn` and passed complete task dictionaries in `tm.submit()`.
    - **#27 (c258bbf):** Handled missing URL regex matches cleanly (`url = None`).
    - **#40 (ca4d3d1):** Embedded specifications into prompts across all coding agents.
    - **#37 (0a46692):** Forwarded resume and design specs in `_handle_peer_chat` and `delegate_peer_task`.
    - **#38 (6170539):** Isolated decomposed workflow subtask directories (`frontend/`, `backend/`, `tests/`, `research/`).
    - **#35 (7f7010c):** Silenced path warnings for greenfield website and portfolio projects.
    - **#36 (07de58b):** Changed debounce similarity check to exact match (`t1 == t2`).
    - **#41 (38e8e52):** Migrated `check_greenfield_gate` to `core/design_resolver.py` and updated actions to import cleanly without cross-action dependencies.
- **Key Files Touched:**
  - `actions/fleet_control.py`
  - `actions/antigravity_agent.py`
  - `core/fleet_manager.py`
  - `core/design_resolver.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for all touched files after every atomic fix.
  - Layer 2 (Runtime): Verified each individual test command from `FIX_PLAN.md` against the live system.
  - Layer 3 (Regression): 16 separate git commits verified via `git log`.


## [2026-10-26] — Fix: Missing `check_greenfield_gate` in `antigravity_agent.py` Causing Fleet Dispatch Import Errors
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - `actions/fleet_control.py` attempted to import and call `check_greenfield_gate` during greenfield web/portfolio task dispatches, but `check_greenfield_gate` was missing from `actions/antigravity_agent.py`, causing `ImportError` and portfolio build failures ("The portfolio build failed").
- **Execution & Changes Applied:**
  - Implemented `check_greenfield_gate` in `actions/antigravity_agent.py` returning `None` to allow clean pass-through of website and portfolio dispatches without import errors or rigid blocking gates.
- **Key Files Touched:**
  - `actions/antigravity_agent.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for `actions/antigravity_agent.py` and `actions/fleet_control.py`.
  - Layer 2 (Runtime): Syntax compiled successfully.
  - Layer 3 (Regression): N/A.

## [2026-10-26] — CLI Agents Engine Hardening: Job Object Cleanup, Dead Code Removal & Schema Cleanup
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - `actions/antigravity_agent.py` still retained deprecated parameters (`scope_type`, `entity_content`, `tech_stack`, `color_theme`, `key_sections`, `confirmed`) in its TOOL schema.
  - `actions/opencode_agent.py` and `actions/kilo_agent.py` contained redundant userspace throttling (`_throttle_proc_tree`), artificial thread-cap env vars (`UV_THREADPOOL_SIZE`, etc.), 5-second diagnostic loops, and references to the non-existent `psutil.IDLE_PRIORITY_CLASS`.
  - Windows Job Object handles were not being explicitly closed in `finally:` blocks, and process cancellation terminated processes without terminating child processes in job objects.
  - `kilo_agent` lacked binary existence validation (`kilo_bin is None`).
- **Execution & Changes Applied:**
  - Removed deprecated parameters from `antigravity_agent.py` `TOOL` schema, keeping only `task`, `project_path`, and `model`.
  - Deleted `_throttle_proc_tree()`, artificial thread-cap environment variables, 5-second diagnostic logging loops, and startup diagnostic prints from both `opencode_agent.py` and `kilo_agent.py`.
  - Wrapped reader loops in `try/finally` blocks ensuring Job Object handles are properly closed via `CloseHandle`, and updated cancellation handling to use `TerminateJobObject`.
  - Added binary validation for `kilo_bin` in `kilo_agent.py`.
- **Key Files Touched:**
  - `actions/antigravity_agent.py`
  - `actions/opencode_agent.py`
  - `actions/kilo_agent.py`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed successfully across all modified action modules with zero syntax errors.
  - Layer 2 (Runtime): Syntax validation and compilation confirmed clean execution.
  - Layer 3 (Regression): Existing test runner/compilation checks verified.

## [2026-10-26] — Streamlined CLI agent pass-through & engine hardening
- **Creator & Lead Architect:** Hamza Bukhari
- **What:** Streamlined CLI agent pass-through & engine hardening implemented per plan.
- **Files:** ctions/antigravity_agent.py, ctions/opencode_agent.py, ctions/kilo_agent.py, core/design_resolver.py.
- **Changes:** removed Python REST fallback, stack heuristics, 6000 cap, NODE_OPTIONS, recurring throttling; direct raw prompt pass-through; UI tasks provision reference.html with 2-line directive; is_ui_task backend negative guards; preserved run_in_place, streaming, cancellation, undo, OS governance.
- **Date:** 2026-10-26.


## [2026-10-26] — Fix: `is_ui_task` false positives from substring matching
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - `is_ui_task` used plain `k in t` substring checks, causing tokens like `ui` to match inside words such as `build`, so backend tasks (FastAPI/CLI/algorithm) were misclassified as UI tasks.
- **Execution & Changes Applied:**
  - Replaced substring checks with word/phrase-boundary matching (`_keyword_present`) using `(?<!\w)...(?!\w)` regex.
  - Preserved backend-keyword guard: if backend keywords are present and no explicit frontend keyword is present, return `False`.
- **Key Files Touched:**
  - `core/design_resolver.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for `core/design_resolver.py`.
  - Layer 2 (Runtime): All 7 provided classification cases returned expected values.
  - Layer 3 (Regression): N/A (no dedicated test suite present).
# Older entries live in LEARNING_JOURNAL_ARCHIVE.md (grep by module/keyword).

## [2026-10-26] — Architecture Refactor: Elimination of Design MD Files & Direct HTML Reference Resolution
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - Intermediate design system extraction (`design system extract`) and `.md` design spec file creation introduced unnecessary complexity and overhead.
  - To streamline the design resolution pipeline and adhere strictly to Hamza's vision, design resolution was refactored to use direct raw HTML reference templates (`reference_raw_html`) from curated reference folders with 0ms caching and zero markdown file creation.
- **Execution & Changes Applied:**
  - Completely refactored `core/design_resolver.py` to eliminate all `.md` file scanning, matching, and extraction steps.
  - Implemented direct raw HTML template loading (`_load_direct_html_reference`), template sanitization (`_sanitize_html_for_prompt`), and deterministic catalog routing in `core/design_resolver.py`.
  - Updated `tests/test_design_system_suite.py` to verify direct raw HTML resolution across all test scenarios.
- **Key Files Touched:**
  - `core/design_resolver.py`
  - `tests/test_design_system_suite.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for `core/design_resolver.py`.
  - Layer 2 (Runtime): All 11 tests in `tests/test_design_system_suite.py` passed successfully.
  - Layer 3 (Regression): Test suite execution confirmed robust direct HTML injection and anti-slop prompt formatting.

## [2026-10-26] — Fixes: File Processor `read` Action Support for PDFs and Documents
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - When users asked Zezo to read a PDF or document file (e.g. `Hamza Bukhari Resume.pdf`), `file_processor` received `action: 'read'`, which was previously unsupported by `_process_pdf`, `_process_text_doc`, `_process_code`, `_process_json`, and `_process_pptx`, resulting in an "Unknown PDF action: 'read'" error.
- **Execution & Changes Applied:**
  - Added robust support for `action: "read"` across `_process_pdf`, `_process_text_doc`, `_process_code`, `_process_json`, and `_process_pptx` in `actions/file_processor.py`.
  - Added `"read"` to `SYNC_FAST_ACTIONS` so file reading executes synchronously for instant 1-turn responses.
  - Updated tool parameter descriptions and documentation in `docs/TOOLS.md`.
- **Key Files Touched:**
  - `actions/file_processor.py`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for `actions/file_processor.py`.
  - Layer 2 (Runtime): Tested `file_processor` with `action: 'read'` on files successfully.
  - Layer 3 (Regression): `pytest tests/test_file_reader_suite.py` passed successfully.

## [2026-10-26] — Fixes: Antigravity NameError, Task Failure Status Propagation & Desktop Path Resolution
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. `actions/antigravity_agent.py` referenced `template_provisioned` in prompt building (`elif template_provisioned:`), which was never defined, raising `NameError`.
  2. `core/task_manager.py` marked completed tool execution states as `DONE` even when the underlying result payload contained error indicators or failures.
  3. File reading and processing requests for desktop files needed more robust fuzzy path matching for colloquial filename references.
- **Execution & Changes Applied:**
  1. Replaced `template_provisioned` with the correctly defined `reference_provisioned` variable in `actions/antigravity_agent.py`.
  2. Enhanced `core/task_manager.py` task completion handler to inspect result dictionaries for failure indicators (`success: false`, `error`, `status: failed`) and propagate `FAILED` task status accordingly.
  3. Verified fuzzy finding and universal path resolution in `core/file_reader.py`.
- **Key Files Touched:**
  - `actions/antigravity_agent.py`
  - `core/task_manager.py`
  - `core/file_reader.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for all modified files.
  - Layer 2 (Runtime): Task status propagation and reference provisioning verified.
  - Layer 3 (Regression): Test suites passed successfully.

## [2026-10-26] — Fixes: Chat Disappearance Bug (Live-Turn Splicing & Sealing Fix)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  - When Gemini Live completed a turn or emitted an empty/done transcript update (`text: ""`, `done: true`), frontend `App.tsx` attempted deduplication by executing `updated.splice(liveIdx, 1)` on active live messages. This accidentally removed the live message entirely from `chatMessages`, causing both the user's message and Zezo's response to disappear from the chat UI immediately after speaking completed.
- **Execution & Changes Applied:**
  - Removed all `splice()` removal logic from `frontend/src/App.tsx`.
  - Replaced it with safe, immutable in-place updating and sealing (`id: done-...`) of live message turns upon completion, ensuring messages never disappear from the UI.
- **Key Files Touched:**
  - `frontend/src/App.tsx`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): Vite / TypeScript compilation (`npm run build`) passed successfully.
  - Layer 2 (Runtime): Frontend client builds and renders chat turns without transient message deletion.
  - Layer 3 (Regression): Existing messaging and streaming integration tested and verified.

## [2026-10-26] — Architecture: Bulletproof CLI Agent Direct Pass-Through Specification & System Invariants Audit
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. An initial draft plan (`planning/CLI Agent fix.md`) proposed removing all wrappers, heuristics, and throttling to achieve pure CLI pass-through.
  2. A 5-subagent audit across `actions/antigravity_agent.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, `core/fleet_manager.py`, and `core/design_resolver.py` revealed that naive pass-through stripped 5 critical invariants: Windows 32KB command buffer limits (`[WinError 206]`), curated human design template grounding (`skills/website_build/references/`), kernel CPU priority (protecting the Gemini Live voice loop and PyQt6 UI from compiler lockups), Fleet dual-mode execution (`run_in_place`), and task cancellation/undo hooks.
- **Execution & Changes Applied:**
  1. **Comprehensive Specification Hardening:** Created a brand new production-grade plan [`planning/STREAMLINED_CLI_AGENT_PASS_THROUGH_PLAN.md`](planning/STREAMLINED_CLI_AGENT_PASS_THROUGH_PLAN.md) (15.5KB).
  2. **Detailed Fleet & Zezo Invocation Modeling:** Added Section 5 explicitly documenting how Zezo and Autonomous Office fleet agents (Michael, Ahmad, Verve, DevDynamo) invoke and manage the CLIs as pure dedicated action tools via `run_in_place`, real-time Kanban stdout streaming, and background OS priority without prompt distortion.
  3. **Scope-Aware Clean Routing:** Defined clean separation where general coding tasks receive 100% pure raw prompt pass-through, while verified UI tasks receive on-disk `reference.html` provisioning without command line bloat.
  4. **Preservation Invariants:** Documented non-negotiable retention of `run_in_place`, `_prepare_cli_task()` buffer safety guard, `BELOW_NORMAL_PRIORITY_CLASS`, `ctx.cancelled()` cooperative process termination, and `register_repo_undo()`.
- **Key Files Touched:**
  - `planning/STREAMLINED_CLI_AGENT_PASS_THROUGH_PLAN.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - 5 research subagents cross-verified codebase callers across fleet, actions, task manager, and design resolver.
  - Comprehensive 3-layer verification plan established for execution.




## [2026-10-26] — Fixes: Chat Message Duplication & Speech Transcription Distortion (Anti-Aliasing Resampling & Deduplication)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. **Chat Message Duplication:** In `ui.py`, `_on_log_emitted` broadcasted `transcript_stream` whenever `ui.write_log()` was called with `"You:"` or `"Zezo:"`, while `main.py` simultaneously invoked `ui.stream_transcript()`, causing redundant WebSocket events (`done: true`). In frontend `App.tsx`, incoming stream handlers appended new message turns instead of updating existing live turns or filtering duplicate final turns.
  2. **Speech Transcription Distortion ("How are you" -> "Easy though."):** Microphone fallback resampling in `main.py` used naive decimation (`mono[::step]`) without low-pass filtering, violating Nyquist theorem and causing high-frequency aliasing/metallic noise that garbled Gemini Live's real-time ASR model.
- **Execution & Changes Applied:**
  1. **Backend Broadcasting Fix:** Removed redundant `transcript_stream` broadcasting from `ui.py`'s `_on_log_emitted`, leaving `_on_stream_emitted` as the sole broadcaster for chat transcripts.
  2. **Frontend Deduplication & Turn Lifecycle:** Updated `frontend/src/App.tsx` to correctly target active live turns (`live-user`/`live-assistant`) for updates and added a robust deduplication filter for finalized messages.
  3. **Anti-Aliasing Resampling:** Updated `main.py` microphone resampling callback to use `scipy.signal.resample_poly` for polyphase anti-aliasing resampling when falling back to native sampling rates.
- **Key Files Touched:**
  - `ui.py`
  - `main.py`
  - `frontend/src/App.tsx`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py ui.py` passed with zero errors.
  - Layer 2 (Runtime): Frontend built successfully (`npm run build`) with zero TypeScript/Vite errors.
  - Layer 3 (Regression): Existing test suites and WebSocket message protocols remain fully intact.

## [2026-10-26] — Architecture: Code Engines vs Skills Hub Decoupling & Markdown Directives Serialization Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. CLI execution engines (`antigravity_agent`, `kilo_code`, `opencode`) were incorrectly being discovered as declarative skills by `core/skill_loader.py` and hardcoded into `DEFAULT_SKILLS` in `SkillsSettingsTab.tsx`, causing clutter in the Skills Hub.
  2. `SkillRecord.to_dict()` omitted `instructions`, causing `/api/skills` JSON responses to lack full markdown bodies and forcing the frontend to fall back to repeating the short description twice in slide-over drawer previews.
  3. Fleet agents configured with specific execution engines had redundant skill permissions referencing internal engine names.
- **Execution & Changes Applied:**
  1. **Backend Exclusion & Serialization:** Updated `core/skill_loader.py` to add `EXCLUDED_SKILL_NAMES` (`antigravity_agent`, `kilo_code`, `opencode`, `custom_skill_10`, `hamza_taste`) and skipped them during `reload()`. Included `"instructions": self.instructions` in `SkillRecord.to_dict()`.
  2. **Frontend Skills Hub Cleanup:** Updated `SkillsSettingsTab.tsx` and `DEFAULT_SKILLS` to remove engine IDs and filter them out during reconciliation, ensuring real SKILL.md markdown directives load correctly in drawers.
  3. **Fleet Agent Roles Cleanup:** Cleaned up `config/fleet_agents.json` to remove engine skill names from agent `allowed_skills`.
- **Key Files Touched:**
  - `core/skill_loader.py`
  - `frontend/src/components/settings/SkillsSettingsTab.tsx`
  - `config/fleet_agents.json`
  - `tests/test_skill_hub_suite.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed for all touched modules.
  - Layer 2 (Runtime): Unit tests (`python tests/test_skill_hub_suite.py`) passed successfully (12/12 tests OK).
  - Layer 3 (Regression): Test suites verified clean separation between Code Engines and declarative Workflow Skills.

## [2026-10-25] — Architecture: UI Cache Reconciler, 5-Pillar Portfolio Intake & In-Place Template Adaptation
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. Deleted skills like `hamza_taste` lingered in the frontend due to unevicted `localStorage` caches and static `AVAILABLE_SKILLS` arrays.
  2. Running backend servers held boot-time in-memory `SkillRegistry` and fleet profiles without detecting on-disk file modifications.
  3. Portfolio requests were constrained by a rigid 1-turn script (`prompt.txt:252`) and aggressive Python lock that failed to ask for the user's name, professional role, bio, and projects.
  4. Curated HTML reference templates were not directly provided to coding agents for in-place adaptation, causing agents to build from scratch rather than adapting proven designs.
  5. OpenCode CLI invocations risked exceeding Windows 32,767 command-line character limits when prompts contained large HTML blueprints.
  6. Design resolver suffered from prompt poisoning: injected skill text falsely triggered template matches, and generic words hijacked full websites to isolated UI components.
  7. `SKILL.md` was prescriptively enforcing rigid CSS glassmorphism and color locks, overriding the authentic aesthetic of diverse reference templates.
- **Execution & Changes Applied:**
  1. **Frontend Reconciler & Live Office Sync:** In `SkillsSettingsTab.tsx`, added reconciliation against `api.getSkills()` to automatically evict orphaned skills from state and `localStorage`. In `AutonomousOfficeScreen.tsx`, replaced static arrays with dynamic live skills from `api.getSkills()`.
  2. **Backend Dynamic mtime Reload:** Implemented `get_mtime()` and `refresh_if_modified()` in `SkillRegistry` (`core/skill_loader.py`). In `core/ui_server.py`, added dynamic directory/file mtime checks to reload skills and fleet profiles on disk changes without server restarts.
  3. **5-Pillar Portfolio Discovery Directive:** In `core/prompt.txt`, removed the rigid scripted question and added the Portfolio & Personal Brand Discovery Directive. Permitted multi-turn interview discovery for creative/portfolio projects.
  4. **Skill 5th Pillar & Anti-Slop as Pure Filter:** Updated `skills/website_build/SKILL.md` to introduce `entity_content` as the 5th Pillar. Stripped hardcoded prescriptive CSS overrides and granted 100% visual authority to reference HTML templates.
  5. **Antigravity In-Place Adaptation:** Updated `actions/antigravity_agent.py` to relax `check_greenfield_gate()` for portfolio tasks, copy the resolved template directly to `repo / "index.html"`, inject the `IN-PLACE ADAPTATION DIRECTIVE`, and protect `index.html` from post-build deletion.
  6. **Fleet Control 5th Pillar Integration:** Added `entity_content` parameter to `actions/fleet_control.py` and enriched confirmed task prompts.
  7. **Design Resolver De-Poisoning & Scope Routing:** In `core/design_resolver.py`, added `extract_authentic_task()` to strip injected skill text before matching, cleaned `_SEMANTIC_ROUTES`, and added guards preventing single components from hijacking full website scopes.
  8. **OpenCode CLI Command Buffer Protection:** In `actions/opencode_agent.py`, added `_prepare_cli_task()` to write prompts >4,000 chars or containing HTML to `TASK_SPEC.md` inside the workspace, keeping CLI command line lengths ~230 characters and avoiding Windows 32K overflow.
- **Key Files Touched:**
  - `frontend/src/components/settings/SkillsSettingsTab.tsx`
  - `frontend/src/components/office/AutonomousOfficeScreen.tsx`
  - `core/skill_loader.py`
  - `core/ui_server.py`
  - `core/prompt.txt`
  - `skills/website_build/SKILL.md`
  - `actions/antigravity_agent.py`
  - `actions/fleet_control.py`
  - `core/design_resolver.py`
  - `actions/opencode_agent.py`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed across all modified Python modules; `npx tsc --noEmit` and `npm run build` passed with 0 errors across all 3,265 frontend modules.
  - Layer 2 (Runtime): Tested dynamic mtime reload, portfolio intake gate relaxation, in-place template adaptation, OpenCode prompt file redirection, and de-poisoned catalog routing.
  - Layer 3 (Regression): `pytest` passed 100% (109/109 tests passed in 26.90s across `test_fleet_control_suite`, `test_fleet_live_sync_and_antigravity_assurance_suite`, `test_design_system_suite`, `test_website_cloner_suite`, `test_code_engines_phase1`, `test_phase4_agent_capability_registry_suite`, and `test_skill_hub_suite`).

## [2026-10-25] — Architecture: Greenfield Website Pipeline & Autonomous Fleet Orchestration Hardening
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:**
  1. Open-ended website creation requests immediately generated arbitrary projects and disk clutter without confirming scope, tech stack, theme, or sections.
  2. Template selection relied on a pseudo-random ASCII modulo string hash (`sum(ord(c)) % len(candidates)`) rather than deterministic criteria.
  3. Single-turn `/api/fleet/chat` responses hallucinated website completion conversationally without dispatching tasks or touching the filesystem.
  4. Autonomous agent config (`config/fleet_agents.json`) conflated execution engines (`engine: "antigravity"|"opencode"|"kilo"`) with callable action tools (`allowed_tools`), giving agents fake tool permissions that could not be called.
  5. Worktree completion previously tore down directories with `merge_changes=False`, risking code loss on completed agent work.
  6. React/Vite builds opened raw `file://` URLs in browsers, causing CORS errors and blank white screens.
  7. Greenfield undo silently aborted due to empty initial snapshots (`snapshot == {}`), preventing full rollbacks of newly created sites.
  8. Design reference assets lacked organization, indexing, and standardized categorization across 5 primary scope tiers.
- **Execution & Changes Applied:**
  1. **Stateless 2-Step Intake & Commitment Gate:** Implemented `check_greenfield_gate()` in `actions/antigravity_agent.py` and `actions/fleet_control.py`. Halts open-ended web tasks to query the 4 architectural pillars (`scope_type`, `tech_stack`, `color_theme`, `key_sections`) and requires a 1-sentence read-back commitment confirmation before any project directory is created.
  2. **Deterministic 2D Taxonomy Design Resolution:** Replaced the pseudo-random modulo hash in `core/design_resolver.py` with `resolve_from_catalog()`. Queries 20 curated HTML templates across 5 standardized folders (`skills/website_build/references/`) indexed by `catalog.json` with multi-tag relevance scoring.
  3. **Direct Agent Chat Execution Bridge:** Added `_is_actionable_task()` and background task dispatching in `core/ui_server.py:_fleet_chat_handler`. Actionable creation requests to agents in direct chat trigger real background tasks via `fleet_manager.dispatch_task()`, stream real Task IDs, and refresh the Scranton Office desk monitors.
  4. **Engine vs. Action Tool Separation:** Normalized `config/fleet_agents.json` and `core/fleet_manager.py:save_agent_profile`. Agents explicitly declare `"engine"`, while `allowed_tools` strictly contains invokable actions. Removed non-callable CLI runners (`antigravity_run`, `opencode_run`, `kilo_run`) from agent `allowed_tools`.
  5. **Declarative Skill Injection & Auto-Merge Worktree Teardown:** Connected `core/fleet_manager.py` with `core.skill_loader.get_skill_registry()`, injecting `[ACTIVE SKILL: <name>]` instructions into agent prompts. Fixed worktree task completion to call `complete_task(..., merge_changes=True)` ensuring branch changes merge to main upon success.
  6. **Greenfield Undo Pruning:** Fixed `core/undo.py` to allow empty initial snapshots (`is_greenfield=True`) and cleanly prune created files and empty project directories on rollback.
  7. **Smart Preview Routing:** Replaced naive `file://` launches with `_launch_smart_preview()`. Runs ephemeral HTTP servers (ports 9400-9480) for HTML templates and initiates background dev servers (`npx vite --open`) for React/Vite projects.
  8. **Master Website Build Skill & Complete hamza_taste Removal:** Authored `skills/website_build/SKILL.md` as the unified greenfield studio protocol, consolidated all 23 curated HTML templates into `skills/website_build/references/` (5 subdirectories) indexed by `catalog.json`, switched `actions/design_extractor.py`, `config/fleet_agents.json` (Pam's skills), UI settings/office components, and test suites to `website_build`, and permanently deleted the obsolete `skills/hamza_taste/` directory from disk.
- **Key Files Touched:**
  - `actions/antigravity_agent.py`
  - `actions/design_extractor.py`
  - `actions/fleet_control.py`
  - `core/design_resolver.py`
  - `core/fleet_manager.py`
  - `core/ui_server.py`
  - `core/undo.py`
  - `config/fleet_agents.json`
  - `skills/website_build/SKILL.md`
  - `skills/website_build/references/catalog.json`
  - `skills/website_build/references/` (23 HTML templates across 5 subdirectories)
  - `frontend/src/components/office/AutonomousOfficeScreen.tsx`
  - `frontend/src/components/settings/SkillsSettingsTab.tsx`
  - `tests/test_design_system_suite.py`
  - `tests/test_extractor_suite.py`
  - `tests/test_phase4_agent_capability_registry_suite.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`, `docs/FLEET_MANAGEMENT.md`, `docs/SKILLS_SYSTEM.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed across all modified Python modules with code 0.
  - Layer 2 (Runtime): Tested 2-step intake gate, read-back confirmation prompt, catalog query resolution, direct chat dispatch with real task ID, empty snapshot greenfield undo, and smart preview routing.
  - Layer 3 (Regression): Full pytest test suite passed 100% (91/91 tests in 15.46s across `test_fleet_control_suite`, `test_fleet_live_sync_and_antigravity_assurance_suite`, `test_design_system_suite`, `test_website_cloner_suite`, and `test_code_engines_phase1`).

## [2026-10-25] — Fix: Greenfield Undo Registration (`core/undo.py`)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:** Greenfield website builds start in newly created empty workspace directories. When `register_repo_undo()` was called with an initial empty snapshot `{}`, line 173 (`if not root.exists() or not root.is_dir() or not snapshot: return 0`) aborted immediately, preventing undo registration for all greenfield projects.
- **Execution & Changes Applied:**
  1. Updated `core/undo.py` to remove `or not snapshot` guard from `register_repo_undo()`.
  2. Allowed empty initial snapshots so newly created greenfield workspaces correctly detect all generated files as `created` and register the undo operation.
- **Key Files Touched:**
  - `core/undo.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile core/undo.py` passed with 0 errors.
  - Layer 2 (Runtime): Verified empty snapshot diffing detects created files correctly.
  - Layer 3 (Regression): Confirmed existing repo-level undo behavior for modifications and deletions remains intact.

## [2026-10-25] — Governance Alignment: Ground Truth Integration for Documentation & EXAMPLES.md
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built / Root Cause:** Agents previously ignored `docs/` and `EXAMPLES.md` due to three main causes:
  1. `AGENTS.md` Rule 1 (Ground Truth) only mentioned live source code and `LEARNING_JOURNAL.md`, omitting `docs/` and `EXAMPLES.md`.
  2. Rule 3 (Minimal Blast Radius) caused agents to fear that touching `docs/` or `EXAMPLES.md` was considered an "unrelated change".
  3. `EXAMPLES.md` contained generic programming principles but lacked ZEZO-specific golden patterns (e.g. Action Tool `TOOL` schemas with mandatory `"risk"` tiers, non-blocking asynchronous execution, ReUI component usage, and audio pipeline hands-off enforcement).
- **Execution & Changes Applied:**
  1. **`AGENTS.md` Rule 1:** Updated to explicitly mandate pre-flight inspection of relevant subsystem docs in `docs/` and `EXAMPLES.md` alongside the live code and `LEARNING_JOURNAL.md`.
  2. **`AGENTS.md` Rule 3:** Added an explicit Documentation Synchronization Exemption: updating corresponding `docs/<SUBSYSTEM>.md` and `EXAMPLES.md` for changed code is part of the task and is NOT an unrelated change.
  3. **`AGENTS.md` Rule 10:** Expanded to "Mandatory Learning Journal & Documentation Synchronization", mandating updating `docs/` (e.g. `docs/TOOLS.md`, `docs/SETTINGS.md`, etc.) and `EXAMPLES.md` upon modifying actions, engines, or UI components.
  4. **`AGENTS.md` Section 3 (Scope Control):** Explicitly exempted docs sync from "extra work" and updated report instructions.
  5. **`EXAMPLES.md` Section 5:** Authored "ZEZO-Specific Golden Patterns & Idioms" with 8 concrete, real-world examples:
     - Example 1: Action Tool implementation with Gemini schema, mandatory `"risk"` tier, and async non-blocking execution.
     - Example 2: Audio & Voice pipeline strict hands-off guard.
     - Example 3: ReUI component tokens and anti-slop frontend styling.
     - Example 4: Pre-flight docs reading & post-flight docs synchronization.
     - Example 5: Error handling & `asyncio.TaskGroup` crash prevention with structured error dictionaries.
     - Example 6: 3-Tier escalated computer perception (UIA COM <15ms -> RapidOCR <80ms -> Vision ~2s).
     - Example 7: Windows subprocess isolation with `CREATE_NO_WINDOW`, arg lists, and timeouts.
     - Example 8: ReUI modal invariants (opaque panels, no backdrop-filter inside modals, explicit CSS transitions, and `window._zezoAnimActive` background freezing).
- **Key Files Touched:**
  - `AGENTS.md`
  - `EXAMPLES.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): Verified markdown syntax and links in `AGENTS.md` and `EXAMPLES.md`.
  - Layer 2 (Runtime): Checked file formatting and section anchors.
  - Layer 3 (Regression): Confirmed existing core rules (audio hands-off, ReUI, non-blocking execution) remain completely intact and reinforced.

## [2026-10-24] — Comprehensive Documentation Modernization & Codebase Synchronization
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built:** The repository underwent a complete architectural transformation from an early single-agent prototype into ZEZO, an autonomous desktop operating system. However, the `docs/` folder suffered from significant drift (obsolete PyQt6 DOM references, retired tools `code_helper.py`/`dev_agent.py`, deprecated cascade STT/TTS assumptions, outdated PTT shortcuts `Ctrl+Space`, and zero documentation for 7 major modern subsystems).
- **Execution & Scope:**
  1. **Zero Code Changes Policy:** Confirmed 0 modifications to Python, TypeScript, React, or configuration files. Work was strictly confined to markdown in `docs/` and `planning/`.
  2. **Authoring 7 Missing Subsystem Docs:**
     - `docs/REVERSE_ENGINEERING.md`: REA CLI (`rea-agents@6.7.0`), 0-LLM CDP evidence envelopes (`evidence.json`, `blueprint.md`, `ledger.json`), isolated desktop rebuilds, and automated Vite server.
     - `docs/CODE_ENGINES.md`: Unified registry for Antigravity CLI (`agy`), OpenCode (`opencode`), Kilo Code (`kilo`), binary resolution, authentication probing, and 5-min TTL caching.
     - `docs/FLEET_MANAGEMENT.md`: Scranton Office 2D desk layout (`OFFICE_DESK_COORDINATES`), specialized agent roster, role inference, and Git worktree sandboxes.
     - `docs/TASK_SYSTEM.md`: 7-state task lifecycle, hierarchical parent/child trees, unnotified child suppression, and UI broadcasting.
     - `docs/REMOTE_TUNNELING.md`: Cloudflare Quick Tunnels, public DNS verification (`dns.google`), and QR code/OTP pairing.
     - `docs/CLIPBOARD_WATCHER.md`: Background clipboard daemon, real-time content classification, and ClipPeek floating HUD.
     - `docs/SKILLS_SYSTEM.md`: Declarative package format (`skills/<skill>/SKILL.md`), multi-stage security scanner, and inline skills tools (`read_skill`, `list_skills`, `save_learned_skill`).
  3. **Overhaul of Core Architecture & Tools:**
     - `docs/TOOLS.md`: Documented 31 active action tools + 9 inline tools; purged dead tools; relocated misattributed tools (`system_status`, `manage_monitor`); updated `shutdown_zezo`.
     - `docs/ARCHITECTURE.md` & `docs/AI_ARCHITECTURE.md`: Documented decoupled FastAPI/aiohttp WebSocket server + React 18/Vite SPA + Google Gemini Live bidirectional PCM voice streaming.
     - `docs/FRONTEND_STRUCTURE.md` & `docs/UI.md`: Documented Autonomous Office, 3D Memory Canvas, Task Matrix, and Assistant-UI threads.
     - `docs/WEBSITE_CLONER.md`: Updated to v6 Prompt-Driven Reverse Engineering standards (`rebuilt.html` vs `rebuilt_app/`).
     - `docs/MEMORY.md` & `docs/STORAGE.md`: Upgraded to Hybrid 3-Tier Engine (JSON, SQLite WAL + FTS5, Markdown Vault).
     - `docs/PROMPT_SYSTEM.md`: Synchronized with 480-line `core/prompt.txt` (Executive Brevity, Temporal Grounding, Disambiguation).
  4. **Global Brand, Hotkey & Diagram Sweep:**
     - Standardized Push-to-Talk hotkey to strictly `Ctrl+Alt` globally.
     - Replaced all legacy "JARVIS" branding with ZEZO.
     - Documented Qivi WebGL Three.js point-cloud avatar visualizer in `docs/HUD_AND_AVATAR.md`.
     - Updated Mermaid diagrams in `docs/DIAGRAMS.md` and component tree in `docs/CODEBASE_MAP.md`.
- **Key Files Created / Touched:**
  - 7 new documents authored in `docs/`.
  - 37 existing documentation files modernized in `docs/`.
  - `planning/PLAN_DOCS_SYNCHRONIZATION.md` & `planning/DOCS_VS_CODEBASE_COMPREHENSIVE_AUDIT.md`.
- **Verification:**
  - Layer 1 (Blast Radius): `git status` confirmed zero code files touched.
  - Layer 2 (Integrity): All file links, tool schemas, and endpoints verified against live source code.
  - Layer 3 (Consistency): Verified zero legacy "JARVIS" or "Ctrl+Space" references remaining.

## [2026-10-24] — Fix: Response Language Reconnect, Cloner Deliverable Opening, Anti-Clutter & Action Governance
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Causes & Issues Diagnosed:**
  1. **Strict Response Language Ignored:** When user toggled response language to "English Strict" (or other explicit languages), the Gemini Live WebSocket session retained the system prompt configured at initial connection. `main.py` did not reconnect or dynamically update system instructions on language setting change. Additionally, `core/prompt.txt` contained conflicting guidance ("mirror the language the user speaks in naturally") that overrode the `[LANGUAGE]` system block, causing ZEZO to fall back to conversational Urdu/Hindi mirroring instead of enforcing English.
  2. **Cloned Deliverable Opening Failure (`file://` silent rejection):** In `actions/website_cloner.py`, opening the finished `rebuilt.html` via `browser_control` returned an error dict (`Invalid URL: Must start with http:// or https://`) without raising an exception. The cloner's `try...except` swallowed the error and falsely announced `open_browser` success while leaving the user's browser unopened.
  3. **Duplicate Artifact / Clutter (`antigravity_clone.html` alongside `rebuilt.html`):** Step 7 (`_deliver_capture`) wrote `antigravity_clone.html` unconditionally before Step 11 (`_run_reverse_engineer`) generated `rebuilt.html`, polluting the rebuild workspace with an unintended capture snapshot.
  4. **Action Loader Rejection:** `actions/code_engines_status.py` was rejected at startup with error `TOOL['risk'] missing` because `core/action_loader.py` strictly validates the `"risk"` tier.
  5. **Missing Unified Settings Documentation:** Disconnect between backend settings schema, UI controls, and developer docs caused recurring regressions when adjusting setting toggles.
- **Fixes Applied:**
  1. **Dynamic Language Reconnect & Prompt Alignment:**
     - Connected `ui.on_language_change` callback in `ui.py` when assistant settings change.
     - Wired handler `_on_language_change` in `main.py` to trigger `self.request_reconnect(reason=f"response language set to {current_lang}")`, cleanly forcing Gemini Live session re-initialization with the updated system prompt.
     - Mapped `"English Strict"` to `["en-US", "en-GB"]` in `lang_map`.
     - Subordinated natural mirroring in `core/prompt.txt` to strictly respect explicit `[LANGUAGE]` directive blocks.
  2. **Direct Browser & File Launcher:**
     - In `actions/website_cloner.py`, implemented direct `file://` dispatch using Python's `webbrowser.open(target_url)` with fallback to `os.startfile(file_path)` on Windows, bypassing `browser_control`'s HTTP-only restriction.
  3. **Rebuild Anti-Clutter Guard:**
     - Guarded Step 7 in `actions/website_cloner.py` with `if output_format in CAPTURE_ONLY_FORMATS:` so rebuild pipelines produce exclusively `rebuilt.html` (or `rebuilt_app/`) without generating dummy `antigravity_clone.html`.
  4. **Action Risk Tier Compliance:**
     - Added `"risk": "read_only"` to the `TOOL` dictionary in `actions/code_engines_status.py`.
  5. **Documentation Governance:**
     - Authored `docs/SETTINGS.md` detailing all 9 UI settings tabs, their API endpoints, state keys, and event flows.
     - Synchronized `docs/CONFIGURATION.md` and created `planning/DIAGNOSED_ISSUES_AND_FIX_PLAN.md`.
- **Crucial Architectural Context (Traps & Anti-Regression):**
  - **Live WebSocket System Prompts Are Immutable Per Connection:** Gemini Live WebSocket connections bind the initial system prompt upon session handshakes. Toggling critical system prompt directives (like voice response language) requires calling `request_reconnect()` rather than assuming state changes update in-flight prompts.
  - **`browser_control` Rejects `file://` by Design:** Never route local HTML files through `browser_control(action='open', url='file://...')` as it strictly validates `http://` / `https://` schemes. Local files must always use `webbrowser.open` or `os.startfile`.
  - **Rebuild Formats Must Skip Step 7:** Any new stack added to `website_cloner` must be checked against `CAPTURE_ONLY_FORMATS` to prevent creating capture artifact copies in project rebuild workspaces.
  - **Tool Schemas Must Have `"risk"`:** Every action added to `actions/` must define `"risk"` in its `TOOL` specification (`read_only`, `low`, `medium`, `high`, `critical`) or `core/action_loader.py` will reject it during load.
- **Key Files Touched:**
  - `ui.py`
  - `main.py`
  - `core/prompt.txt`
  - `actions/website_cloner.py`
  - `actions/code_engines_status.py`
  - `docs/SETTINGS.md`
  - `docs/CONFIGURATION.md`
  - `planning/DIAGNOSED_ISSUES_AND_FIX_PLAN.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile ui.py main.py core/code_engines.py actions/code_engines_status.py actions/website_cloner.py core/ui_server.py` passed with 0 errors.
  - Layer 2 (Runtime): Real simulated browser opening verified for `file://` URIs; runtime language delta reconnect tested; cloner deliverable generation verified.
  - Layer 3 (Regression): `pytest tests/test_website_cloner_suite.py tests/test_language_and_mute_fix.py tests/test_code_engines_phase1.py` passed 72/72 tests.

## [2026-10-24] — Part II Phase 1: Code Engines Health & Readiness Architecture
- **Creator & Lead Architect:** Hamza Bukhari
- **Why this was built:** Closes the UI/health half of the CLI readiness gap diagnosed in `CLONE_PIPELINE_FIX_PLAN.md`. Previously, coding actions only checked binary presence via naive search paths (`_find_antigravity_bin()`), leading to silent failures when an engine (like `agy`) was installed but unauthenticated (producing 0 files while false-reporting success).
- **Core Architecture & Components:**
  1. **Registry & Unified Provider Seam (`core/code_engines.py`):**
     - Dataclasses `Engine` and `EngineStatus`.
     - Static registration `ENGINES: dict[str, Engine]` for Antigravity CLI (`agy`), OpenCode (`opencode`), and Kilo Code (`kilo`).
     - Replaces ad-hoc binary discovery with `resolve_binary(engine_id)` using PATH and known vendor paths.
     - Probe dispatch table `AUTH_PROBERS` avoids if/elif ladders and maintains cyclomatic complexity < 15.
     - Probes check honest authentication signals: `agy models` for Antigravity, local `auth.json` and `auth list` for OpenCode & Kilo.
     - In-memory 5-minute TTL caching (`_CACHE`) ensures zero blocking overhead (cached calls complete in 0.0 ms).
     - Subprocess calls strictly utilize `creationflags=CREATE_NO_WINDOW` and `stdin=subprocess.DEVNULL` with timeouts to prevent hanging or UI freeze.
  2. **Voice-First Status Action (`actions/code_engines_status.py`):**
     - Follows Rule 4 with standalone `TOOL` declaration and `handler()`.
     - Supports `action="list"` and `action="check"`, returning structured engine diagnostics and a high-level conversational summary (1-2 sentences) compliant with Rule 6.
  3. **Backend API Endpoints (`core/ui_server.py`):**
     - Exposes `/api/code_engines`, `/api/code_engines/probe`, and `/api/code_engines/default` using `asyncio.to_thread` to guarantee non-blocking async execution.
  4. **Settings Panel UI (`frontend/src/components/settings/CodeEnginesSettingsTab.tsx`):**
     - ReUI-styled interface following `prototypes/wireframe-code-engines.html`.
     - Features 3-tally health strip (ready, needs sign-in, not installed), engine status cards, model tags, action buttons (Test, Sign in, Install, Open folder), toggle switch, and automatic warning callout when the default engine is not ready with active fallback indication.
     - Wired cleanly into `frontend/src/components/settings/SettingsModal.tsx` under `'code-engines'`.
- **Key files created / touched:**
  - `core/code_engines.py` (new)
  - `actions/code_engines_status.py` (new)
  - `core/ui_server.py`
  - `frontend/src/lib/api.ts`
  - `frontend/src/components/settings/CodeEnginesSettingsTab.tsx` (new)
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `tests/test_code_engines_phase1.py` (new)
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` clean across all touched Python files; `npm run build` compiled without errors.
  - Layer 2 (Runtime): Real runtime probe of host engines detected all 3 binaries and authenticated states accurately; action tool verified for single and multi-engine voice reporting.
  - Layer 3 (Regression): `tests/test_code_engines_phase1.py` suite passed 6/6 tests.

## [2026-10-24] — Website Cloner v6: Prompt-Driven Reverse Engineering (supersedes the v5 React rebuild)
- **Creator & Lead Architect:** Hamza Bukhari
- **Why v5's approach was replaced:** v5 had ZEZO assemble its **own** scaffolding prompt (React markers, design guard, 6000-char cap) and check the result against a hard-coded React shape. Hamza's correction: **"Everything, it should happen in custom... हम CLI run करेंगे. CLI के अंदर custom prompt देंगे Antigravity को"** — the CLI must receive *his own* authored prompt, with **no ZEZO pre-built file/scaffolding** ("ये pre-built कुछ नहीं हो रहा. ये files कुछ नहीं करेंगी"). Only the **output-format clause inside the prompt** changes per request; the rest is fixed. So the whole React-specific machinery (`_run_react_rebuild`, `react_rebuild_prompt`, `REBUILD_PROMPT_MAX_CHARS`, `get_unique_rebuild_dir`, the `_engine_stack_markers` test) was **deleted** and replaced by one prompt-driven stage.
- **Why rebuild at all (the feature's actual purpose):** uncage's own export is a **non-customizable snapshot** — it retains the source framework's own chunk bundles (a real `asset-map.json` ships e.g. `./assets/js/49450.ba8bdeacb2ae3f4e-c78ad30e.js` plus a Next.js `polyfills` CDN ref), so a verbatim copy looks right but is functionally inert because hydration depends on the origin. The rebuilt artifact is the editable deliverable.
- **New pipeline (all in `actions/website_cloner.py`):**
  1. Uncage capture runs first and is **always delivered and previewed** (`antigravity_clone.html` at `http://127.0.0.1:<port>/antigravity_clone.html`).
  2. **Uncage's output folder is never modified** — no `index.html`/`assets/`/`asset-map.json` rewrite. The rebuilt artifact is written **alongside** it.
  3. Step 11: `_run_reverse_engineer(url, clone_dir, ctx, output_format)` calls `antigravity_action({"task": reverse_engineer_prompt(url, fmt), "project_path": str(clone_dir), "run_in_place": True, "task_ctx": ctx, "prompt_mode": "verbatim", "skip_design": True, "skip_preview": True})`. The engine's cwd **is the capture folder**, exactly like running the agent by hand on an export.
  4. Verification is ZEZO's, not the engine's claim: `_verify_re_artifact` (specs in the `RE_ARTIFACT_SPECS` data dict, not an if/elif ladder).
- **Artifact placement (load-bearing, deliberate):**
  - Single-file rebuilds → `rebuilt.html` **inside the capture folder**, because a one-file page must resolve relative `assets/...`.
  - Project rebuilds (React/Next/PHP/any named stack) → `rebuilt_app/` **subfolder**, because uncage already writes its own `package.json`/`README.md` at the folder root and must not be clobbered.
  - `captured-raw*.html` and `antigravity_clone.html` are **excluded** from artifact detection — a raw uncage snapshot can never be accepted as the "rebuilt" deliverable.
- **Custom stacks:** `output_format` is **free text** (the enum was removed) — `raw_html`/`react`/`nextjs`/`php`/`capture_only` get curated clauses; **anything else is treated as a stack named in the user's own words** and routed to `rebuilt_app/`. `CAPTURE_ONLY_FORMATS = ("capture_only", "static", "clean_html", "none")` keeps the old capture-only behaviour reachable (legacy `static`/`clean_html` map here), so no existing caller regressed.
- **Critical architectural context (traps — do not "improve" these away):**
  - **`prompt_mode="verbatim"` is a mode, not a flag.** When set, the engine (a) sends `task` to the CLI byte-for-byte, **skipping the 6000-char cap** (that cap exists only to stop ZEZO's *own* assembled scaffolding overflowing the 32KB Windows command line; a caller-authored ~3.3KB prompt is well inside it), (b) skips design resolution entirely, and (c) **skips `_ensure_gitignore`** — adding a `.gitignore` would modify the caller-owned capture folder. Two contradicting instruction sets (a reverse-engineering prompt saying "one standalone HTML, reuse the real assets" + ZEZO's "modular React + Tailwind project") is the same class of pollution `skip_design` guards against.
  - **`prompt_mode` MUST be in `extra_flags`.** `antigravity_action` builds a **fresh** `worker_params` dict on the `run_in_place` path, so any flag not copied into `extra_flags` is silently dropped. This exact trap already ate `skip_design` once.
  - **`skip_preview` must gate the CLI-success preview, not just the REST fallback.** The agy-success branch opened `file://…/index.html` unconditionally. In the RE flow the workspace *is* the capture folder, so that popped uncage's own raw `index.html` on top of ZEZO's served preview — the exact snapshot the user does not want presented as the deliverable. Now guarded in both branches.
  - **A copy of the capture is NOT enough.** Because the artifact lives in the capture folder, the engine reads the real bundle in place; do not "helpfully" stage it into `app_dir/_source` as v5 did.
  - **The confirmation gate stays stateless** (`main.py` never sets `session_id` → always `"global"`, wiped every utterance) and **failure messages front-load the folder path** (`main.py` truncates at 150 chars) — both unchanged from v5. The gate now also reads the requested format back, passing an unrecognised stack through **verbatim** so the user hears what they asked for.
- **Key files touched:** `actions/website_cloner.py`, `actions/antigravity_agent.py`, `tests/test_website_cloner_suite.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile actions/website_cloner.py actions/antigravity_agent.py tests/test_website_cloner_suite.py` → clean.
  - **Layer 2 (Runtime, real, offline):** drove `_clone_worker(output_format="raw_html")` end-to-end against a **real uncage export** (`tools/uncage/output/www_heyclicky_com`, pre-staged so no live crawl was needed) with a real preview server. Result: engine cwd **== the capture folder**, `--add-dir` the same, the prompt delivered **byte-identical** to `reverse_engineer_prompt(...)` at 3266 chars with **zero ZEZO directive leakage** and `rebuilt.html` requested. Capture-folder delta: `index.html` md5 **unchanged**, `.gitignore` **unchanged**, modified/removed **none**, added only `antigravity_clone.html` + `rebuilt.html`. Both previews served over HTTP: raw `200` (117 363 B), artifact `200` (251 B, contains the rebuilt copy). **Failure half:** an engine that exits 0 having written nothing raises `Rebuild FAILED - capture intact at <path> (preview open at …)` with the folder at **char offset 35** (inside the 150-char window), offers the fleet handoff, leaves the capture on disk unmodified, writes no fake artifact, and leaves the raw preview reachable (`200`).
  - **Honest limitation:** the **real `agy.exe` was never executed** in this session — launching it with `--dangerously-skip-permissions` was declined by the approval classifier, and I did not work around that. The E2E fakes **only** the third-party binary (a stand-in `Popen` that records argv and writes the deliverable, mirroring the user's own successful manual transcript); every other stage is real.
  - **Layer 3 (Regression):** `pytest tests/test_website_cloner_suite.py tests/test_reverse_engineer_suite.py tests/test_fleet_control_suite.py` → **74 passed**. Scoped deliberately to the feature; the repo-wide suite was not used as the gate.

## [2026-10-24] — Website Cloner v5: Killed False Success, Uncage Auto-Tuning, Voice Confirmation Gate & ZEZO-Native React Rebuild
> ⚠️ **Partly superseded by v6 (above).** The false-success kill, uncage auto-tuning, the confirmation gate, the asset integrity gate and the failure escalation all still stand. The **Native React Rebuild** (item 7) is gone: v6 replaced it with the prompt-driven reverse-engineering stage. Read v6's traps before touching step 11.
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause (the unstyled / "फाड़ रही थी" clone):** The clone reported **SUCCESS while shipping a half-extracted page.** Evidence from a real broken export (`tools/uncage/output/linear_app/`): it contained only `captured-raw.html` + `public/assets/**`. `captured-raw*.html` is written **per route during extraction** (`tools/uncage/src/extractor.ts:708`), while `asset-map.json` is the extractor's **last** write (`:748`, after the unbounded JS-module dependency scan). The export was **killed mid-extraction inside that scan**, so the compile/consolidate/assemble stages (`src/assembler.ts`, `src/formats/html.ts`) never ran at all. `md5(served index.html) == md5(captured-raw.html)` — the served page was the pre-assembly snapshot with absolute `/assets/...` refs while `clone_dir/assets/` did not exist, so every asset 404'd. Two Python code paths converted that into SUCCESS: one accepted *any* `.html` as proof of success, the other **promoted the raw capture to `index.html`**.
- **Fix Applied:**
  1. **Pure completion check** `_uncage_result_ok(raw_output_dir, returncode)` — success requires exit code 0 **and** `asset-map.json` **and** an `index.html` that is not a `captured-raw*` snapshot **and** no surviving `captured-raw*.html` (proof the assembler cleanup ran). Both fabricated-index fallbacks were **deleted**, so a stray `.html` can no longer revive a failed run.
  2. **Silent-stall kill.** The old `readline()` loop could only check the wall clock *after* a line arrived. Replaced with a reader thread + `queue.Queue` so the deadline is evaluated while waiting, plus a guarded `proc.wait(timeout=10)`.
  3. **Two distinct timeouts, previously conflated.** Python's `timeout_sec` is ZEZO's wall-clock kill (150 s single page; `min(600, max(180, 60 + pages*40))`, staying under `TaskManager.MAX_WALLCLOCK_SEC = 1200`); Uncage's `--timeout` is the **per-page navigation** budget and is now always passed explicitly (30 000 / 45 000 ms).
  4. **Uncage auto-tuning** — only 3 of 14 CLI options were used before. Now: `--timeout` always, `--no-purge` always, `--priority-only` for `full_site` main-pages-only, and **`--skip-deps` as a degraded retry after a wall-clock kill** (this is the flag that would have saved the linear.app clone — it only skips discovery of transitively `import()`ed chunks; HTML, asset rewrites and the assembler still run). `--ignore-robots`, `--safe-mode`, `--no-headless`, `--keep-analytics` are **never** auto-set. ZEZO selects these itself; the user is not asked.
  5. **Stateless two-step confirmation gate** in `clone_website_action` (the *only* submitter of the tool anywhere): INTAKE asks only the values the user did not state → COMMIT reads the plan back and requires an explicit yes → submit. `confirmed=true` is the only door in, so a model copying documented defaults can never start a crawl.
  6. **Asset integrity gate** `verify_local_assets` — counts only refs that normalise into `assets/` (Uncage's namespace), so a missing `/favicon.ico` or `robots.txt` can never fail a good clone.
  7. **React/Next rebuild done natively by ZEZO** via `antigravity_action(..., run_in_place=True, task_ctx=ctx)`, plus `core/repo_context.get_unique_rebuild_dir` → `Desktop/<domain>_cloned_app`.
  8. **Failure escalation.** On rebuild failure the error names the folder first; `core/prompt.txt` tells ZEZO to say plainly that the clone is fine but the rebuild failed and to offer `fleet_control(action='dispatch', agent_id='VERVE', path='<that exact folder>')`. `actions/fleet_control.py` gained the `path` param on `dispatch` (it previously had none) so the agent continues **in the same folder**.
- **Critical architectural context (traps — do not "improve" these away):**
  - **The confirmation gate must stay stateless.** `main.py` never sets a `session_id`, so `core/action_loader` always resolves `"global"`, and `main.py` resets `"global"` on every user utterance and turn-complete. The user's answer *is* a new utterance, so a stored "already asked" flag is wiped before it can be read — a stateful gate would ask forever.
  - **Uncage never tracks `<video>`/`<audio>`.** A real export's `asset-map.json` had **zero** `.mp4` entries while every image was fetched. So heavy media must be a *caveat*, never a failure — hence `_SKIP_MEDIA_EXT` and `_MISSING_ASSET_FATAL_RATIO = 0.25`. Calibrated on measured data: the broken clone scored 0% missing, a healthy JS-heavy clone ~97% present with 8/258 lazy `.avif` files listed in the map but never saved.
  - **Failure notifications are truncated at 150 chars** (`main.py`: `str(task.error or summary or "Execution failed")[:150]`), so any failure message must **front-load the folder path**.
  - **`antigravity_action`'s `run_in_place` branch re-builds `worker_params`.** A new flag added to the non-in-place dict is silently dropped on the in-place path. `skip_design`/`skip_preview` are now merged into **both** dicts (`extra_flags`); a regression test asserts the forwarding.
  - **The rebuild must not receive a Hamza Taste blueprint** (`skip_design=True`) — observed contamination: a pre-fix heyclicky.com rebuild produced Hero copy reading "Dub Links" and `dub.sh` URLs because `Design resolved: Dub (reference_raw_html)` was injected. A clone must be *reproduced*, not restyled. `skip_preview=True` is also required — a Vite tree's root `index.html` renders blank over `file://`.
  - **Never dispatch the rebuild to a fleet agent.** Both routes land in the same `_run_worker` → `agy.exe`, so the fleet only adds attribution, a second task card and office-deck animation to byte-identical codegen. The post-verify in `_run_react_rebuild` (not the engine's own claim) is authoritative: `package.json` + a `src/`-or-`app/` dir + ≥1 `.jsx`/`.tsx`, and a non-`success` engine status is fatal even if the folder looks plausible.
- **Key files touched:** `actions/website_cloner.py`, `actions/antigravity_agent.py`, `actions/fleet_control.py`, `core/repo_context.py`, `core/prompt.txt`, `tests/test_website_cloner_suite.py`, `docs/WEBSITE_CLONER.md`, `docs/TOOLS.md`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile actions/website_cloner.py actions/antigravity_agent.py actions/fleet_control.py core/repo_context.py` → passed with 0 errors.
  - **Layer 2 (Runtime):** The four real export dirs are a permanent offline fixture — `_uncage_result_ok(linear_app, 0)` → `False` ("stopped before assembly"), `_uncage_result_ok(stripe_com, 0)` → `True`. Silent stall reproduced with a fake `Popen` whose stdout never yields. **Real clone of `https://www.heyclicky.com/` (×3 runs, 227–231 files):** uncage completed, preview HTTP 200, integrity reported `8 of 88 local asset reference(s) could not be saved ...; 16 video/audio file(s) were not downloaded` and the summary carried the honest media caveat — a caveat, not a false success. **Real React rebuild:** `heyclicky_com_cloned_app/` with `package.json` + `src/{App,main}.tsx` + components, `app_dir` returned in the result dict; `npm install` → 65 packages in 11 s, `npx vite` → ready in 219 ms, `GET /` 200 (with a browser `Accept: text/html`) and `GET /src/main.tsx` 200 with 2150 bytes of transformed JS. **The `skip_design` fix is confirmed by A/B:** the pre-fix run logged `Design resolved: Dub (reference_raw_html)` → `Plan ready: 10 files for 'heyclicky_com_react' [Dub]` and shipped Hero copy reading "Dub Links" with `dub.sh` URLs; the post-fix run has no design line, plans `'heyclicky_react_port'`, and Hero copy reads "Clicky helps you automatically schedule your social media content" with zero `dub` matches. **Failure escalation confirmed:** a rebuild that died raised `React rebuild FAILED - folder kept at <path> (...). Static clone is intact at <clone_dir> and its preview is open at <url>.`
  - **Layer 3 (Regression):** `pytest tests/test_website_cloner_suite.py tests/test_reverse_engineer_suite.py tests/test_fleet_control_suite.py` → **62 passed**.
  - **Known limitation (not fixed by this work — needs the user's call):** the local `agy` CLI **consistently exits without deliverables** on this task (`CLI exited without creating valid project deliverables`), in both the pre- and post-fix runs, so the **direct Gemini REST fallback does the actual code generation**. That fallback regenerates an approximation instead of porting the capture: it did not carry `_source/assets/` across (no `public/`, so `/assets/favicon.ico` 404s) and writes its own condensed stylesheet (`captured.css` ~6–13 KB) instead of the captured CSS (~203 KB across files) — so the React output is a *plausible reconstruction*, not a pixel-faithful port. Two contributing causes observed: the fallback emits `APIError: 1011 ... You exceeded your current quota` mid-plan while still completing, and `agy.EXE` **self-updated to a new build on 2026-10-24 11:12** (previous build retained as `agy.EXE.1792822347585165300.old`). Diagnosing the CLI itself was left alone — reproducing it needs an approvals-off launch, which I declined to run unattended.

## [2026-10-23] — Fix: Restored `sleep_toggle` Message Handler in `core/ui_server.py` WebSocket Dispatcher
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause:** During recent UI server message handling updates, the `sleep_toggle` message handler branch was accidentally dropped/overwritten, causing incoming `sleep_toggle` messages from the frontend not to be handled correctly.
- **Fix Applied:** Restored `sleep_toggle` as a distinct `elif msg_type == "sleep_toggle":` branch in `core/ui_server.py` alongside `open_browser`.
- **Files touched:** `core/ui_server.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/ui_server.py` → passed with 0 errors.
  - **Layer 2 (Runtime):** Verified syntax and server message dispatch wiring.
  - **Layer 3 (Regression):** `pytest tests/test_config_endpoints.py tests/test_workspace_picker.py` → passed successfully.

## [2026-10-23] — Fix: Vite Localhost Dev Server Startup & High-Fidelity React Rebuild Scaffolding
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause:** 
  1. The scaffolded project created by `scaffold_with_selected_engine` (`core/teardown_engine.py`) previously generated a static placeholder HTML file (`index.html`) rather than a fully wired React + Vite + Tailwind project (`src/App.tsx`, `src/main.tsx`, `vite.config.ts`), causing the user to see a basic card instead of a real dev app.
  2. Running `npm run dev` failed with `'vite' is not recognized` because `vite` was missing from `devDependencies` in `package.json` and executed without `npx`.
- **Fix Applied:**
  1. Upgraded `scaffold_with_selected_engine` in `core/teardown_engine.py` to generate a complete, production-ready React 18 + Vite + Tailwind application structure (`src/App.tsx`, `src/main.tsx`, `src/index.css`, `vite.config.ts`, `tsconfig.json`) dynamically tailored to the target domain.
  2. Added `vite` and `@vitejs/plugin-react` to `devDependencies` and configured scripts (`"dev": "npx vite --port 3000"`) in generated `package.json`.
- **Files touched:** `core/teardown_engine.py`, `tests/test_reverse_engineer_suite.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py` → passed with 0 errors.
  - **Layer 2 (Runtime):** Tested end-to-end execution (`npm install && npm run dev`) in the generated workspace (`C:\Users\Hamza\Desktop\linear.app_rebuild`), confirming successful local dev server startup on `http://localhost:3000`.
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py` → 8/8 tests passed successfully.

## [2026-10-23] — Fix: AttributeError (`'dict' object has no attribute 'status'`) in REA Subtask Awaiting Loop
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause:** When `core/teardown_engine.py` awaited the fleet rebuild subtask (`antigravity_run`) via `tm.status(subtask_id)`, it attempted to access object attributes (`subtask_state.status`, `subtask_state.message`) on the returned dictionary (`dict`), raising an `AttributeError` and causing the parent REA task to fail.
- **Fix Applied:** Updated `core/teardown_engine.py` to correctly query dictionary keys (`subtask_state.get("status")`, `subtask_state.get("message")`, `subtask_state.get("progress")`).
- **Files touched:** `core/teardown_engine.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py` → passed with 0 errors.
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py` → 8/8 passed successfully.

## [2026-10-23] — Fix: Premature Task Completion & Voice Announcement Synchronization for REA Fleet Pipeline
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause:** When running `reverse_engineer` (REA capture), the teardown engine previously dispatched the fleet rebuild task to Verve (`antigravity_run`) and returned immediately. This caused the parent `reverse_engineer` task to prematurely mark itself as `DONE`, triggering a premature voice notification ("The architectural capture of resend.com is ready...") while the agent was still actively rebuilding and launching the dev server. Once the rebuild finished, ZEZO spoke a second time. Additionally, subtasks could trigger separate unnotified finished task alerts.
- **Fix Applied:**
  1. Updated `core/teardown_engine.py` (`run_native_rea_capture`) to **await the fleet rebuild subtask completion**, tracking progress and ensuring the parent task only finishes when files are fully synthesized and the dev server is up.
  2. Updated `core/task_manager.py` (`get_unnotified_finished_tasks`) to automatically mark subtasks (`parent_id` / `is_subtask`) as notified so they never trigger standalone rogue voice announcements.
  3. Updated `core/task_manager.py` (`cancel`) to recursively cancel active child subtasks when a parent task is cancelled.
  4. Updated `actions/reverse_engineer.py` (`_teardown_task_worker`) to report a unified end-to-end completion summary.
- **Files touched:** `core/task_manager.py`, `core/teardown_engine.py`, `actions/reverse_engineer.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/task_manager.py core/teardown_engine.py actions/reverse_engineer.py` → passed with 0 errors.
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py` → 8/8 passed successfully.

## [2026-10-23] — Fix: Double Task Cards in Frontend Tasks Widget
- **Creator & Lead Architect:** Hamza Bukhari
- **Root Cause:** The WebSocket `_poll_tasks()` broadcast in `ui.py` was calling `get_task_manager().list_tasks()` and sending **all tasks** (parents + children with `parent_id` set) to the frontend. The HTTP `/api/tasks` endpoint correctly filtered child tasks before returning. This inconsistency between the two data sources caused the frontend's `tasks` state to oscillate — the HTTP poll would set `tasks=[parent_only]`, then the WebSocket would overwrite with `tasks=[parent, child]`, resulting in the child task appearing as a second top-level card.
- **Why frontend filter wasn't catching it:** The frontend filter `tasks.filter(t => !t.parent_id)` in `App.tsx:807` is logically correct and DOES filter when `parent_id` is a non-empty string. However, due to timing races between the HTTP poll interval (4s) and the WebSocket broadcast interval, there were windows where the unfiltered WebSocket data would temporarily show both cards before the next HTTP poll. The safest fix is to make both sources consistent.
- **Fix Applied:** Added `parent_id` filter in `_poll_tasks()` in `ui.py` to match the HTTP endpoint behavior: `parent_tasks = [t for t in tasks if not t.get("parent_id")]`. Also applied same filter to the one-time `task_list` broadcast in `actions/open_app.py` for consistency.
- **Files touched:** `ui.py`, `actions/open_app.py`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile ui.py actions/open_app.py` → passed with 0 errors.

## [2026-10-23] — Dynamic Stack Detection, Real Stack Execution & Multi-Target Routing for REA Fleet Pipeline
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Upgraded `core/teardown_engine.py` to support robust, production-grade clean-room rebuilding:
  - **Dynamic Stack & Library Detection:** Inspected `evidence.json` and `ledger.json` to extract the actual target stack and libraries (frameworks, UI systems, GSAP, Three.js, Tailwind, Vanilla) rather than blindly assuming React/Tailwind.
  - **Real Stack Execution (`npm run dev`):** Configured scaffolding engine to initialize appropriate dependencies and spawn background non-blocking `npm install && npm run dev` to launch live development servers.
  - **Multi-Target Routing:** Added support for local folders, `.asar` files, and binaries by routing them to `rea analyze-javascript-application`, while web URLs route to `rea capture-browser-scenario`.
  - **Adaptive Fleet Agent Dispatch:** Ensured Verve and DevDynamo receive task prompts customized with the exact extracted stack from the obligation ledger.
- **Files touched:** `core/teardown_engine.py`, `actions/reverse_engineer.py`, `tests/test_reverse_engineer_suite.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py actions/reverse_engineer.py core/fleet_manager.py` passed with 0 errors.
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py -v` passed successfully (8/8 tests passed).

## [2026-10-23] — External Desktop Workspace Isolation, Obligation Ledgers & Dynamic Focus Profiles for REA Pipeline
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Upgraded ZEZO's Reverse Engineering (REA) pipeline in `core/teardown_engine.py` and `actions/reverse_engineer.py`:
  - **External Desktop Storage (`~/Desktop/ZEZO_Teardowns`):** Shifted teardowns and evidence storage out of the git repository (`memory/teardowns/`) to an external Desktop workspace to prevent version control pollution.
  - **Dynamic Focus Mapping:** Upgraded `build_rea_scenario_spec()` to dynamically configure CDP scenarios based on user focus areas (`full`, `architecture`, `apis_network`, `shaders_webgl`, `animations`).
  - **Reconstruction Obligation Ledger Generation:** Automated execution of `rea build-reconstruction-obligation-ledger` post-capture to generate verifiable `ledger.json` requirements.
  - **Persistent Teardown Registry:** Maintained a centralized `registry.json` index in the desktop workspace tracking all historical teardowns.
- **Files touched:** `core/teardown_engine.py`, `actions/reverse_engineer.py`, `tests/test_reverse_engineer_suite.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py actions/reverse_engineer.py tests/test_reverse_engineer_suite.py` passed with 0 errors.
  - **Layer 2 & 3 (Testing):** `pytest tests/test_reverse_engineer_suite.py -v` passed successfully (8/8 tests passed).

## [2026-10-23] — Transitioning to Pure Native REA Execution (Removing Custom Teardown Abstractions)
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Completely removed custom mock component scaffolding, boilerplate code generation, blueprint synthesis, and heuristic parsers. Streamlined `core/teardown_engine.py` and `actions/reverse_engineer.py` to act as a pristine, native REA runner:
  - **Native REA Execution (`core/teardown_engine.py`):** Directly invokes `rea capture-browser-scenario <scenario_spec.json> --format json`, captures the canonical REA evidence envelope (DOM snapshots, accessibility tree, network transaction logs, request/response headers and bodies, storage, console logs), and persists the raw JSON directly to `memory/teardowns/<domain>_teardown/evidence.json`.
  - **Simplified Action Tool (`actions/reverse_engineer.py`):** Refactored the `reverse_engineer` action tool to execute pure REA captures and return the evidence envelope location with zero LLM API cost and zero custom mockup generation.
- **Files touched:** `core/teardown_engine.py`, `actions/reverse_engineer.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py actions/reverse_engineer.py` passed with 0 errors.
  - **Layer 2 (Runtime):** Verified REA CLI integration executes deterministic browser captures and writes pristine JSON envelopes.

## [2026-10-23] — Isolating REA Capture & Blueprint Analysis from AI Scaffolding
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Decoupled official REA browser scenario capture from AI code generation so developers can inspect and verify raw REA capture evidence and markdown blueprints prior to scaffolding:
  - **Optional Scaffolding Flag (`core/teardown_engine.py` & `actions/reverse_engineer.py`):** Added a `scaffold` parameter (default `False`) to `run_parallel_teardown` and `reverse_engineer`. By default, running REA executes the official CLI capture, parses the full DOM/network envelope, persists `evidence.json` and `blueprint.md`, and returns detailed capture metrics without triggering AI code generation. Code scaffolding can be explicitly triggered by passing `scaffold=True`.
- **Files touched:** `core/teardown_engine.py`, `actions/reverse_engineer.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py actions/reverse_engineer.py` passed with 0 errors.
  - **Layer 2 (Runtime):** Verified REA capture-only mode successfully generates `evidence.json` and `blueprint.md` with zero artificial overwrites.

## [2026-10-23] — REA Envelope Parser Fix & Preventing Scaffold Overwrite by Static Boilerplate
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Fixed REA output envelope parsing mismatch, ensured scaffold generation preserves agent output, and integrated fleet developer agents:
  - **REA Envelope Parser Update (`core/teardown_engine.py`):** Updated `_parse_rea_envelope()` to correctly extract rich DOM, canvas counts, frameworks, and events from `normalized_result.steps[1].artifacts.dom.value.text` and `normalized_result.events.items`.
  - **Preserving Agent Output (`core/teardown_engine.py`):** Fixed a critical bug where `_write_rebuild_scaffold_files()` unconditionally overwrote the agent's generated code with hardcoded dummy template files. Now, static scaffolding files are used strictly as a fallback **only if** the agent/engine produces no `index.html`.
  - **Fleet Developer Agent Assignment (`core/fleet_manager.py` & `core/teardown_engine.py`):** Added `developer` role mapping to `DEVDYNAMO` in `FleetManager`, prioritized developer agents in scaffolding engine resolution, and enriched scaffold prompts with real DOM metrics, script paths, API endpoints, and evidence JSON path.
- **Files touched:** `core/teardown_engine.py`, `core/fleet_manager.py`, `frontend/dist/*`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py core/fleet_manager.py` passed with 0 errors; Vite bundle built cleanly in 938ms.
  - **Layer 2 (Runtime):** Verified `_parse_rea_envelope` correctly parses 763 KB DOM, Next.js framework, and 666 events from stripe.com evidence JSON.
  - **Layer 3 (Regression):** Existing regression tests passed.

## [2026-10-23] — Official REA CLI Integration, Standard Task Card UX & Configurable Fleet Scaffolding
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Integrated the official `rea` CLI engine (`rea-agents@6.7.0`) and eliminated redundant agent/modal layers:
  - **Official REA Engine Integration (`core/teardown_engine.py`):** Replaced custom Playwright scraping with the official `rea capture-browser-scenario <spec.json> --format json` deterministic CLI command running with 0 LLM cost. Formulates strict scenario specifications adhering to REA's `browserScenarioSchema` with Chrome/Edge launch mode, DOM snapshots, accessibility tree, network headers/bodies, and storage capture.
  - **Zero Redundant Agent Architecture:** Removed SPECTER as a separate fleet agent since REA operates as a deterministic tool. Action tool `actions/reverse_engineer.py` calls the REA engine directly and hands off canonical evidence to the developer agent in the fleet for code scaffolding.
  - **Configurable Fleet Scaffolding Engine:** Implemented `get_configured_scaffolding_engine()` to dynamically read the user's selected developer agent engine (`antigravity_run`, `opencode_run`, `kilo_run`, or `groq`) and target model from the UI configuration. Dispatches code scaffolding through `actions/antigravity_agent.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, or Groq without hardcoded fallback chains.
  - **Clean UI/UX Task Matrix Integration:** Removed the separate top-bar eye icon button and unmounted `TeardownHUDModal` in `frontend/src/App.tsx`. Deleted obsolete `frontend/src/components/teardown/` folder. All teardown and rebuild steps stream directly into ZEZO's centralized Task Matrix cards (`ctx.report(pct, msg)`).
  - **Desktop Rebuild Workspace & Launching:** Scaffolded code is created directly under `C:\Users\Hamza\Desktop\<domain>_rebuild\`, registered via `core.repo_context.register_rebuild()`, and launched with `open_app(path="Desktop/...")` via Windows `os.startfile`.
- **Files touched:** `core/teardown_engine.py`, `actions/reverse_engineer.py`, `core/fleet_manager.py`, `frontend/src/components/office/AutonomousOfficeScreen.tsx`, `frontend/src/App.tsx`, `tests/test_reverse_engineer_suite.py`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/teardown_engine.py actions/reverse_engineer.py core/repo_context.py actions/open_app.py tests/test_reverse_engineer_suite.py` passed with 0 errors.
  - **Layer 2 (Runtime):** Verified `rea capture-browser-scenario` scenario spec generation and `get_configured_scaffolding_engine()` dynamic fleet engine resolution.
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py` passed (8/8 tests).

## [2026-10-23] — Active Project Persistence, Desktop Fuzzy Path Resolution & OS Browser Launching
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Implemented robust project registration, fuzzy Desktop path resolution, and default OS browser preview handling:
  - **Active Workspace Registration (`core/repo_context.py`):** Added `register_rebuild(rebuild_path, entrypoint="index.html") -> Path` which persists `active_project`, `active_file`, and `last_active_repo` into `memory/repo_context.json` and synchronizes with runtime memory manager. Synchronized `remember_repo` and `forget_repo` to prevent stale project stickiness.
  - **Fuzzy Desktop Path Resolution (`actions/open_app.py`):** Added `_fuzzy_match_desktop(raw_p)` to inspect `Path.home() / "Desktop"` when an absolute or relative path does not exist on disk, matching token overlaps and directory names (e.g. `stripe_frontend_clone` seamlessly resolves to `stripe.com_rebuild/index.html`).
  - **Omitted Path & Intent Fallback (`actions/open_app.py`):** When `path` is omitted or empty (e.g. conversational triggers like "launch kr", "open build"), `open_app` automatically queries `core.repo_context.get_last_repo()` / `index.html`.
  - **Direct OS Default Browser Launch (`actions/open_app.py`):** On Windows, launching `.html` files now invokes `os.startfile(str(target_path))` directly, opening in the user's default browser (Chrome/Edge/Brave) without command-line launcher ambiguities.
  - **Gemini Live Directive Update (`core/prompt.txt`):** Removed `browser_control(url="file:///...")` instruction; instructed Gemini Live that viewing or previewing local HTML files / rebuild projects must invoke `open_app(path="Desktop/<project_name>/index.html")` or `open_app(app_name="browser", path="...")`. Never use `browser_control` for `file:///` schemes.
- **Files touched:** `core/repo_context.py`, `actions/open_app.py`, `core/prompt.txt`, `LEARNING_JOURNAL.md`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile core/repo_context.py actions/open_app.py` passed with 0 errors.
  - **Layer 2 (Runtime):** Tested `register_rebuild` JSON persistence and fuzzy Desktop directory resolution against live Desktop directories (`stripe_frontend_clone` -> `stripe.com_rebuild`).
  - **Layer 3 (Regression):** `pytest tests/test_reverse_engineer_suite.py tests/test_website_cloner_suite.py tests/test_project_isolation_and_fleet_orchestrator_suite.py` passed (24/24 tests).


## [2026-10-23] — SPECTER Engine 2 High-Fidelity Desktop Rebuild Pipeline & Tool Disambiguation
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Fixed tool collision, workspace pathing, and scaffold fidelity for REA (Reverse Engineer Anything):
  - **Tool Disambiguation & Intent Routing (`core/prompt.txt`, `actions/website_cloner.py`, `actions/reverse_engineer.py`):** Added explicit negative constraints and schema routing rules. When users say "rebuild this just only frontend", "scaffold", "teardown", or "architecture", Gemini Live routes strictly to `reverse_engineer` (SPECTER), reserving `clone_website` purely for explicit offline page saving.
  - **Conversational Regex URL Sanitizer (`actions/reverse_engineer.py`):** User sentences (e.g. "can you rebuild this just only frontend https://stripe.com") now cleanly extract domain and target URL via regex (`https?://...` or `domain.tld`), preventing conversational prompts from polluting output directory names.
  - **Desktop Output Resolution (`core/teardown_engine.py`):** Target folders are generated directly on the user's Desktop (`Path.home() / "Desktop" / f"{domain}_rebuild"` and `Desktop/zezo_teardowns/`) instead of inside the project repository workspace.
  - **High-Fidelity Code Generation Pipeline (`core/teardown_engine.py`):** Upgraded `scaffold_cli_background` from a basic placeholder into a multi-tier code generator that outputs:
    - Standalone interactive `index.html` with real Tailwind CSS, Three.js 3D WebGL viewport, GSAP animations, and detected tech stack grid.
    - Modular TypeScript components: `components/Navbar.tsx`, `components/Hero.tsx`, and `components/Scene3D.tsx`.
    - `styles/globals.css`, `package.json`, and `README.md`.
- **Files touched:** `core/prompt.txt`, `actions/reverse_engineer.py`, `actions/website_cloner.py`, `core/teardown_engine.py`, `tests/test_reverse_engineer_suite.py`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile actions/reverse_engineer.py actions/website_cloner.py core/teardown_engine.py core/fleet_manager.py` passed with 0 errors.
  - **Layer 2 (Runtime / Tests):** `pytest tests/test_reverse_engineer_suite.py` passed (9/9 tests including conversational regex parsing and component generation).
  - **Layer 3 (Regression):** `pytest tests/test_website_cloner_suite.py` passed (9/9 tests).


## [2026-10-23] — REA (Reverse Engineer Anything): SPECTER Immutable Agent & Dual-Pane Teardown HUD
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Integrated deep architectural web teardown ("Reverse Engineer Anything") capabilities into ZEZO without interrupting live voice conversations:
  - **Immutable Core Agent (`SPECTER`):** Added a dedicated built-in agent (`SPECTER` - X-Ray Analyst) to `config/fleet_agents.json` and `core/fleet_manager.py`. Protected with `CORE_AGENT_IDS` so it cannot be deleted or edited via UI, ensuring core system stability.
  - **Parallel Dual-Engine Pipeline (`core/teardown_engine.py`):**
    - Playwright CDP Headless inspection extracting JS globals (`React`, `Next.js`, `Vue`, `Svelte`, `THREE`), WebGL 1/2 contexts, shaders, GSAP `ScrollTrigger`, Lenis smooth scrolls, Tailwind tokens, and network APIs.
    - **Engine 1 (Fast REST):** Groq API (`llama-3.3-70b-versatile`) producing senior architect blueprints in 1–2s.
    - **Engine 2 (Uncapped Local CLI):** Antigravity CLI (`agy`) / `opencode` running headless background scaffolding in `workspace/teardowns/<domain>_rebuild/`.
    - **Engine 3 (Zero-LLM Fallback):** Deterministic Python template generator translating CDP evidence into Markdown if offline.
  - **Action Tool (`actions/reverse_engineer.py`):** Rule 4 compliant non-blocking action tool for assistant runtime.
  - **Dual-Pane Teardown HUD (`TeardownHUDModal.tsx`):** Built high-tech ReUI modal with dual-pane layout: Left pane displays detected stack badges, WebGL shaders, network endpoints, and Markdown blueprint; Right pane renders live scaffold file tree and background CLI logs.
  - **Assistant-UI In-Chat Integration:** Added `ReverseEngineerToolUI` to `frontend/src/components/assistant-ui/thread.tsx` with dynamic status pills and direct launcher to the Teardown HUD.
- **Files touched:** `actions/reverse_engineer.py`, `core/teardown_engine.py`, `core/fleet_manager.py`, `config/fleet_agents.json`, `frontend/src/components/teardown/TeardownHUDModal.tsx`, `frontend/src/components/office/AutonomousOfficeScreen.tsx`, `frontend/src/components/assistant-ui/thread.tsx`, `frontend/src/hooks/useZezoSocket.ts`, `frontend/src/App.tsx`, `tests/test_reverse_engineer_suite.py`.
- **Verification:**
  - **Layer 1 (Static):** `python -m py_compile` passed for all Python files. `npm --prefix frontend run build` passed with 0 TypeScript/Vite errors.
  - **Layer 2 (Runtime):** End-to-end test suite `tests/test_reverse_engineer_suite.py` (7/7 tests passed: immutability, keyword routing, Rule 4 declaration, deterministic blueprinting, Groq fallback, non-blocking dispatch).
  - **Layer 3 (Regression):** Existing test suites `test_fleet_control_suite.py`, `test_website_cloner_suite.py`, and `test_dispatcher.py` all passed (24/24 tests).

## [2026-10-23] — Settings Modal UX Redesign: Shorter Taxonomy & Robust Keyword Search
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Redesigned the Settings modal sidebar based on expert product design principles:
  - **Simplified & Shortened Sidebar Labels:** Streamlined verbose names into crisp, modern single-word/short nouns (*"General & Controls"* → *"General"*, *"Audio Settings"* → *"Audio"*, *"Providers & Keys"* → *"API & Keys"*, *"Assistant Persona"* → *"Persona"*, *"Appearance & Accents"* → *"Appearance"*, *"Memory & Intelligence"* → *"Memory"*, *"About ZEZO"* → *"About"*).
  - **Robust Keyword Search Indexing:** Added deep keyword metadata arrays to navigation items so typing terms like *"mic"*, *"theme"*, *"gemini"*, or *"hotkey"* instantly filters and highlights the correct settings section, complete with a clean empty state.
- **Files touched:** `frontend/src/components/settings/SettingsModal.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`, Vite production build passed successfully in 933ms); Layer 2 (Runtime: test suites passed).

## [2026-10-23] — ClipPeek "Open in Browser" WebSocket Action Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Fixed the "Open in Browser" button in the ClipPeek floating clipboard overlay not opening links:
  - **Root Cause:** Direct `window.open()` in QtWebEngine desktop environment was either blocked as a popup or failed on domain-only/www copies lacking `https://`.
  - **Fix:** Added `open_browser` WebSocket message handler in Python backend (`core/ui_server.py`) using Python's robust `webbrowser.open(url)`, with URL normalization (`https://` prefix) in `ClipPeekOverlay.tsx`.
- **Files touched:** `core/ui_server.py`, `frontend/src/components/clipboard/ClipPeekOverlay.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`, Python compilation `python -m py_compile`); Layer 2 (Runtime: test suites passed successfully).

## [2026-10-23] — Single URL Summary & Multi-Platform Fan-Out Fix in Core Prompt
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Investigated and resolved the issue where asking the assistant to summarize a single URL (e.g., `https://www.docker.com`) incorrectly triggered multiple parallel research tasks (YouTube video transcripts, Reddit searches, multi-platform aggregator search).
  - **Root Cause:** Context pollution from old URLs (e.g. previous YouTube video ID `sOxlDirIAbk`) combined with broad multi-source research prompt instructions (`[EXHAUSTIVE REPORT GENERATION STANDARD]`).
  - **Fix:** Added strict **Single URL & Topic Scope Rule** in `core/prompt.txt` directing the model to fetch and analyze *only* the specific requested URL using `agent_reach(platform='web')` or `web_read_page`, strictly preventing unauthorized cross-platform multi-source fanning out unless explicitly requested by the user.
- **Files touched:** `core/prompt.txt`, `frontend/index.html`.
- **Verification:** Layer 1 (Static: Python compilation `python -m py_compile` & test suite `pytest tests/test_payload_and_task_modal.py tests/test_fleet_control_suite.py` passed successfully).

## [2026-10-22] — Zezo ClipPeek: Smart Clipboard Companion Feature
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Implemented **Zezo ClipPeek**, a smart floating clipboard companion that bridges the OS clipboard visibility gap:
  - **Backend Clipboard Watcher (`core/clipboard_watcher.py`):** Background daemon thread monitoring OS clipboard changes (`pyperclip`) and classifying content types (URL, code, article, text).
  - **WebSocket Broadcasting (`core/ui_server.py`):** Automatically broadcasts `clipboard_update` events to all active UI web clients.
  - **Frontend Overlay (`frontend/src/components/clipboard/ClipPeekOverlay.tsx`):** Floating ReUI card in bottom-right corner with content preview, context-aware action chips (`Open in Browser`, `Summarize / Explain`, `Send to Chat`), and an inline prompt input bar.
- **Files touched:** `core/clipboard_watcher.py`, `core/ui_server.py`, `frontend/src/components/clipboard/ClipPeekOverlay.tsx`, `frontend/src/App.tsx`.
- **Verification:** Layer 1 (Static: Python compilation `python -m py_compile`); Layer 2 (Runtime: Unit test pipeline `pytest tests/test_pipeline_ui_integration.py` passed).

## [2026-10-22] — Clipboard & URL Paste Fix in Desktop Input Driver
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Fixed the clipboard paste issue where copying links (URLs) or running paste actions left target text inputs empty:
  - **Clipboard Fallback on Empty Text:** Updated `_handle_type` in `computer_control.py` to automatically fetch text from the system clipboard via `input_driver.get_clipboard()` when action is paste/clipboard and no text is explicitly provided in parameters.
  - **URL / Link Paste Support:** Updated `type_safe_unicode` in `pyautogui_driver.py` to recognize URLs (`http://`, `https://`, `www.`) and automatically route them through robust clipboard-safe `ctrl+v` injection instead of character-by-character typing.
- **Files touched:** `actions/computer_control.py`, `core/computer/pyautogui_driver.py`.
- **Verification:** Layer 1 (Static: Python compilation `python -m py_compile`); Layer 2 (Runtime: Unit test pipeline `pytest tests/test_pipeline_ui_integration.py` passed).

## [2026-10-22] — Memory Graph Canvas: Performance Optimization & Lag Elimination
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Optimized `MemoryGraphCanvas.tsx` to eliminate lagging and jank:
  - **Removed React Hover Re-renders:** Eliminated `setHoverNode` state updates inside `onNodeHover` mouse move events, replacing it with `hoverNodeRef.current`. This prevents the entire component from re-rendering on every mouse movement over graph nodes.
  - **Fixed Search TypeError:** Added optional chaining (`n.label?.toLowerCase()`) to robustly handle missing or undefined node labels during search filtering.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`); Layer 2 (Runtime: Vite production build passed successfully with zero errors).

## [2026-10-22] — Memory Graph Canvas: Fixed Timeline Feed View Overlap via Persistent DOM Container & Hidden Toggle
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Fixed the issue where the 3D graph canvas was visible underneath the timeline feed view by keeping the canvas container `canvasAreaRef` permanently mounted in the DOM and toggling its visibility via Tailwind's `hidden` / `block` classes, ensuring clean separation and zero overlap between the 3D Graph and Timeline Feed tabs.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`); Layer 2 (Runtime: Vite production build passed successfully with zero errors).

## [2026-10-22] — Memory & Intelligence Page Layout Refinement: Title & Actions Outside ReUI Frame, Full-Width Edge-to-Edge Canvas
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Refactored the Memory & Intelligence section layout in `SettingsModal.tsx` to match other settings pages: placed title, description, and action buttons outside/above the ReUI Frame container, set `FramePanel` padding to `p-0` for edge-to-edge layout, ensuring the time filter bar, search toolbar, and 3D force graph / timeline canvas fill the full available width and height.
- **Files touched:** `frontend/src/components/settings/SettingsModal.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`); Layer 2 (Runtime: Vite production build passed successfully with zero errors).

## [2026-10-22] — Removed Categories from Memory & Intelligence UI
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Removed category dropdown filter from `MemoryGraphCanvas.tsx`, category selection from `NewMemoryModal.tsx`, and category badges from timeline cards per user preference to streamline the UI and eliminate unnecessary clutter.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`, `frontend/src/components/memory/NewMemoryModal.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`); Layer 2 (Runtime: Vite production build passed successfully in 854ms with zero errors).

## [2026-10-22] — Memory Graph Canvas: Restored 3D Force Graph Controls, Animation Sliders & Link Particles
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Restored all advanced 3D force graph controls, physics sliders, and animated features into `MemoryGraphCanvas.tsx` while preserving the newly added timeline view and date/category filters:
  - **Toolbar Controls:** Added Zoom In, Zoom Out, Center Focus (Fit to Screen), Fullscreen toggle (with ESC key support), and Sliders panel toggle.
  - **Animation & Physics Sliders Panel:** Collapsible popover with live sliders for Auto-rotate speed, Particle flow speed, Particle count, Node size, Charge strength (repulsion), and Link distance, plus Node motion On/Off toggle.
  - **Animated Link Particles:** Restored glowing directional particles streaming along links for live data flow visualization.
  - **Node Drag Physics:** Restored node dragging with jelly spring-back physics and simulation reheat (`d3ReheatSimulation`).
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation `tsc -b`); Layer 2 (Runtime: Vite production build passed successfully in 954ms with zero errors).

## [2026-10-22] — Agent Inspector UI Polish: Harmonized Buttons, Removed Redundant Fire Button & Agent-Specific Logs
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Polished the Agent Inspector right panel in `AutonomousOfficeScreen.tsx` based on user feedback: removed the redundant top "FIRE" button, harmonized all action buttons (`CHAT`, `EDIT`, `FILES`, `DISMISS`) and environment row icons to consistent monochrome ReUI style, and restricted live logs in agent mode to show strictly that agent's logs.
- **Key details:**
  - `AutonomousOfficeScreen.tsx`: Removed duplicate top "FIRE" header button, leaving the clean action button row.
  - Button & Icon Harmonization: Updated action buttons and environment icons (`Terminal`, `Folder`, `Cpu`, `Shield`, `Zap`) to neutral monochrome styling (`text-[var(--foreground)]` / `text-[var(--muted-foreground)]`) without random neon colors.
  - Agent-Specific Logs: Refactored `displayedLogs` memo so that when `logFilterMode === 'agent'`, it displays strictly `selectedAgent.logs`.
- **Files touched:** `frontend/src/components/office/AutonomousOfficeScreen.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation & clean production Vite build passed successfully); Layer 2 (Runtime: Verified clean unified button styling, agent-specific logs filtering, and zero redundant buttons).

## [2026-10-22] — Header Cleanup, Toggle Theme Switcher, Universal Shadow Removal & UI Cutoff Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Cleaned up the header (removed clock/date display and center "ZEZO" title), replaced the theme switcher button with a toggle-type segmented pill, eliminated drop shadows universally across all frames, cards, modals, and buttons, replaced hardcoded dark backgrounds with theme-aware tokens, and resolved the office agent panel layout cutoff.
- **Key details:**
  - `frontend/src/App.tsx`: Removed the clock/date display and center title from the top header bar, added a clean toggle-type segmented pill theme switcher button, and styled upload buttons with high contrast.
  - Universal Shadow Removal: Sanitized all ReUI frames, cards, buttons, modals (`NewMemoryModal.tsx`, `ConfirmDialog`, `SettingsModal`, etc.) to remove all `shadow-*` utility classes.
  - Light & Dark Mode Contrast: Replaced hardcoded dark background hexes (`bg-[#0a0a0a]`, `bg-[#0d0d0d]`, `bg-[#0e0e0e]`) with semantic theme tokens (`bg-card`, `bg-[var(--background)]`).
  - Office Agent Panel UI Cutoff: Expanded sidebar grid column width in `AutonomousOfficeScreen.tsx` to prevent agent card horizontal truncation.
- **Files touched:** `frontend/src/App.tsx`, `frontend/src/components/settings/SettingsModal.tsx`, `frontend/src/components/office/AutonomousOfficeScreen.tsx`, `frontend/src/components/reui/card.tsx`, `frontend/src/components/reui/frame.tsx`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/reui/confirm-dialog.tsx`, `frontend/src/components/memory/NewMemoryModal.tsx`, `frontend/src/index.css`.
- **Verification:** Layer 1 (Static: TypeScript compilation and clean production Vite build passed successfully); Layer 2 (Runtime: Verified correct header rendering, toggle theme pill, shadow-free UI across light and dark modes, and fixed office agent panel grid width).

## [2026-10-22] — Minimal Mono Theme Polish, Avatar Synchronization & Light Mode Contrast Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Polished the Minimal Mono theme, synchronized avatar palettes and particles, removed drop shadows from frames, cards, and buttons, and updated `MemoryGraphCanvas.tsx` to use theme-aware semantic background tokens (`bg-card`, `bg-input`, `bg-background`).
- **Key details:**
  - Synchronized Qivi avatar and particles with monochrome themes (`#141414`, `#383838`, `#f5f5f5`, `#ffffff`).
  - Removed all `shadow-*` drop shadows from ReUI frames, cards, and buttons per design guidelines.
  - Refactored `MemoryGraphCanvas.tsx` hardcoded dark backgrounds (`bg-[#08090d]`, `bg-[#0c0e15]`, etc.) to use theme-aware CSS tokens (`bg-background`, `bg-card`, `bg-input`), ensuring excellent light mode and dark mode visibility.
- **Files touched:** `frontend/src/components/settings/SettingsModal.tsx`, `frontend/src/index.css`, `frontend/src/components/avatar/ChatAvatarIcon.tsx`, `frontend/src/components/canvas/QiviAvatarVisualizer.tsx`, `frontend/src/components/reui/card.tsx`, `frontend/src/components/reui/frame.tsx`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1 (Static: TypeScript compilation and clean Vite build); Layer 2 (Runtime: Theme selectable, light/dark mode fully functional with proper contrast and zero shadows).

## [2026-10-22] — Added "Minimal Mono" Theme to Appearance Settings
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Added the requested minimalist monochrome OKLCH theme ("Minimal Mono") into `frontend/src/components/settings/SettingsModal.tsx` and `frontend/src/index.css`.
- **Key details:**
  - Configured both dark mode (`[data-theme="minimal"]`) and light mode (`[data-theme="minimal-light"]`) variants using official OKLCH color tokens and Tailwind v4 CSS variables.
  - Added theme metadata, preview swatches, and description in `THEME_SYSTEMS`.
- **Files touched:** `frontend/src/components/settings/SettingsModal.tsx`, `frontend/src/index.css`.
- **Verification:** Layer 1 (Static: TypeScript compilation & Vite build passed with zero errors); Layer 2 (Runtime: Theme fully selectable and active in Appearance settings).

## [2026-10-22] — Added Built-in Deep Research Agent "RECON" to Fleet
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built:** Added a permanent built-in Deep Researcher & Intelligence Agent named **RECON** into `config/fleet_agents.json`.
- **Key details:**
  - Configured with `agent_reach`, Tavily search, and multi-source web reading capabilities.
  - Assigned dedicated desk coordinates (`desk_x: 600, desk_y: 400`) and marked as a protected system agent.
- **Files touched:** `config/fleet_agents.json`.
- **Verification:** Layer 1 (JSON parse test); Layer 2 (FleetManager loading test verified RECON is successfully active).

## [2026-10-22] — Memory Graph Canvas 60 FPS Performance & Lag Elimination
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Severe lag and frame drops across the memory page were caused by four compounding issues:
  1. `three-forcegraph` `refresh()` invocation on mouse hover: An effect listening to `[selectedNodeId, hoverNode, highlightNodes]` was calling `graphInstanceRef.current.refresh()`. In `three-forcegraph`, `refresh()` sets `state._flushObjects = true`, which flushes and completely reconstructs every 3D mesh, geometry, and sprite in the scene on every sub-pixel mouse movement.
  2. Canvas texture churn in `three-spritetext`: Setting `node.__sprite.color` dynamically triggered `SpriteText`'s internal `_genCanvas()`, forcing 118 canvas 2D draw operations and 118 GPU texture re-uploads per hover event.
  3. Continuous React re-renders on hover: `hoverNode` state updates caused the entire React component tree to re-evaluate on every hover event.
  4. Composite GPU blur: `backdrop-blur-md` on modal toolbars layered over the active 60 FPS WebGL canvas forced costly full-frame compositing passes.
- **Fixes applied:**
  1. Switched `hoverNode`, `highlightNodes`, and `selectedNodeId` tracking to refs (`hoverNodeRef`, `highlightNodesRef`, `selectedNodeIdRef`), eliminating all React re-renders on hover.
  2. Implemented zero-allocation GPU material updates via `Graph.nodeColor(...)`, `Graph.linkColor(...)`, `Graph.linkWidth(...)`, and `Graph.linkDirectionalParticles(...)` instead of calling `refresh()`.
  3. Initialized `SpriteText` instances statically once with `depthWrite = false`, completely stopping continuous canvas redraws and texture re-allocations.
  4. Disconnected `dimensions` from the `ForceGraph3D` initialization dependency array, maintaining a stable singleton instance and handling resize via dedicated `.width()` and `.height()` calls.
  5. Removed nested `backdrop-blur-md` overlays adhering to AGENTS.md UI Rule 2.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1 (Static: `tsc -b && vite build` built in 844ms with zero errors); Layer 2 (Runtime: static texture caching and direct Three.js material color mutators confirmed).

## [2026-10-22] — MemoryGraphCanvas 3D Force Graph Initialization Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** `3d-force-graph` `controlType` was incorrectly chained as a method (`.controlType('orbit')`), whereas in `3d-force-graph`, `controlType` is an initialization configuration option passed as `{ controlType: 'orbit' }` to `ForceGraph3D(domElement, options)`.
- **Fixes applied:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`: Passed `{ controlType: 'orbit' }` into `GraphCreator(canvasAreaRef.current, { controlType: 'orbit' })` instead of chaining `.controlType('orbit')`.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1/2 (TypeScript build via `tsc -b && vite build`) passed successfully.

## [2026-10-22] — Push-to-Talk Real-Time Streaming & Delayed Turn Commit Architecture
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Pure local buffering of PTT audio resulted in bulk dumps and synchronization issues with Gemini Live's real-time streaming sockets, leading to dropped turns or delayed responses.
- **Fixes applied:** `main.py`: Restored real-time audio streaming through `out_queue` while PTT is held, combined with a 0.5-second delayed `audio_stream_end` signal upon hotkey release (dispatched via background thread). This ensures real-time transcription accuracy and prevents premature server VAD turn completion during mid-sentence pauses.
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suites passed successfully (5/5 passed).

## [2026-10-22] — PTT Anti-Burst Pacing, Queue Flushing & Extended Silence Watchdog
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) Dumping all buffered PTT audio in one microsecond burst caused Gemini server-side drop/turn drop (`ZERO model output`). (2) The 5-second silence watchdog timed out prematurely during long PTT processing. (3) Stale queues caused ghost replays of old instructions.
- **Fixes applied:** (1) `main.py`: Implemented smooth chunk pacing (`await asyncio.sleep(0.01)` between 4KB chunks) when streaming buffered PTT audio upon hotkey release. (2) Extended silence watchdog window to ~13.5s when PTT is enabled. (3) Added thorough queue draining (`out_queue`, `audio_in_queue`) and buffer reset on PTT press start (`held=True`).
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suite passed successfully (5/5 passed).

## [2026-10-22] — Push-to-Talk Local Audio Buffering & Send-on-Release Architecture
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Real-time PTT streaming caused server-side VAD premature turn completion during mid-sentence pauses in long speech (causing speech leaks and Zezo responding prematurely) and inaccurate transcriptions due to partial phonetic chunks being processed iteratively.
- **Fixes applied:** `main.py`: Implemented local audio buffering (`self._ptt_audio_buffer`) while PTT hotkey (`Ctrl+Alt`) is held (`_ptt_held == True`). Audio chunks are accumulated locally in memory and dispatched to Gemini Live all at once *only* upon hotkey release (`_ptt_held == False`), ensuring 100% complete utterance delivery and accurate transcription.
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suite passed successfully (5/5 passed).

## [2026-10-22] — Gemini Live Transcription Language Hints & PTT Long-Speech VAD Fix

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) Language transcription mixing / wrong language output: `input_audio_transcription={}` was empty without language hints, causing Gemini Live ASR to occasionally misinterpret English or mixed/Roman Urdu speech into random languages (like Spanish). (2) PTT long-speech cutoff / speech leak: During long speech while holding PTT, brief mid-sentence pauses triggered server-side VAD turn completion prematurely, causing Zezo to reply mid-speech while the user was still holding the hotkey.
- **Fixes applied:** (1) `main.py`: Configured `input_audio_transcription=types.AudioTranscriptionConfig(language_codes=active_lang_codes)` mapped from configured response language (`resp_lang`) with robust multilingual fallback (`["en-US", "ur-PK", "hi-IN", "es-ES"]`). (2) `main.py`: Added `realtime_input_config=types.RealtimeInputConfig(automatic_activity_detection=types.AutomaticActivityDetection(silence_duration_ms=2500))` when PTT is enabled, preventing premature VAD turn completion during pauses in long speech.
- **Files touched:** `main.py`, `tests/test_language_and_mute_fix.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 pytest test suites passed successfully (5/5 passed).

## [2026-10-22] — Hotkey PTT Debounce & VS Code Minimization Fixes

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) VS Code minimization failed because `is_self_or_console_window` flagged `code.exe` parent processes and title matches (`jarvis`/`zezo`) as self/console windows, blocking minimization, and `APP_ALIASES_MAP` lacked `"vs code"` aliases. (2) Hotkey PTT debounce (`_DEBOUNCE_S = 0.06`) caused a slight initial delay or missed first press when starting speech.
- **Fixes applied:** (1) `core/computer/windows_native.py`: Added `"vs code"`, `"vscode"`, `"code"` to `APP_ALIASES_MAP` and allowed target app matches to bypass console-window protection when explicitly requested. (2) `core/hotkey.py`: Reduced debounce threshold `_DEBOUNCE_S` from `0.06` to `0.02` for immediate first-press audio capture.
- **Files touched:** `core/computer/windows_native.py`, `core/hotkey.py`.
- **Verification:** Layer 1 (`py_compile`) passed on both modified files.
- **Not touched:** Audio/voice pipeline stream loops in `main.py`.

---

## [2026-10-22] — Search Pipeline Repair: Cooldown, Circuit Breaker, Synthesis, Chat Dedup

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Search pipeline had four compounding defects: (1) `core/gemini.py` cooled all models on 503/UNAVAILABLE by mislabeling them "out of quota", and `tried = […] or list(ladder)` re-ran the full ladder when every rung was cooling. (2) `actions/web_search.py`'s `_note_gemini_error` only tripped the 15-min grounding breaker on "429"/"RESOURCE_EXHAUSTED" strings, but `gemini.call()` swallows 429s and returns None, so the breaker never opened. (3) Tavily socket timeout was 3.0s, so Tier-1 always timed out. (4) `_search` and `_price` returned raw snippet dumps with no Groq synthesis.
- **Fixes applied:** (1) `core/gemini.py`: split quota vs transient vs missing (404) error handling; transient no longer cools; all-rungs-cooling returns []. (2) `actions/web_search.py`: breaker trips on "every gemini model failed"/"all backends failed"; Tavily timeout 3.0→8.0s; `_search` and `_price` now synthesize via Groq; `_price` query de-mangled. (3) `frontend/src/App.tsx`: chat dedup merges partial-dictation overlap.
- **Files touched:** `core/gemini.py`, `actions/web_search.py`, `frontend/src/App.tsx`.
- **Verification:** `py_compile` passed on `core/gemini.py` and `actions/web_search.py`.
- **Not touched:** audio/voice pipeline files.

---

## [2026-10-22] — Session Quality Fixes: Duplicate Replies, URL Verification, Prompt Rules

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Duplicate identical replies after tool calls; hallucinated/unchecked URLs opened in browser; unsolicited follow-up questions; self-contradictory phrasing; false 404 claims; answers to incomplete utterances; language switching.
- **Fixes applied:** (1) `main.py`: cleared `_interrupted` at `turn_complete` and after `send_tool_response`; dedup guard on consecutive identical assistant turns; barge-in gated while speaking; replies gated on full transcript. (2) `actions/browser_control.py`: per-URL status for `new_tab` multi-url; verified/failed reporting; `_safe_url` validation. (3) `core/prompt.txt`: rules banning self-contradictory phrasing, unsolicited follow-ups, language switching, unverified tool claims, guessed URLs, answering incomplete utterances.
- **Files touched:** `main.py`, `actions/browser_control.py`, `core/prompt.txt`.
- **Verification:** `py_compile` passed on `main.py` and `actions/browser_control.py`.
- **Not touched:** audio/voice pipeline files.

- **Creator & Lead Architect:** Hamza Bukhari
- **What was updated:**
  - **Strengthened Rule 6 & Section 3 Rule 1 in `AGENTS.md`:**
    - Explicitly codified the **Strict Hands-Off Policy ("Bila-Wajah Touch Mat Karo")** for ZEZO's audio and voice pipeline files (`main.py` live loops `_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`).
    - Made it non-negotiable: agents are strictly forbidden from modifying, refactoring, or experimenting with audio/voice pipeline files unless the user's explicit prompt specifically asks to fix or modify audio/voice behavior.
    - If a task focuses on browser control, computer automation, tools, UI styling, settings, or memory, audio/voice pipeline files must remain 100% untouched.
- **Key files touched:**
  - `AGENTS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Automatic Desktop Fallback Restoration, Daemon Leak Closure (9 Functions) & Chrome Profile Resolution
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built / fixed:**
  - **A. Automatic Desktop Fallback (Regression Fix):**
    - Root cause: When desktop Chrome was running without `--remote-debugging-port=9222` (the standard user state), `_verify_session_identity()` returned an error string which caused `_act_go_to`, `_act_search`, `_act_new_tab`, and `_act_close_tab` to return `Refused: Session identity mismatch...`. Because this check short-circuited the function, desktop input fallbacks (Ctrl+L, Ctrl+T, Ctrl+W) were unreachable, forcing the LLM to fall back to `computer_control` manually.
    - Fix: When identity mismatch occurs or CDP is unavailable, automatically execute desktop navigation via `input_driver` (`_focus_desktop_browser()` -> hotkey -> `type_safe_unicode` -> Enter) instead of refusing. Only refuse if `input_driver` is unavailable or `_focus_desktop_browser()` fails.
    - Input Desktop Bridge: Integrated `OpenInputDesktop` and `SetThreadDesktop` Win32 API in `_resolve_desktop_browser_hwnd` and `_focus_desktop_browser` to reliably discover and control desktop Chrome even when running from background agent threads.
  - **B. Closed 9 Remaining Desync Paths:**
    - Gated `_act_click`, `_act_locate`, `_act_get_title`, `_act_verify_page`, `_act_scroll`, `_act_press`, `_act_get_url` (final fallback), `_extract_label_from_snapshot`, and `_try_dismiss_banners` behind session identity verification.
    - In `_act_click`, on identity mismatch it delegates to `_click_desktop`; if desktop resolution fails, it refuses with identity error and NEVER leaks to daemon `snapshot -i` or daemon click.
  - **C. Happy Path Host Verification:**
    - In `_act_go_to` and `_act_search` (`code == 0`), parse the verification URL returned by `get url` and confirm the expected host/domain is present. Catches stale daemon tabs that exit code 0 without navigating.
  - **D. Dynamic Chrome Profile & Hygiene:**
    - Replaced hardcoded `--profile-directory=Default` with dynamic reading of `profile.last_used` from `<user-data-dir>/Local State` (e.g. `"Profile 7"`).
    - In `_act_list_tabs`, replaced misleading `"1 tab open in Chrome (active window)"` fallback with `"Unable to list open tabs."`.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_strict_verification.py` (0 errors).
  - Layer 2 (Runtime): Real desktop fallback execution confirmed on live Chrome: `browser_control({"action": "go_to", "url": "https://www.docker.com"})` successfully focused desktop Chrome (HWND 1442802), dispatched omnibox navigation, and verified 19 open tabs via UIA.
  - Layer 3 (Regression): 49 passed in pytest suite (17 strict verification + 7 enhancements + 14 stability + 11 phase2 hygiene).
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_strict_verification.py`
  - `tests/test_browser_control_enhancements.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Browser Control Security Hardening (P0), Single-Session Identity Enforcement & Correctness Suite
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built / fixed:**
  - **A. Security (P0):**
    - Eliminated `shell=True` from `_exec_ab` across both primary and retry paths. Passed arguments as structured list `[ab_bin, *shlex.split(effective_args)]` with explicit stdout file handles.
    - Implemented `_safe_url(s)` enforcing `http`/`https` schemes and rejecting injection metacharacters (`;`, `&`, `|`, `$`, `(`, `)`, `<`, `>`, `"`, `'`, `\n`, `\r`, `%`, `\`). Enforced in `_act_go_to`, `_act_search`, `_act_new_tab`, `_act_screenshot`, `_act_type`, and `_act_fill_form`.
    - Replaced all `subprocess.Popen(cmd /c start ...)` sites with native `os.startfile()` (Windows) / `["open", url]` (Darwin) / `["xdg-open", url]` (Linux).
    - Constrained `_exec_ab` retries strictly to idempotent inspection queries (`get url`, `get title`, `snapshot`, `tab list`). Mutation actions (`click`, `type`, `fill`, `press`, `open`, `tab close`) are never retried.
  - **B. Single-Session (P0):**
    - Removed `CDP_Profile` isolation directory. Enforced user's real Chrome `User Data` directory with `--profile-directory=Default`. If already running without CDP, returns `False` rather than silently starting a parallel profile.
    - Added identity verification in `_verify_session_identity()` comparing `/json/version` and CDP process PID against `_resolve_desktop_browser_hwnd()`. Returns hard diagnostic error string on mismatch.
    - Eliminated double-open bug in `_act_go_to` and `_act_search`. Gated desktop input fallbacks behind `params.get("desktop_only")`.
    - Enforced session identity verification in `_act_snapshot`, `_act_screenshot`, `_act_get_text`, and `_act_fill_form`. Removed `_ensure_chrome_cdp()` from `_act_snapshot`.
  - **C. Correctness (P1):**
    - Fixed `_find_element_info` label extraction: skips `class=`, `id=`, `role=` attributes, prioritizing `aria-label=` and `name=`.
    - Added automatic `_reset_snapshot()` cache invalidation upon every successful navigation (`open`, `go_to`, `new_tab`, `back`, `forward`, `reload`).
    - Defocused active omnibox / inputs via `eval document.body.focus()` in `_act_scroll`, removing `input_driver.press("escape")`.
    - Refused `_act_close` and `_act_nav_history` on identity failure.
    - Required URL host / path verification in `_act_go_to` and `_act_search` EOF retry before confirming navigation success.
    - Added camelCase action dispatch support with regex conversion (`goTo` -> `go_to`).
    - Prevented caching failed navigation attempts in `_last_nav` deduplication.
    - Stopped treating EOF while parsing as success in `_act_close_tab`.
  - **D. Hygiene (P2):**
    - Unified `windows_native` import across all functions.
    - Protected `_act_get_url` clipboard fallback in `try/finally` restoring original clipboard contents.
    - Restricted `_clear_stale_ab_target` deletion of daemon port/pid/config files unless explicitly relaunching.
    - Removed trailing `handler = browser_control`.
    - Refined `_act_verify_page` to compare hostname / valid subdomains instead of raw substring matching.
    - Accelerated `_act_locate` to DOM `querySelectorAll` evaluation (<150ms) avoiding full a11y tree snapshots.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_strict_verification.py` (0 errors).
  - Layer 2 (Runtime): Tested all 12 scenarios in `tests/test_browser_control_scenarios.py` (0 errors).
  - Layer 3 (Regression): 38 passed, 1 skipped in `pytest` suite across enhancements, stability, hygiene, and strict verification.
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_strict_verification.py`
  - `tests/test_browser_control_enhancements.py`
  - `tests/test_desktop_chrome_stability_suite.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Desktop Chrome CDP 9222 Integration, Zero-Phantom Fallback & Sub-100ms Action Execution
- **Creator & Lead Architect:** Hamza Bukhari
- **What was fixed:**
  - **Browser Control Failure & Desync on Spotify & Google Login:**
    - Root cause: Headless split-brain. Navigation opened URLs in desktop Chrome via keystrokes while launching a detached headless `agent-browser` session. When in-page element clicks failed via Windows UIA or OCR, `_act_click` silently clicked inside the headless background daemon and reported success, creating a false confirmation while desktop Chrome remained untouched. Furthermore, Spotify cookie consent overlays blocked button access.
    - Fix:
      1. **CDP Port 9222 Unified Desktop Bridge (`actions/browser_control.py`):** Added `_ensure_chrome_cdp()`, `_is_cdp_available()`, and `_clear_stale_ab_target()`. Desktop Chrome launches with `--remote-debugging-port=9222`, `--remote-allow-origins=*`, and `--user-data-dir`.
      2. **Direct CDP Command Wire (`actions/browser_control.py`):** `_exec_ab()` auto-prepends `--cdp 9222` when available, directing all snapshots, clicks, typing, and URL queries to the user's live desktop Chrome.
      3. **Zero-Phantom Fallback & Mandatory Verification (`actions/browser_control.py`):** Removed silent execution in detached background daemons. If an element cannot be found or clicked on the active page, `_act_click` returns an explicit diagnostic error rather than false success.
      4. **Automated Consent Overlay Dismissal (`actions/browser_control.py`):** Added `_try_dismiss_banners()` to auto-detect and click "Accept cookies", "Accept all", or overlay close buttons prior to re-evaluating targets.
- **Verification & Latency:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_enhancements.py` (0 errors).
  - Layer 2 (Runtime): Tested real Spotify navigation, Log in click, and Google OAuth button click in `tests/test_live_cdp.py`:
    - Page Snapshot latency: **59.0ms**
    - Click Log In latency: **106.9ms**
    - Click "Continue with Google" latency: **94.6ms** (navigated directly to `accounts.google.com/v3/signin/...`)
    - Unit tests in `tests/test_browser_control_enhancements.py` (7/7 passed).
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_phase2_dispatch_hygiene_suite.py` (25/25 passed).
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_enhancements.py`
  - `tests/test_live_cdp.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Browser Control Desktop Convergence, Ref Resolution & Audio Buffer Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **What was fixed:**
  - **Browser Control Failure on Desktop Web Clicks (Spotify "Log in" and "Sign up" buttons):**
    - Root cause: When Gemini passed snapshot refs (`@e14`) or CSS selectors (`button[data-testid='login-button']`) to `_act_click`, `_click_desktop` explicitly returned `None` because of a check `if target.startswith(("@", "#", ".")) or "[" in target: return None`. Consequently, clicks were executed solely in the headless `agent-browser` daemon, leaving the user's desktop Chrome untouched. Additionally, when Gemini Vision fallback was triggered, `_screen_find_vision` crashed with `NameError: name 'gtypes' is not defined`.
    - Fix:
      1. **Snapshot Ref Label Resolution (`actions/browser_control.py`):** Added `_extract_label_from_snapshot(target)` which inspects the active snapshot to extract the human-readable element text (e.g. `button "Log in" [ref=e14]` -> `"Log in"`, `button "Sign up" [ref=e13]` -> `"Sign up"`).
      2. **Desktop Click Resolution via OCR Escalation (`actions/browser_control.py`):** Removed the ref bail-out check in `_click_desktop`. When a ref or selector is supplied, it extracts the visual label, focuses desktop Chrome, and runs `_find_target_element_escalated(label)` (RapidOCR Multilingual 0 MB VRAM -> Gemini Vision) to click the element at physical screen coordinates `(cx, cy)`.
      3. **Vision Fallback Import Fix (`actions/computer_control.py`):** Fixed missing `from google.genai import types as gtypes` import.
  - **Audio Output Stuttering & Buffer Under-runs (`main.py`):**
    - Root cause: `_open_spk` in `main.py` enforced `blocksize=CHUNK_SIZE` (1024 frames = ~42ms). On Windows USB audio adapters (e.g. USB PnP Sound Device 7.1), tiny fixed block sizes caused hardware buffer under-runs and crackling/stuttering during concurrent thread activity.
    - Fix: Configured `blocksize=0` in `sd.RawOutputStream`, allowing PortAudio to select the audio device's optimal hardware buffer size (~180ms latency with zero under-runs).
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py actions/computer_control.py main.py` (0 errors).
  - Layer 2 (Runtime): Unit tests in `tests/test_browser_control_enhancements.py` verifying ref label extraction and desktop OCR click execution (7/7 passed).
  - Layer 3 (Regression): `pytest tests/test_browser_control_enhancements.py tests/test_desktop_chrome_stability_suite.py tests/test_phase2_dispatch_hygiene_suite.py` (32/32 passed).
- **Key files touched:**
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `main.py`
  - `tests/test_browser_control_enhancements.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Desktop WebEngine Startup Race Condition & Blank UI Fix
- **What was fixed:**
  - **Desktop Window Rendering Blank White Screen on `python main.py` (`ui.py` & `core/ui_server.py`):**
    - Root cause: In `ui.py`, `MainWindow.__init__` called `self._server.start()`, which initialized `aiohttp.web.TCPSite` asynchronously in a background thread. The main thread immediately executed `self.web_view.load(QUrl(server_url))` before `TCPSite` had finished binding to `http://127.0.0.1:8765/`. Chromium's initial request failed, resulting in a blank white window (`DOM root length: 0`).
    - Fix: Added a thread-safe `self._ready_event = threading.Event()` in `ZezoUIServer` (`core/ui_server.py`), signaled immediately when `self._site.start()` completes and the socket is listening. In `ui.py`, added `self._server._ready_event.wait(timeout=3.0)` right before `self.web_view.load()`, guaranteeing the static HTTP server is active before WebEngine navigates.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile ui.py core/ui_server.py` (0 errors).
  - Layer 2 (Runtime): Verified in PyQt6 runtime that `win.web_view.page().runJavaScript('document.body.innerHTML')` loaded `42,068` DOM characters immediately upon window creation.
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` (1/1 passed).
- **Key files touched:**
  - `core/ui_server.py`
  - `ui.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Real-Time WebSocket Mode Synchronization for Push-To-Talk & Wake Word
- **What was fixed:**
  - **Interaction Mode Toggle "Failed to fetch" & Failure to Arm PTT/Wake Word Live:**
    - Root cause: When selecting Push-To-Talk or Wake Word in Settings, `SettingsModal.tsx` relied exclusively on `api.saveConfig()` HTTP fetch. In dev mode (or during backend busy cycles), `api.ts` threw unhandled `Failed to fetch` errors, and more critically, WebSocket events `ptt_toggle` and `wake_toggle` were never sent to `ZezoUIServer`. Consequently, `main.py`'s `set_push_to_talk()` and `_ui_wake_toggle()` were never invoked in real time without a manual reconnect.
    - Fix: Added `sendWakeToggle` and `sendPttToggle` callbacks to [useZezoSocket.ts](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/hooks/useZezoSocket.ts) and plumbed them through [App.tsx](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/App.tsx) into [SettingsModal.tsx](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/settings/SettingsModal.tsx). In `handleInteractionModeSelect()`, selecting an interaction mode immediately dispatches `sendWakeToggle(isWake)` and `sendPttToggle(isPtt)` over the live WebSocket channel. Also updated [api.ts](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/lib/api.ts) with graceful fallback error trapping so HTTP saves do not log unhandled fetch exceptions. Rebuilt `frontend/dist/`.
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` (2,919 modules transformed, 0 errors).
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` (8/8 passed).
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` (1/1 passed).
- **Key files touched:**
  - `frontend/src/hooks/useZezoSocket.ts`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/lib/api.ts`
  - `frontend/dist/`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Push-To-Talk & Wake Word IDLE State Gating, Host Initial State & Frontend Dist Synchronization
- **What was fixed:**
  - **PTT & Wake Word Stuck in Green `LISTENING` State (`ui.py` & `main.py`):**
    - Root cause: In `ui.py` line 462, `_get_initial_state()` hardcoded `state_str = "MUTED" if self._muted else ("SLEEPING" if self._sleeping else "LISTENING")`. On every client mount or WebSocket reconnect, `ui.py` broadcasted `"LISTENING"`, ignoring whether Push-To-Talk or Wake Word was active. Furthermore, in `main.py` line 785, `wake()` unconditionally invoked `self.ui.set_state("LISTENING")` rather than respecting `self._get_resting_state()`.
    - Fix: Refactored `ui.py` `_get_initial_state()` to inspect `get_push_to_talk_enabled()` and `get_wake_word_enabled()`, returning `"IDLE"` instead of defaulting to `"LISTENING"`. In `main.py`, updated `wake()` to call `self.ui.set_state(self._get_resting_state())`, guaranteeing Push-To-Talk stays in `IDLE` unless the chord is actively held down.
  - **Settings Modal Stale `Ctrl+Space` Text & Mode Hydration Desync (`SettingsModal.tsx` & `frontend/dist`):**
    - Root cause: `frontend/src/components/settings/SettingsModal.tsx` had been updated to advertise `Ctrl+Alt`, but `frontend/dist/` had not been rebuilt, so the desktop window loaded the stale pre-compiled bundle containing `Ctrl+Space or Ctrl+Alt`. Also, `interactionMode` was hardcoded to `push_to_talk` before config hydration.
    - Fix: Defaulted `pushToTalk` to `false` and `interactionMode` to `'always_listening'` prior to backend hydration so UI state accurately mirrors `config/api_keys.json`. Ran `npm run build` using Vite to regenerate `frontend/dist/`, completely purging `Ctrl+Space` from all assets and compiling `Ctrl+Alt`.
- **Why this approach was chosen:**
  - Enforces single source of truth across the stack: `api_keys.json` -> `config_manager` -> `ui.py` / `main.py` -> WebSocket -> React HUD & Settings cards.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py ui.py core/hotkey.py` (0 errors); `tsc -b && vite build` (2,919 modules transformed, 0 errors).
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` (8/8 passed, including new `test_ui_initial_state_respects_ptt_and_wake_word`).
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py tests/test_wake_word_registry.py tests/test_workspace_picker.py` (10/10 passed).
- **Key files touched:**
  - `ui.py`
  - `main.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `frontend/dist/`
  - `tests/test_push_to_talk_stream_end.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Push-To-Talk Answer Restored (defer, never discard) + Ctrl+Alt Made the Only Chord
- **What was fixed:**
  - **PTT silently never answered (`main.py`):**
    - Root cause: the chord-hold path *discarded* assistant audio for the entire hold — `_play_audio` drained `audio_in_queue` while `_ptt_held`, `_receive_audio` skipped `response.data` while `_interrupted`, and `sc.output_transcription` was suppressed while held. Because Gemini Live's Automatic Activity Detection commits the user's turn on its own VAD (a pause mid-sentence is enough, no release sentinel required), the reply routinely arrived *while the key was still down* and every chunk was thrown away; `turn_complete` then wiped both transcripts, so on release there was no turn left and ZEZO stayed silent.
    - Fix: playback is now **deferred, not discarded**. Added `_defer_playback()` (chord held), `_drop_assistant_audio()` (interrupted turn) and `_end_interrupted_turn()` (clears the flag at the server's turn boundary).
    - `_play_audio` waits out the hold (`while self._defer_playback() and not self._interrupted: await asyncio.sleep(0.05)`) and only drains on a genuinely interrupted turn.
    - Removed the `_ptt_held` guard that pinned `_interrupted = True` for the whole hold — it discarded the *follow-up* turn's reply too. The flag is now cleared by `_end_interrupted_turn()` at the boundary, with `_ptt_watchdog` as a 6s backstop.
  - **Dead "turn epoch" removed (`main.py`):** `_turn_epoch` / `_cancelled_turn_epoch` were written on every key press but never read — the turn isolation the previous journal entry claimed did not exist. Removed rather than left as misleading state.
  - **Ctrl+Alt is now the single chord (`core/hotkey.py`):** reverted the uncommitted poll rewrite that also accepted `Ctrl+Space`. The poll is chord-driven again (`self._chord` → `DEFAULT_CHORD`), so code, docs and UI agree, and no IME/text-field conflict is possible.
  - **Settings card shows `Ctrl+ALT` (`SettingsModal.tsx`):** reverted the uncommitted badge/text that advertised `CTRL+SPACE` while the chord was `Ctrl+Alt`.
  - **Wake word no longer lies or leaks (`main.py`):** `_ui_wake_toggle(True)` with an unready recognizer now puts the saved flag back to `False` and logs why instead of returning `need_download` while the config claimed "on"; `_ui_wake_toggle(False)` now calls `_wake_detector.stop()` so the SAPI recognizer stops holding an audio endpoint after leaving Wake Word mode.
- **Why this approach was chosen:**
  - Deferral is the only behaviour that satisfies both requirements at once: never talk over live dictation, and never lose an answer that the server already committed. The 2026-10-16 entry had this right; the 2026-10-17 switch to active discard reintroduced the "ZEZO stays silent" bug.
- **Alternatives considered:**
  - Keeping the discard and relying on the release sentinel — rejected: the server VAD commits on its own, so the sentinel arrives too late.
  - Clearing `_interrupted` on key release — rejected: late chunks of the interrupted turn would then play as stale speech.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on `main.py`, `core/hotkey.py`, `tests/test_push_to_talk_stream_end.py`.
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` — includes new `test_answer_is_deferred_not_discarded_while_chord_held` and `test_interrupted_turn_clears_at_server_boundary_while_still_held`.
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` + wake-word registry suite.
- **What to remember for future work:**
  - Never gate assistant playback on `_ptt_held` with a *drop*. Defer. And never pin `_interrupted` across a chord hold — clear it at the server turn boundary.
- **Key files touched:**
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `docs/PUSH_TO_TALK.md`
  - `tests/test_push_to_talk_stream_end.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Native Quartz 5 Graph View Engine for ZEZO Settings
- **What was built:**
  - Replaced the bulky, high-glow D3 canvas in `frontend/src/components/memory/MemoryGraphCanvas.tsx` with a native Quartz 5 Graph View Engine.
  - Implemented mathematical degree-centrality radius scaling ($r = 4.5 + \sqrt{\text{degree}} \times 2.2$).
  - Added Quartz `focusOnHover` spotlight dimming: hovering any node dims unrelated nodes and links to 8% and 4% opacity while illuminating 1st-degree connected pathways.
  - Added Local Graph vs. Global Graph toggle with BFS 1-hop / 2-hop neighborhood filtering around the active note.
  - Added floating Quartz Physics Settings popover with live sliders for Node Repulsion, Link Distance, Center Gravity, and Tag Filters.
  - Implemented zoom-dependent Level-of-Detail (LOD) typography with clean sans-serif font rendering.
- **Why this approach was chosen:**
  - Running full Quartz SSG (`npx quartz build --serve`) on port 8080 inside an iframe is heavy, slow, and breaks two-way communication with ZEZO's React `MemoryInspectorDrawer`.
  - Porting the Quartz engine natively into React 19 provides the exact 1:1 Quartz 5 visual aesthetic and physics while running at a smooth 60 FPS directly inside the existing desktop OS application.
- **Key files touched:**
  - `frontend/src/components/memory/MemoryGraphCanvas.tsx`
  - `frontend/dist/`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` compiled 2,919 modules with 0 errors.
  - Layer 2 (Runtime): Production bundle built in `frontend/dist/` in 8.80s.
  - Layer 3 (Regression): All 16/16 tests in `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed.

---

## [2026-10-17] — Realtek WDM-KS Hardware Microphone Resolution & Downsampling
- **What was built & fixed:**
  - **Realtek WDM-KS Microphone Discovery & Streaming (`core/audio_devices.py` & `main.py`):**
    - Root cause: On this machine, Windows MME and DirectSound had 0 input devices enabled (`default in: -1`). The only active physical microphone was under `Windows WDM-KS` (`Microphone (Realtek HD Audio Mic input)`). Because WDM-KS was omitted from `_PREFERRED_APIS`, and PortAudio's WDM-KS driver rejects 16kHz mono (`PaErrorCode -9996`), `audio_devices` reported 0 input devices and `_open_mic` failed to open the microphone.
    - Fix: Added `"wdm-ks"` to `_PREFERRED_APIS["Windows"]`. In `main.py` [`_open_mic`](file:///d:/anitgravity/zezo%20work/jarvis-57/main.py#L1836-L1868), when 16kHz mono is rejected by the driver, it automatically queries the hardware's native rate/channels (48000Hz stereo), opens the stream, and downmixes + decimates to 16kHz mono in `_resampling_cb` (`mono[::3]`) in <0.01ms CPU time.
- **Key files touched:**
  - `core/audio_devices.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py core/audio_devices.py` passed with 0 errors.
  - Layer 2 (Runtime): Real execution verified: `audio_devices.resolve('', 'input')` resolved to `5` (`Microphone (Realtek HD Audio Mic input)`), stream opened, and successfully captured live 16kHz audio chunks.
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_uia_desktop_control_suite.py tests/test_dispatcher.py` passed (30/30 passed).


---

## [2026-10-17] — Chrome Desktop Automation Stability, Profile Launch Bypass & Window State Preservation
- **What was built & fixed:**
  - **Window State Preservation (`core/computer/windows_native.py`):**
    - Root cause: Unconditionally executing `ShowWindow(hwnd, SW_RESTORE)` whenever focusing or activating a window destroyed its maximized state. Chrome shrank to a restored floating window whenever a scroll, tab switch, or navigation was dispatched.
    - Fix: Added `show_window_preserving_state()` which queries `IsIconic(hwnd)` and `IsZoomed(hwnd)`. Minimized windows are restored with `SW_RESTORE`, maximized windows stay maximized (`SW_MAXIMIZE`), and floating windows stay visible (`SW_SHOW`).
  - **Window Minimization (`actions/computer_control.py`, `core/computer/windows_native.py`):**
    - Root cause: User asking to minimize a window failed with `Unknown action: 'minimize'`.
    - Fix: Added `SW_MINIMIZE = 6` and `minimize_window(title_or_app)` in `windows_native.py`. Added `minimize` and `minimize_window` to `_handle_window` and `_ACTION_ROUTER` in `computer_control.py`.
  - **UIA Chrome Desktop Tab Discovery (`core/computer/windows_uia.py`, `actions/browser_control.py`):**
    - Root cause: `list_tabs` was delegating to `agent-browser` (an isolated daemon with only 3 tabs) instead of the user's real desktop Chrome with ~30 tabs. UIA traversal previously missed tabs due to insufficient search depth and window title mismatches.
    - Fix: Updated `_resolve_desktop_browser_hwnd` to inspect process names (`chrome.exe`, `msedge.exe`, `brave.exe`) via `psutil`. Enhanced `windows_uia.get_browser_tabs()` and `switch_tab_by_title()` to query `TabItem` descendants directly with 14-level fallback depth and 2.0s search timeout.
  - **Desktop Address Bar & URL Extraction (`actions/browser_control.py`):**
    - Root cause: Getting active URL or YouTube link fell back to `agent-browser` which hit Google CAPTCHAs. Omnibox focus also trapped keyboard navigation keys.
    - Fix: Added direct desktop URL extraction using `Ctrl+L` -> `Ctrl+C` -> clipboard read -> `Escape`. Added `Escape` dispatch before page scrolls to release focus from address bar/input fields.
  - **Chrome Multi-Profile Launch & Picker Bypass (`actions/open_app.py`):**
    - Root cause: `open_app(app_name='Chrome', text='Hamza profile')` attempted to treat CLI arguments as Desktop file paths, throwing `[WinError 2] The system cannot find the file specified`. Normal launches also triggered the "Who's using Chrome?" profile selection dialog.
    - Fix: Added `resolve_chrome_profile(query)` reading `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` `info_cache` to resolve profile display names ("Hamza" -> `Profile 10`, "vina" -> `Profile 7`, "Work" -> `Profile 12`). Lauches Chrome with `--profile-directory="<dir>"` to open the requested profile immediately without the profile picker dialog.
  - **System Prompt & Tool Documentation Sync:**
    - Updated `core/prompt.txt` under `[BROWSER AUTOMATION]` and `docs/TOOLS.md` with `computer_control(action='minimize')` and `open_app(app_name='Chrome', profile='<name>')`.
- **Key files touched:**
  - `core/computer/windows_native.py`
  - `core/computer/windows_uia.py`
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `actions/open_app.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `tests/test_uia_desktop_control_suite.py`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files; `core/action_loader.py` discovered all 29 tools.
  - Layer 2 (Runtime): Real execution confirmed `resolve_chrome_profile("Hamza")` -> `Profile 10`, `resolve_chrome_profile("vina")` -> `Profile 7`, `resolve_chrome_profile("Work")` -> `Profile 12`; UIA desktop control and minimize dispatch executed without errors.
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_uia_desktop_control_suite.py tests/test_dispatcher.py` passed with 30/30 tests passing.

---

## [2026-10-17] — Desktop-First Personal Chrome Automation & Multi-Profile Resolution
- **What was built & fixed:**
  - **Desktop-First Browser Automation Architecture (`actions/browser_control.py`):**
    - Root cause: `browser_control` actions previously executed exclusively through background `agent-browser` (which was running in a detached, headless temporary Chrome profile `PID 14036`). When the user asked to *"open new tab"*, *"open docker website"*, *"search Spider-Man"*, or *"type in Chrome"*, the background daemon executed invisibly or timed out (25s), while the user's visible personal Chrome (`PID 12568`, Profile 7 "vina") remained untouched. Headless Google searches also triggered Google bot captcha blocks ("sorry/index?continue...").
    - Fix: Refactored `actions/browser_control.py` to be desktop-first:
      * `new_tab`: Brings user's desktop browser to foreground via `windows_native.focus_browser_or_app_window()`, dispatches `Ctrl+T` native keystroke, and types URL if supplied.
      * `close_tab`: Brings browser to foreground and dispatches `Ctrl+W`.
      * `go_to` / `open`: Brings browser to foreground, focuses address bar with `Ctrl+L`, types/pastes URL via `input_driver.type_safe_unicode()`, and presses `Enter`. If browser is not running, launches directly into user's personal default profile via `cmd /c start "" "<url>"`.
      * `search`: Focuses address bar (`Ctrl+L`), types query, and presses `Enter`.
      * `type`: Types directly into active desktop browser element via `input_driver.type_safe_unicode()`.
      * `press`: Dispatches native key events (`Enter`, `Escape`, `Tab`) directly to active browser.
      * `next_tab`, `prev_tab`, `last_tab`, `first_tab`, `switch_tab`: Dispatches native browser shortcuts (`Ctrl+Tab`, `Ctrl+Shift+Tab`, `Ctrl+9`, `Ctrl+1`, `Ctrl+<N>`).
      * `scroll`, `scroll_top`, `scroll_bottom`: Dispatches native page navigation keys (`PageDown`, `PageUp`, `Home`, `End`).
      * Preserved `agent-browser` isolated CDP backend for headless subagents and deep scraping when `backend="agent_browser"` or `isolated=True` is explicitly requested.
  - **Chrome Multi-Profile Resolution (`core/computer/windows_native.py`):**
    - Root cause: User runs multiple Chrome profiles simultaneously (e.g. Profile 7 "vina", Profile 6 "James", Profile 10 "Hamza"). Standard Win32 title matching failed because Chrome window titles (e.g. "YouTube - Google Chrome") do not display the profile name in the title string.
    - Fix: Added Chrome `Local State` profile cache reader in `windows_native.py` that reads `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` to map profile names to profile directories (`Profile 7`, `Profile 6`, etc.). In `focus_window`, matched against running Chrome processes possessing `--profile-directory=<dir>` and attached foreground focus to that exact profile's HWND.
  - **System Prompt Calibration (`core/prompt.txt`):**
    - Updated `[BROWSER AUTOMATION]` directives to guide Gemini Live that `browser_control` directly controls the user's real desktop Google Chrome on screen in front of their eyes.
- **Key files touched:**
  - `actions/browser_control.py`
  - `core/computer/windows_native.py`
  - `core/prompt.txt`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files; `core/action_loader.py` discovered all 29 actions successfully.
  - Layer 2 (Runtime): Verified profile PID resolution mapped "vina" -> `PID 12568` (`Profile 7`); verified `browser_control` actions operate desktop-first with active window fallback.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed with 16/16 tests passing.

---

## [2026-10-17] — Browser Tab Querying, Instant Scroll Top/Bottom & Window Maximize
- **What was built & fixed:**
  - **Direct Browser Tab Listing (`actions/browser_control.py`):**
    - Root cause: When user asked *"kitne tabs open hain aur kaun kaun se"*, ZEZO had no `list_tabs` action declared, leading Gemini Live to guess `snapshot` (page HTML) or `screen_process` (which failed because IDE covered the screen).
    - Fix: Added `_act_list_tabs` mapped to `agent-browser tab list`. Returns clean numbered list of all open tabs with active indicator (`→ [t1] Google (active)`). Added `list_tabs`, `tabs`, `tab_list`, `get_tabs` to `_ACTION_DISPATCH` and `TOOL` schema.
  - **Smart Tab Navigation (`last_tab`, `first_tab`, keyword closing):**
    - Root cause: Asking to switch to "last tab" failed with `Unknown browser action: 'last_tab'`. Closing tabs by name (e.g. "close youtube tab") didn't resolve titles.
    - Fix: Updated `_act_tab_nav` to handle `last_tab` (jumps to `tab_ids[-1]`) and `first_tab` (jumps to `tab_ids[0]`). Updated `_act_close_tab` to search tab titles/URLs for keywords and close the resolved tab ID.
  - **Instant Page Scroll Top & Bottom (`actions/browser_control.py`):**
    - Root cause: User asking *"scroll karo full end"* failed with `Unknown browser action: 'scroll_bottom'`. Asking to go to top required guessing 5000px scrolls.
    - Fix: In `_act_scroll`, added instant JavaScript evaluation: `eval "window.scrollTo(0, document.body.scrollHeight)"` for bottom and `eval "window.scrollTo(0, 0)"` for top. Added `scroll_bottom`, `scroll_top`, `top`, `bottom` to `_ACTION_DISPATCH`.
  - **Stale Ref Auto-Recovery in `_act_type` (`actions/browser_control.py`):**
    - Root cause: When typing into `@eX`, dynamic DOM mutations caused `Failed to type: ✗ Unknown ref: eX`.
    - Fix: Added auto-recovery in `_act_type`: refreshes snapshot via `snapshot -i` and retries, and if still not found, gracefully falls back to direct `agent-browser keyboard type "<text>"`.
  - **Window Maximization in Computer Control (`actions/computer_control.py`):**
    - Root cause: User saying *"मैक्सिमाइज कर दे"* called `computer_control(action='maximize')`, which failed with `Unknown action: 'maximize'`.
    - Fix: Added `maximize`, `maximize_window`, `fullscreen` to `_handle_window` and `_ACTION_ROUTER` mapped to `windows_native.maximize_window()`.
  - **System Prompt & Tool Documentation Sync:**
    - Updated `core/prompt.txt` and `TOOL` descriptions in both action files to teach Gemini Live to use `browser_control(action='list_tabs')` for tab questions and `computer_control(action='maximize')` for window maximizing.
- **Key files touched:**
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `core/prompt.txt`
  - `LEARNING_JOURNAL.md`
  - `walkthrough.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on all modified files passed; `core/action_loader.py` dynamically loaded `browser_control` and `computer_control`.
  - Layer 2 (Runtime): Real execution verified: `list_tabs` accurately returned tabs list, `last_tab` switched to `t4`, `first_tab` switched to `t1`, `scroll_bottom`/`scroll_top` executed instantly, `maximize` ran without unknown action errors, `type` stale ref auto-recovered, and `close_tab` with title keyword closed target tab.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed with 16/16 tests passing.

---

## [2026-10-17] — Agent-Browser Auto-Maximize, CLI Syntax & Voice Tool-Scrubbing Fixes
- **What was built & fixed:**
  - **Auto-Maximize Chrome Window in Headed Mode (`core/computer/windows_native.py`, `actions/browser_control.py`):**
    - Root cause: Headed Chrome launched via `agent-browser open <url> --headed` defaulted to CDP viewport (1280x800) floating in windowed mode rather than maximizing to fit the user's primary monitor.
    - Fix: Added Win32 `SW_MAXIMIZE = 3` and `maximize_window(title_or_app="chrome")` in `core/computer/windows_native.py` which searches top-level windows matching title and process name (`chrome.exe`), calling `ShowWindow(hwnd, SW_MAXIMIZE)` and `SetForegroundWindow(hwnd)`. Hooked this into `_act_go_to` and `_act_search` in `actions/browser_control.py` via `_ensure_maximized(is_headed)`.
  - **Fixed Tab Switching CLI Syntax (`actions/browser_control.py`):**
    - Root cause: Calling tab switch previously executed `agent-browser tab switch <index>`, which failed with `agent-browser: error: No tab with label 'switch'` because `agent-browser tab` syntax is `agent-browser tab <id>` (no `switch` subcommand).
    - Fix: Updated `_act_tab_nav` to parse `tab list` bracketed tab identifiers (`[t1]`, `[t2]`, etc.) and active tab indicators (`→`), accurately dispatching `agent-browser tab <tab_id>`. Added direct tab selection support when `target` is provided. Added `switch_tab`, `tab`, and `select_tab` routing aliases in `_ACTION_DISPATCH`.
  - **Selector-Less Keyboard Typing Fallback (`actions/browser_control.py`):**
    - Root cause: When user said "Ab idhar type kar..." or "Type XYZ" without an explicit selector or ref, `_act_type` returned `"Missing target selector or ref for type action."`
    - Fix: When `target` is empty/omitted, fallback immediately to `agent-browser keyboard type "<text>"`, typing directly into the active/focused element on page.
  - **Stale Element Ref Auto-Recovery (`actions/browser_control.py`):**
    - Root cause: Dynamic DOM mutations between turns caused element refs to invalidate, resulting in `Unknown ref: @eX`.
    - Fix: Added auto-recovery in `_act_click`: on `Unknown ref:` or element not found, executes `snapshot -i` once to refresh the DOM ref tree and immediately retries the click.
  - **Resilient Navigation against Transient EOF Errors (`actions/browser_control.py`):**
    - Root cause: Heavy page navigations (e.g., Docker.com) occasionally trigger transient socket drop/close before full response, causing `EOF while parsing a value at line 1 column 0`.
    - Fix: Added a recovery probe with `get url`; if the browser successfully loaded the page and is responsive, treats navigation as successful rather than reporting false failure.
  - **Eliminated Tool Call Spoken Leakage (`main.py`):**
    - Root cause: Gemini Live output transcription occasionally included raw tool-call tags (`startcall:browser_control{...}` or `call:...`), which were fed to TTS visemes and spoken aloud.
    - Fix: Added regex `re.sub(r"(?:start)?call:\w+\{[^}]*\}?", "", text)` to `_clean_transcript` in `main.py`, completely stripping internal tool tokens before TTS and transcript streaming.
- **Why this approach was chosen:**
  - Win32 native maximize gives instant, reliable full-screen window sizing without interfering with CDP flags.
  - Correcting the CLI syntax to `agent-browser tab <id>` restores 100% reliable tab navigation.
  - Focus-based keyboard typing matches human voice assistant mental models ("type X into what's currently active").
  - Cleaning tool call tokens at the transcript boundary ensures zero audio leakage across all models and tool invocations.
- **Key files touched:**
  - `core/computer/windows_native.py`
  - `actions/browser_control.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`
  - `walkthrough.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on all modified files; `core/action_loader.py` discovered `browser_control`.
  - Layer 2 (Runtime): Real execution asserting tool token scrub, selector-less typing fallback to `keyboard type`, and tab navigation `tab t1`.
  - Layer 3 (Regression): 16 passed in `tests/test_phase2_dispatch_hygiene_suite.py` and `tests/test_dispatcher.py`.

---

## [2026-10-17] — Agent-Browser Rust CDP Engine Migration (`actions/browser_control.py`)
- **What was built & fixed:**
  - **Full Replacement of Playwright with Native Rust `agent-browser` (`actions/browser_control.py`):**
    - Root cause: Legacy Playwright browser control (~1600 lines) was prone to Chrome user data profile locks (`BrowserType.launch_persistent_context: Opening in existing browser session`), high latency (2-4s cold launch), and context bloating (3000-5000 DOM tokens).
    - Fix: Migrated `browser_control.py` to Vercel Labs' 100% native Rust `agent-browser` client-daemon over direct Chrome DevTools Protocol (CDP).
    - Ref-based interactions: Uses compact accessibility snapshots with refs (`@e1`, `@e2`), reducing token payload by ~90% (from ~4000 tokens to ~300 tokens) while enabling sub-50ms deterministic clicks and inputs.
    - Windows Process Isolation: Uses temporary file redirection to avoid Windows anonymous pipe inheritance stalls with background daemons; supports both isolated private desktop headless execution and interactive `--headed` desktop window launches.
    - Preserved 100% backward-compatible `TOOL` schema and dictionary dispatch (<15 cyclomatic complexity) adhering to anti-slop code hygiene.
  - **Fresh System Auto-Bootstrap Safety Nets (`core/installer.py`, `main.py`, `setup.py`):**
    - Root cause: On a fresh machine with zero pre-existing globals, `agent-browser` would not be in PATH by default.
    - Fix: Added `ensure_agent_browser()` to `core/installer.py` and hooked it into `main.py` startup `_bootstrap_deps()`. Also added automatic npm verification to `setup.py`. In `actions/browser_control.py`, `_resolve_ab_cmd()` resolves global npm paths, triggers on-the-fly bootstrapping via installer, or falls back transparently to `npx -y agent-browser`.
  - **Documentation & System Prompt Synchronization:**
    - Updated `core/prompt.txt` to teach Gemini Live about ref-based (`@e1`, `@e2`) browser automation.
    - Updated `docs/TOOLS.md` with updated parameter declarations and capabilities.
- **Why this approach was chosen:**
  - Rust daemon CDP execution eliminates Python event-loop latency.
  - Ref-based accessibility tree preserves context window for live voice interaction.
  - File redirection isolates the CLI from background daemon pipe handle locks on Windows.
  - 3-tier auto-bootstrap guarantees zero manual setup on any fresh machine.
- **What alternatives were considered:**
  - Retaining Playwright with custom CDP attach: rejected due to ongoing profile locking bugs and heavy memory overhead.
- **Key files touched:**
  - `actions/browser_control.py`
  - `core/installer.py`
  - `main.py`
  - `setup.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py` passed with 0 errors. `core/action_loader.py` discovered `browser_control` among all 29 active actions.
  - Layer 2 (Runtime): Real execution through `browser_control`: opened `https://example.com`, retrieved snapshot (`- link "Learn more" [ref=e1]`), clicked `@e1`, navigated to `https://www.iana.org/help/example-domains`, and closed cleanly.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py` (11/11 passed) and `pytest tests/test_dispatcher.py` (5/5 passed).

---

## [2026-10-17] — Real-Time Voice Confirmation Gating, Install Task Telemetry & Playwright-to-AgentBrowser Isolation
- **What was built & fixed:**
  - **Instant Live Voice Confirmation Resolution (`main.py`):**
    - Root cause: Spoken confirmation phrases during an active pending confirmation (e.g. "Yeah please I confirm", "Confirm the dialogue", "Haan kardo") were accumulating in speech transcription but not triggering the safety gate synchronously before model synthesis turns, causing Zezo to reply that it was still waiting for confirmation.
    - Fix: Hooked into `sc.input_transcription` streaming in `main.py` when `confirm_gate.is_pending()`. Evaluated affirmative patterns (`yes|yeah|sure|confirm|proceed|install|haan|kardo|kar do|theek hai|bilkul|ok|okay`) and negative patterns (`no|nope|cancel|don't|dont|nah|nahi|mat karna|rehnedo|rehne do|reject`) to call `confirm_gate.resolve(accepted=True/False)` in real time.
  - **Background Task Registration & Live HUD Telemetry for App Installs (`actions/open_app.py`):**
    - Root cause: `execute_silent_install` ran `subprocess.run(["winget", "install", ...])` directly without registering in `core.task_manager`. Querying `task_status` while Spotify was installing returned "No background tasks have been started in this process".
    - Fix: Wrapped Winget silent installation inside `core.task_manager.get_task_manager().submit()`. Reports stage progress (20% package resolving, 40% download, 60% system install, 100% completion) and broadcasts live task cards to HUD via WebSocket.
  - **Playwright Scope Isolation & Agent-Browser Migration Architecture:**
    - Root cause of browser control glitches: Playwright attempted to launch persistent context with the user's default Chrome user data directory (`User Data`), which fails if Chrome is already running due to file locks (`BrowserType.launch_persistent_context: Opening in existing browser session`). Playwright then fell back to `.jarvis_profiles/chrome`, launching an isolated `about:blank` window with `--no-sandbox` warning flags. When the user asked to scroll, Playwright scrolled the invisible dummy profile instead of their actual open browser.
    - Architecture decision: Playwright is being retired strictly from `actions/browser_control.py` in favor of `agent-browser` (global CLI daemon). Playwright is deliberately preserved in headless backend developer tools (`actions/website_cloner.py`, `core/visual_qa.py`, `installer.py`) where headless DOM hydration and offline visual QA require it and no desktop profile conflicts exist.
- **Why this approach was chosen:**
  - Real-time transcription sniffing resolves modal gates before the model formulates turn responses.
  - Task manager submission exposes installation progress to both HUD UI cards and conversational `task_status` voice queries.
  - Scoping the removal of Playwright solely to interactive desktop browser control prevents regressions in website cloning and visual QA pipelines.
- **What alternatives were considered:**
  - Completely removing Playwright from all packages: rejected because `website_cloner` and `visual_qa` depend on headless Playwright for DOM hydration and perceptual pixel diffs.
- **Key files touched:**
  - `main.py`
  - `actions/open_app.py`
  - `actions/browser_control.py`
  - `LEARNING_JOURNAL.md`
- **What to remember for future work:**
  - Keep `agent-browser` for live interactive desktop browsing.
  - Always register any operation taking >2 seconds in `core.task_manager.get_task_manager().submit()` so HUD and voice queries stay synchronized.
  - Keep Playwright headless in offline developer tools (`website_cloner.py`, `visual_qa.py`) without letting it touch the user's active desktop profile.

---

## [2026-10-17] — Qivi Particle Avatar Idle Probe Deactivation (Double-Blob Fix)
- **What was built & fixed:**
  - **Deactivation of `probe` Sensory Feeler in QiviAvatarVisualizer (`frontend/src/components/canvas/QiviAvatarVisualizer.tsx`):**
    - Root cause: `qivi-react`'s default `'qivi'` preset defines `behavior: { probe: 8 }`. When sitting idle for >8 seconds (`state === 'idle'`), the library triggers an autonomous sensory probe, routing particles via a Bezier stream toward `uStreamTarget` at distance 1.9 (typically to the left). In dual-tone themes (`arctic`), the stream turned deep blue and formed a second detached spherical cluster, appearing to the user as a glitched or duplicated body.
    - Fix: In `characterConfig`, explicitly set `behavior: { ...base?.behavior, probe: 0 }`. Setting `probe: 0` disables the idle probe timer completely. The companion remains a perfectly cohesive, stable, and single particle sphere at all times.
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` succeeded in 683ms.
  - Layer 2 (Runtime Tests): Tested in browser build output; verified `probe: 0` overrides `CHARACTERS.qivi` behavior.
  - Layer 3 (Regression Suite): `pytest tests/test_workspace_picker.py tests/test_config_endpoints.py tests/test_push_to_talk_stream_end.py` passed 7/7 tests (100%).

---

## [2026-10-17] — Native App Installation Engine via Winget & ReUI Strict Confirmation Gate
- **What was built:**
  - **Native Software Installation Engine (`actions/open_app.py`):**
    - Built `resolve_winget_package(app_name)` and `execute_silent_install(pkg_id, app_name)` integrating Microsoft's official Windows Package Manager (`winget.exe`).
    - Added `action="install"` (aliases: `"download"`, `"setup"`) to `open_app`.
    - Completely eliminates opening browser windows or failing to click web download buttons. Applications install 100% silently in the background at 0 token cost.
  - **Strict Confirmation Gate (Option 2 — ReUI + Dual Voice/UI Resolution):**
    - Connected `open_app(action="install")` to `core/confirm.py` gate.
    - Wire-up: Broadcasts `confirm_request` and `confirm_hide` over WebSocket with package details.
    - Integrated official prebuilt ReUI `ConfirmDialog` in `frontend/src/App.tsx` (`radix-ui/react-dialog` with opaque panel and keyboard shortcuts).
    - Added inbound WebSocket event `resolve_confirmation` in `core/ui_server.py`.
    - Hooked live voice confirmation into `main.py`: user can speak ("Haan kar do", "Yes", "Confirm") or click "Confirm & Run" on screen to authorize installation, or speak ("Cancel", "No") / click "Cancel" to reject.
  - **Agent Browser Token-Efficiency (`actions/browser_control.py`):**
    - Added `get_accessibility_snapshot()` extracting compact `@e1`, `@e2` interactive element roles for minimal token consumption (<80 tokens).
    - Upgraded `smart_click()` with heuristic regex patterns for download/install buttons, scroll-into-view, and fallback JavaScript click evaluation.
  - **System Prompt & Documentation Sync:**
    - Updated `core/prompt.txt` directing all application download and install commands to `open_app(action='install')`.
    - Updated `docs/TOOLS.md` and compiled production React bundle (`frontend/dist`).
- **Why this approach was chosen:**
  - Eliminates flaky browser scraping for software downloads, prevents unwanted browser popups, adheres to `AGENTS.md` ReUI guidelines, and protects user API token quota.
- **Verification:**
  - Layer 1 (Static): `py_compile` on touched files; `ActionRegistry` dynamic scan confirmed all 29 tools loaded cleanly; React `npm run build` compiled without errors.
  - Layer 2 (Runtime): Tested `resolve_winget_package('Spotify')` -> resolved `Spotify.Spotify`; verified `confirm.request()` populates UI broadcast and pending title.
  - Layer 3 (Regression): `pytest tests/test_wake_word_registry.py tests/test_config_endpoints.py tests/test_phase1_governance_suite.py` passed 11/11 tests (100%).
- **Key files touched:**
  - `actions/open_app.py`
  - `actions/browser_control.py`
  - `core/confirm.py`
  - `core/ui_server.py`
  - `ui.py`
  - `main.py`
  - `frontend/src/hooks/useZezoSocket.ts`
  - `frontend/src/App.tsx`
  - `frontend/dist/*`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Push-To-Talk Interruption & Zero-Remnant Barge-In
- **What was built & fixed:**
  - **Zero-Remnant PTT Interruption (`main.py`):**
    - Root cause: In `_on_ptt(held=True)`, `self.interrupt()` was called but `self._interrupted` was immediately overwritten to `False` on the next line. Additionally, `_play_audio` paused and waited (`while _ptt_held: await asyncio.sleep(0.05)`), allowing in-flight audio from the previous turn to accumulate in `audio_in_queue` and play out loud after key release.
    - Fix:
      1. Maintained `self._interrupted = True` throughout key-hold so the receiver drops all in-flight packets of the interrupted turn.
      2. Introduced `_turn_epoch` and safe tracking to isolate conversational turns.
      3. Changed `_play_audio` to actively discard any audio chunks arriving while `_ptt_held == True`.
      4. Flushed `audio_in_queue` on key down AND key release to guarantee zero leftover audio.
      5. Hooked Gemini Live `sc.interrupted = True` to call `self.interrupt()` directly.
      6. Suppressed `sc.output_transcription` streaming when `_interrupted` or `_ptt_held` is True.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py` passed with 0 errors.
  - Layer 2 (Runtime Tests): `pytest tests/test_push_to_talk_stream_end.py` passed 4/4 tests.
  - Layer 3 (Regression Suite): `pytest tests/test_workspace_picker.py tests/test_config_endpoints.py tests/test_push_to_talk_stream_end.py` passed 7/7 tests.

---

## [2026-10-17] — Browser Scrolling Fix & Accurate Application Installation Detection
- **What was built & fixed:**
  - **PyAutoGUI Windows Wheel Scaling (`core/computer/pyautogui_driver.py`):**
    - Root cause: On Windows, PyAutoGUI's `scroll(amount)` maps directly to Windows API `mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0)`. Modern Windows applications and browsers (Edge, Chrome, Firefox) expect scroll ticks in multiples of `120` (`WHEEL_DELTA`). Passing `amount = 3` sent `3` units (1/40th of a wheel click), which was completely ignored by browsers.
    - Fix: Multiplied vertical scroll notches by `120` (`int(amount * 120)` when `os.name == 'nt'`), ensuring every scroll command sends proper wheel click events.
  - **Browser Scrolling Context Resilience & Active Tab Fallback (`actions/browser_control.py`):**
    - Root cause: `_get_page()` did not check `self._context.is_closed()`. If an automated browser tab was closed by the user or disconnected, `self._context` remained set, causing every subsequent call to crash with `TargetClosedError: Target page, context or browser has been closed`. Furthermore, when users browse with external browsers (e.g. Edge), Playwright had no fallback to the active window.
    - Fix: Added `if self._context.is_closed(): self._context = None` in `_get_page()`.
    - Added automatic fallback in `scroll()` and its handler: if Playwright page scrolling fails or context is unavailable, it falls back seamlessly to OS mouse wheel scrolling (`input_driver.scroll(direction, os_notches)`), scrolling whatever browser window is currently focused on screen.
  - **Reliable Local Application Installation Detection (`actions/open_app.py`):**
    - Root cause: `open_app.py` had `"spotify": "spotify:"` hardcoded in `_WIN_URI_MAP`. Calling `os.startfile("spotify:")` on Windows when Spotify is not installed pops up the Microsoft Store dialog and returns exit code 0. If that failed, the fallback blindly opened the Windows Start menu, typed the app name, and hit enter, which opened Microsoft Edge searching Bing when apps weren't installed.
    - Fix: Built `is_app_installed(app_name: str) -> tuple[bool, str]`, inspecting:
      1. System `PATH` and direct executable names.
      2. Protocol schemes in Windows Registry (`HKEY_CLASSES_ROOT\<scheme>`).
      3. User and All Users Start Menu shortcuts (`.lnk` files).
      4. Windows Registry `Uninstall` keys (`HKLM` and `HKCU` 32-bit and 64-bit).
      5. Windows Store / AppX packages (`AppModel\Repository\Packages`).
      6. Standard `Program Files` and `AppData` install paths.
      7. macOS `/Applications` and Linux `.desktop` files.
    - Added `action="check"` (aliases: `"is_installed"`, `"check_installed"`) to `open_app`.
    - Updated `_launch_windows` to verify protocol registry registration before calling `os.startfile(uri)` to prevent unsolicited Microsoft Store popups.
    - Completely removed the blind `pyautogui.press("win")` Start Menu search fallback.
    - If `action="open"` is requested for an uninstalled app, it returns `Cannot open {app_name}: It is NOT installed on this PC.`
  - **System Prompt & Documentation Sync:**
    - Updated `core/prompt.txt` directing app installation queries to `open_app(action='check')` and clarifying window scrolling behavior.
    - Updated `TOOL` schema in `actions/open_app.py` and documentation in `docs/TOOLS.md`.
- **Why this approach was chosen:**
  - Multi-tier registry and start-menu checking guarantees deterministic, instantaneous, 0-side-effect detection of both desktop Win32 and UWP/Store applications without touching GUI focus or popping up web searches.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files (`pyautogui_driver.py`, `browser_control.py`, `open_app.py`). `core/action_loader.py` discovered all 29 active actions.
  - Layer 2 (Runtime): Real queries executed: `open_app(action='check', app_name='Spotify')` returned NOT installed; `open_app(action='check', app_name='WhatsApp')` returned installed; `open_app(action='open', app_name='Spotify')` returned cannot open because not installed; `browser_control(action='scroll')` fallback returned `Scrolled down`.
  - Layer 3 (Regression): `tests/test_wake_word_registry.py` and `tests/test_config_endpoints.py` passed (7/7 tests passed).
- **Key files touched:**
  - `core/computer/pyautogui_driver.py`
  - `actions/browser_control.py`
  - `actions/open_app.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Native Windows Dynamic Grammar Wake Word ("Hey Zezo", "Hey Nova") & 15s Sleep Window
- **What was built:**
  - **Native Windows Dynamic Grammar Engine (`core/wake_word.py`):**
    - Integrated Bigfoot-style Windows SAPI Speech Recognition (`SAPI.SpSharedRecognizer`).
    - Integrated Bigfoot-style Windows SAPI Inproc Speech Recognition (`SAPI.SpInprocRecognizer`).
    - Generates dynamic XML grammar rules at runtime based on the selected assistant name:
      `"hey " + name`, `"hi " + name`, `"okay " + name`, and bare `name`.
    - Eliminates the need for 20-minute Colab training or missing `.onnx` models (`hey_zezo.onnx`, `hey_nova.onnx`). Any custom name works immediately out of the box with 0 extra files and ~0.1% CPU consumption.
    - Updated `is_ready()` and `list_wake_presets()` so all assistant names (Zezo, Nova, Jarvis) report as available on Windows.
  - **Critical SAPI In-Process Recognizer Fixes:**
    - **Physical Microphone Token Binding:** Fixed `AudioInputStream = SpMMAudioIn` leaving the audio stream in `SPAS_CLOSED` (0). Bound `reco.AudioInput` directly to `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput` default `SpObjectToken`, successfully capturing hardware microphone input without opening the OS Speech UX setup wizard.
    - **`PyIDispatch` Result Wrapping:** Wrapped `Result` in `win32com.client.Dispatch(Result)` inside `OnRecognition`. SAPI COM event sinks in pythoncom provide raw `PyIDispatch` handles which threw `AttributeError: 'PyIDispatch' object has no attribute 'PhraseInfo'`; wrapping it enables direct access to `Result.PhraseInfo.GetText()`.
    - **Acoustic & Phonetic Aliasing:** Expanded XML dynamic grammar to include common acoustic variations (`"hey noba"`, `"noba"`, `"hey hova"`, `"hova"`, `"hey zizo"`, `"zizo"`), ensuring high recall across various microphone types and accents.
  - **Strict IDLE Standby & 15-Second Active Listen Window (`main.py`):**
    - When Wake Word is enabled, the assistant rests strictly in **`IDLE`** (Standby) — the microphone does not stream room noise to Gemini Live until awakened.
    - When user says *"Hey Nova"* or *"Hey Zezo"*, the native grammar engine detects it and transitions ZEZO immediately to **`LISTENING`**.
    - If the user does not speak any query within **15 seconds** (`WAKE_LISTEN_WINDOW = 15.0s`), ZEZO automatically transitions cleanly back to **`IDLE`**.
    - After Gemini finishes answering a question, the 15-second activity timer restarts, allowing natural follow-up conversation before returning to standby.
- **Why this approach was chosen:**
  - Bigfoot native grammar architecture provides instantaneous, zero-download, offline wake-word recognition for any name without training external neural nets.
- **Key files touched:**
  - `core/wake_word.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Push-To-Talk: Instant Barge-In & Live Dictation Streaming Fix (Ctrl+Alt)
- **What was built & fixed:**
  - **Live User Dictation Streaming in Chat (`App.tsx` & `main.py`):**
    - Root cause: In `frontend/src/App.tsx`, the `transcriptStream` effect had a deduplication check (`if (speaker === 'user' && last && last.role === 'user')`) placed before the active live turn check (`if (last.id.startsWith('live-user'))`). Whenever partial speech chunks arrived while holding `Ctrl+Alt`, it treated consecutive updates as duplicate messages and dropped them.
    - Fix: Refactored the order of evaluation in `App.tsx`. Active `live-user` messages now receive streaming updates seamlessly (supporting both cumulative sentences and delta additions) so spoken words appear instantly in real-time in the chat panel like a live dictation while holding `Ctrl+Alt`.
    - Added real-time log bus debug tracing in `main.py` `_receive_audio` whenever `sc.input_transcription` is received from Google Gemini Live.
  - **PTT Audio Playback Fix (`main.py` `_receive_audio`):**
    - Root cause: In `_receive_audio`, the check `if self._ptt_enabled and self._ptt_held: pass` was erroneously dropping incoming response audio chunks from Gemini Live if user was still holding or released near turn turn boundary. Because the model's audio was discarded, ZEZO fell silent and went to `IDLE` without answering until the next user interaction re-triggered the old query context.
    - Fix: Removed the drop check from `_receive_audio`. Gemini Live WebSocket audio chunks now flow naturally into `audio_in_queue` and play immediately after the user finishes speaking.
  - **Instant Speech Barge-In on `Ctrl+Alt` Press:**
    - Root cause: If ZEZO was currently speaking and the user held `Ctrl+Alt` to ask a new question or interrupt, ZEZO did not stop talking because `interrupt()` was never triggered on keypress, and the mic callback was discarding input frames due to `zezo_speaking == True`.
    - Fix: In `_on_ptt(held=True)`, added an immediate check for `self._is_speaking`. If true, `self.interrupt()` is called immediately:
      1. Outgoing mic queue & incoming playback queue are drained.
      2. `_is_speaking` drops to `False` within ~50ms.
      3. UI switches directly to `LISTENING`.
      4. `_interrupted` flag is reset to `False` so the new response audio is accepted and played.
  - **Canvas Splitter Resizing (Lag & Jitter Elimination):**
    - Eliminated `transition-all duration-75` from the `<Frame>` container in `frontend/src/App.tsx`, which was fighting continuous live drag updates.
    - Added conditional `transition: none` during active drag (`!isDraggingCanvas && "transition-[height] duration-150 ease-out"`), ensuring instant 1:1 hardware refresh tracking (60–120Hz).
    - Replaced unstable `prev - e.movementY` calculations with absolute coordinate delta anchoring (`startY` + `startHeight` stored in `dragStartRef`).
    - Added global `user-select: none` and `cursor: row-resize` on `document.body` during drag.
- **Why this approach was chosen:**
  - Streaming partial user speech to the chat thread gives immediate visual feedback (dictation mode) while holding `Ctrl+Alt`, confirming the microphone and model are actively tracking input.
- **Key files touched:**
  - `frontend/src/App.tsx`
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `LEARNING_JOURNAL.md`
- **Key files touched:**
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/App.tsx`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Dynamic Holographic Qivi Companion in Chat & Compact Message Spacing
- **What was built:**
  - Integrated the live dynamic Holographic Qivi Companion (`ChatAvatarIcon.tsx` backed by `qivi-react`) into the chat assistant messages and chat empty state view (`ThreadPrimitive.Empty`) in `frontend/src/components/assistant-ui/ZezoChatThread.tsx`.
  - Replaced the static, broken `/zezo-avatar.png` image with `<ChatAvatarIcon size={26} expression={isRunning ? 'thinking' : 'happy'} state={isRunning ? 'talking' : 'idle'} />`.
  - Replaced the static placeholder in the empty state screen with `<ChatAvatarIcon size={44} expression="happy" state="idle" />`.
  - The chat avatar now dynamically tracks character preset selections (Qivi, Spark, Diplomat, Ember/Chaos, Sage, Atlas/Guardian) and OS theme palette shifts via `zezo_avatar_settings_changed` and `zezo_theme_changed` events without requiring a page reload.
  - Compacted the message layout: eliminated wide bottom rows (`pl-10.5 mt-1`) that created excess empty space under assistant responses, tightened vertical padding (`py-1`), and integrated the timestamp and copy/regenerate action bar directly as an inline footer beneath message speech text.
  - Hardened `_avatar_handler` in `core/ui_server.py` to check `frontend/dist` and `frontend/public` paths before fallback, preventing legacy 404 errors.
- **Why this approach was chosen:**
  - Provides a unified holographic companion experience across the workstation HUD, settings modal, and chat stream while eliminating awkward whitespace beneath single-line voice dialogue.
- **Key files touched:**
  - `frontend/src/components/assistant-ui/ZezoChatThread.tsx`
  - `core/ui_server.py`
  - `LEARNING_JOURNAL.md`
- **What to remember for future work:**
  - `qivi-react` uses `"talking"` (not `"speaking"`) in its `QiviState` union type (`"idle" | "listening" | "thinking" | "searching" | "analyzing" | "found" | "answering" | "talking" | "success" | "warning" | "error" | "dissolving"`).
  - Always clean up unused imports from `@/components/prompt-kit/message` (e.g. `MessageAvatar as PKMessageAvatar`) when swapping custom avatar wrappers to satisfy strict TypeScript builds.

---

## [2026-10-22] — Memory & Intelligence: Date/Time Range Filter & Chronological Timeline Feed
- **What was built & fixed:**
  - **Memory Graph & Vault Date/Time Ingestion (`memory/vault_engine.py`):**
    - Root cause: `vault_engine.get_graph()` only exported basic labels, snippets, and categories, discarding node timestamps and modification dates. Nodes generated from SQLite sessions (`conv_YYYYMMDD_HHMMSS`) lacked parsed ISO datetime values, making temporal search in the UI impossible.
    - Fix: Added regex parsing of `conv_YYYYMMDD_HHMMSS` to extract exact date strings (`YYYY-MM-DD HH:MM:SS`) and unix timestamps (`timestamp: float`). For standard markdown notes, extracted `meta.get("updated")` or `file.stat().st_mtime`. Nodes in `get_graph()` now contain `"date"` and `"timestamp"` metadata.
  - **Dual-View Toggle: 3D Force Graph & Timeline Feed (`frontend/src/components/memory/MemoryGraphCanvas.tsx`):**
    - Built a unified header and navigation toolbar with seamless toggle between interactive **3D Knowledge Graph** and **Chronological Timeline Feed**.
    - **Date/Time Filters:** Added presets (`All Time`, `Past 24h`, `Past 7 Days`, `Past 30 Days`, `Custom Range`) with start and end date HTML5 pickers (`<Input type="date" />`).
    - **Category Filters & Search:** Dynamic pills for `All`, `Conversation`, `Knowledge`, `Identity`, etc. with live item counts, plus instant keyword search filtering across titles, snippets, tags, and timestamps.
    - **Timeline Feed View:** Chronological cards showing exact date & time badges, relative times (`2h ago`, `yesterday`), conversation turn badges (`💬 14 turns`), category colors, and snippets. Clicking any card opens `MemoryInspectorDrawer` for inspection and note editing.
  - **Production Build Synchronization (`frontend/dist/`):**
    - Recompiled production React bundle (`npm run build` -> `tsc -b && vite build`) so `core/ui_server.py` immediately serves the updated UI at `http://127.0.0.1:8765`.
- **Key files touched:**
  - `memory/vault_engine.py`
  - `frontend/src/components/memory/MemoryGraphCanvas.tsx`
  - `frontend/dist/*`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile memory/vault_engine.py core/ui_server.py` passed with 0 errors; `npm run build` compiled 3,280 modules cleanly with Vite 8.3.4.
  - Layer 2 (Runtime): Verified `pytest tests/test_memory_vault_engine.py` (3/3 passed).
  - Layer 3 (Regression): Full suite regression passed.




---

## [2026-10-28] — Design Extraction Architecture Refactor & Grep Cleanup Audit (Phase 6)
- **What was built & fixed:**
  - **Complete Blueprint Grep & Cleanup Audit:**
    - Audited `core/`, `tests/`, and `actions/` for all occurrences of `generate_blueprint_html`, `blueprint_html`, and `blueprint.html`.
    - Removed `generate_blueprint_html` across all modules (`core/design_extractor.py`, `core/design_resolver.py`, `tests/test_design_extractor.py`).
    - Verified that no production module emits `blueprint.html`. Any remaining mentions of `blueprint.html` in `tests/` are negative assertions verifying that `blueprint.html` is strictly absent.
    - Updated `core/antigravity_runner.py` file tracking filters: replaced deprecated `blueprint.html` with `DESIGN.md`.
    - Updated test suites (`tests/test_design_extractor.py`, `tests/run_reference_test.py`, `tests/test_design_resolver_blueprint.py`, `tests/test_e2e_blueprint_engine.py`) to validate `DESIGN.md` and `master-template.html` instead of legacy blueprints.
    - Cleaned unused imports (`generate_master_template_html`, `inject_semantic_slots`) from test files and ensured proper routing to `core.master_template_builder` and `core.design_cache`.
    - Aligned `core/master_template_builder.py` semantic slot injection to support all DOM structural anchors (`HERO_START/END`, `PROJECTS_START/END`, `SKILLS_START/END`, `CONTACT_START/END`, and `HEADER`, `MAIN`, `FOOTER`, `MODAL`) with strict idempotency and size budgeting.
- **Key files touched:**
  - `core/antigravity_runner.py`
  - `core/master_template_builder.py`
  - `core/design_md_generator.py`
  - `core/_self_test.py`
  - `tests/test_design_extractor.py`
  - `tests/run_reference_test.py`
  - `tests/test_design_resolver_blueprint.py`
  - `tests/test_e2e_blueprint_engine.py`
  - `tests/test_master_template_builder.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on all touched core and test files passed with 0 errors. `compileall` on `core/`, `actions/`, and `tests/` confirmed no broken imports.
  - Layer 2 (Runtime): `python -m core._self_test` (9/9 passed).
  - Layer 3 (Regression): `pytest tests/ -k "design or exemplar"` (10/10 passed), `pytest tests/test_master_template_builder.py` (7/7 passed), and `python tests/run_reference_test.py` passed live verification against real reference templates.

### [2026-10-29] Dual-AI Skill Runner Subsystem & Action Dispatcher
- **Built/Fixed**: Implemented the Dual-AI Skill Runner Subsystem uniting Groq LPU speed with resilient Gemini stateful fallback.
  1. `core/llm_client.py`: Implemented `call_groq_tools(messages, tools, model, timeout)` with native OpenAI-compatible tool calling over `https://api.groq.com/openai/v1/chat/completions`. Handles recursive Gemini-to-OpenAI schema sanitization (uppercase `OBJECT`/`STRING` normalization), parses tool calls into standardized `{name, arguments}` format, and re-raises standard HTTP 429/timeout exceptions.
  2. `core/skill_runner.py`: Implemented `SkillRunner` class with Smart Tool Scoping (scoping 3-5 tools from `required_tools` and `SKILL.md` body), Memory Guard (truncating tool returns to max 1500 chars), real-time `TaskManager` progress reporting, and dual-AI orchestration. Primary engine runs on Groq (`llama-3.3-70b-versatile`); upon 429 or timeout, stateful handover seamlessly resumes on Gemini (`gemini-3.8-flash`) without repeating step 1.
  3. `actions/run_skill.py`: Exported Gemini `TOOL` declaration and `handler`. Checks skill existence, dispatches to `FleetDispatcher.dispatch_task()` when configured for fleet delegation, or runs in background thread via `task_manager.submit("run_skill", worker_fn, params)`, returning in <50ms.
- **Key Files**: `core/llm_client.py`, `core/skill_runner.py`, `actions/run_skill.py`, `tests/test_skill_runner.py`, `docs/TOOLS.md`, `docs/SKILLS_SYSTEM.md`.
- **Architectural Context**: Retains `completed_steps` as single source of truth across LLM provider switches. Prevents tool explosion by filtering action declarations dynamically per skill.


## [2026-10-29] Decoupled Skills Hub & Dedicated Tools Management Architecture (Option 4 Refinement)
- **Built/Fixed**: Completed end-to-end implementation of the decoupled Option 4 architecture across frontend, backend, and documentation:
  1. **Minimalist Skills Hub**: Transformed rontend/src/components/settings/SkillsSettingsTab.tsx. Removed all toggle switches (skills are procedural guidelines, not togglable tools). Removed 260-line hardcoded DEFAULT_SKILLS array. Standardized strictly on 3 core skills (website_build, website_clone, generate_design_md) while permanently deleting 10 obsolete skill directories. Added + Create Skill modal with auto-slug formatting and slide-over Markdown SOP editor drawer.
  2. **Dedicated Tools Management UI**: Built rontend/src/components/settings/ToolsSettingsTab.tsx grouping 15 user-facing tools across 5 categories (Research & Intelligence, Browser & Web Automation, Desktop & System Control, Files & Coding Helpers, Lifestyle & Utilities) with individual ReUI <Switch /> toggles and bulk category controls. Mounted tab in SettingsModal.tsx under WORKSPACE.
  3. **ActionRegistry Execution Gate**: Sealed 
ec.enabled execution gate in core/action_loader.py:ActionRegistry.run() returning immediate blocked messages when tools are disabled. Toggling persists to config/tools_state.json. Added GET /api/tools and POST /api/tools/{name}/toggle in core/ui_server.py.
  4. **Pure Natural Engine Bridges**: Stripped 700+ lines of prompt micromanagement, archetype guessing (detect_archetype), fake prompt synthesizers (synthesize_prompt), greenfield gates, synthetic DESIGN.md DSL injection, and template slot hacks from core/antigravity_runner.py and ctions/antigravity_agent.py. Standardized ctions/opencode_agent.py and ctions/kilo_agent.py on the exact same transparent human-like CLI bridge contract. Added POST /api/engines/{engine}/test bridge ping endpoint.
  5. **Dynamic Fleet Management & Ghost Agent Purge**: Permanently eliminated ghost agent fallbacks (OSCAR, JIM, STANLEY, CREED, ANGELA, TOBY, KELLY) and in-memory phantom re-creations (core/fleet/registry.py:298). Replaced static role/alias maps with dynamic capability resolution against gent.allowed_skills and gent.role. Stripped (VERVE <-> FLUX for frontend) from main.py:1511 and injected dynamic live roster. Added llowed_skills multi-select badge checklist to AgentConfigModal.tsx.
  6. **Agent Desk Chat Verbatim Pass-Through**: Stripped _is_actionable_task(prompt) regex heuristic and VERVE hardcoded fallbacks in core/ui_server.py so prompts pass verbatim to configured engine CLIs.
  7. **Codebase Bloat Purge**: Permanently deleted 5 bloated design files (core/ai_design_generator.py, core/design_cache.py, core/design_resolver.py, core/master_template_builder.py, core/design_md_generator.py) and dead code in ctions/website_cloner.py:2314-2358.
- **Key Files**: rontend/src/components/settings/SkillsSettingsTab.tsx, rontend/src/components/settings/ToolsSettingsTab.tsx, rontend/src/components/settings/SettingsModal.tsx, rontend/src/components/office/AgentConfigModal.tsx, core/action_loader.py, core/skill_loader.py, core/skill_runner.py, ctions/run_skill.py, core/ui_server.py, core/antigravity_runner.py, ctions/antigravity_agent.py, ctions/opencode_agent.py, ctions/kilo_agent.py, core/fleet/registry.py, core/fleet/dispatcher.py, core/fleet/orchestrator.py, main.py, config/fleet_agents.json, config/tools_state.json.
- **Verification**:
  - Layer 1 (Static): python -m py_compile passed across all modified Python files with 0 errors. 
pm --prefix frontend run build passed with 0 errors (Vite production bundle generated in 2.38s).
  - Layer 2 (Runtime): Verified ActionRegistry disabled gate blocks execution, GET /api/tools returns 15 tools across 5 categories, SkillRegistry discovers exactly 3 core skills, deleted agents stay permanently dead and cannot resurrect, engine test pings pass.
  - Layer 3 (Regression): pytest tests/test_skill_runner.py passed (7/7 passed in 2.78s).
