# JARVIS — Audio System

## Overview

JARVIS uses **sounddevice** (Python bindings for PortAudio) for all audio I/O. The audio system handles microphone input, speaker output, device selection, and audio analysis.

## Audio Library

| Library | Package | Version | Purpose |
|---------|---------|---------|---------|
| `sounddevice` | `sounddevice>=0.4,<1` | All platforms | Audio I/O (PortAudio bindings) |
| `numpy` | `numpy>=1.24,<3` | All platforms | Audio processing, FFT, viseme analysis |

**No PortAudio/PyAudio direct usage** — sounddevice wraps PortAudio and provides the callback-based streaming API.

## Audio Parameters

| Parameter | Input (Mic) | Output (Speakers) |
|-----------|-------------|-------------------|
| Sample rate | 16000 Hz | 24000 Hz |
| Channels | 1 (mono) | 1 (mono) |
| Sample format | int16 | int16 |
| Block size | 1024 frames | 1024 frames |
| Duration per chunk | ~64ms | ~43ms |

## Microphone Initialization

**File:** `main.py`, `_listen_audio()` (line 1296)

```python
sd.InputStream(
    samplerate=16000,       # SEND_SAMPLE_RATE
    channels=1,             # CHANNELS
    dtype="int16",          # 16-bit PCM
    blocksize=1024,         # CHUNK_SIZE
    device=mic_dev,         # resolved by name
    callback=callback,      # real-time audio callback
)
```

## Speaker Initialization

**File:** `main.py` — output stream within the `_play_audio()` function

```python
sd.RawOutputStream(
    samplerate=24000,       # RECEIVE_SAMPLE_RATE
    channels=1,             # CHANNELS
    dtype="int16",
    blocksize=1024,         # CHUNK_SIZE
    device=output_dev,      # resolved by name
)
```

**Key difference:** Input uses `InputStream` (callback mode), output uses `RawOutputStream` (write mode). The output stream uses `stream.write()` which blocks until the buffer accepts the audio.

## Device Selection

### How Devices Are Discovered

**File:** `core/audio_devices.py`

```python
def _query() -> dict[str, list[str]]:
    devices = list(sd.query_devices())
    # Filter: non-pseudo, has channels, opens at correct rate
    # Measure: _transport_works() tests if audio actually moves
    # Deduplicate by name
    # One host API per direction
```

### Why Names, Not Indices

Device indices shift when hardware changes. The system stores **device names** and resolves them at open time:

```python
def resolve(name: str, kind: str):
    # Returns sounddevice device index, or None for "system default"
    # Falls back to system default if saved device is gone
```

### AUDIO I/O Panel (Settings UI)

**Files:** `frontend/index.html` (panel + JS), `core/ui_server.py` (state + WS), `ui.py` (reconnect wiring)

The **Settings → Audio Devices** panel is live, not static:

- `core/ui_server._collect_audio_state()` reports the saved device names, the devices the app can actually open at 16 kHz / 24 kHz (`audio_devices.list_devices`), and `input_available` / `output_available`.
- `input_available: false` means the saved device could **not** be opened, so the app is using the system default. The panel shows an inline warning instead of pretending the saved endpoint is in use.
- The panel sends `get_audio_devices` when opened and `save_audio_devices` on **APPLY & RECONNECT**. The server persists via `save_input_device()` / `save_output_device()`, then calls `on_audio_devices_changed`.
- `ui.py` maps that to the existing `on_audio_device_change` callback, which `main.py` handles by rebuilding the session (`request_reconnect(keep_context=True)`) — the new device takes effect without losing the conversation.

**Auto-follow the active device (default behaviour):** `input_device` / `output_device` are **empty by default**, which means "use whatever the OS currently calls the default" (`resolve()` returns `None` → the stream opens on `device=None`). At startup `main.py` checks any saved name with `audio_devices.resolve()`; if it is gone or cannot open at 16/24 kHz it is **cleared to `""`** so the active default is used automatically — the user does not have to re-pick after unplugging/plugging hardware. Picking a working device in the panel pins it again. The panel shows the active default in the first option (`System default — <device name>`) so it is clear which mic/speaker is really in use.

**Live microphone meter:** the panel shows a live level bar + `MIC: hearing you / no signal` text. `main.py` calls `ui.set_mic_level()` from the sounddevice callback with the **raw** level (computed before any gate), and `ZezoUI.set_mic_level` throttles and broadcasts `mic_level` (~12 Hz). `set_mic_level` is deliberately separate from `set_audio_level` (which the playback path uses for the output waveform) so ZEZO's own voice can never appear as "microphone".

**Mic-path diagnostic (used, then removed):** during the latency investigation `_listen_audio` logged a per-2 s `[MicDiag] rx=<frames> sent=<forwarded> peak=<0..1> | asleep=… speaking=… tail=… ptt=… muted=…` line. It proved the microphone delivered frames (`rx=32` every window) while the echo tail was permanently active (`tail ≈ rx`), which located the bug. The instrument was removed once the tail fix was confirmed end-to-end; the live mic meter above remains.

**Echo tail must be armed on the transition only.** `set_speaking(False)` arms the ~273 ms echo tail **only when it was actually speaking** (`was_speaking`). The idle playback loop calls `set_speaking(False)` every ~200 ms; arming on every one of those polls made the tail outlast the poll interval, so it was permanently active and the microphone spent every block in the "our own voice" guard — dropping the user's quieter speech and fragmenting each spoken turn. Regression test: `scratch/verify_speaking_tail.py`.

### Host API Selection

**File:** `core/audio_devices.py`

Each direction picks its own host API:
- **Windows input**: DirectSound
- **Windows output**: MME
- **macOS**: Core Audio (only option)
- **Linux**: PulseAudio/PipeWire

The selection is based on **measurement**, not reasoning:
1. Try preferred APIs in order
2. For each, probe with real audio
3. Measure if audio actually moves (not just opens)
4. Select the first that passes

### The Measurement Problem

The codebase discovered through measurement:
- **DirectSound output** is a silent sink — `stream.write()` returns success but no audio moves
- **MME input** works perfectly but was rejected by an earlier probe using the wrong stream mode
- **WASAPI shared mode** doesn't resample — 16kHz in, 24kHz out against 48kHz hardware fails

The probe runs **in the mode the app actually ships** — DirectSound input passes a callback stream, not a blocking read.

## Audio Callback Architecture

### Input Callback (microphone → Gemini)

```python
def callback(indata, frames, time_info, status):
    # Runs on sounddevice thread
    # 1. Wake word gate (if sleeping)
    # 2. Speaking lock check
    # 3. Echo tail guard
    # 4. Push-to-talk gate
    # 5. Convert to bytes, put in out_queue
    # 6. Update HUD waveform level
```

**Thread safety:** `loop.call_soon_threadsafe()` is used to push to the asyncio queue from the sounddevice thread.

**Bounded queue + drop-oldest (2026-09-26):** `out_queue` is `asyncio.Queue(maxsize=200)`. The callback schedules `ZezoLive._enqueue_out_audio` (not a raw `put_nowait`), which catches `asyncio.QueueFull`, discards the stalest blob, and re-inserts the newest. Without this guard, a lagging `_send_realtime` (e.g. mid-reconnect) made every mic block raise `QueueFull` inside the `call_soon_threadsafe` callback, and asyncio logged `Exception in callback Queue.put_nowait()` thousands of times, flooding the log bus. Dropping oldest keeps the model on the most recent speech and turns a stuck queue into silent back-pressure instead of an error storm.

### Output Stream

```python
# Audio bytes are written to the output stream
# stream.write() blocks until buffer accepts
# The write returns when the buffer accepts, NOT when the speaker finishes
```

This is the key reason for the **echo tail guard** — sound returns when the buffer accepts, not when the room finishes with it.

## Audio Level Analysis

### RMS Level Calculation

```python
def _pcm_level(samples) -> float:
    x = np.asarray(samples, dtype=np.float32)
    rms = float(np.sqrt(np.mean(x * x)))
    if rms <= _LEVEL_FLOOR:    # 60.0
        return 0.0
    return min(1.0, (rms - _LEVEL_FLOOR) / (_LEVEL_FULL - _LEVEL_FLOOR))  # _LEVEL_FULL = 2600.0
```

### Viseme Formant Analysis

```python
def _pcm_visemes(samples, sr=24000):
    # FFT on 1024-sample windows, 480-sample hop (20ms)
    # Band energies for formant tracking:
    #   F1_lo (150-450 Hz), F1_hi (450-1100 Hz)
    #   F2_back (600-1300 Hz), F2_front (1700-3200 Hz)
    #   Hiss (3800-8000 Hz)
    # openness = f1h / (f1l + f1h)
    # width = (f2f - f2b) / (f2f + f2b)
    # fricatives dampen openness
```

**Produces:** 50 mouth shapes per second from audio alone (formant-based).

## Echo Handling

**File:** `core/echo.py` — `EchoGuard` class

The echo guard operates on **band energies**, not raw levels:

```
Band edges: [200, 400, 700, 1100, 1700, 2600, 3800, 5200, 7000] Hz
9 bands total
```

**Algorithm:**
1. Record recent audio output as band energy fingerprints
2. For each mic block, find the output slice that best explains it
3. Subtract as much as fits → residual is whatever was NOT our own voice
4. If residual is significant → it's a user voice
5. Learn the echo gain over time for calibration

**Key properties:**
- Sample-rate agnostic (works across 16kHz mic / 24kHz speakers)
- Self-calibrating within seconds
- Never mutes the microphone — only drops echo blocks
- Adaptive threshold based on room acoustics

## Silence Detection

```python
# _pcm_level() returns 0.0 for RMS <= _LEVEL_FLOOR (60.0)
# This is used for:
# - Waveform display (no bar when silent)
# - Auto-sleep detection (no user speech)
# - Viseme frames (silence → REST mouth shape)
```

## Platform-Specific Audio Behavior

### Windows
- **Host APIs**: DirectSound (input), MME (output)
- **Device enumeration**: 41 entries from `sd.query_devices()` → filtered to ~8 usable
- **Volume control**: `pycaw` library
- **Special behaviors**: Default device moves when headset plugged in

### macOS
- **Host API**: Core Audio (only)
- **Volume control**: `osascript` (AppleScript)
- **Device enumeration**: Clean — one entry per device

### Linux
- **Host APIs**: PulseAudio/PipeWire/ALSA/Jack
- **Volume control**: `pactl`
- **Device enumeration**: Clean with PulseAudio

## Audio Synchronization

### The Playback Cursor Problem

```python
self._play_cursor = 0.0  # wall-clock time when next audio begins to sound
```

The mouth is scheduled against `_play_cursor`, not "now":
- Batches are handed to the device faster than they play
- The cursor advances by the audio duration at 24kHz
- The viseme timing uses this cursor to match mouth shapes to when audio actually sounds

**Timing error**: Measured at 15ms whether the sound card buffers 100ms or 500ms.

### Audio Queue Architecture

```
Mic callback → out_queue → _send_realtime() → WebSocket
                                                     ↓
Mic callback → set_audio_level() → HUD waveform (cosmetic)
                                                     ↓
Speaker output: sounddevice.OutputStream ← audio bytes from session.receive()
```

## Cascade / Offline Audio Architecture

When running in **Cascade Mode** or during **Voice Fallback**:

```
Microphone (sounddevice.InputStream 16kHz)
    ↓
Non-blocking streaming loop (core/voice_fallback.py)
    ↓
[During Assistant Speech] ── RMS >= energy * 1.4 ──► sounddevice.stop() (Instant Barge-in <20ms)
    ↓                                                 ↓
UtteranceSegmenter (180ms pause detection)     _interrupted.set() (Cancels LLM & TTS)
    ↓
Background Utterance Worker Thread ──► STT ──► Fast Intent / Streaming LLM ──► TTS
```

- **Non-blocking Input Stream:** The mic stream reads 512-frame chunks (~32ms) continuously on a dedicated thread, preventing audio buffer starvation or lost frames while TTS is active.
- **Instant Barge-In Stop:** When speech energy exceeds the acoustic threshold during playback, `sounddevice.stop()` halts speaker output in `<20ms` and signals cancellation across all active pipeline stages.

## Latency Management & Low-Latency Turn Tuning

| Mode / Source | Latency | Mitigation / Configuration |
|---------------|---------|----------------------------|
| Live Server-side VAD | ~450ms | `turn_tuning.silence_ms = 450`, `end_sensitivity = "high"` |
| Cascade VAD Pause | ~180ms | `DEFAULT_SILENCE_MS = 180`, `DEFAULT_MIN_MS = 200` |
| Cascade TTFA (First Sentence) | ~150-250ms | `call_groq_stream` sentence-level token accumulation + concurrent TTS |
| Cascade Fast Intent | 0ms | `_try_fast_intent` deterministic device command bypass |
| Sound device buffer | ~43ms (1024 frames @ 24kHz) | Playback cursor tracks actual sound time |
| Network round-trip | ~50-200ms | Real-time WebSocket connection / Groq Cloud endpoint |
| Viseme processing | ~20ms per frame | 20ms step matches audio chunk |
| Echo tail guard | ~270ms | Device latency + `_TAIL_MARGIN` (0.06s), instant break on speech level > 0.08 |
| Proactive Audio | Disabled (`false`) | Prevents classifier hesitation or dropped turns on multilingual speech |

## Audio File References

| File | Purpose |
|------|---------|
| `core/audio_devices.py` | Device enumeration, filtering, measurement, resolution |
| `frontend/index.html` | AUDIO I/O panel markup + live device dropdowns |
| `core/ui_server.py` | `_collect_audio_state`, `get_audio_devices` / `save_audio_devices` |
| `ui.py` | `_handle_audio_devices_changed` → session reconnect |
| `ui.py` (`set_mic_level`) | Raw mic level → `mic_level` broadcast for the panel meter |
| `main.py` (constants) | Sample rates, chunk sizes, channel config |
| `main.py` (_listen_audio) | Mic input callback, gating, streaming |
| `main.py` (_play_audio) | Speaker output, playback cursor |
| `main.py` (_pcm_level) | RMS loudness for waveform display |
| `main.py` (_pcm_visemes) | FFT-based formant analysis for lip-sync |
| `core/echo.py` | Self-echo detection and cancellation |
| `core/viseme.py` | Transcript-based mouth shape fusion |