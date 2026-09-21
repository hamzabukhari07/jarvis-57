---
version: "3.0"
name: "Nexus"
theme: "light"
source: "D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/nexus.html"
extracted_at: "2026-09-21T18:19:54.668871+00:00"
description: "Refined editorial light design system extracted deterministically from Nexus. Features clean #f8f9fa cream canvas, high-contrast #0f172a ink typography, and elegant Inter headings."
colors:
  primary: "#fd6703"
  secondary: "#6c6c6c"
  tertiary: "#fd6703"
  neutral: "#e5e5e5"
  background: "#f8f9fa"
  surface: "#ede9e4"
  text-primary: "#0f172a"
  text-secondary: "#6c6c6c"
  border: "#e5e5e5"
  accent: "#fd6703"
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
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "24px"
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
    background: "#fd6703"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(0, 0, 0, 0.03)"
    border: "1px solid #e5e5e5"
    textColor: "#0f172a"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(0, 0, 0, 0.06)"
  card:
    background: "#ede9e4"
    border: "1px solid #e5e5e5"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 2px 12px -1px rgba(0, 0, 0, 0.08)"
    backdropBlur: "12px"
  input:
    background: "#ffffff"
    border: "1px solid #e5e5e5"
    textColor: "#0f172a"
    placeholder: "#6c6c6c"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#fd6703"
---

# Nexus — Design Specification

> **Aesthetic Profile:** Light Editorial / Cream Precision  
> **Extracted Source:** D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/nexus.html  
> **Theme:** LIGHT  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#f8f9fa`) with layered panels (`#ede9e4`) and hairline borders (`#e5e5e5`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#f8f9fa` | Master canvas background (`light` mode). |
| **Surface / Card** | `#ede9e4` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#fd6703` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#0f172a` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#6c6c6c` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#e5e5e5` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Inter`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Inter`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#f8f9fa`) with focused `#fd6703` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#e5e5e5` outlines, and `#fd6703` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `8px`.
