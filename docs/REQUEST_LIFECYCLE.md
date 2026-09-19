# JARVIS — Request Lifecycle

## Example 1: "Open Chrome"

```
User: "Open Chrome"
    ↓
Microphone captures audio (sounddevice.InputStream, 16kHz)
    ↓
Audio callback → out_queue → _send_realtime() → Gemini Live
    ↓
Gemini STT: "Open Chrome"
    ↓
Gemini LLM: Identifies intent → calls open_app tool
    ↓
_execute_tool(fc) → name="open_app"
    ↓
self._action_registry.has("open_app") → True
    ↓
action_registry.run("open_app", {"app_name": "chrome"}, ctx)
    ↓
actions/open_app.py:open_app(parameters, player, speak)
    ↓
Platform check: {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"}
    ↓
subprocess.Popen(["chrome"], creationflags=CREATE_NO_WINDOW)
    ↓
Result: "Chrome opened."
    ↓
FunctionResponse → Gemini
    ↓
Gemini generates response: "Chrome has been opened."
    ↓
TTS audio → speakers
    ↓
Transcript → UI log, visemes → avatar
```

## Example 2: "What's the weather?"

```
User: "What's the weather?"
    ↓
Mic → Gemini Live → STT → LLM
    ↓
Gemini calls weather_report tool
    ↓
_execute_tool(fc) → name="weather_report"
    ↓
actions/weather_report.py:weather_report(parameters, player, speak)
    ↓
API call for user's city (from memory location)
    ↓
Returns: "It's 72°F and sunny in Seattle."
    ↓
Gemini generates spoken response
    ↓
TTS → speakers
```

## Example 3: "Remember that I'm allergic to peanuts"

```
User: "Remember that I'm allergic to peanuts"
    ↓
Gemini LLM: Identifies memory-worthy fact
    ↓
Gemini calls save_memory tool
    ↓
_execute_tool(fc) → name="save_memory"
    ↓
category="health", key="peanut_allergy", value="allergic to peanuts"
    ↓
update_memory({"health": {"peanut_allergy": {"value": "allergic to peanuts"}}})
    ↓
memory_manager.py:
    load_memory() → update → save_memory()
    ↓
long_term.json updated
    ↓
FunctionResponse → Gemini
    ↓
Gemini generates response: "Noted."
```

## Example 4: "Look at my screen"

```
User: "Look at my screen"
    ↓
Gemini calls screen_process tool
    ↓
_execute_tool(fc) → name="screen_process"
    ↓
angle="screen", text="What do you see?"
    ↓
self._vision_busy = True
    ↓
img_b, mime_t = await loop.run_in_executor(None, _capture_screen)
    ↓
mss captures display → PIL compresses → JPEG (1280x720, quality 82)
    ↓
self._pending_vision = (img_b, mime_t, user_text, "screen")
    ↓
Result: "[VISION_ACTIVE] Screen captured and attached to this exchange."
    ↓
Image attached to SAME exchange as tool result
    ↓
Gemini sees the image → analyzes → generates response
    ↓
One turn, one answer
```

## Example 5: "Move this file"

```
User: "Move this file to Documents"
    ↓
Gemini calls file_controller tool
    ↓
_execute_tool(fc) → name="file_controller"
    ↓
action: "move", source: "...", destination: ".../Documents"
    ↓
actions/file_controller.py:file_controller(parameters, player, speak)
    ↓
shutil.move(source, destination)
    ↓
push_undo(f"Moved file to Documents", lambda: shutil.move(dest, src))
    ↓
Result: "File moved."
    ↓
Undo registered in core/undo.py stack
```

## Example 6: "Undo that"

```
User: "Undo that"
    ↓
Gemini calls undo tool
    ↓
_execute_tool(fc) → name="undo"
    ↓
action="undo" → undo_stack.undo_last()
    ↓
core/undo.py:
    entry = _stack.pop()  # most recent
    detail = entry.undo()  # execute reverse function
    return f"Undone: {entry.label}."
    ↓
FunctionResponse → Gemini
    ↓
Gemini: "Undone: Moved file to Documents."
```

## Example 7: "Shutdown my computer"

```
User: "Shutdown my computer"
    ↓
Gemini calls computer_settings tool
    ↓
_execute_tool(fc) → name="computer_settings"
    ↓
action="shutdown"
    ↓
confirm.request("shutdown", "Shutdown", "This will turn off your computer", shutdown_fn)
    ↓
Returns: "[CONFIRMATION_PENDING] I have put a confirmation on screen..."
    ↓
UI shows CONFIRM/CANCEL banner
    ↓
User presses CONFIRM
    ↓
confirm.resolve(True)
    ↓
Worker thread runs shutdown_fn()
    ↓
subprocess.Popen(["shutdown", "/s", "/t", "0"])
    ↓
Computer shuts down
```

## Example 8: Normal Conversation ("Hello, how are you?")

```
User: "Hello, how are you?"
    ↓
Mic → Gemini Live → STT → "Hello, how are you?"
    ↓
Gemini LLM processes with system prompt + memory + tools
    ↓
No tool call needed
    ↓
Gemini generates response: "Hello! I'm doing well, thanks for asking."
    ↓
TTS audio → speakers
    ↓
Transcript → UI log, visemes → avatar
    ↓
set_speaking(False) → echo tail guard starts
    ↓
Wait for next input
```

## Example 9: "Hey Jarvis, what's the time?"

```
User: "Hey Jarvis"
    ↓
WakeWordDetector detects "Hey Jarvis"
    ↓
wake() → _awake = True
    ↓
Mic now streams to Gemini
    ↓
User continues: "what's the time?"
    ↓
Gemini LLM: Calls system_status tool or reads time from prompt
    ↓
Response: "It's currently [time]."
```

## Example 10: Plugin Execution

```
User: "Start a quiz"
    ↓
Gemini identifies quiz plugin
    ↓
Gemini calls quiz plugin
    ↓
plugin_registry.run("quiz", parameters, player=self.ui)
    ↓
plugins/quiz.py:run(parameters, player, session_memory)
    ↓
JARVIS writes questions on screen
    ↓
User answers on screen
    ↓
Result returned to Gemini → spoken response
```

## Summary

```
Every voice input follows: Mic → gates → Gemini → STT → LLM → (tool OR response) → TTS → speaker
Every tool call follows: Gemini → _execute_tool → handler → result → Gemini → response
Every irreversible action follows: confirm.request → UI banner → user confirms → execute
Every reversible action follows: action → push_undo → user says undo → undo_last
```