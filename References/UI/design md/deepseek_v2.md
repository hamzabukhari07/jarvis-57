---
version: "3.0"
name: "Deepseek Html 20260920 9Ad50E"
theme: "dark"
source: "C:/Users/Hamza/Downloads/deepseek_html_20260920_9ad50e.html"
extracted_at: "2026-09-20T22:38:53.856037+00:00"
description: "High-precision studio design system extracted deterministically from Deepseek Html 20260920 9Ad50E. Features deep #050505 void canvas, high-contrast #f5f5f7 typography, vibrant #f24e1e accents, and glassy elevation."
colors:
  primary: "#f24e1e"
  secondary: "#a0a0ab"
  tertiary: "#f24e1e"
  neutral: "#ffffff"
  background: "#050505"
  surface: "#ffffff"
  text-primary: "#f5f5f7"
  text-secondary: "#a0a0ab"
  border: "#ffffff"
  accent: "#f24e1e"
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
    background: "#f24e1e"
    textColor: "#ffffff"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "brightness(1.1) shadow-lg"
  button-glass:
    background: "rgba(255, 255, 255, 0.04)"
    border: "1px solid #ffffff"
    textColor: "#f5f5f7"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    hover: "background: rgba(255, 255, 255, 0.08)"
  card:
    background: "#ffffff"
    border: "1px solid #ffffff"
    rounded: "{rounded.xl}"
    padding: "{spacing.card-padding}"
    shadow: "0 4px 20px -2px rgba(0, 0, 0, 0.5)"
    backdropBlur: "12px"
  input:
    background: "rgba(0, 0, 0, 0.4)"
    border: "1px solid #ffffff"
    textColor: "#f5f5f7"
    placeholder: "#a0a0ab"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    focusBorder: "#f24e1e"
---

# Deepseek Html 20260920 9Ad50E — Design Specification

> **Aesthetic Profile:** Dark Studio / High-Precision Void  
> **Extracted Source:** C:/Users/Hamza/Downloads/deepseek_html_20260920_9ad50e.html  
> **Theme:** DARK  

---

## 1. Composition & Structural Framing

- **Base Layout:** Fluid CSS Grid / Flexbox with max-width container (`1280px` or `1440px`).
- **Framing:** Base canvas (`#050505`) with layered panels (`#ffffff`) and hairline borders (`#ffffff`).
- **Visual Cadence:** Strict 4px/8px modular rhythm across all paddings, margins, and gaps.

## 2. Color Palette & Hierarchy

| Semantic Role | Token Value | Description & Visual Usage |
| :--- | :--- | :--- |
| **Background / Canvas** | `#050505` | Master canvas background (`dark` mode). |
| **Surface / Card** | `#ffffff` | Primary container panels, modules, and cards. |
| **Primary Accent** | `#f24e1e` | High-intent CTAs, active status indicators, key focus rings. |
| **Text Primary** | `#f5f5f7` | Headers, titles, high-contrast editorial text. |
| **Text Muted** | `#a0a0ab` | Subtitles, meta-tags, helper notes, body copy. |
| **Hairline Border** | `#ffffff` | 1px clean separation borders across containers. |

## 3. Typography Hierarchy

- **Display & Headings:** `Inter`, negative letter-spacing (`-0.02em` to `-0.03em`), semi-bold/serif.
- **Body & UI Text:** `Inter`, `14px` / `15px`, clean high-legibility leading (`1.5`).
- **Telemetry, Code & Chips:** `JetBrains Mono`, `11px` / `12px`, uppercase letter spacing (`0.05em`).

## 4. Anti-Slop Guidelines (Strict Rules for Coding Agents)

1. **NO Generic AI Purple Gradients:** Never generate cliché indigo/purple blobs. Use authentic theme styling (`#050505`) with focused `#f24e1e` accents.
2. **NO Unstyled Browser Inputs:** Form inputs must feature custom backgrounds, `#ffffff` outlines, and `#f24e1e` focus rings.
3. **NO Oversized Empty Spaces:** Keep information density crisp, purposeful, and functional with 8px/16px/24px step spacing.
4. **NO Inconsistent Radii:** Standardize container radii to `16px` and button/input radii to `8px`.
