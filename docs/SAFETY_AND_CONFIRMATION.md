# JARVIS — Safety and Confirmation System

## Overview

Dangerous actions (shutdown, restart, WiFi toggle) are protected by a **confirmation gate** where the confirmation token is issued by the UI, never by the AI model.

**File:** `core/confirm.py`

## The Problem It Solves

The old gate was broken:
```python
# OLD CODE (broken):
confirmed = str(params.get("confirmed", "")).lower()
if confirmed not in ("yes", "true", "1", "confirm"):
    return "Please confirm by calling again with confirmed=yes."
```

**Problem**: `confirmed` is a tool parameter, which means the *model* writes it. Nothing stops it from sending `confirmed=yes` on the first call.

## The Design

The confirmation token is issued by the **interface**:

```
1. Action calls confirm.request(key, title, detail, run)
    ↓
2. Module hands UI a banner (CONFIRM / CANCEL)
    ↓
3. Returns immediately with [CONFIRMATION_PENDING] sentence
    ↓
4. User presses CONFIRM on HUD
    ↓
5. UI calls confirm.resolve(True)
    ↓
6. Stored callable runs on worker thread
    ↓
7. Action executes
```

## How It Works

### request() — Park the Action

```python
def request(key: str, title: str, detail: str, run: Callable[[], str]) -> str:
    global _pending
    _pending = _Pending(key=key, title=title, detail=detail, run=run, at=time.monotonic())
    _show_cb(title, detail)  # Show banner on UI
    return "[CONFIRMATION_PENDING] I have put a confirmation on screen for: {title}..."
```

**Key**: Returns a sentence for the model to say out loud. The model asks the user to confirm. It never claims the action is done.

### resolve() — Execute the Action

```python
def resolve(accepted: bool) -> None:
    global _pending
    p, _pending = _pending, None
    if not accepted:
        return  # Cancelled
    if time.monotonic() - p.at > TIMEOUT_SECONDS:  # 90s
        return  # Expired
    threading.Thread(target=_worker, daemon=True).start()
    # _worker calls p.run()
```

**Key**: Runs on a worker thread — shutting down from a button handler would freeze the UI.

## Timeout

```python
TIMEOUT_SECONDS = 90.0  # 90 seconds
```

Abandoned confirmations are discarded after 90 seconds.

## What Requires Confirmation

| Action | Why |
|--------|-----|
| Shutdown | Irreversible |
| Restart | Irreversible |
| WiFi toggle | Cuts Live API connection, cannot be undone |

## Why Not All Actions Use Confirmation

> The split between the two mechanisms is about reversibility, not about how alarming a word sounds. Anything undoable is done at once; only the genuinely irreversible asks. An assistant that checks with you before turning the volume down is one you stop talking to.

- **Undoable actions**: Do immediately, register undo (`core/undo.py`)
- **Irreversible actions**: Confirmation gate (`core/confirm.py`)

## Security Properties

1. **Model cannot forge confirmation**: The token is issued by the UI, not the model
2. **No blocking**: The model keeps talking while the banner is up
3. **Cheaper than the old gate**: The old gate burned 2 tool round trips (reject then re-call); the new gate costs 0
4. **Timeout safety**: 90-second expiry prevents stale banners
5. **Worker thread**: Actions run off the Qt thread to prevent UI freeze

## Confirmation Flow Example

```
User: "Shutdown my computer"
    ↓
Gemini calls computer_settings(action="shutdown")
    ↓
confirm.request("shutdown", "Shutdown", "This will turn off your computer", shutdown_fn)
    ↓
Returns: "[CONFIRMATION_PENDING] I have put a confirmation on screen for: Shutdown..."
    ↓
UI shows banner: "SHUTDOWN — CONFIRM / CANCEL"
    ↓
Model speaks: "I've put a confirmation on screen for Shutdown. Please confirm on the HUD."
    ↓
User presses CONFIRM
    ↓
confirm.resolve(True)
    ↓
Worker thread runs shutdown_fn()
    ↓
Computer shuts down
```

## Binding to the UI

```python
confirm.bind(show_cb, hide_cb, log_cb)
# show_cb(title, detail) → show banner on HUD
# hide_cb() → remove banner
# log_cb(msg) → log to activity log
```

Called once from `main.py` at startup.

## Summary

```
Protection: confirmation gate for irreversible actions
Token source: UI (never the model)
Actions: shutdown, restart, WiFi toggle
Timeout: 90 seconds
Execution: Worker thread
Non-blocking: Model keeps talking while waiting
Security: Model cannot forge confirmation
Alternative: Undo stack for reversible actions
```