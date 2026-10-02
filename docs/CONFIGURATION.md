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
    "proactive_audio": false,
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

## API Credentials Configuration Hub

ZEZO features a dedicated **API Credentials Configuration** hub (`#api-keys-modal` / `/api/settings/keys`) accessible directly from the Settings drawer or the Voice Pipeline modal.

### Supported Providers & Pre-Flight Probes

| Variable | Provider | Required / Optional | Probe Verification | Purpose |
|---|---|---|---|---|
| `gemini_api_key` | Google Gemini | Required (Default) | Real 1-token REST probe (`gemini-2.5-flash` / `gemini-3.6-flash`) | Gemini Live Voice, Screen Vision, Grounded Search & Autonomous Synthesis |
| `groq_api_key` | Groq LPU | Optional (Cascade/STT) | Real chat completion probe (`qwen/qwen-2.5-32b` / `llama-3.3-70b-versatile`) | Ultra-fast LPU inference for Cascade LLM and Groq Whisper STT |
| `elevenlabs_api_key` | ElevenLabs | Optional (Cascade TTS) | Real user subscription probe (`/v1/user`) | Premium ultra-realistic HD voice cloning & synthesis in Cascade TTS |

All keys are validated with real live pre-flight probes before saving to local `config/api_keys.json` (git-ignored) via transactional atomic write (`os.replace`).

## Three-Modal Settings Architecture

1. **🔑 API Configuration (`#api-keys-modal`)**: Centralized single source of truth for all external API keys with live status badges, masked preview (`AIza••••ABCD`), and show/hide toggles.
2. **⚙️ Customise Assistant (`#customise-modal`)**: Pure assistant identity (Name, Response Language) and dynamic voice persona selector that automatically adjusts its available voice list based on the active voice engine.
3. **🎙️ Voice Pipeline (`#pipeline-modal`)**: Architecture switcher (Gemini Live vs Cascade Loop), STT/LLM/TTS 2x2 grid, one-click presets, automatic failover toggle, and real-time Provider Credentials status tags with a direct link to the API Configuration modal.

## Custom Voice Pipeline (Cascade Mode)

**Default (`live`)**: Gemini Live WebSocket streams audio directly to Google Gemini for 100% integrated STT → LLM → TTS with native tool-calling and barge-in.

**Cascade Mode**: Decouples the voice loop into separate STT, LLM, and TTS engines, enabling offline-first or custom hybrid pipelines. The pipeline runs in `core/voice_fallback.py` with engines injected from config.

### Pipeline Configuration

| Setting | Key | Default | Options | Purpose |
|---------|-----|---------|---------|----------|
| Pipeline mode | `pipeline_mode` | `"live"` | `live` or `cascade` | Gemini Live (default) or custom cascade loop |
| Cascade STT | `stt_engine` | `"groq_whisper"` | `groq_whisper`, `local_whisper`, `vosk` | Speech-to-text engine (used only in cascade mode, default `groq_whisper` for sub-second latency; `local_whisper` uses `tiny` on CPU) |
| Cascade LLM | `llm_engine` | `"groq"` | `groq`, `gemini`, `ollama` | Language model provider (used only in cascade mode) |
| Cascade TTS | `tts_engine` | `"kokoro"` | `kokoro`, `edge_tts`, `elevenlabs` | Text-to-speech engine (used only in cascade mode, auto-sanitizes `lang='en-us'` with EdgeTTS fallback for non-English) |
| Cascade TTS voice | `tts_voice` | `""` (inherits `fallback_voice`) | Engine-specific options | Voice for cascade TTS |

### VAD, Energy Tuning & Low Latency Streaming
In Cascade mode (`core/voice_fallback.py`), voice activity detection uses:
- `DEFAULT_ENERGY = 600.0` RMS threshold to reject ambient background hiss and fan noise.
- `DEFAULT_SILENCE_MS = 180` ms pause duration for fast conversational turn-taking.
- `DEFAULT_MIN_MS = 200` ms minimum utterance length, with voiced block density (>= 40% voiced blocks).
- **Instant Barge-in:** Continuous microphone stream listens during assistant speech and triggers `sounddevice.stop()` when speech energy exceeds `energy * 1.4`.
- **Zero-Latency Fast Intent:** Deterministic command matcher (`_try_fast_intent`) executes volume adjustments, mute, app opening, and time/date queries with 0ms LLM overhead.
- **Streaming Sentence TTS:** `call_groq_stream` yields sentences in ~120ms, starting audio playback immediately on sentence 1 (~150-250ms TTFA).

### How It Works

1. **Live mode** (`pipeline_mode = "live"`): All voice processing happens in Google Gemini Live API. Engine configs are saved but unused. Full tool-calling, barge-in, and real-time conversation.
2. **Cascade mode** (`pipeline_mode = "cascade"`): Local voice loop in `core/voice_fallback.py` dispatches to the configured engines:
   - User speech → `transcribe_utterance(engine=stt_engine)` → text transcript
   - Transcript → `llm_generate(engine=llm_engine)` → AI response
   - Response → `make_tts(engine=tts_engine, voice=tts_voice)` → audio playback

### Configuration Functions

Pipeline settings are accessed via getter/setter functions in `memory/config_manager.py`:
- `get_pipeline_mode()`, `save_pipeline_mode(mode)`
- `get_stt_engine()`, `save_stt_engine(engine)`
- `get_llm_engine()`, `save_llm_engine(engine)`
- `get_tts_engine()`, `save_tts_engine(engine)`
- `get_tts_voice()`, `save_tts_voice(voice)`

Unknown values are automatically sanitized to defaults.

### UI Control

Users configure the voice pipeline via **⚙ Settings → VOICE PIPELINE** modal. Radio buttons switch between Live/Cascade, and dropdowns enable custom engine selection when in Cascade mode. One-click presets (Gemini Live, Cloud Fast, Balanced, Fully Offline) are provided for convenience.

### Feature Toggles

| Setting | Key | Default | Purpose |
|---------|-----|---------|----------|
| Morning Briefing | `morning_brief_enabled` | true | On first boot greeting |

## Turn Tuning

```json
{
    "turn_tuning": {
        "enabled": true,
        "silence_ms": 450,
        "prefix_ms": 100,
        "end_sensitivity": "high",
        "start_sensitivity": "default"
    }
}
```

| Parameter | Range | Default | Purpose |
|-----------|-------|---------|---------|
| `enabled` | boolean | true | Enable turn tuning (responsive end-of-speech) |
| `silence_ms` | 200-3000 | 450 | Server waits through a pause |
| `prefix_ms` | 0-1000 | 100 | Prefix padding |
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

## Groq LPU Coprocessor (Free-Tier Hybrid Ingestion)

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| API key | `groq_api_key` | "" | Enables free-tier Groq acceleration |
| Text model | `groq_model` | `qwen/qwen3.8-27b` | Fast text/code completion (`call_groq_text`) |
| Whisper model | `groq_whisper_model` | `whisper-large-v3-turbo` | Audio/video transcription (`transcribe_groq_whisper`) |
| Vision model | `groq_vision_model` | "" (opt-in) | Image extraction (`call_groq_vision`). Unset by default because Groq's public free tier exposes no multimodal model — images then use the Gemini ladder |

`transcribe_groq_whisper()` caps uploads at Groq's free-tier ~25 MB limit; larger media falls back to the paid Gemini path.

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

## Security, Key Masking & Pre-Flight Verification

1. **Strict Git Sanitization**:
   - `config/api_keys.json` is strictly git-ignored.
   - A public template schema is provided at `config/api_keys.example.json`.
2. **Pre-Flight Live Probes**:
   - Real 1-token probes verify candidate API keys (`validate_gemini_key`, `validate_groq_key`, `validate_elevenlabs_key`) against live provider endpoints before saving.
   - Prevents expired keys, region blocks, quota exhaustion, or invalid formats from corrupting the configuration.
3. **Transactional Staging & Atomic Replace**:
   - Candidate updates are staged in `config/api_keys.json.tmp`.
   - On successful validation, atomic replacement via `os.replace` commits the file, preventing zero-byte corruption during crashes.
   - If validation fails, changes roll back and the active configuration remains untouched with HTTP 400 status.
4. **UI Masking**:
   - Keys are never broadcast raw over WebSockets. Masked representations (`get_masked_gemini_key()`, `get_masked_groq_key()`) ensure UI status badges (`✓ SAVED (AIzaSy••••••••3456)`) render safely.
   - Masked strings (`••••••••`) submitted in UI forms are automatically guarded from overwriting real active keys.

## Model Configuration

| Setting | Key | Default | Purpose |
|---------|-----|---------|---------|
| OpenCode Model | `opencode_model` | `opencode/nemotron-3-ultra-free` | Autonomous multi-file coding agent model |
| Kilo Model | `kilo_model` | `kilo/kilo-auto/free` | Lightweight fast refactoring model |
| Antigravity Model | `antigravity_model` | `gemini-3.7-flash-medium` | Core planning & agent synthesis model |

## Configuration Functions

**File**: `memory/config_manager.py` (Lead Architect: Hamza Bukhari)

All settings accessed via getter/setter functions:
- `get_gemini_key()`, `save_api_keys()`, `save_api_keys_transactional()`, `is_configured()`
- `validate_gemini_key()`, `validate_groq_key()`, `validate_elevenlabs_key()`
- `get_masked_gemini_key()`, `get_masked_groq_key()`
- `get_groq_api_key()`, `get_groq_model()`, `get_groq_vision_model()`, `get_groq_whisper_model()`, `save_groq_config()`
- `get_opencode_model()`, `get_kilo_model()`, `get_antigravity_model()`
- `get_voice()`, `save_voice()`
- `get_response_language()`, `save_response_language()`
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
All config in: config/api_keys.json (git-ignored, template: config/api_keys.example.json)
Transactional: Pre-flight live probes + atomic staging (_atomic_write_config)
No env vars for app configuration
All access via memory/config_manager.py
Settings: API keys, name, voice, response language, models, toggles, devices, tuning, LLM
Voices: Charon, Puck, Kore, Fenrir, Aoede
Masking: get_masked_gemini_key(), get_masked_groq_key() for secure UI status display
Onboarding: Automatic #onboarding-modal trigger when is_configured() is False
Toggles: wake_word, push_to_talk, thinking, proactive_audio
Plugin config: {name: enabled} + {namespace: settings}
```