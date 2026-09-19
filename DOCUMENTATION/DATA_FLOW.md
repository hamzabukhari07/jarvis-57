# JARVIS — Data Flow

## Voice Conversation Flow
User -> Mic -> Echo Guard -> Gemini Live -> Transcription + Tools -> Audio -> Speaker.

## Tool Execution
Gemini Tool Call -> _execute_tool() -> inline/action/plugin registry.

## Memory Data Flow
User info -> save_memory -> long_term.json -> format_memory_for_prompt.

## Background Tasks
System Monitor (10s), Background Monitor (30min), Proactive (60s).