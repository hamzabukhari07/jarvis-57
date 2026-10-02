# 🏛️ ZEZO OS — Native UIA & Multilingual OCR Integration Plan

> **Project:** ZEZO (Autonomous Desktop AI Operating System v2)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Principle:** *"Observe only when necessary — Escalate perception, don't waterfall it. 0 MB VRAM footprint."*  
> **Status:** ✅ FULLY IMPLEMENTED & VERIFIED (3-LAYER TEST SUITE PASSED)  
> **Target Tool Count:** Exactly 24 Discovered Tools (0 Tool Bloat)

---

## 🎯 Executive Summary & Objectives

This plan implements the **0 MB VRAM Escalation Architecture** for ZEZO OS desktop automation, resolving canvas/native control blind spots without adding heavy local vision models (OmniParser/UI-TARS) that would exhaust laptop GPU memory:

1. **L1: Native Windows UIAutomation Core (`uiautomation`):**
   - Traverse and inspect deep control trees (buttons, inputs, tabs, list items) inside Windows native apps, Chromium, and Electron in **< 15ms** using pure CPU COM interop.
   - Run in an STA threadpool worker with `CoInitialize()` and 0.8s timeout boundaries to guarantee the Live audio loop never hangs if an app is unresponsive.
2. **L1.5: Local Lightweight RapidOCR (`rapidocr_onnxruntime`):**
   - Execute spatial multilingual OCR (English, Urdu, Arabic, numeric) on CPU in **< 80ms**.
   - Normalize Urdu/Arabic characters (strip tashkeel/diacritics, unify yeh/kaf/heh) with `fuzzy_threshold=0.75`.
   - Convert screen text into exact `(x, y)` click coordinates without round-trips to cloud vision models.
3. **Escalated Element Finder in `actions/computer_control.py`:**
   - Seamlessly chain: **L1 (UIA Tree)** ➔ **L1.5 (RapidOCR Text Match)** ➔ **L2 (Gemini Multimodal Cloud Vision)**.
4. **Instant Text Inspection in `actions/screen_processor.py`:**
   - Allow Gemini Live to read on-screen text, dialog messages, and Urdu inputs with 0 cloud latency.

---

## 📋 Architectural Verdict & Feasibility

| Check / Requirement | Status | Architecture Decision |
| :--- | :--- | :--- |
| **Tool Count** | ✅ 24 Intact | Zero new tools added; embedded within existing L1/L2 escalation layers. |
| **VRAM Footprint** | ✅ 0 MB VRAM | Pure CPU COM interop + ONNX CPU runtime (~80MB RAM). |
| **Figma / Canvas Blind Spam** | ✅ Fixed | L1.5 RapidOCR finds "Fill", "Width", and labels spatially in <80ms without tab spamming. |
| **Native Button Clicks** | ✅ Fixed | L1 UIA finds "Save", "File", "Don't Save" in <15ms without screenshots. |
| **Thread & Process Safety** | ✅ Safe | Dedicated worker thread with `CoInitialize()` and 0.8s timeout guards. |
| **Multilingual Support** | ✅ Verified | Normalized Urdu/Arabic text matching with 0.75 fuzzy tolerance. |

---

## 📋 Phased Execution Roadmap

```
[ Phase 1: Native Windows UIA Engine Hardening (core/computer/windows_uia.py) ]
       │
[ Phase 2: Lightweight CPU RapidOCR Engine & Urdu Normalizer (core/computer/ocr_engine.py) ]
       │
[ Phase 3: 3-Tier Element Finder Escalation (actions/computer_control.py) ]
       │
[ Phase 4: Instant Screen Text Reading & Grounding (actions/screen_processor.py) ]
       │
[ Phase 5: System Prompt & Figma Canvas Skill Alignment (core/prompt.txt) ]
       │
[ Phase 6: 3-Layer Verification, Test Suite & Documentation Sync ]
```

---

### 🔹 Phase 1: Native Windows UIA Engine Hardening
- **Objective:** Enable instant, robust accessibility tree element discovery and control interaction across all top-level foreground applications without taking screenshots or blocking the async event loop.
- **Key Modules:** `core/computer/windows_uia.py`, `core/computer/__init__.py`
- **Tasks:**
  - [x] Initialize STA COM threading with `CoInitialize()` in worker threads.
  - [x] Implement thread-safe UIA inspection with `searchDepth=6`, `max_elements=20`, and `timeout=0.8s` inside `ThreadPoolExecutor`.
  - [x] Filter interactive control types to avoid scanning 200+ container nodes:
    `ControlType` in `("Button", "Edit", "TabItem", "MenuItem", "Hyperlink", "CheckBox", "ComboBox", "ListItem")`.
  - [x] Support finding elements by Name, AutomationId, ClassName, and ControlType.
  - [x] Implement `dump_interactive_elements(hwnd, max_elements=20, search_depth=6)` returning structured bounds `{"name", "control_type", "center_x", "center_y", "rect"}`.
  - [x] Add graceful fallback to `win32gui` if UIA is disabled or blocked on a legacy window.

---

### 🔹 Phase 2: Lightweight CPU RapidOCR Engine & Urdu Normalizer
- **Objective:** Provide sub-100ms local text detection and bounding box localization with zero GPU VRAM consumption.
- **Key Modules:** `core/computer/ocr_engine.py`, `core/computer/__init__.py`
- **Tasks:**
  - [x] Create `core/computer/ocr_engine.py` wrapping `rapidocr_onnxruntime` with lazy initialization (loads ONNX models on first use).
  - [x] Implement Urdu and Arabic unicode normalization `normalize_urdu(text)`:
    - Strip diacritics / tashkeel (`َ ِ ُ ً ٍ ٌ ّ ْ`).
    - Normalize character variations (`ي`/`ى` ➔ `ی`, `ك` ➔ `ک`, `ه`/`ة` ➔ `ہ`, `أ`/`إ`/`آ` ➔ `ا`).
  - [x] Support whole-screen and region-specific OCR runs.
  - [x] Implement `find_text_coordinates(target_text, region=None, fuzzy_threshold=0.75)` returning `(center_x, center_y, confidence, matched_text)`.

---

### 🔹 Phase 3: 3-Tier Element Finder Escalation
- **Objective:** Upgrade `_find_target_element_escalated()` in `actions/computer_control.py` to route through L1 ➔ L1.5 ➔ L2.
- **Key Modules:** `actions/computer_control.py`
- **Tasks:**
  - [x] Update `_find_target_element_escalated(description)`:
    1. **Tier 1 (L1 UIA):** Search active window UIA accessibility tree (<15ms, depth=6).
    2. **Tier 2 (L1.5 RapidOCR):** Search screen text matches via normalized OCR (<80ms, fuzzy=0.75).
    3. **Tier 3 (L2 Gemini Vision):** Call Gemini Multimodal API if element is a non-text graphic icon (~2.0s).
  - [x] Tag the resolved element source (`l1_uia`, `l1.5_ocr`, `l2_vision`) in execution telemetry.
  - [x] Ensure all 24 tool declarations and parameters remain 100% backward compatible.

---

### 🔹 Phase 4: Instant Screen Text Reading & Grounding
- **Objective:** Enhance `actions/screen_processor.py` to answer text-reading queries in milliseconds without cloud vision calls.
- **Key Modules:** `actions/screen_processor.py`
- **Tasks:**
  - [x] Add `extract_screen_text(region=None, mode='full')` utilizing the local OCR engine.
  - [x] If user asks "what is written on screen" or "read this error", use local OCR if confidence is high, falling back to Gemini Vision for holistic layout comprehension.
  - [x] Combine OCR output with native OS ground-truth state (`get_active_window_context()`).

---

### 🔹 Phase 5: System Prompt & Figma Canvas Skill Alignment
- **Objective:** Teach Gemini Live how to leverage the 3-tier perception hierarchy efficiently.
- **Key Modules:** `core/prompt.txt`, `skills/figma_helper/SKILL.md`
- **Tasks:**
  - [x] Update `core/prompt.txt` under `[PERCEPTION & ACTION ESCALATION]` to document the L1 UIA ➔ L1.5 OCR ➔ L2 Vision escalation ladder.
  - [x] Update `skills/figma_helper/SKILL.md` with recipes combining spatial hotkeys and L1.5 OCR text targeting.

---

### 🔹 Phase 6: 3-Layer Verification, Test Suite & Documentation Sync
- **Objective:** Guarantee zero regressions against `AGENTS.md` rules with automated pass/fail verification criteria.
- **Tasks:**
  - [x] **Layer 1 (Static):** Run `py_compile` across all modified files; verify clean imports and action discovery (24 actions).
  - [x] **Layer 2 (Concrete Runtime Assertions):**
    - **UIA Discovery & Timeout Test:** Verify element lookup in active Notepad or Explorer window in <20ms, assert 0.8s timeout bounds.
    - **OCR & Urdu Normalization Test:** Assert RapidOCR executes on CPU in <100ms, test Urdu normalization (`میرا` vs `ميرا`), and verify fuzzy match at 0.75.
    - **Escalation Ladder Test:** Verify element lookup successfully falls back through L1 ➔ L1.5 ➔ L2.
  - [x] **Layer 3 (Regression Checks):** Confirm zero interference with PyQt6 GUI and Gemini Live audio loop.
  - [x] **Documentation Sync:** Update `planning/README.md`, `planning/ZEZO_PROJECT_BLUEPRINT.md`, and `LEARNING_JOURNAL.md`.

---

## 🚦 Phase Status Tracker

| Phase | Description | Key Deliverables | Status | Risk if Skipped |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Native Windows UIA Engine | `core/computer/windows_uia.py` (Depth=6, STA COM, 0.8s Timeout) | ✅ Complete | Unable to target native buttons & inputs without vision |
| **Phase 2** | Lightweight CPU RapidOCR Engine | `core/computer/ocr_engine.py` (ONNX pipeline, Urdu Normalizer) | ✅ Complete | Cannot locate on-screen text without cloud latency |
| **Phase 3** | 3-Tier Element Finder Escalation | L1 ➔ L1.5 ➔ L2 in `computer_control.py` | ✅ Complete | Reliance on slow 2s cloud vision for every click |
| **Phase 4** | Instant Screen Text Reading | Fast text extraction in `screen_processor.py` | ✅ Complete | Slow response time when reading dialogs & error text |
| **Phase 5** | Prompt & Skill Alignment | Escalation directives in `prompt.txt` | ✅ Complete | Model fails to prioritize fast local perception |
| **Phase 6** | 3-Layer Verification & Sync | Automated test suite & blueprint update | ✅ Complete | Undetected regression across 24 tools |

