---
name: website_build
description: "Master studio protocol for creating websites, landing pages, and UI components adhering to Hamza Taste design references and anti-slop gates."
domain: ui
author: "Hamza Bukhari"
version: "1.2.0"
agent_directive_section: "Agent Directive"
required_tools: ["browser_control", "file_controller", "antigravity_run"]
triggers: ["build website", "create landing page", "make website", "hero section", "pricing table", "web app", "build site"]
tags: ["ui", "frontend", "greenfield", "anti_slop", "react", "html"]
auto_activate: true
---

# 🌐 Master Studio Website Creation Protocol (`website_build`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Agents, and all UI coding agents.  
> **Core Axiom:** Anti-Slop is strictly a **NEGATIVE QUALITY FILTER** (what to reject), while the **Reference HTML Template** is an **IMMUTABLE READ-ONLY SOURCE OF TRUTH** supplying 100% of the **DESIGN DIRECTION** (typography, colors, tokens, card geometry, micro-interactions, responsive grid, visual rhythm). The agent never mutates or overwrites the reference file; instead, it analyzes the reference design DNA and synthesizes the target deliverable (`index.html` or new pages/sections) with authentic client content, extending any new sections using the exact same structural patterns.

---

## 📋 1. Intake & Content Discovery Protocol

Before writing code or initializing scaffolds, discover user intent and real content:
1. **Scope (`scope_type`):** `landing_page`, `portfolio`, `business_site`, `dashboard`, `component`.
2. **Entity & Content Discovery:** Real identity/name, role/bio, actual projects, experience milestones, and authentic socials. Check Desktop for resumes (`Desktop/*Resume*.pdf`, `Desktop/*CV*.pdf`). Never generate placeholder dummy names!
3. **Tech Stack (`tech_stack`):** `single_file_html`, `react_tailwind`, or custom stacks (`nextjs`, `astro`, `vue`, `svelte`).
4. **Confirmation Read-Back:** Before executing, state a concise 1-sentence confirmation:
   > *"Plan: Build a **[scope_type]** for **[entity_content / identity]** using **[tech_stack]** based on **[reference_template]** aesthetic into Desktop/**[folder_name]**. Should I proceed?"*

---

## 🎨 2. Design Foundation & Reference Library

Derive visual tokens directly from the curated catalog (`skills/website_build/references/catalog.json`):
- **1. Landing Pages (`1_landing_pages/`):** `saas.html`, `solvine.html`, `clerk clone.html`, `dub.html`, `ai landing page.html`, `blinq.html`, `Crazy UI landing page.html`, `Sticker Landing.html`, `Cut-Paper Collective Site.html`, `nami landing page.html`.
- **2. Business & Corporate Sites (`2_business_sites/`):** `frewall.html`, `racquet club.html`, `arclune.html`.
- **3. Portfolios & Resumes (`3_portfolios/`):** `Hairline Grid Portfolio.html`, `Scrapbook Resume.html`.
- **4. Dashboards & Consoles (`4_dashboards/`):** `Standalone Ecosystem.html`, `orbit admin.html`, `froma os .html`.
- **5. Isolated Components (`5_components/`):** `aura frame.html`, `autonomus.html`, `skeumorphic spatial component.html`, `image gen.html`, `nexus.html`.

**Rules:**
- **Immutable Reference:** Never mutate, overwrite, or delete reference files.
- **Extensibility:** When creating new sections, borrow the exact card wrapper markup, border tokens, typography, and button classes from the reference.

---

## 🛑 3. Anti-Slop Quality Filters (What Not To Do)

Enforce the **6 Mandatory Rejection Gates** and **4 Visual Authority Guards**:
1. ❌ **Broken Responsive Layouts:** Banned absolute positioning hacks; require CSS Grid / Flexbox (375px, 768px, 1024px, 1280px+); zero horizontal scrollbars.
2. ❌ **Default Unstyled Controls:** Custom hover, active, and accessible focus states styled to match reference; no default Chrome blue rings.
3. ❌ **Fake Placeholder Metrics & Buzzword Copy:** No "0.00001ms Latency" or generic lorem ipsum; require authentic discovered domain copy.
4. ❌ **Non-Functioning Buttons or Dead Anchors:** No empty `href="#"`; smooth scrolling anchors and working interactive JS toggles.
5. ❌ **Muddy Heavy Drop-Shadows:** Banned harsh black `shadow-2xl` smudges; required subtle diffuse elevation or fine 1px hairline borders (`border-white/[0.08]` or `border-black/[0.06]`).
6. ❌ **Cheap Jump Hover Animations:** Banned `hover:scale-105` jumps; required 1px hairline border highlights, subtle background brightness lift, 150-200ms ease-out transitions, and active tactile compression (`active:scale-[0.98]`).
7. ❌ **NO Prescriptive Style Overrides:** 100% visual authority belongs to the reference template.
8. ❌ **NO Cliché AI Purple/Indigo Gradients:** Banned `bg-gradient-to-r from-purple-600 to-indigo-600` and neon purple blobs.
9. ❌ **NO Plain 90s RGB Primaries:** Use calibrated palette tokens from the reference template.
10. ❌ **NO Dead / Sluggish Interactions:** Clear visual state changes and tactile feedback.

---

## 💻 4. Code Generation & Stack Rules

- **Branch A: Single-File HTML:** Exactly ONE self-contained `index.html` in workspace root. Zero build steps, zero npm dependencies.
- **Branch B: Modular React 18 + Tailwind:** Clean Vite + React + TypeScript scaffold under `src/components/`, zero type errors (`tsc --noEmit` passes).
- **Branch C: Universal Custom Stacks:** Framework-idiomatic scaffolding for Next.js (App Router), Astro, Vue, or Svelte with clean dependency hygiene.

---

## 🚀 5. Verification & Live Preview

1. **Static Build Check:** Ensure zero syntax or module resolution errors.
2. **Background Dev Server:** Launch dev servers asynchronously (`creationflags=subprocess.CREATE_NO_WINDOW` on Windows).
3. **HTTP 200 Healthcheck:** Poll local port in background before notifying user.
4. **Mandatory Confirmation Gate:** Never auto-launch browser windows. Ask user:
   > *"Website build ho chuki hai aur `http://localhost:[port]` par active hai. Kya main preview window open karun?"*

---

## 🤖 Agent Directive

When executing a greenfield website build task, execute the master directive matching the target deliverable:

### Scenario 1: Personal & Engineer Portfolio (Single-File HTML)
````markdown
You are an expert Web Designer, UI/UX Designer, and Senior Frontend Engineer. Your task is to build a complete, clean, high-performance, responsive single-file engineer portfolio in standalone HTML5 with embedded CSS and vanilla JavaScript. Work within the target workspace directory and output the deliverable directly as 'index.html' with zero external build or npm dependencies.

Use this reference file (skills/website_build/references/3_portfolios/Hairline Grid Portfolio.html) for building UI Design. Inspect the reference file directly to extract its layout structure, styling, typography, spacing rhythm, card geometry, and visual DNA. Do not modify or overwrite the reference file.

USER REQUIREMENTS & SECTIONS:
- Hero & Status Beacon: Full name, title, live availability status beacon, concise technical bio, and quick-action links (Resume, GitHub, Email, Contact).
- Architecture & Systems Grid: Showcase flagship platforms, projects, and architecture notes with real metrics.
- Technical Skills & Stack: Grouped monospace skill tags (languages, frameworks, distributed systems, orchestration).
- Experience & Milestones Timeline: Chronological roles, achievements, high-throughput systems scaling, and milestones.
- Contact & Footer: Verified mailto link, GitHub profile link, LinkedIn, and clean 1px hairline terminal footer.
- Content Authenticity: Write authentic domain-accurate copy. Never use placeholder dummy names, fake corporate buzzwords, or lorem ipsum filler.

ANTI-SLOP QUALITY RULES:
- Layouts: Absolute positioning hacks are strictly banned. Use CSS Grid or Flexbox with standard breakpoints (375px, 768px, 1024px, 1280px+); zero horizontal scrollbars.
- Controls: Raw default browser controls are forbidden. Custom hover, active, and accessible focus states styled to match the reference.
- Restraint: Banned harsh black drop-shadows (use subtle 1px hairline borders); banned jumpy hover:scale-105 animations (use 150-200ms ease-out transitions and active:scale-[0.98]).
- Visuals: Banned generic AI purple/indigo gradients and plain 90s RGB primaries.
- Anchors: No dead href="#" links; all anchors smoothly scroll to their actual sections.
- Deliverable: Exactly ONE self-contained index.html with all CSS and vanilla JS embedded, ready for instant preview.
````

### Scenario 2: High-Converting SaaS Marketing Landing Page (Single-File HTML or React + Tailwind)
````markdown
You are an expert Web Designer, UI/UX Designer, and Senior Frontend Engineer. Your task is to build a modern, high-converting SaaS marketing landing page for the user's product or application. Work within the target workspace directory and output production-quality, responsive code.

Use this reference file (skills/website_build/references/1_landing_pages/saas.html) for building UI Design. Inspect the reference file directly to extract its layout structure, styling, typography, spacing rhythm, card geometry, and visual DNA. Do not modify or overwrite the reference file.

USER REQUIREMENTS & SECTIONS:
- Announcement Bar & Header: Sticky blur navbar with brand logo, product navigation, docs link, and high-contrast pill CTA.
- Hero Section: High-converting headline, crisp value proposition subhead, primary CTA, secondary interactive demo button, and a product UI frame mockup.
- Social Proof / Logo Ticker: Trusted enterprise badges with clean grayscale SVG logos.
- Feature Grid & Bento Cards: Interactive bento layout showcasing core capabilities with icons and concise value copy.
- Metrics & Counter: Verified operational metrics with clean stat counter cards.
- Pricing Matrix: Monthly / Annual toggle (with discount badge) and tier cards with feature checkmarks and distinct recommended plan highlight.
- Testimonials Carousel / Grid: Authentic customer testimonials with avatars, names, titles, and verified company tags.
- FAQ Accordion: Interactive expand/collapse FAQ questions addressing key features, integration, and pricing.
- Final Conversion CTA & Footer: High-impact CTA banner and clean multi-column footer with legal and status links.
- Content Authenticity: Write authentic, product-specific copy. Never use cringe claims like "1000000x faster than reality" or generic lorem ipsum text.

ANTI-SLOP QUALITY RULES:
- Layouts: Absolute positioning hacks are strictly banned. Use CSS Grid or Flexbox with standard breakpoints (375px, 768px, 1024px, 1280px+); zero horizontal scrollbars.
- Controls: Raw default browser controls are forbidden. Custom hover, active, and accessible focus states styled to match the reference.
- Restraint: Banned harsh black drop-shadows (use subtle 1px hairline borders); banned jumpy hover:scale-105 animations (use 150-200ms ease-out transitions and active:scale-[0.98]).
- Visuals: Banned generic AI purple/indigo gradients and plain 90s RGB primaries.
- Anchors: No dead href="#" links; all anchors smoothly scroll to their actual sections with working JS mobile menu and accordion toggles.
- Deliverable: Deliver complete, fully functional, production-ready implementation with zero placeholder TODOs.
````

### Scenario 3: Operational Analytics Dashboard (Next.js / Modular Framework)
````markdown
You are an expert Web Designer, UI/UX Designer, and Senior Frontend Systems Architect. Your task is to build a responsive operational analytics dashboard console. Work within the target workspace directory and preserve clean component architecture.

Use this reference file (skills/website_build/references/4_dashboards/orbit admin.html) for building UI Design. Inspect the reference file directly to extract its layout structure, styling, typography, spacing rhythm, card geometry, and visual DNA. Do not modify or overwrite the reference file.

USER REQUIREMENTS & SECTIONS:
- Cluster Health & Infrastructure: Health status beacons and cluster overview stats.
- Telemetry & Analytics Grid: Latency, throughput, and error rates presented in clear, readable charts and metric stat cards.
- Activity & Audit Logs: Readable event log panel with timestamps, severity badges, and structured details.
- Task / Resource Table: Functional table with clear status indicators, column headers, and working filter controls.
- Content Authenticity: Use domain-accurate data. Clearly identify sample preview data vs live metrics.

ANTI-SLOP QUALITY RULES:
- Layouts: Use CSS Grid or Flexbox with standard breakpoints; prevent accidental horizontal overflow.
- Controls: Fully styled inputs, dropdowns, table rows, and status indicators matching the reference design language.
- Restraint: Subtle 1px hairline borders and crisp data density; no muddy black drop-shadows.
- Micro-Interactions: Smooth hover transitions, table row highlights, and active button compression.
- Visuals: Calibrated dark console theme; no garish neon purple gradients.
- Deliverable: Deliver a working, responsive dashboard with functional interactions and clearly presented data.
````
