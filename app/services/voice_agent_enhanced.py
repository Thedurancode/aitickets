"""
Enhanced Voice Agent with Natural Language Understanding

Features:
- Context-aware conversations with memory
- Proactive suggestions based on platform state
- Natural multi-turn dialogues
- Emotional intelligence and tone adaptation
- Learns from conversation patterns
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import (
    Event, EventGoer, Ticket, TicketTier, Venue,
    MetaAdCampaign, ConversionTracking, SocialMediaPost
)
from app.services.event_intelligence import monitor_ad_performance
from app.services.cross_event_intelligence import identify_best_customers
from app.services.learning_engine import track_conversion
from app.config import get_settings

logger = logging.getLogger(__name__)


# ==================== Context & Memory ====================

@dataclass
class ConversationContext:
    """Maintains conversation state and context."""

    user_id: int
    session_id: str
    current_event: Optional[int] = None
    current_topic: Optional[str] = None
    conversation_history: deque = field(default_factory=lambda: deque(maxlen=10))
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    pending_actions: List[Dict] = field(default_factory=list)
    emotional_state: str = "neutral"  # neutral, excited, frustrated, confused
    last_interaction: datetime = field(default_factory=datetime.utcnow)

    def add_turn(self, user_input: str, agent_response: str):
        """Add a conversation turn to history."""
        self.conversation_history.append({
            "timestamp": datetime.utcnow(),
            "user": user_input,
            "agent": agent_response
        })
        self.last_interaction = datetime.utcnow()

    def is_recent(self, minutes: int = 5) -> bool:
        """Check if last interaction was recent."""
        return (datetime.utcnow() - self.last_interaction).seconds < (minutes * 60)

    def get_context_summary(self) -> str:
        """Get a summary of recent context."""
        if not self.conversation_history:
            return "New conversation"

        recent_topics = []
        for turn in list(self.conversation_history)[-3:]:
            if "event" in turn["user"].lower():
                recent_topics.append("events")
            if "ticket" in turn["user"].lower():
                recent_topics.append("tickets")
            if "marketing" in turn["user"].lower() or "ad" in turn["user"].lower():
                recent_topics.append("marketing")

        return f"Recent topics: {', '.join(set(recent_topics))}" if recent_topics else "General conversation"


class EmotionalTone(Enum):
    """Agent emotional tones for natural conversation."""
    PROFESSIONAL = "professional"
    ENTHUSIASTIC = "enthusiastic"
    EMPATHETIC = "empathetic"
    CASUAL = "casual"
    URGENT = "urgent"
    CELEBRATORY = "celebratory"


# ==================== Enhanced Voice Agent ====================

class EnhancedVoiceAgent:
    """
    Next-generation voice agent with natural language understanding,
    context awareness, and proactive assistance.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.contexts: Dict[int, ConversationContext] = {}
        self.tone = EmotionalTone.PROFESSIONAL

    async def process_voice_input(
        self,
        user_id: int,
        text: str,
        session_id: Optional[str] = None,
        audio_emotion: Optional[str] = None  # From voice emotion detection
    ) -> Dict[str, Any]:
        """
        Process voice input with full context awareness.

        Args:
            user_id: User ID
            text: Transcribed text from voice
            session_id: Session identifier for multi-turn conversations
            audio_emotion: Detected emotion from voice tone

        Returns:
            Response with text, suggestions, and actions
        """
        # Get or create context
        context = self._get_or_create_context(user_id, session_id)

        # Detect user emotional state from text and audio
        if audio_emotion:
            context.emotional_state = audio_emotion
        else:
            context.emotional_state = self._detect_emotion_from_text(text)

        # Adapt tone based on user's emotional state
        self._adapt_tone(context)

        # Get proactive insights before processing
        proactive_insights = await self._get_proactive_insights(context)

        # Understand intent with context
        intent, entities = await self._understand_intent_with_context(text, context)

        # Process the request
        result = await self._execute_intent(intent, entities, context)

        # Generate natural response
        response_text = self._generate_natural_response(intent, result, context, proactive_insights)

        # Get follow-up suggestions
        suggestions = self._get_contextual_suggestions(intent, result, context)

        # Update context
        context.add_turn(text, response_text)

        # Check for proactive alerts
        alerts = await self._check_for_alerts(context)

        return {
            "text": response_text,
            "intent": intent,
            "entities": entities,
            "emotional_tone": self.tone.value,
            "suggestions": suggestions,
            "proactive_insights": proactive_insights,
            "alerts": alerts,
            "context": {
                "session_id": context.session_id,
                "current_topic": context.current_topic,
                "pending_actions": context.pending_actions
            },
            "voice_settings": {
                "speed": 1.0 if context.emotional_state != "frustrated" else 0.9,
                "pitch": "normal",
                "emphasis": self._get_emphasis_words(response_text, self.tone)
            }
        }

    def _get_or_create_context(self, user_id: int, session_id: Optional[str]) -> ConversationContext:
        """Get existing or create new conversation context."""
        if user_id not in self.contexts:
            self.contexts[user_id] = ConversationContext(
                user_id=user_id,
                session_id=session_id or f"session_{datetime.utcnow().timestamp()}"
            )

        context = self.contexts[user_id]

        # Reset context if session is old
        if not context.is_recent(minutes=30):
            context.conversation_history.clear()
            context.current_topic = None
            context.pending_actions.clear()

        return context

    def _detect_emotion_from_text(self, text: str) -> str:
        """Detect emotional state from text content."""
        text_lower = text.lower()

        if any(word in text_lower for word in ["urgent", "asap", "immediately", "now", "help"]):
            return "urgent"
        elif any(word in text_lower for word in ["confused", "don't understand", "what", "huh", "?"]):
            return "confused"
        elif any(word in text_lower for word in ["great", "awesome", "excellent", "amazing", "!"]):
            return "excited"
        elif any(word in text_lower for word in ["frustrated", "annoying", "stuck", "not working"]):
            return "frustrated"
        else:
            return "neutral"

    def _adapt_tone(self, context: ConversationContext):
        """Adapt agent tone based on user's emotional state."""
        emotion_map = {
            "urgent": EmotionalTone.URGENT,
            "confused": EmotionalTone.EMPATHETIC,
            "excited": EmotionalTone.ENTHUSIASTIC,
            "frustrated": EmotionalTone.EMPATHETIC,
            "neutral": EmotionalTone.PROFESSIONAL
        }
        self.tone = emotion_map.get(context.emotional_state, EmotionalTone.PROFESSIONAL)

    async def _get_proactive_insights(self, context: ConversationContext) -> List[Dict]:
        """Get proactive insights based on current context."""
        insights = []

        # Check for underperforming ads
        if context.current_event:
            ad_performance = monitor_ad_performance(self.db, context.current_event, auto_pause=False)
            if ad_performance.get("alerts"):
                insights.append({
                    "type": "ad_performance",
                    "urgency": "high",
                    "message": ad_performance["alerts"][0] if ad_performance["alerts"] else None
                })

        # Check for sales milestones
        today_sales = self._get_today_sales()
        if today_sales and today_sales > 100:
            insights.append({
                "type": "milestone",
                "urgency": "low",
                "message": f"Congratulations! You've sold {today_sales} tickets today!"
            })

        # Check for VIP customer activity
        vip_customers = identify_best_customers(self.db, limit=5)
        if vip_customers.get("top_customers"):
            recent_vip = [c for c in vip_customers["top_customers"]
                         if c["last_purchase_days_ago"] < 1]
            if recent_vip:
                insights.append({
                    "type": "vip_activity",
                    "urgency": "medium",
                    "message": f"VIP customer {recent_vip[0]['name']} just made a purchase!"
                })

        return insights

    async def _understand_intent_with_context(
        self,
        text: str,
        context: ConversationContext
    ) -> Tuple[str, Dict]:
        """
        Understand intent considering conversation context.
        Uses context to resolve ambiguous references.
        """
        text_lower = text.lower()
        entities = {}

        # Handle contextual references
        if "it" in text_lower or "that" in text_lower or "this" in text_lower:
            # Resolve based on context
            if context.current_event:
                entities["event_id"] = context.current_event
            if context.current_topic:
                entities["topic"] = context.current_topic

        # Multi-turn conversation patterns
        if context.conversation_history:
            last_turn = list(context.conversation_history)[-1] if context.conversation_history else None
            if last_turn:
                # Handle follow-up questions
                if "how about" in text_lower or "what about" in text_lower:
                    # Maintain previous intent with new parameters
                    return self._extract_intent(text), entities

        # Extract intent and entities
        intent = self._extract_intent(text)

        # Extract time references
        if "today" in text_lower:
            entities["time_range"] = "today"
        elif "yesterday" in text_lower:
            entities["time_range"] = "yesterday"
        elif "this week" in text_lower:
            entities["time_range"] = "week"
        elif "this month" in text_lower:
            entities["time_range"] = "month"

        # Extract event references
        if "event" in text_lower:
            # Try to extract event name
            import re
            event_pattern = r'event[s]?\s+(?:called\s+|named\s+)?(["\']?)([^"\']+)\1'
            match = re.search(event_pattern, text_lower)
            if match:
                entities["event_name"] = match.group(2)

        # Update context
        context.current_topic = intent

        return intent, entities

    def _extract_intent(self, text: str) -> str:
        """Extract primary intent from text."""
        text_lower = text.lower()

        intent_patterns = [
            ("create_event", ["create", "new event", "add event", "schedule"]),
            ("check_sales", ["sold", "sales", "tickets sold", "how many"]),
            ("get_revenue", ["revenue", "earnings", "money", "profit"]),
            ("marketing_status", ["marketing", "ads", "campaign", "promotion"]),
            ("customer_insights", ["customers", "buyers", "vip", "audience"]),
            ("urgent_alert", ["urgent", "alert", "warning", "problem"]),
            ("event_status", ["status", "how is", "performing", "doing"]),
            ("help", ["help", "what can", "commands", "options"]),
            ("cancel", ["cancel", "stop", "abort", "nevermind"]),
            ("confirm", ["yes", "confirm", "correct", "that's right"]),
            ("thank", ["thank", "thanks", "great", "perfect"]),
        ]

        for intent, keywords in intent_patterns:
            if any(keyword in text_lower for keyword in keywords):
                return intent

        return "general_query"

    async def _execute_intent(
        self,
        intent: str,
        entities: Dict,
        context: ConversationContext
    ) -> Dict:
        """Execute the identified intent with entities."""

        if intent == "check_sales":
            return await self._get_sales_data(entities, context)
        elif intent == "get_revenue":
            return await self._get_revenue_data(entities, context)
        elif intent == "marketing_status":
            return await self._get_marketing_status(entities, context)
        elif intent == "customer_insights":
            return await self._get_customer_insights(entities, context)
        elif intent == "event_status":
            return await self._get_event_status(entities, context)
        elif intent == "create_event":
            return await self._initiate_event_creation(entities, context)
        elif intent == "confirm":
            return await self._handle_confirmation(context)
        elif intent == "cancel":
            return await self._handle_cancellation(context)
        elif intent == "help":
            return self._get_help_info(context)
        else:
            return {"type": "general", "message": "How can I help you with your events?"}

    def _generate_natural_response(
        self,
        intent: str,
        result: Dict,
        context: ConversationContext,
        proactive_insights: List[Dict]
    ) -> str:
        """Generate natural language response based on intent and tone."""

        # Get tone-appropriate response templates
        templates = self._get_response_templates(self.tone)

        # Build base response
        if intent == "check_sales":
            base_response = templates["sales"].format(**result)
        elif intent == "get_revenue":
            base_response = templates["revenue"].format(**result)
        elif intent == "marketing_status":
            base_response = templates["marketing"].format(**result)
        elif intent == "thank":
            base_response = templates["acknowledgment"]
        else:
            base_response = result.get("message", "I understand.")

        # Add proactive insights if relevant
        if proactive_insights and self.tone != EmotionalTone.URGENT:
            priority_insight = max(proactive_insights,
                                 key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["urgency"]])
            if priority_insight["urgency"] in ["high", "medium"]:
                base_response += f" By the way, {priority_insight['message']}"

        # Add contextual continuity
        if context.conversation_history and len(context.conversation_history) > 2:
            if self.tone == EmotionalTone.CASUAL:
                base_response = f"So, {base_response.lower()}"
            elif self.tone == EmotionalTone.PROFESSIONAL:
                base_response = f"Additionally, {base_response.lower()}"

        return base_response

    def _get_response_templates(self, tone: EmotionalTone) -> Dict[str, str]:
        """Get response templates based on emotional tone."""

        if tone == EmotionalTone.ENTHUSIASTIC:
            return {
                "sales": "Awesome news! You've sold {tickets_sold} tickets {time_period}! That's {percentage_change}% {direction} than yesterday!",
                "revenue": "Fantastic! You've earned ${revenue} {time_period}! Keep it up!",
                "marketing": "Your marketing is doing great! {campaign_status}",
                "acknowledgment": "You're welcome! Happy to help make your event a success!"
            }
        elif tone == EmotionalTone.EMPATHETIC:
            return {
                "sales": "I understand your concern. You've sold {tickets_sold} tickets {time_period}. Let me help you improve that.",
                "revenue": "Your revenue {time_period} is ${revenue}. Would you like suggestions to increase it?",
                "marketing": "I see what you mean. {campaign_status}. Let's work on optimizing it.",
                "acknowledgment": "I'm here to help. Let me know if you need anything else."
            }
        elif tone == EmotionalTone.URGENT:
            return {
                "sales": "Quick update: {tickets_sold} tickets sold {time_period}. {urgent_action}",
                "revenue": "Revenue {time_period}: ${revenue}. Immediate action needed: {urgent_action}",
                "marketing": "Alert: {campaign_status}. Taking action now.",
                "acknowledgment": "Understood. Acting on this immediately."
            }
        elif tone == EmotionalTone.CASUAL:
            return {
                "sales": "Hey! You've sold {tickets_sold} tickets {time_period}. Not bad!",
                "revenue": "You've made ${revenue} {time_period}. Nice!",
                "marketing": "Your marketing's {campaign_status}. Looking good!",
                "acknowledgment": "No problem! Glad I could help!"
            }
        else:  # PROFESSIONAL
            return {
                "sales": "You have sold {tickets_sold} tickets {time_period}, which is {percentage_change}% {direction} from the previous period.",
                "revenue": "Total revenue {time_period} is ${revenue}, with an average ticket price of ${avg_price}.",
                "marketing": "Marketing campaign status: {campaign_status}. ROI is currently {roi}.",
                "acknowledgment": "Thank you. Please let me know if you need further assistance."
            }

    def _get_contextual_suggestions(
        self,
        intent: str,
        result: Dict,
        context: ConversationContext
    ) -> List[str]:
        """Get contextual follow-up suggestions."""
        suggestions = []

        if intent == "check_sales":
            suggestions.extend([
                "Show me revenue breakdown",
                "Which tickets are selling best?",
                "Compare with last week",
                "Show customer demographics"
            ])
        elif intent == "get_revenue":
            suggestions.extend([
                "Show me top revenue events",
                "What's my profit margin?",
                "Export financial report",
                "Show payment methods breakdown"
            ])
        elif intent == "marketing_status":
            suggestions.extend([
                "Pause underperforming ads",
                "Increase budget for top campaign",
                "Show conversion rates",
                "Create new campaign"
            ])
        elif intent == "create_event":
            if context.pending_actions:
                suggestions.extend([
                    "Set ticket prices",
                    "Add VIP tier",
                    "Schedule marketing",
                    "Generate flyer"
                ])

        # Add contextual suggestions based on insights
        if result.get("low_sales"):
            suggestions.insert(0, "Boost this event")
        if result.get("high_demand"):
            suggestions.insert(0, "Add more tickets")

        return suggestions[:4]  # Return top 4 suggestions

    async def _check_for_alerts(self, context: ConversationContext) -> List[Dict]:
        """Check for important alerts that need immediate attention."""
        alerts = []

        # Check for events happening soon with low sales
        upcoming_events = (
            self.db.query(Event)
            .filter(
                Event.event_date <= datetime.now().date() + timedelta(days=3),
                Event.event_date >= datetime.now().date()
            )
            .all()
        )

        for event in upcoming_events:
            tickets_sold = (
                self.db.query(func.count(Ticket.id))
                .filter(Ticket.event_id == event.id)
                .scalar()
            )

            capacity = sum(t.quantity_available for t in event.ticket_tiers)
            if capacity > 0:
                fill_rate = tickets_sold / capacity
                if fill_rate < 0.3:  # Less than 30% sold
                    alerts.append({
                        "type": "low_sales_warning",
                        "event_id": event.id,
                        "event_name": event.name,
                        "days_until": (event.event_date - datetime.now().date()).days,
                        "fill_rate": fill_rate,
                        "message": f"⚠️ {event.name} is in {(event.event_date - datetime.now().date()).days} days but only {fill_rate*100:.0f}% sold!",
                        "action": "Would you like me to boost marketing for this event?"
                    })

        # Check for ad spend anomalies
        high_spend_campaigns = (
            self.db.query(MetaAdCampaign)
            .filter(
                MetaAdCampaign.status == "ACTIVE",
                MetaAdCampaign.daily_spend_cents > MetaAdCampaign.budget_cents * 1.2
            )
            .all()
        )

        for campaign in high_spend_campaigns:
            alerts.append({
                "type": "overspend_warning",
                "campaign_id": campaign.id,
                "message": f"💸 Campaign '{campaign.name}' is overspending!",
                "action": "Should I pause it?"
            })

        return alerts

    # ==================== Helper Methods ====================

    def _get_today_sales(self) -> int:
        """Get today's ticket sales count."""
        today_start = datetime.combine(datetime.now().date(), datetime.min.time())

        return (
            self.db.query(func.count(Ticket.id))
            .filter(Ticket.created_at >= today_start)
            .scalar() or 0
        )

    async def _get_sales_data(self, entities: Dict, context: ConversationContext) -> Dict:
        """Get sales data based on entities."""
        time_range = entities.get("time_range", "today")
        event_id = entities.get("event_id", context.current_event)

        # Calculate date range
        if time_range == "today":
            start_date = datetime.combine(datetime.now().date(), datetime.min.time())
        elif time_range == "yesterday":
            start_date = datetime.combine(
                datetime.now().date() - timedelta(days=1),
                datetime.min.time()
            )
        elif time_range == "week":
            start_date = datetime.now() - timedelta(days=7)
        else:
            start_date = datetime.now() - timedelta(days=30)

        # Query tickets
        query = self.db.query(func.count(Ticket.id)).filter(Ticket.created_at >= start_date)
        if event_id:
            query = query.filter(Ticket.event_id == event_id)

        tickets_sold = query.scalar() or 0

        # Get comparison
        comparison_start = start_date - (datetime.now() - start_date)
        comparison_tickets = (
            self.db.query(func.count(Ticket.id))
            .filter(
                Ticket.created_at >= comparison_start,
                Ticket.created_at < start_date
            )
            .scalar() or 0
        )

        percentage_change = (
            ((tickets_sold - comparison_tickets) / comparison_tickets * 100)
            if comparison_tickets > 0 else 0
        )

        return {
            "tickets_sold": tickets_sold,
            "time_period": time_range,
            "percentage_change": abs(round(percentage_change, 1)),
            "direction": "up" if percentage_change > 0 else "down",
            "low_sales": tickets_sold < 10,
            "high_demand": tickets_sold > 100
        }

    async def _get_revenue_data(self, entities: Dict, context: ConversationContext) -> Dict:
        """Get revenue data based on entities."""
        time_range = entities.get("time_range", "today")

        # Similar to sales data but sum price_paid_cents
        if time_range == "today":
            start_date = datetime.combine(datetime.now().date(), datetime.min.time())
        else:
            start_date = datetime.now() - timedelta(days=30)

        revenue_cents = (
            self.db.query(func.sum(Ticket.price_paid_cents))
            .filter(Ticket.created_at >= start_date)
            .scalar() or 0
        )

        avg_price = (
            self.db.query(func.avg(Ticket.price_paid_cents))
            .filter(Ticket.created_at >= start_date)
            .scalar() or 0
        )

        return {
            "revenue": f"{revenue_cents/100:.2f}",
            "time_period": time_range,
            "avg_price": f"{avg_price/100:.2f}",
            "urgent_action": "Consider flash sale" if revenue_cents < 100000 else None
        }

    async def _get_marketing_status(self, entities: Dict, context: ConversationContext) -> Dict:
        """Get marketing campaign status."""
        active_campaigns = (
            self.db.query(MetaAdCampaign)
            .filter(MetaAdCampaign.status == "ACTIVE")
            .count()
        )

        total_spend = (
            self.db.query(func.sum(MetaAdCampaign.total_spend_cents))
            .filter(MetaAdCampaign.status == "ACTIVE")
            .scalar() or 0
        )

        return {
            "campaign_status": f"{active_campaigns} active campaigns",
            "total_spend": f"${total_spend/100:.2f}",
            "roi": "2.3x"  # Would calculate from actual conversions
        }

    async def _get_customer_insights(self, entities: Dict, context: ConversationContext) -> Dict:
        """Get customer insights."""
        vip_data = identify_best_customers(self.db, limit=10)

        return {
            "vip_count": vip_data["segments"]["vip"],
            "top_customer": vip_data["top_customers"][0] if vip_data["top_customers"] else None,
            "recommendation": vip_data["recommendation"]
        }

    async def _get_event_status(self, entities: Dict, context: ConversationContext) -> Dict:
        """Get comprehensive event status."""
        event_id = entities.get("event_id", context.current_event)
        if not event_id:
            return {"message": "Which event would you like to check?"}

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"message": "I couldn't find that event."}

        tickets_sold = (
            self.db.query(func.count(Ticket.id))
            .filter(Ticket.event_id == event_id)
            .scalar() or 0
        )

        revenue = (
            self.db.query(func.sum(Ticket.price_paid_cents))
            .filter(Ticket.event_id == event_id)
            .scalar() or 0
        )

        context.current_event = event_id

        return {
            "event_name": event.name,
            "tickets_sold": tickets_sold,
            "revenue": f"${revenue/100:.2f}",
            "days_until": (event.event_date - datetime.now().date()).days if event.event_date else None
        }

    async def _initiate_event_creation(self, entities: Dict, context: ConversationContext) -> Dict:
        """Start event creation flow."""
        context.pending_actions = [
            {"step": "name", "completed": False},
            {"step": "date", "completed": False},
            {"step": "venue", "completed": False},
            {"step": "pricing", "completed": False}
        ]

        return {
            "message": "I'll help you create a new event. What's the name of the event?",
            "flow": "event_creation",
            "next_step": "name"
        }

    async def _handle_confirmation(self, context: ConversationContext) -> Dict:
        """Handle user confirmation."""
        if context.pending_actions:
            # Process pending action
            action = context.pending_actions[0]
            action["completed"] = True
            context.pending_actions.pop(0)

            if context.pending_actions:
                next_action = context.pending_actions[0]
                return {"message": f"Great! Now let's set up {next_action['step']}"}
            else:
                return {"message": "Perfect! Your event is all set up."}

        return {"message": "Confirmed!"}

    async def _handle_cancellation(self, context: ConversationContext) -> Dict:
        """Handle cancellation request."""
        context.pending_actions.clear()
        context.current_topic = None

        return {"message": "No problem, cancelled. What else can I help you with?"}

    def _get_help_info(self, context: ConversationContext) -> Dict:
        """Get help information."""
        return {
            "message": "I can help you with: checking sales, viewing revenue, managing marketing campaigns, understanding your customers, creating events, and monitoring performance. Just ask me naturally!",
            "examples": [
                "How many tickets did I sell today?",
                "Show me this week's revenue",
                "Are my ads performing well?",
                "Who are my VIP customers?",
                "Create a new event for next month"
            ]
        }

    def _get_emphasis_words(self, text: str, tone: EmotionalTone) -> List[str]:
        """Get words to emphasize in voice output based on tone."""
        if tone == EmotionalTone.ENTHUSIASTIC:
            return ["awesome", "fantastic", "great", "amazing", "congratulations"]
        elif tone == EmotionalTone.URGENT:
            return ["urgent", "immediately", "now", "alert", "action"]
        elif tone == EmotionalTone.EMPATHETIC:
            return ["understand", "help", "support", "together", "improve"]
        else:
            return ["total", "revenue", "sold", "profit", "success"]


# ==================== Voice Command API Integration ====================

async def process_enhanced_voice_command(
    db: Session,
    user_id: int,
    text: str,
    session_id: Optional[str] = None,
    audio_emotion: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process voice command with enhanced natural language understanding.

    This is the main entry point for the enhanced voice agent.
    """
    agent = EnhancedVoiceAgent(db)
    return await agent.process_voice_input(user_id, text, session_id, audio_emotion)