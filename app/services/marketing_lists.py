"""
Marketing List Service

Handles creation, management, and preview of reusable audience segments.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import func, and_, or_, text
from sqlalchemy.orm import Session, joinedload

from app.models import (
    EventGoer, MarketingList, CustomerPreference, Ticket, TicketTier,
    TicketStatus, event_category_link,
)


def apply_segment_filters(query, filters: Dict[str, Any]) -> tuple:
    """
    Apply segment filters to EventGoer query.

    Returns: (filtered_query, filter_description)
    """
    descriptions = []

    # VIP status
    if filters.get("is_vip"):
        query = query.join(CustomerPreference).filter(CustomerPreference.is_vip == True)
        descriptions.append("VIP customers")

    # VIP tier
    if filters.get("vip_tier"):
        query = query.join(CustomerPreference).filter(CustomerPreference.vip_tier == filters["vip_tier"])
        descriptions.append(f"VIP tier: {filters['vip_tier']}")

    # Minimum events attended
    if filters.get("min_events"):
        min_events = filters["min_events"]
        query = query.join(CustomerPreference).filter(CustomerPreference.total_events_attended >= min_events)
        descriptions.append(f"Attended {min_events}+ events")

    # Maximum events attended
    if filters.get("max_events"):
        max_events = filters["max_events"]
        query = query.join(CustomerPreference).filter(CustomerPreference.total_events_attended <= max_events)
        descriptions.append(f"Attended ≤{max_events} events")

    # Minimum lifetime spend
    if filters.get("min_spent_cents"):
        min_spent = filters["min_spent_cents"]
        query = query.join(CustomerPreference).filter(CustomerPreference.total_spent_cents >= min_spent)
        descriptions.append(f"Spent ${min_spent/100:.2f}+")

    # Maximum lifetime spend
    if filters.get("max_spent_cents"):
        max_spent = filters["max_spent_cents"]
        query = query.join(CustomerPreference).filter(CustomerPreference.total_spent_cents <= max_spent)
        descriptions.append(f"Spent ≤${max_spent/100:.2f}")

    # Event category interest
    if filters.get("category_ids"):
        category_ids = filters["category_ids"]
        # Find event goers who attended events in these categories
        subquery = (
            query.session.query(EventGoer.id)
            .join(Ticket)
            .join(TicketTier)
            .join(event_category_link, event_category_link.c.event_id == TicketTier.event_id)
            .filter(event_category_link.c.category_id.in_(category_ids))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(subquery))
        descriptions.append(f"Interested in {len(category_ids)} categories")

    # Specific event attendees
    if filters.get("event_id"):
        event_id = filters["event_id"]
        subquery = (
            query.session.query(EventGoer.id)
            .join(Ticket)
            .join(TicketTier)
            .filter(TicketTier.event_id == event_id)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(subquery))
        descriptions.append(f"Attended event #{event_id}")

    # Birthday this month
    if filters.get("has_birthday_this_month"):
        current_month = datetime.now(timezone.utc).month
        query = query.filter(func.extract('month', EventGoer.birthdate) == current_month)
        query = query.filter(EventGoer.birthday_opt_in == True)
        descriptions.append("Birthday this month (opted-in)")

    # Last purchase recency
    if filters.get("last_purchase_days_ago"):
        days_ago = filters["last_purchase_days_ago"]
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
        query = query.join(CustomerPreference).filter(CustomerPreference.last_interaction_date >= cutoff_date)
        descriptions.append(f"Purchased within {days_ago} days")

    # First-time buyers
    if filters.get("first_time_buyers"):
        query = query.join(CustomerPreference).filter(CustomerPreference.total_events_attended == 1)
        descriptions.append("First-time buyers")

    # No-show customers (bought tickets but never checked in)
    if filters.get("no_show"):
        # Has tickets but none are checked in
        has_tickets = (
            query.session.query(EventGoer.id)
            .join(Ticket)
            .filter(Ticket.status == TicketStatus.PAID)
            .distinct()
        )
        has_checkins = (
            query.session.query(EventGoer.id)
            .join(Ticket)
            .filter(Ticket.status == TicketStatus.CHECKED_IN)
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(has_tickets))
        query = query.filter(~EventGoer.id.in_(has_checkins))
        descriptions.append("Never checked in")

    # Marketing opt-in status
    if filters.get("marketing_opt_in") is not None:
        query = query.filter(EventGoer.marketing_opt_in == filters["marketing_opt_in"])
        descriptions.append("Marketing opt-in" if filters["marketing_opt_in"] else "Not opted-in to marketing")

    # Email opt-in status
    if filters.get("email_opt_in") is not None:
        query = query.filter(EventGoer.email_opt_in == filters["email_opt_in"])
        descriptions.append("Email opt-in" if filters["email_opt_in"] else "No email opt-in")

    # SMS opt-in status
    if filters.get("sms_opt_in") is not None:
        query = query.filter(EventGoer.sms_opt_in == filters["sms_opt_in"])
        descriptions.append("SMS opt-in" if filters["sms_opt_in"] else "No SMS opt-in")

    # Preferred language
    if filters.get("preferred_language"):
        lang = filters["preferred_language"]
        query = query.join(CustomerPreference).filter(CustomerPreference.preferred_language == lang)
        descriptions.append(f"Language: {lang}")

    # Dormant customers (haven't purchased in X days)
    if filters.get("dormant_days"):
        days = filters["dormant_days"]
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.join(CustomerPreference).filter(CustomerPreference.last_interaction_date < cutoff_date)
        descriptions.append(f"Dormant {days}+ days")

    filter_summary = " AND ".join(descriptions) if descriptions else "All opted-in customers"

    return query, filter_summary


def create_marketing_list(
    db: Session,
    name: str,
    segment_filters: Dict[str, Any],
    description: Optional[str] = None,
) -> dict:
    """Create a new marketing list."""
    # Check if name already exists
    existing = db.query(MarketingList).filter(MarketingList.name == name).first()
    if existing:
        return {"error": f"Marketing list '{name}' already exists"}

    # Create the list
    marketing_list = MarketingList(
        name=name,
        description=description,
        segment_filters=json.dumps(segment_filters),
    )
    db.add(marketing_list)
    db.commit()
    db.refresh(marketing_list)

    # Preview the list to get count
    preview = preview_marketing_list(db, marketing_list.id, limit=0)

    return {
        "id": marketing_list.id,
        "name": marketing_list.name,
        "description": marketing_list.description,
        "segment_filters": segment_filters,
        "current_count": preview["total_count"],
        "filter_description": preview["filter_description"],
        "created_at": marketing_list.created_at.isoformat(),
    }


def get_marketing_list(db: Session, list_id: int) -> dict:
    """Get a marketing list by ID."""
    marketing_list = db.query(MarketingList).filter(MarketingList.id == list_id).first()

    if not marketing_list:
        return {"error": "Marketing list not found"}

    # Parse filters
    filters = json.loads(marketing_list.segment_filters)

    # Get current count
    preview = preview_marketing_list(db, list_id, limit=0)

    return {
        "id": marketing_list.id,
        "name": marketing_list.name,
        "description": marketing_list.description,
        "segment_filters": filters,
        "current_count": preview["total_count"],
        "filter_description": preview["filter_description"],
        "created_at": marketing_list.created_at.isoformat(),
        "updated_at": marketing_list.updated_at.isoformat(),
    }


def list_marketing_lists(db: Session, limit: int = 50, offset: int = 0) -> dict:
    """List all marketing lists with current counts."""
    lists = (
        db.query(MarketingList)
        .order_by(MarketingList.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total_count = db.query(func.count(MarketingList.id)).scalar()

    results = []
    for lst in lists:
        filters = json.loads(lst.segment_filters)
        preview = preview_marketing_list(db, lst.id, limit=0)

        results.append({
            "id": lst.id,
            "name": lst.name,
            "description": lst.description,
            "segment_filters": filters,
            "current_count": preview["total_count"],
            "filter_description": preview["filter_description"],
            "created_at": lst.created_at.isoformat(),
            "updated_at": lst.updated_at.isoformat(),
        })

    return {
        "lists": results,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


def preview_marketing_list(
    db: Session,
    list_id: int,
    limit: int = 10,
) -> dict:
    """
    Preview who's in a marketing list.
    Returns count + sample of customers.
    """
    marketing_list = db.query(MarketingList).filter(MarketingList.id == list_id).first()

    if not marketing_list:
        return {"error": "Marketing list not found"}

    # Parse filters
    filters = json.loads(marketing_list.segment_filters)

    # Start with base query - all event goers
    query = db.query(EventGoer)

    # Apply segment filters
    query, filter_description = apply_segment_filters(query, filters)

    # Get total count
    total_count = query.count()

    # Get sample customers
    sample_customers = []
    if limit > 0:
        customers = query.limit(limit).all()

        for customer in customers:
            # Get customer stats
            pref = db.query(CustomerPreference).filter(CustomerPreference.event_goer_id == customer.id).first()

            sample_customers.append({
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "is_vip": pref.is_vip if pref else False,
                "total_spent_cents": pref.total_spent_cents if pref else 0,
                "total_events_attended": pref.total_events_attended if pref else 0,
                "marketing_opt_in": customer.marketing_opt_in,
                "email_opt_in": customer.email_opt_in,
                "sms_opt_in": customer.sms_opt_in,
            })

    return {
        "list_id": list_id,
        "list_name": marketing_list.name,
        "filter_description": filter_description,
        "total_count": total_count,
        "sample_customers": sample_customers,
        "segment_filters": filters,
    }


def update_marketing_list(
    db: Session,
    list_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    segment_filters: Optional[Dict[str, Any]] = None,
) -> dict:
    """Update a marketing list."""
    marketing_list = db.query(MarketingList).filter(MarketingList.id == list_id).first()

    if not marketing_list:
        return {"error": "Marketing list not found"}

    # Check for name conflicts
    if name and name != marketing_list.name:
        existing = db.query(MarketingList).filter(MarketingList.name == name).first()
        if existing:
            return {"error": f"Marketing list '{name}' already exists"}
        marketing_list.name = name

    if description is not None:
        marketing_list.description = description

    if segment_filters is not None:
        marketing_list.segment_filters = json.dumps(segment_filters)

    marketing_list.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(marketing_list)

    return get_marketing_list(db, list_id)


def delete_marketing_list(db: Session, list_id: int) -> dict:
    """Delete a marketing list."""
    marketing_list = db.query(MarketingList).filter(MarketingList.id == list_id).first()

    if not marketing_list:
        return {"error": "Marketing list not found"}

    list_name = marketing_list.name
    db.delete(marketing_list)
    db.commit()

    return {
        "success": True,
        "message": f"Marketing list '{list_name}' deleted successfully",
    }


def get_list_recipients(
    db: Session,
    list_id: int,
    channel: Optional[str] = None,
) -> List[EventGoer]:
    """
    Get all recipients for a marketing list.
    Optionally filter by channel opt-in status.

    Args:
        db: Database session
        list_id: Marketing list ID
        channel: Optional channel filter ("email" or "sms")

    Returns:
        List of EventGoer objects who match the filters
    """
    marketing_list = db.query(MarketingList).filter(MarketingList.id == list_id).first()

    if not marketing_list:
        return []

    # Parse filters
    filters = json.loads(marketing_list.segment_filters)

    # Start with base query
    query = db.query(EventGoer)

    # Apply segment filters
    query, _ = apply_segment_filters(query, filters)

    # Filter by channel opt-in if specified
    if channel == "email":
        query = query.filter(EventGoer.email_opt_in == True)
    elif channel == "sms":
        query = query.filter(EventGoer.sms_opt_in == True)

    return query.all()
