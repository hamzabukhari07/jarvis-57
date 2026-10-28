"""
core/design_extractor.py — Deterministic Design System & Token Extractor

Extracts authentic design tokens (colors, typography, spacing, radii, components,
keyframes, and CSS custom properties) from raw HTML/CSS templates into a structured
DesignTokens data model.

Known limitations:
- Media-query selector context is flattened during parsing (inner rules are merged with their inner selectors).
- CSS @import is not followed.
- JS-injected styles are not seen.
- !important is ignored in value resolution.
- Master template drops <script> tags in the final reduction stage if size budget requires it - interactive JS is not guaranteed if the source is huge.
- Cache version v2 must be bumped whenever extractor logic changes; otherwise stale cache is served.
"""

from __future__ import annotations

import colorsys
import math
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
except ImportError:
    BeautifulSoup = None

from core.design_tokens import ColorTokens, ComponentToken, DesignTokens, TypeToken

__all__ = [
    "DEFAULT_SVG_PLACEHOLDER",
    "strip_base64_images",
    "strip_base64_bloat",
    "extract_keyframes",
    "extract_design_tokens",
    "generate_design_md",
    "extract_design_system_from_html",
]

# NOTE: The hardcoded zinc colors in DEFAULT_SVG_PLACEHOLDER (#18181b, #27272a, #71717a)
# are intentional placeholder asset styling colors, NOT extracted brand tokens.
DEFAULT_SVG_PLACEHOLDER = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 400'%3E"
    "%3Crect width='100%25' height='100%25' fill='%2318181b'/%3E"
    "%3Cpath d='M250 180l50-50 100 100H200z' fill='%2327272a'/%3E"
    "%3Ccircle cx='340' cy='150' r='20' fill='%2327272a'/%3E"
    "%3Ctext x='50%25' y='75%25' dominant-baseline='middle' text-anchor='middle' "
    "fill='%2371717a' font-family='sans-serif' font-size='14'%3EAsset Placeholder%3C/text%3E"
    "%3C/svg%3E"
)

_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
_RGB_RE = re.compile(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d\.]+)?\s*\)", re.IGNORECASE)
_HSL_RE = re.compile(r"hsla?\s*\(\s*(-?[\d\.]+)\s*,\s*([\d\.]+)%\s*,\s*([\d\.]+)%(?:\s*,\s*[\d\.]+)?\s*\)", re.IGNORECASE)
_OKLCH_RE = re.compile(
    r"oklch\s*\(\s*([\d\.]+)(%?)\s+([\d\.]+)(%?)\s+(none|[\d\.]+(?:deg|rad|grad|turn)?)(?:\s*/\s*[\d\.]+%?)?\s*\)",
    re.IGNORECASE,
)
_VAR_DEF_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;}{]+);?")
_GOOGLE_FONTS_RE = re.compile(r"fonts\.googleapis\.com/css2\?family=([^&\"'\s]+)")
_BASE64_IMAGE_RE = re.compile(r"data:image/[a-zA-Z0-9\+\-\.]+;base64,[A-Za-z0-9+/=]+")


# ============================================================================
# BASE64 STRIPPING & PREPROCESSING
# ============================================================================

def _collapse_base64_whitespace(html_content: str) -> str:
    r"""Finds each ;base64, and consumes [A-Za-z0-9+/=\s\\]+ to collapse internal whitespace."""
    if not html_content or ";base64," not in html_content:
        return html_content

    def _sub(m: re.Match) -> str:
        data = re.sub(r"[\s\\]+", "", m.group(1))
        return f";base64,{data}"

    return re.sub(r";base64,([A-Za-z0-9+/=\s\\]+)", _sub, html_content)


def strip_base64_images(html_content: str, placeholder: Optional[str] = None) -> str:
    """
    Strips megabytes of embedded base64 image data, font data, compiled script data,
    and framework hydration scripts from HTML templates, replacing images with a
    lightweight clean SVG placeholder asset.
    """
    if not html_content:
        return html_content
    sub_val = placeholder or DEFAULT_SVG_PLACEHOLDER
    c = html_content

    # 1. Strip script tags with data: src
    c = re.sub(r'<script\b[^>]*src=["\']data:[^"\']+["\'][^>]*>\s*</script>', '', c, flags=re.IGNORECASE)

    # 2. Strip Next.js / framework hydration scripts
    if "__next_f" in c:
        c = re.sub(r'<script\b[^>]*>.*?__next_f.*?</script>', '', c, flags=re.DOTALL | re.IGNORECASE)
    if "__NEXT_DATA__" in c:
        c = re.sub(r'<script\b[^>]*id=["\']__NEXT_DATA__["\'][^>]*>.*?</script>', '', c, flags=re.DOTALL | re.IGNORECASE)

    # 3. Strip preload links with data URIs
    c = re.sub(r'<link\b[^>]*href=["\']data:[^"\']+["\'][^>]*>', '', c, flags=re.IGNORECASE)

    # 4. Strip base64 fonts in @font-face rules
    c = re.sub(r'@font-face\s*\{[^{}]*(?:;base64,|data:(?:font|application))[^{}]*\}', '', c, flags=re.IGNORECASE)

    # 5. Strip base64 images -> SVG placeholder
    if "data:image/" in c:
        c = _collapse_base64_whitespace(c)
        c = _BASE64_IMAGE_RE.sub(sub_val, c)

    # 6. Strip any residual data URIs or base64 url calls
    c = re.sub(r'url\(\s*["\']?(?:data:[^"\'\)]+|;base64,[A-Za-z0-9+/=]+)["\']?\s*\)', 'none', c, flags=re.IGNORECASE)
    c = re.sub(r'data:(?:text/javascript|text/css|application|font|audio|video)/[^"\'\)\s>,]+', '', c, flags=re.IGNORECASE)

    # 7. Strip empty style/script tags
    c = re.sub(r'<style[^>]*>\s*</style>', '', c)
    c = re.sub(r'<script[^>]*>\s*</script>', '', c)

    return c


strip_base64_bloat = strip_base64_images


# ============================================================================
# COLOR MATH & NORMALIZATION (WCAG 2.x & OKLCH)
# ============================================================================

def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        h = h[:6]
    elif len(h) != 6:
        return 128, 128, 128
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return 128, 128, 128


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _oklch_to_hex(l: float, c: float, h_deg: float) -> Optional[str]:
    try:
        h_deg = h_deg % 360
        h_rad = math.radians(h_deg)
        a = c * math.cos(h_rad)
        b = c * math.sin(h_rad)
        l_ = l + 0.3963377774 * a + 0.2158037573 * b
        m_ = l - 0.1055613458 * a - 0.0638541728 * b
        s_ = l - 0.0894841775 * a - 1.2914855480 * b
        l_lin, m_lin, s_lin = l_ ** 3, m_ ** 3, s_ ** 3
        r_lin = +4.0767416621 * l_lin - 3.3077115913 * m_lin + 0.2309699292 * s_lin
        g_lin = -1.2684380046 * l_lin + 2.6097574011 * m_lin - 0.3413193965 * s_lin
        b_lin = -0.0041960863 * l_lin - 0.7034186147 * m_lin + 1.7076147010 * s_lin

        def gamma(x: float) -> float:
            return 12.92 * x if x <= 0.0031308 else 1.055 * (max(0.0, x) ** (1.0 / 2.4)) - 0.055

        r = int(min(255, max(0, round(gamma(r_lin) * 255))))
        g = int(min(255, max(0, round(gamma(g_lin) * 255))))
        b = int(min(255, max(0, round(gamma(b_lin) * 255))))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return None


def _hsl_to_hex(h: float, s: float, l: float) -> Optional[str]:
    try:
        h = h % 360
        s_norm = s / 100.0
        l_norm = l / 100.0
        c = (1.0 - abs(2.0 * l_norm - 1.0)) * s_norm
        x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
        m = l_norm - c / 2.0
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return f"#{int((r + m) * 255):02x}{int((g + m) * 255):02x}{int((b + m) * 255):02x}"
    except Exception:
        return None


def _normalize_color_to_hex(val: str) -> Optional[str]:
    val = (val or "").strip().lower()
    if not val:
        return None

    named = {
        "black": "#000000",
        "white": "#ffffff",
        "transparent": None,
        "inherit": None,
        "currentcolor": None,
        "none": None,
    }
    if val in named:
        return named[val]

    # OKLCH
    m_oklch = _OKLCH_RE.search(val)
    if m_oklch:
        l_val = float(m_oklch.group(1))
        if m_oklch.group(2) == "%":
            l_val /= 100.0
        c_val = float(m_oklch.group(3))
        if m_oklch.group(4) == "%":
            c_val = (c_val / 100.0) * 0.4
        hue_raw = m_oklch.group(5).lower()
        if hue_raw == "none":
            h_val = 0.0
        elif hue_raw.endswith("deg"):
            h_val = float(hue_raw[:-3])
        elif hue_raw.endswith("rad"):
            h_val = math.degrees(float(hue_raw[:-3]))
        elif hue_raw.endswith("grad"):
            h_val = float(hue_raw[:-4]) * 0.9
        elif hue_raw.endswith("turn"):
            h_val = float(hue_raw[:-4]) * 360.0
        else:
            h_val = float(hue_raw)
        res = _oklch_to_hex(l_val, c_val, h_val)
        if res:
            return res

    # HSL
    m_hsl = _HSL_RE.search(val)
    if m_hsl:
        res = _hsl_to_hex(float(m_hsl.group(1)), float(m_hsl.group(2)), float(m_hsl.group(3)))
        if res:
            return res

    # HEX
    m_hex = _HEX_RE.search(val)
    if m_hex:
        raw = m_hex.group(0)
        r, g, b = _hex_to_rgb(raw)
        return _rgb_to_hex(r, g, b)

    # RGB
    m_rgb = _RGB_RE.search(val)
    if m_rgb:
        r, g, b = int(m_rgb.group(1)), int(m_rgb.group(2)), int(m_rgb.group(3))
        return _rgb_to_hex(r, g, b)

    return None


def _relative_luminance(hex_str: str) -> float:
    """WCAG 2.x linearized relative luminance."""
    try:
        r, g, b = _hex_to_rgb(hex_str)

        def _lin(c: int) -> float:
            c_norm = c / 255.0
            return c_norm / 12.92 if c_norm <= 0.04045 else ((c_norm + 0.055) / 1.055) ** 2.4

        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    except Exception:
        return 0.5


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.x contrast ratio (1.0 to 21.0)."""
    try:
        l1 = _relative_luminance(hex_a)
        l2 = _relative_luminance(hex_b)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)
    except Exception:
        return 1.0


def _best_foreground(bg_hex: str) -> str:
    """Picks either #000000 or #ffffff to maximize WCAG contrast against bg_hex."""
    cr_black = _contrast_ratio(bg_hex, "#000000")
    cr_white = _contrast_ratio(bg_hex, "#ffffff")
    return "#000000" if cr_black >= cr_white else "#ffffff"


def _saturation(hex_str: str) -> float:
    try:
        r, g, b = _hex_to_rgb(hex_str)
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        if max_c == 0:
            return 0.0
        return (max_c - min_c) / max_c
    except Exception:
        return 0.0


def _hue_degrees(hex_str: str) -> float:
    try:
        r, g, b = _hex_to_rgb(hex_str)
        h, _, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return h * 360.0
    except Exception:
        return 0.0


def _euclidean_rgb_distance(c1: str, c2: str) -> float:
    try:
        r1, g1, b1 = _hex_to_rgb(c1)
        r2, g2, b2 = _hex_to_rgb(c2)
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
    except Exception:
        return 0.0


def _adjust_color(hex_str: str, factor: float) -> str:
    try:
        r, g, b = _hex_to_rgb(hex_str)
        if factor > 0:
            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)
        else:
            r = int(r * (1.0 + factor))
            g = int(g * (1.0 + factor))
            b = int(b * (1.0 + factor))
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _rgb_to_hex(r, g, b)
    except Exception:
        return hex_str


# ============================================================================
# CSS PARSING, KEYFRAMES & VARIABLE RESOLUTION
# ============================================================================

def extract_keyframes(raw_css: str) -> dict[str, str]:
    """
    Extracts all @keyframes definitions from CSS into a name -> body mapping.
    Correctly balances braces to capture multi-step keyframe blocks while ignoring
    braces inside string literals.
    """
    if not raw_css or "@" not in raw_css:
        return {}
    clean_css = re.sub(r"/\*[\s\S]*?\*/", "", raw_css)
    keyframes: dict[str, str] = {}
    pattern = re.compile(r"@(?:-(?:webkit|moz|o|ms)-)?keyframes\s+([a-zA-Z0-9_-]+)\s*\{", re.IGNORECASE)
    for m in pattern.finditer(clean_css):
        name = m.group(1).strip()
        open_brace_idx = m.end() - 1
        depth = 0
        end_brace_idx = -1
        in_single = False
        in_double = False
        escape_next = False
        for i in range(open_brace_idx, len(clean_css)):
            ch = clean_css[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == "'" and not in_double:
                in_single = not in_single
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                continue
            if not in_single and not in_double:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_brace_idx = i
                        break
        if end_brace_idx != -1:
            body = clean_css[open_brace_idx + 1:end_brace_idx].strip()
            keyframes[name] = body
    return keyframes


def _parse_css_blocks(css: str) -> list[tuple[str, str]]:
    """
    Depth-tracking parser returning (prelude, body) pairs at depth 0.
    Handles string literals properly so braces inside quotes are not treated as blocks.
    """
    blocks: list[tuple[str, str]] = []
    if not css:
        return blocks

    n = len(css)
    i = 0
    start = 0
    in_single = False
    in_double = False

    while i < n:
        ch = css[i]
        if ch == "\\" and (in_single or in_double):
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue

        if not in_single and not in_double:
            if ch == ";":
                start = i + 1
            elif ch == "{":
                prelude = css[start:i].strip()
                body_start = i + 1
                depth = 1
                j = body_start
                b_single = False
                b_double = False
                while j < n and depth > 0:
                    c = css[j]
                    if c == "\\" and (b_single or b_double):
                        j += 2
                        continue
                    if c == "'" and not b_double:
                        b_single = not b_single
                    elif c == '"' and not b_single:
                        b_double = not b_double
                    elif not b_single and not b_double:
                        if c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                    j += 1
                body = css[body_start : j - 1]
                if prelude:
                    blocks.append((prelude, body))
                start = j
                i = j
                continue
        i += 1

    return blocks


def _find_var_calls(text: str) -> list[tuple[int, int, str, Optional[str]]]:
    """
    Finds var(...) calls with balanced parentheses.
    Returns list of (start_idx, end_idx, var_name, fallback).
    Nested var calls are included (inner calls appear before enclosing outer calls).
    """
    results: list[tuple[int, int, str, Optional[str]]] = []
    if not text or "var(" not in text:
        return results

    stack: list[int] = []
    i = 0
    n = len(text)
    in_single = False
    in_double = False

    while i < n:
        ch = text[i]
        if ch == "\\" and (in_single or in_double):
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue

        if not in_single and not in_double:
            if text.startswith("var(", i):
                stack.append(i)
                i += 4
                continue
            elif ch == ")" and stack:
                start_idx = stack.pop()
                end_idx = i + 1
                inner = text[start_idx + 4 : i]
                # Split on first comma at depth 0 within inner
                comma_idx = -1
                depth = 0
                s_in, d_in = False, False
                for j, c in enumerate(inner):
                    if c == "\\" and (s_in or d_in):
                        continue
                    if c == "'" and not d_in:
                        s_in = not s_in
                    elif c == '"' and not s_in:
                        d_in = not d_in
                    elif not s_in and not d_in:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1
                        elif c == "," and depth == 0:
                            comma_idx = j
                            break
                if comma_idx != -1:
                    var_name = inner[:comma_idx].strip()
                    fallback = inner[comma_idx + 1:].strip()
                else:
                    var_name = inner.strip()
                    fallback = None
                results.append((start_idx, end_idx, var_name, fallback))
                i += 1
                continue
        i += 1

    return results


def _resolve_var_string(val: str, css_vars: dict[str, str], max_passes: int = 5) -> str:
    """Substitutes var(...) references in a string value using css_vars and fallbacks."""
    current = val
    for _ in range(max_passes):
        if "var(" not in current:
            break
        calls = _find_var_calls(current)
        if not calls:
            break
        substituted = False
        for start, end, var_name, fallback in calls:
            if "var(" in current[start + 4 : end - 1]:
                continue
            if var_name in css_vars:
                rep = css_vars[var_name]
                current = current[:start] + rep + current[end:]
                substituted = True
                break
            elif fallback is not None:
                current = current[:start] + fallback + current[end:]
                substituted = True
                break
        if not substituted:
            break
    return current


def _resolve_css_variables(raw_css: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Pass 1: Collect all --name: value definitions.
    Pass 2: Recursively resolve var(--name) nested references until convergence.
    Returns (defs, unresolved).
    """
    clean_css = re.sub(r"/\*[\s\S]*?\*/", "", raw_css)
    defs: dict[str, str] = {}
    for var_name, var_val in _VAR_DEF_RE.findall(clean_css):
        clean_name = var_name.strip()
        clean_val = var_val.strip()
        if "var(" not in clean_val and len(clean_val) > 500:
            continue
        defs[clean_name] = clean_val

    for _ in range(10):
        changed = False
        for k, v in list(defs.items()):
            if "var(" not in v:
                continue
            calls = _find_var_calls(v)
            if not calls:
                continue
            new_v = v
            for start, end, var_name, fallback in calls:
                if "var(" in v[start + 4 : end - 1]:
                    continue
                if var_name in defs:
                    rep = defs[var_name]
                    new_v = new_v[:start] + rep + new_v[end:]
                    changed = True
                    break
                elif fallback is not None:
                    new_v = new_v[:start] + fallback + new_v[end:]
                    changed = True
                    break
            if new_v != v:
                defs[k] = new_v
        if not changed:
            break

    unresolved = {k: v for k, v in defs.items() if "var(" in v}
    return defs, unresolved


def _extract_css_rules(raw_css: str, css_vars: dict[str, str]) -> list[tuple[str, dict[str, str]]]:
    """
    Extracts selector -> properties mapping using depth-tracking parser.
    Flattens @media/@supports/@layer/@container and resolves var() calls.
    """
    clean_css = re.sub(r"/\*[\s\S]*?\*/", "", raw_css)
    rules: list[tuple[str, dict[str, str]]] = []

    def _process_blocks(blocks: list[tuple[str, str]]):
        for prelude, body in blocks:
            p_lower = prelude.lower().strip()
            if p_lower.startswith(("@font-face", "@page", "@property", "@keyframes", "@-webkit-keyframes", "@-moz-keyframes", "@-o-keyframes")):
                continue
            if p_lower.startswith(("@media", "@supports", "@layer", "@container")):
                inner_blocks = _parse_css_blocks(body)
                _process_blocks(inner_blocks)
                continue

            # Standard CSS rule
            props: dict[str, str] = {}
            for decl in body.split(";"):
                decl = decl.strip()
                if ":" in decl:
                    k, sep, v = decl.partition(":")
                    k_clean = k.strip().lower()
                    v_clean = v.strip()
                    if k_clean and v_clean:
                        resolved_v = _resolve_var_string(v_clean, css_vars)
                        props[k_clean] = resolved_v
            if props:
                rules.append((prelude.strip().lower(), props))

    top_blocks = _parse_css_blocks(clean_css)
    _process_blocks(top_blocks)
    return rules


# ============================================================================
# DESIGN SUBSYSTEM EXTRACTORS
# ============================================================================

def _extract_semantic_colors(
    css_vars: dict[str, str],
    all_hex_counts: Counter,
    theme: str,
    bg_hex: str,
) -> dict[str, str]:
    """
    Extracts semantic colors without fabricating defaults.
    Checks css_vars first, then looks for hue-clustered saturated hexes in all_hex_counts.
    Omit the family if not found.
    """
    semantic: dict[str, str] = {}

    var_patterns = {
        "success": ["--success", "--green", "--positive", "--ok"],
        "error": ["--error", "--danger", "--red", "--negative"],
        "warning": ["--warning", "--warn", "--yellow", "--caution"],
        "info": ["--info", "--blue", "--notice"],
    }

    for role, keys in var_patterns.items():
        for k in keys:
            for vk, vv in css_vars.items():
                if k in vk.lower():
                    hex_val = _normalize_color_to_hex(vv)
                    if hex_val:
                        semantic[role] = hex_val
                        break
            if role in semantic:
                break

    hue_ranges = {
        "success": [(90, 150)],
        "error": [(0, 15), (345, 360)],
        "warning": [(30, 60)],
        "info": [(200, 260)],
    }

    for role, ranges in hue_ranges.items():
        if role in semantic:
            continue
        candidates = []
        for hex_val, count in all_hex_counts.most_common():
            if _saturation(hex_val) > 0.3 and _contrast_ratio(hex_val, bg_hex) > 2.0:
                hue = _hue_degrees(hex_val)
                for low, high in ranges:
                    if low <= hue <= high:
                        candidates.append((count, hex_val))
                        break
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            semantic[role] = candidates[0][1]

    return semantic


def _extract_gradients(css_text: str) -> list[tuple[str, str]]:
    """
    Finds linear-gradient(...) calls and extracts first and last hex stops (up to 3 gradients).
    Does NOT emit Vercel's hardcoded gradients.
    """
    gradients: list[tuple[str, str]] = []
    if not css_text or "linear-gradient" not in css_text:
        return gradients

    pattern = re.compile(r"linear-gradient\s*\(([^)]+)\)", re.IGNORECASE)
    seen = set()

    for m in pattern.finditer(css_text):
        content = m.group(1)
        hexes = []
        for hex_m in _HEX_RE.finditer(content):
            h_norm = _normalize_color_to_hex(hex_m.group(0))
            if h_norm:
                hexes.append(h_norm)
        for rgb_m in _RGB_RE.finditer(content):
            h_norm = _normalize_color_to_hex(rgb_m.group(0))
            if h_norm:
                hexes.append(h_norm)
        for hsl_m in _HSL_RE.finditer(content):
            h_norm = _normalize_color_to_hex(hsl_m.group(0))
            if h_norm:
                hexes.append(h_norm)

        if len(hexes) >= 2:
            pair = (hexes[0], hexes[-1])
            if pair not in seen and pair[0] != pair[1]:
                seen.add(pair)
                gradients.append(pair)
                if len(gradients) >= 3:
                    break

    return gradients


def _extract_typography_scale(
    css_rules: list[tuple[str, dict[str, str]]],
    default_font: str = "sans-serif",
) -> dict[str, TypeToken]:
    """
    Scan font-size values (convert rem/em -> px @16px root).
    Bucket: display-xl >=40, display-lg 32-39, display-md 24-31, display-sm 20-23,
    body-lg 17-19, body-md 15-16, body-sm 13-14, caption 11-12.
    Take most frequent (size, weight, line-height, letter-spacing) per bucket.
    Skip empty buckets.
    """
    buckets: dict[str, Counter] = {
        "display-xl": Counter(),
        "display-lg": Counter(),
        "display-md": Counter(),
        "display-sm": Counter(),
        "body-lg": Counter(),
        "body-md": Counter(),
        "body-sm": Counter(),
        "caption": Counter(),
    }

    for sel, props in css_rules:
        if "font-size" not in props:
            continue
        fs_raw = props["font-size"]
        m = re.search(r"([\d\.]+)\s*(px|rem|em)", fs_raw, re.IGNORECASE)
        if not m:
            continue
        val = float(m.group(1))
        unit = m.group(2).lower()
        px = val * 16.0 if unit in ("rem", "em") else val
        px_int = round(px)

        bucket_name = None
        if px_int >= 40:
            bucket_name = "display-xl"
        elif 32 <= px_int <= 39:
            bucket_name = "display-lg"
        elif 24 <= px_int <= 31:
            bucket_name = "display-md"
        elif 20 <= px_int <= 23:
            bucket_name = "display-sm"
        elif 17 <= px_int <= 19:
            bucket_name = "body-lg"
        elif 15 <= px_int <= 16:
            bucket_name = "body-md"
        elif 13 <= px_int <= 14:
            bucket_name = "body-sm"
        elif 11 <= px_int <= 12:
            bucket_name = "caption"

        if not bucket_name:
            continue

        family = props.get("font-family", default_font).split(",")[0].strip().strip("'\"")
        weight = props.get("font-weight", "600" if "display" in bucket_name else "400").strip()
        line_height = props.get("line-height", "1.2" if "display" in bucket_name else "1.5").strip()
        letter_spacing = props.get("letter-spacing", "0px").strip()

        buckets[bucket_name][(family, f"{px_int}px", weight, line_height, letter_spacing)] += 1

    scale: dict[str, TypeToken] = {}
    for bucket_name, counter in buckets.items():
        if counter:
            most_freq = counter.most_common(1)[0][0]
            scale[bucket_name] = TypeToken(
                font_family=most_freq[0],
                font_size=most_freq[1],
                font_weight=most_freq[2],
                line_height=most_freq[3],
                letter_spacing=most_freq[4],
            )

    return scale


def _extract_spacing_scale(css_rules: list[tuple[str, dict[str, str]]]) -> list[int]:
    """
    Collect all padding/margin/gap/row-gap/column-gap px values (2-256).
    Return sorted dedup set. Return [] if none found.
    """
    spacing_set = set()
    spacing_props = (
        "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
        "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
        "gap", "row-gap", "column-gap",
    )
    pattern = re.compile(r"([\d\.]+)\s*(px|rem|em)", re.IGNORECASE)

    for _, props in css_rules:
        for p in spacing_props:
            if p in props:
                for m in pattern.finditer(props[p]):
                    val = float(m.group(1))
                    unit = m.group(2).lower()
                    px = val * 16.0 if unit in ("rem", "em") else val
                    px_int = round(px)
                    if 2 <= px_int <= 256:
                        spacing_set.add(px_int)

    return sorted(list(spacing_set))


def _extract_radii(css_rules: list[tuple[str, dict[str, str]]]) -> tuple[list[str], str, str]:
    """
    Extract radii returning (all_radii, card_radius, button_radius).
    Convert rem/em -> px. 9999px/99999px -> 'full'.
    card = most common in .card/.panel/.surface context.
    button = most common in .btn/.button/button context.
    Fallbacks only if empty: card="12px", button="8px".
    """
    all_counts: Counter = Counter()
    card_counts: Counter = Counter()
    btn_counts: Counter = Counter()

    pattern = re.compile(r"([\d\.]+)\s*(px|rem|em)|(9999+px|50%|full)", re.IGNORECASE)

    for sel, props in css_rules:
        if "border-radius" in props:
            val_raw = props["border-radius"].strip()
            if any(k in val_raw for k in ("9999px", "99999px", "50%", "full")):
                norm = "full"
            else:
                m = pattern.search(val_raw)
                if m:
                    if m.group(3):
                        norm = "full"
                    else:
                        num = float(m.group(1))
                        unit = m.group(2).lower()
                        px = num * 16.0 if unit in ("rem", "em") else num
                        norm = "full" if px >= 999 else f"{round(px)}px"
                else:
                    norm = val_raw

            all_counts[norm] += 1
            if re.search(r"\.(card|panel|surface|tile|box)\b", sel):
                card_counts[norm] += 1
            if re.search(r"(\.btn|\.button|\bbutton\b|\.cta)", sel):
                btn_counts[norm] += 1

    all_radii = [r for r, _ in all_counts.most_common()]
    card_radius = card_counts.most_common(1)[0][0] if card_counts else (all_radii[0] if all_radii else "12px")
    btn_radius = btn_counts.most_common(1)[0][0] if btn_counts else (all_radii[0] if all_radii else "8px")

    return all_radii, card_radius, btn_radius


def _extract_components(
    html: str,
    css_rules: list[tuple[str, dict[str, str]]],
    soup=None,
) -> list[ComponentToken]:
    """
    Extracts component tokens present in HTML classes and classifies kind by name.
    Deduplicates by name (merges props), sorts by kind then name, capped at 40.
    """
    html_classes: set[str] = set()
    if soup:
        for el in soup.find_all(class_=True):
            cls_attr = el.get("class", [])
            if isinstance(cls_attr, list):
                html_classes.update(cls_attr)
            elif isinstance(cls_attr, str):
                html_classes.update(cls_attr.split())
    else:
        for m in re.finditer(r'class=["\']([^"\']+)["\']', html, re.IGNORECASE):
            html_classes.update(m.group(1).split())

    scrapbook_kw = {
        "polaroid", "notepaper", "notebook", "paper", "tape", "sticker", "pin", "clip",
        "idcard", "contact-card", "postcard", "letter", "note", "say-note", "quote",
        "big-quote", "thought", "speech", "bubble", "handwritten",
    }
    pricing_kw = {"pricing", "plan", "tier", "subscribe"}
    navigation_kw = {"nav", "navbar", "header", "footer", "sidebar", "menu", "tab"}
    action_kw = {"btn", "button", "cta", "link", "action"}
    surface_kw = {"card", "panel", "surface", "tile", "block", "box"}
    form_kw = {"input", "field", "form", "textarea", "select", "checkbox", "radio", "toggle", "switch"}
    badge_kw = {"badge", "pill", "chip", "tag", "label", "kbd"}
    overlay_kw = {"modal", "dialog", "drawer", "sheet", "popover", "tooltip", "toast"}
    media_kw = {"avatar", "icon", "logo", "img", "image", "media", "thumb"}
    section_kw = {"hero", "banner", "feature", "showcase", "band", "section"}
    tool_kw = {"tool", "tool-tile", "skill", "tech"}
    progress_kw = {"timeline", "step", "progress", "meter"}

    def _classify_kind(name: str) -> str:
        nl = name.lower()
        tokens = re.split(r"[-_]", nl)
        for t in tokens:
            if t in scrapbook_kw: return "scrapbook"
        for kw in scrapbook_kw:
            if kw in nl: return "scrapbook"
        for t in tokens:
            if t in pricing_kw: return "pricing"
        for kw in pricing_kw:
            if kw in nl: return "pricing"
        for t in tokens:
            if t in navigation_kw: return "navigation"
        for kw in navigation_kw:
            if kw in nl: return "navigation"
        for t in tokens:
            if t in action_kw: return "action"
        for kw in action_kw:
            if kw in nl: return "action"
        for t in tokens:
            if t in surface_kw: return "surface"
        for kw in surface_kw:
            if kw in nl: return "surface"
        for t in tokens:
            if t in form_kw: return "form"
        for kw in form_kw:
            if kw in nl: return "form"
        for t in tokens:
            if t in badge_kw: return "badge"
        for kw in badge_kw:
            if kw in nl: return "badge"
        for t in tokens:
            if t in overlay_kw: return "overlay"
        for kw in overlay_kw:
            if kw in nl: return "overlay"
        for t in tokens:
            if t in media_kw: return "media"
        for kw in media_kw:
            if kw in nl: return "media"
        for t in tokens:
            if t in section_kw: return "section"
        for kw in section_kw:
            if kw in nl: return "section"
        for t in tokens:
            if t in tool_kw: return "tool"
        for kw in tool_kw:
            if kw in nl: return "tool"
        for t in tokens:
            if t in progress_kw: return "progress"
        for kw in progress_kw:
            if kw in nl: return "progress"
        return "generic"

    components_by_name: dict[str, ComponentToken] = {}

    for selector, props in css_rules:
        clean_sel = re.sub(r"::?[a-zA-Z0-9_-]+(\([^)]*\))?", "", selector)
        clean_sel = re.sub(r"\[[^\]]*\]", "", clean_sel)
        cand_classes = re.findall(r"\.([a-zA-Z0-9_-]+)", clean_sel)
        for cls_name in cand_classes:
            if cls_name in html_classes:
                if cls_name not in components_by_name:
                    kind = _classify_kind(cls_name)
                    components_by_name[cls_name] = ComponentToken(
                        name=cls_name,
                        kind=kind,
                        selector=f".{cls_name}",
                        properties=dict(props),
                    )
                else:
                    components_by_name[cls_name].properties.update(props)

    sorted_components = sorted(components_by_name.values(), key=lambda c: (c.kind, c.name))
    return sorted_components[:40]


# ============================================================================
# MASTER ENTRY POINT: extract_design_tokens
# ============================================================================

def extract_design_tokens(raw_html: str, name: str = "Design System") -> DesignTokens:
    """
    Deterministic design token extraction pipeline.
    Parses HTML and CSS into a structured DesignTokens object.
    """
    warnings_list: list[str] = []
    clean_html = strip_base64_images(raw_html)

    soup = BeautifulSoup(clean_html, "html.parser") if BeautifulSoup else None

    # Collect raw CSS from style tags and inline styles
    style_blocks: list[str] = []
    if soup:
        for s in soup.find_all("style"):
            if s.string:
                style_blocks.append(s.string)
    else:
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", clean_html, re.DOTALL | re.IGNORECASE):
            style_blocks.append(m.group(1))

    raw_css = "\n".join(style_blocks)

    # Keyframes extraction
    keyframes = extract_keyframes(raw_css)

    # CSS Variables resolution
    css_vars, unresolved = _resolve_css_variables(raw_css)
    if unresolved:
        warnings_list.append(f"Unresolved CSS variables ({len(unresolved)}): {list(unresolved.keys())[:5]}")

    # CSS Rules extraction
    css_rules = _extract_css_rules(raw_css, css_vars)

    # Collect all hex occurrences across rules and vars for statistical ranking
    all_hex_counts: Counter = Counter()
    for _, props in css_rules:
        for _, val in props.items():
            for m in _HEX_RE.finditer(val):
                h = _normalize_color_to_hex(m.group(0))
                if h:
                    all_hex_counts[h] += 1
            for m in _RGB_RE.finditer(val):
                h = _normalize_color_to_hex(m.group(0))
                if h:
                    all_hex_counts[h] += 1
            for m in _HSL_RE.finditer(val):
                h = _normalize_color_to_hex(m.group(0))
                if h:
                    all_hex_counts[h] += 1
            for m in _OKLCH_RE.finditer(val):
                h = _normalize_color_to_hex(m.group(0))
                if h:
                    all_hex_counts[h] += 1

    for _, v in css_vars.items():
        h = _normalize_color_to_hex(v)
        if h:
            all_hex_counts[h] += 2

    # -------------------------------------------------------------------------
    # 1. Background Detection
    # -------------------------------------------------------------------------
    bg_color: Optional[str] = None
    bg_var_keys = [
        "--paper", "--paper-bg", "--paper-2", "--cream", "--cream-bg", "--canvas-2",
        "--page-bg", "--surface-base", "--bg-base", "--background-color",
        "--body-background", "--layout-bg", "--shell-bg", "--base-bg",
        "--background", "--bg", "--canvas", "--surface", "--app-bg",
    ]
    for k in bg_var_keys:
        if k in css_vars:
            h = _normalize_color_to_hex(css_vars[k])
            if h:
                bg_color = h
                break

    # Scan inline style on root / body containers
    if not bg_color and soup:
        for sel_tag in ("html", "body", "#root", "#app", ".page", ".app", ".shell", ".wrap"):
            el = None
            if sel_tag.startswith("#"):
                el = soup.find(id=sel_tag[1:])
            elif sel_tag.startswith("."):
                el = soup.find(class_=sel_tag[1:])
            else:
                el = soup.find(sel_tag)
            if el and el.get("style"):
                st = el["style"]
                for p in ("background-color", "background"):
                    m_p = re.search(rf"{p}\s*:\s*([^;]+)", st, re.IGNORECASE)
                    if m_p:
                        h = _normalize_color_to_hex(m_p.group(1))
                        if h:
                            bg_color = h
                            break
            if bg_color:
                break

    # Scan CSS rules restricted to root/body selectors
    if not bg_color:
        root_sel_re = re.compile(r"^(html|body|main|#root|#app|\.(page|app|shell|wrap|site|layout|container))\b", re.IGNORECASE)
        for sel, props in css_rules:
            single_sels = [s.strip() for s in sel.split(",")]
            if any(root_sel_re.search(s) for s in single_sels):
                for p in ("background-color", "background"):
                    if p in props:
                        raw_val = props[p]
                        if "gradient" in raw_val:
                            # take first color stop
                            stops = _HEX_RE.findall(raw_val) or _RGB_RE.findall(raw_val)
                            if stops:
                                h = _normalize_color_to_hex(stops[0] if isinstance(stops[0], str) else f"rgb{stops[0]}")
                                if h:
                                    bg_color = h
                                    break
                        else:
                            h = _normalize_color_to_hex(raw_val)
                            if h:
                                bg_color = h
                                break
            if bg_color:
                break

    # Fallback: bg_counts on non-accent selectors
    if not bg_color:
        bg_counts: Counter = Counter()
        skip_re = re.compile(r"(glow|shadow|accent|highlight|sticker|tape|badge|pill|chip|mark|hl|hover|active|focus|btn|button|tag)", re.IGNORECASE)
        for sel, props in css_rules:
            if not skip_re.search(sel):
                for p in ("background-color", "background"):
                    if p in props:
                        h = _normalize_color_to_hex(props[p])
                        if h:
                            bg_counts[h] += 1
        if bg_counts:
            bg_color = bg_counts.most_common(1)[0][0]

    # Fallback: all_hex_counts filtered to low saturation
    if not bg_color:
        low_sat = [c for c, _ in all_hex_counts.most_common() if _saturation(c) < 0.25]
        if low_sat:
            bg_color = low_sat[0]

    # Absolute last resort
    if not bg_color:
        bg_color = "#ffffff"
        warnings_list.append("Background color could not be reliably detected; fell back to default #ffffff")

    # Theme determination based on canvas relative luminance
    theme = "dark" if _relative_luminance(bg_color) < 0.5 else "light"

    # -------------------------------------------------------------------------
    # 2. Text Primary Detection
    # -------------------------------------------------------------------------
    text_primary: Optional[str] = None
    text_var_keys = ["--ink", "--foreground", "--text", "--text-primary", "--body-color", "--color"]
    for k in text_var_keys:
        if k in css_vars:
            h = _normalize_color_to_hex(css_vars[k])
            if h and _contrast_ratio(h, bg_color) >= 4.5:
                text_primary = h
                break

    if not text_primary:
        # Prefer body / html / p
        body_sel_re = re.compile(r"^(body|html|p)\b", re.IGNORECASE)
        for sel, props in css_rules:
            if body_sel_re.search(sel) and "color" in props:
                h = _normalize_color_to_hex(props["color"])
                if h and _contrast_ratio(h, bg_color) >= 4.5:
                    text_primary = h
                    break

    if not text_primary:
        for c, _ in all_hex_counts.most_common():
            if _contrast_ratio(c, bg_color) >= 4.5:
                text_primary = c
                break

    if not text_primary:
        text_primary = _best_foreground(bg_color)

    # -------------------------------------------------------------------------
    # 3. Surface & Surface 2 Detection
    # -------------------------------------------------------------------------
    surface_color: Optional[str] = None
    surface_var_keys = ["--surface", "--surface-1", "--card-bg", "--panel-bg", "--bg-surface"]
    for k in surface_var_keys:
        if k in css_vars:
            h = _normalize_color_to_hex(css_vars[k])
            if h and h != bg_color:
                surface_color = h
                break

    if not surface_color:
        for sel, props in css_rules:
            if re.search(r"\.(card|panel|surface|tile|box)\b", sel):
                for p in ("background-color", "background"):
                    if p in props:
                        h = _normalize_color_to_hex(props[p])
                        if h and h != bg_color:
                            surface_color = h
                            break
            if surface_color:
                break

    if not surface_color:
        surface_color = _adjust_color(bg_color, 0.08 if theme == "dark" else -0.04)

    surface_2 = _adjust_color(surface_color, 0.05 if theme == "dark" else -0.04)
    muted_color = _adjust_color(text_primary, 0.4 if theme == "dark" else -0.4)

    # -------------------------------------------------------------------------
    # 4. Border Detection
    # -------------------------------------------------------------------------
    border_color: Optional[str] = None
    border_var_keys = ["--border", "--line", "--hairline", "--border-color", "--border-1", "--cream-4", "--divider"]
    for k in border_var_keys:
        if k in css_vars:
            h = _normalize_color_to_hex(css_vars[k])
            if h and h != bg_color:
                border_color = h
                break

    if not border_color:
        cand_borders = []
        for _, props in css_rules:
            for bp in ("border-color", "border", "border-bottom"):
                if bp in props:
                    h = _normalize_color_to_hex(props[bp])
                    if h and h != bg_color:
                        cand_borders.append(h)
        low_sat_borders = [c for c in cand_borders if _saturation(c) <= 0.45]
        if low_sat_borders:
            border_color = Counter(low_sat_borders).most_common(1)[0][0]
        elif cand_borders:
            border_color = Counter(cand_borders).most_common(1)[0][0]

    if not border_color:
        border_color = "#27272a" if theme == "dark" else "#e4e4e7"

    border_strong = _adjust_color(border_color, 0.15 if theme == "dark" else -0.15)

    # -------------------------------------------------------------------------
    # 5. Accent Primary & Secondary Detection
    # -------------------------------------------------------------------------
    primary_accent: Optional[str] = None
    secondary_accent: Optional[str] = None

    accent_var_keys = [
        "--accent", "--primary", "--brand", "--tape", "--cta",
        "--theme-accent", "--color-primary", "--accent-1",
    ]
    for k in accent_var_keys:
        if k in css_vars:
            h = _normalize_color_to_hex(css_vars[k])
            if h and h != bg_color and h != text_primary:
                if not primary_accent:
                    primary_accent = h
                elif not secondary_accent and _euclidean_rgb_distance(h, primary_accent) >= 40:
                    secondary_accent = h
                    break

    # Rank candidate accents by (count, _saturation)
    cand_accents: list[tuple[int, float, str]] = []
    for c, count in all_hex_counts.most_common():
        if c in (bg_color, text_primary, surface_color, border_color):
            continue
        cr_bg = _contrast_ratio(c, bg_color)
        cr_text = _contrast_ratio(c, text_primary)
        if cr_bg >= 2.0 or cr_text >= 1.5:
            cand_accents.append((count, _saturation(c), c))

    cand_accents.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if not primary_accent and cand_accents:
        primary_accent = cand_accents[0][2]

    if not secondary_accent and primary_accent:
        for _, _, c in cand_accents:
            if c != primary_accent and _euclidean_rgb_distance(c, primary_accent) >= 40:
                secondary_accent = c
                break

    if not primary_accent:
        primary_accent = "#3b82f6" if theme == "dark" else "#2563eb"
        warnings_list.append(f"Primary accent not found; defaulted to {primary_accent}")

    if not secondary_accent:
        secondary_accent = _adjust_color(primary_accent, 0.25 if theme == "dark" else -0.25)

    on_primary = _best_foreground(primary_accent)
    link = primary_accent
    link_deep = _adjust_color(link, -0.2 if theme == "light" else 0.2)
    link_soft = _adjust_color(link, 0.3 if theme == "light" else -0.3)

    # -------------------------------------------------------------------------
    # 6. Semantic Colors & Gradients
    # -------------------------------------------------------------------------
    semantic_colors = _extract_semantic_colors(css_vars, all_hex_counts, theme, bg_color)
    gradients = _extract_gradients(raw_css)

    # -------------------------------------------------------------------------
    # 7. Typography, Spacing, Radii & Components
    # -------------------------------------------------------------------------
    # Font detection
    display_font = ""
    body_font = ""
    mono_font = ""
    extracted_fonts: list[str] = []

    for m in _GOOGLE_FONTS_RE.finditer(clean_html):
        f = m.group(1).replace("+", " ").split(":")[0]
        if f not in extracted_fonts:
            extracted_fonts.append(f)

    for sel, props in css_rules:
        if "font-family" in props:
            fam = props["font-family"].split(",")[0].strip().strip("'\"")
            if fam and fam not in extracted_fonts and fam.lower() not in ("inherit", "initial", "unset"):
                extracted_fonts.append(fam)

    for f in extracted_fonts:
        f_lower = f.lower()
        if "mono" in f_lower or "code" in f_lower or "courier" in f_lower:
            if not mono_font:
                mono_font = f
        elif any(k in f_lower for k in ("display", "serif", "heading", "caveat", "playfair", "clash")):
            if not display_font:
                display_font = f
        else:
            if not body_font:
                body_font = f

    if not body_font:
        body_font = extracted_fonts[0] if extracted_fonts else "sans-serif"
    if not display_font:
        display_font = body_font
    if not mono_font:
        mono_font = "monospace"

    typography = _extract_typography_scale(css_rules, body_font)
    if not typography:
        warnings_list.append("Typography scale empty; no explicit font-size declarations matched")

    spacing = _extract_spacing_scale(css_rules)
    if not spacing:
        warnings_list.append("Spacing scale empty; no pixel spacing values found")

    radii, card_radius, button_radius = _extract_radii(css_rules)
    if not radii:
        warnings_list.append("No border-radius rules detected; using default fallbacks for card/button")

    components = _extract_components(clean_html, css_rules, soup)
    if not components:
        warnings_list.append("Components list empty; no matching class declarations in HTML/CSS")

    color_tokens = ColorTokens(
        canvas=bg_color,
        surface=surface_color,
        surface_2=surface_2,
        ink=text_primary,
        body=text_primary,
        muted=muted_color,
        border=border_color,
        border_strong=border_strong,
        primary_accent=primary_accent,
        secondary_accent=secondary_accent,
        on_primary=on_primary,
        link=link,
        link_deep=link_deep,
        link_soft=link_soft,
        semantic=semantic_colors,
        gradients=gradients,
        warnings=list(warnings_list),
    )

    return DesignTokens(
        theme=theme,
        fonts=extracted_fonts if extracted_fonts else [body_font],
        display_font=display_font,
        body_font=body_font,
        mono_font=mono_font,
        colors=color_tokens,
        typography=typography,
        spacing=spacing,
        radii=radii,
        card_radius=card_radius,
        button_radius=button_radius,
        components=components,
        keyframes=keyframes,
        css_vars=css_vars,
        warnings=warnings_list,
    )


# ============================================================================
# BACKWARD COMPATIBILITY SHIMS
# ============================================================================

def generate_design_md(
    raw_html: str | Path,
    title: Optional[str] = None,
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Backward-compatibility shim.
    Delegates token extraction to extract_design_tokens and Markdown generation to core.design_md_generator.
    """
    from core.design_md_generator import generate_design_md as _gen
    if isinstance(raw_html, Path) or (isinstance(raw_html, str) and "\n" not in raw_html and Path(raw_html).is_file()):
        raw_text = Path(raw_html).read_text(encoding="utf-8", errors="replace")
        default_title = Path(raw_html).stem.replace("-", " ").replace("_", " ").title()
    else:
        raw_text = str(raw_html)
        default_title = "Design System"

    effective_title = title or default_title
    tokens = extract_design_tokens(raw_text, effective_title)
    md = _gen(tokens, effective_title)
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md, encoding="utf-8")
    return md


def extract_design_system_from_html(
    html_input: str | Path,
    output_path: Optional[str | Path] = None,
    component_name: Optional[str] = None,
) -> str:
    """Legacy wrapper around generate_design_md."""
    return generate_design_md(
        raw_html=html_input,
        title=component_name,
        output_path=output_path,
    )
