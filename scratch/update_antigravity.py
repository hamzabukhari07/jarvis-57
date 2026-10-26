from pathlib import Path

path = Path("actions/antigravity_agent.py")
text = path.read_text(encoding="utf-8")

old_block = """        # Template Provisioner: When a design template is resolved (from catalog or reference),
        # copy the raw HTML template directly to repo / "index.html" as initial scaffold.
        template_provisioned = False
        if resolved_design and resolved_design.is_active() and resolved_design.raw_html:
            try:
                if not is_existing_project or is_redesign or wants_new_build:
                    (repo / "index.html").write_text(resolved_design.raw_html, encoding="utf-8")
                    template_provisioned = True
                    ctx.report(8, f"Master template scaffold placed at index.html ({resolved_design.source_name})")
            except Exception as e:
                logger.warning("Failed to copy raw HTML template to index.html: %s", e)

        # Build clean, bounded prompt for CLI to prevent Windows 32KB command-line overflow
        prompt_parts = [
            f"Task: {task}",
            f"Target Workspace Directory: {repo.as_posix()}",
        ]

        # Directive synthesis: In-place adaptation when template is provisioned
        design_directive = ""
        if template_provisioned:
            in_place_parts = [
                "IN-PLACE ADAPTATION DIRECTIVE:\\n"
                "A master design template has been placed at 'index.html'.\\n"
                "DO NOT write a new website from scratch. \\n"
                "YOUR MISSION: Update and adapt the existing 'index.html' in place. \\n"
                "Keep all existing CSS styles, color tokens, animations, and typography intact.\\n"
                "Replace the placeholder text, titles, navigation items, and project cards with the real user content provided below."
            ]
            entity_val = payload.get("entity_content")
            if entity_val:
                in_place_parts.append(f"USER CONTENT & PROFILE DATA:\\n{entity_val}")
            if resolved_design.anti_slop_rules:
                in_place_parts.append(resolved_design.anti_slop_rules)
            design_directive = "\\n\\n".join(in_place_parts)"""

new_block = """        # Master Design Reference Provisioner: Copy 100% untruncated raw HTML to reference.html (Read-Only Source of Truth)
        reference_provisioned = False
        if resolved_design and resolved_design.is_active():
            try:
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

                if reference_provisioned:
                    ctx.report(8, f"Master design reference placed at reference.html ({resolved_design.source_name})")
            except Exception as e:
                logger.warning("Failed to provision master reference.html: %s", e)

        # Build clean, bounded prompt for CLI to prevent Windows 32KB command-line overflow
        prompt_parts = [
            f"Task: {task}",
            f"Target Workspace Directory: {repo.as_posix()}",
        ]

        # Directive synthesis: Reference-guided synthesis per website_build SKILL.md
        design_directive = ""
        if reference_provisioned:
            ref_parts = [
                "🎨 MASTER DESIGN SYSTEM REFERENCE: 'reference.html'\\n"
                "A complete, untruncated master design template has been placed in your workspace at 'reference.html'.\\n"
                "READ AND INSPECT 'reference.html' FIRST. It contains the exact CSS styling, color palette, typography hierarchy, glassmorphic elevation, micro-interactions, layout grid, and @keyframes animations.\\n"
                "YOUR MISSION:\\n"
                "1. Generate 'index.html' in the workspace root as the primary entry point / deliverable.\\n"
                "2. Faithfully adapt and port the design system from 'reference.html' into 'index.html' (or modular CSS/React components if requested).\\n"
                "3. Populate 'index.html' with authentic user copy, headings, and domain content based on the user's task prompt.\\n"
                "4. EXTENSIBILITY: When adding new sections or pages, borrow the existing card wrappers, heading typography classes, and button markup from 'reference.html'.\\n"
                "5. DO NOT edit, mutate, or delete 'reference.html' — treat it as an immutable read-only design truth."
            ]
            entity_val = payload.get("entity_content")
            if entity_val:
                ref_parts.append(f"USER CONTENT & PROFILE DATA:\\n{entity_val}")
            if resolved_design.anti_slop_rules:
                ref_parts.append(resolved_design.anti_slop_rules)
            design_directive = "\\n\\n".join(ref_parts)"""

text_norm = text.replace("\r\n", "\n")
old_norm = old_block.replace("\r\n", "\n")
new_norm = new_block.replace("\r\n", "\n")

if old_norm in text_norm:
    updated = text_norm.replace(old_norm, new_norm, 1)
    if "\r\n" in text:
        updated = updated.replace("\n", "\r\n")
    path.write_text(updated, encoding="utf-8")
    print("SUCCESS: antigravity_agent.py updated")
else:
    print("FAILED: old_norm not found")
