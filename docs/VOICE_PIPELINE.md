# JARVIS — Voice Pipeline

## Complete Voice Interaction Flow

```
User speaks
    ↓
Microphone captures audio (sounddevice.InputStream, 16kHz, mono, int16)
    ↓
Audio callback fires (1024 frames = ~64ms)
    ↓
callback() in _listen_audio()
    ↓
┌──────────────────────────────────────┐
│ GATE 1: Wake Word                    │
│ if waking_enabled and not awake:     │
│   → audio goes to WakeWordDetector   │
│   → if "Hey Jarvis" detected → wake()│
│   → otherwise: return (no streaming) │
└──────────────────────────────────────┘
    ↓ (if awake)
┌──────────────────────────────────────┐
│ GATE 2: Speaking Lock                │
│ if self._is_speaking:                │
│   → DON'T stream (barge-in blocked)  │
│   → BUT listen locally for interrupt  │
└──────────────────────────────────────┘
    ↓ (if not speaking)
┌──────────────────────────────────────┐
│ GATE 3: Echo Tail Guard              │
│ if self._tail_active():              │
│   → EchoGuard.is_user_speech()       │
│   → if echo → drop block             │
│   → if user voice → pass through     │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ GATE 4: Push-to-Talk                 │
│ if ptt_enabled and not ptt_held:     │
│   → block audio                      │
└──────────────────────────────────────┘
    ↓
Audio bytes → out_queue → send_realtime_input()
    ↓
WebSocket → Google Gemini Live API
    ↓
┌──────────────────────────────────────┐
│ Gemini Live Processing               │
│                                      │
│ STT: Converts audio to transcript    │
│ LLM: Processes transcript, reasons   │
│ Tool: Calls functions if needed      │
│ TTS: Generates response audio        │
└──────────────────────────────────────┘
    ↓
session.receive() yields response
    ↓
┌──────────────────────────────────────┐
│ RESPONSE HANDLING                    │
│                                      │
│ Transcript → _clean_transcript()     │
│           → _is_repeat_chunk()       │
│           → VisemeStream.feed_text() │
│           → UI activity log          │
│                                      │
│ Audio → _play_audio()                │
│      → sounddevice.OutputStream      │
│      → Speakers                      │
│                                      │
│ Audio → VisemeStream.frames()        │
│      → Avatar mouth animation        │
└──────────────────────────────────────┘
    ↓
User hears response, avatar speaks
    ↓
set_speaking(False) → echo tail guard starts
    ↓
Wait for next user input or auto-sleep
```

## Detailed Transition Explanations

### Transition 1: User Speaks → Microphone

**File:** `main.py`, `_listen_audio()` line 1296

The `sounddevice.InputStream` is opened with a callback:
```python
sd.InputStream(
    samplerate=16000, channels=1, dtype="int16",
    blocksize=1024, device=mic_dev, callback=callback
)
```

The callback fires whenever ~64ms of audio is captured. It runs on a **dedicated sounddevice thread**.

### Transition 2: Microphone → Audio Gating

The callback applies four sequential gates. Each gate can stop the audio from reaching Gemini:

1. **Wake word gate**: If asleep and wake word enabled, audio goes ONLY to the local wake word detector
2. **Speaking lock**: If JARVIS is speaking, microphone is muted to prevent self-interference
3. **Echo tail guard**: After JARVIS finishes speaking, a 475ms window where the assistant's own voice is filtered out
4. **Push-to-talk**: If enabled, audio is blocked unless the Ctrl+Space chord is held

### Transition 3: Audio → Gemini Live

```python
# _send_realtime()
await self.session.send_realtime_input(
    audio=types.Blob(
        data=msg["data"],
        mime_type=msg.get("mime_type", "audio/pcm")
    )
)
```

Audio is sent as raw PCM bytes over the Gemini Live WebSocket connection. Each chunk is ~20ms of audio.

### Transition 4: Gemini Live → Response

```python
async for resp in session.receive():
    sc = getattr(resp, "server_content", None)
    # Extract transcript
    if sc and sc.output_transcription and sc.output_transcription.text:
        transcript = sc.output_transcription.text
    # Extract audio
    # Gemini produces both text and audio simultaneously
```

The response contains:
- `output_transcription.text` — the model's spoken words transcribed
- `audio` — the raw audio bytes for playback
- `tool_calls` — function calls the model wants to execute

### Transition 5: Transcript → Viseme

```python
# VisemeStream.feed_text()
for item in text_to_visemes(text):
    self._q.append(item)

# VisemeStream.frames() — called per audio frame
out = []
for level, a_open, a_wide in audio:
    self._carry += hop / self._step_seconds()
    while self._carry >= 1.0 and self._q:
        self._cur = self._q.popleft()
        self._carry -= 1.0
    t_open, t_wide, closure = VISEMES.get(self._cur[0], VISEMES["REST"])
    o = 0.72 * t_open + 0.28 * a_open  # text leads, audio corrects
    w = 0.78 * t_wide + 0.22 * a_wide
    out.append((level, o, w))
```

**Blend ratio**: 72% text-determined shape + 28% audio-determined shape. This means the transcript supplies the mouth shape (critical for closures like /m/, /b/, /p/) while the audio supplies timing and force.

### Transition 6: Audio → Speakers

```python
def _play_audio(audio_bytes):
    # Decode and play via sounddevice
    sd.play(decoded_samples, 24000)
    # Non-blocking — the callback continues
```

The audio playback cursor is tracked precisely:
```python
self._play_cursor = 0.0  # updated per audio batch
# The mouth animation is scheduled against this cursor
```

### Transition 7: Auto-Sleep

```python
async def _run_sleep_watch():
    while True:
        await asyncio.sleep(5)
        if not self._wake_enabled or not self._awake:
            continue
        if speaking:
            continue
        if (time.monotonic() - self._last_user_speech) > 120.0:
            self.sleep(reason="no speech for 2 minutes")
```

The assistant auto-sleeps after 2 minutes of silence (wake-word mode only).

## Timing Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `SEND_SAMPLE_RATE` | 16000 | Mic sample rate |
| `RECEIVE_SAMPLE_RATE` | 24000 | Speaker sample rate |
| `CHUNK_SIZE` | 1024 | Audio frames per callback |
| `_VIS_HOP` | 480 | Viseme frame step (20ms at 24kHz) |
| `_VIS_WIN` | 1024 | Viseme analysis window (~43ms) |
| `_TAIL_MARGIN` | 0.25s | Echo tail margin |
| `WAKE_SLEEP_TIMEOUT` | 120.0s | Auto-sleep after silence |
| `_REPEAT_MIN` | 12 chars | Minimum chunk length for dedup |

## Error Handling in Voice Pipeline

### Interrupted Speech
```python
def interrupt():
    self._interrupted = True
    # Drain the audio queue
    while True:
        q.get_nowait()  # discard queued audio
    self._visemes.reset()
    self._play_cursor = 0.0
```

### Session Reconnection
```python
# _ReconnectSignal raised inside TaskGroup
# TaskGroup unwinds → session destroyed → new session created
# Resumption handle replayed if keep_context=True
```

### Audio Device Failure
```python
try:
    _mic_stream = _open_mic(_mic_dev)
except Exception:
    # Falls back to system default
    _mic_stream = _open_mic(None)
```

## Data Flow Summary

```
MIC → callback → gates → out_queue → WebSocket → Gemini
                                                          ↓
Gemini ← receive ← WebSocket ← audio ← speakers ← output stream
                                     ↓
                              VisemeStream → avatar
                              transcript → UI log
                              audio → playback cursor → speakers
```