# ZEZO — Session Management

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## Overview

ZEZO manages Gemini Live sessions with support for resumption, reconnection, and context compression. Sessions can last for hours thanks to sliding-window compression. In addition, ZEZO supports composite session IDs for autonomous fleet agent lineages and peer delegations.

---

## Session Creation

**File:** `main.py`, `ZezoLive._build_config()` and `run()` method

```python
# 1. Build LiveConnectConfig
cfg = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription={},
    input_audio_transcription={},
    system_instruction=system_instruction,
    tools=[{"function_declarations": _all_decls}],
    session_resumption=types.SessionResumptionConfig(
        handle=self._resume_handle  # None on first connect
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        sliding_window=types.SlidingWindow(),
    ),
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=get_voice()
            )
        )
    ),
)

# 2. Connect
cm = cl.aio.live.connect(model=LIVE_MODEL, config=cfg)
session = await asyncio.wait_for(cm.__aenter__(), 30)
```

---

## Composite Session IDs & Fleet Lineage

In ZEZO's multi-agent architecture, sessions operate on two levels:

1. **Core Voice Session**: Managed directly via `genai.Client.aio.live.connect()`, streaming bidirectional PCM audio with Gemini Live.
2. **Composite Agent & Task Sessions**: Specialist fleet agents (e.g. Verve, Flux, Ahmad, Michael) and background execution tasks use composite session IDs structured as:
   ```
   <agent_id>:<session_uuid>
   ```
   - **Agent Thread Isolation:** Stored and tracked per agent (`zezo_agent_threads_<agent_id>`), guaranteeing isolated multi-turn context without memory contamination between agents.
   - **Autonomous P2P Peer Sessions:** When agents hand off tasks via `fleet_control(action='peer_chat')`, `core.fleet_manager.generate_peer_session_id()` generates deterministic lineage tokens:
     ```
     peer:<from_agent>-><to_agent>:<timestamp>
     ```
   - **Loop Gating:** `core.loop_gates.LoopGateKeeper` tracks execution iterations, tool invocation quotas, and timeout gates per composite `session_id`.

---

## Session Resumption

### How It Works

```
Server issues resumption handle every few seconds
    ↓
self._resume_handle updated in RAM
    ↓
On reconnect:
    session_resumption=types.SessionResumptionConfig(handle=self._resume_handle)
    ↓
Session resumes with conversation intact
```

### Critical Design Decision: RAM Only

**The resumption handle is stored only in RAM, never on disk.** This is deliberate:

> Persisting it to disk would make a fresh launch continue yesterday's conversation, which sounds appealing but breaks the session-summary flow: `_save_session_summary` runs at shutdown and the morning briefing pops it the next day. A conversation that never ends never produces a summary, and the "yesterday we talked about…" line silently disappears.

### What Breaks Resumption

- **Voice change**: `keep_context=False` → fresh session (server restores voice with session)
- **Audio device change**: `keep_context=True` → conversation preserved
- **Expired handle**: Dropped after one attempt (never retried)

---

## Connection Drops & Recovery

### Detection

```python
# _watch_reconnect() task monitors for voluntary reconnects
await self._reconnect_event.wait()
raise _ReconnectSignal(keep_context=keep)
```

### Recovery

```python
# TaskGroup catches the signal, unwinds
# _run() catches _ReconnectSignal, rebuilds session
# Resumption handle replayed if keep_context=True
```

---

## Context Compression

```python
context_window_compression=types.ContextWindowCompressionConfig(
    sliding_window=types.SlidingWindow(),
)
```

This enables **unlimited sessions** — the context window never fills up. Old turns are compressed rather than discarded.

---

## Session State Variables

| State Variable | Type | Purpose |
|----------------|------|---------|
| `self.session` | LiveSession | The active Gemini Live session |
| `self._resume_handle` | str | Resumption token (RAM only) |
| `self._turn_done_event` | asyncio.Event | Signals turn completion |
| `self._session_log` | list[str] | Conversation turns for summary |
| `self._is_speaking` | bool | Speaking state |
| `self._last_user_speech` | float | Monotonic time of last speech |
| `self._awake` | bool | Wake state |

---

## Session Continuity

The session survives:
- **Network drops**: Resumption handle replayed, conversation continues
- **Microphone changes**: `_on_audio_device_change()` → rebuild with `keep_context=True`
- **Voice changes**: `_on_voice_change()` → rebuild with `keep_context=False` (fresh start)

---

## Session Termination (`shutdown_zezo`)

```python
# shutdown_zezo tool
async def _do_shutdown():
    await self._save_session_summary()
    await self.session.send_client_content(
        turns=[{"role": "user", "parts": [{"text": "Say a brief natural goodbye to the user."}]}],
        turn_complete=True
    )
    await asyncio.sleep(1.5)
    import os as _os
    _os._exit(0)
```

**Session summary** is saved to `memory/long_term.json["sessions"]` on shutdown.

---

## Turn Management & Push-to-Talk

```
User speaks (or holds Push-to-Talk: Ctrl+Alt) → turn_complete=True
    ↓
Gemini processes → may call tools
    ↓
Tool results returned to Gemini
    ↓
Gemini generates response
    ↓
Turn complete → _turn_done_event set
    ↓
Ready for next turn
```

- **Push-to-Talk Hotkey:** Strictly **`Ctrl+Alt`**. When pressed, mic audio streams immediately with a 50ms brush-protection debounce and 0.5s delayed turn commit.
- **Duplicate prevention**: `_is_repeat_chunk()` guards against API re-sending transcript tails across multiple `turn_complete` events.

---

## Enhanced Live Features

### Proactive Audio
```python
if get_proactive_audio_enabled():
    cfg["proactivity"] = types.ProactivityConfig(proactive_audio=True)
```
The model can detect speech not addressed to it and stay quiet.

### Turn Tuning
```python
if turn.get("enabled", True):
    detect = types.AutomaticActivityDetection(
        silence_duration_ms=turn["silence_ms"],  # default 550ms
        prefix_padding_ms=turn["prefix_ms"],     # default 150ms
    )
```

### Media Resolution
```python
res = get_media_resolution()  # "default", "low", "medium", "high"
```
Controls screenshot/camera tokenisation.

---

## Summary

```
Session creation: genai.Client.aio.live.connect()
Resumption: Handle in RAM, replayed on reconnect
Compression: Sliding window, unlimited sessions
Continuity: Survives network drops, device changes
Termination: Session summary saved via shutdown_zezo, then exit
Composite Sessions: <agent_id>:<session_uuid> & peer:<src>-><dst>:<ts>
Turn Management: turn_complete, duplicate prevention, Push-to-Talk (Ctrl+Alt)
Enhancements: Proactive audio, turn tuning, media resolution
```
