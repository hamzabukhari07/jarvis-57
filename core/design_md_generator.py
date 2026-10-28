"""Design Markdown Generator for ZEZO Design System.

Converts extracted DesignTokens into studio-grade <design-context> DESIGN.md specifications
using the YAML Design Token DSL and architectural narrative format.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from core.design_tokens import ColorTokens, ComponentToken, DesignTokens, TypeToken


def _adjust_color(hex_str: str, factor: float) -> str:
    """Adjust brightness of hex color. factor > 0 lightens, factor < 0 darkens."""
    try:
        hex_clean = hex_str.lstrip("#")
        if len(hex_clean) == 3:
            hex_clean = "".join(c * 2 for c in hex_clean)
        if len(hex_clean) != 6:
            return hex_str
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
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
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_str


def _has_font(fonts: list[str], names: list[str]) -> bool:
    """Detect presence of font name via word-boundary regex (not naive substring)."""
    return any(any(re.search(rf"\b{re.escape(n)}\b", f, re.I) for n in names) for f in fonts)


def _detect_aesthetic_profile(tokens: DesignTokens) -> str:
    """Detect aesthetic profile using font word-boundary regex and tokens."""
    fonts = list(tokens.fonts) if tokens.fonts else []
    if tokens.display_font and tokens.display_font not in fonts:
        fonts.append(tokens.display_font)
    if tokens.body_font and tokens.body_font not in fonts:
        fonts.append(tokens.body_font)

    scrapbook_fonts = [
        "Caveat", "Bradley Hand", "Kalam", "Shadows Into Light",
        "Patrick Hand", "Architects Daughter", "Gochi Hand", "Permanent Marker"
    ]
    if _has_font(fonts, scrapbook_fonts):
        return "Creative Scrapbook & Visual Narrative"

    if any("serif" in f.lower() and "sans" not in f.lower() for f in fonts):
        return "Refined Editorial & Classic Typography"

    saas_fonts = [
        "Inter", "Plus Jakarta Sans", "Outfit", "Geist",
        "DM Sans", "Manrope", "Satoshi", "General Sans", "Space Grotesk"
    ]
    if _has_font(fonts, saas_fonts):
        return "Modern SaaS & High-Precision System"

    theme = (tokens.theme or "light").lower()
    if theme == "dark":
        return "Dark Minimalist & High-Precision Void"
    return "Minimalist Monochromatic & Clean System"


def _build_description(tokens: DesignTokens, name: str, aesthetic_profile: str) -> str:
    """Build narrative description string for YAML frontmatter."""
    theme = (tokens.theme or "light").lower()
    canvas = tokens.colors.canvas or "#ffffff"
    ink = tokens.colors.ink or "#000000"
    primary = getattr(tokens.colors, "primary", "") or tokens.colors.primary_accent
    border = tokens.colors.border
    display_font = tokens.display_font or "system-ui"

    desc = f"An architectural interpretation of {name} — a design system rooted in {aesthetic_profile}. Master canvas sits on {canvas} ({theme} mode), high-contrast ink text in {ink}"
    extras = []
    if primary:
        extras.append(f"supported by dynamic {primary} accents")
    if border:
        extras.append(f"calibrated {border} borders")
    if display_font:
        extras.append(f"and {display_font} typography")

    if extras:
        desc += ", " + ", ".join(extras) + "."
    else:
        desc += "."
    return desc


def generate_design_md(
    tokens: DesignTokens,
    name: str,
    output_path: Optional[str | Path] = None,
) -> str:
    """
    Generates complete <design-context> DESIGN.md specification from extracted DesignTokens.
    Strictly adheres to:
    - YAML Design Token DSL + architectural narrative format
    - Quoted YAML strings via json.dumps()
    - Never emits empty/missing keys
    - Never emits hardcoded Vercel inventory or brand colors
    """
    slug_name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower() or "design-system"
    aesthetic_profile = _detect_aesthetic_profile(tokens)
    theme = (tokens.theme or "light").lower()
    colors = tokens.colors or ColorTokens()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Frontmatter: Name & Description
    # ─────────────────────────────────────────────────────────────────────────
    name_yaml_val = json.dumps(f"{slug_name}-design-analysis")
    desc_text = _build_description(tokens, name, aesthetic_profile)
    desc_yaml_val = json.dumps(desc_text)

    yaml_blocks: list[str] = [
        "---",
        "version: alpha",
        f"name: {name_yaml_val}",
        f"description: {desc_yaml_val}",
        "",
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Colors YAML Section
    # ─────────────────────────────────────────────────────────────────────────
    primary_val = getattr(colors, "primary", "") or colors.primary_accent
    color_candidates = [
        ("primary", primary_val),
        ("on-primary", colors.on_primary),
        ("ink", colors.ink),
        ("body", colors.body),
        ("muted", colors.muted),
        ("border", colors.border),
        ("border-strong", colors.border_strong),
        ("canvas", colors.canvas),
        ("surface", colors.surface),
        ("surface-2", colors.surface_2),
        ("link", colors.link),
        ("link-deep", colors.link_deep),
        ("link-soft", colors.link_soft),
        ("selection-bg", getattr(colors, "selection_bg", "")),
        ("selection-fg", getattr(colors, "selection_fg", "")),
    ]
    if getattr(colors, "secondary_accent", ""):
        color_candidates.append(("secondary", colors.secondary_accent))

    emitted_colors: dict[str, str] = {}
    color_yaml_lines: list[str] = ["colors:"]

    for key, val in color_candidates:
        if val and str(val).strip():
            clean_v = str(val).strip()
            color_yaml_lines.append(f'  {key}: "{clean_v}"')
            emitted_colors[key] = clean_v

    # Semantic Colors: emit ONLY if family exists in tokens.colors.semantic
    semantic = colors.semantic if isinstance(colors.semantic, dict) else {}
    emitted_semantics: dict[str, dict[str, str]] = {}
    for fam in ("success", "error", "warning", "info"):
        if fam in semantic and semantic[fam]:
            base_val = str(semantic[fam]).strip()
            soft_val = semantic.get(f"{fam}-soft") or semantic.get(f"{fam}_soft")
            if not soft_val:
                soft_val = _adjust_color(base_val, 0.75 if theme == "light" else -0.6)
            else:
                soft_val = str(soft_val).strip()

            deep_val = semantic.get(f"{fam}-deep") or semantic.get(f"{fam}_deep")
            if not deep_val:
                deep_val = _adjust_color(base_val, -0.2 if theme == "light" else 0.2)
            else:
                deep_val = str(deep_val).strip()

            color_yaml_lines.append(f'  {fam}: "{base_val}"')
            color_yaml_lines.append(f'  {fam}-soft: "{soft_val}"')
            color_yaml_lines.append(f'  {fam}-deep: "{deep_val}"')

            emitted_colors[fam] = base_val
            emitted_colors[f"{fam}-soft"] = soft_val
            emitted_colors[f"{fam}-deep"] = deep_val
            emitted_semantics[fam] = {
                "base": base_val,
                "soft": soft_val,
                "deep": deep_val,
            }

    # Gradients: emit ONLY for gradients in tokens.colors.gradients
    gradients = colors.gradients if isinstance(colors.gradients, list) else []
    emitted_gradients: list[tuple[str, str]] = []
    for idx, grad in enumerate(gradients[:3], 1):
        if isinstance(grad, (tuple, list)) and len(grad) >= 2:
            start_stop, end_stop = str(grad[0]).strip(), str(grad[1]).strip()
            if start_stop and end_stop:
                color_yaml_lines.append(f'  gradient-{idx}-start: "{start_stop}"')
                color_yaml_lines.append(f'  gradient-{idx}-end: "{end_stop}"')
                emitted_colors[f"gradient-{idx}-start"] = start_stop
                emitted_colors[f"gradient-{idx}-end"] = end_stop
                emitted_gradients.append((start_stop, end_stop))

    yaml_blocks.append("\n".join(color_yaml_lines))
    yaml_blocks.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Typography YAML Section
    # ─────────────────────────────────────────────────────────────────────────
    display_stack = f"{tokens.display_font}, Inter, system-ui, -apple-system, sans-serif" if tokens.display_font else "Inter, system-ui, -apple-system, sans-serif"
    body_stack = f"{tokens.body_font}, Inter, system-ui, -apple-system, sans-serif" if tokens.body_font else "Inter, system-ui, -apple-system, sans-serif"
    mono_stack = f"{tokens.mono_font}, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace" if tokens.mono_font else "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"

    typography_yaml_lines: list[str] = ["typography:"]
    populated_typography: dict[str, dict[str, str]] = {}

    STANDARD_TYPOGRAPHY_DEFAULTS = [
        ("display-xl", "3rem", "700", "1.1", "-0.02em", display_stack),
        ("display-lg", "2.25rem", "700", "1.15", "-0.015em", display_stack),
        ("display-md", "1.875rem", "600", "1.2", "-0.01em", display_stack),
        ("display-sm", "1.5rem", "600", "1.25", "0px", display_stack),
        ("body-lg", "1.125rem", "400", "1.5", "0px", body_stack),
        ("body-md", "1rem", "400", "1.5", "0px", body_stack),
        ("body-md-strong", "1rem", "600", "1.5", "0px", body_stack),
        ("body-sm", "0.875rem", "400", "1.4", "0px", body_stack),
        ("caption-mono", "0.75rem", "400", "1.4", "0.05em", mono_stack),
        ("code", "0.875rem", "400", "1.4", "0px", mono_stack),
    ]

    raw_typo = tokens.typography if (tokens.typography and isinstance(tokens.typography, dict)) else {}
    for bucket_name, type_tok in raw_typo.items():
        font_size = getattr(type_tok, "font_size", "") or (type_tok.get("font_size") if isinstance(type_tok, dict) else "")
        if not font_size:
            continue

        font_weight = getattr(type_tok, "font_weight", "") or (type_tok.get("font_weight") if isinstance(type_tok, dict) else "400")
        line_height = getattr(type_tok, "line_height", "") or (type_tok.get("line_height") if isinstance(type_tok, dict) else str(font_size))
        letter_spacing = getattr(type_tok, "letter_spacing", "") or (type_tok.get("letter_spacing") if isinstance(type_tok, dict) else "0px")

        b_lower = bucket_name.lower()
        if b_lower in ("caption-mono", "code") or "mono" in b_lower:
            stack = mono_stack
        elif b_lower.startswith("display") or b_lower.startswith("heading") or b_lower.startswith("title"):
            stack = display_stack
        else:
            stack = body_stack

        typography_yaml_lines.append(f"  {bucket_name}:")
        typography_yaml_lines.append(f'    fontFamily: "{stack}"')
        typography_yaml_lines.append(f"    fontSize: {font_size}")
        typography_yaml_lines.append(f"    fontWeight: {font_weight}")
        typography_yaml_lines.append(f"    lineHeight: {line_height}")
        if letter_spacing:
            typography_yaml_lines.append(f"    letterSpacing: {letter_spacing}")

        populated_typography[bucket_name] = {
            "fontFamily": stack,
            "fontSize": str(font_size),
            "fontWeight": str(font_weight),
            "lineHeight": str(line_height),
            "letterSpacing": str(letter_spacing),
        }

    # Fill missing standard scales
    for std_name, std_size, std_weight, std_lh, std_ls, std_stack in STANDARD_TYPOGRAPHY_DEFAULTS:
        if std_name not in populated_typography:
            typography_yaml_lines.append(f"  {std_name}:")
            typography_yaml_lines.append(f'    fontFamily: "{std_stack}"')
            typography_yaml_lines.append(f"    fontSize: {std_size}")
            typography_yaml_lines.append(f"    fontWeight: {std_weight}")
            typography_yaml_lines.append(f"    lineHeight: {std_lh}")
            if std_ls:
                typography_yaml_lines.append(f"    letterSpacing: {std_ls}")

            populated_typography[std_name] = {
                "fontFamily": std_stack,
                "fontSize": std_size,
                "fontWeight": std_weight,
                "lineHeight": std_lh,
                "letterSpacing": std_ls,
            }

    yaml_blocks.append("\n".join(typography_yaml_lines))
    yaml_blocks.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Rounded YAML Section
    # ─────────────────────────────────────────────────────────────────────────
    rounded_yaml_lines: list[str] = [
        "rounded:",
        "  none: 0px",
    ]
    emitted_radii: list[tuple[str, str]] = [("none", "0px")]

    has_full = False
    numeric_radii: list[tuple[float, str]] = []
    raw_radii = tokens.radii if isinstance(tokens.radii, list) else []

    for r in raw_radii:
        r_str = str(r).strip().lower()
        if r_str in ("full", "9999px", "99999px"):
            has_full = True
            continue
        m = re.search(r"^(\d+(?:\.\d+)?)\s*(?:px)?$", r_str)
        if m:
            val = float(m.group(1))
            if 0 < val < 9000:
                fmt_val = f"{int(val) if val.is_integer() else val}px"
                numeric_radii.append((val, fmt_val))

    seen_vals: set[float] = set()
    unique_radii: list[str] = []
    for val, val_str in sorted(numeric_radii, key=lambda x: x[0]):
        if val not in seen_vals:
            seen_vals.add(val)
            unique_radii.append(val_str)

    n_r = len(unique_radii)
    if n_r == 1:
        named_radii = [("md", unique_radii[0])]
    elif n_r == 2:
        named_radii = [("sm", unique_radii[0]), ("lg", unique_radii[1])]
    elif n_r == 3:
        named_radii = [("sm", unique_radii[0]), ("md", unique_radii[1]), ("lg", unique_radii[2])]
    elif n_r == 4:
        named_radii = [("xs", unique_radii[0]), ("sm", unique_radii[1]), ("md", unique_radii[2]), ("lg", unique_radii[3])]
    elif n_r == 5:
        named_radii = [("xs", unique_radii[0]), ("sm", unique_radii[1]), ("md", unique_radii[2]), ("lg", unique_radii[3]), ("xl", unique_radii[4])]
    elif n_r >= 6:
        named_radii = [
            ("xs", unique_radii[0]),
            ("sm", unique_radii[1]),
            ("md", unique_radii[2]),
            ("lg", unique_radii[3]),
            ("xl", unique_radii[-2]),
            ("2xl", unique_radii[-1]),
        ]
    else:
        named_radii = []

    for name_r, val_r in named_radii:
        rounded_yaml_lines.append(f"  {name_r}: {val_r}")
        emitted_radii.append((name_r, val_r))

    if has_full:
        rounded_yaml_lines.append("  full: 9999px  # NOTE: 9999px is a universal CSS idiom for fully-rounded")
        emitted_radii.append(("full", "9999px"))

    yaml_blocks.append("\n".join(rounded_yaml_lines))
    yaml_blocks.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Spacing YAML Section
    # ─────────────────────────────────────────────────────────────────────────
    spacing_yaml_lines: list[str] = ["spacing:"]
    SPACING_MAP = [
        ("xxs", 2),
        ("xs", 4),
        ("sm", 8),
        ("md", 12),
        ("lg", 16),
        ("xl", 24),
        ("2xl", 32),
        ("3xl", 40),
        ("4xl", 48),
        ("5xl", 64),
        ("6xl", 96),
    ]
    raw_spacing = tokens.spacing if isinstance(tokens.spacing, list) else []
    spacing_set = set(raw_spacing)
    found_spacing = False
    emitted_spacings: list[tuple[str, int]] = []

    for sp_name, sp_val in SPACING_MAP:
        if sp_val in spacing_set:
            spacing_yaml_lines.append(f"  {sp_name}: {sp_val}px")
            emitted_spacings.append((sp_name, sp_val))
            found_spacing = True

    if 192 in spacing_set:
        spacing_yaml_lines.append("  section: 192px")
        emitted_spacings.append(("section", 192))
        found_spacing = True
    elif 128 in spacing_set:
        spacing_yaml_lines.append("  section: 128px")
        emitted_spacings.append(("section", 128))
        found_spacing = True

    if not found_spacing:
        spacing_yaml_lines.append("  base: 4px  # NOTE: 4px base rhythm assumed")

    yaml_blocks.append("\n".join(spacing_yaml_lines))
    yaml_blocks.append("")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Components YAML Section
    # ─────────────────────────────────────────────────────────────────────────
    components_yaml_lines: list[str] = ["components:"]
    raw_components = tokens.components if isinstance(tokens.components, list) else []

    if not raw_components:
        components_yaml_lines.append("  # NOTE: no component classes were detected in the source.")
    else:
        for comp in raw_components[:30]:
            c_name = getattr(comp, "name", "") or ""
            clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "-", c_name).strip("-") or "component"
            kind = getattr(comp, "kind", "generic") or "generic"
            props = getattr(comp, "properties", {}) if isinstance(getattr(comp, "properties", {}), dict) else {}

            bg = props.get("background-color") or props.get("background") or "transparent"
            color = props.get("color") or "{colors.ink}"
            border_color = props.get("border-color") or props.get("border")
            rounded = props.get("border-radius") or "{rounded.md}"
            padding = props.get("padding") or props.get("padding-inline") or "{spacing.md}"

            components_yaml_lines.append(f"  {clean_name}:")
            components_yaml_lines.append(f"    # kind: {kind}")
            components_yaml_lines.append(f'    backgroundColor: "{bg}"')
            components_yaml_lines.append(f'    textColor: "{color}"')
            if border_color:
                components_yaml_lines.append(f'    borderColor: "{border_color}"')
            components_yaml_lines.append(f'    rounded: "{rounded}"')
            components_yaml_lines.append(f'    padding: "{padding}"')
            if "height" in props:
                components_yaml_lines.append(f'    height: "{props["height"]}"')

    yaml_blocks.append("\n".join(components_yaml_lines))
    yaml_blocks.append("---")
    yaml_content = "\n".join(yaml_blocks)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Body Markdown Sections
    # ─────────────────────────────────────────────────────────────────────────
    md_lines: list[str] = [
        "<design-context>",
        yaml_content,
        "",
        "## Overview",
        "",
        f"{name} is an architectural design system — a crafted design language whose surface is built on `{emitted_colors.get('canvas', '#ffffff')}` ({theme} mode) paired with `{emitted_colors.get('ink', '#000000')}` ink typography.",
    ]

    overview_second_sentence_parts = []
    if primary_val:
        overview_second_sentence_parts.append(f"`{primary_val}` as the decisive brand accent")
    if emitted_colors.get("border"):
        overview_second_sentence_parts.append(f"subtle `{emitted_colors['border']}` borders")
    if tokens.display_font:
        overview_second_sentence_parts.append(f"{tokens.display_font} typography")

    if overview_second_sentence_parts:
        md_lines.append(f"The interface introduces {', supported by '.join(overview_second_sentence_parts)}.")

    md_lines.extend([
        "",
        "## Colors",
        "",
        "### Brand & Accent",
    ])

    if primary_val:
        md_lines.append(f"- **Primary CTA / Ink** (`{{{{colors.primary}}}}` — `{primary_val}`): The main conversion CTA color and high-contrast anchor.")
    if emitted_colors.get("link"):
        md_lines.append(f"- **Link / Interactive** (`{{{{colors.link}}}}` — `{emitted_colors['link']}`): Interactive link and focus state accent.")
    if emitted_colors.get("secondary"):
        md_lines.append(f"- **Secondary Accent** (`{{{{colors.secondary}}}}` — `{emitted_colors['secondary']}`): Complementary accent for secondary highlights.")

    md_lines.extend([
        "",
        "### Surface",
    ])
    if emitted_colors.get("canvas"):
        md_lines.append(f"- **Canvas** (`{{{{colors.canvas}}}}` — `{emitted_colors['canvas']}`): Base page background canvas.")
    if emitted_colors.get("surface"):
        md_lines.append(f"- **Surface** (`{{{{colors.surface}}}}` — `{emitted_colors['surface']}`): Elevated card and panel surfaces.")
    if emitted_colors.get("surface-2"):
        md_lines.append(f"- **Surface 2** (`{{{{colors.surface-2}}}}` — `{emitted_colors['surface-2']}`): Inset regions and secondary surface layers.")
    if emitted_colors.get("border"):
        md_lines.append(f"- **Border** (`{{{{colors.border}}}}` — `{emitted_colors['border']}`): Structural container divider and hairline rule.")
    if emitted_colors.get("border-strong"):
        md_lines.append(f"- **Border Strong** (`{{{{colors.border-strong}}}}` — `{emitted_colors['border-strong']}`): Emphasized border and prominent divider.")

    md_lines.extend([
        "",
        "### Text",
    ])
    if emitted_colors.get("ink"):
        md_lines.append(f"- **Ink** (`{{{{colors.ink}}}}` — `{emitted_colors['ink']}`): Primary titles, headings, and high-contrast text.")
    if emitted_colors.get("body"):
        md_lines.append(f"- **Body** (`{{{{colors.body}}}}` — `{emitted_colors['body']}`): Secondary narrative, subtitles, and descriptive paragraphs.")
    if emitted_colors.get("muted"):
        md_lines.append(f"- **Muted** (`{{{{colors.muted}}}}` — `{emitted_colors['muted']}`): Subtle helper labels, timestamps, and fine print.")
    if emitted_colors.get("on-primary"):
        md_lines.append(f"- **On Primary** (`{{{{colors.on-primary}}}}` — `{emitted_colors['on-primary']}`): High-contrast inverted text on primary surfaces.")

    # Semantic Narrative: ONLY if semantic family exists
    if emitted_semantics:
        md_lines.extend([
            "",
            "### Semantic",
        ])
        if "success" in emitted_semantics:
            md_lines.append(f"- **Success** (`{{{{colors.success}}}}` — `{emitted_semantics['success']['base']}`): Positive states and verified confirmations.")
        if "error" in emitted_semantics:
            md_lines.append(f"- **Error** (`{{{{colors.error}}}}` — `{emitted_semantics['error']['base']}`): Destructive actions and form validation alerts.")
        if "warning" in emitted_semantics:
            md_lines.append(f"- **Warning** (`{{{{colors.warning}}}}` — `{emitted_semantics['warning']['base']}`): Cautionary status and pending indicators.")
        if "info" in emitted_semantics:
            md_lines.append(f"- **Info** (`{{{{colors.info}}}}` — `{emitted_semantics['info']['base']}`): Informational alerts and system notices.")

    # Brand Gradient Narrative: ONLY if gradients exist
    if emitted_gradients:
        md_lines.extend([
            "",
            "### Brand Gradient",
            "The brand signature gradient flow:",
        ])
        for idx, (g_start, g_end) in enumerate(emitted_gradients, 1):
            md_lines.append(f"- `{{{{colors.gradient-{idx}-start}}}}` ({g_start}) → `{{{{colors.gradient-{idx}-end}}}}` ({g_end})")

    # ─────────────────────────────────────────────────────────────────────────
    # Typography Narrative
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Typography",
        "",
        "### Font Family",
        f"- **Display / Headings**: {display_stack}",
        f"- **Body / Narrative**: {body_stack}",
        f"- **Technical / Monospace**: {mono_stack}",
    ])

    if populated_typography:
        md_lines.extend([
            "",
            "### Hierarchy",
            "",
            "| Token | Size | Weight | Line Height | Letter Spacing | Use |",
            "|---|---|---|---|---|---|",
        ])
        use_descriptions = {
            "display-xl": "Hero main headline.",
            "display-lg": "Major section titles.",
            "display-md": "Card cluster titles, modal headers.",
            "display-sm": "Sub-section micro-headings.",
            "body-lg": "Lead introductory paragraphs.",
            "body-md": "Default body copy.",
            "body-md-strong": "Bolded inline body emphasis.",
            "body-sm": "Secondary body, nav links, compact cards.",
            "body-sm-strong": "Navigation CTA labels, table headers.",
            "caption": "Meta tags, badge labels, fine print.",
            "caption-mono": "Technical metadata and category tags.",
            "code": "Code snippets, terminal commands.",
            "button-md": "Compact button labels.",
            "button-lg": "Large marketing CTA labels.",
        }
        for bucket_name, info in populated_typography.items():
            use_text = use_descriptions.get(bucket_name, f"{bucket_name.replace('-', ' ').title()} copy.")
            md_lines.append(
                f"| `{{{{typography.{bucket_name}}}}}` | {info['fontSize']} | {info['fontWeight']} | {info['lineHeight']} | {info['letterSpacing']} | {use_text} |"
            )

    md_lines.extend([
        "",
        "### Principles",
        "- **Negative tracking on display titles**: Refined tracking for editorial poise.",
        "- **Technical separation**: Monospaced face reserved exclusively for technical labels, code, and data metrics.",
        "- **Calibrated hierarchy**: Clear typographic scale establishing effortless visual hierarchy.",
    ])

    # Note on Font Substitutes: ONLY if tokens.display_font not in standard fallbacks
    disp_font = (tokens.display_font or "").strip()
    if disp_font and disp_font not in ("Inter", "system-ui", "Arial", "Helvetica"):
        md_lines.extend([
            "",
            "### Note on Font Substitutes",
            f"- If {disp_font} is not locally available, system fallbacks provide instant graceful degradation: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.",
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # Layout Narrative
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Layout",
        "",
        "### Spacing System",
    ])
    if emitted_spacings:
        sp_summary = " · ".join(f"`{{{{spacing.{name}}}}}` ({val}px)" for name, val in emitted_spacings)
        md_lines.append(f"- Spacing tokens: {sp_summary}")
    else:
        md_lines.append("- Spacing tokens: `base` (4px modular rhythm assumed).")

    md_lines.extend([
        "- Container lateral rhythm: `16px` to `24px` standard gutters.",
        "",
        "### Grid & Container",
        "- Max container width: `1280px` / `1400px` centered with lateral gutters.",
        "- Standard grid: Multi-column responsive layout collapsing to single column on mobile.",
        "",
        "### Responsive Strategy",
        "",
        "| Name | Width | Key Changes |",
        "|---|---|---|",
        "| Mobile | < 600px | 1-column vertical stack, mobile navigation sheet. |",
        "| Tablet | 600–959px | 2-column grid adaptation, compact padding. |",
        "| Desktop | 960–1199px | Full multi-column grid layouts. |",
        "| Wide | ≥ 1200px | Max container width constraint with centered margins. |",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # Elevation & Depth
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Elevation & Depth",
        "",
        "| Level | Treatment | Use |",
        "|---|---|---|",
        "| Level 0 — Flat | No shadow, 1px hairline border. | Base canvas panels and full-bleed bands. |",
        "| Level 1 — Inset Hairline | Inset border rule. | Standard cards and content modules. |",
        "| Level 2 — Subtle Drop | `0px 1px 2px rgba(0,0,0,0.05)` + border. | Elevated interactive cards. |",
        "| Level 3 — Soft Stack | `0px 4px 12px -2px rgba(0,0,0,0.08)` + border. | Feature cards and active containers. |",
        "| Level 4 — Float Stack | `0px 8px 24px -4px rgba(0,0,0,0.12)` + border. | Pricing tiers and prominent popovers. |",
        "| Level 5 — Modal | `0px 16px 40px -8px rgba(0,0,0,0.20)` + border. | Modal dialogs and central overlays. |",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # Shapes
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Shapes",
        "",
        "### Border Radius Scale",
        "",
        "| Token | Value | Use |",
        "|---|---|---|",
    ])
    radius_use_descriptions = {
        "none": "Full-bleed hero and footer bands.",
        "xs": "Micro badges and code tags.",
        "sm": "Form input controls and small badges.",
        "md": "Primary buttons and interactive chips.",
        "lg": "Standard cards and containers.",
        "xl": "Prominent hero panels and modals.",
        "2xl": "Large modal cards and containers.",
        "full": "Circular icon buttons and pill badges.",
    }
    for name_r, val_r in emitted_radii:
        r_desc = radius_use_descriptions.get(name_r, f"{name_r.title()} shape container.")
        md_lines.append(f"| `{{{{rounded.{name_r}}}}}` | {val_r} | {r_desc} |")

    # ─────────────────────────────────────────────────────────────────────────
    # Components Narrative
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Components",
    ])

    if not raw_components:
        md_lines.extend([
            "",
            "*No component classes were detected in the source.*",
        ])
    else:
        # Group by kind
        grouped_comps: dict[str, list[ComponentToken]] = {}
        for comp in raw_components[:30]:
            k = getattr(comp, "kind", "generic") or "generic"
            grouped_comps.setdefault(k, []).append(comp)

        for kind_name, comp_list in grouped_comps.items():
            md_lines.extend([
                "",
                f"### {kind_name.title()} Components",
            ])
            for comp in comp_list:
                c_name = getattr(comp, "name", "")
                props = getattr(comp, "properties", {}) if isinstance(getattr(comp, "properties", {}), dict) else {}
                desc_tokens = []
                bg = props.get("background-color") or props.get("background")
                if bg:
                    desc_tokens.append(f"bg: `{bg}`")
                fg = props.get("color")
                if fg:
                    desc_tokens.append(f"color: `{fg}`")
                bd = props.get("border-color") or props.get("border")
                if bd:
                    desc_tokens.append(f"border: `{bd}`")
                br = props.get("border-radius")
                if br:
                    desc_tokens.append(f"radius: `{br}`")
                pd = props.get("padding") or props.get("padding-inline")
                if pd:
                    desc_tokens.append(f"padding: `{pd}`")

                summary = ", ".join(desc_tokens) if desc_tokens else "native styling"
                md_lines.append(f"- **`{c_name}`**: {summary}")

    # ─────────────────────────────────────────────────────────────────────────
    # Do's and Don'ts (Universal rules only, no Vercel-specific items)
    # ─────────────────────────────────────────────────────────────────────────
    md_lines.extend([
        "",
        "## Do's and Don'ts",
        "",
        "### Do",
        f"- Maintain authentic {theme} canvas (`{{{{colors.canvas}}}}`) with clear semantic surface layers.",
        "- Use `{{colors.primary}}` for primary conversion CTAs.",
        "- Apply negative letter-spacing to headings for high-end typographic authority.",
        "- Standardize container padding using modular rhythm tokens.",
        "- Ensure all form controls have custom borders and focus rings.",
        "",
        "### Don't",
        "- Don't leave form inputs unstyled with default browser borders.",
        "- Don't use uppercase typography outside of technical/monospace tags.",
        "- Don't apply single harsh drop-shadows; use multi-level stacked elevation.",
        "",
        "</design-context>",
        "",
    ])

    final_md = "\n".join(md_lines)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(final_md, encoding="utf-8")

    return final_md
