# JARVIS — Voice Pipeline

## Pipeline Modes

ZEZO supports two voice pipeline architectures:

### UI initialization contract

The pipeline and assistant settings controls are defined in the frontend ES module. The module must parse completely before `socket.connect()` runs; otherwise the browser cannot register `saveCustomiseSettings`, `togglePipelineMode`, `applyPreset`, or `savePipelineSettings`. Keep the WebSocket connection call after all UI handler declarations, and syntax-check the complete module after editing it.

### 1. Gemini Live (Default)

**Mode**: `pipeline_mode = "live"`

All audio processing in a single Google Gemini Live WebSocket:
- **STT**: Google automatic speech recognition (real-time)
- **LLM**: Gemini reasoning and function-calling
- **TTS**: Gemini synthetic voice (Puck, Charon, Fenrir, Kore, Aoede)
- **Barge-in**: User can interrupt mid-response
- **Tool-calling**: Native function invocation
- **Latency**: ~200-500ms end-to-end

**Best for**: Real-time conversations, tool invocation, natural interruption.

### 2. Cascade Mode (Custom Engines)

**Mode**: `pipeline_mode = "cascade"`

Decoupled pipeline where each stage runs locally or on custom endpoints:

| Stage | Options | Source |
|-------|---------|--------|
| **STT** | `local_whisper`, `groq_whisper`, `vosk` | Config key `stt_engine` |
| **LLM** | `groq`, `gemini`, `ollama` | Config key `llm_engine` |
| **TTS** | `kokoro`, `edge_tts`, `elevenlabs` | Config key `tts_engine` |
| **Voice** | Engine-specific | Config key `tts_voice` |

**Engine runthrough**:
1. User speech → `transcribe_utterance(engine=stt_engine)`
2. Text → `llm_generate(engine=llm_engine)` → response
3. Response → `make_tts(engine=tts_engine, voice=tts_voice)` → audio

**Presets** (UI one-click)
- **Gemini Live**: Live mode (fastest, best quality)
- **Cloud Fast**: `groq_whisper` + `groq` + `edge_tts` (good quality, lower cost)
- **Balanced**: `groq_whisper` + `groq` + `kokoro` (local TTS, cloud inference)
- **Fully Offline**: `local_whisper` + `ollama` + `kokoro` (no cloud, needs local LLM)

**Best for**: Offline-first, cost control, testing individual engines, custom voice synthesis.

### 3. Voice Fallback Failover & Error Surfacing

**Mode**: `voice_fallback = "auto" | "off"` (Config key `voice_fallback`)

Controlled via the UI toggles in the Settings Drawer, Customise Assistant modal, and Voice Pipeline modal:
- **`auto` (Default)**: If the Gemini Live WebSocket connection drops, encounters a network timeout, or hits quota limits, ZEZO immediately fails over to the local/cascade voice loop (`VoiceFallback`) without dropping user interaction.
- **`off`**: Automatic failover is strictly disabled. Instead of falling back to offline engines, the exact connection, authentication, or model error is rendered directly to the HUD (`ERR: Live connection failed: ...`), and the user is informed with a prompt to toggle Fallback ON if offline voice is desired.
- **Direct Groq Key Entry**: The Voice Pipeline modal includes an inline Groq API key configuration card that saves directly to local `config/api_keys.json` and dynamically refreshes telemetry warnings without modal swapping.

---

## Complete Voice Interaction Flow (Gemini Live)

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
3. **Echo tail guard**: After JARVIS finishes speaking, a ~260ms window (`_out_latency` + `_TAIL_MARGIN=0.06s`) where the assistant's own voice is filtered out
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
| `_TAIL_MARGIN` | 0.06s | Echo tail margin (plus measured `_out_latency`) |
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

## Offline Voice Fallback & Cascade Architecture (`core/voice_fallback.py`)

Gemini Live is the primary real-time voice path. When Gemini Live is unavailable (offline, quota limit, service disruption) or when the user explicitly configures **Cascade Mode**, ZEZO executes a high-performance decoupled voice loop:

```
Full-Duplex Mic (sounddevice 16k InputStream)
    ↓
UtteranceSegmenter (180ms VAD pause, 200ms min length, 600.0 RMS energy gate)
    ↓ (complete utterance)
Background Utterance Worker Thread (non-blocking mic stream, generation_id tracked)
    ↓
STT Transcribe: local faster-whisper (tiny)  →  Groq Whisper Large v3 Turbo  →  Vosk
    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Fast Deterministic Matcher (0ms LLM overhead)                 │
│ Exact & conversational variations: "can you please open the calc",     │
│ "launch vscode", "mute", "increase volume", "stop", "next track"       │
│ → Direct action invocation without Groq LLM or conversational TTS      │
└────────────────────────────────────────────────────────────────────────┘
    ↓ (if unhandled)
┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Laya Secondary Intent Router (Confidence Gated >= 0.75)       │
│ Isolated intent classifier with confidence scoring & abstention        │
└────────────────────────────────────────────────────────────────────────┘
    ↓ (if abstained)
┌────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Groq LLM Streaming & Sentence TTS Pipeline                    │
│ Streaming tokens → sentence accumulator → parallel synthesis           │
│ Kokoro offline / Edge-TTS / ElevenLabs                                 │
└────────────────────────────────────────────────────────────────────────┘
    ↕
Instant Barge-In Interruption (Continuous mic detects user speech → sd.stop() < 20ms, cancels in-flight TTS & increments generation_id)
```

### Key Cascade Features:

1. **Full-Duplex Continuous Mic Stream**:
   - `sd.InputStream` runs continuously on its own thread without pausing during STT, LLM inference, or TTS playback.
   - Utterances are dispatched to a dedicated daemon worker (`utterance-worker`), ensuring the microphone loop never stalls or drops incoming audio frames.

2. **Race-Condition-Safe Instant Barge-in & Generation IDs**:
   - Monotonically increasing `_generation_id` tracks active response lifecycle.
   - When the user speaks over the assistant (`_is_speaking == True` and `level >= energy * 1.4`):
     - `_interrupt()` halts audio playback immediately via `sd.stop()` (< 20ms).
     - Increments `_generation_id` and sets `_interrupted` event.
     - Drains audio queues in TTS engine and halts pending synthesis tasks.
     - Prevents stale sentence callbacks from old generations from playing or entering the audio queue.
     - Feeds interruption audio block directly into `UtteranceSegmenter.push()` so the new user turn begins seamlessly without dropping frames.

3. **3-Layer Intent Architecture (`core/fast_intent.py` & `core/laya_router.py`)**:
   - **Layer 1: Deterministic Matcher**: Extensible registry handling prefix/suffix stripping ("can you please", "could you", "jarvis please"), app alias mapping (calculator, chrome, vscode, terminal, spotify, discord, notepad, settings, etc.), media controls (play/pause, next track, prev track), volume adjustments, and system queries. Directly dispatches actions (`open_app`, `computer_settings`, `pyautogui`) without invoking Groq LLM or generating conversational TTS.
   - **Layer 2: Laya Secondary Router**: Isolated classifier with confidence gating and abstention. Handles complex conversational variations.
   - **Layer 3: Groq LLM Fallback**: Streaming LLM response via `call_groq_stream` when neither layer classifies the command.

4. **Real Latency Instrumentation**:
   - Real-time logging of all pipeline transitions:
     - `[TIMING] STT start / end / total`
     - `[TIMING] FAST_INTENT start / end / FAST_DISPATCH total`
     - `[TIMING] LAYA start / end / total`
     - `[TIMING] LLM start / LLM first token`
     - `[TIMING] FIRST_SENTENCE / TTFT`
     - `[TIMING] TTS start / first audio / PLAYBACK start`
     - `[TIMING] TTFA`
     - `[TIMING] BARGE_IN detected / PLAYBACK stopped / stop duration`

5. **Configurable Engines & Auto-Start**:
   - **Config:** `voice_fallback` = `auto` (default) | `manual` | `off`.
   - **Engines:** `stt_engine` (`groq_whisper` / `local_whisper` / `vosk`), `llm_engine` (`groq` / `gemini` / `ollama`), `tts_engine` (`kokoro` / `edge_tts` / `elevenlabs`), `tts_voice`.
   - **Dynamic Language Support:** Response prompt dynamically enforces user-configured language (`get_response_language()`), automatically falling back to Edge-TTS for non-English scripts.
   - **Standalone Execution:** `python -m core.voice_fallback`.

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