# SKILL: hamza_taste (UI)
**Description:** Master Studio UI Anti-Slop Directive & Reference-First Design Protocol for autonomous web generation and frontend agents.

# 🎨 Hamza Taste — Studio UI Anti-Slop Directive & Reference Protocol

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, and all Autonomous Coding Agents  
> **Core Principle:** Anti-Slop is a **FILTER** (what to reject), while **Reference HTML Templates** supply 100% of the **DIRECTION** (colors, typography, components, and layout).

---

## 💎 CORE ARCHITECTURAL CONTRACT

1. **Direction Comes From References (`skills/hamza_taste/references/`):**
   - The reference library contains curated, production-grade HTML templates (SaaS, Dashboards, AI Agents, Spatial UI, Media).
   - Coding agents MUST adopt the **exact colors, typography, radii, glassmorphic elevation, and card geometry** extracted from the active reference template.
   - **NEVER Hallucinate Colors:** Never replace a Cyan/Navy reference with default greens, or a Minimal Monochrome reference with purple gradients.

2. **Quality Comes From Anti-Slop Filters:**
   - `hamza_taste` acts as an uncompromising quality filter ensuring zero AI slop, honest copy, styled controls, and responsive containers.

---

## 🛑 NON-NEGOTIABLE ANTI-SLOP RULES (TIERED FILTER)

### 🔴 Tier 1: Absolute Hard Gates (Strictly Forbidden)
1. ❌ **NO Cliché AI Purple/Indigo Gradients:** Strictly forbid generic `bg-gradient-to-r from-purple-600 to-indigo-600` blobs, neon purple hero text, or floating ambient blobs.
2. ❌ **NO Unstyled Native Controls:** Default browser scrollbars, form inputs, checkboxes, and select dropdowns are strictly forbidden. Every form input must have a custom styled dark surface, border highlight, and focus ring.
3. ❌ **NO Fake Buzzwords / Fake Telemetry Copy:** Never generate cringe copy like *"Next-Gen AI 2.0 Synergy Engine"*, *"0.00001ms Latency"*, or *"Loved by 10,000,000 Fortune 500 CEOs"*. Use honest, realistic product copy.
4. ❌ **NO Plain 90s RGB Primaries:** Pure `#ff0000`, `#00ff00`, `#0000ff` are banned. Use refined, harmonized tokens extracted from the reference design.
5. ❌ **NO Fragile or Breaking Layouts:** Absolute positioning hacks for structural layout are banned. All layouts MUST use CSS Grid or Flexbox with `max-w-7xl` (`1280px` or `1440px`) centered containers.

### 🟡 Tier 2: Rhythm, Geometry & Density Locks
1. 📐 **4px/8px Modular Rhythm:** Spacing, padding, and margins must follow strict 4px/8px increments (`p-4`, `p-6`, `p-8`, `gap-4`, `gap-6`).
2. 🔲 **No Giant Vacuous Spaces:** Avoid absurd 120px empty padding blocks with single words. Keep UI density crisp, purposeful, and functional.
3. 🔘 **Consistent Radius Hierarchy:** Button radius (`8px`), Card radius (`14px`–`16px`), Modal radius (`16px`–`20px`), Pill badges (`9999px`).
4. 🪟 **True Glassmorphism:** Glass surfaces must feature layered depth: `background: rgba(24, 24, 27, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08);`.

### 🟢 Tier 3: Delivery & Interaction Gate
1. ⚡ **Button Micro-Interactions:** Active scale (`active:scale-95`), transition duration `150ms ease-out`, hover brightness boost (`hover:brightness-110` or glow shadow).
2. 🏷️ **High-Contrast Typography Hierarchy:** Primary headers pure high-contrast (`#fafafa` / `#ffffff`), secondary body zinc (`#a1a1aa`), meta/chips mono (`#71717a`).

---

## 🎯 AUTONOMOUS REFERENCE SELECTION PROTOCOL

When an agent receives a UI / Web generation task:
1. **Domain or Name Specified:** Agent automatically matches the most accurate HTML template from `references/html/` (e.g. `saas.html` for SaaS, `autonomus.html` for AI agents, `Standalone Ecosystem.html` for dashboards, `image gen.html` for media, `froma os .html` for OS/Terminal).
2. **Generic Request (e.g. *"Build a website"*):** Agent autonomously selects the optimal flagship reference template from the library and announces the selection in voice feedback.
3. **0ms Instant Cache:** Tokens are extracted and cached into `references/design md/` for instant, zero-latency recall across all coding tasks.