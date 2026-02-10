"""
Predictive Analytics Engine

Pure-Python statistical methods for demand forecasting, dynamic pricing,
churn prediction (RFM analysis), and event recommendations.
No external ML libraries required.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc

from app.models import (
    Event,
    TicketTier,
    Ticket,
    TicketStatus,
    EventGoer,
    CustomerPreference,
    PageView,
    WaitlistEntry,
    WaitlistStatus,
    PromoCode,
    EventCategory,
    event_category_link,
)


# ============== Helpers ==============


def _assign_quartiles(values: list[float], reverse: bool = False) -> list[int]:
    """Assign quartile scores 1-4. reverse=True means lower value gets higher score."""
    n = len(values)
    if n == 0:
        return []
    sorted_unique = sorted(set(values))
    rank_map = {}
    total = max(len(sorted_unique) - 1, 1)
    for i, v in enumerate(sorted_unique):
        percentile = i / total
        if reverse:
            percentile = 1 - percentile
        if percentile >= 0.75:
            rank_map[v] = 4
        elif percentile >= 0.50:
            rank_map[v] = 3
        elif percentile >= 0.25:
            rank_map[v] = 2
        else:
            rank_map[v] = 1
    return [rank_map[v] for v in values]


def _min_max_normalize(values: list[float]) -> list[float]:
    """Normalize values to 0-1 range."""
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    spread = hi - lo
    if spread == 0:
        return [0.5] * len(values)
    return [(v - lo) / spread for v in values]


def _get_reengagement_suggestion(segment: str, pref: Optional[CustomerPreference]) -> str:
    fav_types = []
    if pref and pref.favorite_event_types:
        try:
            fav_types = json.loads(pref.favorite_event_types)
        except (json.JSONDecodeError, TypeError):
            pass
    type_str = f" for {fav_types[0]} events" if fav_types else ""

    if segment == "at_risk":
        return f"Send a personalized discount code{type_str}. This customer has high lifetime value."
    elif segment == "lapsed":
        return f"Send a 'we miss you' campaign{type_str} with a special offer to re-engage."
    else:
        return f"Consider a win-back campaign with a significant discount{type_str}."


def _build_recommendation_reason(
    content_score: float, collab_score: float, popularity_score: float, event
) -> str:
    parts = []
    if content_score > 0.5:
        cats = [c.name for c in event.categories] if event.categories else []
        if cats:
            parts.append(f"Matches interest in {', '.join(cats[:2])}")
    if collab_score > 0.3:
        parts.append("Similar attendees are buying tickets")
    if popularity_score > 0.5:
        parts.append("Trending with high demand")
    if not parts:
        parts.append("Upcoming event worth considering")
    return ". ".join(parts) + "."


# ============== Feature 1: Demand Forecasting ==============


def predict_demand(db: Session, event_id: int) -> dict:
    """Predict demand for an event: sell-out probability, projected date, demand score."""
    now = datetime.now(timezone.utc)

    event = (
        db.query(Event)
        .options(joinedload(Event.categories), joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        return {"error": "Event not found"}

    # Check if past event
    try:
        event_dt = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
        event_dt = event_dt.replace(tzinfo=timezone.utc)
        if event_dt < now:
            return {"error": "This event has already occurred. Demand prediction is only available for upcoming events."}
        days_until = max((event_dt - now).days, 0)
    except ValueError:
        days_until = 30

    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    total_available = sum(t.quantity_available for t in tiers)
    total_sold = sum(t.quantity_sold for t in tiers)
    total_remaining = max(total_available - total_sold, 0)

    if total_available == 0:
        return {
            "event_id": event.id,
            "event_name": event.name,
            "demand_score": 0,
            "sellout_probability_percent": 0,
            "projected_sellout_date": None,
            "insufficient_data": True,
            "message": "No ticket tiers configured for this event.",
        }

    # Earliest purchase for velocity
    earliest_purchase = (
        db.query(sqlfunc.min(Ticket.purchased_at))
        .join(TicketTier)
        .filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
        )
        .scalar()
    )

    # Waitlist size
    waitlist_count = (
        db.query(sqlfunc.count(WaitlistEntry.id))
        .filter(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.status == WaitlistStatus.WAITING,
        )
        .scalar()
        or 0
    )

    # Page views: last 3 days vs days 4-7
    views_recent = (
        db.query(sqlfunc.count(PageView.id))
        .filter(
            PageView.event_id == event_id,
            PageView.page == "detail",
            PageView.created_at >= now - timedelta(days=3),
        )
        .scalar()
        or 0
    )
    views_prior = (
        db.query(sqlfunc.count(PageView.id))
        .filter(
            PageView.event_id == event_id,
            PageView.page == "detail",
            PageView.created_at >= now - timedelta(days=7),
            PageView.created_at < now - timedelta(days=3),
        )
        .scalar()
        or 0
    )

    # Historical comparator — same categories or venue
    category_ids = [c.id for c in event.categories] if event.categories else []
    past_filters = [
        Event.id != event_id,
        Event.event_date < now.strftime("%Y-%m-%d"),
    ]
    if category_ids:
        past_with_cat = (
            db.query(event_category_link.c.event_id)
            .filter(event_category_link.c.category_id.in_(category_ids))
            .distinct()
            .subquery()
        )
        past_filters.append(Event.id.in_(db.query(past_with_cat.c.event_id)))
    elif event.venue_id:
        past_filters.append(Event.venue_id == event.venue_id)

    hist = (
        db.query(
            sqlfunc.sum(TicketTier.quantity_sold).label("sold"),
            sqlfunc.sum(TicketTier.quantity_available).label("avail"),
            sqlfunc.count(sqlfunc.distinct(Event.id)).label("count"),
        )
        .join(Event, TicketTier.event_id == Event.id)
        .filter(*past_filters)
        .first()
    )
    hist_sold = int(hist.sold or 0) if hist else 0
    hist_avail = max(int(hist.avail or 1), 1) if hist else 1
    hist_count = int(hist.count or 0) if hist else 0
    hist_sell_through = hist_sold / hist_avail

    # Compute signals
    sell_through = total_sold / max(total_available, 1)

    days_on_sale = 1
    current_velocity = 0.0
    if earliest_purchase:
        ep = earliest_purchase
        if ep.tzinfo is None:
            ep = ep.replace(tzinfo=timezone.utc)
        days_on_sale = max((now - ep).days, 1)
        current_velocity = total_sold / days_on_sale

    velocity_ratio = min(sell_through / max(hist_sell_through, 0.01), 2.0)
    waitlist_pressure = min(waitlist_count / max(total_available, 1), 1.0)
    view_trend = (views_recent + 1) / max(views_prior + 1, 1)
    view_trend_normalized = min(view_trend / 2.0, 1.0)
    time_scarcity = 1.0 / max(days_until, 1) if days_until <= 30 else 0.0
    time_scarcity_normalized = min(time_scarcity * 10, 1.0)

    # Composite demand score (0-100)
    demand_score = (
        sell_through * 30
        + min(velocity_ratio / 2.0, 1.0) * 25
        + waitlist_pressure * 15
        + view_trend_normalized * 15
        + time_scarcity_normalized * 15
    )
    demand_score = max(0, min(100, round(demand_score)))

    # Sell-out probability via logistic function
    k = 0.1
    sellout_probability = round(100 / (1 + math.exp(-k * (demand_score - 50))), 1)

    # Projected sell-out date
    projected_sellout_date = None
    if current_velocity > 0 and total_remaining > 0:
        days_to_sellout = total_remaining / current_velocity
        projected = now + timedelta(days=days_to_sellout)
        if days_until == 0 or projected <= event_dt:
            projected_sellout_date = projected.strftime("%Y-%m-%d")

    # Sell-out pace targets
    required_per_day = round(total_remaining / max(days_until, 1), 2) if total_remaining > 0 else 0
    on_track = current_velocity >= required_per_day if required_per_day > 0 else True
    if required_per_day > 0 and current_velocity > 0:
        pace_ratio = round(current_velocity / required_per_day, 2)
    else:
        pace_ratio = 0.0

    # Per-tier pace breakdown
    tier_pace = []
    for t in tiers:
        tier_remaining = max(t.quantity_available - t.quantity_sold, 0)
        tier_required = round(tier_remaining / max(days_until, 1), 2) if tier_remaining > 0 else 0
        # Tier-level velocity from actual purchases
        tier_sold_count = (
            db.query(sqlfunc.count(Ticket.id))
            .filter(
                Ticket.ticket_tier_id == t.id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            )
            .scalar()
            or 0
        )
        tier_velocity = round(tier_sold_count / max(days_on_sale, 1), 2)
        tier_on_track = tier_velocity >= tier_required if tier_required > 0 else True
        tier_pace.append({
            "tier_id": t.id,
            "tier_name": t.name,
            "sold": t.quantity_sold,
            "remaining": tier_remaining,
            "capacity": t.quantity_available,
            "required_per_day": tier_required,
            "current_per_day": tier_velocity,
            "on_track": tier_on_track,
        })

    return {
        "event_id": event.id,
        "event_name": event.name,
        "event_date": event.event_date,
        "demand_score": demand_score,
        "sellout_probability_percent": sellout_probability,
        "projected_sellout_date": projected_sellout_date,
        "inventory": {
            "total_available": total_available,
            "total_sold": total_sold,
            "total_remaining": total_remaining,
            "sell_through_percent": round(sell_through * 100, 1),
        },
        "velocity": {
            "tickets_per_day": round(current_velocity, 2),
            "days_on_sale": days_on_sale,
        },
        "sellout_pace": {
            "days_until_event": days_until,
            "required_per_day": required_per_day,
            "current_per_day": round(current_velocity, 2),
            "pace_ratio": pace_ratio,
            "on_track": on_track,
            "message": (
                f"Selling {round(current_velocity, 1)}/day — need {required_per_day}/day to sell out by {event.event_date}."
                if not on_track and required_per_day > 0
                else f"On track at {round(current_velocity, 1)}/day (need {required_per_day}/day)."
                if on_track and required_per_day > 0
                else "No remaining inventory."
            ),
            "tiers": tier_pace,
        },
        "signals": {
            "waitlist_size": waitlist_count,
            "page_views_last_3_days": views_recent,
            "page_views_prior_4_days": views_prior,
            "view_trend_ratio": round(view_trend, 2),
            "days_until_event": days_until,
        },
        "historical_comparison": {
            "similar_events_count": hist_count,
            "avg_sell_through_percent": round(hist_sell_through * 100, 1),
        },
    }


# ============== Feature 2: Dynamic Pricing Suggestions ==============


def get_pricing_suggestions(db: Session, event_id: int) -> dict:
    """Get dynamic pricing suggestions for each tier. Suggestions only — does NOT change prices."""
    now = datetime.now(timezone.utc)

    event = (
        db.query(Event)
        .options(joinedload(Event.categories))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        return {"error": "Event not found"}

    try:
        event_dt = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
        event_dt = event_dt.replace(tzinfo=timezone.utc)
        if event_dt < now:
            return {"error": "This event has already occurred. Pricing suggestions are only for upcoming events."}
        days_until = max((event_dt - now).days, 0)
    except ValueError:
        days_until = 30

    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    if not tiers:
        return {"error": "No ticket tiers found for this event."}

    # Price elasticity from promo code usage
    promo_tickets = (
        db.query(sqlfunc.count(Ticket.id))
        .join(TicketTier)
        .filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.discount_amount_cents > 0,
        )
        .scalar()
        or 0
    )
    total_event_tickets = (
        db.query(sqlfunc.count(Ticket.id))
        .join(TicketTier)
        .filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
        )
        .scalar()
        or 0
    )
    promo_ratio = promo_tickets / max(total_event_tickets, 1)

    if promo_ratio > 0.4:
        elasticity_level = "high"
        elasticity_text = "Customers are price-sensitive — many used promo codes."
    elif promo_ratio > 0.15:
        elasticity_level = "medium"
        elasticity_text = "Moderate price sensitivity — some promo code usage."
    else:
        elasticity_level = "low"
        elasticity_text = "Customers show low price sensitivity — room for increases."

    # Historical avg price for same category
    category_ids = [c.id for c in event.categories] if event.categories else []
    hist_avg_price = None
    if category_ids:
        hist_avg_price = (
            db.query(sqlfunc.avg(TicketTier.price))
            .join(Event, TicketTier.event_id == Event.id)
            .join(event_category_link, Event.id == event_category_link.c.event_id)
            .filter(
                event_category_link.c.category_id.in_(category_ids),
                Event.event_date < now.strftime("%Y-%m-%d"),
            )
            .scalar()
        )

    # Per-tier suggestions
    tier_suggestions = []
    for tier in tiers:
        available = tier.quantity_available
        sold = tier.quantity_sold
        remaining = max(available - sold, 0)
        st = sold / max(available, 1)

        # Determine adjustment
        adjustment = 0.0
        direction = "hold"
        confidence = "medium"
        reasoning = ""

        if st >= 0.90:
            adjustment = 0.20
            direction = "increase"
            confidence = "high"
            reasoning = f"Tier is {round(st * 100)}% sold. Very strong demand supports a 20% increase."
        elif st >= 0.80 and days_until > 3:
            adjustment = 0.15
            direction = "increase"
            confidence = "high"
            reasoning = f"Tier is {round(st * 100)}% sold with {days_until} days remaining. Strong demand supports a 15% increase."
        elif st >= 0.60 and days_until > 7:
            adjustment = 0.10
            direction = "increase"
            confidence = "medium"
            reasoning = f"Tier is {round(st * 100)}% sold with {days_until} days to go. Moderate demand — consider a 10% increase."
        elif st < 0.15 and days_until < 3:
            adjustment = -0.25
            direction = "decrease"
            confidence = "high"
            reasoning = f"Only {round(st * 100)}% sold with {days_until} days left. Aggressive discount recommended."
        elif st < 0.30 and days_until < 7:
            adjustment = -0.15
            direction = "decrease"
            confidence = "medium"
            reasoning = f"Only {round(st * 100)}% sold with {days_until} days remaining. Consider a 15% discount to drive sales."
        elif st < 0.40 and days_until < 14:
            adjustment = -0.10
            direction = "decrease"
            confidence = "low"
            reasoning = f"{round(st * 100)}% sold with {days_until} days to go. A modest discount may help."
        else:
            reasoning = f"Tier is {round(st * 100)}% sold with {days_until} days remaining. Current pricing is appropriate."

        # Modulate by elasticity
        if elasticity_level == "high" and direction == "increase":
            adjustment = min(adjustment, 0.10)
            reasoning += " (Capped due to high price sensitivity.)"
        elif elasticity_level == "high" and direction == "decrease":
            adjustment *= 1.2

        new_price = max(0, int(tier.price * (1 + adjustment)))

        tier_suggestions.append({
            "tier_id": tier.id,
            "tier_name": tier.name,
            "current_price_cents": tier.price,
            "current_price_display": f"${tier.price / 100:.2f}",
            "sell_through_percent": round(st * 100, 1),
            "remaining": remaining,
            "suggested_price_cents": new_price,
            "suggested_price_display": f"${new_price / 100:.2f}",
            "adjustment_percent": round(adjustment * 100, 1),
            "direction": direction,
            "confidence": confidence,
            "reasoning": reasoning,
        })

    return {
        "event_id": event.id,
        "event_name": event.name,
        "event_date": event.event_date,
        "days_until_event": days_until,
        "price_elasticity": {
            "promo_usage_ratio": round(promo_ratio, 3),
            "elasticity_level": elasticity_level,
            "interpretation": elasticity_text,
        },
        "tiers": tier_suggestions,
        "historical_avg_price_cents": int(hist_avg_price) if hist_avg_price else None,
        "note": "These are suggestions only. No prices have been changed.",
    }


# ============== Feature 3: Churn Prediction (RFM) ==============


def predict_churn(db: Session, min_days_inactive: int = 30, limit: int = 50) -> dict:
    """Identify at-risk customers using RFM analysis."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=min_days_inactive)

    # Get customers with preferences who are inactive
    rows = (
        db.query(EventGoer, CustomerPreference)
        .join(CustomerPreference, EventGoer.id == CustomerPreference.event_goer_id)
        .filter(CustomerPreference.last_interaction_date < cutoff)
        .order_by(CustomerPreference.total_spent_cents.desc())
        .limit(limit)
        .all()
    )

    if not rows:
        return {
            "total_at_risk": 0,
            "min_days_inactive": min_days_inactive,
            "customers": [],
            "message": "No at-risk customers found for the given criteria.",
        }

    # Compute RFM scores
    recency_vals = []
    frequency_vals = []
    monetary_vals = []
    for goer, pref in rows:
        lid = pref.last_interaction_date
        if lid:
            if lid.tzinfo is None:
                lid = lid.replace(tzinfo=timezone.utc)
            days_since = (now - lid).days
        else:
            days_since = 999
        recency_vals.append(float(days_since))
        frequency_vals.append(float(pref.total_events_attended or 0))
        monetary_vals.append(float(pref.total_spent_cents or 0))

    r_scores = _assign_quartiles(recency_vals, reverse=True)  # lower recency = higher score
    f_scores = _assign_quartiles(frequency_vals, reverse=False)
    m_scores = _assign_quartiles(monetary_vals, reverse=False)

    customers = []
    for i, (goer, pref) in enumerate(rows):
        r, f, m = r_scores[i], f_scores[i], m_scores[i]
        total_rfm = r + f + m

        if r <= 2 and (f >= 3 or m >= 3):
            segment = "at_risk"
        elif r <= 2 and f <= 2 and m >= 2:
            segment = "lapsed"
        else:
            segment = "lost"

        days_inactive = int(recency_vals[i])

        customers.append({
            "customer_id": goer.id,
            "name": goer.name,
            "email": goer.email,
            "segment": segment,
            "rfm_scores": {"recency": r, "frequency": f, "monetary": m, "total": total_rfm},
            "days_inactive": days_inactive,
            "total_spent_dollars": round((pref.total_spent_cents or 0) / 100, 2),
            "total_events": pref.total_events_attended or 0,
            "last_interaction": pref.last_interaction_date.isoformat() if pref.last_interaction_date else None,
            "re_engagement_suggestion": _get_reengagement_suggestion(segment, pref),
        })

    return {
        "total_at_risk": len(customers),
        "min_days_inactive": min_days_inactive,
        "customers": customers,
    }


def get_customer_segments(db: Session) -> dict:
    """Get customer segmentation summary using RFM analysis."""
    now = datetime.now(timezone.utc)

    rows = (
        db.query(EventGoer, CustomerPreference)
        .join(CustomerPreference, EventGoer.id == CustomerPreference.event_goer_id)
        .all()
    )

    total = len(rows)
    if total == 0:
        # Count customers without preferences
        total_goers = db.query(sqlfunc.count(EventGoer.id)).scalar() or 0
        return {
            "total_customers_analyzed": 0,
            "total_customers_without_profile": total_goers,
            "segments": {},
            "message": "No customers have preference profiles yet.",
        }

    recency_vals = []
    frequency_vals = []
    monetary_vals = []
    for goer, pref in rows:
        lid = pref.last_interaction_date
        if lid:
            if lid.tzinfo is None:
                lid = lid.replace(tzinfo=timezone.utc)
            days_since = (now - lid).days
        else:
            days_since = 999
        recency_vals.append(float(days_since))
        frequency_vals.append(float(pref.total_events_attended or 0))
        monetary_vals.append(float(pref.total_spent_cents or 0))

    r_scores = _assign_quartiles(recency_vals, reverse=True)
    f_scores = _assign_quartiles(frequency_vals, reverse=False)
    m_scores = _assign_quartiles(monetary_vals, reverse=False)

    segments = {"active": [], "at_risk": [], "lapsed": [], "lost": []}
    for i, (goer, pref) in enumerate(rows):
        r, f, m = r_scores[i], f_scores[i], m_scores[i]
        total_rfm = r + f + m

        if total_rfm >= 10:
            segment = "active"
        elif r <= 2 and (f >= 3 or m >= 3):
            segment = "at_risk"
        elif r <= 2 and f <= 2 and m >= 2:
            segment = "lapsed"
        else:
            segment = "lost"
        segments[segment].append(pref.total_spent_cents or 0)

    result_segments = {}
    descriptions = {
        "active": "Champions — highly engaged, recent, high-value customers",
        "at_risk": "Previously valuable customers showing signs of disengagement",
        "lapsed": "Customers who have not interacted recently with moderate prior engagement",
        "lost": "Low engagement customers who have been inactive for a long time",
    }
    for seg_name, spent_list in segments.items():
        count = len(spent_list)
        avg = round(sum(spent_list) / max(count, 1) / 100, 2)
        result_segments[seg_name] = {
            "count": count,
            "percent": round(count / max(total, 1) * 100, 1),
            "avg_spent_dollars": avg,
            "description": descriptions[seg_name],
        }

    avg_r = round(sum(recency_vals) / max(total, 1), 1)
    avg_f = round(sum(frequency_vals) / max(total, 1), 1)
    avg_m = round(sum(monetary_vals) / max(total, 1) / 100, 2)

    return {
        "total_customers_analyzed": total,
        "segments": result_segments,
        "rfm_distribution": {
            "recency_avg_days": avg_r,
            "frequency_avg_events": avg_f,
            "monetary_avg_dollars": avg_m,
        },
    }


# ============== Feature 4: Event Recommendations ==============


def recommend_events(
    db: Session,
    customer_id: Optional[int] = None,
    customer_email: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """Get personalized event recommendations for a customer."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Find customer
    if customer_id:
        goer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()
    elif customer_email:
        goer = db.query(EventGoer).filter(EventGoer.email == customer_email).first()
    else:
        return {"error": "Provide either customer_id or customer_email"}

    if not goer:
        return {"error": "Customer not found"}

    pref = db.query(CustomerPreference).filter(CustomerPreference.event_goer_id == goer.id).first()

    # Upcoming events
    upcoming = (
        db.query(Event)
        .options(joinedload(Event.categories), joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.event_date >= today)
        .all()
    )
    if not upcoming:
        return {
            "customer_id": goer.id,
            "customer_name": goer.name,
            "recommendations": [],
            "message": "No upcoming events to recommend.",
        }

    # Customer's past events
    customer_event_rows = (
        db.query(sqlfunc.distinct(TicketTier.event_id))
        .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
        .filter(
            Ticket.event_goer_id == goer.id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
        )
        .all()
    )
    customer_event_ids = set(r[0] for r in customer_event_rows)

    # Filter out events customer already has tickets for
    candidate_events = [e for e in upcoming if e.id not in customer_event_ids]
    if not candidate_events:
        candidate_events = upcoming  # Fallback: show all upcoming if they've been to all

    # --- Signal 1: Content-based (category match) ---
    fav_types = []
    if pref and pref.favorite_event_types:
        try:
            fav_types = json.loads(pref.favorite_event_types)
        except (json.JSONDecodeError, TypeError):
            pass
    fav_lower = [f.lower() for f in fav_types]

    content_scores = []
    for event in candidate_events:
        score = 0.0
        if fav_lower and event.categories:
            cat_names = [c.name.lower() for c in event.categories]
            for fav in fav_lower:
                for cat in cat_names:
                    if fav in cat or cat in fav:
                        score += 1.0
                        break
        content_scores.append(score)

    # --- Signal 2: Collaborative filtering ---
    collab_scores_raw = {}
    if customer_event_ids:
        co_attendee_rows = (
            db.query(sqlfunc.distinct(Ticket.event_goer_id))
            .join(TicketTier)
            .filter(
                TicketTier.event_id.in_(customer_event_ids),
                Ticket.event_goer_id != goer.id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            )
            .all()
        )
        co_ids = [r[0] for r in co_attendee_rows]

        if co_ids:
            co_buying = (
                db.query(
                    TicketTier.event_id,
                    sqlfunc.count(sqlfunc.distinct(Ticket.event_goer_id)).label("buyers"),
                )
                .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
                .join(Event, TicketTier.event_id == Event.id)
                .filter(
                    Ticket.event_goer_id.in_(co_ids),
                    Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                    Event.event_date >= today,
                )
                .group_by(TicketTier.event_id)
                .all()
            )
            for row in co_buying:
                collab_scores_raw[row.event_id] = row.buyers

    collab_scores = [float(collab_scores_raw.get(e.id, 0)) for e in candidate_events]

    # --- Signal 3: Popularity (page views + sell rate) ---
    cutoff_7d = now - timedelta(days=7)
    view_rows = (
        db.query(PageView.event_id, sqlfunc.count(PageView.id).label("views"))
        .filter(PageView.event_id.isnot(None), PageView.created_at >= cutoff_7d)
        .group_by(PageView.event_id)
        .all()
    )
    view_map = {r.event_id: r.views for r in view_rows}

    popularity_scores = []
    for event in candidate_events:
        views = view_map.get(event.id, 0)
        total_avail = sum(t.quantity_available for t in event.ticket_tiers) if event.ticket_tiers else 1
        total_sold = sum(t.quantity_sold for t in event.ticket_tiers) if event.ticket_tiers else 0
        sell_rate = total_sold / max(total_avail, 1)
        popularity_scores.append(views + sell_rate * 100)

    # Normalize all signals to 0-1
    content_norm = _min_max_normalize(content_scores)
    collab_norm = _min_max_normalize(collab_scores)
    pop_norm = _min_max_normalize(popularity_scores)

    # Combine: content 40%, collaborative 35%, popularity 25%
    combined = []
    for i in range(len(candidate_events)):
        score = content_norm[i] * 0.40 + collab_norm[i] * 0.35 + pop_norm[i] * 0.25
        combined.append((score, i))

    combined.sort(key=lambda x: -x[0])

    recommendations = []
    for rank, (score, idx) in enumerate(combined[:limit]):
        event = candidate_events[idx]
        remaining = 0
        lowest_price = None
        if event.ticket_tiers:
            remaining = sum(max(t.quantity_available - t.quantity_sold, 0) for t in event.ticket_tiers)
            active_prices = [t.price for t in event.ticket_tiers if t.quantity_sold < t.quantity_available]
            lowest_price = min(active_prices) if active_prices else None

        recommendations.append({
            "rank": rank + 1,
            "event_id": event.id,
            "event_name": event.name,
            "event_date": event.event_date,
            "event_time": event.event_time,
            "venue_name": event.venue.name if event.venue else None,
            "categories": [c.name for c in event.categories] if event.categories else [],
            "score": round(score, 3),
            "signals": {
                "content_match": round(content_norm[idx], 3),
                "collaborative": round(collab_norm[idx], 3),
                "popularity": round(pop_norm[idx], 3),
            },
            "reason": _build_recommendation_reason(
                content_norm[idx], collab_norm[idx], pop_norm[idx], event
            ),
            "tickets_remaining": remaining,
            "lowest_price_cents": lowest_price,
        })

    return {
        "customer_id": goer.id,
        "customer_name": goer.name,
        "recommendations": recommendations,
    }


def get_trending_events(db: Session, days: int = 7, limit: int = 10) -> dict:
    """Get currently trending events by page views, sales velocity, and waitlist growth."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    cutoff = now - timedelta(days=days)

    # Upcoming events
    events = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.event_date >= today)
        .all()
    )
    if not events:
        return {"period_days": days, "trending_events": []}

    event_ids = [e.id for e in events]

    # Page views per event
    view_rows = (
        db.query(PageView.event_id, sqlfunc.count(PageView.id).label("views"))
        .filter(PageView.event_id.in_(event_ids), PageView.created_at >= cutoff)
        .group_by(PageView.event_id)
        .all()
    )
    view_map = {r.event_id: r.views for r in view_rows}

    # Recent ticket sales per event
    sale_rows = (
        db.query(TicketTier.event_id, sqlfunc.count(Ticket.id).label("sales"))
        .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
        .filter(
            TicketTier.event_id.in_(event_ids),
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.purchased_at >= cutoff,
        )
        .group_by(TicketTier.event_id)
        .all()
    )
    sale_map = {r.event_id: r.sales for r in sale_rows}

    # Waitlist entries per event
    wl_rows = (
        db.query(WaitlistEntry.event_id, sqlfunc.count(WaitlistEntry.id).label("entries"))
        .filter(
            WaitlistEntry.event_id.in_(event_ids),
            WaitlistEntry.created_at >= cutoff,
            WaitlistEntry.status == WaitlistStatus.WAITING,
        )
        .group_by(WaitlistEntry.event_id)
        .all()
    )
    wl_map = {r.event_id: r.entries for r in wl_rows}

    # Compute scores
    view_vals = [float(view_map.get(e.id, 0)) for e in events]
    sale_vals = [float(sale_map.get(e.id, 0)) for e in events]
    wl_vals = [float(wl_map.get(e.id, 0)) for e in events]

    view_norm = _min_max_normalize(view_vals)
    sale_norm = _min_max_normalize(sale_vals)
    wl_norm = _min_max_normalize(wl_vals)

    scored = []
    for i, event in enumerate(events):
        score = view_norm[i] * 0.40 + sale_norm[i] * 0.35 + wl_norm[i] * 0.25
        scored.append((score, i))

    scored.sort(key=lambda x: -x[0])

    results = []
    for rank, (score, idx) in enumerate(scored[:limit]):
        event = events[idx]
        total_avail = sum(t.quantity_available for t in event.ticket_tiers) if event.ticket_tiers else 0
        total_sold = sum(t.quantity_sold for t in event.ticket_tiers) if event.ticket_tiers else 0
        remaining = max(total_avail - total_sold, 0)
        sell_through = round(total_sold / max(total_avail, 1) * 100, 1)

        results.append({
            "rank": rank + 1,
            "event_id": event.id,
            "event_name": event.name,
            "event_date": event.event_date,
            "venue_name": event.venue.name if event.venue else None,
            "trending_score": round(score, 2),
            "signals": {
                "page_views": int(view_vals[idx]),
                "recent_sales": int(sale_vals[idx]),
                "waitlist_entries": int(wl_vals[idx]),
            },
            "sell_through_percent": sell_through,
            "tickets_remaining": remaining,
        })

    return {"period_days": days, "trending_events": results}


# ============== Feature 7: Revenue Forecasting ==============


def forecast_revenue(db: Session, time_horizon_days: int = 90) -> dict:
    """Project total revenue across all upcoming events based on velocity and historical patterns."""
    now = datetime.now(timezone.utc)
    horizon_date = (now + timedelta(days=time_horizon_days)).strftime("%Y-%m-%d")
    today_str = now.strftime("%Y-%m-%d")

    # Get all upcoming events within the horizon
    upcoming = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.categories))
        .filter(
            Event.event_date >= today_str,
            Event.event_date <= horizon_date,
        )
        .all()
    )

    if not upcoming:
        return {
            "time_horizon_days": time_horizon_days,
            "total_events": 0,
            "current_revenue_dollars": 0,
            "projected_revenue_dollars": 0,
            "events": [],
            "message": f"No upcoming events in the next {time_horizon_days} days.",
        }

    # Historical average sell-through for confidence calibration
    hist_stats = (
        db.query(
            sqlfunc.sum(TicketTier.quantity_sold).label("sold"),
            sqlfunc.sum(TicketTier.quantity_available).label("avail"),
        )
        .join(Event, TicketTier.event_id == Event.id)
        .filter(Event.event_date < today_str)
        .first()
    )
    hist_sold = int(hist_stats.sold or 0) if hist_stats else 0
    hist_avail = max(int(hist_stats.avail or 1), 1) if hist_stats else 1
    hist_completion_rate = min(hist_sold / hist_avail, 1.0) if hist_avail > 0 else 0.5

    total_current = 0
    total_projected_low = 0
    total_projected_mid = 0
    total_projected_high = 0
    event_forecasts = []

    for event in upcoming:
        tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()
        if not tiers:
            continue

        # Current revenue from sold tickets
        current_rev = (
            db.query(
                sqlfunc.sum(TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0))
            )
            .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
            .filter(
                TicketTier.event_id == event.id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            )
            .scalar()
            or 0
        )

        total_available = sum(t.quantity_available for t in tiers)
        total_sold = sum(t.quantity_sold for t in tiers)
        total_remaining = max(total_available - total_sold, 0)

        # Avg price of remaining tickets (weighted by tier capacity)
        if total_remaining > 0:
            weighted_price = sum(
                t.price * max(t.quantity_available - t.quantity_sold, 0) for t in tiers
            ) / total_remaining
        else:
            weighted_price = sum(t.price for t in tiers) / max(len(tiers), 1)

        # Current velocity
        earliest_purchase = (
            db.query(sqlfunc.min(Ticket.purchased_at))
            .join(TicketTier)
            .filter(
                TicketTier.event_id == event.id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            )
            .scalar()
        )

        velocity = 0.0
        if earliest_purchase and total_sold > 0:
            ep = earliest_purchase
            if ep.tzinfo is None:
                ep = ep.replace(tzinfo=timezone.utc)
            days_on_sale = max((now - ep).days, 1)
            velocity = total_sold / days_on_sale

        # Days until event
        try:
            event_dt = datetime.strptime(f"{event.event_date} {event.event_time or '23:59'}", "%Y-%m-%d %H:%M")
            event_dt = event_dt.replace(tzinfo=timezone.utc)
            days_until = max((event_dt - now).days, 0)
        except ValueError:
            days_until = 30

        # Project additional sales
        if velocity > 0 and days_until > 0:
            projected_additional_tickets = min(velocity * days_until, total_remaining)
        else:
            # Fallback: use historical completion rate
            projected_additional_tickets = total_remaining * hist_completion_rate

        projected_additional_rev = projected_additional_tickets * weighted_price

        # Confidence intervals
        # Data quality factor: more sales = more confidence
        data_quality = min(total_sold / max(total_available * 0.1, 1), 1.0)  # 1.0 at 10%+ sold
        confidence = 0.3 + (data_quality * 0.4) + (min(hist_completion_rate, 0.5) * 0.3)

        mid_rev = current_rev + projected_additional_rev
        spread = max(1.0 - confidence, 0.2)  # Higher confidence = tighter range
        low_rev = current_rev + (projected_additional_rev * max(1.0 - spread, 0.1))
        high_rev = current_rev + (projected_additional_rev * min(1.0 + spread, 2.0))

        total_current += current_rev
        total_projected_low += low_rev
        total_projected_mid += mid_rev
        total_projected_high += high_rev

        event_forecasts.append({
            "event_id": event.id,
            "event_name": event.name,
            "event_date": event.event_date,
            "venue_name": event.venue.name if event.venue else None,
            "current_revenue_dollars": round(current_rev / 100, 2),
            "projected_revenue_dollars": {
                "low": round(low_rev / 100, 2),
                "mid": round(mid_rev / 100, 2),
                "high": round(high_rev / 100, 2),
            },
            "tickets": {
                "sold": total_sold,
                "remaining": total_remaining,
                "capacity": total_available,
                "projected_additional": round(projected_additional_tickets),
            },
            "velocity_per_day": round(velocity, 2),
            "days_until_event": days_until,
            "confidence": round(confidence, 2),
        })

    # Sort by projected mid revenue descending
    event_forecasts.sort(key=lambda x: x["projected_revenue_dollars"]["mid"], reverse=True)

    return {
        "time_horizon_days": time_horizon_days,
        "total_events": len(event_forecasts),
        "current_revenue_dollars": round(total_current / 100, 2),
        "projected_revenue_dollars": {
            "low": round(total_projected_low / 100, 2),
            "mid": round(total_projected_mid / 100, 2),
            "high": round(total_projected_high / 100, 2),
        },
        "historical_completion_rate_percent": round(hist_completion_rate * 100, 1),
        "events": event_forecasts,
    }
