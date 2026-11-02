---
name: generate_design_md
description: "Master studio protocol for auditing, extracting, and documenting design systems into canonical DESIGN.md and preview.html specifications via autonomous coding engines."
domain: design
author: "Hamza Bukhari"
version: "2.2.0"
execution_mode: "engine_only"
supported_engines: ["antigravity", "opencode", "kilo"]
supported_modes: ["url", "local"]
pre_flight_action: "scrapling_extract"
agent_directive_section: "Agent Directive"
ingested_files: ["site_dom.html", "site_styles.css", "site_tokens.json"]
required_tools: ["antigravity_run", "opencode_run", "kilo_run", "browser_control", "file_controller"]
output_files: ["DESIGN.md", "preview.html"]
triggers: ["generate design md", "extract design tokens", "extract design system", "create design spec", "analyze styling", "design system extraction", "audit design", "design tokens", "design system"]
tags: ["design", "tokens", "preview", "audit", "engine_only", "anti_slop", "dual_mode"]
auto_activate: true
---

# 🎨 Master Design System Extraction Protocol (`generate_design_md`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Core Subsystem:** Autonomous Coding Engine Pipeline (Google Antigravity CLI `agy`, OpenCode, Kilo Code)  
> **Target Audience:** Autonomous Coding Engines, Office Specialist Agents, and ZEZO Core Orchestrators.  
> **Core Axiom:** **Authenticity over invention.** Every token, color, font, radius, spacing step, and shadow documented must be traceable to real source code or extracted stylesheet data. You audit and extract the authentic design DNA — you do not redesign, invent unbacked tokens, or impose aesthetic bias.

---

## ⚡ 1. Two-Phase Execution Workflow

The protocol operates strictly in two modes depending on whether the target is a remote web destination or a local codebase:

### Mode 1: Live URL Mode (Scrapling Pre-Flight Ingestion)
1. **Target Directory Allocation:** ZEZO creates an isolated project workspace (e.g. `Desktop/<domain>-design-spec`).
2. **Headless Ingestion:** Pre-flight handler `scrapling_extract` fetches and dumps 3 files into the folder:
   - `site_dom.html`: Cleaned, hydrated DOM snapshot of the live webpage with semantic boundaries.
   - `site_styles.css`: Consolidated extracted stylesheets, computed rules, and CSS variables.
   - `site_tokens.json`: Pre-parsed JSON map of colors, typography, spacing, and radii.
3. **Execution Gate:** Coding engines (AntiGravity / OpenCode) inspect these 3 local files on disk as immutable truth without making external network calls.

### Mode 2: Local Codebase / Folder Mode
1. **Direct Inspection:** Coding engines inspect existing source code across 3 priority tiers:
   - **Tier 1 (System Sources):** `tailwind.config.*`, `theme.*`, `tokens.json`, CSS variables in `:root`/`.dark`, and global stylesheets.
   - **Tier 2 (Shared Primitives):** `components/ui/*`, `components/primitives/*`, button, input, card, dialog implementations.
   - **Tier 3 (Conflict Resolution):** Shared primitives override page-local overrides; repeated usage (≥3 times) overrides one-offs; newer files win. Ambiguities are recorded under "Known Issues / Gaps".

---

## 📄 2. Deliverables & Output Contract

Every extraction run delivers the following deliverables in the target directory:

### Deliverable 1: `DESIGN.md` (Canonical Specification)
Must follow this exact structure without omitting sections:
- **Overview:** Brand feel, density, corner language, surface hierarchy, primary mode.
- **Colors:** Table of tokens (`Primary`, `Primary Foreground`, `Secondary`, `Tertiary`, `Neutral`, `Neutral Foreground`, `Border`, `Destructive`, `Success`, `Warning`, `Info`) with hex values and roles.
- **Typography:** Headline, Body, and Monospace fonts with weights, line-heights, tracking, and type scale steps.
- **Spacing & Radius:** Spacing scale steps, corner radius tokens, and border conventions.
- **Elevation:** Box-shadow tokens (`shadow-sm`, `shadow-md`, `shadow-lg`) with exact CSS values and usage.
- **Components:** Documented states for Buttons, Inputs, Cards, Navigation, and Modals/Badges.
- **Do's and Don'ts:** Positive and negative patterns derived from source.
- **Known Issues / Gaps:** Missing or conflicting tokens.
- **Sources:** Traceable list of every file inspected.

### Deliverable 2: `preview.html` (Interactive Companion Catalog)
- **Single-File Standalone:** Zero external build dependencies. All styles embedded in `<style>` and scripts in `<script>`.
- **Interactive Light/Dark Toggle:** Seamlessly switches between light and dark palettes.
- **Color Swatches Grid:** Rendered with hex codes, token names, and WCAG AA/AAA contrast badges.
- **Typography Specimen:** Visual type scale hierarchy.
- **Component Playground:** Interactive Buttons, Form Inputs with focus rings, Cards with elevation, and Status Badges.

---

## 🛡️ 3. Anti-Slop Directives

- **Zero Generic AI Purple Gradients:** Never invent purple/pink glowing gradients unless defined in the source theme.
- **Zero Hallucinated Icons or Utilities:** Only reference libraries or CSS classes that exist in the source.
- **Authentic Density:** Match the exact density of the source (compact enterprise vs spacious marketing).
- **No Speculative Token Completion:** If a token is missing, write `Not found in source`. Never fabricate dummy hex codes.

---

## 🤖 Agent Directive

When auditing and extracting a design system, execute the corresponding directive based on the target mode:

### Scenario A: Extract Design System from Live URL (Pre-Flight Ingested Assets)
````markdown
You are an expert Frontend Systems Architect, UI Auditor, and Design Tokens Specialist. Your task is to audit and extract the authentic design system from the pre-flight extracted files of a live website in the workspace into canonical design system specifications.

The target directory contains three pre-flight extraction files:
1. 'site_dom.html' — Cleaned, hydrated DOM snapshot of the live webpage.
2. 'site_styles.css' — Extracted stylesheets, computed rules, and CSS variables.
3. 'site_tokens.json' — Pre-parsed JSON map of colors, typography, spacing, and radii.

CRITICAL CONSTRAINTS:
- Treat these three files as your primary immutable source of truth.
- Do not run external web searches or attempt to re-crawl the live URL.
- Audit and document what is actually present. Do not redesign, invent unbacked tokens, or impose aesthetic bias.
- Execute directly with surgical precision without leaving placeholder TODOs.

EXECUTION STEPS:
1. Ingest and cross-reference 'site_tokens.json', 'site_styles.css', and 'site_dom.html'.
2. Extract the complete visual DNA:
   - Color palette (Primary, Secondary, Tertiary, Neutral, Border, Semantic states).
   - Typography hierarchy (Font families, weights, type scale, line heights).
   - Spacing rhythm, corner radius scale, and elevation shadows.
   - Component primitives (Button variants, form inputs, cards, badges, navigation).
3. Generate 'DESIGN.md' following the canonical specification template.
4. Generate 'preview.html' as an interactive visual design catalog with Dark/Light toggle, color swatches with contrast badges, typography specimen, and live component playground.

OUTPUT DELIVERABLES:
1. DESIGN.md
2. preview.html

Deliver production-quality, auditable files directly in the target directory now.
````

### Scenario B: Extract Design System from Local Codebase / Workspace Files
````markdown
You are an expert Frontend Systems Architect, UI Auditor, and Design Tokens Specialist. Your task is to audit and extract the authentic design system from the local codebase and files in the workspace into canonical design system specifications.

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
- Zero generic AI purple gradients; maintain authentic density and spacing.

EXECUTION STEPS:
1. Scan and inspect all system configuration files, stylesheets, and UI primitives.
2. Synthesize the complete visual DNA into 'DESIGN.md' following the canonical template.
3. Build 'preview.html' as an interactive visual design catalog with Dark/Light toggle, color swatches with contrast badges, typography specimen, and live component playground.

OUTPUT DELIVERABLES:
1. DESIGN.md
2. preview.html

Deliver production-quality, auditable files directly in the target directory now.
````
