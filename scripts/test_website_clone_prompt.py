from pathlib import Path
from core.skill_loader import get_skill_registry
from core.skill_prompt_engineer import craft_skill_engine_prompt

def test_website_clone():
    skill_reg = get_skill_registry()
    skill_record = skill_reg.get_skill("website_clone")
    if not skill_record:
        print("Error: website_clone skill not found in registry!")
        return

    skill_sop = skill_record.instructions
    directive_hdr = skill_record.agent_directive_section
    pre_flight = skill_record.pre_flight_action

    user_task = "Clone https://linear.app and produce a clean, self-contained offline rebuild in Single-File HTML"
    target_dir = "C:/Users/Hamza Bukhari/Desktop/linear-clone-test"

    print("=" * 80)
    print("🚀 TESTING SKILL PROMPT ENGINEER: website_clone")
    print(f"Skill:              website_clone")
    print(f"Pre-Flight Action:  {pre_flight}")
    print(f"Directive Section:  {directive_hdr}")
    print(f"Task:               {user_task}")
    print(f"Target Path:        {target_dir}")
    print("=" * 80 + "\n")

    # Generate prompt using AI (Groq LPU) passing directive_header explicitly
    prompt = craft_skill_engine_prompt(
        skill_name="website_clone",
        skill_sop=skill_sop,
        user_task=user_task,
        target_dir=target_dir,
        context={
            "url": "https://linear.app",
            "rebuild_mode": "clean_html",
        },
        engine="antigravity",
        directive_header=directive_hdr,
    )

    print("--- [GENERATED PROMPT FOR ANTIGRAVITY] ---")
    print(prompt)
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_website_clone()
