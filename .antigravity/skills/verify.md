# Skill: verify

**Never trust "done" without runtime evidence.** Unit tests and compilation are necessary but NOT sufficient. You must verify real execution before marking any task as complete.

---

## 🛡️ 3-Layer Verification Architecture

```
[ Code Change ]
       │
       ├──► Layer 1: Static Checks (py_compile, imports, action discovery)
       │
       ├──► Layer 2: Runtime Evidence (Actual execution logs, real output files, API responses)
       │
       └──► Layer 3: Regression Checks (Verify 2+ existing features remain intact)
```

---

## 🧪 Verification Pipeline (Execute in Order)

### 🔹 Layer 1: Static Checks (Zero Syntax / Import Errors)

1. **Compilation Check:**
   ```bash
   python -m py_compile <path/to/modified_file.py>
   ```
2. **Clean Import Check:**
   ```bash
   python -c "import <modified_module>; print('IMPORT OK')"
   ```
3. **Action Discovery Check (if `actions/` modified):**
   ```bash
   python -c "from pathlib import Path; from core.action_loader import discover_actions; reg = discover_actions(Path('actions'), set(), print); print('Active actions count:', len(reg._actions))"
   ```

---

### 🔹 Layer 2: Runtime Evidence (Mandatory Execution Proof)

**Unit tests are not runtime tests.** You MUST execute the real action/feature and provide raw runtime artifacts:

1. **Real Input Execution:**
   - Execute the actual tool handler or entrypoint with real files, real inputs, and actual parameters.
   - Run the relevant command or script simulating real user invocation.
2. **Log Verification:**
   - Capture and paste raw stdout / log lines from `FileReader`, `TaskManager`, or `Gemini`.
3. **Output & Artifact Inspection:**
   - Check created/modified files on disk, inspect byte lengths, or verify generated Markdown/JSON payloads.

> [!CAUTION]
> **No Runtime Evidence = UNVERIFIED.**  
> If you cannot execute runtime tests (e.g., missing physical hardware, live credentials, or external API outage), you MUST report **`STATUS: UNVERIFIED`** with the exact reason. You are strictly forbidden from writing `FIXED` or `PASSED`.

---

### 🔹 Layer 3: Regression Checks (System Integrity)

Verify that at least **2 existing, unmodified features** continue to work without regression:
```bash
# Example regression check
python -c "from actions.open_app import open_app; from actions.task_status import task_status; print(task_status({}))"
```

---

## 📋 Mandatory Verification Report Format

Always conclude verification using this exact format:

```text
═══════════════════════════════════════════
VERIFICATION REPORT
═══════════════════════════════════════════

FILES CHANGED:
- [List of modified/created files]

LAYER 1: STATIC CHECKS
- Compilation: [PASS / FAIL] (exact command)
- Imports: [PASS / FAIL]
- Discovery: [PASS / FAIL]

LAYER 2: RUNTIME EVIDENCE
- Command / Execution: [Exact script or command run]
- Raw Log Output: [Pasted actual log lines]
- Extracted Content / Artifact: [Length, file preview, or API return]
- Status: [PASS / UNVERIFIED / FAIL]
- Reason if Unverified: [N/A or exact blocker]

LAYER 3: REGRESSION CHECKS
- Feature 1: [PASS / FAIL] (e.g., task_status query)
- Feature 2: [PASS / FAIL] (e.g., open_app tool check)

FINAL STATUS: FIXED | UNVERIFIED | FAILED
═══════════════════════════════════════════
```

---

## 📐 Spec Compliance

If OpenSpec-tracked feature:
- `openspec list` → confirm change exists
- If done + verified → `/opsx:archive`
- Else → leave active

If bug fix:
- Update `LEARNING_JOURNAL.md` manually
