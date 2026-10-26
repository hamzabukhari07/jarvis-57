Plan: Simplify Agent CLI Pass-Through (Remove Over-Engineering & Wrappers)
Context

ZEZO currently wraps system CLI binaries (agy, kilo, opencode) with heavy pre-scaffolding, stack heuristics, design blueprint injections, window throttling, and Python fallback logic. When handling novel or complex user prompts (such as full-stack app builds), these heuristic wrappers and hardcoded regex prompt transformations introduce friction and deviate from the minimalist vision of ZEZO as a clean orchestrator that passes raw user prompts directly to the native system CLIs.

This plan details the removal of unnecessary wrapper heuristics, design injection layers, and fallback logic across actions/antigravity_agent.py, actions/opencode_agent.py, and actions/kilo_agent.py, replacing them with a streamlined, direct pass-through execution model.

🎨 User Vision & Architecture Diagram
The user's core vision for ZEZO is a clean, direct pass-through orchestrator that sends exact user prompts straight to system CLIs (agy, kilo, opencode) without heavy pre-scaffolding or wrapper overhead.

flowchart TD
    subgraph User["👤 User Request"]
        A["Raw User Prompt\n('Build a full stack web app...')"]
    end

    subgraph ZEZO["⚡ ZEZO Orchestrator (Simplified Pass-Through)"]
        B["Task Manager / Background Worker\n(No heuristics / No design injection / No fallbacks)"]
    end

    subgraph CLIs["🛠️ Native System CLI Binaries"]
        C1["Antigravity CLI (agy)"]
        C2["OpenCode CLI (opencode)"]
        C3["Kilo CLI (kilo)"]
    end

    subgraph Target["📁 Target Workspace"]
        D["Project Files on Disk"]
    end

    A --> B
    B -->|Direct Pass-Through -p / run| C1
    B -->|Direct Pass-Through run| C2
    B -->|Direct Pass-Through run| C3
    C1 --> D
    C2 --> D
    C3 --> D
Recommended Approach
Streamline actions/antigravity_agent.py:

Remove complex design resolver auto-injections (resolve_design, format_design_prompt) and blueprint provisioning.
Remove heavy pre-scaffolding prompt wrappers, regex heuristics, and Windows job object CPU/memory throttling layers.
Forward the raw user prompt and project path directly to the agy CLI binary (agy -p <task> --add-dir <repo> --dangerously-skip-permissions).
Streamline actions/opencode_agent.py & actions/kilo_agent.py:

Strip out wrapper overhead, TASK_SPEC.md splitting logic, design injections, and speculative prompt formatting.
Directly execute opencode run and kilo run with the user's prompt and target project directory.
Preserve Core Safety & Execution Ground Truth:

Maintain correct subprocess execution with subprocess.CREATE_NO_WINDOW on Windows.
Retain task tracking and proper exit code / output reporting for async background task execution.
Critical Files to Modify
actions/antigravity_agent.py: Remove design auto-injection heuristics, job object throttling, and complex prompt wrappers; implement clean direct pass-through to agy.
actions/opencode_agent.py: Remove wrapper overhead and simplify execution to pass prompts directly to opencode.
actions/kilo_agent.py: Remove wrapper overhead and simplify execution to pass prompts directly to kilo.
Verification Plan
Static Analysis:
Run python -m py_compile actions/antigravity_agent.py actions/opencode_agent.py actions/kilo_agent.py to ensure syntax correctness and clean imports.
Runtime Verification:
Invoke agent actions with test prompts to verify that the CLI binary receives the raw prompt correctly and executes without wrapper errors.
Regression Check:
Run relevant tests (e.g. pytest tests/) to ensure system stability.