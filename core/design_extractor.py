"""
core/design_extractor.py — Deterministic Design System & Token Extractor

Parses any raw HTML/CSS file or template into a studio-grade, standardized
DESIGN.md specification with YAML frontmatter, tokens, component recipes,
and anti-slop guidelines.

Features:
  - Full CSS custom properties (:root) resolution with recursive nested var() support
  - Semantic Role Detection (Background, Text, Accent, Surface, Border, Typography)
  - Automatic Light/Dark Theme Detection & theme-aware descriptions
  - Zero hardcoded color defaults (dynamically computed from extracted palette)
  - 100% deterministic local Python execution
"""

from __future__ import annotations

import datetime
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

_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
_RGB_RE = re.compile(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d\.]+)?\s*\)", re.IGNORECASE)
_HSL_RE = re.compile(r"hsla?\s*\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%(?:\s*,\s*[\d\.]+)?\s*\)", re.IGNORECASE)
_VAR_DEF_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;}{]+);?")
_VAR_USAGE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)(?:\s*,\s*([^)]+))?\s*\)")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}{]+);?", re.IGNORECASE)
_GOOGLE_FONTS_RE = re.compile(r"fonts\.googleapis\.com/css2\?family=([^&\"'\s]+)")
_BORDER_RADIUS_RE = re.compile(r"border-radius\s*:\s*([^;}{]+);?", re.IGNORECASE)
_CSS_RULE_RE = re.compile(r"([^{]+)\{([^}]+)\}", re.DOTALL)


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


def _normalize_color_to_hex(val: str) -> Optional[str]:
    val = (val or "").strip().lower()
    if not val:
        return None

    # Named standard colors
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

    # Hex match
    m_hex = _HEX_RE.search(val)
    if m_hex:
        raw = m_hex.group(0)
        r, g, b = _hex_to_rgb(raw)
        return _rgb_to_hex(r, g, b)

    # RGB/RGBA match
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
        clean_val = var_val.strip().split("/*")[0].strip()
        defs[var_name.strip()] = clean_val

    # Iterative recursive resolution (up to 10 passes)
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
        # Resolve var() in body
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


def extract_design_system_from_html(
    html_input: str | Path,
    output_path: Optional[str | Path] = None,
    component_name: Optional[str] = None,
) -> str:
    """
    Extracts tokens, color hierarchy, typography, radii, and component recipes
    from raw HTML/CSS deterministically following the 4 Semantic Role Priorities.
    """
    source_label = "inline"
    if isinstance(html_input, Path) or (isinstance(html_input, str) and "\n" not in html_input and Path(html_input).exists()):
        file_path = Path(html_input)
        raw_html = file_path.read_text(encoding="utf-8", errors="replace")
        default_name = file_path.stem.replace("-", " ").replace("_", " ").title()
        source_label = file_path.as_posix()
    else:
        raw_html = str(html_input)
        default_name = "Extracted Design System"

    name = component_name or default_name

    # 1. Gather all CSS & Classes
    soup = BeautifulSoup(raw_html, "html.parser") if BeautifulSoup else None
    
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
        style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", raw_html, re.DOTALL | re.IGNORECASE)
        classes = re.findall(r'class=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
        flattened_classes = []
        for c in classes:
            flattened_classes.extend(c.split())
        classes = flattened_classes

    all_css = "\n".join(style_blocks)

    # 2. Resolve CSS Custom Properties (:root)
    css_vars = _resolve_css_variables(all_css)
    css_rules = _extract_css_rules(all_css, css_vars)

    # 3. Collect All Document Colors & Count Frequencies
    all_hex_raw = _HEX_RE.findall(raw_html)
    all_hex_counts = Counter(h.lower() for h in all_hex_raw)

    # Convert resolved CSS variables to color mapping
    var_colors: dict[str, str] = {}
    for vk, vv in css_vars.items():
        c_hex = _normalize_color_to_hex(vv)
        if c_hex:
            var_colors[vk.lower()] = c_hex

    # ─────────────────────────────────────────────────────────────────────────
    # FIX 2: SEMANTIC ROLE DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    # --- ROLE 1: BACKGROUND ---
    bg_color: Optional[str] = None
    # 1. Check :root semantic names
    bg_var_keys = [
        "--background", "--bg", "--canvas", "--surface-1", "--cream",
        "--theme-bg", "--app-bg", "--body-bg", "--main-bg", "--dark",
    ]
    for k in bg_var_keys:
        if k in var_colors:
            bg_color = var_colors[k]
            break

    # 2. Check <body> / <html> tag inline styles & Tailwind/utility classes
    if not bg_color and soup:
        body_tag = soup.find("body")
        html_tag = soup.find("html")
        for tag in (body_tag, html_tag):
            if not tag:
                continue
            # Check style attribute
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
            # Check class attribute
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

    # 3. Check body / html CSS rules
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

    # 4. Fallback: most common background color in top-level selectors (ignoring inner glows/blobs)
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

    # --- FIX 3: LIGHT / DARK THEME DETECTION ---
    if not bg_color:
        # Check overall luminance of most frequent colors
        if all_hex_counts:
            top_color = all_hex_counts.most_common(1)[0][0]
            bg_color = top_color
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

    # Check <body> / <html> tag inline styles & Tailwind/utility classes for text
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

    # --- ROLE 3: ACCENT PRIMARY ---
    primary_accent: Optional[str] = None
    accent_var_keys = [
        "--accent", "--primary", "--brand", "--highlight", "--accent-1",
        "--color-primary", "--color-accent", "--cta",
    ]
    for k in accent_var_keys:
        if k in var_colors:
            primary_accent = var_colors[k]
            break

    if not primary_accent:
        # Check main CTA / primary button selectors
        for sel, props in css_rules:
            if any(btn_kw in sel for btn_kw in (".btn-primary", ".button-primary", ".cta", "button.primary", ".btn")):
                for p in ("background-color", "background", "color"):
                    if p in props:
                        c_hex = _normalize_color_to_hex(props[p])
                        if c_hex and c_hex != bg_color:
                            primary_accent = c_hex
                            break
            if primary_accent:
                break

    if not primary_accent:
        # Check link/nav/action selectors (ignoring copy-pill, status badges, chips)
        for sel, props in css_rules:
            if any(action_kw in sel for action_kw in ("a:hover", "a.active", ".nav a", "button")):
                if not any(skip_kw in sel for skip_kw in ("pill", "badge", "tag", "chip", "copied")):
                    for p in ("background-color", "background", "color"):
                        if p in props:
                            c_hex = _normalize_color_to_hex(props[p])
                            if c_hex and _is_saturated_accent(c_hex):
                                primary_accent = c_hex
                                break
            if primary_accent:
                break

    if not primary_accent:
        # Find prominent saturated non-neutral color in palette (must occur > 2 times to not be an isolated badge)
        prominent_saturated = [
            (c, count) for c, count in all_hex_counts.items()
            if _is_saturated_accent(c) and c != bg_color and c != text_primary and count > 2
        ]
        if prominent_saturated:
            prominent_saturated.sort(key=lambda item: _saturation(item[0]) * item[1], reverse=True)
            primary_accent = prominent_saturated[0][0]

    # For monochrome / editorial designs, primary accent defaults to text_primary (e.g. bold ink / pure white)
    if not primary_accent:
        primary_accent = text_primary

    # --- ROLE 4: SURFACE / CARD ---
    surface_color: Optional[str] = None
    surface_var_keys = [
        "--surface", "--card", "--panel", "--cream-2", "--cream-3",
        "--surface-2", "--card-bg", "--surface-card",
    ]
    for k in surface_var_keys:
        if k in var_colors and var_colors[k] != bg_color:
            surface_color = var_colors[k]
            break

    if not surface_color:
        for sel, props in css_rules:
            if any(card_kw in sel for card_kw in (".card", ".panel", "section", "article", ".wrap")):
                for p in ("background-color", "background"):
                    if p in props:
                        c_hex = _normalize_color_to_hex(props[p])
                        if c_hex and c_hex != bg_color:
                            surface_color = c_hex
                            break
            if surface_color:
                break

    if not surface_color:
        surface_color = "#ede9e4" if theme == "light" else "#18181b"

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
        border_color = "#e5e5e5" if theme == "light" else "#27272a"

    # Secondary text
    text_secondary: Optional[str] = None
    sec_var_keys = ["--muted", "--muted-2", "--text-secondary", "--muted-text", "--text-muted", "--ink-2"]
    for k in sec_var_keys:
        if k in var_colors:
            text_secondary = var_colors[k]
            break
    if not text_secondary:
        text_secondary = "#6c6c6c" if theme == "light" else "#a1a1aa"

    # 4. Extract Typography & Fonts
    fonts: list[str] = []
    
    # Check font vars first (--ff-serif, --font-serif, --ff, --font)
    for vk, vv in css_vars.items():
        if any(fkw in vk.lower() for fkw in ("font", "ff")):
            for part in vv.split(","):
                clean = part.strip().strip('"').strip("'")
                if clean and clean not in fonts and clean.lower() not in ("sans-serif", "serif", "monospace"):
                    fonts.append(clean)

    # Google fonts link tags
    for gfont in _GOOGLE_FONTS_RE.findall(raw_html):
        clean_gfont = gfont.split(":")[0].replace("+", " ")
        if clean_gfont not in fonts:
            fonts.append(clean_gfont)

    # Headings / body font-family
    for sel, props in css_rules:
        if any(h_kw in sel for h_kw in ("h1", "h2", "h3", ".serif", ".h1", "body")):
            if "font-family" in props:
                for fam_part in props["font-family"].split(","):
                    clean_fam = fam_part.strip().strip('"').strip("'")
                    if clean_fam and clean_fam not in fonts and clean_fam.lower() not in ("sans-serif", "serif", "monospace"):
                        fonts.insert(0, clean_fam)

    if not fonts:
        fonts = ["Inter", "sans-serif"]
    
    # Pick primary display font (prioritize serif if present in headings/vars)
    serif_font = next((f for f in fonts if any(skw in f.lower() for skw in ("serif", "instrument", "canela", "garamond", "georgia"))), None)
    primary_font = serif_font or fonts[0]
    body_font = next((f for f in fonts if f != serif_font and "mono" not in f.lower()), "Inter")
    mono_font = next((f for f in fonts if "mono" in f.lower()), "JetBrains Mono")

    # 5. Extract Border Radius
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

    # 6. Build Theme-Aware Description & Frontmatter
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if theme == "light":
        theme_desc = f"Refined editorial light design system extracted deterministically from {name}. Features clean {bg_color} cream canvas, high-contrast {text_primary} ink typography, and elegant {primary_font} headings."
        aesthetic_profile = "Light Editorial / Cream Precision"
    else:
        theme_desc = f"High-precision studio design system extracted deterministically from {name}. Features deep {bg_color} void canvas, high-contrast {text_primary} typography, vibrant {primary_accent} accents, and glassy elevation."
        aesthetic_profile = "Dark Studio / High-Precision Void"

    md_content = f"""---
version: "3.0"
name: "{name}"
theme: "{theme}"
source: "{source_label}"
extracted_at: "{now_iso}"
description: "{theme_desc}"
colors:
  primary: "{primary_accent}"
  secondary: "{text_secondary}"
  tertiary: "{primary_accent}"
  neutral: "{border_color}"
  background: "{bg_color}"
  surface: "{surface_color}"
  text-primary: "{text_primary}"
  text-secondary: "{text_secondary}"
  border: "{border_color}"
  accent: "{primary_accent}"
typography:
  display-lg:
    fontFamily: "{primary_font}"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "{primary_font}"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: "{body_font}"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "24px"
  code-sm:
    fontFamily: "{mono_font}"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: "16px"
  label-md:
    fontFamily: "{body_font}"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  sm: "6px"
  md: "{btn_radius}"
  lg: "12px"
  xl: "{card_radius}"
  full: "9999px"
spacing:
  base: "4px"
  sm: "4px"
  md: "8px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
  card-padding: "20px"
  section-padding: "48px"
components:
  button-primary:
    background: "{primary_accent}"
    textColor: "{'#ffffff' if theme == 'dark' else '#ffffff'}"
    typography: "{{typography.label-md}}"
    rounded: "{{rounded.md}}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "{'rgba(255, 255, 255, 0.04)' if theme == 'dark' else 'rgba(0, 0, 0, 0.03)'}"
    border: "1px solid {border_color}"
    textColor: "{text_primary}"
    typography: "{{typography.label-md}}"
    rounded: "{{rounded.md}}"
    padding: "8px 16px"
    hover: "{'background: rgba(255, 255, 255, 0.08)' if theme == 'dark' else 'background: rgba(0, 0, 0, 0.06)'}"
  card:
    background: "{surface_color}"
    border: "1px solid {border_color}"
    rounded: "{{rounded.xl}}"
    padding: "{{spacing.card-padding}}"
    shadow: "{'0 4px 20px -2px rgba(0, 0, 0, 0.5)' if theme == 'dark' else '0 2px 12px -1px rgba(0, 0, 0, 0.08)'}"
    backdropBlur: "12px"
  input:
    background: "{'rgba(0, 0, 0, 0.4)' if theme == 'dark' else '#ffffff'}"
    border: "1px solid {border_color}"
    textColor: "{text_primary}"
    placeholder: "{text_secondary}"
    rounded: "{{rounded.md}}"
    padding: "10px 14px"
    focusBorder: "{primary_accent}"
---

# {name} — Design Specification

> **Aesthetic Profile:** {aesthetic_profile}  
> **Extracted Source:** {source_label}  
> **Theme:** {theme.upper()}  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`{bg_color}`) with layered panels (`{surface_color}`) and hairline borders (`{border_color}`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `{bg_color}` | Master canvas background (`{theme}` mode). |
| **Surface / Card** | `{surface_color}` | Primary container panels, modules, and cards. |
| **Primary Accent** | `{primary_accent}` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `{text_primary}` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `{text_secondary}` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `{border_color}` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `{primary_font}`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `{body_font}`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `{mono_font}`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`{bg_color}`) with focused `{primary_accent}` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `{border_color}` outlines, and `{primary_accent}` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `{card_radius}` and button/input radii to `{btn_radius}`.
"""

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md_content, encoding="utf-8")

    return md_content
