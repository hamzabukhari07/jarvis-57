# JARVIS — Undo System

## Overview

The undo system allows JARVIS to reverse its own actions. It uses a **closure-based stack** where each reversible operation stores a label and a reverse function.

**File:** `core/undo.py`

## Architecture

```python
# Stack structure
_stack: list[_Entry] = []  # Max 10 entries
_lock = threading.Lock()

@dataclass
class _Entry:
    label: str                    # Human-readable description
    undo: Callable[[], str]      # Zero-argument reverse function
    at: float = time.monotonic()  # When it happened
```

## How Actions Register Undo

Actions opt in by calling `push_undo()`:

```python
from core.undo import push_undo

# Example from volume control:
old = volume_get()
volume_set(new)
push_undo(f"volume → {new}%", lambda: volume_set(old))

# The reverse function captures the OLD state
# Nothing runs until undo_last() is called
```

**Cost**: A list append behind a lock — microseconds. Nothing in the stack runs unless asked.

## Stack Operations

### Push

```python
def push_undo(label: str, undo_fn: Callable[[], str]) -> None:
    with _lock:
        _stack.append(_Entry(label=str(label)[:120], undo=undo_fn))
        while len(_stack) > MAX_DEPTH:  # MAX_DEPTH = 10
            _stack.pop(0)
```

### Undo

```python
def undo_last() -> str:
    with _lock:
        entry = _stack.pop() if _stack else None
    if entry is None:
        return "There is nothing to undo..."
    try:
        detail = entry.undo() or ""
    except Exception as e:
        return f"Could not undo '{entry.label}': {e}"
    return f"Undone: {entry.label}." + (f" {detail}" if detail else "")
```

**Key**: The entry is popped **before** running so a failing undo can't be retried forever.

### History

```python
def history() -> list[str]:
    """Most recent first."""
    with _lock:
        return [e.label for e in reversed(_stack)]
```

### Clear

```python
def clear() -> None:
    """Called on shutdown. Forget the stack."""
    with _lock:
        _stack.clear()
```

## What Can Be Undone

| Category | Actions |
|----------|---------|
| **Files** | move, rename, create, copy, write, delete, organize desktop |
| **Settings** | volume, brightness, dark mode, WiFi toggle |

## What Cannot Be Undone

| Category | Reason |
|----------|--------|
| **Shutdown/Restart** | Irreversible → confirmation gate instead |
| **WiFi toggle** | Cuts the Live API connection → confirmation gate |
| **File copies** | Reverse is removing the copy (not the original) |
| **Folder creation** | Remove only if still empty |
| **Files > 1 MB** | Excluded to avoid holding large data in memory |

## Desktop Organization Special Case

`organize_desktop` is the least reversible action (moves dozens of files). It uses a **journal**:

```
Every move is journaled
    ↓
Undo restores all moves in one go
    ↓
Cleanup empty folders
```

## Thread Safety

- `push_undo()`: Called from executor threads → protected by `threading.Lock`
- `undo_last()`: Called from `_execute_tool()` → protected by `threading.Lock`
- `clear()`: Called on shutdown → protected by `threading.Lock`

## Lifecycle

```
Action executes
    ↓
Previous state captured in closure
    ↓
push_undo(label, reverse_fn) → stack append
    ↓
User says "undo"
    ↓
undo tool calls undo_last()
    ↓
Stack pop → reverse function executed
    ↓
Result returned to Gemini → spoken to user
```

## Closure Pattern

```python
# The closure captures the OLD state:
old_volume = get_volume()
set_volume(new_volume)
push_undo(f"volume → {new_volume}%", lambda: set_volume(old_volume))

# When undo runs later, it calls:
lambda: set_volume(old_volume)  # old_volume captured at push time
```

## Memory Management

- Stack depth capped at 10 entries
- Closures holding file contents are excluded for files > 1MB
- `clear()` called on shutdown prevents stale closures

## Summary

```
Stack: Max 10 entries, thread-safe, FIFO (oldest dropped)
Registration: push_undo(label, lambda: reverse_fn)
Execution: undo_last() → pop → execute reverse
Coverage: Files (move/rename/create/delete), settings (volume/brightness)
Limits: >1MB files excluded, irreversible actions use confirm.py
Cost: O(1) push, O(1) pop, nothing runs unless asked
```