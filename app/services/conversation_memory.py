"""
Conversation Memory Service

Manages voice conversation sessions for multi-turn context:
- Session lifecycle (create, get, cleanup)
- Conversation history tracking
- Entity extraction from tool results
- Reference resolution (pronouns, "the usual", etc.)
- Intent prediction and proactive suggestions
- Cross-session customer memory
- Pending operation tracking (multi-turn flows)
"""

import json
import logging
import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import ConversationSession, EventGoer, Ticket, Event, TicketTier, CustomerNote

logger = logging.getLogger(__name__)

# Constants
MAX_TURNS = 10
SESSION_TTL_MINUTES = 30

# Intent patterns for prediction
INTENT_PATTERNS = {
    "check_in": ["check in", "checking in", "arrived", "here for"],
    "purchase": ["buy", "purchase", "get tickets", "want tickets", "need tickets"],
    "refund": ["refund", "cancel", "money back"],
    "info": ["how many", "availability", "sold", "left", "who's coming", "guest list"],
    "notification": ["send", "text", "email", "remind", "notify"],
}

# Follow-up predictions based on last action
FOLLOW_UP_PREDICTIONS = {
    "check_in_by_name": ["check in companion", "check in family member", "lookup other tickets"],
    "purchase_ticket": ["add more tickets", "check availability", "apply promo code"],
    "guest_list": ["check in someone", "send notification"],
    "list_events": ["get ticket availability", "check event details"],
    "refund_ticket": ["issue another refund", "check customer tickets"],
}

# Undo/correction detection patterns
UNDO_PATTERNS = [
    r"\bundo\b", r"\bundo that\b", r"\bcancel that\b", r"\brevert\b",
    r"\broll\s*back\b", r"\btake\s*(that\s*)?back\b", r"\bnever\s*mind\b",
]

CORRECTION_PATTERNS = [
    r"\bno\s*,?\s*i\s*meant\b",
    r"\bsorry\s*,?\s*i\s*meant\b",
    r"\bactually\s*,?\s*i\s*meant\b",
    r"\bwait\s*,?\s*not\b",
    r"\bnot\s+\w+\s*,\s*\w+",  # "not John, Mike"
    r"\bi\s*said\s+\w+\s*,?\s*not\b",  # "I said Mike, not"
    r"\bwrong\s+(person|customer|name|event)\b",
    r"\bthat'?s?\s*not\s*(right|correct|who)\b",
    r"\bi\s*meant\s+\w+",  # "I meant Mike"
]

# Confirmation/quick reply patterns
CONFIRMATION_PATTERNS = [
    r"^yes$", r"^yep$", r"^yeah$", r"^yup$", r"^correct$", r"^right$",
    r"^that'?s?\s*(?:right|correct|it)$", r"^do\s*it$", r"^go\s*ahead$",
    r"^confirm$", r"^approved$", r"^affirmative$", r"^sure$", r"^ok(?:ay)?$",
]

REJECTION_PATTERNS = [
    r"^no$", r"^nope$", r"^nah$", r"^cancel$", r"^stop$", r"^wait$",
    r"^don'?t$", r"^never\s*mind$", r"^abort$", r"^wrong$",
]

SELECTION_PATTERNS = [
    r"(?:the\s+)?first(?:\s+one)?", r"(?:the\s+)?second(?:\s+one)?",
    r"(?:the\s+)?third(?:\s+one)?", r"(?:the\s+)?fourth(?:\s+one)?",
    r"(?:the\s+)?last(?:\s+one)?", r"number\s+(\d+)", r"option\s+(\d+)",
    r"(?:the\s+)?(\d+)(?:st|nd|rd|th)(?:\s+one)?",
    r"^(\d+)$",  # Just a number
    r"that\s+one", r"this\s+one",
]

# Group check-in detection patterns
GROUP_PATTERNS = [
    r"\b(?:check\s*in\s+)?the\s+(\w+)\s+(?:party|group|family)\b",  # "the Smith party"
    r"\bcheck\s*in\s+(?:the\s+)?(\w+)s\b",  # "check in the Smiths"
    r"\b(\w+)\s+and\s+(?:his|her|their)\s+(?:wife|husband|partner|family|group)\b",  # "John and his wife"
    r"\bcheck\s*in\s+(?:the\s+)?(?:whole|entire)\s+(?:party|group)\b",  # "check in the whole party"
    r"\bcheck\s*in\s+everyone\b",  # "check in everyone" (uses current context)
    r"\bcheck\s*in\s+all\s+of\s+them\b",  # "check in all of them"
    r"\b(\w+)\s+(?:and|with)\s+(\w+)\b",  # "John and Sarah"
]

# Actions that can be undone and how
REVERSIBLE_ACTIONS = {
    "check_in_by_name": {
        "reversible": True,
        "undo_action": "undo_check_in",
        "description": "Uncheck the customer (set back to not checked in)",
    },
    "check_in_ticket": {
        "reversible": True,
        "undo_action": "undo_check_in",
        "description": "Uncheck the ticket",
    },
    "purchase_ticket": {
        "reversible": True,
        "undo_action": "cancel_ticket",
        "description": "Cancel the pending ticket (if not yet paid)",
        "condition": "status == PENDING",
    },
    "refund_ticket": {
        "reversible": False,
        "description": "Refunds cannot be undone",
    },
    "send_ticket_sms": {
        "reversible": False,
        "description": "Messages cannot be unsent",
    },
    "send_event_reminder": {
        "reversible": False,
        "description": "Reminders cannot be unsent",
    },
}


def get_or_create_session(db: Session, session_id: Optional[str] = None) -> tuple[ConversationSession, bool]:
    """
    Get an existing session or create a new one.

    Args:
        db: Database session
        session_id: Optional session ID. If None, creates a new session.

    Returns:
        Tuple of (session, is_new)
    """
    now = datetime.now(timezone.utc)

    if session_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.session_id == session_id,
            ConversationSession.expires_at > now
        ).first()

        if session:
            # Update last activity
            session.last_activity = now
            session.expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)
            db.commit()
            return session, False

    # Create new session
    new_session = ConversationSession(
        session_id=str(uuid.uuid4()),
        conversation_history=json.dumps([]),
        entity_context=json.dumps({"customers": [], "events": []}),
        expires_at=now + timedelta(minutes=SESSION_TTL_MINUTES)
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    logger.info(f"Created new conversation session: {new_session.session_id}")
    return new_session, True


def add_turn(
    db: Session,
    session: ConversationSession,
    role: str,
    content: str,
    tool_calls: Optional[list] = None
) -> None:
    """
    Add a conversation turn to the session history.
    Trims to MAX_TURNS if exceeded.

    Args:
        db: Database session
        session: The conversation session
        role: "user" or "assistant"
        content: The message content
        tool_calls: Optional list of tool calls made
    """
    history = json.loads(session.conversation_history or "[]")

    turn = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if tool_calls:
        turn["tool_calls"] = tool_calls

    history.append(turn)

    # Trim to MAX_TURNS
    if len(history) > MAX_TURNS:
        history = history[-MAX_TURNS:]

    session.conversation_history = json.dumps(history)
    session.last_activity = datetime.now(timezone.utc)
    db.commit()


def get_history_for_llm(session: ConversationSession) -> list[dict]:
    """
    Get conversation history formatted for LLM context.

    Args:
        session: The conversation session

    Returns:
        List of message dicts with role and content
    """
    history = json.loads(session.conversation_history or "[]")

    # Format for LLM
    messages = []
    for turn in history:
        msg = {"role": turn["role"], "content": turn["content"]}
        messages.append(msg)

    return messages


def extract_entities_from_result(tool_name: str, result: dict) -> dict:
    """
    Extract entities (customers, events) from tool execution results.

    Args:
        tool_name: Name of the tool that was executed
        result: The tool's result dict

    Returns:
        Dict with extracted entities: {"customers": [...], "events": [...]}
    """
    entities = {"customers": [], "events": []}

    if "error" in result:
        return entities

    # Check-in results
    if tool_name in ("check_in_by_name", "check_in_ticket"):
        if result.get("customer_name"):
            entities["customers"].append({
                "id": result.get("customer_id"),
                "name": result.get("customer_name"),
                "relation": "checked_in"
            })
        if result.get("event_id"):
            entities["events"].append({
                "id": result.get("event_id"),
                "name": result.get("event_name", ""),
                "relation": "current"
            })

    # Guest list results
    elif tool_name == "guest_list":
        if result.get("event_id"):
            entities["events"].append({
                "id": result.get("event_id"),
                "name": result.get("event_name", ""),
                "relation": "current"
            })
        # Extract attendees
        for attendee in result.get("attendees", [])[:5]:  # Limit to first 5
            if attendee.get("customer_id"):
                entities["customers"].append({
                    "id": attendee.get("customer_id"),
                    "name": attendee.get("name", ""),
                    "relation": "attendee"
                })

    # Ticket lookup results
    elif tool_name == "lookup_ticket":
        if result.get("customer_id"):
            entities["customers"].append({
                "id": result.get("customer_id"),
                "name": result.get("customer_name", ""),
                "relation": "ticket_holder"
            })
        if result.get("event_id"):
            entities["events"].append({
                "id": result.get("event_id"),
                "name": result.get("event_name", ""),
                "relation": "ticket_event"
            })

    # Purchase ticket results
    elif tool_name == "purchase_ticket":
        if result.get("customer_id"):
            entities["customers"].append({
                "id": result.get("customer_id"),
                "name": result.get("customer_name", ""),
                "relation": "purchaser"
            })
        if result.get("event_id"):
            entities["events"].append({
                "id": result.get("event_id"),
                "name": result.get("event_name", ""),
                "relation": "purchased"
            })

    # List events results
    elif tool_name == "list_events":
        for event in result.get("events", [])[:3]:  # Limit to first 3
            entities["events"].append({
                "id": event.get("id"),
                "name": event.get("name", ""),
                "relation": "listed"
            })

    return entities


def update_entity_context(
    db: Session,
    session: ConversationSession,
    entities: dict
) -> None:
    """
    Update session's entity context with newly extracted entities.

    Args:
        db: Database session
        session: The conversation session
        entities: Dict with "customers" and "events" lists
    """
    existing = json.loads(session.entity_context or '{"customers": [], "events": []}')

    # Merge customers (avoid duplicates)
    existing_customer_ids = {c["id"] for c in existing["customers"] if c.get("id")}
    for customer in entities.get("customers", []):
        if customer.get("id") and customer["id"] not in existing_customer_ids:
            existing["customers"].append(customer)
            existing_customer_ids.add(customer["id"])

    # Merge events (avoid duplicates)
    existing_event_ids = {e["id"] for e in existing["events"] if e.get("id")}
    for event in entities.get("events", []):
        if event.get("id") and event["id"] not in existing_event_ids:
            existing["events"].append(event)
            existing_event_ids.add(event["id"])

    # Keep only last 10 of each
    existing["customers"] = existing["customers"][-10:]
    existing["events"] = existing["events"][-10:]

    # Update current focus
    if entities.get("customers"):
        latest_customer = entities["customers"][-1]
        if latest_customer.get("id"):
            session.current_customer_id = latest_customer["id"]

    if entities.get("events"):
        latest_event = entities["events"][-1]
        if latest_event.get("id"):
            session.current_event_id = latest_event["id"]

    session.entity_context = json.dumps(existing)
    db.commit()


def resolve_references(user_input: str, session: ConversationSession, db: Session) -> dict:
    """
    Resolve pronouns and references in user input based on session context.

    Args:
        user_input: The user's input text
        session: The conversation session
        db: Database session

    Returns:
        Dict with entity hints for the LLM
    """
    hints = {}
    entity_context = json.loads(session.entity_context or '{"customers": [], "events": []}')
    input_lower = user_input.lower()

    # Pronoun patterns that suggest referring to a person
    pronoun_patterns = [
        r"\b(his|her|their|them|he|she|they)\b",
        r"\balso\s+(his|her|their)\b",
        r"\b(wife|husband|spouse|partner)\b",
        r"\b(son|daughter|child|kid)\b",
        r"\b(brother|sister|sibling)\b",
        r"\b(mother|father|mom|dad|parent)\b",
    ]

    has_pronoun_reference = any(re.search(p, input_lower) for p in pronoun_patterns)

    # If we have pronouns and a current customer, provide context
    if has_pronoun_reference and session.current_customer_id:
        current_customer = db.query(EventGoer).filter(
            EventGoer.id == session.current_customer_id
        ).first()

        if current_customer:
            hints["current_customer"] = {
                "id": current_customer.id,
                "name": current_customer.name,
                "email": current_customer.email
            }

            # Check for family relationship words
            family_patterns = {
                "wife": "wife",
                "husband": "husband",
                "spouse": "spouse",
                "partner": "partner",
                "son": "son",
                "daughter": "daughter",
                "child": "child",
                "kid": "child",
                "brother": "brother",
                "sister": "sister",
                "mom": "mother",
                "mother": "mother",
                "dad": "father",
                "father": "father"
            }

            for word, relation in family_patterns.items():
                if word in input_lower:
                    # Try to find family member
                    from app.services.family_resolver import find_family_member
                    family_member = find_family_member(
                        db, session.current_customer_id, relation
                    )
                    if family_member:
                        hints["resolved_family_member"] = family_member
                        hints["family_relation"] = relation
                    break

    # Check for "the usual" pattern
    if "the usual" in input_lower or "usual tickets" in input_lower or "usual order" in input_lower:
        # Find customer reference in input or use current
        customer_id = session.current_customer_id

        # Try to extract customer from input
        # Look for email pattern
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_input)
        if email_match:
            email = email_match.group()
            customer = db.query(EventGoer).filter(EventGoer.email == email).first()
            if customer:
                customer_id = customer.id

        if customer_id:
            usual_pattern = detect_usual_pattern(db, customer_id)
            if usual_pattern:
                hints["usual_pattern"] = usual_pattern

    # Add current event context
    if session.current_event_id:
        current_event = db.query(Event).filter(
            Event.id == session.current_event_id
        ).first()
        if current_event:
            hints["current_event"] = {
                "id": current_event.id,
                "name": current_event.name
            }

    # Add recent entities for context
    if entity_context.get("customers"):
        hints["recent_customers"] = entity_context["customers"][-3:]
    if entity_context.get("events"):
        hints["recent_events"] = entity_context["events"][-3:]

    # Enrich with smart context
    hints = enrich_entity_hints(db, session, hints, user_input)

    return hints


def detect_usual_pattern(db: Session, customer_id: int) -> Optional[dict]:
    """
    Detect a customer's usual purchase pattern from their history.

    Args:
        db: Database session
        customer_id: The customer's ID

    Returns:
        Dict with pattern info or None if no clear pattern
    """
    from sqlalchemy import func
    from app.models import TicketStatus

    # Get last 10 purchases
    tickets = db.query(Ticket).join(TicketTier).join(Event).filter(
        Ticket.event_goer_id == customer_id,
        Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
    ).order_by(Ticket.purchased_at.desc()).limit(10).all()

    if len(tickets) < 2:
        return None

    # Analyze patterns
    tier_counts = {}
    event_name_parts = {}
    quantities_per_event = {}

    for ticket in tickets:
        tier_name = ticket.ticket_tier.name
        tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1

        event_name = ticket.ticket_tier.event.name
        # Extract keywords from event name
        for word in event_name.split():
            if len(word) > 3:  # Skip short words
                event_name_parts[word.lower()] = event_name_parts.get(word.lower(), 0) + 1

        # Track quantities per event
        event_id = ticket.ticket_tier.event_id
        if event_id not in quantities_per_event:
            quantities_per_event[event_id] = 0
        quantities_per_event[event_id] += 1

    # Find dominant tier
    if tier_counts:
        dominant_tier = max(tier_counts.items(), key=lambda x: x[1])
        if dominant_tier[1] >= len(tickets) * 0.5:  # At least 50% consistency
            pattern_tier = dominant_tier[0]
        else:
            pattern_tier = None
    else:
        pattern_tier = None

    # Find average quantity per event
    if quantities_per_event:
        avg_quantity = sum(quantities_per_event.values()) / len(quantities_per_event)
        typical_quantity = round(avg_quantity)
    else:
        typical_quantity = 1

    # Find common event type keywords
    event_hint = None
    if event_name_parts:
        common_parts = sorted(event_name_parts.items(), key=lambda x: -x[1])
        if common_parts and common_parts[0][1] >= 2:
            event_hint = common_parts[0][0]

    # Build pattern
    pattern = {
        "tier": pattern_tier,
        "quantity": typical_quantity,
        "event_hint": event_hint,
        "sample_size": len(tickets)
    }

    return pattern


def cleanup_expired_sessions(db: Session) -> int:
    """
    Delete expired conversation sessions.

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    now = datetime.now(timezone.utc)

    deleted = db.query(ConversationSession).filter(
        ConversationSession.expires_at < now
    ).delete()

    db.commit()

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} expired conversation sessions")

    return deleted


# ============== Smart Enhancements ==============

def detect_intent(user_input: str) -> Optional[str]:
    """
    Detect the user's intent from their input.

    Returns:
        Intent category or None
    """
    input_lower = user_input.lower()

    for intent, patterns in INTENT_PATTERNS.items():
        if any(p in input_lower for p in patterns):
            return intent

    return None


def get_pending_operation(session: ConversationSession) -> Optional[dict]:
    """
    Check if there's a pending multi-turn operation.

    For example: "2 tickets" without specifying event.

    Returns:
        Dict with pending operation details or None
    """
    entity_context = json.loads(session.entity_context or '{}')
    return entity_context.get("pending_operation")


def set_pending_operation(
    db: Session,
    session: ConversationSession,
    operation: str,
    partial_args: dict
) -> None:
    """
    Set a pending operation that needs more info.

    Args:
        db: Database session
        session: The conversation session
        operation: The operation type (e.g., "purchase_ticket")
        partial_args: Arguments collected so far
    """
    entity_context = json.loads(session.entity_context or '{}')
    entity_context["pending_operation"] = {
        "operation": operation,
        "partial_args": partial_args,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    session.entity_context = json.dumps(entity_context)
    db.commit()


def clear_pending_operation(db: Session, session: ConversationSession) -> None:
    """Clear any pending operation."""
    entity_context = json.loads(session.entity_context or '{}')
    if "pending_operation" in entity_context:
        del entity_context["pending_operation"]
        session.entity_context = json.dumps(entity_context)
        db.commit()


def get_customer_memory(db: Session, customer_id: int) -> dict:
    """
    Get cross-session memory for a customer.

    Aggregates preferences, past interactions, and VIP status.

    Returns:
        Dict with customer memory
    """
    from app.models import CustomerPreference, TicketStatus

    customer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()
    if not customer:
        return {}

    memory = {
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
    }

    # Get preferences
    pref = db.query(CustomerPreference).filter(
        CustomerPreference.event_goer_id == customer_id
    ).first()

    if pref:
        memory["is_vip"] = pref.is_vip
        memory["vip_tier"] = pref.vip_tier
        memory["total_events_attended"] = pref.total_events_attended
        memory["preferred_section"] = pref.preferred_section
        memory["accessibility_required"] = pref.accessibility_required
        if pref.favorite_teams:
            try:
                memory["favorite_teams"] = json.loads(pref.favorite_teams)
            except:
                pass

    # Get recent notes
    notes = db.query(CustomerNote).filter(
        CustomerNote.event_goer_id == customer_id
    ).order_by(CustomerNote.created_at.desc()).limit(5).all()

    if notes:
        memory["recent_notes"] = [
            {"type": n.note_type, "note": n.note[:100]}
            for n in notes
        ]

    # Get purchase stats
    ticket_count = db.query(func.count(Ticket.id)).filter(
        Ticket.event_goer_id == customer_id,
        Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
    ).scalar()
    memory["total_tickets"] = ticket_count or 0

    return memory


def get_time_context(db: Session, event_id: Optional[int] = None) -> dict:
    """
    Get time-aware context for smarter conversation handling.

    Provides:
    - Current time/date info
    - Event day detection
    - Doors open / check-in rush detection
    - Event phase (pre-doors, check-in rush, in-progress, post-event)
    - Auto-detects today's event if none specified

    Returns:
        Dict with comprehensive time context
    """
    from app.models import EventStatus

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    current_hour = now.hour
    current_minute = now.minute

    context = {
        "current_time": now.strftime("%H:%M"),
        "current_date": today,
        "day_of_week": now.strftime("%A"),
        "is_weekend": now.weekday() >= 5,
        "is_business_hours": 9 <= current_hour <= 21,
        "is_evening": current_hour >= 17,
        "is_morning": current_hour < 12,
    }

    # If no event_id, try to find today's event
    event = None
    if event_id:
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        # Auto-detect: find the next upcoming event for today
        event = db.query(Event).filter(
            Event.event_date == today,
            Event.status == EventStatus.SCHEDULED
        ).order_by(Event.event_time).first()

        if event:
            context["auto_detected_event"] = True

    if event:
        context["event_id"] = event.id
        context["event_name"] = event.name
        context["event_date"] = event.event_date
        context["event_time"] = event.event_time
        context["doors_open_time"] = event.doors_open_time

        try:
            event_hour = int(event.event_time.split(":")[0])
            event_minute = int(event.event_time.split(":")[1]) if ":" in event.event_time else 0

            # Parse doors open time
            doors_hour = None
            if event.doors_open_time:
                doors_hour = int(event.doors_open_time.split(":")[0])
                doors_minute = int(event.doors_open_time.split(":")[1]) if ":" in event.doors_open_time else 0
            else:
                # Default: doors open 1 hour before event
                doors_hour = event_hour - 1
                doors_minute = event_minute

            if event.event_date == today:
                context["is_event_day"] = True

                # Calculate minutes until various milestones
                current_minutes = current_hour * 60 + current_minute
                event_minutes = event_hour * 60 + event_minute
                doors_minutes = doors_hour * 60 + (doors_minute if event.doors_open_time else event_minute)

                minutes_until_event = event_minutes - current_minutes
                minutes_until_doors = doors_minutes - current_minutes

                context["minutes_until_event"] = minutes_until_event
                context["hours_until_event"] = minutes_until_event // 60

                # Determine event phase
                if minutes_until_doors > 60:
                    context["event_phase"] = "pre_event"
                    context["phase_description"] = "Event is later today"
                elif minutes_until_doors > 0:
                    context["event_phase"] = "approaching"
                    context["phase_description"] = f"Doors open in {minutes_until_doors} minutes"
                    context["prepare_for_checkins"] = True
                elif minutes_until_event > 0:
                    context["event_phase"] = "doors_open"
                    context["phase_description"] = "Doors are open - check-in active"
                    context["is_checkin_rush"] = minutes_until_event <= 30
                    context["checkin_mode"] = True
                elif minutes_until_event > -180:  # Within 3 hours of start
                    context["event_phase"] = "in_progress"
                    context["phase_description"] = "Event is in progress"
                    context["event_in_progress"] = True
                else:
                    context["event_phase"] = "post_event"
                    context["phase_description"] = "Event has ended"
                    context["post_event"] = True

                # Check-in rush detection (30 min before to 15 min after start)
                if -15 <= minutes_until_event <= 30:
                    context["is_checkin_rush"] = True
                    context["rush_hint"] = "High check-in volume expected - prioritize speed"

            else:
                context["is_event_day"] = False
                try:
                    event_dt = datetime.strptime(event.event_date, "%Y-%m-%d")
                    days_until = (event_dt.date() - now.date()).days
                    context["days_until_event"] = days_until

                    if days_until == 1:
                        context["is_tomorrow"] = True
                        context["phase_description"] = "Event is tomorrow"
                    elif days_until <= 7:
                        context["is_this_week"] = True
                        context["phase_description"] = f"Event in {days_until} days"
                    elif days_until < 0:
                        context["is_past_event"] = True
                        context["phase_description"] = "Event has passed"
                except:
                    pass

        except (ValueError, AttributeError):
            pass

    # Time-based behavior hints
    if context.get("is_checkin_rush"):
        context["behavior_hint"] = "Speed mode: minimize confirmations, rapid check-ins"
    elif context.get("event_in_progress"):
        context["behavior_hint"] = "Support mode: handle issues, late arrivals"
    elif context.get("post_event"):
        context["behavior_hint"] = "Wrap-up mode: surveys, feedback, refund requests"
    elif context.get("is_evening") and not context.get("is_event_day"):
        context["behavior_hint"] = "Planning mode: ticket sales, event inquiries"

    return context


def disambiguate_customer(
    db: Session,
    name: str,
    session: ConversationSession
) -> list[dict]:
    """
    Find customers matching a partial name with disambiguation info.

    Returns:
        List of matching customers with context
    """
    from app.models import TicketStatus

    # Find matching customers
    customers = db.query(EventGoer).filter(
        EventGoer.name.ilike(f"%{name}%")
    ).limit(5).all()

    if not customers:
        return []

    # Get entity context for recency hints
    entity_context = json.loads(session.entity_context or '{}')
    recent_customer_ids = {c["id"] for c in entity_context.get("customers", [])}

    results = []
    for customer in customers:
        info = {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "recently_mentioned": customer.id in recent_customer_ids,
        }

        # Get their ticket for today's event (if any)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_ticket = db.query(Ticket).join(TicketTier).join(Event).filter(
            Ticket.event_goer_id == customer.id,
            Event.event_date == today,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
        ).first()

        if today_ticket:
            info["has_ticket_today"] = True
            info["today_event"] = today_ticket.ticket_tier.event.name
            info["checked_in"] = today_ticket.status == TicketStatus.CHECKED_IN

        results.append(info)

    # Sort: recently mentioned first, then has ticket today
    results.sort(key=lambda x: (
        -x.get("recently_mentioned", False),
        -x.get("has_ticket_today", False)
    ))

    return results


def predict_next_action(session: ConversationSession) -> Optional[dict]:
    """
    Predict what the user might want to do next.

    Returns:
        Dict with prediction and confidence
    """
    history = json.loads(session.conversation_history or "[]")

    if not history:
        return None

    # Find last tool call
    last_tool = None
    for turn in reversed(history):
        if turn.get("tool_calls"):
            last_tool = turn["tool_calls"][-1].get("tool")
            break

    if not last_tool:
        return None

    predictions = FOLLOW_UP_PREDICTIONS.get(last_tool, [])
    if not predictions:
        return None

    return {
        "likely_actions": predictions,
        "based_on": last_tool,
        "confidence": "medium"
    }


def get_smart_suggestions(
    db: Session,
    session: ConversationSession,
    user_input: str
) -> list[str]:
    """
    Generate smart suggestions based on context.

    Returns:
        List of suggested actions
    """
    suggestions = []
    entity_context = json.loads(session.entity_context or '{}')

    # Check for pending operation
    pending = get_pending_operation(session)
    if pending:
        op = pending["operation"]
        if op == "purchase_ticket" and not pending["partial_args"].get("event_id"):
            suggestions.append("Specify which event for the tickets")
        elif op == "check_in_by_name" and not pending["partial_args"].get("name"):
            suggestions.append("Provide the customer's name")

    # Time-based suggestions
    time_ctx = get_time_context(db, session.current_event_id)
    if time_ctx.get("is_event_day"):
        if time_ctx.get("hours_until_event", 0) <= 2:
            suggestions.append("Check-ins will be common - ready for rapid check-in mode")
        if time_ctx.get("event_in_progress"):
            suggestions.append("Event is underway - focus on attendee support")

    # Customer-based suggestions
    if session.current_customer_id:
        memory = get_customer_memory(db, session.current_customer_id)
        if memory.get("is_vip"):
            suggestions.append(f"VIP customer ({memory.get('vip_tier', 'VIP')})")
        if memory.get("accessibility_required"):
            suggestions.append("Customer has accessibility requirements")

    # Prediction-based
    prediction = predict_next_action(session)
    if prediction:
        suggestions.extend([f"You might want to: {a}" for a in prediction["likely_actions"][:2]])

    return suggestions[:4]  # Limit to top 4


def enrich_entity_hints(
    db: Session,
    session: ConversationSession,
    hints: dict,
    user_input: str
) -> dict:
    """
    Enrich entity hints with smart context.

    Adds:
    - Undo/correction context
    - Pending operations
    - Time context
    - Customer memory
    - Disambiguation help
    - Predictions
    """
    # Check for group check-in (highest priority for batch operations)
    group_ctx = get_group_checkin_context(db, session, user_input)
    if group_ctx:
        hints["group_checkin"] = group_ctx

    # Check for undo/correction intent
    undo_correction = get_undo_or_correction_context(db, session, user_input)
    if undo_correction:
        hints["undo_or_correction"] = undo_correction

    # Add last action context (even if not undoing, useful for reference)
    last_action = get_last_action(session)
    if last_action:
        hints["last_action"] = {
            "tool": last_action.get("tool"),
            "customer_name": last_action.get("result", {}).get("customer_name"),
            "reversible": last_action.get("reversible"),
        }

    # Add pending operation
    pending = get_pending_operation(session)
    if pending:
        hints["pending_operation"] = pending

    # Add time context
    hints["time_context"] = get_time_context(db, session.current_event_id)

    # Add customer memory
    if session.current_customer_id:
        hints["customer_memory"] = get_customer_memory(db, session.current_customer_id)

    # Add predictions
    prediction = predict_next_action(session)
    if prediction:
        hints["prediction"] = prediction

    # Add suggestions
    hints["suggestions"] = get_smart_suggestions(db, session, user_input)

    # Detect ambiguous names and help disambiguate
    name_match = re.search(r'\b([A-Z][a-z]+)\b', user_input)
    if name_match and not hints.get("resolved_family_member"):
        name = name_match.group(1)
        matches = disambiguate_customer(db, name, session)
        if len(matches) > 1:
            hints["ambiguous_customers"] = matches
            hints["disambiguation_needed"] = True
        elif len(matches) == 1:
            hints["likely_customer"] = matches[0]

    # Check for confirmation context (user responding to pending question)
    confirmation_ctx = get_confirmation_context(db, session, user_input)
    if confirmation_ctx:
        hints["confirmation"] = confirmation_ctx

    return hints


def save_interaction_note(
    db: Session,
    customer_id: int,
    interaction_type: str,
    note: str
) -> None:
    """
    Save a note about a customer interaction for future context.

    This helps build cross-session memory.
    """
    customer_note = CustomerNote(
        event_goer_id=customer_id,
        note_type=interaction_type,
        note=note,
        created_by="ai_agent"
    )
    db.add(customer_note)
    db.commit()


# ============== Undo/Correction Support ==============

def detect_undo_intent(user_input: str) -> bool:
    """
    Detect if the user wants to undo the last action.

    Examples: "undo that", "cancel that", "never mind", "take that back"
    """
    input_lower = user_input.lower()
    return any(re.search(p, input_lower) for p in UNDO_PATTERNS)


def detect_correction_intent(user_input: str) -> Optional[dict]:
    """
    Detect if the user is correcting a previous statement.

    Returns:
        Dict with correction info or None

    Examples:
        "no, I meant Mike" → {"type": "correction", "correct_value": "Mike"}
        "not John, Mike" → {"type": "replacement", "wrong": "John", "correct": "Mike"}
    """
    input_lower = user_input.lower()

    for pattern in CORRECTION_PATTERNS:
        match = re.search(pattern, input_lower)
        if match:
            result = {"type": "correction", "raw_input": user_input}

            # Pattern: "not X, Y" - extract both wrong and correct values
            replacement_match = re.search(r'not\s+(\w+)\s*,\s*(\w+)', input_lower)
            if replacement_match:
                result["type"] = "replacement"
                result["wrong_value"] = replacement_match.group(1)
                result["correct_value"] = replacement_match.group(2)
                return result

            # Pattern: "I meant X" or "meant X" - get everything after "meant"
            meant_match = re.search(r'meant\s+(.+?)(?:\s*$|,|\.|!)', input_lower)
            if meant_match:
                # Clean up the value - get the main word(s)
                value = meant_match.group(1).strip()
                # Remove articles
                value = re.sub(r'^(the|a|an)\s+', '', value)
                result["correct_value"] = value
                return result

            # Pattern: "actually X" - get what comes after
            actually_match = re.search(r'actually\s*,?\s+(.+?)(?:\s*$|,|\.|!)', input_lower)
            if actually_match:
                value = actually_match.group(1).strip()
                value = re.sub(r'^(the|a|an)\s+', '', value)
                # Don't include "I meant" in the value
                value = re.sub(r'^i\s+meant\s+', '', value)
                result["correct_value"] = value
                return result

            return result

    return None


def get_last_action(session: ConversationSession) -> Optional[dict]:
    """
    Get the last action that was performed in this session.

    Returns:
        Dict with action info including reversibility
    """
    entity_context = json.loads(session.entity_context or '{}')
    return entity_context.get("last_action")


def set_last_action(
    db: Session,
    session: ConversationSession,
    tool_name: str,
    arguments: dict,
    result: dict
) -> None:
    """
    Record the last action for potential undo.

    Args:
        db: Database session
        session: The conversation session
        tool_name: Name of the tool that was called
        arguments: Arguments passed to the tool
        result: Result from the tool execution
    """
    entity_context = json.loads(session.entity_context or '{}')

    # Get reversibility info
    reversibility = REVERSIBLE_ACTIONS.get(tool_name, {
        "reversible": False,
        "description": "This action cannot be undone"
    })

    entity_context["last_action"] = {
        "tool": tool_name,
        "arguments": arguments,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reversible": reversibility.get("reversible", False),
        "undo_action": reversibility.get("undo_action"),
        "undo_description": reversibility.get("description"),
        "undo_condition": reversibility.get("condition"),
    }

    # Also keep a short history of actions (last 5)
    action_history = entity_context.get("action_history", [])
    action_history.append(entity_context["last_action"])
    entity_context["action_history"] = action_history[-5:]

    session.entity_context = json.dumps(entity_context)
    db.commit()


def clear_last_action(db: Session, session: ConversationSession) -> None:
    """Clear the last action after successful undo."""
    entity_context = json.loads(session.entity_context or '{}')
    if "last_action" in entity_context:
        del entity_context["last_action"]
        session.entity_context = json.dumps(entity_context)
        db.commit()


def get_undo_context(session: ConversationSession) -> Optional[dict]:
    """
    Get context needed to undo the last action.

    Returns:
        Dict with undo instructions or None if not undoable
    """
    last_action = get_last_action(session)
    if not last_action:
        return None

    if not last_action.get("reversible"):
        return {
            "can_undo": False,
            "reason": last_action.get("undo_description", "This action cannot be undone"),
            "action": last_action.get("tool"),
        }

    # Build undo context based on action type
    tool = last_action.get("tool")
    args = last_action.get("arguments", {})
    result = last_action.get("result", {})

    undo_context = {
        "can_undo": True,
        "action": tool,
        "undo_action": last_action.get("undo_action"),
        "description": last_action.get("undo_description"),
    }

    # Add specific undo parameters based on action type
    if tool in ("check_in_by_name", "check_in_ticket"):
        undo_context["undo_params"] = {
            "ticket_id": result.get("ticket_id"),
            "customer_name": result.get("customer_name"),
            "action": "uncheck",
        }
    elif tool == "purchase_ticket":
        undo_context["undo_params"] = {
            "ticket_id": result.get("ticket_id"),
            "action": "cancel",
            "condition": "Only if status is still PENDING",
        }

    return undo_context


def handle_correction(
    db: Session,
    session: ConversationSession,
    correction: dict,
    user_input: str
) -> dict:
    """
    Process a correction and return hints for the LLM.

    Args:
        db: Database session
        session: The conversation session
        correction: Correction info from detect_correction_intent
        user_input: Original user input

    Returns:
        Dict with correction context for LLM
    """
    last_action = get_last_action(session)

    context = {
        "is_correction": True,
        "correction_type": correction.get("type"),
        "user_input": user_input,
    }

    if correction.get("correct_value"):
        context["correct_value"] = correction["correct_value"]

    if correction.get("wrong_value"):
        context["wrong_value"] = correction["wrong_value"]

    if last_action:
        context["last_action"] = {
            "tool": last_action.get("tool"),
            "arguments": last_action.get("arguments"),
            "can_undo": last_action.get("reversible", False),
        }

        # If they're correcting a name, provide the wrong name that was used
        if last_action.get("arguments", {}).get("name"):
            context["previous_name_used"] = last_action["arguments"]["name"]

    return context


def get_undo_or_correction_context(
    db: Session,
    session: ConversationSession,
    user_input: str
) -> Optional[dict]:
    """
    Check if user wants to undo or correct, and return appropriate context.

    This is the main entry point for undo/correction handling.

    Returns:
        Dict with undo/correction context, or None if neither detected
    """
    # Check for undo intent
    if detect_undo_intent(user_input):
        undo_ctx = get_undo_context(session)
        if undo_ctx:
            undo_ctx["intent"] = "undo"
            return undo_ctx
        return {
            "intent": "undo",
            "can_undo": False,
            "reason": "No recent action to undo",
        }

    # Check for correction intent
    correction = detect_correction_intent(user_input)
    if correction:
        return handle_correction(db, session, correction, user_input)

    return None


# ============== Batch Group Check-in ==============

def detect_group_checkin(user_input: str) -> Optional[dict]:
    """
    Detect if user wants to check in a group.

    Returns:
        Dict with group info or None

    Examples:
        "check in the Smith party" → {"type": "party", "name": "Smith"}
        "John and his wife" → {"type": "with_companion", "primary": "John", "relation": "wife"}
        "check in John and Sarah" → {"type": "pair", "names": ["John", "Sarah"]}
    """
    input_lower = user_input.lower()

    # Pattern: "check in the whole/entire party" (uses session context) - check FIRST
    if re.search(r'check\s*in\s+(?:the\s+)?(?:whole|entire)\s+(?:party|group)', input_lower):
        return {
            "type": "whole_party",
            "raw_input": user_input
        }

    # Pattern: "the Smith party/group/family" - but NOT "the whole party"
    party_match = re.search(r'(?:check\s*in\s+)?the\s+(\w+)\s+(?:party|group|family)', input_lower)
    if party_match:
        name = party_match.group(1)
        if name not in ("whole", "entire"):
            return {
                "type": "party",
                "name": name,
                "raw_input": user_input
            }

    # Pattern: "check in the Smiths"
    plural_match = re.search(r'check\s*in\s+(?:the\s+)?(\w+)s\b', input_lower)
    if plural_match:
        name = plural_match.group(1)
        # Avoid matching common words
        if name not in ("ticket", "guest", "customer", "person", "attendee"):
            return {
                "type": "family_name",
                "name": name,
                "raw_input": user_input
            }

    # Pattern: "John and his wife/family"
    companion_match = re.search(
        r'(\w+)\s+and\s+(?:his|her|their)\s+(wife|husband|partner|family|group|kids|children)',
        input_lower
    )
    if companion_match:
        return {
            "type": "with_companion",
            "primary": companion_match.group(1),
            "relation": companion_match.group(2),
            "raw_input": user_input
        }

    # Pattern: "check in everyone" or "all of them"
    if re.search(r'check\s*in\s+(?:everyone|all\s+of\s+them)', input_lower):
        return {
            "type": "all_context",
            "raw_input": user_input
        }

    # Pattern: "John and Sarah" - explicit pair
    pair_match = re.search(r'check\s*in\s+(\w+)\s+(?:and|with)\s+(\w+)', input_lower)
    if pair_match:
        return {
            "type": "pair",
            "names": [pair_match.group(1), pair_match.group(2)],
            "raw_input": user_input
        }

    return None


def find_group_members(
    db: Session,
    session: ConversationSession,
    group_info: dict,
    event_id: Optional[int] = None
) -> list[dict]:
    """
    Find all members of a group for batch check-in.

    Args:
        db: Database session
        session: Conversation session for context
        group_info: Group detection result from detect_group_checkin
        event_id: Optional event ID to filter tickets

    Returns:
        List of group members with ticket info
    """
    from app.models import TicketStatus

    members = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Determine event to use
    if not event_id:
        event_id = session.current_event_id
        if not event_id:
            # Try to find today's event
            time_ctx = get_time_context(db, None)
            event_id = time_ctx.get("event_id")

    if not event_id:
        return []

    group_type = group_info.get("type")

    if group_type == "party" or group_type == "family_name":
        # Find by last name
        last_name = group_info.get("name", "")
        tickets = db.query(Ticket).join(TicketTier).join(EventGoer).filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            EventGoer.name.ilike(f"% {last_name}") | EventGoer.name.ilike(f"{last_name} %")
        ).all()

        for ticket in tickets:
            members.append({
                "customer_id": ticket.event_goer_id,
                "name": ticket.event_goer.name,
                "email": ticket.event_goer.email,
                "ticket_id": ticket.id,
                "status": ticket.status.value,
                "already_checked_in": ticket.status == TicketStatus.CHECKED_IN
            })

    elif group_type == "with_companion":
        # Find primary person and their companions
        primary_name = group_info.get("primary", "")
        relation = group_info.get("relation", "")

        # Find primary
        primary_ticket = db.query(Ticket).join(TicketTier).join(EventGoer).filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            EventGoer.name.ilike(f"%{primary_name}%")
        ).first()

        if primary_ticket:
            members.append({
                "customer_id": primary_ticket.event_goer_id,
                "name": primary_ticket.event_goer.name,
                "email": primary_ticket.event_goer.email,
                "ticket_id": primary_ticket.id,
                "status": primary_ticket.status.value,
                "already_checked_in": primary_ticket.status == TicketStatus.CHECKED_IN,
                "role": "primary"
            })

            # Find companions
            if relation in ("wife", "husband", "partner", "spouse"):
                from app.services.family_resolver import find_family_member
                companion = find_family_member(db, primary_ticket.event_goer_id, relation)
                if companion and companion.get("id"):
                    comp_ticket = db.query(Ticket).join(TicketTier).filter(
                        TicketTier.event_id == event_id,
                        Ticket.event_goer_id == companion["id"],
                        Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
                    ).first()
                    if comp_ticket:
                        members.append({
                            "customer_id": companion["id"],
                            "name": companion["name"],
                            "email": companion.get("email"),
                            "ticket_id": comp_ticket.id,
                            "status": comp_ticket.status.value,
                            "already_checked_in": comp_ticket.status == TicketStatus.CHECKED_IN,
                            "role": relation
                        })

            elif relation in ("family", "group", "kids", "children"):
                # Find all with same last name or purchased together
                last_name = primary_ticket.event_goer.name.split()[-1] if primary_ticket.event_goer.name else ""
                if last_name:
                    family_tickets = db.query(Ticket).join(TicketTier).join(EventGoer).filter(
                        TicketTier.event_id == event_id,
                        Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                        Ticket.event_goer_id != primary_ticket.event_goer_id,
                        EventGoer.name.ilike(f"% {last_name}")
                    ).all()
                    for ft in family_tickets:
                        members.append({
                            "customer_id": ft.event_goer_id,
                            "name": ft.event_goer.name,
                            "email": ft.event_goer.email,
                            "ticket_id": ft.id,
                            "status": ft.status.value,
                            "already_checked_in": ft.status == TicketStatus.CHECKED_IN,
                            "role": "family"
                        })

    elif group_type == "pair":
        # Find specific named pair
        names = group_info.get("names", [])
        for name in names:
            ticket = db.query(Ticket).join(TicketTier).join(EventGoer).filter(
                TicketTier.event_id == event_id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                EventGoer.name.ilike(f"%{name}%")
            ).first()
            if ticket:
                members.append({
                    "customer_id": ticket.event_goer_id,
                    "name": ticket.event_goer.name,
                    "email": ticket.event_goer.email,
                    "ticket_id": ticket.id,
                    "status": ticket.status.value,
                    "already_checked_in": ticket.status == TicketStatus.CHECKED_IN
                })

    elif group_type in ("whole_party", "all_context"):
        # Use recent customers from session context
        entity_context = json.loads(session.entity_context or '{}')
        recent_customers = entity_context.get("customers", [])

        for customer in recent_customers:
            customer_id = customer.get("id")
            if customer_id:
                ticket = db.query(Ticket).join(TicketTier).filter(
                    TicketTier.event_id == event_id,
                    Ticket.event_goer_id == customer_id,
                    Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN])
                ).first()
                if ticket:
                    members.append({
                        "customer_id": customer_id,
                        "name": customer.get("name", ""),
                        "ticket_id": ticket.id,
                        "status": ticket.status.value,
                        "already_checked_in": ticket.status == TicketStatus.CHECKED_IN
                    })

    # Deduplicate by customer_id
    seen = set()
    unique_members = []
    for m in members:
        if m["customer_id"] not in seen:
            seen.add(m["customer_id"])
            unique_members.append(m)

    return unique_members


def get_group_checkin_context(
    db: Session,
    session: ConversationSession,
    user_input: str
) -> Optional[dict]:
    """
    Check for group check-in and return context if detected.

    This is the main entry point for group check-in handling.

    Returns:
        Dict with group check-in context or None
    """
    group_info = detect_group_checkin(user_input)
    if not group_info:
        return None

    members = find_group_members(db, session, group_info)

    if not members:
        return {
            "is_group_checkin": True,
            "group_type": group_info.get("type"),
            "group_identifier": group_info.get("name") or group_info.get("primary") or group_info.get("names"),
            "members_found": 0,
            "error": "No matching group members found with tickets for this event"
        }

    # Count already checked in
    already_checked = sum(1 for m in members if m.get("already_checked_in"))
    to_check_in = [m for m in members if not m.get("already_checked_in")]

    return {
        "is_group_checkin": True,
        "group_type": group_info.get("type"),
        "group_identifier": group_info.get("name") or group_info.get("primary") or group_info.get("names"),
        "members": members,
        "members_found": len(members),
        "already_checked_in": already_checked,
        "to_check_in": len(to_check_in),
        "to_check_in_list": to_check_in,
        "member_names": [m["name"] for m in members],
        "ticket_ids": [m["ticket_id"] for m in to_check_in],
    }


# ============== Confirmation Tracking ==============

def detect_confirmation_reply(user_input: str) -> Optional[dict]:
    """
    Detect if user is confirming, rejecting, or selecting from options.

    Returns:
        Dict with reply type and details, or None
    """
    input_clean = user_input.strip().lower()

    # Check for confirmation
    for pattern in CONFIRMATION_PATTERNS:
        if re.match(pattern, input_clean):
            return {"type": "confirm", "raw_input": user_input}

    # Check for rejection
    for pattern in REJECTION_PATTERNS:
        if re.match(pattern, input_clean):
            return {"type": "reject", "raw_input": user_input}

    # Check for selection
    for pattern in SELECTION_PATTERNS:
        match = re.search(pattern, input_clean)
        if match:
            result = {"type": "select", "raw_input": user_input}

            # Extract selection index
            if "first" in input_clean:
                result["index"] = 0
            elif "second" in input_clean:
                result["index"] = 1
            elif "third" in input_clean:
                result["index"] = 2
            elif "fourth" in input_clean:
                result["index"] = 3
            elif "last" in input_clean:
                result["index"] = -1
            elif match.groups():
                # Extract number from capture group
                for g in match.groups():
                    if g and g.isdigit():
                        result["index"] = int(g) - 1  # Convert to 0-indexed
                        break

            return result

    return None


def set_pending_confirmation(
    db: Session,
    session: ConversationSession,
    action: str,
    args: dict,
    context: dict,
    options: list = None,
    question: str = None
) -> None:
    """
    Set a pending confirmation with full context.

    Args:
        db: Database session
        session: Conversation session
        action: The action to execute on confirmation (e.g., "check_in_by_name")
        args: Arguments for the action
        context: Full context (event name, customer name, etc.)
        options: Optional list of options user can select from
        question: The confirmation question that was asked
    """
    entity_context = json.loads(session.entity_context or '{}')

    entity_context["pending_confirmation"] = {
        "action": action,
        "args": args,
        "context": context,
        "options": options,
        "question": question,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    session.entity_context = json.dumps(entity_context)
    db.commit()


def get_pending_confirmation(session: ConversationSession) -> Optional[dict]:
    """Get the pending confirmation if any."""
    entity_context = json.loads(session.entity_context or '{}')
    return entity_context.get("pending_confirmation")


def clear_pending_confirmation(db: Session, session: ConversationSession) -> None:
    """Clear the pending confirmation."""
    entity_context = json.loads(session.entity_context or '{}')
    if "pending_confirmation" in entity_context:
        del entity_context["pending_confirmation"]
        session.entity_context = json.dumps(entity_context)
        db.commit()


def resolve_confirmation(
    db: Session,
    session: ConversationSession,
    user_input: str
) -> Optional[dict]:
    """
    Check if user is responding to a pending confirmation.

    Returns:
        Dict with resolution details or None if no pending confirmation
    """
    pending = get_pending_confirmation(session)
    if not pending:
        return None

    reply = detect_confirmation_reply(user_input)
    if not reply:
        # User said something else - might be changing their request
        return {
            "has_pending": True,
            "pending": pending,
            "reply_type": "other",
            "raw_input": user_input,
            "hint": "User may be modifying their request or asking something else"
        }

    result = {
        "has_pending": True,
        "pending": pending,
        "reply_type": reply["type"],
    }

    if reply["type"] == "confirm":
        result["execute"] = True
        result["action"] = pending["action"]
        result["args"] = pending["args"]
        result["context"] = pending["context"]
        # Clear after resolution
        clear_pending_confirmation(db, session)

    elif reply["type"] == "reject":
        result["execute"] = False
        result["cancelled"] = True
        clear_pending_confirmation(db, session)

    elif reply["type"] == "select":
        options = pending.get("options", [])
        index = reply.get("index")

        if options and index is not None:
            # Handle "last" selection
            if index == -1:
                index = len(options) - 1

            if 0 <= index < len(options):
                selected = options[index]
                result["execute"] = True
                result["selected"] = selected
                result["selected_index"] = index

                # Merge selected option into args
                if isinstance(selected, dict):
                    result["args"] = {**pending["args"], **selected}
                else:
                    result["args"] = pending["args"]

                result["action"] = pending["action"]
                result["context"] = pending["context"]
                clear_pending_confirmation(db, session)
            else:
                result["execute"] = False
                result["error"] = f"Invalid selection. Please choose 1-{len(options)}"
        else:
            result["execute"] = False
            result["error"] = "No options to select from"

    return result


def build_confirmation_question(
    action: str,
    args: dict,
    event_context: dict = None,
    customer_context: dict = None
) -> str:
    """
    Build a clear confirmation question with full context.

    Returns:
        Human-readable confirmation question
    """
    parts = []

    # Action-specific formatting
    if action == "check_in_by_name":
        customer = args.get("name") or customer_context.get("name", "this customer")
        parts.append(f"Check in {customer}")

    elif action == "check_in_ticket":
        ticket_id = args.get("ticket_id", "ticket")
        parts.append(f"Check in ticket #{ticket_id}")

    elif action == "purchase_ticket":
        qty = args.get("quantity", 1)
        tier = args.get("tier_name", "ticket")
        parts.append(f"Purchase {qty} {tier} ticket(s)")

    elif action == "refund_ticket":
        parts.append("Process refund")

    elif action == "send_ticket_sms":
        parts.append("Send ticket via SMS")

    else:
        parts.append(f"Execute {action}")

    # Add event context
    if event_context:
        event_name = event_context.get("name") or event_context.get("event_name")
        event_time = event_context.get("event_time")
        event_date = event_context.get("event_date")

        if event_name:
            event_str = event_name
            if event_time:
                event_str += f" at {event_time}"
            if event_date:
                # Only add date if not today
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if event_date != today:
                    event_str += f" on {event_date}"
            parts.append(f"for {event_str}")

    # Add customer context if not already in action
    if customer_context and action not in ("check_in_by_name",):
        customer_name = customer_context.get("name")
        if customer_name:
            parts.append(f"({customer_name})")

    return " ".join(parts) + "?"


def get_confirmation_context(
    db: Session,
    session: ConversationSession,
    user_input: str
) -> Optional[dict]:
    """
    Main entry point for confirmation handling.

    Returns context about pending confirmations and user responses.
    """
    # Check if there's a pending confirmation
    pending = get_pending_confirmation(session)

    if pending:
        # Resolve the user's response
        resolution = resolve_confirmation(db, session, user_input)
        return resolution

    # No pending confirmation - check if user's input looks like a confirmation anyway
    reply = detect_confirmation_reply(user_input)
    if reply:
        return {
            "has_pending": False,
            "orphan_reply": True,
            "reply_type": reply["type"],
            "hint": "User gave a confirmation-style reply but nothing is pending"
        }

    return None
