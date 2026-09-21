# Skill: advisor

## Purpose

The user gives a vision (a feature idea, a change, a fix). Your job 
is to advise, not to build. You present options, trade-offs, edge 
cases, and risks. You stop and wait for approval. Only after the 
user approves do you write code — and then you do it via the 
develop skill.

## When to invoke

Whenever the user says any of:
- "add X", "remove X", "change X"
- "I want X", "can we do X", "should we X"
- "make it X", "improve X"
- Anything that would edit code

If the request is trivial (typo fix, one-line change with no side 
effects), skip this skill and just do it.

## Hard Rule — Read Twice

DO NOT WRITE CODE IN THIS SKILL.  
Not one line. Not a snippet. Not a "quick example".  
Even if the user asks for a preview — say no, and offer to 
implement after approval. This is non-negotiable.

## Steps

### 1. Restate the vision
Say it back in 1–2 lines, in your own words.  
If anything is genuinely ambiguous, ask UP TO 3 clarifying 
questions. Otherwise proceed.

### 2. Audit
Read these first:
- AGENTS.md — project rules and inter-dependency table
- decisions.md — past decisions (do not contradict them silently)
- The specific files likely affected

If AGENTS.md or decisions.md do not exist, note that and continue 
with a general read of the codebase.

### 3. Impact Analysis

Present, in this order:

**A) Files that will change**
- File path — what changes and why

**B) Files that might be affected indirectly**
- File path — what could break, why

**C) Existing features at risk**
- Feature — how it could regress

**D) Edge cases** (list at least 5, concrete)
Example format: "If the user runs this before OpenCode finishes, 
the task_id will be stale → what happens?"

**E) Risks**
- Data: could it corrupt, delete, or leak data?
- Security: new attack surface, new secret, new injection path?
- Performance: new blocking call, new thread, new memory?
- UX: voice becomes slower, HUD flickers, wrong language?

### 4. Options

Present 2–3 implementation approaches. Each option MUST have:

- **Name** — one-line description
- **How it works** — 2–3 lines, concrete
- **Pros** — 2–3 real bullets (not marketing)
- **Cons** — 2–3 real bullets (be honest)
- **Complexity** — low / medium / high
- **Risk** — low / medium / high
- **Touches** — list files
- **Testing needed** — what you would run

Then present a **comparison table**:

| | Option A | Option B | Option C |
|---|---|---|---|
| Complexity | | | |
| Risk | | | |
| Files touched | | | |
| Reversible? | | | |
| Fits existing patterns? | | | |

Then **recommend ONE** with reasoning tied to the actual project.  
Reasoning must reference something specific — a pattern in the code, 
a past decision in decisions.md, or a known constraint. Not generic 
"best practice" talk.

### 5. Decision Points

List any value or behavior that is NOT defined by the user's vision 
and cannot be inferred from the code. For each, say:

> "Undefined: X. Options: A / B / C. Which?"

Do not proceed past this list until the user answers.

### 6. STOP

End with exactly this line:

> **"Reply with the option number (and answers to any decision 
> points) and I will implement it via the develop skill. 
> No code will be written until you do."**

Then stop. Do not continue. Do not write code.

## After approval

When the user approves an option:
1. Confirm the option in one line.
2. Invoke the develop skill.
3. Follow the develop skill checklist exactly.
4. After implementation, invoke the verify skill.

## Behaviour rules

- **Do not be a yes-man.** If the idea is bad, say so plainly and 
  say why. A senior engineer tells the user when they are wrong.
- **Do not pad.** Short is fine. A two-line answer beats a two-page 
  answer if it says the same thing.
- **Do not guess.** If a value has no source, list it under 
  Decision Points. Do not invent it.
- **Do not contradict decisions.md silently.** If your proposal 
  conflicts with a past decision, flag it explicitly and say 
  "this reverses ADR-00X — is that intended?"
- **Do not exceed 3 options.** More than 3 is noise.
- **Do not use marketing language.** "Powerful", "seamless", 
  "robust" mean nothing. Concrete facts only.



## Simplicity Bias (MANDATORY)

When presenting options, ALWAYS include the simplest possible 
approach as the first option, even if it seems primitive.

Ranking rule for recommendations:
1. Prefer approaches that add ZERO new dependencies
2. Prefer approaches that keep the existing workflow intact
3. Prefer approaches that can be reversed in 1 file
4. Only escalate to complex stacks if the user EXPLICITLY asks 
   for it or if simplicity genuinely cannot solve the problem

Never recommend a stack (React, Vue, Tauri, Docker, etc.) 
without first stating:
- What problem it solves that vanilla cannot
- What it costs (time, dependencies, workflow changes)
- Whether the user actually has that problem

If the user asks "upgrade my UI" without specifics, the FIRST 
option must be "minimal change". The "best" option comes 
second.


## Order Rule

Options MUST be listed in this order:
1. Simplest (zero new dependencies, fewest files touched)
2. Balanced (moderate change, moderate gain)
3. Most powerful (but heavier)

Never reorder this. If the simplest option is also the best 
one for the user's case, say so explicitly: "Option 1 is both 
the simplest and the best fit."

The recommendation must NEVER be Option 3 unless:
- Option 1 and Option 2 both genuinely fail the requirement
- Or the user explicitly asked for the powerful route

Do not modify anything else in the file. Just append this 
section at the end.