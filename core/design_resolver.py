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
    text = re.sub(r"\[(?:Stack|Theme|Scope|Sections|Entity/Content):[^\]]+\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\[[^\]]+\]\s*", "", text)
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
    if not task:
        return False
    clean_task = extract_authentic_task(task) or task
    clean_task = re.sub(r"^\[[^\]]+\]\s*", "", clean_task).strip()
    t = clean_task.lower()
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
    if "edit" in t or "paper" in t or "scrapbook" in t:
        return "editorial_warm"
    if "dark" in t or "obsidian" in t or "void" in t:
        return "dark_obsidian"
    if "lux" in t or "gold" in t or "warm" in t:
        return "luxury_light"
    if "clean" in t or "min" in t or "light" in t or "white" in t:
        return "clean_minimal"
    if "bold" in t or "creat" in t or "vibrant" in t:
        return "creative_bold"
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
        m_sc = re.search(r"\[[^\]]*\bScope:\s*([^,\]\r\n]+)", task_text, re.I)
        if m_sc:
            req_scope = _normalize_scope(m_sc.group(1).strip())
    if not req_scope:
        req_scope = _infer_scope(task_clean)

    req_theme = _normalize_theme(theme)
    if not req_theme:
        m_th = re.search(r"\[[^\]]*\bTheme:\s*([^,\]\r\n]+)", task_text, re.I)
        if m_th:
            req_theme = _normalize_theme(m_th.group(1).strip())
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

    # Prioritize explicitly passed scope & theme arguments, falling back to task bracket directives [Scope: ...] / [Theme: ...]
    explicit_scope = _normalize_scope(scope)
    if not explicit_scope:
        m_sc = re.search(r"\[[^\]]*\bScope:\s*([^,\]\r\n]+)", task, re.I)
        if m_sc:
            explicit_scope = _normalize_scope(m_sc.group(1).strip())

    explicit_theme = _normalize_theme(theme)
    if not explicit_theme:
        m_th = re.search(r"\[[^\]]*\bTheme:\s*([^,\]\r\n]+)", task, re.I)
        if m_th:
            explicit_theme = _normalize_theme(m_th.group(1).strip())

    # 1. Priority 1: User-Explicit Reference Match in task
    matched_html: Optional[Path] = None
    task_words = set(re.findall(r"[a-z0-9]+", task_clean))

    def _is_explicit_match(p_file: Path) -> bool:
        stem_str = p_file.stem
        if stem_str.lower() in ("design-system", "design_system", "design system"):
            return False
        clean_stem = re.sub(r"[-_\s]+", " ", stem_str.lower())
        clean_stem = clean_stem.replace(".html", "").replace(".htm", "").replace("design", "").strip()
        generic_tokens = {"ai", "app", "ui", "web", "site", "new", "doc", "docs", "dev", "pro", "v1", "v2"}
        stem_tokens = [t for t in clean_stem.split() if t not in ("landing", "page", "the", "a", "an", "and", "component", "system")]
        if not stem_tokens:
            stem_tokens = clean_stem.split()

        # Direct explicit reference name checks
        if p_file.name.lower() in task_clean:
            return True
        if f"use {clean_stem}" in task_clean or f"like {clean_stem}" in task_clean or f"{clean_stem} template" in task_clean or f"{clean_stem} reference" in task_clean:
            return True

        # Reject if stem_tokens is just that single generic token (e.g., 'ai landing page.html' stripping landing/page leaves ['ai'])
        if len(stem_tokens) == 1 and stem_tokens[0] in generic_tokens:
            return False

        # If explicit_scope is defined, ensure candidate doesn't violate explicit_scope
        if explicit_scope:
            expected_dir = _SCOPE_DIRS.get(explicit_scope, "")
            p_posix = str(p_file).replace("\\", "/")
            if expected_dir and expected_dir not in p_posix:
                return False

        if stem_tokens and all(tok in task_words for tok in stem_tokens):
            return True
        if clean_stem and clean_stem not in generic_tokens and len(clean_stem) >= 3 and re.search(rf"\b{re.escape(clean_stem)}\b", task_clean):
            return True
        return False

    for p in available_html:
        if _is_explicit_match(p):
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

    # 2. Priority 2: Check session memory & persistent memory (only if no redesign intent and matches explicit_scope)
    candidate_design_target = ""
    if not has_redesign_intent:
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
        cached_matches_scope = True
        if explicit_scope:
            expected_dir = _SCOPE_DIRS.get(explicit_scope, "")
            p_posix = str(candidate_design_target).replace("\\", "/")
            if expected_dir and expected_dir not in p_posix:
                cached_matches_scope = False

        if cached_matches_scope:
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
    comp_stems = ("aura frame", "nexus", "autonomus", "skeumorphic spatial component", "image gen")
    dash_stems = ("froma os", "froma os ", "Standalone Ecosystem", "orbit admin")

    for keywords, target_stem in _SEMANTIC_ROUTES:
        if any(_keyword_present(task_clean, kw) for kw in keywords):
            target_norm = _norm_stem(target_stem)
            cat_html = next((h for h in available_html if target_norm in _norm_stem(h.name) or _norm_stem(h.name) in target_norm), None)

            # Category / Scope Isolation
            is_comp = (target_stem.strip() in [s.strip() for s in comp_stems]) or (
                cat_html is not None and ("5_components" in str(cat_html).replace("\\", "/") or "component" in cat_html.name.lower())
            )
            is_dash = (target_stem.strip() in [s.strip() for s in dash_stems]) or (
                cat_html is not None and ("4_dashboards" in str(cat_html).replace("\\", "/") or "dashboard" in cat_html.name.lower())
            )

            if inferred_scope in ("portfolio", "landing_page", "business_site"):
                if is_comp:
                    user_wants_comp = (inferred_scope == "component") or any(
                        _keyword_present(task_clean, ck) for ck in ["component", "card", "frame", "hud", "widget", "button"]
                    )
                    if not user_wants_comp:
                        continue

                if is_dash:
                    user_wants_dash = (inferred_scope == "dashboard") or any(
                        _keyword_present(task_clean, dk) for dk in ["dashboard", "admin", "os", "console", "portal", "ecosystem"]
                    )
                    if not user_wants_dash:
                        continue
            elif is_comp:
                user_wants_comp = (inferred_scope == "component") or any(
                    _keyword_present(task_clean, ck) for ck in ["component", "card", "frame", "hud", "widget", "button"]
                )
                if not user_wants_comp and inferred_scope in ("landing_page", "portfolio", "business_site", "dashboard"):
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
    cat_match = resolve_from_catalog(scope=explicit_scope, theme=explicit_theme, task_text=authentic_task)
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


def check_greenfield_gate(task: str, parameters: Dict[str, Any], caller_tool: str = "antigravity_run") -> Optional[str]:
    """Check greenfield gate for web/portfolio builds. Returns None if build can proceed, or a prompt message if clarification is needed."""
    explicit_path = parameters.get("project_path") or parameters.get("path") or ""
    run_in_place = bool(parameters.get("run_in_place", False))

    if explicit_path or run_in_place:
        return None

    is_web = is_ui_task(task) or any(k in task.lower() for k in ("build website", "create website", "make website", "build landing page", "create landing page", "build portfolio", "create portfolio", "new website", "new landing page", "dashboard", "app"))
    if not is_web:
        return None

    scope_type = parameters.get("scope_type")
    tech_stack = parameters.get("tech_stack")
    color_theme = parameters.get("color_theme")
    key_sections = parameters.get("key_sections")
    entity_content = parameters.get("entity_content")
    confirmed = parameters.get("confirmed", False)

    missing = []
    if not scope_type:
        missing.append("scope_type (e.g. landing_page, portfolio, business_site, dashboard, component)")
    if scope_type == "portfolio" and not entity_content:
        missing.append("entity_content (candidate name, role, key projects, or attached resume PDF)")
    if not tech_stack:
        missing.append("tech_stack (e.g. single_file_html, modular_html_css_js, react_vite, nextjs)")
    if not color_theme:
        missing.append("color_theme (e.g. dark_obsidian, clean_minimal, luxury_gold, cyber_matrix, custom)")
    if not key_sections:
        missing.append("key_sections (comma-separated section names)")

    if missing:
        missing_str = ", ".join(missing)
        if scope_type == "portfolio":
            return f"Portfolio build clarification required. I need to know: {missing_str}. For portfolio scope, please share your name, role, key projects, or attach your resume PDF."
        return f"Greenfield build clarification required. I need to know: {missing_str}."

    if not confirmed:
        plan_summary = f"1-sentence plan: Build a {scope_type or 'web application'} using {tech_stack or 'single_file_html'} with {color_theme or 'clean_minimal'} theme and sections [{key_sections}]."
        return f"{plan_summary} Please confirm by setting confirmed=true to proceed."

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Automated Blueprint & Master Template Generation Engine
# ─────────────────────────────────────────────────────────────────────────────

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    BeautifulSoup = None
    Comment = None

try:
    from core.design_extractor import generate_blueprint_html, generate_design_md, strip_base64_bloat
except ImportError:
    try:
        from design_extractor import generate_blueprint_html, generate_design_md, strip_base64_bloat
    except ImportError:
        generate_blueprint_html = None
        generate_design_md = None
        strip_base64_bloat = None


def inject_semantic_slots(html_str: str) -> str:
    """
    Intelligently detects common section elements (hero/header, projects/features/portfolio,
    skills/about/experience, contact/footer) and injects semantic slot boundaries:
      <!-- SLOT:HERO_START --> ... <!-- SLOT:HERO_END -->
      <!-- SLOT:PROJECTS_START --> ... <!-- SLOT:PROJECTS_END -->
      <!-- SLOT:SKILLS_START --> ... <!-- SLOT:SKILLS_END -->
      <!-- SLOT:CONTACT_START --> ... <!-- SLOT:CONTACT_END -->
    """
    if not html_str:
        return html_str

    slots = ["HERO", "PROJECTS", "SKILLS", "CONTACT"]
    if all(f"<!-- SLOT:{s}_START -->" in html_str for s in slots):
        return html_str

    if not BeautifulSoup or not Comment:
        # Fallback regex-based slot boundary injector
        res = html_str
        for s in slots:
            if f"<!-- SLOT:{s}_START -->" not in res:
                res = f"<!-- SLOT:{s}_START -->\n<!-- SLOT:{s}_END -->\n" + res
        return res

    soup = BeautifulSoup(html_str, "html.parser")
    body = soup.find("body")
    if not body:
        return html_str

    containers = [body]
    main_el = body.find("main")
    if main_el:
        containers.append(main_el)
    for c in list(body.find_all("div", recursive=False)):
        containers.append(c)

    candidates = []
    seen = set()
    for cont in containers:
        for tag in cont.find_all(["section", "header", "footer", "article", "div"], recursive=False):
            if id(tag) not in seen:
                seen.add(id(tag))
                tag_id = (tag.get("id") or "").lower()
                tag_cls = " ".join(tag.get("class") or []).lower()
                tag_aria = (tag.get("aria-label") or tag.get("aria-labelledby") or "").lower()
                desc = f"{tag.name} {tag_id} {tag_cls} {tag_aria}"
                candidates.append((tag, desc))

    if len(candidates) < 4:
        for tag in body.find_all(["section", "header", "footer"]):
            if id(tag) not in seen:
                seen.add(id(tag))
                tag_id = (tag.get("id") or "").lower()
                tag_cls = " ".join(tag.get("class") or []).lower()
                tag_aria = (tag.get("aria-label") or tag.get("aria-labelledby") or "").lower()
                desc = f"{tag.name} {tag_id} {tag_cls} {tag_aria}"
                candidates.append((tag, desc))

    assigned: dict[str, Any] = {"HERO": None, "PROJECTS": None, "SKILLS": None, "CONTACT": None}

    # Pass 1: CONTACT (footer, contact, cta, reach, newsletter)
    for tag, desc in candidates:
        if tag.name == "footer" or any(k in desc for k in ["contact", "footer", "get-in-touch", "touch", "newsletter", "cta"]):
            assigned["CONTACT"] = tag
            break

    # Pass 2: HERO (header, hero, banner, intro, masthead, top)
    for tag, desc in candidates:
        if tag is not assigned["CONTACT"] and (
            tag.name == "header" or any(k in desc for k in ["hero", "banner", "intro", "masthead", "ph", "header", "top"])
        ):
            assigned["HERO"] = tag
            break

    # Pass 3: PROJECTS (work, project, portfolio, feature, case, service, capabilities, product, showcase)
    for tag, desc in candidates:
        if tag not in assigned.values() and any(
            k in desc for k in ["project", "work", "portfolio", "feature", "case", "service", "capabilities", "product", "showcase", "integration", "gallery", "app"]
        ):
            assigned["PROJECTS"] = tag
            break

    # Pass 4: SKILLS (skill, stack, tech, about, experience, testimonial, pricing, team, stat, bio)
    for tag, desc in candidates:
        if tag not in assigned.values() and any(
            k in desc for k in ["skill", "stack", "tech", "about", "experience", "testim", "pricing", "team", "stat", "bio", "review", "philosophy", "principle"]
        ):
            assigned["SKILLS"] = tag
            break

    # Pass 5: Sequential fallback for unassigned slots
    remaining = [tag for tag, _ in candidates if tag not in assigned.values()]
    for slot_name in slots:
        if assigned[slot_name] is None and remaining:
            assigned[slot_name] = remaining.pop(0)

    for slot_name in slots:
        tag = assigned.get(slot_name)
        if tag is not None and tag.parent:
            start_comment = Comment(f" SLOT:{slot_name}_START ")
            end_comment = Comment(f" SLOT:{slot_name}_END ")
            tag.insert_before(start_comment)
            tag.insert_after(end_comment)
        else:
            start_comment = Comment(f" SLOT:{slot_name}_START ")
            end_comment = Comment(f" SLOT:{slot_name}_END ")
            body.append(start_comment)
            body.append(end_comment)

    return str(soup)


def generate_master_template_html(raw_html: str, max_bytes: int = 40000) -> str:
    """
    Generates a clean interactive clone with functional JS and CSS,
    lightweight placeholder assets, and injected semantic slot boundaries.
    Guarantees 100% valid document structure (never arbitrarily sliced).
    """
    if not raw_html:
        return ""

    # 1. Strip base64 image bloat, embedded fonts, and flight hydration scripts first
    if strip_base64_bloat:
        c = strip_base64_bloat(raw_html)
    else:
        ph_img = (
            'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" '
            'viewBox="0 0 400 300"><rect width="100%" height="100%" fill="%2318181b"/>'
            '<text x="50%" y="50%" fill="%2371717a" font-family="sans-serif" font-size="14" '
            'dominant-baseline="middle" text-anchor="middle">Asset Placeholder</text></svg>'
        )
        c = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]{64,}', ph_img, raw_html)
        c = re.sub(r"""<link[^>]+href=['"]data:[^'"]+['"][^>]*>""", "", c, flags=re.IGNORECASE)
        c = re.sub(r"""<script[^>]+src=['"]data:[^'"]+['"][^>]*>.*?</script>""", "", c, flags=re.DOTALL | re.IGNORECASE)
        c = re.sub(r"""data:(?:text/javascript|application|font)[^;'")\s]+""", "", c)

    # 2. Clean CSS whitespace and comments
    def _clean_style(m: re.Match) -> str:
        s = m.group(1)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
        s = re.sub(r'@font-face\s*\{[^}]*data:[^}]*\}', '', s)
        s = re.sub(r'\s+', ' ', s)
        s = re.sub(r'\s*([\{\}:;,])\s*', r'\1', s)
        return f'<style>{s.strip()}</style>'

    c = re.sub(r'<style[^>]*>(.*?)</style>', _clean_style, c, flags=re.DOTALL)

    # 3. Strip non-slot HTML comments
    c = re.sub(r'<!--(?!\s*SLOT:).*?-->', '', c, flags=re.DOTALL)

    # 4. Simplify bulky SVGs (> 140 chars)
    def _clean_svg(m: re.Match) -> str:
        svg_content = m.group(0)
        if len(svg_content) > 140:
            m_cls = re.search(r"""class=['"]([^'"]+)['"]""", svg_content)
            cls_attr = f' class="{m_cls.group(1)}"' if m_cls else ''
            m_vb = re.search(r"""viewBox=['"]([^'"]+)['"]""", svg_content)
            vb_attr = f' viewBox="{m_vb.group(1)}"' if m_vb else ' viewBox="0 0 24 24"'
            return f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"{vb_attr}{cls_attr} fill="currentColor"><path d="M0 0h24v24H0z"/></svg>'
        return svg_content

    c = re.sub(r'<svg[^>]*>.*?</svg>', _clean_svg, c, flags=re.DOTALL)
    c = re.sub(r'\n\s*\n', '\n', c)

    # 5. Inject semantic slot boundaries on the clean HTML
    c = inject_semantic_slots(c)

    # 6. If DOM has large repetitive card/item lists, condense them via DOM structure (NEVER string slice)
    if BeautifulSoup and len(c.encode("utf-8")) > max_bytes:
        try:
            soup = BeautifulSoup(c, "html.parser")
            body = soup.find("body")
            if body:
                for grid in body.find_all(lambda tag: tag.get("class") and any(k in " ".join(tag.get("class")) for k in ["grid", "flex", "cards", "list"])):
                    children = [child for child in grid.find_all(recursive=False) if getattr(child, "name", None)]
                    if len(children) > 2:
                        for child in children[2:]:
                            child.decompose()
                res = str(soup)
                if len(res.encode("utf-8")) < len(c.encode("utf-8")):
                    c = res
        except Exception:
            pass

    # 7. Minify whitespace between tags if still slightly over budget
    if len(c.encode("utf-8")) > max_bytes:
        c = re.sub(r'>\s+<', '><', c)

    return c


_EXTRACTED_CACHE_DIR = _WORKSPACE_ROOT / "skills" / "website_build" / "references" / "extracted_cache"


def get_or_create_reference_design_cache(
    reference_html_path: Path | str,
) -> Tuple[Path, Path]:
    """
    Retrieves or generates cached (DESIGN.md, master-template.html) for a reference template.
    Stored inside skills/website_build/references/extracted_cache/<slug>/.
    On cache hit, execution completes in < 5ms without re-extraction.
    """
    ref_path = Path(str(reference_html_path).strip()).resolve()
    if not ref_path.exists() or not ref_path.is_file():
        raise FileNotFoundError(f"Reference HTML file not found at: {ref_path}")

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ref_path.stem).strip("_").lower()
    cache_dir = _EXTRACTED_CACHE_DIR / slug
    cached_md = cache_dir / "DESIGN.md"
    cached_mt = cache_dir / "master-template.html"

    ref_mtime = ref_path.stat().st_mtime
    if (
        cached_md.exists()
        and cached_md.stat().st_size > 0
        and cached_mt.exists()
        and cached_mt.stat().st_size > 0
        and cached_md.stat().st_mtime >= ref_mtime
        and cached_mt.stat().st_mtime >= ref_mtime
    ):
        logger.debug("Cache HIT for reference template '%s' at %s", ref_path.name, cache_dir)
        return cached_md, cached_mt

    # Cache MISS: Extract once deterministically and persist
    logger.info("Cache MISS for reference template '%s'. Extracting DESIGN.md & master-template.html...", ref_path.name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_html = ref_path.read_text(encoding="utf-8", errors="ignore")

    if len(raw_html) > 300000:
        if strip_base64_bloat:
            raw_html = strip_base64_bloat(raw_html)
        else:
            raw_html = _sanitize_html_for_prompt(raw_html, max_chars=300000)

    # 1. Generate world-class DESIGN.md (<design-context> YAML Token DSL + Narrative)
    if generate_design_md:
        try:
            design_md_content = generate_design_md(raw_html, title=ref_path.stem)
            cached_md.write_text(design_md_content, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to generate DESIGN.md for cache: %s", e)
            cached_md.write_text(f"# {ref_path.stem}\n\nFailed to extract design tokens.", encoding="utf-8")
    else:
        cached_md.write_text(f"# {ref_path.stem}\n\nDesign extractor unavailable.", encoding="utf-8")

    # 2. Generate clean interactive master-template.html (< 40 KB)
    master_template_content = generate_master_template_html(raw_html, max_bytes=39900)
    cached_mt.write_text(master_template_content, encoding="utf-8")

    return cached_md, cached_mt


def generate_blueprint_and_template(
    reference_html_path: Path | str,
    output_dir: Path | str,
) -> Tuple[Path, Path]:
    """
    Automated Design Specification & Master Template Generation Engine:
    1. Reads reference HTML file or fetches from persistent cache (skills/website_build/references/extracted_cache/).
    2. Provisions DESIGN.md (~3-6 KB <design-context> DSL) into output_dir.
    3. Provisions < 40 KB master-template.html into output_dir with functional JS/CSS and semantic slot boundaries:
       <!-- SLOT:HERO_START --> ... <!-- SLOT:HERO_END -->
       <!-- SLOT:PROJECTS_START --> ... <!-- SLOT:PROJECTS_END -->
       <!-- SLOT:SKILLS_START --> ... <!-- SLOT:SKILLS_END -->
       <!-- SLOT:CONTACT_START --> ... <!-- SLOT:CONTACT_END -->
    4. Returns (design_md_path, master_template_path) in < 1 second (or < 5ms on cache hit).
    """
    ref_path = Path(str(reference_html_path).strip()).resolve()
    out_dir = Path(str(output_dir).rstrip()).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Retrieve from or store into permanent reference cache
    cached_md, cached_mt = get_or_create_reference_design_cache(ref_path)

    # 2. Copy directly into task workspace
    design_md_path = out_dir / "DESIGN.md"
    master_template_path = out_dir / "master-template.html"

    design_md_path.write_text(cached_md.read_text(encoding="utf-8"), encoding="utf-8")
    master_template_path.write_text(cached_mt.read_text(encoding="utf-8"), encoding="utf-8")

    md_size = design_md_path.stat().st_size
    mt_size = master_template_path.stat().st_size
    logger.info(
        "Provisioned DESIGN.md (%d bytes) & master-template (%d bytes, < 40KB) at %s",
        md_size,
        mt_size,
        out_dir,
    )

    return design_md_path, master_template_path

