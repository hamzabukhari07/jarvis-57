from pathlib import Path

path = Path("actions/kilo_agent.py")
text = path.read_text(encoding="utf-8")

# 1. Add MAX_CLI_PROMPT_LEN and _prepare_cli_task helper before _run_worker
target_before_worker = 'def _run_worker(params: dict, ctx: TaskContext) -> dict:'
replacement_before_worker = '''MAX_CLI_PROMPT_LEN = 4000


def _prepare_cli_task(task: str, repo_path: Path) -> str:
    """
    Ensure the CLI prompt does not exceed safe command-line buffer limits on Windows.
    If the prompt exceeds MAX_CLI_PROMPT_LEN or contains raw HTML blueprints,
    write the full task specification to TASK_SPEC.md in the repo workspace.
    """
    if not task:
        return ""

    task_lower = task.lower()
    is_large = len(task) > MAX_CLI_PROMPT_LEN
    has_raw_html = "```html" in task_lower or "<html" in task_lower or "<!doctype" in task_lower

    if not (is_large or has_raw_html):
        return task

    try:
        repo_path.mkdir(parents=True, exist_ok=True)
        spec_file = repo_path / "TASK_SPEC.md"
        spec_file.write_text(task, encoding="utf-8")
        return (
            "Execute the coding task defined in TASK_SPEC.md. "
            "Read TASK_SPEC.md in the workspace first, then implement all specifications, "
            "requirements, and guidelines exactly as described."
        )
    except Exception as e:
        logger.warning("Failed writing TASK_SPEC.md for Kilo (%s); truncating prompt", e)
        return task[:MAX_CLI_PROMPT_LEN]


def _run_worker(params: dict, ctx: TaskContext) -> dict:'''

# 2. In _run_worker, use _prepare_cli_task
target_cmd = 'cmd = [kilo_bin, "run", task, "--model", model, "--auto"]'
replacement_cmd = '''cli_task = _prepare_cli_task(task, Path(repo))
    cmd = [kilo_bin, "run", cli_task, "--model", model, "--auto"]'''

# 3. In kilo_agent, add design resolution and reference.html provisioning
target_kilo_agent = '''    model = _resolve_model(parameters.get("model") or parameters.get("model_id"))

    # In-place execution for fleet tasks (eliminates phantom ZEZO CODER cards)
    run_in_place = bool(parameters.get("run_in_place", False))
    task_ctx = parameters.get("task_ctx")

    if run_in_place:
        worker_params = {
            "repo": str(repo),
            "task": task,
            "model": model,
            "bin": kilo_bin,
        }
        res = _run_worker(worker_params, ctx=task_ctx)
        import json
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "kilo_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task,
            "model": model,
            "bin": kilo_bin,
        },
    )'''

replacement_kilo_agent = '''    model = _resolve_model(parameters.get("model") or parameters.get("model_id"))

    # Resolve design system tokens if UI/Web task
    from core.design_resolver import is_ui_task, resolve_design
    resolved_design = None
    task_with_design = task
    if is_ui_task(task):
        resolved_design = resolve_design(task, repo_path=repo)
        if resolved_design and resolved_design.is_active():
            reference_provisioned = False
            try:
                repo.mkdir(parents=True, exist_ok=True)
                ref_dst = repo / "reference.html"
                if getattr(resolved_design, "source_path", None) and resolved_design.source_path.exists():
                    import shutil
                    shutil.copy2(resolved_design.source_path, ref_dst)
                    reference_provisioned = True
                elif getattr(resolved_design, "full_raw_html", None) and resolved_design.full_raw_html.strip():
                    ref_dst.write_text(resolved_design.full_raw_html, encoding="utf-8")
                    reference_provisioned = True
                elif resolved_design.raw_html and resolved_design.raw_html.strip():
                    ref_dst.write_text(resolved_design.raw_html, encoding="utf-8")
                    reference_provisioned = True
            except Exception as e:
                logger.warning("Failed to provision reference.html for Kilo Code: %s", e)

            if reference_provisioned:
                design_directive = (
                    "🎨 MASTER DESIGN SYSTEM REFERENCE: 'reference.html'\\n"
                    "A complete, untruncated master design template has been placed in your workspace at 'reference.html'.\\n"
                    "READ AND INSPECT 'reference.html' FIRST. It contains the exact CSS styling, color palette, typography hierarchy, glassmorphic elevation, micro-interactions, layout grid, and @keyframes animations.\\n"
                    "YOUR MISSION:\\n"
                    "1. Generate 'index.html' in the workspace root as the primary entry point / deliverable.\\n"
                    "2. Faithfully adapt and port the design system from 'reference.html' into 'index.html' (or modular CSS/React components if requested).\\n"
                    "3. Populate 'index.html' with authentic user copy and domain content.\\n"
                    "4. EXTENSIBILITY: When adding new sections or pages, borrow the existing card wrappers, heading typography classes, and button markup from 'reference.html'.\\n"
                    "5. DO NOT edit, mutate, or delete 'reference.html' — treat it as an immutable read-only design truth."
                )
                if resolved_design.anti_slop_rules:
                    design_directive += f"\\n\\n{resolved_design.anti_slop_rules}"
                task_with_design = f"{task}\\n\\n{design_directive}"

    # In-place execution for fleet tasks (eliminates phantom ZEZO CODER cards)
    run_in_place = bool(parameters.get("run_in_place", False))
    task_ctx = parameters.get("task_ctx")

    if run_in_place:
        worker_params = {
            "repo": str(repo),
            "task": task_with_design,
            "model": model,
            "bin": kilo_bin,
        }
        res = _run_worker(worker_params, ctx=task_ctx)
        import json
        return json.dumps(res) if isinstance(res, dict) else str(res)

    tm = get_task_manager()
    task_id = tm.submit(
        "kilo_agent",
        _run_worker,
        {
            "repo": str(repo),
            "task": task_with_design,
            "model": model,
            "bin": kilo_bin,
        },
    )'''

text_norm = text.replace("\r\n", "\n")
t1 = target_before_worker.replace("\r\n", "\n")
r1 = replacement_before_worker.replace("\r\n", "\n")
t2 = target_cmd.replace("\r\n", "\n")
r2 = replacement_cmd.replace("\r\n", "\n")
t3 = target_kilo_agent.replace("\r\n", "\n")
r3 = replacement_kilo_agent.replace("\r\n", "\n")

assert t1 in text_norm, "t1 not found"
text_norm = text_norm.replace(t1, r1, 1)

assert t2 in text_norm, "t2 not found"
text_norm = text_norm.replace(t2, r2, 1)

assert t3 in text_norm, "t3 not found"
text_norm = text_norm.replace(t3, r3, 1)

if "\r\n" in text:
    text_norm = text_norm.replace("\n", "\r\n")

path.write_text(text_norm, encoding="utf-8")
print("SUCCESS: kilo_agent.py updated")
