# ⚙️ JARVIS (ZEZO OS)
### The Ultimate Cross-Platform Autonomous AI Desktop OS — By Hamza Bukhari

A real-time multimodal AI operating system that can hear, see, speak, and autonomously execute complex tasks on Windows, macOS, and Linux. Built on the Google Gemini Live API for native bi-directional audio streaming, delivering digital autonomy with zero subscriptions.

---

## ⚡ Highlights & Key Capabilities

- **🤖 Autonomous Agent Swarm**: Integrated asynchronous execution with OpenCode, Kilo Code, and Antigravity agents.
- **🎙️ Realtime Gemini Live Voice**: Ultra-low latency voice streaming with local wake-word ("Hey Jarvis"), Push-to-Talk (`Ctrl+Space`), and self-echo filtering.
- **🖥️ Tactical 3-Column Workspace**: Precision GPU-accelerated HUD with live CPU/RAM/GPU telemetry, task matrix queue, and expandable Live Display Canvas.
- **🎛️ Unified Command Dock**: Hardware-level mic mute/unmute, phosphor matrix state indicator, emergency stop (`Escape`), and sleep/power management.
- **🧠 SQLite FTS5 Memory Engine**: Fast full-text BM25 search over conversation history (`zezo_brain.db`) with automatic secret redaction.
- **🛠️ Self-Describing Tools & Skills**: 24 auto-discovered system actions (browser automation, desktop control, web research, file operations) and 11 high-level skill workflows.
- **🛡️ Governance & Reversible Undo**: Guardrails for critical actions and instant rollback ("undo") for file and system modifications.

---

## 🚀 Quick Start

### 1. Prerequisites
- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.11, 3.12, or 3.13
- **Hardware**: Microphone & speakers (GPU not required)
- **API Key**: Free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Installation & Launch
```bash
# 1. Clone repository
git clone https://github.com/HamzaBukhari/JARVIS.git
cd JARVIS

# 2. Run OS-aware setup (auto-installs dependencies for your OS)
python setup.py

# 3. Launch JARVIS
python main.py
```

> **First Run**: Paste your Gemini API key in `config/api_keys.json` or open **⚙ Settings** in the UI.

---

## 🗂️ Project Structure

```
JARVIS/
├── main.py                   # Live session orchestrator, audio I/O & action router
├── ui.py                     # PyQt6 WebEngine host & tactical HUD container
├── setup.py                  # OS-aware automated installer
├── frontend/                 # Tactical HTML5/CSS/JS cockpit interface
│   ├── index.html            # 3-column workspace & unified command dock
│   ├── style.css             # High-precision styling & theme tokens
│   └── js/ui.js              # WebSocket bridge & state matrix controller
├── core/                     # Core runtime engines
│   ├── action_loader.py      # Dynamic tool scanner & validator
│   ├── skill_loader.py       # Multi-step skill package loader
│   ├── task_manager.py       # Thread-safe background task registry
│   ├── log_bus.py            # Event ring buffer & secret redaction
│   ├── echo.py               # Acoustic echo cancellation guard
│   ├── hotkey.py             # Global Push-to-Talk handler (Ctrl+Space)
│   └── governance.py         # Path validation & tool security policies
├── actions/                  # 24 built-in system tools (browser, files, apps, system)
├── skills/                   # 11 high-level declarative autonomous workflows
└── memory/                   # SQLite FTS5 store & persistent long-term memory
```

---

## 🎛️ Voice & Keyboard Shortcuts

| Shortcut / Voice Command | Action |
|---|---|
| `Ctrl + Space` *(Hold)* | Global Push-to-Talk (Mic opens while holding) |
| `Escape` / Click **STOP** | Emergency Stop & Interrupt active generation |
| `"Hey Jarvis"` | Wake assistant from sleep mode |
| `"Undo"` | Rollback last file modification or setting change |
| `F4` / Click **MIC** | Toggle microphone mute |
| `Ctrl + L` / Click ⧉ | Open backend log console overlay |

---

## 🔒 Security & Privacy

- **Local Execution**: All memories (`zezo_brain.db`), configurations, and credentials stay local to your machine.
- **Zero Cloud Storage**: No external telemetry, logging servers, or tracking.
- **Automatic Secret Redaction**: Sensitive API tokens (`AIzaSy*`, `AQ.*`, `gsk_*`) are scrubbed before reaching logs or UI.

---

## 📚 Documentation

- 🌐 [Master Architecture Blueprint](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/ARCHITECTURE.md)
- 🛠️ [Tool & Action Reference](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/TOOLS.md)
- 🖥️ [HUD & Workspace Guide](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/HUD_AND_AVATAR.md)
- 🧠 [Storage & Memory Engine](file:///d:/anitgravity/zezo%20work/jarvis-57/docs/STORAGE.md)

---

## 👤 Creator & License

- **Creator & Lead Architect**: **Hamza Bukhari**
- **License**: [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (Personal & Non-Commercial use)
