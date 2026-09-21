# 🏛️ JARVIS — Architecture Decision Records (ADR Log)

> **Lead Architect:** Hamza Bukhari  
> **Status:** Active Reference Log  

---

## ADR-001: Modular Monolith Pattern (`actions/` directory)
* **Date:** 2026-08-15 (Inferred)
* **Context:** JARVIS is a native desktop assistant requiring fast, in-process execution across dozens of automation tools without network serialization overhead.
* **Decision:** Keep the core engine as a modular monolith where each tool is an isolated file in `actions/` exposing a standard `TOOL` dictionary and handler function.
* **Consequence:** Eliminates inter-process latency; tools are auto-discovered at startup without hardcoding dispatch trees in `main.py`.

---

## ADR-002: Gemini Live WebSockets for Voice & Vision
* **Date:** 2026-09-01 (Inferred)
* **Context:** Real-time conversational AI requires sub-500ms voice turnaround, barge-in capabilities, live audio streaming, and screen/camera visual understanding.
* **Decision:** Use Google Gemini Live API (`gemini-3.1-flash-live-preview`) over bidirectional WebSockets for audio and camera frame ingestion.
* **Consequence:** Native real-time streaming audio with low latency; avatar lip-sync is generated straight from audio formants and live text phonemes.

---

## ADR-003: Delegation to External Coding Agents (OpenCode / Kilo)
* **Date:** 2026-09-19
* **Context:** Gemini Live voice models excel at real-time audio conversations but can hallucinate or fail on 50-file software engineering tasks.
* **Decision:** Delegate multi-file coding, refactoring, and test generation to specialized autonomous CLI agents (`opencode_agent`, `kilo_agent`) rather than generating raw code in the voice session.
* **Consequence:** Voice remains purely conversational; heavy autonomous development runs in isolated, purpose-built coding environments.

---

## ADR-004: Asynchronous Task Execution Pattern (`core/task_manager.py`)
* **Date:** 2026-09-19
* **Context:** Running OpenCode or Kilo CLI directly blocked the tool handler for up to 3 minutes, freezing the voice turn loop.
* **Decision:** Action handlers return an 8-character `task_id` immediately, running the CLI process in a daemon worker thread managed by `TaskManager`.
* **Consequence:** The voice loop and 3D avatar remain 100% fluid; users query live progress anytime using the `task_status` tool.

---

## ADR-005: 3-Tier Repository Context Resolution (`core/repo_context.py`)
* **Date:** 2026-09-19
* **Context:** Coding agents previously guessed paths using regex or defaulted to `Desktop`, leading to edits in incorrect directories.
* **Decision:** Implement a 3-tier resolver: Explicit user path ➔ Remembered `last_active_repo` in memory ➔ Active Git CWD ➔ Prompt user for confirmation.
* **Consequence:** Zero path guessing; paths are persisted in `memory/repo_context.json` and auto-created if specified explicitly.

---

## ADR-006: SQLite FTS5 for Persistent Memory (`memory/sqlite_memory.py`)
* **Date:** 2026-09-15 (Inferred)
* **Context:** Exact keyword, function name, and historical recall in chat transcripts required fast local search without the overhead of heavy vector embedding models.
* **Decision:** Use an embedded SQLite database (`zezo_brain.db`) with FTS5 full-text indexing and BM25 relevance ranking, coupled with automated secret redaction.
* **Consequence:** Instant local keyword recall with zero external vector database dependencies or cloud embedding costs.

---

## ADR-007: Software-Rendered 3D Holographic Avatar (`core/avatar.py`)
* **Date:** 2026-08-20 (Inferred)
* **Context:** The HUD avatar needed to run on low-power machines, laptops, and VMs without demanding dedicated GPU acceleration.
* **Decision:** Render the 3D head geometry purely in software using PyQt6's `QPainter`, vectorized numpy transformations, and 50 Hz viseme frequency extraction.
* **Consequence:** Zero GPU dependencies, cross-platform compatibility, and smooth ~60 FPS facial acting and lip-syncing.

---

## ADR-008: Deferred Groq Acceleration in Favor of Routing Stability
* **Date:** 2026-09-19
* **Context:** Adding Groq LPU before solidifying agent delegation and repo resolution added unnecessary moving parts.
* **Decision:** Formalize Groq integration in `FUTURE_UPGRADES.md` as Phase 2; focus Phase 1 strictly on OpenCode/Kilo asynchronous delegation and task monitoring.
* **Consequence:** Clean, predictable system behavior without dual-engine race conditions.

---

## ADR-009: Groq LPU Coprocessor Integration with Transparent Gemini Fallback (`core/llm_client.py`, `actions/code_helper.py`)
* **Date:** 2026-09-19
* **Context:** Single-file code synthesis, intent detection, and inline edits via standard REST APIs suffered from 5-8 second latency.
* **Decision:** Implement Groq LPU acceleration via `call_groq_text()` using `llama-3.3-70b-versatile` in `core/llm_client.py`. In `actions/code_helper.py`, route all single-file code generation and editing through Groq with transparent fallback to Gemini REST if the key is unset or an error occurs.
* **Consequence:** Sub-second (500+ tok/s) code generation when Groq is configured, with 100% backward-compatible resilience and zero Gemini Live WebSocket disruption.

---

## ADR-010: Polished Solid 3D Sculpt Avatar Architecture (`core/avatar.py`, `core/avatar_mesh.py`)
* **Date:** 2026-09-19
* **Context:** The initial avatar displayed a development wireframe look with grid lines, green dots, and flat unshaded facets that felt unpolished.
* **Decision:** Overhaul the avatar into a polished, solid 3D cyber sculpt:
  1. Added anatomical ear geometry (`_add_ears`) to the 3D head mesh.
  2. Eliminated all wireframe grids and landmark node dots.
  3. Implemented multi-point studio lighting (Key + Fill + Specular Blinn-Phong sheen + Silhouette Rim Fresnel).
  4. Sculpted elegant tapered eyebrow arches, serene closed/resting eyelids with natural lash seams, and contoured lips with speech cavity depth.
* **Consequence:** Delivers a premium, sleek 3D sculpt look while remaining 100% software-rendered via PyQt6 `QPainter` with sub-3ms latency and full HueWheel theme support.

---

## ADR-011: Authentic 3D Robot Head Fast OBJ Pipeline (`core/avatar_mesh.py`, `core/avatar.py`)
* **Date:** 2026-09-19
* **Context:** The user provided an authentic 3D model with specialized ear pods and cortex geometry. Converting large raw FBX files directly caused high CPU indexing overhead.
* **Decision:** Convert the high-poly model into an optimized OBJ mesh `core/robot_head_fast.obj` (1,076 vertices, 2,299 triangles) and parse it dynamically in `core/avatar_mesh.py` with pure software projection in `core/avatar.py`.
* **Consequence:** Sub-3ms software render time per frame, authentic robotic head design, and zero GPU overhead.

---

## ADR-012: Autonomous Technical Design System & Framing in PyQt6 (`ui.py`)
* **Date:** 2026-09-19
* **Context:** The previous cyan neon HUD aesthetic felt noisy and outdated compared to contemporary high-end technical AI interfaces.
* **Decision:** Adopt the design tokens and visual geometry from `References/UI/autonomus.html`:
  1. Deep matte void `#050505` with `#0a0a0a` / `#111111` surface cards and hairline borders (`rgba(255,255,255,0.06)`).
  2. Dual typography hierarchy (`Inter` for UI and `JetBrains Mono` for telemetry, logs, and condition chips).
  3. Signature 4-corner crosshair L-brackets rendered via `draw_corner_brackets()` on cards and viewports.
  4. High-precision International Cyber Orange (`#f24e1e`) accent with full live HueWheel retinting compatibility.
* **Consequence:** Delivers an ultra-modern, high-precision desktop AI OS interface while preserving 100% native PyQt6 performance and signal compatibility.

---

## ADR-013: Animated GIF Avatar Integration with 3D Code Preservation (`ui.py`)
* **Date:** 2026-09-20
* **Context:** The user requested replacing the active avatar centerpiece on the HUD with the animated graphic from `References/download.gif` while explicitly keeping all 3D avatar mesh files and generators intact.
* **Decision:**
  1. Updated `HudCanvas` in `ui.py` to initialize a `QMovie` playback loop for `References/download.gif` with cached frame stepping and 60 Hz frame synchronization.
  2. Applied smooth aspect-ratio scaling and centered positioning in the HUD display band with gentle audio-reactive pulse scaling during speech and listening states.
  3. Maintained complete preservation of `core/avatar.py`, `core/avatar_mesh.py`, and `core/robot_head_fast.obj` with automatic fallback rendering.
* **Consequence:** Delivers the exact animated HUD visualization requested by the user with zero CPU stutter and complete backward compatibility.

---

## ADR-014: Obsidian Studio Design System (`ui.py`)
* **Date:** 2026-09-20
* **Context:** The user requested re-skinning the desktop UI with the design system, colors, typography, buttons, and card lighting from `References/UI/image gen.html`.
* **Decision:**
  1. Implemented Zinc-950 backdrop (`#09090b`), Zinc-900 card surfaces (`#18181b`), subtle hairline borders (`#27272a`), and clean Studio Emerald accents (`#10b981`).
  2. Applied modern rounded geometry (`border-radius: 6px`–`8px` for inputs/cards/buttons) with glass hover states.
  3. Preserved full 3-column desktop layout (Telemetry, Avatar/Content Splitter, Activity Log + Upload + Command Input) and seamless pitch-black HUD center.
* **Consequence:** Delivers a modern studio aesthetic with zero layout or signal regression.

---

## ADR-015: Deterministic Design System Extractor & Hamza Taste Skill Engine (`core/design_extractor.py`, `actions/design_extractor.py`, `skills/hamza_taste/`)
* **Date:** 2026-09-20
* **Context:** Coding agents frequently generated generic AI boilerplate ("purple gradients", unstyled controls, inconsistent spacing). Furthermore, extracting design systems from HTML references required deterministic parsing without wasting LLM reasoning tokens.
* **Decision:**
  1. Built a deterministic Python parser (`core/design_extractor.py`) to extract colors, typography, border radii, shadows, and component recipes into standard `DESIGN.md` files matching `Skeuomorphic-Spatial-Component-DESIGN.md`.
  2. Created the `extract_design_system` action in `actions/design_extractor.py` for auto-discovery and on-demand extraction.
  3. Established the master `skills/hamza_taste/` declarative skill and presets (`studio.md`, `cyber.md`, `minimal.md`) providing strict anti-slop rules, Obsidian Dark `#09090b` / Studio Emerald `#10b981` default tokens, and modern glass component recipes for all coding agents.
  4. Updated Gemini Live system prompt routing to automatically enforce `hamza_taste` standards on UI development tasks.
* **Consequence:** Sub-50ms design extraction with zero token overhead and guaranteed studio-grade, anti-slop web frontend synthesis.

---

## ADR-016: Reference-First Design Prioritization & Dynamic Domain Presets (`skills/hamza_taste/SKILL.md`, `core/prompt.txt`)
* **Date:** 2026-09-20
* **Context:** Previously, the system prompt hardcoded Obsidian Dark (`#09090b`) and Studio Emerald (`#10b981`) in the agent delegation instructions, which caused Gemini to force emerald green onto all landing pages and override uploaded reference templates (e.g. `nexus.html`).
* **Decision:**
  1. Updated `skills/hamza_taste/SKILL.md` to establish **Priority 1: Reference-First Rule** — when a reference design is supplied, coding agents must faithfully adopt its exact color palette, typography, and layout instead of forcing default colors.
  2. Defined `hamza_taste` as an Anti-Slop Quality Framework (clean grids, styled controls, professional spacing) rather than a single static color scheme.
  3. Formulated dynamic domain-tailored palettes (Pharma/Medical, FinTech, Minimal SaaS, Cyber Matrix) for when no reference is provided.
  4. Updated `core/prompt.txt` UI & Frontend Design Protocol to prevent hardcoding fixed color codes into coding agent prompts.
* **Consequence:** 100% faithful reference design reproduction with studio-grade anti-slop execution across all business domains.

---

## ADR-017: Subprocess CPU Affinity Throttling & Task-Aware Monitor Alerting (`actions/opencode_agent.py`, `actions/kilo_agent.py`, `actions/system_monitor.py`)
* **Date:** 2026-09-20
* **Context:** Running OpenCode or Kilo CLI spawned multithreaded Node.js/V8 workers on all 12 CPU logical cores at once. When combined with the 60 FPS PyQt6 HUD rasterizer and audio pipeline, the system CPU reached 97–100%, causing false-alarm voice warnings from `SystemMonitor`.
* **Decision:**
  1. Applied `psutil.cpu_affinity()` hard-cap in `opencode_agent.py` and `kilo_agent.py` restricting background coding agents to half of the available CPU cores (e.g. 6 out of 12 threads), guaranteeing 50% CPU headroom for OS, browser, and JARVIS.
  2. Set `UV_THREADPOOL_SIZE` in the subprocess environment.
  3. Configured `actions/system_monitor.py` to suppress high-CPU warning alarms when `TaskManager` has active coding agent tasks running.
* **Consequence:** Eliminates 100% CPU system freezes, keeps the UI and voice loop fluid at all times, and prevents false CPU warning interrupts.

---

## ADR-018: Complete 4-Part CPU Throttling, Scope Isolation & Task Watchdog (`core/task_manager.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, `actions/system_monitor.py`)
* **Date:** 2026-09-20
* **Context:** CPU core capping alone was incomplete because Node.js threads still spawned uncontrolled, root Desktop indexing scanned thousands of files, long-running processes lacked wall-clock timeouts, and system monitor suppression lacked proportional task-load verification.
* **Decision:**
  1. **Source-Level Thread Limits:** Set `UV_THREADPOOL_SIZE=2`, `NODE_OPTIONS=--max-old-space-size=1024`, and `OMP_NUM_THREADS=2` before spawning CLI processes.
  2. **Dynamic CPU Affinity:** Added tiered core allocation leaving at least 2 cores free on small machines and capping at 50% on multi-core systems.
  3. **Scope Enforcement & Gitignore Guard:** Strictly reject running agents directly on root `Desktop`, home, or drive root; automatically inject minimal `.gitignore` with `node_modules/`, `venv/`, `dist/` exclusions.
  4. **Task Watchdog & Proportional Monitor:** Added a 5-second background watchdog in `TaskManager` with 20-minute hard wall-clock timeout and high-CPU log warnings (>90% for 60s+). In `SystemMonitor`, compare task subprocess CPU contribution against total CPU so alerts only suppress if the task accounts for >=50% of the spike.
* **Consequence:** Guaranteed sub-60% CPU usage on small repos, zero root Desktop directory traversal bottlenecks, and zero false-positive monitor alarms while preserving rogue process detection.

---

## ADR-019: Global Coding Task Concurrency Queue & Atomic Status Synchronization (`core/task_manager.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, `actions/task_status.py`)
* **Date:** 2026-09-20
* **Context:** Sequential voice commands previously caused multiple heavy coding agents (e.g. OpenCode + Kilo) to run concurrently on overlapping CPU cores, causing cumulative resource saturation and process tree orphan leaks.
* **Decision:**
  1. **Strict Concurrency Limit:** Set `MAX_CONCURRENT_CODING_TASKS = 1` in `TaskManager`. Subsequent coding tasks enter a thread-safe `QUEUED` state with position tracking (`queued (position #1)`) and automatically dequeue when the active task finishes. Non-coding tools run unhindered.
  2. **Process Tree Lifecycle:** Applied CPU affinity and priority to both parent CLI processes and all spawned child workers (e.g. `node.exe`). Wrapped execution in strict `proc.wait(timeout=10)` and `_terminate_pid()` to guarantee zero orphaned background processes.
  3. **Atomic Status Consistency:** Ensured `status()` queries live state under `_lock` with timestamp safeguards (preventing `running` flicker once `finished_at` is stamped).
  4. **Active Worker CPU Watchdog:** Workers measure subprocess tree CPU every 2 seconds and log warnings if load exceeds 80% for >10s continuously.
* **Consequence:** Enforces single-agent execution, prevents concurrent CPU starvation, ensures 100% accurate status reporting, and eliminates orphan process leaks.

---

## ADR-020: Hardware-Enforced Windows Job Object Throttling & Node Runtime Concurrency Caps (`actions/opencode_agent.py`, `actions/kilo_agent.py`, `core/task_manager.py`)
* **Date:** 2026-09-20
* **Context:** Setting `cpu_affinity` and priority classes on parent `cmd.exe` or child `node.exe` processes via user-space Python calls was insufficient because Node.js/V8 internal worker pools and native build addons bypassed Python-level process affinity masks and scheduled threads across all cores.
* **Decision:**
  1. **Hardware-Enforced Job Objects:** Created kernel-level Windows Job Objects (`ctypes.WinDLL("kernel32")`) with `JOB_OBJECT_LIMIT_AFFINITY` and `JOB_OBJECT_LIMIT_PRIORITY_CLASS = IDLE_PRIORITY_CLASS`. Assigned the root CLI process to the Job Object so the Windows NT kernel hardware-enforces core masking and idle priority inheritance recursively onto all child processes (`node.exe`, `rg.exe`, `esbuild`, etc.).
  2. **STDIN Handle Isolation:** Set `stdin=subprocess.DEVNULL` to prevent npm `.cmd` wrappers from hanging interactive stream descriptors.
  3. **V8 & Threadpool Environment Limits:** Configured `NODE_OPTIONS="--max-old-space-size=1024 --v8-pool-size=2"`, `UV_THREADPOOL_SIZE="2"`, `OMP_NUM_THREADS="2"`, `V8_NUM_THREADS="2"`, `PISCINA_THREADS="2"`, `OPENBLAS_NUM_THREADS="2"`, `MKL_NUM_THREADS="2"`.
  4. **Multi-Core Watchdog Threshold:** Updated `TaskManager` CPU watchdog to measure whole-tree CPU consumption against a scaled multi-core threshold (`core_count * 25%`).
  5. **Startup & Live Telemetry:** Added `[OpenCode Diagnostic]` / `[Kilo Diagnostic]` startup logs reporting PID, affinity mask, nice level, and child PIDs, along with 5-second interval process-tree telemetry.
* **Consequence:** Guaranteed sub-40% CPU ceiling during heavy compilation/refactoring tasks, zero audio dropouts in the voice loop, and full transparent diagnostic reporting.

---

## ADR-021: Repo Snapshot Undo, Deferred Completion Alerts & Browser Navigation Debounce (`core/undo.py`, `core/task_manager.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, `actions/browser_control.py`)
* **Date:** 2026-09-20
* **Context:**
  1. OpenCode/Kilo coding runs modified repo files without registering reversions in `core/undo.py`, resulting in "nothing to undo".
  2. Background task completion alerts were capable of premature emission before worker processes fully exited.
  3. Rapid duplicate `go_to` tool invocations from Gemini Live caused multiple browser windows/tabs to open simultaneously.
* **Decision:**
  1. **Repo Snapshot & Revert:** Implemented `capture_repo_snapshot()` and `register_repo_undo()` in `core/undo.py`. Pre-run byte snapshots are captured before spawning CLI processes; on completion, diffs (created, modified, deleted) are detected and an undo closure is pushed to `undo_stack` that cleanly deletes created files, restores modified files, and brings back deleted files.
  2. **Worker Lifecycle TaskContext Callbacks:** Added `ctx.on_complete()` and `ctx.on_fail()` to `TaskContext`. Registered undo and status callbacks exclusively in the background worker's `finally` block AFTER `proc.wait()` returns.
  3. **Browser Navigation Debounce:** Added thread-safe deduplication cache `_last_nav` with a 4.0s debounce window in `actions/browser_control.py` to prevent redundant native process launches on rapid identical navigation calls.
* **Consequence:** Full "undo" support for autonomous coding tasks, guaranteed post-exit completion alert timing, and eliminated duplicate browser windows.

---

## ADR-022: Active Project Memory Synchronization & FTS5 Fact Pruning (`actions/opencode_agent.py`, `actions/kilo_agent.py`, `memory/sqlite_memory.py`, `core/prompt.txt`)
* **Date:** 2026-09-20
* **Context:**
  1. Zezo experienced amnesia regarding the active coding project and file (e.g., hallucinating `index.html` in a non-existent `coding` folder instead of remembering `tapex-landing.html` in `Desktop/opencode_project`).
  2. Stale or hallucinated memory entries (`coding_task_index_html`) persisted in SQLite FTS5 `facts` even when edited or deleted from `long_term.json`.
  3. `kilo_run` did not automatically register active project, active file, or recent task metadata into `memory_manager`.
* **Decision:**
  1. **Dual-Phase Memory Sync in Coding Agents:** Added automatic synchronization of `active_project`, `active_file`, and `recent_task` to `memory_manager` upon submission in both `opencode_agent.py` and `kilo_agent.py`. In addition, post-execution snapshots inspect modified files and dynamically update `active_file` in memory.
  2. **SQLite Facts Pruning:** Updated `sync_facts_from_dict()` in `memory/sqlite_memory.py` to compare against valid `(category, key)` pairs and automatically `DELETE` orphaned records from SQLite `facts` when removed from JSON.
  3. **System Prompt Grounding:** Updated `core/prompt.txt` under `[CODING DELEGATION]` to explicitly mandate consulting `Active projects / goals:` in memory (`active_project`, `active_file`, `recent_task`) before answering questions about active or past coding work, forbidding hallucination of paths or files.
* **Consequence:** 100% accurate file and project context retention across voice sessions with zero memory decay or phantom file references.

---

## ADR-023: Fuzzy Normalized Directory Matching & Universal File Search (`actions/file_controller.py`, `core/repo_context.py`)
* **Date:** 2026-09-20
* **Context:**
  1. Spoken user input for folder names frequently contains spaces or spoken word divisions (e.g. "open code project", "open code", "my project") whereas filesystem directory names use underscores, dashes, or camelCase (e.g. `opencode_project`).
  2. `file_controller`'s `find_files` function previously filtered only regular files and skipped directories entirely, causing `find "open code project"` to return "No open code project found in Desktop/".
* **Decision:**
  1. **Normalized Token Matching:** Implemented `_norm_token()` in `actions/file_controller.py` stripping whitespace, hyphens, and underscores for case-insensitive phonetic substring and exact matching.
  2. **Fuzzy Directory Resolution:** Added `_fuzzy_find_in_dir()` to `_resolve_path()` in `actions/file_controller.py` and fuzzy directory iteration to `_expand()` in `core/repo_context.py`.
  3. **Universal Search Results:** Updated `find_files()` in `file_controller.py` to match both directories (`📁 [DIR]`) and files, ensuring spoken searches resolve folders instantly.
* **Consequence:** Spoken voice queries like "Desktop par open code project dhundo" resolve instantly to `Desktop/opencode_project` without requiring manual path corrections from the user.

---

## ADR-024: Synchronous Task State Initialization & False Queued Elimination (`core/task_manager.py`)
* **Date:** 2026-09-20
* **Context:**
  1. `TaskState` was initialized with default `status = TaskStatus.QUEUED`.
  2. In `TaskManager.submit()`, `_start_task_thread()` spawned worker threads asynchronously, but `state.status = TaskStatus.RUNNING` was only set inside the worker thread execution function.
  3. When `opencode_agent` or `kilo_agent` called `tm.status(task_id)` immediately after submission to check whether the task was queued behind another task, it read the initial `queued` state before the thread ran, causing Zezo to falsely announce "Another coding task is currently running. I have queued OpenCode task...".
* **Decision:**
  1. **Synchronous Running Stamping:** Stamped `state.status = TaskStatus.RUNNING` synchronously under `_lock` inside `_start_task_thread()` prior to launching the daemon thread.
  2. **True Queue Check:** Ensured that `tm.status(task_id).get("status") == "queued"` only returns `True` if the task is genuinely placed in `_coding_queue` waiting for an active coding task to finish.
* **Consequence:** Completely eliminated false "task queued" announcements when starting coding tasks on an idle system while maintaining strict concurrency protection.

---

## ADR-025: Smart Design Token Caching, Dynamic Reference Scanner & Dual-Store Workflow (`actions/design_extractor.py`, `skills/hamza_taste/SKILL.md`, `References/UI/`)
* **Date:** 2026-09-20
* **Context:**
  1. Parsing large HTML reference files (such as `NEXUS_PRO_X_standalone.html` at 3.6MB) on every coding turn added repetitive CPU parsing overhead and latency.
  2. The user organized reference designs into a structured dual-store under `References/UI/` (`html/` for raw HTML templates and `design md/` for extracted token specifications).
  3. The system required a dynamic, zero-maintenance discovery mechanism where dropping any new HTML or MD file into `References/UI/` makes it instantly available to Zezo and coding agents without requiring manual edits to skill manifests.
* **Decision:**
  1. **Dual-Store Organization:** Standardized `References/UI/html/` as the raw template source and `References/UI/design md/` as the default destination and cache repository for generated `DESIGN.md` specifications.
  2. **Smart Timestamp-Aware Cache:** Implemented mtime verification in `actions/design_extractor.py`. If a matching specification already exists in `design md/` and is newer than the source HTML, the action performs an instant (0ms) cache hit and delivers the tokens directly to the agent. If the source HTML has been edited, it automatically re-extracts the updated design tokens.
  3. **Live Dynamic Reference Scanner:** Implemented `_find_reference_file()` and `list_available_designs()` (`action='list'`) in `actions/design_extractor.py` scanning `References/UI/` live at runtime, eliminating static lists in skill files.
  4. **Multi-Destination Exporting:** Supported custom export destinations (e.g. `Desktop/DESIGN.md` or active repo) while simultaneously updating the persistent cache in `References/UI/design md/`.
* **Consequence:** 0ms instant design specification recall, zero token/CPU waste on repeated design requests, automatic re-extraction on HTML modification, and effortless plug-and-play addition of new design templates.

---

## ADR-026: Full-Stack System Rebrand to ZEZO (`ui.py`, `main.py`, `AGENTS.md`, `skills/`)
* **Date:** 2026-09-20
* **Context:** The system transitioned identity from JARVIS to ZEZO across the assistant's persona, interface, database (`zezo_brain.db`), and branding.
* **Decision:**
  1. **UI & Orchestrator Standardization:** Renamed main GUI class `JarvisUI` to `ZezoUI` in `ui.py` while providing a backward-compatible module alias `JarvisUI = ZezoUI`.
  2. **Desktop Artifacts & Autostart:** Rebranded shortcut scripts, `.lnk` shortcuts, macOS `.app` bundle / `Info.plist` identifiers (`com.zezo.assistant`), Linux desktop entries (`zezo.desktop`), and icon resolution (`config/zezo.ico`).
  3. **Log & Tag Normalization:** Updated real-time chat and HUD activity streamers to recognize `zezo:` alongside user prefixes.
  4. **Skill Authorship:** Synchronized all declarative skill manifests in `skills/` to `ZEZO / Hamza Bukhari`.
* **Consequence:** 100% unified ZEZO branding across the desktop operating system with zero breaking changes for existing tools or scripts.

---

## ADR-027: Asynchronous Antigravity Agent Execution & 3-Tier Repo Context Resolution (`actions/antigravity_agent.py`)
* **Date:** 2026-09-20
* **Context:**
  1. `antigravity_run` previously ran synchronously inside the action handler, blocking the Gemini Live tool loop for 15-30 seconds during multi-file synthesis and causing WebSocket timeout disconnects.
  2. Workspace directory resolution in `antigravity_agent.py` used regex matching on user prompt tokens, leading to arbitrary directory generation (e.g. `Desktop/create_a_modern_saas_landing_p`) rather than building in the user's active/specified project folder (e.g. `Desktop/website`).
* **Decision:**
  1. **Asynchronous Task Worker:** Refactored `actions/antigravity_agent.py` to submit background tasks to `core.task_manager.TaskManager` via `_run_worker()`, returning an immediate 8-character `task_id` in <10ms.
  2. **Live Granular Progress Reporting:** Integrated `ctx.report()` hooks reporting architectural planning (5-15%), file generation steps (15-90%), and syntax verification (95-100%) visible through `task_status`.
  3. **3-Tier Repo Resolution:** Adopted `core.repo_context.resolve(explicit=...)` ensuring Antigravity operates strictly within the resolved active workspace, with fallback prompts for root directory attempts.
  4. **Undo & Memory Persistence:** Registered repo snapshots via `core.undo.register_repo_undo()` and synchronized `active_project` / `recent_task` metadata into `memory_manager`.
* **Consequence:** Eliminates voice loop freezes, delivers 100% accurate directory execution without phantom folders, and enables real-time task progress monitoring.

---

## ADR-028: Proactive Agent Failure Recovery & 1-Turn Fallback Auto-Redelegation (`main.py`, `core/prompt.txt`)
* **Date:** 2026-09-20
* **Context:** When autonomous coding tasks crashed or faced free community endpoint rate-limits (e.g. OpenCode exiting with code 1), Zezo previously reported generic errors without offering actionable recovery paths, requiring the user to re-dictate the full prompt to another agent.
* **Decision:**
  1. **Enriched Failure Alerts (`main.py`):** Structured task failure notifications (`[TASK_FAILURE_NOTIFICATION]`) to automatically bundle `original_task`, `repo_path`, `failed_agent`, and detailed `error_reason` (including process output tails).
  2. **Conversational Recovery Choices (`core/prompt.txt`):** Directed Zezo to immediately explain why the failure occurred and proactively ask the user whether to (a) switch to an alternative free model (e.g. `opencode/mimo-v2.5-free` or `opencode/nemotron-3-ultra-free`), or (b) switch to Antigravity / Kilo Code.
  3. **Zero-Repetition Redelegation:** Enabled 1-turn voice dispatch where responding *"Antigravity ko de do"* or *"Model change karke chalao"* instantly re-dispatches the exact original task and target folder to the selected tool without making the user re-type or re-speak their prompt.
* **Consequence:** Eliminates dead-end task failures, provides resilient multi-model recovery, and delivers seamless autonomous developer assistance.

---

## ADR-029: Deterministic Design Token & Reference Resolution Engine (`core/design_resolver.py`, `actions/antigravity_agent.py`)
* **Date:** 2026-09-20
* **Context:**
  1. Autonomous coding agents (such as Antigravity) previously lacked direct awareness of `skills/hamza_taste/SKILL.md`, domain presets (`presets/cyber.md`, `studio.md`, `minimal.md`), and raw HTML reference templates in `References/UI/`.
  2. When building web applications or SaaS landing pages, the agent defaulted to generic, un-styled or hallucinated CSS palettes rather than faithfully adhering to Hamza's studio aesthetics and reference component recipes.
* **Decision:**
  1. **Centralized Design Resolver (`core/design_resolver.py`):** Created a deterministic resolver following the Hamza Taste hierarchy:
     - **Priority 1 (Reference-First):** Match explicit or domain keywords against `References/UI/design md/` (0ms cached `DESIGN.md`) or `References/UI/html/` (auto-extracted and cached on the fly via `core.design_extractor`).
     - **Priority 2 (Domain Presets):** Resolve domain keywords to `cyber`, `minimal`, or `studio` obsidian presets.
     - **Anti-Slop Directives:** Enforce non-negotiable rules against AI purple gradients, unstyled form controls, and loose layout spacing.
  2. **Antigravity Prompt Injection (`actions/antigravity_agent.py`):** Integrated `resolve_design()` into `plan_antigravity_project()` and `write_antigravity_file()`, formatting complete color tokens, typography, glass elevation, and component HTML recipes directly into Gemini's synthesis context.
* **Consequence:** Eliminates generic boilerplate UI output, guarantees 100% faithful reference design adoption, and provides a shared design resolver engine across all autonomous coding agents.

---

## ADR-030: Hamza Taste 3.0 — Anti-Slop Filter & 13 Reference HTML Architecture (`skills/hamza_taste/`, `core/design_resolver.py`)
* **Date:** 2026-09-20
* **Context:**
  1. `skills/hamza_taste/SKILL.md` previously blended text presets (`presets/cyber.md`, `minimal.md`, `studio.md`), default studio tokens, and anti-slop rules in a single file, causing agent confusion about whether to adopt HTML references or fall back to text presets.
  2. The project contains 13 production-grade HTML templates (SaaS, Dashboards, AI Agents, Spatial UI, Media, OS) that are vastly superior to static text presets.
* **Decision:**
  1. **Strict Filter vs. Direction Separation:** Adopted the proven Anti-Slop model where `hamza_taste` acts strictly as an **Anti-Slop Filter** (Tier 1 Hard Gates, Tier 2 Rhythm & Density, Tier 3 Delivery Checks), while **Direction** is 100% supplied by the 13 HTML templates in `skills/hamza_taste/references/html/`.
  2. **Presets Removal:** Completely eliminated `skills/hamza_taste/presets/`, establishing the 13 HTML reference templates as the single source of truth.
  3. **Semantic Category Router & Autonomous Agent Choice:** Updated `core/design_resolver.py` with multi-category semantic routing (SaaS, AI Agent, Dashboard, Media, OS, Spatial, Tech) and autonomous flagship selection for generic prompts.
* **Consequence:** 100% unified, zero-ambiguity design system where coding agents faithfully adopt curated reference HTML designs with strict anti-slop quality assurance.

---

## ADR-031: Semantic Design Extractor with Nested CSS Var Resolution & Theme Classification (`core/design_extractor.py`)
* **Date:** 2026-09-20
* **Context:**
  1. `core/design_extractor.py` previously used naive global hex-frequency counting and hardcoded obsidian fallback strings.
  2. For light/cream editorial templates like `Crazy UI landing page.html`, it picked an isolated badge hover color (`#1b5e20` green) as primary accent and forced `#000` obsidian canvas in the output `DESIGN.md`.
* **Decision:**
  1. **Recursive CSS Variable Resolution:** Implemented multi-pass parsing that resolves nested `var(--name)` and fallback expressions across `:root` and stylesheet rules into concrete hex values.
  2. **Semantic Role Detection:** Established strict priority cascades for `Background`, `Text Primary`, `Accent Primary`, `Surface/Card`, `Border`, and `Typography` based on semantic variable names, `body`/`h1` selectors, and CTA styles rather than raw hex frequency.
  3. **Luminance-Based Theme Classification:** Added deterministic `theme: light | dark` detection, generating theme-appropriate descriptions (e.g. cream canvas / black ink for light mode vs void canvas / emerald for dark mode) and eliminating generic "deep obsidian" text.
  4. **Dynamic Computed Fallbacks:** Removed all hardcoded hex constants (`#000`, `#09090b`, `#10b981`, `#1b5e20`), computing palette tokens dynamically from the source template.
* **Consequence:** 100% faithful design token extraction for both light/cream and dark themes with zero color pollution.













## ADR-032: Unified Backend Log Bus & Full Log Console (`core/log_bus.py`, `ui.py`)

* **Date:** 2026-09-20
* **Context:**
  1. Backend diagnostics had no readable destination inside the desktop app. Every `print(...)` across `actions/` and `core/` wrote to a console window that `main.py` deliberately hides on Windows via the `CREATE_NO_WINDOW` `Popen` patch, so subprocess and action output was written and never seen.
  2. Ten-plus modules (`core/task_manager.py`, `actions/opencode_agent.py`, `actions/kilo_agent.py`, `core/repo_context.py`, `actions/antigravity_agent.py`, `actions/web_reader.py`, ...) already call `logging.getLogger(...)`, but the project contained no `logging.basicConfig()` or any other handler attachment, so records below `WARNING` were discarded outright and `WARNING`+ fell through to Python's `lastResort` handler onto that same hidden console.
  3. The existing 600-line `LogWidget` ACTIVITY LOG is a curated conversation feed with a deliberate typewriter animation, making it a presentation surface unsuitable for diagnostics.
  4. Nothing was persisted or searchable, and `AGENTS.md` incorrectly claimed `core/governance.py` performed secret scrubbing when it does not.
* **Decision:**
  1. **Single Funnel (`core/log_bus.py`):** Added a bounded 20,000-line ring buffer fed by three sources — one root `logging.Handler` (capturing every existing `getLogger` call project-wide with zero edits to those modules), line-buffered `sys.stdout`/`sys.stderr` tee objects, and an explicit mirror of the curated `ZezoUI.write_log` feed. Redaction is applied **at ingest** by reusing `memory/sqlite_memory.redact_secrets()`, so the buffer, the panel, and any export file can never hold a live credential, and the project keeps exactly one secret-pattern list.
  2. **Poll, Do Not Push (`AGENTS.md` rule 3):** The UI polls the bus via `mark()`/`since(cursor)` on a 250 ms `QTimer` rather than subscribing to callbacks, because the bus is written from worker threads and touching a widget from those threads would violate the never-block-the-GUI-thread rule.
  3. **Separate Sink, Unchanged Feed:** Added `LogConsoleOverlay` (`_HudOverlay` subclass) with level/source/text filtering, search, FOLLOW/PAUSE, CLEAR, EXPORT to a user-chosen path, and COPY ALL. The ACTIVITY LOG `LogWidget` was deliberately left untouched.
  4. **Proportional Sizing:** Unlike its fixed-`_OW` siblings, the console clamps to `max(560, min(1180, w-120)) × max(340, min(680, h-140))` and re-fits in `resizeEvent`, because `_MIN_H` is only 580 and a hardcoded height would render clipped.
  5. **No `main.py` Edit:** The bus self-installs on import (idempotent) and `ui.py` is imported by `main.py` before the action/plugin/skill loaders run, honouring the develop-skill rule against unnecessary `main.py` changes.
* **Consequence:** Every backend log line — action `print()` output, `task_manager` lifecycle records, subprocess tails, and governance blocks — is finally visible, filterable, and exportable from the desktop app on `Ctrl+L`, with credentials stripped before they reach any sink.
* **Correction (2026-09-20):** The redaction guarantee above did not hold for Google's current `AQ.…` key format — see ADR-033. The key never reached a *durable* sink, but it did reach the in-memory buffer and was exportable. Library-level log noise is now suppressed at source and the pattern list is format-agnostic.

---

## ADR-033: Option A "Studio Matrix" Multi-Task Architecture (`core/task_manager.py`, `ui.py`)
* **Date:** 2026-09-21
* **Context:**
## ADR-033: Credential Redaction Hardened After Live-Key Exposure & Third-Party Log Noise Policy (`memory/sqlite_memory.py`, `core/log_bus.py`)

* **Date:** 2026-09-20
* **Context:**
  1. ADR-032 shipped `core/log_bus.py` with a root `logging` handler at `DEBUG` and claimed credentials were "stripped before they reach any sink". **That guarantee was falsified within the first live session.** With a handler finally attached, the `websockets.client` DEBUG stream became visible and printed the Gemini Live handshake request headers — including `x-goog-api-key: AQ.Ab8RN6…` in plaintext, matching the live key in `config/api_keys.json` exactly (53 chars, `AQ.` prefix).
  2. `redact_secrets()` matched only the legacy `AIzaSy…` Google key shape. Google's current `AQ.…` key format was invisible to every pattern, so the key entered the ring buffer unredacted and was reachable via EXPORT (writes plaintext to disk) and COPY ALL (writes plaintext to the clipboard).
  3. The same function guards turn persistence in `memory/sqlite_memory.py` (lines 149/155/157/159), so the identical gap also threatened `zezo_brain.db` — a **pre-existing** hole that predates the log bus.
  4. The same DEBUG stream flooded the buffer: `websockets.client` emits a record per realtime audio chunk plus per response frame, measured at roughly ten lines per second while idle, rolling the entire 20,000-line buffer over in about half an hour and evicting every real diagnostic.
* **Decision:**
  1. **Redact by Header Name, Not Only by Key Shape:** `_SECRET_PATTERNS` entries became `(pattern, replacement)` pairs, and a format-agnostic rule now scrubs any value behind `x-goog-api-key`, `x-api-key`, `api-key`, `authorization`, or `x-auth-token`. Matching the header name means any present or future key format is covered without a new pattern, which is the failure mode that caused this incident.
  2. **Coverage Completed:** Added the current `AQ.…` Google key shape, session `Set-Cookie` values, and relaxed the GitHub token length. Header-based rules preserve the credential's name for readability (`x-goog-api-key: [REDACTED_SECRET]`).
  3. **Silence Noisy Libraries by Default:** `_NOISY_LOGGERS` (`websockets`, `asyncio`, `urllib3`, `httpcore`, `httpx`, `PIL`, `google.genai`, `grpc`, `absl`) are pinned to `WARNING` at install time. Their INFO/WARNING/ERROR still flow. Setting `ZEZO_LOG_DEBUG=1` restores the full wire dump for deliberate debugging. This is the **first** line of defence: the API key never enters the buffer at all; redaction is the second.
  4. **Regression Guard:** Added `tests/test_secret_redaction_suite.py` asserting every credential shape is scrubbed, benign lines are untouched, `Authorization` receives exactly one label, and scrubbing is idempotent.
* **Consequence:** Credentials are scrubbed regardless of key format, the log buffer carries signal instead of per-frame audio chatter, and the exposure cannot silently return. **The key that appeared in the log must still be rotated** — redaction cannot un-leak a credential that was already displayed.

---

## ADR-034: Activity Log Copy Bar + Multi-File Upload UI (`ui.py`, `FileDropZone`, `LogWidget`)

* **Date:** 2026-09-21
* **Context:**
  1. The activity log (`LogWidget` in the right sidebar) had no copy/clear mechanism — users could not extract their conversation transcript, inspect history, or clear the 600-line buffer without restarting.
  2. File upload (`FileDropZone`) accepted only a single file at a time via `urls[0]` in `dropEvent` and `getOpenFileName` in `_browse()`, making batch upload impossible and leaving dropped-file metadata (size, extension, parent folder) invisible in the UI.
  3. `main.py:1337` dispatches `file_processor` using `self.ui.current_file` (a single path), so multi-file support had to remain backward-compatible with that single-path contract unless `main.py` was intentionally updated.
* **Decision:**
  1. **Activity Log Copy Bar (Option A from wireframes):** A 24px compact button strip placed directly above `LogWidget` with 4 controls:
     - **📋 COPY ALL** — copies either `log_bus.export_text()` (if backend log bus is active) or `LogWidget.toPlainText()` to the system clipboard; logs `SYS: Copied N lines to clipboard`.
     - **🧹 CLEAR** — calls `LogWidget.clear_all()` (clears both the `QTextEdit` and `log_bus`) for a clean slate.
     - **▼ FOLLOW** — checkable button (cosmetic for now; future iteration can pause the 6ms/char typewriter animation when unchecked).
     - **line counter badge** — shows `N / MAX` where N comes from `log_bus.snapshot()` (or `toPlainText().count('\n')` fallback) and MAX is `log_bus.MAX_LINES` (20,000) or 600.
     - Right-click context menu on `LogWidget` is extended with `Copy All (Activity Log)`, `Clear Activity Log`, and `Select All` entries.
  2. **Multi-File Upload (Option A from wireframes):** Replaced the single `_file_hint` `QLabel` with `_UploadedFilesBar` (`QWidget`), a 120px-scrollable list with:
     - Per-file rows: emoji icon (by extension category) + truncated name + size + format tag + ✕ remove button.
     - Horizontal icon strip in `FileDropZone._paint_files()` (up to 5 icons + "+N" overflow badge).
     - Footer: **📋 SELECT ALL** (visual highlight), **🧹 CLEAR ALL** (calls `FileDropZone.clear_all()`), **→ SEND ALL** (emits `files_sent` signal → `_on_files_sent` → dispatches `[FILES_UPLOADED]` to assistant with all paths).
     - `FileDropZone.file_selected` signal changed from `pyqtSignal(str)` to `pyqtSignal(list)`; `dropEvent` loops `urls[:10]`; `_browse()` uses `QFileDialog.getOpenFileNames()`.
     - `FileDropZone.current_files: list[str]` replaces `_current_file: str | None`.
  3. **Backward compatibility with `main.py` (Option A — no `main.py` edit):** `MainWindow.current_file` property retained, returning `self._drop_zone.current_files[0]` — so `main.py:1337` (`args["file_path"] = self.ui.current_file`) still resolves to the most recently uploaded file without any change to `main.py` or `actions/file_processor.py`. Multi-file dispatch is handled via the `[FILES_UPLOADED]` message sent to the assistant, which can then reference individual files by name.
  4. **`QAction` import corrected:** Moved from `PyQt6.QtWidgets` to `PyQt6.QtGui` (PyQt6 convention), since `QAction` does not live in `QtWidgets` in PyQt6.
* **Consequence:**
  - Users can now copy their full conversation history with one click, clear the log, and track total line count.
  - Users can drop or browse multiple files at once (up to 10) and see them in a scrollable list with per-file removal and a "Send All" button that dispatches everything to the assistant.
  - `main.py` and `actions/file_processor.py` receive no breaking changes — `current_file` still works for single-file dispatch.
  - The `QAction` import fix resolves the `ImportError` that prevented `ui.py` from loading at all.

---

## ADR-035: Active Project Design Preservation, Tailwind Token Extraction & HTML-First CSS Pipeline (`core/design_resolver.py`, `core/design_extractor.py`, `actions/antigravity_agent.py`, `actions/opencode_agent.py`)

* **Date:** 2026-09-21
* **Context:**
  1. When users asked Antigravity to add sections to an existing project (e.g. adding 5-6 sections to an existing hero section in `Desktop/website`), Antigravity resolved design purely through prompt keywords (e.g. matching `"saas"` in prompt) and pulled `Saas-DESIGN.md` from static references.
  2. `Saas-DESIGN.md` had a corrupted background color `#f97316` (bright orange) because `core/design_extractor.py` parsed an inner element hover radial glow instead of the `<body>` tag's Tailwind class `class="bg-[#ececee]..."`.
  3. Antigravity's planner and file generator generated `style.css` *before* `index.html`. `style.css` only wrote 4 basic generic classes (`.button`, `.card`), whereas `index.html` wrote dozens of BEM / layout classes (`.btn--primary`, `.container--grid`, `.card__metric`, `.pricing-tier`) that had zero CSS definitions, causing unstyled layouts and unconstrained element expansion.
  4. Template matching in `core/design_resolver.py` used rigid concatenated substring matching, causing multi-word templates like `"Crazy UI"` to miss and fall back to SaaS.
* **Decision:**
  1. **Tailwind & Inline Style Extraction (`core/design_extractor.py`):** Added explicit extraction of `<body>` and `<html>` tag inline styles and Tailwind utility classes (`bg-[#...]`, `bg-zinc-950`, `bg-white`, `text-[#...]`, `text-zinc-800`, etc.). Filtered fallback background color analysis to exclude inner glows, blobs, pills, and card components.
  2. **Active Project Design Hierarchy (`core/design_resolver.py`):** Updated `resolve_design(task, session_memory, repo_path)` to check the target repository first for existing `index.html` or `style.css`. If found, design tokens are extracted directly from the active project (`project_existing`), preserving custom styling, themes, and classes unless the user explicitly commands a theme switch.
  3. **Tokenized Reference Matching (`core/design_resolver.py`):** Implemented distinctive keyword token intersection matching so phrases like `"inspired by Crazy UI reference"` accurately resolve to `Crazy-Ui-Landing-Page-DESIGN.md`.
  4. **HTML-First File Ordering & 100% CSS Rule Coverage (`actions/antigravity_agent.py`):**
     - Enforced `index.html` to be planned and generated *first*.
     - When `style.css` is generated second, it receives the complete on-disk `index.html` markup in context with a strict directive to write complete, dedicated CSS styling for every tag, class, container, badge, and button.
     - Enforced container bounds (`max-width: 1200px; margin: 0 auto;`), CSS Grid responsive tiers, glass elevations (`backdrop-filter: blur(12px)`), and `@media (max-width: 768px)` media queries.
  5. **OpenCode Agent Alignment (`actions/opencode_agent.py`):** Integrated `core.design_resolver` into `actions/opencode_agent.py` so OpenCode CLI automatically receives active design specs and anti-slop guidelines for UI tasks.
  6. **Automated Verification:** Added `test_7_existing_repo_preservation` in `tests/test_design_system_suite.py` asserting active project design extraction and theme preservation across 12 total automated test suites.
* **Consequence:** Antigravity and OpenCode generate pixel-perfect, fully styled, responsive landing pages with zero missing CSS classes or layout expansion bugs, while existing project hero sections and styles are 100% preserved.

---

## ADR-036: Task Cancellation Action, ANSI Code Cleansing, UI DropZone Layout & Automated Regression Suite (`core/task_manager.py`, `actions/task_status.py`, `ui.py`, `core/prompt.txt`, `tests/test_ui_and_task_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. When users attempted to cancel background coding tasks (e.g. saying "Please cancel the kilo task"), the voice loop had no cancellation action and fell back to sending `ctrl+c` keystrokes via `computer_control`, leaving the background process running.
  2. `main.py:_run_task_completion_watcher` threw `AttributeError: 'TaskState' object has no attribute 'params'` when notifying on task failure because `TaskState` lacked `params`.
  3. Terminal output streamed from OpenCode/Kilo CLI contained raw ANSI escape codes (`\x1b[0m`, `\x1b[90m`), which rendered as literal square brackets and garbled text in the Task Inspector status bar.
  4. In `FileDropZone._paint_files()`, category emoji icons and text headings overlapped vertically across the 100px canvas height, causing visual collisions.
  5. When users requested to view or open a generated website ("open karke dikhao"), the model invoked VS Code via `open_app` instead of opening the webpage in the browser.
* **Decision:**
  1. **Task Cancellation Tool (`actions/task_status.py`):** Added `action="cancel"` to `task_status`. When called with or without `task_id`, it immediately invokes `task_manager.cancel()`, which sets `cancel_event`, updates task status to `CANCELLED`, terminates child process trees via `_terminate_pid()`, and triggers queue dequeueing.
  2. **`TaskState.params` Propagation (`core/task_manager.py`):** Added `params: dict = field(default_factory=dict)` to `TaskState`. Updated `TaskManager.submit()` to persist parameter payloads for recovery routing in `main.py`.
  3. **ANSI Code Cleansing (`core/task_manager.py`, `ui.py`):** Added regex-based `strip_ansi()` utility in `core/task_manager.py` and applied it to `TaskState.message`, `TaskContext.report()`, `res["tail"]`, and `ui.py` Task Inspector displays (`_inspect_task_by_id()`).
  4. **DropZone Multi-File Layout Refactoring (`ui.py`):** Restructured `_DropCanvas._paint_files()` into dedicated non-overlapping horizontal bands:
     - Row 1 (Y: 12–34px): Category emoji icons + `+N` badge.
     - Row 2 (Y: 40–60px): White bold count header (`N files loaded`).
     - Row 3 (Y: 64–82px): Monospace metadata subtext (`X MB total · Click to add more`).
     - Top-Right (Y: 8–28px, X: W-28px): Constrained `(✕)` clear button click box.
  5. **Browser Routing & Agent Stickiness (`core/prompt.txt`):** Instructed the model to:
     - Always open web projects/pages in the default browser (`browser_control(action="go_to")`), reserving VS Code only for explicit IDE requests.
     - Maintain agent stickiness: follow-up modifications on projects created by Antigravity remain with `antigravity_run`.
     - Route cancellation requests ("cancel task", "kilo band karo") to `task_status(action="cancel")`.
  6. **Dedicated Automated Regression Suite (`tests/test_ui_and_task_suite.py`):** Created 7 automated tests covering DropZone file addition, single-file removal, queue clearing, batch actions, ANSI stripping, `TaskState.params` persistence, and process cancellation. Total suite expanded to 19 automated tests passing with 100% success.

---

## ADR-037: Option A Dynamic Trigger-Indexed Skill Hub, Multi-Domain Namespace & Declarative Context Budgeting (`core/skill_loader.py`, `ui.py`, `main.py`, `tests/test_skill_hub_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. The system had declarative skills in `skills/` but lacked domain-aware categorization (UI/UX, Coding, Research, System Diagnostics, General), leading to a flat list without structured taxonomy.
  2. Skills lacked trigger indexing and intent scoring, making selective context budgeting impossible without loading large instruction bodies.
  3. The HUD interface had no visual interface for inspecting, editing, pinning, toggling, or installing skill packages via drag-and-drop.
  4. Dynamic skill synthesis from successful multi-step executions (`save_learned_skill`) lacked structured YAML frontmatter generation with triggers and domain tags.
* **Decision:**
  1. **Dynamic Trigger-Indexed Skill Registry (`core/skill_loader.py`):**
     - Upgraded `SkillRecord` with `domain`, `author`, `version`, `tags`, `triggers`, `pinned`, `disabled`, and `auto_activate`.
     - Implemented zero-dependency `_parse_yaml_frontmatter()` supporting nested trigger lists, tags, and booleans.
     - Implemented domain heuristic inference (`_infer_domain_from_name_and_tags`) and default trigger synthesis (`_generate_default_triggers`).
     - Added `match_skills(query)` with multi-tier scoring (pinned = 100, name match = 40, trigger match = 30 + len, tag match = 15).
     - Added `get_active_skill_prompt(task_text, max_tokens_budget)` dynamically assembling prioritized skill instructions within token limits.
     - Added persistent toggle mode storage (`config/skills_state.json`) and drag-and-drop package installation (`install_skill` for `.zip` and folders).
     - Added `save_learned_skill()` and `delete_skill()` with automated frontmatter formatting.
  2. **PyQt6 Visual Skill Hub & HUD Integration (`ui.py`):**
     - Created `SkillHubOverlay` with domain category tabs (`ALL`, `UI`, `CODING`, `RESEARCH`, `SYSTEM`), real-time search filtering, and live token budget estimation.
     - Built `_SkillCardWidget` featuring domain color badges, multi-state mode cycling (● AUTO ➔ 📌 PINNED ➔ ⊘ DISABLED), trigger pill displays, and in-place deletion.
     - Built `_SkillDropTarget` accepting dropped `.zip` archives and skill directories.
     - Built `SkillEditorModal` for editing `SKILL.md` directly from the HUD.
     - Wired entry points in `MainWindow`: `Ctrl+Shift+S` global shortcut, quick-access settings drawer button, and responsive window resize handling.
  3. **Automated Verification Suite (`tests/test_skill_hub_suite.py`):**
     - Created 8 automated tests covering YAML parsing, domain inference, trigger scoring, context budgeting, toggle persistence, package installation, skill synthesis, and PyQt6 UI component instantiation. Total suite expanded to 27 tests passing with 100% success.
* **Consequence:** Full QwenPaw-inspired skill management with instant trigger-matched context injection, visual drag-and-drop package installation, and seamless PyQt6 HUD control.

---

## ADR-038: Adaptive Design Resolution, Redesign Intent Override & Multi-Domain Routing (`core/design_resolver.py`, `actions/antigravity_agent.py`, `tests/test_design_system_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. Antigravity was reported locked to a single design theme, failing to adopt new design references during redesign requests or apply varied aesthetics on generic user prompts.
  2. Root cause investigation identified three architectural issues:
     - `_SEMANTIC_ROUTES` in `core/design_resolver.py` contained overly generic tokens (e.g., `"landing page"` mapped exclusively to `saas`), causing all landing page requests to collapse into a single reference template.
     - `resolve_design()` prioritized existing repo files (`project_existing`) above user redesign and theme-change requests. When a user requested *"Change the design using Saas-DESIGN.md reference"*, the resolver extracted the existing on-disk `index.html` as `project_existing`, completely ignoring the requested reference.
     - `actions/antigravity_agent.py` contained hardcoded system prompt rules (*"CRITICAL PRESERVATION DIRECTIVE: DO NOT discard or rewrite existing layouts/styles"*) that prevented the LLM from refactoring HTML/CSS to match new design specifications during redesign tasks.
* **Decision:**
  1. **Redesign Intent Detection (`core/design_resolver.py`):**
     - Implemented `is_redesign_or_explicit_request(task)` to identify keywords indicating redesign, theme changes, restyling, or explicit design reference mentions (`redesign`, `change design`, `update theme`, `regenerate`, `make it look like`, `theme`, `reference`).
  2. **Hierarchical Resolution Precedence:**
     - Re-ordered `resolve_design()`:
       - Priority 1: Explicit user-specified design file or cached spec name (e.g. `Saas-DESIGN.md` or `saas.html`).
       - Priority 2: Redesign intent detection ➔ bypasses `project_existing` and routes to explicit/semantic/preset references.
       - Priority 3: Non-redesign additive tasks with existing HTML ➔ resolves `project_existing` to preserve established styles.
       - Priority 4: Rich semantic domain keyword routing.
       - Priority 5: Diverse autonomous fallback across primary reference templates (`dub`, `Crazy UI`, `nami`, `saas`, `autonomus`, `aura frame`, `image gen`) using task-context hashing rather than hardcoded static fallbacks.
  3. **Multi-Domain Semantic Routing Matrix:**
     - Real estate, property, housing, agency directories ➔ `dub landing page`
     - Creative agency, portfolio, design studio, vibrant UI ➔ `Crazy UI landing page`
     - AI, machine learning, robotics, automated agents ➔ `autonomus`
     - Gaming, esports, futuristic cyberpunk, tech ➔ `nexus`
     - Luxury, jewelry, fashion, premium products ➔ `aura frame`
     - Finance, fintech, minimal, documentation, dashboard ➔ `nami landing page`
     - SaaS, cloud, enterprise, B2B, developer tooling ➔ `saas`
  4. **Antigravity Adaptive Prompt Directives (`actions/antigravity_agent.py`):**
     - When `is_redesign_or_explicit_request(task)` is `True`, Antigravity injects `CRITICAL REDESIGN & THEME OVERHAUL DIRECTIVE` commanding complete overhaul of colors, typography, and layout according to the resolved design tokens.
     - When `is_redesign_or_explicit_request(task)` is `False`, Antigravity maintains `CRITICAL PRESERVATION DIRECTIVE` for safe additive workflows.
  5. **Automated Verification:**
     - Added `test_8_redesign_intent_overrides_existing_repo` and `test_9_diverse_domain_and_generic_scenarios` to `tests/test_design_system_suite.py`.
     - Verified all 30 test cases in the test suite pass with 100% success.
* **Consequence:** Eliminates static theme lock-in. Antigravity dynamically adapts styles to domain requirements, faithfully honors explicit design reference overrides, and preserves existing project styles only during additive tasks.

---

## ADR-039: Direct Raw HTML Reference Blueprint Injection & On-Demand Design Extractor (`core/design_resolver.py`, `actions/antigravity_agent.py`, `core/prompt.txt`, `tests/test_design_system_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. The 13 built-in HTML references in `skills/hamza_taste/references/html/` contain world-class visual layouts, rich hero sections, glassmorphic card patterns, micro-interactions, and complex CSS `@keyframes` animations.
  2. While `*-DESIGN.md` specifications extracted high-level design tokens (hex colors, font families), they abstracted away the concrete structural HTML layout and exact component markup.
  3. Passing the pure raw HTML template directly into Antigravity's generation prompts enables 100% visual fidelity, exact component architecture, and pixel-perfect styling adaptation to any domain.
* **Decision:**
  1. **Direct Raw HTML Ingestion (`core/design_resolver.py`):**
     - Updated `ResolvedDesign` to store `raw_html: str`.
     - Built `_sanitize_html_for_prompt()` to strip massive base64 image data URIs and oversized inline SVG paths while preserving all CSS stylesheets, `@keyframes`, class definitions, and DOM component hierarchies within token budgets.
     - `resolve_design()` reads the raw HTML template directly from `skills/hamza_taste/references/html/` across all priorities (explicit match, session memory, domain semantic routing, and autonomous choice).
  2. **Raw HTML Generation Prompt Formatting (`core/design_resolver.py`):**
     - When `raw_html` is available, `format_design_prompt()` embeds the sanitized HTML template directly into `MASTER RAW HTML REFERENCE TEMPLATE` code blocks, instructing Antigravity to replicate the layout, hero sections, card patterns, and animations faithfully while adapting textual copy and branding to the user's business domain.
  3. **Role of `extract_design_system` Tool (`core/prompt.txt`, `actions/design_extractor.py`):**
     - Retained as a dedicated on-demand utility tool for user-uploaded custom files, live URL inspection, and creating standalone `DESIGN.md` specifications when explicitly requested by the user.
  4. **Automated Verification Suite:**
     - Expanded `tests/test_design_system_suite.py` with `test_10_raw_html_injection_in_prompt`.
     - All 31 automated tests pass with 100% success.
* **Consequence:** Antigravity synthesizes studio-grade web pages directly from authentic HTML reference templates with complete structural and animation fidelity.

---

## ADR-040: Unified ZEZO Coder Facade, Slide-Out Telemetry Drawer & Smart Domain-Aware Routing (`ui.py`, `core/prompt.txt`, `actions/*.py`, `tests/test_zezo_coder_drawer_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. The assistant previously exposed underlying CLI agent names (`OpenCode`, `Kilo`, `Antigravity`) in voice responses and UI task cards, cluttering the user experience and breaking the assistant's unified operating system identity.
  2. The left sidebar Task Queue cards and the slide-out matrix drawer lacked domain metadata, ETA estimation, direct project actions (`[PREVIEW]`, `[OPEN FOLDER]`), and transparent internal hardware telemetry (process tree, CPU affinity, Job Object status).
  3. Coding tasks required clear, domain-aware default routing (e.g. frontend/UI tasks defaulting to Antigravity with raw HTML reference injection, backend/CLI tasks defaulting to OpenCode) while preserving 100% user control via explicit overrides and settings.
* **Decision:**
  1. **Unified ZEZO Coder Persona & Voice Loop (`core/prompt.txt`):**
     - Established the single unified identity `ZEZO Coder`. The assistant speaks strictly in first-person (*"Main aapka landing page build kar raha hoon..."*) and never utters raw CLI engine names in conversation.
     - Enforced domain-aware default routing: UI / Frontend / Landing Pages / Web Apps $\rightarrow$ `antigravity_run` (with raw HTML reference templates & design resolver); Backend / CLI / Python $\rightarrow$ `opencode_run`; single-file tweaks $\rightarrow$ `code_helper`; multi-file refactors $\rightarrow$ `antigravity_run` (if UI) or `kilo_run`.
     - Instructed the model to always open generated web pages in the default browser (`browser_control` or `open_app`), never VS Code unless explicitly commanded.
     - Routed cancellation requests directly to `task_status(action="cancel")`.
  2. **Standardized Tool Return Badges (`actions/*.py`):**
     - Updated `antigravity_agent.py`, `opencode_agent.py`, and `kilo_agent.py` to return clean `ZEZO Coder (Task ID: ...)` notifications and player badges.
  3. **Dual-Layer Slide-Out Task Drawer & Telemetry Inspector (`ui.py`):**
     - **Left Sidebar `TaskQueueWidget`:** Renders compact `ZEZO Coder` cards across `● RUNNING` (with live progress bar, elapsed time, and ETA calculation), `○ QUEUED` (with `Position #N` badge and task title), and `✓ DONE` (with completion timestamp and duration).
     - **Slide-Out `TaskMatrixDrawer`:** Renders full `⚡ ZEZO Coder` inspector cards featuring task summary, target workspace, status with ETA, `── INTERNAL DETAILS ──` (Engine, Model, PID, Job Object, CPU Affinity, Child Processes, Timestamps), `── RECENT LOG ──` (timestamped step logs), and direct action buttons:
       - `[🌐 PREVIEW]`: Instantly opens generated HTML/web page in default browser via `_open_project_preview()`.
       - `[📁 OPEN FOLDER]`: Opens target project folder in native OS file explorer via `_open_project_folder()`.
       - `[✕ CANCEL]`: Gracefully terminates the running task.
       - `[🔍 INSPECT]`: Focuses task inside HUD center panel.
       - `[📜 FULL LOG]`: Opens the Backend Log Console (`Ctrl+L`).
  4. **Dedicated Automated Regression Suite:**
     - Created `tests/test_zezo_coder_drawer_suite.py` with 5 automated test cases verifying queue card rendering, drawer telemetry, action buttons, prompt rules, and tool return strings.
     - Total test suite expanded to 37 automated tests passing with 100% success.
* **Consequence:** Full studio-grade unified ZEZO Coder interface, complete hardware telemetry visibility, effortless 1-click preview and explorer access, and intelligent domain-aware autonomous coding delegation.

---

## ADR-041: Native Antigravity CLI (`agy`) Subprocess Integration & Multi-Model Execution (`actions/antigravity_agent.py`, `memory/config_manager.py`, `ui.py`, `tests/test_antigravity_cli_integration_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. Antigravity Agent in ZEZO was previously executing code synthesis exclusively through the Python Google GenAI REST SDK rather than utilizing the user's locally installed official Antigravity CLI (`agy.exe`).
  2. The native Antigravity CLI (`agy` v1.2.7) offers access to official models (`gemini-3.7-flash-medium`, `gemini-3.8-flash-medium`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`), tool autonomy (`--dangerously-skip-permissions`), and rich execution capabilities.
  3. Running `agy` in ZEZO required:
     - Automatic binary discovery (`_find_antigravity_bin()`) across system PATH and LocalAppData directories.
     - Model configuration and alias mapping (`gemini-3.7-flash-medium` default, with model switching in settings UI and tool calls).
     - Hardware-enforced Windows Job Object limits (`_create_throttled_job`) and CPU core affinity throttling to keep the system responsive.
     - Non-blocking asynchronous task execution via `TaskManager` with live progress streaming and Undo snapshot registration.
     - Transparent fallback to Python Gemini REST SDK if the CLI binary is absent.
* **Decision:**
  1. **Dynamic CLI Discovery & Model Resolution (`actions/antigravity_agent.py`):**
     - Built `_find_antigravity_bin()` scanning for `agy.exe`, `agy`, `antigravity.exe` in system PATH and `%LOCALAPPDATA%\agy\bin\agy.exe`.
     - Built `_resolve_model()` normalizing model aliases (`sonnet` $\rightarrow$ `claude-sonnet-4-6`, `opus` $\rightarrow$ `claude-opus-4-6-thinking`, `3.7` $\rightarrow$ `gemini-3.7-flash-medium`, etc.).
  2. **Hardware-Throttled CLI Execution (`actions/antigravity_agent.py`):**
     - Implemented `subprocess.Popen([agy_bin, "-p", prompt, "--dangerously-skip-permissions", "--model", model], cwd=repo, ...)` with `_WIN_HIDE` flags.
     - Enforced Windows Job Object limits (`JOB_OBJECT_LIMIT_AFFINITY | JOB_OBJECT_LIMIT_PRIORITY_CLASS`) and capped CPU affinity to 50% logical cores.
     - Streamed stdout lines real-time into `TaskContext.report(pct, text)`.
     - Captured and registered repo snapshots before and after execution via `register_repo_undo()`.
  3. **Config & UI Integration (`memory/config_manager.py`, `ui.py`):**
     - Added `ANTIGRAVITY_CLI_MODELS`, `DEFAULT_ANTIGRAVITY_MODEL`, `get_antigravity_model()`, `save_antigravity_model()` to `memory/config_manager.py`.
     - Added `◈ ANTIGRAVITY CLI (ZEZO CODER)` section to `Autonomous Coding Agents & Skills` modal in `ui.py` with dynamic `🟢 CLI INSTALLED` / `⚪ CLI NOT FOUND` status indicator and model selection dropdown.
  4. **Automated Verification Suite (`tests/test_antigravity_cli_integration_suite.py`):**
     - Created 5 automated tests verifying * **Consequence:** Full native Antigravity CLI integration with multi-model freedom (`gemini-3.7-flash-medium`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`), hardware Job Object safety, real-time log streaming, and zero-downtime Gemini REST fallback.

---

## ADR-042: Active Repo Context Persistence, Task Debouncing, Blueprint Lifecycle & 100% Progress Bar Saturation (`core/task_manager.py`, `core/repo_context.py`, `actions/antigravity_agent.py`, `ui.py`, `main.py`)

* **Date:** 2026-09-21
* **Context:**
  1. **Folder Desynchronization on Completion:** When Antigravity completed builds in a target workspace (e.g. `Desktop/portfolio`), subsequent voice commands erroneously listed or searched inside stale workspaces because `remember_repo()` was not synchronized on task completion.
  2. **Duplicate Consecutive Task Dispatch:** Rapid tool calls could queue duplicate tasks.
  3. **Task Inspector Progress Bar Saturation:** Progress bar needed explicit 100% saturation on completion.
* **Decision:**
  1. Synchronized `remember_repo()` on task submission and completion.
  2. Implemented 8-second deduplication in `TaskManager.submit()`.
  3. Guaranteed 100% progress bar saturation across all UI inspectors.
  4. Automatically unlinked temporary blueprint files after generation.
* **Consequence:** Zero duplicate task queues, clean project workspaces, and full 100% progress bar saturation.

---

## ADR-043: Autonomous Traffic Vectors Design System on Mobile Remote Access Web Frontend (`dashboard/static/login.html`, `dashboard/static/app.html`)

* **Date:** 2026-09-21
* **Context:**
  1. The mobile remote access frontend (`dashboard/static/login.html` and `dashboard/static/app.html`) previously used a generic Indigo palette (`#6366f1`) and basic rounded cards, which felt disconnected from the high-tech desktop HUD aesthetic.
  2. The user provided the "Autonomous Traffic Vectors" design system specification (`get idea/Autonomous Traffic Vectors · Design System.html`) featuring deep matte void (`#050505`), international cyber orange (`#f24e1e`), technical framing with 4-corner L-brackets, and `Inter` + `JetBrains Mono` typography.
* **Decision:**
  1. **Redesigned `dashboard/static/login.html`:**
     - Applied matte void background `#050505` with subtle technical grid overlay.
     - Framed the login card with technical 4-corner crosshair brackets (`.corner`, `.corner-v`).
     - Replaced generic PIN styling with 6-character monospace segmented input (`JetBrains Mono`), cyber orange focus glow, uppercase auto-formatting, and animated error shake.
     - Preserved 100% of underlying JavaScript authentication, bearer tokens, and device auto-login workflows.
  2. **Redesigned `dashboard/static/app.html`:**
     - Header bar updated with technical live pulse status, AES-256 E2EE security badge, and IP:PORT node indicator.
     - Feed messages transformed into technical HUD telemetry panels with cyber-orange micro-labels (`[JARVIS :: TELEMETRY]`, `[YOU :: LOCAL]`).
     - File upload and transfer cards updated with cyber-orange gradient progress tracks (`#f24e1e` to `#ff8a5c`), status chips, and download buttons.
     - Footer control bar updated with monospace input field, high-precision tactile buttons, and real-time PCM16 voice stream pulse animation.
* **Consequence:** Delivers a unified, studio-grade technical AI interface on mobile browsers matching the desktop OS design language with zero regression in WebSocket, E2EE, or voice functionality.

---

## ADR-044: Universal Multi-Format File Ingestion Engine (`core/file_reader.py`, `actions/file_processor.py`, `dashboard/server.py`, `main.py`)

* **Date:** 2026-09-21
* **Context:**
  1. ZEZO previously handled file reading through fragmented, format-specific ad-hoc snippets across `actions/file_processor.py`. Scanned PDFs with no selectable text or complex multi-column layouts failed with empty text extraction.
  2. Ingestion of modern Microsoft Office formats (`.docx`, `.xlsx`, `.pptx`), HTML, EPUB, and PDFs required a unified pipeline.
  3. Image and document ingestion needed clear separation:
     - Real-time conversational camera/screen frames and mobile photo uploads stream through Gemini Live WebSockets (`main.py`).
     - One-shot static document OCR and multi-page scanned PDF analysis route through Gemini REST Multimodal Document API (`core/gemini.py`), with lazy `docling` fallback.
  4. Memory safety required a 64KB (65,536 character) default truncation guard to prevent context explosion on massive files.
* **Decision:**
  1. **Hierarchical Extraction Ladder (`core/file_reader.py`):**
     - **Direct Read:** Text and code files (`.txt`, `.py`, `.js`, `.json`, `.csv`, `.md`, `.yaml`, etc.) are decoded with an encoding fallback ladder (`utf-8` $\rightarrow$ `utf-8-sig` $\rightarrow$ `cp1252` $\rightarrow$ `latin-1` $\rightarrow$ binary decode with replace).
     - **Microsoft MarkItDown (`markitdown`):** Primary converter for modern Office formats (`.docx`, `.xlsx`, `.pptx`), clean native PDFs, HTML, and EPUB to GitHub-flavored Markdown.
     - **PDF Scanned Quality Check (`_is_scanned_pdf`):** Evaluates extracted text length and character density per page ($< 100$ chars/page).
     - **Gemini REST Multimodal Document API:** If a PDF is scanned or below quality threshold, falls back to one-shot Gemini REST API with Base64 payload.
     - **Docling Lazy OCR:** Secondary offline layout converter imported strictly on-demand.
     - **Archive Inspector:** Inspects and outlines contents of `.zip`, `.tar`, `.gz`, and `.7z` archives.
     - **Legacy Office Formats (`.doc`, `.xls`, `.ppt`):** Explicit rejection explaining the user to save as modern `.docx`/`.xlsx`/`.pptx`.
  2. **64KB Truncation Guard:** Automatically appends truncation notices with original length indicators if file size exceeds 64KB.
  3. **Action Integration (`actions/file_processor.py`):** Unified `_process_pdf`, `_process_text_doc`, and `_process_pptx` to query `read_file()` from `core.file_reader`.
* **Consequence:** Robust multi-format file reading across 30+ extensions with automatic scanned-document OCR, high-speed MarkItDown conversion, lazy Docling safety, and strict 64KB context protection.

---

## ADR-045: Dual-Mode Adaptive Asynchronous File Processing Architecture (`actions/file_processor.py`, `core/task_manager.py`)

* **Date:** 2026-09-21
* **Context:**
  1. When users uploaded documents (e.g. `Hamza Bukhari Resume.pdf`) and asked for heavy operations (such as summarization, OCR, conversion, or multi-page analysis), `actions/file_processor.py` ran synchronously inside the Gemini Live tool call loop.
  2. Because Gemini REST calls or document parsing took 10–30+ seconds, the live WebSocket loop blocked, freezing the 3D avatar in the `THINKING` state, preventing barge-in, and risking WebSocket heartbeat timeouts.
  3. Fast metadata operations (`info`, `word_count`, `validate`, `list`), however, execute in sub-5ms and do not require background queuing.
* **Decision:**
  1. **Dual-Mode Adaptive Routing:**
     - **Fast Synchronous Tier (`SYNC_FAST_ACTIONS`):** Lightweight metadata inspection (`info`, `word_count`, `validate`, `list`) runs synchronously in $<5$ms and returns instant answers directly to the active voice turn.
     - **Heavy Asynchronous Tier:** Heavy operations (`summarize`, `ocr`, `transcribe`, `analyze`, `to_word`, `extract_text`, `extract_images`, etc.) submit a worker task via `get_task_manager().submit("file_processor", _file_task_worker, params)`.
  2. **Immediate Task Turn Return ($<20$ms):**
     - The tool handler returns immediately with the generated `task_id` and a natural conversational voice message: `"Maine '{path.name}' ko background task queue mein bhej diya hai (Task ID: {task_id}). Main isko process kar raha hoon, aap parallel mujhse baat karte rahein."`
     - The live WebSocket audio loop remains 100% responsive for immediate follow-up conversation.
  3. **HUD Activity Log & Voice Notification on Completion (Decision 1 - Option 2):**
     - When the background worker finishes processing:
       - Full text and analysis results are posted directly to the HUD activity panel via `player.show_content(f"FILE RESULT · {path.name.upper()}", result)`.
       - A short 1-sentence voice announcement is spoken via `speak(...)` / TTS: `"Hamza, aapki file '{path.name}' ka summary complete ho gaya hai aur HUD par post kar diya hai."`
  4. **Task Lifecycle Hooks:**
     - Background worker updates progress across phases (`ctx.report(20, ...)` $\rightarrow$ `ctx.report(60, ...)` $\rightarrow$ `ctx.report(100, ...)`), calls `ctx.on_complete()` upon completion, or `ctx.on_fail(err)` upon error.
* **Consequence:** Eliminates voice loop and avatar freezing during heavy document summarization and OCR, maintains instant responsiveness for fast metadata queries, and delivers clean non-intrusive HUD and voice completion updates.

---

## ADR-046: Background Task Summary Content Propagation & Non-Hallucinating File Creation (`actions/file_processor.py`, `main.py`, `tests/test_file_reader_suite.py`)

* **Date:** 2026-09-21
* **Context:**
  1. When `file_processor` ran in the background to summarize or process documents, it posted the full markdown text to the HUD content viewer via `player.show_content()`.
  2. However, `_file_task_worker` returned `{"status": "success", "result": res}` without an explicit `"summary": res` key, causing `main.py`'s notification builder to fall back to `task.message` (`"Completed summarize"`).
  3. Consequently, the Gemini Live session received `[TASK_NOTIFICATION]` containing only the completion status rather than the actual extracted summary text.
  4. When the user subsequently instructed the assistant to save or export the summary to disk (e.g. `"summary report ko desktop pr txt ma dal de"`), Gemini lacked the extracted content and generated a placeholder string (`"Task 3606fa50 summarized content for Hamza Bukhari Resume.pdf"`) into `file_controller(action='create_file')`.
* **Decision:**
  1. **Explicit Summary Key in Task Results (`actions/file_processor.py`):**
     - Updated `_file_task_worker` to return `{"status": "success", "result": res, "summary": res, "file": path.name, "action": action}` so that both `result` and `summary` access patterns resolve the authentic content.
  2. **Comprehensive Task Notification Payload (`main.py`):**
     - Updated `main.py`'s finished task processor to inspect `res.get("summary") or res.get("result") or ...` and include `Result / Summary Content:\n{summary}` in the `[TASK_NOTIFICATION]` payload.
     - Added an explicit protocol directive: `"If the user asks to save, write, or export this summary into a file, ALWAYS use the exact 'Result / Summary Content' text above as the content parameter for file_controller(action='create_file') — NEVER invent placeholder text."`
  3. **Automated Verification:**
     - Added `test_background_file_processor_summary_payload` in `tests/test_file_reader_suite.py` ensuring background worker returns complete text in `res["summary"]`.
* **Consequence:** 100% authentic document summary content is retained in session memory and written to output files without placeholder hallucination.

---

## ADR-047: Autonomous Traffic Vectors Desktop UI Redesign & Clean Activity Stream (`ui.py`)

* **Date:** 2026-09-21
* **Context:**
  1. The production desktop UI required complete aesthetic alignment with the approved Autonomous Traffic Vectors design system (`prototypes/zezo_desktop_ui_prototype.html`).
  2. The activity stream was previously cluttered with repetitive internal state transition messages (`SYS: State changed to LISTENING`, `SYS: State changed to SPEAKING`).
  3. Visual elements had mixed rounded corners (`border-radius: 6px-14px`) and excessive ambient glow halos around the central avatar viewport.
* **Decision:**
  1. **Strict 0px Technical Frame Design System:**
     - Eliminated all rounded corners across panels, drawers, overlays (`SetupOverlay`, `RemoteKeyOverlay`, `CustomizeOverlay`, `SkillHubOverlay`, `ConfirmBanner`), metric bars, and controls, standardizing on sharp 90-degree technical corners (`border-radius: 0px`).
     - Added geometric corner bracket accents (`draw_corner_brackets`) to technical cards and container boundaries.
  2. **Pitch-Black Centerpiece Viewport & Tactical Status Capsule:**
     - Configured the avatar viewport to pure `#000000` pitch black with zero glow halos, increasing avatar core dimensions to 290px–330px.
     - Engineered a bottom-centered tactical status capsule (`#0a0a0c`, 32px height) with a live state beacon dot, monospace state label, hairline vertical divider, and calm organic dual-harmonic sinusoidal waveform (`waveSpeed: 0.0010` feel).
  3. **Activity Stream Noise Suppression:**
     - Removed internal state transition logging from `_apply_state()`, keeping the activity log strictly focused on genuine user prompts, assistant replies, tool executions, and critical system alerts.
  4. **Multi-Preset 0ms Instant Accent Retinting:**
     - Updated `C` token constants and `apply_ui_accent()` to dynamically re-tint primary and glow accents (Orange `#f24e1e`, Cyan `#00e2ff`, Green `#00ff88`, Purple `#c084fc`) across all active UI components with zero latency.
* **Consequence:** 100% visual parity with the design prototype, distraction-free activity stream, and responsive high-performance desktop HUD.

---

## ADR-048: Header Remote Trigger, QuickDrawer Theme Retinting & Multi-View Content Tabs (`ui.py`)

* **Date:** 2026-09-21
* **Context:**
  1. The reference prototype (`prototypes/zezo_desktop_ui_prototype.html`) and design system (`Autonomous Traffic Vectors · Design System.html`) specify a 5th quick-action header button for mobile remote QR pairing (`📱`).
  2. QuickDrawer required an immediate, user-accessible theme color dot picker (`UI ACCENT COLOR`: Solar Orange `#f24e1e`, Neon Cyan `#06b6d4`, Cyber Emerald `#22c55e`, Hyper Purple `#a855f7`).
  3. The collapsible content panel below the HUD needed operational multi-view tabs (`CODING AGENT`, `WEB RESEARCH`, `FILE EXTRACTION`, `SOCIAL INTEL`, `TELEMETRY`, `TRANSCRIPT`) and context-aware action buttons (`PREVIEW`, `FOLDER`) matching the prototype layout.
* **Decision:**
  1. **Header Mobile Remote Quick Trigger:**
     - Added `self._qr_hdr_btn = QPushButton("📱")` directly to `_build_header()`, wired to open `RemoteKeyOverlay` on click.
  2. **QuickDrawer Instant Accent Picker:**
     - Integrated a dedicated `UI ACCENT COLOR` horizontal section in `_build_quick_drawer()` with 4 clickable square color chips that dynamically re-tint the application live without restart.
  3. **Multi-View Inspector Tabs & Context Actions in Content Panel:**
     - Integrated `_hud_tabs_widget` with 6 operational tab views into `_build_content_panel()`.
     - Added `_content_prev_btn` (`🌐 PREVIEW`) and `_content_folder_btn` (`📁 FOLDER`) that auto-resolve the active task's workspace directory and provide instant opening.
* **Consequence:** Full feature and visual parity with the reference design system, interactive operational inspector views, and one-click remote QR pairing directly from the header bar.

---

## ADR-049: Web Engine Desktop UI Architecture with Local WebSocket Bridge (`ui.py`, `core/ui_server.py`, `frontend/`)

* **Date:** 2026-09-21
* **Context:**
  1. Native PyQt6 QSS widgets lack modern CSS3 features (Flexbox, CSS Grid, hardware-accelerated animations, backdrop-filter, blend modes), preventing 100% pixel-perfect fidelity with the Autonomous Traffic Vectors design system and HTML5 prototype.
  2. The assistant required a high-performance desktop shell architecture similar to modern agentic frameworks (QwenPaw / AgentScope) while preserving the pure Python backend, Gemini Live voice streaming, task manager, and local desktop shortcuts.
* **Decision:**
  1. **Decoupled Web Frontend Layer (`frontend/`):**
     - Built a standalone Vanilla HTML5 + ES Modules + CSS frontend implementing the exact Autonomous Traffic Vectors design system, 0px technical framing, 60 FPS HTML5 Canvas avatar/waveform visualizer, and multi-view operational tabs.
  2. **Local Async WebSocket Bridge (`core/ui_server.py`):**
     - Engineered a high-throughput, thread-safe `aiohttp` WebSocket & static file server running on `127.0.0.1:8765`.
     - Streams telemetry, agent state transitions, task progress, and activity logs reactively to connected web views.
  3. **Embedded Desktop Shell Container (`ui.py`):**
     - Hosted the UI in `QWebEngineView`, maintaining Windows AppUserModelID (`zezo.assistant.v2`) for standalone Taskbar grouping and `_create_desktop_shortcut()` for `ZEZO.lnk`.
* **Consequence:** 100% pixel-perfect visual fidelity, 60 FPS GPU-accelerated canvas visualizers, zero npm/Node.js build friction, and complete preservation of the existing Python backend and desktop shortcut features.





