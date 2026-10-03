# 🧠 Code Graph & Anti-Slop Mandatory Pre-Flight Protocol

## 🛡️ Non-Negotiable Pre-Flight Enforcement for All Tasks

Whenever the AI agent is asked to **debug, refactor, add new features, investigate errors, or modify code**, it MUST execute the following pre-flight routine BEFORE proposing or writing any code changes:

---

### Step 1: Code Graph Query (CGC MCP Server)
- Before modifying, refactoring, or debugging any function or module, query the code graph using the `codegraph` MCP server.
- In **opencode**, MCP tools are namespaced with the server name as prefix, so call `codegraph_execute_cypher_query` (NOT bare `execute_cypher_query`, and NOT `call_mcp_tool` — that was the Antigravity convention and does not exist here).
  - **Find Callers & Blast Radius:**
    ```cypher
    MATCH (caller:Function)-[:CALLS]->(target:Function) WHERE target.name = '<function_name>' RETURN caller.name, caller.path
    ```
  - **Trace Function Dependencies & Structure:**
    ```cypher
    MATCH (f:Function) WHERE f.path CONTAINS '<file_name>' RETURN f.name, f.path
    ```
- Prefer the dedicated tools over raw Cypher where possible: `codegraph_find_code`, `codegraph_analyze_code_relationships`, `codegraph_calculate_cyclomatic_complexity`, `codegraph_find_dead_code`, `codegraph_list_indexed_repositories`.
- If no `codegraph_*` tool is available, fall back to the CLI: `cgc -db kuzudb analyze callers <fn>`, `cgc -db kuzudb find name <symbol>`, `cgc -db kuzudb find content "<query>"`.
- On `Could not set lock on file`, the embedded KùzuDB is owned by another process. Do not retry; use `grep`/`glob` and say so.
- Verify what other modules depend on the code being changed to prevent unintended side effects or regressions.

> **Note:** this file is reference material and is NOT auto-loaded into agent context. The enforceable copy of this rule lives in `AGENTS.md` §9, which opencode loads automatically.

---

### Step 2: Anti-Slop Code Hygiene Standard
- Every Python file created or modified must strictly adhere to `.agents/skills/antislop_code/SKILL.md`:
  - **No Monolithic If-Elif Ladders:** Use dictionary dispatch tables (`_ACTION_ROUTER = {...}`) or specialized handler functions.
  - **Cyclomatic Complexity Limit:** Keep function complexity strictly **< 15**.
  - **No AI Slop / Boilerplate Comments:** Strip generic comments like `# check if None`, `# loop through items`, or ASCII art comment boxes.
  - **Type Annotations & Clean Signatures:** Preserve exact parameter contracts (`parameters: dict = None, response=None, player=None, session_memory=None`).

---

### Step 3: Strict 3-Layer Verification
- **Layer 1 (Static):** Run `python -m py_compile` and verify action discovery.
- **Layer 2 (Runtime):** Test handler invocation and check real log output.
- **Layer 3 (Regression & Ledger):** Update `LEARNING_JOURNAL.md` with an ADR entry.
