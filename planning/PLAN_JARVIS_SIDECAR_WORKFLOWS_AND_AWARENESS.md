# 🚀 Architecture & Future Blueprint: Native Sidecar, Visual Workflows & Continuous Awareness

> **Project:** ZEZO OS v2 (Autonomous Desktop AI Operating System)  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Source Inspiration:** Repo 3 (JARVIS Daemon & Low-Level Sidecar Architecture)  
> **Status:** Future Implementation Roadmap (Independent of Multi-Agent Fleet)  
> **Date:** October 2026  

---

## 🎯 Executive Summary

Yeh blueprint **ZEZO OS v2** ke liye advanced hardware-level automation, continuous visual awareness, aur visual DAG workflow capabilities ko document karta hai jo humne Repo 3 (`JARVIS`) ke low-level Go Sidecar aur TypeScript daemon se analyze kiye hain. 

Yeh plan current **Multi-Agent Fleet (`PLAN_MULTI_AGENT_FLEET_AND_CIRCUIT_BREAKER.md`)** se completely decoupled aur separate hai, taake future mein as a dedicated upgrade phase implement kiya ja sake.

---

## 🗺️ Architecture Overview: 6 Core Superpowers

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                ZEZO CORE DESKTOP OS                                    │
└───────────┬───────────────────────────────┬──────────────────────────────┬─────────────┘
            │                               │                              │
            ▼                               ▼                              ▼
┌───────────────────────┐       ┌───────────────────────┐      ┌───────────────────────┐
│ 1. Sub-Orb Rail       │       │ 2. UIA Cache Engine   │      │ 3. Awareness Buffer   │
│ • Floating sub-widgets│       │ • Event-driven cache  │      │ • 5s dHash delta      │
│ • Real-time task ring │       │ • < 5ms bounding box  │      │ • Zero-cost memory    │
│ • Click-to-inspect    │       │ • RapidOCR bypass     │      │ • Sub-500ms vision    │
└───────────────────────┘       └───────────────────────┘      └───────────────────────┘
            │                               │                              │
            ▼                               ▼                              ▼
┌───────────────────────┐       ┌───────────────────────┐      ┌───────────────────────┐
│ 4. Visual DAG Engine  │       │ 5. Non-Activating Win │      │ 6. Privacy Blinder    │
│ • Trigger ➡️ Action   │       │ • WS_EX_NOACTIVATE    │      │ • Instant Mute/Blind  │
│ • Visual node canvas  │       │ • Zero focus stealing │      │ • Null frame stream   │
│ • Autonomous queues   │       │ • Caret-anchored pill │      │ • Frosted glass HUD   │
└───────────────────────┘       └───────────────────────┘      └───────────────────────┘
```

---

## 📦 Detailed Capability Specifications

### 1. 🟣 Sub-Orb / Sub-Pebble Desktop Rail (Background Task Multi-Tasking)
* **Goal:** Jab background heavy agents (`opencode_agent`, `kilo_agent`, `agent_reach`) chal rahe hon, toh voice loop ko 100% free rakhte huye screen ke right edge par interactive floating sub-orbs dock karna.
* **Architecture:**
  - Screen border par a discrete translucent drawer (`WS_EX_TOPMOST | WS_EX_NOACTIVATE`).
  - Har background task ka aik miniature sprite/orb (YouTube transcription, Code Refactoring, Web Scraping) with a live circular progress indicator.
  - Sub-orb click karne par lightweight sliding drawer se live terminal logs aur code diffs display honge.
* **Files to touch in future:** `ui.py`, `core/task_manager.py`, `frontend/js/ui.js`.

---

### 2. ⚡ Event-Driven UIAutomation Cache Engine (< 5ms Desktop Inspection)
* **Goal:** Windows desktop apps (Chrome, VS Code, Figma, Settings) ke UI elements ko 15-20s RapidOCR ke bajaye sub-millisecond speed par locate karna.
* **Architecture:**
  - `WinEventHook` (`EVENT_SYSTEM_FOREGROUND`, `EVENT_OBJECT_LOCATIONCHANGE`) ke zariye active window ka UIAutomation accessibility tree memory cache mein load karna.
  - Jab tak active window change na ho, cached Bounding-Boxes (`x, y, w, h`) 0.1ms mein return honge.
  - RapidOCR sirf tab chalega jab native accessibility tree completely missing ho.
* **Files to touch in future:** `core/computer/windows_native.py`, `actions/computer_control.py`.

---

### 3. 👁️ Continuous Background Awareness Ring Buffer & dHash Filter
* **Goal:** Vision queries ("What's on my screen?", "Fix this error") ka jawab bina 6s vision latency aur bina heavy API quota waste kiye **< 500ms** mein dena.
* **Architecture:**
  - Har 5 second par primary display ka 64-bit gradient difference hash (`dHash`) calculate karna.
  - Agar screen static ho (`hamming_distance <= 2`), toh frame discard ho jayega (Zero CPU/Memory cost).
  - Screen change hone par lightweight local OCR / UIA context ring buffer (last 5 frames) mein update hoga.
  - Live Gemini/Groq session ke pass already current screen context cached hoga.
* **Files to touch in future:** `actions/screen_processor.py`, `core/computer/ocr_engine.py`, `main.py`.

---

### 4. 🔄 Visual Node-Based Workflow DAG Engine
* **Goal:** User ko voice ya UI se complex automation pipelines create karne ki taqat dena (e.g. "Trigger ➡️ Process ➡️ Notify").
* **Architecture:**
  - n8n / Activepieces style modular node engine:
    - **Trigger Nodes:** Spoken phrase, Webhook, File change, Timer, Screen keyword detection.
    - **Processing Nodes:** LLM reasoning, Code execution, Python script, Regex extraction.
    - **Action Nodes:** Win32 click, WhatsApp/Telegram message, Browser navigation, File write.
* **Files to touch in future:** `core/workflow_engine.py`, `ui.py`, `frontend/workflows.html`.

---

### 5. 🪟 Non-Activating Floating Desktop Overlay (`WS_EX_NOACTIVATE`)
* **Goal:** Global hotkey (`Ctrl+Alt+Space`) se dictation aur visual tools open karna bina current active window (IDE, Game, Browser) ka typing focus chheenay.
* **Architecture:**
  - Win32 extended window styles: `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST`.
  - Windows Caret detection: Floating pill active mouse ya text caret ke qareeb anchor hogi.
  - User background app mein typing continue rakh sakta hai jabke ZEZO voice listen kar raha hoga.
* **Files to touch in future:** `core/hotkey.py`, `ui.py`, `core/computer/windows_native.py`.

---

### 6. 🔒 Instant Privacy Blinder (`Blind Awareness` Mode)
* **Goal:** Sensitive tasks (passwords, banking, private docs) ke dauran screen captures aur mic listening ko single command se physically disconnect karna.
* **Architecture:**
  - Voice trigger: *"Go blind for 5 minutes"* ya HUD lock button.
  - Screen capture pipeline zero-byte black frames return karegi aur mic stream physically gate ho jayegi.
  - HUD orb par frosted glass / shutter animation render hogi jo confirm karegi ke ZEZO completely blind hai.
* **Files to touch in future:** `main.py`, `actions/screen_processor.py`, `ui.py`.

---

## 📌 Implementation Readiness Matrix

| Feature Module | Complexity | Dependencies | Future Implementation Target |
| :--- | :--- | :--- | :--- |
| **Sub-Orb Desktop Rail** | Medium | PyQt6 HUD / WebSocket server | Post-Fleet Milestone |
| **UIA Event Cache** | High | Win32 ctypes / UIAutomation | Desktop Speed Milestone |
| **Awareness Ring Buffer** | Medium | dHash / Memory Ring Buffer | Vision Latency Milestone |
| **Visual Workflow DAG** | High | Web Canvas / Workflow Runner | Autonomous Workflow Phase |
| **Non-Activating Stapler** | Low | `WS_EX_NOACTIVATE` / Win32 | Hotkey Overlay Phase |
| **Privacy Blinder** | Low | Frame Gate / Shutter UI | Security & Safety Phase |

---

> *Note: This blueprint is archived in `planning/` as a standalone design reference for future implementation.*
