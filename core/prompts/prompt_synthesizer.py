"""core/prompts/prompt_synthesizer.py
Dynamic Exemplar-Based Prompt Synthesizer for Autonomous Code & Web Building Agents.

Creator & Lead Architect: Hamza Bukhari
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

# Archetype Constants
PORTFOLIO = "portfolio_archetype"
LANDING_PAGE = "landing_page_archetype"
SURGICAL_EDIT = "surgical_edit_archetype"
DASHBOARD = "dashboard_archetype"

# Directory where exemplar files reside
EXEMPLARS_DIR = Path(__file__).resolve().parent / "exemplars"

# Mandatory anti-stall guardrail directives
GUARDRAIL_DIRECTIVES = [
    "DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.",
    "ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).",
    "PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.",
    "Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers."
]

# Fallback exemplars in memory in case files on disk are absent
_FALLBACK_PORTFOLIO = """# ROLE & DIRECTIVE: PORTFOLIO SPECIALIST
You are an elite portfolio designer and frontend engineer. Your mission is to produce a stunning, polished, responsive portfolio website directly into '{target_file}'.

## 🛡️ STRICT EXECUTION GUARDRAILS (ANTI-STALL)
1. DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.
2. ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).
3. PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.
4. Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers.

## 🎯 TARGET SPECIFICATIONS
- Target File: {target_file}
- Design Theme: {theme}
- Primary Directive: {task_directive}

## 📐 SECTION ARCHITECTURE
1. Hero & Identity: Compelling headline, bio summary, avatar/visual anchor, quick action CTAs (Resume, Contact).
2. Work & Selected Projects: High-impact project cards with tech tags, live preview/code links, and measurable outcomes.
3. Capabilities & Tech Stack: Categorized skills with crisp visual hierarchy and badge styling.
4. Experience & Career Timeline: Chronological roles, achievements, and impact statements.
5. Contact & Socials: Direct contact touchpoints, clean email links, and social icon buttons.

## 🧩 CONTENT & SLOTS TO INJECT
{slots}

{content}
"""

_FALLBACK_LANDING_PAGE = """# ROLE & DIRECTIVE: HIGH-CONVERTING LANDING PAGE SPECIALIST
You are a master product designer and conversion-rate optimization engineer. Your mission is to craft a modern, high-impact SaaS/product landing page directly into '{target_file}'.

## 🛡️ STRICT EXECUTION GUARDRAILS (ANTI-STALL)
1. DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.
2. ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).
3. PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.
4. Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers.

## 🎯 TARGET SPECIFICATIONS
- Target File: {target_file}
- Design Theme: {theme}
- Primary Directive: {task_directive}

## 📐 SECTION ARCHITECTURE
1. Navigation: Sticky minimalist header with logo, primary links, and conversion CTA.
2. Hero Section: High-converting headline, sub-headline value proposition, primary/secondary action buttons, and mock preview.
3. Social Proof & Trust: Customer badges, press mentions, or metric counters.
4. Core Features & Capabilities: Bento-grid or alternating split feature blocks with crisp iconography and benefit-driven copy.
5. Interactive Showcase / Testimonials: Engaging customer quotes, interactive preview widget, or demo container.
6. Pricing & Plans: Transparent, comparative tier cards with distinct "Most Popular" highlight.
7. FAQ & Objection Handling: Accordion-style expandable common questions.
8. Final CTA & Footer: Urgent closing CTA banner and clean footer links.

## 🧩 CONTENT & SLOTS TO INJECT
{slots}

{content}
"""

_FALLBACK_SURGICAL_EDIT = """# ROLE & DIRECTIVE: SURGICAL CODE ADAPTATION SPECIALIST
You are a precise frontend surgical engineer. Your mission is to update, replace, or refine targeted sections of '{target_file}' without degrading or breaking surrounding structure.

## 🛡️ STRICT EXECUTION GUARDRAILS (ANTI-STALL)
1. DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.
2. ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).
3. PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.
4. Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers.

## 🎯 TARGET SPECIFICATIONS
- Target File: {target_file}
- Design Theme: {theme}
- Primary Directive: {task_directive}

## 🔍 SURGICAL EXECUTION PROTOCOL
1. Locate the exact slot comment or targeted section: `<!-- SLOT:<NAME> -->` ... `<!-- /SLOT:<NAME> -->`.
2. Replace only the inner markup corresponding to the user request.
3. Preserve all CSS tokens, class names, canvas scripts, event listeners, and layout wrappers untouched.
4. Do NOT reformat or rewrite sections outside the declared scope.
5. Complete the entire file update in a single clean write pass.

## 🧩 SLOTS & DIRECTIVES
{slots}

{content}
"""

_FALLBACK_DASHBOARD = """# ROLE & DIRECTIVE: DASHBOARD & APPLICATION UI SPECIALIST
You are a senior product systems architect. Your mission is to produce a state-of-the-art interactive dashboard directly into '{target_file}'.

## 🛡️ STRICT EXECUTION GUARDRAILS (ANTI-STALL)
1. DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.
2. ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).
3. PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.
4. Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers.

## 🎯 TARGET SPECIFICATIONS
- Target File: {target_file}
- Design Theme: {theme}
- Primary Directive: {task_directive}

## 📐 SECTION ARCHITECTURE
1. App Shell: Responsive navigation sidebar with active route states and collapsible toggle.
2. Header: Breadcrumbs, search input, system status indicator, and user profile badge.
3. KPI & Metric Highlights: Grid of summary statistic cards with trend delta pills (+/- percentages).
4. Data Visualizations: Interactive chart canvas containers with filter tabs (7D, 30D, 1Y).
5. Tabular Data & Activity Feed: Filterable data table with sortable columns, status tags, and action buttons.
6. Responsive Layout: Smooth stacking on mobile/tablet viewports with clean overflow scrolling.

## 🧩 CONTENT & SLOTS TO INJECT
{slots}

{content}
"""

FALLBACK_EXEMPLARS: Dict[str, str] = {
    PORTFOLIO: _FALLBACK_PORTFOLIO,
    LANDING_PAGE: _FALLBACK_LANDING_PAGE,
    SURGICAL_EDIT: _FALLBACK_SURGICAL_EDIT,
    DASHBOARD: _FALLBACK_DASHBOARD,
}


def _normalize_archetype_key(name: str) -> str:
    """Normalize raw archetype strings to recognized identifiers."""
    cleaned = (name or "").strip().lower()
    if cleaned.endswith(".txt"):
        cleaned = cleaned[:-4]

    mapping = {
        "portfolio": PORTFOLIO,
        "portfolio_archetype": PORTFOLIO,
        "landing": LANDING_PAGE,
        "landing_page": LANDING_PAGE,
        "landing_page_archetype": LANDING_PAGE,
        "surgical": SURGICAL_EDIT,
        "surgical_edit": SURGICAL_EDIT,
        "surgical_edit_archetype": SURGICAL_EDIT,
        "dashboard": DASHBOARD,
        "dashboard_archetype": DASHBOARD,
    }
    return mapping.get(cleaned, cleaned)


def load_exemplar(archetype_name: str) -> str:
    """
    Loads raw archetype text from `core/prompts/exemplars/{archetype_name}.txt`.
    Falls back gracefully to alternative file extensions or built-in defaults if missing.
    """
    if not archetype_name:
        return FALLBACK_EXEMPLARS[LANDING_PAGE]

    normalized_key = _normalize_archetype_key(archetype_name)

    # 1. Check possible file paths on disk
    candidate_names = [
        archetype_name,
        f"{archetype_name}.txt",
        normalized_key,
        f"{normalized_key}.txt",
    ]

    for candidate in candidate_names:
        # Check relative to exemplars directory
        file_path = EXEMPLARS_DIR / candidate
        if file_path.is_file():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Check as direct path
        direct_path = Path(candidate)
        if direct_path.is_file():
            try:
                return direct_path.read_text(encoding="utf-8")
            except Exception:
                pass

    # 2. Fall back to built-in fallback exemplars dictionary
    if normalized_key in FALLBACK_EXEMPLARS:
        return FALLBACK_EXEMPLARS[normalized_key]

    # 3. Generic fallback
    return FALLBACK_EXEMPLARS[LANDING_PAGE]


def detect_archetype(task_description: str) -> str:
    """
    Auto-detect the appropriate archetype identifier based on keywords in the task description.
    """
    if not task_description:
        return LANDING_PAGE

    desc = task_description.lower().strip()

    # 1. Explicit surgical or slot targeting directives
    surgical_indicators = [
        "surgical", "<!-- slot", "slot:", "slot ", "update slot",
        "replace slot", "patch", "swap section", "tweak hero"
    ]
    if any(ind in desc for ind in surgical_indicators):
        return SURGICAL_EDIT

    # 2. Portfolio & personal brand intents
    portfolio_indicators = [
        "portfolio", "resume", "cv", "personal site", "developer portfolio",
        "designer portfolio", "personal brand", "bio page", "freelance site"
    ]
    if any(ind in desc for ind in portfolio_indicators):
        return PORTFOLIO

    # 3. Dashboard & operational systems
    dashboard_indicators = [
        "dashboard", "admin", "analytics", "metrics", "crm",
        "control panel", "portal", "kpi", "reporting view"
    ]
    if any(ind in desc for ind in dashboard_indicators):
        return DASHBOARD

    # 4. Landing page / SaaS marketing intents
    landing_indicators = [
        "landing", "landing page", "saas", "waitlist", "product page",
        "lead gen", "sales page", "marketing site", "hero section"
    ]
    if any(ind in desc for ind in landing_indicators):
        return LANDING_PAGE

    # 5. Modification actions without creation terms
    edit_verbs = ["edit", "modify", "update", "replace", "fix", "tweak", "change"]
    create_verbs = ["create", "build", "generate", "scaffold", "new", "make"]
    has_edit = any(verb in desc for verb in edit_verbs)
    has_create = any(verb in desc for verb in create_verbs)
    if has_edit and not has_create:
        return SURGICAL_EDIT

    return LANDING_PAGE


def _format_guardrails(target_file: str) -> str:
    """Format standard anti-stall guardrails block for the target file."""
    lines = [
        "## 🛡️ STRICT EXECUTION GUARDRAILS (ANTI-STALL)",
        f"1. DIRECT ADAPTATION: Write directly to '{target_file}' in a single pass.",
        "2. ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts (no BeautifulSoup, chunking, or inspect.py).",
        "3. PRESERVE STYLES & INTERACTION: Keep all <style> animations and interactive JavaScript functions intact.",
        "4. Slot Targeting: Replace content inside designated <!-- SLOT:* --> markers."
    ]
    return "\n".join(lines)


def _safe_substitute(template: str, variables: Dict[str, Any]) -> str:
    """
    Safely substitutes {identifier} placeholders in template using variables mapping.
    Prevents KeyError and preserves CSS/JS curly bracket blocks untouched.
    """
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in variables:
            val = variables[key]
            return str(val) if val is not None else ""
        return match.group(0)

    # Match tokens like {target_file}, {theme}, etc.
    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", replacer, template)


def synthesize_prompt(archetype: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Synthesizes an execution-ready prompt for autonomous coding agents.

    - Reads the archetype exemplar.
    - Safely substitutes dynamic variables: {target_file}, {theme}, {content}, {slots}, {task_directive}, etc.
    - Strictly enforces anti-stall guardrails.
    """
    ctx = dict(context or {})

    # Ensure required default context variables
    target_file = ctx.setdefault("target_file", "index.html")
    ctx.setdefault("theme", "Modern High-Contrast Minimalist (Tailwind / ReUI)")
    ctx.setdefault("content", "")
    ctx.setdefault("slots", "")
    ctx.setdefault("task_directive", "Synthesize and assemble complete deliverables directly.")

    # Load base archetype template
    raw_exemplar = load_exemplar(archetype)

    # Safe variable substitution
    synthesized = _safe_substitute(raw_exemplar, ctx)

    # Validate that strict anti-stall guardrails are present
    formatted_guardrails = _format_guardrails(target_file)
    has_direct_adaptation = "DIRECT ADAPTATION: Write directly to" in synthesized
    has_forbidden = "ABSOLUTELY FORBIDDEN: DO NOT write intermediate Python scripts" in synthesized
    has_preserve = "PRESERVE STYLES & INTERACTION" in synthesized
    has_slot = "Slot Targeting: Replace content inside designated <!-- SLOT:" in synthesized

    # If any mandatory guardrail is missing from the template, inject the full guardrails block
    if not (has_direct_adaptation and has_forbidden and has_preserve and has_slot):
        synthesized = f"{formatted_guardrails}\n\n{synthesized}"

    return synthesized.strip()
