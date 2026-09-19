# JARVIS — Plugin System

## Overview

JARVIS has a **drop-in plugin system** where adding a new skill is as simple as dropping a `.py` file into `plugins/`. Plugins are auto-discovered at startup and registered as tools the AI can invoke.

## Discovery Mechanism

**File:** `core/plugin_loader.py` — `discover_plugins()`

```
Scan plugins/ directory
    ↓
For each *.py (sorted, skip _*)
    ↓
Import module via importlib.util
    ↓
Check for module-level PLUGIN dict
    ↓
Validate name, description, parameters, run()
    ↓
Check name collisions with actions AND core tools
    ↓
Create PluginRecord
    ↓
PluginRegistry
```

## Plugin Interface

### Required: PLUGIN Dict

```python
PLUGIN = {
    "name": "my_plugin",                    # ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$
    "description": "...",                    # Gemini uses this to decide when to call
    "parameters": {"type": "OBJECT", "properties": {...}},
}
```

### Required: run() Function

```python
def run(parameters: dict, player=None, session_memory=None) -> str:
    """
    parameters: dict of args Gemini extracted
    player: JarvisUI instance (for logging)
    session_memory: reserved
    Return: short natural-language string (spoken back)
    Never raise: catch own errors
    """
    ...
```

### Optional: PLUGIN_SETTINGS

```python
PLUGIN_SETTINGS = {
    "namespace": "my_plugin",
    "title": "My Plugin Settings",
    "fields": [...],    # Config fields for the settings UI
    "action": "connect", # Optional test button
}
```

### Optional: Behavior and Scheduling

```python
PLUGIN = {
    ...
    "behavior": "NON_BLOCKING",   # BLOCKING | NON_BLOCKING
    "scheduling": "WHEN_IDLE",     # WHEN_IDLE | SILENT | INTERRUPT
}
```

## Validation

**File:** `core/plugin_loader.py`, `_validate()`

| Check | Detail |
|-------|--------|
| Name format | `^[a-zA-Z_][a-zA-Z0-9_]{0,63}$` |
| Description | Non-empty string |
| Parameters | Must be `{"type": "OBJECT", ...}` |
| Handler | `run` must be callable |
| Collision | Cannot shadow core tools or actions |
| Settings | Must be dict with `fields` list |

## Plugin Lifecycle

```
1. Startup: discover_plugins() scans all *.py files
2. Validation: each plugin checked for correct structure
3. Registration: valid plugins added to PluginRegistry
4. Runtime: Gemini can call plugin tools by name
5. Settings: users can enable/disable plugins via config
6. Logging: successes logged to console, failures to activity log
```

## How Gemini Sees Plugins

Plugins are merged into the tool declarations sent to Gemini:

```python
_all_decls = (
    TOOL_DECLARATIONS
    + self._action_registry.get_tool_declarations()
    + self._plugin_registry.get_tool_declarations()  # ← plugins here
)
```

**Important**: Plugin names that collide with core tools or actions are **rejected**. This prevents shadowing.

## Plugin Registration

```python
self._plugin_registry = discover_plugins(
    plugins_dir=_base_dir / "plugins",
    core_tool_names=_core_names,    # inline tools + actions
    logger=lambda msg: print(f"[Plugins] {msg}"),
    notify=lambda msg: self.ui.write_log(f"SYS: {msg}"),
)
```

The `core_tool_names` set prevents name collisions between plugins and the built-in actions/tools.

## Plugin Execution

**File:** `core/plugin_loader.py`, `PluginRegistry.run()`

```python
def run(self, name: str, parameters: dict, player=None, session_memory=None) -> str:
    rec = self._plugins.get(name)
    if rec is None or not rec.valid:
        return f"Plugin '{name}' is not available."
    if not get_plugin_enabled(name):
        return f"The '{name}' plugin is currently disabled."
    try:
        return _call_run(rec.run, parameters, player, session_memory)
    except Exception as e:
        self._notify(f"Plugin '{name}' failed — see the console.")
        return f"Sir, the '{name}' plugin failed: {e}"
```

**Crash isolation**: Plugin exceptions are caught and reported, never propagated to crash the app.

## Enable/Disable

Plugins are **enabled by default** (opt-out model). State stored in `config/api_keys.json`:

```python
def get_plugin_enabled(plugin_name: str) -> bool:
    return load_api_keys().get("plugins_enabled", {}).get(plugin_name, True)
```

## How to Add a New Plugin

### Step 1: Create a .py file in plugins/

```python
# plugins/my_plugin.py

PLUGIN = {
    "name": "my_plugin",
    "description": "Does something useful. Call it when...",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "What to search"},
        },
        "required": ["query"]
    },
}

def run(parameters: dict, player=None, session_memory=None) -> str:
    query = parameters.get("query", "")
    try:
        result = f"Found results for {query}."
        if player:
            player.write_log(f"JARVIS: {result}")
        return result
    except Exception as e:
        return f"Sir, my_plugin failed: {e}"
```

### Step 2: Drop it in plugins/

That's it. No other file needs to change. The plugin is auto-discovered at the **next launch**.

### Step 3: Restart the app

```bash
python main.py
```

The plugin appears in:
- The tool list Gemini can use
- The Plugin Manager UI overlay
- The settings drawer (if PLUGIN_SETTINGS is defined)

## Plugin Examples in the Repository

| Plugin | File | Purpose |
|--------|------|---------|
| Quiz | `plugins/quiz.py` | Interactive quiz |
| Document Review | `plugins/document_review.py` | Contract/policy review |
| Template | `plugins/_template.py` | Copy this to create a new plugin |
| Shared: OAuth | `plugins/_google_core.py` | Shared OAuth for Gmail/Calendar |
| Shared: Printer | `plugins/_printer_core.py` | Shared printer connectivity |

## Plugin Security Model

- Plugins run in the **same process** as the main application
- No sandboxing — plugins have full access to the Python environment
- Plugin names cannot collide with core tools (prevention, not isolation)
- Plugin exceptions are caught and isolated (crashes don't take down the app)
- Plugins can log to the activity log via `player.write_log()`
- Plugins can speak mid-task via `self.request_say()` (injected through the Live session)

## Summary

```
Plugin = .py file with PLUGIN dict + run() function
Discovery = auto-scanned at startup
Collision = names checked against core tools and actions
Enable/disable = config/api_keys.json
Adding a plugin = drop a .py file, restart
Crash isolation = exceptions caught, logged, not propagated
```