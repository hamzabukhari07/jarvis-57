# ⚙️ ZEZO — Settings & Configuration System

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Source of Truth:** ReUI Design System & Atomic Config Store (`config/api_keys.json`)  
> **Target OS:** Windows (Primary), macOS, Linux  

---

## 🧭 Overview

ZEZO provides a unified, reactive **10-Tab ReUI Settings Hub** (`frontend/src/components/settings/SettingsModal.tsx`). It consolidates runtime interaction behavior, speech and audio hardware routing, autonomous coding engines, declarative agent skills, themes, remote Cloudflare tunnels, credentials, and telemetry into a single cohesive control center.

All configuration updates persist atomically to `config/api_keys.json` with multi-attempt transactional staging (`os.replace`) to guarantee zero corruption even during sudden restarts or concurrent background writes.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ZEZO 9-TAB REUI SETTINGS HUB                          │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ Sidebar Groups  │ Modular Settings Tabs                                     │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ CONTROLS        │ 1. ⚙️ General (Interaction modes, autostart, reasoning)    │
│                 │ 2. 🎙️ Audio/Voice (Endpoints, mic meter, sample rate)     │
│                 │ 3. 💻 Code Engines (Antigravity, OpenCode, Kilo Code)     │
│                 │ 4. ✨ Skills (Declarative plugins, SKILL.md editor)        │
│                 │ 5. 🎨 Appearance (OKLCH themes, Qivi 3D WebGL hologram)   │
├─────────────────┼───────────────────────────────────────────────────────────┤
│ GATEWAY / SYSTEM│ 6. 🌐 Cloudflare Tunnel (Quick Tunnels, mobile pairing)   │
│                 │ 7. 🔑 Providers (Gemini, Groq, Tavily, ElevenLabs keys)   │
│                 │ 8. 📊 Telemetry (Latency metrics, log bus, health)        │
│                 │ 9. ℹ️ About (Creator: Hamza Bukhari, build, version)       │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

---

## 🗂️ The 10 Modular ReUI Settings Tabs

### 1. ⚙️ General & Quick Controls
Configures conversational turn-taking, startup lifecycle, and reasoning:
- **Interaction Modes**: Mutually exclusive 3-way segmented selector:
  - `Always Listening` (`always_listening`): Open mic; Gemini Live server VAD handles turns.
  - `Wake Word` (`wake_word`): Passive standby; wakes on *"Hey Zezo"* for a 15s window.
  - `Push-To-Talk` (`push_to_talk`): Mic open strictly while holding `Ctrl+Alt`.
- **Morning Briefing (`morning_brief_enabled`)**: Weather, calendar, and system briefing on first launch of the day.
- **Auto-Start on Boot (`autostart_enabled`)**: Creates Windows startup shortcut (`shell:startup`).
- **Extended Reasoning (`thinking_enabled`)**: Enables step-by-step chain-of-thought rationale.
- **Proactive Audio (`proactive_audio_enabled`)**: Spoken status hints and task completion alerts.

### 2. 🎙️ Audio/Voice Pipeline
Hardware endpoints and acoustic signal calibration:
- **Input Endpoint (`input_device`)**: Selects physical microphone; auto-follows system default if empty.
- **Output Endpoint (`output_device`)**: Selects physical speaker; auto-follows system default if empty.
- **Live Mic Test Meter**: Real-time volume RMS calculation rendered via `ui.set_mic_level`.
- **Acoustic Self-Echo Guard**: Filter window (`_out_latency + _TAIL_MARGIN`) preventing self-interruption.
- **Explicit Sample Rate**: Enforces `types.Blob(data=..., mime_type="audio/pcm;rate=16000")`.
- **Zero-Crash Disconnect Fallback**: Graceful fallback to silent/text/remote mode if hardware is unplugged.

### 3. 💻 Autonomous Code Engines
Manages external agentic coding CLIs:
- **Engines Managed**: Google DeepMind Antigravity CLI (`antigravity`), OpenCode (`opencode`), Kilo Code (`kilo`).
- **Readiness Probing**: Status detection (`ready`, `sign_in_required`, `not_installed`, `off`).
- **Default Engine (`default_code_engine`)**: Sets which CLI handles general autonomous coding requests.
- **REST Endpoints**: Backed by `/api/code_engines` and `actions/code_engines_status.py`.

### 4. ✨ Declarative Skills Hub
Extensible skill registry and in-place directive editor:
- **Skill Format**: Standardized `skills/<skill_name>/SKILL.md` packages.
- **Multi-Stage Security Scanner**: Scans for prompt injection, base64 obfuscation, and token hijacking.
- **Mode Controls**: Pin, disable, or set auto-activation for individual skills.
- **REST Endpoints**: Backed by `/api/skills` (`/mode`, `/install`, `/save`, `/delete`).

### 5. 🎨 Appearance & Themes
Perceptual OKLCH themes and 3D WebGL particle companion:
- **OKLCH Color Systems**:
  - `Terracotta` (`copper`): Warm baked clay, obsidian cards, copper-amber accents.
  - `Neo Mint` (`emerald`): Deep obsidian with electric cyber-emerald and neo-mint highlights.
  - `Arctic Teal` (`arctic-teal`): Slate obsidian paired with oceanic teal.
  - `Cobalt` (`cobalt`): Pitch obsidian with radiant electric blue.
  - `Amethyst` (`indigo`): Charcoal slate with vibrant violet accents.
- **Qivi 3D WebGL Avatar (`QiviAvatarVisualizer`)**:
  - WebGL point-cloud companion rendered via Three.js with audio-reactive viseme morphing.
  - Archetypes (`qivi`, `female`/Nova, `male`/Sol, `ember`, `sage`, `atlas`).
  - Shapes (`blob`, `shield`, `star`, `hex`, `heart`).

### 6. 🌐 Cloudflare Tunnel & Remote Gateway
Zero-configuration remote access for smartphones and remote browsers:
- **Dual Connectivity**: High-speed LAN Direct (`http://<LAN_IP>:8000`) and Cloudflare Quick Tunnels (`https://*.trycloudflare.com`).
- **Public DNS Verification**: Direct query to `dns.google` bypassing local ISP negative DNS caches.
- **QR Code Pairing**: High-contrast QR code with ephemeral 6-character token (`TTL = 600s`).

### 7. 🔑 Providers & API Credentials
Centralized provider management with live pre-flight validation probes:
- `gemini_api_key`: Google Gemini Live bidirectional WebSocket, multimodal vision, tool execution.
- `groq_api_key`: Fast Groq LPU inference for Whisper STT and fallback routing.
- `elevenlabs_api_key`: Optional ElevenLabs HD neural voice synthesis.
- `tavily_api_key`: Real-time web intelligence and clean content scraping.

### 8. 📊 Telemetry & System Status
Comprehensive diagnostics and activity monitoring:
- **Live Latency Logging**: Measures roundtrip STT, LLM TTFT (Time-To-First-Token), and TTS TTFA (Time-To-First-Audio).
- **Log Bus**: Streaming WebSocket event log bus categorized by severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- **Hardware Telemetry**: Real-time CPU, RAM, and GPU VRAM utilization metrics.

### 9. ℹ️ About
System provenance and architecture attributions:
- **Creator & Lead Architect**: **Hamza Bukhari**.
- **Runtime Version**: Active build commit and environment details.
- **Core Principles**: ReUI component consistency, strict 3-layer verification, non-blocking execution.

---

## 📡 REST API Schemas for Settings & Workspace Subsystems

### 1. `/api/code_engines` (Code Engine Management)

#### `GET /api/code_engines`
Returns detection status for all registered coding CLIs.
```json
// Response (200 OK)
{
  "status": "success",
  "engines": {
    "antigravity": {
      "id": "antigravity",
      "name": "Antigravity CLI",
      "binary_path": "C:\\Users\\Hamza\\AppData\\Roaming\\npm\\agy.cmd",
      "installed": true,
      "state": "ready",
      "model": "gemini-3.8-flash-high",
      "models": ["gemini-3.8-flash-high", "claude-sonnet-4-6"]
    },
    "opencode": {
      "id": "opencode",
      "name": "OpenCode",
      "binary_path": "C:\\Users\\Hamza\\AppData\\Roaming\\npm\\opencode.cmd",
      "installed": true,
      "state": "ready",
      "model": "glm-5.3-flash-free",
      "models": ["glm-5.3-flash-free", "nemotron-3-ultra-free"]
    },
    "kilo": {
      "id": "kilo",
      "name": "Kilo Code",
      "binary_path": null,
      "installed": false,
      "state": "not_installed",
      "model": "kilo/free",
      "models": []
    }
  },
  "default_engine": "antigravity"
}
```

#### `POST /api/code_engines/probe`
Forces an immediate CLI re-probe (bypassing 5-minute cache).
```json
// Request Body
{
  "engine_id": "antigravity" // Optional: probe specific or omit for all
}

// Response (200 OK)
{
  "status": "success",
  "engines": { ... },
  "default_engine": "antigravity"
}
```

#### `POST /api/code_engines/default`
Sets the active default code engine.
```json
// Request Body
{
  "engine_id": "opencode"
}

// Response (200 OK)
{
  "status": "success"
}
```

---

### 2. `/api/skills` (Declarative Skills Management)

#### `GET /api/skills`
Fetches all discovered declarative skill packages and categories.
```json
// Query Params: ?domain=coding (optional)
// Response (200 OK)
{
  "status": "success",
  "skills": [
    {
      "name": "hamza_taste",
      "domain": "design",
      "description": "Master Studio UI Anti-Slop Directive and reference-first design protocols.",
      "pinned": true,
      "disabled": false,
      "auto_activate": true,
      "path": "skills/hamza_taste/SKILL.md",
      "triggers": ["design", "ui", "reui", "styling"]
    }
  ],
  "domains": ["coding", "design", "research", "system", "media", "orchestration"]
}
```

#### `POST /api/skills/mode`
Toggles pinned, disabled, or auto-activation state.
```json
// Request Body
{
  "name": "hamza_taste",
  "pinned": true,
  "disabled": false,
  "auto_activate": true
}

// Response (200 OK)
{
  "status": "success",
  "name": "hamza_taste",
  "pinned": true,
  "disabled": false,
  "auto_activate": true
}
```

#### `POST /api/skills/save`
Synthesizes or updates a `SKILL.md` directive package on disk.
```json
// Request Body
{
  "name": "custom_react_audit",
  "description": "Strict React 18 component structure checker.",
  "instructions": "# React Audit\n1. Check useEffect cleanup.\n2. Ensure memoization.",
  "domain": "coding",
  "author": "Hamza Bukhari",
  "triggers": ["react", "audit"]
}

// Response (200 OK)
{
  "status": "success",
  "message": "Skill 'custom_react_audit' saved successfully",
  "skills": [ ... ]
}
```

#### `POST /api/skills/delete`
Deletes a skill package from disk.
```json
// Request Body
{
  "name": "custom_react_audit"
}

// Response (200 OK)
{
  "status": "success",
  "message": "Skill deleted",
  "skills": [ ... ]
}
```

---

### 3. `/api/tasks` (Background Task System)

#### `GET /api/tasks`
Returns all background parent tasks categorized for task tracking modals.
```json
// Response (200 OK)
{
  "status": "success",
  "tasks": [
    {
      "id": "task_9f8a1b2c",
      "title": "Clone and rebuild stripe.com",
      "status": "running",
      "progress": 0.45,
      "created_at": 1729601000.5,
      "subtasks": [
        {"id": "sub_1", "title": "Capture DOM scenario", "status": "done"},
        {"id": "sub_2", "title": "Export Vite template", "status": "running"}
      ],
      "cancellable": true
    }
  ]
}
```

---

## 🛠️ Adding New Settings (Developer Guidelines)

When introducing a new configuration option:
1. **Extend `config/api_keys.json` schema**: Define default values and getters/setters in `memory/config_manager.py`.
2. **ReUI Components Only**: Build UI controls using ReUI primitives (`Switch`, `Input`, `Select`, `Card`, `Badge`). Never introduce unstyled raw HTML inputs.
3. **No `transition: all`**: Specify explicit transition properties (`transition-colors`, `transition-transform`) to preserve 60 FPS animation performance.
4. **Preserve `_zezoAnimActive`**: Ensure modal open/close hooks correctly toggle background rendering when settings panels are active.
5. **Verify All 3 Layers**: Run `py_compile`, verify runtime behavior with test scripts, and document changes in `LEARNING_JOURNAL.md`.
