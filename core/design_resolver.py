"""
core/design_resolver.py — Autonomous Direct HTML Design & Reference Resolver.

Inspects coding tasks for UI/Web hints, explicit reference names, or semantic domain keywords,
and deterministically resolves design tokens DIRECTLY from curated HTML templates in:
  - Direction Layer: Exact raw HTML, CSS, layouts, typography, and components from
    skills/website_build/references/ (falling back to skills/hamza_taste/references/)
  - Filter Layer: Non-negotiable Anti-Slop Directives from skills/website_build/SKILL.md
  - Autonomous Agent Choice: Deterministic catalog matching against catalog.json with 0ms caching.

NO intermediate markdown extraction or .md design files are created or used. 100% direct raw HTML.

Created for ZEZO by Hamza Bukhari.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zezo.design_resolver")

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# Semantic Category Mapping for the curated HTML Reference Templates
_SEMANTIC_ROUTES: list[tuple[list[str], str]] = [
    (["saas", "b2b", "subscription", "software", "crm", "api service", "cloud platform", "developer platform"], "saas"),
    (["dub", "conversion", "marketing", "link", "real estate", "property", "properties", "mortgage", "realtor", "broker", "sales", "affiliate", "home"], "dub"),
    (["tennis", "padel", "racquet club", "luxury club", "resort", "country club"], "racquet club"),
    (["autonomous bot", "bot assistant ui", "autonomus", "autonomous agent card", "robotics card", "ai agent card", "agent terminal"], "autonomus"),
    (["dashboard", "ecosystem", "analytics", "admin", "metrics", "infrastructure", "backend console", "portal", "monitoring"], "Standalone Ecosystem"),
    (["os", "operating system", "window", "desktop", "terminal", "desktop app", "workspace", "file manager"], "froma os "),
    (["image", "media", "art", "photo", "gallery", "generator", "video", "creator", "photo studio", "art studio", "photography", "visual", "film"], "image gen"),
    (["crazy", "creative", "agency", "bold", "dynamic", "vibrant", "design agency", "creative studio", "branding", "advertising", "showcase", "fashion showcase"], "Crazy UI landing page"),
    (["portfolio", "personal portfolio", "hairline", "grid portfolio", "developer cv", "engineer portfolio", "minimal resume"], "Hairline Grid Portfolio"),
    (["scrapbook", "scrapbook resume", "editorial portfolio", "visual resume"], "Scrapbook Resume"),
    (["nexus card", "matrix hardware", "matrix component", "nexus hardware", "futuristic matrix"], "nexus"),
    (["spatial", "skeuomorphic", "glass", "3d card", "spatial computing", "vision card", "neumorphism card"], "skeumorphic spatial component"),
    (["aura frame", "aura hud", "glowing frame", "hud frame", "neon frame card", "glowing border component"], "aura frame"),
    (["nami", "minimal", "clean", "docs", "documentation", "fintech", "banking", "finance", "medical", "clinic", "healthcare", "consulting", "law", "legal"], "nami landing page"),
]


@dataclass
class ResolvedDesign:
    source_name: str
    source_type: str  # "reference_raw_html", "reference_cached", "reference_autonomous", "project_existing"
    anti_slop_rules: str = ""
    raw_html: str = ""
    accent_color: str = ""
    bg_color: str = ""
    source_path: Optional[Path] = None
    full_raw_html: str = ""

    def is_active(self) -> bool:
        return bool(
            (self.full_raw_html and self.full_raw_html.strip())
            or (self.raw_html and self.raw_html.strip())
            or (self.source_path and self.source_path.exists())
        )


def _get_workspace_root() -> Path:
    return _WORKSPACE_ROOT


def _get_ui_dirs() -> Tuple[Path, Path]:
    """
    Locate UI reference directories with priority:
    1. skills/website_build/references/
    2. skills/hamza_taste/references/
    3. References/UI
    """
    ws = _get_workspace_root()
    ref_ui = ws / "skills" / "website_build" / "references"
    if not ref_ui.exists():
        ref_ui = ws / "skills" / "hamza_taste" / "references"
    if not ref_ui.exists() and (ws / "References" / "UI").exists():
        ref_ui = ws / "References" / "UI"

    if (ref_ui / "html").exists():
        html_dir = ref_ui / "html"
    else:
        html_dir = ref_ui

    return ref_ui, html_dir


def _get_available_templates() -> Tuple[List[Path], Path]:
    """Gather all available HTML templates across primary and fallback references (Zero MD files)."""
    ws = _get_workspace_root()
    primary_ref = ws / "skills" / "website_build" / "references"
    fallback_ref = ws / "References" / "new Designs"
    legacy_ref = ws / "References" / "UI"

    ref_ui, html_dir = _get_ui_dirs()

    available_html: list[Path] = []
    seen_stems: set[str] = set()

    for rdir in [primary_ref, fallback_ref, legacy_ref]:
        if rdir and rdir.exists():
            for p in rdir.rglob("*.html"):
                if p.is_file() and p.stat().st_size > 0:
                    norm = _norm_stem(p.stem)
                    if norm not in seen_stems:
                        seen_stems.add(norm)
                        available_html.append(p)

    return available_html, ref_ui


def extract_authentic_task(task: str) -> str:
    """Extract the authentic user task prompt, stripping injected agent prefixes and directives."""
    if not task:
        return ""
    text = task
    task_splits = re.split(r"(?:^|\n)\s*Task:\s*", text, flags=re.IGNORECASE)
    if len(task_splits) > 1:
        text = task_splits[-1]

    text = re.sub(r"\[ACTIVE SKILL:[^\]]*\].*?(?=(\n\s*Task:|\Z))", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"CRITICAL\s+[A-Z0-9\s/_\-]+\s+DIRECTIVE:.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"═+.*═+", "", text, flags=re.DOTALL)
    text = re.sub(r"##\s*🛑\s*NON-NEGOTIABLE\s+ANTI-SLOP.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--\s*\[Template content truncated.*?-->", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[(?:Stack|Theme|Scope|Sections):[^\]]+\]", "", text, flags=re.IGNORECASE)
    return text.strip()


def _norm_stem(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    clean = re.sub(r"[-_\s]+", "", name.lower())
    clean = clean.removesuffix(".html").removesuffix(".htm").removesuffix("design")
    return clean


def _sanitize_html_for_prompt(raw_html: str, max_chars: int = 50000) -> str:
    """Strip bulky base64 data URIs while preserving all CSS styles, animations, and layouts."""
    if not raw_html:
        return ""
    cleaned = re.sub(
        r'data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}',
        'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100%" height="100%" fill="%23222"/></svg>',
        raw_html,
    )
    cleaned = re.sub(r'd="[A-Za-z0-9\s,\.\-]{1000,}"', 'd="M0 0h24v24H0z"', cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n<!-- [Template content truncated for context budget] -->\n</body>\n</html>"
    return cleaned


def _get_anti_slop_rules() -> str:
    """Load canonical anti-slop rules from skills/website_build/SKILL.md."""
    ws = _get_workspace_root()
    skill_file = ws / "skills" / "website_build" / "SKILL.md"
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


def _keyword_present(text: str, keyword: str) -> bool:
    """Match a keyword as a whole word/phrase (avoids substrings like 'ui' in 'build')."""
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, text) is not None


def is_ui_task(task: str) -> bool:
    """Determine if a task involves Web/UI/Frontend development."""
    t = task.lower()
    backend_keywords = [
        "fastapi", "django", "flask", "express", "postgres", "database",
        "backend", "api endpoint", "script", "cli tool", "algorithm",
    ]
    ui_keywords = [
        "website", "web page", "webpage", "landing page", "landingpage",
        "ui", "ux", "frontend", "html", "css", "dashboard", "component",
        "saas", "portfolio", "web app", "webapp", "interface", "app layout",
        "header", "footer", "button", "cards", "pricing", "hero section"
    ]
    has_backend = any(_keyword_present(t, k) for k in backend_keywords)
    has_ui = any(_keyword_present(t, k) for k in ui_keywords)
    explicit_frontend = any(_keyword_present(t, k) for k in [
        "website", "web page", "webpage", "landing page", "html", "css",
        "frontend", "ui", "ux", "portfolio", "dashboard", "component",
        "interface", "web app", "webapp", "button", "cards", "pricing",
        "hero section", "header", "footer",
    ])
    if has_backend and not explicit_frontend:
        return False
    return has_ui


def is_redesign_or_explicit_request(task: str) -> bool:
    """Check if the user is asking to change/redesign/replace the design or use a specific reference."""
    t = task.lower()
    redesign_keywords = [
        "redesign", "change design", "new design", "update design", "change the design",
        "update the design", "change color", "change theme", "different theme",
        "different design", "regenerate", "make it like", "look like", "replace design",
        "start fresh", "rebuild", "re-create", "reference", "design system", "theme",
        "palette", "styling", "switch to", "make it exact", "according to this",
        "provided design", "loaded design", "design theme", "clean real estate",
        "entirely new", "from scratch", "start over", "brand new", "convert to",
        "convert into", "single file", "single-file", "single html", "single-html",
        "one index", "one html file", "static html", "static site",
        "no react", "without react", "not react",
    ]
    return any(k in t for k in redesign_keywords)


def _load_direct_html_reference(html_file: Optional[Path]) -> Optional[tuple[str, str, str, str, Optional[Path]]]:
    """
    Returns (source_name, source_type, raw_html, full_raw_html, source_path)
    Loads raw HTML directly with zero intermediate markdown extraction or MD files.
    """
    if html_file and html_file.exists():
        try:
            full_raw_html = html_file.read_text(encoding="utf-8", errors="ignore")
            raw_html = _sanitize_html_for_prompt(full_raw_html)
            clean_stem = re.sub(r"[-_\s]+", "-", html_file.stem).title()
            return clean_stem, "reference_raw_html", raw_html, full_raw_html, html_file
        except Exception as e:
            logger.warning("Failed reading raw html %s: %s", html_file, e)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic Catalog Matching System (Zero MD dependency)
# ─────────────────────────────────────────────────────────────────────────────

def _find_catalog_path() -> Optional[Path]:
    """Find catalog.json across reference directories."""
    ws = _get_workspace_root()
    candidates = [
        ws / "skills" / "website_build" / "references" / "catalog.json",
        ws / "References" / "new Designs" / "catalog.json",
        ws / "References" / "catalog.json",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def load_catalog() -> list[dict[str, Any]]:
    """Load structured template catalog from catalog.json."""
    templates: list[dict[str, Any]] = []
    cpath = _find_catalog_path()
    if cpath:
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "templates" in data:
                templates = list(data["templates"])
            elif isinstance(data, list):
                templates = list(data)
        except Exception as e:
            logger.warning("Failed reading catalog.json from %s: %s", cpath, e)

    existing_ids = {t.get("id") for t in templates if isinstance(t, dict)}

    canonical_fallbacks = [
        {
            "id": "saas",
            "name": "Saas Modern SaaS Platform",
            "relative_path": "1_landing_pages/saas.html",
            "scope": "landing_page",
            "theme": "dark_obsidian",
            "tags": ["saas", "software", "cloud", "api", "b2b", "subscription", "platform", "developer platform"],
            "bg_mode": "dark_obsidian",
            "primary_color": "#3b82f6",
            "flagship_rank": 100,
        },
        {
            "id": "dub",
            "name": "Dub Links Marketing & Conversion",
            "relative_path": "1_landing_pages/dub.html",
            "scope": "landing_page",
            "theme": "clean_minimal",
            "tags": ["dub", "marketing", "links", "conversion", "analytics", "real estate", "property", "properties", "mortgage", "realtor", "broker", "sales", "affiliate", "home"],
            "bg_mode": "light_mono",
            "primary_color": "#000000",
            "flagship_rank": 90,
        },
        {
            "id": "solvine",
            "name": "Solvine Modern SaaS",
            "relative_path": "1_landing_pages/solvine.html",
            "scope": "landing_page",
            "theme": "dark_obsidian",
            "tags": ["saas", "software", "cloud", "api", "b2b", "developer", "platform", "scheduling"],
            "bg_mode": "dark_obsidian",
            "primary_color": "#3b82f6",
            "flagship_rank": 80,
        },
        {
            "id": "racquet_club",
            "name": "Cirrus Racquet Club Luxury",
            "relative_path": "2_business_sites/racquet club.html",
            "scope": "business_site",
            "theme": "luxury_light",
            "tags": ["club", "sports", "tennis", "padel", "luxury", "hospitality", "hotel", "fitness", "lifestyle", "resort", "warm"],
            "bg_mode": "light_warm",
            "primary_color": "#1b2a1e",
            "flagship_rank": 95,
        },
        {
            "id": "hairline_grid",
            "name": "Hairline Grid Engineer Portfolio",
            "relative_path": "3_portfolios/Hairline Grid Portfolio.html",
            "scope": "portfolio",
            "theme": "clean_minimal",
            "tags": ["portfolio", "developer", "engineer", "designer", "resume", "minimal", "grid", "personal", "cv"],
            "bg_mode": "light_mono",
            "primary_color": "#09090b",
            "flagship_rank": 95,
        },
        {
            "id": "orbit_admin",
            "name": "Orbit Ops Modern Analytics Admin",
            "relative_path": "4_dashboards/orbit admin.html",
            "scope": "dashboard",
            "theme": "clean_minimal",
            "tags": ["admin", "dashboard", "analytics", "metrics", "ops", "monitoring", "saas", "table", "portal"],
            "bg_mode": "light_mono",
            "primary_color": "#111827",
            "flagship_rank": 90,
        },
        {
            "id": "standalone_ecosystem",
            "name": "Dense Infrastructure Ecosystem Console",
            "relative_path": "4_dashboards/Standalone Ecosystem.html",
            "scope": "dashboard",
            "theme": "dark_obsidian",
            "tags": ["infrastructure", "ecosystem", "network", "cloud", "backend", "console", "visualization", "cluster", "dashboard", "analytics", "admin"],
            "bg_mode": "dark_void",
            "primary_color": "#e48b59",
            "flagship_rank": 95,
        },
        {
            "id": "autonomus",
            "name": "Autonomus AI Agent Terminal Card",
            "relative_path": "5_components/autonomus.html",
            "scope": "component",
            "theme": "dark_obsidian",
            "tags": ["ai", "robotics", "bot", "assistant", "agent", "terminal", "dark", "vectors", "node", "autonomous"],
            "bg_mode": "dark_void",
            "primary_color": "#06b6d4",
            "flagship_rank": 90,
        },
    ]

    for fb in canonical_fallbacks:
        if fb["id"] not in existing_ids:
            templates.append(fb)

    return templates


def _find_template_file(
    template: dict[str, Any] | str | Path,
    available_html: Optional[list[Path]] = None,
) -> Optional[Path]:
    """Resolve the real on-disk HTML path for a catalog entry or path string."""
    ws = _get_workspace_root()
    if isinstance(template, (str, Path)):
        ref_path = str(template).strip()
    elif isinstance(template, dict):
        ref_path = str(template.get("relative_path", "") or template.get("path", "") or template.get("name", "")).strip()
    else:
        ref_path = str(template).strip()

    if not ref_path:
        return None

    ref_file_name = Path(ref_path).name
    target_norm = _norm_stem(ref_file_name)

    # 1. Direct path check (workspace-relative or absolute)
    p_direct = Path(ref_path)
    if not p_direct.is_absolute():
        p_direct = ws / ref_path
    if p_direct.exists() and p_direct.is_file() and p_direct.stat().st_size > 0:
        return p_direct

    # 2. Check candidate reference directories
    ref_roots = [
        ws / "skills" / "website_build" / "references",
        ws / "skills" / "hamza_taste" / "references",
        ws / "References" / "new Designs",
        ws / "References" / "UI",
    ]
    for root in ref_roots:
        if not root.exists():
            continue
        p = root / ref_path
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p

    # 3. Direct filename match under primary references
    wb_dir = ws / "skills" / "website_build" / "references"
    if wb_dir.exists():
        for p in wb_dir.rglob(ref_file_name):
            if p.is_file() and p.stat().st_size > 0:
                return p

    # 4. Search in available_html or auto-discover
    if available_html is None:
        try:
            available_html, _ = _get_available_templates()
        except Exception:
            available_html = []

    for p in available_html:
        if _norm_stem(p.name) == target_norm or target_norm in _norm_stem(p.name):
            if p.is_file() and p.stat().st_size > 0:
                return p

    # 5. Fallback in References/new Designs
    for p in (ws / "References" / "new Designs").rglob("*.html"):
        if _norm_stem(p.name) == target_norm and p.is_file() and p.stat().st_size > 0:
            return p

    return None


_SCOPE_DIRS: dict[str, str] = {
    "landing_page": "1_landing_pages",
    "business_site": "2_business_sites",
    "portfolio": "3_portfolios",
    "dashboard": "4_dashboards",
    "component": "5_components",
}


def _matches_scope(tmpl: dict[str, Any], target_scope: str) -> bool:
    norm_target = _normalize_scope(target_scope) or target_scope
    tmpl_scope = _normalize_scope(tmpl.get("scope"))
    if tmpl_scope and tmpl_scope == norm_target:
        return True
    rel_path = tmpl.get("relative_path", "").replace("\\", "/")
    expected_dir = _SCOPE_DIRS.get(norm_target, "")
    if expected_dir and expected_dir in rel_path:
        return True
    return False


def _normalize_scope(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.lower().strip().replace("-", "_").replace(" ", "_")
    if "land" in s:
        return "landing_page"
    if "busin" in s or "corp" in s or "company" in s:
        return "business_site"
    if "port" in s or "resume" in s or "cv" in s:
        return "portfolio"
    if "dash" in s or "admin" in s or _keyword_present(s, "os"):
        return "dashboard"
    if "comp" in s or "card" in s or "frame" in s or "hud" in s:
        return "component"
    return s


def _normalize_theme(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t = t.lower().strip().replace("-", "_").replace(" ", "_")
    if "dark" in t or "obsidian" in t or "void" in t:
        return "dark_obsidian"
    if "lux" in t or "gold" in t or "warm" in t:
        return "luxury_light"
    if "clean" in t or "min" in t or "light" in t or "white" in t:
        return "clean_minimal"
    if "bold" in t or "creat" in t or "vibrant" in t:
        return "creative_bold"
    if "edit" in t or "paper" in t:
        return "editorial_warm"
    return t


def _infer_scope(task_text: str) -> Optional[str]:
    t = task_text.lower()
    if any(k in t for k in ["dashboard", "admin", "analytics", "metrics", "console", "portal", "ecosystem"]):
        return "dashboard"
    if any(k in t for k in ["portfolio", "resume", "cv", "personal site", "showcase"]):
        return "portfolio"
    if any(k in t for k in ["business", "corporate", "law firm", "consulting", "restaurant", "club", "hotel", "resort", "hospitality", "store"]):
        return "business_site"
    if any(k in t for k in ["component", "card", "frame", "button", "widget", "hud"]):
        return "component"
    if any(k in t for k in ["landing", "saas", "waitlist", "website", "web page", "webpage"]):
        return "landing_page"
    return None


def _infer_theme(task_text: str) -> Optional[str]:
    t = task_text.lower()
    if any(k in t for k in ["dark", "obsidian", "void", "cyber", "neon", "matrix", "black"]):
        return "dark_obsidian"
    if any(k in t for k in ["luxury", "gold", "club", "warm", "tennis", "hospitality", "hotel", "resort", "premium"]):
        return "luxury_light"
    if any(k in t for k in ["clean", "minimal", "minimalist", "light", "white", "simple", "docs"]):
        return "clean_minimal"
    if any(k in t for k in ["bold", "creative", "vibrant", "crazy", "playful"]):
        return "creative_bold"
    if any(k in t for k in ["editorial", "paper", "scrapbook"]):
        return "editorial_warm"
    return None


def resolve_from_catalog(
    scope: Optional[str] = None,
    theme: Optional[str] = None,
    task_text: str = "",
) -> Optional[dict[str, Any]]:
    """Deterministic catalog matcher pointing directly to raw HTML files."""
    available_html, _ = _get_available_templates()
    templates = load_catalog()
    if not templates:
        return None

    authentic_task = extract_authentic_task(task_text)
    task_clean = authentic_task.lower() if authentic_task else task_text.lower()

    req_scope = _normalize_scope(scope)
    if not req_scope:
        m_sc = re.search(r"\[Scope:\s*([a-zA-Z0-9_\-]+)\]", task_text, re.I)
        if m_sc:
            req_scope = _normalize_scope(m_sc.group(1))
    if not req_scope:
        req_scope = _infer_scope(task_clean)

    req_theme = _normalize_theme(theme)
    if not req_theme:
        m_th = re.search(r"\[Theme:\s*([a-zA-Z0-9_\-]+)\]", task_text, re.I)
        if m_th:
            req_theme = _normalize_theme(m_th.group(1))
    if not req_theme:
        req_theme = _infer_theme(task_clean)

    if req_scope:
        matching_scope_templates = [t for t in templates if _matches_scope(t, req_scope)]
        if matching_scope_templates:
            templates = matching_scope_templates

    task_words = set(re.findall(r"[a-z0-9]+", task_clean))
    scored_candidates = []

    for tmpl in templates:
        file_path = _find_template_file(tmpl, available_html)
        if not file_path:
            continue

        score = tmpl.get("flagship_rank", 50)

        tmpl_scope = tmpl.get("scope", "")
        if req_scope:
            if tmpl_scope == req_scope or _matches_scope(tmpl, req_scope):
                score += 30
            else:
                score -= 20

        tmpl_theme = tmpl.get("theme", "")
        if req_theme:
            if tmpl_theme == req_theme:
                score += 20
            elif ("light" in req_theme and "light" in tmpl_theme) or ("dark" in req_theme and "dark" in tmpl_theme):
                score += 8
            else:
                score -= 10

        tags = [t.lower().strip() for t in tmpl.get("tags", [])]
        for tag in tags:
            tag_words = tag.split()
            if len(tag_words) == 1:
                if tag in task_words:
                    score += 12
            else:
                if tag in task_clean:
                    score += 18
                elif any(w in task_words for w in tag_words if len(w) > 3):
                    score += 6

        id_words = re.findall(r"[a-z0-9]+", tmpl.get("id", "").lower())
        for w in id_words:
            if len(w) > 3 and w in task_words:
                score += 10

        name_words = re.findall(r"[a-z0-9]+", tmpl.get("name", "").lower())
        for w in name_words:
            if len(w) > 3 and w in task_words:
                score += 8

        entry = dict(tmpl)
        entry["file_path"] = file_path
        entry["score"] = score
        scored_candidates.append(entry)

    if not scored_candidates:
        return None

    scored_candidates.sort(key=lambda x: (x["score"], -len(x.get("name", "")), x.get("id", "")), reverse=True)
    return scored_candidates[0]


# ─────────────────────────────────────────────────────────────────────────────
# Main Design Resolution Engine (100% Direct HTML, Zero MD / Extraction)
# ─────────────────────────────────────────────────────────────────────────────

def resolve_design(
    task: str,
    session_memory: Optional[dict] = None,
    repo_path: Optional[str | Path] = None,
    scope: Optional[str] = None,
    theme: Optional[str] = None,
) -> ResolvedDesign:
    """
    Deterministically resolves design DIRECTLY from raw HTML reference templates:
      1. Priority 1: User-explicit reference name match in task (e.g. "use dub landing page", "saas.html").
      2. Priority 2: Session memory / persistent memory for active_design_path.
      3. Priority 3: Deterministic Catalog & Semantic Category match.
      4. Priority 4: Existing project repository index.html raw HTML.
      5. Priority 5: Autonomous Agent Choice (Deterministic Catalog Tag Matcher).
    """
    anti_slop = _get_anti_slop_rules()
    available_html, _ = _get_available_templates()

    authentic_task = extract_authentic_task(task)
    task_clean = authentic_task.lower() if authentic_task else task.lower()
    has_redesign_intent = is_redesign_or_explicit_request(authentic_task or task)

    # 1. Priority 1: User-Explicit Reference Match in task
    matched_html: Optional[Path] = None
    task_words = set(re.findall(r"[a-z0-9]+", task_clean))

    def _is_explicit_match(stem_str: str) -> bool:
        if stem_str.lower() in ("design-system", "design_system", "design system"):
            return False
        clean_stem = re.sub(r"[-_\s]+", " ", stem_str.lower())
        clean_stem = clean_stem.replace(".html", "").replace(".htm", "").replace("design", "").strip()
        stem_tokens = [t for t in clean_stem.split() if t not in ("landing", "page", "the", "a", "an", "and", "component", "system")]
        if not stem_tokens:
            stem_tokens = clean_stem.split()
        if stem_tokens and all(tok in task_words for tok in stem_tokens):
            return True
        if clean_stem and len(clean_stem) >= 3 and re.search(rf"\b{re.escape(clean_stem)}\b", task_clean):
            return True
        return False

    for p in available_html:
        if _is_explicit_match(p.stem):
            matched_html = p
            break

    if matched_html:
        res = _load_direct_html_reference(matched_html)
        if res:
            name, stype, raw_h, full_raw_h, s_path = res
            return ResolvedDesign(
                source_name=name,
                source_type=stype,
                raw_html=raw_h,
                anti_slop_rules=anti_slop,
                source_path=s_path,
                full_raw_html=full_raw_h,
            )

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
            res = _load_direct_html_reference(p)
            if res:
                name, stype, raw_h, full_raw_h, s_path = res
                return ResolvedDesign(
                    source_name=name,
                    source_type="reference_cached",
                    raw_html=raw_h,
                    anti_slop_rules=anti_slop,
                    source_path=s_path,
                    full_raw_html=full_raw_h,
                )
        else:
            target_norm = _norm_stem(str(candidate_design_target))
            matched_h = next((h for h in available_html if _norm_stem(h.name) == target_norm), None)
            if matched_h:
                res = _load_direct_html_reference(matched_h)
                if res:
                    name, stype, raw_h, full_raw_h, s_path = res
                    return ResolvedDesign(
                        source_name=name,
                        source_type=stype,
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                        source_path=s_path,
                        full_raw_html=full_raw_h,
                    )

    # 3. Priority 3: Deterministic Catalog & Semantic Category Match
    explicit_scope = _normalize_scope(scope)
    if not explicit_scope:
        m_sc = re.search(r"\[Scope:\s*([a-zA-Z0-9_\-]+)\]", task, re.I)
        if m_sc:
            explicit_scope = _normalize_scope(m_sc.group(1))

    explicit_theme = _normalize_theme(theme)
    if not explicit_theme:
        m_th = re.search(r"\[Theme:\s*([a-zA-Z0-9_\-]+)\]", task, re.I)
        if m_th:
            explicit_theme = _normalize_theme(m_th.group(1))

    if explicit_scope or explicit_theme:
        cat_match = resolve_from_catalog(scope=explicit_scope, theme=explicit_theme, task_text=authentic_task)
        if cat_match and cat_match.get("file_path"):
            cand_file = cat_match["file_path"]
            res = _load_direct_html_reference(cand_file)
            if res:
                name, stype, raw_h, full_raw_h, s_path = res
                return ResolvedDesign(
                    source_name=name,
                    source_type=stype,
                    raw_html=raw_h,
                    anti_slop_rules=anti_slop,
                    accent_color=cat_match.get("primary_color", ""),
                    bg_color=cat_match.get("bg_mode", ""),
                    source_path=s_path,
                    full_raw_html=full_raw_h,
                )

    # Semantic keyword routing across curated reference templates
    inferred_scope = explicit_scope or _infer_scope(task_clean)
    for keywords, target_stem in _SEMANTIC_ROUTES:
        if any(kw in task_clean for kw in keywords):
            target_norm = _norm_stem(target_stem)
            cat_html = next((h for h in available_html if target_norm in _norm_stem(h.name) or _norm_stem(h.name) in target_norm), None)

            is_comp = False
            if cat_html and ("5_components" in str(cat_html).replace("\\", "/") or "component" in cat_html.name.lower()):
                is_comp = True
            elif target_stem in ("aura frame", "nexus", "autonomus", "skeumorphic spatial component"):
                is_comp = True

            if is_comp:
                wants_comp = (inferred_scope == "component") or any(
                    ck in task_clean for ck in ["component", "card", "frame", "hud", "widget", "button"]
                )
                if not wants_comp and inferred_scope in ("landing_page", "portfolio", "business_site", "dashboard"):
                    continue

            if cat_html:
                res = _load_direct_html_reference(cat_html)
                if res:
                    name, stype, raw_h, full_raw_h, s_path = res
                    return ResolvedDesign(
                        source_name=name,
                        source_type=stype,
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                        source_path=s_path,
                        full_raw_html=full_raw_h,
                    )

    # 4. Priority 4: Existing Project Design Raw HTML (ONLY when NOT a redesign request)
    if repo_path and not has_redesign_intent:
        r_path = Path(repo_path).resolve()
        if r_path.exists() and r_path.is_dir():
            repo_html = r_path / "index.html"
            repo_css = r_path / "style.css"
            if repo_html.exists() and repo_html.stat().st_size > 50:
                res = _load_direct_html_reference(repo_html)
                if res:
                    _, _, raw_h, full_raw_h, s_path = res
                    return ResolvedDesign(
                        source_name=f"Project ({r_path.name})",
                        source_type="project_existing",
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                        source_path=s_path,
                        full_raw_html=full_raw_h,
                    )
            elif repo_css.exists() and repo_css.stat().st_size > 50:
                try:
                    fake_html = f"<html><head><style>{repo_css.read_text(encoding='utf-8', errors='ignore')}</style></head><body></body></html>"
                    raw_h = _sanitize_html_for_prompt(fake_html)
                    return ResolvedDesign(
                        source_name=f"Project CSS ({r_path.name})",
                        source_type="project_existing",
                        raw_html=raw_h,
                        anti_slop_rules=anti_slop,
                        full_raw_html=fake_html,
                    )
                except Exception:
                    pass

    # 5. Priority 5: Autonomous Agent Choice (Deterministic Catalog Tag Matcher)
    cat_match = resolve_from_catalog(scope=scope, theme=theme, task_text=authentic_task)
    if cat_match and cat_match.get("file_path"):
        cand_file = cat_match["file_path"]
        res = _load_direct_html_reference(cand_file)
        if res:
            name, stype, raw_h, full_raw_h, s_path = res
            return ResolvedDesign(
                source_name=f"{name} (Autonomous Choice)",
                source_type="reference_autonomous",
                raw_html=raw_h,
                anti_slop_rules=anti_slop,
                accent_color=cat_match.get("primary_color", ""),
                bg_color=cat_match.get("bg_mode", ""),
                source_path=s_path,
                full_raw_html=full_raw_h,
            )

    # Ultimate fallback if no template files are present
    return ResolvedDesign(
        source_name="Hamza Taste Master",
        source_type="default",
        raw_html="",
        anti_slop_rules=anti_slop,
    )


def format_design_prompt(design: ResolvedDesign) -> str:
    """Format the direct raw HTML reference template into an optimized prompt block."""
    if not design or not design.is_active():
        return ""

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
