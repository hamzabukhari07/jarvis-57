---
version: "3.0"
name: "Dub"
theme: "light"
source: "C:/Users/Hamza Bukhari/Documents/antigravity/zezo latest/skills/hamza_taste/references/html/dub.html"
extracted_at: "2026-10-01T12:03:37.264246+00:00"
description: "Refined editorial light design system extracted deterministically from Dub. Features clean #ffffff cream canvas, high-contrast #171717 ink typography, and elegant Menlo headings."
colors:
  primary: "#000000"
  secondary: "#6c6c6c"
  tertiary: "#000000"
  neutral: "#e5e5e5"
  background: "#ffffff"
  surface: "#fafafa"
  text-primary: "#171717"
  text-secondary: "#6c6c6c"
  border: "#e5e5e5"
  accent: "#000000"
typography:
  display-lg:
    fontFamily: "Menlo"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "Menlo"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: "Menlo"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "24px"
  code-sm:
    fontFamily: "SFMono-Regular"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: "16px"
  label-md:
    fontFamily: "Menlo"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  sm: "6px"
  md: "5px"
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
    background: "#000000"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(0, 0, 0, 0.03)"
    border: "1px solid #e5e5e5"
    textColor: "#171717"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(0, 0, 0, 0.06)"
  card:
    background: "#fafafa"
    border: "1px solid #e5e5e5"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 2px 12px -1px rgba(0, 0, 0, 0.08)"
    backdropBlur: "12px"
  input:
    background: "#ffffff"
    border: "1px solid #e5e5e5"
    textColor: "#171717"
    placeholder: "#6c6c6c"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#000000"
---

# Dub — Design Specification

> **Aesthetic Profile:** Light Editorial / Cream Precision  
> **Extracted Source:** C:/Users/Hamza Bukhari/Documents/antigravity/zezo latest/skills/hamza_taste/references/html/dub.html  
> **Theme:** LIGHT  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#ffffff`) with layered panels (`#fafafa`) and hairline borders (`#e5e5e5`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#ffffff` | Master canvas background (`light` mode). |
| **Surface / Card** | `#fafafa` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#000000` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#171717` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#6c6c6c` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#e5e5e5` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Menlo`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Menlo`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `SFMono-Regular`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#ffffff`) with focused `#000000` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#e5e5e5` outlines, and `#000000` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `5px`.
