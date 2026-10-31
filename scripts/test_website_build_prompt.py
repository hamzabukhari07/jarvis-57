from pathlib import Path
from core.skill_prompt_engineer import craft_skill_engine_prompt

def test_website_build():
    # 1. Read real SKILL.md for website_build
    skill_file = Path("skills/website_build/SKILL.md")
    if not skill_file.exists():
        print(f"Error: {skill_file} not found!")
        return

    skill_sop = skill_file.read_text(encoding="utf-8")

    # 2. Your actual test task & target directory
    user_task = "Build a modern high-converting SaaS landing page for an AI voice assistant named Zezo"
    target_dir = "C:/Users/Hamza Bukhari/Desktop/zezo-saas-website"

    print("=" * 80)
    print("🌐 TESTING SKILL PROMPT ENGINEER: website_build")
    print(f"Skill: website_build")
    print(f"Task:  {user_task}")
    print(f"Path:  {target_dir}")
    print("=" * 80 + "\n")

    # 3. Generate prompt using AI (Groq LPU)
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
    )

    print("--- [GENERATED PROMPT FOR ANTIGRAVITY] ---")
    print(prompt)
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_website_build()
