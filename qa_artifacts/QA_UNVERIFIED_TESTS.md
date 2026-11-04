# ⚠️ ZEZO QA AUDIT: UNVERIFIED TESTS & SYSTEMIC LIMITATIONS

> **Target Application:** ZEZO Autonomous Desktop AI Assistant  
> **Auditor:** Antigravity Autonomous QA Audit Team  
> **Date:** November 4, 2026  
> **Scope:** Audit of `qa_artifacts/QA_REPORT.md` Claims & Verification Gaps  

---

## 1. Executive Summary of Unverified Areas

While the underlying Python backend runtime, ToolExecutor security choke points, ProcessSupervisor Win32 Job Objects, and SQLite WAL database layer demonstrated robust execution across 225 passing tests, the QA audit has revealed **one critical end-to-end integration flow that is NOT VERIFIED** and **several tests whose execution types were mislabelled or simulated**.

In accordance with strict QA principles, **NOT TESTED or UNVERIFIED must never be converted into PASS**.

| Scope / Focus Area | Claimed Status | Audited Status | Root Cause / Verification Limitation |
|---|---|---|---|
| **Frontend Conversation Continuity (Multi-Turn Chat)** | PASS | **NOT VERIFIED** | Frontend `AgentDirectChatView.tsx` drops conversation IDs and ignores SSE `done` event returned IDs, preventing backend context retention in live UI chat. |
| **Conversational Stream Cancellation (K01–K06)** | LIVE APPLICATION TEST | **MOCKED / SIMULATED TEST** | Tested against in-memory `MockUI` and a synthetic async generator `mock_llm_stream()`; never interrupted a live remote Gemini streaming socket. |
| **Live Token-by-Token Streaming (J02, J05)** | PASS | **CONFIRMED FAIL** | Architectural defect in `runtime.py` line 459 where `list(gemini.stream_text())` buffers all chunks into a list before yielding with `sleep(0.01)`. TTFT was 11.433s (97.5% of total time). |

---

## 2. Deep Dive: Frontend Conversation Continuity Disconnect

### 2.1 The Dental SaaS Scenario (Suite E - Alex / Dental SaaS)
The QA specification mandated verifying conversation memory across multiple turns:
- **Turn 1:** *"My name is Alex. I am building a SaaS product for dentists. Remember this project context. Tell me what you understood."*
- **Turn 2:** *"What type of product am I building? Who is my target audience? What project context did I give you?"*

### 2.2 Verification Path Audit (Scenarios A, B, and C)
- **Scenario A (Direct AgentRuntime in Python):** **VERIFIED PASS**.  
  `tests/run_suite_e_tests.py` created an isolated in-memory runtime instance, generated an explicit `conv_id = runtime.get_or_create_conversation()`, and passed the same ID into both turns. The memory store accurately recalled the project context.
- **Scenario B (Backend HTTP/SSE API with Explicit `conversation_id`):** **VERIFIED PASS**.  
  When an external caller explicitly passes `{"conversation_id": "conv_12345"}`, `ui_server.py` retains context.
- **Scenario C (Actual `AgentDirectChatView` UI Integration):** **NOT VERIFIED / BROKEN IN CODE**.  
  The actual frontend chat component **never maintains continuity across consecutive user messages**.

### 2.3 Evidence of Code-Level Defect in `frontend/src/components/office/AgentDirectChatView.tsx`

1. **Thread ID Initialization (lines 88–90, 107):**
   ```tsx
   const [activeThreadId, setActiveThreadId] = useState<string>(
     () => threads[0]?.id || `thread-${agent.id}-${Date.now()}`
   );
   ```
   When a user opens chat or starts a new thread, the client generates an ID prefixed with `thread-` (e.g. `thread-MICHAEL-1730732400000`).

2. **Conversation ID Gating (line 260):**
   ```tsx
   conversationId={activeThreadId.startsWith('conv_') ? activeThreadId : undefined}
   ```
   Because `activeThreadId` starts with `thread-` and not `conv_`, the frontend explicitly passes `conversationId: undefined` to the backend API!

3. **Backend SSE Done Event (`core/ui_server.py` lines 1576–1580):**
   The backend creates a brand-new conversation (prefixed with `conv_`) and yields an SSE `done` event containing:
   ```json
   event: done
   data: {"reply": "...", "conversation_id": "conv_766af0238e"}
   ```

4. **Frontend Drops Returned ID (lines 305–341, 184–199):**
   When `AgentDirectChatView.tsx` receives the `done` event, it reads `chunk.reply` but **completely ignores `chunk.conversation_id`**.
   In `handleConversationComplete` (lines 184–199):
   ```tsx
   const handleConversationComplete = (reply: string) => {
     // Preserves activeThreadId as `thread-...`
     // Never updates activeThreadId or thread record with chunk.conversation_id!
   };
   ```

5. **Failure on Message 2:**
   When the user types their second question (*"What type of product am I building?"*), `activeThreadId` is still `thread-...`.  
   `activeThreadId.startsWith('conv_')` evaluates to `false` again!  
   The frontend sends `conversationId: undefined` a second time, forcing the backend to spin up a **second, completely isolated conversation**. The agent has zero knowledge of Alex or the Dental SaaS.

**Audit Verdict:** Frontend conversation continuity in `AgentDirectChatView` is **NOT VERIFIED** and cannot function without updating `activeThreadId` upon receiving the SSE `done` payload.

---

## 3. Mislabelled Execution Types (Suite K: Cancellation)

In `qa_artifacts/QA_TEST_RESULTS.json`, tests K01 through K06 were claimed as `LIVE APPLICATION TEST`.

### 3.1 Audited Execution Reality
Inspection of `qa_artifacts/run_suite_k_tests.py` demonstrates:
- Tests K01–K06 executed against `MockUI` and a local in-memory generator:
  ```python
  async def mock_llm_stream():
      for i in range(1, 100):
          yield f"chunk_{i} "
          await asyncio.sleep(0.05)
  ```
- These tests verified Python `asyncio.CancelledError` cooperative task cancellation inside a test loop.
- **They did NOT connect to the live Google Gemini WebSocket or the live `/api/agents/chat/stream` SSE endpoint.**
- Therefore, labelling them as `LIVE APPLICATION TEST` was inaccurate. They have been officially re-categorized in `QA_VALIDATED_RESULTS.json` as **`MOCKED / SIMULATED TEST`**.

### 3.2 Contrasting with K07–K11 (Live Win32 Process Containment)
Conversely, tests K07–K11 executed against real live Windows processes:
- Spawns a real Python worker script `deep_tree_worker.py` via `ProcessSupervisor.spawn()`.
- Windows Job Object assigns `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- Process tree with root PID, child PID, and grandchild PID was confirmed alive via `psutil`.
- `terminate_tree()` reaped all 3 processes cleanly in 0.0002 seconds with 0 orphaned processes remaining.
- These are legitimately categorized as **`LIVE PROCESS TEST`**.

---

## 4. Confirmed Streaming Failures (Suite J)

The 2 failures reported in the original QA report are verified as genuine, reproducible architectural defects:

1. **FAIL-J05: Fake Timer Streaming (`core/agents/runtime.py` lines 459–467)**
   - The method `step_stream_async` buffers all stream chunks into a list using `list(gemini.stream_text(...))` inside a thread pool executor.
   - It then iterates through the list and yields chunks with `await asyncio.sleep(0.01)`.
   - This creates an illusion of streaming while consuming full generation latency upfront.
2. **FAIL-J02: High Time-To-First-Token (TTFT)**
   - First token delivered at **11.433 seconds** out of an 11.724-second total duration.
   - 97.5% of total request elapsed before any text was rendered to the user.

---

## 5. Storage Isolation & Cleanup Gaps

While core user data remained uncorrupted, the audit identified that test runners executed directly against production paths rather than sandboxed fixtures:

1. **Test Agents Leaked to `config/agents.json`:**
   - `TEST_RESTRICTED_ATTE`
   - `SECURITY_AUDIT_L0`
   - `SNEAKYL0AGENT`
   - Left in storage because `run_security_depth_suite.py` saved profiles to disk but did not execute `delete_agent()` in its teardown.
2. **Test Conversation Threads Leaked to `memory/zezo_brain.db`:**
   - 15+ test threads (`conv_1de754160a93`, `conv_agent1_34ebbdc9`, etc.) and over 100 benchmark messages remain in SQLite tables.
   - User database integrity check passed (`PRAGMA integrity_check` = `ok`), but production database contains test artifacts.

---

## 6. Audit Summary Table

| Test ID | Name | Suite | Claimed Label | Corrected Label | Status | Audit Finding |
|---|---|---|---|---|---|---|
| **E00** | Dental SaaS Context Retention | Suite E | LIVE APPLICATION TEST | LIVE BACKEND TEST (SCENARIO A) | **PARTIALLY VERIFIED** | Backend runtime context passed; UI multi-turn integration NOT VERIFIED. |
| **K01** | Start Long Request | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | Simulated async task; no live Gemini socket tested. |
| **K02** | Cancel Active Generation | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | Simulated cancellation flag; no live Gemini socket tested. |
| **K03** | Verify UI Stops | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | MockUI state verification only. |
| **K04** | Backend Processing Stops | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | In-memory generator abort only. |
| **K05** | Cancellation Recorded | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | Python task state check only. |
| **K06** | No Further Chunks Arrive | Suite K | LIVE APPLICATION TEST | MOCKED / SIMULATED TEST | PASS (SIMULATED) | Mock collector check only. |
| **J02** | First Chunk Timing | Suite J | FAIL | FAIL | **CONFIRMED FAIL** | TTFT 11.433s / 97.5% of total duration. |
| **J05** | No Fake Timer Streaming | Suite J | FAIL | FAIL | **CONFIRMED FAIL** | `list(gemini.stream_text())` + `sleep(0.01)` buffering confirmed. |

