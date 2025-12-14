"""
LLM-based intent router - replaces regex-based classification.
"""
from typing import Dict, Any, Optional
from app.llm.provider import classify_intent
from app.core.config import INTENT_CONFIDENCE_THRESHOLD
from app.core.logger import logger


async def route_intent(
    user_message: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Route user message to appropriate intent using LLM.
    
    Returns:
        {
            "intent": "general" | "rag" | "action_candidate",
            "confidence": float,
            "should_use_rag": bool,
            "should_plan_action": bool,
        }
    """
    result = await classify_intent(user_message, correlation_id)
    
    intent = result["intent"]
    confidence = result["confidence"]
    
    # Determine routing decisions
    should_use_rag = intent == "rag"
    should_plan_action = intent == "action_candidate"
    
    # Apply confidence threshold
    if confidence < INTENT_CONFIDENCE_THRESHOLD:
        intent = "general"
        should_use_rag = False
        should_plan_action = False
    
    logger.info(
        f"Intent routed: {intent}",
        extra={
            "intent": intent,
            "confidence": confidence,
            "should_use_rag": should_use_rag,
            "should_plan_action": should_plan_action,
            "correlation_id": correlation_id,
        }
    )
    
    return {
        "intent": intent,
        "confidence": confidence,
        "should_use_rag": should_use_rag,
        "should_plan_action": should_plan_action,
    }

