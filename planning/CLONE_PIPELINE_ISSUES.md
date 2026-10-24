# 🐞 Website Cloner — Issue Report (run of 2026-10-24, 12:28–12:34)

> **Creator & Lead Architect:** Hamza Bukhari
> **Status:** Diagnosis only — **no code was changed** for this report.
> **Scope:** the `clone_website` feature only (Uncage capture + prompt-driven reverse-engineering rebuild).
> **Method:** live run evidence read from the filesystem, the `agy` CLI logs, and the production
> state files — not from assumptions.

---

## 0. TL;DR

The **rebuild actually succeeded** — a correct Linear rebuild (`rebuilt.html`, 8797 B) exists on disk
right now. It landed in the **wrong folder**, so `clone_website` looked in the capture folder, found
nothing, and reported `FAILED`.

That wrong folder is the top of a five-step cascade:

```
"Desktop/linear_app_clone"
   → resolved against ZEZO's own CWD  →  <ZEZO repo>/Desktop/linear_app_clone
   → inside the ZEZO source tree      →  is_zezo_source_dir() == True
   → explicit path SILENTLY DISCARDED →  resolve() falls back to remember-state
   → remember-state was test-polluted →  ...\pytest-of-Hamza\pytest-43\test_...\test_proj
   → agy ran there, artifact written there, verification looked elsewhere → FAILED
```

That first step is also a **second bug in its own right**: the clone now sits *inside ZEZO's own
repository* — 811 files / 14.4 MB under `D:\...\jarvis-57\Desktop\linear_app_clone\`, untracked with
**no `.gitignore` rule matching it**, i.e. one `git add .` from being committed into ZEZO's history
(Issue 1a). The user's real `C:\Users\Hamza\Desktop\` is still empty.

On top of that, `agy` **is not logged in** on this machine, so the CLI itself produced nothing and
its silence was masked by a false-success check.

> 📐 **Before/after flow diagrams** (the same request through the same code, and what changes) are in
> [`CLONE_PIPELINE_FIX_PLAN.md` §0.5](./CLONE_PIPELINE_FIX_PLAN.md#05-before--after--what-actually-changes).
> The fix for every issue below is in that same document.

---

## 1. Evidence base

| Source | What it proved |
|---|---|
| `D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone\` | The capture itself is **intact and correct** — but it was written **inside the ZEZO repo** (Issue 1a) |
| `git status` / `git check-ignore` on that path | Untracked `?? Desktop/`, **no ignore rule** — 811 files / 14.4 MB committable into ZEZO's history |
| `C:\Users\Hamza\AppData\Local\Temp\pytest-of-Hamza\pytest-43\test_kilo_and_opencode_run_in_0\test_proj\` | The rebuild artifact landed here instead |
| `C:\Users\Hamza\.gemini\antigravity-cli\log\cli-20261024_1231{23,234,403}.log` | All three `agy` runs' workspace + auth failure |
| `memory/repo_context.json` | The production "active repo" store is polluted with a pytest temp dir |
| `core/repo_context.py` (live call) | `resolve(explicit=<clone_dir>)` returns the pytest dir |
| Task card + UI screenshots | DONE→FAILED flip, `[object Object]` logs |

### 1.1 Capture folder — CORRECT ✅
`D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone\` (all files 12:31)

```
index.html               1,036,565 B     ← real assembled uncage page
antigravity_clone.html   1,036,665 B     ← ZEZO's verbatim copy
asset-map.json                46,283 B
assets/                                  ← real assets
package.json                     204 B
README.md                        650 B
.gitignore                        24 B
rebuilt.html              ** MISSING ** ← verification looked here
```

**Uncage did its job. Do not touch this folder.**

### 1.2 Where the artifact actually went
`C:\Users\Hamza\AppData\Local\Temp\pytest-of-Hamza\pytest-43\test_kilo_and_opencode_run_in_0\test_proj\`

```
rebuilt.html     8,797 B   12:31   ← the clone's rebuild. Landed here.
.gitignore          74 B   12:32   ← ZEZO wrote it here (see Issue 7)
index.html      29,164 B   12:34   ← an UNRELATED page, title "Image Gen Dashboard Canvas"
```

`rebuilt.html` opens with:

```html
<title>Linear • The rebuild</title>
<link rel="icon" type="image/x-icon" href="assets/6989437.ico">
    --color-black: #000212;        <!-- Linear's real design token -->
    --color-text-primary: #f7f8f8;
```

So the reverse-engineering stage **worked correctly** — and its relative `assets/...` references are
broken precisely because it was written outside the capture folder.

### 1.3 `agy` ran three times, unauthenticated
`cli-20261024_123123.log`, `cli-20261024_123234.log`, `cli-20261024_123403.log` — each run lasted
~5 seconds and contains:

```
E errorreport.go:224] error getting token source: You are not logged into Antigravity.
I model_configs.go:346] Auth mode is unspecified, skipping fetchAvailableModels and returning empty response
I resolver.go:85] Model ID gemini-3.7-flash-medium not in local config, defaulting to CCPA
I server.go:3219] Language server shutting down
```

All three, regardless of what ZEZO passed:

```
I manager.go:492] Initializing CLI store manager for workspace
   C:\Users\Hamza\AppData\Local\Temp\pytest-of-Hamza\pytest-43\test_kilo_and_opencode_run_in_0\test_proj
```

The clone's own run (12:31:23) mentions `linear_app_clone` **zero times**.

---

## 2. Issues

Severity: 🔴 blocks the feature · 🟠 degrades trust/observability · 🟡 hygiene

### 🔴 Issue 1 — `target_dir` resolves against ZEZO's CWD, so the clone is written **into ZEZO's own repository**

**File:** [`actions/website_cloner.py:2758`](../actions/website_cloner.py#L2758)

```python
target_dir_param = params.get("target_dir") or params.get("repo") or params.get("project_path")
if target_dir_param:
    clone_dir = Path(target_dir_param).resolve()      # ← resolves against the ZEZO process CWD
```

The user said **"desktop pe save karna hai"**, the model passed `"Desktop/linear_app_clone"`, and it
became `D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone` — a `Desktop` folder **inside
ZEZO's own repository**.

The correct mapping already exists in the codebase and the worker bypasses it —
[`core/repo_context.py:132-133`](../core/repo_context.py#L132-L133):

```python
if first in ("desktop", "downloads", "documents", "projects", "dev"):
    base = Path.home() / parts[0].capitalize()
```

**Impact:** every voice request that names a folder by its common name ("Desktop", "Documents")
lands in the ZEZO repo instead of the user's real folder — and, worse, inside the source tree, which
triggers Issue 2.

#### 1a. What it left behind in the repo — verified `2026-10-24`

The clone was delivered into `D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone\` — a
`Desktop` folder **inside the ZEZO project itself**. Measured on disk right now:

```
git status --short -- Desktop     →  ?? Desktop/          (untracked)
git check-ignore -v Desktop/...   →  no rule matches       (NOT ignored)
files                             →  811
total size                        →  14,363,485 B (14.4 MB)
```

Consequences, in order of how much they hurt:

1. **It is committable.** `?? Desktop/` is untracked and **no `.gitignore` rule matches it**, so a
   routine `git add .` / `git add -A` silently commits 14.4 MB of a third-party site's assets into
   ZEZO's own history. Once committed it is permanent in the history, not just the working tree —
   and the artifact that should have been on the user's real Desktop is now a repo dependency.
2. **It is inside the source tree**, which is exactly what makes `is_zezo_source_dir()` return True
   and triggers Issue 2. The two are the same bug seen from two sides: the wrong *place* (Issue 1)
   and the silent *rejection* of that place (Issue 2).
3. **Every repo-wide scan now walks it.** Anything that recurses from the repo root — the HUD file
   browser ([`core/ui_server.py:48`](../core/ui_server.py#L48), bounded at 5000 entries), an IDE
   index, a code-graph run — now sees 811 unrelated files, and `_scan_folder`'s 5000-entry cap means
   the *user's actual project files* can be pushed out of the listing by clone assets.
4. **It is not a "temporary" folder a cleanup would find.** The name is `Desktop`, which reads as
   intentional. Nothing in the codebase marks it as engine output to be removed.

**The correct destination** was `C:\Users\Hamza\Desktop\linear_app_clone` — the user said "desktop
pe save karna hai", and
[`core/repo_context.py:132-133`](../core/repo_context.py#L132-L133) already maps that word to
`Path.home()/"Desktop"`. The clone worker bypasses that mapping entirely.

#### 1b. It is now recorded as the user's **active project** in long-term memory

Verified in `memory/long_term.json` (written 2026-10-24, the day of the run):

```json
"projects": {
  "active_project": {
    "value": "D:\\anitgravity\\zezo work\\jarvis-57\\Desktop\\linear_app_clone",
    "updated": "2026-10-24"
  }
},
...
"notes": {
  "recent_task": { "value": "Cloned website https://linear.app into linear_app_clone", ... }
}
```

So this is **not** a stray folder that can simply be moved by hand — ZEZO's **long-term memory**
now names a path *inside its own repository* as the active project. Both entries are durable and
survive restarts.

**And the two active-project stores disagree:**

| Store | Value |
|---|---|
| `memory/repo_context.json` | `...\pytest-of-Hamza\pytest-43\test_...\test_proj` (Issue 10) |
| `memory/long_term.json` → `projects.active_project` | `D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone` |

Which one wins depends on the caller, so "the active project" is now ambiguous — and **both values
are wrong**. This is the concrete reason the follow-up agent ran in a pytest temp folder while ZEZO
told the user it was working in `linear_app_clone`: the two stores each held a different wrong answer.

**Root cause of the split — the guard is on one door, and the clone walks through a different one:**

- [`core/repo_context.py:64-79`](../core/repo_context.py#L64-L79) — `remember_repo()` **has** the
  guard, so it **silently refused** to record the in-repo path (debug-level log only, no user signal):
  ```python
  def remember_repo(path: str) -> None:
      if not path or is_zezo_source_dir(path):
          logger.debug("repo_context: ignoring request to remember Zezo root or empty path: %s", path)
          return
  ```
  This is exactly why `repo_context.json` was *not* updated — it still holds the pytest dir.
- [`actions/website_cloner.py:2945-2950`](../actions/website_cloner.py#L2945-L2950) — and then the
  worker writes the same thing **directly**, to a different store, with **no guard at all**:
  ```python
  register_clone(clone_dir)                                        # guarded → no-op, silently
  remember("active_project", str(clone_dir), category="projects")  # ← unguarded: THIS is what stuck
  ```
- [`actions/antigravity_agent.py:980-986`](../actions/antigravity_agent.py#L980-L986) — the same
  unguarded direct `remember("active_project", …)` pattern, on the agent path.
- [`core/repo_context.py:356-378`](../core/repo_context.py#L356-L378) — `register_rebuild()` is a
  third writer to the same store, also with no `is_zezo_source_dir` check.

So the *same* `is_zezo_source_dir` decision as Issue 2 is reached by two different doors with two
different results: one silently rejects the path, another silently accepts it. Neither tells the user.
The fix for this is FIX-12 in [`CLONE_PIPELINE_FIX_PLAN.md`](./CLONE_PIPELINE_FIX_PLAN.md) — route
every `active_project` write through a single guarded function.

> **Recovery note (not performed, and *not* just a folder move):** because of 1b, clearing this needs
> two things — move the folder to the real `C:\Users\Hamza\Desktop\`, **and** correct/clear the
> `active_project` value in `memory/long_term.json` (plus the pytest path in
> `memory/repo_context.json`, Issue 10). Moving the folder alone leaves ZEZO pointing at a path that
> no longer exists.

---

### 🔴 Issue 2 — A path inside the ZEZO tree is silently discarded (the real damage)

**File:** [`core/repo_context.py:194-202`](../core/repo_context.py#L194-L202)

```python
if explicit:
    p = _expand(explicit)
    if p and not is_zezo_source_dir(p):      # ← fails → falls through, no warning, no error
        p.mkdir(parents=True, exist_ok=True)
        remember_repo(str(p))
        return p, "explicit"
# ... falls through to the remember-state branch and returns THAT instead
```

`is_zezo_source_dir` ([`:29-40`](../core/repo_context.py#L29-L40)) returns True for anything under
the ZEZO root:

```python
cand = Path(p).resolve()
if cand == _ZEZO_ROOT or _ZEZO_ROOT in cand.parents:
    return True
```

Because Issue 1 put the clone folder under the ZEZO root, the explicit path was rejected and
`resolve()` returned the remembered repo. **Proven live:**

```
clone_dir          : D:\anitgravity\zezo work\jarvis-57\Desktop\linear_app_clone
is_zezo_source_dir : True
remembered repo    : C:\Users\Hamza\...\pytest-43\test_kilo_and_opencode_run_in_0\test_proj
resolve(explicit) -> C:\Users\Hamza\...\pytest-43\test_kilo_and_opencode_run_in_0\test_proj
                     | source = memory
```

**Impact:** this is the single most destructive link in the chain. A caller can pass a perfectly
correct absolute path and **the engine will work somewhere else entirely, silently**. It hit twice in
this session — once in the clone's rebuild stage, once in the follow-up agent dispatch.

---

### 🔴 Issue 3 — The engine reports SUCCESS when it wrote nothing

**File:** [`actions/antigravity_agent.py:703-711`](../actions/antigravity_agent.py#L703-L711),
[`:737-739`](../actions/antigravity_agent.py#L737-L739)

```python
created_list = []
for p in repo.rglob("*"):                    # full-tree scan — NOT a before/after diff
    created_list.append(rel)
...
real_files = [p for p in created_list if p not in (...)]
has_entry = (repo / "index.html").exists() or (repo / "main.py").exists() or (repo / "src").exists()

if not real_files or not has_entry:          # ← satisfied by files that were ALREADY there
```

In `run_in_place` on a pre-populated folder (the capture folder, or any existing project), these two
conditions are satisfied by pre-existing files. A CLI that exits immediately having written **zero
bytes** is therefore returned as `{"status": "success"}`.

**Impact:** this is why the run *looked* like it worked from the inside while Antigravity produced
nothing. Only the (new) `_verify_re_artifact` check caught it, and by then it named the wrong folder
(Issue 1/2).

---

### 🔴 Issue 4 — The task card flips to COMPLETED in the middle of the pipeline

**File:** [`actions/antigravity_agent.py:795`](../actions/antigravity_agent.py#L795)
→ [`core/task_manager.py:598-611`](../core/task_manager.py#L598-L611)

```python
ctx.on_complete(result_payload)          # engine, called with the CLONE task's own ctx
```

```python
def _on_complete(self, task_id, result=None):
    s.status = TaskStatus.DONE
    s.progress = 100
    s.message = "completed"
```

`_run_reverse_engineer` passes the clone task's own `ctx` into `antigravity_action(..., task_ctx=ctx)`
so the build reports into one card — but `_run_worker` then calls `on_complete()` on that same ctx.
The **WEBSITE_CLONER card is marked DONE (100%, "completed") while `_clone_worker` is still running**,
before `_verify_re_artifact` has been consulted.

**Impact:** exactly the report — "task complete ho gaya", and the raw capture link had already been
opened. The card then flipped DONE → FAILED, which is what the failure screenshot shows.

---

### 🔴 Issue 5 — Wrong link opened, and a localhost server is started for a raw HTML file

**File:** [`actions/website_cloner.py:2928-2941`](../actions/website_cloner.py#L2928-L2941)

```python
preview_url, port = start_local_preview_server(clone_dir)                  # unconditional
antigravity_preview_url = f"{preview_base}/antigravity_clone.html"         # ← uncage's raw snapshot
browser_control({"action": "go_to", "url": antigravity_preview_url})
```

Three distinct problems:

1. **A server is started even for a single raw HTML deliverable.** As the user said: *"agar raw HTML
   file hai to server nahi chalana chahiye… wo direct HTML file hai, usko browser pe open karega."*
   `127.0.0.1` is unnecessary indirection for a file that opens by double-click.
2. **What was opened is uncage's `antigravity_clone.html`** — the non-customizable snapshot. That is
   the exact artifact the feature exists to move *away* from.
3. **The artifact is only opened on success.** When the rebuild fails, the artifact-open block never
   runs, so the last thing in front of the user is the raw snapshot.

The URL the user saw — `http://127.0.0.1:9400/antigravity_clone.html` — is this line.

---

### 🔴 Issue 6 — `core/prompt.txt` was never updated for the new flow (this is why ZEZO said "React")

**File:** [`core/prompt.txt:405-412`](../core/prompt.txt#L405-L412)

```
- WEBSITE CLONE REACT REBUILD FAILURE: if the failed background task was a website clone whose React
  rebuild failed, the error text starts with "React rebuild FAILED -" and names the folder ...
  2. ... but the React rebuild failed ...
  3. ... fleet_control(action='dispatch', agent_id='VERVE', path='<the exact folder from the error>', ...)
     ALWAYS pass `path` - without it the agent gets a brand-new empty folder and the captured work is lost.
```

Three failures in one block:

- The new failure message is **`"Rebuild FAILED - capture intact at …"`**. It does **not** start with
  `"React rebuild FAILED -"`, so **this branch never matched**.
- The branch hardcodes **"React"**. With the trigger dead, the model improvised and told the user
  "the React rebuild failed" although the requested format was raw HTML (proven by the artifact name
  `rebuilt.html`).
- Because the branch never ran, the **"ALWAYS pass `path`"** rule never applied → the agent was
  dispatched without a path → Issue 2 → the same pytest folder again.

Also [`core/prompt.txt:384`](../core/prompt.txt#L384):

```
* After clone completes: Deliver ONE concise completion sentence: "Website clone is complete, and the
  live preview is open in your browser."
```

There is **no failure branch for "capture ok / rebuild failed"**, so the model announced completion.

> ⚠️ **This one is a regression introduced by the v6 rewrite:** the failure message was changed from
> `React rebuild FAILED -` to `Rebuild FAILED -` without updating the string the prompt matches on.

---

### 🔴 Issue 7 — The agent was dispatched without a path, and a design blueprint was injected

Two separate defects that together produced "नया design बना दिया".

**(a) No path on the hand-off.** `_handle_dispatch` does support it —
[`actions/fleet_control.py:40`](../actions/fleet_control.py#L40):
```python
target_path = str(params.get("path") or params.get("project_path") or "").strip() or None
```
But the model never passed it (Issue 6 killed the instruction that says to), so the dispatch fell
through to `resolve()` → memory → the pytest folder. The chat claim *"I've just dispatched Verve to
work on the linear_app_clone folder directly"* is contradicted by the agy log, which shows the
pytest workspace for that run too.

**(b) Hamza Taste design injection on the agent path.**
[`actions/antigravity_agent.py:406`](../actions/antigravity_agent.py#L406):
```python
if is_ui_task(task) and not is_verbatim and not payload.get("skip_design"):
    resolved_design = resolve_design(task, session_memory=session_mem, repo_path=repo)
```
The clone's own rebuild is protected (`skip_design=True`, `prompt_mode="verbatim"`). A dispatched
agent / plain `antigravity_run` call is **not** — so a Hamza Taste blueprint is injected. That is why
the "rebuild" came back as *"the full Aura Frame design reference"* instead of a reproduction of
Linear. `Aura Frame` is one of the Hamza Taste references (see
`tests/test_design_system_suite.py:6`).

The unrelated page that ended up in the same folder proves the point: `index.html` (12:34) is titled
**"Image Gen Dashboard Canvas"**.

---

### 🔴 Issue 8 — `[object Object]` in Execution Logs (the reason diagnosis was blind)

**Backend:** [`core/task_manager.py:103`](../core/task_manager.py#L103) — `logs: list[dict]`,
appended at [`:594`](../core/task_manager.py#L594) as `{"time", "text", "progress"}`.

**Frontend:** [`TaskManagerModal.tsx:567`](../frontend/src/components/tasks/TaskManagerModal.tsx#L567)

```tsx
{Array.isArray(selectedTask.logs) ? selectedTask.logs.join('\n') : String(selectedTask.logs)}
```

`Array.prototype.join` calls `String()` on each element; the elements are objects → `"[object Object]"`.
The eleven lines in the screenshot are eleven log entries rendered uselessly.

**Impact:** the real failure text was in the card the whole time and could not be read. Every
diagnosis of a failed clone is blind until this is fixed. (Fix direction: map to `l.time + ' ' + l.text`.)

---

### 🟠 Issue 9 — The read-back hides the resolved location

**File:** [`actions/website_cloner.py:3090`](../actions/website_cloner.py#L3090)

```python
folder = Path(target_dir).name if target_dir else default_dir.name
```

The user confirmed after hearing *"into 'linear_app_clone'"*. The **actual resolved path was never
spoken**, so the wrong location could not be caught at the confirmation step — which is the one place
it was cheap to catch. It also never mentioned that the destination was inside the ZEZO repo.

---

### 🟠 Issue 10 — Production state is polluted by test runs (the trigger for the fallback)

**File:** [`core/repo_context.py:25`](../core/repo_context.py#L25)
```python
_STORE_PATH = Path(__file__).resolve().parent.parent / "memory" / "repo_context.json"
```

That is a **real production file**, and it currently contains:

```json
{
  "last_active_repo": "C:\\Users\\Hamza\\AppData\\Local\\Temp\\pytest-of-Hamza\\pytest-43\\test_kilo_and_opencode_run_in_0\\test_proj",
  "active_project":   "C:\\Users\\Hamza\\AppData\\Local\\Temp\\pytest-of-Hamza\\pytest-43\\test_kilo_and_opencode_run_in_0\\test_proj"
}
```

Tests call `remember_repo()` directly (e.g. `tests/test_payload_and_task_modal.py:10`) and
`memory/*.json` is gitignored, so the pollution is invisible and permanent. This is the value that
(a) ZEZO reported to the user as "the path you are working on", and (b) became `agy`'s workspace.

---

### 🟡 Issue 11 — ZEZO writes into a folder it should not touch

[`actions/antigravity_agent.py:396`](../actions/antigravity_agent.py#L396) — `_ensure_gitignore(repo)`
drops a `.gitignore` into the engine's workspace. It is correctly skipped in `prompt_mode="verbatim"`
(the clone's own rebuild), but **not** on the agent/`antigravity_run` path — hence the stray
74-byte `.gitignore` in the temp folder at 12:32.

### 🟡 Issue 12 — Model string is not recognised by the CLI
`core/models.py:65` sets `gemini-3.8-flash-medium` and the task card showed it, but `agy` received
`gemini-3.7-flash-medium` and said `not in local config, defaulting to CCPA` — i.e. neither value is
a model the CLI knows, so it silently ran on its own default.

### 🟡 Issue 13 — Dirty git tree from design re-extraction
`skills/hamza_taste/references/design md/*.md` (5 files) are modified — **timestamp-only**
(`extracted_at` only). Worth knowing before blaming a diff.

---

## 3. What is new versus pre-existing (honest attribution)

| Issue | Origin |
|---|---|
| 1, 1a, 1b — `target_dir` CWD resolve → clone written into the ZEZO repo → recorded as the active project | **pre-existing** (present in v5); 1b is the `remember_repo` guard asymmetry, also pre-existing |
| 2 — silent discard of an explicit path | **pre-existing** |
| 3 — engine false-success check | **pre-existing** |
| 4 — nested `on_complete` flips the card | **pre-existing** (v5 used the same `task_ctx=ctx`) |
| 5 — unconditional server + wrong file opened | **pre-existing** |
| 6 — `prompt.txt` out of sync | **INTRODUCED by the v6 rewrite** (failure text changed, prompt string not) |
| 7 — no path + design injection on the agent path | **pre-existing** |
| 8 — `[object Object]` logs | **pre-existing** |
| 9 — read-back hides the path | **pre-existing** |
| 10 — test pollution of production state | **pre-existing** |
| 11/12/13 | **pre-existing / minor** |

Worker-side checks added in v6 (`_uncage_result_ok`, `verify_local_assets`, `_verify_re_artifact`)
all behaved correctly — `_verify_re_artifact` is precisely what surfaced this failure instead of
shipping a fake success.

---

## 4. User-reported symptom → root cause map

| Reported | Root cause |
|---|---|
| Wrong link opened (`127.0.0.1:9400/antigravity_clone.html`) | Issue 5 |
| Wrong folder used | Issue 1 → Issue 2 → Issue 10 |
| **Clone created inside the ZEZO project folder** (14.4 MB / 811 files, untracked and un-ignored) | Issue 1a — the same `resolve()` against ZEZO's CWD; this is also what arms Issue 2 |
| The user's real `C:\Users\Hamza\Desktop\` is still empty | Issue 1 (the `~/Desktop` mapping at `repo_context.py:132-133` was bypassed) |
| ZEZO now believes the "active project" is that in-repo folder | Issue 1b — `long_term.json` `projects.active_project` was written to the in-repo path |
| ZEZO said it was working in `linear_app_clone` but the agent ran in a temp folder | Issue 1b + Issue 10 — the two active-project stores hold two *different* wrong paths |
| "Rebuild stack galat samjha" / said "React" | Issue 6 (stale prompt) + Issue 7b (design injection) |
| Antigravity never ran / no task assigned | Issue 2 (wrong workspace) + Issue 3 (false success) + `agy` not logged in (§1.3) |
| Task showed COMPLETED then failed | Issue 4 |
| `[object Object]` in logs | Issue 8 |
| A brand-new design was generated instead | Issue 7a + 7b |
| Raw HTML should not need a server | Issue 5 |
| A raw snapshot must not be the deliverable | Issue 5 (+ `prompt_mode="verbatim"` already prevents the design blueprint) |
| Uncage itself worked | ✅ — capture in `Desktop/linear_app_clone` is intact and correct |

---

## 5. Dependency order (if these are fixed later)

```
Issue 1b (the two active-project stores disagree; one writer is unguarded) ─┐
Issue 10 (clear the polluted store)                                       ─┤
Issue 1  (resolve "Desktop" → ~/Desktop)                                   ├─► Issue 2 stops firing
Issue 2  (never silently drop a path)                                      ┘
        └─► the engine runs in the capture folder
                └─► Issue 3 no longer matters (real files land where they are expected)
Issue 4  (do not complete the caller's card)
Issue 6  (re-sync prompt.txt with the real failure text)
Issue 8  (logs readable) ─► everything above becomes debuggable
Issue 5  (open the real artifact; no server for a raw file)
Issue 7  (pass the path; do not inject a design blueprint on a rebuild)
```

Issues **1, 1a, 1b, 2, 10 and 3** are the ones that turned a **working rebuild** into a reported
failure — and left 14.4 MB of a third-party site sitting inside ZEZO's own repository, un-ignored,
with ZEZO's long-term memory pointing at it.
