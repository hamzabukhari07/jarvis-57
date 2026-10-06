import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# Canonical model identifiers live in ONE place: core/models.py.
# Re-exported here so existing `from memory.config_manager import ...` keeps working.
from core.models import (
    ANTIGRAVITY_CLI_MODELS,
    DEFAULT_ANTIGRAVITY_MODEL,
    ANTIGRAVITY_MODEL_ALIASES,
    DEFAULT_GROQ_MODEL,
    DEFAULT_GROQ_VISION_MODEL,
    DEFAULT_GROQ_WHISPER_MODEL,
    GEMINI_FAST_MODELS,
)

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def clean_api_key(k: str | None) -> str | None:
    """Sanitize API key input, stripping whitespace and discarding accidental multi-line terminal dumps."""
    if not k:
        return None
    val = str(k).strip()
    if not val:
        return None
    if "\n" in val or "\r" in val or len(val) > 256:
        for line in val.splitlines():
            line = line.strip()
            if line.startswith("gsk_") or line.startswith("AIzaSy") or line.startswith("AQ."):
                return line
        return None
    return val


def _atomic_write_config(data: dict) -> None:
    """Safely write config dictionary to disk via staging file and atomic replace."""
    ensure_config_dir()
    tmp_file = CONFIG_FILE.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
    try:
        os.replace(tmp_file, CONFIG_FILE)
    except Exception:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        raise


def validate_gemini_key(api_key: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Pre-flight real probe to Google Generative AI REST API with a 1-token query."""
    c_key = clean_api_key(api_key)
    if not c_key or len(c_key) < 15:
        return False, "Invalid or too short Gemini API key"
    try:
        import requests
        candidates = list(GEMINI_FAST_MODELS) or ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview"]
        last_err = ""
        for model_name in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={c_key}"
            payload = {
                "contents": [{"parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 1}
            }
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    return True, "Gemini API key is valid"
                elif resp.status_code in (400, 401, 403):
                    try:
                        err_detail = resp.json().get("error", {}).get("message", resp.text[:120])
                    except Exception:
                        err_detail = resp.text[:120]
                    return False, f"Gemini API key unauthorized ({resp.status_code}): {err_detail}"
                elif resp.status_code == 429:
                    return False, "Gemini quota exceeded / rate limited (HTTP 429)"
                elif resp.status_code == 404:
                    last_err = f"Model {model_name} not found"
                    continue
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:120]}"
            except requests.exceptions.Timeout:
                last_err = "Request timed out"
                continue
        return False, f"Gemini probe failed: {last_err}"
    except Exception as e:
        return False, f"Gemini probe connection error: {str(e)}"


def validate_groq_key(api_key: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Pre-flight real probe to Groq chat completions API with a 1-token query."""
    c_key = clean_api_key(api_key)
    if not c_key or not c_key.startswith("gsk_"):
        return False, "Invalid Groq API key format (must start with 'gsk_')"
    try:
        import requests
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {c_key}",
            "Content-Type": "application/json",
        }
        candidates = [
            DEFAULT_GROQ_MODEL,
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "groq/compound-mini",
            "qwen/qwen3.8-27b",
        ]
        # Deduplicate candidates preserving order
        models_to_try = list(dict.fromkeys(candidates))
        last_err = ""

        for candidate in models_to_try:
            payload = {
                "model": candidate,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if resp.status_code == 200:
                    return True, "Groq API key is valid"
                elif resp.status_code in (401, 403):
                    try:
                        err_detail = resp.json().get("error", {}).get("message", resp.text[:120])
                    except Exception:
                        err_detail = resp.text[:120]
                    return False, f"Groq API key unauthorized ({resp.status_code}): {err_detail}"
                elif resp.status_code == 429:
                    return False, "Groq rate limit / quota exceeded (HTTP 429)"
                elif resp.status_code == 404:
                    last_err = f"Model {candidate} not found"
                    continue
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:120]}"
            except requests.exceptions.Timeout:
                last_err = "Request timed out"
                continue

        return False, f"Groq probe failed: {last_err}"
    except Exception as e:
        return False, f"Groq probe connection error: {str(e)}"


def validate_elevenlabs_key(api_key: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Pre-flight probe to ElevenLabs user endpoint."""
    c_key = clean_api_key(api_key)
    if not c_key or len(c_key) < 10:
        return False, "Invalid ElevenLabs API key format"
    try:
        import requests
        url = "https://api.elevenlabs.io/v1/user"
        headers = {"xi-api-key": c_key}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return True, "ElevenLabs API key is valid"
        elif resp.status_code in (401, 403):
            return False, f"ElevenLabs authentication failed (HTTP {resp.status_code})"
        else:
            return False, f"ElevenLabs server returned HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return False, f"ElevenLabs probe connection error: {str(e)}"


def validate_tavily_key(api_key: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Pre-flight probe to Tavily search API with a 1-result query."""
    c_key = clean_api_key(api_key)
    if not c_key or len(c_key) < 10:
        return False, "Invalid Tavily API key format (must be at least 10 chars)"
    try:
        import requests
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": c_key,
            "query": "ping",
            "search_depth": "basic",
            "max_results": 1
        }
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            return True, "Tavily API key is valid"
        elif resp.status_code in (401, 403):
            return False, f"Tavily authentication failed (HTTP {resp.status_code})"
        elif resp.status_code == 429:
            return False, "Tavily rate limit or monthly quota exceeded (HTTP 429)"
        else:
            return False, f"Tavily server returned HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return False, f"Tavily probe connection error: {str(e)}"


def save_api_keys_transactional(
    gemini_api_key: str | None = None,
    groq_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
    tavily_api_key: str | None = None,
    validate: bool = True,
) -> tuple[bool, str]:
    """Validate candidate API keys with real live probes, then write atomically.
    
    If validation fails for any key, no disk changes occur and (False, err_msg) is returned.
    """
    ensure_config_dir()
    data: dict = load_api_keys()

    # Gemini key validation
    if gemini_api_key is not None:
        c_gem = clean_api_key(gemini_api_key)
        if c_gem and "••••" not in c_gem:
            if validate:
                ok, err = validate_gemini_key(c_gem)
                if not ok:
                    return False, f"Gemini Key Error: {err}"
            data["gemini_api_key"] = c_gem

    # Groq key validation
    if groq_api_key is not None:
        c_groq = clean_api_key(groq_api_key)
        if c_groq and "••••" not in c_groq:
            if validate:
                ok, err = validate_groq_key(c_groq)
                if not ok:
                    return False, f"Groq Key Error: {err}"
            data["groq_api_key"] = c_groq
        elif str(groq_api_key).strip() == "":
            data["groq_api_key"] = ""

    # ElevenLabs key validation
    if elevenlabs_api_key is not None:
        c_el = clean_api_key(elevenlabs_api_key)
        if c_el and "••••" not in c_el:
            if validate:
                ok, err = validate_elevenlabs_key(c_el)
                if not ok:
                    return False, f"ElevenLabs Key Error: {err}"
            data["elevenlabs_api_key"] = c_el
        elif str(elevenlabs_api_key).strip() == "":
            data["elevenlabs_api_key"] = ""

    # Tavily key validation
    if tavily_api_key is not None:
        c_tav = clean_api_key(tavily_api_key)
        if c_tav and "••••" not in c_tav:
            if validate:
                ok, err = validate_tavily_key(c_tav)
                if not ok:
                    return False, f"Tavily Key Error: {err}"
            data["tavily_api_key"] = c_tav
        elif str(tavily_api_key).strip() == "":
            data["tavily_api_key"] = ""

    _atomic_write_config(data)
    return True, "API keys validated and saved successfully"


def save_api_keys(
    gemini_api_key: str | None = None,
    groq_api_key: str | None = None,
    tavily_api_key: str | None = None,
) -> None:
    """Save keys directly with atomic write (non-validating fallback for backward compatibility)."""
    ensure_config_dir()
    data: dict = load_api_keys()

    if gemini_api_key is not None:
        c_gem = clean_api_key(gemini_api_key)
        if c_gem and "••••" not in c_gem:
            data["gemini_api_key"] = c_gem
    if groq_api_key is not None:
        c_groq = clean_api_key(groq_api_key)
        if c_groq and "••••" not in c_groq:
            data["groq_api_key"] = c_groq
        elif str(groq_api_key).strip() == "":
            data["groq_api_key"] = ""
    if tavily_api_key is not None:
        c_tav = clean_api_key(tavily_api_key)
        if c_tav and "••••" not in c_tav:
            data["tavily_api_key"] = c_tav
        elif str(tavily_api_key).strip() == "":
            data["tavily_api_key"] = ""

    _atomic_write_config(data)


def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load api_keys.json: {e}")
        return {}

def get_gemini_key() -> str | None:
    return load_api_keys().get("gemini_api_key")

def get_tavily_api_key() -> str | None:
    key = load_api_keys().get("tavily_api_key", "").strip()
    return key if key else None

def get_masked_gemini_key() -> str:
    key = get_gemini_key()
    if not key or len(key) < 10:
        return ""
    return key[:6] + "••••••••••••" + key[-4:]

def get_masked_groq_key() -> str:
    key = load_api_keys().get("groq_api_key", "")
    if not key or len(key) < 10:
        return ""
    return key[:6] + "••••••••••••" + key[-4:]

def get_masked_elevenlabs_key() -> str:
    key = load_api_keys().get("elevenlabs_api_key", "")
    if not key or len(key) < 8:
        return ""
    return key[:4] + "••••••••••••" + key[-4:]

def get_masked_tavily_key() -> str:
    key = load_api_keys().get("tavily_api_key", "")
    if not key or len(key) < 8:
        return ""
    return key[:5] + "••••••••••••" + key[-4:]

def is_configured() -> bool:
    key = get_gemini_key()
    return bool(key and len(key) > 15)


def get_assistant_name() -> str:
    """Return the configured assistant name, or 'JARVIS' if not set."""
    return load_api_keys().get("assistant_name", "JARVIS") or "JARVIS"


def get_user_name() -> str:
    """Return the configured user name for addressing."""
    return load_api_keys().get("user_name", "")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    """Persist assistant name and user name to config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data["assistant_name"] = assistant_name.strip() or "JARVIS"
    data["user_name"] = user_name.strip()
    _atomic_write_config(data)


# ── Assistant voice ──────────────────────────────────────────────────────────
# Gemini Live prebuilt voices. Names are proper nouns — identical in every
# language, so this list is safe to show verbatim in any locale.
AVAILABLE_VOICES = ["Charon", "Puck", "Kore", "Fenrir", "Aoede"]
DEFAULT_VOICE    = "Charon"


def get_voice() -> str:
    """Return the configured Live voice, falling back to the default if unset
    or if the stored value is not a voice we recognise."""
    v = load_api_keys().get("voice_name", DEFAULT_VOICE) or DEFAULT_VOICE
    return v if v in AVAILABLE_VOICES else DEFAULT_VOICE


def save_voice(voice_name: str) -> None:
    """Persist the chosen Live voice. Unknown names collapse to the default so a
    bad value can never reach the API and break the session."""
    ensure_config_dir()
    data: dict = load_api_keys()
    v = (voice_name or "").strip()
    data["voice_name"] = v if v in AVAILABLE_VOICES else DEFAULT_VOICE
    _atomic_write_config(data)


# ── Assistant response language ──────────────────────────────────────────────
AVAILABLE_LANGUAGES = [
    "auto",       # Dynamic Language Matching (Matches User's Spoken Language)
    "English",    # Always English
    "Urdu",       # Always Urdu
    "Hindi",      # Always Hindi
    "Spanish",    # Always Spanish
    "French",     # Always French
    "German",     # Always German
    "Arabic",     # Always Arabic
    "Turkish",    # Always Turkish
]
DEFAULT_RESPONSE_LANGUAGE = "auto"


def get_response_language() -> str:
    """Return configured assistant response language ('auto', 'English', 'Urdu', etc.)."""
    return load_api_keys().get("response_language", DEFAULT_RESPONSE_LANGUAGE) or DEFAULT_RESPONSE_LANGUAGE


def save_response_language(lang: str) -> None:
    """Persist the chosen response language."""
    ensure_config_dir()
    data: dict = load_api_keys()
    l = (lang or "").strip()
    data["response_language"] = l if l in AVAILABLE_LANGUAGES else DEFAULT_RESPONSE_LANGUAGE
    _atomic_write_config(data)


def get_wake_word_enabled() -> bool:
    """Whether local wake-word gating is on (assistant sleeps until 'Hey Jarvis')."""
    return load_api_keys().get("wake_word_enabled", False)


def save_wake_word_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = load_api_keys()
    data["wake_word_enabled"] = bool(enabled)
    _atomic_write_config(data)


def get_push_to_talk_enabled() -> bool:
    """Hold-a-key-to-speak. When on, the mic is closed unless the chord is held."""
    return load_api_keys().get("push_to_talk_enabled", False)


def save_push_to_talk_enabled(enabled: bool) -> None:
    _save_flag("push_to_talk_enabled", enabled)


HUD_STYLES = ("face", "core")


def get_hud_style() -> str:
    """Which centrepiece the HUD draws: the animated head, or the reactor core.

    Taste, not capability — both render in the same software painter and cost
    about the same. Defaults to the head because that is what JARVIS shipped
    with; anyone who preferred the older look can switch back in ⚙ and the
    choice survives a restart.
    """
    v = str(load_api_keys().get("hud_style", "face")).strip().lower()
    return v if v in HUD_STYLES else "face"


def save_hud_style(style: str) -> None:
    s = str(style or "").strip().lower()
    _save_flag("hud_style", s if s in HUD_STYLES else "face")


# ── Live-session tuning ──────────────────────────────────────────────────────
# Everything here is optional and has a working default, so an untouched
# config behaves exactly like a configured one. Each value is also a way out:
# if a future model dislikes one of these, set it back and nothing else changes.

def get_thinking_enabled() -> bool:
    """Whether the Live model may spend tokens thinking before it answers.

    Off by default. A voice assistant is judged on how fast it starts talking,
    and the reasoning that actually needs deliberation in this app is delegated
    to the planning tools, which run on a separate non-Live model.
    """
    return bool(load_api_keys().get("thinking_enabled", False))


def save_thinking_enabled(enabled: bool) -> None:
    _save_flag("thinking_enabled", enabled)


def get_turn_tuning() -> dict:
    """How eagerly the server decides you have stopped speaking.

    ON by default with responsive 450ms silence detection and high end sensitivity
    so user speech is processed immediately with minimal latency.
    `silence_ms` is the pause the server sits through before completing your turn.
    """
    cfg = load_api_keys().get("turn_tuning")
    cfg = cfg if isinstance(cfg, dict) else {}

    def _int(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(cfg.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "enabled":    bool(cfg.get("enabled", True)),
        "silence_ms": _int("silence_ms", 450, 200, 3000),
        "prefix_ms":  _int("prefix_ms", 100, 0, 1000),
        # "high" = quicker to decide speech has ended.
        "end_sensitivity":   str(cfg.get("end_sensitivity", "high")).lower(),
        "start_sensitivity": str(cfg.get("start_sensitivity", "default")).lower(),
    }


def save_turn_tuning(values: dict) -> None:
    ensure_config_dir()
    data: dict = load_api_keys()
    cur = data.get("turn_tuning")
    cur = dict(cur) if isinstance(cur, dict) else {}
    cur.update(values or {})
    data["turn_tuning"] = cur
    _atomic_write_config(data)


def get_proactive_audio_enabled() -> bool:
    """Whether the model gets to decide an utterance was not aimed at it and
    stay quiet.

    Off by default so every user utterance is heard and processed immediately
    without classifier hesitation or turn lag.
    """
    return bool(load_api_keys().get("proactive_audio", False))


def save_proactive_audio_enabled(enabled: bool) -> None:
    _save_flag("proactive_audio", enabled)


# ── Offline voice fallback ───────────────────────────────────────────────────

# ── Voice Engine Defaults (Pure Gemini Live WebSocket Mode) ───────────────────
PIPELINE_MODES = ("live",)
DEFAULT_PIPELINE_MODE = "live"
FALLBACK_VOICES = ("af_heart", "af_bella", "am_adam", "am_michael")
STT_ENGINES = ("gemini_live",)
LLM_ENGINES = ("gemini_live",)
TTS_ENGINES = ("gemini_live",)


def get_voice_fallback_mode() -> str:
    return "off"


def save_voice_fallback_mode(mode: str) -> None:
    pass


def get_fallback_voice() -> str:
    return "af_heart"


def save_fallback_voice(voice: str) -> None:
    pass


def get_pipeline_mode() -> str:
    return "live"


def save_pipeline_mode(mode: str) -> None:
    pass


def get_stt_engine() -> str:
    return "gemini_live"


def save_stt_engine(engine: str) -> None:
    pass


def get_llm_engine() -> str:
    return "gemini_live"


def save_llm_engine(engine: str) -> None:
    pass


def get_tts_engine() -> str:
    return "gemini_live"


def save_tts_engine(engine: str) -> None:
    pass


def get_tts_voice() -> str:
    return ""


def save_tts_voice(voice: str) -> None:
    pass



def _get_choice(key: str, options: tuple, default: str) -> str:
    v = str(load_api_keys().get(key, default) or default).strip().lower()
    return v if v in options else default


def _save_choice(key: str, value: str, options: tuple, default: str) -> None:
    ensure_config_dir()
    data: dict = load_api_keys()
    v = str(value or default).strip().lower()
    data[key] = v if v in options else default
    _atomic_write_config(data)


# ── CLI & Coding Agent Preferences ───────────────────────────────────────────
CREATION_AGENTS = ("opencode", "antigravity", "kilo")
DEFAULT_CREATION_AGENT = "opencode"

EDIT_AGENTS = ("groq_helper", "kilo", "opencode")
DEFAULT_EDIT_AGENT = "groq_helper"


def get_preferred_creation_agent() -> str:
    """Preferred CLI agent for building new multi-file projects."""
    return _get_choice("preferred_creation_agent", CREATION_AGENTS, DEFAULT_CREATION_AGENT)


def save_preferred_creation_agent(agent: str) -> None:
    _save_choice("preferred_creation_agent", agent, CREATION_AGENTS, DEFAULT_CREATION_AGENT)


def get_preferred_edit_agent() -> str:
    """Preferred CLI agent / tool for editing existing files or sections."""
    return _get_choice("preferred_edit_agent", EDIT_AGENTS, DEFAULT_EDIT_AGENT)


def save_preferred_edit_agent(agent: str) -> None:
    _save_choice("preferred_edit_agent", agent, EDIT_AGENTS, DEFAULT_EDIT_AGENT)


MEDIA_RESOLUTIONS = ("default", "low", "medium", "high")


def get_media_resolution() -> str:
    """How finely the model tokenises the screenshots and camera frames it is
    sent. 'medium' keeps on-screen text readable at a fraction of the tokens a
    full-resolution frame costs; 'low' is cheaper still but starts losing small
    text, which is most of what screen captures are for."""
    v = str(load_api_keys().get("media_resolution", "medium")).strip().lower()
    return v if v in MEDIA_RESOLUTIONS else "medium"


def save_media_resolution(value: str) -> None:
    v = str(value or "").strip().lower()
    _save_flag("media_resolution", v if v in MEDIA_RESOLUTIONS else "medium")


def _save_flag(key: str, value) -> None:
    """Read-modify-write one key without disturbing the rest of the config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data[key] = bool(value) if isinstance(value, bool) else value
    _atomic_write_config(data)


def get_brief_enabled() -> bool:
    return load_api_keys().get("morning_brief_enabled", True)


def save_brief_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = load_api_keys()
    data["morning_brief_enabled"] = bool(enabled)
    _atomic_write_config(data)


def get_startup_lnk_path() -> Path | None:
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "ZEZO.lnk"
    return None


def get_autostart_enabled() -> bool:
    if platform.system() == "Windows":
        lnk = get_startup_lnk_path()
        if lnk and lnk.exists():
            return True
    return bool(load_api_keys().get("autostart_enabled", False))


def save_autostart_enabled(enabled: bool) -> bool:
    _save_flag("autostart_enabled", enabled)
    if platform.system() == "Windows":
        lnk = get_startup_lnk_path()
        if lnk:
            if enabled:
                try:
                    script = BASE_DIR / "main.py"
                    python = Path(sys.executable)
                    pythonw = python.parent / "pythonw.exe"
                    target = str(pythonw if pythonw.exists() else python)
                    ico_path = CONFIG_DIR / "zezo.ico"
                    icon_loc = str(ico_path) if ico_path.exists() else f"{target},0"

                    vbs = "\n".join([
                        'Set ws = CreateObject("WScript.Shell")',
                        f'Set sc = ws.CreateShortcut("{str(lnk)}")',
                        f'sc.TargetPath = "{target}"',
                        f'sc.Arguments = Chr(34) & "{str(script)}" & Chr(34)',
                        f'sc.WorkingDirectory = "{str(BASE_DIR)}"',
                        'sc.Description = "ZEZO Autonomous AI Operating System"',
                        f'sc.IconLocation = "{icon_loc}"',
                        'sc.Save',
                    ])
                    import tempfile
                    fd, tmp = tempfile.mkstemp(suffix=".vbs")
                    try:
                        with os.fdopen(fd, "w", encoding="utf-8") as f:
                            f.write(vbs)
                        proc = subprocess.Popen(
                            ["wscript.exe", "/nologo", tmp],
                            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                        )
                        proc.wait(timeout=10)
                    finally:
                        try:
                            os.unlink(tmp)
                        except Exception:
                            pass
                    return True
                except Exception as e:
                    print(f"Failed to enable autostart: {e}")
                    return False
            else:
                try:
                    if lnk.exists():
                        lnk.unlink()
                    return True
                except Exception as e:
                    print(f"Failed to disable autostart: {e}")
                    return False
    return True


# ── Audio devices ────────────────────────────────────────────────────────────
# Stored as device NAMES, not sounddevice indices. Indices shift every time a
# USB device is plugged in or removed, so a saved index silently starts pointing
# at a different microphone. The empty string means "system default", which is
# both the factory setting and what an unresolvable saved device falls back to —
# so unplugging a headset degrades to the built-in speakers instead of crashing.

def _patch_config(**fields) -> None:
    """Read-modify-write one or more keys in api_keys.json."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data.update(fields)
    _atomic_write_config(data)


def get_input_device() -> str:
    """Microphone device name, or '' for the system default."""
    return (load_api_keys().get("input_device", "") or "").strip()


def save_input_device(name: str) -> None:
    _patch_config(input_device=(name or "").strip())


def get_output_device() -> str:
    """Speaker device name, or '' for the system default."""
    return (load_api_keys().get("output_device", "") or "").strip()


def save_output_device(name: str) -> None:
    _patch_config(output_device=(name or "").strip())


def get_plugin_enabled(plugin_name: str) -> bool:
    """Plugins are enabled by default the moment they're discovered (opt-out model)."""
    return load_api_keys().get("plugins_enabled", {}).get(plugin_name, True)


# ── Per-plugin settings ("tokens" / connection details) ───────────────────────
# Generic store so a plugin can declare its own config fields (PLUGIN_SETTINGS)
# and the settings UI renders + persists them WITHOUT any core edit — keeping the
# drop-in model intact. Values live under plugin_config[<namespace>][<key>].
# A namespace defaults to the plugin name, but a suite of plugins (e.g. the
# several printer plugins) can share ONE namespace.
def get_plugin_config(namespace: str) -> dict:
    """All stored values for a namespace (empty dict if none set yet)."""
    cfg = load_api_keys().get("plugin_config")
    val = cfg.get(namespace) if isinstance(cfg, dict) else None
    return dict(val) if isinstance(val, dict) else {}


def get_plugin_setting(namespace: str, key: str, default=None):
    """A single value from a namespace, or `default` if unset."""
    return get_plugin_config(namespace).get(key, default)


def save_plugin_config(namespace: str, values: dict) -> None:
    """Merge `values` into a namespace's stored config (read-modify-write, like
    every other helper here). Only the provided keys are touched."""
    ensure_config_dir()
    data: dict = load_api_keys()
    pc = data.get("plugin_config")
    if not isinstance(pc, dict):
        pc = {}
    cur = pc.get(namespace)
    if not isinstance(cur, dict):
        cur = {}
    cur.update(values)
    pc[namespace] = cur
    data["plugin_config"] = pc
    _atomic_write_config(data)


def save_plugin_enabled(plugin_name: str, enabled: bool) -> None:
    ensure_config_dir()
    data: dict = load_api_keys()
    plugins_cfg = data.get("plugins_enabled")
    if not isinstance(plugins_cfg, dict):
        plugins_cfg = {}
    plugins_cfg[plugin_name] = enabled
    data["plugins_enabled"] = plugins_cfg
    _atomic_write_config(data)


# ── OpenCode Zen & Free Models Config ─────────────────────────────────────────

OPENCODE_ZEN_FREE_MODELS = [
    "opencode/big-pickle",                 # Specialized agentic coding model
    "opencode/nemotron-3-ultra-free",      # NVIDIA Nemotron 3 Ultra (Free)
    "opencode/nemotron-3.5-lightning-free",# High-speed NVIDIA Nemotron (Free)
    "opencode/mimo-v2.6-flash-free",       # Fast execution Xiaomi Mimo Flash (Free)
    "opencode/ling-3.1-flash-free",         # Multimodal reasoning & speed (Free)
    "opencode/longcat-2.5-preview-free",    # Extended context code model (Free)
    "opencode/space-bunny-free",           # Lightweight agile coding model (Free)
    "opencode/fledge-alpha-free",          # Alpha reasoning coding model (Free)
    "opencode/muse-spark-1.3-contributor-free", # Open-source coding model (Free)
]

DEFAULT_OPENCODE_MODEL = "opencode/big-pickle"
DEFAULT_OPENCODE_PROVIDER = "zen"


def get_opencode_provider() -> str:
    """Return configured OpenCode provider (defaults to 'zen')."""
    return load_api_keys().get("opencode_provider", DEFAULT_OPENCODE_PROVIDER) or DEFAULT_OPENCODE_PROVIDER


def save_opencode_provider(provider: str) -> None:
    """Persist OpenCode provider to config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data["opencode_provider"] = provider.strip() or DEFAULT_OPENCODE_PROVIDER
    _atomic_write_config(data)


def get_opencode_model() -> str:
    """Return configured OpenCode model (defaults to 'opencode/nemotron-3-ultra-free')."""
    raw = load_api_keys().get("opencode_model", DEFAULT_OPENCODE_MODEL) or DEFAULT_OPENCODE_MODEL
    # Normalize legacy zen/ prefixes if found in config
    if raw.startswith("zen/"):
        name = raw.replace("zen/", "")
        if "nemotron" in name:
            raw = "opencode/nemotron-3-ultra-free"
        elif "pickle" in name:
            raw = "opencode/big-pickle"
        elif "mimo" in name:
            raw = "opencode/mimo-v2.6-flash-free"
        else:
            raw = f"opencode/{name}"
    return raw


def save_opencode_model(model: str) -> None:
    """Persist chosen OpenCode model to config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data["opencode_model"] = model.strip() or DEFAULT_OPENCODE_MODEL
    _atomic_write_config(data)


# ── Kilo Code & Free Models Config ───────────────────────────────────────────

KILO_CODE_FREE_MODELS = [
    "kilo/kilo-auto/free",                         # Auto Free (Dynamic router) - Default
    "kilo/dots-studio/dots-3-note-preview:free",    # Dots Studio Dots3-Note Preview
    "kilo/inclusionai/ling-3.0-flash-vl:free",      # Ling 3.0 Flash VL (Multimodal Vision)
    "kilo/nex-agi/nex-n2.5-pro:free",               # Nex AGI Nex-N2.5-Pro
    "kilo/nvidia/nemotron-3-ultra-550b-a55b:free",  # NVIDIA Nemotron 3 Ultra
    "kilo/poolside/laguna-s-2.1:free",              # Poolside Laguna S 2.1
    "kilo/stepfun/step-3.7-flash:free",             # StepFun Step 3.7 Flash
]

DEFAULT_KILO_MODEL = "kilo/kilo-auto/free"


def get_kilo_model() -> str:
    """Return configured Kilo Code model (defaults to 'kilo/kilo-auto/free')."""
    raw = load_api_keys().get("kilo_model", DEFAULT_KILO_MODEL) or DEFAULT_KILO_MODEL
    if not raw.startswith("kilo/"):
        raw = f"kilo/{raw}"
    return raw


def save_kilo_model(model: str) -> None:
    """Persist chosen Kilo Code model to config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    m = model.strip() or DEFAULT_KILO_MODEL
    if not m.startswith("kilo/"):
        m = f"kilo/{m}"
    data["kilo_model"] = m
    _atomic_write_config(data)


# ── Antigravity CLI & Model Config ───────────────────────────────────────────

# ANTIGRAVITY_CLI_MODELS / DEFAULT_ANTIGRAVITY_MODEL are imported from
# core/models.py above — single source of truth, re-exported for callers.


def get_antigravity_model() -> str:
    """Return configured Antigravity CLI model (defaults to 'gemini-3.7-flash-medium')."""
    return load_api_keys().get("antigravity_model", DEFAULT_ANTIGRAVITY_MODEL) or DEFAULT_ANTIGRAVITY_MODEL


def save_antigravity_model(model: str) -> None:
    """Persist chosen Antigravity model to config."""
    ensure_config_dir()
    data: dict = load_api_keys()
    data["antigravity_model"] = model.strip() or DEFAULT_ANTIGRAVITY_MODEL
    _atomic_write_config(data)


# ── Groq LPU Coprocessor Config ──────────────────────────────────────────────

# DEFAULT_GROQ_MODEL / DEFAULT_GROQ_VISION_MODEL / DEFAULT_GROQ_WHISPER_MODEL are
# imported from core/models.py above. Groq's public free tier exposes NO
# multimodal/vision model, so vision is opt-in (empty default → Gemini).


def get_groq_api_key() -> str | None:
    """Return the configured Groq API key, or None if not set or invalid."""
    key = load_api_keys().get("groq_api_key", "").strip()
    if not key or any(c in "\r\n" for c in key) or any(ord(c) >= 128 for c in key):
        return None
    return key


def get_groq_model() -> str:
    """Return configured Groq model (defaults to 'llama-3.3-70b-versatile')."""
    return load_api_keys().get("groq_model", DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL


def get_groq_vision_model() -> str:
    """Return configured Groq multimodal model for image/document extraction."""
    return (
        load_api_keys().get("groq_vision_model", DEFAULT_GROQ_VISION_MODEL)
        or DEFAULT_GROQ_VISION_MODEL
    )


def get_groq_whisper_model() -> str:
    """Return configured Groq Whisper model for audio/video transcription."""
    return (
        load_api_keys().get("groq_whisper_model", DEFAULT_GROQ_WHISPER_MODEL)
        or DEFAULT_GROQ_WHISPER_MODEL
    )


def get_elevenlabs_api_key() -> str | None:
    """Return the configured ElevenLabs API key, or None if not set."""
    key = load_api_keys().get("elevenlabs_api_key", "").strip()
    return key if key else None


def save_groq_config(
    api_key: str,
    model: str = DEFAULT_GROQ_MODEL,
    vision_model: str = "",
    whisper_model: str = "",
) -> None:
    """Persist Groq API key and model choices to config.

    ``vision_model`` / ``whisper_model`` are optional and only written when
    provided, so existing callers keep their exact behaviour.
    """
    ensure_config_dir()
    data: dict = load_api_keys()
    if api_key:
        data["groq_api_key"] = api_key.strip()
    if model:
        data["groq_model"] = model.strip() or DEFAULT_GROQ_MODEL
    if vision_model:
        data["groq_vision_model"] = vision_model.strip() or DEFAULT_GROQ_VISION_MODEL
    if whisper_model:
        data["groq_whisper_model"] = whisper_model.strip() or DEFAULT_GROQ_WHISPER_MODEL
    _atomic_write_config(data)
