# 📔 ZEZO Engineering Learning Journal

## [2026-09-21] — Bug: Desktop UI Dummy Data, Center Button Bar & Right Column Squeeze
- **What was broken:** The UI loaded with static prototype mock data (hardcoded tasks, fake hardware metrics, mock logs), a 7-button demo state bar in the center avatar frame, and the right activity/chat column was squeezed/pushed off-screen.
- **Root cause:**
  1. rontend/index.html contained static HTML cards in the left/center/right columns and modal templates instead of dynamic empty states.
  2. Element IDs in Telemetry (al_cpu, ar_cpu, etc.) and Task Queue were missing or mismatched with 	elemetry_update and 	ask_list WebSocket payloads.
  3. TaskManager was missing a list_tasks() method, causing AttributeError in _poll_tasks().
  4. The 7 prototype demo buttons had a wide flex container layout that pushed the 3rd column off-screen on standard desktop resolutions.
- **Fix applied:**
  1. Cleaned rontend/index.html of all hardcoded mock tasks, documents, and fake messages.
  2. Removed the 7 demo prototype state buttons; live state is displayed cleanly in the tactical bottom capsule (#state-telemetry-capsule).
  3. Made the 3-column workspace grid responsive (minmax(240px, 280px) 1fr minmax(290px, 340px)) ensuring the chat/activity stream is always visible and interactive.
  4. Added list_tasks() alias in core/task_manager.py and dynamic task rendering in rontend/index.html.
  5. Wired real-time telemetry, log ring buffer, and task list updates over WebSocket.
- **Files touched:**
  - rontend/index.html
  - core/task_manager.py
  - ui.py
  - core/ui_server.py
- **Lesson for next time:** Ensure UI templates decouple static prototype placeholders from the dynamic WebSocket state bindings and verify method signatures on internal engine managers before hooking them up to polling loops.

## [2026-09-21] — Bug: Delayed Text Responses & Layout Responsiveness
- **What was broken:**
  1. Typed text commands in the chat bar were not answered immediately (delayed until a second command or voice turn was triggered).
  2. The assistant's response was categorized under `[SYS]` with `intent: greeting ...` prefix instead of a `ZEZO AI` chat bubble.
  3. The 3rd column (Activity Stream & Chat Input) remained partially clipped on standard resolutions due to CSS Grid `min-width: auto` content inflation.
- **Root cause:**
  1. `main.py` and `core/gemini.py` passed `turns` to `session.send_client_content()` as a single `dict` (`turns={"role": "user", ...}`) instead of a `list` (`turns=[{"role": "user", ...}]`). In `google-genai` v1, passing a dict causes Pydantic schema validation to fail inside the async task, dropping the initial message.
  2. `ui.py`'s `_on_log_emitted()` used case-sensitive matching for `"ZEZO:"` while `main.py` logged `"zezo:"`, causing AI replies to fall back to `SYS` logs.
  3. `.workspace-grid` used `minmax(240px, 280px) 1fr ...` where the center `1fr` column defaulted to `minmax(auto, 1fr)`. Because the HUD tabs and inspector header were ~650px wide, `auto` expanded the center column and pushed the right column off-screen.
- **Fix applied:**
  1. Fixed all `send_client_content()` invocations in `main.py` and `core/gemini.py` to pass `turns=[{"role": "user", "parts": [...]}]`.
  2. Updated `_on_log_emitted()` in `ui.py` to use case-insensitive matching (`u_text.startswith("ZEZO:")` and `u_text.startswith(f"{self._assistant_name.upper()}:")`) and stripped internal `intent:` reasoning prefixes.
  3. Updated `.workspace-grid` to `grid-template-columns: minmax(210px, 250px) minmax(0, 1fr) minmax(260px, 300px);` and applied `min-width: 0` to all column wrappers so the layout is 100% responsive and never clips.
- **Files touched:**
  - `main.py`
  - `ui.py`
  - `core/gemini.py`
  - `frontend/index.html`
- **Lesson for next time:** Always pass `list[Content]` to `send_client_content()` in `google-genai` v1 and always pair `1fr` grid columns with `minmax(0, 1fr)` and `min-width: 0` on flex/grid children.

## [2026-09-21] — Bug: Desktop File Dropzone Ingestion Injected Context & Resume-to-Portfolio Auto-Dispatch
- **What was broken:**
  1. When a user dropped/uploaded a resume or document on the desktop dropzone, the AI assistant did not immediately recognize that the file was attached and asked the user if they were uploading a file.
  2. When the user asked to build a portfolio/landing page based on the uploaded resume, the AI stalled and claimed it was "extracting details" or "about to start" without dispatching `antigravity_run` right away.
- **Root cause:**
  1. `core/ui_server.py`'s `/api/upload` endpoint processed the file and broadcasted to Web UI frontend via socket, but lacked the `on_file_uploaded` callback hook to `ui.py` and `main.py` (`ZezoLive`). As a result, the live Gemini session never received the ingested document payload or path.
  2. `core/prompt.txt` lacked an explicit auto-dispatch directive for ingested resumes/documents to portfolio generation, allowing conversational stalling and unfulfilled promises.
- **Fix applied:**
  1. Added `on_file_uploaded` callback in `core/ui_server.py` and invoked it with extracted `file_info` on upload.
  2. Wired `_handle_file_uploaded` in `MainWindow` (`ui.py`) and exposed `current_file` / `on_file_uploaded` properties on `ZezoUI`.
  3. Hooked `self.ui.on_file_uploaded = self._on_ui_file_uploaded` in `main.py` (`ZezoLive`), injecting the full extracted text and file path directly into the active Gemini Live WebSocket session.
  4. Added strict anti-stalling and resume-to-portfolio auto-dispatch directives in `core/prompt.txt` under `[ACKNOWLEDGE BEFORE A SILENCE]` and `[CODING DELEGATION — ZEZO CODER]`.
- **Files touched:**
  - `core/ui_server.py`
  - `ui.py`
  - `main.py`
  - `core/prompt.txt`
  - `tests/test_desktop_ingestion_callback.py`
- **Lesson for next time:** Ensure any UI ingestion channel (desktop dropzone or mobile remote access) has an end-to-end event bridge injecting the payload into the live conversation turn, backed by explicit tool auto-dispatch prompt directives.

## [2026-09-21] — Feature: Customise Assistant Voice Preview & Fixed Response Language Mode
- **What was built:**
  1. Removed the unnecessary "Autonomous Coding Engine Model" dropdown from the "Customise Assistant" modal.
  2. Added a Voice Preview player next to the Gemini Live Voice Persona selector with instant real audio samples for all 5 personas (Puck, Aoede, Charon, Fenrir, Kore).
  3. Added an "Assistant Response Language" selector allowing users to set a strict fixed reply language (e.g. Always English, Always Urdu, Always Hindi) or Auto-Detect.
  4. Wired full persistence via `/api/settings/assistant` and WebSocket `save_assistant_settings`, updating `api_keys.json`, UI state, and Live system prompt instructions.
- **Why this approach:**
  - `edge-tts` samples cached in `frontend/assets/voices/` guarantee instant, latency-free offline voice previews in the browser without consuming Gemini API tokens on simple clicks.
  - Dynamically rendering `{language_directive}` in `core/prompt.txt` ensures the Gemini Live WebSocket session strictly abides by the user's fixed response language preference even when speech is in Urdu or Hindi.
- **Alternatives considered:** Calling Gemini Live REST API on every preview click (rejected due to rate limits and unnecessary latency).
- **Files touched:**
  - `frontend/index.html`
  - `frontend/assets/voices/*.mp3`
  - `core/ui_server.py`
  - `ui.py`
  - `main.py`
  - `core/prompt.txt`
  - `memory/config_manager.py`
  - `tests/test_assistant_customise_suite.py`
- **Lesson for next time:** Modals should always be backed by real two-way data bindings and real audio assets rather than prototype alert stubs.

## [2026-09-21] — Bug: NameError `_names` in `main.py:_build_config`
- **What was broken:** Running `python main.py` failed during Live connect loop with `NameError: name '_names' is not defined` inside `_build_config()`.
- **Root cause:** When adding `language_directive` in `main.py`, the line defining `_names` from `_all_decls` was inadvertently displaced.
- **Fix applied:** Restored `_names = {(d.get("name") if isinstance(d, dict) else getattr(d, "name", "")) for d in _all_decls}` directly after `_all_decls` in `main.py:_build_config()`.
- **Files touched:**
  - `main.py`
  - `LEARNING_JOURNAL.md`
- **Lesson for next time:** Always verify that variable assignments referenced in dictionary constructors remain in scope during refactors.

## [2026-09-22] — Bug: `computer_control(action='close_window')` Closed ZEZO Application
- **What was broken:** When instructed to close an application or folder window (e.g. Explorer), ZEZO called `computer_control(action='close_window')`, which broadcast raw `Alt+F4` to the active window. Because ZEZO / console had focus, it sent `Alt+F4` to itself and terminated the assistant.
- **Root cause:**
  1. `actions/computer_control.py` called `_hotkey("alt", "f4")` unconditionally without checking what process or window was in the foreground.
  2. `actions/open_app.py` previously attempted `taskkill /IM explorer.exe /F` for Explorer which terminated the Windows Desktop shell and lacked self-process protection.
  3. `actions/computer_settings.py` also had unconditional `Alt+F4` fallbacks and `pyautogui.FAILSAFE = True`.
- **Fix applied:**
  1. Implemented `_is_self_or_console_window(hwnd)` in `actions/computer_control.py` checking PID, parent process hierarchy via `psutil`, and assistant window titles ("ZEZO", "JARVIS", "powershell", "cmd.exe", "windowsterminal").
  2. Implemented `_safe_close_window(title)` sending `WM_CLOSE` (0x0010) directly to target windows via Win32 API and searching for top-level non-self application windows when ZEZO is in the foreground, protecting ZEZO from self-kill.
  3. Implemented `_safe_close_tab()` protecting the assistant window from receiving `Ctrl+W` / `Cmd+W`.
  4. Updated `actions/open_app.py:close_application_by_name` to gracefully close Explorer folder windows via `Shell.Application` COM object and prevent self-termination.
  5. Delegated `actions/computer_settings.py` window/app close logic to `_safe_close_window` and set `pyautogui.FAILSAFE = False`.
- **Files touched:**
  - `actions/computer_control.py`
  - `actions/open_app.py`
  - `actions/computer_settings.py`
  - `LEARNING_JOURNAL.md`
- **Lesson for next time:** Never emit broadcast OS-level destructive hotkeys (like `Alt+F4` or `Ctrl+W`) blindly without inspecting foreground window ownership and verifying that the current assistant process is protected.
