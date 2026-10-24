# 🔧 Website Cloner — Fix Plan

> **Creator & Lead Architect:** Hamza Bukhari
> **Companion document:** [`CLONE_PIPELINE_ISSUES.md`](./CLONE_PIPELINE_ISSUES.md) — the diagnosis this plan fixes.
> **Status:** plan only. **No code has been changed yet.**
> **Issue IDs** below (1, 1a, 1b, 2…13) refer to that report.

**Two parts, and they are independent:**

| Part | What | Ship |
|---|---|---|
| **Part I** | The clone bug and its fallout — FIX-00a…00e, FIX-01…15 | A bug fix. Do not delay it for Part II. |
| **Part II** | **Code Engines** — a settings section to manage the coding CLIs ([wireframe](./wireframe-code-engines.html)) | New feature. Three phases; Phase 1 is read-only and zero-risk. |

They meet in one place: **FIX-00e** is the backend half of the gap Part II closes in the UI. The same
gap caused this incident — `agy` is installed but not signed in, and nothing anywhere said so.

---

## 0. Scope, rules and boundaries

**In scope:** the `clone_website` pipeline and the three shared seams it leans on
(`core/repo_context.py`, `actions/antigravity_agent.py`, `core/prompt.txt`) plus one frontend file.

**STRICTLY OUT OF SCOPE — do not touch:**

| Thing | Why |
|---|---|
| `tools/uncage/**` | Uncage worked correctly. Its capture was intact and faithful. **Untouched.** |
| `main.py` live audio loops (`_listen_audio`, `_receive_audio`, `_play_audio`, `_on_ptt`), `core/audio_devices.py`, `core/wake_word.py`, `core/hotkey.py` | AGENTS.md Rule 6 — hands off. Nothing here is audio/voice. |
| `core/teardown_engine.py` REA dispatch | Separate feature, working. |
| The `_synthesize_clean_website` synthesis stack | Unreachable/duplicated; Rule 3 says leave it. |

**Rules being honoured:** Rule 2 (extend, never degrade — every fix below *adds* a guard or a check;
none replaces an advanced implementation with a simpler one), Rule 3 (minimal blast radius), Rule 5
(non-blocking), Rule 7 (3-layer verification), Rule 8 (no `if/elif` ladders — use dict dispatch),
Rule 10 (journal entry at the end).

**Severity order used below:** P0 = the feature is broken or data is at risk · P1 = wrong behaviour
the user can see · P2 = hygiene.

---

## 0.5 Before / After — what actually changes

The same request, *"clone linear.app, desktop pe save karo"*, through the same code. Fix numbers refer
to the sections below.

### BEFORE (the run of 2026-10-24)

```
User: "clone linear.app, desktop pe save karo"
  |
  v
clone_website(target_dir="Desktop/linear_app_clone")
  |
  +-- Path("Desktop/linear_app_clone").resolve()      <-- resolved against ZEZO's CWD
  |     `-> D:\...\jarvis-57\Desktop\linear_app_clone      !! INSIDE THE REPO ITSELF
  |
  +-- Uncage capture -----> OK  811 files / 14.4 MB, written into the repo
  |
  +-- rebuild stage hands that folder to the engine
  |     `-- resolve(explicit=<ZEZO repo>\Desktop\linear_app_clone)
  |           `-- is_zezo_source_dir() == True
  |                 `-- X  path SILENTLY DISCARDED (no warning, no error)
  |                       `-- falls back to memory/repo_context.json
  |                             `-> ...\pytest-of-Hamza\pytest-43\...\test_proj   !! WRONG FOLDER
  |
  +-- agy runs in test_proj            (not logged in -> wrote 0 bytes, exited in 5 s)
  |     `-- _run_worker scans test_proj, sees pre-existing files
  |           `-- decides "status": "success"            !! FALSE SUCCESS
  |                 `-- ctx.on_complete()                !! CARD = DONE / 100% / "completed"
  |
  +-- prompt.txt looks for "React rebuild FAILED -"
  |     `-- X  never matches (code now says "Rebuild FAILED -")
  |           `-- model improvises: "the React rebuild failed"
  |                 `-- dispatches VERVE with NO path   !! hand-off loses the folder
  |                       `-- resolve() -> memory -> test_proj  AGAIN
  |
  +-- a Hamza Taste blueprint is injected on that agent path
  |     `-- "Image Gen Dashboard Canvas" appears in the temp folder  !! not a Linear rebuild
  |
  `-- _verify_re_artifact: no rebuilt.html in the capture folder
        `-- FAILED                                        !! card flips DONE -> FAILED
              `-- last thing opened: http://127.0.0.1:9400/antigravity_clone.html   !! raw snapshot

END STATE (measured on disk):
  D:\...\jarvis-57\Desktop\linear_app_clone\   <- clone INSIDE the repo, untracked, NOT ignored
  C:\...\pytest-43\...\test_proj\rebuilt.html  <- the real, correct rebuild - orphaned here
  C:\Users\Hamza\Desktop\                      <- still EMPTY (what the user asked for)
  long_term.json    active_project = the in-repo folder
  repo_context.json active_project = the pytest folder     <- the two stores DISAGREE
  task card logs    [object Object] x11                    <- unreadable, diagnosis blind
```

### AFTER (once Batches 0-2 land)

```
User: "clone linear.app, desktop pe save karo"
  |
  v
clone_website(target_dir="Desktop/linear_app_clone")
  |
  +-- expand_user_dir("Desktop/linear_app_clone")                 [FIX-01]
  |     `-> C:\Users\Hamza\Desktop\linear_app_clone                    OK REAL DESKTOP
  |
  +-- Uncage capture -----> OK  same 811 files, now in the right place
  |                             (repo stays clean: git status shows nothing)   [FIX-00a]
  |
  +-- rebuild stage hands that folder to the engine
  |     `-- resolve(explicit=C:\Users\Hamza\Desktop\linear_app_clone)
  |           `-- is_zezo_source_dir() == False
  |                 `-- OK used as-is
  |           (and if it ever IS in-repo again -> raises LOUDLY)    [FIX-02]
  |
  +-- agy runs in C:\Users\Hamza\Desktop\linear_app_clone
  |     +-- not logged in -> writes 0 bytes
  |     `-- _run_worker before/after diff -> "0 new files"          [FIX-03]
  |           `-- X  no "success" claim
  |                 `-- ctx.on_complete() NOT called
  |                       (the caller owns the card)                [FIX-04]
  |                       OK card still RUNNING - never lies "completed"
  |
  +-- _verify_re_artifact: no rebuilt.html
  |     `-- FAILED - but an HONEST failure that names the folder:
  |           "Rebuild FAILED - capture intact at C:\Users\Hamza\Desktop\linear_app_clone"
  |
  +-- prompt.txt matches "Rebuild FAILED - capture intact at"       [FIX-06]
  |     `-- "capture theek hai, rebuild fail hua. Folder: C:\Users\Hamza\Desktop\..."
  |           `-- offers the hand-off WITH path=...                 [FIX-08]
  |                 `-- agent works in the SAME folder
  |
  +-- no blueprint injected on a rebuild task                       [FIX-07]
  |
  `-- opens the right thing                                         [FIX-05]
        rebuild ok  -> rebuilt.html opened as file:// (NO server for one raw file)
        rebuild bad -> the capture, so the user still sees something real

END STATE:
  C:\Users\Hamza\Desktop\linear_app_clone\     <- where the user asked for it
  D:\...\jarvis-57\                            <- repo clean, git status clean
  long_term.json active_project = the REAL Desktop path,
                                 via ONE guarded writer           [FIX-12]
  task card logs = readable text                                  [FIX-09]
```

> ⚠️ **Read the two "agy" lines together.** The AFTER flow above shows the engine still not writing
> anything, because **`agy` is logged out on this machine**. That is the honest post-fix behaviour: an
> honest failure instead of a fake success. To take the *"rebuild ok → `rebuilt.html`"* branch you must
> first do **FIX-00e** (sign in to `agy`). Batches 1-2 fix *where* it runs and *what we report* —
> they do not make it *produce*.

### The one-line difference

| | Before | After |
|---|---|---|
| Where the clone lands | `<ZEZO repo>\Desktop\...` | `C:\Users\Hamza\Desktop\...` |
| Explicit folder honoured? | **Silently ignored** | Used, or a loud error |
| Engine workspace | a pytest temp dir | the folder the user named |
| CLI writes 0 bytes | reported **success** | reported **failure** |
| Task card mid-run | **DONE 100% "completed"** | still running |
| Hand-off to agent | no `path` → wrong folder | `path` always passed |
| Design blueprint | injected (new design) | not injected on a rebuild |
| What gets opened | `…/antigravity_clone.html` on a server | the real deliverable, `file://` |
| Logs in the card | `[object Object]` | readable text |
| Repo `git status` | `?? Desktop/` (14.4 MB, committable) | clean |

---

## 0.6 Does this plan still run the **real** `agy` CLI, with a prompt? — YES

Confirmed against the current source, because it is the whole point of the feature and no fix below
changes it.

**The invocation ([`actions/antigravity_agent.py:569-594`](../actions/antigravity_agent.py#L569-L594)):**

```python
cmd = [
    agy_bin,                                  # the real native binary, found at :36-46
    "-p", full_prompt,                        # ← THE PROMPT, passed as an argument
    "--add-dir", str(repo),                   # ← the capture folder is IN the engine's scope
    "--dangerously-skip-permissions",
    "--model", resolved_model,
]
proc = subprocess.Popen(cmd, cwd=str(repo), stdin=subprocess.DEVNULL, ...)
ctx.set_pid(proc.pid)
```

| Question | Answer |
|---|---|
| Is the real `agy` CLI process spawned? | **Yes** — `subprocess.Popen` on the resolved `agy.exe`. Unchanged by this plan. |
| Is the prompt given to it? | **Yes** — `-p full_prompt`. |
| Which prompt, for the clone's rebuild? | **The caller's own reverse-engineering prompt, byte-identical.** `prompt_mode="verbatim"` → `is_verbatim` → `full_prompt = task` ([:559-563](../actions/antigravity_agent.py#L559-L563)). No ZEZO directives appended, no 6000-char truncation. (Measured earlier: 3266 chars, zero leakage.) |
| Does it run *in* the capture folder? | **Yes, after FIX-01/FIX-02** — `cwd=str(repo)` and `--add-dir str(repo)`, where `repo` comes from the resolver. Today that resolver hands it the wrong folder; that is the bug FIX-02 fixes. |
| Does the plan replace `agy` with a stub, a fleet agent, or the REST fallback? | **No.** The fleet route reaches this same `_run_worker` → same `agy.exe` call. The REST path is only the fallback *after* a CLI failure. |
| What *does* change about that run? | Only what happens **around** it: FIX-03 detects what it actually wrote instead of assuming, FIX-04 stops it completing the caller's card, FIX-14 stops an unknown `--model` being silently ignored. |

**But — the prerequisite that makes it work (FIX-00e):** `agy` is **not logged in** on this machine, and
nothing in the pipeline checks for that (`_find_antigravity_bin()` tests binary existence only). So
today the engine runs, receives the prompt, writes **nothing**, and exits — and Issue 3 turns that
silence into `status: success`.

> **In one line:** the real `agy` run *is* preserved and *does* receive the prompt — but with `agy`
> signed out it will only ever produce an **honest failure** (post-FIX-03) until you sign in
> (FIX-00e). The plan fixes *where* it runs and *what we report*; signing in is what makes it *produce*.

---

## BATCH 0 — Stop the bleeding (do this first, ~10 minutes)

These are data/state operations, not code. They remove the active risk before any refactor.

> ### ✅ EXECUTED — 2026-10-24. Outcome differs from the plan; read this before the items below.
>
> **The in-repo `Desktop/` folder no longer exists.** A full-disk search found no
> `linear_app_clone` anywhere — not at `D:\anitgravity\zezo work\jarvis-57\Desktop\`, not at
> `C:\Users\Hamza\Desktop\`, not on either drive. The 811-file / 14.4 MB folder was deleted (not
> moved). Consequences:
>
> | Item | Planned | What actually happened |
> |---|---|---|
> | FIX-00a | add `/Desktop/` ignore rule | **DONE** — [`.gitignore:25`](../.gitignore#L25), root-anchored, verified it matches |
> | FIX-00b | move the clone to the real Desktop | **MOOT** — there was nothing to move; the folder is gone |
> | FIX-00c | repoint the two stores at the new path | **DONE, but cleared rather than repointed** — the target path does not exist, so pointing at it would be a new dangling reference. `active_file` was cleared too (it was left behind by `forget_repo()` and is read by [`core/design_resolver.py:278`](../core/design_resolver.py#L278)). |
> | FIX-00d | `git status` must not show `Desktop/` | **DONE** — no `Desktop/` entry |
> | FIX-00e | `agy` must be signed in | **STILL OPEN** — a user action, not a code change. The code half lands with Batch 1. |
>
> Cleared via the app's own API (`core.repo_context.forget_repo()` + `memory.memory_manager.forget()`),
> not by hand-editing, so no mirror was left inconsistent. Backups were taken first
> (`memory/*.pre-fix00c.bak`).
>
> **Left deliberately:** `notes.recent_task = "Cloned website https://linear.app into linear_app_clone"`
> in [long_term.json](../memory/long_term.json) and its SQLite mirror (`facts` row 130). It is an
> accurate historical record of an event that did happen, and no code ever reads `recent_task` as a
> path — every reference is a writer (`website_cloner.py`, `antigravity_agent.py`, `kilo_agent.py`,
> `opencode_agent.py`). Leaves unchanged: the `turns` / `turns_fts` rows, which are the conversation
> transcripts themselves.

### FIX-00a — Keep 14.4 MB of clone out of git history (Issue 1a) — **DONE**

`D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone\` is `?? Desktop/` with **no ignore rule
matching it**, so one `git add .` commits 811 files / 14.4 MB permanently.

**Step 1** — add to the repo's `.gitignore` (the *stopgap*; FIX-01 removes the cause):

```gitignore
# Website-clone output must never be written into the repo. Stopgap for the
# target_dir CWD-resolution bug (see docs/CLONE_PIPELINE_ISSUES.md, Issue 1).
/Desktop/
```

**Step 2** — verify nothing is already tracked:

```powershell
git ls-files Desktop        # must print nothing
```

> Use a **root-anchored** `/Desktop/` pattern. A bare `Desktop/` would also match any legitimate
> `Desktop` folder elsewhere in the tree.

### ~~FIX-00b — Move the clone to where the user asked for it (Issue 1)~~ — **MOOT, see the block above**

The folder was **deleted**, not moved: a full-disk search found no `linear_app_clone` under
`D:\anitgravity`, under `C:\Users\Hamza` (depth 5), or on the real Desktop. There is nothing to move.
The original instruction is kept below only so the intent is not lost if a stale copy ever reappears.

```powershell
# NOT NEEDED — kept for reference only
Move-Item "D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone" `
          "C:\Users\Hamza\Desktop\linear_app_clone"
```

### FIX-00c — Correct the two active-project stores (Issues 1b + 10)

Both hold a **different wrong path**; both must be cleared, or ZEZO keeps pointing at folders that
either no longer exist or are its own repo.

> **Status: DONE (2026-10-24)** — done through the app's own API, not by hand, so nothing was left
> inconsistent:
> ```python
> from core.repo_context import forget_repo      # clears repo_context.json AND long_term.json's
> forget_repo()                                  # projects/active_project via memory_manager.forget()
> from memory.memory_manager import forget
> forget("active_file", category="projects")     # companion pointer, otherwise left dangling
> ```
> Backups taken first: `memory/repo_context.json.pre-fix00c.bak`, `memory/long_term.json.pre-fix00c.bak`.

**`memory/repo_context.json`** — *was* the pytest temp dir. `forget_repo()` **removes** the keys rather
than blanking them, so the correct end state is an empty object, not empty strings:

```json
{}
```

**`memory/long_term.json`** — `projects.active_project` **was**
`D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone`. It is now **cleared**, NOT repointed at
`C:\Users\Hamza\Desktop\linear_app_clone`, because that path also does not exist — repointing would
just be a fresh dangling reference. Clear it (do not use the snippet below as written):

```json
// DO NOT USE — the target folder does not exist
"active_project": { "value": "C:\\Users\\Hamza\\Desktop\\linear_app_clone", "updated": "2026-10-24" }
```

`projects.active_file` (`index.html`) was **also** cleared: `forget_repo()` pops it from
`repo_context.json` but not from long-term memory, and it is read as a fallback target by
[`core/design_resolver.py:278`](../core/design_resolver.py#L278) and
[`actions/design_extractor.py:171`](../actions/design_extractor.py#L171) — a bare `index.html` with no
project root is exactly the dangling-pointer class this plan exists to remove.

> The SQLite brain (`memory/zezo_brain.db`) still contains the string in `turns.content` /
> `turns.tool_args` / `turns.tool_result` and a `facts` mirror of `recent_task`. Those are **historical
> transcripts**, not pointers, and were deliberately left alone — the only live-state rows (`facts`
> for `projects/active_project`, `projects/active_file`) are gone.

### FIX-00d — Confirm the stopgap held — **DONE**

```powershell
git status --short          # Desktop/ must NOT appear
```

Verified: `git status --short --untracked-files=all | grep -i desktop` returns only the unrelated
`planning/PLAN_*DESKTOP*.md` deletions — no `Desktop/` entry. `git ls-files Desktop` prints nothing.
The rule itself was proven to bite with a throwaway probe file:
`git check-ignore -v Desktop/__probe__/x.txt` → `.gitignore:25:/Desktop/`.

### FIX-00e — PREREQUISITE: `agy` must actually be logged in ⚠️ *(found while verifying FIX-01..06)*

**This is not optional and it is not a code fix.** Everything in Batch 1 determines **where** the
engine runs and **whether we report the result honestly**. None of it makes a rebuild appear. On this
machine `agy` is logged out, so the engine currently writes **0 bytes** every time.

**Evidence (the CLI's own newest log, `cli-20261024_123403.log`, 12:34:03 — after all three runs):**

```
E errorreport.go:224] error getting token source: You are not logged into Antigravity.
I model_configs.go:346] Auth mode is unspecified, skipping fetchAvailableModels and returning empty response
W rpcs_plugin_auth.go:106] Not reloading plugin MCP servers: cannot get the signed-in user:
                          error getting token source: You are not logged into Antigravity.
I manager.go:492] Initializing CLI store manager for workspace C:\...\pytest-43\test_proj
```

and a recursive scan of `C:\Users\Hamza\.gemini\antigravity-cli\` finds **no token, credential,
login or session file at all** — only `settings.json`. `crashes\` was written at 12:34:04.

**So the honest expectation after Batches 1-2, with `agy` still logged out:**

```
BEFORE the fixes:  agy writes nothing  ->  reported "success"  ->  card DONE   (a lie)
AFTER  the fixes:  agy writes nothing  ->  reported FAILED     ->  card FAILED (the truth)
```

A rebuild only appears once `agy` is authenticated. Confirm with:

```powershell
agy --version          # binary present?
agy                    # interactive: does it ask you to sign in?
```

**Then add a preflight so this is never silent again** — `_find_antigravity_bin()` only checks that the
*binary exists* ([`actions/antigravity_agent.py:416-419`](../actions/antigravity_agent.py#L416-L419));
nothing checks auth. Before the rebuild stage, detect the logged-out state and report it as a
distinct, actionable reason:

```python
# "not logged in" is a DIFFERENT failure from "the rebuild failed": it is fixable by the
# user in one step, and retrying is pointless until they do it.
if "not logged into Antigravity" in cli_output:
    raise RuntimeError(
        "Antigravity CLI is not signed in, so it produced no files. "
        "Sign in to the agy CLI and re-run the rebuild - the capture is intact at "
        f"{clone_dir}."
    )
```

This is the same class of defect as Issue 3: the engine's silence being interpreted as an outcome.

---

## BATCH 1 — P0: the five fixes that make the feature work

### FIX-01 — Route `target_dir` through the existing `~/Desktop` mapping (Issue 1, 1a) — **DONE**

**File:** [`actions/website_cloner.py:2756-2761`](../actions/website_cloner.py#L2756-L2761)

Today:

```python
if target_dir_param:
    clone_dir = Path(target_dir_param).resolve()      # ← against ZEZO's CWD
    clone_dir.mkdir(parents=True, exist_ok=True)
else:
    clone_dir = get_unique_clone_dir(domain)
```

The mapping this bypasses already exists at
[`core/repo_context.py:132-133`](../core/repo_context.py#L132-L133) but `_expand()` is private. Expose
it as a small public helper in the same module — no behavior change to `resolve()`:

```python
def expand_user_dir(raw: str | Path) -> Path:
    """Expand 'Desktop/x', '~/x', 'downloads/x' to a real absolute path.

    The clone worker must use this instead of Path(...).resolve(), which resolves a
    user-facing folder name against ZEZO's own CWD and writes the clone into the repo.
    """
    p = _expand(str(raw))
    if p is None:
        raise ValueError(f"Cannot work out the folder for {raw!r}.")
    return p
```

Then in the cloner:

```python
if target_dir_param:
    clone_dir = expand_user_dir(target_dir_param)
    clone_dir.mkdir(parents=True, exist_ok=True)
else:
    clone_dir = get_unique_clone_dir(domain)
```

**Do NOT** change `resolve()` to route through this — that would alter behaviour for every other
caller (Rule 2/3).

**Verification**
- Layer 1: `python -m py_compile core/repo_context.py actions/website_cloner.py`
- Layer 2: `expand_user_dir("Desktop/linear_app_clone") == Path.home()/"Desktop"/"linear_app_clone"`;
  an absolute path passes through unchanged; `"~/x"` expands.
- Regression: a clone with an absolute `target_dir` still lands exactly there.

---

### FIX-02 — Never silently discard an explicit path (Issue 2) ← **the highest-value fix** — **DONE**

**File:** [`core/repo_context.py:194-202`](../core/repo_context.py#L194-L202)

Today an explicit path that lives under the ZEZO root is dropped with no signal, and `resolve()`
returns a **remembered, unrelated** folder instead:

```python
if explicit:
    p = _expand(explicit)
    if p and not is_zezo_source_dir(p):
        ...
        return p, "explicit"
# → falls through and returns the remember-state value
```

A caller can pass a perfectly correct absolute path and the engine works somewhere else in complete
silence. This is what sent `agy`, and then the follow-up agent, into a pytest temp folder.

Make the rejection **loud** (it is a real caller error, not a fallback condition):

```python
if explicit:
    p = _expand(explicit)
    if p and is_zezo_source_dir(p):
        raise ValueError(
            f"Refusing to use {p} as a project folder: it is inside ZEZO's own source tree. "
            f"Pass a folder outside {_ZEZO_ROOT} (e.g. Desktop/<name>)."
        )
    if p:
        p.mkdir(parents=True, exist_ok=True)
        remember_repo(str(p))
        return p, "explicit"
# Falls through to remember-state only when the caller gave NO explicit path.
```

**Blast-radius review — callers of `resolve()` to check before merging:**

| Caller | Passes an explicit path? | Notes |
|---|---|---|
| `actions/antigravity_agent.py:924` | yes (`explicit_path`) | Task text can name a folder; the regex at `:909` only matches `folder/dir` phrasing. Audit that it can't produce an in-repo string. |
| `actions/fleet_control.py` (`_handle_dispatch`) | yes (`path`/`project_path`) | FIX-08 makes the model actually pass it. |
| `actions/website_cloner.py` | after FIX-01, no longer calls `resolve()` at all | Route it through `expand_user_dir` only. |
| `tests/test_project_isolation_and_fleet_orchestrator_suite.py:62` | no | Must still pass unchanged. |

**Verification**
- Layer 2 (the exact repro from the diagnosis): with `memory/repo_context.json` seeded to a temp dir,
  `resolve(explicit="<a path under the ZEZO root>")` must now **raise**, not return the temp dir.
- Layer 2: `resolve(explicit="<a normal temp dir>")` still returns it with `source == "explicit"`.
- Layer 3: `pytest tests/test_project_isolation_and_fleet_orchestrator_suite.py tests/test_workspace_picker.py`

> **Executed 2026-10-24 — Layers 1 and 2 only; Layer 3 runs at the end of the batch.**
> `python -m py_compile core/repo_context.py actions/website_cloner.py` → both compile.
> Layer 2, actual output:
> ```
> FIX-01 Desktop/x  -> C:\Users\Hamza\Desktop\linear_app_clone
> FIX-01 absolute   -> C:\Users\Hamza\AppData\Local\Temp\tmp3rbrznpb
> FIX-02 raises     -> Refusing to use D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone
>                      as a project folder: ...
> FIX-02 normal     -> proj_ok explicit
> ALL LAYER-2 CHECKS PASSED
> ```
> The FIX-02 case is the exact diagnosis repro: the path that used to be silently discarded now raises
> instead of quietly returning an unrelated remembered repo.

---

### FIX-03 — The engine must not report success when it wrote nothing (Issue 3)

**File:** [`actions/antigravity_agent.py:702-739`](../actions/antigravity_agent.py#L702-L739)

`created_list` is a **full-tree scan**, so in `run_in_place` on a populated folder it is never empty
and `has_entry` is satisfied by files that were already there. A CLI that exits in 5 seconds having
written zero bytes is returned as `{"status": "success"}`.

Replace the tree scan with a real **before/after diff**. Take the snapshot *before* `Popen`:

```python
def _tree_snapshot(repo: Path) -> dict[str, int]:
    """Map of relative path -> mtime_ns, used to detect what a CLI actually wrote."""
    out: dict[str, int] = {}
    skip = (".git", "node_modules", ".venv", "__pycache__")
    try:
        for p in repo.rglob("*"):
            if p.is_file() and not any(part in skip for part in p.parts):
                out[p.relative_to(repo).as_posix()] = p.stat().st_mtime_ns
    except Exception:
        pass
    return out
```

Then after the process exits:

```python
after = _tree_snapshot(repo)
created_list = [rel for rel, mt in after.items() if before.get(rel) != mt]
```

Keep the scratch-rescue block (`:713-730`) as-is — it appends to `created_list`, which is now
"files the CLI produced", so the rescue still works and the gate stays honest.

**Verification**
- Layer 2: fixture folder containing `index.html`; stub `Popen` to exit 0 writing nothing →
  the worker must **not** return `status: success`.
- Layer 2: same fixture with a stub that writes `rebuilt.html` → `success`.
- Regression: a genuinely new project (empty folder) still reports success.

---

### FIX-04 — Do not complete a task card the caller owns (Issue 4)

**File:** [`actions/antigravity_agent.py:795`](../actions/antigravity_agent.py#L795) (and the second
site at `:896`)

`_run_worker` calls `ctx.on_complete(...)`, and `ctx` may be the **clone task's own** context, passed
in by `_run_reverse_engineer` so the build reports into one card. The result: the WEBSITE_CLONER card
is marked `DONE / 100% / "completed"` **while `_clone_worker` is still running**, before
`_verify_re_artifact` has been consulted. The card then flips DONE → FAILED.

Add an explicit ownership flag, defaulted to today's behaviour so no other caller changes:

In `antigravity_action`'s `extra_flags` ([`:949-953`](../actions/antigravity_agent.py#L949-L953)):

```python
extra_flags = {
    "skip_design": bool(parameters.get("skip_design", False)),
    "skip_preview": bool(parameters.get("skip_preview", False)),
    "prompt_mode": str(parameters.get("prompt_mode") or "").strip(),
    # A caller passing its own task_ctx owns that card's lifecycle: it decides when the
    # task is complete, because it may still have to verify the artifact afterwards.
    "owns_task": not bool(parameters.get("task_ctx")),
}
```

and gate both completion sites:

```python
if payload.get("owns_task", True):
    ctx.on_complete(result_payload)
```

**Then the clone caller must complete its own card** — `_clone_worker` already returns a result and
`_verify_re_artifact` decides success; confirm the worker's normal `on_complete` still fires at the
end of `_clone_worker` for the success path (it does today via the task manager's own wrapper) and
that the failure path still raises.

**Verification**
- Layer 2: run the clone worker with a stubbed engine; assert the task status is **not** `DONE` at
  the moment the engine returns, and only becomes `DONE` after the artifact is verified.
- Regression: a plain `antigravity_run` (no `task_ctx`) still marks its own task complete.
- Regression: `pytest tests/test_fleet_control_suite.py` — fleet dispatch relies on this seam.

---

### FIX-05 — Open the real deliverable; no server for a single raw HTML file (Issue 5)

**File:** [`actions/website_cloner.py:2928-2944`](../actions/website_cloner.py#L2928-L2944)

Three faults in eight lines: a server starts unconditionally, the URL points at
`antigravity_clone.html` (uncage's raw snapshot), and the artifact is never opened on success.

The user's rule: **a raw single HTML file is opened directly, not served.**

```python
def _open_deliverable(path: Path, clone_dir: Path) -> str:
    """Open the finished artifact in the browser.

    A single self-contained HTML page opens straight off disk (file://) - a localhost server
    for one file is pointless indirection. A page whose asset refs are root-absolute
    ('/assets/...') cannot render over file://, so only that case keeps a server.
    """
    html = path.read_text(encoding="utf-8", errors="replace")
    if not re.search(r'(?:src|href)\s*=\s*["\']/(?!/)', html):
        uri = path.resolve().as_uri()
        try:
            from actions.browser_control import browser_control
            browser_control({"action": "go_to", "url": uri})
        except Exception:
            import webbrowser
            webbrowser.open(uri)
        return uri
    preview_url, _port = start_local_preview_server(clone_dir)
    url = f"{preview_url}/{path.relative_to(clone_dir).as_posix()}"
    ...  # as today
    return url
```

Order of operations to fix properly:

1. Capture — as today.
2. Rebuild — as today.
3. **Choose the deliverable**: the verified rebuild artifact if one was produced, else
   `antigravity_clone.html`.
4. Open **that**. Never open the raw snapshot when a rebuild exists.
5. On rebuild failure, still open the capture (today the open block is skipped entirely, leaving the
   user staring at the raw snapshot from step 2's preview).

> **Honest caveat:** `antigravity_clone.html` is byte-faithful to uncage's `index.html`, which uses
> **root-absolute** `/assets/...` refs — so that specific file genuinely needs the server. The
> `file://` path applies to `rebuilt.html` and any self-contained deliverable. The helper above
> decides from the file's own markup rather than from an assumption, which is why it is safe for both.

**Verification**
- Layer 2: rebuild a fixture producing `rebuilt.html` with relative refs → opened as `file://`, no
  server started; assert no listener on 9400-9480.
- Layer 2: the raw capture (root-absolute refs) → server started, HTTP 200.
- Layer 2: rebuild fails → the capture is still opened.

---

### FIX-06 — Re-sync `core/prompt.txt` with the real failure text (Issue 6) ← **the v6 regression**

**File:** [`core/prompt.txt:405-414`](../core/prompt.txt#L405-L414)

The prompt matches `"React rebuild FAILED -"`, but the code raises
`"Rebuild FAILED - capture intact at {clone_dir} (preview open at …). Reason: … A fleet agent can be
pointed at that folder to finish it."` ([`website_cloner.py:2981-2985`](../actions/website_cloner.py#L2981-L2985)).
The branch never fires, so the model improvised "the React rebuild failed" and never got the
instruction to pass `path`.

**Two options — pick one, do not half-do it:**

- **(A) Fix the prompt (recommended).** De-hardcode the stack, because `output_format` is now free
  text and the rebuild may be anything:
  ```
  - WEBSITE CLONE REBUILD FAILURE: if a failed background task was a website clone, the error text
    starts with "Rebuild FAILED - capture intact at" and names the folder that was kept. Then:
    1. Tell the user plainly, in 1 sentence and in their language, that the capture itself is fine,
       but the rebuild they asked for failed - and name the folder. Do NOT name a framework; use
       whatever they asked for.
    2. Offer the handoff: "Is folder ko kisi agent ko de dun?"
    3. If the user agrees, call
       `fleet_control(action='dispatch', agent_id='VERVE', path='<the exact folder from the error>',
        task='Finish the rebuild in this folder: <what was asked>')`.
       ALWAYS pass `path` - without it the agent gets a different folder and the captured work is lost.
    4. NEVER claim the rebuilt app is ready when this failure arrives.
  ```
- **(B) Make the message a stable constant** exported from `website_cloner.py` and confirm it still
  begins with the string the prompt matches. Only worth it if the prompt should stay framework-specific
  — it should not.

Also add a **failure** branch near [`core/prompt.txt:384`](../core/prompt.txt#L384), which today only
has a success sentence, so the model cannot announce a completion that did not happen.

**Verification**
- Layer 2: assert `RE_REBUILD_FAILURE_PREFIX` (or the literal) appears in both the raiser and
  `core/prompt.txt` — a test that fails if the two drift again. **This test is the real fix**;
  the string was already correct in two places once and still drifted.

---

## BATCH 2 — P1: wrong behaviour the user can see

### FIX-07 — No design blueprint on a reverse-engineering / rebuild task (Issue 7b)

**File:** [`actions/antigravity_agent.py:406`](../actions/antigravity_agent.py#L406)

```python
if is_ui_task(task) and not is_verbatim and not payload.get("skip_design"):
    resolved_design = resolve_design(task, session_memory=session_mem, repo_path=repo)
```

The clone's own rebuild is protected (`skip_design=True` + `prompt_mode="verbatim"`). The follow-up
**fleet/agent** path is not, so a rebuild request came back as *"the full Aura Frame design
reference"* — the new page that appeared in the temp folder, titled *"Image Gen Dashboard Canvas"*.

Fix by making the intent detectable, not just declarable:

```python
_REBUILD_MARKERS = ("rebuild", "reverse engineer", "reverse-engineer", "reproduce",
                    "replicate", "clone this", "finish the rebuild", "same design as")

def _is_rebuild_task(task: str) -> bool:
    low = task.lower()
    return any(m in low for m in _REBUILD_MARKERS)
```

and:

```python
if is_ui_task(task) and not is_verbatim and not _is_rebuild_task(task) \
        and not payload.get("skip_design"):
```

Also let the caller be explicit: accept `skip_design` through `fleet_control`'s `dispatch` so an
agent hand-off can request verbatim reproduction.

**Verification**
- Layer 2: `_is_rebuild_task` table test over the marker list, plus a negative case ("build me a
  landing page") that must still get a blueprint.
- Layer 2: a dispatch with a rebuild-phrased task must not write `DESIGN_BLUEPRINT.html`.

---

### FIX-08 — The agent hand-off must carry the folder (Issue 7a)

Mostly fixed by FIX-06 (the prompt regains the `ALWAYS pass path` rule). Close the remaining hole so
it cannot silently regress:

- Confirm `path` is in the `fleet_control` TOOL schema for `dispatch` — the handler accepts it
  ([`actions/fleet_control.py:40`](../actions/fleet_control.py#L40)) but a parameter the model cannot
  see is a parameter it will not send.
- In `_handle_dispatch`, when `path` is omitted, log a **warning** naming the folder it fell back to.
  Do not invent a default (Rule 3) — just stop the fallback being invisible.

**Verification**
- Layer 2: `fleet_control({"action":"dispatch","agent_id":"VERVE","task":"…"})` with no `path`
  emits the warning; with `path` reaches `dispatch_task` carrying it.

---

### FIX-09 — Execution Logs must be readable (Issue 8)

**File:** [`frontend/src/components/tasks/TaskManagerModal.tsx:567`](../frontend/src/components/tasks/TaskManagerModal.tsx#L567)

```tsx
{Array.isArray(selectedTask.logs) ? selectedTask.logs.join('\n') : String(selectedTask.logs)}
```

`join` stringifies each `{time,text,progress}` object → eleven lines of `[object Object]`. **Every**
diagnosis of a failed clone is blind until this is fixed.

```tsx
{Array.isArray(selectedTask.logs)
  ? selectedTask.logs
      .map((l) => (typeof l === 'string' ? l : `${l?.time ?? ''} ${l?.text ?? ''}`.trim()))
      .join('\n')
  : String(selectedTask.logs)}
```

Keep the string branch: `logs` may already be `string[]` from older task records.

**Verification**
- Layer 2: render the modal against a fixture task with `logs: [{time,text,progress}]` → real text,
  no `[object Object]`. Note `frontend/dist` is committed, so **rebuild the bundle** or the fix will
  not reach the app.

---

### FIX-10 — The read-back must name the resolved path (Issue 9)

**File:** [`actions/website_cloner.py:3090`](../actions/website_cloner.py#L3090)

```python
folder = Path(target_dir).name if target_dir else default_dir.name
```

The user confirmed after hearing only *"into 'linear_app_clone'"*. The confirmation step is the
cheapest place to catch a wrong destination — and it never mentioned the folder was inside the ZEZO
repo.

Speak the **resolved absolute path**, and explicitly flag when it is inside ZEZO's own tree (after
FIX-01 that should be impossible, so treat it as an assertion).

**Verification**
- Layer 2: the read-back for `target_dir="Desktop/x"` contains the full
  `C:\Users\Hamza\Desktop\x`, not just `x`.
- Existing read-back tests in `tests/test_website_cloner_suite.py` updated accordingly.

---

## BATCH 3 — P2: hygiene

### FIX-11 — Stop tests writing to production memory (Issue 10)
**File:** [`core/repo_context.py:25`](../core/repo_context.py#L25)

```python
_STORE_PATH = Path(__file__).resolve().parent.parent / "memory" / "repo_context.json"
```

A **production** file that tests write to directly via `remember_repo()`, and `memory/*.json` is
gitignored, so the pollution is invisible and permanent. Allow an override and point tests at a temp
dir:

```python
_STORE_PATH = Path(
    os.environ.get("ZEZO_REPO_CONTEXT_STORE")
    or Path(__file__).resolve().parent.parent / "memory" / "repo_context.json"
)
```

Set `ZEZO_REPO_CONTEXT_STORE` in `tests/conftest.py` (autouse fixture to a `tmp_path`), and audit the
`remember_repo()` calls in the test suite. **The same env-override pattern should be applied to the
`long_term.json` writer** — FIX-12 covers the code side.

### FIX-12 — Two unguarded writers to `active_project` (Issue 1b)

`remember_repo()` has the `is_zezo_source_dir` guard
([`core/repo_context.py:64-79`](../core/repo_context.py#L64-L79)), but two call sites write
`active_project` straight to long-term memory, bypassing it entirely:

- [`actions/website_cloner.py:2945-2950`](../actions/website_cloner.py#L2945-L2950)
  ```python
  register_clone(clone_dir)                      # guarded → silently no-ops for an in-repo path
  remember("active_project", str(clone_dir), category="projects")   # ← unguarded, this is what stuck
  ```
- [`actions/antigravity_agent.py:980-986`](../actions/antigravity_agent.py#L980-L986) — same pattern.

`register_rebuild()` ([`core/repo_context.py:356-378`](../core/repo_context.py#L356-L378)) is a third
unguarded writer.

Make the guard the *single* gate: route every `active_project` write through one function that applies
`is_zezo_source_dir`, and delete the direct `remember("active_project", …)` calls.

**Verification**
- Layer 2: `remember_repo("<path under the repo root>")` leaves `long_term.json` unchanged (today it
  is unchanged only by luck, via the guarded path — the direct call is what leaked).
- Layer 2: the clone worker, run against an in-repo `clone_dir`, must not record it as active.

### FIX-13 — `.gitignore` written into the workspace (Issue 11)
[`actions/antigravity_agent.py:396`](../actions/antigravity_agent.py#L396) — `_ensure_gitignore(repo)`
is correctly skipped in `verbatim` mode but not on the agent path; it dropped a stray 74-byte
`.gitignore` into the temp folder. Extend the existing guard to the rebuild path (FIX-07's predicate).

### FIX-14 — Model string the CLI does not recognise (Issue 12)
`core/models.py:65` sends `gemini-3.8-flash-medium`, the CLI received `gemini-3.7-flash-medium`, and
`agy` logged `not in local config, defaulting to CCPA` for it — i.e. **neither** is a model the CLI
knows and it silently ran its own default. Determine the real accepted id from `agy`'s config and
either align `DEFAULT_ANTIGRAVITY_MODEL` or stop passing `--model` when the value is unknown.
**Then log a warning whenever the resolved model is not the one requested.**

> **Root cause found (2026-10-24), before writing any code.** The mismatch is not in `core/models.py`
> at all — its default is `gemini-3.8-flash-medium`, which *is* in `ANTIGRAVITY_CLI_MODELS`
> ([`core/models.py:57-65`](../core/models.py#L57-L65)). The stale value comes from **persisted user
> config**: `config/api_keys.json` holds
> ```json
> "antigravity_model": "gemini-3.7-flash-medium"
> ```
> and `_resolve_model` ([`actions/antigravity_agent.py:58-62`](../actions/antigravity_agent.py#L58-L62))
> prefers it over the default:
> `selected = (model or "").strip() or get_antigravity_model() or DEFAULT_ANTIGRAVITY_MODEL`.
> `gemini-3.7-flash-medium` is **absent** from `ANTIGRAVITY_CLI_MODELS`, so it reached the CLI, the CLI
> did not recognise it, and it silently ran its own default.
>
> So the fix is a **validation**, not a rename: in `_resolve_model`, if the resolved id is not in
> `ANTIGRAVITY_CLI_MODELS`, log a warning naming requested-vs-used and **omit `--model`** so the CLI
> picks its own default deliberately instead of being handed a string it will discard. `config/` is
> gitignored user state, so fixing the persisted value is a separate, user-facing concern — not a code
> change. (A settings-UI dropdown over `ANTIGRAVITY_CLI_MODELS` would prevent a stale id recurring;
> that is Part II's territory, not this fix.)

### FIX-15 — Dirty `design md/*.md` (Issue 13)
Five files under `skills/hamza_taste/references/design md/` differ by `extracted_at` only. Cosmetic —
revert if the timestamps are not wanted, or leave and stop treating them as a real diff.

---

## 4. Verification plan (AGENTS.md Rule 7)

**Files that will be touched:** `core/repo_context.py`, `actions/website_cloner.py`,
`actions/antigravity_agent.py`, `actions/fleet_control.py`, `core/prompt.txt`,
`core/models.py`, `frontend/src/components/tasks/TaskManagerModal.tsx`, `.gitignore`, tests.

**Layer 1 — static:** `python -m py_compile` on every touched `.py`; `tsc`/vite build for the frontend.

**Layer 2 — runtime, with real evidence:**
1. The four real export dirs in `tools/uncage/output/` are a permanent offline fixture — no live site
   needed for the pipeline tests.
2. **The exact regression repro, end to end:** seed `repo_context.json` with a temp dir, then run
   `_clone_worker` with `target_dir="Desktop/<name>"` → the clone must land in the **real**
   `~/Desktop`, the engine must run **in that folder** (`agy` log's `Initializing CLI store manager
   for workspace` must name it), and the artifact must be found there.
3. **The false-success repro:** stub the CLI to exit 0 having written nothing in a populated folder →
   FAILED, not `success` (FIX-03).
4. **The card-lifecycle repro:** assert the task is not `DONE` while the engine is still returning
   (FIX-04).
5. **Open-behaviour:** `file://` with no server for a self-contained rebuild; server for root-absolute
   refs (FIX-05).
6. **String-drift test:** the failure prefix in the code and in `core/prompt.txt` must match (FIX-06).

**Layer 3 — regression:**
```
pytest tests/test_website_cloner_suite.py tests/test_reverse_engineer_suite.py \
       tests/test_fleet_control_suite.py tests/test_project_isolation_and_fleet_orchestrator_suite.py \
       tests/test_workspace_picker.py
```
> Deliberately **not** the whole repo: the assigned feature plus its direct seams only. (The
> repo-wide suite additionally fails to collect `tests/test_remote_dashboard_suite.py` — pre-existing,
> unrelated.)

**Rule 10:** append a `LEARNING_JOURNAL.md` entry covering the CWD-resolution root cause, the
`is_zo_source_dir` silent-fallback trap, the false-success check, and the prompt/code string drift.

---

## 5. Explicitly NOT in this plan

| Item | Why |
|---|---|
| Any change to `tools/uncage/**` | Uncage behaved correctly. |
| Rebuilding the whole `clone_website` pipeline | Rule 3 — the pipeline works; the destination and the reporting do not. |
| Removing the local preview server entirely | Root-absolute asset pages genuinely need it (FIX-05 caveat). |
| Making the confirmation gate stateful | It is stateless for a documented reason — `main.py` resets the `"global"` session on every utterance. |
| `MAX_CONCURRENT_CLONES` / uncage bootstrap timeouts | Pre-existing, out of scope. |

---

## 6. Suggested merge order

```
BATCH 0   FIX-00e      sign in to `agy` + preflight  ← nothing rebuilds until this is done
          FIX-00a..d   data + state (no code)     ← do first, removes the active risk
BATCH 1   FIX-01, 02   paths (the actual bug)
          FIX-03       false success
          FIX-04       card lifecycle
          FIX-06       prompt re-sync        ← must land with FIX-03/04
          FIX-05       open behaviour
BATCH 2   FIX-07..10   visible behaviour + logs (FIX-09 unblocks all future diagnosis)
BATCH 3   FIX-11..15   hygiene
```

FIX-02 is the one that would have prevented this entire incident; FIX-03 and FIX-04 are what turned
it into a false "completed" card; FIX-06 is the only regression introduced by the v6 rewrite and
should ship in the same batch as the other two.

---
---

# PART II — Code Engines: a settings section to manage the CLIs

> **Wireframe:** [`wireframe-code-engines.html`](./wireframe-code-engines.html) — open it in a browser.
> **Status:** new feature, plan only. **Not a blocker for Part I** — the clone fixes ship on their own.

## P.0 Why this belongs in this document

Part I's **FIX-00e** is the backend half of one gap: the pipeline must know an engine is not ready and
say so. Part II is the **UX half** of the same gap: the user finds out *before* a build fails, instead
of reading a `Rebuild FAILED` line afterwards.

The gap is real and it is not theoretical. `agy.exe` is **installed** on this machine and **not signed
in**, so it runs, receives the prompt, writes 0 bytes, and exits. A settings panel that checked only
"is it installed?" would have shown Antigravity **green** for the entire failed run.

**The one-line requirement, which everything below follows from:**

> The panel reports **readiness**, not **presence**. Installed is not a state worth showing on its own.

## P.1 The four states

| # | State | Meaning | Primary action |
|---|---|---|---|
| 01 | **Not installed** | Binary not found on PATH or in the vendor folders | `Install` |
| 02 | **Sign in required** | Binary found, no authenticated account. Runs and writes nothing | `Sign in` |
| 03 | **Ready** | Installed and authenticated. Lists the models it accepts | `Set as default` |
| 04 | **Off** | The user disabled it. ZEZO will not select it, and says so when asked | `Turn on` |

State **02 is the state this machine is in right now**, and the state presence-checking cannot see.

## P.2 Phase 1 — read-only health panel *(ship this first)*

Everything here is read-only, so it **cannot break the user's setup**, and it alone would have caught
the incident in Part I.

### P1-1 — One provider registry (replaces three duplicated discovery functions)

Three functions currently do the same job with different search paths:
[`_find_antigravity_bin()`](../actions/antigravity_agent.py#L35) (4 PATH names + 4 vendor dirs),
[`_find_opencode_bin()`](../actions/opencode_agent.py#L33) (PATH + `~/.opencode/bin`),
[`_find_kilo_bin()`](../actions/kilo_agent.py#L33) (PATH + `~/.kilo/bin`).

New module **`core/code_engines.py`** — a registry, so the agent modules stop importing each other:

```python
@dataclass(frozen=True)
class Engine:
    id: str                        # "antigravity" | "opencode" | "kilo"
    label: str                     # what the user sees
    path_names: tuple[str, ...]    # names to try on PATH
    vendor_dirs: tuple[Path, ...]  # vendor install locations
    version_argv: tuple[str, ...]  # cheap "are you there, what version" probe
    auth_probe: AuthProbe | None   # how to learn the signed-in state (see P1-2)
    install: InstallRecipe | None
    backs_tool: str                # the ZEZO action this engine powers

ENGINES: dict[str, Engine] = {...}     # dict dispatch, no if/elif (Rule 8)
```

Each agent's `_find_*_bin()` becomes a one-line delegation to
`code_engines.resolve_binary(ENGINE_ID)`, keeping the existing search paths as data instead of
copy-paste.

### P1-2 — The auth probe (the part that has to be done honestly)

**Auth is not a file you can check.** A recursive scan of `~/.gemini/antigravity-cli/` finds **no
token, credential, login or session file** — only `settings.json`. So readiness is knowable only by
*asking the CLI*. Three layers, each cheap enough to cache:

```
1. Binary present?    shutil.which(names) + vendor_dirs       ~1 ms
2. Alive + version?   <engine> --version                      ~200 ms
3. Authenticated?     engine-specific probe                   seconds
```

**Layer 3 must be discovered per engine, never guessed.** For Antigravity the honest signal is the
CLI's own output and log line:

```
E errorreport.go:224] error getting token source: You are not logged into Antigravity.
```

**If an engine has no cheap auth probe, report `Installed · sign-in state unknown` and offer the
`Sign in` button.** Do not invent a `Ready` that was never verified — a status that cannot be trusted
is the same defect as a build that reports success while writing nothing.

Results are cached with a TTL (5 minutes), with a manual **Test** button that forces a re-probe.

### P1-3 — Non-blocking, always (Rule 5)

The probe runs on a background thread. Opening the settings section must never freeze the GUI, and a
slow or hung CLI must not block the panel: the card shows its last known state plus `checking…`. Each
engine's probe is independent and has a short timeout.

### P1-4 — The panel itself

Per the wireframe: a section nav item **Code Engines**, a three-tally summary strip (summary before
detail), one card per engine, a **Default engine** row, and a **routing** row that states any fallback
out loud.

Frontend work, following the existing pattern at
[`SettingsModal.tsx:1876`](../frontend/src/components/settings/SettingsModal.tsx#L1876):

- add `'code-engines'` to `SectionId` and to the section list at `:879-896`
- new `frontend/src/components/settings/CodeEnginesSettingsTab.tsx`
- one line: `{activeSection === 'code-engines' && <CodeEnginesSettingsTab />}`
- ReUI components for Button, Badge, Tooltip, Scroll Area (Rule 1) — do not hand-roll them

### P1-5 — A read-only status tool, because ZEZO is voice-first

The panel is only half the job in a voice product: a user who asks *"AGY install hai?"* out loud must
get an answer. New action **`actions/code_engines_status.py`** (Rule 4: its own file, with `TOOL` +
`handler`), read-only:

```
code_engines_status(action='list'|'check', engine='antigravity')
→ "Antigravity is installed but not signed in, so it cannot write any files.
   OpenCode is ready and will be used instead."
```

This is also what FIX-00e calls when a build is about to need an engine.

### Phase 1 verification

- Layer 1: `python -m py_compile` on every touched file; frontend builds.
- Layer 2: on this machine the panel must show **AGY = Sign in required**, from the CLI's real output,
  not a hardcoded value. Fake a missing binary for a temp engine id → **Not installed**. Stub a clean
  probe → **Ready**.
- Layer 2: open the section with the probe stubbed to sleep 30 s → the GUI stays responsive and the
  card shows `checking…`.
- Layer 3: the existing `antigravity` / `kilo` / `opencode` suites, since `_find_*_bin` is rerouted.

## P.3 Phase 2 — install

**The hard truth: `open_app`'s installer is winget-only**
([`open_app.py:304`](../actions/open_app.py#L304), `:366`) **and these engines are not winget
packages.** `agy` ships with its own installer; `opencode` and `kilo` are npm-distributed. So the
recipes must be per-engine:

```python
@dataclass(frozen=True)
class InstallRecipe:
    kind: str                      # "winget" | "npm" | "download" | "manual_only"
    command: str                   # shown in the gate, in mono
    needs: str                     # e.g. "Node 20+, ~120 MB"
    verify_argv: tuple[str, ...]   # run after installing, to prove it works
```

Rules for this phase:

1. **A finished installer is not a working engine.** Re-probe after installing. Only `Ready` if the
   probe passes; otherwise `Installed · sign-in state unknown`.
2. **Never offer `Install` for something you cannot verify afterwards.** For `manual_only`, show the
   command with a **Check again** button instead of one that pretends to do it.
3. **Confirm gate.** Reuse [`core/confirm.py`](../core/confirm.py) exactly as `open_app` does: the
   token comes from the UI, never from the model.
4. A non-technical user is running a real program on their machine. The gate names the source, the
   exact command, and what it needs.

## P.4 Phase 3 — control, and the two places a toggle can lie

### P3-1 — Enable / disable

`memory/config_manager.py` gains the typed pair it uses for every other setting:

```python
def get_enabled_engines() -> list[str]: ...
def save_engine_enabled(engine_id: str, enabled: bool) -> None: ...
```

### P3-2 — Disable must be *enforced*, not just drawn

Today routing consults no engine list; the model picks a tool from its description. A UI toggle alone
would produce a panel that says "off" while the engine still runs. **Enforce in the worker path**, so
the refusal happens in code and can be explained:

- `resolve_binary()` / the worker returns a clear reason when an engine is disabled or not ready
- the model is told *why*, so it says it out loud instead of silently picking another engine

This is deliberately the **last** phase: it is the one place where the UI can start contradicting the
backend again, which is the class of bug Part I exists to remove.

### P3-3 — Models come from the engine (closes Issue 12)

`core/models.py:65` sends `gemini-3.8-flash-medium`; the CLI received `gemini-3.7-flash-medium` and
logged `not in local config, defaulting to CCPA`. Neither is a model the CLI knows, and it silently
runs its own default. Read the accepted list from the engine and offer that
(`glm-5.3-flash-free`, `mimo-v2.5-free`, …), then **warn whenever the resolved model is not the one
requested.**

### P3-4 — Default engine and a *stated* fallback

The wireframe's `Default engine` row plus the amber routing row. The rule: **a fallback is fine, a
silent fallback is not.** If the default is not ready, the panel names the engine that will be used
instead, and the spoken/returned message says the same thing.

## P.5 Deliberately out of scope

| Not doing | Why |
|---|---|
| **Uninstall** | The riskiest button for a non-technical user, and nothing needs it yet. Revisit behind the confirm gate. |
| **Per-engine model dropdown** | The wireframe shows model *chips* (informational). A picker earns its place only once routing actually selects models. |
| **API-key providers (Groq, Tavily…)** | Keys already live in **API & Keys** with a transactional save path. They are not engines. |
| **"ACP" as the section name** | ACP is a protocol some agents speak. These are CLI coding agents; naming the section after the protocol would confuse the audience it is built for. |

## P.6 Naming

**"Code Engines"** is the recommendation: it says what they do for the user (write code) without
requiring them to know what a CLI is. `Manage CLIs` is the developer's word for it, and the whole
point of this panel is the user who does not have that word.

## P.7 Suggested order across both parts

```
PART I   BATCH 0-3   the clone bug + its fallout             <- the fire
         FIX-00e     pipeline refuses to lie about an engine  <- backend half of the gap
PART II  Phase 1     read-only health panel                   <- UX half, zero risk
         Phase 2     install recipes + post-install verify
         Phase 3     enable/disable + enforcement, models, fallback
```

Parts I and II are independent. Part I is a bug fix and should not wait for this feature; Part II
Phase 1 is the cheapest way to make sure the same class of failure is visible to the user next time.
