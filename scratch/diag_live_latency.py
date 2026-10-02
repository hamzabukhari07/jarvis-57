"""
End-to-end latency probe for Gemini Live turn-taking.

Streams a fixed speech WAV into the Live session exactly like main.py
(16 kHz, 1024-frame chunks, ~64 ms pacing), then sends trailing silence.
Measures: end-of-speech -> first response byte.

Runs the SAME audio twice: once with main.py's tuned turn config, once with
Gemini's server default (no realtime_input_config). If the tuned run is not
faster, the model is ignoring the tuning knob.
"""
from __future__ import annotations
import asyncio
import json
import pathlib
import sys
import time
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from google import genai
from google.genai import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "models/gemini-3.1-live-2.5-flash-preview"  # placeholder, replaced below
MODEL = "models/gemini-3.1-flash-live-preview"
WAV = ROOT / "scratch" / "diag_speech.wav"
API_KEY = json.loads((ROOT / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key", "").strip()

FRAME = 1024          # frames
BYTES = FRAME * 2     # int16 mono
CHUNK_S = FRAME / 16000.0


def load_pcm() -> bytes:
    with wave.open(str(WAV), "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == 16000, \
            f"unexpected wav format: {w.getnchannels()}ch {w.getsampwidth()}B {w.getframerate()}Hz"
        return w.readframes(w.getnframes())


def base_kwargs():
    return dict(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="You are a helpful assistant. Answer briefly.",
        tools=[{"function_declarations": []}],
    )


def tuned_cfg():
    detect = types.AutomaticActivityDetection(silence_duration_ms=450, prefix_padding_ms=100)
    detect.end_of_speech_sensitivity = types.EndSensitivity.END_SENSITIVITY_HIGH
    return dict(base_kwargs(), realtime_input_config=types.RealtimeInputConfig(automatic_activity_detection=detect))


async def run_case(name: str, kwargs: dict, mime: str) -> None:
    pcm = load_pcm()
    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})
    result: dict = {"first_resp": None, "turn_complete": None, "events": []}
    t_end_speech = None

    try:
        async with client.aio.live.connect(model=MODEL, config=types.LiveConnectConfig(**kwargs)) as session:
            done = asyncio.Event()

            async def receiver():
                async for response in session.receive():
                    sc = getattr(response, "server_content", None)
                    got = False
                    if getattr(response, "data", None):
                        got = True
                    if sc and sc.output_transcription and sc.output_transcription.text:
                        got = True
                    if got and result["first_resp"] is None and t_end_speech is not None:
                        result["first_resp"] = time.monotonic() - t_end_speech
                    if sc and sc.turn_complete:
                        result["turn_complete"] = time.monotonic() - (t_end_speech or time.monotonic())
                        done.set()
                        return

            async def sender():
                nonlocal t_end_speech
                # Speech
                for i in range(0, len(pcm) - BYTES + 1, BYTES):
                    await session.send_realtime_input(audio=types.Blob(
                        data=pcm[i:i + BYTES], mime_type=mime))
                    await asyncio.sleep(CHUNK_S)
                t_end_speech = time.monotonic()
                # Trailing silence so server VAD can register end-of-speech
                silence = b"\x00" * BYTES
                for _ in range(int(2.0 / CHUNK_S)):
                    try:
                        await session.send_realtime_input(audio=types.Blob(
                            data=silence, mime_type=mime))
                    except Exception:
                        break
                    await asyncio.sleep(CHUNK_S)

            r_task = asyncio.create_task(receiver())
            s_task = asyncio.create_task(sender())
            try:
                await asyncio.wait_for(done.wait(), timeout=25)
            except asyncio.TimeoutError:
                pass
            s_task.cancel()
            r_task.cancel()
            await asyncio.gather(s_task, r_task, return_exceptions=True)

        fr = result["first_resp"]
        if fr is not None:
            print(f"  {name:26} first_response_after_speech = {fr*1000:.0f} ms")
        else:
            print(f"  {name:26} first_response = NONE (model never answered)")
        if result["turn_complete"] is not None:
            print(f"  {'':26} turn_complete                = {result['turn_complete']*1000:.0f} ms")
    except Exception as e:
        print(f"  {name:26} ERROR: {type(e).__name__}: {str(e)[:200]}")


async def main() -> None:
    if not API_KEY:
        print("no api key")
        return
    pcm = load_pcm()
    print(f"Audio: {WAV.name} ({len(pcm)/32000:.2f}s of speech)\n")
    print("Measuring end-of-speech -> first response (v1alpha):\n")
    await run_case("tuned + rate=16000", tuned_cfg(), "audio/pcm;rate=16000")
    await asyncio.sleep(2)
    await run_case("tuned + bare audio/pcm", tuned_cfg(), "audio/pcm")
    await asyncio.sleep(2)
    await run_case("default + bare audio/pcm", base_kwargs(), "audio/pcm")


if __name__ == "__main__":
    asyncio.run(main())
