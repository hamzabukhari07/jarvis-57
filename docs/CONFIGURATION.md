# JARVIS — Configuration

## Overview

JARVIS stores all configuration in `config/api_keys.json`. All configuration is read/written via `memory/config_manager.py`.

## Configuration File

**File**: `config/api_keys.json`

```json
{
    "gemini_api_key": "...",
    "assistant_name": "JARVIS",
    "user_name": "",
    "voice_name": "Charon",
    "wake_word_enabled": false,
    "push_to_talk_enabled": false,
    "hud_style": "face",
    "thinking_enabled": false,
    "proactive_audio": true,
    "turn_tuning": {...},
    "media_resolution": "medium",
    "morning_brief_enabled": true,
    "input_device": "",
    "output_device": "",
    "plugins_enabled": {...},
    "plugin_config": {...},
    "llm_provider": "ollama",
    "llm_url": "http://localhost:11434",
    "llm_model": "llama3.2"
}
```

**Git-ignored**: Yes
**Security**: Plaintext

## Environment Variables

JARVIS does **not** rely on environment variables for configuration. All settings are stored in `config/api_keys.json`.

The only environment variables used are:
- `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `HF_DATASETS_OFFLINE` — temporarily cleared for model downloads
- `USE_TF=0` — prevents TensorFlow import in TTS
- `TOKENIZERS_PARALLELISM=false` — prevents tokenizer parallelism issues

## API Key

| Variable | Location | Default | Purpose |
|----------|----------|---------|---------|
| `gemini_api_key` | `config/api_keys.json` | None (required) | Gemini API access |

## Assistant Configuration

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| Name | `assistant_name` | "JARVIS" | Assistant identity |
| User Name | `user_name` | "" | How the assistant addresses the user |
| Voice | `voice_name` | "Charon" | Gemini Live voice |
| HUD Style | `hud_style` | "face" | "face" or "core" |

## Available Voices

```
Charon, Puck, Kore, Fenrir, Aoede
```

## Feature Toggles

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| Wake Word | `wake_word_enabled` | false | Local "Hey Jarvis" detection |
| Push-to-Talk | `push_to_talk_enabled` | false | Hold key to speak |
| Thinking | `thinking_enabled` | false | Server reasoning budget |
| Proactive Audio | `proactive_audio` | true | Stay silent when speech not addressed |
| Morning Briefing | `morning_brief_enabled` | true | On first boot greeting |

## Turn Tuning

```json
{
    "turn_tuning": {
        "enabled": false,
        "silence_ms": 550,
        "prefix_ms": 150,
        "end_sensitivity": "high",
        "start_sensitivity": "default"
    }
}
```

| Parameter | Range | Default | Purpose |
|-----------|-------|---------|---------|
| `enabled` | boolean | false | Enable turn tuning |
| `silence_ms` | 200-3000 | 550 | Server waits through a pause |
| `prefix_ms` | 0-1000 | 150 | Prefix padding |
| `end_sensitivity` | "high"/"low"/"default" | "high" | How quickly speech ends |
| `start_sensitivity` | "high"/"low"/"default" | "default" | How quickly speech starts |

## Media Resolution

| Value | Meaning |
|-------|---------|
| `default` | Full resolution |
| `low` | Cheaper, loses small text |
| `medium` | Default, keeps on-screen text readable |
| `high` | Full detail |

## Audio Devices

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| Input device | `input_device` | "" (system default) | Microphone by name |
| Output device | `output_device` | "" (system default) | Speakers by name |

## Plugin Configuration

| Setting | Key | Purpose |
|---------|-----|---------|
| Enabled plugins | `plugins_enabled` | `{plugin_name: true/false}` |
| Plugin settings | `plugin_config` | `{namespace: {key: value}}` |

## Local LLM Configuration

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| Provider | `llm_provider` | "ollama" | "ollama" or "openai" |
| URL | `llm_url` | "http://localhost:11434" | LLM server URL |
| Model | `llm_model` | "llama3.2" | LLM model name |

## Plugin Settings Schema

Plugins can declare `PLUGIN_SETTINGS` for the settings UI:
```python
PLUGIN_SETTINGS = {
    "namespace": "my_plugin",
    "title": "My Plugin",
    "fields": [...],
    "action": "connect",
}
```

## Configuration Functions

**File**: `memory/config_manager.py`

All settings accessed via getter/setter functions:
- `get_voice()`, `save_voice()`
- `get_wake_word_enabled()`, `save_wake_word_enabled()`
- `get_push_to_talk_enabled()`, `save_push_to_talk_enabled()`
- `get_assistant_name()`, `save_assistant_config()`
- `get_input_device()`, `save_input_device()`
- `get_plugin_enabled()`, `save_plugin_enabled()`
- `get_plugin_config()`, `save_plugin_config()`
- `get_turn_tuning()`, `save_turn_tuning()`
- `get_media_resolution()`, `save_media_resolution()`
- `get_thinking_enabled()`, `save_thinking_enabled()`
- `get_proactive_audio_enabled()`, `save_proactive_audio_enabled()`

## Summary

```
All config in: config/api_keys.json (git-ignored)
No env vars for app configuration
All access via memory/config_manager.py
Settings: API key, name, voice, toggles, devices, tuning, LLM
Voices: Charon, Puck, Kore, Fenrir, Aoede
Toggles: wake_word, push_to_talk, thinking, proactive_audio
Plugin config: {name: enabled} + {namespace: settings}
```