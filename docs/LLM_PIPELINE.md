# JARVIS — LLM / Reasoning Pipeline

## How the AI Processes a User Request

### End-to-End Flow

```
User voice input
    ↓
Microphone callback → audio bytes → out_queue
    ↓
_send_realtime() → session.send_realtime_input()
    ↓
Gemini Live receives audio
    ↓
Gemini performs STT → transcript
    ↓
Gemini processes transcript with system prompt + tools + memory
    ↓
Gemini decides: respond directly OR call a tool
    ↓
┌─────────────────────────────────────────────────────┐
│ TOOL CALL PATH                                      │
│                                                       │
│ Gemini outputs function_call                         │
│   ↓                                                  │
│ _execute_tool(fc) in main.py                        │
│   ↓                                                  │
│ Identify handler (inline, action, or plugin)        │
│   ↓                                                  │
│ Run handler (in executor thread if blocking)        │
│   ↓                                                  │
│ FunctionResponse returned to Gemini                 │
│   ↓                                                  │
│ Gemini generates final response                     │
└─────────────────────────────────────────────────────┘
    ↓
Gemini generates TTS audio + transcript
    ↓
session.receive() → audio + text
    ↓
Audio → speakers, Text → visemes + log
```

### System Prompt

The system prompt is constructed in `_build_config()`:

```python
parts = [
    time_ctx,       # Current date and time
    identity_ctx,   # Assistant name, user name, address form
    mem_str,        # Memory block (from long_term.json)
    sys_prompt,     # core/prompt.txt with tokens filled
]
```

**File:** `main.py:964-1018`

### Conversation Context

```
Session resumption handle → continues conversation across reconnects
Sliding window compression → context never overflows
Session log → _session_log for end-of-session summary
```

### Tool Definitions

All tools are declared as `function_declarations` and sent to Gemini:

```python
tools=[{"function_declarations": _all_decls}]
```

Where `_all_decls` = inline TOOL_DECLARATIONS + discovered actions + discovered plugins.

### Tool Dispatch

**File:** `main.py`, `_execute_tool()` (line 1113)

```python
async def _execute_tool(self, fc) -> types.FunctionResponse:
    name = fc.name
    args = dict(fc.args or {})
    
    # Inline handlers (direct Python)
    if name == "save_memory": ...
    elif name == "recall_memory": ...
    elif name == "screen_process": ...
    elif name == "close_camera": ...
    elif name == "system_status": ...
    elif name == "manage_monitor": ...
    elif name == "shutdown_jarvis": ...
    elif name == "undo": ...
    
    # Discovered actions
    elif self._action_registry.has(name):
        self._action_registry.run(name, args, ctx)
    
    # Discovered plugins
    elif self._plugin_registry.has(name):
        self._plugin_registry.run(name, args, player=self.ui)
    
    else: result = f"Unknown tool: {name}"
```

### Tool Execution Details

Each action handler receives:
- `parameters`: dict of extracted arguments
- `player`: JarvisUI instance (for logging, showing content)
- `speak`: method to speak mid-execution
- `response`: response channel
- `session_memory`: persistent session memory

```python
def _call_handler(fn, parameters, ctx):
    sig = inspect.signature(fn)
    # Only passes kwargs the function actually declares
    # So def run(parameters): works, and def run(parameters, player=None): works
```

### Tool Result Flow

```
Tool executes
    ↓
Result string
    ↓
FunctionResponse({"result": result, "scheduling": ...})
    ↓
Gemini receives the result
    ↓
Gemini generates natural language response
    ↓
Response → TTS audio + transcript
```

### Non-Blocking Tools

Tools can declare `behavior="NON_BLOCKING"` and `scheduling="WHEN_IDLE" | "SILENT" | "INTERRUPT"`:
- **WHEN_IDLE**: Wait for a gap in speech (default)
- **SILENT**: Record the result, don't prompt a reply
- **INTERRUPT**: Cut in immediately

### Duplicate Response Prevention

```python
def _is_repeat_chunk(txt: str, buf: list) -> bool:
    """Guards against the API re-sending transcript tails."""
    if len(txt) < _REPEAT_MIN:  # 12 chars
        return bool(buf) and txt == buf[-1]
    return txt in " ".join(buf)
```

### Error Handling

```python
try:
    result = await loop.run_in_executor(None, handler, args, ctx)
except Exception as e:
    result = f"Tool '{name}' failed: {e}"
    self.speak_error(name, e)
```

### Reasoning Engine (Local LLM)

**File:** `core/llm_client.py`

For complex planning tasks (agent mode), the local LLM is used:
- **Backend**: Ollama (default) or OpenAI-compatible server
- **Default model**: `llama3.2`
- **Default URL**: `http://localhost:11434`
- **Used by**: `dev_agent.py`, `code_helper.py`, planner

The local LLM handles multi-step planning while Gemini Live handles the voice conversation.

### Gemini One-Shot Calls

**File:** `core/gemini.py`

For non-live tasks (search, classification, image analysis):
- Uses a separate throwaway Live session per call
- Ladder: Live → specific pinned model → rolling latest
- Quota management: cooldown for 429 errors
- Max 3 concurrent live slots (`_LIVE_SLOTS` semaphore)

### Streaming and Turn Completion

```
Turn starts: session.send_client_content(turns={...}, turn_complete=True)
    ↓
Gemini processes → may call tools → tool results returned
    ↓
Gemini generates response → audio + transcript
    ↓
session.receive() drains all chunks
    ↓
Turn done → _turn_done_event set
    ↓
Ready for next turn
```

### Session Continuity

The session survives:
- Dropped network packets (resumption handle replayed)
- Voice changes (fresh session, context lost — intentional)
- Device changes (resumption handle replayed, context preserved)