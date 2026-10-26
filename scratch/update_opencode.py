from pathlib import Path

path = Path("actions/opencode_agent.py")
text = path.read_text(encoding="utf-8")

old_block = """    # Resolve design system tokens if UI/Web task
    from core.design_resolver import is_ui_task, resolve_design, format_design_prompt
    resolved_design = None
    task_with_design = task
    if is_ui_task(task):
        resolved_design = resolve_design(task, repo_path=repo)
        if resolved_design and resolved_design.is_active():
            design_prompt = format_design_prompt(resolved_design)
            task_with_design = f"{task}\\n\\n{design_prompt}\""""

new_block = """    # Resolve design system tokens if UI/Web task
    from core.design_resolver import is_ui_task, resolve_design, format_design_prompt
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
                logger.warning("Failed to provision reference.html for OpenCode: %s", e)

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
            else:
                design_prompt = format_design_prompt(resolved_design)
                task_with_design = f"{task}\\n\\n{design_prompt}\""""

text_norm = text.replace("\r\n", "\n")
old_norm = old_block.replace("\r\n", "\n")
new_norm = new_block.replace("\r\n", "\n")

if old_norm in text_norm:
    updated = text_norm.replace(old_norm, new_norm, 1)
    if "\r\n" in text:
        updated = updated.replace("\n", "\r\n")
    path.write_text(updated, encoding="utf-8")
    print("SUCCESS: opencode_agent.py updated")
else:
    print("FAILED: old_norm not found")
