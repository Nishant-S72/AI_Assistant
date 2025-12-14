"""
Chat API - refactored to use new architecture.
"""
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from app.agent.intent_router import route_intent
from app.agent.action_planner import plan_action
from app.agent.executor import execute_action
from app.rag.retriever import retrieve_chunks, format_rag_response
from app.llm.provider import run_llm, load_prompt
from app.middleware.tier_gating import get_user_tier
from app.core.config import UserTier
from app.core.errors import TierRestrictionError
from app.core.logger import logger
import uuid


router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request."""
    userMessage: str
    threadId: Optional[str] = None
    tone: Optional[Literal["formal", "warm", "crisp"]] = "warm"
    conversationHistory: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Chat response."""
    kind: Literal["assistant", "suggestion", "action_planned", "action_executed"]
    text: str
    intent: str
    intent_confidence: float
    action_plan: Optional[Dict[str, Any]] = None
    action_execution: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    tier: str
    suggestionId: Optional[str] = None


async def get_current_user(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """Get current user ID from header."""
    if x_user_id:
        return x_user_id
    # Default for development
    return "00000000-0000-0000-0000-000000000000"


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Main chat endpoint with intent routing, RAG, and action planning.
    
    Flow:
    1. Route intent (general/rag/action_candidate)
    2. If RAG: retrieve chunks and synthesize answer
    3. If action_candidate: plan action
    4. If Pro tier and action planned: execute action
    5. Return response with tier-appropriate content
    """
    # Get correlation ID from request state (set by middleware)
    correlation_id = getattr(http_request.state, "correlation_id", None) or str(uuid.uuid4())
    suggestion_id = str(uuid.uuid4())
    
    try:
        # Get user tier
        tier = await get_user_tier(user_id)
        
        logger.info(
            "Chat request received",
            extra={
                "user_id": user_id,
                "tier": tier.value,
                "thread_id": request.threadId,
                "correlation_id": correlation_id,
            }
        )
        
        # Step 1: Route intent
        intent_result = await route_intent(request.userMessage, correlation_id)
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        should_use_rag = intent_result["should_use_rag"]
        should_plan_action = intent_result["should_plan_action"]
        
        response_text = ""
        citations = None
        action_plan = None
        action_execution = None
        
        # Step 2: Handle based on intent
        if should_use_rag:
            # RAG flow
            chunks = await retrieve_chunks(request.userMessage, correlation_id=correlation_id)
            if chunks:
                response_text = await format_rag_response(
                    chunks=chunks,
                    query=request.userMessage,
                    tone=request.tone,
                    correlation_id=correlation_id,
                )
                citations = [
                    {
                        "source": chunk.get("source"),
                        "filename": chunk.get("filename"),
                        "fragment_index": chunk.get("fragment_index"),
                        "score": chunk.get("score"),
                        "snippet": chunk.get("snippet"),
                    }
                    for chunk in chunks
                ]
            else:
                # Fallback if no chunks found
                response_text = "I don't have information about that in the available documents. Would you like me to help with something else?"
        
        elif should_plan_action:
            # Action planning flow
            action_plan = await plan_action(
                user_message=request.userMessage,
                conversation_history=request.conversationHistory,
                correlation_id=correlation_id,
            )
            
            # Check for missing fields
            if action_plan.get("missing_fields"):
                response_text = f"I can help you {action_plan['action_type']}, but I need more information: {', '.join(action_plan['missing_fields'])}"
            else:
                # Action is fully planned
                if tier == UserTier.PRO:
                    # Pro: Execute immediately
                    action_execution = await execute_action(
                        action_type=action_plan["action_type"],
                        parameters=action_plan["parameters"],
                        user_id=user_id,
                        correlation_id=correlation_id,
                    )
                    
                    if action_execution.get("executed"):
                        response_text = f"It's done. {action_plan['action_type']} completed successfully."
                    else:
                        response_text = f"I tried to {action_plan['action_type']}, but encountered an error: {action_execution.get('error', 'Unknown error')}"
                else:
                    # Assist: Suggest only
                    response_text = f"Here's what I suggest: {action_plan['action_type']} with parameters {action_plan['parameters']}. Would you like me to proceed? (Pro tier required for execution)"
        
        else:
            # General conversational flow
            reply_prompt = load_prompt("reply_prompt")
            response_text = await run_llm(
                task="draft_replies",
                prompt=request.userMessage,
                system_prompt=f"{reply_prompt}\n\nTone: {request.tone}",
                temperature=0.7,
                max_tokens=500,
                correlation_id=correlation_id,
            )
        
        # Determine response kind
        if action_execution and action_execution.get("executed"):
            kind = "action_executed"
        elif action_plan:
            kind = "action_planned"
        elif should_use_rag:
            kind = "assistant"
        else:
            kind = "suggestion"
        
        return ChatResponse(
            kind=kind,
            text=response_text,
            intent=intent,
            intent_confidence=confidence,
            action_plan=action_plan,
            action_execution=action_execution,
            citations=citations,
            tier=tier.value,
            suggestionId=suggestion_id,
        )
        
    except TierRestrictionError as e:
        logger.warning(
            "Tier restriction in chat",
            extra={
                "user_id": user_id,
                "error": str(e),
                "correlation_id": correlation_id,
            }
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TIER_RESTRICTION",
                "message": str(e),
                "current_tier": e.details.get("current_tier"),
                "required_tier": e.details.get("required_tier"),
            }
        )
    
    except Exception as e:
        logger.error(
            "Chat request failed",
            extra={
                "user_id": user_id,
                "error": str(e),
                "correlation_id": correlation_id,
            }
        )
        raise HTTPException(status_code=500, detail=f"Chat request failed: {str(e)}")


@router.post("/execute")
async def execute_planned_action(
    action_plan: Dict[str, Any],
    http_request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Execute a planned action (Pro tier only).
    
    Used when Assist tier user approves a suggested action.
    """
    # Get correlation ID from request state (set by middleware)
    correlation_id = getattr(http_request.state, "correlation_id", None) or str(uuid.uuid4())
    
    try:
        tier = await get_user_tier(user_id)
        
        if tier != UserTier.PRO:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "TIER_RESTRICTION",
                    "message": "Action execution requires Pro tier",
                    "current_tier": tier.value,
                    "required_tier": "pro",
                }
            )
        
        action_type = action_plan.get("action_type")
        parameters = action_plan.get("parameters", {})
        
        result = await execute_action(
            action_type=action_type,
            parameters=parameters,
            user_id=user_id,
            correlation_id=correlation_id,
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Action execution failed: {e}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")

