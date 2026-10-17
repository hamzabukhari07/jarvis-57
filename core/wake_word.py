"""
Local wake-word detection for ZEZO ("Hey <assistant name>").

Design goals:
  • ZERO cost when the feature is off — openwakeword is imported ONLY inside
    start()/install helpers, never at module load. If the user never enables
    wake word, none of this touches the app.
  • ZERO latency on the audio path — the microphone callback only ever does a
    cheap, non-blocking queue push (feed()); the actual model inference runs in
    this module's own background thread, so the real-time audio thread and the
    Gemini stream are never slowed.
  • Fully local & offline — audio fed here never leaves the machine; there is no
    network call except the one-time model download the user triggers from the UI.

The active wake phrase is "Hey <assistant name>". Names resolve through a preset
registry plus a local models folder (config/wakewords/*.onnx), so adding a wake
word is a file drop — never a code change.

openwakeword ships small ONNX models (a few MB each) and runs comfortably on a
CPU. Only the packaged "hey_jarvis" model is guaranteed out of the box; custom
names (e.g. hey_zezo, hey_nova) are trained once and dropped into config/wakewords/.
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

# ── Preset assistant identities ──────────────────────────────────────────────
# ONE list drives both the Assistant Persona dropdown and the wake detector.
# "model" is an openwakeword model id: resolved from config/wakewords/<id>.onnx
# first, then from the packaged openwakeword models.
WAKE_PRESETS = [
    {"id": "zezo",   "name": "Zezo",   "model": "hey_zezo"},
    {"id": "nova",   "name": "Nova",   "model": "hey_nova"},
    {"id": "jarvis", "name": "Jarvis", "model": "hey_jarvis"},
]
DEFAULT_PRESET_ID      = "zezo"
DEFAULT_ASSISTANT_NAME = "Zezo"

# Score in [0,1]; above this counts as a detection. Tunable per environment.
DEFAULT_THRESHOLD = 0.6
# Mic frames arrive at 16 kHz int16; this is just the detector's input rate.
SAMPLE_RATE = 16000


# ── Paths ────────────────────────────────────────────────────────────────────

def _config_dir() -> Path:
    """The config/ dir, matching memory.config_manager (frozen-aware). Never raises."""
    try:
        from memory.config_manager import CONFIG_DIR
        return Path(CONFIG_DIR)
    except Exception:
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) \
            else Path(__file__).resolve().parent.parent
        return base / "config"


def wake_words_dir() -> Path:
    """Folder the user drops imported/trained wake models into."""
    return _config_dir() / "wakewords"


def _local_model(model_id: str) -> Path | None:
    for ext in (".onnx", ".tflite"):
        p = wake_words_dir() / f"{model_id}{ext}"
        if p.is_file():
            return p
    return None


def _packaged_dir() -> Path | None:
    try:
        import openwakeword
        return Path(openwakeword.__file__).resolve().parent / "resources" / "models"
    except Exception:
        return None


def _packaged_model(model_id: str) -> bool:
    d = _packaged_dir()
    if not d or not d.is_dir():
        return False
    return bool(any(d.glob(f"{model_id}*.onnx")) or any(d.glob(f"{model_id}*.tflite")))


def resolve_model(model_id: str) -> str | None:
    """A loadable model reference: a local .onnx path first, else a packaged
    openwakeword model id. None when the model exists nowhere."""
    model_id = (model_id or "").strip()
    if not model_id:
        return None
    local = _local_model(model_id)
    if local is not None:
        return str(local)
    if _packaged_model(model_id):
        return model_id
    return None


# ── Preset <-> name helpers ──────────────────────────────────────────────────

def _preset(name: str) -> dict | None:
    key = (name or "").strip().lower()
    for p in WAKE_PRESETS:
        if key and (p["name"].lower() == key or p["id"] == key):
            return p
    return None


def default_wake_model() -> str:
    """A wake model guaranteed to resolve: hey_zezo if shipped, else hey_jarvis."""
    for candidate in ("hey_zezo", "hey_jarvis"):
        if resolve_model(candidate):
            return candidate
    return "hey_jarvis"


def model_for_name(name: str) -> str:
    """Wake model id for an assistant name; unknown names fall back to the default."""
    p = _preset(name)
    if p and resolve_model(p["model"]):
        return p["model"]
    return default_wake_model()


def phrase_for_name(name: str) -> str:
    """'Nova' -> 'Hey Nova' (used for the UI hint and log lines)."""
    return f"Hey {(name or '').strip() or DEFAULT_ASSISTANT_NAME}"


def _pretty_name(model_id: str) -> str:
    s = model_id
    for prefix in ("hey_", "ok_", "hi_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return " ".join(w.capitalize() for w in s.replace("_", " ").split()) or model_id


def list_wake_presets() -> list[dict]:
    """Presets plus any extra config/wakewords/*.onnx, for the Persona dropdown.
    Each entry: {id, name, phrase, model, available}.
    On Windows, the native SAPI grammar supports any dynamic name natively.
    """
    out: list[dict] = []
    seen: set[str] = set()
    is_win = (sys.platform == "win32")
    for p in WAKE_PRESETS:
        seen.add(p["model"])
        available = True if is_win else (resolve_model(p["model"]) is not None)
        out.append({
            "id": p["id"], "name": p["name"], "phrase": f"Hey {p['name']}",
            "model": p["model"], "available": available,
        })
    d = wake_words_dir()
    if d.is_dir():
        for f in sorted(d.glob("*.onnx")):
            if f.stem in seen:
                continue
            name = _pretty_name(f.stem)
            out.append({
                "id": f.stem, "name": name, "phrase": f"Hey {name}",
                "model": f.stem, "available": True,
            })
    return out


# ── Install / readiness ──────────────────────────────────────────────────────

def is_installed() -> bool:
    """True if the openwakeword package is importable (no model check)."""
    try:
        import importlib.util
        return importlib.util.find_spec("openwakeword") is not None
    except Exception:
        return False


def is_ready(model_id: str = "") -> bool:
    """True if wake word detection can run.
    On Windows, the native SAPI Speech Recognition grammar engine is built-in
    and always ready for any dynamic name (no external downloads needed).
    On non-Windows, checks for openwakeword package and models on disk.
    """
    if sys.platform == "win32":
        try:
            import win32com.client
            return True
        except Exception:
            pass

    if not is_installed():
        return False
    try:
        if resolve_model(model_id) is None:
            model_id = default_wake_model()
            if resolve_model(model_id) is None:
                return False
        d = _packaged_dir()
        if not d or not d.is_dir():
            return False
        has_mel = any(d.glob("melspectrogram*.onnx")) or any(d.glob("melspectrogram*.tflite"))
        has_emb = any(d.glob("embedding_model*.onnx")) or any(d.glob("embedding_model*.tflite"))
        return bool(has_mel and has_emb)
    except Exception:
        return False


def install_and_download(logger: Callable[[str], None] = print,
                         notify: Callable[[str], None] | None = None,
                         model_id: str = "") -> tuple[bool, str]:
    """
    One-click setup for the UI button:
    On Windows, native grammar recognition is built-in and requires no download.
    """
    if sys.platform == "win32":
        return True, "Native Windows Speech Recognition is active and ready."
    _tell = notify or (lambda _msg: None)
    try:
        if not is_installed():
            logger("Wake word: installing openwakeword (one-time)…")
            _tell("Wake word: installing openwakeword (one-time)…")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "openwakeword"],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                return False, f"pip install failed: {tail[0][:160]}"
        logger("Wake word: downloading models…")
        _tell("Wake word: downloading models…")
        try:
            import openwakeword.utils as _u
            try:
                _u.download_models([model_id] if model_id else [])
            except TypeError:
                _u.download_models()
        except Exception as e:
            return False, f"model download failed: {e}"

        if not is_ready(model_id):
            return False, "installed, but the wake model could not be loaded."
        logger("Wake word: ready.")
        return True, "Wake word installed and ready."
    except Exception as e:
        return False, f"setup error: {e}"


class WindowsGrammarDetector:
    """
    Native Windows SAPI Dynamic Grammar wake-word detector.
    Inspired by Bigfoot (input-helper.exe):
    - Uses Windows built-in SAPI engine (SAPI.SpSharedRecognizer).
    - Generates dynamic grammar XML on the fly for the chosen assistant name:
      "hey <name>", "hi <name>", "okay <name>", "<name>".
    - Zero external models, zero downloads, zero training. Runs offline at ~0.1% CPU.
    """

    def __init__(self, on_detect: Callable[[], None],
                 phrase: str = "",
                 logger: Callable[[str], None] = print,
                 notify: Callable[[str], None] | None = None):
        self._on_detect = on_detect
        self._phrase = (phrase or DEFAULT_ASSISTANT_NAME).strip()
        self._logger = logger
        self._notify = notify or (lambda _msg: None)
        self._thread: threading.Thread | None = None
        self._running = False
        self._ready = False
        self._reco_context = None

    @property
    def phrase(self) -> str:
        return self._phrase

    @property
    def ready(self) -> bool:
        return self._ready

    def feed(self, frame_int16) -> None:
        """PortAudio mic audio is captured via PortAudio for Gemini Live;
        Windows SAPI accesses the default microphone endpoint directly."""
        pass

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._ready = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="WinWakeGrammarThread")
        self._thread.start()
        self._logger(f"Native Windows Wake Word: active for '{self._phrase}'.")
        return True

    def stop(self) -> None:
        self._running = False
        self._ready = False
        self._reco_context = None

    def _run_loop(self) -> None:
        import tempfile
        import os
        try:
            import win32com.client
            import pythoncom
        except Exception as e:
            self._logger(f"Native SAPI unavailable: {e}")
            return

        pythoncom.CoInitialize()
        tmp_path = None
        try:
            try:
                # In-process recognizer runs quietly inside ZEZO without OS wizard popups
                recognizer = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
                category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
                category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput")
                token = win32com.client.Dispatch("SAPI.SpObjectToken")
                token.SetId(category.Default)
                recognizer.AudioInput = token
                self._logger(f"Native SAPI bound to microphone: {token.GetDescription()}")
            except Exception as bind_err:
                self._logger(f"InprocRecognizer AudioInput failed ({bind_err}), falling back to SpSharedRecognizer")
                recognizer = win32com.client.Dispatch("SAPI.SpSharedRecognizer")

            context = recognizer.CreateRecoContext()
            self._reco_context = context

            # Extract clean name stem (e.g. 'Hey Nova' -> 'nova')
            name_stem = self._phrase.lower()
            for pfx in ("hey ", "hi ", "okay ", "ok "):
                if name_stem.startswith(pfx):
                    name_stem = name_stem[len(pfx):].strip()
                    break

            # Build Bigfoot dynamic grammar choices
            phrases = [
                f"hey {name_stem}",
                f"hi {name_stem}",
                f"okay {name_stem}",
                f"ok {name_stem}",
                name_stem,
            ]
            if name_stem == "nova":
                phrases.extend(["hey noba", "noba", "hey hova", "hova"])
            elif name_stem == "zezo":
                phrases.extend(["hey zizo", "zizo", "hey zeezo", "zeezo"])
            elif name_stem == "jarvis":
                phrases.extend(["hey jarvis", "jarvis"])

            rules_xml = "".join(f"<P>{p}</P>" for p in phrases)
            grammar_xml = f'''<GRAMMAR LANGID="409">
                <RULE NAME="WAKE" TOPLEVEL="ACTIVE">
                    <L>{rules_xml}</L>
                </RULE>
            </GRAMMAR>'''

            with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w", encoding="utf-8") as f:
                f.write(grammar_xml)
                tmp_path = f.name

            grammar = context.CreateGrammar(1)
            grammar.CmdLoadFromFile(tmp_path, 0)
            grammar.CmdSetRuleState("WAKE", 1)
            detector_self = self

            class _Sink:
                def OnRecognition(sink_self, StreamNumber, StreamPosition, RecognitionType, Result):
                    try:
                        try:
                            res_obj = win32com.client.Dispatch(Result)
                            text = res_obj.PhraseInfo.GetText().strip().lower()
                        except Exception:
                            text = Result.PhraseInfo.GetText().strip().lower()
                        now = time.monotonic()
                        if now - getattr(sink_self, "_last_hit", 0.0) < 2.0:
                            return
                        sink_self._last_hit = now
                        detector_self._logger(f"Native Wake Word spotted: '{text}'")
                        try:
                            detector_self._on_detect()
                        except Exception as det_err:
                            detector_self._logger(f"on_detect error: {det_err}")
                    except Exception as err:
                        detector_self._logger(f"Recognition parse error: {err}")

            sink = win32com.client.WithEvents(context, _Sink)

            while self._running:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.05)

        except Exception as e:
            self._logger(f"Native Windows Wake loop ended: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            pythoncom.CoUninitialize()


class WakeWordDetector:
    """
    Main Wake Word Interface.
    On Windows: Uses WindowsGrammarDetector (Bigfoot dynamic grammar pattern)
    On Linux/Mac: Uses openWakeWord fallback
    """

    def __init__(self, on_detect: Callable[[], None],
                 model_id: str = "",
                 phrase: str = "",
                 threshold: float = DEFAULT_THRESHOLD,
                 logger: Callable[[str], None] = print,
                 notify: Callable[[str], None] | None = None):
        self._on_detect = on_detect
        self._model_id  = (model_id or "").strip()
        self._phrase    = phrase or DEFAULT_ASSISTANT_NAME
        self._threshold = threshold
        self._logger    = logger
        self._notify    = notify or (lambda _msg: None)
        self._native_engine = None

        if sys.platform == "win32":
            self._native_engine = WindowsGrammarDetector(
                on_detect=on_detect,
                phrase=self._phrase,
                logger=logger,
                notify=notify,
            )

        # openWakeWord fallback structures
        self._debounce = 1.5
        self._cooldown = 1.5
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._running = False
        self._model = None
        self._ready = False
        self._key = ""

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def phrase(self) -> str:
        return self._phrase

    @property
    def ready(self) -> bool:
        if self._native_engine is not None:
            return self._native_engine.ready
        return self._ready

    def start(self) -> bool:
        if self._native_engine is not None:
            return self._native_engine.start()

        if self._running:
            return True
        ref = resolve_model(self._model_id) or resolve_model(default_wake_model())
        if ref is None:
            self._logger(f"Wake word: model '{self._model_id}' not found.")
            self._notify("Wake word unavailable — use the WAKE NOW button.")
            return False
        try:
            from openwakeword.model import Model
            self._model = Model(wakeword_models=[ref], inference_framework="onnx")
            self._key = Path(ref).stem if ref.lower().endswith((".onnx", ".tflite")) else ref
        except Exception as e:
            self._logger(f"Wake word: could not load model — {e}")
            self._notify("Wake word unavailable — use the WAKE NOW button.")
            self._model = None
            return False
        self._running = True
        self._ready = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeWordThread")
        self._thread.start()
        self._logger(f"Wake word: listening for '{self._phrase}'.")
        return True

    def stop(self) -> None:
        if self._native_engine is not None:
            self._native_engine.stop()
        self._running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        self._model = None
        self._ready = False

    def feed(self, frame_int16) -> None:
        if self._native_engine is not None:
            return
        if not self._running:
            return
        try:
            data = frame_int16[:, 0].copy() if getattr(frame_int16, "ndim", 1) > 1 else frame_int16.copy()
            self._queue.put_nowait(data)
        except queue.Full:
            pass
        except Exception:
            pass

    def _match(self, key: str) -> bool:
        return bool(self._key) and self._key.lower() in (key or "").lower()

    def _loop(self) -> None:
        import numpy as np
        cooldown_until = 0.0
        while self._running:
            try:
                frame = self._queue.get()
                if frame is None or not self._running:
                    break
                arr = np.asarray(frame, dtype=np.int16)
                try:
                    scores = self._model.predict(arr, debounce_time=self._debounce)
                except TypeError:
                    scores = self._model.predict(arr)
                score = 0.0
                if isinstance(scores, dict):
                    score = max((float(v) for k, v in scores.items() if self._match(k)), default=0.0)
                now = time.monotonic()
                if score >= self._threshold and now >= cooldown_until:
                    cooldown_until = now + self._cooldown
                    self._drain()
                    try:
                        self._on_detect()
                    except Exception as e:
                        self._logger(f"Wake word: on_detect error — {e}")
            except Exception as e:
                self._logger(f"Wake word: inference error — {e}")

    def _drain(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except Exception:
            pass
