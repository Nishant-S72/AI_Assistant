"""
Action Planner - LLM-based action planning with validation and schema checks.
"""
from typing import Dict, Any, Optional, List
from app.llm.provider import run_llm, load_prompt
from app.llm.prompt_builder import build_prompt
from app.core.config import ACTION_TYPES
from app.core.errors import ValidationError
from app.core.logger import logger
from app.utils.validation import validate_action_plan
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
        
        # Build structured plan for validation
        structured_plan = {
            "action_type": action_type,
            "parameters": parameters,
        }
        
        # Validate plan using schema-level sanity checks
        is_valid, validation_errors, missing_fields = validate_action_plan(structured_plan)
        
        # Merge with LLM-reported missing fields
        llm_missing = plan.get("missing_fields", [])
        all_missing = list(set(missing_fields + llm_missing))
        
        # If validation failed, regenerate with correction instructions
        if not is_valid or validation_errors:
            logger.warning(
                f"Action plan validation failed: {validation_errors}",
                extra={
                    "action_type": action_type,
                    "validation_errors": validation_errors,
                    "missing_fields": all_missing,
                    "correlation_id": correlation_id,
                }
            )
            
            # Regenerate plan with correction instructions
            correction_instructions = f"""
Previous plan had validation errors:
- {chr(10).join(validation_errors)}
- Missing fields: {', '.join(all_missing) if all_missing else 'None'}

Please regenerate the action plan with these corrections in mind.
"""
            
            # Retry once with corrections
            try:
                corrected_prompt = full_prompt + "\n\n" + correction_instructions
                corrected_response = await run_llm(
                    task="action_planning",
                    prompt=corrected_prompt,
                    system_prompt=system_prompt,
                    temperature=0.2,  # Even lower temperature for corrections
                    max_tokens=500,
                    correlation_id=correlation_id,
                )
                
                # Parse corrected response
                corrected_json_text = corrected_response.strip()
                corrected_json_text = re.sub(r"```json\s*", "", corrected_json_text)
                corrected_json_text = re.sub(r"```\s*", "", corrected_json_text)
                corrected_json_match = re.search(r"\{[\s\S]*\}", corrected_json_text)
                if corrected_json_match:
                    corrected_json_text = corrected_json_match.group(0)
                
                corrected_plan = json.loads(corrected_json_text)
                corrected_action_type = corrected_plan.get("action_type", "").lower()
                corrected_parameters = {k: v for k, v in corrected_plan.items() 
                                      if k not in ["action_type", "confidence", "missing_fields"]}
                
                # Re-validate corrected plan
                corrected_structured = {
                    "action_type": corrected_action_type,
                    "parameters": corrected_parameters,
                }
                is_valid_corrected, corrected_errors, corrected_missing = validate_action_plan(corrected_structured)
                
                if is_valid_corrected:
                    logger.info(
                        f"Action plan corrected successfully: {corrected_action_type}",
                        extra={"correlation_id": correlation_id}
                    )
                    return {
                        "action_type": corrected_action_type,
                        "parameters": corrected_parameters,
                        "confidence": corrected_plan.get("confidence", 0.7),
                        "missing_fields": corrected_missing,
                    }
                else:
                    logger.error(
                        f"Corrected plan still invalid: {corrected_errors}",
                        extra={"correlation_id": correlation_id}
                    )
            except Exception as e:
                logger.error(f"Failed to regenerate action plan: {e}", extra={"correlation_id": correlation_id})
        
        result = {
            "action_type": action_type,
            "parameters": parameters,
            "confidence": plan.get("confidence", 0.8),
            "missing_fields": all_missing,
        }
        
        if validation_errors:
            result["validation_errors"] = validation_errors
        
        logger.info(
            f"Action planned: {action_type}",
            extra={
                "action_type": action_type,
                "confidence": result["confidence"],
                "missing_fields": result["missing_fields"],
                "validation_errors": validation_errors if validation_errors else None,
                "correlation_id": correlation_id,
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Action planning failed: {e}", extra={"correlation_id": correlation_id})
        raise

