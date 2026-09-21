# Skill: debugger

## Purpose

Something is broken in JARVIS. Your job is to find the real cause 
and fix it with discipline — not to make the symptom disappear.

The failure mode this skill exists to prevent:

User reports a bug → agent makes a change → still broken → agent 
makes another change → something else breaks → 20 minutes later 
there are 5 random edits, the original bug, and 2 new bugs.

That is decay. Do not do that.

## When to invoke

Whenever the user says any of:
- "X is not working"
- "X broke"
- "X is behaving weird"
- "Why does X do Y"
- "Fix X"
- Any report of wrong behavior, error, crash, or misoutput

## Hard Rules — Read Twice

1. DO NOT make more than ONE change at a time.
2. DO NOT propose multiple fixes "to try".
3. DO NOT fix the symptom. Find the cause.
4. DO NOT touch unrelated code while debugging.
5. DO NOT say "fixed" until you have re-run the reproduction.
6. DO NOT guess. If you cannot reproduce, say so.

## Steps

### 1. Understand the bug

Restate the bug in 2–3 lines. Plain language, your own words.  
If the user's description is vague, ask UP TO 3 specific questions:

Examples:
- "What command or phrase did you use?"
- "What did you expect to happen?"
- "What actually happened? Any error message, log line, 
   or wrong output?"
- "Does it happen every time or only sometimes?"

Do not proceed until you have a clear, falsifiable description.

### 2. Reproduce it

Before touching code, reproduce the bug. Every single time.

Reproduction can be:
- Running the exact action the user described
- Running a small script that calls the broken function
- Reading the relevant log file for the exact failure
- Checking git status/log if it used to work and now does not

If you cannot reproduce it after 2 honest attempts:
- STOP. Report back: "I could not reproduce this. Here is what 
  I tried. Can you give me X, Y, Z to narrow it down?"
- Do not guess a fix. Do not "improve the code while you are 
  in there". Do not proceed.

### 3. Locate the smallest failing spot

Narrow it down:
- Which file?
- Which function?
- Which line or block?
- Which input triggers it?
- Which input does NOT trigger it?

Write one sentence:  
"The bug is in <file>:<function> when <condition>."

If you cannot pin it to a function, the bug is not yet located. 
Keep narrowing. Do not move on.

### 4. Form ONE theory

Write exactly ONE theory about the root cause. One. Not two. Not 
a list of possibilities.

Format:

> **Theory:** <one sentence about why this is happening>
> **Evidence:** <what in the code or output supports this>
> **Test:** <what you will run to confirm or disprove it>

Then run the test.

- If the test confirms the theory → move to step 5.
- If the test disproves the theory → discard it. Do not patch 
  around it. Do not "also try". Go back to step 3 and form a 
  new theory. Write it out. Test it.

You may loop between 3 and 4 as many times as needed. That is 
correct. What is NOT correct is jumping to a fix without a 
confirmed theory.

### 5. Fix the cause, not the symptom

Once the theory is confirmed:

- Fix the actual cause.
- Do not clamp a null to hide a crash. Find out why it was null.
- Do not add a try/except to silence an error. Fix what threw.
- Do not add an "if this bad state, skip" guard. Fix what 
  created the bad state.

If the fix requires touching more than 2 files → STOP.  
That is not a bug fix. That is a design problem. Report it:

> "This bug is caused by <design decision>, not a coding mistake. 
> The proper fix touches <files>. Do you want to (a) apply a 
> small temporary fix now and plan the proper fix, or (b) stop 
> and redesign?"

Let the user decide.

### 6. Make the minimum change

- One change. One file (usually).
- No refactors while you are in there.
- No renaming.
- No reformatting.
- No touching unrelated lines.
- Update AGENTS.md, decisions.md, or prompt.txt ONLY if the 
  fix changes a documented rule or behavior.

### 7. Re-run the reproduction

Run the exact same reproduction from step 2.

- Bug gone → move to step 8.
- Bug still there → revert the change. Do NOT stack another 
  fix on top. Go back to step 3 with what you learned.

Do not skip this step. "It looks fixed" is not the same as 
"It is fixed."

### 8. Verify nothing else broke

Run 2–3 nearby features that could have been affected.

For example, if you fixed `code_helper`:
- Run a normal code generation request
- Run a request that should hit the fallback
- Run `task_status`

If any of them broke → revert your fix and go back to step 3.

### 9. Report

Use this exact format:

```text
BUG: <one line>
REPRODUCED: <how>
ROOT CAUSE: <one sentence — the actual cause, not the symptom>
FIX: <file:function — what changed and why>
REVERTED? <no / yes — and why if yes>
TESTS RUN: <what you actually executed>
STATUS: FIXED / NOT REPRODUCED / NEEDS USER INPUT / DESIGN ISSUE
```

Short. No padding. No celebration.

## Anti-patterns — never do these

- Trying two fixes at once "to save time"
- Saying "this should work now" without re-running
- Fixing a warning or a lint error that is not the bug
- Refactoring while debugging ("it was ugly anyway")
- Adding a comment that says "TODO: fix properly" instead of 
  fixing properly or reporting a design issue
- Saying "the bug is likely X" and then fixing it without 
  proving X
- Reverting the user's other unrelated changes to "clean up"
- Touching main.py, the voice loop, or task_manager.py unless 
  the bug is proven to be there

## When to STOP and report instead of fixing

Stop and report — do not fix — when:
- You cannot reproduce the bug after 2 honest attempts
- The fix requires more than 2 files
- The root cause is a design decision, not a coding mistake
- The bug only happens on a machine or OS you cannot test
- You are not sure. Uncertainty is not a reason to guess.

Report format for these:

```text
STOPPING: <why>
EVIDENCE: <what you found>
OPTIONS: <2–3 paths forward>
NEXT: Await user decision.
```

## Behaviour rules

- **Trust the user over the tool.** If the user says "I see X" 
  and the tool says "X is not there", believe the user. Look 
  again.
- **The log is not the truth.** A log line saying "closed" 
  means the tool thinks it is closed, not that it is closed.
- **One change, one test, one result.** Loop until solved.
- **Short is fine.** Do not write a novel. Write what is needed.

---

## After the Fix

Once the fix is written and the reproduction passes:

### Step 1: Verify
Invoke the verify skill (`.antigravity/skills/verify.md`).
- Layer 1: static checks
- Layer 2: runtime evidence (paste actual log/output)
- Layer 3: regression (2+ existing features)

Do NOT write "FIXED" until all 3 layers pass.  
If runtime test cannot run → write UNVERIFIED with reason.

### Step 2: OpenSpec Check

If the bug was tracked under an OpenSpec proposal:
  `openspec list`
  - If the change now works: `/opsx:archive`
  - If not complete: leave active

If it was a plain bug fix (no spec): skip this step.

### Step 3: Update LEARNING_JOURNAL.md

Append an entry at the repo root:

```markdown
## [YYYY-MM-DD] — Bug: <one-line summary>
- What was broken:
- Root cause:
- Fix applied:
- Files touched:
- Lesson for next time:
```

Keep it human-readable. This is the persistent record — the chat will be gone tomorrow, this file will not.
