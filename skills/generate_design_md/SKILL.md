---
name: generate_design_md
description: "Master studio protocol for extracting design systems, visual tokens, and creating canonical DESIGN.md specifications from live URLs and HTML templates."
domain: design
author: "Hamza Bukhari"
version: "1.0.0"
required_tools: [extract_design_system, browser_control, file_controller]
triggers: ["generate design md", "extract design tokens", "extract design system", "create design spec", "analyze styling", "design system extraction", "audit design", "design tokens", "design system"]
tags: ["design", "tokens", "extractor", "audit", "dsl"]
auto_activate: true
---

# 🎨 Master Design System Extraction Protocol (`generate_design_md`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Core Subsystem:** Studio Design Token Extractor & Canonical DSL Synthesizer  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Fleet, and all ZEZO UI coding agents.  
> **Core Axiom:** No AI CSS hallucination. Design direction is 100% extracted from authentic, proven digital artifacts (live websites, HTML reference templates, or visual specs) and serialized into deterministic, machine-readable `<design-context>` specifications.

---

## 🏗️ 1. Architecture & Token Extraction Pipeline

The design extractor turns any target website, local HTML template, or visual component into a structured, production-grade `DESIGN.md` document:

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Target Input Ingestion                            │
 │  • Live URL (https://...)                                              │
 │  • Local HTML Template (skills/website_build/references/...)            │
 │  • Custom Workspace Component (index.html / App.tsx)                  │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │           core/design_extractor.py & actions/design_extractor.py       │
 │                                                                        │
 │ 1. DOM & CSS Ingestion: Strip base64, collect inline styles & classes │
 │ 2. Multi-Tier Token Extraction: Hex/RGB/OKLCH, Typography, Geometry    │
 │ 3. WCAG Contrast Calculation: Relative luminance ratio audit           │
 │ 4. Aesthetic Profile Classification: (Saas B2B, Editorial, Cyber, etc) │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │              core/design_md_generator.py (DSL Synthesis)               │
 │                                                                        │
 │  - <design-context> YAML DSL block                                     │
 │  - Semantic Color Tokens (bg, surface, primary, border, accent)        │
 │  - Typography Hierarchy (display, body, mono, font-weights)            │
 │  - Elevation, Glassmorphism, & Animation Keyframes                     │
 │  - Component Recipes (Hero, Navbar, Card, Buttons, Badges)             │
 │  - Anti-Slop Directive Gates                                           │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Canonical Output Delivery                         │
 │  • Caching: skills/website_build/references/design_md/ (0ms recall)    │
 │  • Destination: Desktop/DESIGN.md or workspace root                     │
 │  • Downstream Handoff: OpenCode / Kilo / Antigravity Agents            │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 2. Standard Operating Procedure (5-Phase SOP)

Every design extraction task must execute methodically across five distinct phases:

### Phase 1: Target Ingestion
1. **Source Resolution:**
   - **URL Input:** Use `extract_design_system(file_path="https://...")` or headless browser automation (`browser_control`) to capture the rendered DOM and computed stylesheets.
   - **Local Reference:** Resolve against catalog templates in `skills/website_build/references/` or user workspace files.
2. **Pre-Processing & Sanitization:**
   - Strip inline base64 bloat (`strip_base64_bloat`) and replace with lightweight SVG placeholders to prevent context window overflow.
   - Flatten and merge linked `<style>` blocks and inline element CSS.
3. **Cache Evaluation:**
   - Check if an up-to-date extraction exists in `skills/website_build/references/design_md/`. If unmodified, return the cached specification instantly (0ms latency).

### Phase 2: Multi-Tier Token Extraction
1. **Semantic Color Tokens:**
   - Scan all HEX, RGB, RGBA, HSL, and OKLCH color values.
   - Frequency cluster and map to semantic roles:
     - Background (`--background` / dark void or warm cream)
     - Surface / Card (`--surface` / `--card` with elevation)
     - Border (`--border` / subtle hairline contrast)
     - Primary Brand (`--primary` / high-intent action color)
     - Accent (`--accent` / highlight accents)
     - Text Primary & Muted (`--text` & `--muted`)
2. **Typography Hierarchy:**
   - Detect Google Fonts links and `@font-face` declarations.
   - Extract primary Display font (headings, heroes) and Body font (content, paragraphs).
   - Identify monospace coding font families.
   - Record scale: font sizes, weights (e.g. 400, 500, 600, 700), and line heights.
3. **Geometry & Micro-Interactions:**
   - Border radius scale (`sm`, `md`, `lg`, `full`).
   - Shadows and specular glassmorphism elevation (`backdrop-filter: blur(...)`).
   - Extract CSS `@keyframes` animations (pulse, float, shimmer, gradient flow).

### Phase 3: Accessibility Contrast Audit
1. **WCAG Luminance Calculation:**
   - Calculate relative luminance for extracted text vs background token pairs using standard WCAG formulas:
     $$L = 0.2126 \times R + 0.7152 \times G + 0.0722 \times B$$
2. **Contrast Ratio Compliance:**
   - Verify minimum contrast ratio:
     - Normal text: $\ge 4.5:1$ (WCAG AA).
     - Large text / Headings: $\ge 3:1$ (WCAG AA).
3. **Audit Flagging & Remediation:**
   - If any core text/background pairing fails contrast requirements, flag the violation and provide adjusted, accessible hex values in the generated tokens.

### Phase 4: Canonical DESIGN.md Synthesis
1. **DSL `<design-context>` Generation:**
   - Structure the markdown output starting with the standardized YAML design token block:
     ```markdown
     <design-context>
     version: "2.0"
     aesthetic_profile: "Dark Obsidian Glass / SaaS B2B"
     tokens:
       colors:
         background: "#09090b"
         surface: "#18181b"
         border: "rgba(255, 255, 255, 0.08)"
         primary: "#3b82f6"
         text: "#fafafa"
         muted: "#a1a1aa"
       typography:
         display: "Plus Jakarta Sans, sans-serif"
         body: "Inter, sans-serif"
         mono: "JetBrains Mono, monospace"
     </design-context>
     ```
2. **Component Recipes:**
   - Detail concrete markup and styling recipes for:
     - Navigation Bar (sticky blur, logo lockup, pill action button).
     - Hero Section (badge pill, headline scale, CTA button group).
     - Cards & Containers (hairline borders, glass background, hover elevation).
     - Interactive Controls (inputs, focus rings, buttons, toggles).
3. **Anti-Slop Directives:**
   - Explicitly list visual patterns to **REJECT** (e.g., generic AI purple gradient blobs, unstyled inputs, low-contrast text, missing focus rings).

### Phase 5: Downstream Handoff
1. **Disk Writing:**
   - Save canonical output to requested target (e.g., `Desktop/DESIGN.md`, `<active_repo>/DESIGN.md`, or `skills/website_build/references/design_md/<stem>.md`).
2. **Agent Context Ingestion:**
   - Notify active coding agents (Antigravity Agent, OpenCode, Kilo Code) that design tokens are locked and ready for code synthesis.
3. **Execution Summary:**
   - Report extracted palette, primary fonts, aesthetic classification, and output path.

---

## 🛡️ 3. Safety Invariants & Operational Rules

- **Zero Hallucination:** Every color, font, and radius in `DESIGN.md` must trace back to the analyzed reference.
- **Cache Integrity:** Any modification to `core/design_extractor.py` or token rules requires bumping the extractor version to invalidate stale caches.
- **Accessibility Guarantee:** Never deliver a `DESIGN.md` with unreadable, low-contrast text tokens without explicit remediation notes.
