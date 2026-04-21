"""
Predictive Intelligence Engine
Advanced predictions for events, pricing, demand, and customer behavior
"""

import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.models import Event, EventGoer, Ticket, TicketTier, Weather


class PredictionType(str, Enum):
    SELLOUT_TIME = "sellout_time"
    OPTIMAL_PRICE = "optimal_price"
    DEMAND_FORECAST = "demand_forecast"
    CUSTOMER_BEHAVIOR = "customer_behavior"
    NO_SHOW_RATE = "no_show_rate"
    REVENUE_FORECAST = "revenue_forecast"
    MARKETING_ROI = "marketing_roi"
    CHURN_RISK = "churn_risk"
    VIRAL_POTENTIAL = "viral_potential"
    WEATHER_IMPACT = "weather_impact"


@dataclass
class PredictionModel:
    """Model for a specific type of prediction"""
    model_id: str
    prediction_type: PredictionType
    features: List[str]
    weights: Dict[str, float]
    accuracy: float
    last_trained: datetime
    training_samples: int


@dataclass
class Prediction:
    """Single prediction result"""
    prediction_id: str
    prediction_type: PredictionType
    target: str  # What we're predicting for (event_id, customer_id, etc.)
    value: Any  # Predicted value
    confidence: float
    confidence_interval: Tuple[float, float]  # Lower and upper bounds
    factors: Dict[str, float]  # Contributing factors and their weights
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = None  # When prediction becomes stale
    metadata: Dict = field(default_factory=dict)


@dataclass
class PredictionAlert:
    """Alert based on prediction"""
    alert_id: str
    prediction_id: str
    alert_type: str  # opportunity, risk, anomaly
    message: str
    recommended_action: str
    urgency: str  # immediate, high, medium, low
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PredictiveIntelligenceEngine:
    """Main engine for predictive analytics"""

    def __init__(self, db: Session):
        self.db = db
        self.models: Dict[PredictionType, PredictionModel] = self._initialize_models()
        self.predictions: List[Prediction] = []
        self.alerts: List[PredictionAlert] = []
        self.historical_accuracy: Dict[PredictionType, List[float]] = defaultdict(list)

    def _initialize_models(self) -> Dict[PredictionType, PredictionModel]:
        """Initialize prediction models"""

        models = {}

        # Sellout time prediction model
        models[PredictionType.SELLOUT_TIME] = PredictionModel(
            model_id="sellout_v1",
            prediction_type=PredictionType.SELLOUT_TIME,
            features=["current_sales", "days_remaining", "artist_popularity", "day_of_week", "price_point"],
            weights={
                "current_sales": 0.35,
                "days_remaining": -0.25,
                "artist_popularity": 0.20,
                "day_of_week": 0.10,
                "price_point": -0.10
            },
            accuracy=0.82,
            last_trained=datetime.utcnow(),
            training_samples=500
        )

        # Optimal pricing model
        models[PredictionType.OPTIMAL_PRICE] = PredictionModel(
            model_id="pricing_v1",
            prediction_type=PredictionType.OPTIMAL_PRICE,
            features=["competitor_price", "demand_velocity", "artist_tier", "venue_capacity", "day_of_week"],
            weights={
                "competitor_price": 0.30,
                "demand_velocity": 0.25,
                "artist_tier": 0.20,
                "venue_capacity": -0.15,
                "day_of_week": 0.10
            },
            accuracy=0.78,
            last_trained=datetime.utcnow(),
            training_samples=1000
        )

        # Demand forecast model
        models[PredictionType.DEMAND_FORECAST] = PredictionModel(
            model_id="demand_v1",
            prediction_type=PredictionType.DEMAND_FORECAST,
            features=["historical_demand", "seasonality", "marketing_spend", "social_buzz", "weather"],
            weights={
                "historical_demand": 0.30,
                "seasonality": 0.20,
                "marketing_spend": 0.20,
                "social_buzz": 0.20,
                "weather": 0.10
            },
            accuracy=0.75,
            last_trained=datetime.utcnow(),
            training_samples=2000
        )

        return models

    async def predict_sellout_time(self, event_id: int) -> Prediction:
        """Predict when event will sell out"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Get current sales data
        tickets_sold = self.db.query(Ticket).filter(
            Ticket.event_id == event_id,
            Ticket.status == "paid"
        ).count()

        total_capacity = self.db.query(func.sum(TicketTier.quantity_available)).filter(
            TicketTier.event_id == event_id
        ).scalar() or 500

        # Calculate features
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
        days_remaining = (event_date - datetime.now()).days
        current_sales_rate = tickets_sold / total_capacity

        # Simple prediction logic (would use ML model in production)
        if current_sales_rate > 0.8 and days_remaining > 7:
            predicted_days = days_remaining * (1 - current_sales_rate) * 2
            confidence = 0.90
        elif current_sales_rate > 0.5:
            predicted_days = days_remaining * (1 - current_sales_rate) * 3
            confidence = 0.75
        else:
            # May not sell out
            predicted_days = days_remaining + 30
            confidence = 0.60

        sellout_date = datetime.now() + timedelta(days=predicted_days)

        # Create prediction
        prediction = Prediction(
            prediction_id=f"sellout_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.SELLOUT_TIME,
            target=str(event_id),
            value=sellout_date if predicted_days <= days_remaining else None,
            confidence=confidence,
            confidence_interval=(
                predicted_days * 0.8,
                predicted_days * 1.2
            ),
            factors={
                "current_sales_rate": current_sales_rate,
                "days_remaining": days_remaining,
                "sales_velocity": tickets_sold / max(1, (total_capacity - tickets_sold))
            },
            expires_at=datetime.now() + timedelta(hours=24),
            metadata={
                "will_sell_out": predicted_days <= days_remaining,
                "urgency_level": "high" if predicted_days < 3 else "medium" if predicted_days < 7 else "low"
            }
        )

        self.predictions.append(prediction)

        # Generate alert if selling out soon
        if predicted_days < 3 and confidence > 0.7:
            alert = PredictionAlert(
                alert_id=f"alert_{prediction.prediction_id}",
                prediction_id=prediction.prediction_id,
                alert_type="opportunity",
                message=f"Event {event.name} predicted to sell out in {predicted_days:.0f} days!",
                recommended_action="Increase prices by 15-20% to capture maximum value",
                urgency="high"
            )
            self.alerts.append(alert)

        return prediction

    async def predict_optimal_price(self, event_id: int, tier_name: str = "General") -> Prediction:
        """Predict optimal pricing for maximizing revenue"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Get historical pricing data
        similar_events = self.db.query(Event).filter(
            Event.id != event_id,
            Event.venue_id == event.venue_id
        ).limit(10).all()

        if similar_events:
            # Get average successful prices
            avg_prices = []
            for similar_event in similar_events:
                tiers = self.db.query(TicketTier).filter(
                    TicketTier.event_id == similar_event.id
                ).all()
                if tiers:
                    avg_prices.append(statistics.mean(t.price for t in tiers))

            base_price = statistics.mean(avg_prices) if avg_prices else 50
        else:
            base_price = 50  # Default

        # Adjust based on factors
        adjustments = {
            "artist_popularity": 1.0,  # Would calculate from artist data
            "day_of_week": 1.1 if event.event_date.endswith(('5', '6')) else 0.9,  # Fri/Sat premium
            "seasonality": 1.05,  # Summer premium
            "demand_signals": 1.0  # Would calculate from current interest
        }

        optimal_price = base_price
        for factor, multiplier in adjustments.items():
            optimal_price *= multiplier

        # Calculate confidence based on data availability
        confidence = 0.7 if similar_events else 0.5

        prediction = Prediction(
            prediction_id=f"pricing_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.OPTIMAL_PRICE,
            target=f"{event_id}_{tier_name}",
            value=round(optimal_price, 0),
            confidence=confidence,
            confidence_interval=(
                optimal_price * 0.85,
                optimal_price * 1.15
            ),
            factors=adjustments,
            expires_at=datetime.now() + timedelta(days=7),
            metadata={
                "base_price": base_price,
                "price_elasticity": -1.5,  # Would calculate
                "revenue_maximizing": True
            }
        )

        self.predictions.append(prediction)
        return prediction

    async def predict_demand(self, event_id: int, days_ahead: int = 30) -> Prediction:
        """Predict ticket demand over time"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Get current sales trajectory
        tickets_sold = self.db.query(Ticket).filter(
            Ticket.event_id == event_id,
            Ticket.status == "paid"
        ).count()

        # Calculate daily demand (simplified)
        days_on_sale = 30  # Would calculate actual
        current_daily_rate = tickets_sold / max(1, days_on_sale)

        # Predict future demand curve
        demand_curve = []
        for day in range(days_ahead):
            # Demand typically increases as event approaches
            urgency_multiplier = 1 + (0.05 * (days_ahead - day))

            # Weekend boost
            day_of_week = (datetime.now() + timedelta(days=day)).weekday()
            weekend_multiplier = 1.3 if day_of_week in [4, 5] else 1.0

            daily_demand = current_daily_rate * urgency_multiplier * weekend_multiplier
            demand_curve.append(daily_demand)

        total_predicted_demand = sum(demand_curve)

        prediction = Prediction(
            prediction_id=f"demand_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.DEMAND_FORECAST,
            target=str(event_id),
            value={
                "total_demand": total_predicted_demand,
                "daily_curve": demand_curve[:7],  # First week
                "peak_day": demand_curve.index(max(demand_curve))
            },
            confidence=0.72,
            confidence_interval=(
                total_predicted_demand * 0.7,
                total_predicted_demand * 1.3
            ),
            factors={
                "current_velocity": current_daily_rate,
                "urgency_effect": 0.05,
                "weekend_effect": 0.3
            },
            expires_at=datetime.now() + timedelta(days=1),
            metadata={
                "demand_classification": "high" if total_predicted_demand > 300 else "medium" if total_predicted_demand > 150 else "low"
            }
        )

        self.predictions.append(prediction)
        return prediction

    async def predict_no_show_rate(self, event_id: int) -> Prediction:
        """Predict percentage of ticket holders who won't attend"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Factors affecting no-show rate
        factors = {
            "weather_forecast": 0.0,  # Would get actual forecast
            "day_of_week": 0.05 if event.event_date.endswith(('1', '2', '3')) else 0.0,  # Weekday penalty
            "price_point": 0.0,  # Higher price = lower no-show
            "advance_purchase": 0.05,  # Early purchases have higher no-show
            "event_type": 0.0  # Some event types have higher no-shows
        }

        # Base no-show rate
        base_rate = 0.10  # 10% baseline

        # Apply factors
        predicted_rate = base_rate
        for factor, adjustment in factors.items():
            predicted_rate += adjustment

        # Cap between 0 and 0.3 (30% max)
        predicted_rate = max(0, min(0.3, predicted_rate))

        tickets_sold = self.db.query(Ticket).filter(
            Ticket.event_id == event_id,
            Ticket.status == "paid"
        ).count()

        predicted_no_shows = int(tickets_sold * predicted_rate)

        prediction = Prediction(
            prediction_id=f"noshow_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.NO_SHOW_RATE,
            target=str(event_id),
            value=predicted_rate,
            confidence=0.68,
            confidence_interval=(
                predicted_rate * 0.8,
                predicted_rate * 1.2
            ),
            factors=factors,
            expires_at=datetime.strptime(event.event_date, "%Y-%m-%d"),
            metadata={
                "predicted_no_shows": predicted_no_shows,
                "recommended_oversell": int(predicted_no_shows * 0.7)  # Conservative oversell
            }
        )

        self.predictions.append(prediction)
        return prediction

    async def predict_customer_next_purchase(self, customer_id: int) -> Prediction:
        """Predict customer's next purchase behavior"""

        customer = self.db.query(EventGoer).filter(EventGoer.id == customer_id).first()
        if not customer:
            return None

        # Get purchase history
        past_tickets = self.db.query(Ticket).filter(
            Ticket.event_goer_id == customer_id,
            Ticket.status == "paid"
        ).order_by(desc(Ticket.created_at)).limit(10).all()

        if not past_tickets:
            # New customer
            prediction_value = {
                "days_until_purchase": 30,
                "likely_price_range": [30, 60],
                "likely_event_type": "concert",
                "purchase_probability": 0.3
            }
            confidence = 0.5
        else:
            # Calculate purchase patterns
            purchase_intervals = []
            for i in range(len(past_tickets) - 1):
                interval = (past_tickets[i].created_at - past_tickets[i + 1].created_at).days
                purchase_intervals.append(interval)

            avg_interval = statistics.mean(purchase_intervals) if purchase_intervals else 60
            avg_price = statistics.mean(t.price_paid for t in past_tickets)

            # Predict next purchase
            last_purchase = past_tickets[0].created_at
            days_since_last = (datetime.utcnow() - last_purchase).days
            days_until_next = max(0, avg_interval - days_since_last)

            # Purchase probability increases as we approach typical interval
            if days_since_last >= avg_interval:
                probability = 0.8
            else:
                probability = (days_since_last / avg_interval) * 0.8

            prediction_value = {
                "days_until_purchase": days_until_next,
                "likely_price_range": [avg_price * 0.8, avg_price * 1.2],
                "likely_event_type": "concert",  # Would analyze past events
                "purchase_probability": probability
            }
            confidence = 0.75

        prediction = Prediction(
            prediction_id=f"customer_{customer_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.CUSTOMER_BEHAVIOR,
            target=str(customer_id),
            value=prediction_value,
            confidence=confidence,
            confidence_interval=(
                prediction_value["days_until_purchase"] * 0.5,
                prediction_value["days_until_purchase"] * 1.5
            ),
            factors={
                "purchase_frequency": 1 / avg_interval if 'avg_interval' in locals() else 0,
                "price_sensitivity": 0.5,  # Would calculate
                "loyalty_score": len(past_tickets) / 10
            },
            expires_at=datetime.now() + timedelta(days=30)
        )

        self.predictions.append(prediction)

        # Alert if high probability and customer at risk
        if prediction_value["purchase_probability"] > 0.7 and prediction_value["days_until_purchase"] < 7:
            alert = PredictionAlert(
                alert_id=f"customer_alert_{prediction.prediction_id}",
                prediction_id=prediction.prediction_id,
                alert_type="opportunity",
                message=f"Customer {customer.email} likely to purchase in {prediction_value['days_until_purchase']} days",
                recommended_action="Send personalized event recommendations",
                urgency="medium"
            )
            self.alerts.append(alert)

        return prediction

    async def predict_revenue(self, event_id: int) -> Prediction:
        """Predict total revenue for an event"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Get current sales
        current_revenue = self.db.query(func.sum(Ticket.price_paid)).filter(
            Ticket.event_id == event_id,
            Ticket.status == "paid"
        ).scalar() or 0

        # Predict remaining sales
        demand_prediction = await self.predict_demand(event_id)

        if demand_prediction:
            remaining_demand = demand_prediction.value["total_demand"]
        else:
            remaining_demand = 100  # Default estimate

        # Get average ticket price
        avg_price = self.db.query(func.avg(TicketTier.price)).filter(
            TicketTier.event_id == event_id
        ).scalar() or 50

        predicted_additional_revenue = remaining_demand * avg_price
        total_predicted_revenue = current_revenue + predicted_additional_revenue

        # Calculate confidence based on days remaining
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
        days_remaining = (event_date - datetime.now()).days
        confidence = 0.9 if days_remaining < 7 else 0.75 if days_remaining < 30 else 0.6

        prediction = Prediction(
            prediction_id=f"revenue_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.REVENUE_FORECAST,
            target=str(event_id),
            value=total_predicted_revenue,
            confidence=confidence,
            confidence_interval=(
                total_predicted_revenue * 0.85,
                total_predicted_revenue * 1.15
            ),
            factors={
                "current_revenue": current_revenue,
                "predicted_additional": predicted_additional_revenue,
                "avg_ticket_price": avg_price,
                "remaining_capacity_value": remaining_demand * avg_price
            },
            expires_at=datetime.now() + timedelta(hours=12),
            metadata={
                "revenue_target_achievement": total_predicted_revenue / 10000 if total_predicted_revenue else 0,  # Assuming 10k target
                "needs_intervention": total_predicted_revenue < 5000
            }
        )

        self.predictions.append(prediction)
        return prediction

    async def predict_viral_potential(self, event_id: int) -> Prediction:
        """Predict if event could go viral"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Factors that contribute to virality
        viral_factors = {
            "artist_trending": 0.3,  # Would check social media trends
            "unique_concept": 0.2,  # Would analyze event description
            "social_shares": 0.15,  # Would track actual shares
            "influencer_interest": 0.1,  # Would check influencer mentions
            "timing": 0.15,  # Holiday, weekend, special date
            "price_accessibility": 0.1  # Lower price = more shareability
        }

        # Calculate viral score (simplified)
        viral_score = sum(viral_factors.values()) * 0.6  # Arbitrary scaling

        # Classify viral potential
        if viral_score > 0.7:
            classification = "high"
            message = "High viral potential detected!"
        elif viral_score > 0.4:
            classification = "medium"
            message = "Moderate viral potential"
        else:
            classification = "low"
            message = "Standard promotional approach recommended"

        prediction = Prediction(
            prediction_id=f"viral_{event_id}_{datetime.utcnow().timestamp()}",
            prediction_type=PredictionType.VIRAL_POTENTIAL,
            target=str(event_id),
            value={
                "viral_score": viral_score,
                "classification": classification,
                "message": message
            },
            confidence=0.65,
            confidence_interval=(viral_score * 0.7, min(1.0, viral_score * 1.3)),
            factors=viral_factors,
            expires_at=datetime.now() + timedelta(days=3),
            metadata={
                "recommended_strategy": "influencer_outreach" if classification == "high" else "standard_promotion"
            }
        )

        self.predictions.append(prediction)

        # Alert if high viral potential
        if classification == "high":
            alert = PredictionAlert(
                alert_id=f"viral_alert_{prediction.prediction_id}",
                prediction_id=prediction.prediction_id,
                alert_type="opportunity",
                message=f"Event {event.name} has high viral potential!",
                recommended_action="Allocate budget to influencer marketing and social media amplification",
                urgency="high"
            )
            self.alerts.append(alert)

        return prediction

    def get_active_predictions(self, target: Optional[str] = None) -> List[Prediction]:
        """Get all active (non-expired) predictions"""

        now = datetime.utcnow()
        active = [
            p for p in self.predictions
            if p.expires_at is None or p.expires_at > now
        ]

        if target:
            active = [p for p in active if p.target == target]

        return active

    def get_prediction_accuracy(self, prediction_type: Optional[PredictionType] = None) -> Dict:
        """Get accuracy metrics for predictions"""

        if prediction_type:
            accuracies = self.historical_accuracy.get(prediction_type, [])
            if accuracies:
                return {
                    "type": prediction_type.value,
                    "average_accuracy": statistics.mean(accuracies),
                    "samples": len(accuracies),
                    "confidence": statistics.mean(p.confidence for p in self.predictions if p.prediction_type == prediction_type)
                }
        else:
            # Overall accuracy
            all_accuracies = []
            for accuracies in self.historical_accuracy.values():
                all_accuracies.extend(accuracies)

            if all_accuracies:
                return {
                    "overall_accuracy": statistics.mean(all_accuracies),
                    "total_predictions": len(self.predictions),
                    "active_predictions": len(self.get_active_predictions()),
                    "alerts_generated": len(self.alerts)
                }

        return {"status": "no_accuracy_data"}

    def get_alerts(self, urgency: Optional[str] = None) -> List[PredictionAlert]:
        """Get prediction-based alerts"""

        alerts = self.alerts

        if urgency:
            alerts = [a for a in alerts if a.urgency == urgency]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def update_model_accuracy(self, prediction_id: str, actual_value: Any):
        """Update model accuracy based on actual outcomes"""

        # Find the prediction
        prediction = next((p for p in self.predictions if p.prediction_id == prediction_id), None)

        if not prediction:
            return

        # Calculate accuracy (simplified - would be more sophisticated)
        if isinstance(prediction.value, (int, float)) and isinstance(actual_value, (int, float)):
            error = abs(prediction.value - actual_value) / max(prediction.value, actual_value)
            accuracy = 1 - error
        else:
            # Binary or categorical prediction
            accuracy = 1.0 if prediction.value == actual_value else 0.0

        # Store accuracy
        self.historical_accuracy[prediction.prediction_type].append(accuracy)

        # Update model if accuracy is declining
        recent_accuracies = self.historical_accuracy[prediction.prediction_type][-10:]
        if len(recent_accuracies) >= 10:
            recent_avg = statistics.mean(recent_accuracies)
            if recent_avg < 0.6:  # Below 60% accuracy
                # Model needs retraining
                model = self.models.get(prediction.prediction_type)
                if model:
                    model.accuracy = recent_avg
                    # Would trigger retraining process