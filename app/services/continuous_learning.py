"""
Continuous Feedback Loop Learning System
Learns from every micro-interaction to continuously improve the platform
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.models import Event, EventGoer, Ticket, TicketTier, Notification


class InteractionType(str, Enum):
    VOICE_COMMAND = "voice_command"
    PAGE_VIEW = "page_view"
    CLICK = "click"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_ABANDON = "cart_abandon"
    PURCHASE_COMPLETE = "purchase_complete"
    SEARCH = "search"
    FILTER = "filter"
    SUPPORT_TICKET = "support_ticket"
    REFUND_REQUEST = "refund_request"
    REVIEW_SUBMIT = "review_submit"
    SHARE_SOCIAL = "share_social"
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    SMS_CLICK = "sms_click"
    PROMO_CODE_USE = "promo_code_use"
    NOTIFICATION_DISMISS = "notification_dismiss"


@dataclass
class Interaction:
    """Single user interaction"""
    interaction_id: str
    user_id: Optional[int]
    session_id: str
    interaction_type: InteractionType
    timestamp: datetime
    context: Dict  # Page, event, campaign, etc.
    data: Dict  # Interaction-specific data
    outcome: Optional[str] = None  # Success, failure, abandon, etc.
    value: Optional[float] = None  # Monetary or engagement value


@dataclass
class LearningPattern:
    """Pattern discovered from interactions"""
    pattern_id: str
    pattern_type: str  # behavior, preference, friction, success
    description: str
    occurrences: int
    confidence: float
    impact: Dict  # Business impact metrics
    recommendations: List[str]
    discovered_at: datetime
    last_seen: datetime


@dataclass
class FrictionPoint:
    """Identified friction in user journey"""
    location: str  # Where in the journey
    friction_type: str  # confusion, technical, pricing, etc.
    severity: float  # 0-1
    affected_users: int
    abandon_rate: float
    average_time_stuck: float  # Seconds
    common_paths_after: List[str]
    suggested_fixes: List[str]


@dataclass
class SuccessPath:
    """Successful user journey path"""
    path_id: str
    steps: List[str]
    conversion_rate: float
    average_time: float  # Total journey time
    average_value: float
    user_segment: str
    key_factors: List[str]  # What made this path successful


@dataclass
class LearningInsight:
    """Actionable insight from learning"""
    insight_id: str
    category: str  # UX, pricing, marketing, content, etc.
    title: str
    description: str
    evidence: List[Dict]  # Supporting data
    impact_estimate: Dict
    recommended_action: str
    confidence: float
    priority: str  # high, medium, low
    created_at: datetime


class ContinuousLearningEngine:
    """Main engine for continuous learning from all interactions"""

    def __init__(self, db: Session):
        self.db = db
        self.interactions: List[Interaction] = []
        self.patterns: Dict[str, LearningPattern] = {}
        self.friction_points: List[FrictionPoint] = []
        self.success_paths: List[SuccessPath] = []
        self.insights: List[LearningInsight] = []
        self.learning_models: Dict[str, Any] = {}

    def track_interaction(
        self,
        user_id: Optional[int],
        session_id: str,
        interaction_type: InteractionType,
        context: Dict,
        data: Dict,
        outcome: Optional[str] = None
    ) -> Interaction:
        """Track a single user interaction"""

        interaction = Interaction(
            interaction_id=f"{session_id}_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            session_id=session_id,
            interaction_type=interaction_type,
            timestamp=datetime.utcnow(),
            context=context,
            data=data,
            outcome=outcome,
            value=data.get("value", 0)
        )

        self.interactions.append(interaction)

        # Real-time learning triggers
        if len(self.interactions) % 100 == 0:  # Every 100 interactions
            self.analyze_recent_interactions()

        return interaction

    def analyze_recent_interactions(self, hours: int = 24):
        """Analyze recent interactions for patterns"""

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [i for i in self.interactions if i.timestamp > cutoff]

        if not recent:
            return

        # Analyze different aspects
        self._analyze_abandonment_patterns(recent)
        self._analyze_success_patterns(recent)
        self._analyze_friction_points(recent)
        self._analyze_voice_commands(recent)
        self._analyze_pricing_sensitivity(recent)
        self._analyze_marketing_effectiveness(recent)

        # Generate insights
        self._generate_insights()

    def _analyze_abandonment_patterns(self, interactions: List[Interaction]):
        """Analyze cart and journey abandonment"""

        # Group by session
        sessions = defaultdict(list)
        for interaction in interactions:
            sessions[interaction.session_id].append(interaction)

        abandonment_points = defaultdict(int)
        abandonment_reasons = defaultdict(list)

        for session_id, session_interactions in sessions.items():
            # Check if session ended in abandonment
            last_interaction = session_interactions[-1]

            if last_interaction.interaction_type == InteractionType.CART_ABANDON:
                # Find where they abandoned
                for i, interaction in enumerate(session_interactions[:-1]):
                    if interaction.interaction_type == InteractionType.CART_ADD:
                        # Look at next interactions
                        abandonment_points[interaction.context.get("page", "unknown")] += 1

                        # Try to determine reason
                        if i + 1 < len(session_interactions):
                            next_interaction = session_interactions[i + 1]
                            if next_interaction.data.get("error"):
                                abandonment_reasons["technical_error"].append(session_id)
                            elif "price" in str(next_interaction.data):
                                abandonment_reasons["price_concern"].append(session_id)
                            else:
                                abandonment_reasons["unknown"].append(session_id)

        # Create friction points
        for location, count in abandonment_points.items():
            if count > 5:  # Threshold
                friction = FrictionPoint(
                    location=location,
                    friction_type="high_abandonment",
                    severity=min(1.0, count / 20),  # Normalize
                    affected_users=count,
                    abandon_rate=count / len(sessions) if sessions else 0,
                    average_time_stuck=30.0,  # Would calculate from data
                    common_paths_after=["exit", "back", "search"],
                    suggested_fixes=[
                        "Simplify checkout process",
                        "Add progress indicator",
                        "Offer live chat support"
                    ]
                )
                self.friction_points.append(friction)

    def _analyze_success_patterns(self, interactions: List[Interaction]):
        """Analyze successful conversion patterns"""

        sessions = defaultdict(list)
        for interaction in interactions:
            sessions[interaction.session_id].append(interaction)

        successful_paths = []

        for session_id, session_interactions in sessions.items():
            # Check if session ended in purchase
            if any(i.interaction_type == InteractionType.PURCHASE_COMPLETE for i in session_interactions):
                # Extract path
                path = [i.interaction_type.value for i in session_interactions]

                # Calculate metrics
                total_time = (session_interactions[-1].timestamp - session_interactions[0].timestamp).seconds
                total_value = sum(i.value or 0 for i in session_interactions)

                successful_paths.append({
                    "path": path,
                    "time": total_time,
                    "value": total_value,
                    "user_id": session_interactions[0].user_id
                })

        # Identify common successful patterns
        if successful_paths:
            # Group similar paths
            path_patterns = defaultdict(list)
            for path_data in successful_paths:
                path_key = "_".join(path_data["path"][:5])  # First 5 steps
                path_patterns[path_key].append(path_data)

            # Create success path objects
            for path_key, paths in path_patterns.items():
                if len(paths) > 3:  # Minimum occurrences
                    avg_time = statistics.mean(p["time"] for p in paths)
                    avg_value = statistics.mean(p["value"] for p in paths)

                    success_path = SuccessPath(
                        path_id=path_key,
                        steps=path_key.split("_"),
                        conversion_rate=len(paths) / len(sessions) if sessions else 0,
                        average_time=avg_time,
                        average_value=avg_value,
                        user_segment="general",  # Would determine from user data
                        key_factors=self._identify_success_factors(paths)
                    )
                    self.success_paths.append(success_path)

    def _identify_success_factors(self, paths: List[Dict]) -> List[str]:
        """Identify what made these paths successful"""
        factors = []

        avg_time = statistics.mean(p["time"] for p in paths)
        if avg_time < 300:  # Less than 5 minutes
            factors.append("quick_decision")

        avg_value = statistics.mean(p["value"] for p in paths)
        if avg_value > 100:
            factors.append("high_value_purchase")

        # More analysis would go here
        return factors

    def _analyze_friction_points(self, interactions: List[Interaction]):
        """Identify where users get stuck"""

        # Track time between interactions
        sessions = defaultdict(list)
        for interaction in interactions:
            sessions[interaction.session_id].append(interaction)

        long_pauses = []

        for session_id, session_interactions in sessions.items():
            for i in range(len(session_interactions) - 1):
                current = session_interactions[i]
                next_interaction = session_interactions[i + 1]

                time_diff = (next_interaction.timestamp - current.timestamp).seconds

                if time_diff > 60:  # More than 1 minute
                    long_pauses.append({
                        "location": current.context.get("page", "unknown"),
                        "interaction": current.interaction_type.value,
                        "duration": time_diff,
                        "next_action": next_interaction.interaction_type.value
                    })

        # Aggregate friction points
        friction_locations = defaultdict(list)
        for pause in long_pauses:
            friction_locations[pause["location"]].append(pause["duration"])

        # Create friction points
        for location, durations in friction_locations.items():
            if len(durations) > 5:  # Threshold
                avg_duration = statistics.mean(durations)

                friction = FrictionPoint(
                    location=location,
                    friction_type="user_confusion",
                    severity=min(1.0, avg_duration / 300),  # Normalize to 5 minutes
                    affected_users=len(durations),
                    abandon_rate=0.2,  # Would calculate
                    average_time_stuck=avg_duration,
                    common_paths_after=["help", "back", "exit"],
                    suggested_fixes=[
                        f"Add helper text at {location}",
                        "Simplify the interface",
                        "Add tooltips or guided tour"
                    ]
                )
                self.friction_points.append(friction)

    def _analyze_voice_commands(self, interactions: List[Interaction]):
        """Learn from voice command usage"""

        voice_commands = [i for i in interactions if i.interaction_type == InteractionType.VOICE_COMMAND]

        if not voice_commands:
            return

        # Track failed commands
        failed_commands = defaultdict(int)
        successful_patterns = defaultdict(int)

        for command in voice_commands:
            if command.outcome == "failed":
                failed_commands[command.data.get("command_text", "unknown")] += 1
            elif command.outcome == "success":
                successful_patterns[command.data.get("intent", "unknown")] += 1

        # Create learning pattern for failed commands
        if failed_commands:
            top_failures = sorted(failed_commands.items(), key=lambda x: x[1], reverse=True)[:10]

            pattern = LearningPattern(
                pattern_id="voice_command_failures",
                pattern_type="friction",
                description="Common voice command failures",
                occurrences=sum(failed_commands.values()),
                confidence=0.9,
                impact={
                    "user_frustration": "high",
                    "efficiency_loss": "medium",
                    "abandonment_risk": 0.3
                },
                recommendations=[
                    f"Add training for: '{cmd}'" for cmd, _ in top_failures[:3]
                ],
                discovered_at=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            self.patterns[pattern.pattern_id] = pattern

    def _analyze_pricing_sensitivity(self, interactions: List[Interaction]):
        """Analyze how users react to different prices"""

        # Track cart adds/removes with price data
        price_interactions = defaultdict(list)

        for interaction in interactions:
            if interaction.interaction_type in [InteractionType.CART_ADD, InteractionType.CART_REMOVE]:
                price = interaction.data.get("price", 0)
                tier = interaction.data.get("tier", "unknown")

                price_interactions[tier].append({
                    "price": price,
                    "action": interaction.interaction_type.value,
                    "outcome": interaction.outcome
                })

        # Analyze price points
        for tier, interactions_list in price_interactions.items():
            if len(interactions_list) > 10:
                adds = [i["price"] for i in interactions_list if "add" in i["action"]]
                removes = [i["price"] for i in interactions_list if "remove" in i["action"]]

                if adds and removes:
                    avg_add_price = statistics.mean(adds)
                    avg_remove_price = statistics.mean(removes)

                    if avg_remove_price > avg_add_price * 1.2:  # 20% higher
                        pattern = LearningPattern(
                            pattern_id=f"price_sensitivity_{tier}",
                            pattern_type="pricing",
                            description=f"Price sensitivity detected for {tier} tier",
                            occurrences=len(removes),
                            confidence=0.75,
                            impact={
                                "conversion_loss": 0.2,
                                "revenue_impact": -0.1
                            },
                            recommendations=[
                                f"Consider lowering {tier} prices by 10-15%",
                                f"Test dynamic pricing for {tier}",
                                "Add value justification messaging"
                            ],
                            discovered_at=datetime.utcnow(),
                            last_seen=datetime.utcnow()
                        )
                        self.patterns[pattern.pattern_id] = pattern

    def _analyze_marketing_effectiveness(self, interactions: List[Interaction]):
        """Analyze marketing campaign effectiveness"""

        # Track email and SMS interactions
        email_interactions = defaultdict(lambda: {"opens": 0, "clicks": 0, "conversions": 0})
        sms_interactions = defaultdict(lambda: {"clicks": 0, "conversions": 0})

        sessions_by_user = defaultdict(list)
        for interaction in interactions:
            if interaction.user_id:
                sessions_by_user[interaction.user_id].append(interaction)

        for interaction in interactions:
            campaign_id = interaction.context.get("campaign_id")
            if not campaign_id:
                continue

            if interaction.interaction_type == InteractionType.EMAIL_OPEN:
                email_interactions[campaign_id]["opens"] += 1
            elif interaction.interaction_type == InteractionType.EMAIL_CLICK:
                email_interactions[campaign_id]["clicks"] += 1
                # Check for conversion
                if interaction.user_id:
                    user_sessions = sessions_by_user[interaction.user_id]
                    # Look for purchase after click
                    for session in user_sessions:
                        if session.timestamp > interaction.timestamp and \
                           session.interaction_type == InteractionType.PURCHASE_COMPLETE:
                            email_interactions[campaign_id]["conversions"] += 1
                            break

            elif interaction.interaction_type == InteractionType.SMS_CLICK:
                sms_interactions[campaign_id]["clicks"] += 1

        # Create insights from marketing data
        for campaign_id, metrics in email_interactions.items():
            if metrics["opens"] > 50:  # Minimum threshold
                open_rate = metrics["clicks"] / metrics["opens"] if metrics["opens"] > 0 else 0
                conversion_rate = metrics["conversions"] / metrics["clicks"] if metrics["clicks"] > 0 else 0

                if open_rate < 0.1:  # Less than 10%
                    insight = LearningInsight(
                        insight_id=f"low_email_engagement_{campaign_id}",
                        category="marketing",
                        title="Low email engagement detected",
                        description=f"Campaign {campaign_id} has only {open_rate:.1%} click rate",
                        evidence=[{"campaign_id": campaign_id, "metrics": metrics}],
                        impact_estimate={"lost_revenue": metrics["opens"] * 50 * 0.02},  # Rough estimate
                        recommended_action="Improve subject lines and preview text",
                        confidence=0.8,
                        priority="medium",
                        created_at=datetime.utcnow()
                    )
                    self.insights.append(insight)

    def _generate_insights(self):
        """Generate actionable insights from patterns"""

        # Insight: High abandonment rate
        high_abandon_friction = [f for f in self.friction_points if f.abandon_rate > 0.3]
        if high_abandon_friction:
            worst = max(high_abandon_friction, key=lambda f: f.abandon_rate)

            insight = LearningInsight(
                insight_id=f"high_abandonment_{worst.location}",
                category="UX",
                title=f"Critical abandonment point at {worst.location}",
                description=f"{worst.abandon_rate:.1%} of users abandon at {worst.location}",
                evidence=[{
                    "location": worst.location,
                    "abandon_rate": worst.abandon_rate,
                    "affected_users": worst.affected_users
                }],
                impact_estimate={
                    "lost_revenue": worst.affected_users * 50,  # Avg ticket price
                    "conversion_impact": -worst.abandon_rate
                },
                recommended_action=worst.suggested_fixes[0] if worst.suggested_fixes else "Investigate further",
                confidence=0.9,
                priority="high",
                created_at=datetime.utcnow()
            )
            self.insights.append(insight)

        # Insight: Successful patterns
        if self.success_paths:
            best_path = max(self.success_paths, key=lambda p: p.conversion_rate)

            insight = LearningInsight(
                insight_id=f"success_path_{best_path.path_id}",
                category="conversion",
                title="High-converting user path identified",
                description=f"Path with {best_path.conversion_rate:.1%} conversion rate discovered",
                evidence=[{
                    "steps": best_path.steps,
                    "conversion_rate": best_path.conversion_rate,
                    "avg_value": best_path.average_value
                }],
                impact_estimate={
                    "potential_revenue": best_path.average_value * 100  # If 100 more users
                },
                recommended_action="Guide more users through this successful path",
                confidence=0.85,
                priority="high",
                created_at=datetime.utcnow()
            )
            self.insights.append(insight)

    def apply_learning(self, learning_type: str, context: Dict) -> Dict:
        """Apply learned patterns to improve system behavior"""

        improvements = {
            "applied": [],
            "recommendations": [],
            "confidence": 0.5
        }

        # Apply voice command improvements
        if learning_type == "voice_command":
            command_text = context.get("command_text", "")

            # Check if we've learned about this command
            for pattern_id, pattern in self.patterns.items():
                if "voice" in pattern_id and command_text in str(pattern.recommendations):
                    improvements["recommendations"].append(
                        "Try rephrasing - users typically say it differently"
                    )
                    improvements["confidence"] = pattern.confidence

        # Apply pricing improvements
        elif learning_type == "pricing":
            tier = context.get("tier", "")
            price = context.get("price", 0)

            for pattern_id, pattern in self.patterns.items():
                if "price_sensitivity" in pattern_id and tier in pattern_id:
                    # Suggest optimal price
                    if "lower" in str(pattern.recommendations[0]):
                        optimal_price = price * 0.9  # 10% lower
                        improvements["recommendations"].append(f"Consider pricing at ${optimal_price:.2f}")
                        improvements["applied"].append("dynamic_pricing_adjustment")
                        improvements["confidence"] = pattern.confidence

        # Apply UX improvements
        elif learning_type == "ux":
            page = context.get("page", "")

            for friction in self.friction_points:
                if friction.location == page:
                    improvements["recommendations"].extend(friction.suggested_fixes)
                    improvements["applied"].append("friction_point_optimization")
                    improvements["confidence"] = 0.7

        return improvements

    def get_learning_summary(self) -> Dict:
        """Get summary of all learning"""

        return {
            "total_interactions": len(self.interactions),
            "patterns_discovered": len(self.patterns),
            "friction_points": len(self.friction_points),
            "success_paths": len(self.success_paths),
            "insights_generated": len(self.insights),
            "high_priority_insights": len([i for i in self.insights if i.priority == "high"]),
            "top_friction_point": self.friction_points[0] if self.friction_points else None,
            "best_success_path": self.success_paths[0] if self.success_paths else None,
            "latest_insight": self.insights[-1] if self.insights else None,
            "learning_velocity": {
                "patterns_per_day": len(self.patterns) / max(1, len(set(i.timestamp.date() for i in self.interactions))),
                "insights_per_1000_interactions": (len(self.insights) / len(self.interactions)) * 1000 if self.interactions else 0
            }
        }

    def export_learnings(self) -> Dict:
        """Export all learnings for analysis or backup"""

        return {
            "export_date": datetime.utcnow().isoformat(),
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "description": p.description,
                    "occurrences": p.occurrences,
                    "confidence": p.confidence,
                    "recommendations": p.recommendations
                }
                for p in self.patterns.values()
            ],
            "friction_points": [
                {
                    "location": f.location,
                    "severity": f.severity,
                    "affected_users": f.affected_users,
                    "suggested_fixes": f.suggested_fixes
                }
                for f in self.friction_points
            ],
            "success_paths": [
                {
                    "path_id": s.path_id,
                    "conversion_rate": s.conversion_rate,
                    "average_value": s.average_value,
                    "key_factors": s.key_factors
                }
                for s in self.success_paths
            ],
            "insights": [
                {
                    "title": i.title,
                    "category": i.category,
                    "priority": i.priority,
                    "recommended_action": i.recommended_action
                }
                for i in self.insights
            ]
        }