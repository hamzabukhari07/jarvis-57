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
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Fleet, and all UI coding agents.  
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

### Scenario 2: High-Converting SaaS Marketing Landing Page (React 18 + TypeScript + Tailwind CSS)
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

### Scenario 3: Operational Analytics Dashboard (Next.js App Router, TypeScript, Tailwind, Lucide)
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
Use available real data if the project provides it. Otherwise, use clearly identified sample data for preview.
Do not present simulated values as live production telemetry.
Ensure charts, tables, and status indicators accurately reflect the data being displayed.

[EXECUTION & SUBAGENT STRATEGY]
Inspect the existing project, routes, components, and dependencies before implementation.
Use subagents only when useful for independent work (layout, charts, tables).
Use reusable components where appropriate without overengineering.
Use client components only where interactive behavior requires them.
Preserve existing functionality and avoid unrelated refactoring.

[VALIDATION & QUALITY REQUIREMENTS]
Verify that the dashboard starts and renders correctly.
Test task filters, navigation, and other implemented interactions.
Confirm charts render correctly and display the intended data.
Check responsive behavior and prevent accidental horizontal overflow.
Ensure readable tables, clear status indicators, and consistent visual hierarchy.
Resolve relevant TypeScript errors, runtime errors, and broken interactions.
Deliverable: A working, responsive Next.js dashboard with functional interactions and clearly presented operational data.
````
