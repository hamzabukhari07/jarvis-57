---
version: "3.0"
name: "Dub Landing Page"
theme: "light"
source: "D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/dub landing page.html"
extracted_at: "2026-09-21T18:19:54.686040+00:00"
description: "Refined editorial light design system extracted deterministically from Dub Landing Page. Features clean #f5f2ea cream canvas, high-contrast #1f1511 ink typography, and elegant Roboto headings."
colors:
  primary: "#ff6552"
  secondary: "#6b5f57"
  tertiary: "#ff6552"
  neutral: "#1f1511"
  background: "#f5f2ea"
  surface: "#ede7d9"
  text-primary: "#1f1511"
  text-secondary: "#6b5f57"
  border: "#1f1511"
  accent: "#ff6552"
typography:
  display-lg:
    fontFamily: "Roboto"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "Roboto"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: "Roboto"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "24px"
  code-sm:
    fontFamily: "JetBrains Mono"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: "16px"
  label-md:
    fontFamily: "Roboto"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  sm: "6px"
  md: "6px"
  lg: "12px"
  xl: "20px"
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
    background: "#ff6552"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(0, 0, 0, 0.03)"
    border: "1px solid #1f1511"
    textColor: "#1f1511"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(0, 0, 0, 0.06)"
  card:
    background: "#ede7d9"
    border: "1px solid #1f1511"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 2px 12px -1px rgba(0, 0, 0, 0.08)"
    backdropBlur: "12px"
  input:
    background: "#ffffff"
    border: "1px solid #1f1511"
    textColor: "#1f1511"
    placeholder: "#6b5f57"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#ff6552"
---

# Dub Landing Page — Design Specification

> **Aesthetic Profile:** Light Editorial / Cream Precision  
> **Extracted Source:** D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/dub landing page.html  
> **Theme:** LIGHT  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#f5f2ea`) with layered panels (`#ede7d9`) and hairline borders (`#1f1511`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#f5f2ea` | Master canvas background (`light` mode). |
| **Surface / Card** | `#ede7d9` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#ff6552` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#1f1511` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#6b5f57` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#1f1511` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Roboto`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Roboto`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#f5f2ea`) with focused `#ff6552` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#1f1511` outlines, and `#ff6552` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `20px` and button/input radii to `6px`.
