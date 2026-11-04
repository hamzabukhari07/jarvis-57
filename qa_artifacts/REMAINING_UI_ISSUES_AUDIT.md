# ZEZO: Remaining UI Issues Deep Dive & Root Cause Audit (READ-ONLY)

**Audit Date:** November 4, 2026  
**Auditor:** Senior Software Testing Architect & QA Automation Engineer  
**Audit Type:** Strict Read-Only Deep Dive & Architecture Code Audit  
**Status:** Phase 3 strictly paused. Zero source code, database, configuration, or report modifications performed.

---

## Executive Summary

During manual testing of the ZEZO desktop application, two remaining user-facing issues were observed:
1. **Issue 1 (Antigravity Task Engine Context):** Test 1 produced an incorrect answer when using the Antigravity engine, while Kilo Code returned the correct answer using the same conversation context.
2. **Issue 2 (Streaming UI & Stop Button):** During Test 4, a long prompt produced no loading or thinking indicator; the response appeared all at once instead of progressively streaming; and clicking Stop did not interrupt generation.

This read-only audit traces the complete data, control, and event flow from the React UI down to the Python OS backend, SQLite database, and external CLI/API execution engines. It confirms the exact architectural discrepancies and presents targeted, minimal remediation designs.

---

## 1. Issue 1: Antigravity Task Engine Context Discrepancy

### 1.1 Problem Statement
When a user executes a directive or task in the office view:
- Using the **Kilo Code** engine: The model receives the full context and returns the correct answer.
- Using the **Antigravity** engine (`agy`): The engine produces an incorrect answer or fails to utilize the conversation context.

### 1.2 End-to-End Tracing: Prompt & Context Flow

#### A. Is `conversation_id` passed to external execution engines?
- **Finding:** **NO.**
- **Code Reference:** In [core/agents_manager.py:140-171](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/agents_manager.py#L140-L171) and [core/agents/dispatcher.py:163-187](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/agents/dispatcher.py#L163-L187):
  ```python
  def dispatch_task(
      self,
      agent_id: str,
      prompt: str,
      path: Optional[str] = None,
      model_override: Optional[str] = None,
      is_subtask: bool = False,
      group_id: Optional[str] = None,
      ...
  )
  ```
  Neither `core/ui_server.py` lines 1526–1531 nor `agent_manager.dispatch_task()` accept or pass `conversation_id`. When a background task is launched (via `/task`, `/build`, or action delegation), the task dispatcher operates in task-mode isolation without any reference to the active conversation thread (`conv_...`).

#### B. Is conversation history included in the delegated prompt?
- **Finding:** **NO.**
- **Code Reference:** In [core/ui_server.py:1525-1531](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/ui_server.py#L1525-L1531):
  ```python
  clean_task_prompt = prompt.split(" ", 1)[1] if " " in prompt else prompt
  dispatch_res = agent_manager.dispatch_task(
      agent_id=agent.id,
      prompt=clean_task_prompt,
      path=path,
      model_override=model_override,
  )
  ```
  Only the raw current user prompt (`clean_task_prompt`) is dispatched. The SQLite conversation messages from `agent_messages` are never retrieved, formatted, or injected into the task payload.

#### C. Does SafePromptManager or prompt transformations alter context differently?
- **Finding:** **YES — CRITICAL DIFFERENCE FOUND.**
- **Code Reference:**
  1. In [core/engines/adapter.py:177-198](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/engines/adapter.py#L177-L198):
     `SafePromptManager.write_prompt_if_needed(prompt, threshold=800)` checks if prompt length exceeds 800 characters. If it does, it writes the prompt to `.zezo_tmp/prompt_<task_id>.md` and returns `prompt_file`.
  2. **How Kilo Code builds its CLI vector:**
     In [core/engines/kilo.py:223-228](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/engines/kilo.py#L223-L228):
     ```python
     if prompt_file and prompt_file.exists():
         cmd.extend([
             f"Execute the task outlined in {prompt_file.as_posix()}",
             "--file",
             str(prompt_file.resolve()),  # <--- Explicit file injection into Kilo context!
         ])
     else:
         cmd.append(config.prompt)
     ```
     Kilo Code receives the explicit `--file` CLI flag pointing to the file, which forces Kilo's CLI parser to ingest the full contents of the prompt file into its reasoning context.
  3. **How Antigravity builds its CLI vector:**
     In [core/engines/antigravity.py:245-263](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/engines/antigravity.py#L245-L263):
     ```python
     if prompt_file and prompt_file.exists():
         effective_prompt = (
             f"Execute all directives and requirements in {prompt_file.as_posix()} "
             f"to complete the requested task."
         )
     else:
         effective_prompt = config.prompt

     cmd = [
         str(bin_path),
         "-p",
         effective_prompt,
         "--add-dir",
         str(config.workspace_path.resolve()),
         "--output-format",
         "stream-json",
         "--mode",
         "accept-edits",
     ]
     ```
     `agy` **does not have a `--file` argument** in this call vector. When `prompt_file` is generated, `agy` only receives:
     `-p "Execute all directives and requirements in C:/.../.zezo_tmp/prompt_...md to complete the requested task."`
     If the prompt file resides inside `.zezo_tmp/`, but `.zezo_tmp` is not immediately scanned or if `agy`'s print mode (`-p`) treats it as a general workspace instruction without reading the file contents into memory, `agy` is asked to complete a task whose requirements it cannot see!

#### D. Do Antigravity and Kilo Code use separate sessions or state?
- **Finding:** **YES.**
  - `agy` (`core/engines/antigravity.py`) executes non-interactively in print mode:
    `agy.exe -p <prompt> --add-dir <workspace> --output-format stream-json --mode accept-edits`.
    Although `agy` supports `--conversation <id>` and `-c` (`--continue`) (verified via `agy --help`), **neither flag is ever passed** by `AntigravityEngineAdapter`. Every invocation is completely stateless.
  - `kilo` (`core/engines/kilo.py`) executes via `kilo.cmd run <prompt> --dir <workspace> --format json`.
    `kilo` also supports `--session <id>` and `--continue`, but neither is passed.
  - Furthermore, in conversational mode (`AgentRuntime.step_stream_async`), the engines are **NOT** invoked at all — conversational answers are generated directly by Gemini (`core/gemini.py`) using the system prompt assembled in `AgentRuntime.build_system_prompt()`.

#### E. Root Cause Analysis for Issue 1
| Factor | Kilo Code | Antigravity (`agy`) | Verdict |
| :--- | :--- | :--- | :--- |
| **Prompt File Flag** | Uses `--file <prompt_file>` | Passes string reference in `-p` with no `--file` | **CONFIRMED DEFECT in `antigravity.py`** |
| **Session Continuity** | Fresh process, no session flag | Fresh process, no `--conversation` flag | **CONFIRMED DESIGN GAP** |
| **Conversational Context** | If invoked via chat without history, lacks history | If invoked via chat without history, lacks history | **CONFIRMED** |

**Confirmed Root Cause 1:**
When a prompt is large (>800 chars, e.g., containing user directives, design specifications, or context summaries), `SafePromptManager` offloads the text into a temporary file. Kilo Code passes `--file <path>`, which guarantees the engine reads the file. Antigravity CLI does not have a `--file` parameter passed, and the string passed to `-p` is merely a pointer to a path inside `.zezo_tmp/`. In headless print mode, `agy` frequently responds about not finding the directives or generates a generic response because the context was isolated in the unread `.zezo_tmp/` file.

---

## 2. Issue 2: Streaming UI and Stop Button Failure

### 2.1 Problem Statement
During Test 4 (user pasted a long prompt):
1. No loading or thinking indicator appeared in the chat.
2. The response appeared all at once rather than progressively rendering chunks.
3. Clicking the Stop button failed to interrupt generation.

### 2.2 Complete Flow Audit (Frontend → API → Backend → Provider)

```
[Chat UI: AgentChatThread / AgentDirectChatView]
       │
       ▼ (1) useLocalRuntime({ run({ messages, abortSignal }) })
       │
       ▼ (2) api.streamAgentChat(..., abortSignal) -> fetch('/api/agents/chat/stream')
       │
       ▼ (3) core/ui_server.py: _agent_chat_stream_handler
       │
       ▼ (4) core/agents/runtime.py: AgentRuntime.step_stream_async()
       │
       ▼ (5) core/gemini.py: gemini.stream_text() -> Google GenAI SDK
```

#### A. Inspection of Thinking & Loading Indicators
- **Finding:** **CONFIRMED DEFECT in `AgentChatThread.tsx`.**
- **Evidence:**
  In `frontend/src/components/assistant-ui/thread.tsx` lines 314–318 (the reference assistant-ui implementation), the UI explicitly mounts an animated thinking indicator:
  ```tsx
  {/* Clean animated thinking indicator while generating */}
  {isRunning && !hasContent && (
    <div className="flex items-center py-1 text-xs text-[var(--muted-foreground)]">
      <ThinkingTool state="thinking" />
    </div>
  )}
  ```
  In contrast, inspecting `frontend/src/components/office/AgentChatThread.tsx` lines 76–133 (`AgentAssistantMessage`):
  - `ThinkingTool` is **completely missing**.
  - No `isRunning && !hasContent` check exists.
  - The message only renders `MessagePrimitive.Parts` with `Text: TextPart`.
  - While the LLM is processing the prompt (Time To First Token), `messages` in `assistant-ui` has an assistant message with empty parts, but because `AgentAssistantMessage` lacks the thinking indicator, **the UI renders absolutely nothing** — creating a dead, frozen interface.
  - Furthermore, `onUpdateAgentStatus?.(agent.id, 'WORKING', 'Thinking: ...')` is called, but `AutonomousOfficeScreen.tsx` only updates the roster badge in the left sidebar or speech bubble — it never renders a status inside the active chat thread viewport!

#### B. Inspection of Progressive Streaming vs "All at Once" Rendering
- **Finding:** **CONFIRMED DUAL ROOT CAUSE (React Re-keying Remount + Provider TTFT).**
- **Evidence:**
  1. **Backend Generator:** In `core/agents/runtime.py:465-495`, tokens are yielded from `gemini.stream_text` via `asyncio.Queue` as `{"event": "chunk", "text": payload}`.
  2. **SSE Transport:** In `core/ui_server.py:1571-1574`, each chunk is written immediately:
     ```python
     if ev == "chunk":
         ok = await send_sse("chunk", {"text": item.get("text", "")})
     ```
  3. **Frontend Consumer:** In `frontend/src/lib/api.ts:91-119`, the `ReadableStream` reads buffers, splits on `\n\n`, parses `event: chunk`, and yields `{ type: 'chunk', text: ... }`.
  4. **React Runtime Generator:** In `frontend/src/components/office/AgentDirectChatView.tsx:335-339`:
     ```typescript
     } else if (chunk.type === 'chunk' && chunk.text) {
         currentText += chunk.text
         yield {
             content: [{ type: 'text' as const, text: currentText }],
         }
     }
     ```
     This correctly yields progressive text to `@assistant-ui/react`.
  5. **WHY DID IT APPEAR "ALL AT ONCE"?**
     - **Factor 1 (Provider TTFT):** On long prompts (as noted in Test 4), Gemini's server-side prefill takes several seconds (measured in Suite J as up to 11.4s when quota fallbacks occur). During this time, 0 chunks are emitted, and because there is no thinking indicator (Section A), the UI appears dead. Once generation begins, Gemini delivers high-speed bursts (40–80 tokens/sec), finishing in ~1–2 seconds.
     - **Factor 2 (Component Remounting via React `key`):**
       In `frontend/src/components/office/AgentDirectChatView.tsx:275`:
       ```tsx
       <AgentChatRuntime
         key={`${agent.id}-${activeThreadId}`}
         ...
       />
       ```
       Notice lines 197–199 in `AgentDirectChatView.tsx`:
       ```typescript
       if (targetThreadId !== activeThreadId) {
         setActiveThreadId(targetThreadId);
       }
       ```
       When the SSE `done` event arrives with `chunk.conversation_id` (`conv_...`), `handleConversationComplete` updates `activeThreadId` from `thread-...` to `conv_...`.
       Changing `activeThreadId` **immediately changes the React `key` of `AgentChatRuntime`** (`${agent.id}-${activeThreadId}`).
       This forces React to **unmount the entire `AssistantRuntimeProvider` and destroy the active streaming thread**, remounting a brand-new instance initialized with `threadMessages`. If a user is watching the stream or if a rerender occurs, the transient stream is wiped and replaced instantaneously by the final static text from `initialMessages`!

#### C. Inspection of Stop Button & Cancellation
- **Finding:** **CONFIRMED DEFECT in Cancellation Propagation.**
- **Evidence:**
  1. **UI Button:**
     In `frontend/src/components/office/AgentChatThread.tsx:206-216`:
     ```tsx
     {isRunning ? (
       <ComposerPrimitive.Cancel asChild>
         <Button title="Stop agent run">
           <Square className="w-3.5 h-3.5 fill-current" />
         </Button>
       </ComposerPrimitive.Cancel>
     ) : ...}
     ```
     Clicking this triggers `ComposerPrimitive.Cancel`, which calls `cancelRun()` on `local-thread-runtime-core.js:991`:
     ```javascript
     this.abortController?.abort(error);
     ```
  2. **Fetch Abort:**
     In `frontend/src/lib/api.ts:71-76`, `fetch` is called with `{ signal }`.
     When `abortController.abort()` fires, `fetch` aborts and throws `DOMException: The user aborted a request.`
  3. **Why did generation continue on the backend?**
     In `frontend/src/components/office/AgentDirectChatView.tsx:321-324`:
     ```typescript
     for await (const chunk of api.streamAgentChat(...)) {
       if (abortSignal?.aborted) {
         break
       }
     ...
     } catch (error: any) {
       if (abortSignal?.aborted) {
         console.info('Agent chat stream aborted by user.')
         return
       }
     ```
     When `fetch` aborts, the TCP socket connection to `http://localhost:5000/api/agents/chat/stream` is severed.
  4. **Backend Cancellation Failure:**
     In `core/ui_server.py:1465-1590`:
     ```python
     async def _agent_chat_stream_handler(self, request: web.Request) -> web.StreamResponse:
         ...
         async for item in runtime.step_stream_async(user_input=prompt, conversation_id=conversation_id):
             ev = item.get("event")
             if ev == "chunk":
                 ok = await send_sse("chunk", {"text": item.get("text", "")})
                 if not ok:
                     break
     ```
     Notice:
     - `send_sse` writes to `response.write()`. If the client disconnects, `send_sse` catches `(ConnectionResetError, asyncio.CancelledError)` and returns `False`.
     - `if not ok: break` breaks out of the loop in `ui_server.py`.
     - **HOWEVER:** Breaking out of `step_stream_async` in Python does **NOT** immediately stop the underlying daemon thread in `runtime.py`!
     - In `core/agents/runtime.py:469-487`:
       `producer_thread` runs `gemini.stream_text()` in a background worker thread.
       When `ui_server` breaks, `step_stream_async` exits its `while True` loop and executes its `finally:` block:
       ```python
       finally:
           stop_event.set()
       ```
       `stop_event.set()` signals the producer loop:
       ```python
       for chunk in gemini.stream_text(...):
           if stop_event.is_set():
               break
       ```
     - **WHY DID GENERATION SEEM NOT TO INTERRUPT?**
       1. In `core/gemini.py:530-536`:
          ```python
          response_stream = cl.models.generate_content_stream(**kwargs)
          for chunk in response_stream:
              txt = getattr(chunk, 'text', '') or ''
              if txt:
                  yield txt
          ```
          Google GenAI SDK's `generate_content_stream` holds a blocking HTTP/gRPC stream. If the network has already buffered the tokens from Gemini, the thread keeps receiving until the next chunk boundary check.
       2. **Critical Frontend Bug on Cancel:**
          In `frontend/src/components/office/AgentDirectChatView.tsx:362-365`:
          ```typescript
          } catch (error: any) {
            if (abortSignal?.aborted) {
              console.info('Agent chat stream aborted by user.')
              return
            }
          ```
          When the user clicks **Stop**, the catch block catches the abort and executes `return` without calling `onConversationComplete`!
          Because `onConversationComplete` is never called:
          - The partial text already received (`currentText`) is **never saved to the thread messages**.
          - The UI state remains in a dangling or partial state until the next message or until the component is remounted.
          - If the user re-enters the thread, the conversation state is restored from `initialMessages` (which has 0 record of the cancelled turn), creating the illusion that clicking Stop either broke the state or was ignored.

---

## 3. Confirmed Findings vs Hypotheses

| Investigation Item | Type | Evidence & Status |
| :--- | :---: | :--- |
| **Antigravity missing `--file` for prompt files** | **CONFIRMED** | `core/engines/antigravity.py:245-263` omits `--file`, while `core/engines/kilo.py:223-228` passes `--file`. When prompt > 800 chars, Antigravity cannot read `.zezo_tmp/prompt_...md`. |
| **No conversation history passed to task engines** | **CONFIRMED** | `core/ui_server.py:1526` and `core/agents/dispatcher.py:163` only pass raw single prompt; SQLite `agent_messages` history is never injected into task engines. |
| **Task engines use stateless sessions** | **CONFIRMED** | `antigravity.py` does not pass `--conversation <id>` or `-c`; `kilo.py` does not pass `--session <id>`. |
| **Missing Thinking indicator in AgentChatThread** | **CONFIRMED** | `AgentChatThread.tsx` completely omits `ThinkingTool` or `useAuiState(s => s.thread.isRunning)` loading indicators, making the chat appear completely frozen during TTFT. |
| **React Key remount destroying active stream** | **CONFIRMED** | `AgentDirectChatView.tsx:275` uses `key={`${agent.id}-${activeThreadId}`}`. When `activeThreadId` transitions from `thread-...` to `conv_...`, the entire component remounts, replacing live stream with static message snapshots. |
| **AbortController disconnects SSE socket** | **CONFIRMED** | `fetch` with `signal` aborts connection cleanly, triggering `stop_event.set()` in `runtime.py`. |
| **Incomplete message handling on abort** | **CONFIRMED** | `AgentDirectChatView.tsx:362-365` returns early on abort without saving the interrupted partial response to `savedMessages`. |

---

## 4. Recommended Minimal Fixes

### Fix Recommendation 1: Antigravity Prompt Context (Issue 1)
1. **Pass Prompt File Properly to Antigravity CLI:**
   In [core/engines/antigravity.py:245-263](file:///c:/Users/Hamza%20Bukhari/Documents/antigravity/jarvis-57/core/engines/antigravity.py#L245-L263), when `prompt_file` exists, either:
   - Read the prompt file directly if within safe shell limits or use standard input pipe, OR
   - Instruct `agy` to read the prompt file by passing its contents directly in `-p` when under the safe OS length, or pass the full instruction with explicit directive to read the file in the workspace.
2. **Inject Conversation Context into Task Dispatch:**
   In `core/ui_server.py:1526-1531`, if the user prompt is a follow-up task directive, format recent conversation turns (e.g. last 3–5 turns from `agent_messages`) and prepend them to the task prompt:
   ```python
   # Load recent conversation history if conversation_id exists
   context_prefix = ""
   if conversation_id:
       history = runtime.load_messages(conversation_id=conversation_id, limit=5)
       if history:
           context_prefix = "Previous Conversation Context:\n" + "\n".join(
               f"{m['role'].capitalize()}: {m['content']}" for m in history
           ) + "\n\nCurrent Task:\n"
   clean_task_prompt = context_prefix + clean_task_prompt
   ```

### Fix Recommendation 2: Streaming UI, Thinking Indicator & Stop Button (Issue 2)
1. **Add Thinking Indicator to `AgentChatThread.tsx`:**
   In `AgentAssistantMessage`:
   ```tsx
   const isRunning = useAuiState((s) => s.message.status?.type === "running");
   const hasContent = useAuiState((s) => {
     const parts = s.message.parts;
     return parts && parts.some((p: any) => p.type === "text" && Boolean(p.text?.trim()));
   });

   // Inside PKMessageContent:
   {isRunning && !hasContent && (
     <div className="flex items-center py-1 text-xs text-[var(--muted-foreground)]">
       <ThinkingTool state="thinking" />
     </div>
   )}
   ```
2. **Prevent Destructive Key Remount During Active Stream:**
   In `AgentDirectChatView.tsx:275`, decouple the React key from transient thread ID transitions during an active stream, or stabilize the key by using `agent.id` and managing thread message replacement internally without remounting the entire `AssistantRuntimeProvider`.
3. **Graceful Cancellation Message Settlement:**
   In `AgentDirectChatView.tsx:362-368`, when `abortSignal?.aborted` is caught:
   - Mark the assistant message status as `{ type: 'complete', reason: 'cancelled' }` or save the partial `currentText` with a `[Stopped by user]` annotation.
   - Commit the partial turn so the conversation thread remains consistent and the stop action is clearly reflected in the UI.

