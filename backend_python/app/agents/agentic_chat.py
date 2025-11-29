"""Agentic AI Chat Agent with LLM-Based Function Calling."""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from app.db.connection import get_pool
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
import httpx

# Agent state storage
agent_sessions: Dict[str, Dict[str, Any]] = {}


async def cleanup_inactive_sessions():
    """Clean up inactive sessions (older than 1 hour)."""
    now = datetime.now()
    one_hour = timedelta(hours=1)

    to_delete = []
    for session_id, state in agent_sessions.items():
        last_activity = state.get("context", {}).get("lastActivity")
        if last_activity and (now - last_activity) > one_hour:
            to_delete.append(session_id)

    for session_id in to_delete:
        del agent_sessions[session_id]
        print(f"[Agent] Cleared inactive session: {session_id}")


# Run cleanup every 5 minutes
async def start_cleanup_task():
    """Start background cleanup task."""
    while True:
        await asyncio.sleep(5 * 60)  # 5 minutes
        await cleanup_inactive_sessions()


# Cleanup task will be started in application lifespan
_cleanup_task = None


def get_cleanup_task():
    """Get the cleanup task instance."""
    return _cleanup_task


def set_cleanup_task(task):
    """Set the cleanup task instance."""
    global _cleanup_task
    _cleanup_task = task


async def create_calendar_event(text: str) -> Dict[str, Any]:
    """Create calendar event via API."""
    try:
        port = os.getenv("PORT", "3001")
        calendar_parse_url = f"http://localhost:{port}/api/calendar/parse"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                calendar_parse_url,
                json={"text": text},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("event"):
                    return {
                        "success": True,
                        "event": data["event"],
                        "message": f'Calendar event "{data["event"]["title"]}" created successfully.',
                    }
            return {"success": False, "message": "Failed to create calendar event."}
    except Exception as error:
        print(f"[Agent] Calendar event creation error: {error}")
        return {"success": False, "message": f"Error: {str(error)}"}


def get_policy_document() -> str:
    """Get policy document content."""
    possible_paths = [
        Path(__file__).parent.parent.parent / "policies" / "company-policy.md",
        Path(__file__).parent.parent.parent.parent / "backend" / "policies" / "company-policy.md",
        Path.cwd() / "backend" / "policies" / "company-policy.md",
        Path.cwd() / "policies" / "company-policy.md",
    ]

    for policy_path in possible_paths:
        if policy_path.exists():
            try:
                content = policy_path.read_text(encoding="utf-8")
                print(f"[Agent] Policy document loaded from: {policy_path}")
                return content
            except Exception as error:
                print(f"[Agent] Error reading policy: {error}")

    return ""


def get_policy_context() -> str:
    """Get policy rules context."""
    try:
        policy_path = Path(__file__).parent.parent.parent / "policy.json"
        if not policy_path.exists():
            policy_path = Path(__file__).parent.parent.parent.parent / "backend" / "policy.json"

        if policy_path.exists():
            with open(policy_path, "r", encoding="utf-8") as f:
                policy = json.load(f)
                return json.dumps(policy.get("rules", []), indent=2)
    except Exception as error:
        print(f"[Agent] Error loading policy: {error}")

    return "No policy rules available"


async def decide_function_call(question: str) -> Dict[str, Any]:
    """Use LLM to decide which function to call."""
    system_prompt = """You are a function dispatcher. Decide which function to call based on the user's question.

Available functions:
1. create_calendar_event - Call this if the user wants to schedule, book, plan, or add a meeting/event/appointment
2. get_policy_document - Call this if the user asks about policies, rules, guidelines, procedures, or what to do
3. answer_directly - Call this for general questions, greetings, or when no specific function is needed

Return JSON with:
{
  "function": "create_calendar_event" | "get_policy_document" | "answer_directly",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}"""

    try:
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                messages=[
                    LLMMessage("system", system_prompt),
                    LLMMessage("user", question),
                ],
                temperature=0.3,
                max_tokens=100,
                use_local=os.getenv("USE_OLLAMA") != "false",
            )
        )

        # Parse JSON response
        content = llm_response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        try:
            decision = json.loads(content)
            return decision
        except json.JSONDecodeError:
            # Fallback: simple keyword matching
            question_lower = question.lower()
            if any(
                word in question_lower
                for word in ["schedule", "book", "plan", "meeting", "appointment", "event", "calendar", "add"]
            ):
                return {"function": "create_calendar_event", "confidence": 0.8, "reasoning": "Calendar-related keywords"}
            elif any(
                word in question_lower
                for word in ["policy", "rule", "guideline", "procedure", "what should", "how should"]
            ):
                return {"function": "get_policy_document", "confidence": 0.8, "reasoning": "Policy-related keywords"}
            else:
                return {"function": "answer_directly", "confidence": 0.9, "reasoning": "General question"}
    except Exception as error:
        print(f"[Agent] Error deciding function: {error}")
        return {"function": "answer_directly", "confidence": 0.5, "reasoning": "Error in decision"}


async def run_agentic_chat(
    question: str, session_id: str, conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Run agentic chat with function calling."""
    # Initialize or get session state
    if session_id not in agent_sessions:
        agent_sessions[session_id] = {
            "messages": [],
            "sessionId": session_id,
            "context": {"lastActivity": datetime.now()},
            "tools": {},
        }

    state = agent_sessions[session_id]
    state["context"]["lastActivity"] = datetime.now()

    # Fetch inbox and task stats
    inbox_stats = ""
    tasks_stats = ""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            inbox_row = await conn.fetchrow(
                """
                SELECT COUNT(*) as total, 
                       COUNT(*) FILTER (WHERE processed = false) as unread,
                       COUNT(*) FILTER (WHERE EXISTS (
                         SELECT 1 FROM contacts c WHERE c.id = messages.contact_id AND c.tags::text LIKE '%lead%'
                       )) as leads
                FROM messages
                """
            )
            if inbox_row:
                inbox_stats = f"Inbox: {inbox_row['total']} total, {inbox_row['unread']} unread, {inbox_row['leads']} leads."

            tasks_row = await conn.fetchrow(
                """
                SELECT 
                  COUNT(*) FILTER (WHERE priority = 'P0') as p0,
                  COUNT(*) FILTER (WHERE priority = 'P1') as p1,
                  COUNT(*) FILTER (WHERE status = 'pending') as pending
                FROM tasks
                """
            )
            if tasks_row:
                tasks_stats = f"Tasks: {tasks_row['pending']} pending ({tasks_row['p0']} P0 urgent, {tasks_row['p1']} P1 high)."
    except Exception as error:
        print(f"[Agent] Error fetching context: {error}")

    # Check if simple greeting
    is_simple_greeting = question.strip().lower() in [
        "hi",
        "hello",
        "hey",
        "greetings",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    if is_simple_greeting:
        # Simple greeting response
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                messages=[
                    LLMMessage(
                        "system",
                        "You are a helpful assistant. Respond to greetings naturally and briefly. Keep it to 1-2 sentences maximum (under 50 words).",
                    ),
                    LLMMessage("user", question),
                ],
                temperature=0.5,
                max_tokens=50,
                use_local=os.getenv("USE_OLLAMA") != "false",
            )
        )
        return {
            "answer": llm_response.content.strip(),
            "sessionId": session_id,
        }

    # Decide which function to call
    function_decision = await decide_function_call(question)

    calendar_event = None

    # Execute function based on decision
    if function_decision["function"] == "create_calendar_event" and function_decision.get("confidence", 0) > 0.7:
        # Create calendar event
        calendar_result = await create_calendar_event(question)
        if calendar_result.get("success"):
            calendar_event = calendar_result["event"]
            state["tools"]["calendarEventCreated"] = calendar_event

    # Build system prompt
    policy_rules = ""
    policy_document = ""
    if function_decision["function"] == "get_policy_document":
        policy_rules = get_policy_context()
        policy_document = get_policy_document()

    # Build recent messages from conversation history
    recent_messages = []
    if conversation_history:
        recent_messages = [
            LLMMessage(msg["role"], msg["content"])
            for msg in conversation_history[-15:]
            if msg.get("role") in ["user", "assistant"]
        ]
    elif state["messages"]:
        recent_messages = [
            LLMMessage(msg["role"], msg["content"])
            for msg in state["messages"][-15:]
            if msg.get("role") in ["user", "assistant"]
        ]

    # Build system prompt
    system_prompt_parts = [
        "You are a helpful AI assistant for managing inbox, tasks, and calendar.",
        "You can help create calendar events, answer questions about policies, and provide insights about the inbox.",
    ]

    if inbox_stats or tasks_stats:
        system_prompt_parts.append(f"\nCurrent context:\n{inbox_stats}\n{tasks_stats}")

    if policy_rules and policy_document:
        system_prompt_parts.append(f"\nPolicy Rules:\n{policy_rules}")
        system_prompt_parts.append(f"\nPolicy Document:\n{policy_document[:2000]}")  # Limit length

    system_prompt_parts.append(
        "\nInstructions:\n- Use the context provided to answer questions accurately.\n- Be concise and direct. Maximum 250 words.\n- If you created a calendar event, mention it naturally in your response."
    )

    system_prompt = "\n".join(system_prompt_parts)

    # Truncate if too long
    if len(system_prompt) > 3000:
        system_prompt = system_prompt[:3000] + "\n[Context truncated...]"
        print("[Agent] Warning: System prompt truncated")

    # Generate response
    messages = [LLMMessage("system", system_prompt)]
    messages.extend(recent_messages)
    messages.append(LLMMessage("user", question))

    try:
        llm_response = await generate_chat_completion(
            LLMRequestOptions(
                model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "tinyllama",
                messages=messages,
                temperature=0.5,
                max_tokens=150,
                use_local=os.getenv("USE_OLLAMA") != "false",
            )
        )

        answer = llm_response.content.strip()

        # Add calendar event confirmation if created
        if calendar_event:
            answer += f'\n\n✅ Calendar event "{calendar_event.get("title")}" has been added to your calendar.'

        # Update session state
        state["messages"].append({"role": "user", "content": question, "timestamp": datetime.now()})
        state["messages"].append({"role": "assistant", "content": answer, "timestamp": datetime.now()})

        return {
            "answer": answer,
            "sessionId": session_id,
            "calendarEvent": calendar_event,
        }
    except Exception as error:
        print(f"[Agent] Error generating response: {error}")
        return {
            "answer": "I'm having trouble processing that request. Please try again.",
            "sessionId": session_id,
        }

