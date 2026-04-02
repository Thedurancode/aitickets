"""
Social Proof & FOMO Engine

Real-time widgets to increase urgency and conversions:
- Live viewer count
- Recent purchase notifications
- Scarcity indicators
- Countdown timers
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import random

from app.models import Event, Ticket, TicketTier, PageView


class SocialProofEngine:
    """Generate social proof and FOMO signals for events."""

    def __init__(self, db: Session):
        self.db = db

    def get_live_viewers(self, event_id: int) -> int:
        """Get current number of people viewing this event."""
        # Count page views in last 5 minutes
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)

        count = self.db.query(func.count(PageView.id)).filter(
            and_(
                PageView.event_id == event_id,
                PageView.timestamp >= five_min_ago
            )
        ).scalar() or 0

        # Add some randomness for realism (10-30% boost)
        boost = random.uniform(1.1, 1.3)
        return max(1, int(count * boost))

    def get_recent_purchases(self, event_id: int, limit: int = 5) -> List[Dict]:
        """Get recent ticket purchases for social proof."""
        recent_tickets = self.db.query(Ticket).join(
            TicketTier
        ).filter(
            TicketTier.event_id == event_id,
            Ticket.purchased_at.isnot(None),
            Ticket.purchased_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(
            Ticket.purchased_at.desc()
        ).limit(limit).all()

        purchases = []
        for ticket in recent_tickets:
            # Get event goer info
            goer = ticket.event_goer

            # Anonymize for privacy
            first_name = goer.name.split()[0] if goer.name else "Someone"

            # Generate fake location (in production, use IP geolocation)
            locations = ["Brooklyn", "Manhattan", "Queens", "Bronx", "Staten Island",
                        "Jersey City", "Newark", "Hoboken", "Long Island City"]
            location = random.choice(locations)

            # Time ago
            time_ago = self._format_time_ago(ticket.purchased_at)

            purchases.append({
                "name": first_name,
                "location": location,
                "time_ago": time_ago,
                "quantity": 1  # Could track from checkout session
            })

        return purchases

    def get_velocity(self, event_id: int) -> Dict:
        """Calculate ticket sales velocity (tickets/hour)."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        recent_sales = self.db.query(func.count(Ticket.id)).join(
            TicketTier
        ).filter(
            TicketTier.event_id == event_id,
            Ticket.purchased_at >= one_hour_ago
        ).scalar() or 0

        # Calculate 24hr average
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        daily_sales = self.db.query(func.count(Ticket.id)).join(
            TicketTier
        ).filter(
            TicketTier.event_id == event_id,
            Ticket.purchased_at >= one_day_ago
        ).scalar() or 0

        avg_per_hour = daily_sales / 24 if daily_sales > 0 else 0

        # Determine velocity status
        if recent_sales >= avg_per_hour * 2:
            status = "hot"  # Selling 2x faster than usual
            message = f"🔥 {recent_sales} tickets sold in the last hour!"
        elif recent_sales >= avg_per_hour * 1.5:
            status = "warm"
            message = f"⚡ {recent_sales} tickets sold in the last hour"
        else:
            status = "normal"
            message = None

        return {
            "recent_sales": recent_sales,
            "avg_per_hour": round(avg_per_hour, 1),
            "status": status,
            "message": message
        }

    def get_scarcity_indicators(self, event_id: int) -> Dict:
        """Calculate scarcity signals for FOMO."""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {}

        # Calculate total inventory
        total_available = sum(tier.quantity_available for tier in event.ticket_tiers)
        total_sold = sum(tier.quantity_sold for tier in event.ticket_tiers)
        total_capacity = total_available + total_sold

        if total_capacity == 0:
            return {}

        # Calculate percentage sold
        pct_sold = (total_sold / total_capacity) * 100

        indicators = {
            "total_available": total_available,
            "total_sold": total_sold,
            "pct_sold": round(pct_sold, 1),
            "messages": []
        }

        # Generate scarcity messages
        if total_available <= 10:
            indicators["messages"].append({
                "type": "critical",
                "icon": "🚨",
                "text": f"Only {total_available} tickets left!"
            })
        elif total_available <= 50:
            indicators["messages"].append({
                "type": "warning",
                "icon": "⚠️",
                "text": f"Only {total_available} tickets remaining"
            })

        if pct_sold >= 90:
            indicators["messages"].append({
                "type": "urgent",
                "icon": "🔥",
                "text": f"{round(pct_sold)}% sold out - almost gone!"
            })
        elif pct_sold >= 75:
            indicators["messages"].append({
                "type": "warning",
                "icon": "⚡",
                "text": f"{round(pct_sold)}% sold - selling fast!"
            })

        # Check for lowest price tier
        lowest_tier = min(event.ticket_tiers, key=lambda t: t.price, default=None)
        if lowest_tier and lowest_tier.quantity_available <= 5:
            indicators["messages"].append({
                "type": "price",
                "icon": "💰",
                "text": f"Only {lowest_tier.quantity_available} tickets left at ${lowest_tier.price/100:.0f}"
            })

        return indicators

    def get_countdown_timers(self, event_id: int) -> List[Dict]:
        """Generate countdown timers for urgency."""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return []

        timers = []
        now = datetime.utcnow()

        # Parse event date
        try:
            event_datetime = datetime.strptime(f"{event.event_date} {event.event_time}", "%Y-%m-%d %H:%M")
        except:
            return timers

        # Time until event
        time_until = event_datetime - now
        if time_until.total_seconds() > 0:
            if time_until.days == 0:
                hours = int(time_until.total_seconds() / 3600)
                timers.append({
                    "type": "event_start",
                    "icon": "⏰",
                    "text": f"Event starts in {hours} hours!",
                    "seconds": int(time_until.total_seconds())
                })
            elif time_until.days <= 7:
                timers.append({
                    "type": "event_start",
                    "icon": "📅",
                    "text": f"Event in {time_until.days} days",
                    "seconds": int(time_until.total_seconds())
                })

        # Check for sale end time (if configured)
        if event.sale_start_date and event.sale_start_time:
            try:
                sale_start = datetime.strptime(
                    f"{event.sale_start_date} {event.sale_start_time}",
                    "%Y-%m-%d %H:%M"
                )

                # If sale hasn't started yet
                if sale_start > now:
                    time_until_sale = sale_start - now
                    timers.append({
                        "type": "sale_start",
                        "icon": "🎟️",
                        "text": f"Tickets on sale in {time_until_sale.days}d {time_until_sale.seconds//3600}h",
                        "seconds": int(time_until_sale.total_seconds())
                    })
            except:
                pass

        return timers

    def get_social_proof_bundle(self, event_id: int) -> Dict:
        """Get all social proof signals for an event."""
        return {
            "live_viewers": self.get_live_viewers(event_id),
            "recent_purchases": self.get_recent_purchases(event_id),
            "velocity": self.get_velocity(event_id),
            "scarcity": self.get_scarcity_indicators(event_id),
            "countdowns": self.get_countdown_timers(event_id),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _format_time_ago(self, dt: datetime) -> str:
        """Format datetime as 'X minutes ago', 'X hours ago', etc."""
        now = datetime.utcnow()
        diff = now - dt

        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"


def get_social_proof_engine(db: Session) -> SocialProofEngine:
    """Factory function to get social proof engine."""
    return SocialProofEngine(db)
