# JARVIS — Tool / Function Calling System

## Overview

JARVIS has a **dynamic tool system** where tools are discovered at startup. Every tool follows the same interface: a `TOOL` dict with `name`, `description`, `parameters`, and `handler`.

## Tool Discovery

### Built-in Actions (actions/*.py)

**File:** `core/action_loader.py` — `discover_actions()`

Scans `actions/` directory for `.py` files with a module-level `TOOL` dict.

### Plugins (plugins/*.py)

**File:** `core/plugin_loader.py` — `discover_plugins()`

Scans `plugins/` directory for `.py` files with a module-level `PLUGIN` dict.

### Inline Tools (main.py)

Eight tools are defined directly in `main.py` as `TOOL_DECLARATIONS` because they interact with live-session state (vision, camera, memory writes, shutdown).

## Tool Shape

```python
TOOL = {
    "name": "open_app",                    # Unique identifier
    "description": "...",                   # What Gemini reads to route the call
    "parameters": {"type": "OBJECT", "properties": {...}},  # Schema
    "handler": open_app,                     # The callable
    "behavior": "BLOCKING",                  # Optional: BLOCKING | NON_BLOCKING
    "scheduling": "WHEN_IDLE",              # Optional: WHEN_IDLE | SILENT | INTERRUPT
}
```

## Complete Tool Inventory

### Coding & Autonomous Agents

| Tool | File | Purpose | Parameters |
|------|------|---------|------------|
| `antigravity_run` | `actions/antigravity_agent.py` | Full multi-file web app & design synthesis agent via official Antigravity CLI (`agy`) with pure raw HTML reference blueprint injection, stack-fidelity routing (single-file HTML vs React/Next.js), and adaptive redesign directives | `task`, `project_path`, `model` |
| `opencode_run` | `actions/opencode_agent.py` | Full autonomous implementation, multi-file code generation & test suite synthesis | `task`, `project_path`, `model` |
| `kilo_run` | `actions/kilo_agent.py` | Fast refactoring & multi-file editing agent (free tier StepFun / Gemini) | `task`, `project_path`, `model` |
| `code_helper` | `actions/code_helper.py` | Single function, inline snippet generator, or single-file code review | `task`, `file_path`, `code` |
| `dev_agent` | `actions/dev_agent.py` | Read-only codebase exploration, architecture analysis, and bug hunting | `task`, `repo_path` |
| `extract_design_system` | `actions/design_extractor.py` | On-demand design extractor for custom HTML files, URLs, and generating standalone `DESIGN.md` specs | `file_path`, `output_path`, `action`, `force` |
| `fleet_control` | `actions/fleet_control.py` | Orchestrate named specialist agent fleet (dispatch, hire, fire, list_agents, get_status) | `action`, `agent_id`, `task`, `role`, `default_tool`, `model_id`, `specialty` |
| `task_status` | `actions/task_status.py` | Query live progress, inspect logs, or cancel/terminate running background tasks | `action` ('status'/'cancel'), `task_id` |


### System Control

| Tool | File | Purpose | Parameters |
|------|------|---------|------------|
| `system_status` | `main.py` | Returns CPU, RAM, GPU, temperature, uptime | None |
| `shutdown_jarvis` | `main.py` | Ends the conversation session | None |
| `manage_monitor` | `main.py` | Add/remove/list background monitoring topics | action, topic |

### File Control

| Tool | File | Purpose |
|------|------|---------|
| `file_controller` | `actions/file_controller.py` | Move, rename, copy, create, delete files |
| `file_processor` | `actions/file_processor.py` | Read, summarize, answer questions about files |
| `desktop` | `actions/desktop.py` | Desktop organization |

### Browser & Web

| Tool | File | Purpose | Parameters |
|------|------|---------|------------|
| `clone_website` | `actions/website_cloner.py` | Autonomous AI Website Reverse Engineering pipeline (DOM extraction, token harvesting, AI synthesis of clean semantic HTML/CSS/JS, asset localization, and automatic local preview) | `url`, `output_format` ('static'/'clean_html'/'react'/'nextjs'/'redesign'), `include_subpages`, `max_pages`, `redesign_prompt`, `custom_folder` |
| `browser_control` | `actions/browser_control.py` | Open URLs, navigate tabs, interact with browser | `url`, `action` |
| `web_read_page` | `actions/web_reader.py` | Deep web scraping and markdown text extraction. Scrapling (Fetcher/StealthyFetcher) when installed, otherwise a built-in `requests` + BeautifulSoup fallback. | `url`, `stealth`, `max_chars` |
| `web_search` | `actions/web_search.py` | Ultra-fast 3-tier search (Tavily AI &lt;500ms ➔ Gemini Grounded ➔ DDG) with Groq LPU synthesis, modes: search, news, research, price, compare | `query`, `mode`, `items`, `aspect` |
| `agent_reach` | `actions/agent_reach.py` | Multi-platform intelligence, spoken audio Whisper transcription, video transcripts, social discussions & repo analysis (Instagram Reels, TikTok, YouTube, Reddit, GitHub, X, Stack Overflow, Hacker News, RSS) | `platform` ('auto'/'multi'/'instagram'/'tiktok'/'youtube'/'reddit'/'github'/'twitter'/'stackoverflow'/'hackernews'/'rss'), `target` |
| `flight_finder` | `actions/flight_finder.py` | Live flight price and availability | `origin`, `destination`, `date` |
| `youtube_video` | `actions/youtube_video.py` | Search, play, control YouTube | `query`, `action` |

### OS Controls & Media

| Tool | File | Purpose | Parameters |
|------|------|---------|------------|
| `computer_settings` | `actions/computer_settings.py` | Volume, brightness, WiFi, power, battery queries | `action`, `value` |
| `computer_control` | `actions/computer_control.py` | Mouse clicks/drags, keyboard hotkeys, Unicode typing, compound batch macros, safe window closure with exact title matching (`_safe_close_window`), and 3-tier escalated perception (L1 UIA ➔ L1.5 RapidOCR ROI ➔ L2 Vision) | `action` ('click'/'screen_click'/'double_click'/'type'/'hotkey'/'press'/'batch'/'get_active_window_info'/'close_window'/aliases), `x`, `y`, `description`, `text`, `keys`, `key`, `sequence` |
| `open_app` | `actions/open_app.py` | Application launcher with post-launch focus guard, non-destructive UI view switching (`office_view` vs `dashboard`), and process termination | `app_name`, `path`, `action` ('open'/'close') |
| `weather_report` | `actions/weather_report.py` | Live weather forecast | `city`, `time` |
| `game_updater` | `actions/game_updater.py` | Steam/Epic game updates and patch notes | `game_name`, `action` |
| `reminder` | `actions/reminder.py` | Scheduled alarms, timers, reminders | `time_str`, `message` |
| `send_message` | `actions/send_message.py` | WhatsApp, Telegram messaging with explicit send governance | `platform`, `action` ('search'/'send'), `recipient`, `message` |

### Vision & Perception

| Tool | File | Purpose | Parameters |
|------|------|---------|------------|
| `screen_process` | `actions/screen_processor.py` | Fast OS ground-truth state (1ms), RapidOCR text extraction, multi-region capture, dHash caching (0ms hit), and Gemini multimodal vision | `action` ('capture'/'read_text'), `angle` ('screen'/'camera'), `prompt`, `region` |
| `close_camera` | `main.py` | Close live camera stream view | None |

### Memory

| Tool | File | Purpose |
|------|------|---------|
| `save_memory` | `main.py` | Save fact to long-term memory |
| `recall_memory` | `main.py` | Search long-term memory |

### Undo

| Tool | File | Purpose |
|------|------|---------|
| `undo` | `main.py` | Reverse last action |

### Plugins (Dynamic)

Every `.py` file in `plugins/` with a `PLUGIN` dict becomes a tool. Examples:
- `quiz.py` — Interactive quiz
- `document_review.py` — Contract/policy review
- `background_monitor.py` — Background monitoring
- `proactive.py` — Proactive 2.0
- `reminder.py` — OS-native notifications
- `system_monitor.py` — Hardware telemetry
- `open_app.py` — Application launcher
- `screen_processor.py` — Screen/camera capture
- `weather_report.py` — Weather
- `flight_finder.py` — Flight search
- `game_updater.py` — Game updates
- `file_processor.py` — Document reading
- `code_helper.py` — Code helper
- `dev_agent.py` — Developer agent
- `send_message.py` — Messaging
- `youtube_video.py` — YouTube control
- `browser_control.py` — Browser control
- `computer_control.py` — Desktop control
- `computer_settings.py` — Settings
- `desktop.py` — Desktop management

## How Gemini Discovers Tools

```python
_all_decls = (
    TOOL_DECLARATIONS                          # Inline (main.py)
    + self._action_registry.get_tool_declarations()   # Actions
    + self._plugin_registry.get_tool_declarations()   # Plugins
)
```

These are sent to Gemini as:
```python
tools=[{"function_declarations": _all_decls}]
```

## How Tool Calling Works

### Step 1: Gemini Generates a Function Call

The model outputs a function call in its response based on:
- The tool descriptions in the system prompt
- The `{capabilities}` section populated with all tool names
- The user's request

### Step 2: Main Loop Parses the Function Call

```python
async def _execute_tool(self, fc) -> types.FunctionResponse:
    name = fc.name
    args = dict(fc.args or {})
```

### Step 3: Handler Dispatch

```python
if name == "save_memory":
    # Direct inline handler
elif name == "recall_memory":
    # Direct inline handler
elif name == "screen_process":
    # Direct inline handler
elif self._action_registry.has(name):
    self._action_registry.run(name, args, ctx)
elif self._plugin_registry.has(name):
    self._plugin_registry.run(name, args, player=self.ui)
else:
    result = f"Unknown tool: {name}"
```

### Step 4: Handler Execution

```python
def _call_handler(fn, parameters, ctx):
    sig = inspect.signature(fn)
    # Passes only the kwargs the function declares
    # Supports: def run(parameters): and def run(parameters, player=None):
```

### Step 5: Result Returned to Gemini

```python
return types.FunctionResponse(
    id=fc.id, name=name,
    response={"result": result},
    scheduling=_sched  # if declared
)
```

### Step 6: Gemini Generates Final Response

The model processes the tool result and generates natural language output.

## Tool Parameters

All tools use the same parameter schema:
```python
"parameters": {"type": "OBJECT", "properties": {...}}
```

Example from `open_app`:
```python
TOOL = {
    "name": "open_app",
    "description": "Launches an application...",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Name of the application"},
        },
        "required": ["app_name"]
    },
    "handler": open_app,
}
```

## Tool Behavior

| Behavior | Meaning | Example |
|----------|---------|---------|
| `BLOCKING` | Waits for result before continuing | Most tools |
| `NON_BLOCKING` | Returns immediately, result arrives later | Phone calls |

| Scheduling | Meaning |
|------------|---------|
| `WHEN_IDLE` | Wait for a gap in speech |
| `SILENT` | Record result, don't prompt reply |
| `INTERRUPT` | Cut in immediately |

## Undo System

**File:** `core/undo.py`

```python
# In action handlers:
from core.undo import push_undo
push_undo(f"volume → {new}%", lambda: volume_set(old))
```

- Stack depth: 10 entries max
- Thread-safe with `threading.Lock`
- `undo_last()` pops and executes the reverse callable
- `history()` returns labels for the UI undo panel

## Confirmation System

**File:** `core/confirm.py`

For irreversible actions (shutdown, restart, WiFi):
```python
confirm.request(key, title, detail, run)
    ↓
UI shows CONFIRM/CANCEL banner
    ↓
User presses CONFIRM
    ↓
confirm.resolve(True) → runs the stored callable
```

**Key security property**: The confirmation token is issued by the UI, never by the model. The model cannot forge it.

## Summary

```
All tools follow: TOOL dict + handler function
Discovery: auto-scanned at startup
Dispatch: _execute_tool() in main.py
Security: confirm.py for irreversible actions
Undo: core/undo.py for reversible actions
Dynamic: Adding a tool = adding a .py file with TOOL dict
```