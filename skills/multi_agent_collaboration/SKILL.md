---
name: multi_agent_collaboration
description: Multi-agent task handoff, peer delegation protocols, contract interfaces, and sequential workflow execution across specialist agents.
metadata:
  author: ZEZO / Hamza Bukhari
  version: '2.0'
---

# Multi-Agent Collaboration & Peer Delegation Protocol

Use this skill when orchestrating multi-agent tasks, decomposing full-stack initiatives across specialists, or establishing peer handoffs between named agents (Michael, Ali, Ahmad, Dwight, Pam, Oscar, Kelly).

## Core Principles:
1. **Clear Input/Output Contracts:**
   - When Agent A passes deliverables to Agent B, structure the handoff payload with explicit headings: `Deliverable Summary`, `Key Outputs`, `Next Action Requirements`.
2. **Specialist Role Adherence:**
   - **MICHAEL:** High-level orchestrator & task decomposer.
   - **ALI:** Studio UI layout, HTML/CSS, animations, responsive design.
   - **AHMAD:** Backend logic, database schemas, FastAPI endpoints, microservices.
   - **DWIGHT:** QA test authoring, security review, edge case audit.
   - **PAM:** Design tokens, asset localization, typography and HUD metrics.
   - **OSCAR:** Cyclomatic complexity auditing (<15 score) and performance benchmarking.
   - **KELLY:** Deep web research, YouTube transcription, and multi-source synthesis.
3. **Anti-Recursion Safety:**
   - Max delegation depth is 3. An agent must never delegate back to its calling parent in the same chain.
