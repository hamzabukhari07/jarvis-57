# JARVIS — AI Architecture (Gemini Live)

## Provider, Model, and SDK

```
AI Provider: Google (Google AI / Gemini)
AI Model: gemini-3.1-flash-live-preview
Model Version: Preview (as of JARVIS)
SDK: google-genai (google-genai>=2.8.0,<3)
Python Package: google-genai
```

## Where Configured

| Location | File/Code | What it sets |
|----------|-----------|-------------|
| Model identifier | `main.py:99` | `LIVE_MODEL = "models/gemini-3.1-flash-live-preview"` |
| API key | `config/api_keys.json` | `gemini_api_key` field |
| Voice | `memory/config_manager.py:81-89` | `get_voice()` reads `voice_name` from config |
| Available voices | `memory/config_manager.py:81` | `["Charon", "Puck", "Kore", "Fenrir", "Aoede"]` |
| Default voice | `memory/config_manager.py:82` | `"Charon"` |
| Turn tuning | `memory/config_manager.py:172-203` | `turn_tuning` config section |
| Proactive audio | `memory/config_manager.py:221-235` | `proactive_audio` toggle |
| Thinking enabled | `memory/config_manager.py:158-169` | `thinking_enabled` toggle |
| Media resolution | `memory/config_manager.py:241-252` | `media_resolution` setting |

## Where Initialized

### Live Session Creation

**File:** `main.py`, method `JarvisLive._build_config()` (line 952)

```python
def _build_config(self) -> types.LiveConnectConfig:
    cfg = dict(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="\n".join(parts),
        tools=[{"function_declarations": _all_decls}],
        session_resumption=types.SessionResumptionConfig(handle=self._resume_handle),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=get_voice()
                )
            )
        ),
    )
    # ... optional proactivity and tuning ...
    return types.LiveConnectConfig(**cfg)
```

The session itself is created via `google.genai.Client.aio.live.connect()`:

```python
cm = cl.aio.live.connect(model=LIVE_MODEL, config=gtypes.LiveConnectConfig(**cfg))
session = await asyncio.wait_for(cm.__aenter__(), 30)
```

### One-Shot Gemini Calls (Non-Live)

**File:** `core/gemini.py`

Used for: search, classification, extraction, code generation, image analysis

```python
from google import genai
from google.genai import types as gtypes

cl = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
# Live one-shot:
cm = cl.aio.live.connect(model=_live_model(), config=gtypes.LiveConnectConfig(**kwargs))
```

## Session Lifecycle

### 1. Session Creation

```
JarvisLive._build_config()
    ↓
types.LiveConnectConfig(**cfg)
    ↓
genai.Client.aio.live.connect(model, config)
    ↓
cm.__aenter__() → session
    ↓
session.send_client_content(turns=..., turn_complete=True)
```

### 2. Resumption Handle

```
The server sends session_resumption updates periodically
    ↓
self._resume_handle is updated
    ↓
On reconnect, the handle is passed back
    ↓
Session resumes with conversation intact
```

**Important:** The resumption handle is stored **only in RAM**, never written to disk. This prevents a fresh launch from continuing yesterday's conversation (which would break the session summary flow).

### 3. Connection Drops and Reconnection

**File:** `main.py`, `JarvisLive` class

- A `_ReconnectSignal` exception is raised inside the `asyncio.TaskGroup`
- This unwinds the task group, tearing down audio streams and the session
- The `run()` method catches it and rebuilds the session
- `keep_context=True` replays the resumption handle (conversation continues)
- `keep_context=False` starts fresh (used for voice changes)

### 4. Session Termination

- `shutdown_jarvis` tool → saves session summary, calls `_os._exit(0)`
- `close_camera` tool → stops camera stream
- Application close → Qt cleanup

## System Instructions

### Construction

**File:** `main.py`, `JarvisLive._build_config()` (line 952)

The system instruction is built from four parts:

```python
parts = [
    time_ctx,       # [CURRENT DATE & TIME]
    identity_ctx,   # [IDENTITY]
    mem_str,        # memory block (if any)
    sys_prompt,     # core/prompt.txt with {tokens} filled in
]
system_instruction = "\n".join(parts)
```

### Token Filling

```python
sys_prompt = _render_prompt(sys_prompt, {
    "assistant_name": self._asst_name,       # from config
    "platform": f"{_platform.system()} {_platform.release()}",
    "capabilities": _describe_tools(_all_decls),  # all discovered tools
    "limits": _describe_limits(has_vision, has_mic),
})
```

**File:** `core/prompt.txt` — the template with `{assistant_name}`, `{platform}`, `{capabilities}`, `{limits}` placeholders

### What the System Prompt Contains

1. **[SELF]** — Identity, body awareness, image labeling rules
2. **[WHAT YOU CAN DO]** — Full tool list (dynamically generated)
3. **[WHAT YOU CANNOT DO]** — Limitations (dynamically generated)
4. **[JUDGEMENT]** — How to interpret requests
5. **[VOICE]** — Speaking style rules
6. **[ACKNOWLEDGE BEFORE A SILENCE]** — Anti-stalling rules
7. **[LANGUAGE]** — Language rules
8. **[EXECUTION]** — Tool calling rules
9. **[TAGGED MESSAGES]** — Internal message tags
10. **[SPEED]** — Latency rules

## Tools and Function Calling

### How Tools Are Defined

Tools are declared as `function_declarations` in the LiveConnectConfig:

```python
tools=[{"function_declarations": _all_decls}]
```

Where `_all_decls` = `TOOL_DECLARATIONS` (inline) + `action_registry.get_tool_declarations()` + `plugin_registry.get_tool_declarations()`

### How Gemini Discovers and Invokes Tools

1. Gemini receives the system prompt + tool declarations
2. When a tool is needed, Gemini outputs a function call in its response
3. The response is parsed for function calls
4. `_execute_tool()` dispatches to the appropriate handler
5. The result is returned as a `FunctionResponse`
6. Gemini processes the result and generates the next response

### Tool Declaration Shape

```python
{
    "name": "open_app",
    "description": "Launches an application...",
    "parameters": {"type": "OBJECT", "properties": {...}},
    "behavior": "BLOCKING",  # or "NON_BLOCKING"
    "scheduling": "WHEN_IDLE",  # optional
}
```

### Tool Execution Flow

```
Gemini generates function call
    ↓
main.py:_execute_tool(fc)
    ↓
if name == "save_memory": → direct handler
elif name == "recall_memory": → direct handler
elif name == "screen_process": → direct handler
elif name == "undo": → direct handler
elif name == "shutdown_jarvis": → direct handler
elif name == "manage_monitor": → direct handler
elif name == "system_status": → direct handler
elif name == "close_camera": → direct handler
elif _action_registry.has(name): → action_registry.run()
elif _plugin_registry.has(name): → plugin_registry.run()
else: → "Unknown tool"
    ↓
Result returned as FunctionResponse
    ↓
Gemini processes result → final response
```

## Streaming

### Audio Input Streaming

```
sounddevice.InputStream callback
    ↓
callback(indata, frames, time_info, status)
    ↓
Convert to bytes, put in out_queue
    ↓
_send_realtime() coroutine: session.send_realtime_input(audio=...)
    ↓
WebSocket → Google servers
```

### Audio Output Streaming

```
session.receive() async iterator
    ↓
For each response:
    - server_content.output_transcription.text → transcript
    - server_content.audio → TTS audio data
    ↓
Transcript → VisemeStream.feed_text() → avatar mouth shapes
    ↓
Audio → _play_audio() → sounddevice.OutputStream → speakers
```

### Transcript Handling

```python
async for resp in session.receive():
    sc = getattr(resp, "server_content", None)
    if sc and sc.output_transcription and sc.output_transcription.text:
        chunks.append(sc.output_transcription.text)
```

**Deduplication:** `_is_repeat_chunk()` guards against the API re-sending transcript tails across multiple `turn_complete` events.

## Input Handling

### Audio Input
- Microphone: 16kHz, mono, 16-bit int, 1024-frame chunks
- Phone mic: routed through the same session when connected
- Push-to-talk: blocks audio when chord not held
- Wake word: blocks audio when sleeping (audio goes to detector only)

### Text Input
- Typed commands: `_on_text_command()` → `session.send_client_content(turns={"role":"user","parts":[{"text":text}]}, turn_complete=True)`
- Plugin speech: `plugin_say()` → same mechanism
- System commands: same mechanism

### Image Input
- Screenshot: `_capture_screen()` → base64 → injected into session
- Camera: `_capture_camera()` → base64 → injected into session
- Vision is on-demand only (not continuous)

## Output Handling

### Audio Output
- Gemini Live produces audio directly (native audio model)
- TTS audio is extracted from `server_content` in `session.receive()`
- Played via `sounddevice.OutputStream` at 24kHz

### Text Output
- `output_audio_transcription` provides text transcription of the model's speech
- This is used for: viseme extraction, activity log, transcript display

### Transcript to Pipeline
```
Transcription received
    ↓
_clean_transcript() → strip control chars
    ↓
_is_repeat_chunk() → deduplicate
    ↓
_feed_text() → VisemeStream
    ↓
UI activity log → _on_text_command handling
```

## Model Ladder (for One-Shot Calls)

**File:** `core/gemini.py`

```python
_LADDERS = {
    "fast":  ("live", "gemini-2.5-flash-lite", "gemini-2.5-flash"),
    "smart": ("live", "gemini-2.5-flash", "gemini-2.5-flash-lite"),
    "search": ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"),
}
```

The Live model is always first because it draws on a different quota pool than text models. On the free tier, the text pool runs out; Live is unaffected.

## Error Handling and Retries

### Connection Errors
- `_ReconnectSignal` for voluntary reconnects
- Session resumption handles expired connections
- Background threads handle reconnection transparently

### API Errors (Quota)
- `core/gemini.py` has cooldown system: models returning 429/RESOURCE_EXHAUSTED are skipped for 5 minutes
- Ladder falls back to next model
- `_LIVE_SLOTS` semaphore caps concurrent Live sessions (3 max)

### Timeout
- One-shot calls: 10 seconds minimum
- Live sessions: no hard timeout (managed by TaskGroup)

## Session Resumption Details

```
Server issues resumption handle every few seconds
    ↓
_handle captured in self._resume_handle
    ↓
On reconnect:
    if keep_context=True:
        session_resumption=types.SessionResumptionConfig(handle=self._resume_handle)
    else:
        session_resumption=types.SessionResumptionConfig(handle=None)  # fresh start
```

**Voice changes** use `keep_context=False` because resuming restores the server's session state (including voice), which would make the voice picker appear to do nothing.

**Audio device changes** use `keep_context=True` because the conversation should survive device swaps.

## Enhanced Live Features

### Proactive Audio
- `proactivity.proactive_audio=True` — Gemini stays silent when speech isn't addressed to it
- Auto-disabled if the server rejects it
- Controlled by `get_proactive_audio_enabled()` from config

### Turn Tuning
- `AutomaticActivityDetection` with configurable `silence_ms`, `prefix_ms`, `end_sensitivity`, `start_sensitivity`
- Off by default (conservative defaults work best for most setups)
- Controlled by `get_turn_tuning()` from config

### Media Resolution
- Screenshots and camera frames are tokenised at low/medium/high resolution
- Default: "medium"
- Controlled by `get_media_resolution()` from config