"""
Screen & webcam capture for JARVIS vision.

Provides the two capture entry points main.py uses — `_capture_screen()` and
`_capture_camera()` — plus their helpers (compression, camera auto-detection,
config access). main.py grabs a frame here on demand, then injects it into the
main Gemini Live session; there is no separate vision session here.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"[Vision] ⚠️  Could not save config key '{key}': {e}")


def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()


_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_Q    = 82

import ctypes

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def get_display_metrics() -> dict:
    """Returns primary display resolution and DPI scaling factor."""
    metrics = {"width": 1920, "height": 1080, "dpi_scale": 1.0}
    if platform_system := _get_os():
        if platform_system == "windows":
            try:
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                metrics["width"] = w
                metrics["height"] = h
                try:
                    dpi = user32.GetDpiForSystem()
                    metrics["dpi_scale"] = round(dpi / 96.0, 2)
                except Exception:
                    pass
            except Exception:
                pass
    return metrics


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        print(f"[Vision] [warn] Image compress failed: {e}")
        return img_bytes, f"image/{source_format.lower()}"


def _capture_screen(
    mode: str = "full_screen",
    region: tuple[int, int, int, int] | dict | None = None,
    hwnd: int | None = None,
) -> tuple[bytes, str]:
    """Capture screen frame with multi-region support ('full_screen', 'active_window', 'window_region')."""
    crop_bbox: dict | None = None  # {"top": y, "left": x, "width": w, "height": h}

    if mode == "active_window":
        ctx = get_active_window_context()
        r = ctx.get("rect", {})
        if r.get("width", 0) > 50 and r.get("height", 0) > 50 and not ctx.get("is_minimized"):
            crop_bbox = {
                "top": max(0, r["y"]),
                "left": max(0, r["x"]),
                "width": r["width"],
                "height": r["height"],
            }
    elif mode == "window_region" and region:
        if isinstance(region, dict):
            crop_bbox = {
                "top": max(0, region.get("y", 0)),
                "left": max(0, region.get("x", 0)),
                "width": region.get("width", 100),
                "height": region.get("height", 100),
            }
        elif isinstance(region, (tuple, list)) and len(region) >= 4:
            crop_bbox = {
                "left": max(0, int(region[0])),
                "top": max(0, int(region[1])),
                "width": int(region[2]),
                "height": int(region[3]),
            }

    # 1. Try mss (fastest)
    if _MSS:
        try:
            with mss.mss() as sct:
                if crop_bbox:
                    shot = sct.grab(crop_bbox)
                else:
                    monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
                    target   = monitors[1] if len(monitors) > 1 else monitors[0]
                    shot     = sct.grab(target)
                png = mss.tools.to_png(shot.rgb, shot.size)
                return _compress(png, "PNG")
        except Exception as e:
            print(f"[Vision] [warn] mss capture failed ({e}), trying PIL.ImageGrab...")

    # 2. Try PIL ImageGrab
    if _PIL:
        try:
            import PIL.ImageGrab
            if crop_bbox:
                box = (
                    crop_bbox["left"],
                    crop_bbox["top"],
                    crop_bbox["left"] + crop_bbox["width"],
                    crop_bbox["top"] + crop_bbox["height"],
                )
                img = PIL.ImageGrab.grab(bbox=box)
            else:
                img = PIL.ImageGrab.grab(all_screens=True)
            img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
            return buf.getvalue(), "image/jpeg"
        except Exception as e:
            print(f"[Vision] [warn] PIL.ImageGrab failed ({e}), trying Qt...")

    # 3. Try Qt screen capture if GUI is active
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QBuffer, QIODevice
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                if crop_bbox:
                    pix = screen.grabWindow(0, crop_bbox["left"], crop_bbox["top"], crop_bbox["width"], crop_bbox["height"])
                else:
                    pix = screen.grabWindow(0)
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.ReadWrite)
                pix.save(buf, "JPEG", _JPEG_Q)
                data = bytes(buf.data())
                if data:
                    return data, "image/jpeg"
    except Exception as e:
        print(f"[Vision] [warn] Qt screen grab failed: {e}")

    raise RuntimeError("No working screen capture method available on this system.")


def _cv2_backend() -> int:
    """Return the best OpenCV camera backend for the current OS."""
    if not _CV2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:

    if not _CV2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:

    backend = _cv2_backend()
    print("[Vision] 🔍 Auto-detecting camera...")
    for idx in range(6):
        if _probe_camera(idx, backend):
            print(f"[Vision] ✅ Camera found at index {idx}")
            _save_config_key("camera_index", idx)
            return idx
        print(f"[Vision] ⚠️  Camera index {idx}: no usable frame")

    print("[Vision] ⚠️  No camera found — defaulting to index 0")
    _save_config_key("camera_index", 0)
    return 0


def _get_camera_index() -> int:
    cfg = _load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


def _capture_camera() -> tuple[bytes, str]:
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")

    index   = _get_camera_index()
    backend = _cv2_backend()
    cap     = cv2.VideoCapture(index, backend)

    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")

    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")

    if _PIL:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q)
        return buf.getvalue(), "image/jpeg"

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
    return buf.tobytes(), "image/jpeg"


def get_active_window_context() -> dict:
    """Instant (1ms) OS foreground window, bounds, and process detection."""
    import platform
    context = {
        "hwnd": 0,
        "foreground_title": "",
        "foreground_process": "",
        "rect": {"x": 0, "y": 0, "width": 0, "height": 0},
        "is_maximized": False,
        "is_minimized": False,
        "visible_windows": [],
    }
    if platform.system() == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd:
                context["hwnd"] = int(fg_hwnd)
                length = user32.GetWindowTextLengthW(fg_hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(fg_hwnd, buff, length + 1)
                    context["foreground_title"] = buff.value.strip()
                
                context["is_minimized"] = bool(user32.IsIconic(fg_hwnd))
                context["is_maximized"] = bool(user32.IsZoomed(fg_hwnd))

                try:
                    from core.computer import windows_native
                    phys_rect = windows_native.get_window_rect_physical(fg_hwnd)
                    if phys_rect and phys_rect.get("width", 0) > 0:
                        context["rect"] = phys_rect
                    else:
                        rect = RECT()
                        if user32.GetWindowRect(fg_hwnd, ctypes.byref(rect)):
                            if rect.left > -10000 and (rect.right - rect.left) > 0:
                                context["rect"] = {
                                    "x": int(rect.left),
                                    "y": int(rect.top),
                                    "width": int(rect.right - rect.left),
                                    "height": int(rect.bottom - rect.top),
                                }
                except Exception:
                    pass
                
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid))
                if pid.value:
                    try:
                        import psutil
                        p = psutil.Process(pid.value)
                        context["foreground_process"] = p.name()
                    except Exception:
                        pass

            win_list = []
            def _enum_win(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    l = user32.GetWindowTextLengthW(hwnd)
                    if l > 0:
                        b = ctypes.create_unicode_buffer(l + 1)
                        user32.GetWindowTextW(hwnd, b, l + 1)
                        t = b.value.strip()
                        if t and t not in ("Program Manager", "Settings", "Default IME", "MSCTFIME UI") and len(win_list) < 6:
                            win_list.append(t)
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(_enum_win), 0)
            context["visible_windows"] = win_list
        except Exception:
            pass
    return context


import time
import threading
from dataclasses import dataclass


def compute_dhash(img_bytes: bytes) -> str:
    """Compute 64-bit difference hash (dHash) from image bytes in < 0.2ms."""
    if not _PIL or not img_bytes:
        return ""
    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("L")
        # Resize to 9x8 (9 columns, 8 rows) to compare adjacent horizontal columns
        img = img.resize((9, 8), PIL.Image.BILINEAR)
        pixels = list(img.getdata())
        diff_bits = []
        for row in range(8):
            row_offset = row * 9
            for col in range(8):
                pixel_left = pixels[row_offset + col]
                pixel_right = pixels[row_offset + col + 1]
                diff_bits.append(1 if pixel_right > pixel_left else 0)
        decimal_val = 0
        for bit in diff_bits:
            decimal_val = (decimal_val << 1) | bit
        return f"{decimal_val:016x}"
    except Exception as e:
        print(f"[Vision] [warn] compute_dhash failed: {e}")
        return ""


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute bitwise Hamming distance between two 16-hex perceptual hashes."""
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 999
    try:
        return bin(int(hash1, 16) ^ int(hash2, 16)).count("1")
    except Exception:
        return 999


@dataclass
class PerceptionRecord:
    screen_hash: str
    timestamp: float
    source: str
    app: str
    window_title: str
    rect: dict
    state_summary: str
    query_text: str = ""


class PerceptionCache:
    """Thread-safe perception memory cache with dHash freshness detection."""

    def __init__(self, ttl_seconds: float = 15.0) -> None:
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._last_record: PerceptionRecord | None = None

    def get(
        self,
        img_bytes: bytes,
        app: str,
        window_title: str,
        query_text: str = "",
        max_hamming: int = 2,
    ) -> PerceptionRecord | None:
        if not img_bytes:
            return None
        new_hash = compute_dhash(img_bytes)
        if not new_hash:
            return None

        with self._lock:
            if not self._last_record:
                return None
            now = time.time()
            # 1. TTL check
            if now - self._last_record.timestamp > self._ttl:
                return None
            # 2. Window / App context check
            if app and self._last_record.app and app.lower() != self._last_record.app.lower():
                return None
            if window_title and self._last_record.window_title and window_title.lower() != self._last_record.window_title.lower():
                return None
            # 3. Hamming distance check
            dist = hamming_distance(new_hash, self._last_record.screen_hash)
            if dist <= max_hamming:
                # If query is identical or generic, return cached summary
                if not query_text or not self._last_record.query_text or query_text.lower().strip() == self._last_record.query_text.lower().strip():
                    return self._last_record
                return None
            return None

    def set(
        self,
        img_bytes: bytes,
        source: str,
        app: str,
        window_title: str,
        rect: dict,
        state_summary: str,
        query_text: str = "",
    ) -> None:
        screen_hash = compute_dhash(img_bytes) if img_bytes else ""
        rec = PerceptionRecord(
            screen_hash=screen_hash,
            timestamp=time.time(),
            source=source,
            app=app,
            window_title=window_title,
            rect=rect,
            state_summary=state_summary,
            query_text=query_text,
        )
        with self._lock:
            self._last_record = rec

    def invalidate(self) -> None:
        with self._lock:
            self._last_record = None

    def get_latest(self) -> PerceptionRecord | None:
        with self._lock:
            return self._last_record


_perception_cache = PerceptionCache(ttl_seconds=15.0)


def analyze_visual(
    img_bytes: bytes,
    mime_type: str,
    query_text: str = "",
    source_type: str = "screen",
    crop_mode: str = "auto",
) -> str:
    """Analyze a captured screen or camera frame using fast OS telemetry + one-shot Gemini vision.

    Includes 0ms perceptual hash caching to prevent duplicate API requests when screen state is unchanged.
    """
    os_ctx = get_active_window_context() if source_type == "screen" else {}
    fg_info = ""
    rect_str = ""
    if os_ctx.get("foreground_title"):
        r = os_ctx.get("rect", {})
        if r.get("width", 0) > 0:
            rect_str = f" [Bounds: {r['width']}x{r['height']} at ({r['x']},{r['y']})]"
        fg_info = f"[OS Foreground: {os_ctx['foreground_title']} ({os_ctx.get('foreground_process', '')}){rect_str}]"

    if not img_bytes:
        if fg_info:
            return f"{fg_info} Visible Windows: {', '.join(os_ctx.get('visible_windows', []))}"
        return f"No visual frame captured from {source_type}."

    # Phase 2: Check Perception Cache for 0ms hit
    if source_type == "screen":
        cached = _perception_cache.get(
            img_bytes=img_bytes,
            app=os_ctx.get("foreground_process", ""),
            window_title=os_ctx.get("foreground_title", ""),
            query_text=query_text,
        )
        if cached:
            print("[Vision] [cache] Perception cache hit (0ms) - Screen state unchanged")
            return f"{fg_info} {cached.state_summary} [Cache: 0ms]"

    import core.gemini as _gem
    from google.genai import types as _gtypes

    try:
        part = _gtypes.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        prompt = (
            f"[VISUAL OBSERVATION OF {source_type.upper()}]\n"
            f"OS Active Window Ground Truth: {fg_info}\n"
            f"User Goal / Question: {query_text or 'Describe the active application, window title, and visible content.'}\n\n"
            "Analyze the screenshot and report:\n"
            "1. Active foreground window and application name.\n"
            "2. Key visible elements, open files, search queries or results, chats/contacts, code or error messages.\n"
            "3. Answer the user's specific question factually and concisely based on what is visible on the screen/camera."
        )
        ans = _gem.text(
            contents=[part, prompt],
            tier=_gem.FAST,
            allow_live=False,
            timeout_ms=5000,
            default=""
        )
        if ans and ans.strip():
            obs = ans.strip()
            # Save into perception cache
            if source_type == "screen":
                _perception_cache.set(
                    img_bytes=img_bytes,
                    source="l2_vision",
                    app=os_ctx.get("foreground_process", ""),
                    window_title=os_ctx.get("foreground_title", ""),
                    rect=os_ctx.get("rect", {}),
                    state_summary=obs,
                    query_text=query_text,
                )
            return f"{fg_info} {obs}"
    except Exception as e:
        print(f"[Vision] [warn] Visual model error ({e}) — falling back to OS ground truth")

    # Fallback to instantaneous OS window ground truth if model timed out or had high demand
    if fg_info:
        return (
            f"{fg_info} Visible windows: {', '.join(os_ctx.get('visible_windows', []))}. "
            f"(Visual image captured; active foreground confirmed as {os_ctx['foreground_title']})"
        )
    return "Screen visual captured, but details could not be parsed."


def extract_screen_text(
    img_bytes: bytes | None = None,
    region: tuple[int, int, int, int] | dict | None = None,
) -> str:
    """Extract all visible screen text locally on CPU in < 80ms using RapidOCR (0 MB VRAM)."""
    try:
        from core.computer.ocr_engine import ocr_engine
        if not ocr_engine.is_available:
            return ""
        reg_tuple = None
        if isinstance(region, dict):
            reg_tuple = (region.get("x", 0), region.get("y", 0), region.get("width", 0), region.get("height", 0))
        elif isinstance(region, (tuple, list)) and len(region) >= 4:
            reg_tuple = tuple(int(x) for x in region[:4])
        return ocr_engine.extract_full_text(img=img_bytes, region=reg_tuple)
    except Exception as e:
        print(f"[Vision] Local OCR extraction error: {e}")
        return ""


def get_structured_perception(
    img_bytes: bytes = b"",
    query_text: str = "",
    confidence: float = 1.0,
    source: str = "l0_os",
    obs_text: str = "",
) -> dict:
    """Standardized structured perception dictionary conforming to Phase 3 architecture."""
    ctx = get_active_window_context()
    dhash_val = compute_dhash(img_bytes) if img_bytes else ""
    return {
        "active_app": ctx.get("foreground_process", ""),
        "window_title": ctx.get("foreground_title", ""),
        "screen_state": "focused" if not ctx.get("is_minimized") else "minimized",
        "rect": ctx.get("rect", {}),
        "is_maximized": ctx.get("is_maximized", False),
        "screen_hash": dhash_val,
        "confidence": round(confidence, 2),
        "source": source,
        "timestamp": time.time(),
        "details": obs_text or (f"Active window: {ctx.get('foreground_title', '')}" if ctx.get("foreground_title") else "Desktop"),
        "visible_windows": ctx.get("visible_windows", []),
    }


def screen_processor_handler(parameters: dict, player: Any = None, **kwargs) -> str:
    """Action handler for screen and webcam observation."""
    angle = str(parameters.get("angle", "screen")).lower().strip()
    user_text = str(parameters.get("text", "What is currently visible on the screen?")).strip()
    
    stall = "screen"
    img_b, mime_t = None, "image/jpeg"
    
    if angle == "camera":
        try:
            img_b, mime_t = _capture_camera()
            stall = "camera"
            if player and hasattr(player, "start_camera_stream"):
                player.start_camera_stream()
        except Exception as cam_err:
            print(f"[Vision] ⚠️ Camera unavailable ({cam_err}) — falling back to screen capture")
            img_b, mime_t = _capture_screen()
            stall = "screen"
    else:
        img_b, mime_t = _capture_screen()
        stall = "screen"

    try:
        v_obs = analyze_visual(img_b, mime_t, user_text, stall)
        if player and hasattr(player, "show_content"):
            player.show_content(f"VISION ({stall.upper()})", v_obs)
        return f"[Visual observation from {stall}]: {v_obs}"
    except Exception as e:
        return f"I could not inspect the screen right now: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "screen_process",
    "description": (
        "Captures the screen or webcam image and analyzes it to return a factual, detailed visual observation. "
        "MUST be called when user asks what is on screen, what you see, look at camera, inspect active window, check search results or contacts on screen, etc. "
        "Returns a precise description of the active application, window title, visible text, contacts/chats, code, buttons, or error messages."
    ),
    "risk": "read_only",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "angle": {
                "type": "STRING",
                "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"
            },
            "text": {
                "type": "STRING",
                "description": "The specific question or instruction about the screen/camera state (e.g. 'Is WhatsApp open and is Inferno in the search results?')."
            }
        },
        "required": ["text"]
    },
    "handler": screen_processor_handler,
}
