import json
import sys
from pathlib import Path

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

def save_api_keys(gemini_api_key: str) -> None:
    ensure_config_dir()

    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data["gemini_api_key"] = gemini_api_key.strip()

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["assistant_name"] = assistant_name.strip() or "JARVIS"
    data["user_name"] = user_name.strip()
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    v = (voice_name or "").strip()
    data["voice_name"] = v if v in AVAILABLE_VOICES else DEFAULT_VOICE
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    l = (lang or "").strip()
    data["response_language"] = l if l in AVAILABLE_LANGUAGES else DEFAULT_RESPONSE_LANGUAGE
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_wake_word_enabled() -> bool:
    """Whether local wake-word gating is on (assistant sleeps until 'Hey Jarvis')."""
    return load_api_keys().get("wake_word_enabled", False)


def save_wake_word_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["wake_word_enabled"] = bool(enabled)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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

    OFF by default, and that default was earned. Cutting turns shorter looks
    like a free speed win and is not: proactive audio has to judge whether an
    utterance was even addressed to the assistant, and a turn clipped early
    gives it less to judge, so it stays quiet — and the reply to your first
    sentence only arrives once your second one has given it enough context.
    That reads as the assistant being a turn behind, which is far worse than
    the fraction of a second the tuning saves.

    Turn it on with "turn_tuning": {"enabled": true} if your own microphone and
    speaking pace suit it. `silence_ms` is the one that is felt: the pause the
    server sits through before accepting your turn is over.
    """
    cfg = load_api_keys().get("turn_tuning")
    cfg = cfg if isinstance(cfg, dict) else {}

    def _int(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(cfg.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "enabled":    bool(cfg.get("enabled", False)),
        "silence_ms": _int("silence_ms", 550, 200, 3000),
        "prefix_ms":  _int("prefix_ms", 150, 0, 1000),
        # "high" = quicker to decide speech has ended.
        "end_sensitivity":   str(cfg.get("end_sensitivity", "high")).lower(),
        "start_sensitivity": str(cfg.get("start_sensitivity", "default")).lower(),
    }


def save_turn_tuning(values: dict) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cur = data.get("turn_tuning")
    cur = dict(cur) if isinstance(cur, dict) else {}
    cur.update(values or {})
    data["turn_tuning"] = cur
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_proactive_audio_enabled() -> bool:
    """Whether the model gets to decide an utterance was not aimed at it and
    stay quiet.

    On by default — it is what stops the assistant answering the room. But it
    is also the first thing to switch off if replies ever seem to arrive a turn
    late: what looks like lag is usually the model having judged your previous
    sentence as not addressed to it, and only changing its mind once the next
    one arrives.
    """
    return bool(load_api_keys().get("proactive_audio", True))


def save_proactive_audio_enabled(enabled: bool) -> None:
    _save_flag("proactive_audio", enabled)


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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[key] = bool(value) if isinstance(value, bool) else value
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def get_brief_enabled() -> bool:
    return load_api_keys().get("morning_brief_enabled", True)


def save_brief_enabled(enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["morning_brief_enabled"] = enabled
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Audio devices ────────────────────────────────────────────────────────────
# Stored as device NAMES, not sounddevice indices. Indices shift every time a
# USB device is plugged in or removed, so a saved index silently starts pointing
# at a different microphone. The empty string means "system default", which is
# both the factory setting and what an unresolvable saved device falls back to —
# so unplugging a headset degrades to the built-in speakers instead of crashing.

def _patch_config(**fields) -> None:
    """Read-modify-write one or more keys in api_keys.json.

    Every setter in this file open-coded this. Collapsing it here means a new
    setting is one line, and there is one place where a corrupt config file is
    handled instead of nine."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    pc = data.get("plugin_config")
    if not isinstance(pc, dict):
        pc = {}
    cur = pc.get(namespace)
    if not isinstance(cur, dict):
        cur = {}
    cur.update(values)
    pc[namespace] = cur
    data["plugin_config"] = pc
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def save_plugin_enabled(plugin_name: str, enabled: bool) -> None:
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    plugins_cfg = data.get("plugins_enabled")
    if not isinstance(plugins_cfg, dict):
        plugins_cfg = {}
    plugins_cfg[plugin_name] = enabled
    data["plugins_enabled"] = plugins_cfg
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── OpenCode Zen & Free Models Config ─────────────────────────────────────────

# ── OpenCode Zen & Free Models Config ─────────────────────────────────────────

OPENCODE_ZEN_FREE_MODELS = [
    "opencode/nemotron-3-ultra-free",  # 1M Context, complex multi-file refactoring (Default)
    "opencode/big-pickle",             # Specialized agentic coding stealth model
    "opencode/mimo-v2.5-free",         # Fast execution code generator
    "opencode/nemotron-3.5-lightning-free", # High speed NVIDIA model
    "opencode/ling-3.0-flash-fin-free",     # Multimodal vision & reasoning
    "toeknh/deepseek-v4.1-flash:free",      # DeepSeek V4.1 Flash free
]

DEFAULT_OPENCODE_MODEL = "opencode/nemotron-3-ultra-free"
DEFAULT_OPENCODE_PROVIDER = "zen"


def get_opencode_provider() -> str:
    """Return configured OpenCode provider (defaults to 'zen')."""
    return load_api_keys().get("opencode_provider", DEFAULT_OPENCODE_PROVIDER) or DEFAULT_OPENCODE_PROVIDER


def save_opencode_provider(provider: str) -> None:
    """Persist OpenCode provider to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["opencode_provider"] = provider.strip() or DEFAULT_OPENCODE_PROVIDER
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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
            raw = "opencode/mimo-v2.5-free"
        else:
            raw = f"opencode/{name}"
    return raw


def save_opencode_model(model: str) -> None:
    """Persist chosen OpenCode model to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["opencode_model"] = model.strip() or DEFAULT_OPENCODE_MODEL
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    m = model.strip() or DEFAULT_KILO_MODEL
    if not m.startswith("kilo/"):
        m = f"kilo/{m}"
    data["kilo_model"] = m
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Antigravity CLI & Model Config ───────────────────────────────────────────

ANTIGRAVITY_CLI_MODELS = [
    "gemini-3.7-flash-medium",     # Gemini 3.7 Flash Medium (Default Fast & Smart)
    "gemini-3.8-flash-medium",     # Gemini 3.8 Flash Medium
    "gemini-3.6-flash-medium",     # Gemini 3.6 Flash Medium
    "gemini-3.1-pro-high",         # Gemini 3.1 Pro High Reasoning
    "gemini-3.1-pro-low",          # Gemini 3.1 Pro Fast
    "claude-sonnet-4-6",           # Claude Sonnet 4.6 (Thinking)
    "claude-opus-4-6-thinking",    # Claude Opus 4.6 (Deep Thinking)
    "gpt-oss-120b-medium",         # GPT-OSS 120B Open Weights
]

DEFAULT_ANTIGRAVITY_MODEL = "gemini-3.7-flash-medium"


def get_antigravity_model() -> str:
    """Return configured Antigravity CLI model (defaults to 'gemini-3.7-flash-medium')."""
    return load_api_keys().get("antigravity_model", DEFAULT_ANTIGRAVITY_MODEL) or DEFAULT_ANTIGRAVITY_MODEL


def save_antigravity_model(model: str) -> None:
    """Persist chosen Antigravity model to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["antigravity_model"] = model.strip() or DEFAULT_ANTIGRAVITY_MODEL
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


# ── Groq LPU Coprocessor Config ──────────────────────────────────────────────

DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"


def get_groq_api_key() -> str | None:
    """Return the configured Groq API key, or None if not set."""
    key = load_api_keys().get("groq_api_key", "").strip()
    return key if key else None


def get_groq_model() -> str:
    """Return configured Groq model (defaults to 'llama-3.3-70b-versatile')."""
    return load_api_keys().get("groq_model", DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL


def save_groq_config(api_key: str, model: str = DEFAULT_GROQ_MODEL) -> None:
    """Persist Groq API key and default model to config."""
    ensure_config_dir()
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if api_key:
        data["groq_api_key"] = api_key.strip()
    if model:
        data["groq_model"] = model.strip() or DEFAULT_GROQ_MODEL
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")