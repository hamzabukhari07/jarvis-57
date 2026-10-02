# 📁 Workspace Ingestion & Multi-Format Payload Engine

> **UI Component:** `frontend/index.html` (04 · Payload Ingestion Dropzone)  
> **Server Ingestion:** `core/ui_server.py` (`_upload_handler` + attachment registry)  
> **Extraction Engine:** `core/file_reader.py` (`read_file`) — runs **on demand**  
> **On-Demand Read:** `actions/file_processor.py` (`_resolve_attachment`)  
> **Silent Attach:** `main.py` (`_on_ui_file_uploaded` / `_on_dashboard_file_uploaded`)  

---

## 📖 Overview

The **Workspace Ingestion Engine** allows users to drag-and-drop or select any file (PDF, TXT, DOCX, Code, Audio, Video) or entire multi-file project folders (HTML/CSS/JS, React, Python) into the ZEZO UI dropzone.

**Attach, don’t read.** A drop is registered by **path only** — no extraction, no session turn, no speech — so the drop is instant and the voice loop is never hijacked. ZEZO stays silent until the user explicitly asks about the file, at which point `file_processor` reads the most recent (or a named) attachment, in the background.

```
[ Desktop Drag & Drop / File Picker ]
                 │
  ┌──────────────┴──────────────┐
  ▼                             ▼
Single File (path only)     Folder (workspace)
  │                             │
  ├─► Register in attachment    ├─► Bounded scan (≤5000 files)
  │   registry (name/path/size) │   + repo_context active workspace
  ▼                             ▼
Saved under `uploads/`      Saved under `uploads/<folder_name>/`
  │                             │
  └──────────────┬──────────────┘
                 ▼
    Silent: no read, no Live turn  →  user asks "what's in this file?"
                 ▼
    `file_processor` resolves the attachment → reads on demand
    (TaskManager for heavy work; voice loop stays responsive)
```

---

## 🛠️ Supported File Types & Extraction Engines (used **on demand**, after the user asks)

At drop time every file is stored with `engine: "attached"` and empty text. The engines below run only when the file is actually read.

| File Type | Extension | Extraction Engine (local → free → paid) | Output |
| :--- | :--- | :--- | :--- |
| **Plain Text & Code** | `.txt`, `.py`, `.js`, `.json`, `.md`, `.html`, `.css` | `direct_read` (UTF-8/Latin-1) | Full code / text content |
| **Documents** | `.docx`, `.xlsx`, `.pptx`, `.epub` | `markitdown` → local (`python-docx` / `openpyxl` / `python-pptx`) → `gemini` | Extracted text |
| **PDF (text layer)** | `.pdf` | `markitdown` → `pdfplumber` (local, free) → else OCR | Extracted text |
| **PDF (scanned / no text)** | `.pdf` | `docling_lazy` if installed → `gemini` REST **only** (Live rung excluded; Files API if >2 MB) | Extracted markdown |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.webp` | `groq_vision` (opt-in) → `gemini_vision` (Live-led ladder) → `image_metadata` | OCR text / description |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` | `groq_whisper` (free) → `gemini` | Transcript text |
| **Video** | `.mp4`, `.mov`, `.mkv`, `.webm` | ffmpeg extract → `groq_whisper` → `gemini` | Transcript text |
| **Project Folders** | Directory tree | Recursive scanner | Project file tree & structure |

> **Groq Hybrid (Option B):** when a Groq API key is configured, audio/video transcription runs on Groq's free `whisper-large-v3-turbo` (verified ~10× faster than the paid Gemini path) and images can use Groq multimodal models. Groq's public free tier currently exposes **no vision model**, so `groq_vision_model` is opt-in and unset by default — images then fall through to the Gemini ladder, which leads with the Live model (separate quota pool). See ADR-037.

> **Local-first document extraction (ADR-054):** text-layer PDFs are read locally with **`pdfplumber`** and Office files with **`python-docx` / `openpyxl` / `python-pptx`** — no cloud call and no MarkItDown dependency required. Only genuinely scanned PDFs (no text layer) escalate to Gemini. This is why a `Desktop\CV.pdf` that used to look "scanned" (because MarkItDown was absent) is now extracted locally in ~5 s instead of a 77 s cloud round-trip.

> **Gemini document path (ADR-053):** the Live rung is **never** used for documents — a multi-MB PDF sent over the Live realtime WebSocket closes it with `1006 abnormal closure`. Documents therefore run through `core.gemini.call(..., allow_live=False)`, and files larger than 2 MB are uploaded via the **Files API** (resumable) instead of inline base64, which otherwise trips the socket write timeout on slow links. The model ladder in `core/gemini.py` was also updated from retired `gemini-2.5-*` names to the live ones (`gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3-flash-preview`, …); models returning `429`/`503` are cooled down so the ladder skips them.

---

## ⚙️ Ingestion Protocol & Behavioral Rules

1. **Multi-Payload Ingestion & Management:** Multiple files and project folders can be ingested simultaneously. Attached items are displayed in a clean scrollable list with individual removal buttons (`✕`) and a global `CLEAR ALL` option.
2. **Active Repo Anchor:** Ingested folders are registered in `core/repo_context.py` so all subsequent coding commands (`antigravity_run`, `opencode_run`, `kilo_run`) automatically target the uploaded folder — this is metadata only, the folder is **not** read. Removing an ingested folder clears the registered context via `forget_repo()`.
3. **Lazy Read (Attach ≠ Read):** A dropped file/folder is attached by **path only**. ZEZO does **not** read it, does **not** wake, and does **not** push a Live turn — the drop is silent and instant. Reading happens only on explicit request ("is file mein kya hai", "read this file"), via `file_processor` with an empty `file_path` (most recent attachment) or a file name.
4. **On-Demand Engine:** `actions/file_processor.py::_resolve_attachment()` resolves the request against the UI server registry (`register_attachment` / `latest_attachment` / `find_attachment`, `core/ui_server.py`). Heavy reads run in `TaskManager` (task_id returned immediately); ZEZO stays responsive and reports when done.
5. **Prompt Rule:** `core/prompt.txt` (Lazy Read Rule) forbids claiming to have read an attached file and routes reads through `file_processor`. Both desktop and mobile uploads follow the same rule.
6. **Self-Directory Protection:** `core/repo_context.py` forbids the ZEZO source directory from ever being overwritten by dropzone uploads.
7. **Single-Drop Guarantee:** A drop on the dropzone is handled only by the `#dropzone-box` listener, which calls `e.stopPropagation()` first so the event never bubbles to the `window` drop listener; therefore one drop triggers exactly one `POST /api/upload` (guards against duplicate-listener regressions).
