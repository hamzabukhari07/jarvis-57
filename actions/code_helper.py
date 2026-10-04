import subprocess
import sys
import json
import re
import time
from pathlib import Path

for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR           = get_base_dir()
API_CONFIG_PATH    = BASE_DIR / "config" / "api_keys.json"
DESKTOP            = Path.home() / "Desktop"
MAX_BUILD_ATTEMPTS = 3
# Model choice lives in core/gemini.py, and so does the timeout and the
# fallback ladder. Writing a model name here is what left this file hanging
# forever whenever that one alias was unwell.
from core import gemini


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _generate_text(prompt: str, system: str | None = None) -> str:
    """Background code/text generation via the provider router
    (Groq → Gemini → Ollama). Writing and fixing code is the reasoning tier, so
    a 60s deadline because a whole file can come back."""
    from core.llm_router import generate_text
    return generate_text(prompt, system=system, tier="smart", timeout_ms=60_000)


def _clean_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _resolve_path(raw_path: str, language: str = "") -> Path:
    """Intelligently resolve any file or save path without duplicate Desktop/ nesting."""
    ext_map = {
        "python": ".py", "py": ".py",
        "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts",
        "html": ".html", "css": ".css",
        "java": ".java", "cpp": ".cpp", "c": ".c",
        "bash": ".sh", "shell": ".sh", "powershell": ".ps1",
        "sql": ".sql", "json": ".json", "rust": ".rs", "go": ".go",
    }
    raw = (raw_path or "").strip().strip("'\"`")
    if not raw:
        ext = ext_map.get((language or "python").lower(), ".py")
        return DESKTOP / f"jarvis_code{ext}"

    # Handle ~
    if raw.startswith("~"):
        return Path(raw).expanduser().resolve()

    p = Path(raw)
    if p.is_absolute():
        return p

    # Strip redundant "desktop/" or "desktop\" prefixes
    norm = raw.replace("\\", "/")
    if norm.lower().startswith("desktop/"):
        rel_sub = norm[8:].lstrip("/")
        return DESKTOP / rel_sub

    # If file exists directly on Desktop, return it
    if (DESKTOP / raw).exists():
        return DESKTOP / raw

    # If file exists in a nested Desktop/ subfolder from previous runs
    if (DESKTOP / "Desktop" / raw).exists():
        return DESKTOP / "Desktop" / raw

    # If repo context exists and file is in repo
    try:
        from core.repo_context import get_last_repo
        last_repo = get_last_repo()
        if last_repo and (Path(last_repo) / raw).exists():
            return Path(last_repo) / raw
    except Exception:
        pass

    # If file exists relative to CWD
    if p.exists():
        return p.resolve()

    # Default for new files: save directly on Desktop
    return DESKTOP / raw


def _read_file(file_path: str) -> tuple[str, str]:
    if not file_path:
        return "", "No file path provided."
    p = _resolve_path(file_path)
    if not p.exists():
        return "", f"File not found: {file_path}"
    try:
        return p.read_text(encoding="utf-8"), ""
    except Exception as e:
        return "", f"Could not read file: {e}"


def _save_file(path: Path, content: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to: {path}"
    except Exception as e:
        return f"Could not save: {e}"


def _preview(code: str, lines: int = 10) -> str:
    all_lines = code.splitlines()
    preview   = "\n".join(all_lines[:lines])
    suffix    = f"\n... ({len(all_lines) - lines} more lines)" if len(all_lines) > lines else ""
    return preview + suffix


def _has_error(output: str) -> bool:
    error_signals = ["error", "exception", "traceback", "syntaxerror",
                     "nameerror", "typeerror", "stderr", "failed", "crash"]
    return any(s in output.lower() for s in error_signals)


def _take_screenshot() -> Path | None:
    try:
        import pyautogui
        screenshot_path = Path.home() / "Desktop" / f"jarvis_debug_{int(time.time())}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(screenshot_path))
        print(f"[Code] 📸 Screenshot: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"[Code] ⚠️ Screenshot failed: {e}")
        return None


def _image_to_base64(path: Path) -> str:
    import base64
    return base64.b64encode(path.read_bytes()).decode("utf-8")


_VALID_INTENTS = {"write", "edit", "explain", "run", "build", "screen_debug", "optimize"}


def _detect_intent(description: str, file_path: str, code: str) -> str:
    """
    Language-independent intent detection — NO fixed keyword list.
    Whatever language the user speaks, the description is classified by
    Gemini. If the API is unreachable, it falls back to language-agnostic
    structural hints (does the file exist on disk, was code provided).
    """
    desc        = (description or "").strip()
    file_exists = bool(file_path) and Path(file_path).exists()

    if desc:
        try:
            ctx = []
            if file_path:
                ctx.append(f"a file path is provided (exists on disk: {file_exists})")
            if code:
                ctx.append("an inline code snippet is provided")
            prompt = (
                "Classify a coding assistant request into exactly ONE intent word.\n"
                "The request may be written in ANY language.\n\n"
                f"Request: {desc}\n"
                + (f"Context: {'; '.join(ctx)}\n" if ctx else "")
                + "\nIntents:\n"
                "  write        = create new code from scratch\n"
                "  edit         = modify an existing file\n"
                "  explain      = describe what given code/file does\n"
                "  run          = execute an existing file\n"
                "  build        = write code, run it, and iterate until it works\n"
                "  screen_debug = analyze an error currently visible on the user's screen\n"
                "  optimize     = refactor / clean up / speed up existing code\n\n"
                "Reply with ONLY the intent word, nothing else."
            )
            ans = _generate_text(prompt).strip().lower()
            ans = ans.strip("`'\". \n")
            if ans in _VALID_INTENTS:
                return ans
        except Exception as e:
            print(f"[Code] Intent classification failed ({e}) — structural fallback")

    # Structural fallback — not tied to any language
    if file_exists:
        return "edit" if desc else "explain"
    if code:
        return "explain"
    return "write"

def _write(description: str, language: str, output_path: str, player=None) -> tuple[str, Path]:
    lang = language or "python"

    prompt = f"""You are an expert {lang} developer.
Write clean, working, well-commented {lang} code for the description below.

Rules:
- Output ONLY the code. No explanation, no markdown, no backticks.
- Add helpful inline comments.
- Handle errors and edge cases properly.
- Use modern best practices.
- For web scraping, web requests, or HTTP downloads (e.g. requests, urllib, aiohttp), ALWAYS include a realistic browser User-Agent header (e.g. headers={{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}}) to prevent 403 Forbidden errors.

Description: {description}

Code:"""

    raw_code = _generate_text(prompt)
    code = _clean_code(raw_code)
    path = _resolve_path(output_path, lang)
    _save_file(path, code)
    return code, path


def _fix_code(code: str, error_output: str, description: str) -> str:
    prompt = f"""You are an expert debugger.
The code below failed with the following error. Fix it.
Return ONLY the corrected code — no explanation, no markdown, no backticks.
If the error is 403 Forbidden or a scraping block, add realistic browser User-Agent headers.

Original goal: {description}

Error:
{error_output[:2000]}

Broken code:
{code}

Fixed code:"""

    raw_code = _generate_text(prompt)
    return _clean_code(raw_code)


def _run_file(path: Path, args: list, timeout: int) -> str:
    interpreters = {
        ".py":  [sys.executable],
        ".js":  ["node"],
        ".ts":  ["ts-node"],
        ".sh":  ["bash"],
        ".ps1": ["powershell", "-File"],
        ".rb":  ["ruby"],
        ".php": ["php"],
    }
    interp = interpreters.get(path.suffix.lower())
    if not interp:
        return f"No interpreter for {path.suffix}."

    try:
        result = subprocess.run(
            interp + [str(path)] + (args or []),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(path.parent)
        )
        output = result.stdout.strip()
        error  = result.stderr.strip()
        parts  = []
        if output: parts.append(f"Output:\n{output}")
        if error:  parts.append(f"Stderr:\n{error}")
        return "\n\n".join(parts) if parts else "Executed with no output."

    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except FileNotFoundError:
        return f"Interpreter not found: {interp[0]}."
    except Exception as e:
        return f"Execution error: {e}"


def _build(description, language, output_path, args, timeout, speak=None, player=None) -> str:
    if not description:
        return "Please describe what you want me to build, sir."

    if player:
        player.write_log("[Code] Build started...")

    lang = language or "python"

    try:
        code, path = _write(description, lang, output_path, player)
        print(f"[Code] ✅ Written: {path}")
    except Exception as e:
        msg = f"Could not write initial code: {e}"
        if speak: speak(msg)
        return msg

    last_output = ""
    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        print(f"[Code] 🔄 Attempt {attempt}/{MAX_BUILD_ATTEMPTS}")
        if player:
            player.write_log(f"[Code] Attempt {attempt}...")

        last_output = _run_file(path, args, timeout)

        if not _has_error(last_output):
            msg = (
                f"Build complete, sir. "
                f"The code is working after {attempt} attempt{'s' if attempt > 1 else ''}. "
                f"Saved to {path}."
            )
            if speak: speak(msg)
            return f"{msg}\n\nOutput:\n{last_output}"

        print(f"[Code] ⚠️ Error on attempt {attempt}, fixing...")
        if player:
            player.write_log(f"[Code] Fixing (attempt {attempt})...")

        try:
            code = _fix_code(code, last_output, description)
            _save_file(path, code)
        except Exception as e:
            msg = f"Could not fix code on attempt {attempt}: {e}"
            if speak: speak(msg)
            return msg

    msg = (
        f"I was unable to build a working version after {MAX_BUILD_ATTEMPTS} attempts, sir. "
        f"The last error was: {last_output[:200]}"
    )
    if speak: speak(msg)
    return f"{msg}\n\nLast code saved to: {path}"

def _write_action(description, language, output_path, code_str="", player=None) -> str:
    path = _resolve_path(output_path, language)
    
    # 1. If explicit code string was already provided in parameters, save it immediately
    if code_str and str(code_str).strip():
        code = _clean_code(code_str)
        _save_file(path, code)
        print(f"[Code] ✅ Written directly: {path}")
        if player and hasattr(player, "show_content"):
            player.show_content(f"CODE WRITTEN · {path.name}", code)
        return f"Code written. Saved to: {path}\n\nPreview:\n{_preview(code)}"

    # 2. Otherwise generate code via Groq / LLM router
    if not description:
        return "Please describe what you want me to write, sir."
    if player:
        player.write_log("[Code] Writing code via Groq LPU...")
    try:
        code, path = _write(description, language, output_path, player)
        print(f"[Code] ✅ Written: {path}")
        if player and hasattr(player, "show_content"):
            player.show_content(f"CODE WRITTEN · {path.name}", code)
        return f"Code written. Saved to: {path}\n\nPreview:\n{_preview(code)}"
    except Exception as e:
        return f"Could not generate code: {e}"


def _edit_action(file_path, instruction, player) -> str:
    if not file_path:
        return "Please provide a file path to edit, sir."
    if not instruction:
        return "Please describe what change to make, sir."

    content, err = _read_file(file_path)
    if err:
        return err

    if player:
        player.write_log("[Code] Editing file...")

    prompt = f"""You are an expert code editor.
Apply the following change to the code below.
Return ONLY the complete updated code — no explanation, no markdown, no backticks.

Change: {instruction}

Original code:
{content}

Updated code:"""

    try:
        raw_code = _generate_text(prompt)
        edited   = _clean_code(raw_code)
    except Exception as e:
        return f"Could not edit code: {e}"

    status = _save_file(Path(file_path), edited)
    print(f"[Code] ✅ Edited: {file_path}")
    return f"File edited. {status}\n\nPreview:\n{_preview(edited)}"


def _explain_action(file_path, code, player) -> str:
    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to explain, sir."

    if player:
        player.write_log("[Code] Analyzing code...")

    prompt = f"""Explain what this code does in simple, clear language.
Focus on: what it does, how it works, and any important details.
Be concise — 3 to 6 sentences maximum.

Code:
{code[:4000]}

Explanation:"""

    try:
        return _generate_text(prompt).strip()
    except Exception as e:
        return f"Could not explain code: {e}"


def _run_action(file_path, args, timeout, player) -> str:
    if not file_path:
        return "Please provide a file path to run, sir."
    p = _resolve_path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"
    if player:
        player.write_log(f"[Code] Running {p.name}...")
    return _run_file(p, args, timeout)


def _optimize_action(file_path, code, language, output_path, player) -> str:

    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to optimize, sir."

    if player:
        player.write_log("[Code] Optimizing code...")

    lang  = language or "python"
    prompt = f"""You are an expert {lang} developer and code reviewer.
Optimize the following code for:
1. Performance — eliminate unnecessary operations, use efficient data structures
2. Readability — clear variable names, proper formatting, logical structure
3. Best practices — modern {lang} patterns, error handling, type hints if applicable
4. Remove dead code, redundant comments, and unnecessary complexity

Return ONLY the optimized code — no explanation, no markdown, no backticks.

Original code:
{code[:6000]}

Optimized code:"""

    try:
        raw_code  = _generate_text(prompt)
        optimized = _clean_code(raw_code)
    except Exception as e:
        return f"Could not optimize code: {e}"

    # Save
    save_path = _resolve_path(file_path or output_path, lang)
    status = _save_file(save_path, optimized)
    print(f"[Code] ✅ Optimized: {save_path}")

    original_lines  = len(code.splitlines())
    optimized_lines = len(optimized.splitlines())
    diff = original_lines - optimized_lines

    return (
        f"Code optimized. {status}\n"
        f"Lines: {original_lines} → {optimized_lines} "
        f"({'−' if diff > 0 else '+'}{abs(diff)} lines)\n\n"
        f"Preview:\n{_preview(optimized)}"
    )


def _screen_debug_action(description, file_path, player, speak=None) -> str:

    if player:
        player.write_log("[Code] Taking screenshot for analysis...")

    print("[Code] 📸 Capturing screen for debug...")


    screenshot_path = _take_screenshot()
    if not screenshot_path:
        return "Could not take screenshot, sir. Please make sure PyAutoGUI is installed."


    file_content = ""
    if file_path:
        file_content, err = _read_file(file_path)
        if err:
            print(f"[Code] ⚠️ Could not read file: {err}")

    try:
        from google.genai import types

        image_bytes  = screenshot_path.read_bytes()
        image_base64 = _image_to_base64(screenshot_path)

        user_question = description or "What error or problem do you see on the screen? How can it be fixed?"

        context = ""
        if file_content:
            context = f"\n\nAdditionally, here is the related file content:\n```\n{file_content[:4000]}\n```"

        analysis_prompt = f"""You are an expert programmer and debugger analyzing a screenshot.

User's question: {user_question}{context}

Please:
1. Identify any errors, exceptions, or problems visible on the screen
2. Explain what is causing the problem in simple terms
3. Provide a concrete fix or solution
4. If there's code visible, show the corrected version

Be specific and actionable. If you see an error message, quote it exactly."""

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            analysis_prompt,
        ]

        response = gemini.call(contents, tier=gemini.SMART, timeout_ms=45_000)
        if response is None:
            return "Sir, I couldn't reach Gemini to analyse that screenshot."

        analysis = (response.text or "").strip()
        print(f"[Code] ✅ Screen analysis complete")

        try:
            screenshot_path.unlink()
        except Exception:
            pass

        if file_path and file_content:

            code_match = re.search(r"```[a-zA-Z]*\n(.*?)```", analysis, re.DOTALL)
            if code_match:
                fixed_code = code_match.group(1).strip()
                save_path  = Path(file_path)
                _save_file(save_path, fixed_code)
                analysis += f"\n\n✅ Fixed code has been saved to: {file_path}"
                print(f"[Code] ✅ Fixed code saved: {file_path}")

        return analysis

    except Exception as e:

        try:
            screenshot_path.unlink()
        except Exception:
            pass
        return f"Screen analysis failed: {e}"


_SERVER_COMMAND_KEYWORDS = {
    "uvicorn", "gunicorn", "runserver", "flask run", "npm start", "npm run dev",
    "yarn dev", "vite", "http.server", "fastapi dev", "next dev"
}

def _execute_command(command: str, cwd: str = "", timeout: int = 60, player=None) -> str:
    cmd_str = (command or "").strip()
    if not cmd_str:
        return "No command provided to execute, sir."

    target_dir = Path.home() / "Desktop"
    if cwd:
        try:
            p = _resolve_path(cwd)
            if p.exists() and p.is_dir():
                target_dir = p
            elif p.parent.exists():
                target_dir = p.parent
        except Exception:
            pass

    if player:
        player.write_log(f"[Code] Executing command: {cmd_str}")

    print(f"[Code] ⚡ Running background command: {cmd_str} in {target_dir}")
    
    # 1. Daemon / Long-running server command detection (uvicorn, dev servers, etc.)
    cmd_lower = cmd_str.lower()
    is_server = any(k in cmd_lower for k in _SERVER_COMMAND_KEYWORDS) or "--reload" in cmd_lower

    if is_server:
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                cmd_str,
                shell=True,
                cwd=str(target_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags
            )
            time.sleep(0.5)
            if proc.poll() is None:
                return f"Server command started and running in background (`{cmd_str}`). Process ID: {proc.pid}. Project directory: {target_dir}"
            else:
                return f"Server command exited early with return code {proc.returncode}."
        except Exception as e:
            return f"Failed to start server command: {e}"

    # 2. Short / build commands (pip install, venv, git init, etc.)
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        res = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=min(timeout, 120),
            cwd=str(target_dir),
            creationflags=flags
        )
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        parts = []
        if out: parts.append(f"Output:\n{out}")
        if err: parts.append(f"Stderr:\n{err}")

        result_str = "\n\n".join(parts) if parts else "Executed silently with exit code 0."
        return f"Executed command in background (`{cmd_str}`). Exit code: {res.returncode}\n\n{result_str}"
    except subprocess.TimeoutExpired:
        return f"Command '{cmd_str}' timed out after {timeout} seconds."
    except Exception as e:
        return f"Command execution error: {e}"


def code_helper(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None
) -> str:
    """
    Called from main.py.

    parameters:
        action      : write | edit | explain | run | command | build | screen_debug | optimize | auto
        description : What the code should do / what change to make / what problem to analyze
        command     : CLI / Terminal command to run in background (for action='command')
        language    : Programming language (default: python)
        output_path : Where to save — user specifies full path or filename
        file_path   : Path to existing file (edit / explain / run / build / optimize)
        code        : Raw code string (explain/optimize without a file)
        args        : CLI argument list or command string for run/command
        timeout     : Execution timeout in seconds (default: 30)
    """
    p           = parameters or {}
    action      = p.get("action", "auto").lower().strip()
    description = (p.get("description") or p.get("task") or p.get("instruction") or "").strip()
    language    = p.get("language", "python").strip()
    output_path = (p.get("output_path") or p.get("file_path") or "").strip()
    file_path   = (p.get("file_path") or p.get("output_path") or "").strip()
    code        = (p.get("code") or p.get("code_str") or "").strip()
    args        = p.get("args", [])
    command_arg = p.get("command", "").strip()
    timeout     = int(p.get("timeout", 30))

    cmd_val = command_arg or (description if action in ("command", "execute", "exec", "terminal") else "")
    if not cmd_val and not file_path and isinstance(args, str) and args.strip():
        cmd_val = args.strip()

    if action in ("command", "execute", "exec", "terminal") or (action == "run" and not file_path and cmd_val):
        return _execute_command(cmd_val, cwd=output_path or file_path, timeout=timeout, player=player)

    if action == "auto":
        action = _detect_intent(description, file_path, code)
        print(f"[Code] 🤖 Auto-detected: {action}")

    if action in ("write", "create"):
        return _write_action(description, language, output_path, code_str=code, player=player)

    elif action == "edit":
        return _edit_action(
            file_path,
            description or p.get("instruction", ""),
            player
        )

    elif action == "explain":
        return _explain_action(file_path, code, player)

    elif action == "run":
        if not file_path and cmd_val:
            return _execute_command(cmd_val, cwd=output_path or file_path, timeout=timeout, player=player)
        return _run_action(file_path, args, timeout, player)

    elif action == "build":
        return _build(description, language, output_path, args, timeout, speak, player)

    elif action == "optimize":
        return _optimize_action(file_path, code, language, output_path, player)

    elif action == "screen_debug":
        return _screen_debug_action(description, file_path, player, speak)

    else:
        return f"Unknown action: '{action}'. Use write, edit, explain, run, command, build, optimize, or screen_debug."


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "code_helper",
    "description": "Writes, edits, explains, runs code files or executes terminal/CLI commands silently in background (e.g. venv creation, git init, pip install).",
    "risk": "code_execution",
    "enabled": True,
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "write | edit | explain | run | command | build | auto (default: auto)"
            },
            "command": {
                "type": "STRING",
                "description": "Terminal / CLI command string to execute silently in background (e.g. 'cd desktop/test_project && python -m venv venv && git init')"
            },
            "description": {
                "type": "STRING",
                "description": "What the code should do or what change to make"
            },
            "language": {
                "type": "STRING",
                "description": "Programming language (default: python)"
            },
            "output_path": {
                "type": "STRING",
                "description": "Where to save the file or working directory for command"
            },
            "file_path": {
                "type": "STRING",
                "description": "Path to existing file for edit/explain/run/build"
            },
            "code": {
                "type": "STRING",
                "description": "Raw code string for explain"
            },
            "args": {
                "type": "STRING",
                "description": "CLI arguments for run/build/command"
            },
            "timeout": {
                "type": "INTEGER",
                "description": "Execution timeout in seconds (default: 30)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": code_helper,
}
