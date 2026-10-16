# ⚡ ZEZO
### Autonomous Desktop AI Operating System — By Hamza Bukhari

A real-time multimodal AI operating system that can hear, see, speak, and autonomously execute complex tasks on Windows, macOS, and Linux. Built on the Google Gemini Live API for native bi-directional audio streaming, delivering digital autonomy with zero subscriptions.

---

## ⚡ Highlights & Key Capabilities

- **🤖 Autonomous Agent Swarm**: Integrated asynchronous execution with OpenCode, Kilo Code, and Antigravity agents.
- **🎙️ Realtime Gemini Live Voice**: Ultra-low latency voice streaming with local wake-word ("Hey Zezo"), Push-to-Talk (`Ctrl+Space`), and self-echo filtering.
- **🖥️ React 19 Desktop Workstation**: Precision GPU-accelerated HUD with 2D/3D force-directed Memory Graph, task matrix, and expandable Live Display Canvas.
- **📱 Dedicated Mobile Remote**: Built-in encrypted FastAPI gateway for smartphone remote mic and file uploads (`remote/`).
- **🎛️ Unified Command Dock**: Hardware-level mic mute/unmute, phosphor matrix state indicator, emergency stop (`Escape`), and sleep/power management.
- **🧠 SQLite FTS5 & Markdown Vault**: Local-first memory engine (`zezo_brain.db`) and human-readable Markdown notes with automatic secret redaction.
- **🛠️ Self-Describing Tools & Skills**: 29 auto-discovered system actions (browser automation, desktop control, web research, file operations) and high-level declarative skill workflows.
- **🛡️ Governance & Reversible Undo**: Guardrails for critical actions and instant rollback ("undo") for file and system modifications.

---

## 🚀 Quick Start

### 1. Prerequisites
- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.11, 3.12, or 3.13
- **Node.js**: v18+ (for building React frontend)
- **Hardware**: Microphone & speakers (GPU not required)
- **API Key**: Free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Installation & Launch
```bash
# 1. Clone repository
git clone https://github.com/HamzaBukhari/zezo.git
cd zezo

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Build React 19 Frontend
cd frontend
npm install
npm run build
cd ..

# 5. Configure your API key
copy config\api_keys.example.json config\api_keys.json   # Windows
cp config/api_keys.example.json config/api_keys.json   # macOS/Linux
# Edit config/api_keys.json and add your Gemini API key

# 6. Launch ZEZO
python main.py
```

> **First Run**: Paste your Gemini API key in `config/api_keys.json` or open **⚙ Settings** directly in the UI.

---

## 🗂️ Project Structure

```
zezo/
├── main.py                   # Live session orchestrator, audio I/O & action router
├── ui.py                     # PyQt6 WebEngine host & React HUD container
├── frontend/                 # 100% React 19 Desktop OS Workstation & HUD
│   ├── src/                  # React components (Canvas, Memory Graph, Office Deck, HUD)
│   ├── public/               # Audio samples, icons, avatars
│   └── dist/                 # Production bundle served by ui_server.py
├── remote/                   # Dedicated Mobile Remote Gateway (FastAPI + WebSockets)
│   ├── server.py             # Mobile phone audio/command relay & AES encrypted socket
│   └── static/               # Mobile web client assets
├── core/                     # Core runtime engines
│   ├── action_loader.py      # Dynamic tool scanner & validator
│   ├── skill_loader.py       # Multi-step skill package loader
│   ├── ui_server.py          # Local UI static & WebSocket server
│   ├── task_manager.py       # Thread-safe background task registry
│   ├── log_bus.py            # Event ring buffer & secret redaction
│   ├── echo.py               # Acoustic echo cancellation guard
│   ├── hotkey.py             # Global Push-to-Talk handler (Ctrl+Space)
│   └── governance.py         # Path validation & tool security policies
├── actions/                  # 29 built-in system tools (browser, files, apps, system)
├── skills/                   # High-level declarative autonomous workflows
└── memory/                   # SQLite FTS5 store & persistent markdown knowledge vault
```

---

## 🎛️ Voice & Keyboard Shortcuts

| Shortcut / Voice Command | Action |
|---|---|
| `Ctrl + Space` *(Hold)* | Global Push-to-Talk (Mic opens while holding) |
| `Escape` / Click **STOP** | Emergency Stop & Interrupt active generation |
| `"Hey Zezo"` | Wake assistant from sleep mode |
| `"Undo"` | Rollback last file modification or setting change |
| `F4` / Click **MIC** | Toggle microphone mute |
| `F11` | Toggle Fullscreen |
| `Ctrl + L` / Click ⧉ | Open backend log console overlay |

---

## 🔒 Security & Privacy

- **Local Execution**: All memories (`zezo_brain.db`), configurations, and credentials stay local to your machine.
- **Zero Cloud Storage**: No external telemetry, logging servers, or tracking.
- **Automatic Secret Redaction**: Sensitive API tokens (`AIzaSy*`, `AQ.*`, `gsk_*`) are scrubbed before reaching logs or UI.

---

## 📚 Documentation

- 🌐 [Master Architecture Blueprint](file:///docs/PROJECT_ARCHITECTURE.md)
- 🛠️ [Tool & Action Reference](file:///docs/TOOLS.md)
- ⚙️ [Configuration Guide](file:///docs/CONFIGURATION.md)

---

## 👤 Creator & License

- **Creator & Lead Architect**: **Hamza Bukhari**
- **License**: [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (Personal & Non-Commercial use)
