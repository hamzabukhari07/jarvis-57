# JARVIS — Diagrams

## 1. High-Level Architecture

```mermaid
flowchart TD
    User["👤 User"] -->|voice| Mic["🎤 Microphone"]
    User -->|keyboard| UI["⌨️ UI"]
    Mic -->|audio| Wake["Wake Word Detector"]
    Wake -->|"Hey Jarvis"| Awake["Awake State"]
    Awake -->|stream| Gemini["🧠 Gemini Live API"]
    UI -->|text| Gemini
    Gemini -->|transcript| LLM["LLM Reasoning"]
    LLM -->|tool call| Tools["🔧 Tools"]
    Tools -->|execution| OS["🖥️ OS"]
    Tools -->|save| Memory["🧠 Memory"]
    LLM -->|response| TTS["🔊 TTS"]
    TTS -->|audio| Speakers["🔈 Speakers"]
    TTS -->|text| Avatar["🎨 Avatar"]
    Avatar -->|animation| HUD["🖥️ HUD"]
    UI -->|settings| Config["⚙️ Config"]
    UI -->|remote| Dashboard["📱 Dashboard"]
```

## 2. Startup Sequence

```mermaid
sequenceDiagram
    participant Python
    participant Main as main.py
    participant JarvisLive as JarvisLive
    participant ActionLoader
    participant PluginLoader
    participant WakeWord
    participant UI as ui.py
    
    Python->>Main: Execute main.py
    Main->>Main: Patch subprocess, configure console
    Main->>JarvisLive: Create JarvisLive(ui)
    JarvisLive->>ActionLoader: discover_actions()
    ActionLoader-->>JarvisLive: ActionRegistry
    JarvisLive->>PluginLoader: discover_plugins()
    PluginLoader-->>JarvisLive: PluginRegistry
    alt Wake word enabled
        JarvisLive->>WakeWord: Create WakeWordDetector
        WakeWord-->>JarvisLive: Ready
    end
    JarvisLive->>UI: Create JarvisUI()
    UI-->>JarvisLive: Window ready
    JarvisLive->>Python: Enter event loops
    Python-->>User: Application ready
```

## 3. Voice Pipeline

```mermaid
flowchart LR
    A["User speaks"] --> B["Microphone"]
    B --> C["Audio Callback"]
    C --> D{Wake Word Gate}
    D -->|sleeping| E["Feed openwakeword"]
    D -->|awake| F["Speaking Lock"]
    F -->|JARVIS speaking| G["Drop audio"]
    F -->|user speaking| H["Echo Guard"]
    H -->|echo| G
    H -->|user voice| I["Push-to-Talk Gate"]
    I -->|not held| G
    I -->|held| J["Stream to Gemini"]
    J --> K["Gemini Live STT"]
    K --> L["LLM Processing"]
    L --> M{"Tool needed?"}
    M -->|yes| N["Tool Execution"]
    N --> L
    M -->|no| O["TTS Generation"]
    O --> P["Speakers"]
    O --> Q["Viseme Stream"]
    Q --> R["Avatar Mouth"]
```

## 4. STT Pipeline

```mermaid
flowchart TD
    A["Microphone: 16kHz, mono, int16"] --> B["Audio Callback"]
    B --> C["out_queue"]
    C --> D["session.send_realtime_input()"]
    D --> E["Gemini Live WebSocket"]
    E --> F["Gemini STT Internal"]
    F --> G["output_transcription.text"]
    G --> H["_clean_transcript()"]
    H --> I["_is_repeat_chunk()"]
    I --> J["VisemeStream.feed_text()"]
    J --> K["Activity Log"]
    J --> L["UI Transcript Display"]
    
    Note["Wake word mode: audio goes to openwakeword instead"]
```

## 5. LLM Pipeline

```mermaid
flowchart TD
    A["Transcript"] --> B["System Prompt"]
    B --> C["Time Context"]
    C --> D["Identity Context"]
    D --> E["Memory Block"]
    E --> F["Full System Instruction"]
    F --> G["Gemini Live"]
    G --> H{"Needs tool?"}
    H -->|yes| I["_execute_tool()"]
    I --> J["Run Handler"]
    J --> K["FunctionResponse"]
    K --> G
    H -->|no| L["Generate Response"]
    L --> M["TTS Audio"]
    M --> N["Speakers"]
```

## 6. TTS Pipeline

```mermaid
flowchart TD
    A["Gemini Live Response"] --> B["Audio Extraction"]
    B --> C["sounddevice.OutputStream"]
    C --> D["Speakers"]
    D --> E["EchoGuard.note_output()"]
    E --> F["Track for echo detection"]
    
    G["Viseme Stream"] --> H["Formant Analysis"]
    H --> I["Transcript Parsing"]
    I --> J["Fusion: 72% text + 28% audio"]
    J --> K["Avatar Mouth Shapes"]
    K --> L["QPainter Rendering"]
```

## 7. Tool Calling

```mermaid
sequenceDiagram
    participant Gemini
    participant Main as main.py
    participant Registry as ActionRegistry
    participant Plugin as PluginRegistry
    participant Handler
    
    Gemini->>Main: function_call(name, args)
    Main->>Main: _execute_tool(fc)
    Main->>Main: Identify handler type
    alt Inline tool
        Main->>Main: Direct handler
    elif Action
        Main->>Registry: run(name, args, ctx)
        Registry->>Handler: Call function
    elif Plugin
        Main->>Plugin: run(name, args, player, memory)
        Plugin->>Handler: Call run()
    end
    Handler-->>Main: Result string
    Main-->>Gemini: FunctionResponse
    Gemini->>Gemini: Process result → final response
```

## 8. Plugin System

```mermaid
flowchart TD
    A["plugins/*.py"] --> B["Scan directory"]
    B --> C{"Has PLUGIN dict?"}
    C -->|no| D["Skip"]
    C -->|yes| E["Validate name, description, params"]
    E --> F{"Name collision?"}
    F -->|yes| G["Reject"]
    F -->|no| H["Create PluginRecord"]
    H --> I["Register in PluginRegistry"]
    I --> J["Merge into tool declarations"]
    J --> K["Gemini can call it"]
    
    L["User adds .py file"] --> M["Restart app"]
    M --> B
```

## 9. Memory System

```mermaid
flowchart TD
    A["User reveals fact"] --> B["save_memory tool"]
    B --> C["update_memory()"]
    C --> D["Load long_term.json"]
    D --> E["Merge values"]
    E --> F["Trim to 200k chars"]
    F --> G["Write JSON"]
    G --> H["format_memory_for_prompt()"]
    H --> I["Identity + Recent + Index"]
    I --> J["System Prompt"]
    J --> K["Next Session"]
    
    L["User asks about memory"] --> M["recall_memory tool"]
    M --> N["search_memory()"]
    N --> O["Lexical search"]
    O --> P["Return matching facts"]
```

## 10. Vision System

```mermaid
flowchart TD
    A["User: 'Look at my screen'"] --> B["Gemini calls screen_process"]
    B --> C["_execute_tool()"]
    C --> D["_capture_screen()"]
    D --> E["mss captures display"]
    E --> F["PIL compresses"]
    F --> G["JPEG 1280x720"]
    G --> H["Inject into session"]
    H --> I["Same exchange as tool result"]
    I --> J["Gemini analyzes"]
    J --> K["One turn, one answer"]
    
    L["User: 'Look at camera'"] --> M["_capture_camera()"]
    M --> N["cv2 captures webcam"]
    N --> O["Same injection flow"]
```

## 11. Dashboard

```mermaid
flowchart TD
    A["Phone Browser"] --> B["Connect to localhost:8000"]
    B --> C["QR Code Display"]
    C --> D["Scan QR → session key"]
    D --> E["AES-256-CBC Encryption"]
    E --> F["WebSocket/HTTPS"]
    F --> G["FastAPI Server"]
    G --> H["JarvisLive Methods"]
    H --> I["asyncio.call_soon_threadsafe"]
    I --> J["Gemini Live Session"]
    J --> K["Response → Encrypted → Phone"]
```

## 12. Session Management

```mermaid
flowchart TD
    A["Session Created"] --> B["Gemini Live Connected"]
    B --> C["Server sends resumption handle"]
    C --> D["Handle stored in RAM"]
    D --> E{"Connection drops?"}
    E -->|yes| F["Reconnect"]
    F --> G["Replay resumption handle"]
    G --> B
    E -->|no| H{"Voice change?"}
    H -->|yes| I["Rebuild with keep_context=False"]
    I --> B
    H -->|no| J{"Device change?"}
    J -->|yes| K["Rebuild with keep_context=True"]
    K --> B
    J -->|no| L["Continue"]
```

## 13. Confirmation System

```mermaid
sequenceDiagram
    participant Model as Gemini
    participant Confirm as confirm.py
    participant UI as JarvisUI
    participant Action
    
    Model->>Action: "shutdown computer"
    Action->>Confirm: request("shutdown", title, detail, run)
    Confirm->>UI: Show CONFIRM/CANCEL banner
    Confirm-->>Model: [CONFIRMATION_PENDING]
    Model-->>User: "Please confirm on the HUD"
    User->>UI: Press CONFIRM
    UI->>Confirm: resolve(True)
    Confirm->>Action: Run shutdown_fn()
    Action-->>System: Computer shuts down
```

## 14. Undo System

```mermaid
sequenceDiagram
    participant Action
    participant Undo as core/undo.py
    participant User
    
    Action->>Action: Execute change
    Action->>Undo: push_undo(label, reverse_fn)
    Undo->>Undo: Append to stack
    User->>Action: "undo"
    Action->>Undo: undo_last()
    Undo->>Undo: Pop from stack
    Undo->>Undo: Execute reverse_fn()
    Undo-->>Action: Return result
    Action-->>Model: "Undone"
```

## 15. Data Flow

```mermaid
flowchart LR
    subgraph Input
        Mic["Mic"] --> Audio["Audio"]
        Keyboard["Keyboard"] --> Text["Text"]
    end
    subgraph Processing
        Audio --> Gemini["Gemini Live"]
        Text --> Gemini
        Gemini --> LLM["LLM"]
        LLM --> Tools["Tools"]
        Tools --> Memory["Memory"]
    end
    subgraph Output
        Gemini --> Audio["Audio"]
        Gemini --> Text["Text"]
        Audio --> Speakers["Speakers"]
        Text --> Avatar["Avatar"]
    end
    subgraph Control
        Tools --> OS["OS"]
        OS --> Files["Files"]
        OS --> Settings["Settings"]
    end
```

## 16. Platform Architecture

```mermaid
flowchart TB
    subgraph Code["Platform-Agnostic Code"]
        Core["core/*.py"]
        Actions["actions/*.py"]
        Memory["memory/*.py"]
        Plugins["plugins/*.py"]
        UI["ui.py"]
    end
    
    subgraph Windows["Windows"]
        PTT["Global PTT"]
        Audio["DirectSound/MME"]
        Volume["pycaw"]
        Startup["Registry"]
    end
    
    subgraph Mac["macOS"]
        PTT2["Window PTT"]
        Audio2["Core Audio"]
        Volume2["osascript"]
        Startup2["LaunchAgent"]
    end
    
    subgraph Linux["Linux"]
        PTT3["Window PTT"]
        Audio3["PulseAudio/PipeWire"]
        Volume3["pactl"]
        Startup3[".desktop"]
    end
    
    Code --> Windows
    Code --> Mac
    Code --> Linux
```

## 17. Audio Device Selection

```mermaid
flowchart TD
    A["sd.query_devices()"] --> B["Filter pseudo-devices"]
    B --> C["Filter by channels"]
    C --> D["Filter by host API"]
    D --> E["Check if usable at rate"]
    E --> F["Measure transport works?"]
    F -->|yes| G["Add to list"]
    F -->|no| H["Skip"]
    G --> I["Deduplicate by name"]
    I --> J["Return device names"]
    
    Note["Each direction picks its own host API"]
    Note2["Windows: DirectSound for mic, MME for speakers"]
```

## Summary

```
17 Mermaid diagrams covering all major subsystems
All diagrams based on actual implementation
```