"""
core/models.py — Single source of truth for every provider model identifier.

WHY THIS FILE EXISTS
    Model names get retired (e.g. the old `gemini-2.5-*` / `2.0` / `1.5` names
    now 404 for new keys). When the same string is hardcoded in several files,
    one dead name silently disables a feature in only one of them. Every model
    name now lives here; call sites import from here and never hardcode a model
    string. `core/provider_health.py` pings these at startup and reports which
    are alive.

    Change a model name HERE and the whole app follows.

NO HEAVY IMPORTS
    This module imports nothing from `core/` or `memory/`, so it is safe to
    import from anywhere (`main.py` early, `config_manager.py`, `core/gemini.py`).
"""

# ── Gemini Live (realtime voice) ─────────────────────────────────────────────
# main.py opens the live voice session with this. One-shot Live calls in
# core/gemini.py reuse whatever main.py set (`_live_model()`), falling back here.
GEMINI_LIVE_MODEL = "models/gemini-3.1-flash-live-preview"

# ── Gemini one-shot REST ladders ─────────────────────────────────────────────
# Verified live against this key (2026-09-25): gemini-3.6-flash, gemini-3.5-flash
# and gemini-3-flash-preview answer; gemini-3.7/3.8-flash and gemini-flash-latest
# were 503 (high demand); the old gemini-2.5-*/2.0/1.5 names are 404 for new keys.
# `core/gemini.py` prepends the LIVE sentinel for the rungs that allow it.
GEMINI_FAST_MODELS = (
    "gemini-3-flash-preview",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)
GEMINI_SMART_MODELS = (
    "gemini-3-flash-preview",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)
# Grounded search needs `grounding_metadata`, which a Live turn does not produce,
# so SEARCH is REST-only (no LIVE rung).
GEMINI_SEARCH_MODELS = (
    "gemini-3-flash-preview",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-flash-latest",
)


# ── Antigravity CLI models (agent synthesis) ─────────────────────────────────
# These are the CLI's own model ids (with -medium/-high suffixes) — a different
# namespace from the Gemini API names above. Do not mix the two.
ANTIGRAVITY_CLI_MODELS = [
    "gemini-3.8-flash-high",       # Gemini 3.8 Flash (High)
    "gemini-3.8-flash-medium",     # Gemini 3.8 Flash (Medium)
    "gemini-3.8-flash-low",        # Gemini 3.8 Flash (Low)
    "gemini-3.7-flash-high",       # Gemini 3.7 Flash (High)
    "gemini-3.7-flash-medium",     # Gemini 3.7 Flash (Medium) - Default
    "gemini-3.7-flash-low",        # Gemini 3.7 Flash (Low)
    "gemini-3.6-flash-high",       # Gemini 3.6 Flash (High)
    "gemini-3.6-flash-medium",     # Gemini 3.6 Flash (Medium)
    "gemini-3.6-flash-low",        # Gemini 3.6 Flash (Low)
    "gemini-3.1-pro-high",         # Gemini 3.1 Pro (High)
    "gemini-3.1-pro-low",          # Gemini 3.1 Pro (Low)
    "claude-sonnet-4-6",           # Claude Sonnet 4.6 (Thinking)
    "claude-opus-4-6-thinking",    # Claude Opus 4.6 (Thinking)
    "gpt-oss-120b-medium",         # GPT-OSS 120B (Medium)
]
DEFAULT_ANTIGRAVITY_MODEL = "gemini-3.7-flash-medium"

# Friendly aliases → canonical Antigravity model id.
ANTIGRAVITY_MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-6",
    "claude": "claude-sonnet-4-6",
    "claude-sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6-thinking",
    "claude-opus": "claude-opus-4-6-thinking",
    "3.7": "gemini-3.7-flash-medium",
    "gemini-3.7": "gemini-3.7-flash-medium",
    "3.8": "gemini-3.8-flash-medium",
    "gemini-3.8": "gemini-3.8-flash-medium",
    "3.6": "gemini-3.6-flash-medium",
    "pro": "gemini-3.1-pro-high",
    "pro-high": "gemini-3.1-pro-high",
    "pro-low": "gemini-3.1-pro-low",
    "gpt": "gpt-oss-120b-medium",
    "gpt-oss": "gpt-oss-120b-medium",
}


# ── Groq LPU (free-tier coprocessor) ─────────────────────────────────────────
# Groq's public free tier exposes NO multimodal/vision model, so vision is
# opt-in (empty default → images go straight to the Gemini ladder).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_GROQ_VISION_MODEL = ""
DEFAULT_GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"


# ── Health-check targets ─────────────────────────────────────────────────────
# The REST/API names to verify at startup (deduped, no LIVE sentinel).
GEMINI_CHECK_MODELS = tuple(dict.fromkeys(
    GEMINI_FAST_MODELS + GEMINI_SMART_MODELS + GEMINI_SEARCH_MODELS
))
