# 🧠 ZEZO Skills System: Current State Documentation

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Document Status:** Comprehensive Factual Codebase Audit  
> **Target Subsystems:** `core/skill_loader.py`, `core/skill_scanner.py`, `main.py`, `skills/`, `core/fleet/`, `core/ui_server.py`, `frontend/src/components/settings/SkillsSettingsTab.tsx`, `actions/`  

---

## 1. How It Works

The ZEZO Skills System is a local-first declarative capability engine that stores standard operating procedures (SOPs) as Markdown files on disk, scans them for security threats, indexes their metadata into the primary AI model's system prompt, and makes their full procedural instructions available on-demand via atomic tool calls.

```
                    ┌───────────────────────────────┐
                    │       skills/*/SKILL.md       │
                    │   (Declarative Markdown SOPs) │
                    └───────────────┬───────────────┘
                                    │ rglob("SKILL.md")
                                    ▼
                    ┌───────────────────────────────┐
                    │     core/skill_loader.py      │
                    │  (SkillRegistry & Hot-Reload) │
                    └───────┬───────────────┬───────┘
                            │               │
        format_prompt_block │               │ read_skill(name)
                            ▼               ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     Gemini Live WebSocket Session     │ │   Fleet Specialist Subagent Runner    │
│               (main.py)               │ │      (core/fleet/dispatcher.py)       │
│                                       │ │                                       │
│ • System prompt index injected at boot│ │ • Inspects agent.allowed_skills       │
│ • read_skill tool fetched on-demand   │ │ • Prepends [ACTIVE SKILL: <name>]     │
│ • Conducts atomic tools step-by-step  │ │ • Dispatches to CLI binary (agy/open) │
└───────────────────────────────────────┘ └───────────────────────────────────────┘
```

### 1.1 Discovery & In-Memory Representation (`core/skill_loader.py`)
- **Package Layout:** Skills reside on disk in `<project_root>/skills/<skill_name>/SKILL.md`.
- **Data Structure (`SkillRecord`):** Represents each skill in memory (`core/skill_loader.py:43-73`):
  - `name: str`: Unique identifier derived from YAML frontmatter or directory name.
  - `description: str`: Concise summary describing the capability.
  - `instructions: str`: Raw Markdown content following the frontmatter block.
  - `folder_path: Path`: Absolute path to the skill directory.
  - `domain: str = "general"`: Categorical domain (`ui`, `coding`, `research`, `system`, `general`, `orchestration`).
  - `author: str = "system"`: Author attribution.
  - `version: str = "1.0"`: Version string.
  - `tags: list[str]`: List of categorical tags.
  - `triggers: list[str]`: Keyword triggers used for semantic matching.
  - `auto_activate: bool = True`: Whether the skill activates automatically when matched.
  - `pinned: bool = False`: Whether full instructions are permanently injected into the prompt.
  - `disabled: bool = False`: Whether the skill is excluded from discovery and execution.
- **Filesystem Traversal:** The singleton `SkillRegistry` (`core/skill_loader.py:145-588`, accessed via `get_skill_registry()`) traverses the tree using `self._dir.rglob("SKILL.md")` (line 235).
- **Directory Exclusions:** A hardcoded set `EXCLUDED_SKILL_NAMES = {"antigravity_agent", "kilo_code", "opencode", "custom_skill_10", "hamza_taste"}` (line 114) filters out internal directories and test packages.
- **YAML Frontmatter Parsing:** Extracted via regular expression without third-party dependencies:
  ```python
  _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
  ```
  Parses `name`, `description`, `author`, `version`, `tags`, `triggers`, and `domain` line-by-line.
- **Domain & Trigger Inference:**
  - If `domain` is missing, `_infer_domain_from_name_and_tags()` classifies it into `"ui"`, `"coding"`, `"research"`, `"system"`, or `"general"`.
  - If `triggers` is missing, `_generate_default_triggers()` derives keywords from name, tags, and domain.
- **State Separation (`config/skills_state.json`):**
  - Toggles `pinned`, `disabled`, and `auto_activate` are stored separately in `config/skills_state.json` via `_save_state()` (line 163) and loaded via `_load_state()` (line 155), preserving the immutability of `SKILL.md` files.
- **Hot-Reloading & Cache Invalidation:** `SkillRegistry.get_signature()` (lines 178–202) returns `(max_mtime, count, tuple(sorted(entries)))`. The method `refresh_if_modified()` (lines 208–219) checks this signature before read operations, triggering an in-place `reload()` under a thread lock (`_lock = threading.RLock()`) if any file has been added, modified, or removed.

### 1.2 Security Scanning & Guardrails (`core/skill_scanner.py`)
Incoming skill content, newly generated skills, and installed archives pass through static regex analysis before touching the filesystem or prompt context:
- **Data Structures (`core/skill_scanner.py:70-98`):**
  - `ScanViolation`: Dataclass containing `pattern_name`, `message`, `line_number`, `snippet`, and `severity` (`HIGH`, `CRITICAL`, `MEDIUM`).
  - `ScanReport`: Dataclass containing `is_safe: bool`, `violations: list[ScanViolation]`, `sanitized_content: str`, and `redacted_secrets_count: int`.
- **Prompt Injection Defense (`_PROMPT_INJECTION_PATTERNS`, lines 26–51):**
  - System override directives (`ignore all previous instructions`, `disregard prior rules`).
  - Raw ChatML and Llama enclosure tokens (`<|im_start|>system`, `[INST] <<SYS>>`).
  - Jailbreak and persona hijack phrases (`act as DAN`, `unrestricted god mode`).
  - Token and credential exfiltration patterns (`exfiltrate secrets to`, `curl http://... api_key`).
- **Dangerous System Commands (`core/governance._DANGEROUS_PATTERNS`, lines 142–165):**
  - Drive formatting and raw partitioning (`format c:`, `diskpart`).
  - Destructive root deletions (`rmdir /s /q c:\`, `del /s /q c:\`, `rm -rf /`, `Remove-Item -Recurse c:\`).
  - Shadow copy and recovery tampering (`vssadmin delete shadows`, `wmic shadowcopy delete`, `bcdedit /set recoveryenabled no`).
  - Registry deletions (`reg delete hklm`, `Remove-ItemProperty -Path hklm:`).
  - Obfuscated binary executions (`powershell -enc`, `certutil -decode`).
- **Obfuscation Detection (`_OBFUSCATION_PATTERNS`, lines 54–67):**
  - Encoded PowerShell dynamic evaluation (`iex [System.Text.Encoding]`).
  - Dynamic Python evaluation (`eval(compile(...))`).
  - Obfuscated inline imports (`__import__('os').system`).
- **Secret Scrubbing & Redaction (`scan_skill_text`, lines 103–170):**
  - Invokes `memory.sqlite_memory.redact_secrets(raw_text)` to strip API keys (Google, OpenAI, Tavily, GitHub PATs, Bearer tokens, passwords).
  - Matches are replaced with `[REDACTED_SECRET]` and stored in `ScanReport.sanitized_content`.
- **Archive Safety (`SkillRegistry.install_skill`, `core/skill_loader.py:438-504`):**
  - 50MB archive size limit, 25MB single-file extraction limit.
  - Zip-Slip path traversal defense rejecting any entry resolving outside the target directory.
  - Verifies presence of a valid `SKILL.md` inside the archive root.
  - Runs `scan_skill_directory()` post-extraction; if unsafe, removes the directory completely.

### 1.3 AI Selection & System Prompt Priming (`main.py`)
- **Initialization:** `ZezoLive.__init__()` instantiates `self._skill_registry = get_skill_registry()` (`main.py:687-688`).
- **Prompt Priming:** Inside `ZezoLive._build_config()` (`main.py:1535-1537`), `self._skill_registry.format_prompt_block()` appends the skill catalog to the Gemini Live system instructions:
  ```text
  [AVAILABLE SKILLS & WORKFLOWS]
  Use read_skill(skill_name) before performing specialized workflows:
  • website_build (CODING): Master protocol for building modern websites...
  • git_workflow (SYSTEM): Standard operating procedure for git version control...
  ```
- **Pinned Skills Expansion:** If a skill has `pinned: True` in `config/skills_state.json`, its entire markdown instructions are injected directly into `[PINNED SKILL GUIDELINES]` (`core/skill_loader.py:391-395`).

### 1.4 Invocation & Calling (`main.py`)
Gemini Live accesses the skills engine through three inline tools declared in `main.py` (lines 515–549):
1. `read_skill(skill_name: str)` (lines 515–528): Retrieves the full Markdown SOP.
2. `list_skills()` (lines 529–534): Returns a formatted list of all registered skills.
3. `save_learned_skill(name, description, instructions)` (lines 535–549): Validates, scans, and writes newly synthesized skills to disk.

---

## 2. Execution Flow

The system operates across two distinct execution flows: the **Declarative In-Context Flow** (for Gemini Live) and the **Subagent Fleet Flow** (for external coding engines).

### 2.1 Declarative In-Context Execution Flow (Gemini Live)

```
[User Utterance / Text Command]
               │
               ▼
   [main.py WebSocket Ingestion]
  (Audio: _listen_audio() / Text: _on_text_command())
               │
               ▼
      [Gemini Live Model]
  (Evaluates prompt catalog & tool declarations)
               │
               ├─► Emits tool call: read_skill(skill_name="git_workflow")
               │
               ▼
     [_handle_read_skill() (main.py:1763)]
               │
               ├─► Calls SkillRegistry.read_skill("git_workflow")
               ├─► Checks mtime signature via refresh_if_modified()
               ├─► Reads skills/git_workflow/SKILL.md from disk
               │
               ▼
[WebSocket FunctionResponse sent to Gemini]
               │
               ├─► Full Markdown SOP enters Gemini working memory
               │
               ▼
[Model In-Context Reasoning & Step Execution]
               │
               ├─► Model reads procedural instructions step-by-step
               ├─► Interacts conversationally with user for parameters
               └─► Emits atomic tool calls (e.g. computer_control, file_controller)
```

### 2.2 Subagent Fleet Execution Flow (`core/fleet/`)

```
[User Request / Swarm Task]
               │
               ▼
[FleetOrchestrator / actions/fleet_control.py]
               │
               ▼
[FleetDispatcher.dispatch_task() (core/fleet/dispatcher.py:163-672)]
               │
               ├─► Reads agent.allowed_skills from FleetAgent definition
               ├─► Calls core.skill_loader.get_skill_registry()
               ├─► Resolves skill object: skill_reg._skills.get(sk)
               │
               ▼
[_compile_task_prompt() (core/fleet/dispatcher.py:268-284)]
               │
               ├─► Formats: [ACTIVE SKILL: <name>]\n<instructions>
               ├─► Assembles enriched_prompt (Persona + Skills + Memory + Task)
               │
               ▼
[Subprocess Runner (core/antigravity_runner.py / actions/*_agent.py)]
               │
               ├─► Launches CLI binary: agy, opencode, or kilo
               ├─► Enforces Windows Job Object CPU & memory caps
               └─► CLI runs autonomous loop guided by the injected Markdown SOP
```

---

## 3. Files and Functions

### Core Subsystem Components

| File Path | Component / Function | Operational Responsibility |
| :--- | :--- | :--- |
| `core/skill_loader.py` | `SkillRecord` (dataclass, lines 43–73) | In-memory representation of skill metadata, configuration, and instructions. |
| `core/skill_loader.py` | `SkillRegistry` (class, lines 145–588) | Singleton managing discovery, YAML frontmatter parsing, caching, prompt blocks. |
| `core/skill_loader.py` | `_discover_skills()` / `reload()` (lines 221–298) | Scans `skills/*/SKILL.md`, parses frontmatter, populates `_skills` dictionary. |
| `core/skill_loader.py` | `_parse_yaml_frontmatter()` (lines 75–111) | Custom regex-based parser extracting metadata fields. |
| `core/skill_loader.py` | `get_signature()` (lines 178–202) | Calculates composite `(max_mtime, count, tuple(sorted(names)))` signature. |
| `core/skill_loader.py` | `refresh_if_modified()` (lines 208–219) | Compares current signature against cache; triggers `reload()` on change. |
| `core/skill_loader.py` | `read_skill(name)` (lines 316–330) | Retrieves formatted Markdown text via exact match or substring search. |
| `core/skill_loader.py` | `match_skills(query)` (lines 331–373) | Scoring engine (+40 name, +30 trigger, +15 tag) matching natural language. |
| `core/skill_loader.py` | `format_prompt_block()` (lines 374–398) | Generates `[AVAILABLE SKILLS & WORKFLOWS]` prompt block for model priming. |
| `core/skill_loader.py` | `get_active_skill_prompt()` (lines 399–425) | Generates budgeted skill block for candidate task strings. |
| `core/skill_loader.py` | `install_skill()` (lines 438–504) | Unpacks `.zip` or copies directory, validates Zip-Slip, runs security scan. |
| `core/skill_loader.py` | `save_learned_skill()` (lines 505–570) | Validates, scans, sanitizes, and writes synthesized `SKILL.md` packages to disk. |
| `core/skill_scanner.py` | `ScanViolation` / `ScanReport` (lines 70–98) | Security scan result schemas and severity ratings. |
| `core/skill_scanner.py` | `scan_skill_text()` (lines 103–170) | Line-by-line regex scanning against prompt injection, shell commands, obfuscation. |
| `core/skill_scanner.py` | `scan_skill_directory()` (lines 172–200) | Recursively evaluates all text/code files inside a skill directory. |
| `main.py` | `ZezoLive.__init__()` (lines 687–688) | Instantiates `self._skill_registry = get_skill_registry()`. |
| `main.py` | `_build_config()` (lines 1535–1537) | Injects `format_prompt_block()` into active system instructions. |
| `main.py` | `TOOL_DECLARATIONS` (lines 515–549) | Registers schemas for `read_skill`, `list_skills`, `save_learned_skill`. |
| `main.py` | `_handle_read_skill()` (lines 1763–1766) | Resolves `skill_name` argument and delegates to `SkillRegistry.read_skill()`. |
| `main.py` | `_handle_list_skills()` (lines 1768–1776) | Returns bulleted list of active skills and domains. |
| `main.py` | `_handle_save_learned_skill()` (lines 1778–1786) | Delegates skill synthesis to `SkillRegistry.save_learned_skill()`. |
| `core/fleet/dispatcher.py` | `_compile_task_prompt()` (lines 268–284) | Resolves `agent.allowed_skills` and appends `[ACTIVE SKILL: <name>]` blocks. |
| `core/fleet/registry.py` | `FleetAgent.allowed_skills` (line 83) | Whitelist array of skill names bound to specific agent personas. |
| `core/ui_server.py` | `/api/skills` REST Endpoints (lines 1328–1557) | HTTP API for listing, toggling modes, installing archives, and deleting skills. |
| `frontend/.../SkillsSettingsTab.tsx` | Component (486 LOC) | React UI for managing, toggling, inspecting, and editing skills via drawer. |

---

### Complete Disk Inventory of `skills/` (11 Packages)

An exhaustive physical inspection of `c:\Users\Hamza Bukhari\Documents\antigravity\jarvis-57\skills\` verified exactly 11 skill package directories:

| Package Directory | Frontmatter Status | Name | Domain | Triggers | Tags | Auto Activate | LOC | Bytes | Ancillary Files |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `figma_helper/` | **Missing Delimiters** | Missing* | Missing* | Missing | Missing | Missing | 47 | 2,826 | 0 |
| `git_workflow/` | Valid (Nested `metadata`) | `git_workflow` | Missing* | Missing | Missing | Missing | 23 | 1,009 | 0 |
| `make_plan/` | Valid (Nested `metadata`) | `make_plan` | Missing* | Missing | Missing | Missing | 24 | 1,083 | 0 |
| `multi_agent_collaboration/`| Valid (Nested `metadata`) | `multi_agent_collaboration` | Missing* | Missing | Missing | Missing | 25 | 1,474 | 0 |
| `office_suite/` | Valid (Nested `metadata`) | `office_suite` | Missing* | Missing | Missing | Missing | 21 | 1,576 | 0 |
| `parallel_task_management/` | Valid (Flat fields) | `parallel_task_management` | `general` | Present | Present | Missing | 13 | 417 | 0 |
| `social_research/` | Valid (Nested `metadata`) | `social_research` | Missing* | Missing | Missing | Missing | 23 | 1,225 | 0 |
| `test_fastapi_deploy/` | Valid (Nested `metadata`) | `test_fastapi_deploy` | Missing* | Missing | Missing | Missing | 13 | 326 | 0 |
| `web_research_pipeline/` | Valid (Nested `metadata`) | `web_research_pipeline` | Missing* | Missing | Missing | Missing | 23 | 1,089 | 0 |
| `web_scraper/` | Valid (Nested `metadata`) | `web_scraper` | Missing* | Missing | Missing | Missing | 24 | 1,272 | 0 |
| `website_build/` | Valid (Flat fields) | `website_build` | `ui` | Present | Missing | `True` | 260 | 21,578 | 21 (20 HTML, 1 JSON) |

*\*Note: Fields marked "Missing\*" are dynamically inferred at runtime by `core/skill_loader.py` (e.g. folder name used for `name`, keyword heuristics used for `domain`).*

---

## 4. Current Issues

### 4.1 Skill Shadowing by Monolithic Action Tools
When a user intent matches both a skill and a coarse-grained action tool, Gemini Live invokes the coarse-grained action tool directly, bypassing the skill.
- **Evidence:** Gemini Live receives declarations for both `read_skill` and `clone_website` (`actions/website_cloner.py:3245-3253`). Because `clone_website` explicitly matches `"clone this website"`, Gemini calls `clone_website`. `read_skill` is never invoked.

### 4.2 Complete Bypass in Website Cloner (`actions/website_cloner.py`)
`actions/website_cloner.py` is a 3,310-line monolithic file that bundles crawling, preview hosting, DOM rewriting, and rebuild generation in Python:
- **Evidence 1 (Zero Skill Interaction):** A case-insensitive search across all 3,311 lines of `actions/website_cloner.py` returns **0 hits** for `SkillRegistry`, `read_skill`, `skill_loader`, or `SKILL.md`.
- **Evidence 2 (Hardcoded Prompt Strings):** Instead of consulting declarative skills, prompt templates are hardcoded directly into Python constants:
  - `_synthesize_clean_website` (lines 1445–1482 & 2469–2500): 38-line and 32-line hardcoded prompt strings.
  - `SECTION_PROMPT_TEMPLATE` (lines 1888–1941): 54-line hardcoded prompt template defining system identity and rules.
  - `RE_PROMPT_INSPECT` (lines 2588–2606): 19-line constant string defining persona and file inspection rules.
  - `RE_PROMPT_TAIL` (lines 2610–2623): 14-line constant string defining negative filters.
  - `RE_OUTPUT_CLAUSES` (lines 2626–2660): Format-specific code generation clauses.
  - `reverse_engineer_prompt()` (lines 2701–2720): Assembles the final string passed to the CLI binary.
- **Evidence 3 (Explicit Downstream Bypass Flags):**
  In `actions/website_cloner.py` (lines 2795–2811), the call to `antigravity_action` explicitly passes:
  ```python
  "prompt_mode": "verbatim",
  "skip_design": True,
  ```
  In `core/antigravity_runner.py` (lines 422–450), `skip_design: True` forces `is_ui = False`, which causes `resolve_design()` to be skipped entirely, and `prompt_mode: "verbatim"` causes `synthesize_prompt()` to be skipped entirely. The hardcoded Python string is executed directly by the `agy` CLI binary without consulting any design skill or blueprint.

### 4.3 Monolithic Action Duplication in Design Extraction
A 4,292-line Python pipeline (`actions/design_extractor.py`, `core/design_extractor.py`, `core/design_md_generator.py`, `core/master_template_builder.py`, `core/ai_design_generator.py`, `core/design_resolver.py`) implements deterministic HTML scraping, regex CSS variable parsing, color clustering, typography extraction, and YAML markdown generation in Python.
- **Evidence:** `skills/website_build/SKILL.md` (lines 125–182) already contains standard operating instructions for the LLM to inspect reference templates directly and extract design tokens. The 4,200+ lines of Python perform this procedurally before the AI agent ever receives the task.

### 4.4 Disconnected Sequential Batch Runner (`actions/run_tool_batch.py`)
`actions/run_tool_batch.py` (156 lines) provides a tool `run_tool_batch` that executes up to 10 sequential steps with regex variable substitution (`${steps.0.result}`) and circuit breakers.
- **Evidence:** `actions/run_tool_batch.py` imports only `ActionRegistry` (`core.action_loader`). It has **zero interaction** with `SkillRegistry` or declarative skills in `skills/`. It replaces LLM reasoning between steps with mechanical regex substitution.

### 4.5 YAML Frontmatter Schema Inconsistencies
The 11 packages in `skills/` follow three conflicting frontmatter schemas:
- **Missing Delimiters:** `skills/figma_helper/SKILL.md` has no `---` YAML delimiters. It starts directly with Markdown text, forcing `SkillRegistry` to fall back to directory name heuristics.
- **Nested `metadata` Dictionary:** 8 packages (`git_workflow`, `make_plan`, `multi_agent_collaboration`, `office_suite`, `social_research`, `test_fastapi_deploy`, `web_research_pipeline`, `web_scraper`) use a nested `metadata: {author: ..., version: ...}` block and omit `domain`, `triggers`, `tags`, and `auto_activate`.
- **Flat Fields:** Only 2 packages (`parallel_task_management`, `website_build`) declare top-level `author` and `version` fields. Only `website_build` defines `auto_activate: true`.

### 4.6 Template Count Discrepancy in `skills/website_build/SKILL.md`
- **Evidence:** `skills/website_build/SKILL.md` (lines 61–124) documents 5 scope directories (`1_landing_pages`, `2_business_sites`, `3_portfolios`, `4_dashboards`, `5_components`) and claims 23 production HTML templates exist.
- **Physical Reality:** The physical disk contains 4 directories (`1_landing_pages`, `2_portfolios`, `3_dashboards`, `4_components`) and exactly 20 HTML files, matching `skills/website_build/references/catalog.json`. Templates cited in Markdown text (`saas.html`, `clerk clone.html`, `nami landing page.html`) do not exist on disk.

### 4.7 Rule 4 Architectural Violation (Inline Skill Tools in `main.py`)
- **Evidence:** `AGENTS.md` Core Operating Rule 4 dictates: *"Every action tool must reside in its own file inside `actions/`... `main.py` only hosts inline tools tied directly to live session state (`screen_process`, `manage_monitor`, `shutdown_zezo`, `system_status`). All general tools belong in `actions/`."*
- **Violation:** `read_skill`, `list_skills`, and `save_learned_skill` are hardcoded directly inside `main.py` (lines 515–549, 1763–1786), bypassing `actions/` and `core/action_loader.py`.

### 4.8 API Friction Between Fleet Dispatcher and `SkillRegistry`
- **Evidence:** In `core/fleet/dispatcher.py` (lines 274–279):
  ```python
  skill_obj = getattr(skill_reg, "get_skill", lambda s: getattr(skill_reg, "_skills", {}).get(s))(sk)
  ```
  `SkillRegistry` in `core/skill_loader.py` does not provide a public `get_skill(name)` method. The fleet dispatcher relies on a fallback lambda that directly accesses the private dictionary `skill_reg._skills`.

### 4.9 Ghost Modules and Dead References
Prior audits and legacy documentation cited modules that do not exist:
- **`core/skills_registry.py`:** Does not exist on disk and has 0 git history commits. The actual registry is `core/skill_loader.py`.
- **`actions/execute_skill.py`:** Does not exist on disk and has 0 git history commits.
- **`actions/design_spec.py`:** Does not exist on disk (the implementation is `actions/design_extractor.py` and `core/design_*.py`).
- **`actions/code_review.py`:** Does not exist on disk. Code reviews are handled by fleet agent MICHAEL via `opencode_run` or `actions/ast_tool.py`.
- **`skills/website-cloner/`:** Does not exist on disk (the actual folder is `skills/website_build/`).

---

## 5. Evidence Summary

| Dimension | Verified Codebase Fact | Actual File Path & Line Reference |
| :--- | :--- | :--- |
| **Skill Registry Implementation** | `SkillRegistry` singleton class (598 LOC) | `core/skill_loader.py:145-588` |
| **Inline Tool Schema Declarations** | `read_skill`, `list_skills`, `save_learned_skill` | `main.py:515-549` |
| **System Prompt Skill Injection** | `format_prompt_block()` injected into Gemini config | `main.py:1535-1537` |
| **Inline Tool Execution Handlers** | `_handle_read_skill`, `_handle_list_skills`, `_handle_save_learned_skill` | `main.py:1763-1786` |
| **Security Scanning Heuristics** | Prompt injection, shell command, and obfuscation regexes | `core/skill_scanner.py:26-170` |
| **Fleet Skill Injection** | `[ACTIVE SKILL: <name>]\n<instructions>` prepended to task prompt | `core/fleet/dispatcher.py:268-284` |
| **Private Attribute Fallback** | Dispatcher accesses private `skill_reg._skills` via lambda | `core/fleet/dispatcher.py:274-279` |
| **Fleet Skill Configuration** | 9 fleet agents configured with `"allowed_skills"` arrays | `config/fleet_agents.json:23-301` |
| **REST API Endpoints** | `/api/skills`, `/api/skills/mode`, `/api/skills/install`, etc. | `core/ui_server.py:1328-1557` |
| **Frontend Settings Drawer** | React UI for skill state and prompt inspection (486 LOC) | `frontend/src/components/settings/SkillsSettingsTab.tsx` |
| **Physical Skill Package Count** | Exactly 11 folders containing `SKILL.md` | `skills/*` |
| **Ancillary Reference Assets** | 20 HTML reference templates and 1 `catalog.json` | `skills/website_build/references/*` |
| **Monolithic Cloner LOC** | 3,310 lines with 0 calls to `read_skill` or `SkillRegistry` | `actions/website_cloner.py:1-3311` |
| **Hardcoded Reverse Engineering Prompts** | `RE_PROMPT_INSPECT`, `RE_PROMPT_TAIL`, `SECTION_PROMPT_TEMPLATE` | `actions/website_cloner.py:1888-2623` |
| **Explicit Downstream Bypass Flags** | `prompt_mode="verbatim"` and `skip_design=True` | `actions/website_cloner.py:2804-2805` |
| **Coding Engine Bypass Execution** | `is_ui` set to `False`; `resolve_design()` and prompt synthesis skipped | `core/antigravity_runner.py:422-450` |
| **Design Extraction Monolith LOC** | 4,292 lines across 6 modules duplicating reference inspection | `actions/design_extractor.py`, `core/design_*.py` |
| **Sequential Batch Action** | 156 lines with regex variable replacement and 0 skill integration | `actions/run_tool_batch.py:1-156` |
| **Phantom / Ghost Modules** | `skills_registry.py`, `execute_skill.py`, `design_spec.py`, `code_review.py` | Verified 0 files on disk and 0 git commits |
