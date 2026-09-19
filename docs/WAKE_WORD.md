# JARVIS — Wake Word System

## Overview

JARVIS supports a **local, offline wake-word detection** system using the phrase **"Hey Jarvis"**. The wake word system is **opt-in** and must be explicitly enabled by the user.

## Implementation Details

### Wake Word Model

**File:** `core/wake_word.py`

| Parameter | Value |
|-----------|-------|
| Wake phrase | "Hey Jarvis" |
| Model | `hey_jarvis` (openwakeword ONNX) |
| Framework | ONNX inference |
| Library | `openwakeword` |
| Threshold | 0.5 (score in [0,1]) |
| Sample rate | 16000 Hz |
| Input format | int16 mono |

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Mic Callback (real-time audio thread)               │
│                                                     │
│ if wake_enabled and not awake:                      │
│   det.feed(indata)  ← queue push only              │
│   return  ← nothing goes to Gemini                 │
│                                                     │
│ if awake:                                           │
│   normal streaming to Gemini                       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ WakeWordDetector._loop() (background thread)        │
│                                                     │
│   frame = queue.get()  ← blocks until data available│
│   scores = model.predict(np.int16(frame))           │
│   if max_score >= 0.5:                              │
│     _drain()  ← clear queue backlog                │
│     on_detect()  → wake()                          │
└─────────────────────────────────────────────────────┘
```

### Key Design Goals

1. **Zero cost when off** — `openwakeword` is imported ONLY inside `start()` and `install()`, never at module load. If the feature is disabled, none of this code runs.
2. **Zero latency on audio path** — the mic callback only does a cheap queue push (`put_nowait`). The actual model inference runs in a separate background thread.
3. **Fully local & offline** — audio never leaves the machine. No network call except the one-time model download.

### State Machine

```
ASSUMING ASLEEP (default when wake word enabled)
    ↓
User says "Hey Jarvis"
    ↓
WakeWordDetector._loop() detects score >= 0.5
    ↓
_drain() clears any backlog in queue
    ↓
on_detect() → self.wake(reason="wake word")
    ↓
WAKE STATE
    ↓
self._awake = True
self._last_user_speech = time.monotonic()
self.ui.set_state("LISTENING")
    ↓
Microphone now streams to Gemini
    ↓
Auto-sleep after 120s of silence
    ↓
SLEEP STATE (back to start)
```

### UI Integration

**File:** `main.py`, `JarvisLive.__init__()`

```python
self.ui.wake_is_ready    = wake_is_ready          # () -> bool
self.ui.wake_get_state   = self._wake_state        # () -> dict
self.ui.on_wake_toggle   = self._ui_wake_toggle    # (enable: bool) -> str
self.ui.on_wake_manual   = self._ui_wake_manual    # () -> toggle
self.ui.on_wake_install  = self._ui_wake_install   # () -> (ok, msg)
```

**Wake state dict:**
```python
{"enabled": bool, "awake": bool, "ready": bool}
```

### Ready Check

```python
def is_ready() -> bool:
    """Cheap file existence check — NOT model construction."""
    # Check if openwakeword package exists
    # Check if model files (.onnx, .tflite) exist in resources/models/
    # Returns True only if ALL three model files present:
    #   hey_jarvis*.onnx
    #   melspectrogram*.onnx
    #   embedding_model*.onnx
```

**Why file existence, not model construction?** Constructing a `Model` object is slow and can clash with an already-running detector, causing intermittent failures. The file check is fast and deterministic.

### Installation

```python
def install_and_download() -> tuple[bool, str]:
    # 1. pip install openwakeword
    # 2. openwakeword.utils.download_models(["hey_jarvis"])
    # 3. Verify is_ready()
    # Returns (ok, message)
```

### Sleep/Auto-Sleep

```python
async def _run_sleep_watch():
    """Auto-sleep after 2 minutes of silence."""
    while True:
        await asyncio.sleep(5)
        if not self._wake_enabled or not self._awake:
            continue
        if self._is_speaking:
            continue
        if (time.monotonic() - self._last_user_speech) > 120.0:
            self.sleep(reason="no speech for 2 minutes")
```

### Interaction with Push-to-Talk

When push-to-talk is enabled, holding Ctrl+Space also **wakes** the assistant:

```python
def _on_ptt(self, held: bool) -> None:
    if held:
        if self._wake_enabled and not self._awake:
            self._awake = True  # Wake up!
            self._last_user_speech = time.monotonic()
```

This means push-to-talk doubles as a silent alternative to saying the wake word.

### Interaction with Gemini

When sleeping:
- Audio **never** goes to Gemini
- Nothing leaves the machine
- Only the local detector processes audio
- When the wake word is detected: `wake()` sets `_awake = True`

### What Happens When Asleep

```
Mic callback fires
    ↓
self._wake_enabled and not self._awake → True
    ↓
det.feed(indata)  ← queue push (~0ms)
    ↓
return  ← nothing streamed to Gemini
```

**No network traffic, no AI processing, no audio leaves the machine.** The only cost is a numpy array copy and a queue push.

## Summary

```
Wake word: "Hey Jarvis"
Model: openwakeword (hey_jarvis ONNX)
Detection: Local, offline, ONNX inference
Threshold: 0.5
Auto-sleep: 120 seconds of silence
Opt-in: Requires explicit enable in settings
Push-to-talk integration: Holding Ctrl+Space also wakes
Cost when off: Zero
Cost when on: Queue push only in audio thread; model inference in background thread
```