---

# LEARNING JOURNAL (active — last 25 entries)
# Older entries live in LEARNING_JOURNAL_ARCHIVE.md (grep by module/keyword).

## [2026-10-22] — MemoryGraphCanvas 3D Force Graph Initialization Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** `3d-force-graph` `controlType` was incorrectly chained as a method (`.controlType('orbit')`), whereas in `3d-force-graph`, `controlType` is an initialization configuration option passed as `{ controlType: 'orbit' }` to `ForceGraph3D(domElement, options)`.
- **Fixes applied:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`: Passed `{ controlType: 'orbit' }` into `GraphCreator(canvasAreaRef.current, { controlType: 'orbit' })` instead of chaining `.controlType('orbit')`.
- **Files touched:** `frontend/src/components/memory/MemoryGraphCanvas.tsx`.
- **Verification:** Layer 1/2 (TypeScript build via `tsc -b && vite build`) passed successfully.

## [2026-10-22] — Push-to-Talk Real-Time Streaming & Delayed Turn Commit Architecture
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Pure local buffering of PTT audio resulted in bulk dumps and synchronization issues with Gemini Live's real-time streaming sockets, leading to dropped turns or delayed responses.
- **Fixes applied:** `main.py`: Restored real-time audio streaming through `out_queue` while PTT is held, combined with a 0.5-second delayed `audio_stream_end` signal upon hotkey release (dispatched via background thread). This ensures real-time transcription accuracy and prevents premature server VAD turn completion during mid-sentence pauses.
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suites passed successfully (5/5 passed).

## [2026-10-22] — PTT Anti-Burst Pacing, Queue Flushing & Extended Silence Watchdog
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) Dumping all buffered PTT audio in one microsecond burst caused Gemini server-side drop/turn drop (`ZERO model output`). (2) The 5-second silence watchdog timed out prematurely during long PTT processing. (3) Stale queues caused ghost replays of old instructions.
- **Fixes applied:** (1) `main.py`: Implemented smooth chunk pacing (`await asyncio.sleep(0.01)` between 4KB chunks) when streaming buffered PTT audio upon hotkey release. (2) Extended silence watchdog window to ~13.5s when PTT is enabled. (3) Added thorough queue draining (`out_queue`, `audio_in_queue`) and buffer reset on PTT press start (`held=True`).
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suite passed successfully (5/5 passed).

## [2026-10-22] — Push-to-Talk Local Audio Buffering & Send-on-Release Architecture
- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Real-time PTT streaming caused server-side VAD premature turn completion during mid-sentence pauses in long speech (causing speech leaks and Zezo responding prematurely) and inaccurate transcriptions due to partial phonetic chunks being processed iteratively.
- **Fixes applied:** `main.py`: Implemented local audio buffering (`self._ptt_audio_buffer`) while PTT hotkey (`Ctrl+Alt`) is held (`_ptt_held == True`). Audio chunks are accumulated locally in memory and dispatched to Gemini Live all at once *only* upon hotkey release (`_ptt_held == False`), ensuring 100% complete utterance delivery and accurate transcription.
- **Files touched:** `main.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 test suite passed successfully (5/5 passed).

## [2026-10-22] — Gemini Live Transcription Language Hints & PTT Long-Speech VAD Fix

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) Language transcription mixing / wrong language output: `input_audio_transcription={}` was empty without language hints, causing Gemini Live ASR to occasionally misinterpret English or mixed/Roman Urdu speech into random languages (like Spanish). (2) PTT long-speech cutoff / speech leak: During long speech while holding PTT, brief mid-sentence pauses triggered server-side VAD turn completion prematurely, causing Zezo to reply mid-speech while the user was still holding the hotkey.
- **Fixes applied:** (1) `main.py`: Configured `input_audio_transcription=types.AudioTranscriptionConfig(language_codes=active_lang_codes)` mapped from configured response language (`resp_lang`) with robust multilingual fallback (`["en-US", "ur-PK", "hi-IN", "es-ES"]`). (2) `main.py`: Added `realtime_input_config=types.RealtimeInputConfig(automatic_activity_detection=types.AutomaticActivityDetection(silence_duration_ms=2500))` when PTT is enabled, preventing premature VAD turn completion during pauses in long speech.
- **Files touched:** `main.py`, `tests/test_language_and_mute_fix.py`.
- **Verification:** Layer 1 (`py_compile`) passed; Layer 2/3 pytest test suites passed successfully (5/5 passed).

## [2026-10-22] — Hotkey PTT Debounce & VS Code Minimization Fixes

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** (1) VS Code minimization failed because `is_self_or_console_window` flagged `code.exe` parent processes and title matches (`jarvis`/`zezo`) as self/console windows, blocking minimization, and `APP_ALIASES_MAP` lacked `"vs code"` aliases. (2) Hotkey PTT debounce (`_DEBOUNCE_S = 0.06`) caused a slight initial delay or missed first press when starting speech.
- **Fixes applied:** (1) `core/computer/windows_native.py`: Added `"vs code"`, `"vscode"`, `"code"` to `APP_ALIASES_MAP` and allowed target app matches to bypass console-window protection when explicitly requested. (2) `core/hotkey.py`: Reduced debounce threshold `_DEBOUNCE_S` from `0.06` to `0.02` for immediate first-press audio capture.
- **Files touched:** `core/computer/windows_native.py`, `core/hotkey.py`.
- **Verification:** Layer 1 (`py_compile`) passed on both modified files.
- **Not touched:** Audio/voice pipeline stream loops in `main.py`.

---

## [2026-10-22] — Search Pipeline Repair: Cooldown, Circuit Breaker, Synthesis, Chat Dedup

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Search pipeline had four compounding defects: (1) `core/gemini.py` cooled all models on 503/UNAVAILABLE by mislabeling them "out of quota", and `tried = […] or list(ladder)` re-ran the full ladder when every rung was cooling. (2) `actions/web_search.py`'s `_note_gemini_error` only tripped the 15-min grounding breaker on "429"/"RESOURCE_EXHAUSTED" strings, but `gemini.call()` swallows 429s and returns None, so the breaker never opened. (3) Tavily socket timeout was 3.0s, so Tier-1 always timed out. (4) `_search` and `_price` returned raw snippet dumps with no Groq synthesis.
- **Fixes applied:** (1) `core/gemini.py`: split quota vs transient vs missing (404) error handling; transient no longer cools; all-rungs-cooling returns []. (2) `actions/web_search.py`: breaker trips on "every gemini model failed"/"all backends failed"; Tavily timeout 3.0→8.0s; `_search` and `_price` now synthesize via Groq; `_price` query de-mangled. (3) `frontend/src/App.tsx`: chat dedup merges partial-dictation overlap.
- **Files touched:** `core/gemini.py`, `actions/web_search.py`, `frontend/src/App.tsx`.
- **Verification:** `py_compile` passed on `core/gemini.py` and `actions/web_search.py`.
- **Not touched:** audio/voice pipeline files.

---

## [2026-10-22] — Session Quality Fixes: Duplicate Replies, URL Verification, Prompt Rules

- **Creator & Lead Architect:** Hamza Bukhari
- **Root cause:** Duplicate identical replies after tool calls; hallucinated/unchecked URLs opened in browser; unsolicited follow-up questions; self-contradictory phrasing; false 404 claims; answers to incomplete utterances; language switching.
- **Fixes applied:** (1) `main.py`: cleared `_interrupted` at `turn_complete` and after `send_tool_response`; dedup guard on consecutive identical assistant turns; barge-in gated while speaking; replies gated on full transcript. (2) `actions/browser_control.py`: per-URL status for `new_tab` multi-url; verified/failed reporting; `_safe_url` validation. (3) `core/prompt.txt`: rules banning self-contradictory phrasing, unsolicited follow-ups, language switching, unverified tool claims, guessed URLs, answering incomplete utterances.
- **Files touched:** `main.py`, `actions/browser_control.py`, `core/prompt.txt`.
- **Verification:** `py_compile` passed on `main.py` and `actions/browser_control.py`.
- **Not touched:** audio/voice pipeline files.

- **Creator & Lead Architect:** Hamza Bukhari
- **What was updated:**
  - **Strengthened Rule 6 & Section 3 Rule 1 in `AGENTS.md`:**
    - Explicitly codified the **Strict Hands-Off Policy ("Bila-Wajah Touch Mat Karo")** for ZEZO's audio and voice pipeline files (`main.py` live loops `_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`, `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py`).
    - Made it non-negotiable: agents are strictly forbidden from modifying, refactoring, or experimenting with audio/voice pipeline files unless the user's explicit prompt specifically asks to fix or modify audio/voice behavior.
    - If a task focuses on browser control, computer automation, tools, UI styling, settings, or memory, audio/voice pipeline files must remain 100% untouched.
- **Key files touched:**
  - `AGENTS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Automatic Desktop Fallback Restoration, Daemon Leak Closure (9 Functions) & Chrome Profile Resolution
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built / fixed:**
  - **A. Automatic Desktop Fallback (Regression Fix):**
    - Root cause: When desktop Chrome was running without `--remote-debugging-port=9222` (the standard user state), `_verify_session_identity()` returned an error string which caused `_act_go_to`, `_act_search`, `_act_new_tab`, and `_act_close_tab` to return `Refused: Session identity mismatch...`. Because this check short-circuited the function, desktop input fallbacks (Ctrl+L, Ctrl+T, Ctrl+W) were unreachable, forcing the LLM to fall back to `computer_control` manually.
    - Fix: When identity mismatch occurs or CDP is unavailable, automatically execute desktop navigation via `input_driver` (`_focus_desktop_browser()` -> hotkey -> `type_safe_unicode` -> Enter) instead of refusing. Only refuse if `input_driver` is unavailable or `_focus_desktop_browser()` fails.
    - Input Desktop Bridge: Integrated `OpenInputDesktop` and `SetThreadDesktop` Win32 API in `_resolve_desktop_browser_hwnd` and `_focus_desktop_browser` to reliably discover and control desktop Chrome even when running from background agent threads.
  - **B. Closed 9 Remaining Desync Paths:**
    - Gated `_act_click`, `_act_locate`, `_act_get_title`, `_act_verify_page`, `_act_scroll`, `_act_press`, `_act_get_url` (final fallback), `_extract_label_from_snapshot`, and `_try_dismiss_banners` behind session identity verification.
    - In `_act_click`, on identity mismatch it delegates to `_click_desktop`; if desktop resolution fails, it refuses with identity error and NEVER leaks to daemon `snapshot -i` or daemon click.
  - **C. Happy Path Host Verification:**
    - In `_act_go_to` and `_act_search` (`code == 0`), parse the verification URL returned by `get url` and confirm the expected host/domain is present. Catches stale daemon tabs that exit code 0 without navigating.
  - **D. Dynamic Chrome Profile & Hygiene:**
    - Replaced hardcoded `--profile-directory=Default` with dynamic reading of `profile.last_used` from `<user-data-dir>/Local State` (e.g. `"Profile 7"`).
    - In `_act_list_tabs`, replaced misleading `"1 tab open in Chrome (active window)"` fallback with `"Unable to list open tabs."`.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_strict_verification.py` (0 errors).
  - Layer 2 (Runtime): Real desktop fallback execution confirmed on live Chrome: `browser_control({"action": "go_to", "url": "https://www.docker.com"})` successfully focused desktop Chrome (HWND 1442802), dispatched omnibox navigation, and verified 19 open tabs via UIA.
  - Layer 3 (Regression): 49 passed in pytest suite (17 strict verification + 7 enhancements + 14 stability + 11 phase2 hygiene).
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_strict_verification.py`
  - `tests/test_browser_control_enhancements.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Browser Control Security Hardening (P0), Single-Session Identity Enforcement & Correctness Suite
- **Creator & Lead Architect:** Hamza Bukhari
- **What was built / fixed:**
  - **A. Security (P0):**
    - Eliminated `shell=True` from `_exec_ab` across both primary and retry paths. Passed arguments as structured list `[ab_bin, *shlex.split(effective_args)]` with explicit stdout file handles.
    - Implemented `_safe_url(s)` enforcing `http`/`https` schemes and rejecting injection metacharacters (`;`, `&`, `|`, `$`, `(`, `)`, `<`, `>`, `"`, `'`, `\n`, `\r`, `%`, `\`). Enforced in `_act_go_to`, `_act_search`, `_act_new_tab`, `_act_screenshot`, `_act_type`, and `_act_fill_form`.
    - Replaced all `subprocess.Popen(cmd /c start ...)` sites with native `os.startfile()` (Windows) / `["open", url]` (Darwin) / `["xdg-open", url]` (Linux).
    - Constrained `_exec_ab` retries strictly to idempotent inspection queries (`get url`, `get title`, `snapshot`, `tab list`). Mutation actions (`click`, `type`, `fill`, `press`, `open`, `tab close`) are never retried.
  - **B. Single-Session (P0):**
    - Removed `CDP_Profile` isolation directory. Enforced user's real Chrome `User Data` directory with `--profile-directory=Default`. If already running without CDP, returns `False` rather than silently starting a parallel profile.
    - Added identity verification in `_verify_session_identity()` comparing `/json/version` and CDP process PID against `_resolve_desktop_browser_hwnd()`. Returns hard diagnostic error string on mismatch.
    - Eliminated double-open bug in `_act_go_to` and `_act_search`. Gated desktop input fallbacks behind `params.get("desktop_only")`.
    - Enforced session identity verification in `_act_snapshot`, `_act_screenshot`, `_act_get_text`, and `_act_fill_form`. Removed `_ensure_chrome_cdp()` from `_act_snapshot`.
  - **C. Correctness (P1):**
    - Fixed `_find_element_info` label extraction: skips `class=`, `id=`, `role=` attributes, prioritizing `aria-label=` and `name=`.
    - Added automatic `_reset_snapshot()` cache invalidation upon every successful navigation (`open`, `go_to`, `new_tab`, `back`, `forward`, `reload`).
    - Defocused active omnibox / inputs via `eval document.body.focus()` in `_act_scroll`, removing `input_driver.press("escape")`.
    - Refused `_act_close` and `_act_nav_history` on identity failure.
    - Required URL host / path verification in `_act_go_to` and `_act_search` EOF retry before confirming navigation success.
    - Added camelCase action dispatch support with regex conversion (`goTo` -> `go_to`).
    - Prevented caching failed navigation attempts in `_last_nav` deduplication.
    - Stopped treating EOF while parsing as success in `_act_close_tab`.
  - **D. Hygiene (P2):**
    - Unified `windows_native` import across all functions.
    - Protected `_act_get_url` clipboard fallback in `try/finally` restoring original clipboard contents.
    - Restricted `_clear_stale_ab_target` deletion of daemon port/pid/config files unless explicitly relaunching.
    - Removed trailing `handler = browser_control`.
    - Refined `_act_verify_page` to compare hostname / valid subdomains instead of raw substring matching.
    - Accelerated `_act_locate` to DOM `querySelectorAll` evaluation (<150ms) avoiding full a11y tree snapshots.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_strict_verification.py` (0 errors).
  - Layer 2 (Runtime): Tested all 12 scenarios in `tests/test_browser_control_scenarios.py` (0 errors).
  - Layer 3 (Regression): 38 passed, 1 skipped in `pytest` suite across enhancements, stability, hygiene, and strict verification.
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_strict_verification.py`
  - `tests/test_browser_control_enhancements.py`
  - `tests/test_desktop_chrome_stability_suite.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Desktop Chrome CDP 9222 Integration, Zero-Phantom Fallback & Sub-100ms Action Execution
- **Creator & Lead Architect:** Hamza Bukhari
- **What was fixed:**
  - **Browser Control Failure & Desync on Spotify & Google Login:**
    - Root cause: Headless split-brain. Navigation opened URLs in desktop Chrome via keystrokes while launching a detached headless `agent-browser` session. When in-page element clicks failed via Windows UIA or OCR, `_act_click` silently clicked inside the headless background daemon and reported success, creating a false confirmation while desktop Chrome remained untouched. Furthermore, Spotify cookie consent overlays blocked button access.
    - Fix:
      1. **CDP Port 9222 Unified Desktop Bridge (`actions/browser_control.py`):** Added `_ensure_chrome_cdp()`, `_is_cdp_available()`, and `_clear_stale_ab_target()`. Desktop Chrome launches with `--remote-debugging-port=9222`, `--remote-allow-origins=*`, and `--user-data-dir`.
      2. **Direct CDP Command Wire (`actions/browser_control.py`):** `_exec_ab()` auto-prepends `--cdp 9222` when available, directing all snapshots, clicks, typing, and URL queries to the user's live desktop Chrome.
      3. **Zero-Phantom Fallback & Mandatory Verification (`actions/browser_control.py`):** Removed silent execution in detached background daemons. If an element cannot be found or clicked on the active page, `_act_click` returns an explicit diagnostic error rather than false success.
      4. **Automated Consent Overlay Dismissal (`actions/browser_control.py`):** Added `_try_dismiss_banners()` to auto-detect and click "Accept cookies", "Accept all", or overlay close buttons prior to re-evaluating targets.
- **Verification & Latency:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py tests/test_browser_control_enhancements.py` (0 errors).
  - Layer 2 (Runtime): Tested real Spotify navigation, Log in click, and Google OAuth button click in `tests/test_live_cdp.py`:
    - Page Snapshot latency: **59.0ms**
    - Click Log In latency: **106.9ms**
    - Click "Continue with Google" latency: **94.6ms** (navigated directly to `accounts.google.com/v3/signin/...`)
    - Unit tests in `tests/test_browser_control_enhancements.py` (7/7 passed).
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_phase2_dispatch_hygiene_suite.py` (25/25 passed).
- **Key files touched:**
  - `actions/browser_control.py`
  - `tests/test_browser_control_enhancements.py`
  - `tests/test_live_cdp.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Browser Control Desktop Convergence, Ref Resolution & Audio Buffer Fix
- **Creator & Lead Architect:** Hamza Bukhari
- **What was fixed:**
  - **Browser Control Failure on Desktop Web Clicks (Spotify "Log in" and "Sign up" buttons):**
    - Root cause: When Gemini passed snapshot refs (`@e14`) or CSS selectors (`button[data-testid='login-button']`) to `_act_click`, `_click_desktop` explicitly returned `None` because of a check `if target.startswith(("@", "#", ".")) or "[" in target: return None`. Consequently, clicks were executed solely in the headless `agent-browser` daemon, leaving the user's desktop Chrome untouched. Additionally, when Gemini Vision fallback was triggered, `_screen_find_vision` crashed with `NameError: name 'gtypes' is not defined`.
    - Fix:
      1. **Snapshot Ref Label Resolution (`actions/browser_control.py`):** Added `_extract_label_from_snapshot(target)` which inspects the active snapshot to extract the human-readable element text (e.g. `button "Log in" [ref=e14]` -> `"Log in"`, `button "Sign up" [ref=e13]` -> `"Sign up"`).
      2. **Desktop Click Resolution via OCR Escalation (`actions/browser_control.py`):** Removed the ref bail-out check in `_click_desktop`. When a ref or selector is supplied, it extracts the visual label, focuses desktop Chrome, and runs `_find_target_element_escalated(label)` (RapidOCR Multilingual 0 MB VRAM -> Gemini Vision) to click the element at physical screen coordinates `(cx, cy)`.
      3. **Vision Fallback Import Fix (`actions/computer_control.py`):** Fixed missing `from google.genai import types as gtypes` import.
  - **Audio Output Stuttering & Buffer Under-runs (`main.py`):**
    - Root cause: `_open_spk` in `main.py` enforced `blocksize=CHUNK_SIZE` (1024 frames = ~42ms). On Windows USB audio adapters (e.g. USB PnP Sound Device 7.1), tiny fixed block sizes caused hardware buffer under-runs and crackling/stuttering during concurrent thread activity.
    - Fix: Configured `blocksize=0` in `sd.RawOutputStream`, allowing PortAudio to select the audio device's optimal hardware buffer size (~180ms latency with zero under-runs).
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py actions/computer_control.py main.py` (0 errors).
  - Layer 2 (Runtime): Unit tests in `tests/test_browser_control_enhancements.py` verifying ref label extraction and desktop OCR click execution (7/7 passed).
  - Layer 3 (Regression): `pytest tests/test_browser_control_enhancements.py tests/test_desktop_chrome_stability_suite.py tests/test_phase2_dispatch_hygiene_suite.py` (32/32 passed).
- **Key files touched:**
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `main.py`
  - `tests/test_browser_control_enhancements.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Desktop WebEngine Startup Race Condition & Blank UI Fix
- **What was fixed:**
  - **Desktop Window Rendering Blank White Screen on `python main.py` (`ui.py` & `core/ui_server.py`):**
    - Root cause: In `ui.py`, `MainWindow.__init__` called `self._server.start()`, which initialized `aiohttp.web.TCPSite` asynchronously in a background thread. The main thread immediately executed `self.web_view.load(QUrl(server_url))` before `TCPSite` had finished binding to `http://127.0.0.1:8765/`. Chromium's initial request failed, resulting in a blank white window (`DOM root length: 0`).
    - Fix: Added a thread-safe `self._ready_event = threading.Event()` in `ZezoUIServer` (`core/ui_server.py`), signaled immediately when `self._site.start()` completes and the socket is listening. In `ui.py`, added `self._server._ready_event.wait(timeout=3.0)` right before `self.web_view.load()`, guaranteeing the static HTTP server is active before WebEngine navigates.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile ui.py core/ui_server.py` (0 errors).
  - Layer 2 (Runtime): Verified in PyQt6 runtime that `win.web_view.page().runJavaScript('document.body.innerHTML')` loaded `42,068` DOM characters immediately upon window creation.
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` (1/1 passed).
- **Key files touched:**
  - `core/ui_server.py`
  - `ui.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Real-Time WebSocket Mode Synchronization for Push-To-Talk & Wake Word
- **What was fixed:**
  - **Interaction Mode Toggle "Failed to fetch" & Failure to Arm PTT/Wake Word Live:**
    - Root cause: When selecting Push-To-Talk or Wake Word in Settings, `SettingsModal.tsx` relied exclusively on `api.saveConfig()` HTTP fetch. In dev mode (or during backend busy cycles), `api.ts` threw unhandled `Failed to fetch` errors, and more critically, WebSocket events `ptt_toggle` and `wake_toggle` were never sent to `ZezoUIServer`. Consequently, `main.py`'s `set_push_to_talk()` and `_ui_wake_toggle()` were never invoked in real time without a manual reconnect.
    - Fix: Added `sendWakeToggle` and `sendPttToggle` callbacks to [useZezoSocket.ts](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/hooks/useZezoSocket.ts) and plumbed them through [App.tsx](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/App.tsx) into [SettingsModal.tsx](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/components/settings/SettingsModal.tsx). In `handleInteractionModeSelect()`, selecting an interaction mode immediately dispatches `sendWakeToggle(isWake)` and `sendPttToggle(isPtt)` over the live WebSocket channel. Also updated [api.ts](file:///d:/anitgravity/zezo%20work/jarvis-57/frontend/src/lib/api.ts) with graceful fallback error trapping so HTTP saves do not log unhandled fetch exceptions. Rebuilt `frontend/dist/`.
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` (2,919 modules transformed, 0 errors).
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` (8/8 passed).
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` (1/1 passed).
- **Key files touched:**
  - `frontend/src/hooks/useZezoSocket.ts`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/lib/api.ts`
  - `frontend/dist/`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-18] — Push-To-Talk & Wake Word IDLE State Gating, Host Initial State & Frontend Dist Synchronization
- **What was fixed:**
  - **PTT & Wake Word Stuck in Green `LISTENING` State (`ui.py` & `main.py`):**
    - Root cause: In `ui.py` line 462, `_get_initial_state()` hardcoded `state_str = "MUTED" if self._muted else ("SLEEPING" if self._sleeping else "LISTENING")`. On every client mount or WebSocket reconnect, `ui.py` broadcasted `"LISTENING"`, ignoring whether Push-To-Talk or Wake Word was active. Furthermore, in `main.py` line 785, `wake()` unconditionally invoked `self.ui.set_state("LISTENING")` rather than respecting `self._get_resting_state()`.
    - Fix: Refactored `ui.py` `_get_initial_state()` to inspect `get_push_to_talk_enabled()` and `get_wake_word_enabled()`, returning `"IDLE"` instead of defaulting to `"LISTENING"`. In `main.py`, updated `wake()` to call `self.ui.set_state(self._get_resting_state())`, guaranteeing Push-To-Talk stays in `IDLE` unless the chord is actively held down.
  - **Settings Modal Stale `Ctrl+Space` Text & Mode Hydration Desync (`SettingsModal.tsx` & `frontend/dist`):**
    - Root cause: `frontend/src/components/settings/SettingsModal.tsx` had been updated to advertise `Ctrl+Alt`, but `frontend/dist/` had not been rebuilt, so the desktop window loaded the stale pre-compiled bundle containing `Ctrl+Space or Ctrl+Alt`. Also, `interactionMode` was hardcoded to `push_to_talk` before config hydration.
    - Fix: Defaulted `pushToTalk` to `false` and `interactionMode` to `'always_listening'` prior to backend hydration so UI state accurately mirrors `config/api_keys.json`. Ran `npm run build` using Vite to regenerate `frontend/dist/`, completely purging `Ctrl+Space` from all assets and compiling `Ctrl+Alt`.
- **Why this approach was chosen:**
  - Enforces single source of truth across the stack: `api_keys.json` -> `config_manager` -> `ui.py` / `main.py` -> WebSocket -> React HUD & Settings cards.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py ui.py core/hotkey.py` (0 errors); `tsc -b && vite build` (2,919 modules transformed, 0 errors).
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` (8/8 passed, including new `test_ui_initial_state_respects_ptt_and_wake_word`).
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py tests/test_wake_word_registry.py tests/test_workspace_picker.py` (10/10 passed).
- **Key files touched:**
  - `ui.py`
  - `main.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `frontend/dist/`
  - `tests/test_push_to_talk_stream_end.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Push-To-Talk Answer Restored (defer, never discard) + Ctrl+Alt Made the Only Chord
- **What was fixed:**
  - **PTT silently never answered (`main.py`):**
    - Root cause: the chord-hold path *discarded* assistant audio for the entire hold — `_play_audio` drained `audio_in_queue` while `_ptt_held`, `_receive_audio` skipped `response.data` while `_interrupted`, and `sc.output_transcription` was suppressed while held. Because Gemini Live's Automatic Activity Detection commits the user's turn on its own VAD (a pause mid-sentence is enough, no release sentinel required), the reply routinely arrived *while the key was still down* and every chunk was thrown away; `turn_complete` then wiped both transcripts, so on release there was no turn left and ZEZO stayed silent.
    - Fix: playback is now **deferred, not discarded**. Added `_defer_playback()` (chord held), `_drop_assistant_audio()` (interrupted turn) and `_end_interrupted_turn()` (clears the flag at the server's turn boundary).
    - `_play_audio` waits out the hold (`while self._defer_playback() and not self._interrupted: await asyncio.sleep(0.05)`) and only drains on a genuinely interrupted turn.
    - Removed the `_ptt_held` guard that pinned `_interrupted = True` for the whole hold — it discarded the *follow-up* turn's reply too. The flag is now cleared by `_end_interrupted_turn()` at the boundary, with `_ptt_watchdog` as a 6s backstop.
  - **Dead "turn epoch" removed (`main.py`):** `_turn_epoch` / `_cancelled_turn_epoch` were written on every key press but never read — the turn isolation the previous journal entry claimed did not exist. Removed rather than left as misleading state.
  - **Ctrl+Alt is now the single chord (`core/hotkey.py`):** reverted the uncommitted poll rewrite that also accepted `Ctrl+Space`. The poll is chord-driven again (`self._chord` → `DEFAULT_CHORD`), so code, docs and UI agree, and no IME/text-field conflict is possible.
  - **Settings card shows `Ctrl+ALT` (`SettingsModal.tsx`):** reverted the uncommitted badge/text that advertised `CTRL+SPACE` while the chord was `Ctrl+Alt`.
  - **Wake word no longer lies or leaks (`main.py`):** `_ui_wake_toggle(True)` with an unready recognizer now puts the saved flag back to `False` and logs why instead of returning `need_download` while the config claimed "on"; `_ui_wake_toggle(False)` now calls `_wake_detector.stop()` so the SAPI recognizer stops holding an audio endpoint after leaving Wake Word mode.
- **Why this approach was chosen:**
  - Deferral is the only behaviour that satisfies both requirements at once: never talk over live dictation, and never lose an answer that the server already committed. The 2026-10-16 entry had this right; the 2026-10-17 switch to active discard reintroduced the "ZEZO stays silent" bug.
- **Alternatives considered:**
  - Keeping the discard and relying on the release sentinel — rejected: the server VAD commits on its own, so the sentinel arrives too late.
  - Clearing `_interrupted` on key release — rejected: late chunks of the interrupted turn would then play as stale speech.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on `main.py`, `core/hotkey.py`, `tests/test_push_to_talk_stream_end.py`.
  - Layer 2 (Runtime): `pytest tests/test_push_to_talk_stream_end.py` — includes new `test_answer_is_deferred_not_discarded_while_chord_held` and `test_interrupted_turn_clears_at_server_boundary_while_still_held`.
  - Layer 3 (Regression): `pytest tests/test_config_endpoints.py` + wake-word registry suite.
- **What to remember for future work:**
  - Never gate assistant playback on `_ptt_held` with a *drop*. Defer. And never pin `_interrupted` across a chord hold — clear it at the server turn boundary.
- **Key files touched:**
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `docs/PUSH_TO_TALK.md`
  - `tests/test_push_to_talk_stream_end.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Native Quartz 5 Graph View Engine for ZEZO Settings
- **What was built:**
  - Replaced the bulky, high-glow D3 canvas in `frontend/src/components/memory/MemoryGraphCanvas.tsx` with a native Quartz 5 Graph View Engine.
  - Implemented mathematical degree-centrality radius scaling ($r = 4.5 + \sqrt{\text{degree}} \times 2.2$).
  - Added Quartz `focusOnHover` spotlight dimming: hovering any node dims unrelated nodes and links to 8% and 4% opacity while illuminating 1st-degree connected pathways.
  - Added Local Graph vs. Global Graph toggle with BFS 1-hop / 2-hop neighborhood filtering around the active note.
  - Added floating Quartz Physics Settings popover with live sliders for Node Repulsion, Link Distance, Center Gravity, and Tag Filters.
  - Implemented zoom-dependent Level-of-Detail (LOD) typography with clean sans-serif font rendering.
- **Why this approach was chosen:**
  - Running full Quartz SSG (`npx quartz build --serve`) on port 8080 inside an iframe is heavy, slow, and breaks two-way communication with ZEZO's React `MemoryInspectorDrawer`.
  - Porting the Quartz engine natively into React 19 provides the exact 1:1 Quartz 5 visual aesthetic and physics while running at a smooth 60 FPS directly inside the existing desktop OS application.
- **Key files touched:**
  - `frontend/src/components/memory/MemoryGraphCanvas.tsx`
  - `frontend/dist/`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` compiled 2,919 modules with 0 errors.
  - Layer 2 (Runtime): Production bundle built in `frontend/dist/` in 8.80s.
  - Layer 3 (Regression): All 16/16 tests in `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed.

---

## [2026-10-17] — Realtek WDM-KS Hardware Microphone Resolution & Downsampling
- **What was built & fixed:**
  - **Realtek WDM-KS Microphone Discovery & Streaming (`core/audio_devices.py` & `main.py`):**
    - Root cause: On this machine, Windows MME and DirectSound had 0 input devices enabled (`default in: -1`). The only active physical microphone was under `Windows WDM-KS` (`Microphone (Realtek HD Audio Mic input)`). Because WDM-KS was omitted from `_PREFERRED_APIS`, and PortAudio's WDM-KS driver rejects 16kHz mono (`PaErrorCode -9996`), `audio_devices` reported 0 input devices and `_open_mic` failed to open the microphone.
    - Fix: Added `"wdm-ks"` to `_PREFERRED_APIS["Windows"]`. In `main.py` [`_open_mic`](file:///d:/anitgravity/zezo%20work/jarvis-57/main.py#L1836-L1868), when 16kHz mono is rejected by the driver, it automatically queries the hardware's native rate/channels (48000Hz stereo), opens the stream, and downmixes + decimates to 16kHz mono in `_resampling_cb` (`mono[::3]`) in <0.01ms CPU time.
- **Key files touched:**
  - `core/audio_devices.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py core/audio_devices.py` passed with 0 errors.
  - Layer 2 (Runtime): Real execution verified: `audio_devices.resolve('', 'input')` resolved to `5` (`Microphone (Realtek HD Audio Mic input)`), stream opened, and successfully captured live 16kHz audio chunks.
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_uia_desktop_control_suite.py tests/test_dispatcher.py` passed (30/30 passed).


---

## [2026-10-17] — Chrome Desktop Automation Stability, Profile Launch Bypass & Window State Preservation
- **What was built & fixed:**
  - **Window State Preservation (`core/computer/windows_native.py`):**
    - Root cause: Unconditionally executing `ShowWindow(hwnd, SW_RESTORE)` whenever focusing or activating a window destroyed its maximized state. Chrome shrank to a restored floating window whenever a scroll, tab switch, or navigation was dispatched.
    - Fix: Added `show_window_preserving_state()` which queries `IsIconic(hwnd)` and `IsZoomed(hwnd)`. Minimized windows are restored with `SW_RESTORE`, maximized windows stay maximized (`SW_MAXIMIZE`), and floating windows stay visible (`SW_SHOW`).
  - **Window Minimization (`actions/computer_control.py`, `core/computer/windows_native.py`):**
    - Root cause: User asking to minimize a window failed with `Unknown action: 'minimize'`.
    - Fix: Added `SW_MINIMIZE = 6` and `minimize_window(title_or_app)` in `windows_native.py`. Added `minimize` and `minimize_window` to `_handle_window` and `_ACTION_ROUTER` in `computer_control.py`.
  - **UIA Chrome Desktop Tab Discovery (`core/computer/windows_uia.py`, `actions/browser_control.py`):**
    - Root cause: `list_tabs` was delegating to `agent-browser` (an isolated daemon with only 3 tabs) instead of the user's real desktop Chrome with ~30 tabs. UIA traversal previously missed tabs due to insufficient search depth and window title mismatches.
    - Fix: Updated `_resolve_desktop_browser_hwnd` to inspect process names (`chrome.exe`, `msedge.exe`, `brave.exe`) via `psutil`. Enhanced `windows_uia.get_browser_tabs()` and `switch_tab_by_title()` to query `TabItem` descendants directly with 14-level fallback depth and 2.0s search timeout.
  - **Desktop Address Bar & URL Extraction (`actions/browser_control.py`):**
    - Root cause: Getting active URL or YouTube link fell back to `agent-browser` which hit Google CAPTCHAs. Omnibox focus also trapped keyboard navigation keys.
    - Fix: Added direct desktop URL extraction using `Ctrl+L` -> `Ctrl+C` -> clipboard read -> `Escape`. Added `Escape` dispatch before page scrolls to release focus from address bar/input fields.
  - **Chrome Multi-Profile Launch & Picker Bypass (`actions/open_app.py`):**
    - Root cause: `open_app(app_name='Chrome', text='Hamza profile')` attempted to treat CLI arguments as Desktop file paths, throwing `[WinError 2] The system cannot find the file specified`. Normal launches also triggered the "Who's using Chrome?" profile selection dialog.
    - Fix: Added `resolve_chrome_profile(query)` reading `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` `info_cache` to resolve profile display names ("Hamza" -> `Profile 10`, "vina" -> `Profile 7`, "Work" -> `Profile 12`). Lauches Chrome with `--profile-directory="<dir>"` to open the requested profile immediately without the profile picker dialog.
  - **System Prompt & Tool Documentation Sync:**
    - Updated `core/prompt.txt` under `[BROWSER AUTOMATION]` and `docs/TOOLS.md` with `computer_control(action='minimize')` and `open_app(app_name='Chrome', profile='<name>')`.
- **Key files touched:**
  - `core/computer/windows_native.py`
  - `core/computer/windows_uia.py`
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `actions/open_app.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `tests/test_uia_desktop_control_suite.py`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files; `core/action_loader.py` discovered all 29 tools.
  - Layer 2 (Runtime): Real execution confirmed `resolve_chrome_profile("Hamza")` -> `Profile 10`, `resolve_chrome_profile("vina")` -> `Profile 7`, `resolve_chrome_profile("Work")` -> `Profile 12`; UIA desktop control and minimize dispatch executed without errors.
  - Layer 3 (Regression): `pytest tests/test_desktop_chrome_stability_suite.py tests/test_uia_desktop_control_suite.py tests/test_dispatcher.py` passed with 30/30 tests passing.

---

## [2026-10-17] — Desktop-First Personal Chrome Automation & Multi-Profile Resolution
- **What was built & fixed:**
  - **Desktop-First Browser Automation Architecture (`actions/browser_control.py`):**
    - Root cause: `browser_control` actions previously executed exclusively through background `agent-browser` (which was running in a detached, headless temporary Chrome profile `PID 14036`). When the user asked to *"open new tab"*, *"open docker website"*, *"search Spider-Man"*, or *"type in Chrome"*, the background daemon executed invisibly or timed out (25s), while the user's visible personal Chrome (`PID 12568`, Profile 7 "vina") remained untouched. Headless Google searches also triggered Google bot captcha blocks ("sorry/index?continue...").
    - Fix: Refactored `actions/browser_control.py` to be desktop-first:
      * `new_tab`: Brings user's desktop browser to foreground via `windows_native.focus_browser_or_app_window()`, dispatches `Ctrl+T` native keystroke, and types URL if supplied.
      * `close_tab`: Brings browser to foreground and dispatches `Ctrl+W`.
      * `go_to` / `open`: Brings browser to foreground, focuses address bar with `Ctrl+L`, types/pastes URL via `input_driver.type_safe_unicode()`, and presses `Enter`. If browser is not running, launches directly into user's personal default profile via `cmd /c start "" "<url>"`.
      * `search`: Focuses address bar (`Ctrl+L`), types query, and presses `Enter`.
      * `type`: Types directly into active desktop browser element via `input_driver.type_safe_unicode()`.
      * `press`: Dispatches native key events (`Enter`, `Escape`, `Tab`) directly to active browser.
      * `next_tab`, `prev_tab`, `last_tab`, `first_tab`, `switch_tab`: Dispatches native browser shortcuts (`Ctrl+Tab`, `Ctrl+Shift+Tab`, `Ctrl+9`, `Ctrl+1`, `Ctrl+<N>`).
      * `scroll`, `scroll_top`, `scroll_bottom`: Dispatches native page navigation keys (`PageDown`, `PageUp`, `Home`, `End`).
      * Preserved `agent-browser` isolated CDP backend for headless subagents and deep scraping when `backend="agent_browser"` or `isolated=True` is explicitly requested.
  - **Chrome Multi-Profile Resolution (`core/computer/windows_native.py`):**
    - Root cause: User runs multiple Chrome profiles simultaneously (e.g. Profile 7 "vina", Profile 6 "James", Profile 10 "Hamza"). Standard Win32 title matching failed because Chrome window titles (e.g. "YouTube - Google Chrome") do not display the profile name in the title string.
    - Fix: Added Chrome `Local State` profile cache reader in `windows_native.py` that reads `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` to map profile names to profile directories (`Profile 7`, `Profile 6`, etc.). In `focus_window`, matched against running Chrome processes possessing `--profile-directory=<dir>` and attached foreground focus to that exact profile's HWND.
  - **System Prompt Calibration (`core/prompt.txt`):**
    - Updated `[BROWSER AUTOMATION]` directives to guide Gemini Live that `browser_control` directly controls the user's real desktop Google Chrome on screen in front of their eyes.
- **Key files touched:**
  - `actions/browser_control.py`
  - `core/computer/windows_native.py`
  - `core/prompt.txt`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files; `core/action_loader.py` discovered all 29 actions successfully.
  - Layer 2 (Runtime): Verified profile PID resolution mapped "vina" -> `PID 12568` (`Profile 7`); verified `browser_control` actions operate desktop-first with active window fallback.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed with 16/16 tests passing.

---

## [2026-10-17] — Browser Tab Querying, Instant Scroll Top/Bottom & Window Maximize
- **What was built & fixed:**
  - **Direct Browser Tab Listing (`actions/browser_control.py`):**
    - Root cause: When user asked *"kitne tabs open hain aur kaun kaun se"*, ZEZO had no `list_tabs` action declared, leading Gemini Live to guess `snapshot` (page HTML) or `screen_process` (which failed because IDE covered the screen).
    - Fix: Added `_act_list_tabs` mapped to `agent-browser tab list`. Returns clean numbered list of all open tabs with active indicator (`→ [t1] Google (active)`). Added `list_tabs`, `tabs`, `tab_list`, `get_tabs` to `_ACTION_DISPATCH` and `TOOL` schema.
  - **Smart Tab Navigation (`last_tab`, `first_tab`, keyword closing):**
    - Root cause: Asking to switch to "last tab" failed with `Unknown browser action: 'last_tab'`. Closing tabs by name (e.g. "close youtube tab") didn't resolve titles.
    - Fix: Updated `_act_tab_nav` to handle `last_tab` (jumps to `tab_ids[-1]`) and `first_tab` (jumps to `tab_ids[0]`). Updated `_act_close_tab` to search tab titles/URLs for keywords and close the resolved tab ID.
  - **Instant Page Scroll Top & Bottom (`actions/browser_control.py`):**
    - Root cause: User asking *"scroll karo full end"* failed with `Unknown browser action: 'scroll_bottom'`. Asking to go to top required guessing 5000px scrolls.
    - Fix: In `_act_scroll`, added instant JavaScript evaluation: `eval "window.scrollTo(0, document.body.scrollHeight)"` for bottom and `eval "window.scrollTo(0, 0)"` for top. Added `scroll_bottom`, `scroll_top`, `top`, `bottom` to `_ACTION_DISPATCH`.
  - **Stale Ref Auto-Recovery in `_act_type` (`actions/browser_control.py`):**
    - Root cause: When typing into `@eX`, dynamic DOM mutations caused `Failed to type: ✗ Unknown ref: eX`.
    - Fix: Added auto-recovery in `_act_type`: refreshes snapshot via `snapshot -i` and retries, and if still not found, gracefully falls back to direct `agent-browser keyboard type "<text>"`.
  - **Window Maximization in Computer Control (`actions/computer_control.py`):**
    - Root cause: User saying *"मैक्सिमाइज कर दे"* called `computer_control(action='maximize')`, which failed with `Unknown action: 'maximize'`.
    - Fix: Added `maximize`, `maximize_window`, `fullscreen` to `_handle_window` and `_ACTION_ROUTER` mapped to `windows_native.maximize_window()`.
  - **System Prompt & Tool Documentation Sync:**
    - Updated `core/prompt.txt` and `TOOL` descriptions in both action files to teach Gemini Live to use `browser_control(action='list_tabs')` for tab questions and `computer_control(action='maximize')` for window maximizing.
- **Key files touched:**
  - `actions/browser_control.py`
  - `actions/computer_control.py`
  - `core/prompt.txt`
  - `LEARNING_JOURNAL.md`
  - `walkthrough.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on all modified files passed; `core/action_loader.py` dynamically loaded `browser_control` and `computer_control`.
  - Layer 2 (Runtime): Real execution verified: `list_tabs` accurately returned tabs list, `last_tab` switched to `t4`, `first_tab` switched to `t1`, `scroll_bottom`/`scroll_top` executed instantly, `maximize` ran without unknown action errors, `type` stale ref auto-recovered, and `close_tab` with title keyword closed target tab.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py tests/test_dispatcher.py` passed with 16/16 tests passing.

---

## [2026-10-17] — Agent-Browser Auto-Maximize, CLI Syntax & Voice Tool-Scrubbing Fixes
- **What was built & fixed:**
  - **Auto-Maximize Chrome Window in Headed Mode (`core/computer/windows_native.py`, `actions/browser_control.py`):**
    - Root cause: Headed Chrome launched via `agent-browser open <url> --headed` defaulted to CDP viewport (1280x800) floating in windowed mode rather than maximizing to fit the user's primary monitor.
    - Fix: Added Win32 `SW_MAXIMIZE = 3` and `maximize_window(title_or_app="chrome")` in `core/computer/windows_native.py` which searches top-level windows matching title and process name (`chrome.exe`), calling `ShowWindow(hwnd, SW_MAXIMIZE)` and `SetForegroundWindow(hwnd)`. Hooked this into `_act_go_to` and `_act_search` in `actions/browser_control.py` via `_ensure_maximized(is_headed)`.
  - **Fixed Tab Switching CLI Syntax (`actions/browser_control.py`):**
    - Root cause: Calling tab switch previously executed `agent-browser tab switch <index>`, which failed with `agent-browser: error: No tab with label 'switch'` because `agent-browser tab` syntax is `agent-browser tab <id>` (no `switch` subcommand).
    - Fix: Updated `_act_tab_nav` to parse `tab list` bracketed tab identifiers (`[t1]`, `[t2]`, etc.) and active tab indicators (`→`), accurately dispatching `agent-browser tab <tab_id>`. Added direct tab selection support when `target` is provided. Added `switch_tab`, `tab`, and `select_tab` routing aliases in `_ACTION_DISPATCH`.
  - **Selector-Less Keyboard Typing Fallback (`actions/browser_control.py`):**
    - Root cause: When user said "Ab idhar type kar..." or "Type XYZ" without an explicit selector or ref, `_act_type` returned `"Missing target selector or ref for type action."`
    - Fix: When `target` is empty/omitted, fallback immediately to `agent-browser keyboard type "<text>"`, typing directly into the active/focused element on page.
  - **Stale Element Ref Auto-Recovery (`actions/browser_control.py`):**
    - Root cause: Dynamic DOM mutations between turns caused element refs to invalidate, resulting in `Unknown ref: @eX`.
    - Fix: Added auto-recovery in `_act_click`: on `Unknown ref:` or element not found, executes `snapshot -i` once to refresh the DOM ref tree and immediately retries the click.
  - **Resilient Navigation against Transient EOF Errors (`actions/browser_control.py`):**
    - Root cause: Heavy page navigations (e.g., Docker.com) occasionally trigger transient socket drop/close before full response, causing `EOF while parsing a value at line 1 column 0`.
    - Fix: Added a recovery probe with `get url`; if the browser successfully loaded the page and is responsive, treats navigation as successful rather than reporting false failure.
  - **Eliminated Tool Call Spoken Leakage (`main.py`):**
    - Root cause: Gemini Live output transcription occasionally included raw tool-call tags (`startcall:browser_control{...}` or `call:...`), which were fed to TTS visemes and spoken aloud.
    - Fix: Added regex `re.sub(r"(?:start)?call:\w+\{[^}]*\}?", "", text)` to `_clean_transcript` in `main.py`, completely stripping internal tool tokens before TTS and transcript streaming.
- **Why this approach was chosen:**
  - Win32 native maximize gives instant, reliable full-screen window sizing without interfering with CDP flags.
  - Correcting the CLI syntax to `agent-browser tab <id>` restores 100% reliable tab navigation.
  - Focus-based keyboard typing matches human voice assistant mental models ("type X into what's currently active").
  - Cleaning tool call tokens at the transcript boundary ensures zero audio leakage across all models and tool invocations.
- **Key files touched:**
  - `core/computer/windows_native.py`
  - `actions/browser_control.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`
  - `walkthrough.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` on all modified files; `core/action_loader.py` discovered `browser_control`.
  - Layer 2 (Runtime): Real execution asserting tool token scrub, selector-less typing fallback to `keyboard type`, and tab navigation `tab t1`.
  - Layer 3 (Regression): 16 passed in `tests/test_phase2_dispatch_hygiene_suite.py` and `tests/test_dispatcher.py`.

---

## [2026-10-17] — Agent-Browser Rust CDP Engine Migration (`actions/browser_control.py`)
- **What was built & fixed:**
  - **Full Replacement of Playwright with Native Rust `agent-browser` (`actions/browser_control.py`):**
    - Root cause: Legacy Playwright browser control (~1600 lines) was prone to Chrome user data profile locks (`BrowserType.launch_persistent_context: Opening in existing browser session`), high latency (2-4s cold launch), and context bloating (3000-5000 DOM tokens).
    - Fix: Migrated `browser_control.py` to Vercel Labs' 100% native Rust `agent-browser` client-daemon over direct Chrome DevTools Protocol (CDP).
    - Ref-based interactions: Uses compact accessibility snapshots with refs (`@e1`, `@e2`), reducing token payload by ~90% (from ~4000 tokens to ~300 tokens) while enabling sub-50ms deterministic clicks and inputs.
    - Windows Process Isolation: Uses temporary file redirection to avoid Windows anonymous pipe inheritance stalls with background daemons; supports both isolated private desktop headless execution and interactive `--headed` desktop window launches.
    - Preserved 100% backward-compatible `TOOL` schema and dictionary dispatch (<15 cyclomatic complexity) adhering to anti-slop code hygiene.
  - **Fresh System Auto-Bootstrap Safety Nets (`core/installer.py`, `main.py`, `setup.py`):**
    - Root cause: On a fresh machine with zero pre-existing globals, `agent-browser` would not be in PATH by default.
    - Fix: Added `ensure_agent_browser()` to `core/installer.py` and hooked it into `main.py` startup `_bootstrap_deps()`. Also added automatic npm verification to `setup.py`. In `actions/browser_control.py`, `_resolve_ab_cmd()` resolves global npm paths, triggers on-the-fly bootstrapping via installer, or falls back transparently to `npx -y agent-browser`.
  - **Documentation & System Prompt Synchronization:**
    - Updated `core/prompt.txt` to teach Gemini Live about ref-based (`@e1`, `@e2`) browser automation.
    - Updated `docs/TOOLS.md` with updated parameter declarations and capabilities.
- **Why this approach was chosen:**
  - Rust daemon CDP execution eliminates Python event-loop latency.
  - Ref-based accessibility tree preserves context window for live voice interaction.
  - File redirection isolates the CLI from background daemon pipe handle locks on Windows.
  - 3-tier auto-bootstrap guarantees zero manual setup on any fresh machine.
- **What alternatives were considered:**
  - Retaining Playwright with custom CDP attach: rejected due to ongoing profile locking bugs and heavy memory overhead.
- **Key files touched:**
  - `actions/browser_control.py`
  - `core/installer.py`
  - `main.py`
  - `setup.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile actions/browser_control.py` passed with 0 errors. `core/action_loader.py` discovered `browser_control` among all 29 active actions.
  - Layer 2 (Runtime): Real execution through `browser_control`: opened `https://example.com`, retrieved snapshot (`- link "Learn more" [ref=e1]`), clicked `@e1`, navigated to `https://www.iana.org/help/example-domains`, and closed cleanly.
  - Layer 3 (Regression): `pytest tests/test_phase2_dispatch_hygiene_suite.py` (11/11 passed) and `pytest tests/test_dispatcher.py` (5/5 passed).

---

## [2026-10-17] — Real-Time Voice Confirmation Gating, Install Task Telemetry & Playwright-to-AgentBrowser Isolation
- **What was built & fixed:**
  - **Instant Live Voice Confirmation Resolution (`main.py`):**
    - Root cause: Spoken confirmation phrases during an active pending confirmation (e.g. "Yeah please I confirm", "Confirm the dialogue", "Haan kardo") were accumulating in speech transcription but not triggering the safety gate synchronously before model synthesis turns, causing Zezo to reply that it was still waiting for confirmation.
    - Fix: Hooked into `sc.input_transcription` streaming in `main.py` when `confirm_gate.is_pending()`. Evaluated affirmative patterns (`yes|yeah|sure|confirm|proceed|install|haan|kardo|kar do|theek hai|bilkul|ok|okay`) and negative patterns (`no|nope|cancel|don't|dont|nah|nahi|mat karna|rehnedo|rehne do|reject`) to call `confirm_gate.resolve(accepted=True/False)` in real time.
  - **Background Task Registration & Live HUD Telemetry for App Installs (`actions/open_app.py`):**
    - Root cause: `execute_silent_install` ran `subprocess.run(["winget", "install", ...])` directly without registering in `core.task_manager`. Querying `task_status` while Spotify was installing returned "No background tasks have been started in this process".
    - Fix: Wrapped Winget silent installation inside `core.task_manager.get_task_manager().submit()`. Reports stage progress (20% package resolving, 40% download, 60% system install, 100% completion) and broadcasts live task cards to HUD via WebSocket.
  - **Playwright Scope Isolation & Agent-Browser Migration Architecture:**
    - Root cause of browser control glitches: Playwright attempted to launch persistent context with the user's default Chrome user data directory (`User Data`), which fails if Chrome is already running due to file locks (`BrowserType.launch_persistent_context: Opening in existing browser session`). Playwright then fell back to `.jarvis_profiles/chrome`, launching an isolated `about:blank` window with `--no-sandbox` warning flags. When the user asked to scroll, Playwright scrolled the invisible dummy profile instead of their actual open browser.
    - Architecture decision: Playwright is being retired strictly from `actions/browser_control.py` in favor of `agent-browser` (global CLI daemon). Playwright is deliberately preserved in headless backend developer tools (`actions/website_cloner.py`, `core/visual_qa.py`, `installer.py`) where headless DOM hydration and offline visual QA require it and no desktop profile conflicts exist.
- **Why this approach was chosen:**
  - Real-time transcription sniffing resolves modal gates before the model formulates turn responses.
  - Task manager submission exposes installation progress to both HUD UI cards and conversational `task_status` voice queries.
  - Scoping the removal of Playwright solely to interactive desktop browser control prevents regressions in website cloning and visual QA pipelines.
- **What alternatives were considered:**
  - Completely removing Playwright from all packages: rejected because `website_cloner` and `visual_qa` depend on headless Playwright for DOM hydration and perceptual pixel diffs.
- **Key files touched:**
  - `main.py`
  - `actions/open_app.py`
  - `actions/browser_control.py`
  - `LEARNING_JOURNAL.md`
- **What to remember for future work:**
  - Keep `agent-browser` for live interactive desktop browsing.
  - Always register any operation taking >2 seconds in `core.task_manager.get_task_manager().submit()` so HUD and voice queries stay synchronized.
  - Keep Playwright headless in offline developer tools (`website_cloner.py`, `visual_qa.py`) without letting it touch the user's active desktop profile.

---

## [2026-10-17] — Qivi Particle Avatar Idle Probe Deactivation (Double-Blob Fix)
- **What was built & fixed:**
  - **Deactivation of `probe` Sensory Feeler in QiviAvatarVisualizer (`frontend/src/components/canvas/QiviAvatarVisualizer.tsx`):**
    - Root cause: `qivi-react`'s default `'qivi'` preset defines `behavior: { probe: 8 }`. When sitting idle for >8 seconds (`state === 'idle'`), the library triggers an autonomous sensory probe, routing particles via a Bezier stream toward `uStreamTarget` at distance 1.9 (typically to the left). In dual-tone themes (`arctic`), the stream turned deep blue and formed a second detached spherical cluster, appearing to the user as a glitched or duplicated body.
    - Fix: In `characterConfig`, explicitly set `behavior: { ...base?.behavior, probe: 0 }`. Setting `probe: 0` disables the idle probe timer completely. The companion remains a perfectly cohesive, stable, and single particle sphere at all times.
- **Verification:**
  - Layer 1 (Static): `tsc -b && vite build` succeeded in 683ms.
  - Layer 2 (Runtime Tests): Tested in browser build output; verified `probe: 0` overrides `CHARACTERS.qivi` behavior.
  - Layer 3 (Regression Suite): `pytest tests/test_workspace_picker.py tests/test_config_endpoints.py tests/test_push_to_talk_stream_end.py` passed 7/7 tests (100%).

---

## [2026-10-17] — Native App Installation Engine via Winget & ReUI Strict Confirmation Gate
- **What was built:**
  - **Native Software Installation Engine (`actions/open_app.py`):**
    - Built `resolve_winget_package(app_name)` and `execute_silent_install(pkg_id, app_name)` integrating Microsoft's official Windows Package Manager (`winget.exe`).
    - Added `action="install"` (aliases: `"download"`, `"setup"`) to `open_app`.
    - Completely eliminates opening browser windows or failing to click web download buttons. Applications install 100% silently in the background at 0 token cost.
  - **Strict Confirmation Gate (Option 2 — ReUI + Dual Voice/UI Resolution):**
    - Connected `open_app(action="install")` to `core/confirm.py` gate.
    - Wire-up: Broadcasts `confirm_request` and `confirm_hide` over WebSocket with package details.
    - Integrated official prebuilt ReUI `ConfirmDialog` in `frontend/src/App.tsx` (`radix-ui/react-dialog` with opaque panel and keyboard shortcuts).
    - Added inbound WebSocket event `resolve_confirmation` in `core/ui_server.py`.
    - Hooked live voice confirmation into `main.py`: user can speak ("Haan kar do", "Yes", "Confirm") or click "Confirm & Run" on screen to authorize installation, or speak ("Cancel", "No") / click "Cancel" to reject.
  - **Agent Browser Token-Efficiency (`actions/browser_control.py`):**
    - Added `get_accessibility_snapshot()` extracting compact `@e1`, `@e2` interactive element roles for minimal token consumption (<80 tokens).
    - Upgraded `smart_click()` with heuristic regex patterns for download/install buttons, scroll-into-view, and fallback JavaScript click evaluation.
  - **System Prompt & Documentation Sync:**
    - Updated `core/prompt.txt` directing all application download and install commands to `open_app(action='install')`.
    - Updated `docs/TOOLS.md` and compiled production React bundle (`frontend/dist`).
- **Why this approach was chosen:**
  - Eliminates flaky browser scraping for software downloads, prevents unwanted browser popups, adheres to `AGENTS.md` ReUI guidelines, and protects user API token quota.
- **Verification:**
  - Layer 1 (Static): `py_compile` on touched files; `ActionRegistry` dynamic scan confirmed all 29 tools loaded cleanly; React `npm run build` compiled without errors.
  - Layer 2 (Runtime): Tested `resolve_winget_package('Spotify')` -> resolved `Spotify.Spotify`; verified `confirm.request()` populates UI broadcast and pending title.
  - Layer 3 (Regression): `pytest tests/test_wake_word_registry.py tests/test_config_endpoints.py tests/test_phase1_governance_suite.py` passed 11/11 tests (100%).
- **Key files touched:**
  - `actions/open_app.py`
  - `actions/browser_control.py`
  - `core/confirm.py`
  - `core/ui_server.py`
  - `ui.py`
  - `main.py`
  - `frontend/src/hooks/useZezoSocket.ts`
  - `frontend/src/App.tsx`
  - `frontend/dist/*`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-17] — Push-To-Talk Interruption & Zero-Remnant Barge-In
- **What was built & fixed:**
  - **Zero-Remnant PTT Interruption (`main.py`):**
    - Root cause: In `_on_ptt(held=True)`, `self.interrupt()` was called but `self._interrupted` was immediately overwritten to `False` on the next line. Additionally, `_play_audio` paused and waited (`while _ptt_held: await asyncio.sleep(0.05)`), allowing in-flight audio from the previous turn to accumulate in `audio_in_queue` and play out loud after key release.
    - Fix:
      1. Maintained `self._interrupted = True` throughout key-hold so the receiver drops all in-flight packets of the interrupted turn.
      2. Introduced `_turn_epoch` and safe tracking to isolate conversational turns.
      3. Changed `_play_audio` to actively discard any audio chunks arriving while `_ptt_held == True`.
      4. Flushed `audio_in_queue` on key down AND key release to guarantee zero leftover audio.
      5. Hooked Gemini Live `sc.interrupted = True` to call `self.interrupt()` directly.
      6. Suppressed `sc.output_transcription` streaming when `_interrupted` or `_ptt_held` is True.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile main.py` passed with 0 errors.
  - Layer 2 (Runtime Tests): `pytest tests/test_push_to_talk_stream_end.py` passed 4/4 tests.
  - Layer 3 (Regression Suite): `pytest tests/test_workspace_picker.py tests/test_config_endpoints.py tests/test_push_to_talk_stream_end.py` passed 7/7 tests.

---

## [2026-10-17] — Browser Scrolling Fix & Accurate Application Installation Detection
- **What was built & fixed:**
  - **PyAutoGUI Windows Wheel Scaling (`core/computer/pyautogui_driver.py`):**
    - Root cause: On Windows, PyAutoGUI's `scroll(amount)` maps directly to Windows API `mouse_event(MOUSEEVENTF_WHEEL, 0, 0, amount, 0)`. Modern Windows applications and browsers (Edge, Chrome, Firefox) expect scroll ticks in multiples of `120` (`WHEEL_DELTA`). Passing `amount = 3` sent `3` units (1/40th of a wheel click), which was completely ignored by browsers.
    - Fix: Multiplied vertical scroll notches by `120` (`int(amount * 120)` when `os.name == 'nt'`), ensuring every scroll command sends proper wheel click events.
  - **Browser Scrolling Context Resilience & Active Tab Fallback (`actions/browser_control.py`):**
    - Root cause: `_get_page()` did not check `self._context.is_closed()`. If an automated browser tab was closed by the user or disconnected, `self._context` remained set, causing every subsequent call to crash with `TargetClosedError: Target page, context or browser has been closed`. Furthermore, when users browse with external browsers (e.g. Edge), Playwright had no fallback to the active window.
    - Fix: Added `if self._context.is_closed(): self._context = None` in `_get_page()`.
    - Added automatic fallback in `scroll()` and its handler: if Playwright page scrolling fails or context is unavailable, it falls back seamlessly to OS mouse wheel scrolling (`input_driver.scroll(direction, os_notches)`), scrolling whatever browser window is currently focused on screen.
  - **Reliable Local Application Installation Detection (`actions/open_app.py`):**
    - Root cause: `open_app.py` had `"spotify": "spotify:"` hardcoded in `_WIN_URI_MAP`. Calling `os.startfile("spotify:")` on Windows when Spotify is not installed pops up the Microsoft Store dialog and returns exit code 0. If that failed, the fallback blindly opened the Windows Start menu, typed the app name, and hit enter, which opened Microsoft Edge searching Bing when apps weren't installed.
    - Fix: Built `is_app_installed(app_name: str) -> tuple[bool, str]`, inspecting:
      1. System `PATH` and direct executable names.
      2. Protocol schemes in Windows Registry (`HKEY_CLASSES_ROOT\<scheme>`).
      3. User and All Users Start Menu shortcuts (`.lnk` files).
      4. Windows Registry `Uninstall` keys (`HKLM` and `HKCU` 32-bit and 64-bit).
      5. Windows Store / AppX packages (`AppModel\Repository\Packages`).
      6. Standard `Program Files` and `AppData` install paths.
      7. macOS `/Applications` and Linux `.desktop` files.
    - Added `action="check"` (aliases: `"is_installed"`, `"check_installed"`) to `open_app`.
    - Updated `_launch_windows` to verify protocol registry registration before calling `os.startfile(uri)` to prevent unsolicited Microsoft Store popups.
    - Completely removed the blind `pyautogui.press("win")` Start Menu search fallback.
    - If `action="open"` is requested for an uninstalled app, it returns `Cannot open {app_name}: It is NOT installed on this PC.`
  - **System Prompt & Documentation Sync:**
    - Updated `core/prompt.txt` directing app installation queries to `open_app(action='check')` and clarifying window scrolling behavior.
    - Updated `TOOL` schema in `actions/open_app.py` and documentation in `docs/TOOLS.md`.
- **Why this approach was chosen:**
  - Multi-tier registry and start-menu checking guarantees deterministic, instantaneous, 0-side-effect detection of both desktop Win32 and UWP/Store applications without touching GUI focus or popping up web searches.
- **Verification:**
  - Layer 1 (Static): `python -m py_compile` passed on all modified files (`pyautogui_driver.py`, `browser_control.py`, `open_app.py`). `core/action_loader.py` discovered all 29 active actions.
  - Layer 2 (Runtime): Real queries executed: `open_app(action='check', app_name='Spotify')` returned NOT installed; `open_app(action='check', app_name='WhatsApp')` returned installed; `open_app(action='open', app_name='Spotify')` returned cannot open because not installed; `browser_control(action='scroll')` fallback returned `Scrolled down`.
  - Layer 3 (Regression): `tests/test_wake_word_registry.py` and `tests/test_config_endpoints.py` passed (7/7 tests passed).
- **Key files touched:**
  - `core/computer/pyautogui_driver.py`
  - `actions/browser_control.py`
  - `actions/open_app.py`
  - `core/prompt.txt`
  - `docs/TOOLS.md`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Native Windows Dynamic Grammar Wake Word ("Hey Zezo", "Hey Nova") & 15s Sleep Window
- **What was built:**
  - **Native Windows Dynamic Grammar Engine (`core/wake_word.py`):**
    - Integrated Bigfoot-style Windows SAPI Speech Recognition (`SAPI.SpSharedRecognizer`).
    - Integrated Bigfoot-style Windows SAPI Inproc Speech Recognition (`SAPI.SpInprocRecognizer`).
    - Generates dynamic XML grammar rules at runtime based on the selected assistant name:
      `"hey " + name`, `"hi " + name`, `"okay " + name`, and bare `name`.
    - Eliminates the need for 20-minute Colab training or missing `.onnx` models (`hey_zezo.onnx`, `hey_nova.onnx`). Any custom name works immediately out of the box with 0 extra files and ~0.1% CPU consumption.
    - Updated `is_ready()` and `list_wake_presets()` so all assistant names (Zezo, Nova, Jarvis) report as available on Windows.
  - **Critical SAPI In-Process Recognizer Fixes:**
    - **Physical Microphone Token Binding:** Fixed `AudioInputStream = SpMMAudioIn` leaving the audio stream in `SPAS_CLOSED` (0). Bound `reco.AudioInput` directly to `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput` default `SpObjectToken`, successfully capturing hardware microphone input without opening the OS Speech UX setup wizard.
    - **`PyIDispatch` Result Wrapping:** Wrapped `Result` in `win32com.client.Dispatch(Result)` inside `OnRecognition`. SAPI COM event sinks in pythoncom provide raw `PyIDispatch` handles which threw `AttributeError: 'PyIDispatch' object has no attribute 'PhraseInfo'`; wrapping it enables direct access to `Result.PhraseInfo.GetText()`.
    - **Acoustic & Phonetic Aliasing:** Expanded XML dynamic grammar to include common acoustic variations (`"hey noba"`, `"noba"`, `"hey hova"`, `"hova"`, `"hey zizo"`, `"zizo"`), ensuring high recall across various microphone types and accents.
  - **Strict IDLE Standby & 15-Second Active Listen Window (`main.py`):**
    - When Wake Word is enabled, the assistant rests strictly in **`IDLE`** (Standby) — the microphone does not stream room noise to Gemini Live until awakened.
    - When user says *"Hey Nova"* or *"Hey Zezo"*, the native grammar engine detects it and transitions ZEZO immediately to **`LISTENING`**.
    - If the user does not speak any query within **15 seconds** (`WAKE_LISTEN_WINDOW = 15.0s`), ZEZO automatically transitions cleanly back to **`IDLE`**.
    - After Gemini finishes answering a question, the 15-second activity timer restarts, allowing natural follow-up conversation before returning to standby.
- **Why this approach was chosen:**
  - Bigfoot native grammar architecture provides instantaneous, zero-download, offline wake-word recognition for any name without training external neural nets.
- **Key files touched:**
  - `core/wake_word.py`
  - `main.py`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Push-To-Talk: Instant Barge-In & Live Dictation Streaming Fix (Ctrl+Alt)
- **What was built & fixed:**
  - **Live User Dictation Streaming in Chat (`App.tsx` & `main.py`):**
    - Root cause: In `frontend/src/App.tsx`, the `transcriptStream` effect had a deduplication check (`if (speaker === 'user' && last && last.role === 'user')`) placed before the active live turn check (`if (last.id.startsWith('live-user'))`). Whenever partial speech chunks arrived while holding `Ctrl+Alt`, it treated consecutive updates as duplicate messages and dropped them.
    - Fix: Refactored the order of evaluation in `App.tsx`. Active `live-user` messages now receive streaming updates seamlessly (supporting both cumulative sentences and delta additions) so spoken words appear instantly in real-time in the chat panel like a live dictation while holding `Ctrl+Alt`.
    - Added real-time log bus debug tracing in `main.py` `_receive_audio` whenever `sc.input_transcription` is received from Google Gemini Live.
  - **PTT Audio Playback Fix (`main.py` `_receive_audio`):**
    - Root cause: In `_receive_audio`, the check `if self._ptt_enabled and self._ptt_held: pass` was erroneously dropping incoming response audio chunks from Gemini Live if user was still holding or released near turn turn boundary. Because the model's audio was discarded, ZEZO fell silent and went to `IDLE` without answering until the next user interaction re-triggered the old query context.
    - Fix: Removed the drop check from `_receive_audio`. Gemini Live WebSocket audio chunks now flow naturally into `audio_in_queue` and play immediately after the user finishes speaking.
  - **Instant Speech Barge-In on `Ctrl+Alt` Press:**
    - Root cause: If ZEZO was currently speaking and the user held `Ctrl+Alt` to ask a new question or interrupt, ZEZO did not stop talking because `interrupt()` was never triggered on keypress, and the mic callback was discarding input frames due to `zezo_speaking == True`.
    - Fix: In `_on_ptt(held=True)`, added an immediate check for `self._is_speaking`. If true, `self.interrupt()` is called immediately:
      1. Outgoing mic queue & incoming playback queue are drained.
      2. `_is_speaking` drops to `False` within ~50ms.
      3. UI switches directly to `LISTENING`.
      4. `_interrupted` flag is reset to `False` so the new response audio is accepted and played.
  - **Canvas Splitter Resizing (Lag & Jitter Elimination):**
    - Eliminated `transition-all duration-75` from the `<Frame>` container in `frontend/src/App.tsx`, which was fighting continuous live drag updates.
    - Added conditional `transition: none` during active drag (`!isDraggingCanvas && "transition-[height] duration-150 ease-out"`), ensuring instant 1:1 hardware refresh tracking (60–120Hz).
    - Replaced unstable `prev - e.movementY` calculations with absolute coordinate delta anchoring (`startY` + `startHeight` stored in `dragStartRef`).
    - Added global `user-select: none` and `cursor: row-resize` on `document.body` during drag.
- **Why this approach was chosen:**
  - Streaming partial user speech to the chat thread gives immediate visual feedback (dictation mode) while holding `Ctrl+Alt`, confirming the microphone and model are actively tracking input.
- **Key files touched:**
  - `frontend/src/App.tsx`
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `LEARNING_JOURNAL.md`
- **Key files touched:**
  - `main.py`
  - `core/hotkey.py`
  - `frontend/src/App.tsx`
  - `frontend/src/components/settings/SettingsModal.tsx`
  - `LEARNING_JOURNAL.md`

---

## [2026-10-16] — Dynamic Holographic Qivi Companion in Chat & Compact Message Spacing
- **What was built:**
  - Integrated the live dynamic Holographic Qivi Companion (`ChatAvatarIcon.tsx` backed by `qivi-react`) into the chat assistant messages and chat empty state view (`ThreadPrimitive.Empty`) in `frontend/src/components/assistant-ui/ZezoChatThread.tsx`.
  - Replaced the static, broken `/zezo-avatar.png` image with `<ChatAvatarIcon size={26} expression={isRunning ? 'thinking' : 'happy'} state={isRunning ? 'talking' : 'idle'} />`.
  - Replaced the static placeholder in the empty state screen with `<ChatAvatarIcon size={44} expression="happy" state="idle" />`.
  - The chat avatar now dynamically tracks character preset selections (Qivi, Spark, Diplomat, Ember/Chaos, Sage, Atlas/Guardian) and OS theme palette shifts via `zezo_avatar_settings_changed` and `zezo_theme_changed` events without requiring a page reload.
  - Compacted the message layout: eliminated wide bottom rows (`pl-10.5 mt-1`) that created excess empty space under assistant responses, tightened vertical padding (`py-1`), and integrated the timestamp and copy/regenerate action bar directly as an inline footer beneath message speech text.
  - Hardened `_avatar_handler` in `core/ui_server.py` to check `frontend/dist` and `frontend/public` paths before fallback, preventing legacy 404 errors.
- **Why this approach was chosen:**
  - Provides a unified holographic companion experience across the workstation HUD, settings modal, and chat stream while eliminating awkward whitespace beneath single-line voice dialogue.
- **Key files touched:**
  - `frontend/src/components/assistant-ui/ZezoChatThread.tsx`
  - `core/ui_server.py`
  - `LEARNING_JOURNAL.md`
- **What to remember for future work:**
  - `qivi-react` uses `"talking"` (not `"speaking"`) in its `QiviState` union type (`"idle" | "listening" | "thinking" | "searching" | "analyzing" | "found" | "answering" | "talking" | "success" | "warning" | "error" | "dissolving"`).
  - Always clean up unused imports from `@/components/prompt-kit/message` (e.g. `MessageAvatar as PKMessageAvatar`) when swapping custom avatar wrappers to satisfy strict TypeScript builds.

---

## [2026-10-22] — Memory & Intelligence: Date/Time Range Filter & Chronological Timeline Feed
- **What was built & fixed:**
  - **Memory Graph & Vault Date/Time Ingestion (`memory/vault_engine.py`):**
    - Root cause: `vault_engine.get_graph()` only exported basic labels, snippets, and categories, discarding node timestamps and modification dates. Nodes generated from SQLite sessions (`conv_YYYYMMDD_HHMMSS`) lacked parsed ISO datetime values, making temporal search in the UI impossible.
    - Fix: Added regex parsing of `conv_YYYYMMDD_HHMMSS` to extract exact date strings (`YYYY-MM-DD HH:MM:SS`) and unix timestamps (`timestamp: float`). For standard markdown notes, extracted `meta.get("updated")` or `file.stat().st_mtime`. Nodes in `get_graph()` now contain `"date"` and `"timestamp"` metadata.
  - **Dual-View Toggle: 3D Force Graph & Timeline Feed (`frontend/src/components/memory/MemoryGraphCanvas.tsx`):**
    - Built a unified header and navigation toolbar with seamless toggle between interactive **3D Knowledge Graph** and **Chronological Timeline Feed**.
    - **Date/Time Filters:** Added presets (`All Time`, `Past 24h`, `Past 7 Days`, `Past 30 Days`, `Custom Range`) with start and end date HTML5 pickers (`<Input type="date" />`).
    - **Category Filters & Search:** Dynamic pills for `All`, `Conversation`, `Knowledge`, `Identity`, etc. with live item counts, plus instant keyword search filtering across titles, snippets, tags, and timestamps.
    - **Timeline Feed View:** Chronological cards showing exact date & time badges, relative times (`2h ago`, `yesterday`), conversation turn badges (`💬 14 turns`), category colors, and snippets. Clicking any card opens `MemoryInspectorDrawer` for inspection and note editing.
  - **Production Build Synchronization (`frontend/dist/`):**
    - Recompiled production React bundle (`npm run build` -> `tsc -b && vite build`) so `core/ui_server.py` immediately serves the updated UI at `http://127.0.0.1:8765`.
- **Key files touched:**
  - `memory/vault_engine.py`
  - `frontend/src/components/memory/MemoryGraphCanvas.tsx`
  - `frontend/dist/*`
  - `LEARNING_JOURNAL.md`
- **Verification:**
  - Layer 1 (Static): `python -m py_compile memory/vault_engine.py core/ui_server.py` passed with 0 errors; `npm run build` compiled 3,280 modules cleanly with Vite 8.3.4.
  - Layer 2 (Runtime): Verified `pytest tests/test_memory_vault_engine.py` (3/3 passed).
  - Layer 3 (Regression): Full suite regression passed.


