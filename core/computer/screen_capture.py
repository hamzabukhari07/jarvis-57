"""
core/computer/screen_capture.py - High-Speed Zero-VRAM Screen Capture Engine for ZEZO OS
Utilizes mss (C/DirectX BitBlt) for sub-10ms desktop frame capture with seamless fallback to Pillow/pyautogui.
Creator: Hamza Bukhari
"""
from __future__ import annotations

import io
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image

_MSS_AVAILABLE = False
try:
    import mss
    _MSS_AVAILABLE = True
except ImportError:
    pass


def capture_screen_fast(
    region: Optional[Tuple[int, int, int, int]] = None,
    return_type: str = "pil",
) -> Union[Image.Image, np.ndarray, None]:
    """
    Capture a screenshot of the entire desktop or a specific region in < 10ms.
    
    Args:
        region: Optional (left, top, width, height) tuple
        return_type: "pil" (PIL.Image) or "numpy" (RGB np.ndarray)
        
    Returns:
        PIL.Image or RGB np.ndarray, or None if capture fails.
    """
    if _MSS_AVAILABLE:
        try:
            with mss.mss() as sct:
                if region and len(region) >= 4:
                    monitor = {
                        "left": int(region[0]),
                        "top": int(region[1]),
                        "width": int(region[2]),
                        "height": int(region[3]),
                    }
                else:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]

                sct_img = sct.grab(monitor)
                # sct_img is BGRA format -> convert to RGB NumPy array
                np_bgra = np.array(sct_img)
                np_rgb = np_bgra[:, :, [2, 1, 0]]  # Fast slice BGRA -> RGB

                if return_type == "numpy":
                    return np_rgb
                return Image.fromarray(np_rgb)
        except Exception as e:
            print(f"[ScreenCapture] mss capture fallback: {e}")

    # Fallback to pyautogui / PIL ImageGrab
    try:
        import pyautogui
        img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
        if return_type == "numpy":
            return np.array(img)
        return img
    except Exception as e:
        print(f"[ScreenCapture] pyautogui capture failed: {e}")
        return None


def capture_screen_bytes(
    region: Optional[Tuple[int, int, int, int]] = None,
    format: str = "PNG",
) -> Optional[bytes]:
    """Capture screenshot directly into memory bytes for multimodal LLM or disk storage."""
    img = capture_screen_fast(region=region, return_type="pil")
    if img is None:
        return None
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()
