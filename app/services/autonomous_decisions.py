"""
Autonomous Decision Making System
AI makes confident decisions and takes actions automatically
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Event, AdCampaign, TicketTier, EventGoer, Ticket, Alert
from app.services.analytics_engine import AnalyticsEngine
from app.services.dynamic_pricing import DynamicPricingEngine
from app.services.campaign_tracking import CampaignTrackingService
from app.services.alerts import AlertService


class DecisionType(str, Enum):
    PRICING = "pricing"
    MARKETING = "marketing"
    INVENTORY = "inventory"
    CUSTOMER_SERVICE = "customer_service"
    OPERATIONS = "operations"
    CONTENT = "content"
    SCHEDULING = "scheduling"


class ConfidenceLevel(str, Enum):
    HIGH = "high"  # >90% - Auto execute
    MEDIUM = "medium"  # 70-90% - Execute with notification
    LOW = "low"  # <70% - Suggest only


@dataclass
class DecisionContext:
    """Context for making a decision"""
    event_id: Optional[int]
    campaign_id: Optional[int]
    customer_id: Optional[int]
    current_metrics: Dict
    historical_data: Dict
    external_signals: Dict  # Weather, competition, etc.
    urgency_level: str  # immediate, high, medium, low
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AutonomousDecision:
    """Decision made by the system"""
    decision_id: str
    decision_type: DecisionType
    action: str
    parameters: Dict
    reasoning: str
    confidence: float
    confidence_level: ConfidenceLevel
    expected_impact: Dict
    risk_assessment: Dict
    requires_approval: bool
    auto_execute: bool
    context: DecisionContext
    timestamp: datetime = field(default_factory=datetime.utcnow)
    executed: bool = False
    execution_result: Optional[Dict] = None


@dataclass
class DecisionOutcome:
    """Outcome of an executed decision"""
    decision_id: str
    success: bool
    actual_impact: Dict
    variance_from_expected: Dict
    lessons_learned: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AutonomousDecisionEngine:
    """Main engine for autonomous decision making"""

    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsEngine(db)
        self.pricing_engine = DynamicPricingEngine(db)
        self.campaign_tracking = CampaignTrackingService(db)
        self.alert_service = AlertService(db)
        self.decisions: List[AutonomousDecision] = []
        self.outcomes: List[DecisionOutcome] = []
        self.confidence_thresholds = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.0
        }

    async def monitor_and_decide(self, event_id: int) -> List[AutonomousDecision]:
        """Monitor event and make autonomous decisions"""

        decisions = []

        # Gather context
        context = await self._gather_context(event_id)

        # Check various decision areas
        pricing_decision = await self._evaluate_pricing_decision(context)
        if pricing_decision:
            decisions.append(pricing_decision)

        marketing_decision = await self._evaluate_marketing_decision(context)
        if marketing_decision:
            decisions.append(marketing_decision)

        inventory_decision = await self._evaluate_inventory_decision(context)
        if inventory_decision:
            decisions.append(inventory_decision)

        operations_decision = await self._evaluate_operations_decision(context)
        if operations_decision:
            decisions.append(operations_decision)

        # Execute high-confidence decisions
        for decision in decisions:
            if decision.auto_execute:
                await self.execute_decision(decision)

        return decisions

    async def _gather_context(self, event_id: int) -> DecisionContext:
        """Gather all context needed for decision making"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None

        # Current metrics
        current_metrics = {
            "tickets_sold": self.db.query(Ticket).filter(
                Ticket.event_id == event_id,
                Ticket.status == "paid"
            ).count(),
            "revenue": await self.analytics.calculate_total_revenue(event_id),
            "days_until_event": (datetime.strptime(event.event_date, "%Y-%m-%d") - datetime.now()).days,
            "sellout_percentage": 0,  # Would calculate
            "current_demand_velocity": 0  # Tickets per hour
        }

        # Historical data
        historical_data = {
            "similar_events_performance": [],  # Would fetch
            "seasonal_patterns": {},
            "customer_behavior": {}
        }

        # External signals
        external_signals = {
            "weather_forecast": "clear",  # Would fetch
            "competitor_events": [],  # Would fetch
            "trending_topics": []  # Would fetch
        }

        # Determine urgency
        if current_metrics["days_until_event"] <= 2:
            urgency = "immediate"
        elif current_metrics["days_until_event"] <= 7:
            urgency = "high"
        elif current_metrics["days_until_event"] <= 14:
            urgency = "medium"
        else:
            urgency = "low"

        return DecisionContext(
            event_id=event_id,
            campaign_id=None,
            customer_id=None,
            current_metrics=current_metrics,
            historical_data=historical_data,
            external_signals=external_signals,
            urgency_level=urgency
        )

    async def _evaluate_pricing_decision(self, context: DecisionContext) -> Optional[AutonomousDecision]:
        """Evaluate if pricing should be adjusted"""

        if not context or not context.event_id:
            return None

        # Get current pricing
        tiers = self.db.query(TicketTier).filter(
            TicketTier.event_id == context.event_id,
            TicketTier.status == "active"
        ).all()

        if not tiers:
            return None

        # Analyze demand
        sellout_percentage = context.current_metrics.get("sellout_percentage", 0)
        days_until = context.current_metrics.get("days_until_event", 30)
        demand_velocity = context.current_metrics.get("current_demand_velocity", 0)

        # Decision logic
        decision = None
        confidence = 0.5

        # High demand scenario
        if sellout_percentage > 0.8 and days_until > 7:
            # Increase prices
            price_multiplier = 1.2
            confidence = 0.95
            action = "increase_prices"
            reasoning = f"High demand detected: {sellout_percentage:.0%} sold with {days_until} days remaining"
            expected_impact = {
                "revenue_increase": 0.15,
                "demand_moderation": 0.1
            }

        # Low demand scenario
        elif sellout_percentage < 0.3 and days_until < 14:
            # Decrease prices
            price_multiplier = 0.85
            confidence = 0.85
            action = "decrease_prices"
            reasoning = f"Low demand: only {sellout_percentage:.0%} sold with {days_until} days until event"
            expected_impact = {
                "demand_increase": 0.3,
                "revenue_recovery": 0.1
            }

        # Last minute surge
        elif days_until <= 2 and sellout_percentage < 0.9:
            # Flash sale
            price_multiplier = 0.7
            confidence = 0.9
            action = "flash_sale"
            reasoning = f"Last minute push: {days_until} days left, {1-sellout_percentage:.0%} inventory remaining"
            expected_impact = {
                "sellout_probability": 0.7,
                "revenue_capture": 0.2
            }

        else:
            return None  # No pricing action needed

        # Determine confidence level
        if confidence >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            confidence_level = ConfidenceLevel.HIGH
            auto_execute = True
            requires_approval = False
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            confidence_level = ConfidenceLevel.MEDIUM
            auto_execute = True  # Execute but notify
            requires_approval = False
        else:
            confidence_level = ConfidenceLevel.LOW
            auto_execute = False
            requires_approval = True

        decision = AutonomousDecision(
            decision_id=f"pricing_{context.event_id}_{datetime.utcnow().timestamp()}",
            decision_type=DecisionType.PRICING,
            action=action,
            parameters={
                "price_multiplier": price_multiplier,
                "tier_ids": [t.id for t in tiers],
                "duration_hours": 24 if action != "flash_sale" else 48
            },
            reasoning=reasoning,
            confidence=confidence,
            confidence_level=confidence_level,
            expected_impact=expected_impact,
            risk_assessment={
                "demand_drop_risk": 0.1 if action == "increase_prices" else 0.0,
                "brand_impact_risk": 0.05,
                "competitor_response_risk": 0.2
            },
            requires_approval=requires_approval,
            auto_execute=auto_execute,
            context=context
        )

        self.decisions.append(decision)
        return decision

    async def _evaluate_marketing_decision(self, context: DecisionContext) -> Optional[AutonomousDecision]:
        """Evaluate marketing campaign adjustments"""

        if not context or not context.event_id:
            return None

        # Get active campaigns
        campaigns = self.db.query(AdCampaign).filter(
            AdCampaign.event_id == context.event_id,
            AdCampaign.status == "active"
        ).all()

        if not campaigns:
            # Maybe create a new campaign?
            if context.current_metrics.get("sellout_percentage", 0) < 0.5:
                return await self._create_emergency_campaign_decision(context)
            return None

        # Analyze campaign performance
        total_spend = sum(c.budget_spent or 0 for c in campaigns)
        total_budget = sum(c.budget_total or 0 for c in campaigns)

        # Get performance metrics (simulated)
        roas = 2.5  # Would calculate actual ROAS
        click_rate = 0.03  # Would get from tracking

        decision = None
        confidence = 0.5

        # High ROAS - scale up
        if roas > 3.0 and (total_spend / total_budget) < 0.7:
            confidence = 0.92
            action = "scale_campaigns"
            reasoning = f"Excellent ROAS of {roas:.1f}x - scaling successful campaigns"
            parameters = {
                "budget_increase": 1.5,
                "campaign_ids": [c.id for c in campaigns if c.platform == "meta"]
            }
            expected_impact = {
                "additional_revenue": total_spend * 0.5 * roas,
                "ticket_sales_increase": 0.2
            }

        # Low ROAS - optimize or pause
        elif roas < 1.5:
            confidence = 0.88
            action = "optimize_campaigns"
            reasoning = f"Low ROAS of {roas:.1f}x - optimizing targeting and creative"
            parameters = {
                "pause_underperformers": True,
                "refresh_creative": True,
                "narrow_targeting": True
            }
            expected_impact = {
                "roas_improvement": 0.3,
                "cost_reduction": 0.2
            }

        # Urgency boost
        elif context.urgency_level == "high" and context.current_metrics.get("sellout_percentage", 0) < 0.7:
            confidence = 0.85
            action = "urgency_boost"
            reasoning = f"Event in {context.current_metrics.get('days_until_event')} days - boosting urgency messaging"
            parameters = {
                "increase_frequency": 2.0,
                "urgency_creative": True,
                "expand_audience": True
            }
            expected_impact = {
                "reach_increase": 0.5,
                "conversion_boost": 0.15
            }

        else:
            return None

        # Determine confidence level
        if confidence >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            confidence_level = ConfidenceLevel.HIGH
            auto_execute = True
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            confidence_level = ConfidenceLevel.MEDIUM
            auto_execute = True
        else:
            confidence_level = ConfidenceLevel.LOW
            auto_execute = False

        decision = AutonomousDecision(
            decision_id=f"marketing_{context.event_id}_{datetime.utcnow().timestamp()}",
            decision_type=DecisionType.MARKETING,
            action=action,
            parameters=parameters,
            reasoning=reasoning,
            confidence=confidence,
            confidence_level=confidence_level,
            expected_impact=expected_impact,
            risk_assessment={
                "budget_overrun_risk": 0.15,
                "audience_fatigue_risk": 0.1,
                "competitive_response_risk": 0.05
            },
            requires_approval=not auto_execute,
            auto_execute=auto_execute,
            context=context
        )

        self.decisions.append(decision)
        return decision

    async def _create_emergency_campaign_decision(self, context: DecisionContext) -> AutonomousDecision:
        """Create emergency marketing campaign"""

        days_until = context.current_metrics.get("days_until_event", 30)
        sellout_percentage = context.current_metrics.get("sellout_percentage", 0)

        # Emergency campaign parameters
        budget = 1000 if days_until > 7 else 2000
        confidence = 0.85 if days_until > 3 else 0.95

        decision = AutonomousDecision(
            decision_id=f"emergency_campaign_{context.event_id}_{datetime.utcnow().timestamp()}",
            decision_type=DecisionType.MARKETING,
            action="create_emergency_campaign",
            parameters={
                "budget": budget,
                "platforms": ["meta", "google"],
                "targeting": "broad",
                "creative_type": "urgency",
                "duration_days": min(days_until, 7)
            },
            reasoning=f"Only {sellout_percentage:.0%} sold with {days_until} days left - emergency campaign needed",
            confidence=confidence,
            confidence_level=ConfidenceLevel.HIGH if confidence > 0.9 else ConfidenceLevel.MEDIUM,
            expected_impact={
                "ticket_sales": 100,
                "revenue": 5000,
                "sellout_probability": 0.6
            },
            risk_assessment={
                "brand_desperation_perception": 0.2,
                "budget_waste_risk": 0.15
            },
            requires_approval=False,
            auto_execute=True,
            context=context
        )

        self.decisions.append(decision)
        return decision

    async def _evaluate_inventory_decision(self, context: DecisionContext) -> Optional[AutonomousDecision]:
        """Evaluate inventory management decisions"""

        if not context or not context.event_id:
            return None

        # Check waitlist
        waitlist_count = 0  # Would query actual waitlist

        # Check tier distribution
        tiers = self.db.query(TicketTier).filter(
            TicketTier.event_id == context.event_id
        ).all()

        decision = None

        # Release held inventory
        held_tickets = 0  # Would check for expired holds
        if held_tickets > 10 and context.urgency_level in ["high", "immediate"]:
            decision = AutonomousDecision(
                decision_id=f"inventory_release_{context.event_id}_{datetime.utcnow().timestamp()}",
                decision_type=DecisionType.INVENTORY,
                action="release_held_inventory",
                parameters={
                    "tickets_to_release": held_tickets,
                    "notify_waitlist": True
                },
                reasoning=f"Releasing {held_tickets} held tickets due to urgency",
                confidence=0.95,
                confidence_level=ConfidenceLevel.HIGH,
                expected_impact={
                    "additional_sales": held_tickets * 0.7,
                    "revenue": held_tickets * 50  # Avg price
                },
                risk_assessment={
                    "double_booking_risk": 0.01
                },
                requires_approval=False,
                auto_execute=True,
                context=context
            )

        # Open waitlist
        elif context.current_metrics.get("sellout_percentage", 0) > 0.95 and waitlist_count == 0:
            decision = AutonomousDecision(
                decision_id=f"open_waitlist_{context.event_id}_{datetime.utcnow().timestamp()}",
                decision_type=DecisionType.INVENTORY,
                action="open_waitlist",
                parameters={
                    "max_waitlist_size": 50,
                    "auto_notify": True
                },
                reasoning="Event nearly sold out - opening waitlist",
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                expected_impact={
                    "customer_satisfaction": 0.2,
                    "potential_revenue": 2500
                },
                risk_assessment={
                    "disappointment_risk": 0.3
                },
                requires_approval=False,
                auto_execute=True,
                context=context
            )

        if decision:
            self.decisions.append(decision)

        return decision

    async def _evaluate_operations_decision(self, context: DecisionContext) -> Optional[AutonomousDecision]:
        """Evaluate operational decisions"""

        if not context:
            return None

        decision = None

        # Staffing decisions
        expected_attendance = context.current_metrics.get("tickets_sold", 0)

        if expected_attendance > 400 and context.urgency_level == "immediate":
            decision = AutonomousDecision(
                decision_id=f"staffing_{context.event_id}_{datetime.utcnow().timestamp()}",
                decision_type=DecisionType.OPERATIONS,
                action="increase_staffing",
                parameters={
                    "additional_staff": 3,
                    "roles": ["check_in", "customer_service", "security"]
                },
                reasoning=f"High attendance of {expected_attendance} requires additional staff",
                confidence=0.88,
                confidence_level=ConfidenceLevel.MEDIUM,
                expected_impact={
                    "wait_time_reduction": 0.3,
                    "customer_satisfaction": 0.2
                },
                risk_assessment={
                    "overstaffing_cost": 0.1
                },
                requires_approval=False,
                auto_execute=True,
                context=context
            )
            self.decisions.append(decision)

        # Weather contingency
        if context.external_signals.get("weather_forecast") == "rain" and context.urgency_level in ["high", "immediate"]:
            decision = AutonomousDecision(
                decision_id=f"weather_contingency_{context.event_id}_{datetime.utcnow().timestamp()}",
                decision_type=DecisionType.OPERATIONS,
                action="activate_weather_contingency",
                parameters={
                    "indoor_backup": True,
                    "notify_attendees": True,
                    "provide_rain_gear": True
                },
                reasoning="Rain forecasted - activating weather contingency plan",
                confidence=0.92,
                confidence_level=ConfidenceLevel.HIGH,
                expected_impact={
                    "attendance_retention": 0.8,
                    "satisfaction_maintenance": 0.7
                },
                risk_assessment={
                    "unnecessary_preparation": 0.2
                },
                requires_approval=False,
                auto_execute=True,
                context=context
            )
            self.decisions.append(decision)

        return decision

    async def execute_decision(self, decision: AutonomousDecision) -> DecisionOutcome:
        """Execute an autonomous decision"""

        try:
            result = None

            if decision.decision_type == DecisionType.PRICING:
                result = await self._execute_pricing_decision(decision)
            elif decision.decision_type == DecisionType.MARKETING:
                result = await self._execute_marketing_decision(decision)
            elif decision.decision_type == DecisionType.INVENTORY:
                result = await self._execute_inventory_decision(decision)
            elif decision.decision_type == DecisionType.OPERATIONS:
                result = await self._execute_operations_decision(decision)

            decision.executed = True
            decision.execution_result = result

            # Create outcome
            outcome = DecisionOutcome(
                decision_id=decision.decision_id,
                success=result.get("success", False) if result else False,
                actual_impact=result.get("impact", {}) if result else {},
                variance_from_expected=self._calculate_variance(
                    decision.expected_impact,
                    result.get("impact", {}) if result else {}
                ),
                lessons_learned=self._extract_lessons(decision, result)
            )

            self.outcomes.append(outcome)

            # Notify if medium confidence
            if decision.confidence_level == ConfidenceLevel.MEDIUM:
                await self._notify_decision(decision, outcome)

            return outcome

        except Exception as e:
            # Log error and create failure outcome
            outcome = DecisionOutcome(
                decision_id=decision.decision_id,
                success=False,
                actual_impact={},
                variance_from_expected={},
                lessons_learned=[f"Execution failed: {str(e)}"]
            )
            self.outcomes.append(outcome)
            return outcome

    async def _execute_pricing_decision(self, decision: AutonomousDecision) -> Dict:
        """Execute pricing adjustment"""

        tier_ids = decision.parameters.get("tier_ids", [])
        multiplier = decision.parameters.get("price_multiplier", 1.0)

        updated_count = 0
        for tier_id in tier_ids:
            tier = self.db.query(TicketTier).filter(TicketTier.id == tier_id).first()
            if tier:
                original_price = tier.price
                tier.price = int(tier.price * multiplier)
                updated_count += 1

        self.db.commit()

        return {
            "success": True,
            "updated_tiers": updated_count,
            "impact": {
                "price_change": multiplier - 1,
                "tiers_affected": updated_count
            }
        }

    async def _execute_marketing_decision(self, decision: AutonomousDecision) -> Dict:
        """Execute marketing campaign adjustment"""

        action = decision.action

        if action == "scale_campaigns":
            campaign_ids = decision.parameters.get("campaign_ids", [])
            increase = decision.parameters.get("budget_increase", 1.0)

            for campaign_id in campaign_ids:
                campaign = self.db.query(AdCampaign).filter(AdCampaign.id == campaign_id).first()
                if campaign:
                    campaign.budget_total = int(campaign.budget_total * increase)
                    campaign.budget_daily = int(campaign.budget_daily * increase)

            self.db.commit()

            return {
                "success": True,
                "campaigns_scaled": len(campaign_ids),
                "impact": {
                    "budget_increase": increase - 1
                }
            }

        elif action == "create_emergency_campaign":
            # Would create actual campaign
            return {
                "success": True,
                "campaign_created": True,
                "impact": {
                    "estimated_reach": 10000,
                    "estimated_clicks": 300
                }
            }

        return {"success": False}

    async def _execute_inventory_decision(self, decision: AutonomousDecision) -> Dict:
        """Execute inventory management decision"""

        if decision.action == "release_held_inventory":
            # Would release actual held inventory
            return {
                "success": True,
                "tickets_released": decision.parameters.get("tickets_to_release", 0),
                "impact": {
                    "inventory_available": decision.parameters.get("tickets_to_release", 0)
                }
            }

        elif decision.action == "open_waitlist":
            # Would open actual waitlist
            return {
                "success": True,
                "waitlist_opened": True,
                "impact": {
                    "waitlist_capacity": decision.parameters.get("max_waitlist_size", 50)
                }
            }

        return {"success": False}

    async def _execute_operations_decision(self, decision: AutonomousDecision) -> Dict:
        """Execute operational decision"""

        # Would execute actual operational changes
        return {
            "success": True,
            "operation": decision.action,
            "impact": decision.expected_impact
        }

    def _calculate_variance(self, expected: Dict, actual: Dict) -> Dict:
        """Calculate variance between expected and actual impact"""

        variance = {}
        for key in expected:
            if key in actual:
                variance[key] = actual[key] - expected[key]
            else:
                variance[key] = -expected[key]  # Didn't materialize

        return variance

    def _extract_lessons(self, decision: AutonomousDecision, result: Dict) -> List[str]:
        """Extract lessons learned from decision outcome"""

        lessons = []

        if not result or not result.get("success"):
            lessons.append("Execution failed - review prerequisites")

        # Would analyze actual vs expected for more lessons

        return lessons

    async def _notify_decision(self, decision: AutonomousDecision, outcome: DecisionOutcome):
        """Notify stakeholders about decision"""

        alert = Alert(
            type="autonomous_decision",
            severity="info" if outcome.success else "warning",
            title=f"Autonomous {decision.action} executed",
            description=f"{decision.reasoning}. Confidence: {decision.confidence:.0%}",
            data=json.dumps({
                "decision_id": decision.decision_id,
                "parameters": decision.parameters,
                "outcome": {
                    "success": outcome.success,
                    "impact": outcome.actual_impact
                }
            }),
            event_id=decision.context.event_id
        )

        self.db.add(alert)
        self.db.commit()

    def get_decision_history(self, event_id: Optional[int] = None) -> List[Dict]:
        """Get history of decisions made"""

        decisions = self.decisions
        if event_id:
            decisions = [d for d in decisions if d.context.event_id == event_id]

        return [
            {
                "decision_id": d.decision_id,
                "type": d.decision_type.value,
                "action": d.action,
                "confidence": d.confidence,
                "executed": d.executed,
                "timestamp": d.timestamp.isoformat()
            }
            for d in decisions
        ]

    def get_performance_metrics(self) -> Dict:
        """Get metrics on autonomous decision performance"""

        if not self.outcomes:
            return {"status": "no_decisions_yet"}

        successful = sum(1 for o in self.outcomes if o.success)
        total = len(self.outcomes)

        high_confidence_decisions = [d for d in self.decisions if d.confidence_level == ConfidenceLevel.HIGH]
        high_confidence_success = sum(
            1 for d in high_confidence_decisions
            if any(o.decision_id == d.decision_id and o.success for o in self.outcomes)
        )

        return {
            "total_decisions": len(self.decisions),
            "executed_decisions": total,
            "success_rate": successful / total if total > 0 else 0,
            "high_confidence_success_rate": high_confidence_success / len(high_confidence_decisions) if high_confidence_decisions else 0,
            "auto_execution_rate": sum(1 for d in self.decisions if d.auto_execute) / len(self.decisions) if self.decisions else 0,
            "decision_types": {
                dt.value: sum(1 for d in self.decisions if d.decision_type == dt)
                for dt in DecisionType
            },
            "average_confidence": sum(d.confidence for d in self.decisions) / len(self.decisions) if self.decisions else 0,
            "lessons_learned": sum(len(o.lessons_learned) for o in self.outcomes)
        }