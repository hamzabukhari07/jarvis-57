import sys
import os
import py_compile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import io

# Setup workspace path
WORKSPACE_ROOT = r"c:\Users\Hamza Bukhari\Documents\antigravity\zezo latest"
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

class TestUiaOcrIntegration(unittest.TestCase):
    def test_01_layer1_py_compile_all_modified(self):
        """Layer 1: Verify py_compile passes for all core and action modules."""
        files_to_check = [
            os.path.join(WORKSPACE_ROOT, "core", "computer", "ocr_engine.py"),
            os.path.join(WORKSPACE_ROOT, "core", "computer", "windows_uia.py"),
            os.path.join(WORKSPACE_ROOT, "core", "computer", "__init__.py"),
            os.path.join(WORKSPACE_ROOT, "actions", "computer_control.py"),
            os.path.join(WORKSPACE_ROOT, "actions", "screen_processor.py"),
            os.path.join(WORKSPACE_ROOT, "core", "action_loader.py"),
            os.path.join(WORKSPACE_ROOT, "core", "skill_loader.py"),
        ]
        for f in files_to_check:
            py_compile.compile(f, doraise=True)
            print(f"  [Layer 1] py_compile PASSED: {os.path.basename(f)}")

    def test_02_layer1_action_discovery_and_tool_count(self):
        """Layer 1: Verify action loader discovers exactly 24 tools with valid TOOL contract."""
        from core.action_loader import discover_actions
        registry = discover_actions(Path(WORKSPACE_ROOT) / "actions")
        tool_count = len(registry._actions)
        print(f"  [Layer 1] Discovered {tool_count} actions: {sorted(list(registry._actions.keys()))}")
        self.assertEqual(tool_count, 24, f"Expected exactly 24 tools, found {tool_count}")
        for name, rec in registry._actions.items():
            self.assertTrue(rec.valid, f"Action {name} marked invalid: {rec.error}")
            self.assertTrue(callable(rec.handler), f"Action {name} handler is not callable")

    def test_03_layer1_skill_discovery(self):
        """Layer 1: Verify skill loader discovers all skills including figma_helper."""
        from core.skill_loader import SkillRegistry
        registry = SkillRegistry()
        skills = registry._skills
        print(f"  [Layer 1] Discovered {len(skills)} skills: {list(skills.keys())}")
        self.assertIn("figma_helper", skills, "figma_helper skill was not discovered")

    def test_04_layer2_urdu_normalization(self):
        """Layer 2: Verify Urdu text normalization stripping diacritics and unifying variants."""
        from core.computer.ocr_engine import normalize_urdu
        
        # Test diacritics removal (Zer, Zabar, Pesh, Tashdeed)
        with_diacritics = "مِيْرَا نَام"
        without_diacritics = "میرا نام"
        self.assertEqual(normalize_urdu(with_diacritics), normalize_urdu(without_diacritics))
        
        # Test Arabic Yeh / Persian Yeh normalization
        arabic_yeh = "علي"
        urdu_yeh = "علی"
        self.assertEqual(normalize_urdu(arabic_yeh), normalize_urdu(urdu_yeh))

        # Test Arabic Kaf normalization
        arabic_kaf = "كتاب"
        urdu_kaf = "کتاب"
        self.assertEqual(normalize_urdu(arabic_kaf), normalize_urdu(urdu_kaf))
        print("  [Layer 2] Urdu normalization assertions passed.")

    def test_05_layer2_rapidocr_synthetic_image_recognition(self):
        """Layer 2: Verify RapidOCR detects rendered text on synthetic PIL image without VRAM."""
        from core.computer.ocr_engine import ocr_engine
        
        # Create a clean synthetic white image with high contrast text
        img = Image.new("RGB", (600, 300), color="white")
        draw = ImageDraw.Draw(img)
        
        draw.text((50, 50), "Width: 1440", fill="black")
        draw.text((50, 150), "Export Settings", fill="black")
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        # Test finding coordinates
        res_width = ocr_engine.find_text_coordinates("Width", image=img_bytes)
        self.assertIsNotNone(res_width, "RapidOCR failed to find 'Width' text")
        cx = res_width["center_x"]
        cy = res_width["center_y"]
        self.assertTrue(40 <= cx <= 200, f"Expected center_x near 50-150, got {cx}")
        self.assertTrue(40 <= cy <= 100, f"Expected center_y near 50-70, got {cy}")
        print(f"  [Layer 2] RapidOCR found 'Width' at ({cx}, {cy}) in {res_width.get('latency_ms', 0)}ms (0 VRAM)")

        # Test extract_full_text
        full_text = ocr_engine.extract_full_text(image=img_bytes)
        self.assertTrue("Width" in full_text or "1440" in full_text)
        print(f"  [Layer 2] RapidOCR extracted full text: {full_text.strip()!r}")

    def test_06_layer2_screen_processor_ocr_action(self):
        """Layer 2: Verify extract_screen_text in actions/screen_processor.py."""
        from actions.screen_processor import extract_screen_text
        
        img = Image.new("RGB", (500, 200), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "ZEZO Native Perception", fill="black")
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        
        extracted = extract_screen_text(img_bytes=img_bytes)
        self.assertTrue("Native" in extracted or "Perception" in extracted or "ZEZO" in extracted.upper(), f"Extracted: {extracted}")
        print(f"  [Layer 2] screen_processor.extract_screen_text extracted: {extracted!r}")

    def test_07_layer2_windows_uia_worker(self):
        """Layer 2: Verify Windows UIA query runs without crashing or blocking COM."""
        import win32gui
        from core.computer.windows_uia import windows_uia
        hwnd = win32gui.GetForegroundWindow()
        elements = windows_uia.dump_interactive_elements(hwnd, depth=2, max_elements=10)
        self.assertIsInstance(elements, list)
        print(f"  [Layer 2] Windows UIA returned {len(elements)} live interactive elements for foreground HWND {hwnd}.")

    def test_09_layer2_drag_coordinate_resolution(self):
        """Layer 2: Verify drag action properly calculates coordinates from (x, y) and (x1, y1, x2, y2)."""
        from actions.computer_control import computer_control
        # Test drag with only x, y (simulating Gemini passing start coordinates)
        res_xy = computer_control({"action": "drag", "x": 400, "y": 300})
        self.assertIn("Dragged (400,300) -> (1000,700)", res_xy)
        print(f"  [Layer 2] drag single-point fallback output: {res_xy}")

        # Test drag with explicit x1, y1, x2, y2
        res_box = computer_control({"action": "drag", "x1": 200, "y1": 150, "x2": 800, "y2": 550})
        self.assertIn("Dragged (200,150) -> (800,550)", res_box)
        print(f"  [Layer 2] drag explicit box output: {res_box}")

    def test_10_layer2_models_ladder_priority(self):
        """Layer 2: Verify gemini-3-flash-preview leads fast models ladder over flash-lite."""
        from core.models import GEMINI_FAST_MODELS
        self.assertEqual(GEMINI_FAST_MODELS[0], "gemini-3-flash-preview")
        print(f"  [Layer 2] models ladder top priority: {GEMINI_FAST_MODELS[0]}")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUiaOcrIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
