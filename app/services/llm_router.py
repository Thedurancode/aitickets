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

6. CONVERSATION CONTEXT - Use previous context to resolve references:
   - "also his wife" → look up the wife of the previously mentioned customer
   - "the usual for Mike" → use the customer's typical purchase pattern
   - "them" / "they" → refers to recently mentioned customers

7. SMART CONTEXT AWARENESS:
   - Check "pending_operation" - if user said "2 tickets" before, now asking "for the Raptors game" completes the purchase
   - Check "time_context" - on event day, prioritize check-ins and immediate actions
   - Check "customer_memory" - VIP customers get priority, note accessibility needs
   - Check "prediction" - anticipate what user might want next
   - Check "disambiguation_needed" - if multiple customers match, ask for clarification
   - Check "likely_customer" - if one customer clearly matches, use them

8. VIP AND SPECIAL HANDLING:
   - If customer_memory.is_vip is true, mention VIP status in response
   - If customer_memory.accessibility_required, ensure appropriate accommodations
   - Use customer's preferred_section if available for seating

9. UNDO AND CORRECTION HANDLING:
   - If "undo_or_correction" context is present, handle it as priority
   - For UNDO requests:
     * Check if can_undo is true
     * If yes, use the undo_action and undo_params provided
     * If no, explain why (e.g., "Messages cannot be unsent")
   - For CORRECTIONS ("no, I meant Mike"):
     * Use correct_value as the new input
     * If last action can be undone, undo it first then redo with correct value
     * If not undoable, just perform the new action with correct value
   - Common phrases: "undo that", "cancel that", "never mind", "no, I meant X", "not John, Mike"

10. GROUP/BATCH CHECK-IN:
   - If "group_checkin" context is present, handle batch check-in
   - Check "to_check_in" count - this is how many need to be checked in
   - Use "ticket_ids" list to check in all at once
   - Report: "Checked in X of Y members: [names]"
   - If "already_checked_in" > 0, mention who's already checked in
   - Phrases: "the Smith party", "check in the Johnsons", "John and his wife", "check in everyone"

11. CONFIRMATION HANDLING:
   - If "confirmation" context is present, the user is responding to a pending question
   - Check "reply_type": "confirm", "reject", or "select"
   - For CONFIRM (reply_type=confirm):
     * If execute=true, call the action with the provided args
     * Report success: "Done! [action description]"
   - For REJECT (reply_type=reject):
     * If cancelled=true, acknowledge: "Cancelled. What would you like to do instead?"
   - For SELECT (reply_type=select):
     * If execute=true and selected is present, use the selected option
     * Report: "Selected [option]. Proceeding..."
   - If "orphan_reply" is true, user said yes/no but nothing is pending - ask what they meant
   - Confirmation phrases: "yes", "yeah", "correct", "no", "cancel", "the first one", "number 2"

Current context:
{context}

{entity_hints}

{smart_context}
"""


async def route_voice_command(
    user_input: str,
    tools: list,
    context: dict = None,
    org_name: str = None,
    conversation_history: list = None,
    entity_hints: dict = None,
) -> dict:
    """
    Use LLM to determine the best tool and extract arguments from natural language.

    Args:
        user_input: The user's natural language request
        tools: List of MCP Tool objects with name, description, inputSchema
        context: Optional context dict (last_event_id, last_customer_id, etc.)
        org_name: Organization name for personalization
        conversation_history: Optional list of previous conversation turns
        entity_hints: Optional dict with resolved entity hints (family members, usual patterns)

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

    # Build entity hints string
    entity_hints_str = ""
    if entity_hints:
        hint_parts = []
        if entity_hints.get("current_customer"):
            c = entity_hints["current_customer"]
            hint_parts.append(f"Current customer: {c['name']} (ID: {c['id']}, Email: {c.get('email', 'N/A')})")
        if entity_hints.get("resolved_family_member"):
            fm = entity_hints["resolved_family_member"]
            rel = entity_hints.get("family_relation", "family member")
            hint_parts.append(f"Resolved '{rel}': {fm['name']} (ID: {fm.get('id', 'N/A')})")
        if entity_hints.get("usual_pattern"):
            up = entity_hints["usual_pattern"]
            pattern_desc = []
            if up.get("tier"):
                pattern_desc.append(f"tier: {up['tier']}")
            if up.get("quantity"):
                pattern_desc.append(f"quantity: {up['quantity']}")
            if up.get("event_hint"):
                pattern_desc.append(f"usually for: {up['event_hint']} events")
            hint_parts.append(f"Customer's usual pattern: {', '.join(pattern_desc)}")
        if entity_hints.get("current_event"):
            e = entity_hints["current_event"]
            hint_parts.append(f"Current event: {e['name']} (ID: {e['id']})")
        if entity_hints.get("recent_customers"):
            names = [c["name"] for c in entity_hints["recent_customers"]]
            hint_parts.append(f"Recent customers: {', '.join(names)}")
        entity_hints_str = "\n".join(hint_parts) if hint_parts else ""

    # Build smart context string from enriched hints
    smart_context_str = ""
    if entity_hints:
        smart_parts = []

        # Group check-in context (highest priority for batch ops)
        if entity_hints.get("group_checkin"):
            gc = entity_hints["group_checkin"]
            if gc.get("members_found", 0) > 0:
                names = ", ".join(gc.get("member_names", []))
                smart_parts.append(f"👥 GROUP CHECK-IN: {gc['members_found']} members found")
                smart_parts.append(f"   Members: {names}")
                if gc.get("to_check_in", 0) > 0:
                    smart_parts.append(f"   To check in: {gc['to_check_in']} (ticket_ids: {gc.get('ticket_ids', [])})")
                if gc.get("already_checked_in", 0) > 0:
                    smart_parts.append(f"   Already checked in: {gc['already_checked_in']}")
            else:
                smart_parts.append(f"👥 GROUP CHECK-IN requested but no members found: {gc.get('error', 'Unknown error')}")

        # Undo/correction context
        if entity_hints.get("undo_or_correction"):
            uc = entity_hints["undo_or_correction"]
            if uc.get("intent") == "undo":
                if uc.get("can_undo"):
                    smart_parts.append(f"🔄 UNDO REQUESTED: Can undo '{uc.get('action')}' - use {uc.get('undo_action')}")
                    if uc.get("undo_params"):
                        smart_parts.append(f"   Undo params: {uc['undo_params']}")
                else:
                    smart_parts.append(f"⚠️ UNDO REQUESTED but NOT POSSIBLE: {uc.get('reason')}")
            elif uc.get("is_correction"):
                correction_info = f"✏️ CORRECTION DETECTED: User meant '{uc.get('correct_value', '?')}'"
                if uc.get("wrong_value"):
                    correction_info += f" (not '{uc['wrong_value']}')"
                smart_parts.append(correction_info)
                if uc.get("last_action", {}).get("can_undo"):
                    smart_parts.append(f"   Can undo last action ({uc['last_action']['tool']}) and redo correctly")

        # Last action reference
        if entity_hints.get("last_action") and not entity_hints.get("undo_or_correction"):
            la = entity_hints["last_action"]
            action_info = f"Last action: {la.get('tool')}"
            if la.get("customer_name"):
                action_info += f" for {la['customer_name']}"
            if la.get("reversible"):
                action_info += " (can undo)"
            smart_parts.append(action_info)

        # Pending operation
        if entity_hints.get("pending_operation"):
            po = entity_hints["pending_operation"]
            smart_parts.append(f"PENDING: {po['operation']} with args {po['partial_args']}")

        # Time context
        if entity_hints.get("time_context"):
            tc = entity_hints["time_context"]
            if tc.get("auto_detected_event"):
                smart_parts.append(f"AUTO-DETECTED TODAY'S EVENT: {tc.get('event_name')}")
            if tc.get("event_phase"):
                phase_info = f"EVENT PHASE: {tc['event_phase']}"
                if tc.get("phase_description"):
                    phase_info += f" - {tc['phase_description']}"
                smart_parts.append(phase_info)
            if tc.get("is_checkin_rush"):
                smart_parts.append(f"⚡ CHECK-IN RUSH: {tc.get('rush_hint', 'Prioritize speed')}")
            elif tc.get("checkin_mode"):
                smart_parts.append("CHECK-IN MODE: Doors are open, guests arriving")
            elif tc.get("event_in_progress"):
                smart_parts.append(f"EVENT IN PROGRESS: {tc.get('event_name', 'Current event')}")
            elif tc.get("post_event"):
                smart_parts.append("POST-EVENT: Handle surveys, feedback, refunds")
            if tc.get("behavior_hint"):
                smart_parts.append(f"MODE: {tc['behavior_hint']}")

        # Customer memory
        if entity_hints.get("customer_memory"):
            cm = entity_hints["customer_memory"]
            if cm.get("is_vip"):
                smart_parts.append(f"VIP CUSTOMER: {cm.get('vip_tier', 'VIP')} - {cm['name']}")
            if cm.get("accessibility_required"):
                smart_parts.append(f"ACCESSIBILITY: Customer requires accommodations")
            if cm.get("preferred_section"):
                smart_parts.append(f"Preferred section: {cm['preferred_section']}")

        # Disambiguation
        if entity_hints.get("disambiguation_needed"):
            customers = entity_hints.get("ambiguous_customers", [])
            options = [f"{c['name']} ({c.get('email', 'no email')})" for c in customers[:3]]
            smart_parts.append(f"AMBIGUOUS: Multiple matches - {', '.join(options)}")
        elif entity_hints.get("likely_customer"):
            lc = entity_hints["likely_customer"]
            if lc.get("has_ticket_today"):
                smart_parts.append(f"LIKELY MATCH: {lc['name']} has ticket for {lc.get('today_event')}")

        # Predictions
        if entity_hints.get("prediction"):
            pred = entity_hints["prediction"]
            smart_parts.append(f"PREDICTED NEXT: {', '.join(pred['likely_actions'][:2])}")

        # Suggestions
        if entity_hints.get("suggestions"):
            smart_parts.append(f"SUGGESTIONS: {'; '.join(entity_hints['suggestions'][:2])}")

        # Confirmation context
        if entity_hints.get("confirmation"):
            conf = entity_hints["confirmation"]
            if conf.get("has_pending"):
                pending = conf.get("pending", {})
                reply_type = conf.get("reply_type")

                if conf.get("execute"):
                    action = conf.get("action", "action")
                    context_info = conf.get("context", {})
                    smart_parts.append(f"✅ CONFIRMED: Execute {action}")
                    smart_parts.append(f"   Args: {conf.get('args', {})}")
                    if context_info:
                        smart_parts.append(f"   Context: {context_info}")
                elif conf.get("cancelled"):
                    smart_parts.append("❌ CANCELLED: User rejected the pending action")
                elif reply_type == "select" and conf.get("selected"):
                    smart_parts.append(f"🔢 SELECTED: Option {conf.get('selected_index', 0) + 1} - {conf.get('selected')}")
                elif reply_type == "other":
                    smart_parts.append(f"📝 PENDING ACTION exists but user said something else")
                    smart_parts.append(f"   Pending: {pending.get('question', pending.get('action'))}")
                    smart_parts.append(f"   User said: {conf.get('raw_input', '?')}")
                elif conf.get("error"):
                    smart_parts.append(f"⚠️ SELECTION ERROR: {conf.get('error')}")
            elif conf.get("orphan_reply"):
                reply_type = conf.get("reply_type")
                smart_parts.append(f"❓ ORPHAN {reply_type.upper()}: User said yes/no/selection but nothing pending")

        smart_context_str = "\n".join(smart_parts) if smart_parts else ""

    # Format system prompt
    system = SYSTEM_PROMPT.format(
        org_name=org_name or os.getenv("ORG_NAME", "Event Tickets"),
        context=context_str,
        entity_hints=entity_hints_str,
        smart_context=smart_context_str
    )

    # Build messages with conversation history
    messages = [{"role": "system", "content": system}]

    # Add conversation history if provided
    if conversation_history:
        for turn in conversation_history[-6:]:  # Last 6 turns max
            messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current user input
    messages.append({"role": "user", "content": user_input})

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
    conversation_history: list = None,
    entity_hints: dict = None,
) -> dict:
    """
    Try LLM routing first, fall back to keyword matching if LLM fails or is unavailable.

    Args:
        user_input: The user's natural language request
        tools: List of MCP Tool objects
        keyword_map: Dict mapping keywords to tool names (fallback)
        context: Optional context dict
        org_name: Organization name
        conversation_history: Optional list of previous conversation turns
        entity_hints: Optional dict with resolved entity hints

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

    # Try LLM routing with conversation history and entity hints
    result = await route_voice_command(
        user_input, tools, context, org_name,
        conversation_history=conversation_history,
        entity_hints=entity_hints
    )

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
