"""
Dynamic Pricing Service

Automatically adjusts ticket prices based on demand, time, and inventory.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import TicketTier, Event, Ticket, TicketStatus


def calculate_demand_score(tier: TicketTier, db: Session) -> float:
    """
    Calculate demand score (0-1) based on sell-through rate and velocity.

    Returns:
        float: Score from 0 (low demand) to 1 (high demand)
    """
    if tier.quantity_available == 0:
        return 1.0  # Sold out

    sell_through = tier.quantity_sold / tier.quantity_available

    # Calculate velocity (tickets sold per day)
    tickets_last_24h = (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.ticket_tier_id == tier.id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.purchased_at >= datetime.now(timezone.utc) - timedelta(days=1),
        )
        .scalar() or 0
    )

    # Velocity factor (normalized to 0-1)
    # Assume 10 tickets/day is high velocity
    velocity_factor = min(tickets_last_24h / 10, 1.0)

    # Weighted combination: 70% sell-through, 30% velocity
    demand_score = (sell_through * 0.7) + (velocity_factor * 0.3)

    return min(demand_score, 1.0)


def calculate_time_pressure_multiplier(event: Event) -> float:
    """
    Calculate price multiplier based on time until event.

    Returns:
        float: Multiplier from 1.0 (far away) to 1.5 (very soon)
    """
    try:
        event_datetime = datetime.strptime(
            f"{event.event_date} {event.event_time}",
            "%Y-%m-%d %H:%M"
        )
        event_datetime = event_datetime.replace(tzinfo=timezone.utc)
    except:
        return 1.0

    days_until_event = (event_datetime - datetime.now(timezone.utc)).days

    if days_until_event < 0:
        return 1.0  # Event passed
    elif days_until_event <= 1:
        return 1.5  # Tomorrow or today - high urgency
    elif days_until_event <= 3:
        return 1.3  # Within 3 days
    elif days_until_event <= 7:
        return 1.2  # Within a week
    elif days_until_event <= 14:
        return 1.1  # Within 2 weeks
    else:
        return 1.0  # More than 2 weeks away


def suggest_price_adjustment(
    tier: TicketTier,
    db: Session,
    event: Optional[Event] = None,
) -> dict:
    """
    Suggest price adjustment for a tier based on demand and time pressure.

    Returns:
        dict with suggested_price, reason, demand_score, time_multiplier
    """
    if not tier.dynamic_pricing_enabled:
        return {
            "dynamic_pricing_enabled": False,
            "current_price": tier.price,
            "message": "Dynamic pricing not enabled for this tier",
        }

    # Get base price (fallback to current price if not set)
    base_price = tier.base_price or tier.price

    # Calculate demand score
    demand_score = calculate_demand_score(tier, db)

    # Get event if not provided
    if not event:
        event = db.query(Event).filter(Event.id == tier.event_id).first()

    # Calculate time pressure
    time_multiplier = calculate_time_pressure_multiplier(event) if event else 1.0

    # Price adjustment formula:
    # - Base price * (1 + demand_score * 0.5) * time_multiplier
    # - This means: up to 50% increase from demand, plus time multiplier
    demand_multiplier = 1 + (demand_score * 0.5)
    suggested_price = int(base_price * demand_multiplier * time_multiplier)

    # Clamp to min/max if set
    if tier.min_price is not None:
        suggested_price = max(suggested_price, tier.min_price)
    if tier.max_price is not None:
        suggested_price = min(suggested_price, tier.max_price)

    # Determine reason
    reasons = []
    if demand_score > 0.8:
        reasons.append("high demand")
    elif demand_score > 0.5:
        reasons.append("moderate demand")

    if time_multiplier > 1.0:
        days_away = (
            datetime.strptime(f"{event.event_date} {event.event_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            - datetime.now(timezone.utc)
        ).days
        if days_away <= 1:
            reasons.append("event very soon")
        else:
            reasons.append(f"event in {days_away} days")

    reason = ", ".join(reasons) if reasons else "baseline pricing"

    return {
        "dynamic_pricing_enabled": True,
        "current_price": tier.price,
        "base_price": base_price,
        "suggested_price": suggested_price,
        "price_change": suggested_price - tier.price,
        "price_change_percent": round(((suggested_price - tier.price) / tier.price) * 100, 1) if tier.price > 0 else 0,
        "demand_score": round(demand_score, 2),
        "time_multiplier": round(time_multiplier, 2),
        "reason": reason,
        "min_price": tier.min_price,
        "max_price": tier.max_price,
        "should_update": abs(suggested_price - tier.price) >= 100,  # Update if change >= $1
    }


def apply_price_adjustment(
    db: Session,
    tier_id: int,
    new_price: int,
    reason: str = "dynamic_pricing",
) -> dict:
    """
    Apply a price adjustment to a tier.

    Args:
        db: Database session
        tier_id: Tier ID
        new_price: New price in cents
        reason: Reason for update

    Returns:
        dict with update details
    """
    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

    if not tier:
        return {"error": "Tier not found"}

    if not tier.dynamic_pricing_enabled:
        return {"error": "Dynamic pricing not enabled for this tier"}

    # Validate price bounds
    if tier.min_price is not None and new_price < tier.min_price:
        return {"error": f"Price ${new_price/100:.2f} below minimum ${tier.min_price/100:.2f}"}

    if tier.max_price is not None and new_price > tier.max_price:
        return {"error": f"Price ${new_price/100:.2f} above maximum ${tier.max_price/100:.2f}"}

    old_price = tier.price
    tier.price = new_price
    tier.last_price_update = datetime.now(timezone.utc)
    tier.price_update_reason = reason

    db.commit()
    db.refresh(tier)

    return {
        "success": True,
        "tier_id": tier.id,
        "tier_name": tier.name,
        "old_price": old_price,
        "new_price": new_price,
        "price_change": new_price - old_price,
        "price_change_percent": round(((new_price - old_price) / old_price) * 100, 1) if old_price > 0 else 0,
        "reason": reason,
        "updated_at": tier.last_price_update.isoformat(),
    }


def auto_adjust_event_pricing(
    db: Session,
    event_id: int,
    dry_run: bool = False,
) -> dict:
    """
    Automatically adjust pricing for all dynamic tiers in an event.

    Args:
        db: Database session
        event_id: Event ID
        dry_run: If True, only suggest changes without applying them

    Returns:
        dict with results for each tier
    """
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        return {"error": "Event not found"}

    tiers = (
        db.query(TicketTier)
        .filter(
            TicketTier.event_id == event_id,
            TicketTier.dynamic_pricing_enabled == True,
        )
        .all()
    )

    if not tiers:
        return {
            "event_id": event_id,
            "event_name": event.name,
            "message": "No tiers with dynamic pricing enabled",
            "tiers": [],
        }

    results = []
    for tier in tiers:
        suggestion = suggest_price_adjustment(tier, db, event)

        if dry_run or not suggestion.get("should_update"):
            results.append({
                "tier_id": tier.id,
                "tier_name": tier.name,
                "action": "no_change" if not suggestion.get("should_update") else "suggestion",
                **suggestion,
            })
        else:
            # Apply the adjustment
            update_result = apply_price_adjustment(
                db,
                tier.id,
                suggestion["suggested_price"],
                reason=f"auto_adjust: {suggestion['reason']}",
            )
            results.append({
                "tier_id": tier.id,
                "tier_name": tier.name,
                "action": "updated",
                **update_result,
            })

    return {
        "event_id": event_id,
        "event_name": event.name,
        "dry_run": dry_run,
        "tiers_processed": len(results),
        "tiers": results,
    }


def enable_dynamic_pricing(
    db: Session,
    tier_id: int,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
) -> dict:
    """
    Enable dynamic pricing for a tier.

    Args:
        db: Database session
        tier_id: Tier ID
        min_price: Minimum allowed price in cents (optional)
        max_price: Maximum allowed price in cents (optional)

    Returns:
        dict with updated tier info
    """
    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

    if not tier:
        return {"error": "Tier not found"}

    # Set base price to current price if not already set
    if tier.base_price is None:
        tier.base_price = tier.price

    tier.dynamic_pricing_enabled = True

    if min_price is not None:
        tier.min_price = min_price

    if max_price is not None:
        tier.max_price = max_price

    db.commit()
    db.refresh(tier)

    return {
        "success": True,
        "tier_id": tier.id,
        "tier_name": tier.name,
        "dynamic_pricing_enabled": True,
        "base_price": tier.base_price,
        "current_price": tier.price,
        "min_price": tier.min_price,
        "max_price": tier.max_price,
    }


def disable_dynamic_pricing(db: Session, tier_id: int) -> dict:
    """
    Disable dynamic pricing for a tier and reset to base price.

    Args:
        db: Database session
        tier_id: Tier ID

    Returns:
        dict with updated tier info
    """
    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

    if not tier:
        return {"error": "Tier not found"}

    tier.dynamic_pricing_enabled = False

    # Optionally reset to base price
    if tier.base_price is not None:
        tier.price = tier.base_price
        tier.last_price_update = datetime.now(timezone.utc)
        tier.price_update_reason = "disabled_dynamic_pricing"

    db.commit()
    db.refresh(tier)

    return {
        "success": True,
        "tier_id": tier.id,
        "tier_name": tier.name,
        "dynamic_pricing_enabled": False,
        "price": tier.price,
        "base_price": tier.base_price,
    }
