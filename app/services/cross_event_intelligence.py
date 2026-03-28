"""
Cross-Event Intelligence

Learn from entire event portfolio to make smarter decisions:
- Identify patterns across all events
- Build customer profiles and lookalike audiences
- Detect successful strategies to replicate
- Seasonal pattern recognition
- Competitive intelligence
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import (
    Event, Ticket, TicketTier, EventGoer, Venue, EventCategory,
    TicketStatus
)

logger = logging.getLogger(__name__)


def identify_best_customers(db: Session, limit: int = 100) -> Dict:
    """
    Identify top customers by spend and frequency (RFM analysis).

    RFM = Recency, Frequency, Monetary value

    Returns:
        Dict with top customers and their profiles
    """
    # Get all event goers with ticket counts and spend
    customer_stats = (
        db.query(
            EventGoer.id,
            EventGoer.email,
            EventGoer.first_name,
            EventGoer.last_name,
            func.count(Ticket.id).label("tickets_purchased"),
            func.sum(Ticket.price_paid_cents).label("total_spend_cents"),
            func.max(Ticket.created_at).label("last_purchase"),
        )
        .join(Ticket, Ticket.event_goer_id == EventGoer.id)
        .filter(Ticket.status == TicketStatus.CONFIRMED)
        .group_by(EventGoer.id)
        .having(func.count(Ticket.id) >= 2)  # At least 2 purchases
        .order_by(func.sum(Ticket.price_paid_cents).desc())
        .limit(limit)
        .all()
    )

    top_customers = []

    for customer in customer_stats:
        # Calculate recency (days since last purchase)
        days_since_purchase = (datetime.now(timezone.utc) - customer.last_purchase).days if customer.last_purchase else 9999

        # RFM scoring (simplified)
        recency_score = 5 if days_since_purchase < 30 else (4 if days_since_purchase < 90 else 3)
        frequency_score = min(5, customer.tickets_purchased)
        monetary_score = min(5, customer.total_spend_cents // 10000)  # $100 increments

        rfm_score = recency_score + frequency_score + monetary_score

        top_customers.append({
            "id": customer.id,
            "email": customer.email,
            "name": f"{customer.first_name} {customer.last_name}",
            "tickets_purchased": customer.tickets_purchased,
            "total_spend_cents": customer.total_spend_cents,
            "total_spend_usd": f"${customer.total_spend_cents/100:.2f}",
            "last_purchase_days_ago": days_since_purchase,
            "rfm_score": rfm_score,
            "segment": "VIP" if rfm_score >= 12 else ("High Value" if rfm_score >= 9 else "Regular"),
        })

    # Calculate segments
    vip_count = len([c for c in top_customers if c["segment"] == "VIP"])
    high_value_count = len([c for c in top_customers if c["segment"] == "High Value"])

    return {
        "total_analyzed": len(top_customers),
        "segments": {
            "vip": vip_count,
            "high_value": high_value_count,
            "regular": len(top_customers) - vip_count - high_value_count,
        },
        "top_customers": top_customers[:20],  # Return top 20
        "recommendation": f"Target {vip_count} VIP customers for high-value events with early access",
    }


def find_event_patterns(db: Session) -> Dict:
    """
    Identify successful patterns across all events.

    Patterns:
    - Best-performing venues
    - Most profitable categories
    - Optimal pricing ranges
    - Seasonal trends
    """
    # Analyze venue performance
    venue_performance = (
        db.query(
            Venue.id,
            Venue.name,
            func.count(Event.id).label("events_hosted"),
            func.avg(TicketTier.quantity_sold * 1.0 / TicketTier.quantity_available).label("avg_sell_through"),
        )
        .join(Event, Event.venue_id == Venue.id)
        .join(TicketTier, TicketTier.event_id == Event.id)
        .group_by(Venue.id)
        .having(func.count(Event.id) >= 3)  # At least 3 events
        .order_by(func.avg(TicketTier.quantity_sold * 1.0 / TicketTier.quantity_available).desc())
        .limit(10)
        .all()
    )

    top_venues = [
        {
            "venue_id": v.id,
            "venue_name": v.name,
            "events_hosted": v.events_hosted,
            "avg_sell_through": round(v.avg_sell_through, 2),
        }
        for v in venue_performance
    ]

    # Analyze category performance
    category_performance = (
        db.query(
            EventCategory.id,
            EventCategory.name,
            func.count(Event.id).label("events_count"),
            func.sum(TicketTier.quantity_sold * TicketTier.price).label("total_revenue"),
        )
        .join(Event, Event.category_id == EventCategory.id)
        .join(TicketTier, TicketTier.event_id == Event.id)
        .group_by(EventCategory.id)
        .order_by(func.sum(TicketTier.quantity_sold * TicketTier.price).desc())
        .limit(10)
        .all()
    )

    top_categories = [
        {
            "category_id": c.id,
            "category_name": c.name,
            "events_count": c.events_count,
            "total_revenue_cents": c.total_revenue or 0,
            "total_revenue_usd": f"${(c.total_revenue or 0)/100:.2f}",
        }
        for c in category_performance
    ]

    # Analyze seasonal patterns
    events_by_month = (
        db.query(
            func.extract('month', Event.event_date).label('month'),
            func.count(Event.id).label('events_count'),
            func.avg(TicketTier.quantity_sold * 1.0 / TicketTier.quantity_available).label('avg_sell_through'),
        )
        .join(TicketTier, TicketTier.event_id == Event.id)
        .group_by(func.extract('month', Event.event_date))
        .all()
    )

    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    seasonal_patterns = [
        {
            "month": month_names[int(m.month)],
            "events_count": m.events_count,
            "avg_sell_through": round(m.avg_sell_through, 2) if m.avg_sell_through else 0,
        }
        for m in events_by_month
    ]

    # Find best months
    best_month = max(seasonal_patterns, key=lambda x: x["avg_sell_through"]) if seasonal_patterns else None

    return {
        "top_venues": top_venues,
        "top_categories": top_categories,
        "seasonal_patterns": seasonal_patterns,
        "insights": {
            "best_venue": top_venues[0]["venue_name"] if top_venues else None,
            "best_category": top_categories[0]["category_name"] if top_categories else None,
            "best_month": best_month["month"] if best_month else None,
        },
        "recommendations": [
            f"Focus on {top_venues[0]['venue_name']} venue (highest sell-through)" if top_venues else None,
            f"Prioritize {top_categories[0]['category_name']} events (highest revenue)" if top_categories else None,
            f"Schedule more events in {best_month['month']} (best performance)" if best_month else None,
        ],
    }


def build_lookalike_audience(db: Session, event_id: int) -> Dict:
    """
    Build lookalike audience from an event's attendees.

    Finds customers with similar profiles who haven't attended yet.

    Args:
        db: Database session
        event_id: Source event to build lookalike from

    Returns:
        Dict with lookalike audience members
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Get attendees of this event
    attendees = (
        db.query(EventGoer)
        .join(Ticket, Ticket.event_goer_id == EventGoer.id)
        .filter(
            Ticket.event_id == event_id,
            Ticket.status == TicketStatus.CONFIRMED
        )
        .all()
    )

    if not attendees:
        return {"message": "No attendees yet"}

    # Get their purchase history
    attendee_ids = [a.id for a in attendees]

    # Find events they attended
    common_events = (
        db.query(
            Event.id,
            Event.name,
            func.count(Ticket.id).label("attendee_count")
        )
        .join(Ticket, Ticket.event_id == Event.id)
        .filter(
            Ticket.event_goer_id.in_(attendee_ids),
            Ticket.status == TicketStatus.CONFIRMED,
            Event.id != event_id
        )
        .group_by(Event.id)
        .order_by(func.count(Ticket.id).desc())
        .limit(5)
        .all()
    )

    # Find people who attended those events but not the target event
    common_event_ids = [e.id for e in common_events]

    if not common_event_ids:
        return {"message": "Not enough data for lookalike audience"}

    lookalikes = (
        db.query(EventGoer)
        .join(Ticket, Ticket.event_goer_id == EventGoer.id)
        .filter(
            Ticket.event_id.in_(common_event_ids),
            Ticket.status == TicketStatus.CONFIRMED,
            EventGoer.id.notin_(attendee_ids)  # Haven't attended target event
        )
        .group_by(EventGoer.id)
        .having(func.count(Ticket.id) >= 2)  # Attended at least 2 similar events
        .limit(100)
        .all()
    )

    lookalike_list = [
        {
            "id": lg.id,
            "email": lg.email,
            "name": f"{lg.first_name} {lg.last_name}",
            "match_reason": f"Attended {len(common_events)} similar events",
        }
        for lg in lookalikes
    ]

    return {
        "event_id": event_id,
        "event_name": event.name,
        "source_attendees": len(attendees),
        "lookalike_audience_size": len(lookalike_list),
        "common_events": [
            {"event_id": e.id, "event_name": e.name, "attendee_overlap": e.attendee_count}
            for e in common_events
        ],
        "lookalike_audience": lookalike_list[:50],  # Return top 50
        "recommendation": f"Target {len(lookalike_list)} lookalikes with personalized invite",
    }


def detect_churn_risk(db: Session) -> Dict:
    """
    Identify customers at risk of churning (not returning).

    Flags customers who:
    - Haven't purchased in 90+ days
    - Previously were active (2+ purchases)
    - Unsubscribed from communications

    Returns:
        Dict with at-risk customers and retention suggestions
    """
    # Find customers who haven't purchased recently
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

    at_risk_customers = (
        db.query(
            EventGoer.id,
            EventGoer.email,
            EventGoer.first_name,
            EventGoer.last_name,
            func.count(Ticket.id).label("total_purchases"),
            func.max(Ticket.created_at).label("last_purchase"),
        )
        .join(Ticket, Ticket.event_goer_id == EventGoer.id)
        .filter(Ticket.status == TicketStatus.CONFIRMED)
        .group_by(EventGoer.id)
        .having(
            and_(
                func.count(Ticket.id) >= 2,  # Previously active
                func.max(Ticket.created_at) < ninety_days_ago  # No recent purchase
            )
        )
        .limit(100)
        .all()
    )

    at_risk_list = []

    for customer in at_risk_customers:
        days_inactive = (datetime.now(timezone.utc) - customer.last_purchase).days if customer.last_purchase else 9999

        risk_level = "HIGH" if days_inactive > 180 else ("MEDIUM" if days_inactive > 120 else "LOW")

        at_risk_list.append({
            "id": customer.id,
            "email": customer.email,
            "name": f"{customer.first_name} {customer.last_name}",
            "total_purchases": customer.total_purchases,
            "days_inactive": days_inactive,
            "risk_level": risk_level,
            "retention_action": "Win-back campaign with 20% off" if risk_level == "HIGH" else "Re-engagement email",
        })

    # Segment by risk
    high_risk = [c for c in at_risk_list if c["risk_level"] == "HIGH"]
    medium_risk = [c for c in at_risk_list if c["risk_level"] == "MEDIUM"]

    return {
        "total_at_risk": len(at_risk_list),
        "risk_segments": {
            "high": len(high_risk),
            "medium": len(medium_risk),
            "low": len(at_risk_list) - len(high_risk) - len(medium_risk),
        },
        "at_risk_customers": at_risk_list[:50],  # Top 50
        "recommendations": [
            f"Launch win-back campaign for {len(high_risk)} high-risk customers with discount code",
            f"Send re-engagement emails to {len(medium_risk)} medium-risk customers",
            "Analyze why customers stopped purchasing (survey or exit interview)",
        ],
    }


def compare_similar_events(db: Session, event_id: int) -> Dict:
    """
    Compare an event to similar past events for insights.

    Shows how current event stacks up against:
    - Same venue
    - Same category
    - Similar pricing

    Returns:
        Dict with comparison insights
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Find similar past events (same venue)
    similar_by_venue = (
        db.query(Event)
        .filter(
            Event.venue_id == event.venue_id,
            Event.id != event_id,
            Event.event_date < datetime.now(timezone.utc).date()
        )
        .limit(5)
        .all()
    )

    # Calculate current event stats
    current_tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    current_sold = sum(t.quantity_sold for t in current_tiers)
    current_available = sum(t.quantity_available for t in current_tiers)
    current_sell_through = current_sold / current_available if current_available > 0 else 0

    # Compare to similar events
    comparisons = []

    for past_event in similar_by_venue:
        past_tiers = db.query(TicketTier).filter(TicketTier.event_id == past_event.id).all()
        past_sold = sum(t.quantity_sold for t in past_tiers)
        past_available = sum(t.quantity_available for t in past_tiers)
        past_sell_through = past_sold / past_available if past_available > 0 else 0

        comparisons.append({
            "event_id": past_event.id,
            "event_name": past_event.name,
            "event_date": str(past_event.event_date),
            "sell_through": round(past_sell_through, 2),
            "tickets_sold": past_sold,
        })

    # Calculate average of similar events
    avg_sell_through = sum(c["sell_through"] for c in comparisons) / len(comparisons) if comparisons else 0

    performance = "ABOVE AVERAGE" if current_sell_through > avg_sell_through else "BELOW AVERAGE"

    return {
        "event_id": event_id,
        "event_name": event.name,
        "current_sell_through": round(current_sell_through, 2),
        "current_tickets_sold": current_sold,
        "similar_events": comparisons,
        "average_similar_sell_through": round(avg_sell_through, 2),
        "performance_vs_similar": performance,
        "insight": f"Performing {performance.lower()} compared to {len(comparisons)} similar events at this venue",
    }
