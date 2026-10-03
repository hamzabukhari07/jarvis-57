# 📐 Technical Architecture Plan: Non-Blocking Gemini Voice Loop, Native Windows UIA Desktop Control, & Groq Background Coprocessor

> **Target Goal:** Completely decouple Gemini Live real-time audio session from tool execution, eliminate slow/paid Vision calls for standard desktop automation via native Windows UIA (0ms vision lag, 100% free), and route background LLM synthesis to Groq LPU.  
> **Status:** APPROVED FOR PLANNING  
> **Lead Architect:** Hamza Bukhari  
> **Traceability Standard:** [`feature_planning/SKILL.md`](file:///d:/anitgravity/zezo%20work/jarvis-57/.agents/skills/feature_planning/SKILL.md)  

---

## 🎯 1. Requirements & Invariants

### Functional Requirements
- **REQ-VOICE-001 (Zero Voice Dead-Air):** The Gemini Live WebSocket audio stream must **never freeze or mute** while a tool or sub-agent runs. Immediate verbal acknowledgement must be streamed to the user while work executes asynchronously.
- **REQ-UIA-001 (Direct Desktop Control without Vision):** Desktop UI control (typing into Notepad, clicking Calculator buttons, reading screen values) must execute through **native Windows UI Automation (UIA)** and Win32 accessibility tree before falling back to Vision models.
- **REQ-UIA-002 (Accurate Random Text Generation & Typing):** `computer_control(action='random_data')` must not merely generate a string in memory; if requested in the context of writing/typing, it must directly insert the text into the active focused window.
- **REQ-GROQ-001 (Groq LPU Background Acceleration):** Background text parsing, code analysis, and query synthesis must automatically route through `core/llm_router.py` (Groq LPU @ 800+ tokens/sec) without consuming Gemini tokens.

### Non-Functional & Non-Regression Invariants
- **INV-001 (AGENTS.md Rule 3 & Rule 8):** Audio streaming to Gemini Live must preserve explicit PCM sample rate (`audio/pcm;rate=16000`).
- **INV-002 (Thread Safety):** UI automation calls and Groq requests must run in worker threads (`core.task_manager` / `asyncio` executors) without blocking PyQt6 or the WebSocket reader loop.
- **INV-003 (Anti-Slop):** Cyclomatic complexity must remain `< 15` with clean dictionary dispatch and zero bloated comments.

---

## 🏛️ 2. Architecture: Current vs. Proposed State

```
[CURRENT SYSTEM: Blocking Tool Flow]
User Speech ──► Gemini Live WebSockets ──► Tool Call ('screen_process')
                      │                         │ (Blocks Voice Loop ~2-5s)
                      ▼                         ▼
             [Audio Buffer Freezes] ◄─── Gemini Vision Model (Cloud API)

─────────────────────────────────────────────────────────────────────────

[PROPOSED ARCHITECTURE: 3-Tier Asynchronous OS Flow]
User Speech ──► Gemini Live (Voice Dispatcher) ──► Immediate 1-Word Audio ('On it.')
                      │
                      ▼ Dispatches Non-Blocking Task
             ┌──────────────────────────────────────────────┐
             │         Async Task Orchestrator              │
             └───────┬──────────────────────────────┬───────┘
                     │                              │
                     ▼                              ▼
        [L0/L1 Native Windows UIA]      [Groq LPU Coprocessor]
        • Direct OS Window Access       • 800 tokens/sec Analysis
        • 0ms Vision Lag / 0 MB VRAM    • 100% Free Tier API
        • Instant Click & Type          • Summaries & Code Gen
                     │                              │
                     └──────────────┬───────────────┘
                                    │ Emits Task Result
                                    ▼
                      Gemini Live Voice Summary ('Done.')
```

---

### 📊 Code Graph Breakdown: Before vs. After Mapping

#### 🧠 1. GEMINI: Before vs. After
| Task / Feature | Current System (Before) | Target State (After Plan) | Benefit & Rationale |
| :--- | :--- | :--- | :--- |
| **Realtime Voice Stream** | Gemini Live (`main.py`) | 🌟 **Gemini Live (`main.py`)** | Dedicated voice face — never blocked by background work. |
| **Google Search Grounding** | Gemini Search (`web_search.py`) | 🌟 **Gemini Search (`web_search.py`)** | Live factual grounding metadata directly from Google. |
| **Complex Visual Inspection** | Gemini Vision (`screen_process`) | 🌟 **Gemini Vision (`screen_process`)** | Reserved for chart, diagram & complex photo understanding. |
| **Desktop Element Clicks** | ❌ Gemini Vision (`computer_control.py:185`) | ➡️ **Windows UIA (Zero Gemini)** | 2s lag eliminated, 100% free local Windows API. |
| **Notepad Text Reading** | ❌ Gemini Vision (`screen_process`) | ➡️ **Windows UIA (Zero Gemini)** | Direct UIA text extraction in < 15ms. |
| **Code Exploration Agent** | ❌ Gemini Flash (`dev_agent.py`) | ➡️ **Groq LPU (Zero Gemini)** | Gemini quota preserved; Groq scans at 800+ tok/s. |
| **File Parsing & Summaries**| ❌ Gemini Flash (`file_processor.py`) | ➡️ **Groq LPU (Zero Gemini)** | Fast background file parsing. |
| **YouTube Video Summaries** | ❌ Gemini Flash (`youtube_video.py`) | ➡️ **Groq LPU (Zero Gemini)** | Instant video summary without rate limits. |
| **Flight Info Extraction** | ❌ Gemini Flash (`flight_finder.py`) | ➡️ **Groq LPU (Zero Gemini)** | Quick JSON regex parsing via Groq. |

#### ⚡ 2. GROQ LPU: Before vs. After
| Task / Feature | Current System (Before) | Target State (After Plan) | Performance & Speed |
| :--- | :--- | :--- | :--- |
| **Inline Code Generation** | `actions/code_helper.py` | 🌟 **Groq LPU (`code_helper.py`)** | Sub-second inline code writing. |
| **Autonomous Dev Agent** | ❌ (Gemini dependent) | 🌟 **Groq LPU (`dev_agent.py`)** | Instant codebase bug hunting & file exploration. |
| **File Processor Engine** | ❌ (Gemini dependent) | 🌟 **Groq LPU (`file_processor.py`)** | Batch parsing multiple files in parallel. |
| **Research Synthesis** | `actions/agent_reach.py` | 🌟 **Groq LPU (`agent_reach.py`)** | Fast web/Reddit/GitHub intelligence summaries. |
| **Video & Media Summaries**| ❌ (Gemini dependent) | 🌟 **Groq LPU (`youtube_video.py`)** | Transcript distillation in < 1s. |
| **Flight Search Extraction**| ❌ (Gemini dependent) | 🌟 **Groq LPU (`flight_finder.py`)** | Live flight JSON table generation. |

#### 🖥️ 3. NATIVE WINDOWS UIA: Desktop Control Pillar
| Desktop Action | Current System (Before) | Target State (After Plan) |
| :--- | :--- | :--- |
| **Type into Notepad / Word** | Keystrokes + Vision verify | 🌟 **Multi-tier Text Input:** UIA ValuePattern → Clipboard-Safe Paste → Keystrokes (with foreground target-window guard). |
| **Click Calculator / App Buttons** | Screenshot + Gemini Vision | 🌟 **Direct UIA Element Click** (Win32 Tree invoke in < 15ms local latency, 0 Vision). |
| **Random Data / Mock Typing** | String in memory | 🌟 **Explicit Target Verification + Clipboard-Safe Typing** into verified active window. |
| **Read Window Contents** | Screenshot OCR / Gemini Vision | 🌟 **Direct Control Text Read vs Entire Window Text Read** (< 10ms local extraction). |

---

## 📋 3. Phased Atomic Implementation Roadmap

### Phase 1: Robust Multi-Tier Desktop Control & Input Serialization (`actions/computer_control.py`, `core/computer/windows_uia.py`, `core/computer/input_driver.py`)
- **TASK-101 (Serialized Desktop Input Queue):** Introduce a thread-safe serialized desktop input lock to prevent concurrent tool calls from fighting for mouse/keyboard focus.
- **TASK-102 (Target-Window Focus Guard):** Ensure any typing action verifies the expected application (`hwnd` / process name) is genuinely in the foreground before sending text.
- **TASK-103 (Multi-Tier Text Injection Ladder):** Implement resilient text entry:
  1. `UIA ValuePattern / TextPattern` (Fastest, direct injection).
  2. `Clipboard-Safe Paste (Ctrl+V)` (Universal compatibility across classic Win32 / Electron apps).
  3. `Virtual Keystrokes` (Fallback for custom gaming / raw inputs).
- **TASK-104 (Explicit Typing Intent on `random_data`):** When user intent implies typing, generate the data AND inject it into the active target canvas in one atomic step.

### Phase 2: Non-Blocking Tool Protocol & Audio Pipeline Continuity (`main.py`, `core/task_manager.py`)
- **TASK-201 (Gemini Live Protocol Preservation):** Preserve Google Gemini Live Bidi WebSockets function-calling protocol:
  * Fast tools (< 300ms) return direct tool response.
  * Long-running / Heavy tools (> 1s) immediately return an async `task_id` with verbal acknowledgement, dispatching execution to background workers without starving `_recv_audio()` or `_listen_audio()`.
- **TASK-202 (Audio Continuity & State Telemetry):** Prevent buffer underruns and audio dropouts by decoupling WebSocket write queues from background thread completion.

### Phase 3: Gradual Step-by-Step Groq LPU Task Migration (`core/llm_router.py`)
- **TASK-301 (Step 1 Migration - YouTube & Media):** Migrate `actions/youtube_video.py` summaries to `core.llm_router.generate_text()` (Groq first) and verify latency/quality.
- **TASK-302 (Step 2 Migration - Batch File Parsing):** Migrate `actions/file_processor.py` to Groq LPU with automatic Gemini fallback on context overflow.
- **TASK-303 (Step 3 Migration - Dev Agent Bug Hunter):** Migrate `actions/dev_agent.py` to Groq LPU for rapid codebase exploration.

---

## 🧪 4. Traceability & 3-Layer Verification Matrix

| Requirement | Tasks | Code Files | Verification Test (3 Layers) |
| :--- | :--- | :--- | :--- |
| **REQ-UIA-001** | TASK-101, TASK-102, TASK-103 | `core/computer/windows_uia.py`, `actions/computer_control.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Direct text injection into Notepad with target-window validation.<br>**Layer 3:** Calculator button arithmetic verification. |
| **REQ-UIA-002** | TASK-104 | `actions/computer_control.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Verify random string is actively written to Notepad canvas.<br>**Layer 3:** Full pytest run. |
| **REQ-VOICE-001** | TASK-201, TASK-202 | `main.py`, `core/task_manager.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Measure continuous mic packet stream (>500 packets) during background tool execution.<br>**Layer 3:** Zero audio underruns or WebSocket 1011 disconnects. |
| **REQ-GROQ-001** | TASK-301, TASK-302, TASK-303 | `core/llm_router.py` | **Layer 1:** `py_compile`<br>**Layer 2:** Verify YouTube & file processor logs confirm `[LLM] served by Groq`.<br>**Layer 3:** All 22 test suites pass. |

---

## ⚠️ 5. Risk & Rollback Register

| Risk ID | Description | Severity | Mitigation |
| :--- | :--- | :--- | :--- |
| **RISK-001** | Target window loses focus during typing | High | TASK-102 Foreground Window Guard aborts or re-focuses before keystrokes are sent. |
| **RISK-002** | UIA ValuePattern unsupported by custom editor (e.g. VS Code, Chrome) | Medium | Automatic Tier-2 fallback to Clipboard-Safe Paste (`Ctrl+V`). |
| **RISK-003** | Gemini Live drops session if tool response is delayed | High | Enforce task_id return for long tasks to maintain WebSocket protocol synchronization. |
| **RISK-004** | Groq rate limits on free-tier RPM | Low | Automatic fallback ladder in `core/llm_router.py`: Groq → Gemini Flash → Local Ollama. |
