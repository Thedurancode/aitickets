"""
Voice Command Processor with MCP Integration

Handles natural language voice commands and routes them to appropriate backend services.
Integrates with MCP for code intelligence and cross-session memory.
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import EventGoer, Event, Ticket, TicketTier
from app.auth import get_current_user
from app.models_extensions import (
    Affiliate, LoyaltyAccount, GroupPurchase, GroupPurchaseStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice Commands"])


# ==================== Voice Command Intent Parser ====================

class VoiceIntent:
    """Parse voice commands into structured intents."""

    CREATE_EVENT = "create_event"
    GET_STATS = "get_stats"
    FIND_CODE = "find_code"
    CHECK_SALES = "check_sales"
    GET_REVENUE = "get_revenue"
    LIST_EVENTS = "list_events"
    AFFILIATE_STATS = "affiliate_stats"
    LOYALTY_INFO = "loyalty_info"
    GROUP_BUYING_STATUS = "group_buying_status"
    SEARCH_MEMORY = "search_memory"

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """
        Parse voice command text into intent and parameters.

        Examples:
            "Create event AI Summit on June 15th" -> {intent: CREATE_EVENT, ...}
            "How many tickets sold today?" -> {intent: CHECK_SALES, ...}
            "Show me my affiliate earnings" -> {intent: AFFILIATE_STATS, ...}
        """
        text_lower = text.lower()

        # Event creation
        if any(word in text_lower for word in ["create event", "new event", "make event"]):
            return {
                "intent": VoiceIntent.CREATE_EVENT,
                "raw_text": text,
                "confidence": 0.95
            }

        # Sales/ticket queries
        if any(word in text_lower for word in ["tickets sold", "how many tickets", "sales today"]):
            return {
                "intent": VoiceIntent.CHECK_SALES,
                "raw_text": text,
                "confidence": 0.90
            }

        # Revenue queries
        if any(word in text_lower for word in ["revenue", "earnings", "money made", "total sales"]):
            return {
                "intent": VoiceIntent.GET_REVENUE,
                "raw_text": text,
                "confidence": 0.90
            }

        # Event listing
        if any(word in text_lower for word in ["list events", "show events", "my events", "upcoming events"]):
            return {
                "intent": VoiceIntent.LIST_EVENTS,
                "raw_text": text,
                "confidence": 0.88
            }

        # Affiliate stats
        if any(word in text_lower for word in ["affiliate", "referral", "commission", "clicks"]):
            return {
                "intent": VoiceIntent.AFFILIATE_STATS,
                "raw_text": text,
                "confidence": 0.85
            }

        # Loyalty program
        if any(word in text_lower for word in ["loyalty", "points", "badges", "tier"]):
            return {
                "intent": VoiceIntent.LOYALTY_INFO,
                "raw_text": text,
                "confidence": 0.85
            }

        # Group buying
        if any(word in text_lower for word in ["group", "group buying", "split payment"]):
            return {
                "intent": VoiceIntent.GROUP_BUYING_STATUS,
                "raw_text": text,
                "confidence": 0.83
            }

        # Code search (MCP powered)
        if any(word in text_lower for word in ["find", "show me", "where is", "how does"]):
            return {
                "intent": VoiceIntent.FIND_CODE,
                "raw_text": text,
                "confidence": 0.75
            }

        # General stats
        return {
            "intent": VoiceIntent.GET_STATS,
            "raw_text": text,
            "confidence": 0.60
        }


# ==================== Voice Command Handlers ====================

@router.post("/command")
async def process_voice_command(
    text: str,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a voice command (text input for demo - add Whisper later).

    Examples:
        POST /api/voice/command?text=How many tickets sold today?
        POST /api/voice/command?text=Show me my affiliate earnings
    """
    logger.info(f"Voice command from user {current_user.id}: {text}")

    # Parse intent
    intent_data = VoiceIntent.parse(text)
    intent = intent_data["intent"]

    try:
        # Route to appropriate handler
        if intent == VoiceIntent.CREATE_EVENT:
            result = await handle_create_event(text, current_user, db)

        elif intent == VoiceIntent.CHECK_SALES:
            result = await handle_check_sales(text, current_user, db)

        elif intent == VoiceIntent.GET_REVENUE:
            result = await handle_get_revenue(text, current_user, db)

        elif intent == VoiceIntent.LIST_EVENTS:
            result = await handle_list_events(text, current_user, db)

        elif intent == VoiceIntent.AFFILIATE_STATS:
            result = await handle_affiliate_stats(text, current_user, db)

        elif intent == VoiceIntent.LOYALTY_INFO:
            result = await handle_loyalty_info(text, current_user, db)

        elif intent == VoiceIntent.GROUP_BUYING_STATUS:
            result = await handle_group_buying(text, current_user, db)

        elif intent == VoiceIntent.FIND_CODE:
            result = await handle_code_search(text, current_user, db)

        else:
            result = await handle_general_stats(text, current_user, db)

        return {
            "success": True,
            "intent": intent,
            "confidence": intent_data["confidence"],
            "result": result,
            "natural_language_response": format_natural_response(intent, result)
        }

    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Intent Handlers ====================

async def handle_create_event(text: str, user: EventGoer, db: Session) -> Dict:
    """Handle event creation from voice command."""
    return {
        "type": "event_creation",
        "message": "Event creation requires more details. Please specify: name, date, venue, ticket pricing",
        "next_steps": [
            "Say: 'Name is AI Summit 2026'",
            "Say: 'Date is June 15th'",
            "Say: 'Venue is Convention Center'",
            "Say: 'General admission $99, VIP $299'"
        ]
    }


async def handle_check_sales(text: str, user: EventGoer, db: Session) -> Dict:
    """Check ticket sales with voice query."""

    # Determine time range from voice command
    if "today" in text.lower():
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
    elif "this week" in text.lower():
        start_date = datetime.utcnow() - timedelta(days=7)
    elif "this month" in text.lower():
        start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = datetime.utcnow() - timedelta(days=1)

    # Query tickets
    tickets = db.query(Ticket).join(Event).filter(
        Event.organizer_id == user.id,
        Ticket.created_at >= start_date
    ).all()

    total_tickets = len(tickets)
    total_revenue = sum(t.price_paid for t in tickets)

    # Group by event
    events_data = {}
    for ticket in tickets:
        event_name = ticket.event.name
        if event_name not in events_data:
            events_data[event_name] = {"count": 0, "revenue": 0}
        events_data[event_name]["count"] += 1
        events_data[event_name]["revenue"] += ticket.price_paid

    return {
        "type": "sales_report",
        "period": "today" if "today" in text.lower() else "custom",
        "total_tickets": total_tickets,
        "total_revenue": total_revenue,
        "revenue_formatted": f"${total_revenue/100:,.2f}",
        "by_event": events_data,
        "start_date": start_date.isoformat()
    }


async def handle_get_revenue(text: str, user: EventGoer, db: Session) -> Dict:
    """Get revenue statistics."""

    # All-time revenue
    total_revenue = db.query(func.sum(Ticket.price_paid)).join(Event).filter(
        Event.organizer_id == user.id
    ).scalar() or 0

    # This month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    monthly_revenue = db.query(func.sum(Ticket.price_paid)).join(Event).filter(
        Event.organizer_id == user.id,
        Ticket.created_at >= month_start
    ).scalar() or 0

    # Today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    daily_revenue = db.query(func.sum(Ticket.price_paid)).join(Event).filter(
        Event.organizer_id == user.id,
        Ticket.created_at >= today_start
    ).scalar() or 0

    return {
        "type": "revenue_report",
        "total_revenue": total_revenue,
        "total_revenue_formatted": f"${total_revenue/100:,.2f}",
        "monthly_revenue": monthly_revenue,
        "monthly_revenue_formatted": f"${monthly_revenue/100:,.2f}",
        "daily_revenue": daily_revenue,
        "daily_revenue_formatted": f"${daily_revenue/100:,.2f}"
    }


async def handle_list_events(text: str, user: EventGoer, db: Session) -> Dict:
    """List user's events."""

    # Determine if looking for upcoming or past
    if "past" in text.lower():
        events = db.query(Event).filter(
            Event.organizer_id == user.id,
            Event.date < datetime.utcnow()
        ).order_by(Event.date.desc()).limit(10).all()
    else:
        events = db.query(Event).filter(
            Event.organizer_id == user.id,
            Event.date >= datetime.utcnow()
        ).order_by(Event.date.asc()).limit(10).all()

    return {
        "type": "event_list",
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "name": e.name,
                "date": e.date.isoformat() if e.date else None,
                "venue": e.venue,
                "tickets_sold": len(e.tickets)
            }
            for e in events
        ]
    }


async def handle_affiliate_stats(text: str, user: EventGoer, db: Session) -> Dict:
    """Get affiliate program statistics."""

    affiliate = db.query(Affiliate).filter(
        Affiliate.event_goer_id == user.id
    ).first()

    if not affiliate:
        return {
            "type": "affiliate_stats",
            "registered": False,
            "message": "You're not registered as an affiliate. Would you like to apply?"
        }

    return {
        "type": "affiliate_stats",
        "registered": True,
        "code": affiliate.code,
        "status": affiliate.status.value,
        "total_clicks": affiliate.total_clicks,
        "total_conversions": affiliate.total_conversions,
        "commission_earned": affiliate.total_commission,
        "commission_earned_formatted": f"${affiliate.total_commission/100:,.2f}",
        "commission_pending": affiliate.commission_pending,
        "commission_pending_formatted": f"${affiliate.commission_pending/100:,.2f}",
        "commission_paid": affiliate.commission_paid,
        "commission_paid_formatted": f"${affiliate.commission_paid/100:,.2f}"
    }


async def handle_loyalty_info(text: str, user: EventGoer, db: Session) -> Dict:
    """Get loyalty program information."""

    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.event_goer_id == user.id
    ).first()

    if not account:
        return {
            "type": "loyalty_info",
            "enrolled": False,
            "message": "You're not enrolled in the loyalty program. Sign up to earn points!"
        }

    return {
        "type": "loyalty_info",
        "enrolled": True,
        "tier": account.current_tier.value,
        "available_points": account.available_points,
        "lifetime_points": account.lifetime_points,
        "next_tier": get_next_tier(account.current_tier),
        "points_to_next_tier": calculate_points_to_next_tier(account)
    }


async def handle_group_buying(text: str, user: EventGoer, db: Session) -> Dict:
    """Get group buying status."""

    # Active groups user is organizing
    organizing = db.query(GroupPurchase).filter(
        GroupPurchase.organizer_id == user.id,
        GroupPurchase.status == GroupPurchaseStatus.PENDING
    ).all()

    return {
        "type": "group_buying_status",
        "active_groups": len(organizing),
        "groups": [
            {
                "id": g.id,
                "event_id": g.event_id,
                "total_tickets": g.total_tickets,
                "tickets_claimed": g.total_tickets - (g.amount_remaining // (g.total_amount // g.total_tickets)),
                "amount_paid": g.amount_paid,
                "amount_paid_formatted": f"${g.amount_paid/100:,.2f}",
                "amount_remaining": g.amount_remaining,
                "amount_remaining_formatted": f"${g.amount_remaining/100:,.2f}",
                "expires_at": g.expires_at.isoformat()
            }
            for g in organizing
        ]
    }


async def handle_code_search(text: str, user: EventGoer, db: Session) -> Dict:
    """Handle code search queries using MCP (simulated for demo)."""

    # Extract search term
    search_term = text.lower().replace("find", "").replace("show me", "").replace("where is", "").strip()

    # This would use MCP smart_search in production
    return {
        "type": "code_search",
        "query": search_term,
        "message": f"Code search for: {search_term}",
        "suggestion": "Use MCP smart_search for actual implementation",
        "example_files": [
            "app/routers/stripe_webhooks.py - Payment webhook handlers",
            "app/routers/group_buying.py - Group purchase logic",
            "app/routers/affiliates.py - Affiliate program",
            "app/auth.py - JWT authentication"
        ]
    }


async def handle_general_stats(text: str, user: EventGoer, db: Session) -> Dict:
    """Handle general statistics query."""

    # Gather all stats
    total_events = db.query(func.count(Event.id)).filter(
        Event.organizer_id == user.id
    ).scalar()

    total_tickets = db.query(func.count(Ticket.id)).join(Event).filter(
        Event.organizer_id == user.id
    ).scalar()

    total_revenue = db.query(func.sum(Ticket.price_paid)).join(Event).filter(
        Event.organizer_id == user.id
    ).scalar() or 0

    return {
        "type": "general_stats",
        "total_events": total_events,
        "total_tickets_sold": total_tickets,
        "total_revenue": total_revenue,
        "total_revenue_formatted": f"${total_revenue/100:,.2f}"
    }


# ==================== Helper Functions ====================

def format_natural_response(intent: str, result: Dict) -> str:
    """Convert structured data into natural language response."""

    if intent == VoiceIntent.CHECK_SALES:
        return f"You've sold {result['total_tickets']} tickets worth {result['revenue_formatted']} in the selected period."

    elif intent == VoiceIntent.GET_REVENUE:
        return f"Your total revenue is {result['total_revenue_formatted']}. This month: {result['monthly_revenue_formatted']}. Today: {result['daily_revenue_formatted']}."

    elif intent == VoiceIntent.LIST_EVENTS:
        return f"You have {result['count']} events. " + ", ".join([e["name"] for e in result["events"][:3]])

    elif intent == VoiceIntent.AFFILIATE_STATS:
        if result.get("registered"):
            return f"Your affiliate code is {result['code']}. You've earned {result['commission_earned_formatted']} with {result['commission_pending_formatted']} pending payout."
        return result["message"]

    elif intent == VoiceIntent.LOYALTY_INFO:
        if result.get("enrolled"):
            return f"You're in the {result['tier']} tier with {result['available_points']} points available."
        return result["message"]

    elif intent == VoiceIntent.GROUP_BUYING_STATUS:
        return f"You have {result['active_groups']} active group purchases."

    else:
        return json.dumps(result, indent=2)


def get_next_tier(current_tier):
    """Get next loyalty tier."""
    from app.models_extensions import LoyaltyTier
    tiers = [LoyaltyTier.BRONZE, LoyaltyTier.SILVER, LoyaltyTier.GOLD, LoyaltyTier.PLATINUM]
    current_index = tiers.index(current_tier)
    return tiers[current_index + 1].value if current_index < len(tiers) - 1 else "Max tier"


def calculate_points_to_next_tier(account) -> int:
    """Calculate points needed for next tier."""
    from app.models_extensions import LoyaltyTier
    current = account.lifetime_points

    if account.current_tier == LoyaltyTier.BRONZE:
        return 1000 - current
    elif account.current_tier == LoyaltyTier.SILVER:
        return 3000 - current
    elif account.current_tier == LoyaltyTier.GOLD:
        return 10000 - current
    else:
        return 0  # Already at max
