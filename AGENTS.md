# 🧠 AGENTS.md — Non-Negotiable Engineering Rules & Agent Guidelines

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux  

---

## ⚠️ READ THIS BEFORE MAKING ANY CODE CHANGES

This file contains **strict operational and coding rules** for all AI coding agents working on this repository.
It does **not** describe static feature flows or temporary architectures, because features evolve rapidly. Instead, it mandates **how you must discover current code, write modifications safely, protect newly updated features, and verify your work**.

---

## 🛡️ 1. Core Operating & Engineering Rules

### Rule 1: Live Codebase & Learning Journal Are Ground Truth (No Outdated Assumptions)
- **Do NOT assume architecture or flows from memory or third-party assumptions.**
- Before touching ANY file or debugging any problem:
  1. Inspect the **current implementation in the actual source code**.
  2. Check the most recent entries in [`LEARNING_JOURNAL.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/LEARNING_JOURNAL.md) (active, last 25 entries). For older history, grep [`LEARNING_JOURNAL_ARCHIVE.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/LEARNING_JOURNAL_ARCHIVE.md) by the module/file name you are touching — do NOT read the whole archive.
- If existing code differs from what you expected, **the updated code in the repository is intentional**. Understand why it was written before proposing any change.

### Rule 2: Never Overwrite or Degrade Updated Features (Anti-Regression)
- **Never revert a newly updated feature back to an old pattern.**
- Never replace an advanced/updated implementation (e.g. multi-tier fallbacks, downsampling, profile resolution, UIA inspection) with a naive or older version.
- When fixing an issue or adding a capability, **extend and preserve** existing updated features.

### Rule 3: Zero Unrelated Changes — Minimal Blast Radius ("Jo Jitna Kaha Hai Utna Karo")
- **Touch ONLY the exact files necessary** to complete the user's specific request.
- **NEVER** edit, refactor, reorganize, or "clean up" unrelated files, directories, or imports.
- Do not make speculative abstractions or add unsolicited features.
- If a fix only requires editing `main.py` and `core/audio_devices.py`, do NOT touch actions, UI components, or unrelated configs.

### Rule 4: One File Per Action & Clean Separation
- Every action tool must reside in its own file inside `actions/`.
- Every action module must export:
  1. A module-level `TOOL` dictionary matching the Gemini function declaration schema.
  2. A callable `handler(parameters: dict, **kwargs)` function.
- `main.py` only hosts inline tools tied directly to live session state (`screen_process`, `manage_monitor`, `shutdown_zezo`, `system_status`). All general tools belong in `actions/`.

### Rule 5: Non-Blocking Asynchronous Execution
- **Never block the main PyQt6/GUI thread or the live WebSocket loop.**
- Heavy operations (CLI runs, long-running agent tasks, subprocesses, heavy scraping) must run asynchronously in background threads or return a `task_id` immediately.
- On Windows, always hide background subprocess terminal windows using `creationflags=subprocess.CREATE_NO_WINDOW`.

### Rule 6: Audio & Voice Pipeline Integrity (Strict Hands-Off Policy)
- **STRICT HANDS-OFF POLICY ("Bila-Wajah Touch Mat Karo"):** Audio and voice pipeline files (`main.py` live audio loops `_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`) are core, finely-calibrated, hardware-dependent systems.
  - **DO NOT TOUCH** any audio/voice pipeline code or files unless the user's explicit request specifically and exclusively demands a fix or change to audio or voice behavior.
  - If a task involves browser control, computer automation, actions/tools, UI styling, settings modals, fleet agents, or memory, touching audio/voice pipeline files is **STRICTLY FORBIDDEN**.
  - Never perform unsolicited refactoring, speculative "cleanup", or casual alterations to audio queues, buffer sizes, sample rates, echo cancellation guards, or hotkey hooks.
- **Sole Active Voice Pipeline:** The active live voice conversation runs strictly via Google Gemini Live API (`main.py` WebSockets bidirectional audio).
- **Explicit Sample Rate:** When streaming PCM mic chunks to Gemini Live, always include the explicit sample rate: `types.Blob(data=..., mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")`. Never send bare `audio/pcm`.
- **Never crash the session on hardware errors:** If a microphone or speaker is missing, unplugged, or permission-denied, gracefully fall back to silent/text/remote mode rather than raising an unhandled exception that terminates the session `TaskGroup`.
- **Never speak raw code:** Spoken audio must remain high-level conversational summary (1-2 sentences). Code, syntax, diffs, and large JSON payloads must be routed to the HUD content panel or clipboard.

### Rule 7: Strict 3-Layer Verification (Mandatory Before Claiming Done)
After ANY code change, verify all 3 layers yourself before reporting success:
- **Layer 1 (Static):** Run `python -m py_compile` on every touched file. Verify syntax and imports.
- **Layer 2 (Runtime):** Test real execution with concrete evidence (actual test scripts, real log outputs, real device/file returns). Never claim a run you did not perform.
- **Layer 3 (Regression):** Run relevant existing test suites (`pytest tests/...`) to confirm existing features remain intact.
- **You may NOT write "FIXED" until all 3 layers pass.** If runtime cannot be run, write "UNVERIFIED" with the specific reason.

### Rule 8: Anti-Slop Code Hygiene
- Function cyclomatic complexity must stay **< 15**.
- No massive `if/elif` ladders (use dictionary dispatch).
- No bloated boilerplate, duplicate helper functions, or obvious echo comments.

### Rule 9: Code Graph (CGC) Pre-Flight Query
- Before modifying or debugging unfamiliar modules, inspect blast radius and callers via Code Graph MCP tools or CLI (`cgc`).
- If you see `Could not set lock on file` (KùzuDB single-owner lock held by IDE), fall back immediately to targeted file search without retrying.

### Rule 10: Mandatory Learning Journal Entry
- After completing any feature, fix, or architectural update, append a clean entry to [`LEARNING_JOURNAL.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/LEARNING_JOURNAL.md) at the repo root.
- Document:
  - What was built/fixed and the root cause.
  - Key files touched.
  - Crucial architectural context for future agents to prevent regression.

### Rule 11: Creator Attribution
- Always acknowledge **Hamza Bukhari** as the creator and lead architect.

---


## ⚡ 3. Strict Scope Control & Fast Execution

### Rule 1: Fix Only What the User Asked For
- Treat the user's exact request as the complete scope of work.
- Identify the specific bug, feature, or behavior requested and work only on that.
- Do NOT fix unrelated bugs, improve adjacent features, refactor surrounding code, or modify other systems without explicit permission.
- If a browser control or other bug is reported, fix that specific issue only. Do not modify audio, voice, UI, or other systems.
- **Never touch audio/voice pipeline files** (`main.py` live loops, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`) unless the user explicitly requested an audio/voice fix. **"Bila-wajah audio/voice pipeline files ko touch karna sakhti se mana hai."**
- **"Jo kaha hai, sirf wohi karo. Apni taraf se extra kaam mat karo."**

### Rule 2: Fast, Targeted Diagnosis
- Use the fastest reliable path to identify the root cause.
- Start with the reported error, relevant logs, the affected function, and its direct callers.
- Inspect only the necessary source files and dependencies. Expand the investigation only when the evidence requires it.
- Avoid repeatedly reading the same files, exploring unrelated directories, generating lengthy analysis, or investigating hypothetical problems.
- Do not perform exhaustive repository-wide analysis for a localized bug.
- Prefer a small, evidence-based fix over prolonged investigation.

### Rule 3: Minimal Changes, Maximum Preservation
- Make the smallest change that correctly solves the reported problem.
- Preserve existing working implementations, APIs, behavior, architecture, UI, and user preferences.
- Never replace, simplify, rewrite, or remove existing functionality just because a different implementation seems easier.
- Do not modify unrelated files, dependencies, configurations, or shared components.
- Before editing shared code, confirm that the change is necessary for the requested task.
- Never introduce speculative fixes for problems that have not been reported or demonstrated.

### Rule 4: No Unrequested Fixes
- If you discover an unrelated bug, document it briefly but leave it untouched.
- Do not expand the task scope without asking the user.
- If the requested fix reveals a dependency on another module, modify that module only when necessary to complete the requested fix safely.
- If the root cause is outside the expected module, explain the evidence briefly before making broader changes when the impact is significant.

### Rule 5: Execute Immediately, Avoid Analysis Loops
- Once the relevant implementation and root cause are sufficiently understood, implement the fix immediately.
- Do not continue analyzing after enough evidence exists to make a safe change.
- Do not create unnecessary investigation plans, duplicate diagnostic scripts, speculative TODO lists, or lengthy explanations.
- Do not ask for confirmation for routine, reversible implementation decisions within the user's explicit scope.
- Ask one concise question only when a missing detail blocks safe execution or when a potentially destructive or architectural decision requires approval.

### Rule 6: Proportional Verification
- Verify the specific behavior affected by the change first.
- Run the smallest relevant tests and checks, then expand testing only when the change's risk or impact requires it.
- Follow the mandatory three-layer verification policy in Core Operating Rule 7, but keep each layer targeted to the changed code and affected behavior.
- Never skip required verification just to appear faster.
- Never claim a test passed unless it was actually executed successfully.
- If an environment limitation prevents verification, report the exact limitation and mark the result UNVERIFIED.

### Rule 7: Concise Execution Reports
After completing a task, report only:
1. **Fixed:** What specific issue was addressed.
2. **Files changed:** Only the files actually modified.
3. **Verification:** The checks actually performed and their results.
4. **Unverified:** Any important check that could not be completed.

Do not provide lengthy implementation explanations unless requested.

### Rule 8: Scope Expansion Requires Permission
- The user controls task scope and priorities.
- Never turn a small bug report into a general system improvement project.
- If a broader change appears necessary, explain why in one or two sentences and request permission before proceeding, unless the user has already explicitly authorized that scope.
- **Priority order: User's exact request → Minimal safe fix → Targeted verification → Concise report.**

### Rule 9: Speed Without Recklessness
- Optimize for fast, focused execution, not maximum analysis or maximum code changes.
- Avoid unnecessary tool calls, repeated searches, redundant file inspections, and unrelated test suites.
- Reuse existing project knowledge and recent learning journal entries when relevant.
- Do not sacrifice code correctness, data safety, or mandatory verification for speed.

**Final Principle: Fix the reported problem, preserve everything else, verify the fix, and stop. Do not invent additional work.**

## 🎨 2. Frontend & UI Engineering Rules

### Rule 1: ReUI Design System as Source of Truth
- The frontend UI uses **ReUI as the primary design system and component source of truth**.
- When an official ReUI component exists (Button, Input, Select, Dialog, Sheet, Tabs, Progress, Badge, Tooltip, Scroll Area, Separator), use the actual component. Do NOT reinvent it with raw HTML/CSS.
- Maintain coherent styling tokens: use semantic CSS variables (`--background`, `--foreground`, `--primary`, `--border`, etc.) instead of hardcoded hex values.

### Rule 2: Modal & Window State Invariants
- **No backdrop-filter inside modals:** `.modal-overlay` may have `backdrop-filter: blur(12px)`. Elements *inside* the modal must NOT have `backdrop-filter`. Modal panel backgrounds must be opaque (`#0a0a0a`).
- **Never use `transition: all`:** Always list explicit CSS transition properties.
- **Preserve `_zezoAnimActive`:** Modal opening and closing must manage `window._zezoAnimActive` and hide/show `vortex-gif` avatar so background animations do not waste CPU while modals are open.
- **Settings is a Modal:** The settings panel is `<div class="modal-overlay" id="settings-modal">`, triggered via `openModal('settings-modal')`.
