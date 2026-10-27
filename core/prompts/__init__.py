"""core/prompts
Prompt synthesis and archetype templates for autonomous coding agents.

Creator & Lead Architect: Hamza Bukhari
"""

from core.prompts.prompt_synthesizer import (
    DASHBOARD,
    LANDING_PAGE,
    PORTFOLIO,
    SURGICAL_EDIT,
    detect_archetype,
    load_exemplar,
    synthesize_prompt,
)

__all__ = [
    "load_exemplar",
    "synthesize_prompt",
    "detect_archetype",
    "PORTFOLIO",
    "LANDING_PAGE",
    "SURGICAL_EDIT",
    "DASHBOARD",
]
