---
name: repo_opportunity_audit
description: Analyze external, cloned, or reference repositories to discover reusable patterns, modules, algorithms, and capability opportunities for ZEZO / JARVIS without unauthorized code copying or dependency bloat.
---

# 🔎 Repository Opportunity Audit Workflow

This workflow skill is activated when inspecting a cloned repository, external open-source project, or reference codebase to identify high-value capabilities, architectures, or algorithms that could enhance **ZEZO / JARVIS**.

It operates in **strictly read-only mode** to deliver a structured opportunity assessment comparing the source repository against ZEZO's modular monolith architecture.

---

## 🎯 When to Trigger

Activate this skill when the user:
- Provides a path to a cloned repository or asks: *"Audit this repo for features we can adapt into Zezo."*
- Asks: *"What capabilities from project X could make Zezo better?"*
- Wants to compare an external agentic framework (e.g. AutoGen, CrewAI, OpenDevin, Hermes) with Zezo's native systems.
- Requests an architectural evaluation of third-party libraries or reference implementations.

---

## 🔄 Step-by-Step Audit Procedure

```
[ 1. SOURCE REPO AUDIT ] ──► Inspect directory tree, dependencies, core engines, and documentation.
           │
[ 2. CAPABILITY EXTRACTION ] ──► Identify concrete algorithms, protocols, data schemas, and UI patterns.
           │
[ 3. TARGET ZEZO AUDIT ] ──► Query target ZEZO architecture using `code_graph_intelligence`.
           │
[ 4. GAP & COMPARISON MATRIX ] ──► Compare capabilities: Already present vs New opportunity vs Incompatible.
           │
[ 5. INTEGRATION FEASIBILITY ] ──► Assess licensing, dependencies, security, complexity, and performance.
           │
[ 6. OPPORTUNITY REPORT ] ──► Deliver prioritized adoption roadmap (Strictly discovery, no code copying).
```

### 1. Source Repository Deep Inspection
- Scan the directory structure and manifest files (`pyproject.toml`, `requirements.txt`, `package.json`).
- Inspect core engine files, entrypoints, and communication protocols (WebSockets, IPC, REST).
- Verify runtime requirements (Python versions, C-extensions, GPU dependencies, platform-specific APIs).

### 2. Identify Concrete Capabilities
- Pinpoint high-value mechanisms:
  - Novel agent coordination patterns or delegation algorithms.
  - Voice activity detection (VAD), audio streaming, or echo suppression techniques.
  - Visual rasterization, canvas animation, or HUD layout techniques.
  - Sandboxed execution, AST transformations, or circuit breaker logic.

### 3. Target ZEZO Architecture Comparison
- Inspect ZEZO's matching subsystem (`core/`, `actions/`, `memory/`, `ui.py`):
  - Use `code_graph_intelligence` to map ZEZO's existing callers and implementations.
  - Verify if ZEZO already has equivalent or superior functionality (e.g., existing `core/git_sandbox.py` or `memory/sqlite_memory.py`).
  - Flag potential duplicate functionality to avoid feature bloat.

### 4. Feasibility, Security & Licensing Assessment
- **License Check:** Verify license compatibility (MIT, Apache 2.0, BSD vs GPL/AGPL copyleft constraints).
- **Dependency Weight:** Evaluate if adapting the feature introduces heavy external dependencies that violate Anti-Slop principles.
- **Platform Compatibility:** Confirm Windows / macOS / Linux compatibility and subprocess handling (`CREATE_NO_WINDOW`).
- **Security Implications:** Check for unsafe `eval()`, unauthenticated endpoints, or arbitrary shell execution vectors.

---

## 📋 Output Format: Repository Opportunity Report

Present findings using this structured markdown format:

```markdown
# 🔎 Repository Opportunity Audit: [Source Repo / Project Name]

### 1. Executive Summary & Source Overview
- **Source Purpose:** [Brief summary of the audited project]
- **Tech Stack & License:** [e.g. Python 3.12 / FastAPI / MIT License]
- **Key Architectural Strengths:** [Notable design patterns or innovations]

### 2. Capability Comparison Matrix

| Feature / Mechanism | Source Implementation | ZEZO Current State | Opportunity Assessment |
| :--- | :--- | :--- | :--- |
| **Agent Coordination** | Pub/Sub Event Bus | Direct TaskManager Submit | **Adopt Pattern:** Add decoupled events |
| **Voice VAD** | WebRTC VAD | Silero VAD in `wake_word` | **Keep Existing:** ZEZO already optimized |
| **Sandboxing** | Docker Container | Git Worktrees (`git_sandbox`) | **Keep Existing:** Native worktrees faster |

### 3. High-Value Adoption Opportunities
1. **[Opportunity 1 Name]**
   - **What it does:** [Mechanism description]
   - **Why it benefits ZEZO:** [Concrete user or architectural benefit]
   - **Target ZEZO Touchpoints:** [`core/engine_name.py`, `actions/new_tool.py`]
   - **Adoption Strategy:** [Clean-room reimplementation adhering to Anti-Slop]

### 4. Incompatibilities & Risks
- **Dependency Bloat:** [Unnecessary packages to avoid]
- **Architectural Clashes:** [Patterns that would block PyQt6 GUI or degrade Gemini Live latency]

### 5. Recommended Next Steps
- Select approved opportunities and transition to `feature_planning`.
```

---

## 🛡️ Safety & Execution Boundaries

- **Strictly Read-Only:** Do NOT copy external files, install packages, or modify ZEZO repository code.
- **Clean-Room Implementation:** Prefer adapting architectural principles and algorithms rather than blindly copying third-party code.
- **Explicit Authorization Required:** Any actual code integration must be planned via `feature_planning` and approved by the user before execution.
