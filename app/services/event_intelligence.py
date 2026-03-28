"""
Event Intelligence & Monitoring Service

Autonomous monitoring and optimization for events:
- Auto-pause low-performing Meta ads
- Detect refund patterns and alert
- Monitor inventory pressure
- Track marketing performance
- Generate alerts and recommendations
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Event, Ticket, TicketTier, MetaAdCampaign, MetaAdStatus,
    TicketStatus, EventGoer
)
from app.config import get_settings

logger = logging.getLogger(__name__)


def monitor_ad_performance(db: Session, event_id: int, auto_pause: bool = True) -> Dict:
    """
    Monitor Meta ad performance and auto-pause underperformers.

    Pauses ads if:
    - ROAS < 1.0 (spending more than earning)
    - Cost per ticket > average ticket price
    - Campaign running >48 hours with <5 conversions

    Args:
        db: Database session
        event_id: Event to monitor
        auto_pause: Automatically pause bad performers (default True)

    Returns:
        Dict with performance analysis and actions taken
    """
    settings = get_settings()

    # Get all active campaigns for this event
    campaigns = (
        db.query(MetaAdCampaign)
        .filter(
            MetaAdCampaign.event_id == event_id,
            MetaAdCampaign.status.in_([MetaAdStatus.ACTIVE, MetaAdStatus.RUNNING])
        )
        .all()
    )

    if not campaigns:
        return {"message": "No active campaigns to monitor"}

    # Get event ticket stats
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Calculate average ticket price
    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    avg_ticket_price = sum(t.price for t in tiers) / len(tiers) if tiers else 0

    # Count tickets sold (potential conversions)
    tickets_sold = db.query(func.count(Ticket.id)).filter(
        Ticket.event_id == event_id,
        Ticket.status == TicketStatus.CONFIRMED
    ).scalar()

    results = {
        "event_id": event_id,
        "event_name": event.name,
        "campaigns_monitored": len(campaigns),
        "avg_ticket_price_cents": avg_ticket_price,
        "total_tickets_sold": tickets_sold,
        "actions": [],
        "alerts": [],
    }

    for campaign in campaigns:
        # Check how long campaign has been running
        created_at = campaign.created_at
        hours_running = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600

        # Get campaign spend (from Meta API in production)
        # For now, estimate based on budget
        if campaign.budget_type == "daily":
            estimated_spend = campaign.budget_cents * min(hours_running / 24, 7)  # Cap at 7 days
        else:
            estimated_spend = campaign.budget_cents

        # Estimate attributed conversions (would come from UTM tracking in production)
        # For now, use a rough heuristic
        campaign_conversions = max(0, int(tickets_sold * 0.3))  # Assume 30% from ads

        # Calculate metrics
        cost_per_ticket = estimated_spend / campaign_conversions if campaign_conversions > 0 else float('inf')
        roas = (campaign_conversions * avg_ticket_price / estimated_spend) if estimated_spend > 0 else 0

        # Decision logic
        should_pause = False
        reason = None

        if hours_running >= 48:
            if campaign_conversions < 5:
                should_pause = True
                reason = f"Low conversions: Only {campaign_conversions} tickets after 48 hours"
            elif roas < 1.0:
                should_pause = True
                reason = f"Poor ROAS: ${roas:.2f} (spending more than earning)"
            elif cost_per_ticket > avg_ticket_price:
                should_pause = True
                reason = f"High cost per ticket: ${cost_per_ticket/100:.2f} vs avg ${avg_ticket_price/100:.2f}"

        campaign_data = {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "hours_running": round(hours_running, 1),
            "estimated_spend_cents": int(estimated_spend),
            "conversions": campaign_conversions,
            "cost_per_ticket_cents": int(cost_per_ticket) if cost_per_ticket != float('inf') else None,
            "roas": round(roas, 2),
        }

        if should_pause and auto_pause:
            # Pause the campaign
            campaign.status = MetaAdStatus.PAUSED
            campaign.paused_reason = reason
            db.commit()

            results["actions"].append({
                **campaign_data,
                "action": "PAUSED",
                "reason": reason,
            })

            logger.warning(f"Auto-paused campaign {campaign.id}: {reason}")
        elif should_pause:
            results["alerts"].append({
                **campaign_data,
                "alert": "SHOULD_PAUSE",
                "reason": reason,
            })

    return results


def detect_refund_patterns(db: Session, event_id: Optional[int] = None) -> Dict:
    """
    Detect unusual refund patterns that might indicate event issues.

    Alerts if:
    - Refund rate > 5% for an event
    - Spike in refunds in last 24 hours
    - Common refund reasons indicating problems

    Args:
        db: Database session
        event_id: Specific event to check, or None for all events

    Returns:
        Dict with refund analysis and alerts
    """
    from app.services.refunds import get_refund_stats

    alerts = []

    if event_id:
        events_to_check = [db.query(Event).filter(Event.id == event_id).first()]
    else:
        # Check all upcoming events
        events_to_check = db.query(Event).filter(
            Event.event_date >= datetime.now(timezone.utc).date()
        ).all()

    for event in events_to_check:
        if not event:
            continue

        stats = get_refund_stats(db, event_id=event.id)

        # Check refund rate
        refund_rate = stats.get("refund_rate", 0)
        if refund_rate > 0.05:  # 5% threshold
            alerts.append({
                "event_id": event.id,
                "event_name": event.name,
                "alert_type": "HIGH_REFUND_RATE",
                "severity": "HIGH" if refund_rate > 0.10 else "MEDIUM",
                "refund_rate": round(refund_rate * 100, 1),
                "message": f"Refund rate of {refund_rate*100:.1f}% exceeds 5% threshold",
                "recommendation": "Investigate event issues - consider contacting customers or reviewing event details",
            })

        # Check for refund spike in last 24 hours
        recent_refunds = (
            db.query(func.count(Ticket.id))
            .filter(
                Ticket.event_id == event.id,
                Ticket.status == TicketStatus.REFUNDED,
                Ticket.refunded_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            )
            .scalar()
        )

        if recent_refunds >= 5:
            alerts.append({
                "event_id": event.id,
                "event_name": event.name,
                "alert_type": "REFUND_SPIKE",
                "severity": "HIGH",
                "recent_refunds": recent_refunds,
                "message": f"{recent_refunds} refunds in last 24 hours",
                "recommendation": "Urgent: Contact customers to identify issue",
            })

        # Analyze refund reasons
        reason_counts = {}
        refunded_tickets = db.query(Ticket).filter(
            Ticket.event_id == event.id,
            Ticket.status == TicketStatus.REFUNDED,
            Ticket.refund_reason.isnot(None)
        ).all()

        for ticket in refunded_tickets:
            reason = ticket.refund_reason.lower()
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # Check for concerning patterns
        concerning_keywords = ["cancelled", "canceled", "postponed", "venue", "quality", "scam", "fraud"]
        for keyword in concerning_keywords:
            count = sum(v for k, v in reason_counts.items() if keyword in k)
            if count >= 3:
                alerts.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "alert_type": "PATTERN_DETECTED",
                    "severity": "MEDIUM",
                    "pattern": keyword,
                    "occurrences": count,
                    "message": f"{count} refunds mention '{keyword}'",
                    "recommendation": f"Review event status - potential issue with {keyword}",
                })

    return {
        "checked_events": len(events_to_check),
        "alerts_found": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat(),
    }


def check_inventory_pressure(db: Session, event_id: int) -> Dict:
    """
    Monitor inventory and suggest pricing/marketing actions.

    Recommendations:
    - High demand + time remaining -> Increase prices
    - Low demand + event approaching -> Flash sale
    - Tier imbalance -> Reallocate inventory

    Args:
        db: Database session
        event_id: Event to analyze

    Returns:
        Dict with inventory analysis and recommendations
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
    if not tiers:
        return {"error": "No ticket tiers found"}

    # Calculate time pressure
    days_until_event = (event.event_date - datetime.now(timezone.utc).date()).days

    recommendations = []
    tier_analysis = []

    for tier in tiers:
        sell_through = tier.quantity_sold / tier.quantity_available if tier.quantity_available > 0 else 0
        remaining = tier.quantity_available - tier.quantity_sold

        tier_data = {
            "tier_id": tier.id,
            "tier_name": tier.name,
            "sell_through_pct": round(sell_through * 100, 1),
            "remaining": remaining,
            "total": tier.quantity_available,
        }

        # High demand + time remaining
        if sell_through >= 0.8 and days_until_event > 14:
            recommendations.append({
                **tier_data,
                "action": "INCREASE_PRICE",
                "priority": "HIGH",
                "reason": f"{sell_through*100:.0f}% sold with {days_until_event} days remaining",
                "suggestion": f"Increase price by 20-30% using dynamic pricing",
            })

        # Selling out soon
        elif sell_through >= 0.95:
            recommendations.append({
                **tier_data,
                "action": "URGENCY_MESSAGING",
                "priority": "HIGH",
                "reason": f"Only {remaining} tickets left!",
                "suggestion": "Trigger 'almost sold out' email/SMS campaign",
            })

        # Low demand, event approaching
        elif sell_through < 0.3 and days_until_event <= 7:
            recommendations.append({
                **tier_data,
                "action": "FLASH_SALE",
                "priority": "MEDIUM",
                "reason": f"Only {sell_through*100:.0f}% sold with {days_until_event} days left",
                "suggestion": f"Create 24-hour flash sale: 20% off",
            })

        # Moderate sell-through
        elif 0.5 <= sell_through < 0.8 and days_until_event > 7:
            recommendations.append({
                **tier_data,
                "action": "MAINTAIN",
                "priority": "LOW",
                "reason": "Healthy sell-through rate",
                "suggestion": "Continue current marketing strategy",
            })

        tier_analysis.append(tier_data)

    # Overall event pressure
    total_sold = sum(t.quantity_sold for t in tiers)
    total_available = sum(t.quantity_available for t in tiers)
    overall_sell_through = total_sold / total_available if total_available > 0 else 0

    pressure_level = "LOW"
    if overall_sell_through >= 0.8:
        pressure_level = "HIGH"
    elif overall_sell_through >= 0.5:
        pressure_level = "MEDIUM"

    return {
        "event_id": event_id,
        "event_name": event.name,
        "days_until_event": days_until_event,
        "overall_sell_through_pct": round(overall_sell_through * 100, 1),
        "pressure_level": pressure_level,
        "total_sold": total_sold,
        "total_available": total_available,
        "remaining": total_available - total_sold,
        "tiers": tier_analysis,
        "recommendations": recommendations,
    }


def suggest_related_events(db: Session, ticket: Ticket) -> List[Dict]:
    """
    Recommend similar events for cross-sell opportunities.

    Based on:
    - Same venue
    - Same category/genre
    - Similar price range
    - Upcoming events only

    Args:
        db: Database session
        ticket: Recently purchased ticket

    Returns:
        List of recommended events
    """
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    if not event:
        return []

    recommendations = []

    # Find events at same venue
    venue_events = (
        db.query(Event)
        .filter(
            Event.venue_id == event.venue_id,
            Event.id != event.id,
            Event.event_date >= datetime.now(timezone.utc).date()
        )
        .limit(3)
        .all()
    )

    for e in venue_events:
        recommendations.append({
            "event_id": e.id,
            "event_name": e.name,
            "event_date": str(e.event_date),
            "match_reason": "Same venue",
            "match_score": 0.8,
        })

    # Find events in same category
    if event.category_id:
        category_events = (
            db.query(Event)
            .filter(
                Event.category_id == event.category_id,
                Event.id != event.id,
                Event.event_date >= datetime.now(timezone.utc).date()
            )
            .limit(3)
            .all()
        )

        for e in category_events:
            if e.id not in [r["event_id"] for r in recommendations]:
                recommendations.append({
                    "event_id": e.id,
                    "event_name": e.name,
                    "event_date": str(e.event_date),
                    "match_reason": "Similar category",
                    "match_score": 0.6,
                })

    # Sort by match score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)

    return recommendations[:5]  # Top 5


def calculate_optimal_send_time(event_context: Dict, artist_research: Optional[Dict] = None) -> Dict:
    """
    Determine best time to send marketing emails based on audience.

    Rules:
    - Younger audience (EDM, hip-hop) -> Evening (8pm-10pm)
    - Older audience (jazz, classical) -> Mid-day (10am-2pm)
    - Weekend events -> Send Thursday evening
    - Weekday events -> Send 3-5 days before
    - High-priced events -> Send earlier in day (professional audience)

    Args:
        event_context: Event analysis from research agent
        artist_research: Artist demographics (optional)

    Returns:
        Dict with optimal send times and reasoning
    """
    event_date = event_context['event']['date']
    is_weekend = event_context['event']['is_weekend']
    avg_price = event_context['pricing']['avg_cents']

    # Default timing
    optimal_hour = 18  # 6pm
    optimal_day_offset = -3  # 3 days before
    reasoning = []

    # Adjust based on artist demographics
    if artist_research and not artist_research.get("fallback"):
        genre = artist_research.get("genre", "").lower()
        fan_demo = artist_research.get("fan_demographics", "").lower()

        # Younger audience genres
        if any(x in genre for x in ["edm", "electronic", "hip-hop", "rap", "trap"]):
            optimal_hour = 20  # 8pm
            reasoning.append("Younger EDM/hip-hop audience - evening send time")

        # Older audience genres
        elif any(x in genre for x in ["jazz", "classical", "blues", "folk"]):
            optimal_hour = 11  # 11am
            reasoning.append("Mature jazz/classical audience - mid-morning send time")

        # Check fan demographics
        if "18-25" in fan_demo or "young" in fan_demo:
            optimal_hour = max(optimal_hour, 19)  # At least 7pm
            reasoning.append("Young fan base - prefer evening communications")
        elif "35+" in fan_demo or "professional" in fan_demo:
            optimal_hour = min(optimal_hour, 12)  # No later than noon
            reasoning.append("Professional audience - morning send time")

    # Adjust based on event timing
    if is_weekend:
        optimal_day_offset = -3  # Thursday before weekend event
        reasoning.append("Weekend event - send Thursday to capture weekend planners")
    else:
        optimal_day_offset = -5  # Monday before weekend event
        reasoning.append("Weekday event - send 5 days advance for planning")

    # Adjust based on pricing (high-priced = professional audience)
    if avg_price > 5000:  # $50+
        optimal_hour = min(optimal_hour, 10)  # Morning send
        reasoning.append("High-priced event - professional audience prefers morning emails")

    # Calculate actual send datetime
    from datetime import datetime
    try:
        event_datetime = datetime.fromisoformat(str(event_date))
        send_date = event_datetime + timedelta(days=optimal_day_offset)
        send_datetime = send_date.replace(hour=optimal_hour, minute=0, second=0)
    except:
        send_datetime = None

    return {
        "optimal_send_hour": optimal_hour,
        "optimal_day_offset": optimal_day_offset,
        "send_datetime": send_datetime.isoformat() if send_datetime else None,
        "reasoning": reasoning,
        "confidence": len(reasoning) / 3.0,  # More factors = higher confidence
    }


def run_intelligence_check(db: Session, event_id: int) -> Dict:
    """
    Run complete intelligence check for an event.

    Checks:
    - Ad performance
    - Refund patterns
    - Inventory pressure
    - Overall event health

    Returns comprehensive report with all alerts and recommendations.
    """
    results = {
        "event_id": event_id,
        "checked_at": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Check ad performance
    try:
        ad_check = monitor_ad_performance(db, event_id, auto_pause=False)
        results["checks"]["ad_performance"] = ad_check
    except Exception as e:
        results["checks"]["ad_performance"] = {"error": str(e)}

    # Check refund patterns
    try:
        refund_check = detect_refund_patterns(db, event_id)
        results["checks"]["refund_patterns"] = refund_check
    except Exception as e:
        results["checks"]["refund_patterns"] = {"error": str(e)}

    # Check inventory pressure
    try:
        inventory_check = check_inventory_pressure(db, event_id)
        results["checks"]["inventory_pressure"] = inventory_check
    except Exception as e:
        results["checks"]["inventory_pressure"] = {"error": str(e)}

    # Count total alerts
    total_alerts = 0
    total_actions = 0

    if "alerts" in results["checks"].get("ad_performance", {}):
        total_alerts += len(results["checks"]["ad_performance"]["alerts"])
    if "actions" in results["checks"].get("ad_performance", {}):
        total_actions += len(results["checks"]["ad_performance"]["actions"])
    if "alerts" in results["checks"].get("refund_patterns", {}):
        total_alerts += len(results["checks"]["refund_patterns"]["alerts"])
    if "recommendations" in results["checks"].get("inventory_pressure", {}):
        total_alerts += len([r for r in results["checks"]["inventory_pressure"]["recommendations"] if r["priority"] in ["HIGH", "MEDIUM"]])

    results["summary"] = {
        "total_alerts": total_alerts,
        "total_actions_taken": total_actions,
        "requires_attention": total_alerts > 0,
    }

    return results
