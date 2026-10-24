# ZEZO — Proactive System

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## Overview

ZEZO includes an autonomous **proactive intelligence system** featuring background monitors, context-aware check-ins, automated morning briefings, and background task completion alerting.

**Source Modules**:
- `main.py` (`_run_task_completion_watcher`, `_run_proactive_mode`, `_send_startup_briefing`)
- `actions/proactive.py` (`ProactiveEngine`)
- `actions/background_monitor.py`
- `actions/system_monitor.py` (`SystemMonitor`)
- `actions/reminder.py`

---

## Background Task Completion Watcher

**File**: `main.py` (`_run_task_completion_watcher`, lines 2940–3035)

```python
async def _run_task_completion_watcher(self) -> None:
    """Watch for background coding agent tasks (OpenCode/Kilo/Antigravity) finishing and notify the user."""
```

### Operational Loop:
1. **Poll Rate:** Cycles every 2 seconds (`asyncio.sleep(2)`).
2. **Speech Collision Safeguard:**
   - Checks `self.session` and `self._awake`.
   - Acquires `self._speaking_lock`: verifies `not self._is_speaking`.
   - Enforces a conversational safety cushion: `(time.monotonic() - self._last_user_speech) >= 3`.
   - ZEZO will never speak over the user or interrupt an ongoing reply with a background alert.
3. **Task Resolution & Notification:**
   - Queries `core.task_manager.get_task_manager().get_unnotified_finished_tasks()`.
   - Marks `task.notified = True`.
   - Dynamically resolves task kind (`ZEZO Coder`, `File Processor`, `Intelligence Research`, or custom tool).
   - Generates contextual system notification tags (`[TASK_NOTIFICATION: ...]`, `[TASK_FAILURE_NOTIFICATION: ...]`, `[TASK_CANCELLED_NOTIFICATION: ...]`).
   - Automatically respects user response language preferences (e.g. Urdu, English, or auto).
   - Posts large code outputs, diffs, or reports directly to the React HUD canvas/content panel (`self.ui.show_content()`) while prompting Gemini Live to utter a 1-sentence voice notification.

---

## Morning Briefing

**File**: `actions/proactive.py` & `main.py` (`_send_startup_briefing`)

- **Trigger:** Fires once per process launch on initial awakening (if `get_brief_enabled()` is true).
- **Wake-Word Mode Guard:** Suppressed if the system boots in sleeping state; only triggers when actively awoken.
- **Content:**
  - Dynamic time-of-day greeting (English / Urdu / preferred language).
  - Current calendar date and local system clock.
  - Recap of the previous session (retrieved from `memory/long_term.json["sessions"]`).
  - Real-time weather and curated news headlines.
- **Queue Consumption:** Session summaries are consumed after the briefing (`pop_last_session()`) to ensure yesterday's topics are never repeated redundantly.

---

## Proactive Engine 2.0 (Context-Aware Check-ins)

**File**: `actions/proactive.py`

```python
class ProactiveEngine:
    # Time-aware, context-aware check-ins
    # Knows time of day, active projects, recent topics
    # Evaluates silence duration and active working context
    # Formulates brief, caring, or relevant 1-2 sentence voice check-ins
    # Employs 0 tool calls during check-in to avoid disrupting workspace
```

- **Trigger:** `[PROACTIVE_CHECK]` injection into context when silence threshold is reached and user has been idle during active work.
- **Safety:** Cooldown timers prevent nagging; honors do-not-disturb modes.

---

## Background Topic Monitoring

**File**: `actions/background_monitor.py`

- User-configured topic watching (e.g., framework releases, documentation updates, design system news).
- Periodic headline retrieval once per day.
- Alerts user naturally when significant developments are discovered.
- **Hard Guardrail:** Strictly forbids financial trading, cryptocurrency, or speculative market monitoring.

---

## Hardware & Telemetry Monitoring

**File**: `actions/system_monitor.py`

```python
class SystemMonitor:
    # Continuous CPU, RAM, GPU, temperature telemetry via psutil
    # Cooldown-based reporting to avoid alert floods
    # Localized natural voice alerts on critical resource spikes
```

- Broadcasts telemetry events via WebSocket to the React HUD header.
- Triggers voice warnings if thermal thresholds or memory exhaustion bounds are crossed.

---

## Weather Reports

**File**: `actions/weather_report.py`

- Live weather data fetched for user's configured location in memory.
- Provides current temperature, condition indicators, and precipitation forecast.

---

## Native Smart Reminders

**File**: `actions/reminder.py`

- Leverages native operating system daemons without third-party bloat:
  - **Windows:** Windows Task Scheduler (`schtasks`)
  - **macOS:** `launchd` / LaunchAgents
  - **Linux:** `systemd --user` timers
- Persistent reminders fire even if ZEZO is temporarily closed.

---

## Proactive Audio (Gemini Live)

**File**: `main.py` (`_build_config()`)

```python
if get_proactive_audio_enabled():
    cfg["proactivity"] = types.ProactivityConfig(proactive_audio=True)
```

- When enabled, Google Gemini Live's native acoustic model analyzes background noise and human speech cadence to differentiate between speech directed at ZEZO versus ambient room chatter, remaining silent when appropriate.

---

## Summary Matrix

| Subsystem | Source File | Trigger / Frequency | Output Mode |
|-----------|-------------|---------------------|-------------|
| **Task Completion Watcher** | `main.py:2940` | Polls every 2s (3s post-speech cushion) | 1-Sentence Voice + HUD Canvas |
| **Morning Briefing** | `actions/proactive.py` | Once per boot upon wake | Spoken Overview + HUD Digest |
| **Proactive 2.0** | `actions/proactive.py` | Contextual idle check-in | 1–2 Sentence Voice Prompt |
| **Topic Monitor** | `actions/background_monitor.py` | Daily scheduled poll | Conversational Voice Alert |
| **Hardware Telemetry** | `actions/system_monitor.py` | Continuous background loop | WebSocket Telemetry + Critical Alerts |
| **Reminders** | `actions/reminder.py` | OS-native scheduler | Native System Notification + Voice |
| **Proactive Audio** | `main.py` | Continuous PCM streaming | Acoustic Silence Gate |
