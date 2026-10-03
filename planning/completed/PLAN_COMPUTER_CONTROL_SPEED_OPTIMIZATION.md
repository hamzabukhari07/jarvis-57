# 📐 Technical Implementation Plan: High-Speed Desktop Vision & Control Optimization (MSS + UIAutomation)

> **Document ID:** `PLAN-2026-10-03-COMPUTER-CONTROL-SPEED`  
> **Target Subsystem:** `core/computer/`, `actions/computer_control.py`, `actions/open_app.py`  
> **Status:** Draft / Ready for Approval  
> **Author:** Hamza Bukhari & AI Assistant  

---

## 🎯 1. Requirements & Invariants

### Functional Requirements
- **REQ-F-001 (Fast Screen Capture):** Integrate `mss` for screenshot capture across `ocr_engine.py`, `screen_processor.py`, and `computer_control.py`, reducing capture latency from ~85ms down to < 8ms with zero VRAM consumption.
- **REQ-F-002 (C++ UIA Element Resolution):** Replace legacy `pywinauto` COM threading wrapper with native `uiautomation` (C++ UIAutomationCore.dll wrapper) to accelerate UI accessibility tree traversal from ~250ms down to < 15ms while eliminating STA thread warnings.
- **REQ-F-003 (Robust 4-Tier Visual Fallback):** Retain seamless multi-tier fallback hierarchy:
  $$\text{L0: Win32 Native (<1ms)} \to \text{L1: uiautomation (<15ms)} \to \text{L1.5: RapidOCR ONNX (<60ms)} \to \text{L2: Gemini Fast Vision (Cloud)}$$
- **REQ-F-004 (Accurate App Focus/Launch):** Ensure `open_app()` and `focus_window()` strictly filter out suspended background broker windows (like UWP `CalculatorApp.exe`) so applications always launch or foreground reliably.

### Non-Functional Requirements & Invariants
- **REQ-NF-001 (Zero Main Thread Blocking):** All screen capture and UIA operations must execute within bounded timeouts (max 0.8s) and never freeze the PyQt6 GUI loop.
- **REQ-NF-002 (Zero GPU VRAM Bloat):** Maintain 0 MB VRAM overhead by avoiding heavy local PyTorch/TorchVision runtime dependencies on standard installations.
- **INV-001 (Anti-Slop Complexity):** Cyclomatic complexity must remain $< 15$ per function across all touched modules.
- **INV-002 (3-Layer Verification):** Strict verification passing static compilation, 109+ pytest unit tests, and runtime regression checks.

---

## 🏛️ 2. Architectural Decision Records (ADRs)

### ADR-068: Native `mss` Capture & `uiautomation` C++ Acceleration
- **Context:** Element finding currently relies on `pyautogui.screenshot()` (Pillow GDI capture ~80ms) and `pywinauto` (~250ms with COM STA thread contention).
- **Decision:**
  1. Implement a unified `capture_screen_fast()` helper in `core/computer/` using `mss` with graceful fallback to `pyautogui`.
  2. Implement `core/computer/windows_uia.py` using `uiautomation` with bounded search depth (depth=6, timeout=0.8s).
- **Alternatives Evaluated:**
  - *Alternative A (Local OmniParser V2):* Rejected as mandatory default due to heavy PyTorch + 4GB CUDA VRAM requirements; kept as a prospective future pluggable engine.
  - *Alternative B (Pure GDI BitBlt via ctypes):* Viable but `mss` already wraps optimized C BitBlt/DirectX across multi-monitor setups with zero bugs.

---

## 🔄 3. Phased Implementation Roadmap

### Phase 1: Fast Screen Capture Engine (`core/computer/screen_capture.py`)
- **TASK-001:** Create lightweight `capture_screen_fast(region=None)` utilizing `mss` (converting raw BGRA buffer to RGB NumPy array / PIL Image) with `pyautogui` fallback.
- **TASK-002:** Integrate `capture_screen_fast` into [`core/computer/ocr_engine.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/core/computer/ocr_engine.py) and [`actions/computer_control.py`](file:///d:/anitgravity/zezo%20work/jarvis-57/actions/computer_control.py).

### Phase 2: Modern C++ UIA Driver (`core/computer/windows_uia.py`)
- **TASK-003:** Refactor `windows_uia.py` to import `uiautomation` with dictionary dispatch and control-type matching.
- **TASK-004:** Add safe top-level and child element inspection with physical bounding rectangle calculation (`BoundingRectangle`).

### Phase 3: Desktop App Launch & Focus Polish (`actions/open_app.py`, `core/computer/windows_native.py`)
- **TASK-005:** Ensure `focus_window()` verifies `IsWindowVisible` and real foreground assignment before declaring success, seamlessly launching via `calc.exe` when needed.

### Phase 4: Verification & Documentation
- **TASK-006:** Run 3-Layer verification (Static compile, Pytest suite 109+ tests, Runtime check).
- **TASK-007:** Update [`LEARNING_JOURNAL.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/LEARNING_JOURNAL.md) and [`docs/TOOLS.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/TOOLS.md).

---

## 🛡️ 4. Traceability & Risk Register

| Requirement ID | Task ID | Code Touchpoint | Verification Test |
| :--- | :--- | :--- | :--- |
| `REQ-F-001` | `TASK-001`, `TASK-002` | `core/computer/screen_capture.py`, `ocr_engine.py` | `test_screen_capture_speed` |
| `REQ-F-002` | `TASK-003`, `TASK-004` | `core/computer/windows_uia.py` | `test_uia_element_search` |
| `REQ-F-003` | `TASK-002`, `TASK-003` | `actions/computer_control.py` | `pytest tests/` (109 suites) |
| `REQ-F-004` | `TASK-005` | `actions/open_app.py`, `windows_native.py` | App launch & focus check |
