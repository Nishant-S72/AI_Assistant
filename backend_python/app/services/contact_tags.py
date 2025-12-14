"""Service for AI-generated contact tags based on chat history."""
from typing import List, Dict, Any
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import os
import json


async def generate_contact_tags(
    contact_name: str,
    contact_email: str,
    contact_company: str = None,
    message_history: List[Dict[str, Any]] = None
) -> List[str]:
    """
    Generate tags for a contact based on their message history using AI.
    
    Args:
        contact_name: Name of the contact
        contact_email: Email of the contact
        contact_company: Company name (optional)
        message_history: List of messages with 'sender', 'body', 'created_at' keys
    
    Returns:
        List of tag strings (e.g., ['lead', 'enterprise', 'urgent', 'technical'])
    """
    if not message_history or len(message_history) == 0:
        # No history - return default tag
        return ["new-lead"]
    
    # Build conversation history
    conversation_text = "\n".join([
        f"[{msg.get('sender', 'unknown')}] {msg.get('body', '')}"
        for msg in message_history[-20:]  # Last 20 messages for context
    ])
    
    # Define the 6 super important tag categories
    ALLOWED_TAGS = [
        "new-lead",                    # New potential customers
        "long-standing",               # Established, loyal customers
        "urgent-action-required",      # Requires immediate attention
        "potential-interest",          # Showing interest but not committed
        "escalation",                  # Issues requiring escalation
        "high-priority"                # High-priority customers/accounts
    ]
    
    # Build prompt for tag generation
    company_context = f" from {contact_company}" if contact_company else ""
    
    # Determine if this is a new lead or long-standing customer based on message count and history
    message_count = len(message_history)
    days_since_first = 0
    if message_history:
        from datetime import datetime
        try:
            first_msg_date = datetime.fromisoformat(message_history[0].get('created_at', '').replace('Z', '+00:00'))
            last_msg_date = datetime.fromisoformat(message_history[-1].get('created_at', '').replace('Z', '+00:00'))
            days_since_first = (last_msg_date - first_msg_date).days
        except:
            pass
    
    system_prompt = f"""You are an AI assistant analyzing customer communication history to categorize contacts. 

Your task is to assign ONE tag from these 6 categories based on the conversation history:

CATEGORY CRITERIA:

1. "new-lead" 
   - Criteria: 0-5 total messages, recent contact (within last 7 days), asking initial questions, minimal interaction history
   - Indicators: First-time contact, basic inquiries, "I'm interested in...", "Can you tell me about...", "What do you offer?", "I just discovered..."

2. "long-standing"
   - Criteria: 10+ messages over 30+ days, repeat interactions, established relationship, loyal customer
   - Indicators: Multiple conversations over time, references to past orders, "We've been working together...", "As usual...", "Like last time...", "We've been customers for..."

3. "urgent-action-required"
   - Criteria: Time-sensitive issues, critical problems, deadlines, requires immediate attention
   - Indicators: Keywords like "urgent", "asap", "emergency", "immediately", "deadline", "critical", "time-sensitive", time pressure mentioned, "need this resolved now"

4. "potential-interest"
   - Criteria: Showing interest but not committed, exploring options, no purchase yet
   - Indicators: Asking about products/services, requesting demos, comparing options, "I'm considering...", "Can you send me information?", "How does this compare to...?", "I'm researching...", "I'm looking at..."

5. "escalation"
   - Criteria: Issues requiring escalation, dissatisfaction, complaints, refund requests, legal concerns
   - Indicators: "Speak to manager", "cancel", "refund", "dissatisfied", "unacceptable", "complaint", "legal matter", "filing a complaint", threats, "worst service", "very unhappy"

6. "high-priority"
   - Criteria: Large orders, premium services, significant revenue, key accounts, strategic partners, executive contacts
   - Indicators: Large dollar amounts mentioned ($1M+, "million", "significant revenue"), executive titles (VP, CEO, Director, C-level), "strategic partner", "key account", "enterprise", premium service requests, "Fortune 500", "dedicated account manager"

ANALYSIS CONTEXT:
- Message count: {message_count}
- Days since first contact: {days_since_first}
- Company: {contact_company or 'Not specified'}

INSTRUCTIONS:
1. Analyze the conversation history carefully
2. Match the conversation patterns to the criteria above
3. Select the MOST APPROPRIATE single tag based on the strongest indicators
4. If multiple criteria apply, choose the one with the strongest evidence
5. Return ONLY a JSON array with ONE tag string. Example: ["new-lead"] or ["urgent-action-required"]

Return ONLY a JSON array with ONE tag string from the list above."""

    user_prompt = f"""Analyze the conversation history with {contact_name}{company_context} ({contact_email}):

{conversation_text}

Based on the conversation history, message count ({message_count}), and relationship duration ({days_since_first} days), assign the MOST APPROPRIATE single tag from the 6 categories. Return as a JSON array with one tag string."""

    try:
        # Explicitly use OPENAI_MODEL, fallback to LLM_MODEL, then default
        openai_model = os.getenv("OPENAI_MODEL")
        if not openai_model:
            openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            print(f"[Tags] ⚠️ OPENAI_MODEL not set, using LLM_MODEL: {openai_model}")
        else:
            print(f"[Tags] ✅ Using OPENAI_MODEL: {openai_model}")
        
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=openai_model,
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", user_prompt),
                ],
                temperature=0.3,  # Lower temperature for more consistent tag generation
                max_tokens=100,  # Tags are short, so we don't need many tokens
                use_local=False,  # Ensure we use OpenAI, not Ollama
            )
        )
        
        # Parse the response - should be a JSON array
        response_text = llm_response.content.strip()
        
        # Try to extract JSON array from response (handle cases where LLM adds explanation)
        import re
        json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        tags = json.loads(response_text)
        
        # Validate tags are strings and clean them
        if isinstance(tags, list):
            tags = [
                str(tag).lower().strip().replace(" ", "-")
                for tag in tags
                if tag and isinstance(tag, (str, int))  # Allow strings and numbers
            ]
            # Remove duplicates and empty strings
            tags = list(dict.fromkeys([t for t in tags if t]))
            # Filter to only allowed tags
            allowed_tags = [
                "new-lead",
                "long-standing",
                "urgent-action-required",
                "potential-interest",
                "escalation",
                "high-priority"
            ]
            tags = [t for t in tags if t in allowed_tags]
            
            # If no valid tags, determine default based on message history
            if not tags:
                message_count = len(message_history) if message_history else 0
                if message_count == 0:
                    return ["new-lead"]
                elif message_count > 10:
                    # Check if long-standing (more than 30 days of history)
                    days_since_first = 0
                    if message_history:
                        from datetime import datetime
                        try:
                            first_msg_date = datetime.fromisoformat(message_history[0].get('created_at', '').replace('Z', '+00:00'))
                            last_msg_date = datetime.fromisoformat(message_history[-1].get('created_at', '').replace('Z', '+00:00'))
                            days_since_first = (last_msg_date - first_msg_date).days
                        except:
                            pass
                    
                    if days_since_first > 30:
                        return ["long-standing"]
                    else:
                        return ["new-lead"]
                else:
                    return ["new-lead"]
            
            # Return first valid tag (should only be one)
            return tags[:1]
        else:
            # If response is not a list, return default based on message count
            message_count = len(message_history) if message_history else 0
            if message_count == 0:
                return ["new-lead"]
            else:
                return ["long-standing"]
            
    except json.JSONDecodeError as e:
        print(f"[Tags] Failed to parse LLM response as JSON: {e}")
        print(f"[Tags] Response was: {llm_response.content if 'llm_response' in locals() else 'N/A'}")
        # Fallback to default tag based on message count
        message_count = len(message_history) if message_history else 0
        if message_count == 0:
            return ["new-lead"]
        else:
            return ["long-standing"]
    except Exception as e:
        print(f"[Tags] Error generating tags: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to default tag based on message count
        message_count = len(message_history) if message_history else 0
        if message_count == 0:
            return ["new-lead"]
        else:
            return ["long-standing"]


async def update_contact_tags(
    contact_id: str,
    pool=None
) -> List[str]:
    """
    Update tags for a contact based on their message history.
    
    Args:
        contact_id: ID of the contact to update
        pool: Database connection pool (optional, will create if not provided)
    
    Returns:
        List of generated tags
    """
    from app.db.connection import get_pool
    
    if pool is None:
        pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Get contact info
        contact_row = await conn.fetchrow(
            "SELECT name, email, company FROM contacts WHERE id = $1",
            contact_id
        )
        
        if not contact_row:
            return []
        
        contact_name = contact_row.get("name", "Unknown")
        contact_email = contact_row.get("email", "")
        contact_company = contact_row.get("company")
        
        # Get message history
        messages = await conn.fetch(
            """
            SELECT sender, body, created_at
            FROM messages
            WHERE contact_id = $1
            ORDER BY created_at ASC
            """,
            contact_id
        )
        
        message_history = [dict(msg) for msg in messages]
        
        # Get current tags to check if they need updating
        current_tags_row = await conn.fetchrow(
            "SELECT tags FROM contacts WHERE id = $1",
            contact_id
        )
        current_tags = []
        if current_tags_row:
            current_tags_raw = current_tags_row.get("tags")
            if isinstance(current_tags_raw, str):
                try:
                    current_tags = json.loads(current_tags_raw)
                except:
                    current_tags = []
            elif isinstance(current_tags_raw, list):
                current_tags = current_tags_raw
        
        # Map old tags to new categories if needed
        old_to_new_mapping = {
            "lead": "new-lead",
            "new-leads": "new-lead",
            "customer": "long-standing",
            "long-standing-customers": "long-standing",
            "long-standing-customer": "long-standing",
            "enterprise": "high-priority",
            "high-value": "high-priority",
            "high value": "high-priority",
            "vip": "high-priority",
            "urgent": "urgent-action-required",
            "urgent-action": "urgent-action-required",
            "complaint": "escalation",
            "new": "new-lead",
        }
        
        # Check if current tags are already in the new format
        allowed_tags = ["new-lead", "long-standing", "urgent-action-required", "potential-interest", "escalation", "high-priority"]
        needs_update = False
        
        # If current tags are not in allowed list, regenerate
        if not current_tags or not any(tag in allowed_tags for tag in current_tags):
            needs_update = True
        else:
            # Check if we have old tags that need mapping
            for tag in current_tags:
                if tag not in allowed_tags and tag in old_to_new_mapping:
                    needs_update = True
                    break
        
        if needs_update:
            # Generate new tags
            tags = await generate_contact_tags(
                contact_name=contact_name,
                contact_email=contact_email,
                contact_company=contact_company,
                message_history=message_history
            )
            
            # Update contact with new tags
            tags_json = json.dumps(tags)
            await conn.execute(
                "UPDATE contacts SET tags = $1 WHERE id = $2",
                tags_json,
                contact_id
            )
            
            # Invalidate cache when tags are updated
            from app.services.cache_manager import invalidate_cache
            try:
                invalidate_cache(
                    reason="tag_updated",
                    contact_id=contact_id
                )
            except Exception as cache_error:
                print(f"[Tags] Failed to invalidate cache: {cache_error}")
            
            print(f"[Tags] Updated tags for {contact_name}: {tags}")
            return tags
        else:
            # Tags are already in the correct format
            valid_tags = [t for t in current_tags if t in allowed_tags]
            if valid_tags:
                print(f"[Tags] Tags already up-to-date for {contact_name}: {valid_tags}")
                return valid_tags
            else:
                # Fallback: generate new tags
                tags = await generate_contact_tags(
                    contact_name=contact_name,
                    contact_email=contact_email,
                    contact_company=contact_company,
                    message_history=message_history
                )
                tags_json = json.dumps(tags)
                await conn.execute(
                    "UPDATE contacts SET tags = $1 WHERE id = $2",
                    tags_json,
                    contact_id
                )
                
                # Invalidate cache when tags are updated
                from app.services.cache_manager import invalidate_cache
                try:
                    invalidate_cache(
                        reason="tag_updated",
                        contact_id=contact_id
                    )
                except Exception as cache_error:
                    print(f"[Tags] Failed to invalidate cache: {cache_error}")
                
                print(f"[Tags] Regenerated tags for {contact_name}: {tags}")
                return tags

