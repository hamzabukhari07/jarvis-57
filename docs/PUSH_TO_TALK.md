# JARVIS — Push-to-Talk

## Overview

Push-to-talk allows the user to hold a key chord to open the microphone, instead of using the wake word. It is **opt-in** and can be toggled in the settings.

## Keyboard Shortcut

- **Default chord**: `Ctrl+Space`
- **Why Ctrl+Space**: Free in most desktop environments, same finger shape on every keyboard layout (worldwide app)

## Implementation

**File:** `core/hotkey.py` — `PushToTalk` class

### Platform-Specific Behavior

#### Windows: Global Push-to-Talk

```python
class PushToTalk:
    def start(self) -> str:
        if _OS == "Windows" and self._can_poll():
            self._scope = "global"
            self._thread = threading.Thread(
                target=self._poll_loop, name="push-to-talk", daemon=True)
```

**How it works:**
- Uses `ctypes.windll.user32.GetAsyncKeyState` — polls two virtual-key codes
- Polling rate: 30 Hz (every ~33ms)
- Debounce: 60ms (key must be held for 60ms before registering)
- **No message loop, no new dependency**
- **Truly global**: works while any other application has focus
- Virtual key codes: `VK_CTRL = 0x11`, `VK_SPACE = 0x20`

```python
def _poll_loop(self) -> None:
    import ctypes
    user32 = ctypes.windll.user32
    codes = [_VK[k] for k in self._chord]
    period = 1.0 / _POLL_HZ  # 0.033s
    while not self._stop.is_set():
        down = all(user32.GetAsyncKeyState(c) & 0x8000 for c in codes)
        if down:
            if now - down_since >= _DEBOUNCE_S:  # 0.06s
                self._set_held(True)
        else:
            down_since = 0.0
            self._set_held(False)
        self._stop.wait(period)
```

#### macOS / Linux: Window-Scoped Push-to-Talk

```python
def start(self) -> str:
    # No portable way to read global key state without a new package
    # or accessibility permissions
    self._scope = "window"
    # Qt shortcut handles the key press/release
```

**Limitation**: The chord only works while the assistant's window has focus. The app **honestly reports this** in the log.

### Scope Reporting

```python
def start(self) -> str:
    if _OS == "Windows" and self._can_poll():
        self._scope = "global"
    else:
        self._scope = "window"
    return self._scope
```

The scope is reported to the user via the log.

### State Transitions

```
Chord released
    ↓
_push_held = False
    ↓
ui.set_state("SLEEPING")  (if wake word is on)
```

```
Chord pressed (held for 60ms)
    ↓
_push_held = True
    ↓
ui.set_state("LISTENING")
    ↓
If wake word is on and assistant was asleep:
    self._awake = True  (wake up)
```

### Integration with Main Loop

**File:** `main.py`, `JarvisLive` class

```python
def set_push_to_talk(self, enabled: bool) -> str:
    """Turn hold-to-talk on or off."""
    self._ptt_enabled = bool(enabled)
    self._ptt_held = False
    if enabled:
        self._ptt = PushToTalk(self._on_ptt)
        scope = self._ptt.start()
    else:
        self._ptt.stop()
        self._ptt = None
    return scope

def _on_ptt(self, held: bool) -> None:
    """Called when chord pressed/released."""
    self._ptt_held = held
    if held and self._wake_enabled and not self._awake:
        self._awake = True  # also wakes from sleep
```

### Audio Gate Behavior

When push-to-talk is active:

```python
def callback(indata, frames, time_info, status):
    if self._ptt_enabled and not self._ptt_held:
        return  # BLOCK: audio never reaches Gemini
    # ... rest of processing
```

**The microphone is completely closed** when the chord is not held. Nothing leaves the machine.

### Configuration

| Setting | Key | Default | Source |
|---------|-----|---------|--------|
| Enabled | `push_to_talk_enabled` | `False` | `config/api_keys.json` |
| Scope | Reported at runtime | `"global"` or `"window"` | `PushToTalk.start()` |

### Thread Safety

The `_on_ptt` callback **may arrive on the hotkey thread** (Windows) or the Qt thread (macOS/Linux). The state is set atomically:

```python
def _set_held(self, held: bool) -> None:
    if held == self._held:
        return
    self._held = held
    try:
        self._on_change(held)
    except Exception:
        pass  # a listener fault must never kill the watcher
```

### Summary

```
Windows: Global, GetAsyncKeyState polling, 30Hz, no dependencies
macOS/Linux: Window-scoped, Qt shortcut, honest limitation reporting
Chord: Ctrl+Space (default), debounced at 60ms
Effect: Microphone opens only while held; also wakes from sleep
Thread: Dedicated polling thread (Windows), Qt thread (macOS/Linux)
```