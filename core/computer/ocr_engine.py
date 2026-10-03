"""
core/computer/ocr_engine.py - Lightweight CPU Multilingual OCR Engine for ZEZO OS
Powered by RapidOCR (ONNX Runtime) with 0 MB VRAM overhead.
Supports English, Urdu, Arabic, numeric spatial text localization in < 80ms.
Creator: Hamza Bukhari
"""
from __future__ import annotations

import difflib
import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

_RAPIDOCR_AVAILABLE = False
try:
    from rapidocr_onnxruntime import RapidOCR
    _RAPIDOCR_AVAILABLE = True
except ImportError:
    pass


# ── Urdu & Arabic Unicode Normalization ───────────────────────────────────────
_TASHKEEL_RE = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\uFEFF]")

_CHAR_REPLACEMENTS = {
    # Alef variants -> bare Alef (ا)
    "\u0622": "\u0627", "\u0623": "\u0627", "\u0625": "\u0627",
    "\u0671": "\u0627", "\u0672": "\u0627", "\u0673": "\u0627", "\u0675": "\u0627",
    # Yeh variants -> Urdu Yeh (ی)
    "\u0649": "\u06CC", "\u064A": "\u06CC", "\u06CD": "\u06CC",
    "\u06CE": "\u06CC", "\u06D0": "\u06CC", "\u06D1": "\u06CC",
    # Kaf variants -> Urdu Keheh (ک)
    "\u0643": "\u06A9", "\u06AA": "\u06A9",
    # Heh variants -> Urdu Choti Heh / Goal Heh (ہ)
    "\u0629": "\u06C1", "\u0647": "\u06C1", "\u06C2": "\u06C1", "\u06C3": "\u06C1", "\u06D5": "\u06C1",
    # Waw with Hamza -> Waw (و)
    "\u0624": "\u0648",
    # Yeh with Hamza -> Urdu Yeh (ی)
    "\u0626": "\u06CC",
}


def normalize_urdu(text: str) -> str:
    """
    Normalize Urdu, Arabic, and multilingual text for robust matching.
    - Strips tashkeel / diacritics
    - Normalizes character variants (yeh, kaf, heh, alef)
    - Removes zero-width joiners and extraneous punctuation
    """
    if not text:
        return ""
    # 1. Strip Tashkeel & Zero-Width Chars
    s = _TASHKEEL_RE.sub("", text)
    s = _ZERO_WIDTH_RE.sub("", s)

    # 2. Character Variant Normalization
    for src, target in _CHAR_REPLACEMENTS.items():
        s = s.replace(src, target)

    # 3. Clean spaces & lowercase
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


_SIDEBAR_PROPERTY_KEYWORDS = {
    "w", "h", "width", "height", "x", "y", "fill", "stroke", "opacity",
    "corner", "radius", "rotation", "align", "constraints", "export",
    "layer", "auto layout", "frame", "clip content", "padding", "gap"
}


class OCREngine:
    """CPU-bound lightweight ONNX OCR Engine for instant spatial UI text grounding."""

    def __init__(self):
        self._engine: Optional[Any] = None
        self._is_ready = False

    def _ensure_engine(self) -> bool:
        """Lazy load RapidOCR engine on first request."""
        if self._engine is not None:
            return True
        if not _RAPIDOCR_AVAILABLE:
            return False
        try:
            t0 = time.perf_counter()
            self._engine = RapidOCR()
            self._is_ready = True
            print(f"[OCREngine] Initialized RapidOCR (CPU ONNX) in {round((time.perf_counter() - t0) * 1000, 1)}ms (0 MB VRAM)")
            return True
        except Exception as e:
            print(f"[OCREngine] Failed to initialize RapidOCR: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return _RAPIDOCR_AVAILABLE

    def extract_text_boxes(
        self,
        img: Union[bytes, np.ndarray, Image.Image],
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract all text lines and bounding boxes from an image in < 80ms.
        Returns: list of dicts with text, confidence, center_x, center_y, rect, and box.
        """
        if not self._ensure_engine():
            return []

        t0 = time.perf_counter()
        np_img = self._to_numpy_image(img)
        if np_img is None:
            return []

        # Crop if region specified: (left, top, width, height)
        offset_x, offset_y = 0, 0
        if region and len(region) >= 4:
            rx, ry, rw, rh = int(region[0]), int(region[1]), int(region[2]), int(region[3])
            h, w = np_img.shape[:2]
            rx = max(0, min(rx, w - 1))
            ry = max(0, min(ry, h - 1))
            rw = max(1, min(rw, w - rx))
            rh = max(1, min(rh, h - ry))
            np_img = np_img[ry : ry + rh, rx : rx + rw]
            offset_x, offset_y = rx, ry

        try:
            result, elapse = self._engine(np_img)
            if not result:
                return []

            boxes = []
            for item in result:
                dt_boxes, rec_res, score = item[0], item[1], float(item[2])
                pts = np.array(dt_boxes, dtype=np.int32)
                min_x = int(np.min(pts[:, 0])) + offset_x
                max_x = int(np.max(pts[:, 0])) + offset_x
                min_y = int(np.min(pts[:, 1])) + offset_y
                max_y = int(np.max(pts[:, 1])) + offset_y

                cx = (min_x + max_x) // 2
                cy = (min_y + max_y) // 2
                width = max_x - min_x
                height = max_y - min_y

                boxes.append({
                    "text": str(rec_res).strip(),
                    "confidence": round(score, 3),
                    "center_x": cx,
                    "center_y": cy,
                    "rect": {
                        "x": min_x,
                        "y": min_y,
                        "width": width,
                        "height": height,
                    },
                    "box": pts.tolist(),
                })

            return boxes
        except Exception as e:
            print(f"[OCREngine] OCR extraction error: {e}")
            return []

    def find_text_coordinates(
        self,
        query: str,
        img: Optional[Union[bytes, np.ndarray, Image.Image]] = None,
        fuzzy_threshold: float = 0.75,
        region: Optional[Tuple[int, int, int, int]] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Locate target text on screen using normalized fuzzy matching with ROI auto-cropping.
        Returns: {name, center_x, center_y, rect, confidence, source='l1.5_ocr', latency_ms}
        """
        if img is None:
            img = kwargs.get("image") or kwargs.get("img_bytes")
        if not query:
            return None

        t0 = time.perf_counter()
        if img is None:
            try:
                from core.computer.screen_capture import capture_screen_fast
                img = capture_screen_fast()
            except Exception as e:
                print(f"[OCREngine] Screenshot capture failed: {e}")
                return None

        norm_query = normalize_urdu(query)

        # ── ROI Auto-Cropping Optimization ──────────────────────────────────
        # If no explicit region given, prioritize the active window or right sidebar.
        active_region = region
        used_roi = False
        if active_region is None:
            try:
                from core.computer.windows_native import windows_native
                act_rect = windows_native.get_active_window_rect()
                if act_rect and act_rect.get("width", 0) > 100 and act_rect.get("height", 0) > 100:
                    # Check if query targets a right-sidebar property in design/editor apps
                    if norm_query in _SIDEBAR_PROPERTY_KEYWORDS or any(k in norm_query for k in ("width", "height", "fill", "stroke", "opacity")):
                        sidebar_w = max(200, int(act_rect["width"] * 0.32))
                        sidebar_x = act_rect["x"] + act_rect["width"] - sidebar_w
                        active_region = (sidebar_x, act_rect["y"], sidebar_w, act_rect["height"])
                        used_roi = True
                    else:
                        active_region = (act_rect["x"], act_rect["y"], act_rect["width"], act_rect["height"])
                        used_roi = True
            except Exception:
                active_region = None

        boxes = self.extract_text_boxes(img, region=active_region)
        # Fallback to full screen if ROI returned 0 text
        if not boxes and used_roi:
            boxes = self.extract_text_boxes(img, region=None)
            used_roi = False

        if not boxes:
            return None

        def _match_boxes(cand_boxes: List[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], float]]:
            b_match = None
            b_score = 0.0
            for b in cand_boxes:
                raw_text = b.get("text", "")
                norm_detected = normalize_urdu(raw_text)
                if not norm_detected:
                    continue

                # Exact match
                if norm_query == norm_detected:
                    return b, 1.0

                # Substring match
                if norm_query in norm_detected:
                    score = 0.85 + 0.15 * (len(norm_query) / max(len(norm_detected), 1))
                    if score > b_score:
                        b_score = score
                        b_match = b
                    continue

                # Word token match
                query_tokens = norm_query.split()
                detected_tokens = norm_detected.split()
                if query_tokens and all(any(qt in dt for dt in detected_tokens) for qt in query_tokens):
                    score = 0.80
                    if score > b_score:
                        b_score = score
                        b_match = b
                    continue

                # Fuzzy similarity match
                sim = difflib.SequenceMatcher(None, norm_query, norm_detected).ratio()
                if sim >= fuzzy_threshold and sim > b_score:
                    b_score = sim
                    b_match = b

            if b_match and b_score >= fuzzy_threshold:
                return b_match, b_score
            return None

        match_res = _match_boxes(boxes)

        # If ROI match failed, do a second-pass full-screen scan
        if not match_res and used_roi:
            full_boxes = self.extract_text_boxes(img, region=None)
            if full_boxes:
                boxes = full_boxes
                match_res = _match_boxes(full_boxes)

        if match_res:
            best_match, best_score = match_res
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "name": best_match["text"],
                "center_x": best_match["center_x"],
                "center_y": best_match["center_y"],
                "rect": best_match["rect"],
                "confidence": best_match["confidence"],
                "source": "l1.5_ocr",
                "similarity": round(best_score, 3),
                "latency_ms": latency,
            }

        # Step 2b: Groq L1.5 Semantic / Spatial Reasoning on OCR text bounding boxes (~40ms)
        try:
            from memory.config_manager import get_groq_api_key
            if get_groq_api_key() and len(boxes) > 0:
                groq_match = self._groq_spatial_match(query, boxes)
                if groq_match:
                    latency = round((time.perf_counter() - t0) * 1000, 1)
                    return {
                        "name": groq_match.get("text", query),
                        "center_x": groq_match["center_x"],
                        "center_y": groq_match["center_y"],
                        "rect": groq_match.get("rect", {}),
                        "confidence": 0.95,
                        "source": "l1.5_groq_ocr",
                        "similarity": 1.0,
                        "latency_ms": latency,
                    }
        except Exception as e:
            print(f"[OCREngine] Groq spatial reasoning failed: {e}")

        return None

    def _groq_spatial_match(self, query: str, boxes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Query Groq LPU to identify target UI element from spatial OCR boxes in ~40ms."""
        from core.llm_client import call_groq_json
        
        # Take up to 60 non-empty text boxes
        valid_boxes = [b for b in boxes if b.get("text") and len(b["text"].strip()) > 0][:60]
        if not valid_boxes:
            return None

        compact_list = [
            {
                "id": i,
                "text": b["text"],
                "center": [b["center_x"], b["center_y"]],
                "rect": [b["rect"]["x"], b["rect"]["y"], b["rect"]["width"], b["rect"]["height"]],
            }
            for i, b in enumerate(valid_boxes)
        ]

        system = (
            "You are a high-speed UI spatial grounding parser. "
            "Given a user query and a list of OCR detected bounding boxes on screen, "
            "identify the box ID that best matches what the user is asking to find or click. "
            "Return JSON ONLY: {\"target_id\": <integer id or null>}"
        )
        prompt = f"User Request: '{query}'\n\nDetected Screen Elements:\n{json.dumps(compact_list, ensure_ascii=False)}"

        res = call_groq_json(prompt, system=system, timeout=10)
        if isinstance(res, dict) and res.get("target_id") is not None:
            try:
                target_id = int(res["target_id"])
                if 0 <= target_id < len(valid_boxes):
                    return valid_boxes[target_id]
            except (ValueError, TypeError):
                pass
        return None


    def extract_full_text(
        self,
        img: Optional[Union[bytes, np.ndarray, Image.Image]] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        **kwargs,
    ) -> str:
        """Extract and format all visible screen text ordered from top to bottom."""
        if img is None:
            img = kwargs.get("image") or kwargs.get("img_bytes")
        if img is None:
            try:
                import pyautogui
                img = pyautogui.screenshot()
            except Exception:
                return ""

        boxes = self.extract_text_boxes(img, region=region)
        if not boxes:
            return ""

        # Sort top-to-bottom, left-to-right
        boxes.sort(key=lambda b: (b["center_y"] // 15, b["center_x"]))
        lines = [b["text"] for b in boxes if b.get("text")]
        return "\n".join(lines)

    def _to_numpy_image(self, img: Union[bytes, np.ndarray, Image.Image]) -> Optional[np.ndarray]:
        """Convert various image formats to BGR numpy array."""
        try:
            if isinstance(img, np.ndarray):
                return img
            if isinstance(img, bytes):
                pil_img = Image.open(io.BytesIO(img)).convert("RGB")
                return np.array(pil_img)[:, :, ::-1]  # RGB to BGR
            if isinstance(img, Image.Image):
                rgb = img.convert("RGB")
                return np.array(rgb)[:, :, ::-1]
        except Exception as e:
            print(f"[OCREngine] Image conversion error: {e}")
        return None


# Global singleton instance
ocr_engine = OCREngine()
