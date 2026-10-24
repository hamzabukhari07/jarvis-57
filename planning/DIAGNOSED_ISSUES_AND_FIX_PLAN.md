# 🛠️ ZEZO Diagnosed Issues & Action Plan

> **Creator & Lead Architect:** Hamza Bukhari  
> **Date:** 2026-10-24  
> **Status:** Diagnosed & Documented (Awaiting execution approval)  

---

## 📋 Overview of Identified Issues

Following a deep forensic audit using specialized subagents across backend logs, SQLite turn history (`memory/zezo_brain.db`), and source modules, three distinct issues were identified:

1. **Issue 1: Response Language Setting Ignored** (User selects "English Strict", but ZEZO continues speaking in Urdu/Hindi).
2. **Issue 2: Website Cloner Deliverable Open Failure & Dummy File Clutter** (`rebuilt.html` announced as open but not launched; redundant `antigravity_clone.html` file generated).
3. **Issue 3: Configuration Documentation Gaps & Action Loader Startup Rejection** (Missing `docs/SETTINGS.md`; `code_engines_status.py` rejected on startup due to missing risk tier).

---

## 🔍 Issue 1: Response Language Bug ("English Strict" Ignored)

### Symptoms
User sets **Response Language** in Settings to **"English Strict"**. When speaking in Hindi/Urdu, ZEZO continues responding in Hindi/Urdu (auto-detect mirroring behavior) until an unexpected session reconnect occurs minutes later.

### Root Causes Identified

#### 1. Missing Language Reconnect Trigger in `ui.py` and `main.py`
- **Files:** [`ui.py:361-374`](../ui.py#L361-L374) and [`main.py:795-802, 950-978`](../main.py#L795-L802)
- **Mechanism:**
  - When assistant name or voice is changed, `main.py` triggers `self.request_reconnect()` to restart the Gemini Live WebSocket session with the updated system instruction.
  - In `ui.py`, `_handle_assistant_settings_changed(name, voice, lang)` receives `lang` but **discards it completely**; no language change event or callback is fired to `main.py`.
  - In `main.py`, `_on_voice_change()` bails out early if the voice hasn't changed (`if getattr(self, "_active_voice", None) == new_voice: return`).
  - Because Gemini Live WebSocket sessions negotiate the system instruction **only upon connection**, the live session continues using the initial prompt (where language was `"auto"`) until a network disconnect or session timeout occurs.
  - **Evidence:** At 15:56:13 the user saved `"English Strict"`. ZEZO continued speaking Urdu at 15:56:49. At 15:57:56 an automated server renewal occurred, and immediately thereafter (16:00 to 16:02), ZEZO spoke strictly in English even though the user spoke Hindi.

#### 2. Hardcoded Conflict in `core/prompt.txt`
- **Files:** [`core/prompt.txt:44-46`](../core/prompt.txt#L44-L46) vs lines 179–185
- **Mechanism:**
  - Lines 44–46 unconditionally mandate:
    ```text
    - MATCH THE USER'S LANGUAGE NATURALLY:
      * If the user speaks Urdu/Roman Urdu, respond in crisp, natural Urdu/Roman Urdu.
      * If the user speaks English, respond in crisp executive English.
    ```
  - Meanwhile, line 180 injects `{language_directive}`: *"YOU MUST respond in English Strict ONLY... STRICT PROHIBITION: NEVER reply in Urdu, Hindi..."*.
  - The model receives two diametrically opposed instructions within the same system prompt.

#### 3. `lang_map` Key Mismatch in ASR Transcription Config
- **Files:** [`main.py:1525-1536`](../main.py#L1525-L1536)
- **Mechanism:**
  - `lang_map` in `main.py` only defines `"English"`, while frontend dropdown and `config_manager.py` send `"English Strict"`.
  - `lang_map.get("English Strict")` fails and falls back to listening for `["en-US", "ur-PK", "hi-IN", "es-ES"]`. The speech-to-text pipeline continues producing Hindi/Urdu transcripts, reinforcing the model's mirroring tendency.

### Planned Fixes
1. Wire `on_language_change` callback from `ui.py` to `main.py`, triggering a voluntary `request_reconnect(reason="language changed")` when response language is modified.
2. In `core/prompt.txt`, guard lines 44–46 so natural language mirroring only applies when response language is set to `"auto"`.
3. In `main.py:1525`, map `"English Strict"` to `["en-US", "en-GB"]` in `lang_map`.

---

## 🌐 Issue 2: Website Cloner Open Failure & `antigravity_clone.html` Clutter

### Symptoms
1. ZEZO announces: *"The fhrouter.com clone is complete, and I've opened the rebuilt HTML page in your browser"*, but no browser window opens until the user asks again in a follow-up turn.
2. The clone target folder contains two HTML files (`rebuilt.html` and `antigravity_clone.html`) when the user only asked for a single rebuilt HTML deliverable.

### Root Causes Identified

#### 1. Silent Rejection of `file://` Scheme in `_open_deliverable`
- **Files:** [`actions/website_cloner.py:192-228`](../actions/website_cloner.py#L192-L228) and [`actions/browser_control.py:787-788, 1592-1594`](../actions/browser_control.py#L787-L788)
- **Mechanism:**
  - Single self-contained rebuilds convert `path` to `file:///.../rebuilt.html` and pass it to `_open_in_browser(uri)`.
  - `_open_in_browser` calls `browser_control({"action": "go_to", "url": uri})`.
  - `browser_control.py` explicitly rejects non-http schemes:
    ```python
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'; only http and https are allowed"
    ```
  - Crucially, `browser_control()` returns a validation error string (`"Validation error: Invalid URL scheme 'file'..."`) **without raising a Python Exception**.
  - Because no Exception is raised, `_open_in_browser`'s `except Exception:` block is bypassed, and fallback `webbrowser.open(url)` is never executed. The call fails silently.
  - The background worker optimistically assumes the open call succeeded and produces a summary claiming the file is open.

#### 2. Dual Generation Steps in `_clone_worker`
- **Files:** [`actions/website_cloner.py:2901-2994`](../actions/website_cloner.py#L2901-L2994) (Step 7) vs lines 3030–3061 (Step 11)
- **Mechanism:**
  - `_clone_worker` executes **Step 7 (Legacy Master Reverse Engineering)** which writes `antigravity_file = clone_dir / "antigravity_clone.html"` unconditionally.
  - Immediately afterwards, it executes **Step 11 (v6 Prompt-Driven Reverse Engineering)** where `agy` runs the reverse-engineering prompt and generates `rebuilt.html`.
  - Because Step 7 is not skipped on rebuild tasks, both files persist in the user's output directory.

### Planned Fixes
1. In `actions/website_cloner.py` (`_open_in_browser`), directly use `webbrowser.open(uri)` for local `file://` URIs instead of routing through `browser_control` (or check if `browser_control` returned an error string and fall back immediately).
2. In `actions/website_cloner.py`, skip Step 7 (`antigravity_clone.html` generation) entirely when `output_format` is not in `CAPTURE_ONLY_FORMATS`, so only `rebuilt.html` is produced.

---

## 📚 Issue 3: Missing Settings Documentation & Startup Action Rejection

### Symptoms
1. AI agents lose context on configuration changes because modern settings are missing from repository documentation.
2. Startup log warning: `[Actions] Action rejected: code_engines_status.py — TOOL['risk'] missing. Every action must declare a valid ToolRisk tier.`

### Root Causes Identified

#### 1. Outdated Configuration Documentation
- **Files:** [`docs/CONFIGURATION.md`](../docs/CONFIGURATION.md); `docs/SETTINGS.md` does not exist.
- **Mechanism:**
  - `docs/CONFIGURATION.md` reflects legacy architecture (3-modal setup, cascade voice pipelines).
  - Modern settings present in `memory/config_manager.py` and `SettingsModal.tsx` (Themes, Accents, WebGL Avatar parameters, Autostart, Code Engine Preferences, Tavily key, Interaction Modes) are completely undocumented in `docs/`.

#### 2. Missing Security Risk Tier in `code_engines_status.py`
- **Files:** [`actions/code_engines_status.py:27-55`](../actions/code_engines_status.py#L27-L55) and [`core/action_loader.py:306-322`](../core/action_loader.py#L306-L322)
- **Mechanism:**
  - `core/action_loader.py` enforces that every action must declare `"risk"` in its `TOOL` dict (`"read_only"`, `"local_mutation"`, etc.).
  - `code_engines_status.py` omitted `"risk": "read_only"`, causing the action loader to reject the action on startup.

### Planned Fixes
1. Add `"risk": "read_only"` to `TOOL` in `actions/code_engines_status.py`.
2. Create `docs/SETTINGS.md` documenting all 9 settings tabs, configuration keys, API endpoints, and live behavioral effects. Update `docs/CONFIGURATION.md`.

---

## 🗺️ Execution Roadmap

| Step | Scope | Target Files | Verification Method |
|---|---|---|---|
| **1** | Language Reconnect Trigger | `ui.py`, `main.py`, `core/prompt.txt` | Verify language change in UI triggers voluntary live reconnect and prompt update. |
| **2** | Cloner File Open Fix | `actions/website_cloner.py` | Verify `_open_deliverable` launches `file://` deliverable without silent swallow. |
| **3** | Cloner Single File Hygiene | `actions/website_cloner.py` | Verify single HTML clone produces only `rebuilt.html` without `antigravity_clone.html`. |
| **4** | Action Risk Tier Fix | `actions/code_engines_status.py` | Verify `action_loader` loads `code_engines_status` with 0 rejections on startup. |
| **5** | Settings Documentation | `docs/SETTINGS.md`, `docs/CONFIGURATION.md` | Audit all config keys against `config_manager.py`. |
