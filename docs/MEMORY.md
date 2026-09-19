# JARVIS — Memory Architecture

## Overview

JARVIS has a **persistent memory system** that stores facts about the user across sessions. Memory is stored locally in `memory/long_term.json` and is loaded into the system prompt at each session start.

## Storage Format

**File:** `memory/long_term.json`

```json
{
    "identity":     {"name": {"value": "Fatih", "updated": "2026-09-17"}, ...},
    "preferences":  {"favorite_food": {"value": "pizza", "updated": "2026-09-16"}, ...},
    "projects":     {"current_project": {"value": "...", "updated": "..."}, ...},
    "relationships":{"sister_name": {"value": "...", "updated": "..."}, ...},
    "wishes":       {"travel_dream": {"value": "...", "updated": "..."}, ...},
    "notes":        {"habit": {"value": "...", "updated": "..."}, ...},
    "sessions":     [{"date": "2026-09-17", "summary": "..."}]
}
```

## Categories

| Category | Purpose | Fields |
|----------|---------|--------|
| `identity` | Name, age, birthday, city, job, language, nationality | Always in prompt, in full |
| `preferences` | Favorite food, color, music, film, game, sport | Budgeted by recency |
| `projects` | Active projects, goals | Budgeted by recency |
| `relationships` | Friends, family, partner, colleagues | Budgeted by recency |
| `wishes` | Future plans, travel dreams | Budgeted by recency |
| `notes` | Habits, schedule, anything else | Budgeted by recency |
| `sessions` | Session summaries | Max 3 entries |

## Memory Limits

```python
MEMORY_MAX_CHARS = 200_000       # Runaway guard (not a feature limit)
PROMPT_CORE_CHARS = 900          # What fits in the system prompt
PROMPT_INDEX_CHARS = 420         # Index of off-screen keys
PROMPT_MAX_PER_CATEGORY = 6      # Most entries per category in prompt
MAX_VALUE_LENGTH = 380           # Max length per value
```

## Memory Pipeline

### 1. Saving Memory

```
User reveals something worth remembering
    ↓
save_memory() tool called
    ↓
update_memory({category: {key: {"value": value}}})
    ↓
memory_manager.py:update_memory()
    ↓
_load_memory() → load from long_term.json
    ↓
_recursive_update() → merge new values
    ↓
_save_memory() → trim to limit → write JSON
```

### 2. Loading Memory

```python
def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _empty_memory()
    data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    # Ensure all categories exist
    for key in base:
        if key not in data:
            data[key] = {}
    return data
```

### 3. Prompt Integration

```python
def format_memory_for_prompt(memory: dict) -> str:
    # 1. Identity — always, in full
    for field in _IDENTITY_FIELDS:  # name, age, birthday, city, job, language, nationality
        val = identity[field]["value"]
        core_lines.append(f"{field.title()}: {val}")
    
    # 2. Everything else, most recently updated first (up to PROMPT_CORE_CHARS)
    rest.sort(key=updated, reverse=True)
    for cat, key, val in rest[:budget]:
        core_lines.append(f"  - {key.title()}: {val}")
    
    # 3. Index of remaining keys (for recall_memory)
    if overflow:
        core_lines.append("[ALSO REMEMBERED — values not shown here...]")
        core_lines.append(", ".join(overflow_keys))
    
    return "\n".join(core_lines)
```

### 4. Memory Search (recall_memory)

```python
def search_memory(query: str, limit: int = 8) -> str:
    words = re.split(r"[^\w]+", query.lower())
    for cat, items in memory.items():
        for key, entry in items.items():
            score = _score(words, cat, key, val)
            # Exact key match: +10
            # Key contains word: +6
            # Value contains word: +3
            # Category matches: +1
    rows.sort(key=(-score, key))
    return formatted results
```

## Index System

**Critical design insight**: A model cannot look something up if it doesn't know the thing exists.

```
System prompt carries:
  1. Identity in full
  2. Recently updated entries (up to 900 chars)
  3. INDEX of all other keys (up to 420 chars)
```

The index is interleaved across categories rather than sorted by recency, so preferences don't push important relationship facts off the end.

**Measured**: 971 characters on a memory holding 62 stored facts — smaller than the old whole-store cap of 2200.

## Memory Creation Flow

```
User says something worth remembering
    ↓
save_memory tool called (or silently from execution)
    ↓
update_memory(memory_update: dict)
    ↓
_recursive_update(target, updates) → returns True if changed
    ↓
_save_memory(memory)
    ↓
_trim_to_limit(memory) → if > 200k chars, delete oldest
    ↓
write JSON to memory/long_term.json
    ↓
set_trim_notifier() → activity log notification if trimmed
```

## Memory Deletion

```python
def forget(key: str, category: str = "notes") -> str:
    memory = load_memory()
    if key in cat:
        del cat[key]
        save_memory(memory)
        return f"Forgotten: {category}/{key}"

# Also accessible via recall_memory with empty query
# to list everything stored
```

## Memory UI

**File:** `memory/memory_manager.py`, `all_entries_for_ui()`

```python
def all_entries_for_ui() -> list[dict]:
    # Returns flat list: category, key, value, updated
    # Sorted newest first
```

Accessed via the ⚙ → **🧠 MEMORY** panel in the UI.

## Session Memory

```python
def save_session_summary(summary: str, language: str = "") -> None:
    # Appends to memory["sessions"]
    # Keeps max 3 entries (safety cap)
    # Format: {"date": "2026-09-17", "summary": "...", "language": "..."}

def pop_last_session() -> dict | None:
    # Returns AND removes the most recent session entry
    # Consumed after use — never repeated in future briefings
```

## Memory Persistence

- **File**: `memory/long_term.json`
- **Format**: JSON with indent=2, UTF-8
- **Location**: `memory/long_term.json` (in app directory)
- **Write**: Every `update_memory()` call
- **Read**: Every session start (`_build_config()`)
- **Lock**: `threading.Lock()` for thread safety
- **Trim**: Automatic when exceeding 200k characters
- **Git**: Listed in `.gitignore`

## Summary

```
Storage: memory/long_term.json (JSON)
Categories: identity, preferences, projects, relationships, wishes, notes, sessions
Prompt budget: 900 chars core + 420 chars index
Search: recall_memory tool (local file scan, <1ms)
Deletion: forget() or delete long_term.json
UI: ⚙ → 🧠 MEMORY panel
Persistence: File on disk, locked, trimmed automatically
```