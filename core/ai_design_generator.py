"""
core/ai_design_generator.py — Settings-Driven AI Design Specification Generator.

Dynamically queries the active default coding engine (Antigravity CLI, OpenCode,
or Kilo Code) configured in ZEZO Frontend Settings, and invokes the engine's CLI
to inspect reference HTML and generate high-fidelity DESIGN.md files.

Adheres strictly to AGENTS.md:
- Creator & Lead Architect: Hamza Bukhari
- Dynamic Settings Binding via core.code_engines.get_default_engine()
- Windows subprocess creation flags (CREATE_NO_WINDOW)
- Non-blocking / graceful fallback to core.design_md_generator if CLI is unavailable
- Cyclomatic complexity < 15 per function
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from core.code_engines import (
    get_default_engine,
    resolve_binary,
    ENGINES,
    _CREATION_FLAGS,
)
from core.design_md_generator import generate_design_md as fallback_generate_design_md

if TYPE_CHECKING:
    from core.design_tokens import DesignTokens

logger = logging.getLogger("zezo.ai_design_generator")

EXTRACTION_SYSTEM_PROMPT = """You are a Lead UI/UX Systems Architect.
Analyze the provided HTML and extract its visual design specification strictly adhering to this XML format:

<design-context>
```yaml
theme: "<dark_obsidian|light_clean|editorial_warm|luxury_light|creative_bold>"
aesthetic_profile: "<short profile description>"
fonts:
  - "<Font 1>"
  - "<Font 2>"
display_font: "<Display Font>"
body_font: "<Body Font>"
mono_font: "<Mono Font, default monospace>"
colors:
  canvas: "<#hex>"
  surface: "<#hex>"
  surface_2: "<#hex>"
  ink: "<#hex>"
  body: "<#hex>"
  muted: "<#hex>"
  border: "<#hex>"
  border_strong: "<#hex>"
  primary_accent: "<#hex>"
  secondary_accent: "<#hex>"
  on_primary: "<#hex>"
  link: "<#hex>"
  link_deep: "<#hex>"
  link_soft: "<#hex>"
  semantic:
    success: "<#hex>"
    warning: "<#hex>"
    error: "<#hex>"
    info: "<#hex>"
  gradients: []
  warnings: []
rounded:
  sm: "<px>"
  md: "<px>"
  lg: "<px>"
  full: "9999px"
spacing:
  section_gap: "<gap>"
  container_max: "<max-w>"
```

## Typography Scale
| Role | Font | Size | Weight | Line Height | Tracking |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Display | ... | ... | ... | ... | ... |
| Body | ... | ... | ... | ... | ... |

## Component Recipes
- Primary CTA: CSS classes and micro-interactions
- Card: Border, surface, hover state
- Input: Border, focus glow, placeholder

## Anti-Slop Guidelines
- 3 to 5 strict visual rules tailored specifically to this template's aesthetic mood.
</design-context>

Return ONLY the <design-context> block with valid YAML frontmatter. No conversational preamble.
"""


def build_cli_command(engine_id: str, binary_path: str, prompt_file: Path) -> list[str]:
    """Builds execution command line list for the specified engine CLI."""
    if engine_id == "antigravity":
        # agy CLI batch non-interactive execution
        return [binary_path, "--non-interactive", "--prompt-file", str(prompt_file)]
    if engine_id == "opencode":
        return [binary_path, "run", f"@{prompt_file}"]
    if engine_id == "kilo":
        return [binary_path, "--batch", str(prompt_file)]
    return [binary_path, str(prompt_file)]


def generate_ai_design_md(
    raw_html: str,
    tokens: Optional[DesignTokens] = None,
    name: str = "design-system",
    output_path: Optional[Path] = None,
    timeout_sec: int = 45,
) -> str:
    """
    Generates DESIGN.md specification using the active default code engine configured in Settings.
    Falls back gracefully to deterministic generator if CLI is missing, disabled, or fails.
    """
    engine_id = get_default_engine()
    bin_path = resolve_binary(engine_id)

    if not bin_path or not os.path.exists(bin_path):
        logger.info(
            "Engine %s binary not resolved. Using deterministic design_md_generator fallback.",
            engine_id,
        )
        if tokens is None:
            from core.design_extractor import extract_design_tokens
            tokens = extract_design_tokens(raw_html)
        md_content = fallback_generate_design_md(tokens, name, output_path=output_path)
        return md_content

    # Prepare temp prompt payload for CLI execution
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_prompt = Path(tmp_dir) / "extract_prompt.txt"
        # Truncate HTML to first 25,000 chars for prompt payload to keep CLI fast
        sample_html = raw_html[:25000] if len(raw_html) > 25000 else raw_html
        tmp_prompt.write_text(
            f"{EXTRACTION_SYSTEM_PROMPT}\n\n--- REFERENCE HTML START ---\n{sample_html}\n--- REFERENCE HTML END ---",
            encoding="utf-8",
        )

        cmd = build_cli_command(engine_id, bin_path, tmp_prompt)
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                creationflags=_CREATION_FLAGS,
            )
            stdout = res.stdout.strip()
            if res.returncode == 0 and "<design-context>" in stdout and "</design-context>" in stdout:
                start_idx = stdout.find("<design-context>")
                end_idx = stdout.find("</design-context>") + len("</design-context>")
                extracted = stdout[start_idx:end_idx]
                if output_path:
                    output_path.write_text(extracted, encoding="utf-8")
                return extracted
        except Exception as e:
            logger.warning("Engine CLI extraction failed (%s): %s. Falling back to local generator.", engine_id, e)

    # Graceful deterministic fallback
    if tokens is None:
        from core.design_extractor import extract_design_tokens
        tokens = extract_design_tokens(raw_html)
    md_content = fallback_generate_design_md(tokens, name, output_path=output_path)
    return md_content


__all__ = [
    "generate_ai_design_md",
    "EXTRACTION_SYSTEM_PROMPT",
]
