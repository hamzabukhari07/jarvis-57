# 📋 Technical Plan: Real-Time Streaming Live Transcription (User & Assistant)

**Author:** Antigravity  
**Lead Architect:** Hamza Bukhari  
**Date:** 2026-10-03  
**Status:** Approved for Implementation  
**Target:** Low-latency word-by-word streaming transcription into Activity Log for both User speech and Assistant voice generation.

---

## 1. Executive Summary & Objective

In the current architecture, both User voice transcripts and Assistant (ZEZO) voice transcripts are buffered internally in `main.py` and only emitted to the Activity Log / stream box at the end of the user utterance or when the turn completes.

This implementation provides:
1. **Real-time User Speech Streaming:** As Gemini Live WebSocket emits `server_content.input_transcription.text` deltas, tokens stream immediately to the UI with an active blinking cursor/indicator.
2. **Real-time Assistant Voice Streaming:** As Gemini Live WebSocket emits `server_content.output_transcription.text` deltas, tokens stream immediately to the UI into an active ZEZO speech bubble.
3. **Turn Sealing & Deduplication:** When `server_content.turn_complete` triggers, the active streaming bubble is cleanly sealed into a permanent transcript card, preventing duplicate logs or UI jitter.
4. **Mic Audio Stream Stabilization (Diagnosis Report Remediation):**
   - Standardize clean PCM audio payload delivery `mime_type="audio/pcm"` in `send_realtime_input()`.
   - Prevent 1011 gateway disconnection during active mic speech.
   - Synchronize queue buffer handling between live streaming callbacks and WebSocket sends.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────┐
│              Gemini Live API (WebSockets)               │
│   sc.input_transcription.text / output_transcription    │
└───────────────────────────┬─────────────────────────────┘
                            │ (partial token events)
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 main.py (_receive_audio)                │
│  - Emits 'transcript_stream' events to ui / ui_server   │
│  - Tracks active user & ai streaming buffers            │
│  - On turn_complete: seals bubbles (done: True)         │
└───────────────────────────┬─────────────────────────────┘
                            │ (WebSocket broadcast)
                            ▼
┌─────────────────────────────────────────────────────────┐
│              core/ui_server.py (WebSocket)              │
│  - broadcast("transcript_stream", { speaker, text, ...})│
└───────────────────────────┬─────────────────────────────┘
                            │ (ws.send_str)
                            ▼
┌─────────────────────────────────────────────────────────┐
│          frontend/index.html & frontend/js/app.js       │
│  - socket.on('transcript_stream')                       │
│  - Creates or appends to active streaming DOM bubble    │
│  - When done: true, removes streaming cursor & finalizes│
└─────────────────────────────────────────────────────────┘
```

---

## 3. WebSocket Protocol Specification

### Event: `transcript_stream`
Payload schema:
```json
{
  "speaker": "user" | "zezo",
  "text": " incremental words or full delta ",
  "done": false | true,
  "id": "stream_user_12345"
}
```

- When `done: false`: Frontend finds element `#stream-msg-${speaker}` (or creates it if missing). It appends or updates the text and shows a typing/speech cursor.
- When `done: true`: Frontend removes the live cursor, converts the bubble into a finalized `.stream-msg`, clears the active stream reference, and updates the log scroll position.

---

## 4. Phase-by-Phase Implementation Steps

### Phase 1: Backend Streaming in `main.py` & `ui.py`
- Add `stream_transcript(speaker: str, text: str, done: bool = False)` method to `ZezoUI` in `ui.py`.
- In `main.py` (`_receive_audio`):
  - Whenever `sc.input_transcription.text` is received, call `ui.stream_transcript("user", txt, done=False)`.
  - Whenever `sc.output_transcription.text` is received:
    - If user speech was streaming, ensure it is sealed: `ui.stream_transcript("user", "", done=True)`.
    - Stream ZEZO token: `ui.stream_transcript("zezo", txt, done=False)`.
  - On `sc.turn_complete` or interruption:
    - Seal any active streaming bubbles: `ui.stream_transcript("user", "", done=True)` and `ui.stream_transcript("zezo", "", done=True)`.

### Phase 2: UI Server WebSocket Integration
- In `ui.py`: emit signal `_stream_sig` ➔ `self._server.broadcast("transcript_stream", {"speaker": speaker, "text": text, "done": done})`.

### Phase 3: Frontend Dynamic Bubble Handler (`index.html` & `app.js`)
- In `frontend/index.html` (and `frontend/js/app.js`):
  - Handle `socket.on('transcript_stream')`.
  - If `!done`:
    - Check if `#active-stream-${speaker}` exists. If not, create a modern themed message bubble with a glowing pulse dot / cursor.
    - Append the incoming text chunk to the body.
    - Scroll `stream-box` to bottom smoothly.
  - If `done`:
    - Find `#active-stream-${speaker}`, remove the pulse cursor, rename/finalize id, and attach the copy button.
  - Handle fallback: if `log_entry` arrives for a message that was already streamed, avoid duplicate cards.

---

## 5. 3-Layer Verification Plan
1. **Layer 1 (Static):** Run `python -m py_compile main.py ui.py core/ui_server.py`.
2. **Layer 2 (Runtime & Tests):** Run `pytest tests/` to confirm all 109 unit and integration tests pass without regression.
3. **Layer 3 (Regression):** Test WebSocket event broadcasting and verify the Activity Log doesn't duplicate entries when `turn_complete` or `log_entry` triggers.
