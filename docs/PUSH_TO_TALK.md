# 🎙️ ZEZO — Push-to-Talk Architecture & Real-Time Dictation

> **Project:** ZEZO  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux  
> **Core Hotkey:** Strictly `Ctrl+Alt` (Global Hook on Windows, Window-scoped on macOS/Linux)  
> **Core Architecture:** Real-Time WebSocket Streaming + 0.5s Delayed Turn Commit (Commit `fd7fcfa`)

---

## 🧭 Overview

Push-to-Talk allows the user to hold a global keyboard chord (`Ctrl+Alt`) to open the microphone, stream speech in real time to the Google Gemini Live API, observe live dictation tokens appear in the UI chat thread instantly, and receive an immediate spoken response upon key release with zero trailing hang.

Push-to-Talk is **opt-in** and can be selected as the active interaction mode in the ReUI Settings Hub (`General & Quick Controls`).

---

## ⌨️ Keyboard Shortcut Contract

- **Chord**: Strictly **`Ctrl+Alt`** — the single, only chord.
- **Why `Ctrl+Alt`**: Free in modern desktop environments (Windows, macOS, Linux), avoids spacebar and IME conflicts, and offers ergonomic thumb/pinky access.
- **`Ctrl+Space` is Deliberately NOT Bound**: Windows Input Method Editors (IMEs), IDE completion popups, and active text fields claim `Ctrl+Space`. Advertising it previously created a hotkey that silently did nothing. `core/hotkey.py` polls only `Ctrl+Alt` (`DEFAULT_CHORD`) and Settings strictly documents `CTRL+ALT`.

---

## 🔄 Sequence Diagram: Real-Time Streaming & Delayed Turn Commit

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Hamza)
    participant Hotkey as core/hotkey.py (PushToTalk)
    participant Main as main.py (ZezoLive)
    participant UI as frontend (React Workstation)
    participant Gemini as Google Gemini Live WebSocket

    Note over User,Gemini: User presses and holds Ctrl + Alt
    User->>Hotkey: Key Down (Ctrl + Alt)
    Note over Hotkey: 50ms Brush-Protection Debounce Check
    Hotkey->>Main: _on_ptt(held=True)
    Main->>UI: set_state("LISTENING")
    Main->>Main: Drain stale queues & cancel pending watchdog
    User->>Main: Speaks ("Summarize my latest pull request")
    Main->>Gemini: Stream PCM blobs in real-time (audio/pcm;rate=16000)
    Gemini-->>Main: sc.input_transcription ("Summarize my latest pull request")
    Main-->>UI: stream_transcript("user", text, done=False)
    UI-->>User: Live dictation text appears in chat thread

    Note over User,Gemini: User releases Ctrl + Alt
    User->>Hotkey: Key Up (Release)
    Hotkey->>Main: _on_ptt(held=False)
    Main->>UI: set_state("THINKING")
    Note over Main: Background daemon waits 0.5s (Delayed Turn Commit)
    Main->>Gemini: send_realtime_input(audio_stream_end=True)
    Note over Gemini: Explicit stream end commits user turn instantly
    Gemini-->>Main: sc.turn_complete + server_content.audio (24kHz PCM)
    Main->>UI: set_state("SPEAKING")
    Main-->>UI: stream_transcript("zezo", text, done=False)
    Main->>User: Spoken voice playback via speakers
    Note over Main,UI: Audio playback finishes
    Main->>UI: set_state("IDLE")
```

---

## 🛠️ Implementation Details

**Core Files:**
- `core/hotkey.py` — `PushToTalk` class
- `main.py` — `ZezoLive` orchestrator (`_on_ptt`, `_send_realtime`, `_listen_audio`, `_play_audio`, `_enqueue_out_audio`)

### 1. Platform-Specific Hook (`core/hotkey.py`)

#### Windows: Global Polling Hook
- Uses `ctypes.windll.user32.GetAsyncKeyState` to poll virtual-key codes:
  - `VK_CONTROL = 0x11`
  - `VK_MENU = 0x12` (Alt key)
- Polling frequency: 30 Hz (~33ms interval).
- Debounce: 60ms on press, **0ms delay on release** (instant release notification).
- **Truly Global**: Intercepts input while IDEs, fullscreen games, browsers, or terminal windows are focused.
- **Zero Heavy Dependencies**: Native Win32 API.

#### macOS / Linux: Window-Scoped Fallback
- Bound via UI window key sequence shortcut.
- Reports `scope == "window"` honestly in logs so the user knows window focus is required.

---

### 2. Real-Time Streaming & 0.5s Delayed Turn Commit (Commit `fd7fcfa`)

#### Problem Solved
Earlier implementations suffered from two opposing issues:
1. **Bulk Buffering**: Storing audio in memory and blasting it in a single burst on release overloaded Gemini Live's WebSocket, causing dropped turns or delayed transcripts.
2. **Abrupt VAD Truncation**: Emitting `audio_stream_end` the millisecond the key was released cut off users who paused naturally between sentences or released the key slightly before speaking their last syllable.

#### The Solution (Commit `fd7fcfa`)
1. **Continuous Real-Time Streaming**: While `Ctrl+Alt` is held, mic audio is pushed immediately into `out_queue` and streamed to Gemini Live over WebSocket:
   ```python
   # main.py _listen_audio()
   if self._ptt_enabled and self._ptt_held:
       if not self.ui.muted and not self._phone_active:
           data = indata.tobytes()
           loop.call_soon_threadsafe(
               self._enqueue_out_audio,
               {"data": data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
           )
   ```
2. **50ms Brush-Protection Debounce**: In `_on_ptt(held=True)`, the hotkey timestamp is checked against the last release time:
   ```python
   if self._ptt is not None:
       last_release = self._ptt.last_release_time
       time_since_release = time.monotonic() - last_release if last_release > 0 else 999.0
       if time_since_release < 0.05:
           return  # Ignore accidental brush
   ```
3. **0.5s Delayed Turn Commit**: Upon hotkey release (`_on_ptt(held=False)`), rather than terminating the turn instantly, a detached daemon thread waits 0.5 seconds before signaling stream completion:
   ```python
   def _delayed_stream_end():
       import time as _t
       _t.sleep(0.5)
       if self._loop and self._loop.is_running():
           self._loop.call_soon_threadsafe(
               self._enqueue_out_audio,
               {"audio_stream_end": True}
           )
   threading.Thread(target=_delayed_stream_end, daemon=True).start()
   ```
4. **Ordered WebSocket End Signal**: In `_send_realtime`:
   ```python
   if msg.get("audio_stream_end"):
       try:
           await self.session.send_realtime_input(audio_stream_end=True)
       except Exception:
           pass
       continue
   ```
   Because `out_queue` is strictly FIFO, all user speech chunks reach Gemini Live before `audio_stream_end=True` triggers server turn finalization.

---

### 3. Live Dictation & Assistant Output Deferral

1. **Real-time Chat Transcription**:
   - As speech chunks reach Gemini Live, server content delivers `sc.input_transcription`.
   - `main.py` dispatches `self.ui.stream_transcript("user", accumulated_in, done=False)` to the frontend.
   - User speech renders live in the chat thread like real-time dictation.
2. **Speaker Playback Deferral**:
   - While the chord is down, `_play_audio` **defers** playback instead of discarding it:
     ```python
     if self._defer_playback():
         while self._defer_playback() and not self._interrupted:
             await asyncio.sleep(0.05)
     ```
   - **Defer, never discard.** Gemini server VAD can commit a turn before the hotkey is released. Discarding playback would silence legitimate answers.
3. **Instant Barge-in**:
   - If the assistant is actively speaking when `Ctrl+Alt` is pressed, `_on_ptt(held=True)` calls `interrupt()` immediately, stopping speaker audio, draining queues, and switching directly to `LISTENING`.

---

### 4. Resting State Transitions

| Action / Event | Assistant State | UI Indicator |
|---|---|---|
| `Ctrl+Alt` held down | `LISTENING` | Cyan waveform pulsing |
| `Ctrl+Alt` released (awaiting reply) | `THINKING` | Amber shimmer animation |
| Assistant replying with audio | `SPEAKING` | Viseme-driven avatar mouth movement |
| Turn complete & playback finished | `IDLE` | Static resting state |

---

### 5. Unified Interaction Modes (UI Selector)

In the ReUI Settings Hub (`General & Quick Controls`), interaction modes are configured via a 3-Card Segmented Selector:

| Mode | Visual Tag | Behavior & Resting State | Underlying Backend Flags |
|---|---|---|---|
| **Always Listening** | `OPEN MIC` | Continuous open mic. Gemini Live server VAD handles back-and-forth turns. | `wake_word_enabled: false`, `push_to_talk_enabled: false` |
| **Wake Word** | `HANDS-FREE` | Standby (`IDLE`). Saying *"Hey Zezo"* wakes mic for 15s active window. | `wake_word_enabled: true`, `push_to_talk_enabled: false` |
| **Push-To-Talk** | `CTRL+ALT` | Standby (`IDLE`). Key-held dictation via `Ctrl+Alt`. Immediate reply upon release. | `wake_word_enabled: false`, `push_to_talk_enabled: true` |

---

### 6. Configuration Parameters

| Setting | JSON Key | Default | Source |
|---|---|---|---|
| Push-to-Talk Enabled | `push_to_talk_enabled` | `false` | `config/api_keys.json` |
| Wake Word Enabled | `wake_word_enabled` | `false` | `config/api_keys.json` |
| Hotkey Scope | Dynamic (`"global"` / `"window"`) | `"global"` | `PushToTalk.start()` |
