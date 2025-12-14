"""
Action Planner - LLM-based action planning with JSON output.
"""
from typing import Dict, Any, Optional, List
from app.llm.provider import run_llm, load_prompt
from app.core.config import ACTION_TYPES
from app.core.errors import ValidationError
from app.core.logger import logger
import json
import re


async def plan_action(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Plan an action from user message.
    
    Returns:
        {
            "action_type": str,
            "parameters": Dict[str, Any],
            "confidence": float,
            "missing_fields": List[str],
        }
    """
    try:
        # Load action planner prompt
        prompt_template = load_prompt("action_planner_prompt")
        
        # Build context from conversation history
        context_text = ""
        if conversation_history:
            recent = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
            context_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent
            ])
        
        # Build full prompt
        full_prompt = f"""User message: {user_message}

{f"Conversation context:\n{context_text}\n" if context_text else ""}

Analyze the user message and determine:
1. What action they want to perform
2. What parameters can be inferred
3. What information is missing

Output valid JSON only."""
        
        system_prompt = prompt_template
        
        response = await run_llm(
            task="action_planning",
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=500,
            correlation_id=correlation_id,
        )
        
        # Parse JSON from response
        json_text = response.strip()
        
        # Remove markdown code blocks if present
        json_text = re.sub(r"```json\s*", "", json_text)
        json_text = re.sub(r"```\s*", "", json_text)
        
        # Extract JSON object
        json_match = re.search(r"\{[\s\S]*\}", json_text)
        if json_match:
            json_text = json_match.group(0)
        
        try:
            plan = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse action plan JSON: {e}", extra={"response": response})
            raise ValidationError(f"Invalid JSON from action planner: {e}")
        
        # Validate action_type
        action_type = plan.get("action_type", "").lower()
        if action_type not in ACTION_TYPES:
            logger.warning(
                f"Unknown action type: {action_type}",
                extra={"action_type": action_type, "correlation_id": correlation_id}
            )
            # Default to general if unknown
            return {
                "action_type": None,
                "parameters": {},
                "confidence": 0.0,
                "missing_fields": ["action_type"],
            }
        
        # Extract parameters (everything except action_type, confidence, missing_fields)
        parameters = {k: v for k, v in plan.items() if k not in ["action_type", "confidence", "missing_fields"]}
        
        result = {
            "action_type": action_type,
            "parameters": parameters,
            "confidence": plan.get("confidence", 0.8),
            "missing_fields": plan.get("missing_fields", []),
        }
        
        logger.info(
            f"Action planned: {action_type}",
            extra={
                "action_type": action_type,
                "confidence": result["confidence"],
                "missing_fields": result["missing_fields"],
                "correlation_id": correlation_id,
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Action planning failed: {e}", extra={"correlation_id": correlation_id})
        raise

