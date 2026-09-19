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

## Latency Management

| Source | Latency | Mitigation |
|--------|---------|------------|
| Sound device buffer | ~43ms (1024 frames @ 24kHz) | Playback cursor tracks actual sound time |
| Gemini Live processing | ~200-500ms | Proactive audio: say something while waiting |
| Network round-trip | ~50-200ms | WebSocket, low-latency connection |
| Viseme processing | ~20ms per frame | 20ms step matches audio chunk |
| Echo tail | ~475ms | Measured from device latency + margin |

## Audio File References

| File | Purpose |
|------|---------|
| `core/audio_devices.py` | Device enumeration, filtering, measurement, resolution |
| `main.py` (constants) | Sample rates, chunk sizes, channel config |
| `main.py` (_listen_audio) | Mic input callback, gating, streaming |
| `main.py` (_play_audio) | Speaker output, playback cursor |
| `main.py` (_pcm_level) | RMS loudness for waveform display |
| `main.py` (_pcm_visemes) | FFT-based formant analysis for lip-sync |
| `core/echo.py` | Self-echo detection and cancellation |
| `core/viseme.py` | Transcript-based mouth shape fusion |