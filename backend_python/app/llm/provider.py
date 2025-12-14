"""
Centralized LLM provider - all LLM calls go through here.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.core.config import DEFAULT_LLM_MODEL, LLM_MODEL_ASSIGNMENTS
from app.core.errors import LLMError
from app.core.logger import logger
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import os
import json
import time


def load_prompt(prompt_name: str) -> str:
    """Load prompt from prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.txt"
    
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    
    # Fallback to parent directory
    alt_path = Path(__file__).parent.parent.parent / "prompts" / f"{prompt_name}.txt"
    if alt_path.exists():
        return alt_path.read_text(encoding="utf-8")
    
    raise FileNotFoundError(f"Prompt file not found: {prompt_name}.txt")


async def run_llm(
    task: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> str:
    """
    Universal LLM call function.
    
    Args:
        task: Task type (e.g., "thread_summaries", "draft_replies", "intent_classification")
        prompt: User prompt
        temperature: Temperature setting
        max_tokens: Max tokens to generate
        model: Override model (if None, uses task-based assignment)
        system_prompt: Optional system prompt override
        correlation_id: Optional correlation ID for logging
    
    Returns:
        LLM response text
    """
    start_time = time.time()
    
    # Determine model
    if model:
        selected_model = model
    else:
        selected_model = LLM_MODEL_ASSIGNMENTS.get(task, DEFAULT_LLM_MODEL)
    
    # Build messages
    messages: List[LLMMessage] = []
    if system_prompt:
        messages.append(LLMMessage("system", system_prompt))
    messages.append(LLMMessage("user", prompt))
    
    try:
        logger.info(
            f"LLM call: {task}",
            extra={
                "task": task,
                "model": selected_model,
                "correlation_id": correlation_id,
            }
        )
        
        response = await generate_chat_completion(
            LLMRequestOptions(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                correlation_id=correlation_id,
            )
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = getattr(response, 'usage', {}).get('total_tokens', 0) if hasattr(response, 'usage') else 0
        
        logger.info(
            f"LLM call completed: {task}",
            extra={
                "task": task,
                "model": selected_model,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "correlation_id": correlation_id,
            }
        )
        
        return response.content
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_type = type(e).__name__
        
        logger.error(
            f"LLM call failed: {task}",
            extra={
                "task": task,
                "model": selected_model,
                "error": str(e),
                "error_type": error_type,
                "latency_ms": latency_ms,
                "correlation_id": correlation_id,
            }
        )
        raise LLMError(
            message=f"LLM call failed for task {task}: {str(e)}",
            model=selected_model,
            details={
                "task": task,
                "latency_ms": latency_ms,
                "error_type": error_type,
                "failure_reason": str(e)
            }
        )


async def classify_intent(
    user_message: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Classify user intent using LLM with standardized prompt.
    
    Returns:
        {
            "intent": "general"|"rag"|"action_candidate",
            "confidence": float,
            "fallback_explanation": str
        }
    """
    try:
        from app.llm.prompt_builder import build_prompt
        
        # Build standardized prompt
        prompt = build_prompt(
            "intent_prompt",
            variables={"task": user_message}
        )
        
        response = await run_llm(
            task="intent_classification",
            prompt=user_message,
            system_prompt=prompt,
            temperature=0.0,
            max_tokens=200,  # Increased for JSON response
            correlation_id=correlation_id,
        )
        
        # Try to parse as JSON first
        try:
            # Remove markdown code blocks if present
            json_text = response.strip()
            json_text = re.sub(r"```json\s*", "", json_text)
            json_text = re.sub(r"```\s*", "", json_text)
            
            # Extract JSON object
            json_match = re.search(r"\{[\s\S]*\}", json_text)
            if json_match:
                result = json.loads(json_match.group(0))
                intent_label = result.get("intent", "general").lower()
                confidence = float(result.get("confidence", 0.7))
                fallback_explanation = result.get("fallback_explanation", "")
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError):
            # Fallback: parse as plain text
            intent_label = response.strip().lower()
            
            # Validate intent
            valid_intents = ["general", "rag", "action_candidate"]
            if intent_label not in valid_intents:
                # Try to extract from response
                for valid in valid_intents:
                    if valid in intent_label:
                        intent_label = valid
                        break
                else:
                    intent_label = "general"  # Default fallback
            
            # Calculate confidence (simplified)
            confidence = 0.9 if intent_label in response.lower() else 0.7
            fallback_explanation = f"Parsed from text response: {response[:100]}"
        
        # Validate intent
        valid_intents = ["general", "rag", "action_candidate"]
        if intent_label not in valid_intents:
            intent_label = "general"
            confidence = 0.5
            fallback_explanation = "Invalid intent label, defaulting to 'general'"
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))
        
        result = {
            "intent": intent_label,
            "confidence": confidence,
            "fallback_explanation": fallback_explanation,
        }
        
        logger.info(
            f"Intent classified: {intent_label}",
            extra={
                "intent": intent_label,
                "confidence": confidence,
                "fallback_explanation": fallback_explanation,
                "correlation_id": correlation_id,
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Intent classification failed: {e}", extra={"correlation_id": correlation_id})
        # Fallback to general
        return {
            "intent": "general",
            "confidence": 0.5,
            "fallback_explanation": f"Error during classification: {str(e)}. Defaulting to 'general'.",
        }

