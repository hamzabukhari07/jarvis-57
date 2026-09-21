# Skill: evaluator

## Purpose

The user drops an external repo, folder, or code file into the 
workspace and asks: "Is this useful for JARVIS? What should I 
copy?" Your job is to evaluate and recommend. You do not write 
or modify code. You do not copy files. You produce a report and 
stop.

## When to invoke

Whenever the user says any of:
- "Look at this repo/folder and tell me if it's useful"
- "Is this good for JARVIS?"
- "Should I copy X from this?"
- "What can I take from this?"
- "Evaluate this code"
- Points at a path (folder/file) and asks about it

## Hard Rules — Read Twice

1. DO NOT modify, copy, move, or delete any file. Read-only.
2. DO NOT write code. Not one line. Even if the user asks for 
   a "quick fix" — say no, offer to implement after approval via 
   the develop skill.
3. DO NOT recommend copying anything without saying exactly 
   which files, and exactly what would need to change to fit 
   JARVIS's patterns.
4. DO NOT compare against imaginary best practices. Compare 
   against THIS project's AGENTS.md and decisions.md.
5. If you cannot determine something, say so. Do not guess.

## Steps

### 1. Understand what you are looking at

Identify:
- Type: full repo / subfolder / single file / snippet
- Language(s) and framework(s)
- Approximate size (files, lines)
- License — CRITICAL. If unknown or restrictive, flag it.
- External dependencies introduced
- Purpose in one line

If the folder is huge (>500 files), ask the user to narrow the 
scope before proceeding. Do not try to read everything.

### 2. Read the JARVIS context first

Before judging the external code, read:
- AGENTS.md — project rules and patterns
- decisions.md — past decisions
- The specific JARVIS files the external code would overlap 
  with (e.g. if it does search, read actions/web_search.py)

You cannot evaluate fit without knowing what you are fitting into.

### 3. Evaluate — the report

Produce these sections, in this order:

**A) What this is**
2–3 lines. Plain language. No marketing.

**B) Relevance to JARVIS**
Does it solve a problem JARVIS has? Yes / Partially / No.  
If No → say so plainly and stop here. Do not waste the user's 
time with pros/cons of something irrelevant.

**C) What is genuinely useful**
List specific pieces (files, functions, ideas) that are worth 
considering. Each entry:
- What it is
- Why it is useful here
- What JARVIS file it would replace or sit next to

**D) What to leave behind**
List specific pieces that are NOT worth copying and why.
Common reasons: wrong framework, heavier than needed, overlaps 
with existing code, license problem, unmaintained, poor quality.

**E) Conflicts with JARVIS**
- Does it duplicate existing functionality? Name the file.
- Does it contradict an ADR in decisions.md? Name the ADR.
- Does it break a rule in AGENTS.md? Name the rule.
- Does it introduce a new dependency JARVIS does not have?
- Would it break the "one file per action" pattern?
- Would it touch main.py or the voice loop?

**F) Risks**
- License: can it legally be copied into JARVIS (CC BY-NC 4.0)?
- Security: any network calls, telemetry, obfuscation, remote fetch?
- Maintenance: when was it last updated? Active?
- Complexity: how many files would come with it?
- Reversibility: if we take it and dislike it, how hard to remove?

**G) Three approaches**

Present exactly 3 options. Do not exceed 3.

**Option 1: Copy nothing.**  
What the user loses by ignoring this. When this is the right 
choice.

**Option 2: Take the idea, not the code.**  
Rewrite the concept inside JARVIS patterns from scratch.  
Pros: fits cleanly. Cons: more work, may miss edge cases.  
Complexity: usually lower than full integration.

**Option 3: Integrate the actual code.**  
Which specific files, how they would be adapted, what changes 
are needed to match JARVIS patterns.  
Pros: faster, tested by someone else.  
Cons: baggage, license, maintenance of external code.

**H) Comparison table**

| | Copy nothing | Idea only | Full integration |
|---|---|---|---|
| Effort | | | |
| Risk | | | |
| Fits JARVIS? | | | |
| Reversible? | | | |
| License OK? | | | |
| Adds dependencies? | | | |

**I) Recommendation**  
One of the three. Reasoning MUST reference something concrete 
from JARVIS — an existing file, an ADR, a rule, or a specific 
piece of the external code. No generic advice.

### 4. Decision Points

List anything that only the user can decide. For each:

> "Undecided: X. Options: A / B / C. Which?"

Typical decision points:
- License acceptance
- Whether to add a new dependency
- Whether to replace an existing JARVIS file
- Whether to adapt or rewrite

### 5. STOP

End with exactly this line:

> **"Reply with the approach (Copy nothing / Idea only / Full 
> integration), answers to any decision points, and I will 
> implement it via the develop skill. No files will be copied 
> or code written until you do."**

Then stop. Do not continue. Do not touch anything.

## Behaviour rules

- **Do not be a yes-man.** If the external code is bad, say so. 
  If it's good but useless for JARVIS, say so.
- **Do not praise.** "Well-written", "elegant", "clean" mean 
  nothing without specifics. Say what it does, not how nice it is.
- **Do not compare against popular projects.** Only compare 
  against JARVIS's actual code and decisions.
- **Do not recommend copying code from a repo with an unclear 
  or restrictive license.** Ever. Say so plainly.
- **Do not exceed 3 approaches.** More is noise.
- **Short is fine.** A three-line answer beats a three-page 
  answer if it says the same thing.



also please read D:\anitgravity\zezo version 2\.antigravity\skills\advisor.md