# ZEZO — System Architecture & Dataflow Diagrams

> **Creator & Lead Architect:** Hamza Bukhari  
> **Target OS:** Windows (Primary), macOS, Linux

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    User["👤 User"] -->|voice / mic| PTT["Push-to-Talk Gate (Ctrl+Alt)"]
    User -->|keyboard & mouse| ReactHUD["🖥️ React 18 / Vite HUD (frontend/src/)"]
    
    subgraph AudioEngine["Audio & Voice Engine"]
        PTT --> Mic["🎤 Microphone (PortAudio)"]
        Mic --> Echo["Echo Guard & VAD"]
        Echo -->|PCM 16/24kHz| ZezoLive["main.py (ZezoLive Engine)"]
    end

    subgraph CoreBrain["Cloud Conversational Brain"]
        ZezoLive <-->|Bidirectional WebSocket PCM| GeminiLive["Google Gemini Live API"]
    end

    subgraph DispatchServer["Local UI & Event Server"]
        ZezoLive <-->|aiohttp / WebSocket /ws| Server["core/ui_server.py"]
        Server <-->|IPC Telemetry & Actions| ReactHUD
    end

    subgraph AutonomousFleet["Multi-Agent Fleet & Tools"]
        ZezoLive -->|Function Calling| Tools["actions/*.py (33 Tools)"]
        Tools --> Fleet["Fleet Agents (Verve, Flux, Ahmad)"]
        Tools --> CodeEngines["Code Engines (Antigravity CLI, OpenCode, Kilo)"]
        Tools --> Teardown["REA Teardown Engine (rea-agents@6.7.0)"]
        Tools --> ComputerPerception["3-Tier Perception (UIA / RapidOCR / Vision)"]
    end

    subgraph MemoryEngine["Hybrid 3-Tier Memory Engine"]
        Tools <--> SQLite["Tier 2: SQLite WAL + FTS5 BM25"]
        Tools <--> Vault["Tier 3: Markdown Vault (memory/vault/)"]
        Tools <--> LongTerm["Tier 1: long_term.json"]
    end
```

---

## 2. Desktop HUD & React 18 Architecture

```mermaid
flowchart TD
    subgraph Container["Desktop Application Shell"]
        HostWindow["ui.py (PyQt6-WebEngine Host)"]
        UIServer["core/ui_server.py (aiohttp WebSocket + Static Server)"]
    end

    subgraph ReactFrontend["React 18 SPA (frontend/src/)"]
        App["App.tsx Shell"]
        useZezoSocket["hooks/useZezoSocket.ts (Auto-reconnecting WS)"]
        
        App --> useZezoSocket
        useZezoSocket <-->|ws://127.0.0.1:8765/ws| UIServer

        App --> Office["AutonomousOfficeScreen.tsx (2D Pixel Desks)"]
        App --> DirectChat["AgentDirectChatView.tsx (1-on-1 Fleet Chat)"]
        App --> MemoryCanvas["MemoryGraphCanvas.tsx (3D Force Knowledge Graph)"]
        App --> ChatThread["ZezoChatThread.tsx (Assistant-UI Primitives)"]
        App --> TaskModal["TaskManagerModal.tsx (Task Tree & Logs)"]
        App --> RemoteModal["MobileRemoteModal.tsx (Cloudflare QR & OTP)"]
        App --> ClipPeek["ClipPeekOverlay.tsx (Floating Clipboard HUD)"]
        App --> Settings["SettingsModal.tsx (9 Modular ReUI Tabs)"]
    end
```

---

## 3. Real-Time Conversational Voice Pipeline

```mermaid
flowchart LR
    A["User speaks"] --> B["Microphone (PortAudio)"]
    B --> C["Audio Callback (main.py)"]
    C --> D{"Wake Word or PTT?"}
    D -->|Sleeping| E["Feed openwakeword"]
    D -->|Awake| F["Speaking Lock Check"]
    F -->|ZEZO speaking| G["Drop audio (Anti-Self-Echo)"]
    F -->|User speaking| H["EchoGuard (Band Energy Match)"]
    H -->|Echo detected| G
    H -->|Clean speech| I["Push-to-Talk (Ctrl+Alt)"]
    I -->|Active| J["Stream PCM Chunk (audio/pcm;rate=16000)"]
    J --> K["Gemini Live WebSocket"]
    K --> L["Gemini Realtime Engine"]
    L --> M{"Tool Call?"}
    M -->|Yes| N["Execute Action Handler"]
    N -->|Tool Response| K
    M -->|No| O["Stream Output PCM Audio"]
    O --> P["sounddevice Speakers"]
    O --> Q["Viseme Generator"]
    Q --> R["React HUD Avatar & 3D Viseme Reactivity"]
```

---

## 4. 3-Tier Perception & Computer Automation

```mermaid
flowchart TD
    A["Target GUI Element Request"] --> B["core/computer/ Unified Perception"]
    
    subgraph Tier1["Tier 1: Windows UI Automation (<15ms)"]
        B --> C["windows_uia.py (STA COM Worker)"]
        C --> D{"Element found in UIA tree?"}
    end

    subgraph Tier1_5["Tier 1.5: Multilingual RapidOCR (<80ms, 0 VRAM)"]
        D -->|No| E["ocr_engine.py (CPU ONNX Runtime)"]
        E --> F["Screen crop & spatial coordinate match"]
        F --> G{"Text match found?"}
    end

    subgraph Tier2["Tier 2: Gemini Vision Escalation (~2s)"]
        G -->|No| H["screen_processor.py (mss screenshot)"]
        H --> I["Gemini 2.0 Flash Multimodal Vision"]
    end

    D -->|Yes| J["Normalized Screen Coordinates (X, Y)"]
    G -->|Yes| J
    I -->|Yes| J

    J --> K["pyautogui_driver.py (Smooth click / Unicode paste)"]
```

---

## 5. Reverse Engineering & Website Cloner Pipeline

```mermaid
sequenceDiagram
    participant User
    participant Gemini as Gemini Live
    participant Action as actions/reverse_engineer.py
    participant Teardown as core/teardown_engine.py
    participant CLI as rea-agents@6.7.0 CLI
    participant Vite as Vite Dev Server (port 3000)
    participant UI as React HUD Canvas

    User->>Gemini: "Reverse engineer https://example.com"
    Gemini->>Action: reverse_engineer(url="https://example.com")
    Action->>Teardown: capture_and_scaffold(url)
    Teardown->>CLI: rea capture-browser-scenario --url ...
    Note over CLI: Headless Chrome CDP intercepts DOM, styles, network assets
    CLI-->>Teardown: Emits evidence.json, blueprint.md, ledger.json
    Teardown->>Teardown: Detect tech stack (WordPress, Next.js, Shopify)
    Teardown->>Teardown: Scaffold clean app in ~/Desktop/<project>_rebuild/
    Teardown->>Vite: Spawn npm run dev on port 3000
    Teardown-->>Action: TeardownEnvelope ready
    Action-->>Gemini: 1-sentence confirmation
    Gemini-->>User: "Rebuild complete. Live preview active on port 3000."
    Action->>UI: Broadcast dev server preview URL to HUD Canvas
```

---

## 6. Proactive Background Task Watcher Loop

```mermaid
flowchart TD
    Start["_run_task_completion_watcher() (main.py:2940)"] --> Sleep["Wait 2 seconds"]
    Sleep --> AwakeCheck{"Session connected & awake?"}
    AwakeCheck -->|No| Sleep
    AwakeCheck -->|Yes| SpeakingCheck{"Is speaking OR speech within 3s cushion?"}
    SpeakingCheck -->|Yes (Collision Risk)| Sleep
    SpeakingCheck -->|No (Safe to Notify)| QueryTasks["core.task_manager.get_unnotified_finished_tasks()"]
    QueryTasks --> HasFinished{"Finished tasks available?"}
    HasFinished -->|No| Sleep
    HasFinished -->|Yes| LoopTasks["Iterate tasks & set task.notified = True"]
    LoopTasks --> BuildPrompt["Construct [TASK_NOTIFICATION] prompt"]
    BuildPrompt --> PostCanvas["self.ui.show_content() (Output to React HUD)"]
    PostCanvas --> VoiceNotify["session.send_client_content(1-sentence voice prompt)"]
    VoiceNotify --> Sleep
```

---

## 7. Hybrid 3-Tier Memory Architecture

```mermaid
flowchart TD
    UserSpeech["User interaction / Fact stated"] --> SaveTool["save_memory action"]
    
    subgraph MemoryEngine["Hybrid 3-Tier Storage Engine"]
        SaveTool --> Tier1["Tier 1: memory/long_term.json\n(Core facts, user preferences, session history)"]
        SaveTool --> Tier2["Tier 2: memory/zezo_brain.db\n(SQLite WAL + FTS5 BM25 full-text indexing)"]
        SaveTool --> Tier3["Tier 3: memory/vault/*.md\n(Obsidian-compatible Markdown files + [[wikilinks]])"]
    end

    Tier1 --> ContextPrompt["System Instruction Context Builder"]
    Tier2 <--> SearchTool["recall_history action (BM25 Search)"]
    Tier3 <--> Graph["frontend/src/components/memory/MemoryGraphCanvas.tsx (3D Force Graph)"]
```

---

## 8. Mobile Remote Access via Cloudflare Quick Tunnel

```mermaid
sequenceDiagram
    participant Phone as Mobile Browser
    participant Cloudflare as Cloudflare Edge (*.trycloudflare.com)
    participant Daemon as core/tunnel_manager.py
    participant Server as core/ui_server.py (:8765)
    participant UI as MobileRemoteModal.tsx

    UI->>Daemon: Request tunnel initialization
    Daemon->>Daemon: Execute cloudflared tunnel --url http://127.0.0.1:8765
    Daemon-->>UI: Ephemeral tunnel URL (https://*.trycloudflare.com)
    UI->>UI: Generate AES-256 OTP pairing token & QR Code
    Phone->>UI: Scans QR Code
    Phone->>Cloudflare: Connects with OTP token in URL
    Cloudflare->>Server: Proxies WebSocket /ws and static assets
    Server->>Server: Validates OTP token
    Server-->>Phone: Full-featured mobile HUD loaded
```

---

## 9. Autonomous Fleet Coordination & Workspace Isolation

```mermaid
flowchart TD
    ZezoCommander["ZEZO Primary Orchestrator (main.py)"] -->|fleet_control action| FleetMgr["core/fleet_manager.py"]
    
    subgraph FleetRoster["Autonomous Specialist Roster"]
        Verve["Verve (Lead Frontend Architect)"]
        Flux["Flux (Backend & Database Engineer)"]
        Ahmad["Ahmad (DevOps & Deployment Specialist)"]
        Michael["Michael (Security & Code Reviewer)"]
    end

    FleetMgr -->|Dispatch Task| Verve
    FleetMgr -->|Dispatch Task| Flux
    FleetMgr -->|Dispatch Task| Ahmad
    FleetMgr -->|Dispatch Task| Michael

    subgraph Sandboxes["Git Worktree Workspace Isolation"]
        Verve --> Worktree1[".git-worktrees/workspace_verve/"]
        Flux --> Worktree2[".git-worktrees/workspace_flux/"]
        Ahmad --> Worktree3[".git-worktrees/workspace_ahmad/"]
    end

    FleetMgr --> Lineage["Composite Session ID: peer:<from>-><to>:<timestamp>"]
    FleetMgr --> Telemetry["Broadcast desk status to AutonomousOfficeScreen.tsx"]
```

---

## 10. Summary Matrix

| Diagram # | System Illustrated | Primary Modules Involved |
|-----------|--------------------|--------------------------|
| **1** | System Overview | `main.py`, `core/ui_server.py`, `frontend/src/` |
| **2** | React 18 HUD | `App.tsx`, `useZezoSocket.ts`, ReUI components |
| **3** | Voice Pipeline | `main.py`, `core/echo.py`, `core/hotkey.py` (`Ctrl+Alt`) |
| **4** | 3-Tier Perception | `windows_uia.py`, `ocr_engine.py`, `screen_processor.py` |
| **5** | REA Teardown Engine | `teardown_engine.py`, `rea-agents@6.7.0`, `reverse_engineer.py` |
| **6** | Task Completion Watcher | `main.py:2940`, `core/task_manager.py` |
| **7** | 3-Tier Memory | `long_term.json`, `sqlite_memory.py`, `vault_engine.py` |
| **8** | Cloudflare Mobile Tunnel | `tunnel_manager.py`, `MobileRemoteModal.tsx`, `cloudflared` |
| **9** | Multi-Agent Fleet | `fleet_manager.py`, `fleet_control.py`, `git_sandbox.py` |
