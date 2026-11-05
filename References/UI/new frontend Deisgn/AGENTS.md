# AGENTS.md — AI UI Design Specialist Guidelines

Welcome to the **Zezo / Vitrum Studio** UI codebase. As an AI UI Design Specialist working on this project, your goal is to deliver clean, precise, and visually cohesive user interfaces that feel natural within our established design language.

---

## 1. Core Design Philosophy

- **Clean & Minimalist**: Every element on screen must serve a clear operational purpose. Avoid superfluous decorations, ornamental icons, or decorative widgets.
- **Consistent & Monochromatic**: Stick strictly to the Vitrum Studio Monochrome / Graphite design system. Do not introduce arbitrary brand colors, vivid gradients, or flashy accents.
- **Calm Interactivity**: Avoid hyperactive, distracting hover states, heavy scaling transformations (`transform: scale(...)`), bouncy animations, or jarring transitions. Micro-interactions should be subtle, refined, and purposeful.
- **Component Reuse First**: Always audit existing components and design primitives before creating new ones.
- **Cohesive Extensions**: When a needed component does not exist, craft it to directly mirror the design tokens, typography, borders, and shadows of the existing design system.

---

## 2. Design Tokens & Styling Rules

All styling is managed through CSS custom properties defined in [`src/styles.css`](file:///c:/Users/Hamza%20Bukhari/Downloads/Viturm%20Dsahboard%20Design/zezo-react/src/styles.css). Never hardcode ad-hoc hex values or arbitrary drop shadows in component code.

### 2.1 Color Palette
- **Graphite Scale**:
  - Light mode: `--graphite-0` (#ffffff) to `--graphite-900` (#26282e).
  - Dark mode: Handled via `[data-theme="dark"]` overrides.
- **Semantic Surfaces**:
  - `var(--shell)`: App background / outer frame.
  - `var(--sidebar)`: Navigation panel background.
  - `var(--card)` / `var(--slab)`: Elevated content cards and container backgrounds.
  - `var(--stage)`: Canvas / active workspace area.
  - `var(--well)` & `var(--well-strong)`: Inset or subtle secondary backgrounds.
- **Typography & Text Contrast**:
  - Primary text: `var(--ink)`
  - Secondary text / captions: `var(--ink-2)`
  - Tertiary / muted labels: `var(--ink-3)`
- **Accents (Use with Extreme Restraint)**:
  - Success / Active state: `var(--emerald-500)` (#10b981) and `var(--emerald-glow)`.
  - Error / Alert state: `var(--rose-500)` (#ef4444).
  - Default highlight / focus: `var(--lamp)` and `var(--lamp-glow)`.

### 2.2 Borders & Shadows (Vitrum Depth)
- **Hairlines**: Always use `var(--hairline)` or `var(--hairline-strong)` for card borders, separators, and button outlines.
- **Elevation Shadows**:
  - Raised elements (buttons, popovers): `var(--shadow-raise)`.
  - Floating panels / stages: `var(--shadow-pane)`.
  - Do not use generic CSS shadows like `box-shadow: 0 4px 6px rgba(0,0,0,0.1)`.

### 2.3 Typography & Sizing
- Font family: Inter, system UI stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
- Monospace font: JetBrains Mono, Fira Code, or monospace for technical data, code, IDs, and timestamps.
- Hierarchy:
  - Headings: Clean, medium/semi-bold font weights (`500` - `600`), tight letter spacing (`-0.01em` to `-0.02em`).
  - Body text: Regular weight (`400` - `450`), readable line height (`1.4` - `1.5`).
  - Metadata / Badges: Small (`11px` - `12px`), uppercase or sentence-cased with subtle opacity.

---

## 3. UI Component Reuse & Architecture

Before authoring new JSX markup, inspect the existing components in [`src/components/`](file:///c:/Users/Hamza%20Bukhari/Downloads/Viturm%20Dsahboard%20Design/zezo-react/src/components):

- **Sidebar (`Sidebar.tsx`)**: Primary navigation, session history, collapsible state, and user actions.
- **MessageItem (`MessageItem.tsx`)**: Chat message rendering, metadata, copy actions, and embedded tool invocations.
- **ToolActionCard (`ToolActionCard.tsx`)**: Technical execution blocks, terminal/diff previews, command inspection.
- **ChatComposer (`ChatComposer.tsx`)**: Text input, tool action shortcuts, and send button interactions.
- **VoiceView (`VoiceView.tsx`)**: Full-screen voice and audio visualization state.

### Rules for Creating New Components
1. **Match the Component Contract**:
   - Write typed TypeScript components (`React.FC<Props>`).
   - Use standard `lucide-react` icons matching the line weight and size (`size={14}` to `size={18}`) of existing UI.
2. **Follow Existing Class Naming & CSS Patterns**:
   - Adhere to the established CSS classes in `src/styles.css` (e.g., `.btn-ghost`, `.badge`, `.card`, `.pane-header`).
   - Keep styles encapsulated or append systematically to `src/styles.css` under well-defined section comments.
3. **Responsive & Collapsible States**:
   - Ensure components gracefully handle compact widths and responsive flex/grid layouts without clipping or overflow artifacts.

---

## 4. Interaction & Motion Rules

- **Hover States**:
  - Keep hover effects discreet: transition background colors (`var(--well)` on hover) and border color softly (`transition: all 0.15s ease`).
  - Avoid glowing drop-shadows on generic buttons or non-primary actions.
  - Never scale up cards or buttons on hover (`:hover { transform: scale(...) }` is prohibited).
- **Active / Pressed States**:
  - Use subtle depression (`transform: translateY(1px)` or opacity change `0.85`).
- **Transitions**:
  - Keep transition durations between `120ms` and `200ms` with `ease-out` or `ease-in-out`.
  - Avoid bouncy spring animations unless specifically animating real-time audio wave visuals.

---

## 5. Review Checklist for UI Specialists

Before finalizing any UI addition or modification, verify:
- [ ] **Visual Cohesion**: Does the UI feel like an integral part of Zezo / Vitrum Studio?
- [ ] **Color Discipline**: Are only tokens (`--graphite-*`, `--ink-*`, `--hairline-*`) used? No rogue colors?
- [ ] **No Visual Clutter**: Have unnecessary badges, decorative borders, gradient texts, or redundant icons been eliminated?
- [ ] **Hover Polish**: Are hover effects understated and subtle?
- [ ] **Dark & Light Compatibility**: Does the view look equally balanced and legible in both light and dark modes?
- [ ] **Component Economy**: Was an existing component reused, or if new, does it follow the exact same structural patterns?
