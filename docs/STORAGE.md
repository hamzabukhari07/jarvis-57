# 💾 ZEZO — Storage & Filesystem Inventory

> **Creator & Lead Architect:** Hamza Bukhari  
> **System Component:** Local Storage Architecture, Memory Databases & External Workspaces  
> **Core Principle:** 100% Local-First. Zero reliance on proprietary cloud storage or external vector clouds.  

---

## 📖 1. Overview & Data Flow

All operational state, memory databases, configurations, and generated code artifacts reside exclusively on the host filesystem. Data is segregated into:
1. **Core Runtime Configuration (`config/`):** API credentials, fleet agent definitions, and MCP configurations.
2. **Hybrid 3-Tier Memory Engine (`memory/`):** Fast JSON profile priming, SQLite WAL + FTS5 database, and local Markdown knowledge vault.
3. **External Desktop Workspaces (`~/Desktop/...`):** Isolated directories for heavy web captures, reverse-engineering teardowns, and application rebuilds.
4. **Declarative Skills Directory (`skills/`):** Modular capability packages.

---

## 🗄️ 2. Complete Storage Inventory

### 2.1. Configuration & Credentials

| Storage Item | Location | Format | Purpose | Security & Git Status |
| :--- | :--- | :--- | :--- | :--- |
| **API Keys & Toggles** | `config/api_keys.json` | JSON | Google Gemini, Groq, and ElevenLabs API keys; assistant name, voice persona, autostart, and brief mode flags. | **Git-Ignored.** Treated as sensitive credentials. |
| **Fleet Roster & Worktrees**| `config/fleet_agents.json` | JSON | Fleet agent registry, Scranton office desk coordinates, LLM engine assignments, and risk tiers. | Tracked in Git (defaults). Local overrides preserved. |
| **MCP Server Config** | `config/mcp_servers.json` | JSON | Model Context Protocol server registrations and execution paths. | **Git-Ignored.** |
| **Skills State** | `config/skills_state.json`| JSON | Enabled/disabled states and scan hashes for discovered skill packages. | **Git-Ignored.** |

---

### 2.2. Hybrid 3-Tier Memory Storage

| Memory Tier | Storage Path | Format / Engine | Description & Limits | Access / Read Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Core Profile** | `memory/long_term.json` | JSON (`memory_manager.py`) | User preferences, relationships, active projects, and core identity. Runaway guard: 200,000 chars. | Loaded into Gemini Live prompt at boot (900 chars core + 420 chars index). |
| **Tier 2: Verbatim History** | `memory/zezo_brain.db` | SQLite WAL + FTS5 (`sqlite_memory.py`) | Turn-by-turn chronological transcript, secret-redacted utterances, tool arguments, facts, and conflicts. | Accessed via `recall_history` tool (`search`, `expand`, `recent`) and REST API. |
| **Tier 3: Local Vault** | `memory/vault/*.md` | Markdown + YAML (`vault_engine.py`) | Human-readable notes with `[[wikilinks]]` topology. Distilled conversation summaries. | Feeds the interactive 3D Force-Directed Knowledge Graph (`MemoryGraphCanvas.tsx`). |
| **Repo Context Cache** | `memory/repo_context.json`| JSON | Active repository paths and working directories. | Synchronized by `core/repo_context.py`. |

> [!IMPORTANT]
> All SQLite database writes in Tier 2 automatically scrub sensitive tokens (Google API keys, GitHub PATs, Bearer tokens, passwords, cookies) before persistence using `redact_secrets()`.

---

### 2.3. External Desktop Workspaces

To prevent repository pollution and ensure safe blast-radius boundaries, all code generation, website cloning, and teardowns are routed to dedicated workspaces on the user's Desktop:

| Workspace Path | Generator Module | Purpose & Content | Lifecycle |
| :--- | :--- | :--- | :--- |
| `~/Desktop/ZEZO_Teardowns/` | `core/teardown_engine.py` / `actions/reverse_engineer.py` | REA teardown evidence envelopes: `evidence.json`, `blueprint.md`, `ledger.json`, screenshots, and raw network traces. | Permanent until user cleanup. Served by Vite preview server (:3000). |
| `~/Desktop/<project>_rebuild/` | `actions/reverse_engineer.py` | Full-stack application rebuilds scaffolded by specialist agents from teardown blueprints. | Active development workspace. |
| `~/Desktop/<domain>_clone/` | `actions/website_cloner.py` (`clone_website`) | Uncage offline static capture (`index.html`, `assets/`, `antigravity_clone.html`, `asset-map.json`). | Preserved offline copy. Served by ephemeral preview server (:9400–9480). |
| `~/Desktop/<domain>_clone/rebuilt.html` | `actions/website_cloner.py` (v6 Rebuild) | Single-file reverse-engineered rebuild created directly alongside capture assets. | Produced when `output_format="raw_html"`. |
| `~/Desktop/<domain>_clone/rebuilt_app/` | `actions/website_cloner.py` (v6 Rebuild) | Multi-file framework rebuild (React, Next.js, PHP, custom). | Produced when `output_format` is a project framework. |

---

### 2.4. Skills & Capability Storage

| Storage Item | Location | Format | Purpose |
| :--- | :--- | :--- | :--- |
| **Declarative Skills** | `skills/<skill_name>/SKILL.md` | Markdown + YAML | User-defined and autonomous learned capability packages. Inspected at startup by `skill_loader.py`. |
| **Built-in CLI Skills** | `builtin/skills/` | Markdown + YAML | Default system skill capabilities. |

---

### 2.5. Cache, Models & Telemetry

| Resource | Path | Format | Description |
| :--- | :--- | :--- | :--- |
| **Playwright Browsers** | System cache (`~/.cache/ms-playwright/` or `%LOCALAPPDATA%`) | Binaries | Headless Chromium and Firefox engines for Uncage and REA browser automation. |
| **Wake Word Models** | `config/wakewords/` | ONNX / TFLite | Real-time wake word models ("Hey Zezo", "Jarvis") for openWakeWord detection. |
| **Telemetry & Log Bus** | Ephemeral memory (`core/ui_server.py`) | In-Memory Ring Buffer | Log bus messages streamed over WebSocket to `BackendLogModal.tsx`. Zero disk growth. |

---

## 🔒 3. Storage Security & Concurrency Invariants

1. **Thread-Safe File Access:** All JSON file reads and writes (`api_keys.json`, `long_term.json`) are guarded by dedicated `threading.Lock()` instances.
2. **SQLite WAL Concurrency:** `memory/zezo_brain.db` operates in Write-Ahead Logging (`WAL`) mode, allowing concurrent reads from frontend API endpoints while the background live loop logs conversation turns.
3. **Exclusion from Version Control:** All sensitive credentials, personal memories, temporary teardown directories, and database files are excluded from Git via `.gitignore`:
   ```gitignore
   config/api_keys.json
   config/mcp_servers.json
   config/skills_state.json
   memory/long_term.json*
   memory/*.db*
   memory/vault/
   ```
