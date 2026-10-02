"""
core/computer/__init__.py - Modular Computer Driver Layer for ZEZO OS
Exports unified Win32 native, Windows UIA, and hardware input drivers.
Creator: Hamza Bukhari
"""
from core.computer.windows_native import WindowsNativeDriver, windows_native
from core.computer.windows_uia import WindowsUIADriver, windows_uia
from core.computer.pyautogui_driver import InputDriver, input_driver
from core.computer.ocr_engine import OCREngine, ocr_engine, normalize_urdu

__all__ = [
    "WindowsNativeDriver",
    "windows_native",
    "WindowsUIADriver",
    "windows_uia",
    "InputDriver",
    "input_driver",
    "OCREngine",
    "ocr_engine",
    "normalize_urdu",
]
