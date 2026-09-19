# JARVIS — TTS (Text-to-Speech)

## Answer: TTS is Handled Entirely by Gemini Live API

> **JARVIS does not use a separate TTS model for the main voice conversation. Text-to-speech is handled natively by the Gemini Live API.**

The Gemini Live model is a **native audio model** — it produces audio directly as its primary output modality. The configuration `response_modalities=["AUDIO"]` means the model only speaks (it cannot respond with text).

## How TTS Works in the Main Pipeline

### The Audio Output Pipeline

```
Gemini Live session produces audio
    ↓
session.receive() async iterator
    ↓
For each response:
    - server_content.audio → raw audio bytes
    - server_content.output_transcription.text → text transcript
    ↓
Audio bytes processed by _play_audio()
    ↓
sounddevice.OutputStream → speakers
    ↓
Simultaneously: text → VisemeStream → avatar mouth shapes
```

### Connection Configuration

```python
cfg = dict(
    response_modalities=["AUDIO"],
    output_audio_transcription={},
    ...
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=get_voice()  # e.g., "Charon"
            )
        )
    ),
)
```

**File:** `main.py:1020-1044` — `_build_config()`

### Voice Configuration

| Parameter | Value | Source |
|-----------|-------|--------|
| Available voices | `Charon`, `Puck`, `Kore`, `Fenrir`, `Aoede` | `memory/config_manager.py:81` |
| Default voice | `Charon` | `memory/config_manager.py:82` |
| Config key | `voice_name` | `config/api_keys.json` |
| Live switch | `_on_voice_change()` → rebuild session | `main.py:786` |

### Voice Switching

When the user changes voice in the UI:

```
ui.py → on_voice_change
    ↓
JarvisLive._on_voice_change()
    ↓
request_reconnect(keep_context=False, reason="new voice")
    ↓
Reconnect signal → TaskGroup unwinds
    ↓
_new session with new voice_name in config
    ↓
Previous conversation preserved via resumption handle?
    NO — voice change drops context intentionally
```

**Why keep_context=False for voice:** Resuming restores the server's session state, and the safe reading is that it restores the voice with it, which would make the picker appear to do nothing.

## Audio Playback Details

### Output Stream

**File:** `main.py` — `_listen_audio()` and `_play_audio()`

```python
# Output stream (speakers)
sd.RawOutputStream(
    samplerate=RECEIVE_SAMPLE_RATE,  # 24000
    channels=CHANNELS,                 # 1
    dtype="int16",
    blocksize=CHUNK_SIZE,              # 1024
    device=output_dev,
)
```

### Audio Queuing

```
Audio received from Gemini Live
    ↓
Audio bytes extracted from response
    ↓
_put_audio() → out_queue
    ↓
_send_audio() coroutine reads from out_queue
    ↓
session.send_audio() or direct playback
```

### Latency Compensation

```python
# The mouth is scheduled against a playback cursor, not "now"
self._play_cursor = 0.0  # wall-clock time when next audio will begin to sound

# The tail guard prevents the assistant from hearing its own echo:
self._tail_until = time.monotonic() + self._out_latency + _TAIL_MARGIN
# _TAIL_MARGIN = 0.25 seconds
# _out_latency is measured from the device's own reported latency
```

## The Echo Guard (Self-Echo Prevention)

**File:** `core/echo.py` — `EchoGuard` class

```
After JARVIS finishes speaking:
    ↓
set_speaking(False) → starts the tail guard
    ↓
Microphone stays OPEN (not muted!)
    ↓
Each audio block: EchoGuard.is_user_speech()
    ↓
Band energy analysis + subtraction
    ↓
If block is our own echo → drop it
    ↓
If block is a user voice → pass to Gemini
    ↓
Tail guard expires → normal operation resumes
```

**How it works:**
1. **Content comparison** — both streams reduced to band energies; the output is subtracted from the input. Pure echo cancels to near zero.
2. **Learned echo gain** — the observed mic-to-output ratio is folded into a running estimate
3. **Two thresholds** — `_head` (near-worst echo) and `_floor` (typical residual)
4. **Warmup** — 16 blocks (~1 second) of listening before judging

**Key parameters:**
```python
_HEAD_Q = 97       # percentile of observed echo
_HEAD_MULT = 1.15  # headroom above the percentile
_MIN_USER = 0.15   # minimum level to count as a voice
_BLOCKS_NORMAL = 5    # ~320ms of evidence for reliable rooms
_BLOCKS_NOISY = 12    # ~770ms for reverberant rooms
```

## The Optional TTS Engines

**File:** `core/tts.py`

While Gemini Live handles the main conversation TTS, `core/tts.py` contains **three alternative TTS engines** for potential use cases:

### EdgeTTS (Default for offline TTS)

```python
class EdgeTTSEngine:
    """Microsoft EdgeTTS – free, requires internet."""
    def __init__(self, voice="en-US-GuyNeural"):
    def speak(self, text: str) -> None:
        # Uses edge_tts.Communicate
```

### Kokoro (Fully Offline)

```python
class KokoroTTSEngine:
    """Fully offline Kokoro neural TTS (~330 MB model)."""
    def __init__(self, voice="af_heart", speed=1.0):
    def speak(self, text: str) -> None:
        # Uses kokoro.KPipeline
        # Producer/consumer threading for synthesis + playback
```

### ElevenLabs (Cloud API)

```python
class ElevenLabsTTSEngine:
    """ElevenLabs cloud TTS – API key required."""
    def __init__(self, api_key, voice_id="pNInz6obpgDQGcFmaJgB"):
    def speak(self, text: str) -> None:
        # POST to elevenlabs.io API
```

### TTSPlayer (Wrapper)

```python
class TTSPlayer:
    """Thread-safe player wrapper."""
    def speak(self, text, on_start=None, on_done=None):
        # Blocking call from dedicated thread
```

**Status:** These engines are **NOT used** in the main conversation pipeline. They exist as alternatives for potential future use or for specific scenarios where Gemini Live TTS is not available.

## Audio Output Format

| Parameter | Value |
|-----------|-------|
| Sample rate | 24000 Hz |
| Channels | Mono |
| Format | int16 PCM |
| Chunk size | 1024 frames |
| Playback | sounddevice |

## Lip-Sync and Audio Sync

The TTS audio and viseme animation are synchronized via a shared clock:

```
Gemini produces audio chunks at ~20ms intervals
    ↓
Audio played via sounddevice at 24kHz
    ↓
_visemes.frames(audio, hop=20ms) called simultaneously
    ↓
VisemeStream blends audio formants + transcript shapes
    ↓
Avatar mouth follows the playback cursor
```

**The playback cursor** (`self._play_cursor`) is the wall-clock time at which audio written next will begin to sound. The mouth is scheduled against this, not against "now". This ensures the mouth tracks the words even when the sound card buffers audio ahead.

## Summary

```
VERIFIED: JARVIS uses Gemini Live API for all TTS in the main conversation.

The model is configured with response_modalities=["AUDIO"], meaning it
produces audio directly. There is no separate TTS model.

core/tts.py contains EdgeTTS, Kokoro, and ElevenLabs engines but they
are NOT used in the main conversation pipeline. They exist as alternatives.

The audio output pipeline is:
  Gemini Live → session.receive() → audio bytes → sounddevice → speakers
  
The echo guard ensures the assistant never hears its own voice echo back.
```