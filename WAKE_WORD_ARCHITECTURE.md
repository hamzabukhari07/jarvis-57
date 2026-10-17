# Wake Word Feature — Full Pipeline & Architecture

> Analysis of how Bigfoot hears its name ("Hey Bigfoot") and starts listening hands-free.
> App: **Bigfoot** (Electron app, Windows). Wake-word spotting is done by a **native C# helper**, and the actual speech-to-text is done by **Whisper (whisper.cpp)**.

---

## 1. TL;DR

- The wake word is **`"Hey <assistantName>"`**. `assistantName` is a **user setting**, default **`"Bigfoot"`**.
- There are **no hardcoded extra names / aliases** in the wake detector. The detector is given **one name** (the user's chosen assistant name) and it automatically accepts **4 spoken variants** of it.
- Detection happens **offline** in **`input-helper.exe`** using the **Windows `System.Speech` recognizer** with a small keyword grammar and a confidence threshold of **0.72**.
- After the wake word fires, the **main process** starts recording, then **Whisper** (also bundled, offline) transcribes the command, and the normal intent/agent flow runs.

---

## 2. Which names does it listen for? ("kon kon sy names")

The wake detector is **dynamic**: the name comes from the setting `assistantName`, not from a fixed list.

### 2.1 The single name source
| Where | Detail |
|---|---|
| Default | `assistantName: 'Bigfoot'` (`src/main/settings.js`) |
| User picks in onboarding | Suggestions: `['Bigfoot', 'Nova', 'Sage', 'Pixel', 'Milo', 'Echo', 'Juno', 'Atlas']` (`src/renderer/onboarding.js`) |
| Also changeable in Settings | `assistantName` setting, validated by `cleanName()` |
| Allowed name characters | letters, spaces, apostrophes, hyphens; **2–24 chars** (`settings.js → cleanName`) |

### 2.2 The variants the detector actually accepts
In `src/main/native/InputHelper.cs → Speech.StartWake(namesCsv)`, for **each** name it receives, it builds these phrases:

```
"hey "  + name
"hi "   + name
"okay " + name
         name          (bare name, no greeting)
```

So for the default name **Bigfoot** the recognizer listens for:

> **"hey bigfoot", "hi bigfoot", "okay bigfoot", "bigfoot"**

If the user renames the assistant to e.g. **Nova**, the same 4 forms apply: **"hey nova", "hi nova", "okay nova", "nova"**.

### 2.3 Important note about "different names"
- The native API (`input.wake(names)`) **technically supports multiple names** — it receives a comma-separated list (`namesCsv`) and builds 4 phrases for each.
- **But the controller always passes only one name**: `this.input.wake([this.name])` (`src/main/controller.js`). So in practice **only one wake name is active** at a time — the assistant name.
- The only other place a name is "known" is `src/main/intents.js → core()`, which strips a **hardcoded** `"hey/hi/okay bigfoot"` / `"big foot"` prefix from the transcript text (text cleanup only — not detection). This does **not** follow a renamed assistant.

---

## 3. Components used ("kon kon si chizy use ki ha")

| Layer | Technology | File(s) |
|---|---|---|
| Wake-word spotting (keyword detection) | **Windows `System.Speech.Recognition.SpeechRecognitionEngine`** (grammar + confidence) | `src/main/native/InputHelper.cs` (class `Speech`) → compiled to `src/main/native/input-helper.exe` |
| Native helper client (IPC over stdin/stdout) | Node `child_process` + line protocol | `src/main/input.js` |
| Orchestration / state machine | Main-process controller | `src/main/controller.js` |
| Microphone capture + VAD | Renderer hidden "engine" window: `getUserMedia`, AudioContext, ScriptProcessor, WAV encoder | `src/renderer/engine.js` |
| Recording service broker | IPC main↔engine window | `src/main/audio.js` |
| Speech-to-text (the command) | **whisper.cpp `whisper-server.exe`** (offline, local HTTP server) | `src/main/local/speech.js` + `src/main/local/catalog.js` |
| Settings / persistence | JSON settings + `safeStorage` for secrets | `src/main/settings.js` |
| Wiring (events, lifecycle) | Electron main | `src/main/main.js` |
| Settings UI toggle + status | | `src/renderer/app.js`, `src/main/ipc.js`, `src/main/tray.js` |
| Transcript intent cleanup | Regex | `src/main/intents.js` |

---

## 4. Full Pipeline (step by step)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 0. SETUP                                                                     │
│    settings.assistantName = "Bigfoot"   (default)                            │
│    settings.wakeWord      = true        (default)                            │
│    settings.onboarded     = true                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. ARM THE WAKE WORD   controller.refreshWakeWord()                          │
│    want = wakeWord && onboarded                                              │
│    if want:  input.wake([this.name])   → base64("Bigfoot")                   │
│    emits activity: Listening for “Hey Bigfoot” (en-US).                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │  (stdin: "12|wake|<base64 names>")
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. NATIVE DETECTOR  input-helper.exe  →  Speech.StartWake(namesCsv)          │
│    • build phrases: hey/hi/okay + name, and bare name                        │
│    • SpeechRecognitionEngine (en-US)  ← default audio device                 │
│    • load grammar "wake" (Choices of phrases)                                │
│    • load grammar "garbage" (AppendWildcard) as competitor                   │
│    • RecognizeAsync(Multiple), event SpeechRecognized:                       │
│         if grammar=="wake" && Confidence >= 0.72 → emit "!|wake|0.xx"        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │  (stdout: "!|wake|0.86")
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. NODE CLIENT  input.js  (readline on stdout)                               │
│    id === '!' && status === 'wake' → this.emit('wake', confidence)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. MAIN WIRING  main.js                                                      │
│    input.on('wake', c => controller.onWake(c))                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. CONTROLLER GATE  onWake(confidence)                                       │
│    • ignore if state !== 'idle' | agent.running | selecting                  │
│    • ignore if wakeWord setting is off                                       │
│    • log: Heard “Bigfoot” (confidence 0.86)                                  │
│    • requireKey()  (license/permission/key check)                            │
│    • startListening('wake')                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. RECORD THE COMMAND  controller.startListening('wake')                     │
│    • audio.startRecording({ vad:true })   → engine window                    │
│    • set state = 'listening', play "listen-start" sound, bubble "yes?"       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. CAPTURE + VAD  renderer/engine.js                                         │
│    • getUserMedia (16 kHz mono, echo cancel, noise suppress, AGC)            │
│    • RMS speech detection (SPEECH_RMS=0.02)                                  │
│    • ends after 1.3 s silence (END_SILENCE_MS)                               │
│    • gives up after 6 s of no speech (NO_SPEECH_MS), max 30 s                │
│    • encodes WAV (44-byte header + 16-bit PCM) → engine:vad event            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │  audio.on('vad') → controller.finishListening()
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. TRANSCRIBE  controller.transcribe(wav) → speech.transcribe()              │
│    • POST WAV to local whisper-server /inference (127.0.0.1:<random port>)   │
│    • temperature=0, prompt=SPEECH_HINT ("Hey Bigfoot, open Chrome …")        │
│    • cleanTranscript(): strip [BLANK_AUDIO]/(music)/*noise*                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 9. ACT ON THE TEXT  controller.runTask(text, 'voice')                        │
│    • intents.js core(): strips a leading "hey/hi/okay bigfoot"               │
│    • fast-intent match, else send to the AI agent; reply is spoken (Kokoro)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Why the native detector has two grammars

`InputHelper.cs` loads **two** grammars into the same recognizer:

1. **`wake`** — `GrammarBuilder(new Choices(phrases))`: only the 4 variants.
2. **`garbage`** — `AppendWildcard()`: a catch-all competitor.

The `garbage` grammar is a *decoy*. Without it, the recognizer would be forced to map **any** speech onto the small wake-word list (everything would look like "bigfoot"). With the competitor loaded, ordinary conversation gets matched to `garbage`, and only a close match to a real wake phrase reaches the `wake` grammar. Then it must also clear **`WakeConfidence = 0.72`**.

---

## 6. Lifecycle, Pausing & Recovery

| Event | Behavior | Code |
|---|---|---|
| App start (onboarded) | `controller.refreshWakeWord()` arms the detector | `main.js` |
| Setting `assistantName` or `wakeWord` changes | `refreshWakeWord()` re-arms with the new name / toggles off | `main.js` `settings.onChange` |
| AI starts working (`processing`/`acting`) | **Wake is paused** (`pauseWakeWord(true)` → `wakeOff()`) to free a CPU core | `controller.js` |
| AI returns to `idle` | Wake is **resumed** (`wake([name])`) | `controller.js` |
| Native helper crashes/exits | After 1.5 s: `refreshWakeWord()` re-arms | `main.js` `input.on('crash')` |
| Tray menu item | Checkbox `Answer to "Hey <name>"` toggles `wakeWord` | `tray.js` |
| `wake:status` IPC | Returns `{ enabled, active }` for the UI | `ipc.js`, `app.js` |

**Arming conditions:** the detector is active only when **`wakeWord === true` AND `onboarded === true`**.

---

## 7. Key constants & thresholds

| Constant | Value | Meaning | File |
|---|---|---|---|
| `WakeConfidence` | `0.72` | Min confidence to accept a wake phrase | `InputHelper.cs` |
| Wake phrases | `hey`, `hi`, `okay`, bare | Prefixes generated per name | `InputHelper.cs` |
| `SPEECH_RMS` | `0.02` | RMS above this = speech | `engine.js` |
| `END_SILENCE_MS` | `1300` | Silence that ends a wake request | `engine.js` |
| `NO_SPEECH_MS` | `6000` | Give up if nobody speaks | `engine.js` |
| `MAX_RECORD_MS` | `30000` | Hard cap on recording | `engine.js` |
| `TARGET_RATE` | `16000` | WAV sample rate fed to Whisper | `engine.js` |
| `SPEECH_HINT` | `"Hey Bigfoot, open Chrome …"` | Whisper priming prompt (biases toward "Bigfoot") | `local/speech.js` |
| `wakeWord` | `true` (default) | Master on/off | `settings.js` |

---

## 8. Files involved (quick map)

| File | Role in the feature |
|---|---|
| `src/main/native/InputHelper.cs` | **Actual wake-word detector** (`Speech` class), compiled to `input-helper.exe` |
| `src/main/input.js` | Node client; `wake(names)`, `wakeOff()`; parses `!|wake|<conf>` |
| `src/main/controller.js` | `refreshWakeWord`, `pauseWakeWord`, `onWake`, `startListening('wake')` |
| `src/main/main.js` | Wires `input.on('wake')`, re-arms on settings change / crash |
| `src/main/settings.js` | `assistantName`, `wakeWord`, `cleanName()` validation |
| `src/main/audio.js` | Brokers record start/stop between main and engine window |
| `src/renderer/engine.js` | Mic capture, VAD, WAV encoding, UI sounds |
| `src/main/local/speech.js` | Whisper.cpp server: transcribe the command |
| `src/main/intents.js` | Strips "hey bigfoot" from the transcript |
| `src/main/ipc.js`, `src/renderer/app.js`, `src/renderer/tray.js` | UI toggle + status |
| `src/renderer/onboarding.js` | Name picker (`NAME_IDEAS`) |

---

## 9. Summary answer to the questions

- **How does it hear different names?** It does not keep a list of names. It reads the **single `assistantName`** setting and asks the Windows recognizer to listen for **`hey/hi/okay + name`** and the **bare name**. Change the name → the 4 phrases change automatically.
- **Which names are "added"?** Only the greeting-prefix variants (`hey`, `hi`, `okay`) plus the bare name. There are **no extra hardcoded aliases** for the wake word. (A hardcoded "bigfoot" only appears later, in `intents.js`, purely to clean the transcribed text.)
- **What powers detection?** Windows **`System.Speech`** grammar recognizer in the **native C# helper** (offline).
- **What powers understanding the command?** **Whisper (whisper.cpp)**, bundled offline, invoked through the audio engine's WAV recording.
