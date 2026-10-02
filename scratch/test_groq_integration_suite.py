"""
scratch/test_groq_integration_suite.py - Verification for Groq Integration:
1. Tool Calling & Decision JSON via Groq
2. L1.5 OCR Visual-Spatial Text Reasoning
3. Code Generation Speed and Precision
Lead Architect: Hamza Bukhari
"""
import json
import time
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.llm_client import call_groq_text, call_groq_json
from core.gemini import text, as_json
from core.computer.ocr_engine import ocr_engine
from core.llm_router import generate_text


def test_1_groq_json_decision():
    """Test fast JSON structured decision making on Groq."""
    t0 = time.perf_counter()
    prompt = "Convert user instruction 'Click the submit button and then save the document' into structured actions"
    system = "Return JSON ONLY: {\"actions\": [{\"action\": \"click\", \"target\": \"submit\"}, {\"action\": \"hotkey\", \"keys\": \"ctrl+s\"}]}"
    
    res = call_groq_json(prompt, system=system)
    latency = (time.perf_counter() - t0) * 1000
    print(f"✅ Test 1 (Groq JSON Decision) in {latency:.1f}ms: {res}")
    assert isinstance(res, dict)
    assert "actions" in res
    assert len(res["actions"]) >= 1


def test_2_groq_ocr_spatial_reasoning():
    """Test L1.5 OCR visual-spatial text reasoning on synthetic screen bounding boxes."""
    t0 = time.perf_counter()
    synthetic_boxes = [
        {"text": "File", "center_x": 30, "center_y": 15, "rect": {"x": 10, "y": 5, "width": 40, "height": 20}},
        {"text": "Edit", "center_x": 80, "center_y": 15, "rect": {"x": 60, "y": 5, "width": 40, "height": 20}},
        {"text": "Search or type a URL", "center_x": 400, "center_y": 45, "rect": {"x": 200, "y": 35, "width": 400, "height": 25}},
        {"text": "Save As...", "center_x": 90, "center_y": 110, "rect": {"x": 20, "y": 100, "width": 140, "height": 20}},
        {"text": "Close Window", "center_x": 90, "center_y": 140, "rect": {"x": 20, "y": 130, "width": 140, "height": 20}},
    ]
    
    # Query with natural spatial / semantic phrasing
    match = ocr_engine._groq_spatial_match("I want to save my file with a new name", synthetic_boxes)
    latency = (time.perf_counter() - t0) * 1000
    print(f"✅ Test 2 (Groq L1.5 OCR Spatial Reasoning) in {latency:.1f}ms: Matched '{match.get('text')}' at ({match.get('center_x')}, {match.get('center_y')})")
    assert match is not None
    assert "Save" in match.get("text", "")


def test_3_groq_code_generation():
    """Test ultra-fast code generation on Groq LPU."""
    t0 = time.perf_counter()
    prompt = "Write a python function `fibonacci(n: int) -> list[int]` that returns the first n Fibonacci numbers."
    system = "Return valid Python code only with docstring and type hints."
    
    code = generate_text(prompt, system=system, tier="smart", timeout_ms=30_000)
    latency = (time.perf_counter() - t0) * 1000
    print(f"✅ Test 3 (Groq Code Generation) in {latency:.1f}ms:\n{code[:180]}...\n")
    assert "def fibonacci" in code
    assert latency < 10000  # Sub-10s (usually < 1.5s on Groq)


if __name__ == "__main__":
    print("🚀 Starting Groq Integration Verification Suite...\n")
    test_1_groq_json_decision()
    test_2_groq_ocr_spatial_reasoning()
    test_3_groq_code_generation()
    print("🎉 ALL 3 GROQ INTEGRATION TESTS PASSED SUCCESSFULLY!")
