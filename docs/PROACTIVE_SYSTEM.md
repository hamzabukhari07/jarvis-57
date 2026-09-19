# JARVIS — Proactive System

## Overview

JARVIS has several **background proactive features** that run without explicit user commands.

**Files**: `actions/proactive.py`, `actions/background_monitor.py`, `actions/reminder.py`, `actions/system_monitor.py`

## Morning Briefing

**File**: `actions/proactive.py`

```python
# Fires once per process on first boot
# Checks: _briefing_sent flag
# Content:
#   - Greeting based on time of day
#   - Time/date
#   - Recap of last session (from memory/long_term.json["sessions"])
#   - Live news headlines
```

**Key behavior**: Session summaries are consumed after use — the morning briefing reads the last session, then `pop_last_session()` removes it from the queue. It never repeats.

## Proactive 2.0

**File**: `actions/proactive.py`

```python
class ProactiveEngine:
    # Time-aware, context-aware check-ins
    # Knows time of day, user's projects, what's been discussed
    # Checks periodically
    # Says something genuinely useful, timely, or caring
    # 1-3 short sentences
    # Calls no tools
```

**Trigger**: `[PROACTIVE_CHECK]` tag in system prompt → user has been quiet for a while.

## Background Monitoring

**File**: `actions/background_monitor.py`

```python
# User-configurable topic watching
# Checks for new headlines once a day
# Alerts naturally when new developments found
# Commands: add, remove, list
```

**Constraints**: No crypto, financial, or trading topics allowed.

## Hardware Monitoring

**File**: `actions/system_monitor.py`

```python
class SystemMonitor:
    # Continuous CPU, RAM, GPU, temperature telemetry
    # Uses psutil library
    # Localized voice alerts
    # Cooldown-based reporting
```

## Weather Report

**File**: `actions/weather_report.py`

- Live weather data for user's city
- Personalized from memory (location)
- Temperature, conditions, forecasts

## Smart Reminders

**File**: `actions/reminder.py`

```
Windows: Task Scheduler
macOS: LaunchAgent
Linux: systemd
```

OS-native scheduled notifications — no extra Python packages needed.

## Proactive Audio

**File**: `main.py`, `_build_config()`

```python
if get_proactive_audio_enabled():
    cfg["proactivity"] = types.ProactivityConfig(proactive_audio=True)
```

This allows Gemini to detect speech not addressed to it and stay quiet.

## Summary

```
Morning briefing: Once per process, uses session memory
Proactive 2.0: Time/context-aware check-ins
Background monitoring: User-configured topic watching
Hardware monitoring: CPU/RAM/GPU/temperature telemetry
Weather: Live data personalized from memory
Reminders: OS-native scheduled notifications
Proactive audio: Gemini detects non-addressed speech
```