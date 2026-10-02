import sys
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath("."))
from core.computer.ocr_engine import OCREngine

def test_roi_crop_speed():
    engine = OCREngine()
    assert engine.is_available, "RapidOCR not installed"
    
    # Create a 1920x1080 synthetic desktop image with a sidebar on the right
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # Left canvas: some noisy lines and shapes
    for i in range(20):
        draw.text((100, 50 + i * 40), f"Random canvas text layer {i}", fill=(180, 180, 180))
    
    # Right sidebar (x: 1500 to 1920)
    draw.rectangle([1500, 0, 1920, 1080], fill=(45, 45, 45))
    draw.text((1530, 100), "Properties", fill=(255, 255, 255))
    draw.text((1530, 200), "Width", fill=(255, 255, 255))
    draw.text((1650, 200), "400", fill=(200, 200, 200))
    draw.text((1530, 300), "Height", fill=(255, 255, 255))
    draw.text((1650, 300), "400", fill=(200, 200, 200))
    draw.text((1530, 400), "Fill", fill=(255, 255, 255))
    
    # Warmup
    engine.extract_text_boxes(img, region=(1500, 0, 420, 1080))
    
    # 1. Full Screen OCR Benchmark
    t0 = time.perf_counter()
    full_boxes = engine.extract_text_boxes(img, region=None)
    full_time = (time.perf_counter() - t0) * 1000
    print(f"Full Screen Scan: {full_time:.1f}ms ({len(full_boxes)} boxes found)")
    
    # 2. ROI Cropped Sidebar Scan (Width / Height)
    t0 = time.perf_counter()
    res_w = engine.find_text_coordinates("Width", img=img, region=(1500, 0, 420, 1080))
    roi_time_w = (time.perf_counter() - t0) * 1000
    print(f"ROI Cropped Scan for 'Width': {roi_time_w:.1f}ms -> {res_w}")
    assert res_w is not None, "Failed to find Width in ROI"
    assert res_w["center_x"] >= 1500, f"Expected x >= 1500, got {res_w['center_x']}"
    
    t0 = time.perf_counter()
    res_h = engine.find_text_coordinates("Height", img=img, region=(1500, 0, 420, 1080))
    roi_time_h = (time.perf_counter() - t0) * 1000
    print(f"ROI Cropped Scan for 'Height': {roi_time_h:.1f}ms -> {res_h}")
    assert res_h is not None, "Failed to find Height in ROI"
    assert res_h["center_x"] >= 1500, f"Expected x >= 1500, got {res_h['center_x']}"
    
    print("\n[PASS] ROI Auto-Cropping Benchmark Passed Successfully!")

if __name__ == "__main__":
    test_roi_crop_speed()
