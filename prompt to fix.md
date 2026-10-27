Command exited with code 0.

Command output:
# Final Antigravity Prompt - Refactor + Fix `design_extractor.py`

Paste this as a **single prompt** to Antigravity. It does the refactor first (safe), then fixes bugs (in order). One shot.

---

```
TASK: Refactor and fix the ZEZO design extraction pipeline.

You are working in a Python project (ZEZO). Current files:
- core/design_extractor.py  - extraction + MD generation + blueprint generation (ALL MIXED, BROKEN)
- core/design_resolver.py   - selection + HTML sanitization + slot injection + template generation + cache (ALL MIXED, BROKEN)

GOAL: Split responsibilities into focused files, then fix known bugs. Preserve the public API of `core/design_resolver.py` (functions `resolve_design`, `generate_blueprint_and_template`, `format_design_prompt`, `check_greenfield_gate`, `is_ui_task`, `is_redesign_or_explicit_request`, class `ResolvedDesign`) - external callers must not break. Remove `generate_blueprint_html` entirely (plan says blueprint.html is dead).

## PHASE 0 - Create the new file structure

Create these files (empty public API first, then fill in PHASES 1-4):

1. `core/design_tokens.py` - pure data classes only, no logic:
```python
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
```

2. `core/design_extractor.py` - REWRITE to contain ONLY: `strip_base64_images()`, `extract_keyframes()`, `extract_design_tokens() -> DesignTokens`. Delete `generate_design_md`, `generate_blueprint_html`, `_extract_design_metadata`, `_extract_css_rules`, `_resolve_css_variables` (move to correct files below).

3. `core/design_md_generator.py` - NEW file. Contains: `generate_design_md(tokens: DesignTokens, name: str) -> str`. Delete all Vercel hardcoded content.

4. `core/master_template_builder.py` - NEW file. Contains: `build_master_template(raw_html: str, tokens: DesignTokens, max_bytes: int = 40000) -> str`, `inject_semantic_slots(html: str) -> str`.

5. `core/design_resolver.py` - REWRITE to contain ONLY: `ResolvedDesign` dataclass, `resolve_design`, `resolve_from_catalog`, `load_catalog`, `is_ui_task`, `is_redesign_or_explicit_request`, `_infer_scope`, `_infer_theme`, `_normalize_scope`, `_normalize_theme`, `_norm_stem`, `extract_authentic_task`, `format_design_prompt`, `check_greenfield_gate`. Delete: `_sanitize_html_for_prompt`, `inject_semantic_slots`, `generate_master_template_html`, `get_or_create_reference_design_cache`, `generate_blueprint_and_template`, `_load_direct_html_reference` (move cache to `design_cache.py`, move HTML sanitization to extractor).

6. `core/design_cache.py` - NEW file. Contains: `get_or_create_reference_design_cache(reference_path: Path) -> tuple[Path, Path]`, `generate_blueprint_and_template(reference_path, output_dir) -> tuple[Path, Path]` (keep the legacy name - external callers depend on it), plus version-aware invalidation.

7. `core/_self_test.py` - NEW file, runnable with `python -m core._self_test`. Contains the PHASE 5 tests. Do not import it anywhere in production code.

## PHASE 1 - Fix `core/design_extractor.py`

### 1.1 `strip_base64_images`
- Replace `_BASE64_IMAGE_RE` with `r"data:image/[a-zA-Z0-9\+\-\.]+;base64,[A-Za-z0-9+/=]+"` (NO `\s`, NO `\\`, NO lookahead).
- Add `_collapse_base64_whitespace(html)` helper: find each `;base64,` and consume `[A-Za-z0-9+/=\s\\]+` to collapse internal whitespace, then re-emit without whitespace. Call this BEFORE the regex.
- Apply the same fix to the `url(...)` step-6 regex: base64 char class `[A-Za-z0-9+/=]+` only.
- Keep all other steps (script stripping, font-face, link stripping).
- Add `# NOTE:` comment above `DEFAULT_SVG_PLACEHOLDER` explaining its hardcoded zinc colors are intentional placeholder colors, not extracted brand colors.

### 1.2 `_resolve_css_variables` and `_extract_css_rules` (keep as private helpers in extractor)
- Strip `/* ... */` comments from `raw_css` before any scanning.
- Replace `_CSS_RULE_RE`-based parsing with a depth-tracking parser `_parse_css_blocks(css: str) -> list[tuple[str, str]]` returning (prelude, body) pairs at depth 0.
  - At-rule `@media/@supports/@layer/@container`: recurse into body, merge inner rules.
  - At-rule `@font-face/@page/@property`: skip.
  - At-rule `@keyframes`: skip (handled by `extract_keyframes`).
  - Flatten into `list[tuple[str, dict[str, str]]]`.
- Replace `_VAR_USAGE_RE` and all inline `var(...)` substitution with a balanced-paren helper `_find_var_calls(text) -> list[tuple[int, int, str, str|None]]`. Use it in both `_resolve_css_variables` and `_extract_css_rules`.
- In `_resolve_css_variables`, remove the `if any(bad in clean_val for bad in ["{","}","@","hover","active","focus"])` check. Raise `len(clean_val) > 200` guard to `500` and only apply to non-`var()` values. After 10 passes, collect unresolved vars into `unresolved` dict and return `(defs, unresolved)`.

### 1.3 `_normalize_color_to_hex` / `_oklch_to_hex` / `_hsl_to_hex`
- `_hsl_to_hex`: add `h = h % 360` at top.
- Update OKLCH regex to `r"oklch\s*\(\s*([\d\.]+)(%?)\s+([\d\.]+)(%?)\s+(none|[\d\.]+(?:deg|rad|grad|turn)?)(?:\s*/\s*[\d\.]+%?)?\s*\)"`. Handle `%` (L /100, C x0.4), `none` hue  0, and all hue units.
- Move `import math` to module top.
- Add `_relative_luminance(hex) -> float` (WCAG 2.x linearized) and `_contrast_ratio(a, b) -> float` and `_best_foreground(bg_hex) -> str` helpers. Use `_best_foreground` everywhere `on_primary` / `selection_fg` / button-text-vs-bg is decided.

### 1.4 `extract_keyframes`
- Strip `/* ... */` comments before brace balancing.
- Track `in_single`, `in_double`, `escape_next` in the brace scanner so `}` inside strings doesn't break the balance.

### 1.5 `extract_design_tokens(raw_html, name) -> DesignTokens` - the new public entry point
Replace `_extract_design_metadata` with this function. Same overall pipeline, with these fixes:

**Background detection (headline bug):**
- Expand `bg_var_keys` with `--paper`, `--paper-bg`, `--paper-2`, `--cream`, `--cream-bg`, `--canvas-2`, `--page-bg`, `--surface-base`, `--bg-base`, `--background-color`, `--body-background`, `--layout-bg`, `--shell-bg`, `--base-bg`.
- Scan inline `style=` on `html`, `body`, `#root`, `#app`, `.page`, `.app`, `.shell`, `.wrap`.
- CSS rule scan restricted to `^(html|body|main|#root|#app|\.(page|app|shell|wrap|site|layout|container))\b` selectors, `background`/`background-color` props. If gradient, take first color stop.
- Fallback: build `bg_counts` only from `background`/`background-color` declarations on selectors NOT matching `r"(glow|shadow|accent|highlight|sticker|tape|badge|pill|chip|mark|hl|hover|active|focus|btn|button|tag)"`. Pick `most_common(1)`.
- Only if `bg_counts` empty: fall back to `all_hex_counts` filtered to low-saturation (`_saturation < 0.25`). Never a saturated accent.
- Absolute last resort: `"#ffffff"` or `"#09090b"` with a warning appended to `tokens.warnings`.

**Semantic colors (do NOT fabricate):**
- Add `_extract_semantic_colors(css_vars, all_hex_counts, theme) -> dict`. Scan css_vars for `--success/--green/--positive/--ok`, `--error/--danger/--red/--negative`, `--warning/--warn/--yellow/--caution`, `--info/--blue/--notice`. If missing, look for hue-clustered saturated hexes in `all_hex_counts` (green 90-150�, red 0-15�/345-360�, yellow/orange 30-60�, blue 200-260�) with `_saturation > 0.3` and `_contrast_ratio > 2.0` vs bg. **Omit the family if not found** - never fall back to `#10b981`/`#ee0000`/`#f5a623`.
- Store into `tokens.colors.semantic`.

**Gradients:**
- Add `_extract_gradients(css_text) -> list[tuple[str, str]]`. Find `linear-gradient(...)` calls, extract first and last hex stops (up to 3 gradients). Store in `tokens.colors.gradients`. **Do not emit Vercel's `#7928ca#ff0080` etc.**

**Typography scale:**
- Add `_extract_typography_scale(css_rules) -> dict[str, TypeToken]`. Scan `font-size` values (convert rem/em  px @16px root). Bucket: `display-xl >=40`, `display-lg 32-39`, `display-md 24-31`, `display-sm 20-23`, `body-lg 17-19`, `body-md 15-16`, `body-sm 13-14`, `caption 11-12`. Take most frequent `(size, weight, line-height, letter-spacing)` per bucket. **Skip empty buckets** - do not invent `48px/600/-2.4px`.

**Spacing scale:**
- Add `_extract_spacing_scale(css_rules) -> list[int]`. Collect all `padding`/`margin`/`gap`/`row-gap`/`column-gap` px values (2-256). Return sorted dedup set. **Do not hardcode 4/8/12/16/...** Return `[]` if none found.

**Radii:**
- Add `_extract_radii(css_rules) -> tuple[list[str], str, str]` returning `(all_radii, card_radius, button_radius)`. Convert rem/em  px. `9999px`/`99999px`  `"full"`. `card` = most common in `.card`/`.panel`/`.surface` context. `button` = most common in `.btn`/`.button`/`button` context. Fallbacks only if empty: `card="12px"`, `button="8px"`.

**Components (NEW - biggest missing feature):**
- Add `_extract_components(html, css_rules, soup) -> list[ComponentToken]`.
- Collect HTML class names (BeautifulSoup or regex fallback).
- For each `(selector, props)` in `css_rules`, split selector on `,`, `.`, `#`, whitespace, strip pseudo `:hover`/`:focus`/`::before`/`[data-*]`. For each class token present in HTML class set, emit a `ComponentToken`.
- Classify `kind` by name:
  - scrapbook: `polaroid`, `notepaper`, `notebook`, `paper`, `tape`, `sticker`, `pin`, `clip`, `idcard`, `contact-card`, `postcard`, `letter`, `note`, `say-note`, `quote`, `big-quote`, `thought`, `speech`, `bubble`, `handwritten`
  - navigation: `nav`, `navbar`, `header`, `footer`, `sidebar`, `menu`, `tab`
  - action: `btn`, `button`, `cta`, `link`, `action`
  - surface: `card`, `panel`, `surface`, `tile`, `block`, `box`
  - form: `input`, `field`, `form`, `textarea`, `select`, `checkbox`, `radio`, `toggle`, `switch`
  - badge: `badge`, `pill`, `chip`, `tag`, `label`, `kbd`
  - overlay: `modal`, `dialog`, `drawer`, `sheet`, `popover`, `tooltip`, `toast`
  - media: `avatar`, `icon`, `logo`, `img`, `image`, `media`, `thumb`
  - pricing: `pricing`, `plan`, `tier`, `subscribe`
  - section: `hero`, `banner`, `feature`, `showcase`, `band`, `section`
  - tool: `tool`, `tool-tile`, `skill`, `tech`
  - progress: `timeline`, `step`, `progress`, `meter`
  - else: `generic`
- Dedupe by name (merge props). Sort by kind then name. Cap at 40.

**Text primary:** prefer `body`/`html,body`/`p` over `h1`. Reject if `_contrast_ratio(text, bg) < 4.5`. If none pass, use `_best_foreground(bg)`.

**Border:** try `border-color` across all rules first, then `border`, then `border-bottom`. Reject candidates with `_saturation > 0.45` unless no low-saturation candidate exists.

**Accents:** reject any hex with `_contrast_ratio(c, bg) < 2.0` or `_contrast_ratio(c, text) < 1.5`. Rank by `(count, _saturation)` desc. `secondary` must differ from `primary` by �40 in Euclidean RGB.

**Warnings:** append to `tokens.warnings` whenever a fallback fires (background last resort, semantic omitted, typography/spacing/radii/components empty, unresolved vars non-empty).

**Return** a `DesignTokens` dataclass instance. No dict return. No `css_rules` in return (keep internal). No `all_hex_counts` in return.

## PHASE 2 - Write `core/design_md_generator.py`

Implement `generate_design_md(tokens: DesignTokens, name: str) -> str` returning the full `<design-context>` markdown.

**Hard rules:**
- Quote YAML string values: use `json.dumps(value)` for `name` and `description` (JSON is valid YAML).
- **Do not emit** any key whose value is empty/missing from `tokens`.
- **Colors section:**
  - Always emit: `canvas`, `surface`, `surface-2`, `ink`, `body`, `muted`, `border`, `border-strong`, `link`, `link-deep`, `link-soft`, `primary`, `on-primary`, `selection-bg`, `selection-fg` - **only if the corresponding `tokens.colors.*` is non-empty**.
  - `success`/`error`/`warning`/`info` + their `-soft`/`-deep` variants: emit **only if** `tokens.colors.semantic` has the family. If absent, omit entirely.
  - `gradient-1-start`/`-end` . `gradient-3-*`: emit only for gradients in `tokens.colors.gradients`. If empty, omit the `### Brand Gradient` subsection.
  - **Do NOT emit** `violet`, `cyan`, `highlight-pink`, `highlight-magenta`, `gradient-develop-*`, `gradient-preview-*`, `gradient-ship-*`. These are Vercel brand colors and must not appear.
- **Typography section:** loop over `tokens.typography` dict. Emit each bucket present. Skip empty. Use `tokens.mono_font` stack for `caption-mono`/`code`, `tokens.body_font` for body buckets, `tokens.display_font` for display buckets.
- **Rounded section:** `none: 0px` always. Then `xs`, `sm`, `md`, `lg`, `xl`, `2xl` - emit **only for radii present in `tokens.radii`** (smallest 4  xs/sm/md/lg, 2 largest  xl/2xl). `full: 9999px` only if `"full"` in `tokens.radii`. Add `# NOTE: 9999px is a universal CSS idiom for fully-rounded` comment.
- **Spacing section:** emit named tokens only for values present in `tokens.spacing`. Map: `xxs=2`, `xs=4`, `sm=8`, `md=12`, `lg=16`, `xl=24`, `2xl=32`, `3xl=40`, `4xl=48`, `5xl=64`, `6xl=96`, `section=128|192`. If `tokens.spacing` empty, emit only `base: 4px` with `# NOTE: 4px base rhythm assumed`.
- **Components section:** loop `tokens.components`. For each, emit:
  ```yaml
  components:
    {component.name}:
      # kind: {component.kind}
      backgroundColor: "{props.get('background-color') or props.get('background') or 'transparent'}"
      textColor: "{props.get('color') or '{colors.ink}'}"
      borderColor: "{props.get('border-color') or '{colors.hairline}'}"     # only if present in props
      rounded: "{props.get('border-radius') or '{rounded.md}'}"
      padding: "{props.get('padding') or props.get('padding-inline') or '{spacing.md}'}"
  ```
  Only emit a property if it was actually found or is a token reference. Cap at 30 components. If `tokens.components` empty, emit `# NOTE: no component classes were detected in the source.` - **do not fall back to the Vercel inventory.**
- **Body markdown:**
  - `### Brand Gradient` - only if gradients exist.
  - `### Semantic` - only if any semantic family exists.
  - Typography hierarchy table - only populated rows.
  - `### Note on Font Substitutes` - only if `tokens.display_font` not in `("Inter", "system-ui", "Arial", "Helvetica")`.
  - Components narrative subsections - iterate `tokens.components` grouped by `kind`. Omit empty kinds.
  - `## Do's and Don'ts` - keep universal items. **Delete** the Vercel-specific "Don't introduce arbitrary purple-to-indigo gradients" line.
- **Aesthetic profile string** (used in `description`): detect via **font-name word-boundary regex**, not substring:
  ```python
  def _has_font(fonts, names):
      return any(any(re.search(rf"\b{re.escape(n)}\b", f, re.I) for n in names) for f in fonts)
  ```
  Use `_has_font(fonts, ["Caveat", "Bradley Hand", ...])` for scrapbook; `any("serif" in f.lower() and "sans" not in f.lower() for f in fonts)` for editorial; `_has_font(fonts, ["Inter", "Plus Jakarta Sans", ...])` for SaaS.

**Signature:** `def generate_design_md(tokens: DesignTokens, name: str) -> str`. Keep a compatibility shim in `design_extractor.py`:
```python
def generate_design_md(raw_html, title=None, output_path=None):
    from core.design_md_generator import generate_design_md as _gen
    from core.design_extractor import extract_design_tokens
    tokens = extract_design_tokens(raw_html, title or "Design System")
    md = _gen(tokens, title or "Design System")
    if output_path:
        Path(output_path).write_text(md, encoding="utf-8")
    return md
```
(External callers using the old signature keep working.)

## PHASE 3 - Write `core/master_template_builder.py`

Move `inject_semantic_slots` and `generate_master_template_html` here. Rename to `build_master_template(raw_html, tokens, max_bytes=40000)`.

**Fix the 199 KB bug - this is the reason the current output is 5x over budget:**
- Enforce `max_bytes` with a **loop**, not a single `if`. Stages (each idempotent, cumulative):
  1. Strip base64 via `strip_base64_images` (fixed in PHASE 1).
  2. Compact CSS: strip comments, collapse whitespace, minify `{}:;,`.
  3. Strip non-`SLOT:` HTML comments.
  4. Simplify SVGs > 140 chars to `<svg width="24" height="24" viewBox="..."><path d="M0 0h24v24H0z"/></svg>`.
  5. Condense repetitive lists: for `grid`/`flex`/`cards`/`list` containers with >2 direct children, `decompose()` all but the first 2.
  6. Minify inter-tag whitespace: `re.sub(r'>\s+<', '><', html)`.
  7. Drop `<script>` tags entirely (if still over budget - master template is for DOM + CSS + keyframes; hydration JS bloat is not needed).
- After all stages, if `len(html.encode()) > max_bytes`, raise `ValueError(f"master-template exceeds {max_bytes} bytes after all reduction stages ({actual} bytes). Input too complex.")` - do **not** return an oversized file.
- Log each stage's size to `logger.info`.

## PHASE 4 - Rewrite `core/design_resolver.py` + write `core/design_cache.py`

### 4.1 `core/design_resolver.py`
Keep only: `ResolvedDesign`, `resolve_design`, `resolve_from_catalog`, `load_catalog`, `_SEMANTIC_ROUTES`, `is_ui_task`, `is_redesign_or_explicit_request`, `_infer_scope`, `_infer_theme`, `_normalize_scope`, `_normalize_theme`, `_norm_stem`, `_matches_scope`, `_find_template_file`, `_find_catalog_path`, `_get_available_templates`, `_get_ui_dirs`, `_get_workspace_root`, `_get_anti_slop_rules`, `_keyword_present`, `extract_authentic_task`, `format_design_prompt`, `check_greenfield_gate`.

**Delete from this file:** `_sanitize_html_for_prompt`, `inject_semantic_slots`, `generate_master_template_html`, `get_or_create_reference_design_cache`, `generate_blueprint_and_template`, `_load_direct_html_reference`, `_EXTRACTED_CACHE_DIR`, the `try: from core.design_extractor import ...` block.

`ResolvedDesign` keeps `raw_html`, `full_raw_html` fields for backwards compat - but they are populated by `_load_direct_html_reference`, which now lives in `design_cache.py` and is imported at the top:
```python
from core.design_cache import _load_direct_html_reference
```
(Yes, it's a private helper used cross-module - that's acceptable; alternatively make it public as `load_direct_html_reference`.)

### 4.2 `core/design_cache.py`
```python
_EXTRACTOR_VERSION = "v2"   # bump this whenever design_extractor.py logic changes

def get_or_create_reference_design_cache(reference_path: Path | str) -> tuple[Path, Path]:
    """Returns (DESIGN.md path, master-template.html path). Cache hit < 5ms."""
    ref_path = Path(str(reference_path).strip()).resolve()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ref_path.stem).strip("_").lower()
    cache_dir = _EXTRACTED_CACHE_DIR / slug
    version_file = cache_dir / "_extractor_version.txt"
    cached_md = cache_dir / "DESIGN.md"
    cached_mt = cache_dir / "master-template.html"

    ref_mtime = ref_path.stat().st_mtime
    version_ok = version_file.exists() and version_file.read_text().strip() == _EXTRACTOR_VERSION
    files_ok = (
        cached_md.exists() and cached_md.stat().st_size > 0 and cached_md.stat().st_mtime >= ref_mtime
        and cached_mt.exists() and cached_mt.stat().st_size > 0 and cached_mt.stat().st_mtime >= ref_mtime
    )
    if version_ok and files_ok:
        logger.debug("Cache HIT: %s", cache_dir)
        return cached_md, cached_mt

    # Cache MISS or STALE
    logger.info("Cache %s for '%s'. Re-extracting...", "STALE" if version_file.exists() else "MISS", ref_path.name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_html = ref_path.read_text(encoding="utf-8", errors="ignore")

    from core.design_extractor import extract_design_tokens
    from core.design_md_generator import generate_design_md
    from core.master_template_builder import build_master_template

    tokens = extract_design_tokens(raw_html, ref_path.stem)
    md = generate_design_md(tokens, ref_path.stem)
    mt = build_master_template(raw_html, tokens, max_bytes=39900)

    cached_md.write_text(md, encoding="utf-8")
    cached_mt.write_text(mt, encoding="utf-8")
    version_file.write_text(_EXTRACTOR_VERSION, encoding="utf-8")
    return cached_md, cached_mt

def generate_blueprint_and_template(reference_html_path, output_dir) -> tuple[Path, Path]:
    """Legacy name - external callers depend on it. Copies cache into output_dir."""
    # Same as current implementation, but delegates to get_or_create_reference_design_cache.
    ...

def _load_direct_html_reference(html_file):  # moved from resolver
    ...
```

## PHASE 5 - Self-test (`core/_self_test.py`)

Write runnable `python -m core._self_test` with `assert` statements:

1. **Scrapbook regression:**
```python
SCRAPBOOK = """<html><head><style>
:root { --paper: #f3eee2; --ink: #2b2b2b; --tape: #f0d531; --accent: #e05a47; }
body { background: var(--paper); color: var(--ink); }
.polaroid { background:#fff; border-radius:4px; padding:12px; }
.tape { background: var(--tape); }
.notepaper { background:#faf6ea; border-radius:2px; padding:16px; }
</style></head><body>
<div class="polaroid"><div class="tape"></div></div>
<div class="notepaper">Note</div>
</body></html>"""
tokens = extract_design_tokens(SCRAPBOOK, "Scrapbook")
assert tokens.colors.canvas == "#f3eee2", tokens.colors.canvas
assert tokens.colors.primary_accent in ("#e05a47", "#f0d531")
assert "polaroid" in {c.name for c in tokens.components}
assert "notepaper" in {c.name for c in tokens.components}
md = generate_design_md(tokens, "Scrapbook")
assert "nav-bar" not in md
assert "pricing-card" not in md
assert "#7928ca" not in md
assert "#ff0080" not in md
assert "#f9cb28" not in md
```

2. **Vercel-like source:**
```python
SAAS = """<html><head><style>
:root { --background: #000; --foreground: #fff; --accent: #0070f3; }
body { background: var(--background); color: var(--foreground); }
.nav-bar { height: 64px; }
.btn-primary { background: #0070f3; color: #fff; }
.pricing-card { border: 1px solid #333; padding: 32px; }
</style></head><body><nav class="nav-bar"></nav><button class="btn-primary">Go</button><div class="pricing-card"></div></body></html>"""
tokens = extract_design_tokens(SAAS, "SaaS")
md = generate_design_md(tokens, "SaaS")
assert "nav-bar" in md
assert "pricing-card" in md
assert "success:" not in md   # no --success in source  omitted
assert "error:" not in md
assert "warning:" not in md
```

3. **Base64 preservation:** `<img src="data:image/png;base64,iVBORw0KGgo=\nAAAA=="><p>after</p>`  `<p>after</p>` survives.

4. **Media query parsing:** `@media (max-width:600px){.foo{color:red}}`  `(".foo", {"color":"red"})` in results.

5. **HSL wrap:** `_hsl_to_hex(-30,100,50) == _hsl_to_hex(330,100,50)`.

6. **Foreground:** `_best_foreground("#f0d531") == "#000000"`, `_best_foreground("#09090b") == "#ffffff"`.

7. **Master template size:** generate for a synthetic 500 KB HTML  `len(build_master_template(...).encode()) < 40000` OR `ValueError` raised. Never an oversized file returned.

8. **Determinism:** `generate_design_md(extract_design_tokens(H, "X"), "X") == generate_design_md(extract_design_tokens(H, "X"), "X")`.

9. **Cache versioning:** write a v1 cache, bump `_EXTRACTOR_VERSION` to v2, call `get_or_create_reference_design_cache`  should re-extract.

## PHASE 6 - Grep & clean

```bash
grep -rn "blueprint\.html\|blueprint_html\|generate_blueprint_html" --include="*.py" .
```
Remove all references from `core/`, `tests/`, `actions/`. `generate_blueprint_html` must not exist anywhere.

```bash
grep -rn "_sanitize_html_for_prompt\|generate_master_template_html" --include="*.py" .
```
Should only appear in `master_template_builder.py` (renamed to `build_master_template`) and `design_cache.py` (import). Remove from `design_resolver.py`.

## PHASE 7 - Final checks

Run:
```bash
python -m py_compile core/design_tokens.py core/design_extractor.py core/design_md_generator.py core/master_template_builder.py core/design_resolver.py core/design_cache.py
python -m core._self_test
pytest tests/ -k "design or exemplar"
```

All must pass. If any test in `tests/` still imports `generate_blueprint_html` or expects a `blueprint.html` file, **update the test** to expect `DESIGN.md` + `master-template.html` instead.

## Deliverable format

Return the full content of each new/modified file:
- `core/design_tokens.py` (new)
- `core/design_extractor.py` (rewritten - extraction only)
- `core/design_md_generator.py` (new)
- `core/master_template_builder.py` (new)
- `core/design_resolver.py` (rewritten - selection only)
- `core/design_cache.py` (new)
- `core/_self_test.py` (new)

Do not return diffs. Do not ask clarifying questions. If a conflict arises between the public API and a fix, preserve the public API and note the conflict in a `# NOTE:` comment.

## Known limitations to document in `design_extractor.py` docstring

- Media-query selector context is flattened during parsing (inner rules are merged with their inner selectors).
- CSS `@import` is not followed.
- JS-injected styles are not seen.
- `!important` is ignored in value resolution.
- Master template drops `<script>` tags in the final reduction stage if size budget requires it - interactive JS is not guaranteed if the source is huge.
- Cache version `v2` must be bumped whenever extractor logic changes; otherwise stale cache is served.
```
