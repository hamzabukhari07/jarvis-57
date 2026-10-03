# ZEZO OS — Tiered Perception & Vision Architecture

> **Creator & Lead Architect:** Hamza Bukhari  
> **Core Principle:** *"Observe only when necessary — Escalate perception, don't waterfall it."*

## Overview

ZEZO features a **4-Tier Escalated Perception Engine** that combines instantaneous Win32 OS telemetry (0.37ms), Windows UI Automation (10ms), local Multilingual RapidOCR (0 MB VRAM, <80ms), perceptual gradient difference hashing (0ms cache hits), and deep Gemini multimodal vision.

```
                              User Request / Gemini Live
                                          │
                                   ZEZO Dispatcher
                                          │
                               ┌───────────────────────┐
                               │ Perception Required?  │
                               └───────────┬───────────┘
                                           │
       ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
       ▼                   ▼                               ▼                   ▼
L0: OS Native (0.37ms) L1: Windows UIA (10ms)  L1.5: RapidOCR (<80ms)  L2: Gemini Vision (2s)
(HWND, DWM Physical)   (Native Control Trees)   (Local Multilingual OCR) (Deep Multimodal)
```

**Files:**
- `actions/screen_processor.py` (L0 OS telemetry, DWM physical crop, fast OCR text extraction, dHash cache)
- `core/computer/windows_uia.py` (L1 Windows UI Automation inspection, STA COM worker)
- `core/computer/ocr_engine.py` (L1.5 RapidOCR CPU ONNX with Urdu/Arabic normalizer)

---

## 4-Tier Perception Ladder

### 1. L0 OS Native Telemetry (0.37ms)
- Direct Windows User32/Kernel32 ctypes query (`GetForegroundWindow`, `IsIconic`, `IsZoomed`).
- Calibrated with `DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS=9)` in `windows_native.py` to eliminate invisible 8px drop-shadow borders (`-8, -8` offset).
- Returns exact active window title, process executable, HWND, and physical screen bounds.

### 2. L1 Windows UI Automation (10ms)
- Inspects the foreground accessibility tree (`pywinauto` / UIAutomation) inside an STA COM worker thread (`searchDepth=6`, `0.8s` timeout).
- Resolves button, text field, and component bounding boxes without taking screenshots or invoking cloud vision.

### 3. L1.5 Local Multilingual RapidOCR (<80ms, 0 MB VRAM)
- Runs lightweight CPU ONNX OCR via `rapidocr_onnxruntime` (~80MB RAM, 0 MB GPU VRAM).
- Strips diacritics/tashkeel and normalizes Urdu/Arabic characters via `normalize_urdu()`.
- Locates spatial text in canvas applications (Figma, Canva, web apps) and extracts screen text in milliseconds.

### 4. L2 Gemini Multimodal Vision (5.0s Timeout Ladder) & Smart Cache (0.0ms Hit)
- 64-bit gradient difference hashing (`compute_dhash`) detects visual frame delta.
- If the screen hash and foreground window are unchanged (Hamming distance <= 2), returns cached observation in **0ms** (`[Cache: 0ms]`), eliminating redundant model calls.
- **5.0s Per-Model Attempt Timeout (`MIN_TIMEOUT_MS = 5000`)**: If a cloud model in the ladder hangs or encounters network latency, it is cancelled at exactly 5.0 seconds and the request cascades down the ladder.
- **Graceful Telemetry Fallback**: If all vision models fail or time out, the engine falls back to deterministic L0 OS native metadata (foreground window title, process executable, and coordinates) without stalling the real-time voice loop.
- Deep multimodal reasoning for graphical icons, color swatches, and complex visual scenes.

---

## Multi-Region Screen Capture
- `full_screen`: Captures primary / combined multi-monitor desktop.
- `active_window`: Automatically crops to the foreground application HWND bounds (saving 60–80% payload size).
- `window_region`: Crops to custom bounding box `(x, y, w, h)`.


```
Gemini calls screen_process tool
    ↓
_execute_tool() handles it
    ↓
self._vision_busy = True  # Cooldown guard (4s)
    ↓
img_b, mime_t = await loop.run_in_executor(None, _capture_screen)
    ↓
self._pending_vision = (img_b, mime_t, user_text, angle)
    ↓
Result returned: "[VISION_ACTIVE] Screen captured and attached to this exchange."
    ↓
Image is attached to the SAME exchange (not a separate turn)
    ↓
Gemini sees the image and responds
    ↓
One turn, one answer (no double-answering)
```

**Key fix**: Previously the image arrived as a separate turn, causing the model to answer before seeing the image (improvising) and then again after. Now the image is attached to the same exchange.

### Image Labels/Source Metadata

Images carry their **source** metadata:
- **Webcam frame**: Shows the USER and their room
- **Screen capture**: Shows their COMPUTER
- The system prompt explicitly states: "Never read a screen capture as a photo of the user"

### Camera Lifecycle

```
screen_process with angle="camera"
    ↓
self._vision_cam_active = True
    ↓
ui.start_camera_stream()  # Live view stays open
    ↓
Next turn_complete
    ↓
_close_camera if _vision_close_pending
    ↓
ui.stop_camera_stream()
```

## Vision Constraints

| Constraint | Value |
|------------|-------|
| Max resolution | 1280x720 |
| Format | JPEG |
| Quality | 82 |
| Cooldown | 4 seconds between calls |
| Concurrency | One vision cycle at a time |
| Labeling | Source metadata attached |
| Mode | On-demand only (not continuous) |

## How Vision Requests Are Triggered

1. **User voice**: "Look at my screen" → Gemini calls screen_process
2. **User text**: Same via typed command
3. **Gemini decides**: Tool description tells the model when to call it

## Vision in the System Prompt

```python
# limits section includes:
if has_vision:
    "- Your sight is not continuous. You see nothing until you call a vision tool..."
else:
    "- You have no sight at all in this build."
```

## Camera Controls

**Inline tool** (`main.py`):
- `screen_process` — capture and attach to exchange
- `close_camera` — close the live camera view

## Summary

```
Capture: mss (screen) + cv2 (webcam)
Resolution: 1280x720 max, JPEG quality 82
Injection: Attached to same exchange (not separate turn)
Labels: Source metadata (USER/room vs COMPUTER)
Cooldown: 4 seconds
Mode: On-demand only
No continuous vision feed
```


### Phase 3-6 Extensions (now live)
- Structured payload: {active_app, window_title, rect, confidence, source, screen_hash, timestamp}
- 5-tier risk: READ_ONLY, LOCAL_MUTATION, EXTERNAL_MUTATION, CODE_EXECUTION, PRIVILEGED_OS + ApprovalGrant 60s TTL
- ToolExecutionContext + Monotonic TaskState CREATED->QUEUED->RUNNING->CANCELLING->DONE/FAILED/CANCELLED (1011 keepalive fix)
- McpClientRuntime isolated worker loop (24ms)
