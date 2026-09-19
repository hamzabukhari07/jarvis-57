# JARVIS — Core Modules

## llm_client.py
Local LLM client for Ollama/OpenAI-compatible servers with automatic model ladder.

## gemini.py
One-shot Gemini calls with model ladder (Live primary, REST fallback), quota circuit breaker.

## wake_word.py
Local Hey Jarvis detection via openwakeword, zero cost when disabled.

## tts.py
Text-to-Speech: EdgeTTS, Kokoro (offline), ElevenLabs. Producer/consumer pipeline.

## stt.py
Speech-to-Text: Whisper (faster-whisper) and Vosk.

## audio_devices.py
Smart device management: filtered list, measured transport, name-based storage.

## viseme.py
Lip-sync: 13 viseme classes, text-to-viseme mapping, audio-text fusion.

## echo.py
Self-echo guard: band energy comparison, learned gain, auto-calibration.

## confirm.py
Irreversible action gate: token from UI, not model.

## undo.py
Shared undo stack: max 10 entries, thread-safe, zero runtime cost.