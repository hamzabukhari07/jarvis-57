# 09 - Model Context Protocol (MCP) Integration

**Status:** ARCHITECTURAL REFERENCE KNOWLEDGE BASE  
**Target Repository:** [QwenPaw (GitHub: agentscope-ai/QwenPaw)](https://github.com/agentscope-ai/QwenPaw)  
**Inspection Mode:** Verified from Source (`packages/qwenpawmail-mcp/`, `src/qwenpaw/agents/acp/session_mcp.py`, `drivers/`)

---

## 1. Role of MCP in Agent Operating Systems

Anthropic's **Model Context Protocol (MCP)** has emerged as the open industry standard for connecting AI models to external data sources, enterprise tools, and developer environments.

Rather than writing custom, hardcoded integrations for every third-party service (PostgreSQL, GitHub, Slack, Linear, Google Drive), QwenPaw positions MCP as a core **Agent OS Driver Layer**:

```mermaid
graph TD
    Agent[QwenPaw Agent Core] -->|Tool Selection| MCP_Client[MCP Client Driver Layer]
    
    subgraph Local_MCP_Servers ["Local Child Process MCP Servers (STDIO)"]
        GitMCP["Git MCP Server (Local Repository Management)"]
        FSMCP["Filesystem MCP Server (Sandboxed Directory Access)"]
        MailMCP["QwenPaw Mail MCP (packages/qwenpawmail-mcp)"]
        SqliteMCP["SQLite MCP Server (Local Database Analysis)"]
    end

    subgraph Remote_MCP_Servers ["Remote Network MCP Servers (SSE / HTTP)"]
        GithubMCP["GitHub Enterprise Server"]
        JiraMCP["Atlassian Jira / Confluence Server"]
        CustomMCP["Private Internal Enterprise Tools"]
    end

    MCP_Client -->|STDIO Streams (stdin/stdout)| Local_MCP_Servers
    MCP_Client -->|Server-Sent Events (SSE) over HTTPS| Remote_MCP_Servers
```

---

## 2. Verified Implementation: `qwenpawmail-mcp` Package

In `packages/qwenpawmail-mcp/`, QwenPaw publishes an out-of-the-box MCP server implementing email operations:
- Implements MCP schema for listing mailboxes, searching threads, reading drafts, and sending encrypted emails.
- Runs as an independent child process communicating via JSON-RPC 2.0 over standard I/O (`stdin`/`stdout`).
- Can be plugged into QwenPaw or any standard MCP-compliant host (e.g. Claude Desktop, Antigravity IDE).

---

## 3. Protocol-Neutral Drivers & Governance

A major risk with external MCP servers is that an untrusted third-party tool could attempt prompt injection or arbitrary disk modification.
In QwenPaw:
- **The Policy Gate Sits In Front of MCP:** When an MCP server advertises a tool (e.g., `execute_sql_query`), the tool must register with QwenPaw's **Governance Policy Engine**.
- If the policy for that MCP tool is set to `ask`, the agent cannot invoke it without user approval, regardless of what the MCP server permits.

---

## 4. Strengths & Tradeoffs

| Advantage | Tradeoff / Risk |
| :--- | :--- |
| Instant access to hundreds of community MCP servers | Spawning 10+ local node/python MCP servers consumes significant RAM |
| Clean separation between tool logic and agent core | JSON-RPC STDIO serialization adds ~5–20ms per tool invocation |
| Standardized schema validation via JSON Schema | External MCP crashes must be handled gracefully without killing the host |

---

## 5. Architectural Recommendations for Zezo

1. **Native Rust MCP Client:**
   Zezo can easily implement an MCP client in Rust (`rmcp` crate or custom JSON-RPC over `tokio::process`). This allows Zezo to connect to any standard MCP server without maintaining custom tool code.
2. **Dynamic Tool Exposure:**
   Allow users to drop standard `mcp_config.json` configurations into Zezo. Zezo auto-starts the declared servers and exposes their tools to the voice agent.
3. **Governance Gate for External MCPs:**
   Never grant external MCP servers unrestricted execution rights. Always route MCP tool calls through Zezo's confirmation dialogs.
