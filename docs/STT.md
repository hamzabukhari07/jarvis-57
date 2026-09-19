# JARVIS — STT (Speech-to-Text)

## Answer: JARVIS Does NOT Use a Separate STT Model

> **JARVIS does not use a separately hosted STT model. Speech recognition is handled entirely through the Gemini Live API.**

This is verified by tracing the audio pipeline in `main.py`. The microphone audio is streamed directly to the Gemini Live session, which performs speech-to-text internally as part of the Live connection. No separate Whisper, Vosk, or other STT model processes the audio for the main conversation.

## How Speech Recognition Actually Works

### The Pipeline

```
User speaks
    ↓
Microphone (sounddevice.InputStream, 16kHz, mono, int16)
    ↓
Audio callback (1024 frames per chunk)
    ↓
callback() in _listen_audio()
    ↓
Wake word gate (if sleeping → audio goes to detector only)
    ↓
Echo guard (if speaking → filter out own echo)
    ↓
Push-to-talk gate (if enabled → only when chord held)
    ↓
Audio bytes → out_queue
    ↓
_send_realtime() → session.send_realtime_input(audio=...)
    ↓
Gemini Live API (WebSocket)
    ↓
Gemini performs STT internally
    ↓
session.receive() → server_content.output_transcription.text
```

### Key Files

| File | Function |
|------|----------|
| `main.py:1296-1400` | `_listen_audio()` — microphone callback, audio gating |
| `main.py:1281-1294` | `_send_realtime()` — streams audio to Gemini |
| `main.py` (receive loop) | `session.receive()` — receives transcripts and audio |

### The Gemini Live Audio Transcription

Gemini Live uses `input_audio_transcription={}` and `output_audio_transcription={}` in the connection config:

```python
cfg = dict(
    response_modalities=["AUDIO"],
    output_audio_transcription={},
    input_audio_transcription={},
    ...
)
```

This tells Gemini Live to:
1. **Transcribe input audio** (the microphone stream) — done internally by Gemini
2. **Output audio transcription** — the model's own text of what it hears
3. **Return audio** — the TTS output alongside the text

### Wake Word Detection (Separate Audio Path)

**File:** `core/wake_word.py`

When the assistant is **asleep** (wake word is enabled but not active), the microphone audio takes a *separate* path:

```
Microphone callback
    ↓
self._wake_enabled and not self._awake → True
    ↓
det.feed(indata)  →  WakeWordDetector.feed()
    ↓
Queue push (non-blocking, ~0 cost)
    ↓
WakeWordDetector._loop() (own background thread)
    ↓
openwakeword Model.predict(np.int16 array)
    ↓
Scores → "Hey Jarvis" detection (threshold: 0.5)
    ↓
Detection → _on_wake_detected() → wake()
```

**This is the ONLY place where a separate speech recognition model (openwakeword) is used.** It only listens for the wake phrase "Hey Jarvis" and never processes general speech.

## The STT Models That Exist in the Codebase

While not used in the main pipeline, `core/stt.py` contains **two STT engine classes** that exist for potential offline use:

### WhisperSTT (`core/stt.py:11-70`)

```python
class WhisperSTT:
    def __init__(self, model_name="base", language=None):
        from faster_whisper import WhisperModel
        # Loads faster-whisper model (cuda/CPU, float16/int8)
    
    def transcribe(self, audio: np.ndarray) -> str:
        # Uses VAD filter, beam_size=1, condition_on_previous_text=False
```

**Status:** Not used in the main audio pipeline. This is a fallback/optional feature for offline transcription.

### VoskSTT (`core/stt.py:73-93`)

```python
class VoskSTT:
    def process_chunk(self, audio_bytes: bytes) -> tuple[str, bool]:
        # Streaming Vosk recognition
        # Returns (text, is_final)
```

**Status:** Not used in the main audio pipeline. Another optional offline engine.

## Audio Format Details

| Parameter | Value | Source |
|-----------|-------|--------|
| Sample rate (input) | 16000 Hz | `main.py:SEND_SAMPLE_RATE` |
| Sample rate (output) | 24000 Hz | `main.py:RECEIVE_SAMPLE_RATE` |
| Channels | 1 (mono) | `main.py:CHANNELS` |
| Sample width | 16-bit int | `main.py:dtype="int16"` |
| Chunk size | 1024 frames | `main.py:CHUNK_SIZE` |
| Format | PCM | `audio/pcm` MIME type |
| Buffer | 2.0s of silence for probe | `core/audio_devices.py` |

## Microphone Initialization

**File:** `main.py`, `_listen_audio()` (line 1296)

```python
def _open_mic(dev):
    return sd.InputStream(
        samplerate=SEND_SAMPLE_RATE,  # 16000
        channels=CHANNELS,              # 1
        dtype="int16",
        blocksize=CHUNK_SIZE,           # 1024
        device=dev,
        callback=callback,
    )
```

Device resolution via `audio_devices.resolve(_mic_name, "input")` — resolves device **name** to sounddevice index.

## Audio Processing Chain

### In the Callback (real-time thread)

```python
def callback(indata, frames, time_info, status):
    # 1. Wake word gate
    if self._wake_enabled and not self._awake:
        det.feed(indata)  # queue push only
        return
    
    # 2. Speaking lock
    with self._speaking_lock:
        jarvis_speaking = self._is_speaking
    
    # 3. Barge-in (while JARVIS speaking, don't stream)
    if jarvis_speaking:
        return
    
    # 4. Echo tail guard
    if self._tail_active():
        if not self._echo.is_user_speech(indata, SEND_SAMPLE_RATE, _pcm_level(indata)):
            return  # this is our own echo
    
    # 5. Push-to-talk gate
    if self._ptt_enabled and not self._ptt_held:
        return
    
    # 6. Stream to Gemini
    data = indata.tobytes()
    loop.call_soon_threadsafe(self.out_queue.put_nowait,
        {"data": data, "mime_type": "audio/pcm"})
```

### Deduplication

**File:** `main.py:_is_repeat_chunk()` (line 307)

```python
def _is_repeat_chunk(txt: str, buf: list) -> bool:
    if len(txt) < _REPEAT_MIN:  # 12 chars
        return bool(buf) and txt == buf[-1]
    joined = " ".join(buf)
    return txt in joined
```

Guards against the Live API re-sending the tail of a transcript across the several `turn_complete` events a tool-using turn produces.

## VAD (Voice Activity Detection)

- **No separate VAD** for the main pipeline — Gemini Live handles it internally
- The **wake word** detector uses its own internal VAD via openwakeword
- The `sounddevice` callback triggers on every audio block; the system decides whether to stream based on state gates (wake, speaking, echo, PTT)
- Silence detection for the waveform display uses `_pcm_level()` with `_LEVEL_FLOOR = 60.0` and `_LEVEL_FULL = 2600.0`

## Summary

```
VERIFIED: JARVIS uses Gemini Live API for all speech-to-text.

There is no separate STT model running for the main conversation.
The audio goes directly from the microphone to Gemini Live, which
handles transcription internally. The only separate speech model
is openwakeword for "Hey Jarvis" detection.

core/stt.py contains WhisperSTT and VoskSTT classes but they are
NOT imported or called anywhere in the main pipeline.
```