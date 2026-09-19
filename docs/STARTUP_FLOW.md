# JARVIS — Startup Flow

## Entry Point

```
main.py
  ↓
main() function (top-level script)
  ↓
JarvisLive.__init__(ui)
  ↓
[Initialization sequence below]
```

The application has **no `if __name__ == "__main__":` block at the very bottom of main.py that calls a `main()` function explicitly** — rather, the top-level code in `main.py` executes directly when Python runs the file. The `JarvisLive` class constructor contains all initialization logic.

## Detailed Startup Sequence

### Step 1: Import and Patching (lines 1-35 of main.py)

```
main.py
  ↓
Windows subprocess patching (CREATE_NO_WINDOW on all Popen)
  ↓
Console UTF-8 reconfiguration (handles non-UTF-8 code pages)
  ↓
Import all modules
```

**File:** `main.py` (lines 1-35)
**What it does:**
- Patches `subprocess.Popen` to force `CREATE_NO_WINDOW` on Windows (prevents console windows from popping up for subprocess calls)
- Reconfigures stdout/stderr to UTF-8 with `errors="replace"` — prevents `UnicodeEncodeError` on legacy code pages (cp1254, cp1251, cp932)

### Step 2: Constants and Configuration (lines 87-109)

```
main.py
  ↓
LIVE_MODEL = "models/gemini-3.1-flash-live-preview"
  ↓
CHANNELS = 1, SEND_SAMPLE_RATE = 16000, RECEIVE_SAMPLE_RATE = 24000
  ↓
CHUNK_SIZE = 1024
  ↓
_LEVEL_FLOOR = 60.0, _LEVEL_FULL = 2600.0
```

**What it initializes:**
- **AI Model**: `models/gemini-3.1-flash-live-preview` — the Gemini Live model identifier
- **Audio parameters**: Mono, 16kHz input, 24kHz output, 1024-frame chunks
- **Level thresholds**: For waveform display and silence detection

### Step 3: Utility Functions Definition (lines 112-320)

Functions defined but not called until needed:
- `_pcm_level()` — maps PCM samples to 0.0-1.0 loudness
- `_pcm_visemes()` — FFT-based formant extraction for lip-sync (20ms frames, 50 shapes/sec)
- `_describe_tools()` — builds capabilities string from discovered tools
- `_describe_limits()` — builds limitations string for self-knowledge
- `_render_prompt()` — fills `{tokens}` in `core/prompt.txt`
- `_get_api_key()` — reads `config/api_keys.json`
- `_load_system_prompt()` — reads `core/prompt.txt`
- `_is_repeat_chunk()` — deduplication guard
- `_clean_transcript()` — strips control characters

### Step 4: TOOL_DECLARATIONS Definition (lines 323-489)

**File:** `main.py` lines 323-489

Inline tool declarations that are hardcoded in `main.py` because they interact with live-session state:
1. `system_status` — real-time system metrics
2. `screen_process` — screen/webcam capture for vision
3. `close_camera` — close camera stream
4. `manage_monitor` — background monitoring topics
5. `shutdown_jarvis` — end the session
6. `save_memory` — save to long-term memory
7. `recall_memory` — search long-term memory
8. `undo` — reverse last action

### Step 5: Helper Classes Definition

- `_ReconnectSignal` — exception for voluntary session rebuilds
- `_is_reconnect_signal()`, `_keep_context_of()` — reconnect signal detection

### Step 6: JarvisLive.__init__() — Main Initialization (lines 530-654)

This is the heart of startup. Every step below happens in order:

```
JarvisLive.__init__(ui)
  ↓
1. Store UI reference and set assistant name
  ↓
2. Initialize session state variables (session=None, queues=None)
  ↓
3. Initialize audio state (_is_speaking=False, _out_level=0.0)
  ↓
4. Initialize viseme system (VisemeStream())
  ↓
5. Initialize echo guard (EchoGuard())
  ↓
6. Initialize push-to-talk system (PushToTalk)
  ↓
7. Initialize wake word system (WakeWordDetector=None)
  ↓
8. Discover actions (core/action_loader.py)
  ↓
9. Discover plugins (core/plugin_loader.py)
  ↓
10. Initialize wake word detector (if enabled)
  ↓
11. Restore push-to-talk preference
  ↓
12. Set up UI callbacks
```

Let me trace each sub-step:

#### 6a. Action Discovery

```
main.py
  ↓
discover_actions(actions_dir=BASE_DIR / "actions", reserved_names=_inline_names)
  ↓
core/action_loader.py:discover_actions()
  ↓
For each *.py in actions/ (sorted):
    1. Skip files starting with "_"
    2. Import module via importlib.util
    3. Check for module-level TOOL dict
    4. Validate name, description, parameters, handler
    5. Check for name collisions with reserved names
    6. Create ActionRecord
  ↓
Returns ActionRegistry with valid actions
```

**Files:** `core/action_loader.py`
**Key validation:** Name must match `^[a-zA-Z_][a-zA-Z0-9_]{0,63}$`, must have TOOL dict with `name`, `description`, `parameters`, `handler`

#### 6b. Plugin Discovery

```
main.py
  ↓
discover_plugins(plugins_dir=BASE_DIR / "plugins", core_tool_names=_core_names)
  ↓
core/plugin_loader.py:discover_plugins()
  ↓
For each *.py in plugins/ (sorted):
    1. Skip files starting with "_"
    2. Import module via importlib.util
    3. Check for module-level PLUGIN dict
    4. Validate name, description, parameters, run()
    5. Check for name collisions with actions AND core tools
    6. Create PluginRecord
  ↓
Returns PluginRegistry with valid plugins
```

**Files:** `core/plugin_loader.py`
**Key validation:** Same naming rules as actions, plus collision check against action names

#### 6c. Wake Word Initialization

```
main.py
  ↓
get_wake_word_enabled() → config/api_keys.json
  ↓
If enabled: ensure WakeWordDetector created
  ↓
core/wake_word.py:WakeWordDetector.__init__()
  ↓
Model loads on first start (openwakeword Model)
  ↓
Background thread starts for inference
```

**Files:** `core/wake_word.py`
**Note:** The detector loads on first use, not at import time, so it costs nothing when wake word is off

#### 6d. Push-to-Talk Initialization

```
main.py
  ↓
get_push_to_talk_enabled() → config/api_keys.json
  ↓
If enabled: set_push_to_talk(True)
  ↓
core/hotkey.py:PushToTalk.__init__(on_change)
  ↓
PushToTalk.start()
  ↓
Windows: Global polling thread (GetAsyncKeyState, 30Hz)
  ↓
macOS/Linux: Window-scoped Qt shortcut
```

**Files:** `core/hotkey.py`

### Step 7: UI Initialization

```
main.py
  ↓
JarvisUI()  (in ui.py)
  ↓
PyQt6.QMainWindow setup
  ↓
HoloAvatar initialization
  ↓
Waveform rendering setup
  ↓
Settings drawer setup
  ↓
Activity log setup
  ↓
Content panel setup
  ↓
Show window
```

**File:** `ui.py` — `JarvisUI` class (5438 lines)

### Step 8: Event Loop Starts

After `JarvisLive` and `JarvisUI` are constructed, the application enters its main event loops:

1. **Qt event loop** — handles all UI rendering, user input, settings changes
2. **asyncio event loop** — manages Gemini Live WebSocket communication
3. **Background threads** — audio callbacks, wake word detection, TTS playback

```
main.py
  ↓
# Application runs in the Qt event loop + asyncio event loop
  ↓
Ready for user interaction
```

## Summary Flow Chart

```
Python starts main.py
    ↓
Patch subprocess, configure console
    ↓
Define constants and utility functions
    ↓
Define inline TOOL_DECLARATIONS
    ↓
Create JarvisLive(ui)
    ↓
  ├── Discover actions (core/action_loader)
  ├── Discover plugins (core/plugin_loader)
  ├── Initialize wake word (if enabled)
  ├── Initialize push-to-talk (if enabled)
  ├── Set up UI callbacks
  └── Create audio device cache
    ↓
Create JarvisUI (PyQt6 window)
    ↓
Connect signals/slots
    ↓
Start Qt event loop + asyncio event loop
    ↓
Application ready
```

## Key Files and Their Roles at Startup

| File | Function | When Called |
|------|----------|-------------|
| `main.py` | Entry point, JarvisLive construction | Immediately |
| `core/action_loader.py` | Auto-discover built-in tools | In JarvisLive.__init__ |
| `core/plugin_loader.py` | Auto-discover plugins | In JarvisLive.__init__ |
| `core/wake_word.py` | Load openwakeword model | In JarvisLive.__init__ (if enabled) |
| `core/hotkey.py` | Set up push-to-talk | In JarvisLive.__init__ (if enabled) |
| `core/audio_devices.py` | Prefetch device list | In JarvisLive.__init__ (via config_manager) |
| `memory/memory_manager.py` | Load long_term.json | In _build_config() |
| `memory/config_manager.py` | Read api_keys.json | Throughout |
| `core/prompt.txt` | Load system prompt template | In _build_config() |
| `ui.py` | Build PyQt6 HUD | After JarvisLive |
| `core/gemini.py` | One-shot Gemini client | On demand (not at startup) |
| `core/llm_client.py` | Local LLM client | On demand (for planning) |
| `dashboard/server.py` | Start FastAPI server | On demand |