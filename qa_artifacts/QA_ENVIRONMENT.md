# QA Environment Report: ZEZO Autonomous Desktop AI Assistant

**Lead Architect:** Hamza Bukhari  
**Date & Time:** November 4, 2026  
**Environment Evaluation Scope:** End-to-End Functional QA Test Environment  

---

## 1. Operating System & Host Environment
- **Operating System:** Windows 11 Enterprise (Version 10.0.26100, SP0, x86_64)
- **Primary Shell:** PowerShell 5.1 / PowerShell 7
- **Target OS Priority:** Windows (Primary), macOS, Linux
- **Sandbox Container / Containment:** Win32 Job Objects (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `CREATE_SUSPENDED`, `CREATE_NO_WINDOW`) + Application-Level `PathJail` (NTFS canonicalization & symlink/junction boundary checking).

---

## 2. Python Runtime & Core Toolchain
- **Python Version:** 3.14.0 (`tags/v3.14.0:ebf955d`, MSC v.1944 64-bit AMD64)
- **Python Binary Path:** `C:\Python314\python.exe`
- **Pytest Suite:** Installed and verified (`pytest 9.0.3` / `136 passed, 1 warning in 31.56s`)
- **Node.js / NPM Toolchain:** Installed (`node`, `npm`, `npx`)
- **Frontend Compiler:** TypeScript 5.x (`tsc -b`), Vite 5.x (`npm run build`)
- **Frontend Target:** React 19 + ReUI / Tailwind CSS

---

## 3. Database & Persistence Layer
- **Database Engine:** SQLite 3.50.4 (WAL Mode Enabled)
- **Primary Database File:** `memory/zezo_brain.db`
- **WAL Pragma Configuration:**
  - `journal_mode = WAL`
  - `busy_timeout = 10000` (10 seconds)
  - `synchronous = NORMAL`
- **Tables Evaluated:**
  - `agent_conversations` (Thread hierarchy, metadata, timestamps)
  - `agent_messages` (Multimodal and turn-level chat history)
  - `turns` (Memory event log)
  - `turns_fts` (FTS5 virtual table for BM25 ranking and search)
  - `internal_task_ledger` (Task state tracking, restart flags, monotonic transitions)
  - `memory_conflicts` (Conflict resolution ledger)
  - `session_condensations` (Session summarization checkpoints)
  - `deleted_fact_tombstones` (Anti-resurrection tombstone table)

---

## 4. External Execution Engines Status
| Engine | Binary Resolved Path | CLI Version / Status | Job Object Containment |
|---|---|---|:---:|
| **Antigravity** | `C:\Users\Hamza Bukhari\AppData\Local\agy\bin\agy.EXE` | `1.4.12` | Verified Active |
| **OpenCode** | `C:\Users\Hamza Bukhari\AppData\Roaming\npm\opencode.CMD` | `2.2.5` | Verified Active |
| **Kilo Code** | `C:\Users\Hamza Bukhari\AppData\Roaming\npm\kilo.CMD` | `7.8.18` (Authenticated) | Verified Active |

---

## 5. Security & Isolation Controls
- **Application Path Containment:** `core/path_jail.py` strictly verifies canonical workspace roots (`os.path.realpath`, `Path.resolve`), blocking directory traversals (`../`), UNC paths, and symlink/junction escapes.
- **Privilege Separation:** `core/tool_executor.py` CallerContext enforcing `L0_READ_ONLY`, `L1_MUTATION`, and `L2_DESTRUCTIVE` security tiers.
- **Process Supervision:** `core/engines/process_supervisor.py` spawning all external engines inside dedicated Win32 Job Objects.
- **Secret Redaction:** `core/engines/adapter.py::redact_sensitive_tokens` masking API keys, Authorization headers, Bearer tokens, and reasoning tokens.

