---
version: "3.0"
name: "Nami Landing Page"
theme: "dark"
source: "C:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57/skills/hamza_taste/references/html/nami landing page.html"
extracted_at: "2026-10-06T06:02:01.094952+00:00"
description: "High-precision studio design system extracted deterministically from Nami Landing Page. Features deep #0d0d0d void canvas, high-contrast #d8d5d0 typography, vibrant #ef6461 accents, and glassy elevation."
colors:
  primary: "#ef6461"
  secondary: "#8f8c85"
  tertiary: "#ef6461"
  neutral: "#333333"
  background: "#0d0d0d"
  surface: "#18181b"
  text-primary: "#d8d5d0"
  text-secondary: "#8f8c85"
  border: "#333333"
  accent: "#ef6461"
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
    fontFamily: "ui-monospace"
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
  md: "7px"
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
    background: "#ef6461"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(255, 255, 255, 0.04)"
    border: "1px solid #333333"
    textColor: "#d8d5d0"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(255, 255, 255, 0.08)"
  card:
    background: "#18181b"
    border: "1px solid #333333"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 4px 20px -2px rgba(0, 0, 0, 0.5)"
    backdropBlur: "12px"
  input:
    background: "rgba(0, 0, 0, 0.4)"
    border: "1px solid #333333"
    textColor: "#d8d5d0"
    placeholder: "#8f8c85"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#ef6461"
---

# Nami Landing Page — Design Specification

> **Aesthetic Profile:** Dark Studio / High-Precision Void  
> **Extracted Source:** C:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57/skills/hamza_taste/references/html/nami landing page.html  
> **Theme:** DARK  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#0d0d0d`) with layered panels (`#18181b`) and hairline borders (`#333333`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#0d0d0d` | Master canvas background (`dark` mode). |
| **Surface / Card** | `#18181b` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#ef6461` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#d8d5d0` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#8f8c85` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#333333` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Menlo`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Menlo`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `ui-monospace`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#0d0d0d`) with focused `#ef6461` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#333333` outlines, and `#ef6461` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `7px`.
