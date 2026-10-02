# SKILL: figma_helper (UI & Desktop Canvas)
**Description:** Canonical spatial interaction recipes and safety guardrails for Figma and web canvas applications.

# 🎨 Figma & Desktop Canvas Helper — Spatial Interaction Protocol

> **Lead Architect & Creator:** Hamza Bukhari  
> **Trigger Condition:** Active window is Figma, Canva, or a web/Electron canvas application.  
> **Core Principle:** Canvas applications render elements in WebGL/HTML5 Canvas without standard Win32 UIA accessibility trees. All manipulations must be spatial coordinates or explicit tool activation sequences.

---

## 🛑 1. Non-Negotiable Anti-Loop Rules
1. ❌ **NEVER Spam `Shift+Tab` or `Tab`:** Figma does not cycle property inspector inputs sequentially with standard tab order. Blind tab spamming selects unintended elements and deletes frames.
2. ❌ **NEVER Type Blindly Without Placing Cursor:** Activating the Text tool (`t`) does NOT open a text box until a coordinate click is registered on the canvas.
3. ❌ **MAX 1 Perception Call Per Action Turn:** Trust the coordinates returned from `screen_process` or `get_active_window_info`.

---

## 🛠️ 2. Canonical Action Recipes

### A. Creating Text on Canvas
```
1. computer_control(action='press', key='t')
2. computer_control(action='click', x=canvas_center_x, y=canvas_center_y)
3. computer_control(action='type', text='Hello World')
4. computer_control(action='press', key='escape')
```

### B. Creating Frames & Shapes
- **Frame (`F`):** `computer_control(action='press', key='f')` ➔ `computer_control(action='drag', x1=400, y1=300, x2=1000, y2=700)` or `computer_control(action='drag', x=400, y=300, width=600, height=400)`
- **Rectangle (`R`):** `computer_control(action='press', key='r')` ➔ `computer_control(action='drag', x1=450, y1=350, x2=850, y2=550)`
- **Ellipse (`O`):** `computer_control(action='press', key='o')` ➔ `computer_control(action='drag', x1=450, y1=350, x2=650, y2=550)`
- **Pen (`P`):** `computer_control(action='press', key='p')`

### C. Canvas Viewport & Zoom Navigation
- **Zoom to Fit:** `computer_control(action='hotkey', keys='shift+1')`
- **Zoom to Selection:** `computer_control(action='hotkey', keys='shift+2')`
- **Pan Canvas:** Hold Space + Drag or use Middle Mouse Drag.

### D. Property Editing (Right Sidebar)
Never use blind tabs. Use L1.5 RapidOCR / L2 Vision target search:
1. `computer_control(action='screen_click', description='Width')` (automatically resolved via L1.5 RapidOCR in <80ms without cloud latency)
2. `computer_control(action='hotkey', keys='ctrl+a')`
3. `computer_control(action='type', text='1200')`
4. `computer_control(action='press', key='enter')`

For non-text elements (color swatches, icon buttons), `screen_click` seamlessly escalates to L2 Gemini Vision.
