"""
Enhanced Ticket Service with Event Publishing
Publishes domain events for real-time reactions instead of just database operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Ticket, TicketTier, Event, EventGoer, TicketStatus,
    PromoCode, DiscountType
)
from app.services.event_bus import (
    event_bus, EventType, DomainEvent,
    publish_ticket_sold, publish_inventory_low
)

logger = logging.getLogger(__name__)


class EventDrivenTicketService:
    """
    Ticket service that publishes events for real-time reactions.
    Every significant action publishes an event for other services to react to.
    """

    def __init__(self, db: Session):
        self.db = db

    async def sell_ticket(
        self,
        event_id: int,
        tier_id: int,
        customer_id: int,
        quantity: int = 1,
        promo_code: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Sell tickets and publish events for real-time reactions.
        """
        try:
            # Get tier and validate availability
            tier = self.db.query(TicketTier).filter(TicketTier.id == tier_id).first()
            if not tier:
                return {"error": "Ticket tier not found"}

            available = tier.quantity_available - tier.quantity_sold
            if available < quantity:
                return {"error": f"Only {available} tickets available"}

            # Calculate price with promo code
            unit_price = tier.price
            if promo_code:
                promo = self.db.query(PromoCode).filter(
                    PromoCode.code == promo_code,
                    PromoCode.event_id == event_id
                ).first()

                if promo and promo.is_valid():
                    if promo.discount_type == DiscountType.PERCENTAGE:
                        unit_price = int(unit_price * (1 - promo.discount_value / 100))
                    else:
                        unit_price = max(0, unit_price - promo.discount_value)

                    promo.uses_count += quantity

            # Create tickets
            tickets = []
            for i in range(quantity):
                ticket = Ticket(
                    event_id=event_id,
                    tier_id=tier_id,
                    event_goer_id=customer_id,
                    price_paid_cents=unit_price,
                    status=TicketStatus.CONFIRMED,
                    confirmation_code=f"TIX-{uuid4().hex[:8].upper()}",
                    metadata=metadata or {}
                )
                self.db.add(ticket)
                tickets.append(ticket)

            # Update tier sold count
            tier.quantity_sold += quantity

            # Commit to database
            self.db.commit()

            # Now publish events for real-time reactions
            correlation_id = str(uuid4())

            # Publish TICKET_SOLD event
            for ticket in tickets:
                await publish_ticket_sold(
                    ticket_id=ticket.id,
                    event_id=event_id,
                    customer_id=customer_id,
                    price_cents=unit_price,
                    tier_id=tier_id,
                    quantity=1
                )

            # Check inventory levels and publish events
            remaining = tier.quantity_available - tier.quantity_sold
            remaining_percentage = (remaining / tier.quantity_available * 100) if tier.quantity_available > 0 else 0

            if remaining == 0:
                # Tier sold out
                await event_bus.publish(DomainEvent(
                    event_type=EventType.TIER_SOLD_OUT,
                    aggregate_id=str(tier_id),
                    aggregate_type="tier",
                    data={
                        "event_id": event_id,
                        "tier_id": tier_id,
                        "tier_name": tier.name
                    },
                    metadata={"source": "ticket_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=correlation_id
                ))

                # Check if entire event is sold out
                total_available = self.db.query(
                    func.sum(TicketTier.quantity_available - TicketTier.quantity_sold)
                ).filter(TicketTier.event_id == event_id).scalar()

                if total_available == 0:
                    await event_bus.publish(DomainEvent(
                        event_type=EventType.EVENT_SOLD_OUT,
                        aggregate_id=str(event_id),
                        aggregate_type="event",
                        data={"event_id": event_id},
                        metadata={"source": "ticket_service"},
                        timestamp=datetime.now(timezone.utc),
                        correlation_id=correlation_id
                    ))

            elif remaining < 5:
                # Critical inventory
                await event_bus.publish(DomainEvent(
                    event_type=EventType.INVENTORY_CRITICAL,
                    aggregate_id=str(tier_id),
                    aggregate_type="tier",
                    data={
                        "event_id": event_id,
                        "tier_id": tier_id,
                        "remaining": remaining,
                        "tier_name": tier.name
                    },
                    metadata={"source": "ticket_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=correlation_id
                ))

            elif remaining_percentage < 10:
                # Low inventory warning
                await publish_inventory_low(
                    event_id=event_id,
                    tier_id=tier_id,
                    remaining=remaining,
                    total=tier.quantity_available
                )

            # Check for group booking (5+ tickets)
            if quantity >= 5:
                await event_bus.publish(DomainEvent(
                    event_type=EventType.GROUP_BOOKING,
                    aggregate_id=str(customer_id),
                    aggregate_type="customer",
                    data={
                        "customer_id": customer_id,
                        "event_id": event_id,
                        "group_size": quantity,
                        "ticket_ids": [t.id for t in tickets]
                    },
                    metadata={"source": "ticket_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=correlation_id
                ))

            # Check sales velocity for spike detection
            await self._check_sales_velocity(event_id, correlation_id)

            return {
                "success": True,
                "tickets": [
                    {
                        "id": t.id,
                        "confirmation_code": t.confirmation_code,
                        "price_paid_cents": t.price_paid_cents
                    }
                    for t in tickets
                ],
                "total_paid_cents": unit_price * quantity,
                "remaining_tickets": remaining
            }

        except Exception as e:
            logger.error(f"Error selling ticket: {e}", exc_info=True)
            self.db.rollback()
            return {"error": str(e)}

    async def refund_ticket(
        self,
        ticket_id: int,
        reason: str,
        refund_amount_cents: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Refund a ticket and publish refund event.
        """
        try:
            ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return {"error": "Ticket not found"}

            if ticket.status != TicketStatus.CONFIRMED:
                return {"error": "Ticket cannot be refunded"}

            # Update ticket status
            ticket.status = TicketStatus.REFUNDED
            ticket.refunded_at = datetime.now(timezone.utc)
            ticket.refund_reason = reason
            ticket.refund_amount_cents = refund_amount_cents or ticket.price_paid_cents

            # Update tier sold count
            tier = self.db.query(TicketTier).filter(TicketTier.id == ticket.tier_id).first()
            tier.quantity_sold = max(0, tier.quantity_sold - 1)

            self.db.commit()

            # Publish TICKET_REFUNDED event
            await event_bus.publish(DomainEvent(
                event_type=EventType.TICKET_REFUNDED,
                aggregate_id=str(ticket_id),
                aggregate_type="ticket",
                data={
                    "ticket_id": ticket_id,
                    "event_id": ticket.event_id,
                    "customer_id": ticket.event_goer_id,
                    "refund_amount_cents": ticket.refund_amount_cents,
                    "reason": reason
                },
                metadata={"source": "ticket_service"},
                timestamp=datetime.now(timezone.utc),
                correlation_id=str(uuid4())
            ))

            # Check if we need to notify waitlist
            remaining = tier.quantity_available - tier.quantity_sold
            if remaining > 0 and tier.quantity_sold == tier.quantity_available - 1:
                # Was sold out, now has availability
                logger.info(f"Ticket available after refund for tier {tier.id}")

            return {
                "success": True,
                "ticket_id": ticket_id,
                "refund_amount_cents": ticket.refund_amount_cents
            }

        except Exception as e:
            logger.error(f"Error refunding ticket: {e}", exc_info=True)
            self.db.rollback()
            return {"error": str(e)}

    async def check_in_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """
        Check in a ticket and publish check-in event.
        """
        try:
            ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return {"error": "Ticket not found"}

            if ticket.status != TicketStatus.CONFIRMED:
                return {"error": f"Ticket status is {ticket.status}, cannot check in"}

            if ticket.checked_in:
                return {"error": "Ticket already checked in"}

            # Update check-in status
            ticket.checked_in = True
            ticket.checked_in_at = datetime.now(timezone.utc)

            self.db.commit()

            # Publish TICKET_CHECKED_IN event
            await event_bus.publish(DomainEvent(
                event_type=EventType.TICKET_CHECKED_IN,
                aggregate_id=str(ticket_id),
                aggregate_type="ticket",
                data={
                    "ticket_id": ticket_id,
                    "event_id": ticket.event_id,
                    "customer_id": ticket.event_goer_id
                },
                metadata={"source": "ticket_service"},
                timestamp=datetime.now(timezone.utc),
                correlation_id=str(uuid4())
            ))

            return {
                "success": True,
                "ticket_id": ticket_id,
                "customer_name": f"{ticket.event_goer.first_name} {ticket.event_goer.last_name}"
            }

        except Exception as e:
            logger.error(f"Error checking in ticket: {e}", exc_info=True)
            self.db.rollback()
            return {"error": str(e)}

    async def _check_sales_velocity(self, event_id: int, correlation_id: str):
        """
        Check sales velocity and publish spike/stall events.
        """
        try:
            # Get sales in last hour
            one_hour_ago = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            recent_sales = self.db.query(func.count(Ticket.id)).filter(
                Ticket.event_id == event_id,
                Ticket.created_at >= one_hour_ago,
                Ticket.status == TicketStatus.CONFIRMED
            ).scalar()

            # Get sales from previous hour for comparison
            two_hours_ago = one_hour_ago.replace(hour=one_hour_ago.hour - 1)
            previous_sales = self.db.query(func.count(Ticket.id)).filter(
                Ticket.event_id == event_id,
                Ticket.created_at >= two_hours_ago,
                Ticket.created_at < one_hour_ago,
                Ticket.status == TicketStatus.CONFIRMED
            ).scalar()

            # Calculate velocity
            current_rate = recent_sales / 60  # Sales per minute

            # Check for spike (2x increase)
            if previous_sales > 0 and recent_sales > previous_sales * 2:
                await event_bus.publish(DomainEvent(
                    event_type=EventType.SALES_SPIKE,
                    aggregate_id=str(event_id),
                    aggregate_type="event",
                    data={
                        "event_id": event_id,
                        "sales_per_minute": current_rate,
                        "recent_sales": recent_sales,
                        "previous_sales": previous_sales
                    },
                    metadata={"source": "ticket_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=correlation_id
                ))

            # Check for stall (no sales in 3+ hours)
            three_hours_ago = one_hour_ago.replace(hour=one_hour_ago.hour - 3)
            last_three_hours = self.db.query(func.count(Ticket.id)).filter(
                Ticket.event_id == event_id,
                Ticket.created_at >= three_hours_ago,
                Ticket.status == TicketStatus.CONFIRMED
            ).scalar()

            if last_three_hours == 0:
                await event_bus.publish(DomainEvent(
                    event_type=EventType.SALES_STALLED,
                    aggregate_id=str(event_id),
                    aggregate_type="event",
                    data={
                        "event_id": event_id,
                        "hours_stalled": 3
                    },
                    metadata={"source": "ticket_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=correlation_id
                ))

        except Exception as e:
            logger.error(f"Error checking sales velocity: {e}", exc_info=True)


async def upgrade_customer_to_vip(db: Session, customer_id: int):
    """
    Check if customer qualifies for VIP status and publish event.
    """
    try:
        # Calculate customer lifetime value
        stats = db.query(
            func.count(Ticket.id).label("ticket_count"),
            func.sum(Ticket.price_paid_cents).label("total_spent")
        ).filter(
            Ticket.event_goer_id == customer_id,
            Ticket.status == TicketStatus.CONFIRMED
        ).first()

        # VIP threshold: $500+ spent OR 10+ events
        if stats.total_spent >= 50000 or stats.ticket_count >= 10:
            customer = db.query(EventGoer).filter(EventGoer.id == customer_id).first()

            # Check if not already VIP
            if not customer.metadata or not customer.metadata.get("vip"):
                await event_bus.publish(DomainEvent(
                    event_type=EventType.CUSTOMER_VIP_ACHIEVED,
                    aggregate_id=str(customer_id),
                    aggregate_type="customer",
                    data={
                        "customer_id": customer_id,
                        "total_spent_cents": stats.total_spent,
                        "ticket_count": stats.ticket_count
                    },
                    metadata={"source": "customer_service"},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=str(uuid4())
                ))

    except Exception as e:
        logger.error(f"Error checking VIP status: {e}", exc_info=True)