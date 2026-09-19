# JARVIS — Project Overview

> **JARVIS** — The Ultimate Cross-Platform Personal AI Assistant
> By Hamza Bukhari | License: CC BY-NC 4.0

## What Is JARVIS?
JARVIS is a real-time voice AI assistant that transforms any computer into an intelligent conversational partner. It listens through your microphone, thinks through Google Gemini Live API, and speaks back through your speakers with zero latency.

The application features a holographic 3D avatar rendered entirely in software with real-time lip-sync.

## Key Features
| Category | Features |
|----------|----------|
| Voice | Real-time Gemini Live, push-to-talk, wake word, auto-sleep |
| Vision | Screen capture, webcam vision, image analysis |
| System Control | Launch apps, volume/brightness, WiFi, keyboard shortcuts |
| Files | Read, write, move, rename, organize |
| Web | Search, browse, YouTube, flight finder |
| Communication | Messages, reminders |
| Memory | Persistent memory with recall, session summaries |
| Monitoring | CPU/RAM/GPU telemetry, background monitoring |
| Remote | Phone dashboard via QR code, file sharing |
| Plugins | Drop-in .py files for custom skills |
| Avatar | Holographic head with lip-sync and expressions |
| Undo | Reverse any file or setting change |
| Multi-Language | Any language, automatic detection |

## Technical Foundation
| Layer | Technology |
|-------|-----------|
| Language | Python 3.11-3.13 |
| UI | PyQt6 |
| AI | Gemini Live API |
| Audio | sounddevice |
| Avatar | QPainter + numpy |
| Wake Word | openwakeword |
| TTS | EdgeTTS/Kokoro/ElevenLabs |
| STT | Whisper/Vosk |
| Dashboard | FastAPI + uvicorn |

## Getting Started
```bash
git clone https://github.com/HamzaBukhari/JARVIS.git
cd JARVIS
python setup.py
python main.py
```

## Philosophy
1. Act immediately — push reversible actions to undo stack
2. Know your limits — state what you cannot do
3. Stay in the background — invisible when not needed
4. Own your data — everything on your machine