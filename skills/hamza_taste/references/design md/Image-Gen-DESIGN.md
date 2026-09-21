---
version: "3.0"
name: "Image Gen"
theme: "dark"
source: "D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/image gen.html"
extracted_at: "2026-09-20T22:59:22.473824+00:00"
description: "High-precision studio design system extracted deterministically from Image Gen. Features deep #09090b void canvas, high-contrast #ececec typography, vibrant #ececec accents, and glassy elevation."
colors:
  primary: "#ececec"
  secondary: "#a1a1aa"
  tertiary: "#ececec"
  neutral: "#27272a"
  background: "#09090b"
  surface: "#18181b"
  text-primary: "#ececec"
  text-secondary: "#a1a1aa"
  border: "#27272a"
  accent: "#ececec"
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
  md: "10px"
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
    background: "#ececec"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(255, 255, 255, 0.04)"
    border: "1px solid #27272a"
    textColor: "#ececec"
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
    textColor: "#ececec"
    placeholder: "#a1a1aa"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#ececec"
---

# Image Gen — Design Specification

> **Aesthetic Profile:** Dark Studio / High-Precision Void  
> **Extracted Source:** D:/anitgravity/zezo work/zezo latest/skills/hamza_taste/references/html/image gen.html  
> **Theme:** DARK  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#09090b`) with layered panels (`#18181b`) and hairline borders (`#27272a`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#09090b` | Master canvas background (`dark` mode). |
| **Surface / Card** | `#18181b` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#ececec` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#ececec` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#a1a1aa` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#27272a` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Inter`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Inter`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#09090b`) with focused `#ececec` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#27272a` outlines, and `#ececec` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `10px`.
