# 06 - Multi-Agent Architecture & The ACP Protocol

**Status:** ARCHITECTURAL REFERENCE KNOWLEDGE BASE  
**Target Repository:** [QwenPaw (GitHub: agentscope-ai/QwenPaw)](https://github.com/agentscope-ai/QwenPaw)  
**Inspection Mode:** Verified from Source (`src/qwenpaw/agents/acp/`, `multi_agent_collaboration-en/`)

---

## 1. Multi-Agent Philosophy & Isolation Model

QwenPaw implements multi-agent workflows through strict **Process & Workspace Isolation** rather than shared state objects:
- Every agent is an independent entity with its own ID, configuration file (`agent.yaml`), local workspace directory, memory store, and enabled toolset.
- Agents do not share global variables. Communication occurs strictly through the **Agent Communication Protocol (ACP)** or message passing.

```mermaid
graph LR
    subgraph Master_Orchestrator ["Primary Agent (e.g. Lead Planner)"]
        LeadAgent["Lead Agent ReAct Loop"]
        LeadSkills["Planning & Delegation Skills"]
    end

    subgraph ACP_Bus ["Agent Communication Protocol (ACP) Bus"]
        ACP_Router["ACP Dispatcher & Permission Broker"]
    end

    subgraph SubAgent_A ["Specialist Agent A (Coding Agent)"]
        Coder["Code Specialist"]
        CoderFS["Isolated Workspace Repo"]
        CoderTools["AST, LSP, Git, Shell Tools"]
    end

    subgraph SubAgent_B ["Specialist Agent B (Researcher Agent)"]
        Researcher["Research Specialist"]
        ResearchTools["Browser, Search, PDF Tools"]
    end

    LeadAgent -->|delegate_task(task, agent_id)| ACP_Router
    ACP_Router -->|Validate Permissions| Coder
    ACP_Router -->|Validate Permissions| Researcher
    Coder -->|Task Result / Artifact| ACP_Router
    Researcher -->|Scraped Insights / Citations| ACP_Router
    ACP_Router --> LeadAgent
```

---

## 2. The Agent Communication Protocol (ACP)

The `src/qwenpaw/agents/acp/` module establishes a standard RPC contract for cross-agent collaboration:
- **`service.py` & `session_mcp.py`:** Manages agent sessions and exposes an agent's capabilities as callable remote endpoints.
- **`permissions.py`:** Enforces delegation boundaries. A lead agent cannot unilaterally grant a sub-agent permissions beyond what the user configured for that sub-agent.
- **`tool_adapter.py`:** Wraps remote agents into standard callable tool schemas so the calling agent's LLM simply sees them as another tool (e.g. `delegate_external_agent(agent_name="researcher", query="...")`).

---

## 3. When Multi-Agent is Useful vs. Unnecessary Complexity

| Use Case | Multi-Agent Verdict | Architectural Rationale |
| :--- | :--- | :--- |
| **Simple Desktop Voice Commands** (*"Open Spotify"*) | **Unnecessary Bloat** | A single agent with direct tools executes instantly. Delegating adds 2–4 seconds of inter-agent latency. |
| **Large Software Refactoring** | **Highly Useful** | Separation of concerns: one agent writes code, a second agent runs the test suite and audits security in parallel. |
| **Long-Running Background Monitoring** | **Useful** | A background agent monitors server logs or price drops without interrupting the user's primary conversational agent. |

---

## 4. Architectural Recommendations for Zezo

1. **Start with Single-Agent Excellence:**
   For Zezo's immediate voice-first desktop assistant mission, multi-agent swarms add unnecessary latency, token costs, and debugging friction.
2. **Design for Future ACP/MCP Compatibility:**
   Implement Zezo's internal tool registry using protocol-neutral schemas. When multi-agent capabilities are added in future phases, the foundation will easily adopt sub-agents without architectural rewrites.
3. **Sub-Task Background Threading:**
   Instead of full independent agents, Zezo can spin up asynchronous background worker tasks within the same agent instance.
