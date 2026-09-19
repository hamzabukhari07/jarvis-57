# JARVIS — Media Pipeline

## Audio Input Pipeline
Microphone -> sounddevice callback -> echo check -> Gemini Live API.

## Audio Output Pipeline
Gemini Live API -> audio_in_queue -> _play_audio() -> sounddevice.RawOutputStream -> Speakers.

## Viseme Extraction
Per 20ms audio slice: FFT analysis, formant energy, openness and width, fricative detection.

## Camera and Screen Capture
OpenCV + MSS. Compressed. Sent to Gemini via inline_data. Labeled by source.