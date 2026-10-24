# ZEZO — Wake Word System

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux  

## Overview

ZEZO supports **local, offline wake-word detection**. The wake phrase is
**`"Hey <assistant name>"`** — the assistant name selected in
⚙ → **Assistant Persona**. The system is **opt-in** and must be enabled in
⚙ → **General & Controls**.

- Default assistant name: **Zezo** → wake phrase **"Hey Zezo"**.
- Selecting **Nova** → wake phrase **"Hey Nova"**.
- Selecting **Jarvis** → wake phrase **"Hey Jarvis"**.

The assistant name is the **single source of truth**: it drives both the
conversational identity and the wake phrase.

## Implementation

**File:** `core/wake_word.py`

| Parameter | Value |
|-----------|-------|
| Wake phrase | `"Hey " + <assistant name>` |
| Engine | `openwakeword` (ONNX, offline) |
| Threshold | 0.6 (score in [0,1]) |
| Debounce / cooldown | 1.5 s debounce + 1.5 s cooldown after a hit |
| Sample rate | 16000 Hz, int16 mono |
| Model source | `config/wakewords/<model>.onnx` first, then packaged openwakeword |

### Preset registry

`WAKE_PRESETS` in `core/wake_word.py` maps assistant names → wake models. One
list drives **both** the Persona dropdown and the detector:

```python
WAKE_PRESETS = [
    {"id": "zezo",   "name": "Zezo",   "model": "hey_zezo"},
    {"id": "nova",   "name": "Nova",   "model": "hey_nova"},
    {"id": "jarvis", "name": "Jarvis", "model": "hey_jarvis"},
]
```

Helper functions:

| Function | Purpose |
|----------|---------|
| `list_wake_presets()` | Presets + any extra `config/wakewords/*.onnx` for the UI |
| `model_for_name(name)` | Resolve a name → model id (falls back to a resolvable default) |
| `phrase_for_name(name)` | `"Nova"` → `"Hey Nova"` |
| `resolve_model(id)` | Local `.onnx` path first, else packaged model |
| `default_wake_model()` | `hey_zezo` if shipped, else `hey_jarvis` |
| `is_ready(model_id)` | Model + shared mel/embedding files present |

### Architecture

```
Mic callback (real-time audio thread)          core/wake_word.WakeWordDetector
─────────────────────────────────────          ───────────────────────────────
if wake_enabled and not awake:                 _loop() (background thread):
    det.feed(indata)   ← queue push only           frame = queue.get()
    return             ← nothing to Gemini          scores = model.predict(frame)
                                                    score = scores[<loaded model>]
if awake:                                           if score >= 0.6:
    normal streaming to Gemini                        on_detect() → wake()
```

**Scoring is per-model:** only the loaded model's own key counts. There is no
cross-model fallback, so a swapped/renamed wake word can never fire on the
wrong model.

### Sleep / auto-sleep

When wake word is enabled the assistant boots **asleep**. It wakes on the wake
phrase (or push-to-talk / the UI wake button) and enters **LISTENING** with a
**15-second listen window** (`WAKE_LISTEN_WINDOW`). The window is a rolling
timer that **resets after each reply** — both when the user speaks
(`_last_user_speech`) and when ZEZO finishes speaking (`_last_speech_end`, set
on the real speaking → idle transition in `set_speaking`). This keeps
conversation mode alive as long as you keep talking back and forth. After
**15 s of silence** it auto-sleeps (`sleep(reason="no speech for 15s")`). While
asleep the mic is gated and **nothing is streamed to Gemini**.

`_run_sleep_watch` polls once per second and compares
`max(_last_user_speech, _last_speech_end)` against the window, so a reply always
buys another 15 s.

### Detection tuning

The detector is tuned to reduce false wakes:

- **Threshold `0.6`** (`DEFAULT_THRESHOLD`) — higher confidence required before
  a hit registers (was `0.5`).
- **1.5 s debounce** — passed to `Model.predict(..., debounce_time=1.5)`, so the
  model itself suppresses rapid repeat triggers.
- **1.5 s cooldown** — after a detection, re-triggers are ignored for 1.5 s
  (`_cooldown`) to stop a single utterance from firing the wake handler twice.

### Model sourcing

- `hey_jarvis` ships with the `openwakeword` package — works out of the box.
- `hey_zezo` / `hey_nova` are trained once with the openWakeWord Colab and
  dropped into `config/wakewords/` (see that folder's README).
- Any extra `config/wakewords/<name>.onnx` is auto-listed in the dropdown.

### Interaction with the assistant name

`main.py` derives the wake model + phrase from `get_assistant_name()`
(`memory/config_manager.py`). Changing the name in the Persona tab hot-swaps the
detector (no app restart) and rebuilds the session prompt:

```python
self._wake_model  = model_for_name(name)
self._wake_phrase = phrase_for_name(name)
```

## Configuration keys

| Key (`config/api_keys.json`) | Meaning |
|------------------------------|---------|
| `wake_word_enabled` | Master on/off for wake gating |
| `assistant_name` | Identity + wake phrase source (`"Zezo"`, `"Nova"`, …) |

## Summary

```
Wake phrase:  "Hey <assistant name>"      (default "Hey Zezo")
Engine:       openwakeword (local, offline, ONNX)
Selection:    Assistant Persona dropdown  → auto-sets the wake word
Threshold:    0.6   (1.5 s debounce + 1.5 s cooldown)
Auto-sleep:   15 s listen window of silence, reset after each reply
Opt-in:       Requires explicit enable in ⚙ → General & Controls
Cost when off: Zero.  Cost when on: a queue push per frame; inference in its own thread.
```
