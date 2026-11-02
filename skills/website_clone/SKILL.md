---
name: website_clone
description: "Master protocol for exact offline website cloning, asset localization, and reverse-engineering rebuilds using the Uncage Hybrid Engine."
domain: web_dev
author: "Hamza Bukhari"
version: "1.2.0"
pre_flight_action: "uncage_capture"
agent_directive_section: "Agent Directive"
required_tools: [clone_website, browser_control, web_read_page, file_controller]
triggers: ["clone website", "copy website", "offline website", "download site", "uncage website", "rebuild website", "website clone", "rip website", "clone", "cloning", "cloner", "download website"]
tags: ["clone", "web_dev", "offline", "uncage", "rebuild"]
auto_activate: true
---

# 🌐 Master Website Cloning Protocol (`website_clone`)

> **Lead Architect & Creator:** Hamza Bukhari  
> **Core Subsystem:** Uncage Ingestion & Autonomous Reverse-Engineering Rebuild Pipeline  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, Autonomous Office Agents, and ZEZO Core Orchestrators.  
> **Core Axiom:** Two-Phase Execution (Ingestion ➔ Rebuild). Uncage captures authentic offline assets into the project folder. Downstream autonomous coding engines inspect real files on disk and rebuild a pixel-perfect, clean implementation.

---

## ⚡ 1. Two-Phase Execution Workflow

The protocol executes in two strictly separated phases:

### Phase 1: Ingestion & Asset Capture (Uncage CLI)
1. **Target Directory Allocation:** ZEZO creates an isolated project workspace (e.g. `Desktop/<domain>_clone`).
2. **Headless Asset Capture:** The pre-flight handler runs the self-contained Uncage CLI:
   ```bash
   node tools/uncage/bin/uncage.js <url> -o <target_dir> --no-purge --timeout 30000
   ```
3. **Capture Deliverables on Disk:**
   - `index.html`: Fully rendered, hydrated DOM snapshot with localized relative asset paths (`./assets/...`).
   - `assets/`: Downloaded stylesheets, web fonts, vector/raster images, and media.
   - `asset-map.json`: Checksum inventory of all localized assets.
4. **Verification Gate:** Execution only proceeds to Phase 2 once `index.html` and assets physically resolve on disk.

### Phase 2: Master Reverse-Engineering Rebuild (Coding Engine)
1. **Workspace Inspection:** The autonomous coding engine (AntiGravity `agy`, OpenCode, Kilo Code) is launched inside the exact project directory.
2. **Real-File Inspection:** The engine inspects `index.html`, stylesheets in `assets/css/`, fonts, and images on disk to extract authentic layout rules, typography, and responsive behaviors.
3. **Deliverable Production:** The engine executes the designated Master Directive below to generate the clean final rebuild.

---

## 🛡️ 2. Safety Invariants & Operational Rules

- **Disk Grounding:** Never guess or hallucinate assets. The coding engine must inspect real files captured on disk.
- **Asset Preservation:** Reuse authentic downloaded assets (`./assets/...`) rather than generating placeholder approximations.
- **Non-Blocking Execution:** Crawling and asset downloading must run asynchronously in background tasks. Never block the main voice loop.
- **Clean Deliverables:** In Single-File HTML mode, deliver a 100% self-contained standalone HTML file. In Framework mode, write modular code strictly into `rebuilt_app/`.

---

## 🤖 Agent Directive

When reverse-engineering and rebuilding an offline captured website, execute the corresponding master directive based on the user's requested deliverable format:

### Scenario A: Rebuild Raw Clone to Single-File Standalone HTML
Use this directive when the target deliverable is a self-contained, zero-dependency single-file HTML preview:

````markdown
You are an expert Web Designer, UI Designer, Frontend Engineer, and Website Reverse Engineering AI Agent. Your only task is to inspect the entire project provided to you through the project files and then rebuild the website as accurately as possible based on the actual files, code, assets, screenshots, components, styles, routes, content, and existing implementation. Do not rely on assumptions when the required information already exists inside the project. First inspect the complete project structure and identify all relevant files including HTML, JSX, TSX, JavaScript, CSS, SCSS, Tailwind files, JSON, images, SVGs, videos, fonts, icons, components, layouts, routes, configuration files, and any other assets or references that affect the website's visual appearance. Understand how the original website is structured from top to bottom and reverse engineer every visible section, including announcement bars, header, navigation, hero, sub-navigation, feature sections, content blocks, image sections, cards, testimonials, logos, statistics, pricing, FAQs, forms, CTAs, footer, and any additional sections or reusable patterns found in the project. Inspect the existing code and assets carefully to determine exact typography, colors, spacing, dimensions, layout behavior, responsive rules, animations, interactions, image usage, iconography, borders, shadows, gradients, backgrounds, and component relationships. Recreate the website as a single standalone HTML file that contains the complete visual experience, with embedded CSS and JavaScript, and make it fully responsive across desktop, tablet, and mobile. Reuse the project's actual assets whenever possible instead of creating replacements, preserve original image proportions and visual hierarchy, use the actual fonts when available, and reproduce important interactions such as dropdowns, mobile navigation, accordions, tabs, sliders, hover effects, scroll animations, menus, and other visible behaviors when they can reasonably be recreated with vanilla JavaScript. Do not create a design system, do not write an analysis report, do not explain what you found, and do not simplify the website into a basic approximation. The objective is to reverse engineer the provided project and produce a highly accurate visual recreation of the website. After inspecting the files, directly build the final HTML implementation using the information available in the project. Keep the implementation clean, structured, responsive, and production-quality. The final deliverable must be the New 100% Raw HTML file you can named it as what you want created from the project analysis, not a description of the implementation.
````

### Scenario B: Rebuild Raw Clone to Clean Modular Framework (React + Tailwind / Next.js / Custom Stack)
Use this exact directive when transforming the raw capture into a clean, modern, modular {target_stack} application:

````markdown
You are an expert Web Designer, UI Designer, Frontend Systems Architect, and Website Reverse Engineering AI Agent. Your only task is to inspect the entire project provided to you through the project files and then rebuild the website into a clean, modern, modular {target_stack} application (e.g. React 18 + TypeScript + Tailwind CSS / Next.js) inside the 'rebuilt_app/' directory as accurately as possible based on the actual files, code, assets, screenshots, components, styles, routes, content, and existing implementation. Do not rely on assumptions when the required information already exists inside the project. 

First inspect the complete project structure and identify all relevant files including HTML, JSX, TSX, JavaScript, CSS, SCSS, Tailwind files, JSON, images, SVGs, videos, fonts, icons, components, layouts, routes, configuration files, and any other assets or references that affect the website's visual appearance. Understand how the original website is structured from top to bottom and reverse engineer every visible section into clean, reusable components (e.g. AnnouncementBar, Header, Navbar, Hero, FeatureGrid, BentoCards, Testimonials, PricingMatrix, FAQAccordion, Forms, CTAs, Footer) under 'src/components/'.

Inspect the existing code and assets carefully to determine exact typography, colors, spacing, dimensions, layout behavior, responsive rules, animations, interactions, image usage, iconography, borders, shadows, gradients, backgrounds, and component relationships. Translate the styling cleanly into Tailwind utility classes and CSS variables, preserving the exact visual DNA of the original.

Reuse the project's actual assets whenever possible by moving them to the public/assets directory instead of creating replacements, preserve original image proportions and visual hierarchy, configure the actual fonts when available, and reproduce important interactions such as dropdowns, mobile navigation, accordions, tabs, sliders, hover effects, scroll animations, menus, and other visible behaviors using idiomatic React hooks and interactive state. Ensure zero TypeScript errors and complete type safety.

Do not write an analysis report, do not explain what you found, and do not simplify the website into a basic starter template. The objective is to reverse engineer the provided project and produce a highly accurate, modular, production-ready implementation of the website. Never mutate or overwrite files in the raw capture directory; write exclusively to 'rebuilt_app/'. Keep the code clean, structured, responsive, and production-quality. The final deliverable must be the fully functioning, executable application in 'rebuilt_app/', not a description of the implementation.
````
