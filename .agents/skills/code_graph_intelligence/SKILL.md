---
name: code_graph_intelligence
description: Query and analyze ZEZO's code graph using CodeGraphContext (CGC) with KùzuDB backend. Use when inspecting dependencies, tracing call chains, finding callers before refactoring, assessing blast radius, or hunting architectural complexity.
---

# 🧠 Code Graph Intelligence Skill (ZEZO Architecture Assistant)

This skill enables Antigravity and ZEZO agents to query the indexed knowledge graph of the repository to ensure zero-regression refactoring, trace call chains, locate symbols, and compute cyclomatic complexity before modifying files.

---

## 🔍 Core Responsibilities

1. **Symbol Discovery:** Locate where functions, classes, models, and action tools are defined across `core/`, `actions/`, `memory/`, and `ui.py`.
2. **Blast Radius Analysis:** Identify every caller and downstream consumer of a function before altering its signature or behavior.
3. **Complexity Hotspot Detection:** Measure cyclomatic complexity to identify functions that violate the Anti-Slop threshold (< 15).
4. **Architectural Verification:** Verify that proposed integrations do not create circular dependencies or orphaned components.

---

## 🛠️ Query Interface & Commands

Run queries via PowerShell commands in `run_command` using the UTF-8 environment wrapper:

### 1. Blast Radius & Callers Check (Mandatory Pre-Flight)
Find every function across the entire project that calls target `<function_name>`:
```powershell
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <function_name>
```

### 2. Find Symbol Definition & Location
Quickly locate where a function or class is defined without full-text grep noise:
```powershell
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb find name <symbol_name>
```

### 3. Check Cyclomatic Complexity
Analyze function complexity across the repository:
```powershell
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze complexity
```

### 4. Search Code Content Graph
Search content across indexed AST nodes:
```powershell
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb find content "<query>"
```

### 5. Re-index / Update Graph After Major Changes
Sync the graph after introducing new files or major refactoring:
```powershell
$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb update
```

---

## ⚡ MCP Tool Reference (OpenCode / Native MCP Environments)

When running in an environment with the `codegraph` MCP server enabled, prefer MCP tools for sub-millisecond query responses:

| MCP Tool | Primary Use Case |
| :--- | :--- |
| `codegraph_find_code` | Locate a symbol definition or search code content |
| `codegraph_analyze_code_relationships` | Enumerate callers and callees — primary blast radius tool |
| `codegraph_calculate_cyclomatic_complexity` | Compute complexity score for a target function |
| `codegraph_find_most_complex_functions` | Identify functions violating the Anti-Slop threshold (>15) |
| `codegraph_find_dead_code` | Discover unreferenced functions or orphaned helpers |
| `codegraph_execute_cypher_query` | Run custom Cypher graph queries |
| `codegraph_list_indexed_repositories` | Confirm graph freshness and repository indexing status |

---

## 🛡️ Pre-Flight Protocol & Failure Handling

### Step 1: Query Before Modification
Before modifying any shared function in `core/` or `actions/`:
1. Find symbol and verify location: `cgc -db kuzudb find name <symbol>`.
2. Enumerate all callers: `cgc -db kuzudb analyze callers <symbol>`.
3. Inspect only the files identified in the call path.

### Step 2: Single-Owner Database Lock Fallback
- **Lock Error Behavior:** If `cgc` returns `Could not set lock on file` or database busy error, the embedded KùzuDB file is locked by an active background watcher or another process.
- **Strict Rule:** Do NOT retry in a loop, do NOT attempt to kill parent processes, and do NOT modify database files directly.
- **Immediate Fallback:** Fall back to native `grep_search` and `view_file` immediately, and note in your report: *"Code Graph lock active; falling back to static AST and grep search."*

### Step 3: Graph as Navigator, Source as Ground Truth
- The Code Graph provides structural navigation and dependency maps.
- Always read the actual lines in the source file via `view_file` to confirm the exact parameter signatures and runtime behavior before making edits.
