# 🎨 Local Folder Redesign & Aesthetic Injection Engine

> **Action:** `actions/antigravity_agent.py` (`antigravity_run`)  
> **Aesthetic Skills:** `skills/hamza_taste/`  
> **Design Resolver:** `core/design_resolver.py`  
> **Undo Safety:** `core/undo.py` (`register_snapshot`)  

---

## 📖 Overview

The **Local Folder Redesign Engine** takes any existing local website or UI project folder on the user's computer (e.g. `Desktop/gym_website` or uploaded clone folder), reads the existing text, structure, and copy, and modernizes it with premium studio aesthetics (dark mode, glassmorphism, fluid animations, dynamic typography, responsive layout).

```
[ Local Website Folder ] 
          │
          ▼
`core/design_resolver.py` & `skills/hamza_taste/` 
(Extracts content, injects design tokens & anti-slop rules)
          │
          ▼
`actions/antigravity_agent.py`
(Preserves copy, rewrites HTML/CSS or compiles to React/Next.js)
          │
          ▼
`core/undo.py` Snapshot Created (1-Click Revertible)
```

---

## 🛠️ Key Capabilities

1. **Content & Copy Preservation:**
   - The engine parses the existing HTML/text and strictly preserves the user's business names, taglines, features, and content while completely overhauling the visual presentation.
2. **Framework & Stack Freedom:**
   - Can output modern Vanilla HTML/CSS/JS, a **single self-contained `index.html`**, or generate a full modern Next.js / Tailwind React application based on user instruction.
   - **Stack fidelity:** the user's requested stack always wins. "single HTML" / "one index.html" / "no React" → one standalone file; React/Next.js only when explicitly requested. A full-rebuild request on a folder that already holds another stack replaces it instead of preserving the old framework.
3. **Studio Design Tokens:**
   - Applies deep obsidian dark modes (`#050505`), vibrant gradient accents, clean typography (Outfit, Inter, Space Grotesk), micro-animations, and glassmorphic cards.
4. **Safety & Rollback:**
   - Automatically registers a folder snapshot in `core/undo.py` prior to writing any changes, allowing the user to say *"Undo"* to instantly restore their original files.
