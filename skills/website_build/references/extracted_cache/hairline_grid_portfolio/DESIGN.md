<design-context>
---
version: alpha
name: hairline-grid-portfolio-design-analysis
description: An architectural interpretation of Hairline Grid Portfolio — a design system rooted in Creative Scrapbook & Visual Narrative. Master canvas sits on #0e0e10 (dark mode), high-contrast ink text in #f5f5f7, supported by dynamic #67a6fb and #a78bfa accents, calibrated #303034 borders, and ui-sans-serif typography.

colors:
  primary: "#67a6fb"
  on-primary: "#000000"
  ink: "#f5f5f7"
  body: "#a0a1a9"
  mute: "#808087"
  hairline: "#303034"
  hairline-strong: "#59595c"
  canvas: "#0e0e10"
  canvas-soft: "#151518"
  canvas-soft-2: "#202023"
  link: "#67a6fb"
  link-deep: "#7db3fb"
  link-bg-soft: "#294264"
  success: "#10b981"
  error: "#ee0000"
  error-soft: "#450a0a"
  error-deep: "#c50000"
  warning: "#f5a623"
  warning-soft: "#451a03"
  warning-deep: "#ab570a"
  violet: "#a78bfa"
  violet-soft: "#53457d"
  violet-deep: "#bda8fb"
  cyan: "#50e3c2"
  cyan-soft: "#042f2e"
  cyan-deep: "#29bc9b"
  highlight-pink: "#ff0080"
  highlight-magenta: "#eb367f"
  gradient-develop-start: "#67a6fb"
  gradient-develop-end: "#a78bfa"
  gradient-preview-start: "#7928ca"
  gradient-preview-end: "#ff0080"
  gradient-ship-start: "#ff4d4d"
  gradient-ship-end: "#f9cb28"
  selection-bg: "#67a6fb"
  selection-fg: "#000000"

typography:
  display-xl:
    fontFamily: ui-sans-serif, Inter, system-ui, -apple-system, sans-serif
    fontSize: 48px
    fontWeight: 600
    lineHeight: 48px
    letterSpacing: -2.4px
  display-lg:
    fontFamily: ui-sans-serif, Inter, system-ui, -apple-system, sans-serif
    fontSize: 32px
    fontWeight: 600
    lineHeight: 40px
    letterSpacing: -1.28px
  display-md:
    fontFamily: ui-sans-serif, Inter, system-ui, -apple-system, sans-serif
    fontSize: 24px
    fontWeight: 600
    lineHeight: 32px
    letterSpacing: -0.96px
  display-sm:
    fontFamily: ui-sans-serif, Inter, system-ui, -apple-system, sans-serif
    fontSize: 20px
    fontWeight: 600
    lineHeight: 28px
    letterSpacing: -0.6px
  body-lg:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0px
  body-md:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
  body-md-strong:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px
  body-sm:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: -0.28px
  body-sm-strong:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
    letterSpacing: -0.28px
  caption:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  caption-mono:
    fontFamily: Geist Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
  code:
    fontFamily: Geist Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
  button-md:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 14px
    fontWeight: 500
    lineHeight: 20px
  button-lg:
    fontFamily: Geist, Inter, system-ui, -apple-system, sans-serif
    fontSize: 16px
    fontWeight: 500
    lineHeight: 24px

rounded:
  none: 0px
  xs: 4px
  sm: 6px
  md: 10px
  lg: 12px
  xl: 16px
  pill-sm: 64px
  pill: 100px
  full: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 40px
  3xl: 48px
  4xl: 64px
  5xl: 96px
  6xl: 128px
  section: 192px

components:
  nav-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    height: 64px
    padding: "{spacing.sm} {spacing.lg}"
  nav-link:
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.full}"
    padding: "{spacing.xs} {spacing.sm}"
  nav-cta-signup:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm-strong}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.xs}"
    height: 28px
  nav-cta-login:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm-strong}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.xs}"
    height: 28px
  nav-cta-ask-ai:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-sm-strong}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.xs}"
    height: 28px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-lg}"
    rounded: "{rounded.pill}"
    padding: "0px {spacing.sm}"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button-lg}"
    rounded: "{rounded.pill}"
    padding: "0px {spacing.sm}"
  button-primary-sm:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: "0px {spacing.xs}"
  button-secondary-sm:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
    padding: "0px {spacing.xs}"
  tab-ghost:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.pill-sm}"
    padding: "0px {spacing.md}"
  icon-button-circular:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    rounded: "{rounded.full}"
  card-marketing:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  card-marketing-large:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  card-soft:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  template-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  code-editor-mockup:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.code}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  form-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.sm}"
    height: 40px
  form-input-sm:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.sm}"
    height: 32px
  form-input-lg:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: "0px {spacing.sm}"
    height: 48px
  badge-secondary:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.body}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "0px {spacing.xs}"
  pricing-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  pricing-card-featured:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  logo-strip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    padding: "{spacing.lg} {spacing.xl}"
  hero-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-xl}"
    padding: "{spacing.4xl} {spacing.lg}"
  feature-mesh-band:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-lg}"
    padding: "{spacing.5xl} {spacing.lg}"
  showcase-band-light:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.display-lg}"
    padding: "{spacing.5xl} {spacing.lg}"
  showcase-band-dark:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.display-lg}"
    padding: "{spacing.5xl} {spacing.lg}"
  footer:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    padding: "{spacing.4xl} {spacing.lg}"
  link-inline:
    textColor: "{colors.link}"
    typography: "{typography.body-md}"
  banner-marketing:
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.full}"
    padding: "{spacing.xs} {spacing.sm}"

  # ─── Examples (illustrative) — auto-derived ───
  ex-pricing-tier:
    description: "Default tier card. Mirrors pricing-card chrome on canvas-soft surface with a hairline border."
    backgroundColor: "{colors.canvas-soft}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-pricing-tier-featured:
    description: "Featured tier — polarity-flipped to ink primary with white text and white CTA."
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-product-selector:
    description: "What's Included summary card — repurposed for feature tiers."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  ex-cart-drawer:
    description: "Subscription summary — line items per add-on."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
    item-divider: "{colors.hairline}"
  ex-app-shell-row:
    description: "Sidebar nav row. Active state uses brand primary as a left-edge indicator bar."
    backgroundColor: "{colors.canvas}"
    activeIndicator: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.sm}"
  ex-data-table-cell:
    description: "Mirrors table chrome. Header uses caption-mono uppercase mono; body uses body-sm."
    headerBackground: "{colors.canvas-soft}"
    headerTypography: "{typography.caption-mono}"
    bodyTypography: "{typography.body-sm}"
    cellPadding: "{spacing.xs} {spacing.sm}"
    rowBorder: "{colors.hairline}"
  ex-auth-form-card:
    description: "Sign-in / sign-up card. Mirrors card-marketing-large chrome with form-input primitives inside."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-modal-card:
    description: "Modal dialog surface — same chrome as card-marketing-large with Level 5 modal shadow."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-empty-state-card:
    description: "Empty-state illustration frame. Generous padding on canvas-soft."
    backgroundColor: "{colors.canvas-soft}"
    rounded: "{rounded.lg}"
    padding: "{spacing.3xl}"
    captionTypography: "{typography.body-md}"
  ex-toast:
    description: "Toast notification surface — flat-cornered card-marketing chrome with Level 4 shadow."
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.md}"
    typography: "{typography.body-sm}"

---

## Overview

Hairline Grid Portfolio is an architectural design system — a crafted design language whose surface is built on `{colors.canvas}` (#0e0e10 in dark mode) paired with `{colors.ink}` (#f5f5f7) ink typography. The interface introduces `{colors.link}` (#67a6fb) as the decisive brand accent, supported by `{colors.violet}` (#a78bfa) highlights and subtle `{colors.hairline}` (#303034) hairline rules.

Type is the decisive voice. ui-sans-serif carries display and headlines with negative letter-spacing for refined editorial authority, while Geist powers high-readability body narrative and Geist Mono handles technical metadata, code blocks, and badges.

Surfaces use a calibrated step ladder: `{colors.canvas}` (#0e0e10 base canvas), `{colors.canvas-soft}` (#151518 elevated panels), `{colors.canvas-soft-2}` (inset regions), and `{colors.primary}` (polarity-flipped dark/light bands). Elevation is built on stacked shadows layered with subtle opacity and crisp inset hairlines.

**Key Characteristics:**
- A high-contrast primary CTA `{colors.primary}` carries core conversion targets, paired with `{colors.canvas}` for secondary actions.
- Curated color accents (`#67a6fb` and `#a78bfa`) provide purposeful focus points without unnecessary color noise.
- Every section eyebrow and small label uses the monospace face `{typography.caption-mono}` or `{typography.code}`.
- Subtle stacked-shadow elevation — layered offsets with delicate opacity — never a single harsh drop-shadow.
- Standardized container geometry: `{rounded.md}` (10px) for buttons/inputs and `{rounded.xl}` (16px) for cards.

## Colors

### Brand & Accent
- **Primary Ink / CTA** (`{colors.primary}` — `#67a6fb`): The main conversion CTA color and high-contrast anchor.
- **Primary Accent** (`{colors.link}` — `#67a6fb`): Brand highlight color for active states, link interactions, and focus rings.
- **Secondary Accent** (`{colors.violet}` — `#a78bfa`): Complementary highlight color for badges and micro-details.

### Surface
- **Canvas** (`{colors.canvas}` — `#0e0e10`): Base page background canvas.
- **Canvas Soft** (`{colors.canvas-soft}` — `#151518`): Elevated card and panel surfaces.
- **Canvas Soft 2** (`{colors.canvas-soft-2}` — `#202023`): Deeper inset surfaces and interactive hover layers.
- **Hairline** (`{colors.hairline}` — `#303034`): 1px structural container divider.
- **Hairline Strong** (`{colors.hairline-strong}` — `#59595c`): Emphasized border and secondary divider.

### Text
- **Ink** (`{colors.ink}` — `#f5f5f7`): All primary titles, headings, and high-contrast text.
- **Body** (`{colors.body}` — `#a0a1a9`): Secondary narrative, subtitles, and descriptive paragraphs.
- **Mute** (`{colors.mute}` — `#808087`): Subtle helper labels, timestamps, and fine print.
- **On Primary** (`{colors.on-primary}` — `#000000`): Inverted text on `{colors.primary}` surfaces.

### Semantic
- **Success / Link** (`{colors.success}` — `#10b981`): Positive states and verified confirmations.
- **Error** (`{colors.error}` — `#ee0000`): Destructive actions and form validation alerts.
- **Warning** (`{colors.warning}` — `#f5a623`): Cautionary status and pending indicators.

### Brand Gradient
The brand signature gradient flow:
- `{colors.gradient-develop-start}` (#67a6fb) → `{colors.gradient-develop-end}` (#a78bfa)

## Typography

### Font Family
- **Display / Headings**: ui-sans-serif, system-ui, -apple-system, sans-serif
- **Body / Narrative**: Geist, system-ui, -apple-system, sans-serif
- **Technical / Monospace**: Geist Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-xl}` | 48px | 600 | 48px | -2.4px | Hero main headline. |
| `{typography.display-lg}` | 32px | 600 | 40px | -1.28px | Major section titles. |
| `{typography.display-md}` | 24px | 600 | 32px | -0.96px | Card cluster titles, modal headers. |
| `{typography.display-sm}` | 20px | 600 | 28px | -0.6px | Sub-section micro-headings. |
| `{typography.body-lg}` | 18px | 400 | 28px | 0px | Lead introductory paragraphs. |
| `{typography.body-md}` | 16px | 400 | 24px | 0px | Default body copy. |
| `{typography.body-md-strong}` | 16px | 500 | 24px | 0px | Bolded inline body emphasis. |
| `{typography.body-sm}` | 14px | 400 | 20px | -0.28px | Secondary body, nav links, compact cards. |
| `{typography.body-sm-strong}` | 14px | 500 | 20px | -0.28px | Navigation CTA labels, table headers. |
| `{typography.caption}` | 12px | 400 | 16px | 0px | Meta tags, badge labels, fine print. |
| `{typography.caption-mono}` | 12px | 400 | 16px | 0px | Technical metadata and category tags. |
| `{typography.code}` | 13px | 400 | 20px | 0px | Code snippets, terminal commands. |
| `{typography.button-md}` | 14px | 500 | 20px | 0px | Compact button labels. |
| `{typography.button-lg}` | 16px | 500 | 24px | 0px | Large marketing CTA labels. |

### Principles
- **Negative tracking on display titles**: Aggressive -2.4px to -0.6px tracking for editorial poise.
- **Technical separation**: Monospaced face reserved exclusively for technical labels, code, and data metrics.
- **Maximum weight 600**: Keep headings grounded without noisy heavy black fonts.

### Note on Font Substitutes
- If ui-sans-serif is not locally available, system fallbacks provide instant graceful degradation: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.

## Layout

### Spacing System
- Base unit: 4px modular rhythm.
- Spacing tokens: `{spacing.xxs}` (4px) · `{spacing.xs}` (8px) · `{spacing.sm}` (12px) · `{spacing.md}` (16px) · `{spacing.lg}` (24px) · `{spacing.xl}` (32px) · `{spacing.2xl}` (40px) · `{spacing.3xl}` (48px) · `{spacing.4xl}` (64px) · `{spacing.5xl}` (96px).
- Section vertical padding: `{spacing.4xl}` (64px) to `{spacing.5xl}` (96px).

### Grid & Container
- Max container width: `1280px` / `1400px` centered with `{spacing.lg}` (24px) lateral gutters.
- Standard columns: 3-column feature grid on desktop, collapsing to 1-column on mobile.

### Responsive Strategy

#### Breakpoints
| Name | Width | Key Changes |
|---|---|---|
| Mobile | < 600px | 1-column vertical stack, mobile navigation sheet. |
| Tablet | 600–959px | 2-column grid adaptation, compact padding. |
| Desktop | 960–1199px | Full multi-column grid layouts. |
| Wide | ≥ 1200px | Max container width constraint with centered margins. |

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Level 0 — Flat | No shadow, 1px `{colors.hairline}` border. | Base canvas panels and full-bleed bands. |
| Level 1 — Inset Hairline | `0 0 0 1px {colors.hairline}` inset border. | Standard cards and content modules. |
| Level 2 — Subtle Drop | `0px 1px 2px rgba(0,0,0,0.05)` + hairline. | Elevated interactive cards. |
| Level 3 — Soft Stack | `0px 4px 12px -2px rgba(0,0,0,0.08)` + hairline. | Feature cards and active containers. |
| Level 4 — Float Stack | `0px 8px 24px -4px rgba(0,0,0,0.12)` + hairline. | Pricing tiers and prominent popovers. |
| Level 5 — Modal | `0px 16px 40px -8px rgba(0,0,0,0.20)` + hairline. | Modal dialogs and central overlays. |

## Shapes

### Border Radius Scale
| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Full-bleed hero and footer bands. |
| `{rounded.xs}` | 4px | Micro badges and code tags. |
| `{rounded.sm}` | 6px | Form input controls and small badges. |
| `{rounded.md}` | 10px | Primary buttons and interactive chips. |
| `{rounded.lg}` | 12px | Standard cards and containers. |
| `{rounded.xl}` | 16px | Prominent hero panels and modals. |
| `{rounded.full}` | 9999px | Circular icon buttons and pill badges. |

## Components

### Buttons
- **`button-primary`**: Background `{colors.primary}`, text `{colors.on-primary}`, shape `{rounded.pill}`, typography `{typography.button-lg}`.
- **`button-secondary`**: Background `{colors.canvas}`, text `{colors.ink}`, border 1px solid `{colors.hairline}`, shape `{rounded.pill}`.

### Cards & Containers
- **`card-marketing`**: Background `{colors.canvas}`, text `{colors.ink}`, shape `{rounded.md}`, border 1px solid `{colors.hairline}`.
- **`card-soft`**: Background `{colors.canvas-soft}`, text `{colors.ink}`, shape `{rounded.md}`.

### Inputs & Forms
- **`form-input`**: Background `{colors.canvas}`, border 1px solid `{colors.hairline}`, text `{colors.ink}`, shape `{rounded.sm}`, height 40px.

## Do's and Don'ts

### Do
- Maintain authentic dark canvas (`{colors.canvas}`) with clear semantic surface layers.
- Use `{colors.primary}` for primary conversion CTAs.
- Apply negative letter-spacing to headings for high-end typographic authority.
- Standardize container padding using 4px/8px modular rhythm tokens.
- Ensure all form controls have custom borders (`{colors.hairline}`) and focus rings (`{colors.link}`).

### Don't
- Don't introduce arbitrary purple-to-indigo gradients.
- Don't leave form inputs unstyled with default browser borders.
- Don't use uppercase typography outside of `{typography.caption-mono}` tags.
- Don't apply single harsh drop-shadows; use multi-level stacked elevation.

</design-context>
