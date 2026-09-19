# JARVIS — System Design

## Architecture
JARVIS follows a modular, event-driven architecture built around a central asyncio event loop.

### Core Components
- Event Loop: Python asyncio manages all concurrent operations
- Audio Pipeline: Real-time mic input and speaker output via sounddevice
- AI Engine: Google Gemini Live API for zero-latency voice conversation
- UI Framework: PyQt6 HUD with holographic avatar
- Dashboard: FastAPI server for phone remote control

## Audio Pipeline
Two parallel streams: Input (16kHz mic) and Output (24kHz speakers), both via sounddevice with configurable device selection.

## AI Engine
Gemini Live API provides real-time conversation with session resumption, sliding window compression, and tool calling.

## State Management
Conversation history, long_term.json memory, audio levels, viseme data, session metadata.

## Concurrency Model
Asyncio for core loop, threading for blocking I/O, sounddevice callbacks for audio, separate loop for dashboard.