# ZEZO
## Revised Architecture Proposal v2

**Project:** ZEZO Autonomous Desktop AI Assistant  
**Platform:** Windows (Primary), macOS, Linux (Future)  
**Document Type:** Architecture Redesign Proposal  
**Status:** Proposed, Pending Approval  
**Version:** 2.0

---

# 1. Executive Summary

ZEZO ka objective ek autonomous desktop AI assistant develop karna hai jo independently tasks perform kar sake, external coding agents use kar sake, custom agents create aur manage kar sake, aur multiple agents ke through complex tasks execute kar sake.

Proposed architecture ka primary goal existing system ko unnecessarily rewrite karna nahi, balkay uski fragmented responsibilities ko gradually simplify aur unify karna hai.

Claude ke architecture review ke baad v2 mein kuch important changes kiye gaye hain:

- Initial architecture ko minimal core tak limit karna.
- Ek unified Agent Runtime establish karna.
- Custom agents ko independent identities aur conversations dena.
- ZEZO ke liye explicit self-execution versus delegation policy define karna.
- Multi-agent orchestration ko incremental phases mein introduce karna.
- ACP compatibility ko implementation se pehle experimentally verify karna.
- Long-running tasks ke liye context management aur checkpoints introduce karna.
- External coding agents ke liye explicit security boundaries define karna.
- SQLite concurrency aur Windows process management address karna.
- Existing functionality ke liye migration aur rollback strategy define karna.

**Core principle:** Pehle ek reliable working agent system build karo. Uske baad usko multi-agent system mein evolve karo.

# 2. Product Vision

ZEZO should operate as the primary AI assistant.

It should have two major capabilities:

### A. ZEZO Core Assistant

ZEZO should independently:

- Understand user requests.
- Plan tasks.
- Use its own tools.
- Execute actions.
- Maintain context and memory.
- Monitor execution.
- Report results.
- Decide when external agents are necessary.

### B. Agent Ecosystem

ZEZO should support:

- Creating custom agents.
- Assigning individual instructions.
- Assigning specific tools and skills.
- Configuring models and execution engines.
- Independent agent conversations.
- Independent agent sessions.
- Delegating tasks to agents.
- Running multiple agents concurrently.
- Collecting and combining agent results.

External engines such as OpenCode and Kilo should be treated as integrations, not as the foundation of ZEZO's internal agent architecture.

# 3. Architecture Principles

The redesigned system must follow these principles:

1. Modular monolith initially, not premature microservices.
2. One authoritative Agent Runtime.
3. One centralized Tool Execution boundary.
4. Persistent conversations and task state.
5. Explicit permissions and execution policies.
6. Clear separation between internal agents and external engines.
7. Backward-compatible migration.
8. Incremental implementation.
9. Observable and recoverable execution.
10. No duplicate execution paths after migration.

**Important:** The architecture should not introduce every proposed module, database table, or abstraction in the first implementation.

Build only what the current vertical slice requires.

# 4. Target Architecture

The proposed architecture has these logical components:

## 4.1 Application Layer

Responsibilities:

- Desktop application lifecycle.
- UI and API communication.
- Application settings.
- User interaction.
- Notifications.

## 4.2 Agent Layer

Responsibilities:

- Agent profiles.
- Agent configuration.
- Agent instructions.
- Agent capabilities.
- Agent conversations.
- Agent session management.

## 4.3 Runtime Layer

Responsibilities:

- Receive agent requests.
- Construct execution context.
- Select model/provider.
- Load assigned tools and skills.
- Execute agent turns.
- Stream responses.
- Manage cancellation and errors.

There should be one authoritative internal execution path.

## 4.4 Tool Execution Layer

Responsibilities:

- Tool registration.
- Tool discovery.
- Schema validation.
- Permission checks.
- Approval handling.
- Execution.
- Results and errors.
- Audit events.

No internal agent should bypass the centralized execution boundary.

## 4.5 Engine Integration Layer

Responsibilities:

- OpenCode integration.
- Kilo integration.
- Other external coding agents.
- ACP clients where supported.
- CLI-based integrations where necessary.
- External process lifecycle management.

## 4.6 Orchestration Layer

Responsibilities:

- Task decomposition.
- Agent selection.
- Task assignment.
- Dependency management.
- Parallel execution.
- Result aggregation.
- Failure recovery.

This layer should be introduced after the basic agent vertical slice works.

## 4.7 Persistence Layer

Responsibilities:

- Agent profiles.
- Conversations.
- Messages.
- Tasks.
- Execution state.
- Memory.
- Configuration.

SQLite remains the initial persistence solution.

# 5. Minimal Core Architecture

The initial implementation should focus on five essential concepts:

1. AgentProfile
2. AgentRuntime
3. ToolExecutor
4. ConversationStore
5. TaskManager

These are the initial architectural foundations.

Additional modules should be introduced only when their responsibilities become necessary.

Avoid initially creating separate subsystems for every small feature.

For example:

- Task artifacts can initially use structured JSON storage.
- Tool approvals can initially use execution events and structured records.
- Agent capabilities can initially be represented through profile configuration.
- Observability can initially live inside the existing logging and event infrastructure.
- Workspace management can initially remain part of the execution boundary.

These decisions can evolve when actual complexity justifies separate modules or tables.

# 6. Agent Profile System

Every agent should have an independent profile.

Proposed profile fields:

| Field | Responsibility |
|---|---|
| id | Unique identifier |
| name | Agent name |
| description | Agent purpose |
| system_instructions | Agent behavior |
| model | Assigned model |
| provider | Model provider |
| engine | Internal or external engine |
| skills | Assigned skills |
| tools | Assigned tools |
| permissions | Execution permissions |
| memory_policy | Memory access rules |
| resource_budget | Token and execution limits |
| enabled | Agent availability |

Supported operations:

- Create agent.
- Edit agent.
- Duplicate agent.
- Enable or disable agent.
- Delete agent.
- Configure model.
- Assign tools.
- Assign skills.
- Configure permissions.

An agent should be configurable without requiring changes to the core runtime.

# 7. Independent Agent Conversations

Every agent should have its own conversation history.

The backend must be the authoritative source of conversation state.

The frontend must not independently own conversation history through localStorage.

Required behavior:

- Each conversation belongs to an agent.
- Conversations persist in SQLite.
- Messages persist independently.
- Agent identity remains associated with conversations.
- Conversations can be restored after application restart.
- Multiple conversations can exist for one agent.
- Conversation context can be summarized when necessary.

Existing localStorage-based chat data must have an explicit migration path.

Migration should preserve existing conversations where possible.

# 8. ZEZO Self-Execution and Delegation Policy

This is an important addition in v2.

ZEZO should not delegate every task automatically.

It should decide whether to execute a task itself or delegate it.

### Execute internally when:

- The task is simple.
- The task requires ZEZO's own tools.
- No specialized agent is necessary.
- Delegation would introduce unnecessary overhead.
- The task is small enough for the current context and resource budget.

### Delegate when:

- The task requires specialized expertise.
- A coding agent is better suited.
- Multiple independent subtasks exist.
- Parallel execution offers a meaningful benefit.
- A specialized agent has the required capabilities.

### Delegation decision process

1. Understand the request.
2. Identify task requirements.
3. Check available agents and capabilities.
4. Estimate complexity and resource cost.
5. Decide between internal execution and delegation.
6. Create a structured task.
7. Execute or delegate.
8. Evaluate results.
9. Report the final outcome.

The planner may use model reasoning, but the runtime must enforce hard limits such as permissions, budgets, maximum delegation depth, and concurrency.

# 9. Multi-Agent Orchestration

Multi-agent orchestration should be introduced after the basic agent system has been validated.

Required capabilities:

- Task decomposition.
- Agent selection.
- Task assignment.
- Sequential execution.
- Parallel execution.
- Task dependencies.
- Execution status.
- Result aggregation.
- Cancellation.
- Retry policies.
- Failure handling.

### Agent communication

Agents should communicate through structured orchestration messages by default.

An agent should not freely access another agent's private conversation.

Communication should happen through:

- Task assignment.
- Task updates.
- Structured handoffs.
- Results.
- Shared project artifacts where authorized.

Direct agent-to-agent messaging can be introduced later if a real use case requires it.

### Loop prevention

The orchestration system must enforce:

- Maximum delegation depth.
- Maximum task count.
- Maximum execution time.
- Maximum retry count.
- Cycle detection.
- Idempotency.
- Resource budgets.

These must be runtime-enforced, not only described in system prompts.

# 10. Long-Running Task Context Strategy

This is a new required architectural component.

Long-running tasks must not depend on keeping the entire conversation inside the model context window.

The system should support:

### A. Context Budget

Every agent execution should have a configurable token budget.

### B. Rolling Summaries

When context grows, older messages should be summarized while preserving important decisions and information.

### C. Execution Checkpoints

Long-running tasks should periodically save:

- Current task objective.
- Completed steps.
- Pending steps.
- Important findings.
- Files modified.
- Errors.
- Next recommended action.

### D. Recovery

If the application restarts:

- Persisted tasks should be restored.
- Interrupted tasks should be marked appropriately.
- External processes that cannot resume should be marked interrupted.
- Agents should be able to continue from their last valid checkpoint when supported.

Conversation history and execution state must remain separate concepts.

# 11. OpenCode and Kilo Integration

OpenCode and Kilo should be integrated through independent engine adapters.

Proposed logical interfaces:

- EngineAdapter
- EngineSession
- EngineEvent
- EngineResult
- EngineCapabilities

### Integration strategy

Support two possible execution mechanisms:

1. ACP integration.
2. CLI/subprocess integration.

ACP should only be enabled when the actual engine version supports the required protocol lifecycle.

Do not assume that both OpenCode and Kilo provide equivalent ACP functionality.

### Required ACP verification

Before implementing the ACP architecture, conduct a time-boxed technical spike.

Test:

- initialize
- session/new
- session/prompt
- session/update
- Streaming events.
- Cancellation.
- Session lifecycle.
- Permission requests.
- Process termination.

Document the exact tested application version and results.

### Generic ACP Client

Prefer a reusable generic ACP client if protocol behavior is sufficiently compatible.

Individual engine adapters should handle engine-specific configuration and differences.

Do not create separate ACP implementations unnecessarily.

CLI integration should remain available when ACP is unavailable or unsuitable.

# 12. External Engine Security

External coding agents introduce a different security boundary.

ZEZO's internal ToolExecutor cannot automatically control every tool operation performed inside an external engine's own process.

Therefore, external engines require their own execution restrictions.

### Required controls

- Dedicated workspace.
- Restricted filesystem access.
- Restricted environment variables.
- No unnecessary access to private configuration.
- Explicit permission policies.
- Process timeouts.
- Resource limits where supported.
- Controlled network access.
- Process cleanup.
- Execution audit logs.

External agents should default to a restricted execution profile.

A risk label such as R0, R1, or R2 is not an OS-level sandbox.

Actual isolation must use appropriate operating-system mechanisms.

# 13. Tool and Skill Architecture

Tools and skills must have separate responsibilities.

### Skills

Skills provide instructions and procedural knowledge.

Examples:

- Research.
- Coding conventions.
- Project analysis.
- Browser workflows.
- Documentation.

### Tools

Tools perform actual operations.

Examples:

- File operations.
- Terminal execution.
- Browser automation.
- Database queries.
- Application controls.

### Required rules

- Agents receive explicitly assigned skills.
- Agents receive explicitly assigned tools.
- Tool execution permissions are checked server-side.
- Tool schemas are validated.
- Risky operations require approval.
- Tool execution is logged.
- Skills cannot bypass execution permissions.

Automatic skill suggestions can be introduced later.

Initially, explicit assignment should remain the source of truth.

# 14. Permissions and Approvals

The permission model should cover both internal and external execution.

### Internal tools

Centralized ToolExecutor must enforce:

- Tool allowlists.
- Risk levels.
- Resource scopes.
- Approval requirements.
- Execution restrictions.

### External engines

Permissions must be enforced through:

- Workspace restrictions.
- Environment restrictions.
- ACP permission capabilities where available.
- Operating-system isolation.

### User-away approvals

If an approval is required while the user is away:

- The operation remains pending.
- ZEZO sends a notification where supported.
- No restricted operation proceeds without authorization.
- The user can approve or reject later.

Approval state must persist across application restarts.

# 15. SQLite and Persistence Reliability

SQLite remains appropriate for the initial desktop application.

However, concurrent agent execution requires careful database access.

Required configuration:

- WAL mode.
- Appropriate busy timeout.
- Transaction boundaries.
- A single-writer queue for writes.
- Safe connection lifecycle.
- Database migration versioning.

The single-writer queue should serialize database writes from concurrent agents.

Avoid introducing unnecessary database infrastructure before measuring actual requirements.

# 16. Windows Process Lifecycle

Windows is ZEZO's primary platform, so process management needs explicit attention.

Required capabilities:

- Track spawned processes.
- Track process identifiers.
- Handle process termination.
- Clean up child processes.
- Prevent orphan processes.
- Handle application shutdown.
- Recover interrupted execution state.
- Apply timeouts.

Process-tree cleanup must be tested on Windows, not assumed to behave identically across platforms.

Use appropriate operating-system process management mechanisms.

# 17. Cost, Token and Rate Budgets

Each agent and execution should have resource limits.

Proposed budget categories:

- Maximum tokens per execution.
- Maximum execution duration.
- Maximum tool calls.
- Maximum delegation depth.
- Maximum concurrent tasks.
- Provider rate limits.
- Optional cost limits.

ZEZO should track resource consumption where provider usage data is available.

Provider fallback should be explicit and configurable.

A fallback must not silently change the agent's intended model or permissions.

# 18. Voice Integration

Voice should be treated as an interaction layer, not a separate agent runtime.

Voice interactions should use the same AgentRuntime and orchestration system as text conversations.

Required behavior:

- User can issue voice commands.
- ZEZO can narrate task progress.
- ZEZO can announce delegation.
- ZEZO can report completed tasks.
- ZEZO can request approvals.
- User can interrupt or cancel execution.

Wake-word support and continuous listening can be developed independently.

Voice should not introduce a duplicate execution path.

# 19. Logging and Observability

Every important execution should produce structured events.

Track:

- Agent ID.
- Conversation ID.
- Task ID.
- Execution ID.
- Tool calls.
- Engine events.
- Errors.
- Retries.
- Approvals.
- Resource usage.
- Execution duration.

### Log security

Logs must not expose:

- API keys.
- Access tokens.
- Private keys.
- Passwords.
- Sensitive environment variables.
- Unnecessary personal data.

Define log retention and cleanup policies.

Observability should begin with the existing logging infrastructure and become a separate subsystem only when justified.

# 20. Migration and Compatibility Strategy

The existing ZEZO system must not be replaced in one operation.

Migration must preserve working functionality.

### Required migration rules

1. Audit current execution paths.
2. Establish baseline tests.
3. Introduce the new runtime.
4. Add compatibility wrappers where necessary.
5. Migrate existing agent functionality.
6. Migrate chat history from localStorage.
7. Route all execution through the new runtime.
8. Verify behavior.
9. Remove old execution paths.
10. Remove compatibility wrappers once no longer needed.

Compatibility wrappers must have an explicit removal condition and deadline.

They must not become permanent alternative execution paths.

### Source-of-truth rule

Backend persistence must remain authoritative.

Frontend state is a representation of backend state, not an independent source of truth.

# 21. Proposed Implementation Roadmap

The roadmap is intentionally smaller and more incremental than the original proposal.

## Phase 0: Audit and Baseline

Objectives:

- Inspect existing code.
- Identify current execution paths.
- Identify dependencies.
- Establish regression tests.
- Review sensitive configuration files.
- Document existing behavior.

Exit criteria:

- Existing functionality has a baseline.
- Critical execution paths are documented.
- Sensitive files are reviewed.
- No source changes are made without a migration plan.

## Phase 1: Minimal Agent Foundation

Implement:

- AgentProfile.
- AgentRuntime.
- ToolExecutor.
- ConversationStore.
- Basic TaskManager.

Build one complete vertical slice:

1. Create a custom agent.
2. Configure its instructions.
3. Start a conversation.
4. Execute an assigned tool.
5. Persist messages.
6. Restart ZEZO.
7. Restore the conversation.

Exit criteria:

The complete workflow works reliably after application restart.

## Phase 2: Agent Capabilities and Permissions

Implement:

- Tool assignments.
- Skill assignments.
- Agent permissions.
- Approval flow.
- Resource limits.
- Execution audit.

Exit criteria:

Agents cannot execute unauthorized tools through internal runtime paths.

## Phase 3: External Engine Integration

Start with one verified integration.

Implement:

- Engine adapter.
- Session lifecycle.
- Event streaming.
- Cancellation.
- Process cleanup.
- Workspace restrictions.

Run the ACP technical spike before deciding whether ACP or CLI should be the primary integration mechanism.

Exit criteria:

One external coding agent can receive tasks, execute them, stream results, and terminate safely.

## Phase 4: Multi-Agent Orchestration

Implement:

- Task decomposition.
- Agent selection.
- Task dependencies.
- Parallel execution.
- Sequential execution.
- Result aggregation.
- Retry and failure handling.
- Delegation limits.

Exit criteria:

ZEZO can delegate multiple independent tasks and reliably collect their results.

## Phase 5: Context and Memory

Implement:

- Rolling summaries.
- Token budgets.
- Execution checkpoints.
- Recovery.
- Shared memory scopes.
- Memory migration.

Exit criteria:

Long-running tasks can preserve context and recover from interruptions.

## Phase 6: Frontend Integration

Implement:

- Agent management UI.
- Independent agent chats.
- Task monitoring.
- Delegation visibility.
- Approval notifications.
- Execution history.
- Voice integration.

Exit criteria:

The frontend uses backend-persisted state consistently.

## Phase 7: Hardening and Cleanup

Implement:

- Windows process lifecycle tests.
- SQLite concurrency tests.
- Security tests.
- Log redaction.
- Retention policies.
- Performance testing.
- Compatibility wrapper removal.
- Documentation updates.

Exit criteria:

No obsolete execution paths remain, and regression tests pass.

# 22. Mandatory Phase Exit Rules

Every phase must satisfy these conditions before the next phase begins:

1. Required functionality works.
2. Regression tests pass.
3. New execution paths are documented.
4. Permissions are verified.
5. Error handling is tested.
6. Persistence is verified.
7. No unauthorized direct tool execution path remains.
8. Obsolete paths are removed when migration is complete.
9. Rollback instructions exist.
10. Documentation reflects the actual implementation.

A phase is not complete merely because its code has been written.

# 23. Open Architecture Decisions

These decisions must be finalized before their respective implementation phases.

| Decision | Required clarification |
|---|---|
| Agent communication | Structured handoff only or optional direct messaging? |
| Delegation | Which tasks should ZEZO delegate by default? |
| ACP | Which exact engine versions support the required lifecycle? |
| Kilo | ACP, CLI, or another supported integration? |
| Memory | Which information can agents share? |
| Skill installation | What is the trust and import model? |
| Permissions | What filesystem and network restrictions are required? |
| Fallback | When can providers or engines be switched? |
| Voice | Which voice capabilities are required initially? |
| Approvals | Which operations require explicit user confirmation? |

Do not invent answers to unresolved decisions during implementation.

# 24. Security Priority

Before major architectural changes:

- Inspect private keys and certificates.
- Identify exposed credentials.
- Review API key storage.
- Verify environment-variable handling.
- Restrict external process environments.
- Establish workspace boundaries.

If any live private key has been exposed in an archive or repository, assess and rotate it immediately.

Security remediation should not wait for the architecture migration.

# 25. Final Architecture Recommendation

The recommended direction is a modular desktop application with:

- One primary ZEZO assistant.
- One unified internal AgentRuntime.
- Configurable custom agents.
- Independent persistent conversations.
- One centralized internal ToolExecutor.
- Separate external engine adapters.
- Structured multi-agent orchestration.
- Explicit memory and context management.
- Persistent tasks and execution events.
- Controlled permissions and resource budgets.

The architecture should evolve incrementally.

Do not build the entire proposed ecosystem at once.

First prove that one custom agent can be created, communicate, use tools, persist its state, and recover after restart.

Then introduce external engines.

Finally, introduce multi-agent orchestration.

**Final principle: ZEZO should become more capable through a reliable architecture, not more complicated through additional abstractions.**