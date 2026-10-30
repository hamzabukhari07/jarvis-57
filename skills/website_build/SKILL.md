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
   - `custom_stack` (Universal Framework Support): Any stack requested by the user, including **Next.js (App Router / Pages Router)**, **Astro**, **Vue / Nuxt**, **Svelte / SvelteKit**, **Remix**, **SolidJS**, or **Vanilla HTML/CSS/JS**. Whichever stack is chosen, the agent translates the reference design DNA (tokens, typography, card geometry, micro-interactions) 100% faithfully into the idiomatic conventions of that framework.

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
When delegating a build task to Google Antigravity Agent, OpenCode, Kilo Code, or Autonomous Fleet Agents, format the task directive using the standardized direct-execution structure below.

#### Anti-Slop Core Axiom & Quality Directives
> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE QUALITY FILTER (what to reject)**, while the Reference HTML Template is an **IMMUTABLE READ-ONLY SOURCE OF TRUTH** supplying 100% of the **DESIGN DIRECTION** (typography, colors, tokens, card geometry, micro-interactions, responsive grid, visual rhythm). Anti-slop ensures engineering craft, responsiveness, and authentic content without imposing artificial design uniformity.

Every task directive must incorporate and enforce the **6 Mandatory Rejection Gates** and **4 Visual Authority Guards**:
- **Gate 1: Broken Responsive Layouts** — No absolute positioning hacks; require CSS Grid / Flexbox with standard breakpoints (375px, 768px, 1024px, 1280px+); zero horizontal scrollbar band-aids (`overflow-x: hidden`).
- **Gate 2: Default Unstyled HTML Controls** — No raw browser buttons, inputs, textareas, checkboxes, or select dropdowns; custom hover, active, and accessible focus states styled to match the reference template; no default Chrome blue focus rings.
- **Gate 3: Fake Placeholder Metrics, Cringe AI Buzzword Copy, or Lorem Ipsum** — No "0.00001ms Latency", "Next-Gen AI 2.0 Synergy Engine", "Loved by 10M Fortune 500 CEOs", or generic lorem ipsum; require authentic discovered user content or domain-accurate, contextual copy.
- **Gate 4: Non-Functioning Buttons or Dead Anchors** — No empty `href="#"` links jumping to top; smooth anchor scrolling to actual sections; working mobile menu toggles, working tabs, and working filter handlers.
- **Gate 5: Muddy Heavy Drop-Shadows (Shadow Restraint)** — Banned harsh, opaque black drop-shadows (e.g. `rgba(0,0,0,0.5)`, heavy `shadow-2xl` black smudges); required subtle diffuse ambient elevation, optical specular edge highlights, or fine 1px hairline border elevation (`border-white/[0.08]` or `border-black/[0.06]`).
- **Gate 6: Cheap Jump Hover Animations & Clunky Micro-Interactions (Hover Restraint)** — Banned `hover:scale-105`/`scale-110` jumps and abrupt zero-easing state changes; required restrained 1px border luminance highlights (`border-white/10` ➔ `border-white/25`), subtle background brightness lift, smooth 150–200ms ease-out transitions, and tactile active click compression (`active:scale-[0.98]`).
- **Guard 1: NO Prescriptive Style Overrides** — 100% visual authority belongs to the reference template; do not force dark glassmorphism on cream/editorial templates; preserve 0px hairline borders or organic textures when specified.
- **Guard 2: NO Cliché AI Purple/Indigo Gradients** — Strictly forbid `bg-gradient-to-r from-purple-600 to-indigo-600`, neon purple hero text, and floating purple ambient blobs.
- **Guard 3: NO Plain 90s RGB Primaries** — Pure `#ff0000`, `#00ff00`, `#0000ff` are banned; use calibrated palette tokens from the reference template.
- **Guard 4: NO Dead / Sluggish Interactions** — Buttons and cards must provide tactile feedback (active compression, smooth transitions) and clear visual state changes.

---

#### Scenario 1: Personal & Engineer Portfolio (Single-File HTML)

````markdown
[TASK DIRECTIVE]
Build a clean, high-performance, responsive single-file engineer portfolio for Hamza Bukhari (Staff AI Systems & Autonomous Agents Architect) in standalone HTML5 with embedded CSS and vanilla JavaScript.
Work within the existing target directory and output the deliverable directly as index.html with zero build or npm dependencies.

[DESIGN REFERENCES]
Use skills/website_build/references/3_portfolios/Hairline Grid Portfolio.html as the primary visual reference.
Study its hairline grid layout, typography, monospace metadata hierarchy, spacing rhythm, card geometry, and clean technical aesthetic.
Preserve the reference's visual identity (monochromatic palette, 1px hairline borders, subtle border hover glows) while adapting it to the engineer portfolio requirements.
Use its existing design patterns instead of introducing an unrelated design theme.
Do not copy unrelated personal data or project links from the reference.

[USER REQUIREMENTS & AUTHENTIC CONTENT]
Entity / Persona: Hamza Bukhari
Role: Creator & Lead Architect of ZEZO | Staff AI Systems & Autonomous Agents Engineer
Required Portfolio Sections:
Hero & Status Beacon: Full name, title, live availability status pill, concise technical bio, and quick-action links (Resume, GitHub, Email, Contact).
Architecture & Systems Grid: Showcase flagship platforms (e.g. ZEZO Autonomous Voice & Agentic OS, Uncage Reverse-Engineering Cloner, Neural Memory Subsystem, Distributed Task Engine).
Technical Skills & Stack: Grouped monospace skill tags (Python, TypeScript, React, Next.js, Rust, Distributed Systems, WebSockets, LLM Orchestration).
Experience & Milestones Timeline: Chronological roles, achievements, high-throughput systems scaling, and lead architect milestones.
Publications / Architecture Notes: Technical writing entries or deep dives with reading times and tags.
Contact & Footer: Verified mailto link, GitHub profile link, LinkedIn, and clean 1px hairline terminal footer.
Content Authenticity:
Use authentic project titles, real tech stacks, and realistic metrics.
Never inject placeholder buzzwords, fake corporate logos, or lorem ipsum filler.

[EXECUTION & SUBAGENT STRATEGY]
Inspect the reference template structure, embedded styles, font imports, and scripts before writing code.
Recreate the website as a single, self-contained standalone HTML file containing all HTML, CSS, and vanilla JS.
Use semantic HTML5 elements, CSS Grid, and Flexbox for responsive desktop, tablet, and mobile viewing.
Preserve the reference's authentic fonts, SVG icons, and clean micro-interactions.
Do not introduce external npm dependencies, build tools, or complex multi-file abstractions.

[VALIDATION & QUALITY REQUIREMENTS]
Verify that index.html opens and renders flawlessly in standard browsers with zero external script or font errors.
Verify responsive behavior across 375px, 768px, 1024px, and 1440px viewports without horizontal scrollbars.
Test smooth anchor scrolling for all navigation links and verify no dead href="#" links exist.
Verify subtle hover transitions on cards and project rows without jarring scale jumps.
Ensure all copy is authentic, coherent, and reflects the engineer's domain.
Deliverable: A complete, responsive, self-contained single-file HTML portfolio ready for instant browser preview.
````

---

#### Scenario 2: High-Converting SaaS Marketing Landing Page (React 18 + TypeScript + Tailwind CSS)

````markdown
[TASK DIRECTIVE]
Build a high-converting, production-ready SaaS marketing landing page for CloudMetrics (Autonomous Cloud Observability Platform) using React 18, TypeScript, Tailwind CSS, and Lucide React icons.
Work within the Vite + React architecture under src/ and preserve modular component organization.

[DESIGN REFERENCES]
Use skills/website_build/references/1_landing_pages/saas.html as the primary visual reference.
Study its high-converting structure, Plus Jakarta Sans typography, dark obsidian glassmorphism, pill badges, feature grids, and button micro-interactions.
Preserve the reference's visual identity, color tokens, borders, and ambient specular highlights while adapting it to the CloudMetrics platform.
Use its existing design patterns instead of introducing an unrelated theme or generic templates.
Do not copy unrelated marketing copy or brand assets from the reference.

[USER REQUIREMENTS & AUTHENTIC CONTENT]
Application / Product: CloudMetrics (Autonomous Cloud Observability & Telemetry Engine)
Required Landing Page Sections:
Announcement Bar & Header: Sticky blur navbar with brand logo, product navigation dropdowns, docs link, and high-contrast pill CTA ("Start Free Trial").
Hero Section: High-converting headline, crisp value proposition subhead, primary CTA, secondary "Watch Interactive Demo" button, and an interactive telemetry frame mockup.
Social Proof / Logo Ticker: Trusted enterprise badges with clean grayscale SVG logos.
Bento Feature Grid: 4-card interactive bento layout showcasing real-time traces, AI anomaly detection, zero-overhead eBPF agents, and automated root-cause analysis.
Metrics & Telemetry Counter: Verified operational metrics with animated counter cards.
Interactive Pricing Matrix: Monthly / Annual toggle (with "Save 20%" discount badge), 3 tier cards (Starter, Pro, Enterprise) with feature checkmarks and distinct primary tier highlight.
Testimonials Carousel: Authentic customer testimonials with avatars, names, titles, and verified company tags.
FAQ Accordion: Interactive expand/collapse FAQ questions addressing security, data residency, integration, and pricing.
Final Conversion CTA & Footer: High-impact dark obsidian CTA banner and comprehensive 5-column footer with legal and status links.
Content Authenticity:
Use domain-accurate cloud observability terminology (eBPF, OpenTelemetry, p99 latency, anomaly isolation).
Never use fake cringe claims like "1000000x faster than reality" or generic lorem ipsum text.

[EXECUTION & SUBAGENT STRATEGY]
Inspect the existing project setup, Tailwind configuration, and component directory structure before implementation.
Modularize into clean, reusable components under src/components/ (e.g., Navbar, Hero, FeatureGrid, BentoCard, PricingTable, FAQAccordion, Footer).
Use TypeScript interfaces for all component props and state models; ensure zero type errors.
Use Lucide React icons for crisp, unified iconography.
Implement interactive states (pricing annual/monthly switch, FAQ accordion toggles, mobile hamburger navigation) with clean React hooks (useState).

[VALIDATION & QUALITY REQUIREMENTS]
Verify that the development server starts cleanly and renders without runtime or React hydration warnings.
Confirm zero TypeScript compilation errors (tsc --noEmit passes).
Test mobile responsive layout down to 375px; verify mobile navigation drawer opens, closes, and navigates cleanly.
Confirm interactive states: annual/monthly toggle accurately updates pricing numbers, FAQ items expand and collapse smoothly.
Verify that all buttons and links have active tactile compression and valid destinations.
Ensure visual hierarchy matches the reference: subtle 1px hairline borders, optical specular glows, and no muddy heavy drop-shadows.
Deliverable: A complete, responsive, modular React 18 + TypeScript + Tailwind CSS landing page ready for production deployment.
````

---

#### Scenario 3: CloudFleet Command Console Operational Analytics Dashboard (Next.js App Router, TypeScript, Tailwind, Lucide)

````markdown
[TASK DIRECTIVE]
Build a responsive operational analytics dashboard for CloudFleet Command Console using Next.js App Router, TypeScript, Tailwind CSS, and Lucide icons.
Work within the existing project directory and preserve its current architecture where practical.

[DESIGN REFERENCES]
Use skills/website_build/references/4_dashboards/orbit admin.html as the primary visual reference.
Study its dashboard layout, navigation, typography, data density, spacing, panels, and visual hierarchy.
Preserve the reference's visual identity while adapting it to the dashboard requirements.
Use its existing design patterns instead of introducing an unrelated dashboard theme.
Do not copy unrelated branding or data from the reference.

[USER REQUIREMENTS & AUTHENTIC CONTENT]
Application: CloudFleet Command Console
Required Dashboard Areas:
Cluster Health: Display the health status of infrastructure clusters.
Worker Nodes: Show worker-node status and relevant operational details.
Queue Latency: Present latency data in clear, readable charts.
Audit Logs: Provide a readable log panel with timestamps, severity, and event details.
Task Management: Display a task table with useful columns, status indicators, and working filters.
Data Behavior:
Use available real data if the project provides it.
Otherwise, use clearly identified sample data for the dashboard preview.
Do not present simulated values as live production telemetry.
Ensure charts, tables, and status indicators accurately reflect the data being displayed.

[EXECUTION & SUBAGENT STRATEGY]
Inspect the existing project, routes, components, and dependencies before implementation.
Use subagents only when useful for independent work, such as dashboard layout, charts, tables, and validation.
Use reusable components where appropriate without overengineering the application.
Use client components only where interactive behavior requires them.
Preserve existing functionality and avoid unrelated refactoring.
Do not create unnecessary helper scripts, duplicate components, or dependencies.

[VALIDATION & QUALITY REQUIREMENTS]
Verify that the dashboard starts and renders correctly.
Test task filters, navigation, and other implemented interactions.
Confirm charts render correctly and display the intended data.
Check responsive behavior and prevent accidental horizontal overflow.
Ensure readable tables, clear status indicators, and consistent visual hierarchy.
Resolve relevant TypeScript errors, runtime errors, and broken interactions.
Clearly distinguish sample data from live data.
Inspect the finished dashboard before reporting completion.
Deliverable: A working, responsive Next.js dashboard with functional interactions and clearly presented operational data.
````

---

## 🛑 3. PHASE 3: ANTI-SLOP AS NEGATIVE QUALITY FILTERS (WHAT NOT TO DO)

> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE FILTER (what to reject)**, NOT a prescriptive style enforcer. The chosen reference HTML template has **100% visual authority** over colors, typography, border geometry, shadows, and layout structure. Anti-slop rules ensure engineering craft, responsiveness, and authentic content without imposing artificial design uniformity.

### 🔴 Mandatory Rejection Gates (The 6 Core Negative Filters)

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

5. ❌ **Muddy, Heavy Drop-Shadows (Anti-Slop Shadow Restraint):**
   - **Banned:** Harsh, muddy, opaque black drop-shadows (e.g., `box-shadow: 0 20px 25px rgba(0,0,0,0.5)`, heavy `shadow-2xl` black smudges, or deep multi-layered ink-like blurs).
   - **Required:** Subtle, diffuse ambient elevation, optical specular edge highlights, or fine 1px hairline border elevation (`border-white/[0.08]` or `border-black/[0.06]`). Shadows must feel photographic and physically grounded, never like dirty ink spills.

6. ❌ **Cheap Jump Hover Animations & Clunky Micro-Interactions (Anti-Slop Hover Restraint):**
   - **Banned:** Jarring, aggressive jump transforms (e.g., `hover:scale-105`, `hover:scale-110`, cheap 90s bouncy zoom jumps) and abrupt zero-easing state changes.
   - **Required:** Restrained, tactile micro-interactions:
     - 1px hairline border luminance highlights on hover (`border-white/10` ➔ `border-white/25` or `border-neutral-200` ➔ `border-neutral-400`).
     - Subtle background brightness lift (e.g., `hover:bg-white/[0.04]` or `hover:bg-black/[0.02]`).
     - Smooth 150ms–200ms ease-out transitions (`transition: all 150ms cubic-bezier(0.16, 1, 0.3, 1)` or explicit property transitions).
     - Tactile active click compression (`active:scale-[0.98]`) for interactive buttons and cards to give physical substance.

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

### Branch C: Universal Custom Stacks (`tech_stack: custom_stack / nextjs / astro / vue / svelte / etc.`)
1. **Framework-Idiomatic Scaffolding:**
   - **Next.js (App Router):** `app/layout.tsx`, `app/page.tsx`, `components/`, Tailwind config, clean server/client component boundaries (`use client` only where interactive state is required).
   - **Astro:** `src/pages/index.astro`, `src/components/`, content collections or static markdown when appropriate.
   - **Vue / Nuxt:** `src/App.vue` or `app.vue`, modular single-file components (`.vue`), script setup syntax.
   - **Svelte / SvelteKit:** `src/routes/+page.svelte`, modular Svelte components.
2. **Design DNA Translation:**
   - Faithfully translate the reference template's CSS variables, font imports, color tokens, and spacing rhythm into the target framework's styling system (Tailwind config, CSS Modules, or scoped styles).
   - Never downgrade styling or replace bespoke craftsmanship with generic framework starter defaults.
3. **Clean Dependency Hygiene:**
   - Only install packages strictly needed for the implementation.
   - Generate production-ready, error-free TypeScript/JavaScript with full type safety.

---

## 🚀 5. PHASE 5: VERIFICATION & SMART LIVE PREVIEW

Never declare a web build task complete without verifying rendering, server health, and obtaining user confirmation before preview launch:

### 5.1 Protocol & Build Integrity
1. **Never launch modern framework projects via `file://` protocol:** Browsers block ES module imports and routing on `file://`.
2. **Compile / Build Verification:** Run a quick static verification (e.g. `npm run build` or `npm run typecheck` if available, or syntax lint) to ensure zero syntax or module resolution errors.

### 5.2 Smart Universal Stack Detection & Runner
Detect the project type from `package.json` / workspace layout and run the appropriate dev server:
- **Next.js:** Launch `npm run dev` (default port `3000`).
- **Vite (React, Vue, Svelte, Vanilla):** Launch `npx vite --port 5173` or `npm run dev`.
- **Astro:** Launch `npx astro dev --port 4321`.
- **Static Single-File HTML:** Serve via ZEZO Ephemeral Preview Server on ports `9400–9480` or direct local browser.
- **Process Spawning Rule:** Always run background development servers asynchronously with `creationflags=subprocess.CREATE_NO_WINDOW` on Windows so no orphaned CLI windows pop up.

### 5.3 Background HTTP 200 Healthcheck
Before notifying the user that the site is ready:
1. Poll the target local server port (e.g., `http://localhost:3000`, `http://localhost:5173`, `http://localhost:9400`) in the background.
2. Verify that the server returns an **HTTP 200** status code.
3. If an error occurs or port conflicts arise, resolve the port or fix the build error before presenting the preview.

### 5.4 Mandatory User Confirmation Gate (NEVER Auto-Open Browser)
> ⚠️ **CRITICAL INVARIANT:** Never automatically open or pop up a browser window, webview, or system default application without explicit user permission. Auto-launching preview windows interrupts the user's workflow.

1. **Step 1 — Announce Readiness:** Once the server is running and verified healthy (HTTP 200), present a clear, polite confirmation prompt:
   > *"Website build ho chuki hai aur `http://localhost:[port]` par successfully active hai. Kya main preview window open karun?"*  
   > *(Or in English: "Website build is complete and running at `http://localhost:[port]`. Would you like me to open the live preview window?")*
2. **Step 2 — Wait for User Confirmation:** Do NOT call any browser launch command, shell `start`, or preview action until the user responds with affirmative intent (*"yes"*, *"open"*, *"preview dikhao"*, *"haan"*, *"proceed"*).
3. **Step 3 — Launch Preview on Confirmation:** Only upon explicit confirmation, invoke the preview opener or HUD preview.
