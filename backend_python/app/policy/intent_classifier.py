"""Hybrid intent classifier: rules + LLM fallback for ambiguous cases."""
import os
import re
from typing import Literal, Dict, Any, List
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions

IntentType = Literal["policy_intent", "action_intent", "general_intent"]

# Confidence threshold for manual labeling
INTENT_RULES_CONFIDENCE_THRESHOLD = float(os.getenv("INTENT_RULES_CONFIDENCE_THRESHOLD", "0.75"))


def classify_intent(user_message: str) -> Dict[str, Any]:
    """
    Classify user message intent using hybrid approach:
    1. Deterministic rules (keywords, patterns)
    2. LLM fallback for ambiguous cases
    
    Returns: {intent, confidence, reasons, method}
    """
    if not user_message:
        return {
            "intent": "general_intent",
            "confidence": 0.5,
            "reasons": ["Empty message"],
            "method": "rules"
        }
    
    lower_message = user_message.lower().strip()
    
    # Step 1: Check for simple greetings -> general_intent
    greeting_pattern = re.compile(
        r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening|howdy|sup|what\'?s up|how are you|how\'?s it going)$',
        re.IGNORECASE
    )
    if greeting_pattern.match(lower_message):
        return {
            "intent": "general_intent",
            "confidence": 0.95,
            "reasons": ["Simple greeting detected"],
            "method": "rules"
        }
    
    # Step 2: Check for action intent (scheduling, calendar, etc.)
    action_candidate = False
    action_reasons = []
    
    # Action keywords (comprehensive list)
    action_keywords = [
        'schedule', 'scheduling', 'scheduled', 'book', 'booking', 'booked',
        'plan', 'planning', 'arrange', 'arranging', 'set up', 'setup',
        'create event', 'add event', 'calendar', 'meeting', 'appointment',
        'call', 'conference', 'reminder', 'invite', 'invitation',
        'reserve', 'reservation', 'block time', 'time slot'
    ]
    
    action_matches = [kw for kw in action_keywords if kw in lower_message]
    if action_matches:
        action_candidate = True
        action_reasons.append(f"Action keywords: {', '.join(action_matches[:3])}")
    
    # Time patterns
    time_patterns = [
        r'\b(tomorrow|today|next week|next month|next year)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b\d{1,2}(:\d{2})?\s?(am|pm|AM|PM)\b',
        r'\b(at|on|by)\s+\d{1,2}',
        r'\b\d{1,2}(st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b',
    ]
    
    time_matches = []
    for pattern in time_patterns:
        if re.search(pattern, lower_message, re.IGNORECASE):
            time_matches.append(pattern)
    
    if time_matches:
        action_candidate = True
        action_reasons.append("Time reference detected")
    
    # Timezone patterns
    timezone_patterns = [
        r'\b(dubai|gst|utc|pst|est|cst|mst|gmt|ist|jst|sgt|hkt)\b',
        r'\+\d{2}:\d{2}',
        r'[A-Z]{3,4}\s+time',
    ]
    
    if any(re.search(p, lower_message, re.IGNORECASE) for p in timezone_patterns):
        action_candidate = True
        action_reasons.append("Timezone reference detected")
    
    # Email pattern (attendees)
    email_pattern = r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
    if re.search(email_pattern, user_message, re.IGNORECASE):
        action_candidate = True
        action_reasons.append("Email address detected (likely attendee)")
    
    # Duration patterns
    duration_patterns = [
        r'\d+\s*(minute|min|hour|hr|day|week|month)\b',
        r'\d+\s*(minute|min|hour|hr)s?\s+(call|meeting|appointment)',
    ]
    
    if any(re.search(p, lower_message, re.IGNORECASE) for p in duration_patterns):
        action_candidate = True
        action_reasons.append("Duration specified")
    
    # Strong action intent if multiple signals
    if action_candidate and (len(action_matches) > 0 or len(time_matches) > 0):
        confidence = 0.9 if (len(action_matches) > 1 or len(time_matches) > 0) else 0.85
        return {
            "intent": "action_intent",
            "confidence": confidence,
            "reasons": action_reasons,
            "method": "rules"
        }
    
    # Step 3: Check for policy intent
    policy_keywords = [
        'policy', 'policies', 'policy doc', 'policy document', 'guideline', 'guidelines',
        'rule', 'rules', 'procedure', 'procedures', 'compliance', 'compliant',
        'section', 'sections', 'clause', 'clauses', 'allowed', 'not allowed',
        'prohibited', 'permitted', 'eligibility', 'eligible', 'requirement', 'requirements',
        'what does the', 'what is our', 'what are our', 'does our', 'can we', 'are we allowed',
        'refund policy', 'return policy', 'privacy policy', 'terms of service',
        'according to', 'per policy', 'policy states', 'policy says',
    ]
    
    policy_matches = [kw for kw in policy_keywords if kw in lower_message]
    if policy_matches:
        confidence = 0.9 if len(policy_matches) > 1 else 0.85
        return {
            "intent": "policy_intent",
            "confidence": confidence,
            "reasons": [f"Policy keywords: {', '.join(policy_matches[:3])}"],
            "method": "rules"
        }
    
    # Step 4: If ambiguous, use LLM fallback
    # Only call LLM if we're uncertain (no strong rule matches)
    if not action_candidate and not policy_matches:
        return _classify_with_llm(user_message)
    
    # Default to general_intent with moderate confidence
    return {
        "intent": "general_intent",
        "confidence": 0.7,
        "reasons": ["No specific intent keywords detected"],
        "method": "rules"
    }


async def _classify_with_llm(user_message: str) -> Dict[str, Any]:
    """
    Use LLM to classify ambiguous intent.
    Returns intent with confidence score from LLM.
    """
    try:
        classification_prompt = f"""Classify this user message into one of three intents:
- policy_intent: User asks about company policies, rules, procedures, compliance
- action_intent: User requests an action (schedule meeting, create task, send email)
- general_intent: General questions, explanations, casual conversation

User message: "{user_message}"

Respond with ONLY a JSON object in this exact format:
{{
  "intent": "policy_intent|action_intent|general_intent",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}

No other text, just the JSON."""

        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("LLM_MODEL", "tinyllama"),
                messages=[
                    LLMMessage("system", "You are an intent classification assistant. Return only valid JSON."),
                    LLMMessage("user", classification_prompt),
                ],
                max_tokens=100,
                temperature=0.1,  # Low temperature for deterministic classification
                use_local=os.getenv("USE_OLLAMA") != "false",
                correlation_id=f"intent_classify_{os.urandom(4).hex()}",
            )
        )
        
        # Parse JSON response
        import json
        response_text = llm_response.content.strip()
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            intent = result.get("intent", "general_intent")
            confidence = float(result.get("confidence", 0.7))
            reason = result.get("reason", "LLM classification")
            
            # Validate intent
            if intent not in ["policy_intent", "action_intent", "general_intent"]:
                intent = "general_intent"
            
            return {
                "intent": intent,
                "confidence": min(max(confidence, 0.0), 1.0),  # Clamp to [0, 1]
                "reasons": [reason],
                "method": "llm"
            }
        else:
            # Fallback if JSON parsing fails
            return {
                "intent": "general_intent",
                "confidence": 0.6,
                "reasons": ["LLM response parsing failed"],
                "method": "llm_fallback"
            }
    
    except Exception as e:
        print(f"[IntentClassifier] LLM classification error: {e}")
        return {
            "intent": "general_intent",
            "confidence": 0.6,
            "reasons": [f"LLM classification failed: {str(e)}"],
            "method": "llm_error"
        }


# For backward compatibility, provide sync wrapper that calls async
def classify_intent_sync(user_message: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for classify_intent.
    Note: This will not use LLM fallback (only rules).
    For full functionality, use classify_intent_async.
    """
    # Run rules-based classification only
    if not user_message:
        return {"intent": "general_intent", "confidence": 0.5, "reasons": [], "method": "rules"}
    
    lower_message = user_message.lower().strip()
    
    # Check action keywords
    action_keywords = ['schedule', 'meeting', 'calendar', 'book', 'appointment']
    if any(kw in lower_message for kw in action_keywords):
        return {"intent": "action_intent", "confidence": 0.85, "reasons": ["Action keywords"], "method": "rules"}
    
    # Check policy keywords
    policy_keywords = ['policy', 'rule', 'procedure', 'guideline']
    if any(kw in lower_message for kw in policy_keywords):
        return {"intent": "policy_intent", "confidence": 0.85, "reasons": ["Policy keywords"], "method": "rules"}
    
    return {"intent": "general_intent", "confidence": 0.7, "reasons": [], "method": "rules"}


# Async version for use in routes
async def classify_intent_async(user_message: str) -> Dict[str, Any]:
    """Async version that supports LLM fallback."""
    # First try rules
    result = classify_intent(user_message)
    
    # If confidence is low and method is rules, try LLM
    if result.get("method") == "rules" and result.get("confidence", 1.0) < INTENT_RULES_CONFIDENCE_THRESHOLD:
        llm_result = await _classify_with_llm(user_message)
        # Use LLM result if it has higher confidence
        if llm_result.get("confidence", 0.0) > result.get("confidence", 0.0):
            return llm_result
    
    return result
