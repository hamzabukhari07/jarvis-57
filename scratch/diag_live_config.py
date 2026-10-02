"""
Diagnostic: does the Live server accept the tuned turn-taking config?

Simulates the exact fields main.py._build_config() sends and reports whether
each one is accepted, isolated, so we can see WHICH field (if any) is being
rejected -- because main.py disables ALL tuning when any single field fails.

Read-only: connects, then closes. Sends no audio and generates no content.
"""
from __future__ import annotations
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import types

MODEL = "models/gemini-3.1-flash-live-preview"
CFG = pathlib.Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
API_KEY = json.loads(CFG.read_text(encoding="utf-8")).get("gemini_api_key", "").strip()


def base_kwargs():
    return dict(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="diagnostic",
    )


def realtime_tuned():
    detect = types.AutomaticActivityDetection(
        silence_duration_ms=450,
        prefix_padding_ms=100,
    )
    detect.end_of_speech_sensitivity = types.EndSensitivity.END_SENSITIVITY_HIGH
    return types.RealtimeInputConfig(automatic_activity_detection=detect)


CASES = {
    "A_minimal":            dict(base_kwargs()),
    "B_realtime_only":      dict(base_kwargs(), realtime_input_config=realtime_tuned()),
    "C_realtime+media":     dict(base_kwargs(), realtime_input_config=realtime_tuned(),
                                 media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM),
    "D_full_tuned":         dict(base_kwargs(), realtime_input_config=realtime_tuned(),
                                 media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
                                 session_resumption=types.SessionResumptionConfig(handle=None),
                                 context_window_compression=types.ContextWindowCompressionConfig(
                                     sliding_window=types.SlidingWindow())),
}

VERSIONS = ["v1alpha", "v1beta"]


async def probe(api_version: str, name: str, kwargs: dict) -> str:
    client = genai.Client(api_key=API_KEY, http_options={"api_version": api_version})
    try:
        async with client.aio.live.connect(model=MODEL, config=types.LiveConnectConfig(**kwargs)):
            return f"PASS"
    except Exception as e:
        return f"FAIL: {type(e).__name__}: {str(e)[:220]}"


async def main() -> None:
    if not API_KEY:
        print("No gemini_api_key in config/api_keys.json")
        return
    for ver in VERSIONS:
        print(f"\n=== api_version={ver} ===")
        for name, kw in CASES.items():
            try:
                res = await asyncio.wait_for(probe(ver, name, kw), timeout=30)
            except asyncio.TimeoutError:
                res = "FAIL: timeout after 30s"
            print(f"  {name:18} -> {res}")


if __name__ == "__main__":
    asyncio.run(main())
