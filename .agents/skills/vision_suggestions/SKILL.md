---
name: vision_suggestions
description: Idea exploration, architectural brainstorming, and feature vision refinement for ZEZO / JARVIS. Analyzes feature requests against current codebase architecture using Code Graph, suggests technical options with trade-offs, and refines concepts without modifying code.
---

# 💡 Vision Suggestions & Idea Exploration Workflow

This workflow skill is activated when exploring a new concept, evaluating a feature seen in another application, clarifying an incomplete vision, or investigating architectural enhancements for **ZEZO / JARVIS**.

It operates in **strictly read-only mode** to produce technically grounded, architectural recommendations without modifying source files.

---

## 🎯 When to Trigger

Activate this skill when the user:
- Asks *"How could we add [feature] to Zezo?"* or *"What if we integrated [library/concept]?"*
- Describes an incomplete vision or rough idea and requests technical guidance.
- Shares a screenshot, reference architecture, or behavior from another AI OS / agent and asks how Zezo could achieve it.
- Asks for architectural trade-offs between two different technical approaches.

---

## 🔄 Step-by-Step Workflow Procedure

```
[ 1. CLARIFY VISION ] ──► Identify user's core intent, desired capabilities, and user experience.
          │
[ 2. GRAPH INSPECTION ] ──► Use `code_graph_intelligence` to map existing related modules & symbols.
          │
[ 3. SOURCE VALIDATION ] ──► Read active source files to verify runtime constraints & extension points.
          │
[ 4. GAP & OVERLAP AUDIT ] ──► Determine what already exists vs what must be built new.
          │
[ 5. SYNTHESIZE OPTIONS ] ──► Develop 2-3 architectural approaches with clear pros/cons and trade-offs.
          │
[ 6. STRUCTURED REPORT ] ──► Present findings, recommended path, and next steps (No code mutation).
```

### 1. Clarify the Core Vision
- Deconstruct the user's idea into:
  - **User Experience (UX):** How does the user interact (voice, hotkey, UI HUD, WebSocket, Telegram)?
  - **Execution Mechanism:** Is this synchronous, asynchronous background task, or local LLM inference?
  - **State & Memory:** Does this require episodic memory (SQLite FTS5), configuration persistence, or Git worktree isolation?

### 2. Code Graph Pre-Flight Audit
- Invoke `code_graph_intelligence` to locate related existing components:
  ```powershell
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb find name <related_symbol>
  $env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"; cgc -db kuzudb analyze callers <related_symbol>
  ```
- *Fallback:* If Code Graph is locked, use `grep_search` and `view_file`.

### 3. Cross-Check Against Ground Truth Source Code
- Inspect the actual target files (`actions/`, `core/`, `ui.py`, `memory/`, `frontend/`).
- Verify existing data flow, signal signatures, and WebSocket event types.
- Ensure ideas respect core architectural invariants (e.g. PyQt6 non-blocking GUI thread, asynchronous task manager, action loader dynamic discovery).

### 4. Evaluate Technical Feasibility & Trade-Offs
- Identify 2 to 3 viable implementation approaches:
  - **Approach A (Minimal Native Integration):** Uses existing stdlib/actions with minimal new surface area.
  - **Approach B (Dedicated Engine / Action):** Implements a dedicated modular action or core engine.
  - **Approach C (External / Pluggable Integration):** Integrates via user plugins (`plugins/`) or background services.
- Compare them across:
  - Latency impact on Gemini Live voice loop.
  - Resource consumption (CPU/RAM/GPU).
  - Maintenance cost & blast radius.
  - Failure modes and error handling.

---

## 📋 Output Format: Vision & Architecture Brief

Present findings using this structured markdown format:

```markdown
# 💡 Vision Exploration: [Feature Name]

### 1. Vision & Core Objectives
- Summary of the proposed feature and expected user experience.

### 2. Existing Repository Capabilities & Touchpoints
- **Reusable Existing Modules:** [e.g. `core/task_manager.py`, `actions/file_controller.py`]
- **Architectural Overlaps:** [Existing tools or workflows that overlap]
- **Extension Points:** [Exact files where new handlers or signals would connect]

### 3. Architectural Options & Trade-Off Analysis

| Approach | Architecture Summary | Pros | Cons / Risks | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Option 1 (Recommended)** | Direct Action Handler | Zero GUI blocking, reuses TaskManager | Requires prompt update | Low |
| **Option 2** | Custom Core Engine | Full lifecycle control | Increases codebase surface area | Medium |

### 4. Key Constraints & Non-Negotiable Rules
- Applicable `AGENTS.md` rules (e.g., async `task_id` pattern, non-blocking UI, anti-slop complexity < 15).

### 5. Recommended Next Steps
- Transition to `feature_planning` to build a dependency-ordered execution roadmap.
```

---

## 🛡️ Safety & Execution Boundaries

- **Strictly Read-Only:** Do NOT write or modify application source code during idea exploration.
- **Fact vs Assumption:** Clearly distinguish confirmed codebase capabilities from hypothetical designs.
- **No Premature Execution:** Always seek user alignment on the preferred approach before proceeding to planning or implementation.
