"""
Master Template Builder for ZEZO Website Build Subsystem.

Converts extracted reference designs and raw HTML templates into lightweight,
budget-constrained master-template.html files (< 40,000 bytes) with cleanly injected
semantic slot boundaries:
  <!-- SLOT: HEADER -->
  <!-- SLOT: MAIN -->
  <!-- SLOT: FOOTER -->
  <!-- SLOT: MODAL -->

Applies cumulative idempotent reduction stages:
  Stage 1: Strip base64 embedded images/fonts/scripts via strip_base64_images.
  Stage 2: Compact CSS (strip comments, collapse whitespace, minify {:;,}).
  Stage 3: Strip non-SLOT HTML comments.
  Stage 4: Simplify bulky SVGs (> 140 chars) to lightweight placeholders.
  Stage 5: Condense repetitive card/grid/flex lists (decompose beyond first 2).
  Stage 6: Minify inter-tag whitespace.
  Stage 7: Drop script tags entirely if still over budget.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, TYPE_CHECKING

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    BeautifulSoup = None  # type: ignore
    Comment = None  # type: ignore

try:
    from core.design_extractor import strip_base64_images
except ImportError:
    def strip_base64_images(html_content: str, placeholder: Optional[str] = None) -> str:
        ph_img = (
            placeholder
            or 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" '
            'viewBox="0 0 400 300"><rect width="100%" height="100%" fill="%2318181b"/>'
            '<text x="50%" y="50%" fill="%2371717a" font-family="sans-serif" font-size="14" '
            'dominant-baseline="middle" text-anchor="middle">Asset Placeholder</text></svg>'
        )
        c = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]{64,}', ph_img, html_content)
        c = re.sub(r"""<link[^>]+href=['"]data:[^'"]+['"][^>]*>""", "", c, flags=re.IGNORECASE)
        c = re.sub(r"""<script[^>]+src=['"]data:[^'"]+['"][^>]*>.*?</script>""", "", c, flags=re.DOTALL | re.IGNORECASE)
        c = re.sub(r"""data:(?:text/javascript|application|font)[^;'")\s]+""", "", c)
        return c

if TYPE_CHECKING:
    from core.design_tokens import DesignTokens

logger = logging.getLogger(__name__)


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
    if all(f"<!-- SLOT:{s}_START -->" in html_str for s in slots) or "<!-- SLOT: HEADER -->" in html_str:
        return html_str

    if not BeautifulSoup or not Comment:
        # Fallback regex-based slot boundary injector
        res = html_str
        for s in slots:
            if f"<!-- SLOT:{s}_START -->" not in res:
                res = f"<!-- SLOT:{s}_START -->\n<!-- SLOT:{s}_END -->\n" + res
        if "<!-- SLOT: HEADER -->" not in res:
            res = "<!-- SLOT: HEADER -->\n" + res
        return res

    soup = BeautifulSoup(html_str, "html.parser")
    body = soup.find("body") or soup.find("html") or soup

    containers = [body]
    main_el = body.find("main")
    if main_el:
        containers.append(main_el)
    for c in list(body.find_all("div", recursive=False)):
        containers.append(c)

    candidates = []
    seen = set()
    for cont in containers:
        for tag in cont.find_all(["section", "header", "footer", "article", "div", "main", "nav"], recursive=False):
            if id(tag) not in seen:
                seen.add(id(tag))
                tag_id = (tag.get("id") or "").lower()
                tag_cls = " ".join(tag.get("class") or []).lower()
                tag_aria = (tag.get("aria-label") or tag.get("aria-labelledby") or "").lower()
                desc = f"{tag.name} {tag_id} {tag_cls} {tag_aria}"
                candidates.append((tag, desc))

    if len(candidates) < 4:
        for tag in body.find_all(["section", "header", "footer", "main", "nav"]):
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

    # Pass 3: PROJECTS (main, content, work, project, portfolio, feature, case, service, capabilities, product, showcase)
    for tag, desc in candidates:
        if tag not in assigned.values() and (
            tag.name in ("main", "article")
            or any(
                k in desc
                for k in [
                    "main",
                    "content",
                    "project",
                    "work",
                    "portfolio",
                    "feature",
                    "case",
                    "service",
                    "capabilities",
                    "product",
                    "showcase",
                    "integration",
                    "gallery",
                    "app",
                ]
            )
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

    # Insert slots
    slot_aliases = {
        "HERO": "HEADER",
        "PROJECTS": "MAIN",
        "CONTACT": "FOOTER",
    }

    for slot_name in slots:
        tag = assigned.get(slot_name)
        alias = slot_aliases.get(slot_name)
        if tag is not None and tag.parent:
            if alias:
                tag.insert_before(Comment(f" SLOT: {alias} "))
            tag.insert_before(Comment(f" SLOT:{slot_name}_START "))
            tag.insert_after(Comment(f" SLOT:{slot_name}_END "))
        elif len(html_str) > 2000:
            # Fallback for large templates
            start_comment = Comment(f" SLOT:{slot_name}_START ")
            end_comment = Comment(f" SLOT:{slot_name}_END ")
            body.append(start_comment)
            body.append(end_comment)

    # Check for modal dialog
    dialog_el = body.find("dialog") or body.find(class_=re.compile(r"modal|dialog|popup", re.I))
    if dialog_el and dialog_el.parent:
        dialog_el.insert_before(Comment(" SLOT: MODAL "))
    elif "<!-- SLOT: MODAL -->" not in str(soup):
        body.append(Comment(" SLOT: MODAL "))

    return str(soup)


def _stage_strip_base64(html: str) -> str:
    """Stage 1: Strip embedded base64 image data and fonts."""
    return strip_base64_images(html)


def _prune_unused_css(css_str: str, dom_classes: set[str], dom_ids: Optional[set[str]] = None) -> str:
    """Prunes unused class rules from css_str if none of the selector classes appear in dom_classes."""
    def selector_matches(sel: str) -> bool:
        sel = sel.strip()
        if not sel:
            return False
        classes = re.findall(r'\.([a-zA-Z0-9_-]+)', sel)
        ids = re.findall(r'#([a-zA-Z0-9_-]+)', sel)
        if not classes and not ids:
            return True
        if any(c in dom_classes for c in classes):
            return True
        if dom_ids and any(i in dom_ids for i in ids):
            return True
        return False

    def process_rules(rules: str) -> str:
        res = []
        idx = 0
        tot = len(rules)
        while idx < tot:
            while idx < tot and rules[idx].isspace():
                idx += 1
            if idx >= tot:
                break
            brace = rules.find('{', idx)
            if brace == -1:
                break
            sel = rules[idx:brace].strip()
            depth = 1
            j = brace + 1
            while j < tot and depth > 0:
                if rules[j] == '{':
                    depth += 1
                elif rules[j] == '}':
                    depth -= 1
                j += 1
            inner = rules[brace + 1:j - 1]
            idx = j

            if sel.startswith('@font-face'):
                continue
            elif sel.startswith('@keyframes') or sel.startswith('@-webkit-keyframes'):
                res.append(sel + '{' + inner + '}')
            elif sel.startswith('@media') or sel.startswith('@supports'):
                inner_pruned = process_rules(inner)
                if inner_pruned.strip():
                    res.append(sel + '{' + inner_pruned + '}')
            elif sel.startswith('@'):
                res.append(sel + '{' + inner + '}')
            else:
                sub_sels = [s.strip() for s in sel.split(',')]
                kept = [s for s in sub_sels if selector_matches(s)]
                if kept:
                    res.append(','.join(kept) + '{' + inner + '}')
        return ''.join(res)

    return process_rules(css_str)


def _strip_unused_keyframes(css_str: str) -> str:
    """Strips @keyframes blocks that are never referenced by animation or animation-name rules."""
    kf_names = re.findall(r'@(?:-\w+-)?keyframes\s+([a-zA-Z0-9_-]+)', css_str, flags=re.IGNORECASE)
    for name in kf_names:
        pattern = rf'(?:animation(?:-name)?\s*:[^;]*?\b{re.escape(name)}\b)'
        if not re.search(pattern, css_str, flags=re.IGNORECASE):
            kf_block_pattern = rf'@(?:-\w+-)?keyframes\s+{re.escape(name)}\s*\{{(?:[^{{}}]*\{{[^{{}}]*\}})*?[^{{}}]*\}}'
            css_str = re.sub(kf_block_pattern, '', css_str, flags=re.DOTALL | re.IGNORECASE)
    return css_str


def _stage_compact_css(html: str) -> str:
    """Stage 2: Compact CSS (strip comments, collapse whitespace, minify {:;,}, prune unrendered & unused selectors)."""
    # Extract DOM classes and IDs if BeautifulSoup is available
    dom_classes: set[str] = set()
    dom_ids: set[str] = set()
    if BeautifulSoup:
        try:
            soup = BeautifulSoup(html, "html.parser")
            body = soup.find("body") or soup
            for tag in body.find_all(True):
                c = tag.get("class")
                if c:
                    if isinstance(c, list):
                        dom_classes.update(c)
                    else:
                        dom_classes.update(c.split())
                i = tag.get("id")
                if i:
                    dom_ids.add(str(i))
        except Exception as e:
            logger.debug("Failed extracting DOM classes for CSS compaction: %s", e)

    subpages = [
        r'/\*\s*=+.*?Inner pages:.*?\*/.*?(?=/\*\s*=+|\Z)',
        r'/\*\s*=+.*?Filters, search, archive.*?\*/.*?(?=/\*\s*=+|\Z)',
        r'/\*\s*=+.*?About page.*?\*/.*?(?=/\*\s*=+|\Z)',
        r'/\*\s*=+.*?Contact page \+ forms.*?\*/.*?(?=/\*\s*=+|\Z)',
        r'/\*\s*=+.*?Command menu, toast.*?\*/.*?(?=/\*\s*=+|\Z)',
        r'/\*\s*[0-9]+\.\s*Inner pages.*?\*/.*?(?=/\*\s*[0-9]+\.|\Z)',
        r'/\*\s*9\.\s*INNER PAGES.*?\*/.*?(?=/\*\s*10\.\s*Footer|\Z)',
        r'/\*\s*=+\s*\n\s*18\.\s*Inner page header.*?(?=/\*\s*=+\s*\n\s*24\.\s*Footer|\Z)',
        r'/\*\s*=+\s*\n\s*Inner routes.*?(?=/\*\s*=+\s*\n\s*(?:Motion|Footer|Responsive)|\Z)',
    ]

    def _clean_style(m: re.Match) -> str:
        attrs = m.group(1)
        s = m.group(2)

        # 1. Prune unrendered sub-page styles and router sections before stripping comments
        for p in subpages:
            s = re.sub(p, '', s, flags=re.DOTALL | re.IGNORECASE)

        # 2. Strip @font-face definitions completely from inline <style>
        s = re.sub(r'@font-face\s*\{[^}]*\}', '', s, flags=re.DOTALL | re.IGNORECASE)

        # 3. Strip comments
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)

        # 4. Strip unused keyframes
        s = _strip_unused_keyframes(s)

        # 5. Prune unused class selectors when style exceeds 30 KB
        if len(s) > 30000 and dom_classes:
            s = _prune_unused_css(s, dom_classes, dom_ids)

        s = re.sub(r'\s+', ' ', s)
        s = re.sub(r'\s*([\{\}:;,])\s*', r'\1', s)
        return f'<style{attrs}>{s.strip()}</style>'

    return re.sub(r'<style([^>]*)>(.*?)</style>', _clean_style, html, flags=re.DOTALL | re.IGNORECASE)


def _stage_strip_comments(html: str) -> str:
    """Stage 3: Strip non-SLOT: HTML comments."""
    return re.sub(r'<!--(?!\s*SLOT:).*?-->', '', html, flags=re.DOTALL)


def _stage_simplify_svgs(html: str) -> str:
    """Stage 4: Simplify SVGs > 140 chars to lightweight placeholders."""
    def _clean_svg(m: re.Match) -> str:
        svg_content = m.group(0)
        if len(svg_content) > 140:
            m_vb = re.search(r"""viewBox=['"]([^'"]+)['"]""", svg_content)
            vb_attr = f' viewBox="{m_vb.group(1)}"' if m_vb else ' viewBox="0 0 24 24"'
            return f'<svg width="24" height="24"{vb_attr}><path d="M0 0h24v24H0z"/></svg>'
        return svg_content

    return re.sub(r'<svg[^>]*>.*?</svg>', _clean_svg, html, flags=re.DOTALL | re.IGNORECASE)


def _stage_condense_lists(html: str) -> str:
    """
    Stage 5: Condense repetitive grid/flex/cards/list containers with > 2 direct children,
    and decompose trailing subpage sections (> 3) when <main> or <body> has multiple sections.
    """
    if not BeautifulSoup:
        return html
    try:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body") or soup
        main_el = body.find("main")

        # SPA subpage decomposition: if main has router subpage wrappers (data-page, data-route, data-view),
        # keep the primary views and decompose repetitive trailing subpage routes (> 1)
        if main_el:
            for attr in ("data-page", "data-route", "data-view"):
                spa_items = main_el.find_all(attrs={attr: True}, recursive=False)
                if len(spa_items) > 1:
                    for it in spa_items[1:]:
                        it.decompose()
                    break

        # When <main> or <body> has > 3 top-level <section> tags, keep the first 3 primary
        # sections and decompose repetitive trailing subpage sections (sections[3:]).
        for parent in ([main_el, body] if main_el else [body]):
            secs = parent.find_all("section", recursive=False)
            if len(secs) > 3:
                for s in secs[3:]:
                    s.decompose()
            # If main only has 1 section wrapper or divs, also check direct child divs
            if parent == main_el and len(secs) <= 1:
                divs = parent.find_all("div", recursive=False)
                if len(divs) > 3:
                    for d in divs[3:]:
                        d.decompose()
            # Also check direct child containers for inner section decomposition
            for c in parent.find_all(recursive=False):
                inner_secs = c.find_all("section", recursive=False)
                if len(inner_secs) > 3:
                    for s in inner_secs[3:]:
                        s.decompose()
                div_secs = [d for d in c.find_all("div", recursive=False) if "section" in (d.get("class") or [])]
                if len(div_secs) > 3:
                    for s in div_secs[3:]:
                        s.decompose()

        # Simplify bulky defs symbols (> 100 chars) if any
        for d in soup.find_all("defs"):
            for sym in d.find_all("symbol"):
                if len(str(sym)) > 100:
                    sym.clear()
                    sym.append(soup.new_tag("path", d="M0 0h24v24H0z"))

        keywords = ["grid", "flex", "cards", "list"]

        def _is_list_container(tag) -> bool:
            if not getattr(tag, "name", None):
                return False
            if tag.name in ("ul", "ol"):
                return True
            raw_cls = tag.get("class")
            if raw_cls:
                cls_str = (" ".join(raw_cls) if isinstance(raw_cls, list) else str(raw_cls)).lower()
                if any(k in cls_str for k in keywords):
                    return True
            raw_id = tag.get("id")
            if raw_id:
                id_str = str(raw_id).lower()
                if any(k in id_str for k in keywords):
                    return True
            return False

        for container in body.find_all(_is_list_container):
            children = [c for c in container.find_all(recursive=False) if getattr(c, "name", None)]
            if len(children) > 2:
                for child in children[2:]:
                    child.decompose()

        return str(soup)
    except Exception as e:
        logger.warning("Stage 5 (condense lists) failed: %s", e)
        return html


def _stage_minify_whitespace(html: str) -> str:
    """Stage 6: Minify inter-tag whitespace."""
    return re.sub(r'>\s+<', '><', html)


def _stage_drop_scripts(html: str) -> str:
    """Stage 7: Drop <script> tags entirely if still over budget."""
    c = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    c = re.sub(r'<script\b[^>]*/>', '', c, flags=re.IGNORECASE)
    return c


def _stage_prune_unrendered_styles(html: str) -> str:
    """Stage 8: Prune unrendered sub-page styles and router sections if still over budget."""
    subpages = [
        r'/\*\s*=+.*?Inner pages:.*?\*/.*?(?=/\*\s*=+|\</style\>)',
        r'/\*\s*=+.*?Filters, search, archive.*?\*/.*?(?=/\*\s*=+|\</style\>)',
        r'/\*\s*=+.*?About page.*?\*/.*?(?=/\*\s*=+|\</style\>)',
        r'/\*\s*=+.*?Contact page \+ forms.*?\*/.*?(?=/\*\s*=+|\</style\>)',
        r'/\*\s*=+.*?Command menu, toast.*?\*/.*?(?=/\*\s*=+|\</style\>)',
    ]
    for p in subpages:
        html = re.sub(p, '', html, flags=re.DOTALL | re.IGNORECASE)

    return _stage_compact_css(html)


def build_master_template(
    raw_html: str,
    tokens: Optional[DesignTokens] = None,
    max_bytes: int = 45000,
) -> str:
    """
    Builds a clean interactive clone (< max_bytes) with functional JS and CSS,
    lightweight placeholder assets, and injected semantic slot boundaries.
    Guarantees 100% valid document structure (never arbitrarily sliced).

    Enforces max_bytes with an idempotent cumulative reduction loop across 7 stages:
      Stage 1: Strip base64 via strip_base64_images.
      Stage 2: Compact CSS: strip comments, collapse whitespace, minify {:;,}.
      Stage 3: Strip non-SLOT: HTML comments.
      Stage 4: Simplify SVGs > 140 chars to <svg width="24" height="24" viewBox="..."><path d="M0 0h24v24H0z"/></svg>.
      Stage 5: Condense repetitive lists and trailing subpage sections (> 3).
      Stage 6: Minify inter-tag whitespace: re.sub(r'>\\s+<', '><', html).
      Stage 7: Drop <script> tags entirely if still over budget.

    After all stages, if len(html.encode("utf-8")) > max_bytes:
      For ultra-rich dashboards/SPAs, sizes up to 65,000 bytes are allowed rather than
      throwing ValueError. Only raises ValueError if actual size exceeds 65,000 bytes.
    """
    if not raw_html or not raw_html.strip():
        return ""

    # Inject semantic slot boundaries first (Stage 3 will preserve SLOT: comments)
    html = inject_semantic_slots(raw_html)

    stages = [
        ("Stage 1 (strip base64 images)", _stage_strip_base64),
        ("Stage 2 (compact CSS)", _stage_compact_css),
        ("Stage 3 (strip non-SLOT HTML comments)", _stage_strip_comments),
        ("Stage 4 (simplify SVGs)", _stage_simplify_svgs),
        ("Stage 5 (condense repetitive lists)", _stage_condense_lists),
        ("Stage 6 (minify inter-tag whitespace)", _stage_minify_whitespace),
        ("Stage 7 (drop script tags)", _stage_drop_scripts),
    ]

    initial_bytes = len(html.encode("utf-8"))
    logger.info("Starting master template build, initial size: %d bytes (budget: %d bytes)", initial_bytes, max_bytes)

    for idx, (stage_name, stage_fn) in enumerate(stages, 1):
        # Stages 1-4 are non-destructive structural cleanup and always run
        # Stages 5-7 are progressive reductions only run if still over budget
        if idx >= 5 and len(html.encode("utf-8")) <= max_bytes:
            logger.info("Under budget (%d <= %d bytes), skipping %s and subsequent reduction stages", len(html.encode("utf-8")), max_bytes, stage_name)
            break

        html = stage_fn(html)
        current_bytes = len(html.encode("utf-8"))
        logger.info("%s: %d bytes", stage_name, current_bytes)

    # Post-reduction cleanups if still slightly over budget
    current_bytes = len(html.encode("utf-8"))
    if current_bytes > max_bytes:
        html = _stage_minify_whitespace(html)
        current_bytes = len(html.encode("utf-8"))
        logger.info("Post-reduction whitespace minify: %d bytes", current_bytes)

    if current_bytes > max_bytes:
        html = _stage_drop_scripts(html)
        current_bytes = len(html.encode("utf-8"))
        logger.info("Post-reduction drop scripts: %d bytes", current_bytes)

    if current_bytes > max_bytes:
        html = _stage_prune_unrendered_styles(html)
        current_bytes = len(html.encode("utf-8"))
        logger.info("Post-reduction prune unrendered styles: %d bytes", current_bytes)

    actual = len(html.encode("utf-8"))
    # For ultra-rich dashboards/SPAs (when using the default 45000 budget),
    # allow templates up to 65,000 bytes without throwing ValueError.
    # If caller explicitly provided max_bytes < 45000, respect caller's max_bytes.
    hard_limit = 65000 if max_bytes >= 45000 else max_bytes
    if actual > hard_limit:
        raise ValueError(
            f"master-template exceeds {max_bytes} bytes after all reduction stages ({actual} bytes). Input too complex."
        )

    return html


# Backwards compatibility alias
generate_master_template_html = build_master_template

__all__ = [
    "inject_semantic_slots",
    "build_master_template",
    "generate_master_template_html",
]
