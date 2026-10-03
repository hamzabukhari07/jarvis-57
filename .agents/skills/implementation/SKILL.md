---
name: implementation
description: Execute approved technical implementation plans, code features, refactor subsystems, and apply bug fixes for ZEZO / JARVIS. Enforces mandatory antislop_code standards, minimizes blast radius, updates documentation, and executes pre/post-flight verification.
---

# ⚡ Implementation & Engineering Execution Workflow

This workflow skill is activated to execute an **approved technical plan**, code a new capability, implement a bug fix, or perform an authorized refactor in the **ZEZO / JARVIS** repository.

It enforces **`antislop_code`** as a mandatory, automated coding standard, follows **`AGENTS.md`** non-negotiable rules, and coordinates with **`code_graph_intelligence`** and **`verification`**.

---

## 🎯 When to Trigger

Activate this skill ONLY when:
- The user explicitly instructs code implementation (e.g. *"Implement Phase 1"*, *"Build this feature"*, *"Apply the fix"*).
- An implementation plan (`feature_planning`) has been approved by the user.
- A bug fix has been explicitly authorized for execution.

---

## 🔄 Step-by-Step Implementation Procedure

```
[ 1. PLAN & RULES AUDIT ] ──► Review target plan, AGENTS.md rules, and touched file boundaries.
            │
[ 2. GRAPH IMPACT CHECK ] ──► Run `code_graph_intelligence` callers query on affected symbols.
            │
[ 3. CODE AUTHORING ] ──► Write minimal, focused code strictly adhering to `antislop_code`.
            │
[ 4. DOC & SCHEMA SYNC ] ──► Update TOOL schemas, prompt.txt, and docs/<FILE>.md in sync.
            │
[ 5. LOCAL STATIC PASS ] ──► Run `python -m py_compile` and action discovery immediately.
            │
[ 6. HAND OFF TO VERIFY ] ──► Transition to `verification` for Layer 2 & 3 checks.
```

### 1. Pre-Flight Preparation & Blast Radius Check
- Re-read the approved plan (`planning/PLAN_<NAME>.md`) and relevant sections of `AGENTS.md`.
- Inspect target files using `view_file`.
- Run Code Graph caller query on any functions/classes whose signatures or behaviors will change:
  ```powershell
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <symbol_name>
  ```

### 2. Mandatory Anti-Slop Code Hygiene Enforcement
Every line of code authored MUST comply with `.agents/skills/antislop_code/SKILL.md`:
- **No AI Box Banners / Decorative Comments:** Use clean whitespace.
- **No Echo Comments:** Delete comments that merely restate the code.
- **Complexity Cap (< 15):** Decompose complex methods into clean, focused subroutines.
- **Dictionary Dispatch:** Use table dispatch over lengthy `if/elif` chains.
- **Standard Library First:** Leverage native Python primitives before external packages.
- **Zero Speculative Indirection:** Do not create abstract factories or unused generic classes.

### 3. Modularity & Tool Registration Rules
- **One File Per Action:** If adding a tool, create `actions/<tool_name>.py` exporting `TOOL = {...}` and a callable `handler(parameters: dict, **kwargs)`.
- **Never Block Main Thread:** Wrap long-running operations in `TaskManager` or background `QThread`.
- **Async Task ID Contract:** Coding agents and long tasks must return `{"status": "queued", "task_id": "..."}` immediately.
- **Never Speak Raw Data:** Voice output must remain concise conversational summaries; large payloads must route to clipboard or HUD.

### 4. Mandatory Documentation Synchronization (Inter-Dependency Matrix)
Whenever code is modified, update corresponding documentation in the same turn:
- If an action in `actions/` is modified $\to$ update `docs/TOOLS.md` and `core/prompt.txt`.
- If a core engine is changed $\to$ update `docs/<ENGINE>.md` and `AGENTS.md`.
- If settings or configuration change $\to$ update `docs/CONFIGURATION.md`.

---

## 🛡️ Scope Control & Safety Boundaries

- **Minimal Blast Radius:** Modify only the files and lines required to satisfy the approved task.
- **No Unrelated Refactoring:** Do not reformat or clean up untouched files outside the immediate scope.
- **Material Scope Change Gate:** If an unexpected architectural roadblock or breaking change is discovered during implementation:
  1. STOP modifying code immediately.
  2. Report the finding clearly to the user.
  3. Propose options and await explicit approval before expanding scope.
