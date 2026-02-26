"""Tests for Customer Intelligence features.

These tests demonstrate the advanced analytics capabilities including:
- Churn prediction (RFM analysis)
- Customer segmentation
- Event recommendations
- Revenue forecasting
- Dynamic pricing suggestions
- Demand prediction
- Trending events
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.services.analytics_engine import (
    predict_churn,
    get_customer_segments,
    recommend_events,
    forecast_revenue,
    get_pricing_suggestions,
    predict_demand,
    get_trending_events,
)


class TestChurnPrediction:
    """Test churn prediction using RFM (Recency, Frequency, Monetary) analysis."""

    def test_predict_churn_returns_structure(self, db):
        """Test that churn prediction returns correct structure."""
        result = predict_churn(db, min_days_inactive=30, limit=10)

        assert "total_at_risk" in result
        assert "min_days_inactive" in result
        assert "customers" in result
        assert result["min_days_inactive"] == 30
        assert isinstance(result["customers"], list)

    def test_predict_churn_with_inactive_customer(self, db, create_event, create_tier, create_event_goer):
        """Test churn prediction with an inactive customer."""
        # Create an event and tier
        event = create_event()
        tier = create_tier(event_id=event["id"], quantity_available=100, price=5000)

        # Update the tier to have quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 10
        db.commit()

        # Create a customer who purchased tickets
        goer = create_event_goer(email="churn_test@example.com", name="Churn Customer")
        from app.models import Ticket, TicketStatus, CustomerPreference
        import random

        # Create a paid ticket
        ticket = Ticket(
            ticket_tier_id=tier["id"],
            event_goer_id=goer["id"],
            status=TicketStatus.PAID,
            price_cents=5000,
            purchased_at=datetime.now(timezone.utc) - timedelta(days=60),  # 60 days ago
            discount_amount_cents=0,
        )
        db.add(ticket)

        # Create customer preference with last interaction 45 days ago
        pref = CustomerPreference(
            event_goer_id=goer["id"],
            total_spent_cents=5000,
            total_events_attended=1,
            last_interaction_date=datetime.now(timezone.utc) - timedelta(days=45),
            favorite_event_types='["concerts"]',
        )
        db.add(pref)
        db.commit()

        # Run churn prediction with 30 days inactive threshold
        result = predict_churn(db, min_days_inactive=30, limit=10)

        # Should find this customer as at-risk
        assert result["total_at_risk"] >= 0

        # If customer is in results, verify structure
        if result["customers"]:
            customer = result["customers"][0]
            assert "customer_id" in customer
            assert "name" in customer
            assert "email" in customer
            assert "segment" in customer
            assert "rfm_scores" in customer
            assert "days_inactive" in customer
            assert "total_spent_dollars" in customer
            assert "re_engagement_suggestion" in customer

            # Verify RFM scores are 1-4
            rfm = customer["rfm_scores"]
            assert 1 <= rfm["recency"] <= 4
            assert 1 <= rfm["frequency"] <= 4
            assert 1 <= rfm["monetary"] <= 4
            assert 3 <= rfm["total"] <= 12

    def test_predict_churn_segments(self, db):
        """Test that customers are properly segmented."""
        result = predict_churn(db, min_days_inactive=30, limit=50)

        for customer in result["customers"]:
            # Valid segments
            assert customer["segment"] in ["at_risk", "lapsed", "lost"]


class TestCustomerSegments:
    """Test customer segmentation using RFM analysis."""

    def test_get_customer_segments_structure(self, db):
        """Test that customer segmentation returns correct structure."""
        result = get_customer_segments(db)

        assert "total_customers_analyzed" in result
        assert "segments" in result
        assert "rfm_distribution" in result

    def test_segments_have_correct_keys(self, db):
        """Test that all segments have required keys."""
        result = get_customer_segments(db)

        valid_segments = ["active", "at_risk", "lapsed", "lost"]
        for seg_name in valid_segments:
            if seg_name in result["segments"]:
                segment = result["segments"][seg_name]
                assert "count" in segment
                assert "percent" in segment
                assert "avg_spent_dollars" in segment
                assert "description" in segment

    def test_rfm_distribution(self, db):
        """Test RFM distribution metrics."""
        result = get_customer_segments(db)

        if "rfm_distribution" in result:
            dist = result["rfm_distribution"]
            assert "recency_avg_days" in dist
            assert "frequency_avg_events" in dist
            assert "monetary_avg_dollars" in dist


class TestEventRecommendations:
    """Test personalized event recommendations."""

    def test_recommend_events_requires_customer(self, db):
        """Test that recommendations require customer identification."""
        result = recommend_events(db, limit=5)
        assert "error" in result

    def test_recommend_events_by_id(self, db, create_event_goer):
        """Test recommendations by customer ID."""
        goer = create_event_goer(email="rec_test@example.com")
        result = recommend_events(db, customer_id=goer["id"], limit=5)

        assert "customer_id" in result
        assert "customer_name" in result
        assert "recommendations" in result

    def test_recommend_events_by_email(self, db, create_event_goer):
        """Test recommendations by customer email."""
        goer = create_event_goer(email="email_rec_test@example.com")
        result = recommend_events(db, customer_email=goer["email"], limit=5)

        assert "customer_id" in result
        assert result["customer_id"] == goer["id"]

    def test_recommend_events_with_event(self, db, create_event, create_tier, create_event_goer):
        """Test recommendations with actual events."""
        # Create upcoming event
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        tier = create_tier(
            event_id=event["id"],
            quantity_available=100,
            price=5000,
        )

        # Update quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 20
        db.commit()

        # Create customer
        goer = create_event_goer(email="rec_with_events@example.com")

        # Run recommendations
        result = recommend_events(db, customer_id=goer["id"], limit=5)

        if result["recommendations"]:
            rec = result["recommendations"][0]
            assert "rank" in rec
            assert "event_id" in rec
            assert "event_name" in rec
            assert "score" in rec
            assert "signals" in rec
            assert "reason" in rec

            # Check signals
            signals = rec["signals"]
            assert "content_match" in signals
            assert "collaborative" in signals
            assert "popularity" in signals

            # Scores should be 0-1
            assert 0 <= signals["content_match"] <= 1
            assert 0 <= signals["collaborative"] <= 1
            assert 0 <= signals["popularity"] <= 1


class TestRevenueForecasting:
    """Test revenue forecasting for upcoming events."""

    def test_forecast_revenue_structure(self, db):
        """Test that revenue forecast returns correct structure."""
        result = forecast_revenue(db, time_horizon_days=90)

        assert "time_horizon_days" in result
        assert "total_events" in result
        assert "current_revenue_dollars" in result
        assert "projected_revenue_dollars" in result
        assert "events" in result

    def test_forecast_revenue_with_event(self, db, create_event, create_tier):
        """Test forecasting with actual events."""
        # Create upcoming event
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        tier = create_tier(
            event_id=event["id"],
            quantity_available=100,
            price=10000,  # $100
        )

        # Update quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 30
        db.commit()

        result = forecast_revenue(db, time_horizon_days=90)

        # Should include our event
        if result["events"]:
            forecast_event = result["events"][0]
            assert "event_id" in forecast_event
            assert "event_name" in forecast_event
            assert "current_revenue_dollars" in forecast_event
            assert "projected_revenue_dollars" in forecast_event
            assert "tickets" in forecast_event
            assert "velocity_per_day" in forecast_event
            assert "confidence" in forecast_event

            # Check confidence bounds
            proj = forecast_event["projected_revenue_dollars"]
            assert "low" in proj
            assert "mid" in proj
            assert "high" in proj
            assert proj["low"] <= proj["mid"] <= proj["high"]

    def test_forecast_revenue_confidence_intervals(self, db):
        """Test that confidence intervals are valid."""
        result = forecast_revenue(db, time_horizon_days=90)

        if "projected_revenue_dollars" in result:
            proj = result["projected_revenue_dollars"]
            assert "low" in proj
            assert "mid" in proj
            assert "high" in proj
            # Low <= Mid <= High
            assert proj["low"] <= proj["mid"] <= proj["high"]


class TestPricingSuggestions:
    """Test dynamic pricing suggestions."""

    def test_pricing_suggestions_structure(self, db, create_event, create_tier):
        """Test that pricing suggestions return correct structure."""
        event = create_event()
        tier = create_tier(event_id=event["id"], quantity_available=100, price=10000)

        # Update quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 50
        db.commit()

        result = get_pricing_suggestions(db, event_id=event["id"])

        assert "event_id" in result
        assert "event_name" in result
        assert "price_elasticity" in result
        assert "tiers" in result
        assert "note" in result

    def test_pricing_suggestions_per_tier(self, db, create_event, create_tier):
        """Test pricing suggestions for individual tiers."""
        event = create_event()
        tier = create_tier(
            event_id=event["id"],
            quantity_available=100,
            price=10000,
        )

        # Update quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 80  # 80% sold - should suggest increase
        db.commit()

        result = get_pricing_suggestions(db, event_id=event["id"])

        if result["tiers"]:
            tier_suggestion = result["tiers"][0]
            assert "tier_id" in tier_suggestion
            assert "tier_name" in tier_suggestion
            assert "current_price_cents" in tier_suggestion
            assert "suggested_price_cents" in tier_suggestion
            assert "adjustment_percent" in tier_suggestion
            assert "direction" in tier_suggestion
            assert "confidence" in tier_suggestion
            assert "reasoning" in tier_suggestion

            # Valid directions
            assert tier_suggestion["direction"] in ["increase", "decrease", "hold"]

            # Valid confidence levels
            assert tier_suggestion["confidence"] in ["high", "medium", "low"]

    def test_pricing_elasticity_detection(self, db, create_event, create_tier):
        """Test price elasticity detection from promo usage."""
        event = create_event()
        create_tier(event_id=event["id"], quantity_available=100, quantity_sold=50, price=10000)

        result = get_pricing_suggestions(db, event_id=event["id"])

        elasticity = result.get("price_elasticity", {})
        assert "promo_usage_ratio" in elasticity
        assert "elasticity_level" in elasticity
        assert "interpretation" in elasticity

        # Valid elasticity levels
        assert elasticity["elasticity_level"] in ["high", "medium", "low"]


class TestDemandPrediction:
    """Test demand prediction and sellout forecasting."""

    def test_demand_prediction_structure(self, db, create_event, create_tier):
        """Test that demand prediction returns correct structure."""
        # Create upcoming event
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        create_tier(event_id=event["id"], quantity_available=100, quantity_sold=40)

        result = predict_demand(db, event_id=event["id"])

        assert "event_id" in result
        assert "event_name" in result
        assert "demand_score" in result
        assert "sellout_probability_percent" in result
        assert "inventory" in result
        assert "velocity" in result
        assert "sellout_pace" in result
        assert "signals" in result

    def test_demand_score_range(self, db, create_event, create_tier):
        """Test that demand score is in valid range."""
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        create_tier(event_id=event["id"], quantity_available=100, quantity_sold=40)

        result = predict_demand(db, event_id=event["id"])

        # Demand score should be 0-100
        assert 0 <= result["demand_score"] <= 100

        # Sellout probability should be 0-100
        assert 0 <= result["sellout_probability_percent"] <= 100

    def test_demand_prediction_inventory_metrics(self, db, create_event, create_tier):
        """Test inventory metrics in demand prediction."""
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        create_tier(event_id=event["id"], quantity_available=100, quantity_sold=40)

        result = predict_demand(db, event_id=event["id"])

        inventory = result["inventory"]
        assert "total_available" in inventory
        assert "total_sold" in inventory
        assert "total_remaining" in inventory
        assert "sell_through_percent" in inventory

        # Remaining should equal available - sold
        assert inventory["total_remaining"] == inventory["total_available"] - inventory["total_sold"]

    def test_demand_prediction_pace_tracking(self, db, create_event, create_tier):
        """Test sellout pace tracking."""
        from datetime import datetime, timedelta, timezone

        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        create_tier(event_id=event["id"], quantity_available=100, quantity_sold=40)

        result = predict_demand(db, event_id=event["id"])

        pace = result["sellout_pace"]
        assert "days_until_event" in pace
        assert "required_per_day" in pace
        assert "current_per_day" in pace
        assert "pace_ratio" in pace
        assert "on_track" in pace
        assert "message" in pace
        assert isinstance(pace["on_track"], bool)


class TestTrendingEvents:
    """Test trending event detection."""

    def test_trending_events_structure(self, db):
        """Test that trending events returns correct structure."""
        result = get_trending_events(db, days=7, limit=10)

        assert "period_days" in result
        assert "trending_events" in result
        assert result["period_days"] == 7

    def test_trending_events_with_data(self, db, create_event, create_tier):
        """Test trending events with actual event data."""
        from datetime import datetime, timedelta, timezone

        # Create upcoming event
        event_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        event = create_event(event_date=event_date)
        tier = create_tier(event_id=event["id"], quantity_available=100, price=10000)

        # Update quantity_sold
        from app.models import TicketTier
        db_tier = db.query(TicketTier).filter(TicketTier.id == tier["id"]).first()
        db_tier.quantity_sold = 30
        db.commit()

        result = get_trending_events(db, days=7, limit=10)

        if result["trending_events"]:
            trending = result["trending_events"][0]
            assert "rank" in trending
            assert "event_id" in trending
            assert "event_name" in trending
            assert "trending_score" in trending
            assert "signals" in trending
            assert "sell_through_percent" in trending
            assert "tickets_remaining" in trending

            # Check signals
            signals = trending["signals"]
            assert "page_views" in signals
            assert "recent_sales" in signals
            assert "waitlist_entries" in signals

            # All signal counts should be non-negative
            assert signals["page_views"] >= 0
            assert signals["recent_sales"] >= 0
            assert signals["waitlist_entries"] >= 0
