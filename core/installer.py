"""
MARK XL — Dependency auto-installer.

Called automatically on first launch and after engine reconfiguration.
Installs only the packages that are actually missing, then exits cleanly.
"""
from __future__ import annotations

import hashlib
import importlib.util
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable

# ── Package lists ─────────────────────────────────────────────────────────
# Each entry: (import_name, pip_package_name)

_CORE: list[tuple[str, str]] = [
    ("psutil",             "psutil"),
    ("PIL",                "pillow"),
    ("sounddevice",        "sounddevice"),
    ("numpy",              "numpy"),
    ("requests",           "requests"),
    ("bs4",                "beautifulsoup4"),
    ("ddgs",               "ddgs"),
    ("pyautogui",          "pyautogui"),
    ("pyperclip",          "pyperclip"),
    ("pygetwindow",        "pygetwindow"),
    ("mss",                "mss"),
    ("cv2",                "opencv-python"),
    ("soundfile",          "soundfile"),
    ("miniaudio",          "miniaudio"),
    ("send2trash",         "send2trash"),
    ("pptx",               "python-pptx"),
    ("youtube_transcript_api", "youtube-transcript-api"),
]

# Windows-only (pywinauto, pycaw, win10toast, comtypes)
_WINDOWS: list[tuple[str, str]] = [
    ("comtypes",   "comtypes"),
    ("pycaw",      "pycaw"),
    ("win10toast", "win10toast"),
    ("pywinauto",  "pywinauto"),
]

# STT engine packages
_STT: dict[str, list[tuple[str, str]]] = {
    "whisper": [("faster_whisper", "faster-whisper")],
    "vosk":    [("vosk",           "vosk")],
}

# TTS engine packages
_TTS: dict[str, list[tuple[str, str]]] = {
    "edgetts":    [("edge_tts", "edge-tts")],
    # kokoro>=0.9 dropped AlbertModel/AutoModel from transformers — version pin is critical
    "kokoro":     [("kokoro",   "kokoro>=0.9"), ("soundfile", "soundfile")],
    "elevenlabs": [],   # uses only requests, already in core
}


# ── Helpers ───────────────────────────────────────────────────────────────

def _available(module: str) -> bool:
    """Return True if the module can be imported (no actual import)."""
    return importlib.util.find_spec(module) is not None


def _pip(package: str, log: Callable | None = None) -> bool:
    if log:
        log(f"SYS: pip install {package} …")
    result = subprocess.run(
        [
            sys.executable, "-m", "pip", "install", package,
            "--quiet", "--disable-pip-version-check",
        ],
        capture_output=True,
    )
    ok = result.returncode == 0
    if not ok and log:
        stderr = result.stderr.decode(errors="replace").strip()
        log(f"ERR: {package} install failed — {stderr[:140]}")
    return ok


# ── Baseline requirements.txt bootstrap ───────────────────────────────────

# One representative import per dependency in requirements.txt, used as the
# truth for "is this installed?" and as the fallback install set if the full
# manifest install fails. Keep it in step with requirements.txt.
_SENTINELS_XPLAT: list[tuple[str, str]] = [
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
    ("google.genai", "google-genai"),
    ("aiohttp", "aiohttp"),
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("playwright", "playwright"),
    ("scrapling", "scrapling[fetchers]"),
    ("ddgs", "ddgs"),
    ("duckduckgo_search", "duckduckgo-search"),
    ("pyautogui", "pyautogui"),
    ("pyperclip", "pyperclip"),
    ("pygetwindow", "pygetwindow"),
    ("PIL", "pillow"),
    ("cv2", "opencv-python"),
    ("mss", "mss"),
    ("psutil", "psutil"),
    ("send2trash", "send2trash"),
    ("youtube_transcript_api", "youtube-transcript-api"),
    ("yt_dlp", "yt-dlp"),
    ("feedparser", "feedparser"),
    ("pptx", "python-pptx"),
    ("openpyxl", "openpyxl"),
    ("docx", "python-docx"),
    ("PyPDF2", "PyPDF2"),
    ("pdfplumber", "pdfplumber"),
    ("markitdown", "markitdown"),
    ("docling", "docling"),
    ("pandas", "pandas"),
    ("pydub", "pydub"),
    ("py7zr", "py7zr"),
    ("paho.mqtt", "paho-mqtt"),
    ("pynvml", "pynvml"),
    ("edge_tts", "edge-tts"),
    ("miniaudio", "miniaudio"),
    ("faster_whisper", "faster-whisper"),
    ("whisper", "openai-whisper"),
    ("vosk", "vosk"),
    ("openwakeword", "openwakeword"),
    ("torch", "torch"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn[standard]"),
    ("cryptography", "cryptography"),
    ("multipart", "python-multipart"),
    ("qrcode", "qrcode[pil]"),
    ("googleapiclient", "google-api-python-client"),
    ("google_auth_oauthlib", "google-auth-oauthlib"),
    ("tinytuya", "tinytuya"),
    ("pytest", "pytest"),
    ("reportlab", "reportlab"),
]
if sys.version_info < (3, 14):
    # kokoro's G2P chain (misaki->spacy->blis) has no 3.14 wheels; mirrors the
    # `python_version < "3.14"` marker in requirements.txt.
    _SENTINELS_XPLAT.append(("kokoro", "kokoro>=0.7,<1"))
_SENTINELS_WIN: list[tuple[str, str]] = [
    ("comtypes", "comtypes"),
    ("pycaw", "pycaw"),
    ("win10toast", "win10toast"),
    ("pywinauto", "pywinauto"),
    ("win32com", "pywin32"),
    ("wmi", "wmi"),
]


def _requirements_file() -> Path:
    return Path(__file__).resolve().parent.parent / "requirements.txt"


def _requirements_stamp() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / ".deps_stamp"


def _install_missing_sentinels(log: Callable | None = None) -> bool:
    sentinels = list(_SENTINELS_XPLAT)
    if platform.system() == "Windows":
        sentinels += _SENTINELS_WIN
    missing = [pkg for mod, pkg in sentinels if not _available(mod)]
    if not missing:
        return True
    if log:
        log(f"SYS: Installing {len(missing)} missing dependency(ies): {', '.join(missing)}")
    ok = True
    for pkg in missing:
        ok = _pip(pkg, log) and ok
    return ok


def ensure_requirements(log: Callable | None = None) -> bool:
    """Install everything declared in requirements.txt — once per manifest.

    The manifest is comprehensive ("everything installs by default"), so the
    whole file is fed to pip the first time, and again whenever requirements.txt
    changes (detected by a content-hash stamp written to config/.deps_stamp).
    If the full install fails — one heavy package can fail to build and abort
    the rest — it falls back to installing only the sentinel packages the app
    needs, so a single bad sdist cannot disable unrelated features.

    Blocking — call from a background thread. A no-op (no pip, no network) once
    the manifest has installed successfully.
    """
    req = _requirements_file()
    if not req.exists():
        return _install_missing_sentinels(log)

    digest = hashlib.sha256(req.read_bytes()).hexdigest()
    stamp = _requirements_stamp()
    try:
        if stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
            return True
    except Exception:
        pass

    if log:
        log("SYS: Verifying dependencies from requirements.txt…")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req),
         "--disable-pip-version-check"],
        capture_output=True,
    )
    if r.returncode == 0:
        try:
            stamp.parent.mkdir(parents=True, exist_ok=True)
            stamp.write_text(digest, encoding="utf-8")
        except Exception:
            pass
        if log:
            log("SYS: All dependencies ready.")
        return True

    # Full install failed — say why, then guarantee the essentials. If the
    # fallback satisfies every sentinel, stamp the manifest anyway so a failing
    # optional build (or a transient file lock) is not retried on every launch.
    out = (r.stderr or r.stdout or b"").decode(errors="replace")
    lines = [ln.strip() for ln in out.strip().splitlines() if ln.strip()]
    err_lines = [ln for ln in lines if "error" in ln.lower()] or lines
    if log:
        log("ERR: requirements install failed — "
            + (err_lines[-1] if err_lines else "unknown error")[:220])
    ok = _install_missing_sentinels(log)
    if ok:
        try:
            stamp.parent.mkdir(parents=True, exist_ok=True)
            stamp.write_text(digest, encoding="utf-8")
        except Exception:
            pass
    return ok


def ensure_playwright_browsers(log: Callable | None = None) -> bool:
    """Download Playwright's Chromium if the installed package cannot find it.

    Python Playwright backs web_reader and the cloner's Tier-1 renderer. The old
    installer only fetched the browser when the package itself was just
    installed, so a later upgrade left the browser stale and every run failed
    with "Executable doesn't exist". Always check the executable, not the
    package version.
    """
    if not _available("playwright"):
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = p.chromium.executable_path
        if exe and Path(exe).exists():
            return True
    except Exception:
        pass

    if log:
        log("SYS: Downloading Playwright Chromium browser (one-time, ~150 MB)…")
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
    )
    if log:
        log("SYS: Playwright Chromium ready." if r.returncode == 0
            else "ERR: Playwright browser download failed.")
    return r.returncode == 0


# ── Public API ────────────────────────────────────────────────────────────

def install_for_config(config: dict, log: Callable | None = None) -> None:
    """
    Install all missing packages required by *config*.

    Blocking — always call from a background thread.
    Progress is reported via the optional *log* callback (receives a str).
    """
    stt = config.get("stt_engine", "whisper").lower()
    tts = config.get("tts_engine", "edgetts").lower()

    needed: list[tuple[str, str]] = list(_CORE)
    needed += _STT.get(stt, [])
    needed += _TTS.get(tts, [])
    if platform.system() == "Windows":
        needed += _WINDOWS

    # Deduplicate (preserve order, key = pip name)
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for mod, pkg in needed:
        if pkg not in seen:
            seen.add(pkg)
            unique.append((mod, pkg))

    missing = [(mod, pkg) for mod, pkg in unique if not _available(mod)]

    if not missing:
        if log:
            log("SYS: All dependencies already installed ✓")
        return

    pkg_names = ", ".join(p for _, p in missing)
    if log:
        log(f"SYS: Installing {len(missing)} package(s): {pkg_names}")

    for _mod, pkg in missing:
        _pip(pkg, log)

    # Playwright: package if absent, then ALWAYS make sure its Chromium exists.
    # The old code only downloaded the browser when the package itself was just
    # installed, so a later `pip install -U playwright` left the browser stale
    # and browser automation died with "Executable doesn't exist".
    if not _available("playwright"):
        _pip("playwright", log)
    ensure_playwright_browsers(log)

    if log:
        log("SYS: All dependencies ready ✓")
