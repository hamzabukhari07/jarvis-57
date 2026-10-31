from pathlib import Path
from core.skill_prompt_engineer import craft_skill_engine_prompt

def test_generate_design_md():
    # 1. Read real SKILL.md directly from repository
    skill_file = Path("skills/generate_design_md/SKILL.md")
    if not skill_file.exists():
        print(f"Error: {skill_file} not found!")
        return

    skill_sop = skill_file.read_text(encoding="utf-8")

    # 2. Your actual task & destination directory
    user_task = "Extract design system and create DESIGN.md for https://www.context.dev/"
    target_dir = "C:/Users/Hamza Bukhari/Desktop/context-design-test"

    print("=" * 80)
    print("🎯 TESTING SKILL PROMPT ENGINEER WITH REAL SKILL.MD")
    print(f"Skill: generate_design_md")
    print(f"Task:  {user_task}")
    print(f"Path:  {target_dir}")
    print("=" * 80 + "\n")

    # 3. Generate prompt using AI (Groq LPU)
    prompt = craft_skill_engine_prompt(
        skill_name="generate_design_md",
        skill_sop=skill_sop,
        user_task=user_task,
        target_dir=target_dir,
        context={"url": "https://www.context.dev/"},
        engine="antigravity",
    )

    print("--- [GENERATED PROMPT FOR ANTIGRAVITY] ---")
    print(prompt)
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_generate_design_md()
