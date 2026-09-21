"""
core/design_resolver.py — Autonomous Design System & Reference Token Resolver.

Inspects coding tasks for UI/Web hints, explicit reference names, or semantic domain keywords,
and deterministically resolves design tokens directly from Hamza Taste's 13 curated HTML templates:
  - Direction Layer: Exact colors, typography, glass elevation, and components from skills/hamza_taste/references/
  - Filter Layer: Non-negotiable Anti-Slop Directives from skills/hamza_taste/SKILL.md
  - Autonomous Agent Choice: Intelligent routing across all 13 reference designs with 0ms caching.

Created for ZEZO by Hamza Bukhari.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.design_extractor import extract_design_system_from_html

logger = logging.getLogger("zezo.design_resolver")

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# Semantic Category Mapping for the 13 HTML Reference Templates
_SEMANTIC_ROUTES: list[tuple[list[str], str]] = [
    (["saas", "b2b", "subscription", "software", "crm", "api service", "cloud platform", "developer platform"], "saas"),
    (["dub", "conversion", "marketing", "link", "real estate", "property", "properties", "mortgage", "realtor", "broker", "sales", "affiliate", "home"], "dub landing page"),
    (["ai", "agent", "autonomous", "bot", "assistant", "robot", "robotics", "machine learning", "deep learning", "neural", "automations"], "autonomus"),
    (["dashboard", "ecosystem", "analytics", "admin", "metrics", "platform", "infrastructure", "backend console", "portal", "monitoring"], "Standalone Ecosystem"),
    (["os", "operating system", "window", "desktop", "terminal", "desktop app", "workspace", "file manager"], "froma os "),
    (["image", "media", "art", "photo", "gallery", "generator", "video", "creator", "photo studio", "art studio", "photography", "visual", "film"], "image gen"),
    (["crazy", "creative", "agency", "bold", "dynamic", "vibrant", "design agency", "portfolio", "creative studio", "branding", "advertising", "showcase", "fashion showcase", "developer portfolio"], "Crazy UI landing page"),
    (["nexus", "matrix", "hardware", "cyber", "tech", "gadget", "device", "gaming", "esports", "crypto", "web3", "blockchain"], "nexus"),
    (["spatial", "skeuomorphic", "glass", "3d", "card", "spatial computing", "vision", "neumorphism", "depth"], "skeumorphic spatial component"),
    (["aura", "frame", "hud", "glowing", "luxury", "watch", "jewelry", "fashion", "premium dark", "elegance", "automotive", "car", "supercar"], "aura frame"),
    (["nami", "minimal", "clean", "docs", "documentation", "fintech", "banking", "finance", "medical", "clinic", "healthcare", "consulting", "law", "legal"], "nami landing page"),
]


@dataclass
class ResolvedDesign:
    source_name: str
    source_type: str  # "reference_raw_html", "reference_cached", "reference_extracted", "reference_autonomous", "project_existing"
    design_spec: str = ""
    anti_slop_rules: str = ""
    raw_html: str = ""
    accent_color: str = ""
    bg_color: str = ""

    def is_active(self) -> bool:
        return bool((self.raw_html and self.raw_html.strip()) or (self.design_spec and self.design_spec.strip()))


def _get_workspace_root() -> Path:
    return _WORKSPACE_ROOT


def _get_ui_dirs() -> Tuple[Path, Path, Path]:
    ws = _get_workspace_root()
    # Primary location: skills/hamza_taste/references/
    ref_ui = ws / "skills" / "hamza_taste" / "references"
    if not ref_ui.exists() and (ws / "References" / "UI").exists():
        ref_ui = ws / "References" / "UI"

    html_dir = ref_ui / "html"
    md_dir = ref_ui / "design md"
    if not md_dir.exists() and (ref_ui / "design_md").exists():
        md_dir = ref_ui / "design_md"

    html_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)
    return ref_ui, html_dir, md_dir


def _norm_stem(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    clean = re.sub(r"[-_\s]+", "", name.lower())
    clean = clean.removesuffix(".html").removesuffix(".htm").removesuffix(".md").removesuffix("design")
    return clean


def _sanitize_html_for_prompt(raw_html: str, max_chars: int = 50000) -> str:
    """
    Strip bulky base64 data URIs and gigantic embedded blobs to keep prompts fast and token-efficient,
    while preserving all CSS styles, @keyframes, classes, structure, and component layouts.
    """
    if not raw_html:
        return ""
    # Replace large base64 image data URIs with concise SVG placeholders
    cleaned = re.sub(
        r'data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}',
        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100%" height="100%" fill="%23222"/></svg>',
        raw_html,
    )
    # Replace huge inline SVG paths (> 1000 chars) with compact path placeholders
    cleaned = re.sub(r'd="[A-Za-z0-9\s,\.\-]{1000,}"', 'd="M0 0h24v24H0z"', cleaned)

    if len(cleaned) > max_chars:
        # Keep head, styles, and full early body layout
        cleaned = cleaned[:max_chars] + "\n<!-- [Template content truncated for context budget] -->\n</body>\n</html>"
    return cleaned


def _get_anti_slop_rules() -> str:
    """Load canonical anti-slop rules from skills/hamza_taste/SKILL.md."""
    skill_file = _get_workspace_root() / "skills" / "hamza_taste" / "SKILL.md"
    if skill_file.exists():
        try:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"(## 🛑 NON-NEGOTIABLE ANTI-SLOP RULES.*?)(\n## 🎯|\Z)", content, re.DOTALL)
            if m:
                return m.group(1).strip()
        except Exception:
            pass

    return """## 🛑 NON-NEGOTIABLE ANTI-SLOP RULES:
1. ❌ NO Cliché AI Purple/Indigo Gradients: Strictly forbid generic purple blobs or purple hero text.
2. ❌ NO Unstyled Native Controls: Custom styled dark inputs, buttons, and scrollbars are mandatory.
3. ❌ NO Fake Buzzwords / Fake Metric Copy: Use honest, realistic product copy.
4. ❌ NO Plain 90s RGB Primaries: Use refined, harmonized tokens extracted from the reference design.
5. ❌ NO Fragile Layouts: All layouts MUST use CSS Grid or Flexbox with max-w-7xl (1280px) containers."""


def is_ui_task(task: str) -> bool:
    """Determine if a task involves Web/UI/Frontend development."""
    t = task.lower()
    keywords = [
        "website", "web page", "webpage", "landing page", "landingpage",
        "ui", "ux", "frontend", "html", "css", "dashboard", "component",
        "saas", "portfolio", "web app", "webapp", "interface", "app layout",
        "header", "footer", "button", "cards", "pricing", "hero section"
    ]
    return any(k in t for k in keywords)


def is_redesign_or_explicit_request(task: str) -> bool:
    """Check if the user is asking to change/redesign/replace the design or use a specific reference."""
    t = task.lower()
    redesign_keywords = [
        "redesign", "change design", "new design", "update design", "change the design",
        "update the design", "change color", "change theme", "different theme",
        "different design", "regenerate", "make it like", "look like", "replace design",
        "start fresh", "rebuild", "re-create", "reference", "design system", "theme",
        "palette", "styling", "switch to", "make it exact", "according to this",
        "provided design", "loaded design", "design theme", "clean real estate"
    ]
    return any(k in t for k in redesign_keywords)


def _load_or_extract_reference(html_file: Optional[Path], md_file: Optional[Path], md_dir: Path) -> Optional[tuple[str, str, str, str]]:
    """
    Returns (source_name, source_type, design_spec, raw_html)
    """
    raw_html = ""
    if html_file and html_file.exists():
        try:
            raw_text = html_file.read_text(encoding="utf-8", errors="ignore")
            raw_html = _sanitize_html_for_prompt(raw_text)
        except Exception as e:
            logger.warning("Failed reading raw html %s: %s", html_file, e)

    # 1. Check cached MD
    if md_file and md_file.exists():
        html_is_newer = False
        if html_file and html_file.exists():
            try:
                html_is_newer = html_file.stat().st_mtime > md_file.stat().st_mtime
            except Exception:
                html_is_newer = False

        if not html_is_newer:
            try:
                spec = md_file.read_text(encoding="utf-8", errors="ignore")
                if spec.strip() or raw_html:
                    clean_stem = re.sub(r"[-_\s]+", "-", md_file.stem).title()
                    return clean_stem, "reference_cached", spec, raw_html
            except Exception as e:
                logger.warning("Failed reading cached design md %s: %s", md_file, e)

    # 2. Extract from HTML
    if html_file and html_file.exists():
        clean_stem = re.sub(r"[-_\s]+", "-", html_file.stem).title()
        target_md_path = md_dir / f"{clean_stem}-DESIGN.md"
        try:
            spec = extract_design_system_from_html(html_file, output_path=target_md_path)
            if spec.strip() or raw_html:
                return clean_stem, "reference_extracted", spec, raw_html
        except Exception as e:
            logger.warning("Failed extracting design from %s: %s", html_file, e)

    if raw_html and html_file:
        clean_stem = re.sub(r"[-_\s]+", "-", html_file.stem).title()
        return clean_stem, "reference_raw_html", "", raw_html

    return None


def resolve_design(
    task: str,
    session_memory: Optional[dict] = None,
    repo_path: Optional[str | Path] = None,
) -> ResolvedDesign:
    """
    Deterministically resolves design directly from Hamza Taste HTML references:
      1. Priority 1: User-explicit reference name match in task (e.g. "use dub landing page", "saas.html").
      2. Priority 2: Session memory / persistent memory for active_design_path.
      3. Priority 3: Semantic Category Match across the 13 reference templates.
      4. Priority 4: Existing repository design (if repo_path contains index.html AND task is NOT a redesign).
      5. Priority 5: Autonomous Agent Choice (Diverse, intelligent curated selection across references).
    """
    anti_slop = _get_anti_slop_rules()
    _, html_dir, md_dir = _get_ui_dirs()
    task_clean = task.lower()
    has_redesign_intent = is_redesign_or_explicit_request(task)

    # Gather available reference files
    available_md = list(md_dir.glob("*.md")) if md_dir.exists() else []
    available_html = list(html_dir.glob("*.html")) if html_dir.exists() else []

    # 1. Priority 1: Explicit Reference Match in task
    matched_html: Optional[Path] = None
    matched_md: Optional[Path] = None
    task_words = set(re.findall(r"[a-z0-9]+", task_clean))

    def _is_explicit_match(stem_str: str) -> bool:
        if stem_str.lower() in ("design-system", "design_system", "design system"):
            return False
        clean_stem = re.sub(r"[-_\s]+", " ", stem_str.lower())
        clean_stem = clean_stem.replace(".html", "").replace(".md", "").replace("design", "").strip()
        stem_tokens = [t for t in clean_stem.split() if t not in ("landing", "page", "the", "a", "an", "and", "component", "system")]
        if not stem_tokens:
            stem_tokens = clean_stem.split()
        if stem_tokens and all(tok in task_words for tok in stem_tokens):
            return True
        if clean_stem and clean_stem in task_clean:
            return True
        return False

    for p in available_md:
        if _is_explicit_match(p.stem):
            matched_md = p
            break

    if not matched_md:
        for p in available_html:
            if _is_explicit_match(p.stem):
                matched_html = p
                break

    if matched_html and not matched_md:
        h_norm = _norm_stem(matched_html.name)
        for p in available_md:
            if _norm_stem(p.name) == h_norm:
                matched_md = p
                break
    elif matched_md and not matched_html:
        m_norm = _norm_stem(matched_md.name)
        for p in available_html:
            if _norm_stem(p.name) == m_norm:
                matched_html = p
                break

    # If explicit reference matched in prompt, return it immediately
    if matched_md or matched_html:
        res = _load_or_extract_reference(matched_html, matched_md, md_dir)
        if res:
            name, stype, spec, raw_h = res
            return ResolvedDesign(source_name=name, source_type=stype, design_spec=spec, raw_html=raw_h, anti_slop_rules=anti_slop)

    # 2. Priority 2: Check session memory & persistent memory
    candidate_design_target = ""
    if session_memory and isinstance(session_memory, dict):
        candidate_design_target = (
            session_memory.get("active_design_path")
            or session_memory.get("active_design")
            or session_memory.get("last_loaded_file")
            or session_memory.get("active_file")
            or ""
        )

    if not candidate_design_target:
        try:
            from memory.memory_manager import recall
            candidate_design_target = recall("active_design_path") or recall("active_design") or ""
        except Exception:
            candidate_design_target = ""

    if candidate_design_target:
        p = Path(candidate_design_target)
        if p.exists() and p.is_file():
            try:
                raw_h = ""
                spec_content = ""
                if p.suffix.lower() in (".html", ".htm"):
                    raw_h = _sanitize_html_for_prompt(p.read_text(encoding="utf-8", errors="ignore"))
                else:
                    spec_content = p.read_text(encoding="utf-8", errors="ignore")
                return ResolvedDesign(
                    source_name=p.stem,
                    source_type="reference_cached",
                    design_spec=spec_content,
                    raw_html=raw_h,
                    anti_slop_rules=anti_slop,
                )
            except Exception:
                pass
        else:
            target_norm = _norm_stem(str(candidate_design_target))
            matched_h = next((h for h in available_html if _norm_stem(h.name) == target_norm), None)
            matched_m = next((m for m in available_md if _norm_stem(m.name) == target_norm), None)
            if matched_h or matched_m:
                res = _load_or_extract_reference(matched_h, matched_m, md_dir)
                if res:
                    name, stype, spec, raw_h = res
                    return ResolvedDesign(
                        source_name=name,
                        source_type=stype,
                        design_spec=spec,
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                    )

    # 3. Priority 3: Semantic Category Match across 13 Reference Templates
    for keywords, target_stem in _SEMANTIC_ROUTES:
        if any(kw in task_clean for kw in keywords):
            target_norm = _norm_stem(target_stem)
            cat_html = next((h for h in available_html if target_norm in _norm_stem(h.name)), None)
            cat_md = next((m for m in available_md if target_norm in _norm_stem(m.name)), None)
            cat_res = _load_or_extract_reference(cat_html, cat_md, md_dir)
            if cat_res:
                name, stype, spec, raw_h = cat_res
                return ResolvedDesign(source_name=name, source_type=stype, design_spec=spec, raw_html=raw_h, anti_slop_rules=anti_slop)

    # 4. Priority 4: Existing Project Design Extraction (ONLY when NOT a redesign request)
    if repo_path and not has_redesign_intent:
        r_path = Path(repo_path).resolve()
        if r_path.exists() and r_path.is_dir():
            repo_html = r_path / "index.html"
            repo_css = r_path / "style.css"
            if repo_html.exists() and repo_html.stat().st_size > 50:
                try:
                    spec = extract_design_system_from_html(repo_html)
                    raw_h = _sanitize_html_for_prompt(repo_html.read_text(encoding="utf-8", errors="ignore"))
                    return ResolvedDesign(
                        source_name=f"Project ({r_path.name})",
                        source_type="project_existing",
                        design_spec=spec,
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                    )
                except Exception as e:
                    logger.warning("Failed extracting design from project %s: %s", repo_html, e)
            elif repo_css.exists() and repo_css.stat().st_size > 50:
                try:
                    fake_html = f"<html><head><style>{repo_css.read_text(encoding='utf-8', errors='ignore')}</style></head><body></body></html>"
                    spec = extract_design_system_from_html(fake_html)
                    return ResolvedDesign(
                        source_name=f"Project CSS ({r_path.name})",
                        source_type="project_existing",
                        design_spec=spec,
                        raw_html=fake_html,
                        anti_slop_rules=anti_slop,
                    )
                except Exception as e:
                    logger.warning("Failed extracting design from project CSS %s: %s", repo_css, e)

    # 5. Priority 5: Autonomous Agent Choice (Diverse, intelligent curated selection)
    # Pick dynamically from available reference templates
    diverse_candidates = ["dub landing page", "Crazy UI landing page", "nami landing page", "saas", "autonomus", "aura frame", "image gen"]
    chosen_stem = "saas"

    # Hash-based variety for completely generic tasks
    if available_html:
        task_hash = sum(ord(c) for c in task_clean)
        chosen_stem = diverse_candidates[task_hash % len(diverse_candidates)]

    target_norm = _norm_stem(chosen_stem)
    flagship_html = next((h for h in available_html if target_norm in _norm_stem(h.name)), None) or (available_html[0] if available_html else None)
    flagship_md = next((m for m in available_md if target_norm in _norm_stem(m.name)), None) or (available_md[0] if available_md else None)

    flagship_res = _load_or_extract_reference(flagship_html, flagship_md, md_dir)
    if flagship_res:
        name, stype, spec, raw_h = flagship_res
        return ResolvedDesign(
            source_name=f"{name} (Autonomous Choice)",
            source_type="reference_autonomous",
            design_spec=spec,
            raw_html=raw_h,
            anti_slop_rules=anti_slop,
        )

    # Fallback if no references exist
    return ResolvedDesign(
        source_name="Hamza Taste Master",
        source_type="default",
        design_spec="",
        raw_html="",
        anti_slop_rules=anti_slop,
    )


def format_design_prompt(design: ResolvedDesign) -> str:
    """Format the resolved design specification into an optimized prompt block."""
    if not design or not design.is_active():
        return ""

    if design.raw_html and design.raw_html.strip():
        return f"""
═══════════════════════════════════════════════════════════════════════════════
🎨 MASTER RAW HTML REFERENCE TEMPLATE (Source: {design.source_name} [{design.source_type}])
═══════════════════════════════════════════════════════════════════════════════
Below is the complete reference HTML template. Use this raw HTML/CSS file directly as your visual, architectural, and component foundation.

```html
{design.raw_html}
```

{design.anti_slop_rules}
═══════════════════════════════════════════════════════════════════════════════
MANDATORY AESTHETIC DIRECTIVE:
1. FAITHFULLY REPLICATE the structural layouts, hero sections, navigation bars, glassmorphism cards, CSS animations (@keyframes), grid/flex structures, typography hierarchy, and color palettes from the raw HTML reference above.
2. ADAPT all textual copy, product names, metrics, and domain-specific sections to the user's specific request.
3. FOR CSS: Extract and implement the complete styling rules, variables, transitions, and hover effects seen in the reference template.
═══════════════════════════════════════════════════════════════════════════════
"""

    return f"""
═══════════════════════════════════════════════════════════════════════════════
🎨 MASTER DESIGN SYSTEM SPECIFICATION (Source: {design.source_name} [{design.source_type}])
═══════════════════════════════════════════════════════════════════════════════
{design.design_spec}

{design.anti_slop_rules}
═══════════════════════════════════════════════════════════════════════════════
MANDATORY AESTHETIC DIRECTIVE:
1. Adopt the exact color hierarchy, font families, radii, glass elevation, and component recipes detailed above.
2. DO NOT overwrite or ignore these tokens with generic AI styles or purple gradients.
3. Every button, input, card, and section container MUST faithfully follow this design specification.
═══════════════════════════════════════════════════════════════════════════════
"""

