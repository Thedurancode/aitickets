"""
Customer DNA Profiling System
Deep behavioral intelligence for personalized experiences and predictions
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import EventGoer, Ticket, Event, TicketTier, PromoCode


class CustomerSegment(str, Enum):
    VIP_FREQUENT = "vip_frequent"  # High value, frequent buyer
    VIP_OCCASIONAL = "vip_occasional"  # High value, less frequent
    REGULAR_LOYAL = "regular_loyal"  # Medium value, consistent
    BARGAIN_HUNTER = "bargain_hunter"  # Price sensitive
    IMPULSE_BUYER = "impulse_buyer"  # Quick decisions
    GROUP_ORGANIZER = "group_organizer"  # Buys for groups
    NEW_CUSTOMER = "new_customer"  # First time or very new
    AT_RISK = "at_risk"  # Declining engagement
    DORMANT = "dormant"  # Haven't purchased recently


@dataclass
class PurchasePattern:
    """Customer's purchase behavior patterns"""
    avg_time_to_decision: float  # Hours from first view to purchase
    preferred_purchase_time: str  # Time of day
    preferred_purchase_day: str  # Day of week
    impulse_score: float  # 0-1, likelihood of impulse purchase
    research_score: float  # 0-1, how much they research
    group_buy_tendency: float  # 0-1, likelihood to buy multiple tickets
    avg_group_size: float
    channel_preference: str  # web, mobile, voice
    device_type: str  # desktop, mobile, tablet
    cart_abandonment_rate: float


@dataclass
class EventPreferences:
    """Customer's event preferences"""
    favorite_genres: List[str]
    favorite_artists: List[str]
    preferred_days: List[str]  # Days of week
    preferred_times: List[str]  # morning, afternoon, evening, night
    preferred_venues: List[str]
    travel_radius_miles: float
    indoor_outdoor_preference: str  # indoor, outdoor, both
    season_preferences: List[str]  # spring, summer, fall, winter
    event_types: List[str]  # concert, festival, comedy, sports, etc.


@dataclass
class PriceProfile:
    """Customer's pricing behavior"""
    price_sensitivity: float  # 0-1, how sensitive to price
    avg_ticket_price: float
    max_ticket_price: float
    min_ticket_price: float
    tier_preference: str  # vip, premium, general, budget
    promo_code_usage_rate: float  # 0-1
    early_bird_tendency: float  # 0-1, likelihood to buy early for discount
    surge_tolerance: float  # 0-1, willingness to pay surge pricing
    bundle_preference: float  # 0-1, likelihood to buy bundles/packages


@dataclass
class SocialProfile:
    """Customer's social behavior"""
    referral_score: float  # 0-1, likelihood to refer others
    influence_score: float  # 0-1, ability to influence others
    social_sharing_rate: float  # 0-1
    review_tendency: float  # 0-1, likelihood to leave reviews
    community_engagement: float  # 0-1
    friend_network_size: int  # Estimated based on group purchases
    trendsetter_score: float  # 0-1, early adopter tendency


@dataclass
class CustomerDNA:
    """Complete customer DNA profile"""
    customer_id: int
    email: str
    segment: CustomerSegment
    purchase_patterns: PurchasePattern
    event_preferences: EventPreferences
    price_profile: PriceProfile
    social_profile: SocialProfile
    lifetime_value: float
    total_events: int
    total_tickets: int
    total_spent: float
    first_purchase_date: datetime
    last_purchase_date: datetime
    churn_risk: float  # 0-1, likelihood to stop buying
    next_purchase_prediction: Dict  # Predicted next purchase
    personalization_tags: List[str]
    updated_at: datetime = field(default_factory=datetime.utcnow)


class CustomerDNAProfiler:
    """System to build and maintain customer DNA profiles"""

    def __init__(self, db: Session):
        self.db = db
        self.profiles_cache: Dict[int, CustomerDNA] = {}

    def build_customer_dna(self, customer_id: int) -> Optional[CustomerDNA]:
        """Build complete DNA profile for a customer"""

        customer = self.db.query(EventGoer).filter(EventGoer.id == customer_id).first()
        if not customer:
            return None

        # Get all customer's tickets
        tickets = self.db.query(Ticket).filter(
            Ticket.event_goer_id == customer_id,
            Ticket.status.in_(["paid", "checked_in"])
        ).all()

        if not tickets:
            return self._create_new_customer_profile(customer)

        # Build each component
        purchase_patterns = self._analyze_purchase_patterns(customer_id, tickets)
        event_preferences = self._analyze_event_preferences(customer_id, tickets)
        price_profile = self._analyze_price_behavior(customer_id, tickets)
        social_profile = self._analyze_social_behavior(customer_id, tickets)

        # Calculate metrics
        lifetime_value = self._calculate_lifetime_value(tickets)
        segment = self._determine_segment(customer_id, tickets, lifetime_value)
        churn_risk = self._calculate_churn_risk(customer_id, tickets)
        next_purchase = self._predict_next_purchase(customer_id, purchase_patterns, event_preferences)

        # Generate tags
        tags = self._generate_personalization_tags(
            segment, purchase_patterns, event_preferences, price_profile
        )

        # Create DNA profile
        dna = CustomerDNA(
            customer_id=customer_id,
            email=customer.email,
            segment=segment,
            purchase_patterns=purchase_patterns,
            event_preferences=event_preferences,
            price_profile=price_profile,
            social_profile=social_profile,
            lifetime_value=lifetime_value,
            total_events=len(set(t.event_id for t in tickets)),
            total_tickets=len(tickets),
            total_spent=sum(t.price_paid for t in tickets),
            first_purchase_date=min(t.created_at for t in tickets),
            last_purchase_date=max(t.created_at for t in tickets),
            churn_risk=churn_risk,
            next_purchase_prediction=next_purchase,
            personalization_tags=tags
        )

        # Cache the profile
        self.profiles_cache[customer_id] = dna

        return dna

    def _create_new_customer_profile(self, customer: EventGoer) -> CustomerDNA:
        """Create profile for new customer with no purchase history"""
        return CustomerDNA(
            customer_id=customer.id,
            email=customer.email,
            segment=CustomerSegment.NEW_CUSTOMER,
            purchase_patterns=PurchasePattern(
                avg_time_to_decision=0,
                preferred_purchase_time="unknown",
                preferred_purchase_day="unknown",
                impulse_score=0.5,
                research_score=0.5,
                group_buy_tendency=0.3,
                avg_group_size=1,
                channel_preference="unknown",
                device_type="unknown",
                cart_abandonment_rate=0
            ),
            event_preferences=EventPreferences(
                favorite_genres=[],
                favorite_artists=[],
                preferred_days=[],
                preferred_times=[],
                preferred_venues=[],
                travel_radius_miles=25,
                indoor_outdoor_preference="both",
                season_preferences=[],
                event_types=[]
            ),
            price_profile=PriceProfile(
                price_sensitivity=0.5,
                avg_ticket_price=0,
                max_ticket_price=0,
                min_ticket_price=0,
                tier_preference="general",
                promo_code_usage_rate=0,
                early_bird_tendency=0.5,
                surge_tolerance=0.5,
                bundle_preference=0.5
            ),
            social_profile=SocialProfile(
                referral_score=0.5,
                influence_score=0.3,
                social_sharing_rate=0.3,
                review_tendency=0.3,
                community_engagement=0.3,
                friend_network_size=0,
                trendsetter_score=0.5
            ),
            lifetime_value=0,
            total_events=0,
            total_tickets=0,
            total_spent=0,
            first_purchase_date=datetime.utcnow(),
            last_purchase_date=datetime.utcnow(),
            churn_risk=0.1,
            next_purchase_prediction={},
            personalization_tags=["new_customer", "unknown_preferences"]
        )

    def _analyze_purchase_patterns(self, customer_id: int, tickets: List[Ticket]) -> PurchasePattern:
        """Analyze customer's purchase behavior patterns"""

        # Group tickets by purchase session (same timestamp)
        purchase_sessions = defaultdict(list)
        for ticket in tickets:
            session_key = ticket.created_at.strftime("%Y-%m-%d %H:%M")
            purchase_sessions[session_key].append(ticket)

        # Calculate patterns
        group_sizes = [len(session) for session in purchase_sessions.values()]
        avg_group_size = statistics.mean(group_sizes) if group_sizes else 1

        # Time of day analysis
        purchase_hours = [ticket.created_at.hour for ticket in tickets]
        preferred_hour = max(set(purchase_hours), key=purchase_hours.count) if purchase_hours else 12

        if preferred_hour < 6:
            preferred_time = "late_night"
        elif preferred_hour < 12:
            preferred_time = "morning"
        elif preferred_hour < 17:
            preferred_time = "afternoon"
        elif preferred_hour < 21:
            preferred_time = "evening"
        else:
            preferred_time = "night"

        # Day of week analysis
        purchase_days = [ticket.created_at.strftime("%A") for ticket in tickets]
        preferred_day = max(set(purchase_days), key=purchase_days.count) if purchase_days else "Friday"

        # Impulse vs research (simplified - would need session tracking)
        days_before_event = []
        for ticket in tickets:
            event = self.db.query(Event).filter(Event.id == ticket.event_id).first()
            if event:
                event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
                days_diff = (event_date - ticket.created_at).days
                days_before_event.append(days_diff)

        avg_days_before = statistics.mean(days_before_event) if days_before_event else 14
        impulse_score = max(0, min(1, 1 - (avg_days_before / 30)))  # Closer to event = more impulsive

        return PurchasePattern(
            avg_time_to_decision=24.0,  # Would need session tracking for real calculation
            preferred_purchase_time=preferred_time,
            preferred_purchase_day=preferred_day,
            impulse_score=impulse_score,
            research_score=1 - impulse_score,
            group_buy_tendency=min(1, (avg_group_size - 1) / 4),  # Normalize to 0-1
            avg_group_size=avg_group_size,
            channel_preference="web",  # Would need tracking
            device_type="desktop",  # Would need tracking
            cart_abandonment_rate=0.15  # Would need tracking
        )

    def _analyze_event_preferences(self, customer_id: int, tickets: List[Ticket]) -> EventPreferences:
        """Analyze customer's event preferences"""

        # Get all events attended
        event_ids = [t.event_id for t in tickets]
        events = self.db.query(Event).filter(Event.id.in_(event_ids)).all()

        # Extract preferences
        genres = []
        artists = []
        venues = []
        days = []
        times = []
        event_types = []

        for event in events:
            # Get event time preference
            hour = int(event.event_time.split(":")[0])
            if hour < 12:
                times.append("morning")
            elif hour < 17:
                times.append("afternoon")
            elif hour < 21:
                times.append("evening")
            else:
                times.append("night")

            # Day of week
            event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
            days.append(event_date.strftime("%A"))

            # Venue
            if event.venue:
                venues.append(event.venue.name)

            # Artist/genre (if available)
            if event.artist:
                artists.append(event.artist.name)
                if hasattr(event.artist, 'genre'):
                    genres.append(event.artist.genre)

        # Get most common preferences
        favorite_genres = list(set(genres))[:3] if genres else []
        favorite_artists = list(set(artists))[:3] if artists else []
        preferred_days = [max(set(days), key=days.count)] if days else ["Friday", "Saturday"]
        preferred_times = [max(set(times), key=times.count)] if times else ["evening"]
        preferred_venues = list(set(venues))[:3] if venues else []

        return EventPreferences(
            favorite_genres=favorite_genres,
            favorite_artists=favorite_artists,
            preferred_days=preferred_days,
            preferred_times=preferred_times,
            preferred_venues=preferred_venues,
            travel_radius_miles=25.0,  # Default, would calculate from venue distances
            indoor_outdoor_preference="both",
            season_preferences=["summer", "fall"],  # Would analyze from dates
            event_types=["concert", "festival"]  # Would categorize events
        )

    def _analyze_price_behavior(self, customer_id: int, tickets: List[Ticket]) -> PriceProfile:
        """Analyze customer's pricing behavior"""

        prices = [t.price_paid for t in tickets]

        # Get tier information
        tier_counts = defaultdict(int)
        promo_uses = 0

        for ticket in tickets:
            tier = self.db.query(TicketTier).filter(TicketTier.id == ticket.tier_id).first()
            if tier:
                if "vip" in tier.name.lower():
                    tier_counts["vip"] += 1
                elif "premium" in tier.name.lower():
                    tier_counts["premium"] += 1
                elif "general" in tier.name.lower():
                    tier_counts["general"] += 1
                else:
                    tier_counts["budget"] += 1

            if ticket.promo_code_id:
                promo_uses += 1

        # Determine tier preference
        if tier_counts:
            tier_preference = max(tier_counts.keys(), key=lambda k: tier_counts[k])
        else:
            tier_preference = "general"

        # Calculate metrics
        avg_price = statistics.mean(prices) if prices else 0
        max_price = max(prices) if prices else 0
        min_price = min(prices) if prices else 0

        # Price sensitivity (variance in prices - high variance = less sensitive)
        if len(prices) > 1:
            price_variance = statistics.variance(prices)
            price_sensitivity = max(0, min(1, 1 - (price_variance / 1000)))  # Normalize
        else:
            price_sensitivity = 0.5

        promo_rate = promo_uses / len(tickets) if tickets else 0

        return PriceProfile(
            price_sensitivity=price_sensitivity,
            avg_ticket_price=avg_price,
            max_ticket_price=max_price,
            min_ticket_price=min_price,
            tier_preference=tier_preference,
            promo_code_usage_rate=promo_rate,
            early_bird_tendency=0.6,  # Would need to track purchase timing
            surge_tolerance=0.4 if tier_preference in ["vip", "premium"] else 0.2,
            bundle_preference=0.5  # Would need bundle purchase data
        )

    def _analyze_social_behavior(self, customer_id: int, tickets: List[Ticket]) -> SocialProfile:
        """Analyze customer's social behavior"""

        # Group purchases indicate social connections
        purchase_sessions = defaultdict(list)
        for ticket in tickets:
            session_key = ticket.created_at.strftime("%Y-%m-%d %H:%M")
            purchase_sessions[session_key].append(ticket)

        group_purchases = [session for session in purchase_sessions.values() if len(session) > 1]

        # Estimate network size from unique companions
        estimated_network = len(group_purchases) * 3  # Rough estimate

        # Calculate scores (would need more data in production)
        influence_score = min(1, estimated_network / 50)  # Normalize

        return SocialProfile(
            referral_score=0.6 if group_purchases else 0.3,
            influence_score=influence_score,
            social_sharing_rate=0.4,  # Would need social media tracking
            review_tendency=0.3,  # Would need review data
            community_engagement=0.5,  # Would need engagement tracking
            friend_network_size=estimated_network,
            trendsetter_score=0.5  # Would analyze early adoption patterns
        )

    def _calculate_lifetime_value(self, tickets: List[Ticket]) -> float:
        """Calculate customer lifetime value"""

        if not tickets:
            return 0.0

        total_spent = sum(t.price_paid for t in tickets)

        # Get time span
        first_purchase = min(t.created_at for t in tickets)
        last_purchase = max(t.created_at for t in tickets)
        months_active = max(1, (last_purchase - first_purchase).days / 30)

        # Monthly spend rate
        monthly_rate = total_spent / months_active

        # Predict future value (simplified - 24 month projection)
        predicted_future = monthly_rate * 24

        return total_spent + (predicted_future * 0.5)  # Weight future value

    def _determine_segment(self, customer_id: int, tickets: List[Ticket], ltv: float) -> CustomerSegment:
        """Determine customer segment based on behavior"""

        if not tickets:
            return CustomerSegment.NEW_CUSTOMER

        # Calculate recency
        last_purchase = max(t.created_at for t in tickets)
        days_since_last = (datetime.utcnow() - last_purchase).days

        # Calculate frequency
        total_events = len(set(t.event_id for t in tickets))

        # High value customer
        if ltv > 1000:
            if total_events >= 5:
                return CustomerSegment.VIP_FREQUENT
            else:
                return CustomerSegment.VIP_OCCASIONAL

        # Regular customer
        elif ltv > 300:
            if days_since_last < 90:
                return CustomerSegment.REGULAR_LOYAL
            elif days_since_last > 180:
                return CustomerSegment.AT_RISK

        # Check for bargain hunting
        promo_uses = sum(1 for t in tickets if t.promo_code_id)
        if promo_uses / len(tickets) > 0.7:
            return CustomerSegment.BARGAIN_HUNTER

        # Dormant
        if days_since_last > 365:
            return CustomerSegment.DORMANT

        # Group organizer
        avg_group_size = len(tickets) / total_events
        if avg_group_size > 3:
            return CustomerSegment.GROUP_ORGANIZER

        # Impulse buyer (needs more logic)
        return CustomerSegment.IMPULSE_BUYER if total_events < 3 else CustomerSegment.REGULAR_LOYAL

    def _calculate_churn_risk(self, customer_id: int, tickets: List[Ticket]) -> float:
        """Calculate risk of customer churning"""

        if not tickets:
            return 0.1  # New customers have low initial churn risk

        # Factors that increase churn risk
        risk_factors = []

        # Recency - longer since last purchase = higher risk
        last_purchase = max(t.created_at for t in tickets)
        days_since = (datetime.utcnow() - last_purchase).days
        recency_risk = min(1, days_since / 365)  # Max out at 1 year
        risk_factors.append(recency_risk * 0.4)  # 40% weight

        # Declining frequency
        if len(tickets) >= 3:
            # Compare recent vs older purchase frequency
            midpoint = len(tickets) // 2
            older_tickets = sorted(tickets, key=lambda t: t.created_at)[:midpoint]
            recent_tickets = sorted(tickets, key=lambda t: t.created_at)[midpoint:]

            older_period = (older_tickets[-1].created_at - older_tickets[0].created_at).days + 1
            recent_period = (recent_tickets[-1].created_at - recent_tickets[0].created_at).days + 1

            older_frequency = len(older_tickets) / older_period if older_period > 0 else 0
            recent_frequency = len(recent_tickets) / recent_period if recent_period > 0 else 0

            if older_frequency > 0:
                frequency_decline = max(0, (older_frequency - recent_frequency) / older_frequency)
                risk_factors.append(frequency_decline * 0.3)  # 30% weight

        # No recent engagement (simplified)
        engagement_risk = 0.3 if days_since > 60 else 0
        risk_factors.append(engagement_risk * 0.3)  # 30% weight

        return min(1, sum(risk_factors))

    def _predict_next_purchase(
        self,
        customer_id: int,
        patterns: PurchasePattern,
        preferences: EventPreferences
    ) -> Dict:
        """Predict customer's next purchase"""

        prediction = {
            "likely_timeframe": "2-4 weeks",
            "likely_event_type": preferences.event_types[0] if preferences.event_types else "concert",
            "likely_price_range": [30, 60],  # Would calculate from price profile
            "likely_day": preferences.preferred_days[0] if preferences.preferred_days else "Friday",
            "likely_group_size": int(patterns.avg_group_size),
            "confidence": 0.7
        }

        # Adjust based on patterns
        if patterns.impulse_score > 0.7:
            prediction["likely_timeframe"] = "1 week"
            prediction["confidence"] = 0.6
        elif patterns.research_score > 0.7:
            prediction["likely_timeframe"] = "4-6 weeks"
            prediction["confidence"] = 0.8

        return prediction

    def _generate_personalization_tags(
        self,
        segment: CustomerSegment,
        patterns: PurchasePattern,
        preferences: EventPreferences,
        price_profile: PriceProfile
    ) -> List[str]:
        """Generate tags for personalization"""

        tags = [segment.value]

        # Behavioral tags
        if patterns.impulse_score > 0.7:
            tags.append("impulse_buyer")
        if patterns.research_score > 0.7:
            tags.append("researcher")
        if patterns.group_buy_tendency > 0.5:
            tags.append("group_buyer")

        # Preference tags
        if "Friday" in preferences.preferred_days or "Saturday" in preferences.preferred_days:
            tags.append("weekend_preference")
        if "evening" in preferences.preferred_times or "night" in preferences.preferred_times:
            tags.append("evening_preference")

        # Price tags
        if price_profile.price_sensitivity > 0.7:
            tags.append("price_sensitive")
        if price_profile.tier_preference == "vip":
            tags.append("premium_buyer")
        if price_profile.promo_code_usage_rate > 0.5:
            tags.append("promo_seeker")

        return tags

    def get_personalized_recommendations(self, customer_id: int, available_events: List[Event]) -> List[Dict]:
        """Get personalized event recommendations for customer"""

        # Get or build DNA profile
        dna = self.profiles_cache.get(customer_id) or self.build_customer_dna(customer_id)
        if not dna:
            return []

        recommendations = []

        for event in available_events:
            score = 0
            reasons = []

            # Match genres
            if hasattr(event.artist, 'genre') and event.artist.genre in dna.event_preferences.favorite_genres:
                score += 30
                reasons.append(f"Matches your favorite genre: {event.artist.genre}")

            # Match artists
            if event.artist and event.artist.name in dna.event_preferences.favorite_artists:
                score += 40
                reasons.append(f"You've enjoyed {event.artist.name} before")

            # Match preferred days
            event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
            day_name = event_date.strftime("%A")
            if day_name in dna.event_preferences.preferred_days:
                score += 20
                reasons.append(f"On your preferred day: {day_name}")

            # Price match
            tiers = self.db.query(TicketTier).filter(TicketTier.event_id == event.id).all()
            if tiers:
                min_price = min(t.price for t in tiers)
                if abs(min_price - dna.price_profile.avg_ticket_price) < 20:
                    score += 15
                    reasons.append("In your typical price range")

            # Venue match
            if event.venue and event.venue.name in dna.event_preferences.preferred_venues:
                score += 10
                reasons.append(f"At your favorite venue: {event.venue.name}")

            if score > 30:  # Threshold for recommendation
                recommendations.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "score": score,
                    "reasons": reasons,
                    "personalized_message": self._generate_personalized_message(dna, event)
                })

        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return recommendations[:5]  # Top 5 recommendations

    def _generate_personalized_message(self, dna: CustomerDNA, event: Event) -> str:
        """Generate personalized marketing message"""

        if dna.segment == CustomerSegment.VIP_FREQUENT:
            return f"Exclusive early access for our VIP member! {event.name} tickets now available."
        elif dna.segment == CustomerSegment.BARGAIN_HUNTER:
            return f"Special discount available! Save 20% on {event.name} with code SAVE20."
        elif dna.segment == CustomerSegment.GROUP_ORGANIZER:
            return f"Group discounts available! Bring your friends to {event.name}."
        elif dna.purchase_patterns.impulse_score > 0.7:
            return f"Limited tickets remaining for {event.name}! Don't miss out!"
        else:
            return f"You might enjoy {event.name} based on your preferences."

    def get_optimal_contact_time(self, customer_id: int) -> Dict:
        """Determine optimal time to contact customer"""

        dna = self.profiles_cache.get(customer_id) or self.build_customer_dna(customer_id)
        if not dna:
            return {"time": "evening", "day": "Friday", "confidence": 0.5}

        return {
            "time": dna.purchase_patterns.preferred_purchase_time,
            "day": dna.purchase_patterns.preferred_purchase_day,
            "channel": dna.purchase_patterns.channel_preference,
            "confidence": 0.8
        }

    def predict_purchase_probability(self, customer_id: int, event: Event, price: float) -> float:
        """Predict probability of customer purchasing tickets for specific event"""

        dna = self.profiles_cache.get(customer_id) or self.build_customer_dna(customer_id)
        if not dna:
            return 0.3  # Default for unknown customers

        probability = 0.5  # Base probability

        # Adjust based on preferences match
        if event.artist and event.artist.name in dna.event_preferences.favorite_artists:
            probability += 0.3

        # Price sensitivity
        if price > dna.price_profile.avg_ticket_price * 1.5:
            probability -= (0.2 * dna.price_profile.price_sensitivity)
        elif price < dna.price_profile.avg_ticket_price * 0.8:
            probability += 0.1

        # Recency boost
        days_since_last = (datetime.utcnow() - dna.last_purchase_date).days
        if days_since_last < 30:
            probability += 0.1
        elif days_since_last > 180:
            probability -= 0.2

        # Segment adjustments
        if dna.segment == CustomerSegment.VIP_FREQUENT:
            probability += 0.2
        elif dna.segment == CustomerSegment.AT_RISK:
            probability -= 0.1

        return max(0, min(1, probability))