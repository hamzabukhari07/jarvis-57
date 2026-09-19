# JARVIS — Vision System

## Overview

JARVIS has **on-demand vision** — it can capture screenshots and webcam images, but only when explicitly requested by the user or through a tool call. Vision is not continuous.

**File:** `actions/screen_processor.py`

## Capture Sources

### Screen Capture

**Library**: `mss` (fast screenshot) + `PIL` (compression)

```python
def _capture_screen() -> tuple[bytes, str]:
    # Uses mss to capture the display
    # Returns (jpeg_bytes, "image/jpeg")
    # Max resolution: 1280x720
    # JPEG quality: 82
```

### Webcam Capture

**Library**: `opencv-python` (cv2)

```python
def _capture_camera() -> tuple[bytes, str]:
    # Uses cv2.VideoCapture(0)
    # Returns (jpeg_bytes, "image/jpeg")
    # Max resolution: 1280x720
```

## How Vision Is Used

### Tool Call: screen_process

```python
# Tool declaration in main.py:
{
    "name": "screen_process",
    "description": "Captures the screen or webcam image...",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "angle": {"type": "STRING", "description": "'screen' or 'camera'"},
            "text": {"type": "STRING", "description": "Question about the image"}
        },
        "required": ["text"]
    }
}
```

### Vision Injection Flow

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