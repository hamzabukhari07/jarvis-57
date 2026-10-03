---
name: antislop_code
description: Pure code hygiene, architectural minimalism, and anti-overengineering standards for ZEZO / JARVIS. Strips generic AI comments, prevents bloated boilerplate, enforces low cyclomatic complexity (<15), and mandates clean, idiomatic, production-grade Python and JavaScript.
---

# 🧹 Anti-Slop Code Hygiene & Architecture Standard

This skill governs all code generation, refactoring, and file modification workflows across the ZEZO / JARVIS codebase. It ensures every line of code is clean, minimal, production-grade, and free of AI-generated boilerplate or speculative complexity.

---

## 🎯 Core Engineering Principles

1. **Simplicity Over Cleverness (KISS):** Write the most direct, readable, and maintainable implementation that fulfills the exact requirements.
2. **You Aren't Gonna Need It (YAGNI):** Do not create speculative abstractions, unnecessary generic interfaces, or anticipatory helper methods for hypothetical future use cases.
3. **Minimal Blast Radius:** Make the smallest coherent set of edits required. Avoid sweeping unrelated refactors or formatting changes in untouched sections of files.
4. **Standard Library & Native First:** Prefer Python's standard library (`pathlib`, `subprocess`, `asyncio`, `threading`, `dataclasses`) and native Web APIs over introducing external utility dependencies.
5. **Architectural Consistency:** Match existing patterns in the codebase (action loader dictionaries, thread-safe manager patterns, PyQt6 signals, centralized log bus).

---

## 🚫 1. What to NEVER Write (AI Code Slop)

### 1. Decorative Separators & Box Banners
- ❌ **Do NOT write:**
  ```python
  # ==========================================
  #                TASK MANAGER ENGINE
  # ==========================================
  # ------------------------------------------
  # Helper Functions
  # ------------------------------------------
  ```
- ✅ **Instead:** Use clean Python whitespace (two blank lines between top-level functions/classes) and clear naming.

### 2. Restating the Obvious (Echo Comments)
- ❌ **Do NOT write:**
  ```python
  # Set timeout to 10 seconds
  timeout = 10
  # Return the response object
  return response
  # Initialize the task list
  tasks = []
  # Import required modules
  import os
  ```
- ✅ **Instead:** Let clean, self-describing variable and function names speak for themselves. Omit obvious comments entirely.

### 3. Step-by-Step Narration
- ❌ **Do NOT write:**
  ```python
  # Step 1: Validate input parameters
  # Step 2: Query the database
  # Step 3: Format the output
  # Step 4: Return result
  ```
- ✅ **Instead:** Break complex workflows into focused, well-named private subroutines (e.g. `_validate_params()`, `_query_records()`, `_format_payload()`).

### 4. Vague Placeholders & Fake TODOs
- ❌ **Do NOT write:**
  ```python
  # TODO: Optimize this later
  # Note: This is important logic
  # In a production app, you should handle errors here
  ```
- ✅ **Instead:** Implement robust error handling immediately, or document the exact architectural constraint requiring deferral.

### 5. Redundant Defensive Wrappers & Speculative Layers
- ❌ **Do NOT write:** 4 layers of class indirection (`BaseAbstractTaskHandlerFactoryManager`) when a single module-level function or simple class is required.
- ✅ **Instead:** Use direct function calls or simple dataclasses.

---

## ✅ 2. What Comments ARE Mandatory (High-Value Rationale Only)

Write comments ONLY when explaining **non-obvious rationale, hardware/OS quirks, critical safety gates, or third-party workarounds**:

```python
# Windows requires CREATE_NO_WINDOW to prevent intrusive terminal popup on background child process
creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# pycaw endpoint volume requires AudioUtilities.GetSpeakers() (deprecated .Activate() crashes on Win11)
volume = AudioUtilities.GetSpeakers().EndpointVolume

# Embedded KùzuDB is single-process; check lock before query to avoid database corruption
if _is_locked(db_path):
    return fallback_search(query)
```

---

## ⚡ 3. Architecture & Complexity Thresholds

1. **Cyclomatic Complexity Cap (< 15):**
   - Every individual function must maintain a cyclomatic complexity score under **15**.
   - If a function contains nested loops and multiple branches, decompose it into focused helper functions.

2. **Dictionary Dispatch Over Giant `if/elif` Chains:**
   - When routing 4+ actions or commands, use a dictionary dispatch table instead of repetitive `if/elif` ladders:
   ```python
   # ✅ Good: Dictionary dispatch
   DISPATCH_TABLE = {
       "dispatch": _handle_dispatch,
       "hire": _handle_hire,
       "fire": _handle_fire,
       "list_agents": _handle_list,
       "get_status": _handle_status,
   }
   handler = DISPATCH_TABLE.get(action)
   if not handler:
       return {"success": False, "error": f"Unknown action: {action}"}
   return handler(params)
   ```

3. **Explicit Error Handling & Safe Fallbacks:**
   - Catch specific exceptions (`FileNotFoundError`, `TimeoutError`, `json.JSONDecodeError`) rather than catching bare `Exception` where possible.
   - When catching broad exceptions at subsystem boundaries, log the exception context to `core.log_bus` with full traceback.

4. **Resource Management (RAII):**
   - Always manage files, sockets, locks, and process handles with context managers (`with`, `async with`).

5. **Type Safety & Clean Contracts:**
   - Use Python type annotations (`str`, `dict[str, Any]`, `Optional[Path]`) on public function signatures.
   - Ensure action tools export a fully formed `TOOL` schema dictionary with required parameter lists and descriptive property fields.

---

## 🔒 4. Enforcement & Integration Rules

- **Automatic Trigger:** This standard is automatically enforced whenever code is authored, refactored, or reviewed within the `implementation` skill.
- **Pre-Commit Self-Audit:** Before presenting completed code, review your diff against the Anti-Slop checklist.
- **Zero Regression on Existing Code:** When modifying an existing file, clean up slop in the immediate lines you touch without disturbing unrelated working logic.
