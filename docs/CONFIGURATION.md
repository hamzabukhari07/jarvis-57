# ⚙️ ZEZO — Configuration Architecture & Schema

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Detailed UI Guide:** See [`docs/SETTINGS.md`](./SETTINGS.md) for full documentation of the modern 9-tab ReUI settings interface.  
> **Target OS:** Windows (Primary), macOS, Linux  

---

## 🧭 Overview

ZEZO centralizes all persistent application settings, provider credentials, hardware endpoints, and agent preferences in `config/api_keys.json`. Access is managed exclusively through the atomic transactional layer in `memory/config_manager.py`.

---

## 📄 Configuration Store: `config/api_keys.json`

**File Location:** `config/api_keys.json`  
**Git Status:** Strictly git-ignored (`.gitignore`)  
**Concurrency Model:** Atomic transactional replacement (`os.replace` with `.tmp` staging) to prevent file corruption during concurrent operations or sudden process termination.

### Canonical Schema

```json
{
  "gemini_api_key": "AIzaSy...",
  "groq_api_key": "gsk_...",
  "elevenlabs_api_key": "",
  "tavily_api_key": "tvly-...",
  "assistant_name": "Zezo",
  "user_name": "Hamza Bukhari",
  "voice_name": "Charon",
  "voice_accent": "auto",
  "response_language": "auto",
  "theme": "copper",
  "accent": "#ea580c",
  "avatar_preset": "qivi",
  "avatar_shape": "blob",
  "avatar_theme": "match_theme",
  "avatar_quality": "high",
  "avatar_lighting": 1.0,
  "wake_word_enabled": false,
  "push_to_talk_enabled": false,
  "autostart_enabled": false,
  "thinking_enabled": false,
  "proactive_audio_enabled": false,
  "morning_brief_enabled": true,
  "input_device": "",
  "output_device": "",
  "default_code_engine": "antigravity",
  "plugins_enabled": {},
  "plugin_config": {}
}
```

---

## 🗂️ The 9 Modular ReUI Settings Tabs

The frontend settings interface (`frontend/src/components/settings/SettingsModal.tsx`) maps cleanly into 9 functional tabs:

1. **⚙️ General**: Turn-taking mode selection (`always_listening`, `wake_word`, `push_to_talk`), Windows autostart daemon, morning briefing, and extended reasoning (`thinking_enabled`).
2. **🎙️ Audio/Voice**: Microphone and speaker endpoint configuration (`input_device`, `output_device`), live mic volume RMS test meter, and hardware disconnect resilience.
3. **🤖 Persona**: Identity (`assistant_name`), Live voice profile (`voice_name`), Voice accent & dialect enunciation (`voice_accent`), response language mode (`response_language`), and 3D companion avatar presets.
4. **💻 Code Engines**: Readiness probing and defaults for local coding CLIs (Antigravity CLI, OpenCode, Kilo Code). Backed by `GET /api/code_engines`.
5. **✨ Skills**: Declarative skill packages (`skills/<name>/SKILL.md`), security scanner, and in-place directive editor. Backed by `GET /api/skills`.
6. **🎨 Appearance**: OKLCH perceptual color palettes (`copper`, `emerald`, `arctic-teal`, `cobalt`, `indigo`) and Qivi 3D WebGL point-cloud avatar companion visualizer.
7. **🌐 Cloudflare Tunnel**: Zero-config reverse tunnels via `cloudflared`, public DNS verification via `dns.google`, and QR code mobile pairing.
8. **🔑 Providers**: Centralized API keys hub with pre-flight validation probes (Gemini, Groq, ElevenLabs, Tavily).
9. **📊 Telemetry**: Live latency instrumentation (STT, LLM TTFT, TTS TTFA), WebSocket event log bus, and system load monitors.
10. **ℹ️ About**: Creator attribution (**Hamza Bukhari**), software version, and architectural overview.

---

## 📡 Core Settings & Task REST Endpoints

| Endpoint | Method | Handled Subsystem | Schema Reference |
|---|---|---|---|
| `/api/code_engines` | `GET` | Probes status of all coding engines | [`docs/SETTINGS.md`](./SETTINGS.md#1-apicode_engines-code-engine-management) |
| `/api/code_engines/probe` | `POST` | Forces fresh CLI re-probe | [`docs/SETTINGS.md`](./SETTINGS.md#post-apicode_enginesprobe) |
| `/api/code_engines/default` | `POST` | Sets default code engine | [`docs/SETTINGS.md`](./SETTINGS.md#post-apicode_enginesdefault) |
| `/api/skills` | `GET` | Lists all discovered declarative skills | [`docs/SETTINGS.md`](./SETTINGS.md#2-apiskills-declarative-skills-management) |
| `/api/skills/mode` | `POST` | Updates skill mode (pinned, disabled) | [`docs/SETTINGS.md`](./SETTINGS.md#post-apiskillsmode) |
| `/api/skills/save` | `POST` | Saves or updates `SKILL.md` directive | [`docs/SETTINGS.md`](./SETTINGS.md#post-apiskillssave) |
| `/api/skills/delete` | `POST` | Deletes a skill package from disk | [`docs/SETTINGS.md`](./SETTINGS.md#post-apiskillsdelete) |
| `/api/tasks` | `GET` | Fetches background parent tasks | [`docs/SETTINGS.md`](./SETTINGS.md#3-apitasks-background-task-system) |

---

## 🎙️ Active Conversational Voice Configuration

Per **AGENTS.md Rule 6**, the active live voice pipeline runs strictly via Google Gemini Live API WebSockets bidirectional streaming (`main.py`):
- Direct PCM mic capture streamed to Gemini Live with explicit sample rate metadata (`types.Blob(data=..., mime_type="audio/pcm;rate=16000")`). Never send bare `audio/pcm`.
- Push-to-Talk is bound strictly to `Ctrl+Alt`.
- Hardware errors gracefully fall back to silent/text/remote mode without crashing the live session `TaskGroup`.

### Turn Tuning Parameters

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

| Parameter | Type | Default | Description |
|---|---|---|---|
| `enabled` | boolean | `true` | Enables active turn sensitivity tuning |
| `silence_ms` | integer | `450` | Milliseconds of silence before server commits turn |
| `prefix_ms` | integer | `100` | Padding audio frames attached to start of speech |
| `end_sensitivity` | string | `"high"` | Sensitivity for detecting completion of user speech |

---

## 🧠 Fast-Path Hybrid Memory Engine Environment Flags

The Fast-Path Hybrid Memory Engine (Option 1) provides zero-latency fact ingestion, an atomic write-ahead journal, in-memory Read-Your-Writes consistency, and turn read budgets governed by the following environment variables:

| Environment Variable | Default | Type | Role & Description |
|---|---|---|---|
| `ZEZO_UNIFIED_MEMORY_TOOL` | `true` | boolean | When `true`, exposes the canonical `actions/memory_tool.py` (`memory` tool) and dynamically disables `actions/recall_history.py`. If `false`, re-enables legacy recall actions. |
| `ZEZO_MEMORY_ASYNC_OUTBOX` | `true` | boolean | When `true`, routes fact writes through the asynchronous outbox queue and write-ahead journal (`outbox_journal.jsonl`). If `false`, executes synchronous fallback writes. |
| `ZEZO_PRETURN_RECALL` | `true` | boolean | When `true`, executes bounded (<=180ms) lexical prefetch for typed chat prompts in `main.py` (`_on_text_command`). Live audio pipelines remain untouched. |
| `ZEZO_MEMORY_READ_BUDGET` | `3` | integer | Maximum memory read queries allowed per conversational turn. Enforced at tool dispatch in `main.py`. |
| `ZEZO_MEMORY_BUDGET_WINDOW_SEC` | `8.0` | float | Inactivity window in seconds before the turn memory read budget resets automatically. |

---

## 🔀 Dual Operational Modes: Chat Mode vs. Live Voice Mode

ZEZO features strict dual operational mode decoupling synchronized across the React frontend and Python daemon via WebSockets (`{ "type": "operational_mode", "mode": "chat" | "live" }`):

| Operational Mode | Primary UI View | Microphone Input | Audio Speaker Output | Purpose & Experience |
|---|---|---|---|---|
| **`chat`** | Text Chat Thread (`ZezoChatThread.tsx`) | Completely Gated (Dropped in `_listen_audio()`) | Completely Suppressed (Dropped in `_drop_assistant_audio()`) | Distraction-free, silent ChatGPT-style text workspace. Zero unsolicited voice audio from speakers; zero room audio sent to LLM. |
| **`live`** | 3D Voice Avatar (`VortexAvatar.tsx`) | Open Bidirectional Audio (PCM stream to Gemini Live) | Full Duplex Vocal Playback (`_play_audio()`) | High-speed bidirectional vocal conversation with emotional prosody and real-time barge-in support. |

### Operational Mode Switch Safety & Race Condition Guard
When switching from `live` to `chat`:
1. `ZezoLive._on_operational_mode_change("chat")` executes immediate `interrupt()`.
2. Both `audio_in_queue` and `out_queue` are flushed synchronously to prevent delayed or buffered speech playback.
3. UI state broadcasts mode changes across all connected clients via `core/ui_server.py`.


