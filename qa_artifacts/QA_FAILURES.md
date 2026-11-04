# QA Failures Report: ZEZO Autonomous Desktop AI Assistant

**Lead Architect:** Hamza Bukhari  
**Date:** November 4, 2026  
**Defects Summary:** 2 Critical Failures Detected in Suite J (Streaming Pipeline)

---

## Failure 1: Simulated Timer Streaming (Fake Streaming)

- **Failure ID:** `FAIL-J05`
- **Related Test IDs:** `J05` (Verify no fake timer-based streaming is used)
- **Severity:** **HIGH**
- **Affected Subsystem:** `core/agents/runtime.py` -> `AgentRuntime.step_stream_async`
- **Actual Behavior:**
  In `core/agents/runtime.py` lines 459–468, `AgentRuntime.step_stream_async` converts the live generator from `gemini.stream_text` into an in-memory synchronous `list()` inside a worker thread before yielding any data to the caller:
  ```python
  def _do_stream():
      return list(gemini.stream_text(query_text, tier="fast", timeout_ms=30000))

  chunks = await loop.run_in_executor(None, _do_stream)
  for ch in chunks:
      accumulated_chunks.append(ch)
      yield {"event": "chunk", "text": ch, "conversation_id": cid}
      await asyncio.sleep(0.01)
  ```
  The function completely buffers the entire LLM generation, waits until the last token is produced, and then replays the buffered list using `await asyncio.sleep(0.01)` to simulate incremental streaming.
- **Expected Behavior:**
  Genuine unbuffered token streaming where each token chunk emitted by the Google Gemini API is yielded to the async caller in real-time as it arrives over the wire.
- **Evidence:**
  Source inspection of `core/agents/runtime.py#L459-L468` and measured streaming telemetry:
  - Total chunks: 18
  - Total generation time: 11.72s
  - Time spent waiting for `_do_stream()` list conversion: 11.43s
  - Post-generation timer replay: 18 chunks emitted with exact 10ms–16ms intervals (`asyncio.sleep(0.01)`).
- **Reproduction Steps:**
  1. Call `AgentRuntime.step_stream_async(prompt="Write a 300 word essay", conversation_id=...)`.
  2. Record timestamp $t_0$ when call is made.
  3. Record timestamp $t_1$ when the first chunk is yielded.
  4. Observe that $t_1 - t_0$ equals the full duration of generation (~11.4s), followed by rapid 10ms spaced chunk delivery.
- **Suspected Root Cause:**
  A synchronous `list()` wrapper was used in `_do_stream()` inside `loop.run_in_executor`, defeating genuine async streaming.
- **Root Cause Confirmed:** **CONFIRMED**
- **Remediation Recommendation:**
  Bridge the synchronous SDK generator into an `asyncio.Queue` using a producer thread, or adopt native async streaming from `google-genai` client, yielding chunks directly as they are received.

---

## Failure 2: High Time-to-First-Token (TTFT) Due to Upstream Stream Buffering

- **Failure ID:** `FAIL-J02`
- **Related Test IDs:** `J02` (Verify first response chunk arrives before complete response is generated)
- **Severity:** **HIGH**
- **Affected Subsystem:** `core/agents/runtime.py` / `core/ui_server.py` `/api/agents/chat/stream`
- **Actual Behavior:**
  The first streaming chunk arrived at **11.433 seconds**, which was **97.5% of the total elapsed response duration (11.724 seconds)**. The client experiences a complete freeze for over 11 seconds before receiving any tokens, destroying the perceived latency advantage of streaming.
- **Expected Behavior:**
  The first token chunk should arrive within 500ms–1500ms (standard TTFT for Gemini Flash Fast tier), while generation continues incrementally.
- **Evidence:**
  Recorded in `qa_artifacts/suite_j_results.json`:
  ```json
  "J02_first_chunk_timing": {
    "status": "FAIL",
    "first_chunk_elapsed_sec": 11.433,
    "total_elapsed_sec": 11.724,
    "ratio_to_total": 0.975
  }
  ```
- **Reproduction Steps:**
  1. Send a multi-paragraph generation prompt to `/api/agents/chat/stream`.
  2. Measure time from request dispatch to receipt of the first SSE `event: chunk`.
  3. Observe latency exceeds 11 seconds.
- **Suspected Root Cause:**
  Direct downstream symptom of Failure 1 (`list(gemini.stream_text(...))` buffering).
- **Root Cause Confirmed:** **CONFIRMED**
- **Remediation Recommendation:**
  Resolving Failure 1 will automatically fix Failure 2, reducing TTFT to sub-second live token delivery.

