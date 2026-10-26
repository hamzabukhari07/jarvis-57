---
name: website_build
description: "Master studio protocol for creating websites, landing pages, and UI components adhering to Hamza Taste design references and anti-slop gates."
domain: ui
author: "Hamza Bukhari"
version: "1.1.0"
triggers: ["build website", "create landing page", "make website", "hero section", "pricing table", "web app"]
auto_activate: true
---

# 🌐 Master Studio Website Creation Protocol (`website_build`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Fleet, and all UI coding agents.  
> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE QUALITY FILTER** (what to reject), while the **Reference HTML Template** is an **IMMUTABLE READ-ONLY SOURCE OF TRUTH** supplying 100% of the **DESIGN DIRECTION** (typography, colors, tokens, card geometry, micro-interactions, responsive grid, visual rhythm). The agent never mutates or overwrites the reference file; instead, it analyzes the reference design DNA and synthesizes the target deliverable (`index.html` or new pages/sections) with authentic client content, extending any new sections using the exact same structural patterns.

---

## 📋 1. PHASE 1: INTAKE & CONTENT DISCOVERY PROTOCOL

Before writing any code or initializing build scaffolds, every coding agent and orchestrator must ensure the user's intent, real content, and custom requirements are discovered:

### 1.1 Discovery Pillars

1. **Scope (`scope_type`):**
   - `landing_page`: High-converting marketing landing page or product showcase.
   - `portfolio`: Personal showcase, developer resume, creative studio, or executive profile.
   - `business_site`: Multi-section corporate, service, clinic, or studio website.
   - `dashboard`: Metrics, telemetry console, admin panel, or web OS interface.
   - `component`: Targeted isolated UI block (Hero Section, Pricing Matrix, Navbar, Modal).

2. **Entity & Content Discovery (`entity_content` — MANDATORY for Portfolios & Business/Personal Sites):**
   - **Identity & Name:** Who is this website for? (e.g., Hamza Bukhari, Dr. Smith Dental Clinic).
   - **Role / Specialization / Bio:** Real profession, background, and value proposition.
   - **Featured Projects / Services:** Actual project names, descriptions, tech stack, and live URLs.
   - **Experience & Milestones:** Real achievements, background, or core offerings.
   - **Contact & Socials:** Real email, GitHub, LinkedIn, Twitter/X, or booking link.
   - **Desktop Resume / Document Check:** If details are not provided upfront, ask or check if a resume or profile document exists on Desktop (e.g. `Desktop/*Resume*.pdf` or `Desktop/*CV*.pdf`) to extract authentic experience and projects.
   - *Rule:* Never generate a portfolio or business site with placeholder dummy names or fake AI text when user content can be discovered!

3. **Custom Requirements & New Sections:**
   - Inquire if the user requires specific sections beyond the standard reference layout (e.g., custom Pricing Calculator, Testimonial Slider, FAQ Accordion, Interactive Demo, Booking Form, or Multi-page navigation).

4. **Tech Stack (`tech_stack`):**
   - `single_file_html`: Standalone, self-contained single-file HTML5 deliverable. Zero npm dependencies, inline styles/scripts, instant double-click preview.
   - `react_tailwind`: Modular React 18 + TypeScript + Tailwind CSS (Vite architecture, production-grade clean code).

5. **Visual Direction:**
   - **100% Inherited from the Matched Reference Template:** The visual direction (colors, typography, geometry, and feel) is governed directly by the authentic reference template. Inquire only about broad aesthetic preference (e.g. Clean Minimalist, Dark Tech, Tactile Editorial Warm, Creative Bold) if not obvious from the user's prompt.

### 1.2 Intake Dialogue Rules
- **Portfolio & Personal / Business Site Requests:** Always ask the necessary content discovery questions first (Who is this for? What is your role/specialization? What are your key projects/services? Do you have a resume on Desktop to pull from?).
- **Fully Specified Requests:** If the user already provided the identity, role, and requirements, proceed directly without redundant questions.
- **Confirmation Read-Back:** Before executing, state a concise 1-sentence confirmation commitment:
  > *"Plan: Build a **[scope_type]** for **[entity_content / identity]** using **[tech_stack]** based on **[reference_template]** aesthetic into Desktop/**[folder_name]**. Should I proceed?"*

Execution proceeds **only** after the user confirms (*"yes"*, *"proceed"*, *"build it"*, *"haan"*).

---

## 🎨 2. PHASE 2: DESIGN FOUNDATION (REFERENCE TAXONOMY & CLONING PROTOCOL)

Do NOT invent, extrapolate, or hallucinate visual tokens from thin air. Visual direction, color palettes, spacing rhythm, card elevation, and typography MUST be derived directly from the curated reference library and catalog index (`skills/website_build/references/catalog.json`).

All design templates are strictly organized into **5 Scope Subdirectories** under `skills/website_build/references/`:

### 2.1 The 5 Standardized Scope Directories & Curated Templates (23 Production HTML Assets)

#### 1. Landing Pages (`skills/website_build/references/1_landing_pages/`) — 10 Flagship Templates
- **`1_landing_pages/saas.html`** (*Hamza Taste SaaS B2B Platform*): Plus Jakarta Sans, high-density feature grid, subtle border highlights, clean pill badges.
- **`1_landing_pages/solvine.html`** (*Solvine Modern SaaS*): Cloud & developer platform, obsidian glass cards, high-contrast dark mode.
- **`1_landing_pages/clerk clone.html`** (*Clerk Authentication & Identity*): Clean developer auth experience, dark obsidian glassmorphism, input focus states.
- **`1_landing_pages/dub.html`** (*Dub Links Marketing & Conversion*): High-converting pill CTAs, link preview cards, stat counters, crisp micro-interactions.
- **`1_landing_pages/ai landing page.html`** (*Taskmuse AI Autopilot Landing*): Warm minimal light aesthetic, task automation showcase, clean badge chips.
- **`1_landing_pages/blinq.html`** (*Blinq Dynamic Conversion Landing*): Modern startup showcase, device frame mockups, clean card hierarchy.
- **`1_landing_pages/Crazy UI landing page.html`** (*CrazyUI Bold Creative Agency*): Warm cream background (`#f6f4f2`), Instrument Serif typography, bold dynamic asymmetry.
- **`1_landing_pages/Sticker Landing.html`** (*Loudish Playful Studio*): Playful creative studio, sticker badge accents, high-energy layouts.
- **`1_landing_pages/Cut-Paper Collective Site.html`** (*Commonfold Cut-Paper Collective*): Tactile editorial paper texture, craftsmanship showcase, warm organic tones.
- **`1_landing_pages/nami landing page.html`** (*Nami Editorial Wave Landing*): Warm sand tones (`#d97706` accent), quiet elegance, editorial typography discipline.

#### 2. Business & Corporate Sites (`skills/website_build/references/2_business_sites/`) — 3 Templates
- **`2_business_sites/frewall.html`** (*Fernwell Health & Pharmacy*): Clean medical/wellness aesthetics, trustworthy layout, modern pharmacy cards.
- **`2_business_sites/racquet club.html`** (*Cirrus Racquet Club Luxury*): Luxury hospitality & sports club, warm organic tones, serif/sans pairing, gold accents.
- **`2_business_sites/arclune.html`** (*Arclune Engineering & Design Studio*): Architectural studio, structured grids, monochromatic elegance.

#### 3. Portfolios & Resumes (`skills/website_build/references/3_portfolios/`) — 2 Templates
- **`3_portfolios/Hairline Grid Portfolio.html`** (*Hairline Grid Engineer Portfolio*): Ultra-fine 1px hairline grid, monospace technical details, developer/architect resume.
- **`3_portfolios/Scrapbook Resume.html`** (*Tessa Marlowe Scrapbook Resume*): Tactile editorial portfolio, organic scrapbooking elements, warm paper aesthetic.

#### 4. Dashboards & Consoles (`skills/website_build/references/4_dashboards/`) — 3 Templates
- **`4_dashboards/Standalone Ecosystem.html`** (*Dense Infrastructure Ecosystem Console*): Deep black void (`#050505`), multi-panel console layout, metric stat cards, tabular telemetry.
- **`4_dashboards/orbit admin.html`** (*Orbit Ops Modern Analytics Admin*): Clean, dense operational analytics dashboard, filter controls, data cards.
- **`4_dashboards/froma os .html`** (*Forma OS Window Desktop Environment*): Floating draggable window frames, dock navigation, desktop OS simulation.

#### 5. Isolated UI Components (`skills/website_build/references/5_components/`) — 5 Templates
- **`5_components/aura frame.html`** (*Aura Spatial Glowing Luxury Frame*): Spatial luxury frame, white & zinc accents, ultra-fine 1px glow border geometry.
- **`5_components/autonomus.html`** (*Autonomus AI Agent Terminal Card*): Pitch-black void (`#050505`), glowing status beacons, cyber terminal aesthetics.
- **`5_components/skeumorphic spatial component.html`** (*Skeuomorphic Spatial Glass Card*): Layered specular lighting, realistic inner shadows, tactile surface response.
- **`5_components/image gen.html`** (*Image Gen Media Canvas & Prompt Bar*): Floating prompt input bar with action pills, masonry image output grid.
- **`5_components/nexus.html`** (*Nexus Cyber HUD Inspiration Card*): High-density dark telemetry cards, scanline accents, system status indicator beacons.

### 2.2 Deterministic `catalog.json` Querying Protocol
Every coding agent, orchestrator, and design resolver must follow this deterministic lookup protocol:
1. **Load Catalog Index:** Read `skills/website_build/references/catalog.json`.
2. **Filter by Scope & Vibe:** Narrow candidates by matching the resolved `scope_type` (e.g. `landing_page`, `business_site`, `portfolio`, `dashboard`, `component`) and aesthetic style keywords.
3. **Keyword & Tag Scoring:** Calculate relevance score by matching task keywords (e.g., "auth", "crypto", "sports", "agency", "medical") against candidate `tags`, `name`, and `id`.
4. **Zero Modulo / Random Hash:** Never use modulo or hash-based random template selection. Deterministic highest-score match is strictly enforced.

### 2.3 Read-Only Reference Provisioning & Clean Separation
- The matched reference HTML template is provided as an **IMMUTABLE READ-ONLY REFERENCE** (either kept in `skills/website_build/references/` or copied as a read-only `reference.html` in the workspace).
- **NEVER overwrite, mutate, or delete the reference file.**
- The agent reads and reverse-engineers the reference file's complete Design System DNA (fonts, colors, spacing rhythm, card elevation, micro-interactions) and generates the new deliverable (`index.html`) using the client's authentic discovered content.

### 2.4 Extensibility Protocol (Creating New Sections & Pages)
When the user requests additional sections, components, or pages not present in the original reference template:
1. **Zero Style Reinvention:** Do NOT invent a new aesthetic, font, or color scheme for the new section.
2. **Structural Pattern Borrowing:**
   - Use the exact same card wrapper markup, border tokens, and padding rhythm found in existing sections.
   - Use the same heading typography classes (`text-xs font-mono uppercase tracking-widest` or `text-3xl font-serif tracking-tight`).
   - Use the same button classes, hover states, and badge pills.
3. **Seamless Blend:** The newly synthesized section must look as if it was designed by the original human designer in the exact same sitting.

---

### 2.5 Master System Directive (Agent Prompt Template)
When delegating a build task to Google Antigravity Agent, OpenCode, or Kilo Code, use this standard directive:

```markdown
# 🏛️ SYSTEM DIRECTIVE: DESIGN-SYSTEM CLONING & CONTENT ADAPTATION

You are an Elite Frontend Systems Architect & UI Designer.
Your mandate is to craft a production-grade web experience by strictly adopting the visual design system of an existing, human-crafted reference HTML template, without altering or degrading the original reference.

---

### 📂 INPUT CONTEXT PROVIDED:
1. **REFERENCE TEMPLATE (READ-ONLY):** `{reference_file_path}`
   - DO NOT EDIT, DELETE, OR MUTATE THIS FILE. This is your immutable source of design truth.
2. **CLIENT IDENTITY & AUTHENTIC CONTENT:**
   - Name / Entity: `{client_name}`
   - Role / Specialization: `{client_role}`
   - Bio / Value Proposition: `{client_bio}`
   - Key Projects / Services / Milestones: `{client_projects}`
   - Contact & Socials: `{client_socials}`
3. **USER CUSTOM REQUIREMENTS / NEW SECTIONS:**
   - `{custom_requirements_or_new_sections}`

---

### 📐 EXECUTION PROTOCOL (4-PHASE SYNTHESIS):

#### PHASE 1: REVERSE-ENGINEER THE DESIGN SYSTEM DNA
Before writing a single line of target code, thoroughly inspect `{reference_file_path}` and extract:
1. **Typography Discipline:** Exact font family imports (Google Fonts, custom serif/sans, system stacks), line-heights, letter-spacing (`tracking-tight`), and font-weight scales.
2. **Color Palette Tokens:** Primary backgrounds (e.g., exact HEX/HSL, grain, paper texture, or matte void), text contrast hierarchy, border colors (e.g., 1px subtle hairline `border-white/10` or organic cream borders), and brand accents.
3. **Card & Container Geometry:** Exact border-radii (`rounded-none`, `rounded-xl`, `rounded-3xl`), padding rhythms, inner shadows, and glassmorphic elevations.
4. **Interactive Micro-Interactions:** Exact CSS transitions, hover transforms, button styles (pill, bordered, magnetic, glow), and script interactions.

#### PHASE 2: INTACT ARCHITECTURAL SYNTHESIS (NEW DELIVERABLE)
- Generate the final deliverable as `{target_file_path}` (e.g., `index.html`).
- **NEVER generate generic AI boilerplate or change the aesthetic direction.**
- If the reference is a Warm Cut-Paper Editorial, your output MUST be 100% Warm Cut-Paper Editorial.
- If the reference is a Monospace Hairline Tech Grid, your output MUST be 100% Monospace Hairline Tech Grid.

#### PHASE 3: AUTHENTIC CONTENT INJECTION (ZERO AI SLOP)
- Replace all placeholder names, dummy titles, and generic links in the template with the provided Client Identity & Content.
- **Strictly Banned:**
  ❌ "Lorem ipsum" or dummy filler text.
  ❌ Cringe AI buzzwords ("Next-Gen AI 2.0", "Synergy", "0.00001ms latency").
  ❌ Broken anchors (`href="#"` that jump to top). Use real section IDs (`#projects`, `#contact`) or functional actions.

#### PHASE 4: EXTENSIBILITY PROTOCOL (CREATING NEW SECTIONS)
If the user requested new sections, pages, or components that did NOT exist in the reference template:
- **DO NOT invent a new style.**
- Clone the existing structural patterns: borrow the card wrappers, badge styles, header hierarchies, and button markup already present in the reference template.
- The new sections must look as if they were designed and crafted by the original human designer in the exact same sitting.

---

### 🎯 FINAL DELIVERABLE:
Deliver a complete, fully functioning, self-contained, responsive `{target_file_path}` that faithfully mirrors the craftsmanship of the reference template while presenting the client's authentic content.
```

---

## 🛑 3. PHASE 3: ANTI-SLOP AS NEGATIVE QUALITY FILTERS (WHAT NOT TO DO)

> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE FILTER (what to reject)**, NOT a prescriptive style enforcer. The chosen reference HTML template has **100% visual authority** over colors, typography, border geometry, shadows, and layout structure. Anti-slop rules ensure engineering craft, responsiveness, and authentic content without imposing artificial design uniformity.

### 🔴 Mandatory Rejection Gates (The 4 Core Negative Filters)

1. ❌ **Broken Responsive Layouts:**
   - Absolute positioning hacks for structural layout are strictly banned.
   - Layouts MUST use CSS Grid or Flexbox with responsive mobile breakpoints (`375px`, `768px`, `1024px`, `1280px`+).
   - No layout overflow clipping or accidental horizontal scrollbars (`overflow-x: hidden` used as a band-aid for broken element widths is banned).
   - Containers must maintain centered max-width bounds appropriate to the reference template structure.

2. ❌ **Default Unstyled HTML Controls:**
   - Raw default browser buttons, inputs, textareas, checkboxes, and select dropdowns are strictly forbidden.
   - Every interactive control must be styled to match the reference template's design language, including custom hover, active, and accessible focus states.
   - No default browser focus rings (e.g., unstyled Chrome blue outlines); use coordinated focus states.
   - Custom-styled scrollbars when scroll containers are present.

3. ❌ **Fake Placeholder Metrics, Cringe AI Buzzword Copy, or Lorem Ipsum:**
   - Never use cringe placeholder copy or fake metrics like *"0.00001ms Latency"*, *"Next-Gen AI 2.0 Synergy Engine"*, or *"Loved by 10M Fortune 500 CEOs"*.
   - Never generate generic lorem ipsum filler.
   - For portfolios and entity sites, use the real user's bio, actual project names, and authentic experience discovered in Pillar 2. If copy must be synthesized, write realistic, authentic, and contextual copy relevant to the client's business domain.

4. ❌ **Non-Functioning Buttons or Dead Anchors:**
   - No empty `href="#"` links that jump to page top or do nothing.
   - All navigation links must smoothly anchor to actual page sections (e.g., `href="#projects"`, `href="#experience"`) or trigger real functional behaviors.
   - Interactive components (mobile menu toggles, modal dialogs, tab switching, copy-to-clipboard, filter pills) must execute working JavaScript handlers.
   - External links (GitHub, LinkedIn, Email) must use valid targets or realistic mailto/URL schemes.

### 🟡 Visual Authority & Anti-Override Guards

1. ❌ **NO Prescriptive Style Overrides (100% Visual Authority to Reference Template):**
   - **Do NOT force dark glassmorphism, fixed border radii, or specific color palettes onto templates that specify different aesthetics.**
   - If a template uses sharp 0px hairline borders (e.g., *Hairline Grid Portfolio*), preserve `0px` border radii and monospace precision.
   - If a template uses warm cream backgrounds and editorial serif typography (e.g., *Crazy UI*, *Scrapbook Resume*), preserve those exact background tones, serif font imports, and organic textures.
   - If a template uses tactile paper layers or colorful sticker badges (e.g., *Cut-Paper Collective*, *Sticker Landing*), preserve them without injecting dark obsidian glass.
   - **Colors, typography, border geometry, shadows, and layout rhythm belong 100% to the chosen reference HTML template.**
2. ❌ **NO Cliché AI Purple/Indigo Gradients:** Strictly forbid generic `bg-gradient-to-r from-purple-600 to-indigo-600`, neon purple hero text, or floating ambient blobs. Use the calibrated palette tokens directly from the reference template.
3. ❌ **NO Plain 90s RGB Primaries:** Pure `#ff0000`, `#00ff00`, `#0000ff` are banned. Use calibrated palette tokens from the reference template.
4. ❌ **NO Dead / Sluggish Interactions:**
   - Interactive buttons and cards should provide tactile feedback (active compression, smooth transitions).
   - Hover states must provide clear visual feedback (brightness boost, border glow, or color shift) consistent with the reference template's aesthetic.

---

## 💻 4. PHASE 4: CODE GENERATION & STACK RULES

### Branch A: Single-File HTML Stack (`tech_stack: single_file_html`)
1. **Single Deliverable:** Exactly ONE self-contained `index.html` file in the workspace root, synthesized from the reference template.
2. **Asset Preservation:** Preserve the authentic fonts, SVG icons, embedded styles, and interactive scripts from the reference template. Do not strip out styles or introduce broken external links.
3. **Zero Build Dependencies:** No `package.json`, no `node_modules`, no build steps. The file must render flawlessly when opened directly.

### Branch B: Modular React 18 + Tailwind Stack (`tech_stack: react_tailwind`)
1. **Project Architecture:**
   - Provide standard Vite + React + TypeScript scaffold files: `package.json`, `vite.config.ts`, `tailwind.config.js`, `tsconfig.json`, `index.html`.
   - Source code modularized under `src/` (e.g. `App.tsx`, `main.tsx`, and component files reflecting the reference template structure).
2. **Valid JSX / TSX:**
   - All attributes must be valid React JSX (`class` ➔ `className`, `for` ➔ `htmlFor`, inline styles as objects).
   - Zero missing imports or unresolved TS interfaces.

---

## 🚀 5. PHASE 5: VERIFICATION & SMART LIVE PREVIEW

Never declare a web build task complete without verifying rendering and preview accessibility:

1. **Protocol Integrity:**
   - **Never launch React / Vite projects via `file://` protocol.** Browsers block ES module imports on `file://`.
2. **Vite / React Verification:**
   - Ensure dependencies are installed (`npm install`).
   - Launch background development server (e.g. `npm run dev` or `npx vite --port 3000`).
   - Confirm server responds with HTTP 200 before presenting preview URL to the user.
3. **Single-File HTML Preview:**
   - Serve static HTML projects via ZEZO's ephemeral preview server on ports `9400–9480` or direct local browser launch.
   - Verify that all SVG icons, font imports, and interactive scripts execute without uncaught JavaScript console errors.
