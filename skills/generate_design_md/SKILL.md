---
name: generate_design_md
description: "Master studio protocol for reverse-engineering design systems and generating canonical DESIGN.md, preview.html, and preview-dark.html specifications via autonomous coding engines."
domain: design
author: "Hamza Bukhari"
version: "2.1.0"
execution_mode: "engine_only"
supported_engines: ["antigravity", "opencode", "kilo"]
supported_modes: ["url", "local"]
pre_flight_ingestion: "scrapling_extract"
ingested_files: ["site_dom.html", "site_styles.css", "site_tokens.json"]
required_tools: ["antigravity_run", "opencode_run", "kilo_run", "browser_control", "file_controller"]
output_files: ["DESIGN.md", "preview.html", "preview-dark.html"]
triggers: ["generate design md", "extract design tokens", "extract design system", "create design spec", "analyze styling", "design system extraction", "audit design", "design tokens", "design system"]
tags: ["design", "tokens", "preview", "audit", "engine_only", "anti_slop", "dual_mode"]
auto_activate: true
---

# 🎨 Master Design System Extraction Protocol (`generate_design_md`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Core Subsystem:** Autonomous Coding Engine Pipeline (Google Antigravity CLI `agy`, OpenCode, Kilo Code)  
> **Target Audience:** Autonomous Coding Engines, Office Fleet Agents, and ZEZO Core Orchestrators.  
> **Core Axiom:** **Authenticity over invention.** Every token, color, font, radius, spacing step, and shadow documented must be traceable to real source code or extracted stylesheet data. You reverse-engineer the authentic design DNA — you do not redesign, invent unbacked tokens, or impose aesthetic bias.

---

## 🧭 1. Operational Role & Scope

You are a **Senior Frontend Design-Systems Auditor and UI Documentation Agent**. Your mandate is to reverse-engineer an existing frontend codebase, component folder, standalone file, or live URL into an authoritative, machine-readable design system specification.

You produce **three mandatory deliverables**:

1. `DESIGN.md` — The canonical design-system specification markdown document that downstream coding agents read as their design source of truth.
2. `preview.html` — A self-contained visual design catalog (light theme) featuring an interactive Dark/Light toggle switch, live color swatches with contrast badges, typography scale specimen, and an interactive UI component playground.
3. `preview-dark.html` — A static self-contained HTML visual catalog pre-rendered with obsidian dark surfaces (`#09090b` / `#18181b`) and dark palette tokens for instant verification without JavaScript dependencies.

---

## ⚡ 2. Dual-Mode Execution Protocol

The protocol operates strictly in two modes depending on whether the target is a remote web destination or a local codebase.

### Mode 1: Live URL Mode (Scrapling Pre-Flight Ingestion)

When extracting from a live website URL (e.g., `https://example.com`), ZEZO's high-speed Scrapling / headless browser extractor runs pre-flight capture **before** invoking the coding engine. The engine does NOT perform live network scraping; instead, it ingests three pre-flight extraction files generated in the target directory:

| Pre-Flight Ingested File | Purpose & Contents |
|---|---|
| `site_dom.html` | Cleaned, hydrated DOM snapshot of the live webpage with semantic tags, section hierarchy, and component boundaries preserved. |
| `site_styles.css` | Consolidated extracted stylesheets containing inline styles, external CSS rules, `@font-face` definitions, and CSS variables. |
| `site_tokens.json` | Pre-parsed JSON map of extracted color values, font families, font sizes, line heights, border radii, and media queries. |

**Engine Rule for Mode 1:** Treat `site_dom.html`, `site_styles.css`, and `site_tokens.json` as the immutable primary source of truth. Do not make external HTTP requests or spawn browser sessions when these files are present.

### Mode 2: Local Codebase / Frontend Folder / Single File Mode

When extracting from a local directory, workspace, component library, or single source file, the engine inspects the local files directly across three hierarchical tiers:

#### Tier 1: System Sources First (Highest Authority)
- `tailwind.config.{js,ts,cjs,mjs}`
- Theme & token files (`theme.{js,ts}`, `tokens.{json,ts}`, `design-tokens.*`)
- CSS variables defined in `:root`, `[data-theme="dark"]`, and `.dark`
- Global application stylesheets (`globals.css`, `app.css`, `index.css`, `style.css`)
- Package dependencies (`package.json`) to detect UI component libraries (Radix, Shadcn UI, Headless UI) and icon packages (Lucide, Tabler, Heroicons)

#### Tier 2: Shared UI Primitives
- Primitive component directories (`components/ui/*`, `components/primitives/*`, `src/common/*`)
- Shared button, input, card, badge, dialog, and dropdown implementations
- Layout and application shells (`layout.tsx`, `AppShell`, `RootLayout`, `Navbar`, `Sidebar`)

#### Tier 3: Conflict Resolution Hierarchy
When conflicting token values exist in the codebase, apply these rules in strict order:
1. **Shared primitive tokens override page-local overrides.**
2. **Repeated usage (≥3 occurrences) overrides one-off screens.**
3. **Newer file wins over older file if both are equally canonical.**
4. **When still ambiguous, document the dominant pattern in `DESIGN.md` and record the divergence under "Known Issues / Gaps".**

---

## 👥 3. Subagents Policy (Strictly Optional)

> **Important Architectural Boundary:** **Do NOT force 5-7 subagents.**

Unlike `website_build` (which decomposes into 5-7 parallel builder subagents for simultaneous section construction), `generate_design_md` is an analytical, precision auditing task where token consistency, cross-file verification, and single-source-of-truth coherence are paramount.

- **Default Execution:** A single focused coding agent performs the complete audit, synthesizes `DESIGN.md`, and builds both `preview.html` and `preview-dark.html`.
- **Dual-Worker Option (Optional):** If parallel decomposition is genuinely beneficial (e.g., in large monorepos with hundreds of components), divide work between at most **two** focused workers:
  - *Worker A (System & Token Auditor):* Analyzes system sources and writes `DESIGN.md`.
  - *Worker B (Visual Catalog Architect):* Reads `DESIGN.md` and builds `preview.html` and `preview-dark.html`.
- **Forbidden:** Forcing 5-7 subagents onto a token extraction task causes race conditions, conflicting token naming, hallucinated divergences, and unnecessary file locks.

---

## 📄 4. Output Contract

Every extraction run must deliver the following three files in the target directory:

### Deliverable 1: `DESIGN.md`

Follow this exact structure. Do not rename sections. Do not skip sections — if a value is absent from the source, record `Not found in source` and list it under "Known Issues / Gaps".

````markdown
# DESIGN.md

## Overview
One paragraph (3–5 sentences) describing the visual language actually present: brand feel, density, corner language, surface hierarchy, and primary mode (light, dark, or both).

## Colors
| Token | Value | Role |
|---|---|---|
| Primary | #xxxxxx | Dominant brand or action color |
| Primary Foreground | #xxxxxx | Text/icon color on primary background |
| Secondary | #xxxxxx | Supporting action or subtle emphasis |
| Tertiary | #xxxxxx | Accent highlights or badges |
| Neutral | #xxxxxx | Backgrounds and surfaces |
| Neutral Foreground | #xxxxxx | Body text and readable content |
| Border | #xxxxxx | Subtle borders and structural dividing lines |
| Destructive | #xxxxxx | Error states, dangerous actions, alerts |
| Success | #xxxxxx | Positive status, confirmations |
| Warning | #xxxxxx | Cautions, transient alerts |
| Info | #xxxxxx | Informational notices |

*Include dark-mode overrides in a secondary table only if they explicitly exist in the source codebase or ingested styles.*

## Typography
- **Headline Font**: family — weights — line-height — tracking
- **Body Font**: family — weights — line-height
- **Label / Monospace Font**: family — weights — tracking
- **Type Scale**: list each step (e.g., xs=12px, sm=14px, base=16px, lg=18px, xl=20px, 2xl=24px, 3xl=30px, 4xl=36px) as found in the source

## Spacing & Radius
- **Spacing Scale**: list the base unit and scale steps (e.g., 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px)
- **Radius Scale**: list all corner radius tokens (e.g., none=0px, sm=4px, md=8px, lg=12px, full=9999px)
- **Border Conventions**: default border width, color token, and divider opacity

## Elevation
List each shadow token:
- `shadow-sm`: CSS value → Usage
- `shadow-md`: CSS value → Usage
- `shadow-lg`: CSS value → Usage

## Components
- **Buttons**: variants (primary, secondary, outline, ghost), sizes, hover/active/disabled/focus states
- **Inputs**: height, padding, radius, border, focus ring color and spread, error state
- **Cards**: padding, corner radius, border, elevation shadow, surface background
- **Navigation**: layout density, active tab indicators, hover states, mobile menu pattern
- **Modals & Badges**: padding, radius, shadow, backdrop blur, badge variants

## Do's and Don'ts
Derived exclusively from observed codebase patterns — not personal opinions:
- **Do**: Documented positive patterns found in the source.
- **Don't**: Anti-patterns explicitly avoided or flagged in the code.

## Known Issues / Gaps
- Missing tokens (e.g., undefined warning or tertiary colors)
- Conflicting patterns (list specific file paths or CSS selectors)
- Inferred values that could not be 100% verified

## Sources
List every file actually read, with a one-line description of its role. This section is mandatory for auditability.
````

### Deliverable 2: `preview.html`

- **Self-Contained Single File:** Zero external build dependencies. All styles embedded in `<style>` and scripts in `<script>`.
- **Interactive Light/Dark Toggle:** A functional toggle switch in the header that seamlessly switches the preview between light and dark palettes.
- **Color Swatches Grid:** Every extracted color token rendered with its hex code, variable name, semantic role, and an automated contrast badge indicating WCAG AA/AAA legibility.
- **Typography Specimen:** Live visual rendering of the complete typographic scale from Display/Hero down to body-sm and monospace code labels.
- **Component Playground:** Interactive UI primitives demonstrating authentic extracted styles:
  - Button matrix (Primary, Secondary, Outline, Ghost, Disabled, Hover states).
  - Form controls (Text input with focus ring, select dropdown, checkbox, switch).
  - Card elevation specimens with authentic padding, border, and shadows.
  - Status badges (Success, Warning, Destructive, Info).

### Deliverable 3: `preview-dark.html`

- **Static Obsidian Dark Catalog:** Pre-rendered with obsidian dark surfaces (`#09090b` / `#18181b` / `#121214`) and zinc borders.
- **Zero JavaScript Dependencies:** Does not rely on client-side JS to render the dark theme.
- **Deterministic Rendering:** Ensures immediate visual verification in headless environments, static previews, and code review diffs.

---

## 🛡️ 5. Anti-Slop & Restraint Directives (`oh-my-design` Standard)

- **Zero Generic AI Purple Gradients:** Never invent purple, violet, or pink glowing mesh gradients unless explicitly defined in the source theme tokens.
- **Zero Hallucinated Icons or Utilities:** Only reference icon libraries or CSS utility classes that actually exist in the source dependencies or extracted stylesheets.
- **Authentic Density & Spacing:** Preserve the exact density of the source. If the application is enterprise-dense (tight 8px padding, compact 13px text), do not inflate it into airy consumer SaaS whitespace.
- **No Speculative Token Completion:** If a secondary color, warning state, or shadow token does not exist in the source, write `Not defined in source` in `DESIGN.md` and record it under "Known Issues / Gaps". Never fabricate a placeholder hex code to fill the table.
- **100% Auditable Traceability:** Every documented token must be traceable to a specific source file, CSS selector, or computed token entry listed in the `## Sources` section.

---

## 📋 6. Reference Prompt Blueprints

When dispatching design extraction tasks to autonomous coding engines (Antigravity CLI `agy`, OpenCode, or Kilo Code), use the authoritative blueprint corresponding to the execution mode:

### Blueprint 1: Live URL Mode (Scrapling Pre-Flight Ingestion)

```text
You are an expert Frontend Systems Architect, UI Auditor, and Design Tokens Specialist.
Your task is to reverse-engineer the authentic design system from the pre-flight extracted files of a live website into canonical design system specifications.

TARGET ENVIRONMENT & PRE-FLIGHT INGESTION:
The target directory contains three pre-flight extraction files:
1. 'site_dom.html' — Cleaned, hydrated DOM snapshot of the live webpage.
2. 'site_styles.css' — Extracted stylesheets, computed rules, and CSS variables.
3. 'site_tokens.json' — Pre-parsed JSON map of colors, typography, spacing, and radii.

CRITICAL CONSTRAINTS:
- Treat these three files as your primary immutable source of truth.
- Do not run external web searches or attempt to re-crawl the live URL.
- Reverse-engineer what is actually present. Do not redesign, invent unbacked tokens, or impose aesthetic bias.
- Do not force 5-7 subagents; execute directly with surgical precision.

EXECUTION STEPS:
1. Ingest and cross-reference 'site_tokens.json', 'site_styles.css', and 'site_dom.html'.
2. Extract the complete visual DNA:
   - Color palette (Primary, Secondary, Tertiary, Neutral, Border, Semantic states).
   - Typography hierarchy (Font families, weights, type scale, line heights).
   - Spacing rhythm, corner radius scale, and elevation shadows.
   - Component primitives (Button variants, form inputs, cards, badges, navigation).
3. Generate 'DESIGN.md' following the canonical specification template.
4. Generate 'preview.html' as a self-contained visual design catalog with an interactive Dark/Light toggle, color swatches with contrast badges, typography specimen, and live component playground.
5. Generate 'preview-dark.html' as a static zero-JS catalog pre-rendered with obsidian dark surfaces (#09090b / #18181b).

OUTPUT DELIVERABLES:
1. DESIGN.md
2. preview.html
3. preview-dark.html

Deliver production-quality, auditable files directly in the target directory now.
```

### Blueprint 2: Local Codebase / Folder / Single File Mode

```text
You are an expert Frontend Systems Architect, UI Auditor, and Design Tokens Specialist.
Your task is to reverse-engineer the authentic design system from the local codebase/files in '{target_dir}' into canonical design system specifications.

ANALYSIS PRIORITIES:
1. System sources first:
   - tailwind.config.*, theme files, design-tokens.*, tokens.json
   - CSS variables in :root, [data-theme="dark"], .dark
   - Global stylesheets (globals.css, app.css, index.css)
   - package.json to verify icon and component dependencies
2. Shared UI primitives:
   - components/ui/*, components/primitives/*
   - Buttons, inputs, cards, dialogs, badges, navigation components
3. Conflict resolution:
   - Shared primitives override page-local overrides.
   - Repeated usage (≥3 times) overrides one-off screens.
   - Newer files win over older files.
   - Ambiguities must be noted in 'Known Issues / Gaps'.

CRITICAL CONSTRAINTS:
- Authenticity over invention: Every token must trace to an actual line or file.
- If a token does not exist, mark it as 'Not found in source' — do not fabricate values.
- Do not force 5-7 subagents; execute directly or with at most two focused workers.
- Zero generic AI purple gradients; maintain authentic density and spacing.

EXECUTION STEPS:
1. Scan and inspect all system configuration files, stylesheets, and UI primitives.
2. Synthesize the complete visual DNA into 'DESIGN.md' following the canonical template.
3. Build 'preview.html' as a self-contained visual design catalog with an interactive Dark/Light toggle, color swatches with contrast badges, typography specimen, and live component playground.
4. Build 'preview-dark.html' as a static zero-JS catalog pre-rendered with obsidian dark surfaces (#09090b / #18181b).

OUTPUT DELIVERABLES:
1. DESIGN.md
2. preview.html
3. preview-dark.html

Deliver production-quality, auditable files directly in '{target_dir}' now.
```
