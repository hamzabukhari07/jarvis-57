import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from google import genai
from google.genai import types
from pathlib import Path
from core.action_loader import discover_actions

async def test_all_tools():
    with open("config/api_keys.json") as f:
        keys = json.load(f)
    api_key = keys["gemini_api_key"]
    client = genai.Client(api_key=api_key)
    
    registry = discover_actions(Path("actions"), logger=lambda s: None)
    decls = registry.get_tool_declarations()
    print(f"Loaded {len(decls)} tool declarations.")
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        tools=[{"function_declarations": decls}],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
        session_resumption=types.SessionResumptionConfig(handle=None),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow()
        ),
    )
    
    model = "models/gemini-3.1-flash-live-preview"
    print(f"Connecting to {model}...")
    async with client.aio.live.connect(model=model, config=config) as session:
        print("Connected! Asking to open Notepad...")
        await session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": "Open notepad now please"}]}],
            turn_complete=True
        )
        async for resp in session.receive():
            if resp.tool_call:
                print(f"Received tool call: {resp.tool_call}")
                fn_responses = []
                for fc in resp.tool_call.function_calls:
                    print(f"Tool call: {fc.name} (id={fc.id})")
                    sched = registry.scheduling(fc.name)
                    extra = {"scheduling": sched} if sched else {}
                    print(f"Scheduling extra: {extra}")
                    fr = types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={"result": "Opened Notepad successfully (Focused)."},
                        **extra
                    )
                    fn_responses.append(fr)
                print(f"Sending tool response: {fn_responses}")
                await session.send_tool_response(function_responses=fn_responses)
                print("Tool response sent successfully!")
            sc = getattr(resp, "server_content", None)
            if sc and sc.output_transcription:
                print(f"AI text: {sc.output_transcription.text}")
            if sc and sc.turn_complete:
                print("Turn complete after tool response!")
                break

if __name__ == "__main__":
    asyncio.run(test_all_tools())
