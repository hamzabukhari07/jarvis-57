# JARVIS — Storage

## Overview

Everything stored locally on the user's machine. No cloud storage.

**File locations**: `config/api_keys.json`, `memory/long_term.json`, `config/certs/`

## Complete Storage Inventory

### 1. API Keys & Configuration

| Storage | Location | Format | Purpose | Read by | Written by |
|---------|----------|--------|---------|---------|------------|
| API keys | `config/api_keys.json` | JSON | Gemini key, assistant name, voice, toggles | `memory/config_manager.py` | UI settings |
| API file | `config/api_keys.json` | JSON | `gemini_api_key` field | `core/gemini.py`, `core/llm_client.py` | Setup/configuration |

**Git-ignored**: Yes (listed in `.gitignore`)
**Security**: Plaintext — treat like a password file

### 2. Memory

| Storage | Location | Format | Purpose | Read by | Written by |
|---------|----------|--------|---------|---------|------------|
| Long-term memory | `memory/long_term.json` | JSON | All stored facts, sessions | `memory/memory_manager.py` | `save_memory` tool, session summary |

**Git-ignored**: Yes
**Size**: Soft limit 200k characters
**Structure**: identity, preferences, projects, relationships, wishes, notes, sessions

### 3. Dashboard Certificates

| Storage | Location | Format | Purpose | Read by | Written by |
|---------|----------|--------|---------|---------|------------|
| TLS cert + key | `config/certs/` | PEM | Self-signed for dashboard | `dashboard/server.py` | Generated locally |

**Git-ignored**: Yes
**Security**: Self-signed, never leaves machine

### 4. Face Model

| Storage | Location | Format | Purpose |
|---------|----------|--------|---------|
| Face mesh | `core/face_model.obj` | OBJ | MediaPipe canonical face model (468 vertices) |

**Git-tracked**: Yes (Apache 2.0 license)
**Size**: 25 KB

### 5. Playwright Browsers

| Storage | Location | Format | Purpose |
|---------|----------|--------|---------|
| Chromium/Firefox | System browser cache | Binary | Browser automation |

Installed via `python setup.py`

### 6. Wake Word Model (Optional)

| Storage | Location | Format | Purpose |
|---------|----------|--------|---------|
| Model files | `openwakeword/resources/models/` | ONNX/TFLite | "Hey Jarvis" detection |

Installed via `pip install openwakeword` + `download_models()`

### 7. Ollama Model (Optional)

| Storage | Location | Format | Purpose |
|---------|----------|--------|---------|
| Model files | `~/.ollama/models/` | GGUF | Local LLM backend |

Installed via `ollama pull`

### 8. Log/Console Output

| Storage | Location | Format | Purpose |
|---------|----------|--------|---------|
| Console | stdout/stderr | Text | Full boot transcript, debug |
| Activity log | UI text widget | Text | User-facing conversation log |

**Never stored to disk**: Console output is ephemeral.

## Storage Characteristics

| Property | Detail |
|----------|--------|
| Format | JSON for structured data, OBJ for 3D model, PEM for certs |
| Encoding | UTF-8 everywhere |
| Thread safety | `threading.Lock()` for JSON files |
| Git tracking | Config, certs, memory excluded via `.gitignore` |
| Persistence | File-based, survives restarts |
| Backup | User responsibility |

## Data Flow for Memory

```
User says something worth remembering
    ↓
save_memory tool called
    ↓
update_memory() → load_memory() → recursive_update()
    ↓
trim_to_limit() → if > 200k chars, delete oldest
    ↓
json.dumps(indent=2, ensure_ascii=False)
    ↓
write to memory/long_term.json
```

## Summary

```
api_keys.json: Config, API key, toggles (git-ignored)
long_term.json: All memory facts and sessions (git-ignored)
certs/: Dashboard TLS (git-ignored)
face_model.obj: 3D face mesh (git-tracked, Apache 2.0)
Playwright: Browser binaries for automation
Wake word: ONNX models (optional)
Ollama: GGUF models (optional)
No cloud storage anywhere
```