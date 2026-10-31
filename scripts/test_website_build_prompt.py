from pathlib import Path
from core.skill_loader import get_skill_registry
from core.skill_prompt_engineer import craft_skill_engine_prompt

def test_website_build():
    skill_reg = get_skill_registry()
    skill_record = skill_reg.get_skill("website_build")
    if not skill_record:
        print("Error: website_build skill not found in registry!")
        return

    skill_sop = skill_record.instructions
    directive_hdr = skill_record.agent_directive_section

    # Actual test task & target directory
    user_task = "Build a modern high-converting SaaS landing page for an AI voice assistant named Zezo"
    target_dir = "C:/Users/Hamza Bukhari/Desktop/zezo-saas-website"

    print("=" * 80)
    print("🌐 TESTING SKILL PROMPT ENGINEER: website_build")
    print(f"Skill:             website_build")
    print(f"Directive Section: {directive_hdr}")
    print(f"Task:              {user_task}")
    print(f"Path:              {target_dir}")
    print("=" * 80 + "\n")

    # Generate prompt using AI (Groq LPU) passing directive_header
    prompt = craft_skill_engine_prompt(
        skill_name="website_build",
        skill_sop=skill_sop,
        user_task=user_task,
        target_dir=target_dir,
        context={
            "scope_type": "landing_page",
            "tech_stack": "single_file_html",
            "color_theme": "dark_modern",
        },
        engine="antigravity",
        directive_header=directive_hdr,
    )

    print("--- [GENERATED PROMPT FOR ANTIGRAVITY] ---")
    print(prompt)
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_website_build()
