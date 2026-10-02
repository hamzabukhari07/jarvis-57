# 🚀 ZEZO Phase Plan: Proactive Voice Narration, Fast ROI OCR & Desktop Macros

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target Goal:** 
> 1. Eliminate all dead-air / silence during desktop operations ("Jarvis Boss & Worker" paradigm).  
> 2. Accelerate UI text localization from 25s to < 250ms via Active Window & Sidebar ROI Cropping.  
> 3. Implement compound desktop macros (`batch` actions with auto-tabbing) + optional Figma WebSocket bridge.

---

## 📋 Problem Analysis & Direct Solutions

| Current Problem | Root Cause | Target Architecture Solution |
| :--- | :--- | :--- |
| **Dead Silence (Chup Rehna)** | Gemini Live stops audio during tool execution; tools run sequentially without intermediate voice updates. | **Phase 1:** Immediate pre-action verbal confirmation + parallel status voice pipe (`plugin_say` / fast TTS narrator) for multi-second tasks. |
| **15s–25s Delay per Click** | Full-screen 4K/1080p RapidOCR scan on CPU when native UIA is unavailable in Electron apps (Figma). | **Phase 2:** Active Window & Right-Sidebar ROI (Region of Interest X: 1500–1920) Cropping (< 250ms OCR). |
| **Sequential Tool Ping-Pong** | Changing Width & Height takes 6–8 separate tool roundtrips. | **Phase 3:** Compound `batch` macro execution (`actions/computer_control.py`) combining Click ➡️ Type ➡️ Tab ➡️ Type ➡️ Enter in 1 call (~1s total). |
| **Figma Direct Control** | Blind coordinate dragging on canvas. | **Phase 4:** Optional 10ms local Figma Plugin WebSocket Bridge (`actions/figma_helper.py`) for direct programmatic canvas drawing. |

---

## 🗺️ Implementation Phases

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Proactive Voice Narration (Zero Dead-Air / Jarvis Boss Mode)        │
│ ├─ Pre-execution verbal acknowledgement in Live session (< 1s response)      │
│ ├─ Parallel progress voice channel (for any action > 1.5s)                   │
│ └─ Prompt tuning: Jarvis acts as vocal Dispatcher & Master Operator          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Sub-Second OCR Acceleration via ROI Cropping (< 250ms)              │
│ ├─ Active Window Bounding-Box Cropping (in core/computer/ocr_engine.py)      │
│ ├─ Right-Sidebar Inspector Priority (Right 25% for W/H/Fill/Stroke inputs)   │
│ └─ Fast pre-filtered OCR grounding (17s ➡️ 200–300ms on CPU)                 │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Compound Desktop Macros & Tab Navigation (`batch` action)           │
│ ├─ `batch` action support in actions/computer_control.py                     │
│ ├─ Smart Auto-Tabbing (Click Width ➡️ Type ➡️ Tab ➡️ Type ➡️ Enter)          │
│ └─ Prompt injection for single-turn compound desktop execution               │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Figma Local Plugin Bridge (Optional Power-User Mode)                │
│ ├─ Lightweight local WebSocket bridge in actions/figma_helper.py             │
│ └─ 10ms programmatic frame/shape creation without mouse dragging             │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: Strict 3-Layer Verification & Real Desktop Benchmark                │
│ ├─ Layer 1: Static syntax & action discovery (24/24 active tools)            │
│ ├─ Layer 2: Runtime benchmarks (OCR < 250ms, batch macro < 1s, voice pipe)   │
│ └─ Layer 3: Full pytest regression suite                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 🔹 Phase 1: Proactive Voice Narration (Zero Dead-Air)

- **Objective:** ZEZO must never be silently busy. User gets immediate verbal confirmation and continuous progress narration.
- **Tasks:**
  1. **Prompt Tuning (`core/prompt.txt`):**
     - Require the model to **always speak an immediate 1-sentence confirmation** (e.g., *"Setting up a 400 by 400 frame in Figma for you, sir."*) before triggering heavy desktop tools.
  2. **Mid-Task Status Voice Pipe (`actions/computer_control.py`):**
     - For tasks with multiple steps or expected duration > 1.5s, dispatch non-blocking audio narration via `context["speak"]` / `plugin_say`.
  3. **HUD Real-time Status:**
     - Broadcast current sub-step (`"Locating Width input..."`, `"Applying dimensions..."`) to UI log and HUD overlay.

---

### 🔹 Phase 2: Sub-Second OCR via ROI Cropping (< 250ms)

- **Objective:** Cut RapidOCR search latency from 25,000ms to < 250ms on CPU.
- **Tasks:**
  1. **Foreground Window Cropping:**
     - In `core/computer/ocr_engine.py`, obtain the active window rectangle using `windows_native.get_active_window_rect()`.
     - Crop the screenshot to only the active application instead of scanning the full 4K screen.
  2. **Sidebar / Inspector Priority Heuristic:**
     - For property queries (`"W"`, `"H"`, `"Width"`, `"Height"`, `"X"`, `"Y"`, `"Fill"`, `"Stroke"`):
     - Automatically crop only the **Right 25% (Sidebar X: 1500–1920)** where property fields reside in design and editing software.
  3. **Benchmark Validation:**
     - Verify OCR latency drops from 17s+ to sub-300ms on CPU.

---

### 🔹 Phase 3: Compound Desktop Macros (`batch` actions)

- **Objective:** Replace 6 to 8 slow tool roundtrips with 1 single atomic execution.
- **Tasks:**
  1. **Batch Action Schema in `actions/computer_control.py`:**
     - Extend `TOOL` to accept `action="batch"` with a step sequence:
       ```json
       {
         "action": "batch",
         "sequence": [
           {"action": "screen_click", "description": "Width"},
           {"action": "type", "text": "400"},
           {"action": "press", "key": "tab"},
           {"action": "type", "text": "400"},
           {"action": "press", "key": "enter"}
         ]
       }
       ```
  2. **Smart Tab Navigation:**
     - Clicking `Width`, typing, and pressing `Tab` automatically moves the cursor to `Height` in Figma, Photoshop, and web forms.
     - Entire dimension change executes in **under 1.0 second**.

---

### 🔹 Phase 4: Figma Local Plugin Bridge (Optional Power-User Mode)

- **Objective:** Provide direct 10ms programmatic canvas creation for power users.
- **Tasks:**
  1. Create `actions/figma_helper.py` hosting a lightweight local WebSocket endpoint (`localhost:8765`).
  2. Provide a 20-line standalone Figma manifest/plugin that creates frames/shapes directly via `figma.createFrame()` in 10ms with 0 OCR and 0 mouse clicks.
  3. Fall back seamlessly to Phase 3 shortcuts when the plugin is not connected.

---

### 🔹 Phase 5: Strict 3-Layer Verification & Documentation

- **Objective:** Guarantee rock-solid system stability without regressions.
- **Tasks:**
  1. **Layer 1 (Static):**
     - Compile all project files with `python -m py_compile`.
     - Validate action discovery for all 24 tools.
  2. **Layer 2 (Runtime Benchmarks):**
     - Measure OCR ROI speed (< 250ms).
     - Measure batch macro execution (< 1.0s).
     - Test live speech announcement during execution.
  3. **Layer 3 (Regression & Docs):**
     - Run pytest suite (`test_agent_settings.py`, `test_api_key_transactional.py`, `test_pipeline_ui_integration.py`).
     - Update `LEARNING_JOURNAL.md`, `docs/TOOLS.md`, and `AGENTS.md`.
