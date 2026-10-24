# 🔊 ZEZO — Audio System Architecture

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux  
> **Core Engineering Rule (AGENTS.md Rule 6):** Audio and voice pipeline code is hardware-dependent and finely calibrated. The active conversational voice pipeline runs strictly via Google Gemini Live API (`main.py` bidirectional WebSockets PCM audio streaming).

---

## 🧭 Overview

ZEZO utilizes **sounddevice** (Python bindings for PortAudio) for all low-latency hardware audio I/O. The audio system handles microphone capture, speaker playback, real-time PCM resampling, dynamic hardware device discovery, and live viseme analysis for the WebGL avatar.

---

## 📦 Core Audio Libraries

| Library | Package | Purpose |
|---|---|---|
| `sounddevice` | `sounddevice>=0.4` | Low-latency audio I/O (PortAudio bindings) |
| `numpy` | `numpy>=1.24` | Audio buffer processing, FFT analysis, RMS volume computation |

Direct PyAudio or raw PortAudio C bindings are strictly avoided in favor of `sounddevice`'s callback-based non-blocking streaming API.

---

## 🎚️ Audio Stream Specifications

| Parameter | Input Stream (Microphone) | Output Stream (Speakers) |
|---|---|---|
| **Sample Rate** | 16,000 Hz (`SEND_SAMPLE_RATE`) | 24,000 Hz (`RECEIVE_SAMPLE_RATE`) |
| **Channels** | 1 (Mono) | 1 (Mono) |
| **Sample Format** | 16-bit Signed Integer (`int16` PCM) | 16-bit Signed Integer (`int16` PCM) |
| **Block Size** | 1024 frames (`CHUNK_SIZE`) | Dynamic unbuffered (`blocksize=0`) |
| **Chunk Latency** | ~64 ms per callback | Immediate streaming output |
| **MIME Type** | `audio/pcm;rate=16000` | Native 24kHz PCM |

---

## 🎤 Microphone Pipeline (`main.py::_listen_audio`)

Microphone capture runs inside `_listen_audio()` via a dedicated PortAudio callback thread:

```python
sd.InputStream(
    samplerate=SEND_SAMPLE_RATE,    # 16000 Hz
    channels=1,                     # Mono
    dtype="int16",                  # 16-bit PCM
    blocksize=CHUNK_SIZE,           # 1024 frames
    device=mic_dev,                 # Resolved device index
    callback=callback,              # Real-time audio callback
)
```

### Hardware Resampling Fallback
If a specialized microphone (e.g. WDM-KS 48000Hz stereo USB array) fails to open at native 16kHz mono, `_open_mic` catches the exception and dynamically opens the device at its native sample rate and channel count, resampling on the fly using stride slicing (`mono[::step]`) down to 16kHz mono before enqueueing.

### Explicit Sample Rate Rule (AGENTS.md Rule 6)
When streaming mic PCM audio to Google Gemini Live over WebSocket, ZEZO strictly includes the explicit sample rate in the MIME type:
```python
await self.session.send_realtime_input(
    audio=types.Blob(
        data=msg["data"],
        mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
    )
)
```
Sending bare `audio/pcm` without the sample rate parameter is strictly prohibited.

---

## 🔊 Speaker Pipeline (`main.py::_play_audio`)

Output streaming runs inside `_play_audio()` using `sd.RawOutputStream`:

```python
sd.RawOutputStream(
    samplerate=RECEIVE_SAMPLE_RATE,  # 24000 Hz
    channels=1,                      # Mono
    dtype="int16",
    blocksize=0,                     # Zero blocksize allows unbuffered push
    device=output_dev,
)
```

- **Playback Cursor Tracking**: `_play_cursor` tracks the exact wall-clock horizon of the audio hardware buffer to synchronize WebGL 3D avatar mouth visemes (`VisemeStream.frames()`) with actual acoustic emission.
- **Echo Tail Calibration**: `_play_audio` dynamically sizes the echo cancellation tail guard based on reported device buffer latency (`stream.latency` + `_TAIL_MARGIN = 0.06s`), ensuring the microphone never picks up ZEZO's own voice.

---

## 🛡️ Audio Hardware Disconnect & Resilience Strategy

Per **AGENTS.md Rule 6**, audio device errors must **never crash the live session**:

1. **Microphone Unplugged / Missing**:
   - `audio_devices.resolve(saved_name, "input")` returns `None` if a previously saved device is disconnected.
   - The system falls back automatically to the system default microphone.
   - If no microphone is found or permission is denied:
     ```python
     if _mic_stream is None:
         print("[Zezo] ⚠️ No working microphone found or permission denied — running in silent/text mode (UI, Text, and Remote ready).")
         self.ui.write_log("SYS: Microphone unavailable — running in text/remote mode.")
         while True:
             await asyncio.sleep(2.0)
     ```
   - The worker task remains alive in an idle loop, keeping the `TaskGroup` running so the text chat, React UI, and Cloudflare remote tunnel remain fully functional.

2. **Speakers Unplugged / Missing**:
   - If output device initialization fails, `_play_audio` logs an alert to the HUD and falls back to visual/text mode without throwing an unhandled exception.

---

## 🎛️ Audio Device Management (`core/audio_devices.py`)

- **Name-Based Resolution**: Device indices change when USB peripherals are connected or disconnected. ZEZO persists friendly device names in `config/api_keys.json` (`input_device`, `output_device`) and dynamically resolves them at runtime via `audio_devices.resolve(name, kind)`.
- **Auto-Follow Active Default**: When `input_device` or `output_device` is empty (`""`), ZEZO automatically uses the current operating system default device (`resolve() returns None`).
- **Live Settings UI**: The ReUI Settings Hub (`Audio & Devices`) provides:
  - Dynamic device dropdowns populated by `audio_devices.list_devices()`.
  - Live interactive microphone volume test meter (`ui.set_mic_level`).
  - Speaker playback test tone verification.
  - Seamless live session reconnection upon saving device selections (`request_reconnect(keep_context=True)`).
