"""
LLM-based intent router with tie-breaker logic and confidence thresholding.
"""
from typing import Dict, Any, Optional
from app.llm.provider import classify_intent
from app.core.config import INTENT_CONFIDENCE_THRESHOLD
from app.core.logger import logger


def _tie_breaker_logic(
    intent: str,
    confidence: float,
    user_message: str,
) -> tuple[str, float, str]:
    """
    Apply tie-breaker logic for ambiguous intents.
    
    Returns:
        (final_intent, adjusted_confidence, explanation)
    """
    explanation = f"Classified as '{intent}' with confidence {confidence:.2f}"
    
    # If confidence is below threshold, apply fallback rules
    if confidence < INTENT_CONFIDENCE_THRESHOLD:
        # Check for explicit keywords that might indicate intent
        message_lower = user_message.lower()
        
        # RAG indicators
        rag_keywords = ["policy", "procedure", "document", "what is", "how does", "according to"]
        if any(keyword in message_lower for keyword in rag_keywords):
            explanation = f"Low confidence ({confidence:.2f}), but RAG keywords detected. Falling back to 'general' for safety."
            return "general", INTENT_CONFIDENCE_THRESHOLD, explanation
        
        # Action indicators
        action_keywords = ["schedule", "send", "create", "book", "set up", "remind"]
        if any(keyword in message_lower for keyword in action_keywords):
            explanation = f"Low confidence ({confidence:.2f}), but action keywords detected. Classifying as 'action_candidate'."
            return "action_candidate", max(confidence, INTENT_CONFIDENCE_THRESHOLD), explanation
        
        # Default fallback
        explanation = f"Confidence below threshold ({confidence:.2f} < {INTENT_CONFIDENCE_THRESHOLD}). Falling back to 'general' for safety."
        return "general", INTENT_CONFIDENCE_THRESHOLD, explanation
    
    return intent, confidence, explanation


async def route_intent(
    user_message: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Route user message to appropriate intent using LLM with tie-breaker logic.
    
    Returns:
        {
            "intent": "general" | "rag" | "action_candidate",
            "confidence": float,
            "should_use_rag": bool,
            "should_plan_action": bool,
            "fallback_explanation": str,
        }
    """
    try:
        result = await classify_intent(user_message, correlation_id)
        
        intent = result.get("intent", "general")
        confidence = result.get("confidence", 0.5)
        fallback_explanation = result.get("fallback_explanation", "")
        
        # Apply tie-breaker logic
        final_intent, adjusted_confidence, explanation = _tie_breaker_logic(
            intent, confidence, user_message
        )
        
        # Use provided explanation or generated one
        if not fallback_explanation:
            fallback_explanation = explanation
        
        # Determine routing decisions
        should_use_rag = final_intent == "rag"
        should_plan_action = final_intent == "action_candidate"
        
        # Final confidence check - never route below threshold without explanation
        if adjusted_confidence < INTENT_CONFIDENCE_THRESHOLD and not fallback_explanation:
            fallback_explanation = f"Confidence {adjusted_confidence:.2f} below threshold {INTENT_CONFIDENCE_THRESHOLD}"
            final_intent = "general"
            should_use_rag = False
            should_plan_action = False
        
        logger.info(
            f"Intent routed: {final_intent}",
            extra={
                "intent": final_intent,
                "confidence": adjusted_confidence,
                "original_confidence": confidence,
                "should_use_rag": should_use_rag,
                "should_plan_action": should_plan_action,
                "fallback_explanation": fallback_explanation,
                "correlation_id": correlation_id,
            }
        )
        
        return {
            "intent": final_intent,
            "confidence": adjusted_confidence,
            "should_use_rag": should_use_rag,
            "should_plan_action": should_plan_action,
            "fallback_explanation": fallback_explanation,
        }
        
    except Exception as e:
        logger.error(
            f"Intent routing failed: {e}",
            extra={"correlation_id": correlation_id, "error": str(e)}
        )
        # Safe fallback
        return {
            "intent": "general",
            "confidence": 0.5,
            "should_use_rag": False,
            "should_plan_action": False,
            "fallback_explanation": f"Error during intent classification: {str(e)}. Defaulting to 'general'.",
        }

