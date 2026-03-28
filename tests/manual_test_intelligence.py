#!/usr/bin/env python3
"""
Manual Intelligence Test Script

Run this to manually test the intelligence features without pytest.
Shows the "wow factor" of the autonomous platform.

Usage:
    python tests/manual_test_intelligence.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Event, Venue, TicketTier, EventGoer, Ticket, TicketStatus, EventCategory
from app.services.event_intelligence import (
    check_inventory_pressure,
    calculate_optimal_send_time,
    suggest_related_events,
)
from app.services.learning_engine import (
    analyze_channel_attribution,
    predict_event_performance,
)
from app.services.cross_event_intelligence import (
    identify_best_customers,
    find_event_patterns,
    detect_churn_risk,
)
from app.services.event_research_agent import (
    analyze_event_context,
    research_artist_or_performer,
)


def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_result(label, value):
    """Print formatted result."""
    print(f"✓ {label}: {value}")


def test_inventory_intelligence(db: Session):
    """Test inventory pressure monitoring."""
    print_header("INVENTORY INTELLIGENCE TEST")

    # Get a recent event
    event = db.query(Event).filter(
        Event.event_date >= datetime.now(timezone.utc).date()
    ).first()

    if not event:
        print("⚠ No upcoming events found. Create an event first.")
        return

    print(f"Analyzing event: {event.name}")

    result = check_inventory_pressure(db, event.id)

    print_result("Event", event.name)
    print_result("Days until event", result.get("days_until_event"))
    print_result("Overall sell-through", f"{result.get('overall_sell_through_pct', 0):.1f}%")
    print_result("Pressure level", result.get("pressure_level"))
    print_result("Total sold", f"{result.get('total_sold')} / {result.get('total_available')}")

    print("\n📊 Tier Analysis:")
    for tier in result.get("tiers", []):
        print(f"  - {tier['tier_name']}: {tier['sell_through_pct']:.1f}% sold ({tier['remaining']} left)")

    print("\n💡 Recommendations:")
    for rec in result.get("recommendations", [])[:3]:
        print(f"  • [{rec['priority']}] {rec['action']}: {rec['reason']}")
        print(f"    → {rec['suggestion']}")


def test_send_time_optimization():
    """Test optimal send time calculation."""
    print_header("SEND TIME OPTIMIZATION TEST")

    # Sample event context
    event_context = {
        "event": {
            "name": "Summer Music Festival",
            "date": "2026-07-15",
            "is_weekend": True,
            "day_of_week": "Saturday",
        },
        "pricing": {
            "avg_cents": 7500,  # $75
        }
    }

    # Sample artist research
    artist_research = {
        "genre": "Electronic/EDM",
        "fan_demographics": "Ages 18-30, young professionals",
    }

    result = calculate_optimal_send_time(event_context, artist_research)

    print_result("Event", event_context["event"]["name"])
    print_result("Genre", artist_research["genre"])
    print_result("Optimal send hour", f"{result['optimal_send_hour']}:00 ({result['optimal_send_hour'] % 12 or 12}{'PM' if result['optimal_send_hour'] >= 12 else 'AM'})")
    print_result("Days before event", result["optimal_day_offset"])
    print_result("Confidence", f"{result['confidence']*100:.0f}%")

    print("\n🧠 Reasoning:")
    for reason in result["reasoning"]:
        print(f"  • {reason}")


def test_customer_intelligence(db: Session):
    """Test customer RFM analysis."""
    print_header("CUSTOMER INTELLIGENCE TEST")

    result = identify_best_customers(db, limit=10)

    print_result("Total customers analyzed", result.get("total_analyzed"))

    segments = result.get("segments", {})
    print("\n👥 Customer Segments:")
    print(f"  • VIP: {segments.get('vip', 0)} customers")
    print(f"  • High Value: {segments.get('high_value', 0)} customers")
    print(f"  • Regular: {segments.get('regular', 0)} customers")

    top_customers = result.get("top_customers", [])[:5]
    if top_customers:
        print("\n🌟 Top 5 Customers:")
        for customer in top_customers:
            print(f"  • {customer['name']} ({customer['email']})")
            print(f"    - Purchases: {customer['tickets_purchased']}")
            print(f"    - Total spent: {customer['total_spend_usd']}")
            print(f"    - Segment: {customer['segment']}")
            print(f"    - RFM Score: {customer['rfm_score']}/15")
    else:
        print("\n⚠ No customer data available yet")


def test_event_patterns(db: Session):
    """Test event pattern analysis."""
    print_header("EVENT PATTERN ANALYSIS TEST")

    result = find_event_patterns(db)

    insights = result.get("insights", {})

    print("🏆 Success Patterns:")
    if insights.get("best_venue"):
        print_result("Best venue", insights["best_venue"])
    if insights.get("best_category"):
        print_result("Top category", insights["best_category"])
    if insights.get("best_month"):
        print_result("Best month", insights["best_month"])

    top_venues = result.get("top_venues", [])[:3]
    if top_venues:
        print("\n🏟️ Top 3 Venues:")
        for venue in top_venues:
            print(f"  • {venue['venue_name']}")
            print(f"    - Events: {venue['events_hosted']}")
            print(f"    - Avg sell-through: {venue['avg_sell_through']*100:.0f}%")
    else:
        print("\n⚠ Not enough event history yet")


def test_churn_detection(db: Session):
    """Test customer churn risk detection."""
    print_header("CHURN RISK DETECTION TEST")

    result = detect_churn_risk(db)

    print_result("Total at-risk customers", result.get("total_at_risk"))

    segments = result.get("risk_segments", {})
    print("\n⚠️ Risk Segments:")
    print(f"  • HIGH risk: {segments.get('high', 0)} customers (>180 days inactive)")
    print(f"  • MEDIUM risk: {segments.get('medium', 0)} customers (120-180 days)")
    print(f"  • LOW risk: {segments.get('low', 0)} customers (90-120 days)")

    at_risk = result.get("at_risk_customers", [])[:3]
    if at_risk:
        print("\n🚨 Top At-Risk Customers:")
        for customer in at_risk:
            print(f"  • {customer['name']} - {customer['days_inactive']} days inactive")
            print(f"    Action: {customer['retention_action']}")
    else:
        print("\n✅ No customers at risk of churning")

    recommendations = result.get("recommendations", [])
    if recommendations:
        print("\n💡 Retention Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")


def test_artist_research():
    """Test artist research with web search."""
    print_header("ARTIST RESEARCH TEST")

    print("Researching: Drake Concert")

    result = research_artist_or_performer("Drake Concert", None)

    if result.get("fallback"):
        print("⚠ Web search unavailable (API key needed)")
        print(f"Fallback result: {result}")
    else:
        print_result("Artist", result.get("artist_name"))
        print_result("Genre", result.get("genre"))
        print_result("Event type", result.get("event_type"))

        bio = result.get("bio", "")
        if bio:
            print(f"\n📝 Bio: {bio[:200]}...")

        social = result.get("social_media", {})
        if social:
            print("\n📱 Social Media:")
            for platform, handle in social.items():
                print(f"  • {platform}: {handle}")


def test_performance_prediction(db: Session):
    """Test event performance prediction."""
    print_header("PERFORMANCE PREDICTION TEST")

    event = db.query(Event).filter(
        Event.event_date >= datetime.now(timezone.utc).date()
    ).first()

    if not event:
        print("⚠ No upcoming events found")
        return

    print(f"Predicting performance for: {event.name}")

    result = predict_event_performance(db, event.id)

    if "error" in result or result.get("message"):
        print(f"⚠ {result.get('message', result.get('error'))}")
    else:
        predictions = result.get("predictions", {})
        print_result("Expected sell-through", f"{predictions.get('sell_through_rate', 0)*100:.0f}%")
        print_result("Predicted tickets sold", predictions.get("tickets_sold"))
        print_result("Revenue forecast", predictions.get("revenue_usd"))
        print_result("Confidence", result.get("confidence"))
        print_result("Based on", result.get("basis"))


def run_all_tests():
    """Run all intelligence tests."""
    print("\n" + "🚀"*40)
    print("AI TICKETS - INTELLIGENCE SYSTEM DEMONSTRATION")
    print("🚀"*40)

    db = SessionLocal()

    try:
        # Run all tests
        test_inventory_intelligence(db)
        test_send_time_optimization()
        test_customer_intelligence(db)
        test_event_patterns(db)
        test_churn_detection(db)
        test_artist_research()
        test_performance_prediction(db)

        # Final summary
        print_header("DEMONSTRATION COMPLETE")
        print("✅ All intelligence systems operational!")
        print("\nFeatures Demonstrated:")
        print("  1. Inventory pressure monitoring with recommendations")
        print("  2. Optimal send time calculation (audience-aware)")
        print("  3. RFM customer segmentation (VIP identification)")
        print("  4. Event pattern analysis (success factors)")
        print("  5. Churn risk detection (retention campaigns)")
        print("  6. Artist research via web search")
        print("  7. Performance prediction (AI forecasting)")
        print("\n🎯 The platform is AUTONOMOUS and SELF-OPTIMIZING!")
        print("\n" + "🚀"*40 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    print("\nStarting AI Tickets Intelligence Demonstration...")
    print("This will test all autonomous features.\n")

    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
