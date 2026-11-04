# ZEZO Architecture Redesign & Cleanup Proposal

**Document type:** Architecture audit and proposed redesign  
**Project:** ZEZO  
**Status:** Proposal only. No implementation changes authorized or performed.  
**Prepared from:** Uploaded `jarvis-57.zip`, the supplied ZEZO architecture material, and the supplied QwenPaw architecture reference.  
**Primary objective:** Simplify and stabilize ZEZO's architecture while delivering a dependable, user-configurable multi-agent experience.

---

## 0. Executive Summary

ZEZO should evolve into a **primary AI assistant with a unified agent runtime and a user-configurable workforce of specialist agents**.

The user should be able to:

1. Chat with ZEZO as the primary assistant and ask it to perform work itself.
2. Create custom agents with their own identity, instructions, model/engine preferences, skills, tools, permissions, and memory settings.
3. Open an independent chat with any agent and have that agent actually execute work, not merely return a normal LLM answer.
4. Let ZEZO delegate work to one or more agents and manage concurrent tasks.
5. Use supported external coding agents such as OpenCode and Kilo through well-defined engine adapters. ACP should be used where the target runner genuinely supports it; CLI integration can remain as a separate adapter where appropriate.
6. See task status, progress, approvals, errors, and deliverables in a consistent interface.

The main architectural problem is not that ZEZO lacks features. It already contains agent profiles, a dispatcher, an orchestrator, a task manager, action/tool loading, skill loading, memory systems, coding-engine runners, and an Agents Office UI. The problem is that these capabilities are spread across multiple execution paths with overlapping responsibilities and inconsistent enforcement.

The proposal is therefore **not a greenfield rewrite**. It is a controlled consolidation:

- Keep valuable existing capabilities.
- Establish one canonical Agent Runtime and execution contract.
- Make chat, delegated work, and external engine execution use the same runtime lifecycle.
- Centralize tool registration and permission enforcement.
- Make skills declarative, discoverable packages injected into agent context.
- Make multi-agent coordination task-based and orchestrator-mediated.
- Separate ACP, CLI, native tools, MCP, and internal agent communication rather than treating them as interchangeable.
- Consolidate persistence behind repositories and explicit data models.
- Remove only confirmed duplicates, obsolete backups, and superseded paths after dependency checks.

### Key architectural principle

> An agent is a persistent configuration and identity, while a run/session is a specific execution of that agent.

The profile survives between conversations. A runtime execution is created for a message or task, loads the profile's permitted capabilities, records events, and persists its session/task state. This separation is central to making ZEZO reliable.

---

## 1. Scope, Evidence and Limitations

### 1.1 Scope

This proposal covers:

- Primary ZEZO assistant runtime.
- User-created agents and agent profiles.
- Independent agent chat and session continuity.
- Skills and tools.
- Internal agent delegation and concurrent task execution.
- OpenCode, Kilo, and other external coding-agent integrations.
- ACP and CLI adapter boundaries.
- Memory, persistence, and task history.
- Frontend Agents Office and chat experiences.
- Security, approvals, observability, testing, and migration.
- Existing file disposition and proposed new project structure.

This proposal does **not** authorize implementation, deletion, refactoring, or configuration changes.

### 1.2 Evidence labels

The document distinguishes three types of statements:

- **Verified in supplied code:** A behavior or structure observed in the uploaded repository.
- **Reference-derived:** A pattern described in the supplied QwenPaw documentation.
- **Proposed:** A target design recommendation for ZEZO. It is not a claim that the feature already exists.

Where runtime behavior, dependency usage, or a full call path has not been executed, it is identified as requiring verification.

### 1.3 Audit limitations

The supplied project was inspected statically. Python files were syntax-checked in the earlier audit, but the application was not launched and a complete runtime/integration test suite was not executed. The proposal should therefore be treated as a source-grounded architecture review, not a certification that every runtime path is correct.

The archive includes `.git`, private certificate files, and personal memory/vault records. These should not be included in routine source-sharing archives. Certificate/private-key exposure should be assessed and affected credentials rotated if they are live.

---

## 2. Product Vision and Functional Requirements

### 2.1 ZEZO as the primary agent

ZEZO remains a fully capable assistant in its own right. It must not become only a dispatcher that forwards every request to a specialist.

ZEZO should be able to:

- Understand user requests.
- Answer directly when no execution is required.
- Use its own approved tools and skills.
- Plan a complex task.
- Decide whether to execute directly or delegate.
- Track delegated work.
- Combine worker results.
- Report progress, blockers, and final deliverables.

Delegation is an execution strategy, not a requirement for every request.

### 2.2 User-created agents

Users should be able to create, edit, duplicate, disable, and delete custom agents.

An agent profile should support:

| Field | Purpose |
|---|---|
| `id` | Stable unique identifier |
| `name` | User-visible name |
| `description` | What the agent is good at |
| `system_instructions` | Identity, behavior, and working instructions |
| `model_provider` | Model provider selection |
| `model_id` | Selected model |
| `engine_type` | Native, ACP runner, or CLI runner |
| `engine_config` | Adapter-specific configuration reference |
| `skills` | Explicitly assigned skills |
| `tools` | Explicitly allowed tools |
| `permissions` | Risk and resource boundaries |
| `memory_policy` | Whether and how memory is used |
| `workspace_policy` | Workspace access and isolation |
| `enabled` | Whether the agent can be selected or delegated to |
| `created_at`, `updated_at` | Lifecycle metadata |

The profile should store configuration, not live process objects or in-memory runtime state.

### 2.3 Independent agent chat

Each agent should have its own chat entry point and persistent conversation/session history.

Expected behavior:

1. User selects an agent.
2. Frontend opens or creates a conversation for that agent.
3. Backend loads the agent profile and session context.
4. A unified Agent Runtime prepares the execution.
5. The runtime resolves model/engine, skills, tools, permissions, workspace, and memory policy.
6. The agent responds or performs work.
7. Events and results stream back to the chat.
8. The session and run state are persisted.

The agent chat must not be a separate direct-LLM shortcut that bypasses the agent's selected engine, skills, tools, and permissions.

### 2.4 Multiple agents working at the same time

ZEZO should be able to delegate independent subtasks to multiple agents.

Example:

```text
User: Build a small SaaS application.

ZEZO (planner)
  ├── UI agent       -> UI implementation
  ├── Backend agent  -> API and database work
  └── QA agent       -> Test plan and later validation

Task Orchestrator
  ├── Tracks each task
  ├── Enforces dependencies
  ├── Applies concurrency limits
  ├── Collects results
  └── Returns a consolidated outcome to ZEZO
```

Concurrency must be controlled. Independent tasks can run in parallel; tasks with dependencies must wait for prerequisites. A QA task that depends on completed implementation should not begin validation prematurely.

### 2.5 External coding agents

ZEZO should be able to use external coding agents when appropriate.

- OpenCode: provide an ACP adapter if the installed OpenCode version and runner support the required ACP contract; otherwise retain a CLI adapter.
- Kilo: verify actual ACP support and version compatibility before promising an ACP integration. Keep a separate CLI adapter where supported.
- Other tools: implement through the same engine adapter interface.

ACP is **Agent Client Protocol**, not the internal agent-to-agent communication protocol. Internal delegation belongs to ZEZO's own orchestration layer.

---

## 3. Current-State Architecture: What Exists Today

This section summarizes the uploaded repository's structure and the source paths identified during the audit.

### 3.1 Main application and primary assistant

| File | Observed responsibility |
|---|---|
| `main.py` | Main application entry and primary assistant/voice interaction flow |
| `core/gemini.py` | Gemini integration |
| `core/llm_client.py` | LLM client functionality |
| `core/llm_router.py` | Model/provider routing |
| `core/dispatcher.py` | Main request/tool dispatch responsibilities |
| `core/action_loader.py` | Dynamic action discovery and registration |
| `core/ui_server.py` | Backend UI/API server, including agent-related endpoints |

The primary assistant and Agents Office do not currently share one fully unified agent execution lifecycle. The primary conversation has its own path, while the agent chat endpoint has a direct model response path.

### 3.2 Agent subsystem

| File | Observed responsibility |
|---|---|
| `core/agents_manager.py` | Agent subsystem facade/manager |
| `core/agents/registry.py` | Agent definitions and registry |
| `core/agents/dispatcher.py` | Agent task dispatch and prompt preparation |
| `core/agents/orchestrator.py` | Task decomposition and multi-agent orchestration |
| `core/task_manager.py` | Background task tracking/execution |
| `config/agents.json` | Agent profile/configuration data |
| `actions/agents_control.py` | Agent-related actions exposed to the primary assistant |
| `actions/agent_reach.py` | Agent reach/communication functionality |

These are valuable building blocks. The proposal is to clarify their boundaries and route them through a canonical runtime rather than discard them.

### 3.3 Coding engine execution

| File | Observed responsibility |
|---|---|
| `core/opencode_runner.py` | OpenCode CLI process runner |
| `core/kilo_runner.py` | Kilo CLI process runner |
| `core/antigravity_runner.py` | Antigravity CLI/process runner |
| `core/code_engines.py` | Code engine status/management functionality |
| `actions/opencode_agent.py` | OpenCode action wrapper |
| `actions/kilo_agent.py` | Kilo action wrapper |
| `actions/antigravity_agent.py` | Antigravity action wrapper |
| `actions/code_engines_status.py` | Engine status action |

**Verified distinction:** Current OpenCode and Kilo execution paths use CLI commands/subprocess runners. The supplied source review did not identify a complete ACP client lifecycle (`initialize`, `session/new`, `session/prompt`, JSON-RPC event handling) for these runners. Existing MCP support in `core/mcp_runtime.py` is a separate protocol and must not be mistaken for ACP.

### 3.4 Tools/actions

- `actions/` contains individual action modules.
- `core/action_loader.py` dynamically discovers and loads actions.
- Action modules expose tool metadata/handlers.
- `actions/agents_control.py` can invoke internal agent functionality.
- Some actions can invoke other execution paths, including coding engines and skills.

The central issue is that tool availability declarations and actual execution authorization need a single enforceable boundary. A tool being hidden from an agent is not sufficient security if another internal path can call the registry directly without checking the same policy.

### 3.5 Skills

| File | Observed responsibility |
|---|---|
| `core/skill_loader.py` | Skill discovery/loading |
| `core/skill_runner.py` | Skill-driven procedural execution |
| `core/skill_scanner.py` | Skill safety scanning |
| `core/skill_prompt_engineer.py` | Skill/prompt assistance |
| `actions/run_skill.py` | Skill execution action |
| `config/skills_state.json` | Skill state/configuration |
| `skills/` | Markdown skill packages |

The current project contains both skill loading/context injection and a procedural SkillRunner. These responsibilities should be clearly separated. A skill should primarily describe reusable instructions and workflow guidance; tools should perform actual operations through the permission-enforced tool executor.

### 3.6 Memory and persistence

| File | Observed responsibility |
|---|---|
| `memory/memory_manager.py` | Long-term memory management |
| `memory/sqlite_memory.py` | SQLite-backed memory/history functionality |
| `memory/memory_condenser.py` | Conversation condensation |
| `memory/memory_state.py` | Memory state |
| `memory/vault_engine.py` | Markdown knowledge vault functionality |
| `memory/config_manager.py` | Configuration management |
| `actions/memory_tool.py` | Memory tool interface |
| `actions/recall_history.py` | History recall action |

There are multiple memory-related stores and responsibilities. The target should not force every memory type into one table or one file, but should provide one coherent Memory Service and consistent APIs.

### 3.7 Frontend

The React frontend includes:

- `frontend/src/components/office/AgentDirectChatView.tsx`
- `frontend/src/components/office/AgentChatThread.tsx`
- `frontend/src/components/office/AgentConfigModal.tsx`
- `frontend/src/components/office/AgentWorkspaceView.tsx`
- `frontend/src/components/office/AgentRosterTable.tsx`
- `frontend/src/components/office/AutonomousOfficeScreen.tsx`
- `frontend/src/components/agents/AgentInspector.tsx`
- `frontend/src/components/agents/AgentsRoster.tsx`
- `frontend/src/components/settings/SkillsSettingsTab.tsx`
- `frontend/src/components/settings/ToolsSettingsTab.tsx`
- `frontend/src/components/settings/CodeEnginesSettingsTab.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/hooks/useZezoSocket.ts`
- `frontend/src/types/zezo.ts`

The UI already has a foundation for an Agents Office. The redesign should preserve and improve this work rather than replace the whole frontend without evidence.

### 3.8 Important current behavior and risks identified

The following are findings from the supplied source review and should be confirmed with focused tests during the audit/migration phases:

1. **Different chat and execution paths:** The Agent Office chat route in `core/ui_server.py` uses a direct Gemini text response path (`gemini.text(...)`) rather than consistently running the selected agent through the same engine/runtime lifecycle as task dispatch. The frontend chat view also stores conversation state locally. This risks UI history and backend session context drifting apart.
2. **CLI-based coding engines:** OpenCode and Kilo runners launch CLI commands. A complete ACP adapter was not found in the supplied source.
3. **Tool permission boundary:** `allowed_tools` filtering and actual tool execution authorization are not one centralized enforcement boundary. Internal direct registry calls need the same checks as normal agent tool calls.
4. **Multi-agent dependency handling:** Existing orchestration includes decomposition and worktree-related behavior, but task dependencies and merge coordination need stronger explicit modeling. A dependent QA task must wait for implementation completion.
5. **Peer communication and loop prevention:** Agent reach/delegation paths need centrally enforced parent/child relationships, call-chain propagation, depth limits, and idempotency. Prompt-only loop prevention is insufficient.
6. **Skill execution overlap:** Skill loading, skill prompt injection, and procedural skill execution overlap. Tool authorization must apply equally when a skill invokes a tool.
7. **Memory fragmentation:** Multiple stores have overlapping responsibilities and agent chat does not consistently share a unified memory/session contract.
8. **Documentation drift risk:** The repository contains multiple architecture documents, plans, journals, backups, prototypes, and code. Documentation should be reconciled after the target architecture is agreed, not treated as proof that every documented feature is implemented.

---

## 4. QwenPaw Reference: Patterns Worth Adapting

The supplied QwenPaw documentation is a useful reference because it describes a more explicit separation of workspace, agent construction, tools, ACP, subagents, and memory. ZEZO should adapt the underlying design principles, not copy its code or assume every documented choice is perfect.

### 4.1 Workspace and agent lifecycle

The reference distinguishes a long-lived workspace from an agent object that can be constructed for a request. The useful lesson is to avoid treating a process/runtime object as the permanent identity of an agent.

**ZEZO adaptation:**
- Agent Profile is persistent.
- Workspace configuration is persistent and separately managed.
- Agent Runtime is created for a run/session.
- Runtime loads the profile and allowed capabilities.
- Runtime can be stopped/recreated without losing the agent's identity or history.

### 4.2 Internal subagents vs external ACP runners

QwenPaw documents internal subagent spawning and external ACP runners as separate concepts.

**ZEZO adaptation:**
- Internal agent delegation is managed by ZEZO's Task Orchestrator.
- External coding tools are managed by Engine Adapters.
- ACP is one possible adapter protocol.
- A worker agent may use a native model runtime or an external engine.
- Internal agent identity and external runner session identity remain separate.

### 4.3 Tool governance

The reference describes centralized tool wrapping, validation, policy checks, approvals, resource controls, and sandboxing.

**ZEZO adaptation:** Every tool call, regardless of origin, must pass through one `ToolExecutor` and policy boundary. This includes calls originating from:
- ZEZO's primary agent.
- A user-created agent.
- A skill workflow.
- A delegated worker.
- An external-engine action exposed as a tool.

### 4.4 Memory separation

The reference distinguishes durable history, session snapshots, and memory backends.

**ZEZO adaptation:** Keep conversation history, session state, task state, and long-term facts separate, while exposing them through one Memory/Session service API.

### 4.5 Reference limitations to respect

The supplied QwenPaw documentation itself describes limitations, including text-only ACP prompt forwarding in the documented path, workspace-manager stubs, and prompt/skill-level rather than hard runtime enforcement for some cross-talk prevention. Therefore:
- Do not assume ACP handles every attachment or multimodal payload.
- Do not treat prompt instructions as a security boundary.
- Do not assume an ACP-compatible client means every external engine supports ACP.
- Verify protocol support and behavior for the exact installed runner version.

---

## 5. Proposed Target Architecture

### 5.1 High-level architecture

```text
                         FRONTEND
       +------------------------------------------+
       | ZEZO Primary Chat | Agent Chat | Office  |
       | Agent Builder     | Tasks      | Settings|
       +----------------------+-------------------+
                              |
                         API / WebSocket
                              |
                    Application Facade
                              |
              +---------------+----------------+
              |                                |
         Agent Manager                   Task Manager
              |                                |
         Agent Registry                 Task Orchestrator
              |                                |
              +---------------+----------------+
                              |
                         Agent Runtime
                              |
        +---------------------+----------------------+
        |          |           |          |          |
      Model      Skills      Tools      Memory    Workspace
      Router     Resolver    Executor   Service   Manager
        |                     |
        |                Policy / Approval
        |
    Execution / Engine Layer
        |
   +----+-------------------------+
   |                              |
 Native Model Runtime        Engine Adapters
                                  |
                      +-----------+-----------+
                      |           |           |
                   OpenCode      Kilo      Other Runners
                    ACP/CLI    Verified CLI  ACP/CLI
```

### 5.2 Architectural rules

1. **One runtime contract:** Primary ZEZO chat, independent agent chat, and delegated agent tasks use the same Agent Runtime contract.
2. **One tool enforcement point:** No internal path executes a tool without the central policy/executor.
3. **Profiles are data:** Agent configuration must not be mixed with live runtime/process state.
4. **Orchestration is separate from execution:** Task planning/delegation does not directly implement model/engine communication.
5. **Protocol adapters are isolated:** ACP, CLI, MCP, and native tools have different contracts.
6. **Persistence is explicit:** Sessions, messages, runs, tasks, events, approvals, and memory have stable IDs and repository interfaces.
7. **UI is not the source of truth:** Backend owns session/task state. Frontend local storage may cache preferences or drafts, not canonical agent conversation history.
8. **Modular monolith first:** Keep one deployable application initially. Use clean module boundaries rather than introducing microservices prematurely.

### 5.3 Proposed backend modules and responsibilities

| Module | Responsibility | Must not do |
|---|---|---|
| `agents/` | Agent profile CRUD, registry, lifecycle metadata | Launch arbitrary CLI processes directly |
| `runtime/` | Unified run lifecycle, context assembly, event streaming | Own provider-specific protocol code |
| `models/` | Model provider selection and model API calls | Manage multi-agent task dependencies |
| `engines/` | Native/ACP/CLI runner adapters | Decide business-level task delegation |
| `tools/` | Tool schemas, registry, executor, validation | Bypass permissions |
| `skills/` | Skill discovery, metadata, resolution, injection, scanning | Execute ungoverned side effects |
| `orchestration/` | Plans, task graph, delegation, concurrency, result aggregation | Directly implement engine protocol |
| `sessions/` | Conversations, messages, session state | Store long-term facts as chat messages |
| `memory/` | Memory policy, facts, retrieval, summarization | Become a second task manager |
| `workspaces/` | Project/worktree isolation and workspace policy | Own agent profile identity |
| `security/` | Permissions, approvals, policy decisions, audit events | Depend only on prompt instructions |
| `storage/` | Database setup, migrations, repositories | Embed product logic in SQL helpers |
| `observability/` | Structured logs, traces, metrics, run events | Store secrets or raw sensitive prompts unnecessarily |
| `api/` | HTTP/WebSocket schemas and routes | Duplicate business logic from services |

---

## 6. Agent Profile, Chat, Session and Run Model

### 6.1 Separate the concepts

| Concept | Meaning | Lifetime |
|---|---|---|
| Agent | User-configured identity and capabilities | Persistent |
| Conversation | A chat thread belonging to ZEZO or an agent | Persistent |
| Session | Runtime continuity/context for a conversation or engine | Persistent metadata; runtime may reconnect |
| Run | One execution triggered by a message/task | Finite |
| Task | A unit of work that may be delegated or scheduled | Persistent until terminal state |
| Engine session | External runner session ID, e.g. ACP/CLI-specific | Adapter-managed |
| Workspace | Project/filesystem scope | Persistent configuration; worktree may be temporary |

Do not use one `session_id` field to mean all of these things.

### 6.2 Recommended data model

Suggested entities/tables (names are proposals):

- `agents`: profile and configuration.
- `agent_capabilities`: normalized skill/tool assignments if needed.
- `conversations`: owner type (`zezo` or `agent`), owner ID, title, timestamps.
- `messages`: role, content, attachments metadata, tool/run references.
- `runs`: run ID, conversation ID, agent ID, status, model/engine selection, timestamps.
- `run_events`: ordered event stream, progress, tool calls, errors, approval requests.
- `engine_sessions`: adapter type, external session ID, state, metadata.
- `tasks`: parent task, assigned agent, status, priority, dependency metadata.
- `task_dependencies`: prerequisite task relationships.
- `task_artifacts`: output paths, commits, reports, references.
- `tool_approvals`: requested action, policy decision, approver, status.
- `memory_items`: scoped durable facts/notes with provenance and confidence.
- `workspaces`: project roots, access policy, worktree metadata.
- `audit_events`: security-relevant operations.

SQLite is a reasonable initial persistence choice for a single-user desktop app, provided transactions, migrations, indexes, and concurrency are handled carefully. Do not create a second database for every feature without a clear reason.

### 6.3 Independent agent chat behavior

Each agent's conversation should be associated with that agent ID. ZEZO should not automatically expose every private agent conversation to every other agent.

Recommended default:
- Agent conversations are private to that agent and the user.
- ZEZO may receive an explicit summary/result from a delegated task.
- Full transcript sharing requires an explicit context-sharing policy.
- Cross-agent memory access is denied by default.
- User can configure shared project memory or selected shared knowledge.

### 6.4 Unified runtime lifecycle

```text
Incoming message/task
        |
Resolve conversation + agent profile
        |
Create Run record
        |
Load workspace + session context
        |
Resolve model/engine adapter
        |
Resolve skills and permitted tools
        |
Evaluate policy and context limits
        |
Execute and stream structured events
        |
Persist messages, events, outputs and state
        |
Return final result
```

A run should have a stable `run_id`, and every tool call/event should reference it.

---

## 7. Tools Architecture

### 7.1 Proposed structure

```text
tools/
  registry.py
  schemas.py
  executor.py
  validation.py
  context.py
  adapters/
  definitions/
```

Existing action modules can initially remain as tool implementations. They should gradually register through the canonical registry.

### 7.2 Required execution contract

Every tool call should follow this sequence:

1. Resolve tool by stable ID.
2. Validate input against its schema.
3. Identify caller: ZEZO, agent, skill, or delegated task.
4. Check caller's allowed tool list.
5. Check risk level and resource scope.
6. Check workspace/file/network boundaries.
7. Request user approval when policy requires it.
8. Execute with timeout and cancellation support.
9. Record result/error and audit event.
10. Return a structured result to the runtime.

No action handler should be able to bypass this contract through direct registry calls.

### 7.3 Permission model

Suggested risk levels:

| Level | Example | Default policy |
|---|---|---|
| `R0` | Read-only information retrieval | Allow within granted scope |
| `R1` | Reversible file edits or project changes | Allow only within assigned workspace and permissions |
| `R2` | Destructive, external, system-level, or irreversible action | Require explicit approval or deny by default |

The exact classification of every existing action must be audited. Do not assume the current labels are accurate.

### 7.4 Agent-specific tools

The UI may show all available tools, but the backend must enforce the selected agent's allowlist. UI hiding is not authorization.

A skill may request tools, but the effective set must be:

`agent_allowed_tools ∩ policy_allowed_tools ∩ skill_requested_tools`

If the intersection is empty, the skill must not gain extra capabilities.

---

## 8. Skills Architecture

### 8.1 Skill definition

Skills should remain human-readable Markdown packages with structured metadata.

Example:

```yaml
---
name: website-build
description: Build or modify a website in an assigned project workspace.
triggers:
  - build a website
  - create a landing page
allowed_tools:
  - filesystem.read
  - filesystem.write
  - terminal.run
---
```

The exact metadata schema should be versioned and validated. Avoid multiple incompatible frontmatter formats.

### 8.2 Proposed skill lifecycle

```text
Skill files
    |
Skill Scanner
    |
Skill Registry
    |
Skill Resolver (agent + task + intent)
    |
Permission intersection
    |
Context injection
    |
Agent Runtime
```

### 8.3 Design decisions

- A skill is primarily instructions, examples, constraints, and workflow guidance.
- Tools perform side effects.
- A skill must not grant itself permissions.
- Skill matching should use explicit assignments first, then optional intent-based suggestions.
- Do not inject every skill into every prompt.
- Skill content should be loaded progressively: metadata first, full instructions only when selected.
- The same skill resolution and permission path must apply to ZEZO and custom agents.
- Self-learning may suggest a new skill draft, but must not silently install or grant it privileged tools.

### 8.4 SkillRunner decision

`core/skill_runner.py` should not be deleted immediately. First inventory which workflows depend on its procedural execution behavior. Then:
- Move reusable workflow orchestration into explicit workflow/task definitions if needed.
- Move actual side effects into governed tools.
- Retain a compatibility wrapper temporarily.
- Remove the old SkillRunner only after all callers have migrated and tests pass.

---

## 9. Multi-Agent Orchestration

### 9.1 Separate agent communication from ACP

Internal agent collaboration should be a ZEZO-native service.

The orchestrator should create tasks and deliver controlled context to workers. Workers should return structured outputs. Agents should not freely call one another's private runtime sessions.

### 9.2 Task lifecycle

Recommended statuses:

`PENDING -> READY -> RUNNING -> WAITING_APPROVAL -> COMPLETED`

Terminal alternatives:
- `FAILED`
- `CANCELLED`
- `BLOCKED`
- `TIMED_OUT`

Each task should contain:
- `task_id`
- `parent_task_id`
- `assigned_agent_id`
- `conversation_id` (optional)
- `run_id`
- `status`
- `priority`
- `input_summary`
- `acceptance_criteria`
- `dependencies`
- `workspace_id`
- `created_at`, `started_at`, `finished_at`
- `result_summary`
- `artifact_refs`
- `error`

### 9.3 Delegation flow

```text
User
 |
ZEZO Runtime
 |
Task Planner
 |
Task Orchestrator
 |--------------------|
 |                    |
Worker Task A       Worker Task B
 |                    |
Agent Runtime       Agent Runtime
 |                    |
Tools/Skills        Tools/Skills
 |                    |
Structured Result   Structured Result
 |--------------------|
 |
Dependency / validation checks
 |
ZEZO synthesizes final response
```

### 9.4 Concurrency and dependencies

- Start with a conservative configurable concurrency limit.
- Run only tasks whose dependencies are complete.
- Use idempotency keys to prevent duplicate task execution.
- Support cancellation and timeout propagation.
- Use bounded retries only for retryable failures.
- Persist task state so application restart does not silently lose the task ledger.
- Make merge strategy explicit for tasks that modify the same repository.
- Prefer isolated worktrees for parallel code changes.
- Require integration/validation before declaring a multi-agent coding task complete.

### 9.5 Loop prevention

Enforce loop prevention in code:
- Parent/child task relationship.
- Maximum delegation depth.
- Maximum tasks per parent.
- Maximum total tool/agent calls per run.
- Cycle detection for repeated agent/task pairs.
- Call-chain propagation.
- Idempotency keys.
- Time and resource budgets.

Prompt instructions may supplement these controls but cannot replace them.

### 9.6 Agent-to-agent message format

Prefer structured task handoffs over unbounded free-form chat:

```json
{
  "task_id": "task_x",
  "parent_task_id": "task_parent",
  "from_agent": "zezo",
  "to_agent": "developer",
  "objective": "Implement the approved API endpoint",
  "context_refs": ["conversation_summary", "spec_file"],
  "acceptance_criteria": [
    "Endpoint validates input",
    "Tests cover success and failure"
  ],
  "allowed_tools": ["filesystem.read", "filesystem.write", "terminal.run"],
  "workspace_id": "workspace_x"
}
```

Workers return status, summary, artifacts, test results, and blockers. They should not need direct access to another worker's private transcript.

---

## 10. External Engines and ACP Strategy

### 10.1 Engine adapter contract

Proposed interface:

```python
class EngineAdapter:
    async def connect(self, config): ...
    async def create_session(self, context): ...
    async def send_message(self, session_id, message): ...
    async def stream_events(self, session_id): ...
    async def request_permission(self, request): ...
    async def cancel(self, session_id, run_id): ...
    async def close_session(self, session_id): ...
    async def health_check(self): ...
```

This is illustrative, not existing code. Adapter methods should return normalized ZEZO events and typed errors.

### 10.2 Adapter types

| Adapter | Purpose |
|---|---|
| Native model adapter | ZEZO-managed model/tool loop |
| ACP adapter | External agent runner speaking ACP |
| CLI adapter | External runner controlled through supported CLI |
| MCP client/runtime | Connect to external MCP tool servers |

Do not combine these into one generic subprocess module.

### 10.3 OpenCode

- Keep current CLI execution as a compatibility path while building the adapter boundary.
- Verify the exact installed OpenCode version's ACP support and launch contract.
- If supported, implement ACP lifecycle and event mapping.
- Preserve CLI adapter for features or environments where ACP is unavailable.
- Persist external session identifiers separately from ZEZO conversation/session IDs.
- Test permission prompts, cancellation, process exit, stderr, timeout, reconnect, and session recovery.

### 10.4 Kilo

- Do not label Kilo as ACP-supported until verified against official/current Kilo documentation and the actual installed version.
- Keep `kilo_runner.py` behind the CLI adapter contract initially.
- If Kilo supports ACP in the target version, implement a separate ACP capability path.
- If not, continue using the CLI adapter or a supported API integration.
- Do not force Kilo into the OpenCode adapter simply because both are coding agents.

### 10.5 MCP is separate

`core/mcp_runtime.py` is an MCP integration path. MCP exposes tools/resources through its own protocol. It should connect to the Tool Registry through a dedicated MCP adapter, not be renamed or reused as ACP.

---

## 11. Memory and Context Architecture

### 11.1 Separate data categories

| Category | What it stores | Owner |
|---|---|---|
| Conversation history | User and agent messages | Session service |
| Run context | Context assembled for one execution | Runtime |
| Task context | Objective, acceptance criteria, delegated summaries | Orchestrator |
| Agent memory | Facts/preferences specific to one agent | Memory service |
| Shared project memory | Approved project knowledge | Memory service/workspace |
| Global user memory | User-approved preferences/facts | Memory service |

### 11.2 Memory access policy

- Agent-specific memory is private by default.
- Shared project memory is explicitly scoped.
- ZEZO may receive worker summaries/results, not unrestricted worker memory.
- Memory entries should retain provenance, timestamp, scope, and confidence.
- User should be able to inspect and delete stored memories.
- Sensitive data should not be automatically promoted to long-term memory.

### 11.3 Consolidation approach

Do not immediately delete `memory_manager.py`, `sqlite_memory.py`, `vault_engine.py`, or `memory_condenser.py`.

First map all read/write callers and identify which store is canonical for each data type. Then define one Memory Service facade and repositories behind it. Preserve import/export and migration paths. Remove redundant storage only after data migration and regression tests.

---

## 12. Frontend Proposal

### 12.1 Main product navigation

The UI should make the distinction clear:

- **ZEZO Chat:** Primary assistant.
- **Agents:** User-created agents and their independent chats.
- **Tasks:** Active, queued, completed, failed, and delegated tasks.
- **Skills:** Browse, assign, inspect, and manage skills.
- **Tools & Permissions:** Available tools and access boundaries.
- **Engines:** Configure and check external coding runners.
- **Memory:** Inspect and manage agent/shared memory.

The existing Agents Office can remain as a visual workspace, but the backend task ledger must be the source of truth.

### 12.2 Agent builder

The Agent Builder should provide:
1. Identity and description.
2. Instructions/personality.
3. Model and engine.
4. Skill assignment.
5. Tool assignment.
6. Permission/risk policy.
7. Workspace access.
8. Memory policy.
9. Test chat/preview.
10. Save and enable/disable.

Avoid presenting options that the backend cannot enforce.

### 12.3 Agent chat

Agent chat should display:
- Conversation history loaded from backend.
- Run status and streaming response.
- Tool activity and approvals.
- Engine/session state when relevant.
- Task delegation events.
- Artifacts and output links.
- Clear errors and retry/cancel controls.

Frontend local storage may cache UI state, drafts, or preferences. It should not be the canonical storage for conversation messages.

### 12.4 Frontend files to preserve and refactor

The current UI components are a useful foundation. Refactor their API/state integration rather than rewriting the design without need.

---

## 13. Proposed File and Directory Disposition

**Important:** `REMOVE` below means a proposed removal candidate, not permission to delete now. Every removal requires a repository-wide import/reference check, runtime verification, and migration plan. Files with unclear ownership are marked `REVIEW`, not assumed unnecessary.

### 13.1 Core application

| Existing path | Proposed status | Reason / action |
|---|---|---|
| `main.py` | REFACTOR | Keep application entry and primary assistant orchestration thin. Move agent lifecycle/business logic into services. |
| `core/ui_server.py` | REFACTOR | Keep API server/routes temporarily; move business logic into application services and make chat use Agent Runtime. |
| `core/dispatcher.py` | REFACTOR | Separate intent/request routing from tool execution and agent orchestration. |
| `core/action_loader.py` | REFACTOR | Evolve into compatibility loader/registration bridge for canonical Tool Registry. |
| `core/agents_manager.py` | REFACTOR | Keep as facade during migration; delegate to AgentService/Registry/Runtime/Orchestrator. |
| `core/agents/registry.py` | KEEP + REFACTOR | Preserve registry concept; validate profiles and use repository persistence. |
| `core/agents/dispatcher.py` | REPLACE IN PHASES | Replace overlapping dispatcher responsibilities with Agent Runtime + execution service. Retain compatibility wrapper during migration. |
| `core/agents/orchestrator.py` | REFACTOR | Keep orchestration concept; replace ad hoc decomposition/dispatch with persistent task graph, dependencies, concurrency, and result aggregation. |
| `core/task_manager.py` | REFACTOR | Make it a task execution worker/scheduler, not a second agent orchestrator. Persist task lifecycle. |
| `core/models.py` | REVIEW / REFACTOR | Inspect model ownership; move domain schemas into module-specific schemas and keep only shared domain types. |
| `core/llm_client.py` | KEEP + REFACTOR | Keep provider client abstraction if used; normalize provider errors and streaming. |
| `core/llm_router.py` | KEEP + REFACTOR | Keep model routing separate from engine routing. |
| `core/gemini.py` | KEEP / ADAPTER | Retain Gemini integration behind model provider interface. |
| `core/code_engines.py` | REFACTOR | Turn into engine registry/status facade; do not duplicate adapter execution. |
| `core/opencode_runner.py` | REFACTOR | Wrap as OpenCode CLI adapter; later add ACP adapter only after compatibility verification. |
| `core/kilo_runner.py` | REFACTOR | Wrap as Kilo CLI adapter; ACP only if supported and verified. |
| `core/antigravity_runner.py` | REFACTOR | Wrap behind a common CLI/engine adapter contract. |
| `core/mcp_runtime.py` | KEEP + REFACTOR | Preserve MCP as a distinct protocol adapter feeding the Tool Registry. |
| `core/plugin_loader.py` | REVIEW | Clarify whether plugins are separate from tools/MCP; merge only if responsibilities truly overlap. |
| `core/skill_loader.py` | REFACTOR | Make it a Skill Registry/Loader, not a parallel execution system. |
| `core/skill_runner.py` | REVIEW -> DEPRECATE AFTER MIGRATION | Inventory callers; migrate side effects to governed tools and workflow/task services before removal. |
| `core/skill_scanner.py` | KEEP + REFACTOR | Preserve security scanning; run on install/update and before activation, with clear policy. |
| `core/skill_prompt_engineer.py` | REVIEW | Determine whether it is a necessary authoring utility or duplicated prompt synthesis. |
| `core/prompt*` and `core/prompts/` | REFACTOR | Consolidate prompt/context assembly behind runtime context builder; preserve useful archetypes and templates. |
| `core/governance.py` | KEEP + REFACTOR | Make it the canonical policy decision service, called by every tool/engine action. |
| `core/confirm.py` | MERGE / REFACTOR | Fold approval state and confirmation UI contract into Security/Approvals service if duplicate. |
| `core/loop_gates.py` | KEEP + REFACTOR | Reuse loop limits, but enforce centrally for runs and delegated task trees. |
| `core/circuit_breaker.py` | KEEP | Reuse for external provider/engine failure isolation; standardize integration. |
| `core/log_bus.py` | KEEP + REFACTOR | Preserve event/log transport; define structured event schema and correlation IDs. |
| `core/provider_health.py` | KEEP + REFACTOR | Retain health checks behind provider/engine status services. |
| `core/git_sandbox.py` | KEEP + REFACTOR | Preserve workspace/worktree isolation; connect to Workspace Manager and task artifacts. |
| `core/repo_context.py` | KEEP + REFACTOR | Retain project context extraction; expose through runtime context service. |
| `core/deliverable_verifier.py` | KEEP + REFACTOR | Keep verification as a reusable completion/acceptance check. |
| `core/undo.py` | KEEP / REVIEW | Preserve if user-facing actions depend on it; integrate with tool execution/audit model. |
| `core/pending_intent.py` | REVIEW | Confirm whether still used by the primary assistant; remove only if superseded. |
| `core/fast_intent.py` | REVIEW | Keep only if measurable value and clear routing boundary exist. |
| `core/laya_router.py` | REVIEW | Clarify ownership and usage before deciding to retain or remove. |
| `core/echo.py` | REVIEW | Determine whether it is production behavior, debugging, or obsolete. |
| `core/url_prefetch.py` | KEEP / REVIEW | Preserve if primary assistant uses it; keep outside agent orchestration. |
| `core/file_reader.py` | REVIEW / MERGE | Check overlap with `actions/file_processor.py` and tool implementations; centralize filesystem access. |
| `core/tunnel_manager.py` | KEEP / SEPARATE | Remote connectivity is a separate subsystem; do not mix it into agent runtime. |
| `core/installer.py` | KEEP / SEPARATE | Packaging/install concerns remain outside agent architecture. |
| `core/computer/` | KEEP + REFACTOR | Preserve platform/computer drivers; expose them as governed tools. |
| `core/audio_devices.py`, `wake_word.py`, `viseme.py`, `hotkey.py`, `clipboard_watcher.py`, `screen_capture` related modules | KEEP / SEPARATE | Voice/desktop interaction is core ZEZO functionality but should remain separate from agent orchestration. |

### 13.2 Actions/tools

| Existing path | Proposed status | Reason / action |
|---|---|---|
| `actions/` | REFACTOR | Preserve action implementations initially; register all through one Tool Registry/Executor. |
| `actions/agents_control.py` | REFACTOR | Convert into thin orchestration API/tool; must not bypass task lifecycle or permissions. |
| `actions/agent_reach.py` | REPLACE IN PHASES | Move peer communication to internal Task Orchestrator; retain compatibility facade during migration. |
| `actions/opencode_agent.py` | REFACTOR | Thin tool wrapper over OpenCode adapter; no direct process management. |
| `actions/kilo_agent.py` | REFACTOR | Thin wrapper over Kilo adapter. |
| `actions/antigravity_agent.py` | REFACTOR | Thin wrapper over Antigravity adapter. |
| `actions/run_skill.py` | REFACTOR | Resolve skill through Skill Registry and run through Agent Runtime/workflow service. |
| `actions/run_tool_batch.py` | REVIEW / REFACTOR | Keep only if batching is a distinct supported feature; all nested calls must pass through ToolExecutor. |
| `actions/task_status.py` | KEEP + REFACTOR | Query canonical Task Service. |
| `actions/memory_tool.py`, `actions/recall_history.py` | REFACTOR | Route through Memory/Session services with scope checks. |
| `actions/code_engines_status.py` | KEEP + REFACTOR | Query Engine Manager. |
| Other action files (`browser_control.py`, `computer_control.py`, `file_controller.py`, `web_search.py`, etc.) | KEEP + STANDARDIZE | Preserve features; standardize schemas, timeouts, permission checks, and result formats. |
| `actions/youtube_video.py.bak` | REMOVE CANDIDATE | Backup file in source tree; verify no imports/references, then remove from active repository. |

### 13.3 Skills

| Existing path | Proposed status | Reason / action |
|---|---|---|
| `skills/` | KEEP + STANDARDIZE | Preserve Markdown skills; validate metadata schema and version. |
| `skills/website_build/` | KEEP | Existing domain skill and references remain useful. |
| `skills/website_clone/` | KEEP | Preserve if still supported; route all operations through governed tools. |
| `skills/generate_design_md/` | KEEP | Preserve as a reusable skill. |
| `.claude/skills/karpathy-guidelines/` | REVIEW / MOVE | Determine whether this is an authoring-only instruction or a ZEZO runtime skill. Move to canonical skill library only if needed. |
| `config/skills_state.json` | REFACTOR | Treat as state/config source only if still needed; move authoritative assignments/activation into persistent Skill Registry data. |

### 13.4 Memory

| Existing path | Proposed status | Reason / action |
|---|---|---|
| `memory/memory_manager.py` | REFACTOR | Make it the public Memory Service facade or replace with a clean service after caller migration. |
| `memory/sqlite_memory.py` | KEEP + REFACTOR | Preserve SQLite implementation; separate history, facts, and retrieval repositories. |
| `memory/memory_condenser.py` | KEEP / REFACTOR | Keep summarization as a service with provenance and explicit scope. |
| `memory/memory_state.py` | REVIEW | Determine whether state duplicates SQLite or config state. |
| `memory/vault_engine.py` | KEEP / REFACTOR | Preserve Markdown vault if valuable; define it as a knowledge-store adapter, not a competing memory manager. |
| `memory/config_manager.py` | REVIEW / MERGE | Move configuration ownership to central config/storage services if duplicated. |
| `memory/vault/` conversation records | PRIVATE DATA, NOT SOURCE | Exclude from source archive; retain/migrate user data separately. |
| `memory/*.bak`, `*.pre-fix*.bak` | REMOVE CANDIDATE | Backup artifacts; archive outside active source only after recovery need is assessed. |

### 13.5 Frontend

| Existing path | Proposed status | Reason / action |
|---|---|---|
| `frontend/src/components/office/AgentDirectChatView.tsx` | REFACTOR | Use backend conversation/session APIs and unified Agent Runtime. Remove canonical chat history dependence on localStorage. |
| `frontend/src/components/office/AgentChatThread.tsx` | KEEP + REFACTOR | Render messages and structured run events from backend. |
| `frontend/src/components/office/AgentConfigModal.tsx` | REFACTOR | Expand into a clear Agent Builder with validated profile, engine, skills, tools, permissions, memory, and workspace configuration. |
| `frontend/src/components/office/AgentWorkspaceView.tsx` | KEEP + REFACTOR | Display agent workspace and task artifacts from canonical APIs. |
| `frontend/src/components/office/AgentRosterTable.tsx` | KEEP + REFACTOR | Use Agent Registry APIs. |
| `frontend/src/components/office/AutonomousOfficeScreen.tsx` | KEEP + REFACTOR | Make it a view over canonical agents/tasks, not an independent state system. |
| `frontend/src/components/agents/AgentInspector.tsx` | REVIEW / MERGE | Check overlap with Agent Builder/Workspace views; merge responsibilities if duplicated. |
| `frontend/src/components/agents/AgentsRoster.tsx` | REVIEW / MERGE | Check overlap with `AgentRosterTable.tsx`; retain one canonical roster component. |
| `frontend/src/components/settings/SkillsSettingsTab.tsx` | KEEP + REFACTOR | Connect to Skill Registry and agent assignments. |
| `frontend/src/components/settings/ToolsSettingsTab.tsx` | KEEP + REFACTOR | Show capabilities and permission policy; backend remains authoritative. |
| `frontend/src/components/settings/CodeEnginesSettingsTab.tsx` | KEEP + REFACTOR | Connect to Engine Manager and adapter health. |
| `frontend/src/lib/api.ts` | REFACTOR | Centralize typed API client and error handling. |
| `frontend/src/hooks/useZezoSocket.ts` | KEEP + REFACTOR | Standardize event envelopes, reconnect, ordering, and correlation IDs. |
| `frontend/src/types/zezo.ts` | REFACTOR | Split into typed domain models for agents, sessions, runs, tasks, tools, and skills. |
| `frontend/src/components/assistant-ui/` | KEEP / REVIEW | Preserve shared chat UI; connect it to the unified conversation/run event model. |
| `frontend/src/components/ui/`, `reui/`, `prompt-kit/` | REVIEW | Identify unused/duplicate primitives before removing; do not mass-delete based on naming. |
| `frontend/src/App.tsx`, `App.css`, `index.css` | KEEP / REFACTOR | Preserve app shell and styling; keep architecture work separate from visual redesign. |
| `frontend/src/classic_style.css` | REVIEW | Check active imports and usage; remove only if unused. |

### 13.6 Documentation, plans, prototypes and root files

| Existing path/group | Proposed status | Reason / action |
|---|---|---|
| `AGENTS_SYSTEM_ARCHITECTURE.md` | REPLACE AFTER APPROVAL | Supersede with approved target architecture; preserve historical copy in archive. |
| `docs/AGENTS_MANAGEMENT.md` | REWRITE | Align with actual agent profile/runtime lifecycle. |
| `docs/AI_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `docs/DATA_FLOW.md`, `docs/REQUEST_LIFECYCLE.md` | RECONCILE | Consolidate overlapping architecture descriptions into a canonical set. |
| `docs/TOOLS.md`, `docs/SKILLS_SYSTEM.md`, `docs/MEMORY.md`, `docs/TASK_SYSTEM.md`, `docs/CODE_ENGINES.md`, `docs/SESSION_MANAGEMENT.md` | UPDATE | Document canonical module boundaries and verified behavior. |
| `docs/` other subsystem docs | KEEP / UPDATE AS NEEDED | Voice, computer control, remote, UI, and installer documentation remain relevant but are outside the agent redesign unless they cross boundaries. |
| `discussions/`, `planning/` | ARCHIVE / REVIEW | Keep decision history; mark superseded plans clearly. Do not treat every plan as active implementation truth. |
| `baseline/` | ARCHIVE / REVIEW | Historical snapshots; remove from production package if not runtime dependencies. Preserve outside active source if useful for recovery. |
| `prototypes/` | ARCHIVE / REVIEW | Keep design references outside runtime package; remove from distributable build if not used. |
| `References/` | ARCHIVE / REVIEW | Design inspiration/reference assets, not runtime architecture. |
| `LEARNING_JOURNAL*.md`, `WORKING_WITH_HAMZA.md` | PRIVATE/TEAM DOCUMENTATION REVIEW | Keep only if intentionally part of project docs; exclude from public/source-sharing bundles when they contain personal context. |
| `readme.md`, `README.md`, `AGENTS.md` | KEEP + UPDATE | Make project entry instructions consistent with approved architecture and strict engineering rules. |
| `config/agents.json` | KEEP + MIGRATE | Preserve agent definitions; add schema validation and migration to canonical profile repository. |
| `config/tools_state.json` | REFACTOR | Move authoritative tool state/permissions into Tool Registry/policy persistence. |
| `config/mcp_servers.json` | KEEP + VALIDATE | Keep MCP server configuration separate from ACP/engine config. |
| `config/api_keys*.json` | KEEP EXAMPLE ONLY | Keep sanitized examples; never commit real credentials. |
| `config/certs/*.key` | REMOVE FROM SOURCE CONTROL / ROTATE IF LIVE | Private keys must not be in source archives/repository. Use secure local secret storage. |
| `config/*.bak`, `*.ico.bak` | REMOVE CANDIDATE | Backup files; verify references before removal. |
| `frontend/node_modules`, Python virtual environments, caches, build outputs | EXCLUDE FROM SOURCE ARCHIVE | Generated dependencies/artifacts, not source-of-truth project files. |
| `.git/` | EXCLUDE FROM SHARED ZIP | Keep Git in the actual repository; omit from routine audit archives unless history analysis is specifically requested. |

### 13.7 Proposed new files/modules

These are proposed additions. Exact file names can change during implementation planning.

```text
core/
  api/
    routes/
      agents.py
      conversations.py
      tasks.py
      tools.py
      skills.py
      engines.py
    schemas/
      agent.py
      conversation.py
      task.py
      events.py

  agents/
    service.py
    profile.py
    registry.py
    repository.py

  runtime/
    agent_runtime.py
    run_manager.py
    context_builder.py
    event_stream.py
    execution_context.py

  models/
    provider_manager.py
    base.py
    schemas.py

  engines/
    base.py
    manager.py
    events.py
    adapters/
      native.py
      opencode_cli.py
      opencode_acp.py
      kilo_cli.py
      kilo_acp.py       # only if verified/supported
      antigravity_cli.py

  tools/
    registry.py
    executor.py
    schemas.py
    validation.py
    permissions.py
    definitions/

  skills/
    registry.py
    loader.py
    resolver.py
    scanner.py
    schemas.py

  orchestration/
    planner.py
    task_manager.py
    scheduler.py
    dependencies.py
    delegation.py
    result_aggregator.py

  sessions/
    service.py
    repository.py
    schemas.py

  memory/
    service.py
    policies.py
    retrieval.py
    repositories/

  workspaces/
    manager.py
    repository.py
    worktree.py

  security/
    policy_engine.py
    approvals.py
    audit.py

  storage/
    database.py
    migrations/
    repositories/

  observability/
    logger.py
    tracing.py
    metrics.py
```

Do not create all these files immediately. Add modules only as the corresponding responsibility is extracted from the existing code.

---

## 14. Security and Reliability Requirements

The following should be treated as release blockers for autonomous multi-agent execution:

1. Tool authorization is enforced server-side at execution time.
2. Agent profiles cannot grant themselves tools or permissions.
3. Skills cannot elevate privileges.
4. External engines run with explicit workspace and filesystem boundaries.
5. Destructive operations require approval or are denied by policy.
6. Secrets are not stored in agent prompts, logs, or source-controlled config.
7. External process launch uses argument arrays, controlled environment variables, timeouts, and safe working directories.
8. Engine sessions and task records are persisted and recoverable.
9. Cancellation propagates to child tasks and external processes.
10. Delegation has depth, concurrency, time, and resource limits.
11. Every run/tool/task has correlation IDs and an audit trail.
12. User data and agent memory are scoped and access-controlled.

---

## 15. Observability and Event Contract

Use one normalized event envelope across native runtime, ACP, CLI, tools, and orchestration.

Example:

```json
{
  "event_id": "evt_x",
  "event_type": "tool.started",
  "timestamp": "ISO-8601",
  "run_id": "run_x",
  "conversation_id": "conv_x",
  "agent_id": "agent_x",
  "task_id": "task_x",
  "source": "tool_executor",
  "payload": {}
}
```

Recommended event types:
- `run.created`
- `run.started`
- `run.progress`
- `run.completed`
- `run.failed`
- `agent.delegated`
- `task.queued`
- `task.started`
- `task.waiting_approval`
- `task.completed`
- `task.failed`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `approval.requested`
- `approval.granted`
- `approval.denied`
- `engine.connected`
- `engine.disconnected`
- `engine.session_created`

Every failure should include a safe, structured error code, human-readable message, retryability, and relevant IDs. Avoid logging credentials or unnecessary private content.

---

## 16. Testing Strategy

Do not rely only on unit tests or manual chat testing.

### 16.1 Unit tests

- Agent profile schema validation.
- Skill metadata validation and resolver.
- Tool schema validation.
- Permission intersection and risk policies.
- Task dependency scheduler.
- Delegation depth and cycle detection.
- Session repository and memory scope.
- Engine adapter event normalization.

### 16.2 Integration tests

1. Create agent -> assign skills/tools -> save -> reload -> verify configuration.
2. Start agent chat -> send message -> stream response -> restart app -> restore conversation.
3. Agent invokes allowed tool -> succeeds.
4. Agent invokes disallowed tool -> denied at execution boundary.
5. Skill requests a tool outside agent permissions -> denied.
6. ZEZO delegates to two agents -> both run concurrently -> results return.
7. Dependent task waits until prerequisite completes.
8. Cancel parent task -> child tasks and external process are cancelled.
9. OpenCode adapter handles session create, prompt, event stream, error, and cancel.
10. Kilo CLI adapter works independently of OpenCode adapter.
11. Restart during active task -> task state is recovered or marked interrupted accurately.
12. Worktree merge conflict -> task is not falsely marked complete.

### 16.3 End-to-end acceptance scenarios

**Scenario A: Independent agent chat**
- User creates a Developer agent.
- Assigns a coding skill and a restricted set of tools.
- Opens its chat.
- Requests a code change.
- Agent uses the configured engine.
- User sees progress and result.
- Conversation is restored after app restart.

**Scenario B: ZEZO delegates parallel work**
- User asks ZEZO to build a project with separable tasks.
- ZEZO creates a task plan.
- Two independent agents run concurrently.
- A dependent QA task waits.
- ZEZO collects results, handles conflicts, validates outputs, and reports completion.

**Scenario C: Permission enforcement**
- Agent tries to call an unassigned tool.
- Backend denies it regardless of whether the tool is hidden in the UI.
- The denial is recorded and visible in the run log.

**Scenario D: External engine unavailable**
- OpenCode/Kilo process fails or disconnects.
- ZEZO marks the run accurately, preserves diagnostics, and offers a safe retry/fallback.
- It does not report success based only on process launch.

---

## 17. Phased Migration Roadmap

Migration should be incremental. Each phase must leave the app in a testable state.

### Phase 0: Baseline and dependency inventory

- Freeze current behavior and record known working flows.
- Map imports/callers for agent, action, skill, memory, and engine modules.
- Identify dead code, duplicate UI components, and config ownership.
- Add/confirm tests for current critical flows.
- Remove no runtime code in this phase.

**Exit criteria:** A verified dependency map and baseline tests.

### Phase 1: Canonical domain models and persistence

- Define Agent, Conversation, Session, Run, Task, Tool, Skill, Workspace, and Approval models.
- Add schema validation and database migrations.
- Migrate agent profile access behind Agent Repository.
- Keep `config/agents.json` as import/bootstrap source during transition if necessary.

**Exit criteria:** Profiles and sessions have stable IDs and validated schemas.

### Phase 2: Unified Agent Runtime

- Create the runtime lifecycle and context builder.
- Route primary ZEZO chat through the runtime where applicable.
- Route Agent Office chat through the same runtime.
- Persist backend conversations and run events.
- Remove direct-chat shortcuts only after feature parity and tests.

**Exit criteria:** ZEZO and custom-agent chat share a consistent run/event/session contract.

### Phase 3: Tool Registry and permission enforcement

- Create canonical Tool Registry and Tool Executor.
- Wrap existing actions as tool definitions.
- Centralize schema validation, policy checks, approvals, timeouts, cancellation, and logs.
- Audit direct registry calls and close bypasses.

**Exit criteria:** Every tool side effect passes through the same enforcement point.

### Phase 4: Skill system consolidation

- Standardize skill metadata.
- Consolidate discovery, scanning, resolution, and injection.
- Enforce tool permission intersection for skills.
- Migrate procedural SkillRunner workflows.
- Deprecate redundant skill execution paths only after tests.

**Exit criteria:** Skills behave consistently for ZEZO and all custom agents.

### Phase 5: Engine adapter layer

- Define normalized engine adapter interface and events.
- Wrap existing OpenCode, Kilo, and Antigravity runners as CLI adapters.
- Verify ACP support/version requirements.
- Add ACP adapter for supported runner(s).
- Add session lifecycle, permission bridge, timeout, cancellation, health checks, and recovery.

**Exit criteria:** Agent Runtime can use native, CLI, or ACP engines through one contract.

### Phase 6: Multi-agent task orchestration

- Persist task graph and dependencies.
- Add bounded concurrency, scheduling, cancellation, retries, and result aggregation.
- Make internal delegation orchestrator-mediated.
- Add worktree/merge coordination.
- Add loop/depth/resource enforcement.

**Exit criteria:** Multiple agents can run independent tasks concurrently and safely return results.

### Phase 7: Memory consolidation

- Map current memory data and all callers.
- Define scope policies and canonical repositories.
- Migrate conversation history, agent memory, shared project memory, and long-term facts.
- Preserve vault import/export if useful.
- Remove redundant stores only after migration validation.

**Exit criteria:** Every memory category has one documented owner and access policy.

### Phase 8: Frontend integration and cleanup

- Update Agent Builder and Agent Chat.
- Connect UI to canonical APIs/events.
- Remove duplicate components only after usage/import analysis.
- Add task center, permission prompts, engine status, and memory controls.
- Reconcile architecture documentation.

**Exit criteria:** Frontend reflects backend truth and all core acceptance scenarios pass.

### Phase 9: Release hardening

- Run integration and end-to-end tests.
- Test app restart, cancellation, process crashes, network failures, and database migrations.
- Review secrets, certificates, permissions, and logs.
- Package only runtime assets.
- Create rollback and data migration procedures.

**Exit criteria:** Release checklist signed off; no critical permission/session/task integrity gaps remain.

---

## 18. Decisions to Confirm Before Implementation

The following are product decisions, not assumptions to silently hard-code:

1. **Agent memory isolation:** Recommended default is private agent memory with explicit shared project/user memory. Confirm whether any agents should share memory by default.
2. **Agent engine default:** Should a new agent default to ZEZO's native runtime, or require the user to select an engine?
3. **Delegation permissions:** May ZEZO delegate to any enabled agent, or only agents explicitly marked as delegatable?
4. **Agent-to-agent chat:** Recommended design is structured task handoff and result delivery, not unrestricted private chat. Confirm whether direct agent messaging is also a desired feature.
5. **Parallel coding:** Should code-writing agents always receive separate Git worktrees, or can a user explicitly allow shared workspace execution?
6. **Approvals:** Which actions may run autonomously, and which require confirmation?
7. **Engine fallback:** If the selected external engine is unavailable, should ZEZO fail clearly or offer a user-approved fallback?
8. **Agent profile portability:** Should users be able to export/import agent profiles and skill bundles?

Recommended defaults are stated above to make the proposal actionable, but these decisions should be confirmed before implementation.

---

## 19. Final Recommendation

Do not start by adding more agent features to the current structure. First establish the shared contracts that all features must use.

The highest-value order is:

1. Canonical Agent Profile and Session/Run/Task models.
2. Unified Agent Runtime for ZEZO and custom-agent chat.
3. Central Tool Registry and server-side permissions.
4. One Skill Registry and resolver.
5. Engine Adapter layer with distinct ACP and CLI implementations.
6. Persistent, orchestrator-managed multi-agent tasks.
7. Memory scope and persistence consolidation.
8. Frontend integration and safe removal of superseded code.

The desired result is:

```text
ZEZO
  = Primary Assistant
  + User-Created Agents
  + Independent Agent Chats
  + Skills and Governed Tools
  + Multi-Agent Task Orchestration
  + Native and External Execution Engines
  + Persistent Sessions and Memory
```

**The success criterion is not the number of modules or agents.** It is that every agent can be configured predictably, every chat uses the same reliable runtime, every tool call is authorized, delegated work is observable and recoverable, and one change in a subsystem does not unexpectedly break another.

---

## Appendix A: Source Paths Reviewed

The proposal is grounded primarily in these uploaded source paths:

- `main.py`
- `core/ui_server.py`
- `core/agents_manager.py`
- `core/agents/registry.py`
- `core/agents/dispatcher.py`
- `core/agents/orchestrator.py`
- `core/task_manager.py`
- `core/action_loader.py`
- `core/opencode_runner.py`
- `core/kilo_runner.py`
- `core/antigravity_runner.py`
- `core/code_engines.py`
- `core/mcp_runtime.py`
- `core/governance.py`
- `core/skill_loader.py`
- `core/skill_runner.py`
- `core/skill_scanner.py`
- `memory/memory_manager.py`
- `memory/sqlite_memory.py`
- `memory/memory_condenser.py`
- `memory/memory_state.py`
- `memory/vault_engine.py`
- `actions/agents_control.py`
- `actions/agent_reach.py`
- `actions/opencode_agent.py`
- `actions/kilo_agent.py`
- `actions/run_skill.py`
- `config/agents.json`
- `config/tools_state.json`
- `config/skills_state.json`
- `frontend/src/components/office/`
- `frontend/src/components/agents/`
- `frontend/src/components/settings/`
- `frontend/src/lib/api.ts`
- `frontend/src/hooks/useZezoSocket.ts`
- `frontend/src/types/zezo.ts`

## Appendix B: Non-goals for this proposal

- No source-code changes.
- No file deletion.
- No database migration.
- No ACP implementation.
- No UI redesign implementation.
- No assumption that every QwenPaw feature should be copied.
- No claim that a static source review proves runtime correctness.

**Document end.**
