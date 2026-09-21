---
version: "alpha"
name: "Skeuomorphic Spatial Component"
description: "Skeuomorphic Spatial Dashboard Section is designed for demonstrating application workflows and interface hierarchy. Key features include clear information density, modular panels, and interface rhythm. It is suitable for product showcases, admin panels, and analytics experiences."
colors:
  primary: "#FF7A6E"
  secondary: "#E7E7E7"
  tertiary: "#FFE278"
  neutral: "#E7E7E7"
  background: "#0C0C0C"
  surface: "#333333"
  text-primary: "#E7E7E7"
  text-secondary: "#757575"
  border: "#757575"
  accent: "#FF7A6E"
typography:
  display-lg:
    fontFamily: "System Font"
    fontSize: "72px"
    fontWeight: 400
    lineHeight: "72px"
    letterSpacing: "-0.025em"
  body-md:
    fontFamily: "System Font"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "22.75px"
  label-md:
    fontFamily: "System Font"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
rounded:
  full: "9999px"
spacing:
  base: "4px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  gap: "4px"
  card-padding: "10px"
  section-padding: "24px"
components:
  button-primary:
    textColor: "{colors.secondary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.full}"
    padding: "8px"
  card:
    rounded: "22px"
    padding: "26.5px"
---

## Overview

- **Composition cues:**
  - Layout: Grid
  - Content Width: Bounded
  - Framing: Glassy
  - Grid: Strong

## Colors

The color system uses light mode with #FF7A6E as the main accent and #E7E7E7 as the neutral foundation.

- **Primary (#FF7A6E):** Main accent and emphasis color.
- **Secondary (#E7E7E7):** Supporting accent for secondary emphasis.
- **Tertiary (#FFE278):** Reserved accent for supporting contrast moments.
- **Neutral (#E7E7E7):** Neutral foundation for backgrounds, surfaces, and supporting chrome.

- **Usage:** Background: #0C0C0C; Surface: #333333; Text Primary: #E7E7E7; Text Secondary: #757575; Border: #757575; Accent: #FF7A6E

## Typography

Typography relies on System Font across display, body, and utility text.

- **Display (`display-lg`):** System Font, 72px, weight 400, line-height 72px, letter-spacing -0.025em.
- **Body (`body-md`):** System Font, 14px, weight 400, line-height 22.75px.
- **Labels (`label-md`):** System Font, 12px, weight 600, line-height 16px.

## Layout

Layout follows a grid composition with reusable spacing tokens. Preserve the grid, bounded structural frame before changing ornament or component styling. Use 4px as the base rhythm and let larger gaps step up from that cadence instead of introducing unrelated spacing values.

Treat the page as a grid / bounded composition, and keep that framing stable when adding or remixing sections.

- **Layout type:** Grid
- **Content width:** Bounded
- **Base unit:** 4px
- **Scale:** 4px, 8px, 12px, 16px, 18px, 24px, 28px, 30px
- **Section padding:** 24px, 30px, 32px
- **Card padding:** 10px, 14px, 24px, 30px
- **Gaps:** 4px, 8px, 12px, 20px

## Elevation & Depth

Depth is communicated through glass, border contrast, and reusable shadow or blur treatments. Keep those recipes consistent across hero panels, cards, and controls so the page reads as one material system.

Surfaces should read as glass first, with borders, shadows, and blur only reinforcing that material choice.

- **Surface style:** Glass
- **Borders:** 0.8px #757575; 0.8px #333333; 1.6px #FFFFFF; 1.6px #FF7A6E
- **Shadows:** rgba(0, 0, 0, 0.4) 0px 4px 12px 0px, rgba(255, 255, 255, 0.08) 0px 1px 0px 0px inset; rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05) 0px 1px 2px 0px; rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.5) 0px 12px 24px 0px, rgba(255, 255, 255, 0.12) 0px 1px 0px 0px inset
- **Blur:** 12px, 24px, 4px

### Techniques
- **Gradient border shell:** Use a thin gradient border shell around the main card. Wrap the surface in an outer shell with 26.5px padding and a 22px radius. Drive the shell with linear-gradient(rgb(31, 31, 31), rgb(18, 18, 18)), linear-gradient(rgb(51, 51, 51), rgb(12, 12, 12)) so the edge reads like premium depth instead of a flat stroke. Keep the actual stroke understated so the gradient shell remains the hero edge treatment. Inset the real content surface inside the wrapper with a slightly smaller radius so the gradient only appears as a hairline frame.

## Shapes

Shapes rely on a tight radius system anchored by 6px and scaled across cards, buttons, and supporting surfaces. Icon geometry should stay compatible with that soft-to-controlled silhouette.

Use the radius family intentionally: larger surfaces can open up, but controls and badges should stay within the same rounded DNA instead of inventing sharper or pill-only exceptions.

- **Corner radii:** 6px, 22px, 28px, 30px, 34px, 9999px
- **Icon treatment:** Linear
- **Icon sets:** Solar

## Components

Anchor interactions to the detected button styles. Reuse the existing card surface recipe for content blocks.

### Buttons
- **Primary:** text #E7E7E7, radius 9999px, padding 8px, border 0.8px solid rgba(0, 0, 0, 0).

### Cards and Surfaces
- **Card surface:** border 0.8px solid rgba(0, 0, 0, 0), radius 22px, padding 26.5px, shadow rgba(0, 0, 0, 0.4) 0px 4px 12px 0px, rgba(255, 255, 255, 0.08) 0px 1px 0px 0px inset.
- **Card surface:** background #141414, border 0.8px solid rgb(51, 51, 51), radius 28px, padding 30px, shadow rgba(0, 0, 0, 0.5) 0px 18px 45px 0px, rgba(255, 255, 255, 0.08) 0px 1px 0px 0px inset.
- **Card surface:** background #141414, border 0.8px solid rgb(51, 51, 51), radius 28px, padding 30px, shadow rgba(0, 0, 0, 0.6) 0px 18px 45px 0px, rgba(255, 255, 255, 0.08) 0px 1px 0px 0px inset.

### Iconography
- **Treatment:** Linear.
- **Sets:** Solar.

## Do's and Don'ts

Use these constraints to keep future generations aligned with the current system instead of drifting into adjacent styles.

### Do
- Do use the primary palette as the main accent for emphasis and action states.
- Do keep spacing aligned to the detected 4px rhythm.
- Do reuse the Glass surface treatment consistently across cards and controls.
- Do keep corner radii within the detected 6px, 22px, 28px, 30px, 34px, 9999px family.

### Don't
- Don't introduce extra accent colors outside the core palette roles unless the page needs a new semantic state.
- Don't mix unrelated shadow or blur recipes that break the current depth system.
- Don't exceed the detected moderate motion intensity without a deliberate reason.

## Motion

Motion feels controlled and interface-led across text, layout, and section transitions. Timing clusters around 300ms and 650ms. Easing favors ease and 0.2. Hover behavior focuses on transform and color changes. Scroll choreography uses GSAP ScrollTrigger for section reveals and pacing.

**Motion Level:** moderate

**Durations:** 300ms, 650ms, 150ms, 700ms

**Easings:** ease, 0.2, 1), 0, cubic-bezier(0.4, cubic-bezier(0.2

**Hover Patterns:** transform, color

**Scroll Patterns:** gsap-scrolltrigger
