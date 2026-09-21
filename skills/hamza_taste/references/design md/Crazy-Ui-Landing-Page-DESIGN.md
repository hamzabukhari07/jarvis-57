---
version: "3.0"
name: "Crazy Ui Landing Page"
theme: "light"
source: "D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/Crazy UI landing page.html"
extracted_at: "2026-09-21T18:19:54.661830+00:00"
description: "Refined editorial light design system extracted deterministically from Crazy Ui Landing Page. Features clean #f6f4f2 cream canvas, high-contrast #0a0a0a ink typography, and elegant Instrument Serif headings."
colors:
  primary: "#000000"
  secondary: "#6c6c6c"
  tertiary: "#000000"
  neutral: "#e9e9e9"
  background: "#f6f4f2"
  surface: "#ede9e4"
  text-primary: "#0a0a0a"
  text-secondary: "#6c6c6c"
  border: "#e9e9e9"
  accent: "#000000"
typography:
  display-lg:
    fontFamily: "Instrument Serif"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "Instrument Serif"
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
  md: "5px"
  lg: "12px"
  xl: "14px"
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
    background: "#000000"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(0, 0, 0, 0.03)"
    border: "1px solid #e9e9e9"
    textColor: "#0a0a0a"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(0, 0, 0, 0.06)"
  card:
    background: "#ede9e4"
    border: "1px solid #e9e9e9"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 2px 12px -1px rgba(0, 0, 0, 0.08)"
    backdropBlur: "12px"
  input:
    background: "#ffffff"
    border: "1px solid #e9e9e9"
    textColor: "#0a0a0a"
    placeholder: "#6c6c6c"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#000000"
---

# Crazy Ui Landing Page — Design Specification

> **Aesthetic Profile:** Light Editorial / Cream Precision  
> **Extracted Source:** D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/Crazy UI landing page.html  
> **Theme:** LIGHT  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#f6f4f2`) with layered panels (`#ede9e4`) and hairline borders (`#e9e9e9`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#f6f4f2` | Master canvas background (`light` mode). |
| **Surface / Card** | `#ede9e4` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#000000` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#0a0a0a` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#6c6c6c` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#e9e9e9` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Instrument Serif`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Inter`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#f6f4f2`) with focused `#000000` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#e9e9e9` outlines, and `#000000` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `14px` and button/input radii to `5px`.
