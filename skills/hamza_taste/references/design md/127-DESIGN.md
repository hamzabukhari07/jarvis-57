---
version: "3.0"
name: "127 Web Design"
theme: "light"
source: "inline"
extracted_at: "2026-10-22T10:09:39.795807+00:00"
description: "Refined editorial light design system extracted deterministically from 127 Web Design. Features clean #f4f6f9 cream canvas, high-contrast #0b1220 ink typography, and elegant inherit headings."
colors:
  primary: "#33c3f0"
  secondary: "#6c6c6c"
  tertiary: "#33c3f0"
  neutral: "#cccccc"
  background: "#f4f6f9"
  surface: "#ede9e4"
  text-primary: "#0b1220"
  text-secondary: "#6c6c6c"
  border: "#cccccc"
  accent: "#33c3f0"
typography:
  display-lg:
    fontFamily: "inherit"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: "1.1"
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "inherit"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "1.2"
    letterSpacing: "-0.02em"
  body-md:
    fontFamily: "inherit"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "24px"
  code-sm:
    fontFamily: "JetBrains Mono"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: "16px"
  label-md:
    fontFamily: "inherit"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  sm: "6px"
  md: "8px"
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
    background: "#33c3f0"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(0, 0, 0, 0.03)"
    border: "1px solid #cccccc"
    textColor: "#0b1220"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(0, 0, 0, 0.06)"
  card:
    background: "#ede9e4"
    border: "1px solid #cccccc"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 2px 12px -1px rgba(0, 0, 0, 0.08)"
    backdropBlur: "12px"
  input:
    background: "#ffffff"
    border: "1px solid #cccccc"
    textColor: "#0b1220"
    placeholder: "#6c6c6c"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#33c3f0"
---

# 127 Web Design — Design Specification

> **Aesthetic Profile:** Light Editorial / Cream Precision  
> **Extracted Source:** inline  
> **Theme:** LIGHT  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#f4f6f9`) with layered panels (`#ede9e4`) and hairline borders (`#cccccc`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#f4f6f9` | Master canvas background (`light` mode). |
| **Surface / Card** | `#ede9e4` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#33c3f0` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#0b1220` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#6c6c6c` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#cccccc` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `inherit`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `inherit`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#f4f6f9`) with focused `#33c3f0` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#cccccc` outlines, and `#33c3f0` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `14px` and button/input radii to `8px`.
