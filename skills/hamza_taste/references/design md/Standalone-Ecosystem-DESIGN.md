---
version: "2.0"
name: "Standalone Ecosystem"
description: "High-precision studio design system extracted deterministically from Standalone Ecosystem. Features deep obsidian void backgrounds, high-contrast typography, emerald/cyber accents, and skeuomorphic glassy elevation."
colors:
  primary: "#e48b59"
  secondary: "#d4e4ec"
  tertiary: "#38bdf8"
  neutral: "#71717a"
  background: "#09090b"
  surface: "#18181b"
  text-primary: "#d8dadf"
  text-secondary: "#d4e4ec"
  border: "#27272a"
  accent: "#e48b59"
typography:
  display-lg:
    fontFamily: "Inter"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "Inter"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: "Inter"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "22px"
  code-sm:
    fontFamily: "JetBrains Mono"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: "16px"
  label-md:
    fontFamily: "Inter"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  base: "4px"
  sm: "4px"
  md: "8px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
  card-padding: "20px"
  section-padding: "48px"
components:
  button-primary:
    background: "#e48b59"
    textColor: "#000000"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(255, 255, 255, 0.04)"
    border: "1px solid #27272a"
    textColor: "#d8dadf"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(255, 255, 255, 0.08)"
  card:
    background: "#18181b"
    border: "1px solid #27272a"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 4px 20px -2px rgba(0, 0, 0, 0.5)"
    backdropBlur: "12px"
  input:
    background: "rgba(0, 0, 0, 0.4)"
    border: "1px solid #27272a"
    textColor: "#d8dadf"
    placeholder: "#d4e4ec"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#e48b59"
---

# Standalone Ecosystem — Design Specification

> **Aesthetic Profile:** Dark Studio / Obsidian Precision  
> **Source Model:** Deterministically Extracted Token Set  
> **Target Audience:** Autonomous Agents & Studio Web Applications  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Deep void foundation (`#09090b`) with layered glassy panels and hairline borders (`#27272a`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Void** | `#09090b` | Master canvas background and dark viewport underlays. |
| **Surface / Card** | `#18181b` | Primary container panels, sidebar modules, node cards. |
| **Surface Elevated** | `#27272a` | Active highlights, hover layers, badge fills. |
| **Primary Accent** | `#e48b59` | High-intent CTAs, active status dots, focus rings, key metrics. |
| **Text Primary** | `#d8dadf` | Headers, active titles, high-contrast numerical readouts. |
| **Text Muted** | `#d4e4ec` | Subtitles, meta-tags, helper notes, inactive state labels. |
| **Hairline Border** | `#27272a` | 1px clean separation borders across all card containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Inter`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold.
- **Body & UI Text:** `Inter`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Elevation, Glassmorphism & Micro-Interactions

- **Glass Surface Recipe:** `background: #18181b88; backdrop-filter: blur(12px); border: 1px solid #27272a;`
- **Card Depth:** Subtle downward ambient drop shadow `0 8px 32px 0 rgba(0, 0, 0, 0.37)` combined with inner top-hairline highlight.
- **Button Micro-Interactions:**
  - Transition duration: `150ms ease-out`
  - Scale on active press: `transform: scale(0.98)`
  - Glow on hover: `box-shadow: 0 0 16px #e48b5933`

## 5. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic studio dark mode (`#09090b`) with focused `#e48b59` highlights.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom dark backgrounds (`rgba(0,0,0,0.5)`), `#27272a` outlines, and `#e48b59` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, modern, and purposeful with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `8px`.

