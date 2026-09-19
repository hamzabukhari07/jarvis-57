# JARVIS — Backend Overview

## Main Loop (main.py)
Central orchestrator managing: Gemini Live session lifecycle, audio streams, tool dispatch, viseme extraction, background tasks, and dashboard.

## Audio Processing
Microphone Capture: sounddevice.InputStream at 16kHz
Echo Guard: Self-calibrating echo cancellation
Viseme Pipeline: 50 mouth shapes/second from audio formants
Speaker Output: sounddevice.RawOutputStream at 24kHz

## Tool System
All tools self-describing and auto-discovered: inline tools, action tools (24+ built-in), plugin tools.

## Memory System
Persistent storage in memory/long_term.json with categorized memory and on-demand recall.