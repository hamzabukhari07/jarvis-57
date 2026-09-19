# 11 - QwenPaw Architectural Reference Notes & Synthesis

**Status:** ARCHITECTURAL REFERENCE KNOWLEDGE BASE  
**Target Repository:** [QwenPaw (GitHub: agentscope-ai/QwenPaw)](https://github.com/agentscope-ai/QwenPaw)  
**Authoring Target:** Zezo Autonomous Desktop Assistant Architecture

---

## 1. Top 10 Architectural Lessons from QwenPaw

1. **The Skill vs. Tool Principle:** Distinguish between atomic executable code functions (Tools) and declarative Markdown usage guides (Skills). This separation allows rapid behavior iteration without modifying executable binaries.
2. **Window-Bound Desktop Automation:** Generic full-screen coordinate clicking is brittle across multi-monitor and high-DPI setups. Binding screenshots, accessibility trees, and clicks to target `HWND` windows (`computer_use` protocol v2) provides rock-solid UI automation.
3. **Four-Tier Security Governance:** Never execute LLM tool calls without passing through an explicit governance layer: Skill Scanner $\rightarrow$ Policy Gate (Allow / Deny / Ask) $\rightarrow$ Tool Guard $\rightarrow$ Kernel Sandbox.
4. **Scroll Context Over Naive Summaries:** Never compress or summarize away historical conversation turns. Persist turns verbatim in indexed SQLite storage and retrieve them selectively on demand.
5. **Human-Auditable Markdown Memory (ReMe):** Store learned long-term user memories and facts in plain, human-readable Markdown files. Transparency builds trust.
6. **Accessibility Tree Web Navigation:** Do not flood LLM prompts with raw HTML. Simplify the DOM into an indexed Accessibility Tree (`[1]`, `[2]`, `[3]`) to reduce token usage by 80%+ and increase action accuracy.
7. **Proactive Scheduled Autonomy:** An AI assistant that only responds when spoken to remains a tool; an assistant with cron scheduling and background heartbeats becomes an autonomous partner.
8. **Batch Tool Invocation:** Support emitting and executing multiple related tool calls in a single reasoning turn to minimize model latency.
9. **Process & Workspace Isolation:** Treat agents as processes with isolated filesystem sandboxes, separate memory, and private permission profiles.
10. **Protocol-Neutral Drivers (MCP):** Build tool adapters using the Model Context Protocol to instantly tap into the broader open-source ecosystem without rewriting integrations.

---

## 2. Top 10 Most Useful Patterns for Zezo

1. **`SKILL.md` Specification Format:** Adopt the standard YAML frontmatter + Markdown instruction format for defining Zezo's desktop skills.
2. **Dynamic Island Confirmation Gate:** Route QwenPaw's `ask` policy directly to Zezo's `CONFIRMATION` UI state before running risky shell commands.
3. **Chrome CDP Attach:** Allow Zezo to connect to the user's running Chrome browser via port 9222 for authenticated automation without credential sharing.
4. **Window Discovery via Win32:** Port `list_windows` and `observe_window` to native Rust Win32 APIs (`EnumWindows`, `GetWindowRect`, `PrintWindow`).
5. **Silent Scheduled Runs:** Support `--silent` cron tasks that run in the background without popups or sound unless an urgent anomaly requires attention.
6. **Task Checkpointing & Resumption:** Persist background task states so system reboots do not abandon in-flight tasks.
7. **AST & Code Editing Tools:** Provide structured code diffing and search primitives for programming workflows.
8. **Structured Error Feedback:** Wrap every failed tool execution in a helpful JSON observation so the model self-corrects on the next turn.
9. **Plain Markdown User Profile:** Store learned user preferences in `%APPDATA%\Zezo\memory\user_profile.md`.
10. **MCP Server Host Support:** Enable Zezo to launch local MCP child processes configured via `mcp_config.json`.

---

## 3. Patterns Zezo Should NOT Copy Blindly

1. **Do NOT Bundle the Python Runtime:** QwenPaw's Python runtime + dependencies create a 500MB+ footprint. Zezo must remain ultra-light (Tauri v2 + Rust).
2. **Do NOT Adopt Complex Multi-Agent Swarms Early:** Multi-agent ACP orchestration introduces latency and orchestration overhead that is counter-productive for a real-time voice assistant.
3. **Do NOT Use Slow Turn-Based Voice:** QwenPaw has no native sub-400ms duplex voice engine; it is designed for text/console channels. Zezo must prioritize voice streaming (inspired by IRIS).
4. **Do NOT Rely on Headless Playwright for Everything:** Spawning full Chromium instances for simple HTTP queries wastes gigabytes of RAM. Use fast native HTTP clients where scraping suffices.

---

## 4. Key Tradeoffs Identified in QwenPaw

| Architectural Choice | Benefit | Downside / Tradeoff |
| :--- | :--- | :--- |
| **AgentScope Python Stack** | Rapid access to cutting-edge AI libraries | Heavy memory footprint; complex deployment on client machines |
| **Deep Sandboxing (AppContainer/Bwrap)** | Extreme security isolation against rogue scripts | Requires elevated permissions or platform-specific kernel configurations |
| **Scroll Context & ReMe** | Perfect history retention and searchable facts | Ongoing disk write overhead and periodic background embedding compute |
| **Headless Playwright Automation** | Can automate any dynamic web page | High CPU/RAM spikes during browser page rendering |

---

## 5. Missing / Inferred Information in Public QwenPaw Repository

- **Cloud Platform Services:** Certain hosted agent coordination features reference the closed AgentScope Cloud Platform (`platform.agentscope.io`).
- **Proprietary Fine-Tuned Models:** References to `QwenPaw-Flash` model weights denote Alibaba Cloud private weights, though open Qwen 2.5 / OpenAI endpoints are fully supported.

---

## 6. Licensing & Usage Considerations
- QwenPaw is licensed under the **Apache License 2.0**.
- Apache 2.0 is extremely permissive, allowing commercial use, modification, and redistribution. Zezo can freely adapt schemas, concepts, and architectural patterns.
