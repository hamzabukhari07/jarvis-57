# 🏛️ Architecture Blueprint: ZEZO Frontend Consolidation & Mobile Remote Modernization

> **Author:** Hamza Bukhari (Lead Architect)  
> **Status:** Proposed Roadmap  
> **Target:** Replace legacy raw HTML codebases with modern, clean, unified React 19 architecture across Desktop OS & Mobile Remote.

---

## 📌 Executive Summary & Motivation

Currently, the repository contains **three separate web/frontend codebases**, creating naming confusion and maintenance overhead:
1. `frontend/` — **Legacy HTML/JS/CSS** (Vanilla JavaScript, raw CSS, outdated DOM manipulation).
2. `web/` — **Modern Desktop Operating System UI** (React 19, Tailwind CSS, ReUI primitives, Assistant-UI, full-screen settings, Qivi avatar).
3. `dashboard/static/` — **Mobile Remote Web UI** running on port 8000 (Vanilla JS `app.html` + `crypto-js.min.js` + `login.html`).

### Objectives:
1. **Retire & Archive `frontend/`:** Remove raw HTML/JS dependencies completely so ZEZO exclusively runs modern React.
2. **Rename & Unambiguous Folder Structure:**
   - Move/rename `web/` ➔ `desktop-ui/` (or standardized `frontend/`).
   - Create a modern touch-friendly React app for the mobile remote ➔ `mobile-remote/` (serving port 8000 via FastAPI).
3. **Consolidate Static Assets:** Migrate voice audio files (`aoede.mp3`, `puck.mp3`, etc.) and icons into permanent React public asset trees.
4. **Preserve 100% Backend Invariants:** Zero breaking changes to `core/ui_server.py`, `dashboard/server.py`, or WebSocket telemetry.

---

## 🏗️ Target Architecture & Directory Layout

```
zezo/
├── desktop-ui/                     # 🖥️ Primary Desktop OS Workstation (Formerly `web/`)
│   ├── src/                        # React 19, ReUI Primitives, Full-screen Settings, Office
│   ├── public/assets/voices/       # Authentic Gemini Live 24kHz preview audio
│   ├── dist/                       # Production build served by core/ui_server.py on port 8765
│   ├── package.json
│   └── vite.config.ts
│
├── mobile-remote/                  # 📱 Touch-First Modern React Remote (Formerly `dashboard/static/`)
│   ├── src/                        # React 19 + Tailwind mobile web app
│   │   ├── components/             # Push-to-Talk button, System quick-actions, Chat stream, File drop
│   │   ├── hooks/useRemoteSocket.ts# AES-256 encrypted WebSocket client (port 8000)
│   │   └── App.tsx                 # Mobile-optimized HUD & pairing screen
│   ├── dist/                       # Production build served by dashboard/server.py on port 8000
│   ├── package.json
│   └── vite.config.ts
│
├── core/
│   ├── ui_server.py                # Updated to serve desktop-ui/dist exclusively (0% fallback to legacy HTML)
│   └── ...
│
├── dashboard/
│   ├── server.py                   # FastAPI server updated to serve mobile-remote/dist static bundle
│   └── ...
│
└── archive/
    └── legacy_vanilla_frontend/    # Preserved old raw HTML/JS for backup/reference only
```

---

## 🗺️ 3-Phase Execution Roadmap

### 📋 Phase 1: Legacy Asset Consolidation & Zero-Dependency Decoupling
- [ ] **Asset Transfer:** Ensure all 5 authentic Gemini Live voice preview audio files (`charon.mp3`, `puck.mp3`, `fenrir.mp3`, `kore.mp3`, `aoede.mp3`) exist in `web/public/assets/voices/` and `web/dist/assets/voices/`.
- [ ] **Decouple `core/ui_server.py`:**
  - Update `FRONTEND_DIR` to point to `desktop-ui/dist` (or `web/dist`).
  - Remove fallbacks referencing old `frontend/index.html` and `frontend/office.html`.
  - Update `_preview_voice_handler` to read directly from the new assets directory.
- [ ] **Decouple Test Suites:**
  - Update `tests/test_payload_and_task_modal.py`, `tests/test_assistant_customise_suite.py`, and `tests/test_scranton_pixel_office_suite.py` to point to the modern React bundle rather than `frontend/index.html`.
- [ ] **Archive `frontend/`:**
  - Safely move `frontend/` into `archive/legacy_vanilla_frontend/` to clean the repository root.

---

### 📋 Phase 2: Folder Normalization & Desktop UI Standardization
- [ ] **Standardize Folder Naming:**
  - Option A: Rename `web/` ➔ `desktop-ui/` (Clear distinction between desktop app and phone remote).
  - Option B: Rename `web/` ➔ `frontend/` (Standard convention, deprecating the old folder).
- [ ] **Update Build & Startup Scripts:**
  - Update `main.py` auto-build check to compile the new folder path on startup if `dist/` is absent.
  - Update `package.json` scripts and IDE launch configurations.

---

### 📋 Phase 3: Mobile Remote UI Modernization (React on Port 8000)
- [ ] **Scaffold `mobile-remote/` React App:**
  - Vite + React 19 + Tailwind CSS + Lucide React.
  - Ultra-lightweight bundle optimized for mobile Safari & Chrome (under 150KB gzip).
- [ ] **Implement Mobile Remote Features:**
  - **Pairing & Key Screen:** Responsive 6-digit key input + auto-connect via URL hash (`#key=...`).
  - **AES-256 Crypto Bridge:** Clean TypeScript wrapper for WebSocket payload encryption/decryption matching `dashboard/server.py`.
  - **Haptic Push-to-Talk:** Large tactile microphone button with real-time audio energy ring.
  - **Quick Control Matrix:** Volume up/down, Mute toggle, Sleep/Wake, System Health meters.
  - **Live Chat Stream:** Mobile-first assistant chat transcript thread.
  - **Direct Upload Tray:** Mobile file picker and photo upload directly dispatched to ZEZO runtime.
- [ ] **FastAPI Integration (`dashboard/server.py`):**
  - Point FastAPI `STATIC_DIR` to `mobile-remote/dist`.
  - Compile build and verify end-to-end phone browser access over LAN Wi-Fi (`http://192.168.x.x:8000`).

---

## 🔒 Non-Negotiable Safety & Invariant Gates
1. **Single-Terminal Startup:** Running `python main.py` must continue to launch the entire environment without requiring manual background terminals.
2. **Offline-First:** All assets (audio previews, fonts, lucide icons) must remain 100% locally bundled (no external CDNs).
3. **LAN Encryption:** Mobile remote must retain zero-trust AES-256 session key exchange over plain HTTP/LAN.
4. **3-Layer Verification:** Each phase must pass static compile (`npm run build`, `py_compile`), runtime validation, and pytest suites.

