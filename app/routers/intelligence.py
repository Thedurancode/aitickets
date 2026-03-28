"""
Event Intelligence API Router

Endpoints for autonomous monitoring and optimization.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.rate_limit import limiter
from app.services.event_intelligence import (
    monitor_ad_performance,
    detect_refund_patterns,
    check_inventory_pressure,
    suggest_related_events,
    calculate_optimal_send_time,
    run_intelligence_check,
)
from app.services.learning_engine import (
    track_conversion,
    analyze_channel_attribution,
    learn_optimal_pricing,
    learn_send_time_patterns,
    predict_event_performance,
    run_ab_test_analysis,
)
from app.services.cross_event_intelligence import (
    identify_best_customers,
    find_event_patterns,
    build_lookalike_audience,
    detect_churn_risk,
    compare_similar_events,
)
from app.models import Ticket

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/events/{event_id}/ad-performance")
@limiter.limit("20/minute")
async def get_ad_performance(
    request: Request,
    event_id: int,
    auto_pause: bool = Query(False, description="Automatically pause underperforming ads"),
    db: Session = Depends(get_db),
):
    """
    Monitor Meta ad performance for an event.

    Analyzes ROAS, cost per ticket, and conversion rates.
    Can automatically pause campaigns that are underperforming.

    **Pause Criteria:**
    - ROAS < 1.0 (spending more than earning)
    - Cost per ticket > average ticket price
    - Campaign running >48 hours with <5 conversions
    """
    result = monitor_ad_performance(db, event_id, auto_pause=auto_pause)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/refund-patterns")
@limiter.limit("20/minute")
async def get_refund_patterns(
    request: Request,
    event_id: Optional[int] = Query(None, description="Specific event ID, or None for all events"),
    db: Session = Depends(get_db),
):
    """
    Detect unusual refund patterns across events.

    **Alerts on:**
    - Refund rate > 5% for an event
    - Spike in refunds in last 24 hours
    - Common refund reasons indicating problems (cancelled, venue issues, etc.)

    **Use Cases:**
    - "Are there any refund issues I should know about?"
    - "Check refund patterns for event 123"
    - "Alert me if refunds spike"
    """
    result = detect_refund_patterns(db, event_id)
    return result


@router.get("/events/{event_id}/inventory-pressure")
@limiter.limit("20/minute")
async def get_inventory_pressure(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Analyze inventory and get AI recommendations.

    **Recommendations:**
    - High demand + time remaining → Increase prices
    - Low demand + event approaching → Flash sale
    - Tier imbalance → Reallocate inventory
    - Almost sold out → Urgency messaging

    **Use Cases:**
    - "Should I raise prices for this event?"
    - "What should I do about low sales?"
    - "Check inventory pressure for event 123"
    """
    result = check_inventory_pressure(db, event_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/tickets/{ticket_id}/recommendations")
@limiter.limit("30/minute")
async def get_ticket_recommendations(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
):
    """
    Get event recommendations for cross-sell based on a ticket purchase.

    Suggests similar events based on:
    - Same venue
    - Same category/genre
    - Similar price range

    **Use Cases:**
    - Add recommendations to purchase confirmation emails
    - Upsell on purchase success page
    - Personalized event discovery
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    recommendations = suggest_related_events(db, ticket)

    return {
        "ticket_id": ticket_id,
        "event_id": ticket.event_id,
        "recommendations": recommendations,
    }


@router.get("/events/{event_id}/check")
@limiter.limit("10/minute")
async def run_full_intelligence_check(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Run complete intelligence check for an event.

    Performs all monitoring checks:
    - Ad performance analysis
    - Refund pattern detection
    - Inventory pressure analysis

    Returns comprehensive report with all alerts and recommendations.

    **Use Cases:**
    - "Run full health check on event 123"
    - "What's the status of my event?"
    - "Any issues I should know about?"
    """
    result = run_intelligence_check(db, event_id)
    return result


@router.post("/events/{event_id}/calculate-send-time")
@limiter.limit("20/minute")
async def calculate_send_time(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Calculate optimal email send time based on event and audience.

    Considers:
    - Artist genre and fan demographics
    - Event timing (weekend vs weekday)
    - Ticket pricing (professional vs casual audience)
    - Historical performance data

    **Returns:**
    - Optimal hour of day (0-23)
    - Optimal days before event
    - Recommended send datetime
    - Reasoning for recommendations
    """
    from app.services.event_research_agent import analyze_event_context
    from app.routers.event_research import research_cache

    # Get event context
    event_context = analyze_event_context(db, event_id)

    if "error" in event_context:
        raise HTTPException(status_code=404, detail=event_context["error"])

    # Get artist research if available
    artist_research = None
    if event_id in research_cache:
        research_report = research_cache[event_id]
        artist_research = research_report.get("artist_research")

    # Calculate optimal time
    result = calculate_optimal_send_time(event_context, artist_research)

    return {
        "event_id": event_id,
        "event_name": event_context["event"]["name"],
        **result,
    }


# ============== Learning Engine Endpoints ==============

@router.get("/events/{event_id}/channel-attribution")
@limiter.limit("20/minute")
async def get_channel_attribution(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Analyze which marketing channels are driving ticket sales.

    Returns:
    - Tickets sold per channel
    - Revenue per channel
    - ROAS for paid channels
    - Best performing channel

    **Use Cases:**
    - "Which marketing channel is working best?"
    - "What's my ROAS on Meta ads?"
    - "Show me channel breakdown for event 123"
    """
    result = analyze_channel_attribution(db, event_id)
    return result


@router.get("/learning/optimal-pricing")
@limiter.limit("20/minute")
async def get_optimal_pricing(
    request: Request,
    venue_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Learn optimal pricing from historical data.

    Analyzes past events to find pricing that maximizes revenue.

    **Filters:**
    - venue_id: Learn for specific venue
    - category_id: Learn for specific category

    **Use Cases:**
    - "What's the best price point for concerts at this venue?"
    - "Learn from past jazz events"
    """
    result = learn_optimal_pricing(db, venue_id, category_id)
    return result


@router.get("/learning/send-time-patterns")
@limiter.limit("20/minute")
async def get_send_time_patterns(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Learn which email send times drive the most conversions.

    Returns:
    - Best hour of day
    - Best day of week
    - Conversion rates by time

    **Use Cases:**
    - "When should I send marketing emails?"
    - "What time gets best open rates?"
    """
    result = learn_send_time_patterns(db)
    return result


@router.get("/events/{event_id}/predict-performance")
@limiter.limit("20/minute")
async def predict_performance(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Predict event performance based on similar past events.

    Forecasts:
    - Expected sell-through rate
    - Predicted ticket sales
    - Revenue forecast
    - Confidence level

    **Use Cases:**
    - "How many tickets will this event sell?"
    - "Predict revenue for event 123"
    - "Compare to similar past events"
    """
    result = predict_event_performance(db, event_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/learning/ab-test/{test_name}")
@limiter.limit("20/minute")
async def get_ab_test_results(
    request: Request,
    test_name: str,
    db: Session = Depends(get_db),
):
    """
    Get A/B test results and winning variant.

    **Available Tests:**
    - email_subject_line
    - ad_creative

    Returns winner and improvement percentage.
    """
    result = run_ab_test_analysis(db, test_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============== Cross-Event Intelligence Endpoints ==============

@router.get("/customers/best")
@limiter.limit("20/minute")
async def get_best_customers(
    request: Request,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """
    Identify top customers by RFM analysis.

    RFM = Recency, Frequency, Monetary value

    Returns:
    - VIP customers
    - High-value customers
    - RFM scores
    - Recommendations

    **Use Cases:**
    - "Who are my best customers?"
    - "Show me VIP segment"
    - "Get customer profiles for targeting"
    """
    result = identify_best_customers(db, limit)
    return result


@router.get("/patterns/events")
@limiter.limit("20/minute")
async def get_event_patterns(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Identify successful patterns across all events.

    Analyzes:
    - Best-performing venues
    - Most profitable categories
    - Seasonal trends
    - Success patterns

    **Use Cases:**
    - "What venue works best?"
    - "When should I schedule events?"
    - "Which categories are most profitable?"
    """
    result = find_event_patterns(db)
    return result


@router.get("/events/{event_id}/lookalike-audience")
@limiter.limit("20/minute")
async def get_lookalike_audience(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Build lookalike audience from event attendees.

    Finds customers who:
    - Attended similar events
    - Match demographic profile
    - Haven't attended this event yet

    **Use Cases:**
    - "Find similar customers to invite"
    - "Build targeting list for event 123"
    - "Who else should I market to?"
    """
    result = build_lookalike_audience(db, event_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/customers/churn-risk")
@limiter.limit("20/minute")
async def get_churn_risk(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Identify customers at risk of churning.

    Flags customers who:
    - Haven't purchased in 90+ days
    - Previously were active (2+ purchases)
    - Need retention campaigns

    Returns win-back recommendations.

    **Use Cases:**
    - "Who's about to churn?"
    - "Show me inactive customers"
    - "Who needs a win-back campaign?"
    """
    result = detect_churn_risk(db)
    return result


@router.get("/events/{event_id}/compare")
@limiter.limit("20/minute")
async def compare_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Compare event to similar past events.

    Shows how current event performs vs:
    - Same venue events
    - Same category events
    - Similar pricing events

    **Use Cases:**
    - "How does this event compare?"
    - "Am I doing better than similar events?"
    - "Compare event 123 to past events"
    """
    result = compare_similar_events(db, event_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
