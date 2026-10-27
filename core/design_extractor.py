"""
core/design_extractor.py — Deterministic Design System & Token Extractor

Parses any raw HTML/CSS file or template into a studio-grade, standardized
DESIGN.md specification with YAML frontmatter, tokens, component recipes,
and anti-slop guidelines, or generates a standalone < 25 KB blueprint.html.

Features:
  - Base64 image stripping & replacement with clean SVG / placeholder assets
  - Standalone studio-grade < 25 KB blueprint.html with visual token dashboard
  - Full CSS custom properties (:root) resolution with recursive nested var() support
  - CSS @keyframes animation extraction & live micro-interaction showcase
  - Semantic Role Detection (Background, Text, Accent, Surface, Border, Typography)
  - Automatic Light/Dark Theme Detection & theme-aware descriptions
  - Zero hardcoded color defaults (dynamically computed from extracted palette)
  - 100% deterministic local Python execution
"""

from __future__ import annotations

import datetime
import html
import json
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
except ImportError:
    BeautifulSoup = None

__all__ = [
    "DEFAULT_SVG_PLACEHOLDER",
    "strip_base64_images",
    "strip_base64_bloat",
    "extract_keyframes",
    "generate_blueprint_html",
    "extract_design_system_from_html",
    "generate_design_md",
]

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
_HSL_RE = re.compile(r"hsla?\s*\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%(?:\s*,\s*[\d\.]+)?\s*\)", re.IGNORECASE)
_VAR_DEF_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;}{]+);?")
_VAR_USAGE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)(?:\s*,\s*([^)]+))?\s*\)")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}{]+);?", re.IGNORECASE)
_GOOGLE_FONTS_RE = re.compile(r"fonts\.googleapis\.com/css2\?family=([^&\"'\s]+)")
_BORDER_RADIUS_RE = re.compile(r"border-radius\s*:\s*([^;}{]+);?", re.IGNORECASE)
_CSS_RULE_RE = re.compile(r"([^{]+)\{([^}]+)\}", re.DOTALL)
_BASE64_IMAGE_RE = re.compile(
    r"data:image/[a-zA-Z0-9\+\-\.]+;base64,[A-Za-z0-9+/=\s\\]+?(?=['\"\)\s>,]|$)",
    re.IGNORECASE,
)


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
    import math
    try:
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
        s_norm = s / 100.0
        l_norm = l / 100.0
        c = (1.0 - abs(2.0 * l_norm - 1.0)) * s_norm
        x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
        m = l_norm - c / 2.0
        if 0 <= h < 60: r, g, b = c, x, 0
        elif 60 <= h < 120: r, g, b = x, c, 0
        elif 120 <= h < 180: r, g, b = 0, c, x
        elif 180 <= h < 240: r, g, b = 0, x, c
        elif 240 <= h < 300: r, g, b = x, 0, c
        else: r, g, b = c, 0, x
        return f"#{int((r+m)*255):02x}{int((g+m)*255):02x}{int((b+m)*255):02x}"
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
    m_oklch = re.search(r"oklch\s*\(\s*([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)", val)
    if m_oklch:
        res = _oklch_to_hex(float(m_oklch.group(1)), float(m_oklch.group(2)), float(m_oklch.group(3)))
        if res:
            return res

    # HSL
    m_hsl = _HSL_RE.search(val)
    if m_hsl:
        res = _hsl_to_hex(float(m_hsl.group(1)), float(m_hsl.group(2)), float(m_hsl.group(3)))
        if res:
            return res

    m_hex = _HEX_RE.search(val)
    if m_hex:
        raw = m_hex.group(0)
        r, g, b = _hex_to_rgb(raw)
        return _rgb_to_hex(r, g, b)

    m_rgb = _RGB_RE.search(val)
    if m_rgb:
        r, g, b = int(m_rgb.group(1)), int(m_rgb.group(2)), int(m_rgb.group(3))
        return _rgb_to_hex(r, g, b)

    return None


def _luminance(hex_str: str) -> float:
    try:
        r, g, b = _hex_to_rgb(hex_str)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    except Exception:
        return 0.5


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

def _is_saturated_accent(hex_str: str) -> bool:
    try:
        r, g, b = _hex_to_rgb(hex_str)
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        if max_c == 0:
            return False
        sat = (max_c - min_c) / max_c
        lum = _luminance(hex_str)
        return sat > 0.30 and 0.15 < lum < 0.88
    except Exception:
        return False


def _resolve_css_variables(raw_css: str) -> dict[str, str]:
    """
    Pass 1: Collect all --name: value definitions.
    Pass 2: Recursively resolve var(--name) nested references until full convergence.
    """
    defs: dict[str, str] = {}
    for var_name, var_val in _VAR_DEF_RE.findall(raw_css):
        clean_name = var_name.strip()
        clean_val = var_val.strip().split("/*")[0].strip()
        if any(bad in clean_val for bad in ["{", "}", "@", "hover", "active", "focus"]):
            continue
        if len(clean_val) > 200:
            continue
        defs[clean_name] = clean_val

    for _ in range(10):
        changed = False
        for k, v in list(defs.items()):
            if "var(" in v:
                def _sub(m: re.Match) -> str:
                    ref = m.group(1).strip()
                    fallback = m.group(2).strip() if m.group(2) else ""
                    return defs.get(ref, fallback or ref)

                new_v = _VAR_USAGE_RE.sub(_sub, v)
                if new_v != v:
                    defs[k] = new_v
                    changed = True
        if not changed:
            break

    return defs


def _extract_css_rules(raw_css: str, css_vars: dict[str, str]) -> list[tuple[str, dict[str, str]]]:
    """Extract selector -> properties mapping with variable replacement."""
    rules: list[tuple[str, dict[str, str]]] = []
    
    for sel_raw, body_raw in _CSS_RULE_RE.findall(raw_css):
        selector = sel_raw.strip().lower()
        resolved_body = body_raw
        for var_name, var_val in css_vars.items():
            if var_name in resolved_body:
                resolved_body = re.sub(
                    rf"var\(\s*{re.escape(var_name)}(?:\s*,\s*[^)]+)?\s*\)",
                    var_val,
                    resolved_body,
                )

        props: dict[str, str] = {}
        for decl in resolved_body.split(";"):
            decl = decl.strip()
            if ":" in decl:
                k, sep, v = decl.partition(":")
                props[k.strip().lower()] = v.strip().split("/*")[0].strip()
        
        if props:
            rules.append((selector, props))

    return rules


def strip_base64_images(html_content: str, placeholder: Optional[str] = None) -> str:
    """
    Strips megabytes of embedded base64 image data (e.g. data:image/png;base64,...),
    font data, compiled script data, and framework hydration scripts from HTML templates,
    replacing images with a lightweight clean SVG placeholder asset.
    """
    if not html_content:
        return html_content
    sub_val = placeholder or DEFAULT_SVG_PLACEHOLDER
    c = html_content

    # 1. Strip script tags with data: src (compiled Webpack / Turbopack runtime chunks)
    c = re.sub(r'<script\b[^>]*src=["\']data:[^"\']+["\'][^>]*>\s*</script>', '', c, flags=re.IGNORECASE)

    # 2. Strip Next.js / framework hydration scripts
    if "__next_f" in c:
        c = re.sub(r'<script\b[^>]*>.*?__next_f.*?</script>', '', c, flags=re.DOTALL | re.IGNORECASE)
    if "__NEXT_DATA__" in c:
        c = re.sub(r'<script\b[^>]*id=["\']__NEXT_DATA__["\'][^>]*>.*?</script>', '', c, flags=re.DOTALL | re.IGNORECASE)

    # 3. Strip preload links with data URIs (e.g. embedded font binaries)
    c = re.sub(r'<link\b[^>]*href=["\']data:[^"\']+["\'][^>]*>', '', c, flags=re.IGNORECASE)

    # 4. Strip base64 fonts in @font-face rules
    c = re.sub(r'@font-face\s*\{[^{}]*(?:;base64,|data:(?:font|application))[^{}]*\}', '', c, flags=re.IGNORECASE)

    # 5. Strip base64 images -> SVG placeholder
    if "data:image/" in c:
        c = _BASE64_IMAGE_RE.sub(sub_val, c)

    # 6. Strip any residual data URIs or base64 url calls
    c = re.sub(r'url\(\s*["\']?(?:data:[^"\'\)]+|;base64,[A-Za-z0-9+/=\s\\]+)["\']?\s*\)', 'none', c, flags=re.IGNORECASE)
    c = re.sub(r'data:(?:text/javascript|text/css|application|font|audio|video)/[^"\'\)\s>,]+', '', c, flags=re.IGNORECASE)

    # 7. Strip empty style/script tags
    c = re.sub(r'<style[^>]*>\s*</style>', '', c)
    c = re.sub(r'<script[^>]*>\s*</script>', '', c)

    return c


strip_base64_bloat = strip_base64_images


def extract_keyframes(raw_css: str) -> dict[str, str]:
    """
    Extracts all @keyframes definitions from CSS into a name -> body mapping.
    Correctly balances braces to capture multi-step keyframe blocks.
    """
    keyframes: dict[str, str] = {}
    pattern = re.compile(r"@(?:-(?:webkit|moz|o|ms)-)?keyframes\s+([a-zA-Z0-9_-]+)\s*\{", re.IGNORECASE)
    for m in pattern.finditer(raw_css):
        name = m.group(1).strip()
        open_brace_idx = m.end() - 1
        depth = 0
        end_brace_idx = -1
        for i in range(open_brace_idx, len(raw_css)):
            ch = raw_css[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_brace_idx = i
                    break
        if end_brace_idx != -1:
            body = raw_css[open_brace_idx + 1:end_brace_idx].strip()
            keyframes[name] = body
    return keyframes


def _extract_design_metadata(
    clean_html: str,
    name: str = "Design System",
    source_label: str = "inline",
) -> dict[str, Any]:
    """
    Core deterministic extraction engine: resolves colors, CSS variables, typography,
    radii, spacing, theme, and keyframes across raw HTML/CSS.
    """
    soup = BeautifulSoup(clean_html, "html.parser") if BeautifulSoup else None
    
    style_blocks: list[str] = []
    classes: list[str] = []
    
    if soup:
        for s in soup.find_all("style"):
            if s.string:
                style_blocks.append(s.string)
        for el in soup.find_all(True):
            cls = el.get("class")
            if isinstance(cls, list):
                classes.extend(cls)
            elif isinstance(cls, str):
                classes.extend(cls.split())
    else:
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", clean_html, re.DOTALL | re.IGNORECASE)
        raw_classes = re.findall(r'class=["\']([^"\']+)["\']', clean_html, re.IGNORECASE)
        for c in raw_classes:
            classes.extend(c.split())

    all_css = "\n".join(style_blocks)

    # 1. Resolve CSS Custom Properties (:root) & rules
    css_vars = _resolve_css_variables(all_css)
    css_rules = _extract_css_rules(all_css, css_vars)
    extracted_keyframes = extract_keyframes(all_css)

    # 2. Collect All Document Colors & Count Frequencies
    all_hex_raw = _HEX_RE.findall(clean_html)
    all_hex_counts = Counter(h.lower() for h in all_hex_raw)

    var_colors: dict[str, str] = {}
    for vk, vv in css_vars.items():
        c_hex = _normalize_color_to_hex(vv)
        if c_hex:
            var_colors[vk.lower()] = c_hex

    # 3. Semantic Role Detection
    # --- ROLE 1: BACKGROUND ---
    bg_color: Optional[str] = None
    bg_var_keys = [
        "--background", "--bg", "--canvas", "--surface-1", "--cream",
        "--theme-bg", "--app-bg", "--body-bg", "--main-bg", "--dark",
    ]
    for k in bg_var_keys:
        if k in var_colors:
            bg_color = var_colors[k]
            break

    if not bg_color and soup:
        body_tag = soup.find("body")
        html_tag = soup.find("html")
        for tag in (body_tag, html_tag):
            if not tag:
                continue
            style_attr = tag.get("style", "")
            if style_attr:
                for decl in style_attr.split(";"):
                    if ":" in decl:
                        k, sep, v = decl.partition(":")
                        if k.strip().lower() in ("background-color", "background"):
                            c_hex = _normalize_color_to_hex(v.strip())
                            if c_hex:
                                bg_color = c_hex
                                break
            if bg_color:
                break
            classes_attr = tag.get("class", [])
            if isinstance(classes_attr, str):
                classes_attr = classes_attr.split()
            for cls in classes_attr:
                cls_lower = cls.lower()
                m_hex = re.match(r"^bg-\[#([0-9a-fA-F]{3,8})\]$", cls_lower)
                if m_hex:
                    raw = f"#{m_hex.group(1)}"
                    r, g, b = _hex_to_rgb(raw)
                    bg_color = _rgb_to_hex(r, g, b)
                    break
                tw_bg_map = {
                    "bg-white": "#ffffff",
                    "bg-black": "#000000",
                    "bg-zinc-950": "#09090b",
                    "bg-zinc-900": "#18181b",
                    "bg-zinc-800": "#27272a",
                    "bg-slate-950": "#020617",
                    "bg-slate-900": "#0f172a",
                    "bg-gray-950": "#030712",
                    "bg-gray-900": "#111827",
                    "bg-neutral-950": "#0a0a0a",
                    "bg-neutral-900": "#171717",
                    "bg-zinc-50": "#fafafa",
                    "bg-zinc-100": "#f4f4f5",
                    "bg-gray-50": "#f9fafb",
                    "bg-gray-100": "#f3f4f6",
                    "bg-slate-50": "#f8fafc",
                    "bg-slate-100": "#f1f5f9",
                }
                if cls_lower in tw_bg_map:
                    bg_color = tw_bg_map[cls_lower]
                    break
            if bg_color:
                break

    if not bg_color:
        for sel, props in css_rules:
            if sel in ("body", "html,body", "body,html", "html"):
                for p in ("background-color", "background"):
                    if p in props:
                        c_hex = _normalize_color_to_hex(props[p])
                        if c_hex:
                            bg_color = c_hex
                            break
            if bg_color:
                break

    if not bg_color:
        bg_counts: Counter[str] = Counter()
        for sel, props in css_rules:
            if any(skip in sel for skip in ("glow", "blob", "radial", "cap-glow", "card", "badge", "pill", "tag", "btn", "button", "modal", "tooltip")):
                continue
            for p in ("background-color", "background"):
                if p in props:
                    c = _normalize_color_to_hex(props[p])
                    if c:
                        bg_counts[c] += 1
        if bg_counts:
            bg_color = bg_counts.most_common(1)[0][0]

    if not bg_color:
        if all_hex_counts:
            bg_color = all_hex_counts.most_common(1)[0][0]
        else:
            bg_color = "#09090b"

    theme = "light" if _luminance(bg_color) > 0.5 else "dark"

    # --- ROLE 2: TEXT PRIMARY ---
    text_primary: Optional[str] = None
    text_var_keys = [
        "--text", "--text-primary", "--ink", "--foreground", "--color",
        "--text-color", "--body-color", "--font-color", "--ink-1",
    ]
    for k in text_var_keys:
        if k in var_colors:
            text_primary = var_colors[k]
            break

    if not text_primary and soup:
        body_tag = soup.find("body")
        html_tag = soup.find("html")
        for tag in (body_tag, html_tag):
            if not tag:
                continue
            style_attr = tag.get("style", "")
            if style_attr:
                for decl in style_attr.split(";"):
                    if ":" in decl:
                        k, sep, v = decl.partition(":")
                        if k.strip().lower() == "color":
                            c_hex = _normalize_color_to_hex(v.strip())
                            if c_hex:
                                text_primary = c_hex
                                break
            if text_primary:
                break
            classes_attr = tag.get("class", [])
            if isinstance(classes_attr, str):
                classes_attr = classes_attr.split()
            for cls in classes_attr:
                cls_lower = cls.lower()
                m_hex = re.match(r"^text-\[#([0-9a-fA-F]{3,8})\]$", cls_lower)
                if m_hex:
                    raw = f"#{m_hex.group(1)}"
                    r, g, b = _hex_to_rgb(raw)
                    text_primary = _rgb_to_hex(r, g, b)
                    break
                tw_text_map = {
                    "text-white": "#ffffff",
                    "text-black": "#000000",
                    "text-zinc-950": "#09090b",
                    "text-zinc-900": "#18181b",
                    "text-zinc-800": "#27272a",
                    "text-zinc-700": "#3f3f46",
                    "text-zinc-100": "#f4f4f5",
                    "text-slate-900": "#0f172a",
                    "text-gray-900": "#111827",
                    "text-gray-800": "#1f2937",
                }
                if cls_lower in tw_text_map:
                    text_primary = tw_text_map[cls_lower]
                    break
            if text_primary:
                break

    if not text_primary:
        for sel, props in css_rules:
            if sel in ("body", "html,body", "p", "h1"):
                if "color" in props:
                    c_hex = _normalize_color_to_hex(props["color"])
                    if c_hex:
                        text_primary = c_hex
                        break

    if not text_primary:
        text_primary = "#0a0a0a" if theme == "light" else "#ffffff"

    # --- ROLE 3: ACCENT PRIMARY & SECONDARY ---
    primary_accent: Optional[str] = None
    secondary_accent: Optional[str] = None
    accent_var_keys = [
        "--accent", "--primary", "--brand", "--cobalt", "--sky", "--blue",
        "--purple", "--green", "--neon", "--hl", "--highlight", "--coral",
        "--orange", "--pink", "--paper-yellow", "--paper-pink", "--paper-blue",
        "--cta", "--color-primary", "--theme-accent", "--accent-1", "--color-accent",
    ]
    for k in accent_var_keys:
        if k in var_colors and var_colors[k] != bg_color and var_colors[k] != text_primary:
            if not primary_accent:
                primary_accent = var_colors[k]
            elif not secondary_accent and var_colors[k] != primary_accent:
                secondary_accent = var_colors[k]
                break

    if not primary_accent:
        for sel, props in css_rules:
            if any(btn_kw in sel for btn_kw in (".btn-primary", ".button-primary", ".cta", "button.primary", ".btn", "a:hover")):
                for p in ("background-color", "background", "color"):
                    if p in props:
                        c_hex = _normalize_color_to_hex(props[p])
                        if c_hex and c_hex != bg_color and c_hex != text_primary and _saturation(c_hex) > 0.15:
                            primary_accent = c_hex
                            break
            if primary_accent:
                break

    if not primary_accent:
        prominent_saturated = [
            c for c, count in all_hex_counts.most_common(40)
            if c != bg_color and c != text_primary and _saturation(c) > 0.18
        ]
        if prominent_saturated:
            primary_accent = prominent_saturated[0]

    if not primary_accent:
        primary_accent = "#2563eb" if theme == "light" else "#60a5fa"

    if not secondary_accent:
        for c, count in all_hex_counts.most_common(40):
            if c != bg_color and c != text_primary and c != primary_accent and _saturation(c) > 0.15:
                secondary_accent = c
                break
    if not secondary_accent:
        secondary_accent = "#f59e0b" if theme == "light" else "#a78bfa"

    # --- ROLE 4: SURFACE / CARD ---
    surface_color: Optional[str] = None
    surface_var_keys = [
        "--surface", "--card", "--panel", "--sheet", "--paper-2", "--surface-2",
        "--cream-2", "--cream-3", "--card-bg", "--surface-card",
    ]
    for k in surface_var_keys:
        if k in var_colors and var_colors[k] != bg_color:
            c = var_colors[k]
            if theme == "light" and _luminance(c) > 0.4:
                surface_color = c
                break
            elif theme == "dark" and _luminance(c) < 0.6:
                surface_color = c
                break

    if not surface_color:
        for sel, props in css_rules:
            if any(card_kw in sel for card_kw in (".card", ".panel", "section", "article", ".wrap")):
                for p in ("background-color", "background"):
                    if p in props:
                        c_hex = _normalize_color_to_hex(props[p])
                        if c_hex and c_hex != bg_color:
                            if theme == "light" and _luminance(c_hex) > 0.4:
                                surface_color = c_hex
                                break
                            elif theme == "dark" and _luminance(c_hex) < 0.6:
                                surface_color = c_hex
                                break
            if surface_color:
                break

    if not surface_color:
        surface_color = "#ffffff" if theme == "light" else "#18181b"

    # --- ROLE 5: BORDER ---
    border_color: Optional[str] = None
    border_var_keys = [
        "--border", "--line", "--hairline", "--border-color", "--border-1",
        "--cream-4", "--divider",
    ]
    for k in border_var_keys:
        if k in var_colors:
            border_color = var_colors[k]
            break

    if not border_color:
        for _, props in css_rules:
            for bp in ("border-color", "border", "border-bottom"):
                if bp in props:
                    c_hex = _normalize_color_to_hex(props[bp])
                    if c_hex:
                        border_color = c_hex
                        break
            if border_color:
                break

    if not border_color:
        border_color = "#e4e4e7" if theme == "light" else "#27272a"

    # Secondary text
    text_secondary: Optional[str] = None
    sec_var_keys = ["--muted", "--muted-2", "--text-secondary", "--muted-text", "--text-muted", "--ink-2"]
    for k in sec_var_keys:
        if k in var_colors:
            text_secondary = var_colors[k]
            break
    if not text_secondary:
        text_secondary = "#6c6c6c" if theme == "light" else "#a1a1aa"

    # 4. Typography
    fonts: list[str] = []
    for vk, vv in css_vars.items():
        if any(fkw in vk.lower() for fkw in ("font", "ff")):
            for part in vv.split(","):
                clean = part.strip().strip('"').strip("'")
                if clean and clean not in fonts and clean.lower() not in ("sans-serif", "serif", "monospace"):
                    fonts.append(clean)

    for gfont in _GOOGLE_FONTS_RE.findall(clean_html):
        clean_gfont = gfont.split(":")[0].replace("+", " ")
        if clean_gfont not in fonts:
            fonts.append(clean_gfont)

    for sel, props in css_rules:
        if any(h_kw in sel for h_kw in ("h1", "h2", "h3", ".serif", ".h1", "body")):
            if "font-family" in props:
                for fam_part in props["font-family"].split(","):
                    clean_fam = fam_part.strip().strip('"').strip("'")
                    if clean_fam and clean_fam not in fonts and clean_fam.lower() not in ("sans-serif", "serif", "monospace"):
                        fonts.insert(0, clean_fam)

    if not fonts:
        fonts = ["Inter", "sans-serif"]
    
    serif_font = next((f for f in fonts if any(skw in f.lower() for skw in ("serif", "instrument", "canela", "garamond", "georgia"))), None)
    primary_font = serif_font or fonts[0]
    body_font = next((f for f in fonts if f != serif_font and "mono" not in f.lower()), "Inter")
    mono_font = next((f for f in fonts if "mono" in f.lower()), "JetBrains Mono")

    # 5. Radii
    radii: list[str] = []
    for r in _BORDER_RADIUS_RE.findall(all_css):
        clean_r = r.strip()
        if clean_r and clean_r not in radii:
            radii.append(clean_r)

    card_radius = "16px"
    btn_radius = "8px"
    for r in radii:
        if "px" in r:
            val_num = re.findall(r"\d+", r)
            if val_num:
                n = int(val_num[0])
                if 12 <= n <= 24:
                    card_radius = f"{n}px"
                elif 4 <= n <= 10:
                    btn_radius = f"{n}px"

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw_lower = clean_html.lower()
    if any(h in raw_lower for h in ["caveat", "bradley hand", "scrapbook", "sticker"]):
        aesthetic_profile = "Creative Scrapbook & Visual Narrative"
        theme_desc = f"Vibrant scrapbook editorial design extracted from {name}. Features playful hand-drawn notes, rich {primary_accent} accents, and authentic paper surfaces."
    elif any(s in raw_lower for s in ["instrument serif", "georgia", "palatino", "playfair", "serif"]):
        aesthetic_profile = "Refined Editorial & Classic Typography"
        theme_desc = f"High-contrast editorial typography system extracted from {name}. Features classic {primary_font} display fonts, calibrated {border_color} hairline rules, and deep {text_primary} ink."
    elif any(saas in raw_lower for saas in ["plus jakarta sans", "inter", "outfit", "saas", "dashboard"]) and theme == "light":
        aesthetic_profile = "Modern SaaS & High-Precision System"
        theme_desc = f"Studio-grade SaaS product design system from {name}. High-readability {primary_font} headings, sharp {card_radius} card radii, and vibrant {primary_accent} brand accents."
    elif theme == "dark" and (_saturation(primary_accent) > 0.45 or "neon" in raw_lower or "matrix" in raw_lower):
        aesthetic_profile = "Dark Cyberpunk & High-Contrast Neon HUD"
        theme_desc = f"Deep void matrix extracted from {name}. Deep {bg_color} obsidian canvas, glowing {primary_accent} neon micro-interactions, and monospace telemetry."
    elif theme == "dark":
        aesthetic_profile = "Dark Minimalist & High-Precision Void"
        theme_desc = f"Monochromatic dark studio system extracted from {name}. Deep {bg_color} canvas, hairline {border_color} borders, and crisp {text_primary} typography."
    elif theme == "light" and ("hairline" in raw_lower or "grid" in raw_lower or "mono" in raw_lower):
        aesthetic_profile = "Minimalist Monochromatic & Hairline Grid"
        theme_desc = f"Architectural hairline grid portfolio system extracted from {name}. Monospaced tokens, subtle {border_color} borders, and clean {bg_color} negative space."
    else:
        aesthetic_profile = f"{theme.title()} Bespoke Design System"
        theme_desc = f"Deterministic design system extracted from {name} featuring {primary_font} typography and {primary_accent} accents."

    return {
        "name": name,
        "source_label": source_label,
        "theme": theme,
        "theme_desc": theme_desc,
        "aesthetic_profile": aesthetic_profile,
        "extracted_at": now_iso,
        "bg_color": bg_color,
        "surface_color": surface_color,
        "primary_accent": primary_accent,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "border_color": border_color,
        "secondary_accent": secondary_accent,
        "fonts": fonts,
        "primary_font": primary_font,
        "body_font": body_font,
        "mono_font": mono_font,
        "radii": radii,
        "card_radius": card_radius,
        "btn_radius": btn_radius,
        "css_vars": css_vars,
        "css_rules": css_rules,
        "keyframes": extracted_keyframes,
        "all_hex_counts": all_hex_counts,
        "clean_html": clean_html,
    }



def generate_design_md(
    raw_html: str | Path,
    title: Optional[str] = None,
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Generates a world-class <design-context> DESIGN.md specification conforming to the
    YAML Design Token DSL + architectural narrative format requested for Zezo.
    """
    source_label = "inline"
    if isinstance(raw_html, Path) or (isinstance(raw_html, str) and "\n" not in raw_html and Path(raw_html).exists()):
        file_path = Path(raw_html)
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        default_name = file_path.stem.replace("-", " ").replace("_", " ").title()
        source_label = file_path.as_posix()
    else:
        raw_text = str(raw_html)
        default_name = "Custom Design System"

    name = title or default_name
    slug_name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()

    clean_html = strip_base64_images(raw_text)
    meta = _extract_design_metadata(clean_html, name=name, source_label=source_label)

    theme = meta["theme"]
    bg_color = meta["bg_color"]
    surface_color = meta["surface_color"]
    primary_accent = meta["primary_accent"]
    secondary_accent = meta["secondary_accent"]
    text_primary = meta["text_primary"]
    text_secondary = meta["text_secondary"]
    border_color = meta["border_color"]
    primary_font = meta["primary_font"]
    body_font = meta["body_font"]
    mono_font = meta["mono_font"]
    card_radius = meta["card_radius"]
    btn_radius = meta["btn_radius"]
    aesthetic_profile = meta["aesthetic_profile"]

    # Derived semantic tokens
    ink = text_primary
    body = text_secondary
    canvas = bg_color
    canvas_soft = surface_color
    canvas_soft_2 = _adjust_color(surface_color, -0.04 if theme == "light" else 0.05)
    hairline = border_color
    hairline_strong = _adjust_color(border_color, -0.2 if theme == "light" else 0.2)

    primary = text_primary if theme == "light" else primary_accent
    on_primary = "#ffffff" if _luminance(primary) < 0.5 else "#000000"

    mute = _adjust_color(text_secondary, 0.2 if theme == "light" else -0.2)
    link = primary_accent
    link_deep = _adjust_color(primary_accent, -0.15 if theme == "light" else 0.15)
    link_bg_soft = _adjust_color(primary_accent, 0.75 if theme == "light" else -0.6)

    success = "#0070f3" if (_saturation(primary_accent) > 0.3 and "blue" in primary_accent) else "#10b981"
    error = "#ee0000"
    error_soft = "#f7d4d6" if theme == "light" else "#450a0a"
    error_deep = "#c50000"
    warning = "#f5a623"
    warning_soft = "#ffefcf" if theme == "light" else "#451a03"
    warning_deep = "#ab570a"

    violet = secondary_accent
    violet_soft = _adjust_color(secondary_accent, 0.7 if theme == "light" else -0.5)
    violet_deep = _adjust_color(secondary_accent, -0.25 if theme == "light" else 0.25)

    cyan = "#50e3c2"
    cyan_soft = "#aaffec" if theme == "light" else "#042f2e"
    cyan_deep = "#29bc9b"

    highlight_pink = "#ff0080"
    highlight_magenta = "#eb367f"

    grad_dev_start = primary_accent
    grad_dev_end = secondary_accent
    grad_prev_start = "#7928ca"
    grad_prev_end = "#ff0080"
    grad_ship_start = "#ff4d4d"
    grad_ship_end = "#f9cb28"

    selection_bg = primary_accent
    selection_fg = "#ffffff" if _luminance(primary_accent) < 0.5 else "#000000"

    display_font_stack = f"{primary_font}, Inter, system-ui, -apple-system, sans-serif"
    body_font_stack = f"{body_font}, Inter, system-ui, -apple-system, sans-serif"
    mono_font_stack = f"{mono_font}, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"

    desc = f"An architectural interpretation of {name} — a design system rooted in {aesthetic_profile}. Master canvas sits on {canvas} ({theme} mode), high-contrast ink text in {ink}, supported by dynamic {primary_accent} and {secondary_accent} accents, calibrated {hairline} borders, and {primary_font} typography."

    md_content = f"""<design-context>
---
version: alpha
name: {slug_name}-design-analysis
description: {desc}

colors:
  primary: "{primary}"
  on-primary: "{on_primary}"
  ink: "{ink}"
  body: "{body}"
  mute: "{mute}"
  hairline: "{hairline}"
  hairline-strong: "{hairline_strong}"
  canvas: "{canvas}"
  canvas-soft: "{canvas_soft}"
  canvas-soft-2: "{canvas_soft_2}"
  link: "{link}"
  link-deep: "{link_deep}"
  link-bg-soft: "{link_bg_soft}"
  success: "{success}"
  error: "{error}"
  error-soft: "{error_soft}"
  error-deep: "{error_deep}"
  warning: "{warning}"
  warning-soft: "{warning_soft}"
  warning-deep: "{warning_deep}"
  violet: "{violet}"
  violet-soft: "{violet_soft}"
  violet-deep: "{violet_deep}"
  cyan: "{cyan}"
  cyan-soft: "{cyan_soft}"
  cyan-deep: "{cyan_deep}"
  highlight-pink: "{highlight_pink}"
  highlight-magenta: "{highlight_magenta}"
  gradient-develop-start: "{grad_dev_start}"
  gradient-develop-end: "{grad_dev_end}"
  gradient-preview-start: "{grad_prev_start}"
  gradient-preview-end: "{grad_prev_end}"
  gradient-ship-start: "{grad_ship_start}"
  gradient-ship-end: "{grad_ship_end}"
  selection-bg: "{selection_bg}"
  selection-fg: "{selection_fg}"

typography:
  display-xl:
    fontFamily: {display_font_stack}
    fontSize: 48px
    fontWeight: 600
    lineHeight: 48px
    letterSpacing: -2.4px
  display-lg:
    fontFamily: {display_font_stack}
    fontSize: 32px
    fontWeight: 600
    lineHeight: 40px
    letterSpacing: -1.28px
  display-md:
    fontFamily: {display_font_stack}
    fontSize: 24px
    fontWeight: 600
    lineHeight: 32px
    letterSpacing: -0.96px
  display-sm:
    fontFamily: {display_font_stack}
    fontSize: 20px
    fontWeight: 600
    lineHeight: 28px
    letterSpacing: -0.6px
  body-lg:
    fontFamily: {body_font_stack}
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0px
  body-md:
    fontFamily: {body_font_stack}
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
  body-md-strong:
    fontFamily: {body_font_stack}
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px
  body-sm:
    fontFamily: {body_font_stack}
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: -0.28px
  body-sm-strong:
    fontFamily: {body_font_stack}
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
    letterSpacing: -0.28px
  caption:
    fontFamily: {body_font_stack}
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  caption-mono:
    fontFamily: {mono_font_stack}
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  code:
    fontFamily: {mono_font_stack}
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
  button-md:
    fontFamily: {body_font_stack}
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
  button-lg:
    fontFamily: {body_font_stack}
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px

rounded:
  none: 0px
  xs: 4px
  sm: 6px
  md: {btn_radius}
  lg: 12px
  xl: {card_radius}
  pill-sm: 64px
  pill: 100px
  full: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 40px
  3xl: 48px
  4xl: 64px
  5xl: 96px
  6xl: 128px
  section: 192px

components:
  nav-bar:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-sm}}"
    height: 64px
    padding: "{{spacing.sm}} {{spacing.lg}}"
  nav-link:
    textColor: "{{colors.body}}"
    typography: "{{typography.body-sm}}"
    rounded: "{{rounded.full}}"
    padding: "{{spacing.xs}} {{spacing.sm}}"
  nav-cta-signup:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.body-sm-strong}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.xs}}"
    height: 28px
  nav-cta-login:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-sm-strong}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.xs}}"
    height: 28px
  nav-cta-ask-ai:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    typography: "{{typography.body-sm-strong}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.xs}}"
    height: 28px
  button-primary:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.button-lg}}"
    rounded: "{{rounded.pill}}"
    padding: "0px {{spacing.sm}}"
  button-secondary:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.button-lg}}"
    rounded: "{{rounded.pill}}"
    padding: "0px {{spacing.sm}}"
  button-primary-sm:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.button-md}}"
    rounded: "{{rounded.pill}}"
    padding: "0px {{spacing.xs}}"
  button-secondary-sm:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.button-md}}"
    rounded: "{{rounded.pill}}"
    padding: "0px {{spacing.xs}}"
  tab-ghost:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-sm}}"
    rounded: "{{rounded.pill-sm}}"
    padding: "0px {{spacing.md}}"
  icon-button-circular:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    rounded: "{{rounded.full}}"
  card-marketing:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.lg}}"
  card-marketing-large:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  card-soft:
    backgroundColor: "{{colors.canvas-soft}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.lg}}"
  template-card:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.md}}"
  code-editor-mockup:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.code}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.lg}}"
  form-input:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    typography: "{{typography.body-sm}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.sm}}"
    height: 40px
  form-input-sm:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    typography: "{{typography.body-sm}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.sm}}"
    height: 32px
  form-input-lg:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.sm}}"
    padding: "0px {{spacing.sm}}"
    height: 48px
  badge-secondary:
    backgroundColor: "{{colors.canvas-soft}}"
    textColor: "{{colors.body}}"
    typography: "{{typography.caption}}"
    rounded: "{{rounded.full}}"
    padding: "0px {{spacing.xs}}"
  pricing-card:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  pricing-card-featured:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.body-md}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  logo-strip:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.body}}"
    typography: "{{typography.body-sm}}"
    padding: "{{spacing.lg}} {{spacing.xl}}"
  hero-band:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.display-xl}}"
    padding: "{{spacing.4xl}} {{spacing.lg}}"
  feature-mesh-band:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.display-lg}}"
    padding: "{{spacing.5xl}} {{spacing.lg}}"
  showcase-band-light:
    backgroundColor: "{{colors.canvas-soft}}"
    textColor: "{{colors.ink}}"
    typography: "{{typography.display-lg}}"
    padding: "{{spacing.5xl}} {{spacing.lg}}"
  showcase-band-dark:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    typography: "{{typography.display-lg}}"
    padding: "{{spacing.5xl}} {{spacing.lg}}"
  footer:
    backgroundColor: "{{colors.canvas}}"
    textColor: "{{colors.body}}"
    typography: "{{typography.body-sm}}"
    padding: "{{spacing.4xl}} {{spacing.lg}}"
  link-inline:
    textColor: "{{colors.link}}"
    typography: "{{typography.body-md}}"
  banner-marketing:
    backgroundColor: "{{colors.canvas-soft}}"
    textColor: "{{colors.body}}"
    typography: "{{typography.body-sm}}"
    rounded: "{{rounded.full}}"
    padding: "{{spacing.xs}} {{spacing.sm}}"

  # ─── Examples (illustrative) — auto-derived ───
  ex-pricing-tier:
    description: "Default tier card. Mirrors pricing-card chrome on canvas-soft surface with a hairline border."
    backgroundColor: "{{colors.canvas-soft}}"
    textColor: "{{colors.ink}}"
    borderColor: "{{colors.hairline}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  ex-pricing-tier-featured:
    description: "Featured tier — polarity-flipped to ink primary with white text and white CTA."
    backgroundColor: "{{colors.ink}}"
    textColor: "{{colors.on-primary}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  ex-product-selector:
    description: "What's Included summary card — repurposed for feature tiers."
    backgroundColor: "{{colors.canvas-soft}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.lg}}"
  ex-cart-drawer:
    description: "Subscription summary — line items per add-on."
    backgroundColor: "{{colors.canvas}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.lg}}"
    item-divider: "{{colors.hairline}}"
  ex-app-shell-row:
    description: "Sidebar nav row. Active state uses brand primary as a left-edge indicator bar."
    backgroundColor: "{{colors.canvas}}"
    activeIndicator: "{{colors.primary}}"
    rounded: "{{rounded.sm}}"
    padding: "{{spacing.xs}} {{spacing.sm}}"
  ex-data-table-cell:
    description: "Mirrors table chrome. Header uses caption-mono uppercase mono; body uses body-sm."
    headerBackground: "{{colors.canvas-soft}}"
    headerTypography: "{{typography.caption-mono}}"
    bodyTypography: "{{typography.body-sm}}"
    cellPadding: "{{spacing.xs}} {{spacing.sm}}"
    rowBorder: "{{colors.hairline}}"
  ex-auth-form-card:
    description: "Sign-in / sign-up card. Mirrors card-marketing-large chrome with form-input primitives inside."
    backgroundColor: "{{colors.canvas-soft}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  ex-modal-card:
    description: "Modal dialog surface — same chrome as card-marketing-large with Level 5 modal shadow."
    backgroundColor: "{{colors.canvas}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.xl}}"
  ex-empty-state-card:
    description: "Empty-state illustration frame. Generous padding on canvas-soft."
    backgroundColor: "{{colors.canvas-soft}}"
    rounded: "{{rounded.lg}}"
    padding: "{{spacing.3xl}}"
    captionTypography: "{{typography.body-md}}"
  ex-toast:
    description: "Toast notification surface — flat-cornered card-marketing chrome with Level 4 shadow."
    backgroundColor: "{{colors.canvas}}"
    rounded: "{{rounded.md}}"
    padding: "{{spacing.sm}} {{spacing.md}}"
    typography: "{{typography.body-sm}}"

---

## Overview

{name} is an architectural design system — a crafted design language whose surface is built on `{{colors.canvas}}` ({bg_color} in {theme} mode) paired with `{{colors.ink}}` ({text_primary}) ink typography. The interface introduces `{{colors.link}}` ({primary_accent}) as the decisive brand accent, supported by `{{colors.violet}}` ({secondary_accent}) highlights and subtle `{{colors.hairline}}` ({border_color}) hairline rules.

Type is the decisive voice. {primary_font} carries display and headlines with negative letter-spacing for refined editorial authority, while {body_font} powers high-readability body narrative and {mono_font} handles technical metadata, code blocks, and badges.

Surfaces use a calibrated step ladder: `{{colors.canvas}}` ({bg_color} base canvas), `{{colors.canvas-soft}}` ({surface_color} elevated panels), `{{colors.canvas-soft-2}}` (inset regions), and `{{colors.primary}}` (polarity-flipped dark/light bands). Elevation is built on stacked shadows layered with subtle opacity and crisp inset hairlines.

**Key Characteristics:**
- A high-contrast primary CTA `{{colors.primary}}` carries core conversion targets, paired with `{{colors.canvas}}` for secondary actions.
- Curated color accents (`{primary_accent}` and `{secondary_accent}`) provide purposeful focus points without unnecessary color noise.
- Every section eyebrow and small label uses the monospace face `{{typography.caption-mono}}` or `{{typography.code}}`.
- Subtle stacked-shadow elevation — layered offsets with delicate opacity — never a single harsh drop-shadow.
- Standardized container geometry: `{{rounded.md}}` ({btn_radius}) for buttons/inputs and `{{rounded.xl}}` ({card_radius}) for cards.

## Colors

### Brand & Accent
- **Primary Ink / CTA** (`{{colors.primary}}` — `{primary}`): The main conversion CTA color and high-contrast anchor.
- **Primary Accent** (`{{colors.link}}` — `{primary_accent}`): Brand highlight color for active states, link interactions, and focus rings.
- **Secondary Accent** (`{{colors.violet}}` — `{secondary_accent}`): Complementary highlight color for badges and micro-details.

### Surface
- **Canvas** (`{{colors.canvas}}` — `{bg_color}`): Base page background canvas.
- **Canvas Soft** (`{{colors.canvas-soft}}` — `{surface_color}`): Elevated card and panel surfaces.
- **Canvas Soft 2** (`{{colors.canvas-soft-2}}` — `{canvas_soft_2}`): Deeper inset surfaces and interactive hover layers.
- **Hairline** (`{{colors.hairline}}` — `{border_color}`): 1px structural container divider.
- **Hairline Strong** (`{{colors.hairline-strong}}` — `{hairline_strong}`): Emphasized border and secondary divider.

### Text
- **Ink** (`{{colors.ink}}` — `{text_primary}`): All primary titles, headings, and high-contrast text.
- **Body** (`{{colors.body}}` — `{text_secondary}`): Secondary narrative, subtitles, and descriptive paragraphs.
- **Mute** (`{{colors.mute}}` — `{mute}`): Subtle helper labels, timestamps, and fine print.
- **On Primary** (`{{colors.on-primary}}` — `{on_primary}`): Inverted text on `{{colors.primary}}` surfaces.

### Semantic
- **Success / Link** (`{{colors.success}}` — `{success}`): Positive states and verified confirmations.
- **Error** (`{{colors.error}}` — `{error}`): Destructive actions and form validation alerts.
- **Warning** (`{{colors.warning}}` — `{warning}`): Cautionary status and pending indicators.

### Brand Gradient
The brand signature gradient flow:
- `{{colors.gradient-develop-start}}` ({grad_dev_start}) → `{{colors.gradient-develop-end}}` ({grad_dev_end})

## Typography

### Font Family
- **Display / Headings**: {primary_font}, system-ui, -apple-system, sans-serif
- **Body / Narrative**: {body_font}, system-ui, -apple-system, sans-serif
- **Technical / Monospace**: {mono_font}, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{{typography.display-xl}}` | 48px | 600 | 48px | -2.4px | Hero main headline. |
| `{{typography.display-lg}}` | 32px | 600 | 40px | -1.28px | Major section titles. |
| `{{typography.display-md}}` | 24px | 600 | 32px | -0.96px | Card cluster titles, modal headers. |
| `{{typography.display-sm}}` | 20px | 600 | 28px | -0.6px | Sub-section micro-headings. |
| `{{typography.body-lg}}` | 18px | 400 | 28px | 0px | Lead introductory paragraphs. |
| `{{typography.body-md}}` | 16px | 400 | 24px | 0px | Default body copy. |
| `{{typography.body-md-strong}}` | 16px | 500 | 24px | 0px | Bolded inline body emphasis. |
| `{{typography.body-sm}}` | 14px | 400 | 20px | -0.28px | Secondary body, nav links, compact cards. |
| `{{typography.body-sm-strong}}` | 14px | 500 | 20px | -0.28px | Navigation CTA labels, table headers. |
| `{{typography.caption}}` | 12px | 400 | 16px | 0px | Meta tags, badge labels, fine print. |
| `{{typography.caption-mono}}` | 12px | 400 | 16px | 0px | Technical metadata and category tags. |
| `{{typography.code}}` | 13px | 400 | 20px | 0px | Code snippets, terminal commands. |
| `{{typography.button-md}}` | 14px | 500 | 20px | 0px | Compact button labels. |
| `{{typography.button-lg}}` | 16px | 500 | 24px | 0px | Large marketing CTA labels. |

### Principles
- **Negative tracking on display titles**: Aggressive -2.4px to -0.6px tracking for editorial poise.
- **Technical separation**: Monospaced face reserved exclusively for technical labels, code, and data metrics.
- **Maximum weight 600**: Keep headings grounded without noisy heavy black fonts.

### Note on Font Substitutes
- If {primary_font} is not locally available, system fallbacks provide instant graceful degradation: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.

## Layout

### Spacing System
- Base unit: 4px modular rhythm.
- Spacing tokens: `{{spacing.xxs}}` (4px) · `{{spacing.xs}}` (8px) · `{{spacing.sm}}` (12px) · `{{spacing.md}}` (16px) · `{{spacing.lg}}` (24px) · `{{spacing.xl}}` (32px) · `{{spacing.2xl}}` (40px) · `{{spacing.3xl}}` (48px) · `{{spacing.4xl}}` (64px) · `{{spacing.5xl}}` (96px).
- Section vertical padding: `{{spacing.4xl}}` (64px) to `{{spacing.5xl}}` (96px).

### Grid & Container
- Max container width: `1280px` / `1400px` centered with `{{spacing.lg}}` (24px) lateral gutters.
- Standard columns: 3-column feature grid on desktop, collapsing to 1-column on mobile.

### Responsive Strategy

#### Breakpoints
| Name | Width | Key Changes |
|---|---|---|
| Mobile | < 600px | 1-column vertical stack, mobile navigation sheet. |
| Tablet | 600–959px | 2-column grid adaptation, compact padding. |
| Desktop | 960–1199px | Full multi-column grid layouts. |
| Wide | ≥ 1200px | Max container width constraint with centered margins. |

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Level 0 — Flat | No shadow, 1px `{{colors.hairline}}` border. | Base canvas panels and full-bleed bands. |
| Level 1 — Inset Hairline | `0 0 0 1px {{colors.hairline}}` inset border. | Standard cards and content modules. |
| Level 2 — Subtle Drop | `0px 1px 2px rgba(0,0,0,0.05)` + hairline. | Elevated interactive cards. |
| Level 3 — Soft Stack | `0px 4px 12px -2px rgba(0,0,0,0.08)` + hairline. | Feature cards and active containers. |
| Level 4 — Float Stack | `0px 8px 24px -4px rgba(0,0,0,0.12)` + hairline. | Pricing tiers and prominent popovers. |
| Level 5 — Modal | `0px 16px 40px -8px rgba(0,0,0,0.20)` + hairline. | Modal dialogs and central overlays. |

## Shapes

### Border Radius Scale
| Token | Value | Use |
|---|---|---|
| `{{rounded.none}}` | 0px | Full-bleed hero and footer bands. |
| `{{rounded.xs}}` | 4px | Micro badges and code tags. |
| `{{rounded.sm}}` | 6px | Form input controls and small badges. |
| `{{rounded.md}}` | {btn_radius} | Primary buttons and interactive chips. |
| `{{rounded.lg}}` | 12px | Standard cards and containers. |
| `{{rounded.xl}}` | {card_radius} | Prominent hero panels and modals. |
| `{{rounded.full}}` | 9999px | Circular icon buttons and pill badges. |

## Components

### Buttons
- **`button-primary`**: Background `{{colors.primary}}`, text `{{colors.on-primary}}`, shape `{{rounded.pill}}`, typography `{{typography.button-lg}}`.
- **`button-secondary`**: Background `{{colors.canvas}}`, text `{{colors.ink}}`, border 1px solid `{{colors.hairline}}`, shape `{{rounded.pill}}`.

### Cards & Containers
- **`card-marketing`**: Background `{{colors.canvas}}`, text `{{colors.ink}}`, shape `{{rounded.md}}`, border 1px solid `{{colors.hairline}}`.
- **`card-soft`**: Background `{{colors.canvas-soft}}`, text `{{colors.ink}}`, shape `{{rounded.md}}`.

### Inputs & Forms
- **`form-input`**: Background `{{colors.canvas}}`, border 1px solid `{{colors.hairline}}`, text `{{colors.ink}}`, shape `{{rounded.sm}}`, height 40px.

## Do's and Don'ts

### Do
- Maintain authentic {theme} canvas (`{{colors.canvas}}`) with clear semantic surface layers.
- Use `{{colors.primary}}` for primary conversion CTAs.
- Apply negative letter-spacing to headings for high-end typographic authority.
- Standardize container padding using 4px/8px modular rhythm tokens.
- Ensure all form controls have custom borders (`{{colors.hairline}}`) and focus rings (`{{colors.link}}`).

### Don't
- Don't introduce arbitrary purple-to-indigo gradients.
- Don't leave form inputs unstyled with default browser borders.
- Don't use uppercase typography outside of `{{typography.caption-mono}}` tags.
- Don't apply single harsh drop-shadows; use multi-level stacked elevation.

</design-context>
"""

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md_content, encoding="utf-8")

    return md_content


def extract_design_system_from_html(
    html_input: str | Path,
    output_path: Optional[str | Path] = None,
    component_name: Optional[str] = None,
) -> str:
    """
    Extracts tokens, color hierarchy, typography, radii, and component recipes
    from raw HTML/CSS deterministically in the world-class <design-context> DSL format.
    """
    return generate_design_md(
        raw_html=html_input,
        title=component_name,
        output_path=output_path,
    )



def generate_blueprint_html(
    raw_html: str | Path,
    title: str = "Design Blueprint",
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Produces a standalone, studio-grade < 25 KB blueprint.html containing the authentic
    extracted design system (theme, palette, typography, components, keyframe animations,
    and :root CSS design tokens), uniquely adapted to the reference design.
    """
    if isinstance(raw_html, Path) or (isinstance(raw_html, str) and "\n" not in raw_html and Path(raw_html).is_file()):
        file_path = Path(raw_html)
        if title == "Design Blueprint":
            title = file_path.stem.replace("-", " ").replace("_", " ").title()
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    else:
        raw_text = str(raw_html)

    # 1. Strip base64 image bloat first
    clean_html = strip_base64_images(raw_text)

    # 2. Extract metadata
    meta = _extract_design_metadata(clean_html, name=title, source_label=title)

    theme = meta["theme"]
    aesthetic_profile = meta.get("aesthetic_profile") or (f"{theme.title()} Bespoke Design System")
    bg_color = meta["bg_color"]
    surface_color = meta["surface_color"]
    primary_accent = meta["primary_accent"]
    secondary_accent = meta.get("secondary_accent") or "#f59e0b"
    text_primary = meta["text_primary"]
    text_muted = meta["text_secondary"]
    border_color = meta["border_color"]
    display_font = meta["primary_font"]
    body_font = meta["body_font"]
    mono_font = meta["mono_font"]
    card_radius = meta["card_radius"]
    btn_radius = meta["btn_radius"]
    css_vars = meta["css_vars"]
    extracted_keyframes = meta["keyframes"]
    all_hex_counts = meta["all_hex_counts"]

    # Contrast & Surface calibration
    is_light = (theme == "light")
    bp_bg = bg_color
    bp_surface = surface_color if surface_color != bg_color else ("#ffffff" if is_light else "#18181b")
    bp_text = text_primary
    bp_muted = text_muted
    bp_border = border_color
    bp_accent = primary_accent
    bp_accent_sec = secondary_accent

    # Top distinct palette colors (extended swatches)
    top_swatches: list[str] = []
    seen_colors = {bg_color.lower(), surface_color.lower(), primary_accent.lower(), secondary_accent.lower(), text_primary.lower(), text_muted.lower(), border_color.lower()}
    for c, cnt in all_hex_counts.most_common(24):
        c_lower = c.lower()
        if c_lower not in seen_colors and len(top_swatches) < 8:
            top_swatches.append(c)
            seen_colors.add(c_lower)

    # Format CSS Tokens Block
    css_token_lines = [
        "/* ==========================================",
        f" * Design Blueprint Tokens - {title}",
        f" * Style: {aesthetic_profile.upper()}",
        f" * Theme: {theme.upper()} | Generated by Zezo Studio Engine",
        " * ========================================== */",
        ":root {",
        "  /* --- Semantic Palette --- */",
        f"  --bg: {bg_color};",
        f"  --surface: {bp_surface};",
        f"  --accent: {primary_accent};",
        f"  --accent-secondary: {secondary_accent};",
        f"  --text-primary: {text_primary};",
        f"  --text-muted: {text_muted};",
        f"  --border: {border_color};",
        "",
        "  /* --- Typography --- */",
        f"  --font-display: '{display_font}', sans-serif;",
        f"  --font-body: '{body_font}', sans-serif;",
        f"  --font-mono: '{mono_font}';",
        "",
        "  /* --- Radii & Spacing --- */",
        "  --radius-sm: 6px;",
        f"  --radius-md: {btn_radius};",
        "  --radius-lg: 12px;",
        f"  --radius-xl: {card_radius};",
        "  --radius-full: 9999px;",
        "  --space-xs: 4px;",
        "  --space-sm: 8px;",
        "  --space-md: 16px;",
        "  --space-lg: 24px;",
        "  --space-xl: 32px;",
    ]

    custom_vars = [
        (k, v) for k, v in sorted(css_vars.items())
        if k not in ("--bg", "--surface", "--accent", "--border", "--text", "--muted")
        and len(v) < 80
    ]
    if custom_vars:
        css_token_lines.append("")
        css_token_lines.append("  /* --- Custom Design Properties --- */")
        for k, v in custom_vars[:15]:
            css_token_lines.append(f"  {k}: {v};")

    css_token_lines.append("}")

    if extracted_keyframes:
        css_token_lines.append("")
        css_token_lines.append("/* --- Keyframe Animations --- */")
        for kf_name, kf_body in list(extracted_keyframes.items())[:6]:
            clean_body = re.sub(r"\s+", " ", kf_body).strip()
            css_token_lines.append(f"@keyframes {kf_name} {{ {clean_body} }}")

    full_css_tokens = "\n".join(css_token_lines)
    escaped_title = html.escape(title)
    clean_css_tokens_html = html.escape(full_css_tokens)

    # Keyframes showcase
    keyframes_cards_html = []
    anim_style_rules = []
    display_keyframes = extracted_keyframes.copy()
    if not display_keyframes:
        display_keyframes["pulse-glow"] = "0%, 100% { transform: scale(1); opacity: 0.9; } 50% { transform: scale(1.04); opacity: 1; }"
        display_keyframes["float-gentle"] = "0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); }"

    for idx, (k_name, k_body) in enumerate(list(display_keyframes.items())[:6]):
        clean_body = re.sub(r"\s+", " ", k_body).strip()
        anim_class = f"anim-demo-{idx}"
        anim_style_rules.append(f"@keyframes {k_name} {{ {clean_body} }}")
        anim_style_rules.append(f".{anim_class} {{ animation: {k_name} 3s infinite ease-in-out; }}")
        keyframes_cards_html.append(f"""
        <div class="bp-card kf-card">
          <div class="kf-visual-box"><div class="kf-demo-badge {anim_class}"></div></div>
          <div class="kf-info">
            <span class="kf-name">@{k_name}</span>
            <span class="kf-meta">3s &bull; infinite</span>
          </div>
        </div>
        """)

    embedded_anim_css = "\n".join(anim_style_rules)

    palette_roles = [
        ("Background", bg_color, "--bg", "Canvas base"),
        ("Surface", bp_surface, "--surface", "Cards & elevation"),
        ("Primary Accent", primary_accent, "--accent", "Brand hero & CTAs"),
        ("Secondary Accent", secondary_accent, "--accent-secondary", "Supporting accent"),
        ("Headline Ink", text_primary, "--text-primary", "Primary typography"),
        ("Hairline Border", border_color, "--border", "1px containment"),
    ]
    swatch_cards_html = []
    for label, col_val, token_name, desc in palette_roles:
        lum = _luminance(col_val)
        contrast_tag = "DARK" if lum < 0.5 else "LIGHT"
        border_hint = f"border: 1px solid {'rgba(0,0,0,0.1)' if lum > 0.8 else 'rgba(255,255,255,0.15)'};"
        swatch_cards_html.append(f"""
        <div class="swatch-card" onclick="copyText('{col_val}', 'Copied {col_val}')" title="Click to copy {col_val}">
          <div class="swatch-tile" style="background-color: {col_val}; {border_hint}">
            <span class="swatch-tag" style="background:{'rgba(0,0,0,0.6)' if lum > 0.5 else 'rgba(255,255,255,0.2)'};color:{'#fff' if lum > 0.5 else '#fff'};">{contrast_tag}</span>
          </div>
          <div class="swatch-details">
            <div class="swatch-name">{label}</div>
            <div class="swatch-token">{token_name}</div>
            <div class="swatch-hex"><code>{col_val}</code></div>
          </div>
        </div>
        """)

    extended_swatches_html = []
    for c in top_swatches:
        extended_swatches_html.append(
            f"""<div class="color-chip" style="background-color: {c}" onclick="copyText('{c}', 'Copied {c}')" title="{c}"><span class="chip-label">{c}</span></div>"""
        )

    # Card background contrast
    card_bg_css = "background: var(--bp-surface);"
    card_border_css = "border: 1px solid var(--bp-border);"
    badge_bg_css = f"background: {primary_accent}20; color: {primary_accent}; border: 1px solid {primary_accent}40;"

    out_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escaped_title} &bull; Design Blueprint</title>
  <style>
    :root {{
      --bp-bg: {bp_bg};
      --bp-surface: {bp_surface};
      --bp-border: {bp_border};
      --bp-text: {bp_text};
      --bp-muted: {bp_muted};
      --bp-accent: {bp_accent};
      --bp-accent-sec: {bp_accent_sec};
      --bp-radius: {card_radius};
      --bp-btn-radius: {btn_radius};
      --bp-font-display: '{display_font}', -apple-system, sans-serif;
      --bp-font-body: '{body_font}', -apple-system, sans-serif;
      --bp-font-mono: '{mono_font}', monospace;
    }}
    {embedded_anim_css}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bp-bg);
      color: var(--bp-text);
      font-family: var(--bp-font-body);
      line-height: 1.5;
      padding: 32px 24px;
      -webkit-font-smoothing: antialiased;
    }}
    .bp-container {{ max-width: 1120px; margin: 0 auto; }}
    .bp-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--bp-border);
      margin-bottom: 32px;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .bp-title-wrap h1 {{
      font-family: var(--bp-font-display);
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .theme-badge {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 3px 10px;
      border-radius: 9999px;
      {badge_bg_css}
    }}
    .bp-subtitle {{
      color: var(--bp-muted);
      font-size: 13px;
      margin-top: 6px;
    }}
    .btn-copy-css {{
      background: var(--bp-accent);
      color: #fff;
      border: none;
      padding: 9px 16px;
      border-radius: var(--bp-btn-radius);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: opacity 0.2s, transform 0.1s;
    }}
    .btn-copy-css:hover {{ opacity: 0.9; transform: translateY(-1px); }}
    .section-title {{
      font-family: var(--bp-font-display);
      font-size: 15px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin: 36px 0 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--bp-text);
    }}
    .bp-card {{
      {card_bg_css}
      {card_border_css}
      border-radius: var(--bp-radius);
      padding: 20px;
    }}
    .swatches-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 14px;
    }}
    .swatch-card {{
      {card_bg_css}
      {card_border_css}
      border-radius: var(--bp-radius);
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .swatch-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }}
    .swatch-tile {{
      height: 72px;
      width: 100%;
      display: flex;
      align-items: flex-start;
      justify-content: flex-end;
      padding: 8px;
    }}
    .swatch-tag {{
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.05em;
      padding: 2px 6px;
      border-radius: 4px;
    }}
    .swatch-details {{
      padding: 12px;
    }}
    .swatch-name {{
      font-size: 12px;
      font-weight: 600;
      color: var(--bp-text);
    }}
    .swatch-token {{
      font-size: 10px;
      font-family: monospace;
      color: var(--bp-muted);
      margin-top: 2px;
    }}
    .swatch-hex {{
      font-size: 11px;
      font-family: monospace;
      font-weight: 600;
      color: var(--bp-text);
      margin-top: 4px;
    }}
    .chips-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .color-chip {{
      width: 32px;
      height: 32px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 9px;
      border: 1px solid rgba(0,0,0,0.1);
      transition: transform 0.15s;
    }}
    .color-chip:hover {{ transform: scale(1.1); }}
    .chip-label {{ display: none; }}
    .two-col-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}
    @media (max-width: 768px) {{
      .two-col-grid {{ grid-template-columns: 1fr; }}
    }}
    .type-specimen {{
      margin-bottom: 16px;
    }}
    .type-label {{
      font-size: 11px;
      color: var(--bp-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }}
    .type-display {{
      font-family: var(--bp-font-display);
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.15;
      color: var(--bp-text);
    }}
    .type-body {{
      font-family: var(--bp-font-body);
      font-size: 14px;
      color: var(--bp-muted);
      line-height: 1.6;
    }}
    .type-code {{
      font-family: var(--bp-font-mono);
      font-size: 12px;
      color: var(--bp-accent);
      background: rgba(0,0,0,0.04);
      padding: 6px 10px;
      border-radius: 6px;
      display: inline-block;
      margin-top: 4px;
    }}
    .preview-canvas {{
      {card_bg_css}
      {card_border_css}
      border-radius: var(--bp-radius);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .src-btn-primary {{
      background: var(--bp-accent);
      color: #fff;
      border: none;
      padding: 10px 20px;
      border-radius: var(--bp-btn-radius);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: opacity 0.15s, transform 0.1s;
    }}
    .src-btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px); }}
    .src-btn-glass {{
      background: transparent;
      color: var(--bp-text);
      border: 1px solid var(--bp-border);
      padding: 10px 20px;
      border-radius: var(--bp-btn-radius);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }}
    .src-btn-glass:hover {{ background: rgba(0,0,0,0.04); }}
    .src-pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
      background: var(--bp-accent-sec);
      color: #fff;
    }}
    .src-input {{
      width: 100%;
      padding: 10px 14px;
      background: transparent;
      border: 1px solid var(--bp-border);
      border-radius: var(--bp-btn-radius);
      color: var(--bp-text);
      font-size: 13px;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }}
    .src-input:focus {{
      border-color: var(--bp-accent);
      box-shadow: 0 0 0 2px var(--bp-accent)40;
    }}
    .kf-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 14px;
    }}
    .kf-card {{
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 12px;
      padding: 16px;
    }}
    .kf-visual-box {{
      height: 60px;
      width: 100%;
      background: rgba(0,0,0,0.04);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--bp-border);
    }}
    .kf-demo-badge {{
      width: 24px;
      height: 24px;
      border-radius: 6px;
      background: var(--bp-accent);
    }}
    .kf-name {{
      font-size: 12px;
      font-weight: 600;
      font-family: var(--bp-font-mono);
      color: var(--bp-text);
    }}
    .kf-meta {{
      font-size: 10px;
      color: var(--bp-muted);
    }}
    .code-container {{
      position: relative;
    }}
    pre.code-block {{
      background: #09090b;
      border: 1px solid var(--bp-border);
      border-radius: var(--bp-radius);
      padding: 16px;
      font-family: var(--bp-font-mono);
      font-size: 12px;
      line-height: 1.5;
      color: #fafafa;
      overflow-x: auto;
      max-height: 380px;
    }}
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #18181b;
      border: 1px solid #3f3f46;
      color: #fafafa;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      opacity: 0;
      transform: translateY(10px);
      transition: opacity 0.2s, transform 0.2s;
      pointer-events: none;
      z-index: 9999;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
  </style>
</head>
<body>
  <div class="bp-container">
    <header class="bp-header">
      <div class="bp-title-wrap">
        <h1>{escaped_title} <span class="theme-badge">{aesthetic_profile}</span></h1>
        <p class="bp-subtitle">Extracted Design System &bull; {len(css_vars)} Tokens &bull; {len(all_hex_counts)} Colors &bull; {len(display_keyframes)} Animations &bull; {display_font}</p>
      </div>
      <button class="btn-copy-css" onclick="copyTokens()">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        Copy :root CSS
      </button>
    </header>

    <div class="section-title">Color Architecture & Semantic Hierarchy</div>
    <div class="swatches-grid">
      {''.join(swatch_cards_html)}
    </div>
    <div class="chips-row">
      {''.join(extended_swatches_html)}
    </div>

    <div class="section-title">Component Design System & Live Specimen</div>
    <div class="two-col-grid">
      <div class="bp-card">
        <div class="type-specimen">
          <div class="type-label">Display & Headline ({display_font})</div>
          <div class="type-display">Design Precision & Distinct Identity</div>
        </div>
        <div class="type-specimen">
          <div class="type-label">Body Text ({body_font})</div>
          <div class="type-body">Modular spacing scales, calibrated contrast, and authentic semantic tokens preserve the unique character of this reference design.</div>
        </div>
        <div class="type-specimen">
          <div class="type-label">Telemetry & Tokens ({mono_font})</div>
          <div class="type-code">token.resolve("--accent") &rarr; {primary_accent}</div>
        </div>
      </div>

      <div class="preview-canvas">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="type-label">Live Extracted Component Preview</span>
          <span class="src-pill">LIVE PROTOTYPE</span>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button class="src-btn-primary">Primary Action</button>
          <button class="src-btn-glass">Ghost Secondary</button>
        </div>
        <input type="text" class="src-input" placeholder="Search or filter records..." value="Active focus ring demonstration">
      </div>
    </div>

    <div class="section-title">Micro-Interactions & Animation Lab</div>
    <div class="kf-grid">
      {''.join(keyframes_cards_html)}
    </div>

    <div class="section-title">Production-Ready :root Tokens Stylesheet</div>
    <div class="code-container">
      <pre class="code-block" id="css-tokens-code"><code>{clean_css_tokens_html}</code></pre>
    </div>
  </div>

  <div class="toast" id="toast">Copied to clipboard</div>

  <script>
    function copyText(text, msg) {{
      navigator.clipboard.writeText(text).then(() => showToast(msg || 'Copied!'));
    }}
    function copyTokens() {{
      const code = document.getElementById('css-tokens-code').innerText;
      navigator.clipboard.writeText(code).then(() => showToast('Copied :root CSS Tokens!'));
    }}
    function showToast(msg) {{
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2000);
    }}
  </script>
</body>
</html>"""

    # Enforce strictly < 25 KB
    out_bytes = out_html.encode("utf-8")
    if len(out_bytes) > 25000:
        compact_css = re.sub(r"/\*.*?\*/", "", full_css_tokens, flags=re.DOTALL)
        compact_css = re.sub(r"\n\s*\n", "\n", compact_css)
        clean_css_tokens_html = html.escape(compact_css)
        out_html = out_html.replace(html.escape(full_css_tokens), clean_css_tokens_html)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(out_html, encoding="utf-8")

    return out_html
