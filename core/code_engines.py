"""
core/code_engines.py — Central registry and health probe for local coding CLIs.

Manages discovery, resolution, caching, and readiness verification for
supported autonomous code engines:
  - Antigravity CLI (agy)
  - OpenCode (opencode)
  - Kilo Code (kilo)

Adheres strictly to AGENTS.md:
  - Cyclomatic complexity < 15 per function
  - Dictionary dispatch (no if/elif ladders)
  - Windows subprocess flags (CREATE_NO_WINDOW)
  - Non-blocking / cached execution
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("zezo.code_engines")

# Process creation flags to prevent flashing terminal windows on Windows
_IS_WINDOWS = platform.system() == "Windows"
_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if _IS_WINDOWS else 0

CACHE_TTL = 300.0  # 5 minutes cache TTL for probed engine readiness
DEFAULT_ENGINE_KEY = "default_code_engine"


@dataclass(frozen=True)
class Engine:
    """Static registration for an autonomous coding engine."""
    id: str
    label: str
    short_code: str
    path_names: tuple[str, ...]
    vendor_dirs: tuple[Path, ...]
    version_argv: tuple[str, ...]
    models: tuple[str, ...]
    backs_tool: str
    install_command: str = ""
    install_needs: str = ""


@dataclass
class EngineStatus:
    """Dynamic probed state of a coding engine."""
    id: str
    label: str
    short_code: str
    state: str  # "ready" | "sign_in_required" | "not_installed" | "off" | "unknown"
    binary_path: Optional[str] = None
    version: Optional[str] = None
    models: tuple[str, ...] = ()
    reason: str = ""
    backs_tool: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "short_code": self.short_code,
            "state": self.state,
            "binary_path": self.binary_path,
            "version": self.version,
            "models": list(self.models),
            "reason": self.reason,
            "backs_tool": self.backs_tool,
            "timestamp": self.timestamp,
        }


# Path names tailored to target platform
_AGY_NAMES = (
    ("agy.exe", "agy", "antigravity.exe", "antigravity")
    if _IS_WINDOWS
    else ("agy", "antigravity")
)
_OPENCODE_NAMES = (
    ("opencode.cmd", "opencode.exe", "opencode")
    if _IS_WINDOWS
    else ("opencode",)
)
_KILO_NAMES = (
    ("kilo.cmd", "kilo.exe", "kilo", "kilocode.cmd", "kilocode.exe", "kilocode")
    if _IS_WINDOWS
    else ("kilo", "kilocode")
)

# Canonical vendor directories
_HOME = Path.home()
_AGY_VENDOR = (
    _HOME / "AppData" / "Local" / "agy" / "bin",
    _HOME / ".antigravity" / "bin",
    _HOME / ".agy" / "bin",
    _HOME / "AppData" / "Local" / "antigravity" / "bin",
    _HOME / "AppData" / "Roaming" / "npm",
)
_OPENCODE_VENDOR = (
    _HOME / ".opencode" / "bin",
    _HOME / "AppData" / "Roaming" / "npm",
    _HOME / "AppData" / "Local" / "opencode" / "bin",
)
_KILO_VENDOR = (
    _HOME / ".kilo" / "bin",
    _HOME / "AppData" / "Roaming" / "npm",
    _HOME / "AppData" / "Local" / "kilo" / "bin",
)

ENGINES: dict[str, Engine] = {
    "antigravity": Engine(
        id="antigravity",
        label="Antigravity CLI",
        short_code="AG",
        path_names=_AGY_NAMES,
        vendor_dirs=_AGY_VENDOR,
        version_argv=("--version",),
        models=(
            "gemini-3.8-flash-high",
            "gemini-3.8-flash-medium",
            "claude-sonnet-4-6",
            "claude-opus-4-6-thinking",
            "gpt-oss-120b-medium",
        ),
        backs_tool="antigravity_action",
        install_command='powershell -c "irm https://antigravity.dev/install.ps1 | iex"' if _IS_WINDOWS else "curl -fsSL https://antigravity.dev/install.sh | bash",
        install_needs="Standard shell, ~80 MB disk",
    ),
    "opencode": Engine(
        id="opencode",
        label="OpenCode",
        short_code="OC",
        path_names=_OPENCODE_NAMES,
        vendor_dirs=_OPENCODE_VENDOR,
        version_argv=("--version",),
        models=(
            "glm-5.3-flash-free",
            "mimo-v2.5-free",
            "opencode/nemotron-3-ultra-free",
        ),
        backs_tool="opencode_action",
        install_command="npm install -g opencode",
        install_needs="Node 20+, ~120 MB disk",
    ),
    "kilo": Engine(
        id="kilo",
        label="Kilo Code",
        short_code="KC",
        path_names=_KILO_NAMES,
        vendor_dirs=_KILO_VENDOR,
        version_argv=("--version",),
        models=(
            "kilo/free",
            "kilo/fast-code",
        ),
        backs_tool="kilo_action",
        install_command="npm install -g kilo",
        install_needs="Node 20+, ~90 MB disk",
    ),
}

# Cache state
_CACHE: dict[str, EngineStatus] = {}
_CACHE_LOCK = threading.Lock()


def resolve_binary(engine_id: str) -> Optional[str]:
    """Resolves executable path for given engine via PATH and vendor directories."""
    engine = ENGINES.get(engine_id)
    if not engine:
        return None

    # Step 1: probe system PATH
    for name in engine.path_names:
        found = shutil.which(name)
        if found and Path(found).is_file():
            return found

    # Step 2: probe vendor directory candidates
    for vdir in engine.vendor_dirs:
        for name in engine.path_names:
            candidate = vdir / name
            if candidate.is_file():
                return str(candidate)

    return None


def _probe_version(bin_path: str, version_argv: tuple[str, ...]) -> Optional[str]:
    """Executes version check probe returning sanitized first line."""
    try:
        cmd = [bin_path] + list(version_argv)
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=_CREATION_FLAGS,
        )
        combined = (res.stdout or res.stderr or "").strip()
        if combined:
            first_line = combined.splitlines()[0].strip()
            return first_line[:60]
    except Exception as e:
        logger.debug("Failed to probe version for %s: %s", bin_path, e)
    return None


def _probe_antigravity_auth(bin_path: str, engine: Engine) -> tuple[str, str]:
    """Honest auth probe for Antigravity CLI."""
    # Fast path: check local settings file or environment credentials
    has_local_creds = False
    creds_source = ""
    settings_candidates = (
        Path.home() / ".gemini" / "antigravity-cli" / "settings.json",
        Path.home() / ".antigravity" / "settings.json",
    )
    for cfg_candidate in settings_candidates:
        try:
            if cfg_candidate.is_file() and cfg_candidate.stat().st_size > 0:
                has_local_creds = True
                creds_source = cfg_candidate.name
                break
        except Exception as e:
            logger.debug("Error checking antigravity settings %s: %s", cfg_candidate, e)

    env = os.environ.copy()
    try:
        from memory.config_manager import load_api_keys
        cfg_keys = load_api_keys()
        gem_key = cfg_keys.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if gem_key:
            env["GEMINI_API_KEY"] = gem_key
            has_local_creds = True
            creds_source = creds_source or "GEMINI_API_KEY"
    except Exception:
        pass

    try:
        cmd = [bin_path, "models"]
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=_CREATION_FLAGS,
            env=env,
        )
        combined = f"{res.stdout}\n{res.stderr}".lower()
        if "not logged in" in combined or "error getting token" in combined or "sign in" in combined:
            return "sign_in_required", "Installed, but no account is signed in. The CLI exits in seconds and produces no files."
        if res.returncode == 0 and ("gemini" in combined or "claude" in combined or "gpt" in combined):
            return "ready", "Installed and authenticated. Accepts model prompts and generates multi-file diffs."
        if res.returncode == 0:
            return "ready", "Installed and responsive."
        if has_local_creds:
            return "ready", f"Installed with local credentials ({creds_source})."
        return "sign_in_required" if "auth" in combined else "unknown", f"Antigravity status uncertain (code {res.returncode})."
    except subprocess.TimeoutExpired:
        if has_local_creds:
            return "ready", f"Installed with local credentials ({creds_source}); live model probe timed out."
        return "unknown", "Probe timed out while contacting Antigravity CLI."
    except Exception as e:
        if has_local_creds:
            return "ready", f"Installed with local credentials ({creds_source}); probe error: {e}"
        return "unknown", f"Probe error: {e}"


def _probe_opencode_auth(bin_path: str, engine: Engine) -> tuple[str, str]:
    """Honest auth probe for OpenCode."""
    # Fast path: check cached credentials file
    try:
        auth_file = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        if auth_file.is_file():
            data = json.loads(auth_file.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and len(data) > 0:
                return "ready", f"Authenticated with {len(data)} stored provider key(s)."
    except Exception as e:
        logger.debug("Error checking opencode auth.json: %s", e)

    # CLI fallback check
    try:
        cmd = [bin_path, "auth", "list"]
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=_CREATION_FLAGS,
        )
        combined = f"{res.stdout}\n{res.stderr}".lower()
        if "api key" in combined or "stored" in combined:
            return "ready", "Authenticated with stored provider keys."
        if "no credentials" in combined or "no integrations" in combined:
            return "sign_in_required", "Installed, but no provider API key is stored."
    except Exception:
        pass

    return "sign_in_required", "Installed, but no authenticated credentials detected."


def _probe_kilo_auth(bin_path: str, engine: Engine) -> tuple[str, str]:
    """Honest auth probe for Kilo Code."""
    # Fast path: check cached credentials file
    try:
        auth_file = Path.home() / ".local" / "share" / "kilo" / "auth.json"
        if auth_file.is_file():
            data = json.loads(auth_file.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and len(data) > 0:
                return "ready", f"Authenticated ({len(data)} credential profile)."
    except Exception as e:
        logger.debug("Error checking kilo auth.json: %s", e)

    # CLI fallback check
    try:
        cmd = [bin_path, "auth", "list"]
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=_CREATION_FLAGS,
        )
        combined = f"{res.stdout}\n{res.stderr}".lower()
        if "credentials" in combined or "gateway" in combined:
            return "ready", "Authenticated with Kilo Gateway."
    except Exception:
        pass

    return "sign_in_required", "Installed, but no authenticated credentials detected."


AUTH_PROBERS: dict[str, Callable[[str, Engine], tuple[str, str]]] = {
    "antigravity": _probe_antigravity_auth,
    "opencode": _probe_opencode_auth,
    "kilo": _probe_kilo_auth,
}


def probe_engine(engine_id: str, force: bool = False) -> dict[str, Any]:
    """
    Non-blocking or cached probe function returning status dictionary.
    Possible states: "not_installed", "sign_in_required", "ready", "off", "unknown".
    """
    engine = ENGINES.get(engine_id)
    if not engine:
        return {
            "id": engine_id,
            "label": engine_id,
            "short_code": "?",
            "state": "unknown",
            "binary_path": None,
            "version": None,
            "models": [],
            "reason": f"Unknown engine identifier '{engine_id}'.",
            "backs_tool": "",
            "timestamp": time.time(),
        }

    now = time.time()
    with _CACHE_LOCK:
        if not force and engine_id in _CACHE:
            cached = _CACHE[engine_id]
            if (now - cached.timestamp) < CACHE_TTL:
                return cached.to_dict()

    # Step 1: Binary resolution
    bin_path = resolve_binary(engine_id)
    if not bin_path:
        status = EngineStatus(
            id=engine.id,
            label=engine.label,
            short_code=engine.short_code,
            state="not_installed",
            binary_path=None,
            version=None,
            models=engine.models,
            reason=f"Binary not found on PATH or in vendor directories ({', '.join(engine.path_names[:2])}).",
            backs_tool=engine.backs_tool,
            timestamp=now,
        )
        with _CACHE_LOCK:
            _CACHE[engine_id] = status
        return status.to_dict()

    # Step 2: Version probe
    version = _probe_version(bin_path, engine.version_argv)

    # Step 3: Auth probe via dispatch table
    prober = AUTH_PROBERS.get(engine_id)
    state, reason = (
        prober(bin_path, engine)
        if prober
        else ("unknown", "Installed · sign-in state unknown.")
    )

    status = EngineStatus(
        id=engine.id,
        label=engine.label,
        short_code=engine.short_code,
        state=state,
        binary_path=bin_path,
        version=version,
        models=engine.models,
        reason=reason,
        backs_tool=engine.backs_tool,
        timestamp=now,
    )
    with _CACHE_LOCK:
        _CACHE[engine_id] = status
    return status.to_dict()


def probe_all_engines(force: bool = False) -> list[dict[str, Any]]:
    """Probes status of all registered code engines."""
    return [probe_engine(eid, force=force) for eid in ENGINES]


def get_default_engine() -> str:
    """Reads configured default coding engine or defaults to antigravity."""
    try:
        from memory.config_manager import load_api_keys
        cfg = load_api_keys()
        val = cfg.get(DEFAULT_ENGINE_KEY)
        if val in ENGINES:
            return str(val)
    except Exception:
        pass
    return "antigravity"


def set_default_engine(engine_id: str) -> bool:
    """Persists default coding engine."""
    if engine_id not in ENGINES:
        return False
    try:
        from memory.config_manager import _patch_config
        _patch_config(default_code_engine=engine_id)
        return True
    except Exception as e:
        logger.error("Failed to save default code engine: %s", e)
        return False
