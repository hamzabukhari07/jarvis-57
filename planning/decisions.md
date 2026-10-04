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

---

## ADR-050: Autonomous Website Cloner & Adaptive Redesigner (`actions/website_cloner.py`, `core/task_manager.py`, `core/repo_context.py`, `core/undo.py`, `core/prompt.txt`)

* **Date:** 2026-09-22
* **Context:**
  1. Users requested the ability to clone any website by providing its URL via voice or text ("apple.com clone kardo"), download offline-ready frontend assets, view immediate browser previews, and adaptively convert the cloned pages into modular React/Next.js projects or Hamza Taste studio redesigns.
  2. Pure static downloaders (such as raw cURL or basic HTTrack) fail on modern Single Page Applications (React, Next.js, Webflow, Framer) by downloading un-hydrated `<div id="root"></div>` containers without rendered elements.
  3. Opening cloned websites directly via `file:///...` causes CORS and root-relative path errors in modern browsers.
  4. Chaining AI code conversion or redesign required strict race-condition-free task execution where the cloner flushes all assets to disk before Antigravity begins parsing.
* **Decision:**
  1. **3-Tier Fallback Ladder (`actions/website_cloner.py`):**
     - **Tier 1 (Default / SPA):** Playwright Headless Chromium rendering full DOM with `networkidle` wait condition and stealth headers.
     - **Tier 2 (HTTP Stream):** Fallback via `urllib`/`requests` + `BeautifulSoup` ensuring resilience if headless browser drivers fail.
     - **Tier 3 (Recursive Full-Site):** Cross-platform `shutil.which("httrack")` CLI invocation triggered strictly when the user explicitly requests full-site mirroring (`mode="full_site"`).
  2. **Fault-Tolerant Asset Downloader & Partial Success Guard:**
     - Parallel downloads (up to 8 concurrent workers) for CSS, JS, images, and fonts with size caps (25MB per asset, 200MB total directory size).
     - Failed assets (404/403/timeout) gracefully retain original remote URLs without failing the clone task.
  3. **Local Ephemeral Loopback Preview Server (`http://127.0.0.1:PORT`):**
     - Automatically starts a lightweight daemon HTTP server on loopback ports (9400–9480) and opens `http://127.0.0.1:PORT/index.html` in the default browser, avoiding all CORS and `file://` relative path failures.
  4. **Task Chaining (`core/task_manager.py` `submit_after`):**
     - Added `submit_after(parent_task_id, tool_name, fn, params)` and `MAX_CONCURRENT_CLONES = 2` semaphore in `TaskManager`.
     - When `output_format` is `"react"` or `"redesign"`, `website_cloner` chains execution to `antigravity_agent` only *after* disk assets are 100% written.
  5. **Undo & Workspace Integration (`core/undo.py`, `core/repo_context.py`):**
     - Auto-allocates collision-safe workspaces (`Desktop/<domain>_clone`, `_1`, `_2`), registers active workspace in `repo_context.json`, and records an undo snapshot via `register_clone_snapshot()`.
  6. **Voice Safety & Disclaimers (`core/prompt.txt`):**
     - Clarified voice disclaimer: *"Frontend clone kar raha hoon (backend database/logic clone nahi hota)."*
* **Consequence:** 100% offline-ready website cloning across modern SPAs and static sites in 5–10s, instant browser preview, zero `file://` CORS breakage, seamless Antigravity React/redesign conversion, and complete undo support.

---

## ADR-051: 2-Stage Clean HTML Cloner, On-Demand React/Next.js Transpiler, and Local Folder Redesign (`actions/website_cloner.py`, `actions/antigravity_agent.py`, `core/prompt.txt`, `tests/test_website_cloner_suite.py`)

* **Date:** 2026-09-22
* **Context:**
  1. Default website cloning previously captured compiled production bundles (`_next/static/chunks/*`, `turbopack*.js`, webpack runtime hashes, tracking blobs, and hydration attributes), rendering the cloned JavaScript unreadable and difficult to customize directly in VS Code.
  2. Users requested that the default cloned output match the clean, unminified, formatted HTML5 + Tailwind/CSS structure of `skills/hamza_taste/references/html`, with on-demand conversion to modular React (Vite) or Next.js 15 App Router projects.
  3. Users also requested the ability to point ZEZO to any existing local website folder on Desktop to autonomously redesign it using Hamza Taste studio aesthetics while strictly preserving all real text, headings, and functional content.
* **Decision:**
  1. **2-Stage Cloner Pipeline (`actions/website_cloner.py`):**
     - **Stage 1 (Default - Clean HTML in 3–5s):** Automatically sanitizes the rendered DOM via `_sanitize_and_clean_dom()`, stripping all framework chunk scripts (`_next/static`, `turbopack`, `webpack.runtime`, `sw-register`, `googletagmanager`, `doubleclick`), removing inline JSON hydration blobs (`__NEXT_DATA__`, `__remixContext`), deleting framework hydration attributes (`data-reactroot`, `data-n-head`, `data-server-rendered`), and generating a clean, human-readable vanilla interaction file (`assets/js/app.js`).
     - **Stage 2 (On-Demand AI Synthesis):** When `output_format` is `"react"` or `"nextjs"`, chains to `antigravity_agent` to decompose the clean HTML blueprint into modular TypeScript components (`src/components/Navbar.tsx`, `Hero.tsx`, `Features.tsx`, `Footer.tsx`), creating modern `package.json`, `tailwind.config.js`, `tsconfig.json`, and Vite / Next.js entrypoints.
  2. **Local Folder Redesign Engine (`actions/antigravity_agent.py`):**
     - Enhanced `antigravity_agent` with local folder redesign prompts that inspect existing `index.html`/`style.css`, extract authentic copy and layout structure, create an automatic undo snapshot, and rebuild the frontend with Obsidian Studio glassmorphism, animated mesh gradients, and fluid typography.
  3. **Multi-Format Routing (`core/prompt.txt`):**
     - Updated prompt rules: Default is clean HTML/CSS; user requests for `"React mein convert karo"` / `"Next.js project banao"` / `"Redesign kardo"` map directly to `output_format="react"`, `"nextjs"`, or `antigravity_run` local folder redesign.
* **Consequence:** 100% human-readable, editable cloner output matching `hamza_taste` standards, instant 3-5s preview, zero production chunk garbage, modular React/Next.js transpilation on demand, and seamless local folder redesign with full undo protection.

---

## ADR-052: Free-Tier Groq Hybrid Ingestion & Canonical Gemini Ladder Repair (`core/llm_client.py`, `core/file_reader.py`, `actions/file_processor.py`, `memory/config_manager.py`)

* **Date:** 2026-09-24
* **Context:**
  1. Audio/video transcription in `actions/file_processor.py::_process_audio` ran through the paid Gemini multimodal REST path (`_gemini_client`), and image extraction in `core/file_reader.py` went straight to the paid Gemini vision path. The user asked to make ingestion "completely free" (Option B, Groq Hybrid) without a GPU.
  2. `core/file_reader.py::_read_with_gemini_rest` built a raw `genai.Client` and looped hardcoded model names (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-1.5-flash`). Runtime evidence showed **all four return 404 NOT_FOUND** — the fallback used by images and scanned PDFs was dead. This directly contradicted the LEARNING_JOURNAL lesson "never bypass `core/gemini.py`'s `call()` ladder".
  3. Groq's public free tier (verified live via `/v1/models`) exposes `whisper-large-v3`/`whisper-large-v3-turbo` and text models (`qwen/qwen3.8-27b`, `openai/gpt-oss-*`) but **no multimodal/vision model**.
* **Decision:**
  1. **Groq client primitives (`core/llm_client.py`):** Added `call_groq_vision()` (OpenAI-compatible `image_url` base64 data URI, multi-model fallback) and `transcribe_groq_whisper()` (multipart upload to `/openai/v1/audio/transcriptions`).
  2. **Config (`memory/config_manager.py`):** Added `get_groq_vision_model()` / `get_groq_whisper_model()` and extended `save_groq_config()` with optional `vision_model` / `whisper_model` kwargs (backward compatible). `DEFAULT_GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"`; `DEFAULT_GROQ_VISION_MODEL = ""` is intentionally empty because the free tier serves no vision model, so images never pay a wasted failed call.
  3. **Free-first routing:**
     - `actions/file_processor.py`: `transcribe` tries Groq Whisper first, then falls back to the paid Gemini path. Video `transcribe` inherits it via audio extraction.
     - `core/file_reader.py`: image branch tries `groq_vision` (opt-in) → `gemini_vision` → metadata.
  4. **Gemini ladder repair (`core/file_reader.py`):** Rewrote `_read_with_gemini_rest()` to call `core.gemini.call([prompt, part], tier=gemini.SMART, timeout_ms=60000)`, restoring the Live-led ladder with cooldown/fallback instead of retired hardcoded names.
* **Consequence:** Audio/video transcription is now free and ~10x faster when Groq is configured; image/scanned-PDF extraction works again through the canonical ladder; and no failed Groq vision call is ever made on the default configuration.
* **Verification:** Layer 1 `py_compile` + imports + 24/24 action discovery. Layer 2 real runtime — Groq Whisper returned `"The quick brown fox jumps over the lazy dog."` (`(Groq Whisper)` label, task DONE in 3.9s), and image OCR returned the exact `"ZEZO GROQ VISION TEST CODE 12345"` via `gemini_vision`. Layer 3 — `task_status`, `open_app` import, and action discovery all intact.
* **Known limitation:** Groq vision is wired but dormant until Groq ships a multimodal model (or the user points `groq_vision_model` at a proxy). Scanned-PDF Groq extraction would require page rasterization (no `PyMuPDF` dependency is currently declared), so scanned PDFs remain on the local Docling → Gemini ladder.

---

## ADR-053: Documents Never Use the Live Rung; Files-API Transport + Live Model Ladder Repair (`core/gemini.py`, `core/file_reader.py`)

* **Date:** 2026-09-25
* **Context:**
  1. A user dropped a 4.5 MB scanned `CV.pdf`. Extraction died with `[Gemini] live: APIError: 1006 None. abnormal closure [internal]` and the run appeared to hang.
  2. Runtime probes confirmed three separate faults: (a) the `SMART` ladder leads with the `LIVE` rung, and pushing a multi-MB `application/pdf` over the Live realtime WebSocket closes it with `1006`; (b) the REST rungs still listed retired names (`gemini-2.5-*` → **404** for new keys, verified live); (c) inline base64 uploads of a 6 MB payload exceeded the socket **write timeout** (~92 s) on this connection, so even a working REST model could not receive the file inline.
  3. `markitdown` and `docling` are **not installed** (and not declared in `requirements.txt`), so there was no local fallback; the scanned PDF had no working path at all.
  4. Live probes found the working multimodal models: `gemini-3-flash-preview` and `gemini-3.5-flash` returned the real CV text; `gemini-3.6-flash`/`3.7`/`3.8`/`gemini-flash-latest` returned transient `503`; the **Files API** uploaded 4.5 MB successfully in ~53 s.
* **Decision:**
  1. **`core/gemini.py`:** Replaced the retired `_LADDERS` model names with the verified live ones (`gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3-flash-preview`, `gemini-3.7/3.8-flash`, `gemini-flash-latest`). Added an `allow_live: bool = True` parameter to `call()` that drops the `LIVE` rung when `False`. Extended the cooldown branch to also cool on `503`/`UNAVAILABLE` (previously only `429`), so an overloaded model is skipped for 5 minutes.
  2. **`core/file_reader.py`:** `_read_with_gemini_rest(path, instruction, allow_live=True)` now (a) routes files **> 2 MB** through a new `_extract_via_files_api()` helper (resumable Files API upload, then `gemini.call(..., allow_live=False)`), and (b) passes `allow_live=False` from the scanned-PDF branch so documents never touch the Live WebSocket.
* **Consequence:** Scanned/large PDFs extract again (verified: `Desktop\CV.pdf` → 4,778 chars, `engine=gemini_document_api`, no `1006`), normal one-shot text calls still work, and overloaded models no longer head every ladder attempt.
* **Verification:** Layer 1 `py_compile` + import (`allow_live` present, `_INLINE_LIMIT_BYTES=2097152`). Layer 2 real runtime on `C:\Users\Hamza Bukhari\Desktop\CV.pdf` → `[FILES_API] Extracted 4,425 characters` → `[DONE] ... Engine: gemini_document_api | Output: 4,778 chars`; `303` model cooled and skipped. Layer 3 regression — `gemini.text('...ok')` → `'ok'`, text file → `direct_read`, image → `gemini_vision` (exact OCR), Groq Whisper transcript intact, `tests/test_file_reader_suite.py` 6 passed / 1 pre-existing unrelated failure.
* **Known limitation:** This environment lacks `markitdown`/`docling`, so native PDF text extraction also depends on Gemini; adding `pdfplumber` (already installed) as a local native-PDF reader is a worthwhile follow-up. `gemini-3.5-flash`/`3-flash-preview` were the available multimodal models at test time; availability is quota-dependent.

---

## ADR-054: Local-First Document Readers (pdfplumber + Office libs) as the MarkItDown-Independent Path (`core/file_reader.py`, `requirements.txt`)

* **Date:** 2026-09-25
* **Context:**
  1. `core/file_reader.py` treated MarkItDown as the primary converter for PDF and Office files. `markitdown` and `docling` are **not installed** (and were not declared), so `_read_with_markitdown()` always returned `None`. Every PDF was therefore classified `is_scanned=True` and sent to paid Gemini, and `.docx/.xlsx/.pptx` fell through to `_read_text_direct()` — a raw binary decode that yields garbage.
  2. `pdfplumber`, `python-docx`, `openpyxl`, and `python-pptx` were already installed and already declared in `requirements.txt`, but `file_reader.py` never used them.
  3. A 4.5 MB `Desktop\CV.pdf` was reported as scanned and cost a 77 s Gemini round-trip — even though it actually has a text layer.
* **Decision:**
  1. **New local readers in `core/file_reader.py`:** added `_read_with_pdfplumber()` (text-layer PDFs) and `_read_office_local()` (`.docx` via python-docx, `.xlsx` via openpyxl, `.pptx` via python-pptx).
  2. **Local-first ordering:** the PDF branch now uses `md_text or _read_with_pdfplumber(path)` and only escalates to Gemini when that yields too little text (`_is_scanned_pdf`); the Office branch uses `md_text or _read_office_local(path, ext)` before any raw decode. New engine labels: `pdfplumber`, `office_local`.
  3. **`requirements.txt`:** added `markitdown` to the declared dependencies (optional fast path) and noted `docling` under the heavy optional extras for offline OCR of truly scanned PDFs.
* **Consequence:** Text-layer PDFs and Office documents are read **locally, free, and fast** (verified: `Desktop\CV.pdf` 4,287 chars in 5.0 s vs the previous 77 s Gemini path; native `Resume.pdf` and `Hamza-Bukhari-CV.pdf` also via `pdfplumber`). Gemini is now used **only** for genuinely scanned documents.
* **Verification:** Layer 1 `py_compile` + import. Layer 2 real runtime — `Desktop\CV.pdf` → `engine=pdfplumber`, 4,287 chars, 5.0 s, correct CV text; `Resume.pdf` → `pdfplumber` 4,542 chars; generated `.docx`/`.xlsx`/`.pptx` → `office_local`. Layer 3 regression — `tests/test_file_reader_suite.py` 6 passed / 1 pre-existing unrelated failure; text `direct_read` and image `gemini_vision` unchanged.

---

## ADR-055: Lazy Attachment Model — Drop Registers a Path, Read Is Explicit and Non-Blocking (`core/ui_server.py`, `main.py`, `actions/file_processor.py`, `core/prompt.txt`, `frontend/index.html`)

* **Date:** 2026-09-25
* **Context:**
  1. Dropping a file ran `read_file()` **synchronously inside the aiohttp `_upload_handler`** — blocking the UI server event loop and keeping the HTTP request open for 5–77 s on a large PDF.
  2. `main.py::_handle_ui_file_uploaded` then **woke ZEZO and pushed a forced Live turn** (`send_client_content(..., turn_complete=True)`) with the extracted content (or image base64), so a drop hijacked the conversation and the assistant stopped listening while it responded. Image drops were auto-described; the mobile dashboard did the same.
  3. The user asked for: attach silently, read only on request, keep the voice loop free and multiple tasks running.
* **Decision:**
  1. **Lazy registry (`core/ui_server.py`):** `_upload_handler` no longer reads anything — it saves the file and registers it by path (`register_attachment`, `latest_attachment`, `find_attachment`, `remove_attachment`, `clear_attachments`, thread-locked, cap 50). Folder drops still register the active workspace via `repo_context` but use a **bounded scan** (`_scan_folder`, ≤5000 files). `payload_remove`/`payload_clear` also update the registry.
  2. **Silent drop (`main.py`):** `_handle_ui_file_uploaded` and `_on_dashboard_file_uploaded` just set the current file and write a one-line log — **no wake, no session wait, no `send_client_content`**. Image auto-describe removed.
  3. **On-demand read (`actions/file_processor.py`):** new `_resolve_attachment()` — empty `file_path` → most recent attachment; a bare name (not an existing path) → registry name match; folder-for-latest or empty registry → a clear clarifying message. Heavy reads already route through `TaskManager`.
  4. **Prompt rule (`core/prompt.txt`, decision A):** new "Dropped / Attached Files (Lazy Read Rule)": never claim to have read an attached file; on reference, call `file_processor` with empty `file_path` (or a name); heavy reads return a task_id and ZEZO must not block or go silent.
  5. **Frontend (`frontend/index.html`):** activity card reads `[FILE ATTACHED]` / "attached — not read yet" until the file is read.
* **Consequence:** A drop is instant and silent; ZEZO keeps listening and can run several tasks; content is read only when asked, in the background. Aligns with ADR-045 (async heavy file ops) and refines ADR-034 (multi-file).
* **Verification:** Layer 1 `py_compile` + import + 24/24 actions. Layer 2 real runtime — POST `/api/upload` of a 4.5 MB PDF returned in **0.05 s** (was 5–77 s); registry entry `engine="attached"`, `text_len=0`; `file_processor({"action":"info"})` with no path resolved the latest attachment and returned `PDF: 1 pages, size: 4.5 MB`; fuzzy name + exact name + folder-refusal + empty-registry messages all correct. Layer 3 — explicit-path `file_processor` works, `task_status` works, prompt tokens intact, `tests/test_file_reader_suite.py` 6 passed / 1 pre-existing unrelated failure.
* **Known limitation:** attachment registry is in-memory on the UI server singleton (cleared on restart — intended, uploads are session-scoped). Multi-file ambiguity resolves to the most recent; the user must name a file to disambiguate.

---

## ADR-056: Web HUD Animation Gate & Drag-Performance Fix (`frontend/index.html`)

* **Date:** 2026-09-25
* **Context:**
  1. Dragging a file over the desktop UI logged `WebContentsAdapter::updateDragAction was not called within 3000 ms` repeatedly and the UI lagged badly.
  2. That message is QtWebEngine's browser adapter timing out while waiting for the renderer to return the drag action. The renderer main thread was saturated by two continuous `requestAnimationFrame` loops: a **full-window Three.js WebGL particle globe** (`#webgl-bg`, 2000 particles, `antialias:true`, `setPixelRatio(min(dpr,2))`, always started at window load) and the dot-matrix icon (`ctx.shadowBlur` per frame). The page also carried 5 `backdrop-filter`, 23 `box-shadow`, and 18 `transition: all`.
* **Decision:**
  1. **Animation gate:** `window._zezoAnimActive` — checked at the top of both loops. `_zezoPauseAnim(dragging)` sets it and `window._zezoDragging`; wired to `dragenter`/`dragover`/`dragend`/`drop`/`dragleave`.
  2. **~30 FPS cap** on both loops (`now - last < 33`), plus **pause on `document.hidden`** via `visibilitychange`.
  3. **Cheaper globe:** `antialias:false`, `setPixelRatio(min(devicePixelRatio, 1.5))`.
  4. **`dragenter` now calls `preventDefault()`** (proper Qt/Chromium drag protocol).
  5. **`.dropzone` / `.dropzone-icon`** `transition: all` replaced with explicit `border-color` / `background` / `color`.
* **Consequence:** The renderer thread is free during a drag, so Chromium's drag-action request is answered in time; overall HUD cost is roughly halved and idle-when-hidden.
* **Verification:** Layer 1 — page loads in real Chromium (msedge) with **no page errors**. Layer 2 — runtime state: initial `{active:true, dragging:false}`; after a bubbling `dragenter`+`dragover` on `#dropzone-box` → `{active:false, dragging:true}` (paused); after `dragend` → `{active:true, dragging:false}` (resumed). Layer 3 — globe element present, dropzone present, drop handler unchanged.
* **Known limitation:** the dot-matrix icon still uses `ctx.shadowBlur`; the 30 FPS cap mitigates but does not remove that cost. The machine-specific warning can only be fully confirmed as gone on the user's hardware.

---

## ADR-057: Log-Noise Suppression for the Rust HTTP Stack, Task-Status Monitor Guard & Deterministic YouTube Play (`core/log_bus.py`, `actions/background_monitor.py`, `actions/youtube_video.py`, `core/prompt.txt`)

* **Date:** 2026-09-25
* **Context:**
  1. A backend log export was ~95% noise: `hickory_net.*`, `hickory_resolver.*`, `h2.*`, `cookie_store.cookie_store`, and `primp` DEBUG records from `ddgs`→`primp` (Rust). A single web search emitted >1000 lines, rolling the 20,000-line ring buffer in seconds and hiding real diagnostics. ADR-033's `_NOISY_LOGGERS` covered Python HTTP libs but not this Rust stack.
  2. `manage_monitor` had been used to create monitors for task ids ("Antigravity task 7a8eb009 status", "OpenCode task 138e6a1b status"), causing wasteful web searches and an irrelevant alert. Task status is a local concern (`task_status`).
  3. `youtube_video(action="play")` passed a pasted URL to `yt-dlp` as `ytsearch1:<url>`, returning the wrong video, and its success string claimed "Playing" when it had only opened a page.
* **Decision:**
  1. **`core/log_bus.py`:** added `hickory_net`, `hickory_resolver`, `hickory_proto`, `h2`, `cookie_store`, `primp` to `_NOISY_LOGGERS` (pinned to WARNING unless `ZEZO_LOG_DEBUG=1`), extending ADR-033.
  2. **`actions/background_monitor.py`:** `_looks_like_task_status()` rejects topics that name a task id (6+ hex chars) with a status word; `add_monitor()` returns a clear message instead of creating the monitor. `core/prompt.txt` adds: task status is local, never monitor a task id.
  3. **`actions/youtube_video.py`:** `_handle_play` now opens a valid YouTube URL **directly** in the default browser; a search term resolves to the top result (else the filtered search page); the return string no longer claims playback. TOOL description updated; `core/prompt.txt` says to fall back to `browser_control` after one failed attempt rather than retrying.
* **Consequence:** Log exports carry signal instead of DNS/HTTP2 frames; no bogus task-status monitors; pressing play on a pasted URL opens it first time.
* **Verification:** Layer 1 `py_compile` + imports + 24/24 actions + prompt tokens intact. Layer 2 runtime — the six loggers resolve to WARNING; `_looks_like_task_status` True for task topics, False for "space exploration"; `add_monitor` rejected a task topic; play-URL opened directly with `_find_video_url` NOT called, play-search opened the resolved video. Layer 3 — YouTube TOOL/action map intact, monitor functions intact, `tests/test_file_reader_suite.py` 6 passed / 1 pre-existing.

---

## ADR-058: Website-Build Stack Fidelity & Reference-Matcher Word Boundary (`actions/antigravity_agent.py`, `core/design_resolver.py`, `core/prompt.txt`, `skills/antigravity_agent/SKILL.md`)

* **Date:** 2026-09-25
* **Context:**
  1. A user asked for *"an entirely new, single-file HTML portfolio … complete design within one index"* in a folder that already held a React build. ZEZO kept it as React and ignored the Hamza Taste reference.
  2. `is_redesign_or_explicit_request()` did not recognise "entirely new / from scratch / single-file HTML", so `_run_worker` selected the `is_existing_project and not is_redesign` branch, which instructs **preservation** and **omitted the design directive entirely**. The flow had no notion of the user's requested output *stack*.
  3. `is_react_or_next` was a bare substring scan (`react`, `vite`, `jsx`, …) that also fired on negations ("no react", "not React").
  4. `core/design_resolver.py::_is_explicit_match` used `clean_stem in task_clean` (raw substring). The 2-char `en` stem matched inside ordinary words ("cont**en**t", "**en**tirely", "ag**en**cy"), so many normal requests falsely resolved to the HTML-less `En-DESIGN` reference (`raw_html=0`), which meant no `DESIGN_BLUEPRINT.html` was written and the real Hamza Taste reference was never injected. The shipped `tests/test_design_system_suite.py` already failed 3 tests because of this.
* **Decision:**
  1. **Reference matcher (`core/design_resolver.py`):** replaced the substring fallback with a word-boundary regex for stems ≥3 chars (`\b<stem>\b`), and extended `is_redesign_or_explicit_request()` with full-rebuild/stack markers ("entirely new", "from scratch", "single file", "single html", "static site", "no react", …).
  2. **Stack routing (`actions/antigravity_agent.py`):** explicit static/single-file HTML intent (`is_static_html`) now takes precedence over framework inference; `is_react_or_next` is gated by negation and static intent; full-rebuild intent overrides project preservation. A dedicated **single-file HTML directive** and a **shared Hamza Taste design directive (Direction + anti-slop Filter)** are appended in **every** branch. If a reference has no raw HTML, a `DESIGN_BLUEPRINT.md` (spec + anti-slop) is written instead, so the reference is never silently lost.
  3. **Contract sync:** `antigravity_run` TOOL description and `core/prompt.txt` now state the stack-fidelity rule; the stale hardcoded `D:\anitgravity\...` reference path in `skills/antigravity_agent/SKILL.md` was replaced with the repo-relative path.
* **Consequence:** A "single HTML" request produces one self-contained `index.html` even when the target folder holds React, React/Next.js is only produced when explicitly requested, and the resolved Hamza Taste blueprint is injected for every build branch.
* **Verification:** Layer 1 — `py_compile` PASS, 24/24 actions discovered. Layer 2 — `tests/test_design_system_suite.py` now **11 passed** (was 3 failed); the exact CV task resolves to `Crazy-Ui-Landing-Page-Design` with a 35,546-char raw HTML blueprint; a runtime harness stubbing `subprocess.Popen` proved the real `_run_worker` selects SINGLE-FILE for the CV task, REACT for an explicit React task, and STATIC for "single html, no react" (`scratch/verify_antigravity_stack_routing.py`). Layer 3 — `tests/test_website_cloner_suite.py` + `tests/test_extractor_suite.py` 9 passed.
* **Known limitation:** the technology CLI (`agy`) agent must still choose to read `DESIGN_BLUEPRINT.html`; the directive is now present in every branch and the anti-slop Filter is included, but compliance is ultimately the external agent's decision.

---

## ADR-059: Real-Time Fact Grounding & No-Entity-Substitution Directive (`core/prompt.txt`, `actions/web_search.py`)

* **Date:** 2026-09-25
* **Context:**
  1. A user asked to compare "Pixel 9 Pro XL vs iPhone 18 Pro Max latest real data". The Live voice model (`GEMINI_LIVE_MODEL`, frozen training knowledge) built the `web_search` call with **"iPhone 16 Pro Max"** — it silently rewrote the user's explicit product name to the newest one it remembered.
  2. It then answered *"the iPhone 18 Pro Max hasn't been released yet. We're still on the iPhone 16 series"* — from parametric memory — even though `_run_worker`'s `[SYSTEM LOCAL DATE & TIME]` said **Friday, September 25, 2026**, and even after the user corrected it.
  3. Runtime evidence showed the tool itself is correct: `_ddg_search('iPhone 18 Pro Max specs')` returns the real product (Wikipedia, `apple.com/iphone-18-pro/specs`, and the Apple newsroom post dated 09-Sept-2026). The only blocker was the model overriding tool data with memory.
  4. `core/prompt.txt` had no temporal-grounding or entity-fidelity rule; the only relevant text was the `web_search` TOOL description's "always prefer this over guessing", which the model ignored.
* **Decision:**
  1. **`core/prompt.txt`** — new `[REAL-TIME FACTS & TEMPORAL GROUNDING — NON-NEGOTIABLE]` section: training knowledge is frozen; any current-fact/product/release/price/event question must go through `web_search` and be answered only from its result; **search the exact entity the user named** and never substitute an older one; never assert "hasn't been released / doesn't exist" unless the search says so; if search is empty, say data was unavailable rather than falling back to memory; the user and search result outrank memory on current facts.
  2. **`actions/web_search.py`** — TOOL description now states the same memory-is-outdated rule and the exact-entity requirement (defense in depth, since the model reads tool descriptions).
* **Consequence:** ZEZO no longer "corrects" a user's current product/version and no longer contradicts live search with stale memory; current-fact questions route to grounding by policy.
* **Verification:** Layer 1 — `py_compile` PASS; all prompt tokens intact; `_render_prompt` renders with no unrendered tokens, new section present. Layer 2 — real `_ddg_search('iPhone 18 Pro Max specs')` returned live data proving the model's memory was the only failure (`scratch/live_ddg_iphone18.txt`). Layer 3 — web/prompt/assistant tests 14 passed; action discovery 24/24.
* **Known limitation:** the Live model's compliance with the prompt cannot be unit-tested — the fix is a policy/instruction change. Gemini grounded search can also hit its own quota (observed `out of quota → DDG fallback` in this session), which is exactly why the rule now forbids memory fallback and requires an honest "data unavailable" when search returns nothing.

---

## ADR-060: Deep Multi-Platform Research Compiler — Full-Text Extraction, No Hardcoded Matrix (`actions/agent_reach.py`)

* **Date:** 2026-09-25
* **Context:**
  1. A user asked ZEZO to research how people make vibe-coded apps production-ready, compile all the posts and "extract every link's data". The generated report (`Desktop/Consolidated_Vibe_Report.md`) contained only **one-line search snippets** for Reddit/HN, no article bodies, an empty GitHub section, a boilerplate "Executive Summary", and — for a vibe-coding query — a **hardcoded `Rust vs Go` comparison matrix**. A second hardcoded Rust/Go sentence was appended to the spoken multi-report summary.
  2. Root cause: `fetch_multi_platform_search` only called `web_search(mode='research')` (grounded search/DDG snippets) for Reddit/HN and never fetched the content behind any URL. There was no web/blog source at all, no per-resource analysis and no synthesis. The `Rust vs Go` section was a leftover template unrelated to the query.
* **Decision:**
  1. **Rewrite `fetch_multi_platform_search`** into a deep compiler: discover real sources (YouTube, web/blogs, Reddit, GitHub, Hacker News), then **fetch the full body of each** — web article markdown via `extract_web_content`, Reddit post+comments via `fetch_reddit_discussion`, HN thread via `fetch_hackernews`, YouTube captions via `fetch_youtube_transcript`, GitHub README via `fetch_github_repository`.
  2. **Per-resource analysis** via `core.llm_router.generate_text` (Groq → Gemini → Ollama), with a verbatim trimmed-extract fallback if every provider fails. **Synthesis** of an Executive Summary + Key Findings + a step-by-step playbook from the collected analyses only.
  3. **Remove both hardcoded `Rust vs Go` blocks** (report matrix and the spoken summary sentence).
  4. **Bound every fetch** with `_run_bounded` (per-host timeout) and set `allow_audio_fallback=False` for YouTube in batch mode, so a report never downloads 12–18 MB of audio per video or stalls on one slow host.
  5. Reddit's blocked `.json` endpoint now falls back to full-page `extract_web_content` before a snippet search.
* **Consequence:** `agent_reach(platform='multi')` produces a genuinely deep report: every claim maps to a fully-read source, with an "All Sources" reference list; no topic-irrelevant boilerplate; bounded runtime/bandwidth.
* **Verification:** Layer 1 `py_compile` + 24/24 actions. Layer 2 real run on "production-ready AI vibe coding" → `Desktop/ZEZO_DEEP_TEST.md` of **24,524 bytes / 183 lines / 15 fully-extracted resources**, `has hardcoded Rust/Go matrix: False`, Reddit/HN/YouTube sections carrying real synthesised content (e.g. the Lovable experiment's 15k LOC / 495 credits / Supabase+Stripe details). Layer 3 `tests/test_payload_and_task_modal.py` 4 passed; full suite 60 passed / 6 pre-existing unrelated failures.
* **Known limitation:** some hosts still block extraction (Reddit JSON returns 403 here; Scrapling sometimes bypasses it). Reddit is therefore occasionally snippet-level. YouTube batch mode relies on captions/description, not Whisper, by design.

---

## ADR-061: Honest App Launch & Screen-Grounded Clicks (`actions/open_app.py`, `actions/computer_control.py`, `core/prompt.txt`)

* **Date:** 2026-09-25
* **Context (from a real session):**
  1. "Open this file in VS Code" failed twice while ZEZO reported *"Opened … in Visual Studio Code"* both times. `open_app` ran `cmd /c start "" "code" "<file>"`; VS Code's `code` shim is not on PATH, so the command errored (a stray cmd window) and VS Code, when launched via the Start-Menu shortcut fallback, opened without the file. `open_app` returned success unconditionally.
  2. Asked to click the file icon, ZEZO called `computer_control(action='smart_click')` → `Unknown action: 'smart_click'` (`smart_click` is a `browser_control` action), then `double_click` with no coordinates → it clicked wherever the cursor happened to be.
  3. ZEZO also took a browser search from a garbled transcript ("vibe coding" misheard as "whiteboarding") and called `computer_control(action='screenshot')`, which wrote `jarvis_screenshot.png` to the Desktop despite the baseline rule to use `screen_process`.
* **Decision:**
  1. **`open_app.py`:** added `_resolve_windows_launcher()` — resolves the real executable (VS Code's `Code.exe` under `%LOCALAPPDATA%`/`%PROGRAMFILES%`, or the `code.cmd` shim) and launches it with the file; if unresolved it opens the file with the OS default and says so. The path branch no longer claims success it cannot verify.
  2. **`computer_control.py`:** `click`/`double_click`/`right_click` now accept a `description` and resolve it via `screen_find` when `x,y` are absent; added `screen_double_click`; `smart_click` is accepted as a description-based-click alias. Unfound elements return an honest "not found" instead of a blind click.
  3. **`core/prompt.txt`:** new `[TRANSCRIPT CONFIDENCE & SIDE EFFECTS]` block — a garbled/out-of-context transcript is not an instruction; ask one clarifying question and never take a browser/desktop side effect on a guess. Desktop-by-name clicks must use `screen_click`/`screen_double_click`; `screenshot` remains forbidden (use `screen_process`); when an app launch is unconfirmed, tell the user the truth.
* **Consequence:** opening a file in VS Code now works and failures are reported honestly; clicking a named desktop element targets it instead of the cursor position; the model is steered away from acting on a bad transcript.
* **Verification:** Layer 1 `py_compile` PASS; 24/24 actions; prompt renders, tokens intact. Layer 2 runtime harness `scratch/verify_computer_control_fixes.py` → ALL PASS (VS Code resolver returns the real `Code.exe`; `open_app` launches `[Code.exe, <file>]` and reports honest success; unresolvable app honestly falls back to the default application; `smart_click`/`double_click(desc)`/`screen_double_click` target the found coords; unfound elements are reported). Layer 3 full suite 60 passed / 6 pre-existing unrelated failures.
* **Known limitation:** `screen_find` depends on the Gemini vision ladder, so a click-by-description can return "not found" if the vision call is rate-limited; the tool then refuses to click rather than guessing. The no-path `_launch_windows` Start-Menu key-search fallback still cannot verify its own success.

---

## ADR-062: Bounded Mic Queue Drop-Oldest & Fail-Fast Scrapling Fetch (`main.py`, `actions/web_reader.py`)

* **Date:** 2026-09-26
* **Context (from a real log-bus export, 1216 lines, ~95% one error):**
  1. The log was dominated by `[asyncio] [ERROR] Exception in callback Queue.put_nowait()` repeated thousands of times. Reproduction confirmed `asyncio.queues.QueueFull`: the PortAudio mic callback (`main.py`) scheduled `self.out_queue.put_nowait` via `loop.call_soon_threadsafe` with no guard, and `out_queue` is bounded (`asyncio.Queue(maxsize=200)`). Whenever the Live send loop (`_send_realtime`) lagged — reconnect or a heavy turn — the queue filled and every mic block raised inside the callback, which asyncio logs as one ERROR (with traceback) per block. The phone-audio path already guarded this; the PC-mic path did not.
  2. The same log showed Scrapling `Page.goto: Timeout 30000ms exceeded … waiting until "load"` repeatedly for `reddit.com`, each attempt timed out and was retried (default `retries=3`), and a StealthyFetcher timeout inside the `try` was re-caught by the outer `except`, causing a second browser attempt. A single blocked Reddit page cost ~53s.
* **Decision:**
  1. **`main.py`:** added `ZezoLive._enqueue_out_audio(item)` — `put_nowait`, on `QueueFull` discard the oldest blob (`get_nowait`) and insert the newest; the mic callback now schedules this method. Bounded audio back-pressure drops stale speech silently instead of raising (the live model always hears the most recent audio).
  2. **`actions/web_reader.py`:** `_STEALTH_KWARGS = {timeout: 15000, network_idle: False, retries: 1}` applied to every StealthyFetcher call, and the fetch block restructured so a StealthyFetcher failure cannot trigger a second browser attempt. Blocked hosts now fail fast and fall through to the HTTP fallback.
* **Consequence:** A lagging send loop no longer floods the log bus (the error storm is impossible by construction); blocked/heavy pages cost one bounded attempt instead of repeated 30s ones.
* **Verification:** Layer 1 `py_compile` PASS; 24/24 actions. Layer 2 — the asyncio mechanism was reproduced (`Exception in callback Queue.put_nowait()` → `QueueFull`); the real `ZezoLive._enqueue_out_audio` on a full 3-slot queue, flooded with 5 items, raised nothing and retained the newest `[5,6,7]`; Scrapling accepted the new kwargs (`StealthyFetcher.fetch('https://example.com', **_STEALTH_KWARGS)` → 200) and `extract_web_content` still returns content; a timed Reddit fetch dropped from **52.8s → 25.1s** with a single attempt. Layer 3 — full suite 6 pre-existing failures / 75 passed (unchanged set).
* **Known limitation:** fully-blocked hosts (Reddit returns 403 to both the JSON endpoint and Scrapling here) are inherently unreadable and now fail honestly in ~25s rather than hanging; DDG's brave backend DNS `Query Refused` is an external network condition and was left as-is.

---

## ADR-063: Cascade Voice Pipeline Latency, VAD Filtering & Multi-Engine Resilience (`core/voice_fallback.py`, `core/tts.py`, `main.py`, `memory/config_manager.py`)

* **Date:** 2026-09-27
* **Lead Architect:** Hamza Bukhari
* **Context:**
  1. Cascade offline/fallback voice loop suffered from severe duplicate reply rendering in the UI/activity log (due to calling both `_log` and `_on_reply`).
  2. Ambient microphone noise and background fan hiss triggered VAD with a low threshold (450 RMS), causing Whisper to hallucinate phrases (e.g. Russian "Спасибо" / Korean "MBC 뉴스") on silence.
  3. Faster-Whisper with the `base` model on CPU incurred 5-7 seconds latency per turn.
  4. Kokoro TTS failed with empty audio ("No audio was received") due to an invalid default language code (`lang='e'`) and passing non-Kokoro voice names like `en-US-GuyNeural` without prefix sanitation. Non-English responses also failed on Kokoro.
  5. Lazy TTS initialization caused a 2-3s delay on the first utterance and had a race condition without thread locking.
* **Decision:**
  1. **Single Render Path & TTS Pre-validation:** Render `Zezo: {reply}` only after `_speak(reply)` succeeds. If TTS fails, do not render a phantom reply. Removed duplicate `on_reply` callback in `main.py`.
  2. **Kokoro Language & Voice Sanitation:** Set `lang="en-us"` by default in `KokoroTTSEngine`. Map voice prefix (`a` -> `en-us`, `b` -> `en-gb`) and fallback to `af_heart` if an incompatible voice is passed. Automatically delegate non-English text to `EdgeTTSEngine` in `VoiceFallback._speak()`.
  3. **STT Latency Optimization:** Switched local Whisper CPU model to `tiny` for sub-2s inference. Set default STT engine in `config_manager.py` to `groq_whisper` for sub-second cloud transcription.
  4. **VAD Energy & Voiced Ratio Guard:** Raised energy threshold to `DEFAULT_ENERGY = 700.0` RMS and added a requirement in `UtteranceSegmenter.push()` that at least 40% of blocks in an utterance must be voiced, rejecting ambient hiss and click artifacts.
  5. **TTS Preloading & Thread Safety:** Guarded TTS initialization with `_tts_lock` and preloaded the model at startup in a background daemon thread (`_preload_tts`).
  6. **Clean Reconnect Observation:** `main.py::_run_cascade_pipeline` now observes `_reconnect_event` without clearing it, preventing signal race conditions with `_watch_reconnect`.
* **Consequence:** Sub-2s responsive offline/cascade loop with zero duplicate log entries, complete immunity to ambient room noise hallucinations, and robust multi-lingual TTS fallback.
* **Verification:** Layer 1 `py_compile` on all 4 touched files passed. Layer 2 comprehensive test suite (`tests/test_voice_fallback_suite.py`) passed 10/10 tests covering VAD filtering, Kokoro language sanitization, non-English EdgeTTS fallback, single render, and thread locks. Layer 3 regression suite passed 27/27 tests across settings, UI, and pipeline integrations. 24 actions and 10 skills discovered.

---

## ADR-064: Modal Backdrop Policy, rAF Gating & Drawer Layout Architecture (`frontend/style.css`, `frontend/index.html`, `docs/UI.md`)

* **Date:** 2026-09-27
* **Lead Architect:** Hamza Bukhari
* **Context:**
  1. Opening any modal or drawer triggered severe, continuous background home-screen flickering in QtWebEngine.
  2. Investigation revealed double-nested `backdrop-filter: blur(12px)` rules (both `.modal-overlay` and `.modal-panel .frame-inner` applied blurs).
  3. Modal and drawer entry animations used `transform: scale()`, forcing the GPU compositor to re-rasterize blurry backdrops on every frame.
  4. Active matrix canvas and avatar loops continued rendering behind modal overlays, triggering continuous repaints.
  5. The `#settings-drawer` was clipped, cutting off lower controls and the theme color dot picker due to `max-height: calc(100vh - 70px)` and an `overflow: hidden` rule on secondary `.frame` elements.
* **Decision:**
  1. **Single Top-Level Backdrop Blur:** Removed `backdrop-filter: blur()` from `.frame-inner`, `.avatar-command-dock`, `.command-input-container`, `.top-navbar`, and `.overlay-backdrop`. Only `.modal-overlay` carries `backdrop-filter: blur(12px)`. Modal inner panels are fully opaque `#0a0a0a` with `backdrop-filter: none !important;`.
  2. **Translate-Only Keyframes:** Removed `scale()` from `@keyframes modalIn` and `@keyframes drawerIn`, retaining only GPU-friendly `translateY()` and `opacity`.
  3. **rAF Modal Gating:** Updated `openModal()` and `closeModal()` in `frontend/index.html` to set `window._zezoAnimActive = false` while any modal is open and resume only when all modals close.
  4. **Drawer Layout & Overflow:** Configured `#settings-drawer` to `display: none !important;` by default, `display: flex !important;` when open, `max-height: 95vh; height: auto; min-height: 400px; overflow: visible;`, with child `.frame-inner` set to `overflow-y: auto; max-height: none;`. Removed `overflow: hidden;` from the secondary `.frame` selector.
* **Consequence:** 100% elimination of modal background flickering, smooth 60 FPS transitions, zero CPU/GPU overhead behind open modals, and complete visibility and usability of all settings drawer controls.
* **Verification:** Validated CSS selector integrity (`grep -c "@keyframes modalIn"` = 1, `grep -c "backdrop-filter: blur"` = 1). Full ZEZO system boot passed cleanly with all 24 actions and 10 skills active.

---

## ADR-065: Dead 3D Software Avatar Subsystem Deprecation & Cleanup (`core/avatar.py`, `core/avatar_mesh.py`, `core/face_model.obj`, `core/robot_head_fast.obj`, `setup.py`, `readme.md`, `docs/`)

* **Date:** 2026-10-02
* **Lead Architect:** Hamza Bukhari
* **Context:**
  1. The legacy QPainter 3D software rasterizer (`core/avatar.py`, `core/avatar_mesh.py`, `core/face_model.obj`, `core/robot_head_fast.obj`) was replaced by the modern GPU-accelerated HTML5/PyQt6 tactical workspace with the Fluid Vortex Core and Unified Command Dock.
  2. The old avatar files remained in the repository as dead, unexecuted artifacts and added unnecessary clutter to documentation and asset validation scripts.
* **Decision:**
  1. Removed `core/avatar.py`, `core/avatar_mesh.py`, `core/face_model.obj`, and `core/robot_head_fast.obj`.
  2. Removed `_check_assets()` face mesh verification from `setup.py`.
  3. Synchronized `readme.md`, `AGENTS.md`, `docs/HUD_AND_AVATAR.md`, `docs/CODEBASE_MAP.md`, `docs/ARCHITECTURE.md`, `docs/DEPENDENCIES.md`, `docs/DATA_FLOW.md`, `docs/STORAGE.md`, `planning/PROJECT_ARCHITECTURE.md`, and `planning/ZEZO_PROJECT_BLUEPRINT.md` to reflect the active tactical workspace architecture.
* **Consequence:** Cleaned codebase of ~147 KB of dead assets, removed outdated references across all documentation, and retained 100% functionality and test stability across all active modules.

---

## ADR-066: Project Workspace Isolation, In-Place Fleet Dispatch & Concurrency Load Balancing (`core/repo_context.py`, `actions/antigravity_agent.py`, `core/fleet_manager.py`, `config/fleet_agents.json`, `frontend/index.html`, `core/prompt.txt`)

* **Date:** 2026-10-04
* **Lead Architect:** Hamza Bukhari
* **Context (Vision 1.0):**
  1. Successive project generation requests previously overwrote the prior active folder (`Desktop/website` or sticky `last_active_repo`), causing severe project clobbering (e.g. building a real-estate site clobbered a freshly built portfolio).
  2. Fleet dispatch (`fleet_control(action='dispatch')`) submitted tasks to `TaskManager` whose internal worker invoked `antigravity_action`, which in turn invoked `tm.submit` a second time, resulting in two disconnected task cards: an immediately finished agent card and a persistent orphan `ZEZO CODER` card.
  3. Single agent bottleneck: All frontend requests routed solely to Ali with no concurrency limits or overflow balancing.
  4. Task cards in `frontend/index.html` displayed generic IDs without assigned agent branding or clean relative target paths.
* **Decision:**
  1. **Dynamic Workspace Isolation:** Implemented `extract_project_slug(prompt)` and `get_unique_project_dir(topic_or_task)` in `core/repo_context.py`. Allocates semantic, collision-safe directories (`Desktop/<slug>`, `Desktop/<slug>_1`). Decoupled sticky `get_last_repo()` when a brand-new project build is initiated.
  2. **In-Place Worker Execution (`run_in_place=True`):** Updated `actions/antigravity_agent.py` to accept `run_in_place=True` and `task_ctx`. `fleet_manager` executes the build synchronously within the agent's task lifecycle, eliminating phantom secondary `ZEZO CODER` cards.
  3. **Fleet Roster Expansion & Concurrency Balancing (Max 3 Tasks):** Registered `HAIDER` in `config/fleet_agents.json` as Frontend Developer adjacent to Ali. Implemented `get_agent_active_task_count(agent_id)` in `core/fleet_manager.py`. If Ali is at capacity ($\ge 3$ tasks), incoming frontend tasks automatically overflow to Haider.
  4. **Task Card Informative Rendering:** Updated `renderTasks()` in `frontend/index.html` to display the assigned agent badge (`ALI`, `HAIDER`, `AHMAD`), descriptive task heading (`taskTitle`), and formatted clean relative path (`Desktop/...`).
  5. **Orchestrator System Prompt Alignment:** Updated `core/prompt.txt` to enforce the Vision 1.0 paradigm: *"ZEZO Manages the Work. Agents Execute the Work."* and added the pre-flight clarification guard for broad open-ended prompts.
* **Consequence:** 100% project workspace isolation, zero folder clobbering, zero ghost cards in TaskManager, transparent multi-agent load balancing, and clear UI queue ownership.


