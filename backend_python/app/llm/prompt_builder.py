"""
Prompt builder utility for standardized prompt construction.
"""
from typing import Dict, Any, Optional
from pathlib import Path
from app.llm.prompts import common_sections


def build_prompt(
    template_name: str,
    variables: Dict[str, Any],
    user_tier: Optional[str] = None,
) -> str:
    """
    Build a standardized prompt from a template.
    
    Args:
        template_name: Name of the prompt template file (without .txt)
        variables: Dictionary of variables to substitute
        user_tier: Optional user tier ("assist" or "pro")
    
    Returns:
        Fully constructed prompt string
    """
    # Load template
    prompts_dir = Path(__file__).parent / "prompts"
    template_path = prompts_dir / f"{template_name}.txt"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_name}.txt")
    
    template = template_path.read_text(encoding="utf-8")
    
    # Build common sections
    sections = {
        "system_context": common_sections.SYSTEM_ROLES.get(
            template_name.replace("_prompt", ""),
            common_sections.SYSTEM_ROLES["assistant"]
        ),
        "universal_disclaimers": common_sections.UNIVERSAL_DISCLAIMERS,
        "style_guidelines": common_sections.STYLE_GUIDELINES,
    }
    
    # Add tier-specific instructions if tier is provided
    if user_tier:
        tier_key = "assist" if user_tier.lower() == "assist" else "pro"
        sections["tier_instructions"] = common_sections.TIER_INSTRUCTIONS.get(tier_key, "")
    
    # Add examples based on template type
    if "intent" in template_name:
        sections["examples"] = common_sections.INTENT_EXAMPLES
    elif "action" in template_name:
        sections["examples"] = common_sections.ACTION_PLANNING_EXAMPLES
    elif "reply" in template_name:
        tone = variables.get("tone", "warm")
        sections["examples"] = common_sections.REPLY_GENERATION_EXAMPLES.get(tone, "")
    
    # Replace section placeholders
    for key, value in sections.items():
        # Use double braces to escape in f-string, then replace
        placeholder = "{{" + key + "}}"
        template = template.replace(placeholder, value)
    
    # Replace variable placeholders
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if placeholder in template:
            # Format value appropriately
            if isinstance(value, list):
                formatted_value = "\n".join([f"- {item}" for item in value])
            elif isinstance(value, dict):
                formatted_value = "\n".join([f"- {k}: {v}" for k, v in value.items()])
            else:
                formatted_value = str(value)
            template = template.replace(placeholder, formatted_value)
    
    return template

