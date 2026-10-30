# 🔬 ZEZO Architecture Review: The Minimalist Frontend & Dual-AI Skill Runner

> **Project:** ZEZO Autonomous Desktop AI Operating System  
> **Creator & Lead Architect:** Hamza Bukhari  
> **Document Status:** Architectural Feasibility Review & Production Blueprint  
> **Core Decisions:**
> 1. **Zero Frontend Over-Engineering:** Preserve the exact existing ReUI Skills Hub layout. Remove toggle confusion; keep only simple Edit & Delete on cards, opening the clean slide-over drawer to edit plain Markdown SOPs.
> 2. **Dual-AI Architecture (Gemini Live + Groq with Gemini Fallback):** Gemini Live handles uninterrupted real-time voice, while Groq LPU (500–800 t/s) executes background skill steps with automatic Gemini Flash fallback.
> **Target Codebase Modules:** `frontend/src/components/settings/SkillsSettingsTab.tsx`, `core/skill_loader.py`, `core/task_manager.py`, `core/llm_client.py`, `main.py`, `actions/`  

---

## 1. Frontend UX: Minimalist, Familiar & Zero Over-Engineering

### The Core Decision:
**Current Skill Hub frontend jaisa hai, waisa hi rahega. Koi naye complex tabs, split-panes, ya engine selectors nahi banaye jayenge.**

### Exact Frontend Interaction Flow:
1. **Cards List View:**
   * User ko `Settings > Skills Hub` mein cards ki list nazar aayegi jaise abhi aati hai.
   * **Toggle Switch Removed:** Enable/Disable toggle ka jhanjhat bilkul khatam kar diya gaya hai.
   * **Clean Actions:** Card par bas do clean actions honge: **Edit** aur **Delete**.
2. **Slide-Over Drawer (Click karne par):**
   * Jab user card par click karta hai ya Edit dabata hai, right side se **Slide-Over Drawer** khulta hai (existing ReUI drawer).
   * Wahan koi engine selector ya technical controls nahi honge.
   * Drawer mein user simply apni **Plain Markdown SOP** read ya edit karta hai.
   * **"Save"** button dabane par local disk par `SKILL.md` update ho jati hai aur ZEZO ka hot-reload usay foran pick kar leta hai.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  🧠 ZEZO Settings > Skills Hub                                      [ + Create Skill ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐                      │
│  │ 🌐 Website Clone Protocol   │  │ 🎨 Website Build Protocol   │   [ SLIDE-OVER       │
│  │ Deep clone & rebuild        │  │ Reference-first design SOP  │     DRAWER]          │
│  │ Domain: UI                  │  │ Domain: UI                  │   ────────────────── │
│  │ [ ✏️ Edit ]     [ 🗑️ Delete ] │  │ [ ✏️ Edit ]     [ 🗑️ Delete ] │   # Website Clone    │
│  └─────────────────────────────┘  └─────────────────────────────┘   Protocol           │
│                                                                     1. Use web_crawl   │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐   2. Verify assets   │
│  │ 🌿 Git Workflow Protocol    │  │ 🔍 Deep Web Research        │   3. Preview server  │
│  │ Atomic staging & commits    │  │ Multi-hop factual research  │   ────────────────── │
│  │ Domain: System              │  │ Domain: Research            │   [ Discard ] [💾Save]│
│  │ [ ✏️ Edit ]     [ 🗑️ Delete ] │  │ [ ✏️ Edit ]     [ 🗑️ Delete ] │                      │
│  └─────────────────────────────┘  └─────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend AI Separation: Gemini Live vs Groq (With Gemini Fallback)

Skill execution mein do mukhtalif AI engines apni apni specific jagah par kaam karte hain:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        BRAIN 1: VOICE & DIALOG                         │
│                    (Google Gemini Live - main.py)                      │
│                                                                        │
│  • Manages 24kHz bidirectional WebSocket audio stream.                 │
│  • Listens to user microphone & speaks real-time responses.            │
│  • NEVER blocks, NEVER executes long multi-step pipelines.             │
│  • Dispatches skill task in <50ms and keeps talking with the user.    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Immediate non-blocking handoff)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     BRAIN 2: BACKGROUND SKILL RUNNER                   │
│                       (core/task_manager.py Thread)                    │
│                                                                        │
│  Primary: Groq LPU (llama-3.3-70b-versatile @ 500-800 t/s)             │
│  Fallback: Google Gemini Flash (gemini-3.8-flash)                      │
│                                                                        │
│  • Ingests plain Markdown SKILL.md instructions.                       │
│  • Reads SOP step-by-step and invokes atomic action tools.             │
│  • Sub-second tool-calling loop (Step 1 -> Step 2 -> Step 3).         │
│  • Updates TaskManager progress and HUD subtasks in real time.         │
│  • Dynamically retries or adapts if an error occurs.                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      REUSABLE ATOMIC PYTHON TOOLS                      │
│                            (actions/*.py)                              │
│                                                                        │
│  • web_crawl       (Node/Playwright stealth crawler)                   │
│  • verify_assets   (Local asset integrity checker)                     │
│  • preview_server  (Loopback HTTP preview server)                      │
│  • antigravity_run (Heavy code rebuilds via agy.exe CLI)               │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Gemini Live (Audio/Voice & Decision Maker):
* **Hamesha Active:** Gemini Live ka audio session kabhi freeze ya pause nahi hota.
* Jab aap bolte hain: *"Zezo, website clone kardo"*:
  1. Gemini Live aapki voice intent sun kar pehchan leta hai ke `website_clone` skill chalani hai.
  2. Foran background task submit karta hai.
  3. **< 50ms ke andar** user ko aawaz mein jawab deta hai: *"Maine background mein start kar diya hai, Task ID #a1b2 hai."*
  4. User aage gap-shap karta rahe ya koi aur kaam kare, audio stream chalti rehti hai.

### 2.2 Background Runner: Groq (Primary) + Gemini Flash (Fallback):
Jab task background worker thread mein jata hai:
* **Primary Engine: Groq LPU (`llama-3.3-70b-versatile`):**
  * **Kyun?** Groq **500–800 tokens/sec** deta hai.
  * Markdown SOP ko sub-second speed par evaluate karta hai aur sequential tools (`web_crawl`, `verify_assets`, etc.) ko call kar leta hai.
  * Gemini Live ka quota aur credits bilkul waste nahi hote.
* **Automatic Fallback: Gemini Flash (`gemini-3.8-flash`):**
  * Agar Groq ki API key missing ho, rate limit hit ho jaye, ya network timeout ho, toh background runner **khud-ba-khud Gemini Flash** par switch kar leta hai. Task kabhi fail ya hang nahi hota.

---

## 3. Real Zero-Code vs New Capabilities Boundary

* **Existing Tools Se Naya Feature:** Agar required atomic tools (`actions/*.py`) system mein pehle se maujood hain, toh koi bhi naya feature ya workflow banana **100% Zero-Code** hai. Aap bas UI mein ja kar plain Markdown SOP likhenge aur Save kar denge.
* **Nayi System Capability:** Agar system ke paas koi tool hi nahi hai (e.g. Photoshop script chalana ya 3D printer control karna), toh pehle ek developer ko Python mein uska atomic action tool likhna hoga, uske baad woh kisi bhi skill mein use ho sakega.

---

## 4. Progress, Confirmations & HUD Status

1. **Live Task Progress:**
   * Background runner har step complete hone par `core/task_manager.py` mein progress update karta hai (e.g., `progress=50%`, `message="Assets verified"`).
   * Main screen par existing task progress bar bina voice loop ko disturb kiye live update hota hai.
2. **Confirmation Gates (Zero Voice Freezing):**
   * Agar kisi skill mein likha hai *"Ask user confirmation before full crawl"*:
   * Background thread `threading.Event` par pause ho jati hai.
   * HUD mein ek confirmation prompt flash hota hai.
   * User button click kare ya aawaz se "Yes" bol de, background runner resume ho jata hai—Gemini Live ka audio connection bina kisi disconnect ke chalta rehta hai.

---

## 5. Summary Matrix: What Changes vs What Stays the Same

| Area | Purana Setup | Naya Streamlined Architecture |
| :--- | :--- | :--- |
| **Frontend Layout** | Existing cards & right drawer | **Same existing layout preserved.** Toggle button removed; simple Edit & Delete on cards. |
| **Skill Format** | Plain Markdown | **100% Plain Markdown SOP.** Zero JSON, zero custom workflow syntax. |
| **Drawer Editor** | Markdown textarea | **Same Markdown textarea.** User plain text instructions likhta hai aur Save karta hai. |
| **Voice Continuity** | Monolithic tool execution | **1-turn <50ms handoff.** Gemini Live continuous chalta rehta hai bina freeze huye. |
| **Execution Engine** | Hardcoded monolithic Python code | **Groq LPU (500–800 t/s) with Gemini Flash fallback** background runner. |

---
*Report prepared for Hamza Bukhari, Creator & Lead Architect of ZEZO.*
