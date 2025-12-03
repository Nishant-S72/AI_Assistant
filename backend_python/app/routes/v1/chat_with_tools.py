"""Chat endpoint with function calling support."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from app.clients.llm import generate_chat_completion, LLMMessage, LLMRequestOptions
from app.tools.registry import get_registry
import os
import json

router = APIRouter()


class ChatWithToolsRequest(BaseModel):
    """Request model for chat with tools."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    conversation_id: Optional[str] = None


@router.post("/chat_with_tools")
async def chat_with_tools(request: ChatWithToolsRequest):
    """
    Chat endpoint that supports LLM function calling.
    
    If model response contains function_call, dispatches to handler
    and continues conversation with function result.
    """
    try:
        registry = get_registry()
        model = request.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Convert messages to LLMMessage format
        llm_messages = [
            LLMMessage(msg["role"], msg["content"])
            for msg in request.messages
        ]
        
        # Add tools to request
        tools = registry.get_tools()
        
        # Call LLM with tools
        # TODO: Modify generate_chat_completion to support tools parameter
        # For now, we'll use OpenAI directly with tools
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = await client.chat.completions.create(
            model=model,
            messages=[msg.to_dict() for msg in llm_messages],
            tools=tools if tools else None,
            tool_choice="auto",
        )
        
        message = response.choices[0].message
        assistant_message = {"role": "assistant", "content": message.content}
        
        # Check for function call
        if message.tool_calls:
            # Process function calls
            tool_results = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                try:
                    result = await registry.call(function_name, function_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result),
                    })
                except Exception as e:
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": str(e)}),
                    })
            
            # Add function results to conversation
            request.messages.append(assistant_message)
            request.messages.extend(tool_results)
            
            # Continue conversation with function results
            # TODO: Make recursive call or loop until no more function calls
            # For now, return the function results
            return {
                "response": assistant_message,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in message.tool_calls
                ],
                "tool_results": tool_results,
            }
        
        return {
            "response": assistant_message,
            "tool_calls": None,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

