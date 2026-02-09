"""
LLM-based Voice Command Router

Uses an LLM to intelligently route natural language commands to the appropriate
MCP tools, extracting arguments from context.

Supports multiple LLM providers:
- OpenAI (GPT-4o, GPT-4o-mini)
- Zhipu AI (GLM-4)

Much smarter than hardcoded phrase matching - understands intent and extracts
entities like names, dates, quantities, etc.
"""

import os
import json
from typing import Optional
from openai import AsyncOpenAI

# Initialize clients lazily
_client: Optional[AsyncOpenAI] = None


def _get_setting(key: str, default: str = "") -> str:
    """Get setting from environment or pydantic settings."""
    # First try environment variable
    val = os.getenv(key.upper())
    if val:
        return val

    # Then try pydantic settings
    try:
        from app.config import get_settings
        settings = get_settings()
        return getattr(settings, key.lower(), default)
    except Exception:
        return default


def get_llm_provider() -> str:
    """Determine which LLM provider to use based on available API keys."""
    if _get_setting("OPENROUTER_API_KEY"):
        return "openrouter"
    elif _get_setting("ZHIPU_API_KEY"):
        return "zhipu"
    elif _get_setting("OPENAI_API_KEY"):
        return "openai"
    return None


def get_client() -> tuple[AsyncOpenAI, str]:
    """
    Get the appropriate LLM client based on available API keys.
    Supports: OpenRouter, Zhipu/GLM, OpenAI
    Returns (client, model_name) tuple.
    """
    global _client

    openrouter_key = _get_setting("OPENROUTER_API_KEY")
    zhipu_key = _get_setting("ZHIPU_API_KEY")
    openai_key = _get_setting("OPENAI_API_KEY")

    # Priority 1: OpenRouter (access to many models including OpenAI)
    if openrouter_key:
        if _client is None:
            _client = AsyncOpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
        model = _get_setting("LLM_ROUTER_MODEL", "openai/gpt-4o-mini")
        return _client, model

    # Priority 2: Zhipu/GLM
    if zhipu_key:
        if _client is None:
            base_url = _get_setting("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
            _client = AsyncOpenAI(
                api_key=zhipu_key,
                base_url=base_url
            )
        model = _get_setting("LLM_ROUTER_MODEL", "glm-4")
        return _client, model

    # Priority 3: OpenAI direct
    if openai_key:
        if _client is None:
            _client = AsyncOpenAI(api_key=openai_key)
        model = _get_setting("LLM_ROUTER_MODEL", "gpt-4o-mini")
        return _client, model

    return None, None


# System prompt that defines the assistant's behavior
SYSTEM_PROMPT = """You are a voice assistant for an event ticketing system called "{org_name}".
Your job is to understand user requests and call the appropriate tool with the correct arguments.

IMPORTANT GUIDELINES:

1. EXTRACT INFORMATION from the user's request:
   - Names (customer names, event names)
   - Contact info (email, phone numbers)
   - Dates and times
   - Quantities and amounts
   - Event or ticket IDs when mentioned

2. HANDLE AMBIGUITY intelligently:
   - "tonight's event" or "the event" → don't include event_id, the system will use the current/next event
   - "check in John" → use name="John" for check_in_by_name
   - "refund their ticket" → if no identifier, the system will prompt for more info

3. CONTEXT AWARENESS:
   - If user says "the event" without specifying, omit event_id (system defaults to today's event)
   - Partial names are OK - the system does fuzzy matching
   - Phone numbers can be in any format - extract the digits

4. COMMON PATTERNS:
   - "how many..." → usually get_ticket_availability or guest_list
   - "send/text/email..." → notification tools
   - "check in..." → check_in_by_name (preferred) or check_in_ticket
   - "refund..." → refund_ticket
   - "who's coming" / "guest list" → guest_list
   - "revenue" / "sales" → get_revenue_report or get_event_sales

5. ALWAYS PREFER action over asking for clarification. Make reasonable assumptions.

Current context:
{context}
"""


async def route_voice_command(
    user_input: str,
    tools: list,
    context: dict = None,
    org_name: str = None,
) -> dict:
    """
    Use LLM to determine the best tool and extract arguments from natural language.

    Args:
        user_input: The user's natural language request
        tools: List of MCP Tool objects with name, description, inputSchema
        context: Optional context dict (last_event_id, last_customer_id, etc.)
        org_name: Organization name for personalization

    Returns:
        dict with:
            - tool: Tool name to call (or None if no tool needed)
            - arguments: Extracted arguments dict
            - message: Optional message if no tool called
    """
    client, model = get_client()

    if client is None:
        return {
            "tool": None,
            "arguments": {},
            "error": "No LLM API key configured (set ZHIPU_API_KEY or OPENAI_API_KEY)",
            "routed_by": "llm_error"
        }

    # Convert MCP tools to OpenAI function format
    functions = []
    for tool in tools:
        func = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get("inputSchema", {})
        }
        # Ensure parameters has required fields for OpenAI
        if "type" not in func["parameters"]:
            func["parameters"]["type"] = "object"
        if "properties" not in func["parameters"]:
            func["parameters"]["properties"] = {}
        functions.append(func)

    # Build context string
    context_str = ""
    if context:
        context_parts = []
        if context.get("last_event_id"):
            context_parts.append(f"Last referenced event ID: {context['last_event_id']}")
        if context.get("last_event_name"):
            context_parts.append(f"Last referenced event: {context['last_event_name']}")
        if context.get("last_customer_id"):
            context_parts.append(f"Last referenced customer ID: {context['last_customer_id']}")
        if context.get("current_event"):
            context_parts.append(f"Today's event: {context['current_event']}")
        context_str = "\n".join(context_parts) if context_parts else "No previous context."
    else:
        context_str = "No previous context."

    # Format system prompt
    system = SYSTEM_PROMPT.format(
        org_name=org_name or os.getenv("ORG_NAME", "Event Tickets"),
        context=context_str
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input}
    ]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[{"type": "function", "function": f} for f in functions],
            tool_choice="auto",
            temperature=0.1,  # Low temperature for consistent tool selection
        )

        message = response.choices[0].message

        # Check if LLM called a tool
        if message.tool_calls and len(message.tool_calls) > 0:
            tool_call = message.tool_calls[0]
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            return {
                "tool": tool_call.function.name,
                "arguments": arguments,
                "reasoning": message.content,  # Sometimes includes explanation
                "routed_by": "llm"
            }

        # No tool called - LLM wants to respond directly
        return {
            "tool": None,
            "arguments": {},
            "message": message.content or "I'm not sure how to help with that. Could you rephrase?",
            "routed_by": "llm"
        }

    except Exception as e:
        # If LLM fails, return error (caller can fall back to keyword matching)
        return {
            "tool": None,
            "arguments": {},
            "error": str(e),
            "routed_by": "llm_error"
        }


async def route_with_fallback(
    user_input: str,
    tools: list,
    keyword_map: dict,
    context: dict = None,
    org_name: str = None,
) -> dict:
    """
    Try LLM routing first, fall back to keyword matching if LLM fails or is unavailable.

    Args:
        user_input: The user's natural language request
        tools: List of MCP Tool objects
        keyword_map: Dict mapping keywords to tool names (fallback)
        context: Optional context dict
        org_name: Organization name

    Returns:
        dict with tool, arguments, and routing metadata
    """
    # Check if any LLM API key is configured
    if not _get_setting("OPENROUTER_API_KEY") and not _get_setting("OPENAI_API_KEY") and not _get_setting("ZHIPU_API_KEY"):
        # Fall back to keyword matching
        action = user_input.lower().strip()
        tool_name = keyword_map.get(action, action)
        return {
            "tool": tool_name,
            "arguments": {},
            "routed_by": "keyword_fallback",
            "reason": "No LLM API key configured (set ZHIPU_API_KEY or OPENAI_API_KEY)"
        }

    # Try LLM routing
    result = await route_voice_command(user_input, tools, context, org_name)

    # If LLM failed, fall back to keywords
    if result.get("error"):
        action = user_input.lower().strip()
        tool_name = keyword_map.get(action, action)
        return {
            "tool": tool_name,
            "arguments": {},
            "routed_by": "keyword_fallback",
            "reason": f"LLM error: {result['error']}"
        }

    return result
