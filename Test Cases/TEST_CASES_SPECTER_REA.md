# 🧪 ZEZO REA (Reverse Engineer Anything) — Test Cases & Validation Guide

> **Feature:** Official REA CLI Integration (`rea-agents@6.7.0`), Task Matrix UX & Configurable Fleet Scaffolding  
> **Lead Architect & Creator:** Hamza Bukhari  
> **Target OS:** Windows (Primary)  
> **Output Directory:** `C:\Users\<User>\Desktop\<domain>_rebuild\`  

---

## 📋 Comprehensive Execution Checklist

Use this interactive checklist to track which tests pass or fail during testing:

| ID | Test Scenario | Expected Outcome | Status |
|:---:|:---|:---|:---:|
| **TC-01** | **Rebuild vs Clone Intent** | Dispatches `reverse_engineer` (NOT `clone_website`) | [ ] Pass / [ ] Fail |
| **TC-02** | **Official REA CLI Execution** | Runs `rea capture-browser-scenario` (0 LLM cost) | [ ] Pass / [ ] Fail |
| **TC-03** | **Task Matrix Card UX** | Live steps inside Task Card (No popups / No eye button) | [ ] Pass / [ ] Fail |
| **TC-04** | **Configurable Fleet Engine** | Obey UI dropdown (Antigravity / OpenCode / Kilo / Groq) | [ ] Pass / [ ] Fail |
| **TC-05** | **Desktop Output & Quality** | Scaffolded on Desktop with 3D WebGL `index.html` + React | [ ] Pass / [ ] Fail |
| **TC-06** | **"Launch Kr" Preview** | Opens default browser via `os.startfile` | [ ] Pass / [ ] Fail |
| **TC-07** | **Conversational Clean Domain** | No prompt pollution in folder name (`stripe.com_rebuild`) | [ ] Pass / [ ] Fail |
| **TC-08** | **Offline Cloner Isolation** | "Clone for offline" routes strictly to `clone_website` | [ ] Pass / [ ] Fail |

---

## 🎯 Detailed Test Cases

### 🎯 Test Case 1: Rebuild Frontend Routing & Intent Disambiguation
- **Goal:** Verify that asking to *"rebuild"* or *"scaffold"* a frontend routes strictly to **`reverse_engineer`** and **NEVER** to `clone_website`.
- **Test Prompt:**
  ```text
  Can you rebuild this just only frontend https://stripe.com
  ```
- **Verification Steps:**
  - [ ] 1. Gemini Live dispatches `reverse_engineer` action tool.
  - [ ] 2. Voice response announces: *"Official REA engine is capturing stripe.com via isolated browser session. Scaffolding code directly to your Desktop workspace..."*
  - [ ] 3. No folders created inside project repo directory.
  - [ ] 4. Project scaffold is created directly on **Desktop** at:
    ```
    C:\Users\<YourUser>\Desktop\stripe.com_rebuild\
    ```
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 2: Official REA CLI Execution (Zero-LLM CDP Evidence)
- **Goal:** Ensure the official `rea` CLI binary runs bounded browser scenarios and extracts canonical CDP evidence.
- **Test Prompt:**
  ```text
  Teardown linear.app and inspect the network APIs
  ```
- **Verification Steps:**
  - [ ] 1. Background process executes: `rea capture-browser-scenario <spec.json> --format json`.
  - [ ] 2. Scenario spec matches REA schema (`browser: { mode: "launch" }`, `viewport: { width: 1440, height: 900 }`).
  - [ ] 3. Canonical evidence JSON is saved at:
    ```
    memory/teardowns/linear.app_teardown/evidence.json
    ```
  - [ ] 4. Evidence contains extracted DOM metrics, detected frameworks, styling tokens, and network API endpoints.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 3: Task Matrix Card Streaming UX (No Modals, No Eye Icon)
- **Goal:** Verify that progress updates stream directly inside ZEZO's centralized Task Matrix cards without popup clutter.
- **Test Prompt:**
  ```text
  Rebuild frontend of supabase.com
  ```
- **Verification Steps:**
  - [ ] 1. Header has NO eye icon button.
  - [ ] 2. NO floating modal popups appear.
  - [ ] 3. A new card appears in the Task Matrix titled **"REA rebuild for supabase.com"**.
  - [ ] 4. The card streams live progress percentage (0% $\rightarrow$ 40% $\rightarrow$ 65% $\rightarrow$ 100%).
  - [ ] 5. On completion, card shows target directory path: `Desktop/supabase.com_rebuild`.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 4: Configurable Fleet Scaffolding Engine (UI Dropdown Driven)
- **Goal:** Verify scaffolding dispatches strictly to the engine and model configured in the UI (no hardcoded fallback chains).
- **Test Setup:**
  - In Autonomous Office Deck / Fleet settings, set the developer agent's engine to **OpenCode** (or **KiloCode** / **Antigravity** / **Groq**) and select a model.
- **Test Prompt:**
  ```text
  Rebuild this frontend https://resend.com
  ```
- **Verification Steps:**
  - [ ] 1. `get_configured_scaffolding_engine()` reads the active selection from configuration.
  - [ ] 2. Scaffolding dispatches directly to the selected tool (e.g. `opencode_run` or `kilo_run` or `antigravity_run`).
  - [ ] 3. Model parameter passed to the CLI matches the user's selected model.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 5: Desktop Output & High-Fidelity Artifacts
- **Goal:** Verify generated scaffold contains working modern components and runnable 3D WebGL scene.
- **Test Prompt:**
  ```text
  Rebuild the frontend of raycast.com
  ```
- **Verification Steps:**
  - [ ] 1. Folder `Desktop/raycast.com_rebuild/` is generated with:
    - [ ] `index.html` (Standalone, interactive with WebGL canvas)
    - [ ] `components/Navbar.tsx` (Responsive navbar with lucide icons)
    - [ ] `components/Hero.tsx` (Hero section with gradient typography)
    - [ ] `components/Scene3D.tsx` (Three.js WebGL canvas component)
    - [ ] `styles/globals.css` (Tailwind CSS variables & tokens)
    - [ ] `package.json` (React, Three.js, GSAP, Tailwind dependencies)
    - [ ] `README.md` (Project overview and quickstart instructions)
  - [ ] 2. Double-clicking `index.html` renders full page with rotating 3D Torus Knot and Tailwind layout.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 6: "Launch Kr" / Local Browser Launching
- **Goal:** Verify that conversational launch requests open the rebuild in the OS default browser via `open_app`.
- **Test Prompts:**
  - Step 1: `Rebuild frontend of stripe.com` (Wait for completion)
  - Step 2: `Launch kr` OR `Open it in browser`
- **Verification Steps:**
  - [ ] 1. Rebuild path is registered in `core.repo_context` (`active_project` & `active_file: "index.html"`).
  - [ ] 2. Gemini Live invokes `open_app(path="Desktop/stripe.com_rebuild/index.html")` (NOT `browser_control` with `file:///`).
  - [ ] 3. `actions/open_app.py` resolves Desktop path and runs `os.startfile(str(p))` on Windows.
  - [ ] 4. Rebuild `index.html` opens immediately in your default browser (Chrome/Edge/Brave).
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 7: Conversational Prompt with Clean Domain Extraction
- **Goal:** Ensure conversational sentences do NOT pollute directory names.
- **Test Prompt:**
  ```text
  Can you please inspect the architecture of vercel.com and rebuild it on my desktop right now
  ```
- **Verification Steps:**
  - [ ] 1. Regex extracts clean domain: `vercel.com`.
  - [ ] 2. Output folder on Desktop is cleanly named:
    ```
    C:\Users\<YourUser>\Desktop\vercel.com_rebuild\
    ```
  - [ ] 3. Speech and task title contain clean domain without conversational prompt noise.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL

---

### 🎯 Test Case 8: Offline Cloner vs REA Isolation
- **Goal:** Confirm `clone_website` still functions for explicit clone requests without conflict.
- **Test Prompt:**
  ```text
  Clone this website for offline viewing https://example.com
  ```
- **Verification Steps:**
  - [ ] 1. Dispatches `clone_website` (NOT `reverse_engineer`).
  - [ ] 2. Offline assets saved to `Desktop/example.com_clone/`.
- **Test Result:** [ ] PASS &nbsp;&nbsp; [ ] FAIL
