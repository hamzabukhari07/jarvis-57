---
name: make_plan
description: Technical architecture planning, dependency-ordered phased roadmap creation, blast-radius assessment, and verification milestone checklists.
metadata:
  author: ZEZO / Hamza Bukhari
  version: '2.0'
---

# Technical Architecture Planning & Roadmap Formulation

Use this skill when turning user feature requirements into structured, dependency-ordered technical execution plans before coding.

## Planning Protocol:
1. **Architecture & Scope Analysis:**
   - Enumerate all affected files, modules, and API contracts.
   - Assess dependency blast radius using Code Graph Context.
2. **Phased Breakdown:**
   - Group tasks into logical, discrete phases with measurable exit criteria.
   - Enforce read-only safety for discovery and planning phases.
3. **3-Layer Verification Checklist:**
   - Every phase must specify static compilation, runtime evidence, and regression test requirements.
4. **Anti-Slop Adherence:**
   - Maintain function cyclomatic complexity $< 15$.
   - Avoid speculative abstractions and monolithic files.
