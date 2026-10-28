"""Design tokens data structures for the ZEZO design extraction pipeline.

Pure data classes representing extracted design tokens (colors, typography,
components, spacing, radii, etc.).
"""

from dataclasses import dataclass, field


@dataclass
class ColorTokens:
    canvas: str = ""
    surface: str = ""
    surface_2: str = ""
    ink: str = ""
    body: str = ""
    muted: str = ""
    border: str = ""
    border_strong: str = ""
    primary_accent: str = ""
    secondary_accent: str = ""
    on_primary: str = ""
    link: str = ""
    link_deep: str = ""
    link_soft: str = ""
    semantic: dict = field(default_factory=dict)   # {"success": "#..", "error": "#..", ...}
    gradients: list = field(default_factory=list)  # [("#start", "#end"), ...]
    warnings: list = field(default_factory=list)


@dataclass
class TypeToken:
    font_family: str
    font_size: str
    font_weight: str
    line_height: str
    letter_spacing: str = "0px"


@dataclass
class ComponentToken:
    name: str
    kind: str            # navigation / action / surface / form / badge / scrapbook / section / media / ...
    selector: str
    properties: dict = field(default_factory=dict)


@dataclass
class DesignTokens:
    theme: str = "light"          # "light" | "dark"
    fonts: list = field(default_factory=list)
    display_font: str = ""
    body_font: str = ""
    mono_font: str = ""
    colors: ColorTokens = field(default_factory=ColorTokens)
    typography: dict = field(default_factory=dict)   # {"display-xl": TypeToken, ...}
    spacing: list = field(default_factory=list)      # [4, 8, 12, ...] ints in px
    radii: list = field(default_factory=list)        # ["4px", "8px", ...] str
    card_radius: str = ""
    button_radius: str = ""
    components: list = field(default_factory=list)   # [ComponentToken, ...]
    keyframes: dict = field(default_factory=dict)    # {"name": "body"}
    css_vars: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
