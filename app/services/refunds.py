"""
Refund Management Service

Handles full and partial refunds via Stripe with comprehensive tracking.
"""

import stripe
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Ticket, TicketStatus, EventGoer, TicketTier

# Initialize Stripe
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


def process_refund(
    db: Session,
    ticket_id: int,
    reason: str,
    amount_cents: Optional[int] = None,
    notify_customer: bool = True,
) -> dict:
    """
    Process a full or partial refund for a ticket.

    Args:
        db: Database session
        ticket_id: ID of ticket to refund
        reason: Refund reason (customer_request, event_cancelled, duplicate, fraud, other)
        amount_cents: Amount to refund in cents (None = full refund)
        notify_customer: Whether to send email notification

    Returns:
        Dict with refund details or error
    """
    # Get the ticket
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        return {"error": "Ticket not found"}

    if ticket.status == TicketStatus.REFUNDED:
        return {"error": "Ticket already refunded"}

    if ticket.status not in [TicketStatus.PAID, TicketStatus.CHECKED_IN]:
        return {"error": f"Cannot refund ticket with status: {ticket.status}"}

    if not ticket.stripe_payment_intent_id:
        return {"error": "No Stripe payment intent found for this ticket"}

    # Get ticket price
    tier = db.query(TicketTier).filter(TicketTier.id == ticket.ticket_tier_id).first()
    if not tier:
        return {"error": "Ticket tier not found"}

    # Calculate refund amount
    ticket_price = tier.price
    if ticket.discount_amount_cents:
        ticket_price -= ticket.discount_amount_cents

    # Check for already refunded amount (prevent over-refunding)
    already_refunded = ticket.refund_amount_cents or 0
    remaining_refundable = ticket_price - already_refunded

    if remaining_refundable <= 0:
        return {"error": "Ticket has already been fully refunded"}

    if amount_cents is None:
        refund_amount = remaining_refundable  # Full refund of remaining amount
    else:
        if amount_cents > remaining_refundable:
            return {"error": f"Refund amount (${amount_cents/100:.2f}) exceeds remaining refundable amount (${remaining_refundable/100:.2f})"}
        refund_amount = amount_cents

    # Process refund with Stripe (with idempotency key to prevent duplicates)
    try:
        idempotency_key = f"refund_{ticket_id}_{int(datetime.now(timezone.utc).timestamp())}"
        refund = stripe.Refund.create(
            payment_intent=ticket.stripe_payment_intent_id,
            amount=refund_amount,
            reason=_map_refund_reason(reason),
            metadata={
                "ticket_id": str(ticket.id),
                "event_goer_id": str(ticket.event_goer_id),
                "refund_reason": reason,
            },
            idempotency_key=idempotency_key,
        )

        # Update ticket (accumulate refund amount for partial refunds)
        previous_refunds = ticket.refund_amount_cents or 0
        total_refunded = previous_refunds + refund_amount

        ticket.refund_amount_cents = total_refunded
        ticket.refund_reason = reason
        ticket.refunded_at = datetime.now(timezone.utc)
        ticket.stripe_refund_id = refund.id

        # Only mark as REFUNDED and restore inventory if fully refunded
        if total_refunded >= ticket_price:
            ticket.status = TicketStatus.REFUNDED
            # Restore tier inventory only when fully refunded
            tier.quantity_sold = max(0, tier.quantity_sold - 1)

        db.commit()
        db.refresh(ticket)

        # Get customer info
        customer = db.query(EventGoer).filter(EventGoer.id == ticket.event_goer_id).first()

        return {
            "success": True,
            "refund_id": refund.id,
            "ticket_id": ticket.id,
            "amount_refunded_cents": refund_amount,
            "amount_refunded": f"${refund_amount / 100:.2f}",
            "refund_type": "full" if refund_amount == ticket_price else "partial",
            "reason": reason,
            "refunded_at": ticket.refunded_at.isoformat(),
            "customer_email": customer.email if customer else None,
            "stripe_refund": {
                "id": refund.id,
                "status": refund.status,
                "receipt_number": refund.receipt_number,
            },
        }

    except stripe.error.StripeError as e:
        return {"error": f"Stripe refund failed: {str(e)}"}


def _map_refund_reason(internal_reason: str) -> str:
    """Map internal refund reasons to Stripe's allowed values."""
    mapping = {
        "duplicate": "duplicate",
        "fraud": "fraudulent",
        "customer_request": "requested_by_customer",
        "event_cancelled": "requested_by_customer",
        "other": "requested_by_customer",
    }
    return mapping.get(internal_reason, "requested_by_customer")


def bulk_refund(
    db: Session,
    ticket_ids: list[int],
    reason: str,
    amount_cents: Optional[int] = None,
) -> dict:
    """
    Process refunds for multiple tickets.

    Args:
        db: Database session
        ticket_ids: List of ticket IDs to refund
        reason: Refund reason
        amount_cents: Amount per ticket (None = full refund each)

    Returns:
        Dict with results for each ticket
    """
    results = {
        "total": len(ticket_ids),
        "successful": 0,
        "failed": 0,
        "refunds": [],
        "errors": [],
    }

    for ticket_id in ticket_ids:
        result = process_refund(
            db=db,
            ticket_id=ticket_id,
            reason=reason,
            amount_cents=amount_cents,
            notify_customer=True,
        )

        if "error" in result:
            results["failed"] += 1
            results["errors"].append({
                "ticket_id": ticket_id,
                "error": result["error"],
            })
        else:
            results["successful"] += 1
            results["refunds"].append(result)

    return results


def get_refund_history(
    db: Session,
    event_id: Optional[int] = None,
    event_goer_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Get refund history with optional filters.

    Args:
        db: Database session
        event_id: Filter by event
        event_goer_id: Filter by customer
        limit: Max results
        offset: Pagination offset

    Returns:
        Dict with refund records
    """
    query = db.query(Ticket).filter(Ticket.status == TicketStatus.REFUNDED)

    if event_id:
        query = query.join(TicketTier).filter(TicketTier.event_id == event_id)

    if event_goer_id:
        query = query.filter(Ticket.event_goer_id == event_goer_id)

    total_count = query.count()
    refunds = query.order_by(Ticket.refunded_at.desc()).offset(offset).limit(limit).all()

    refund_records = []
    for ticket in refunds:
        tier = db.query(TicketTier).filter(TicketTier.id == ticket.ticket_tier_id).first()
        customer = db.query(EventGoer).filter(EventGoer.id == ticket.event_goer_id).first()

        refund_records.append({
            "ticket_id": ticket.id,
            "refund_id": ticket.stripe_refund_id,
            "customer_name": customer.name if customer else None,
            "customer_email": customer.email if customer else None,
            "tier_name": tier.name if tier else None,
            "refund_amount_cents": ticket.refund_amount_cents,
            "refund_reason": ticket.refund_reason,
            "refunded_at": ticket.refunded_at.isoformat() if ticket.refunded_at else None,
        })

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "refunds": refund_records,
    }


def get_refund_stats(db: Session, event_id: Optional[int] = None) -> dict:
    """
    Get refund statistics.

    Args:
        db: Database session
        event_id: Filter by event (optional)

    Returns:
        Dict with refund stats
    """
    query = db.query(Ticket).filter(Ticket.status == TicketStatus.REFUNDED)

    if event_id:
        query = query.join(TicketTier).filter(TicketTier.event_id == event_id)

    refunded_tickets = query.all()

    total_refunds = len(refunded_tickets)
    total_refunded_cents = sum(t.refund_amount_cents or 0 for t in refunded_tickets)

    # Count by reason
    reasons = {}
    for ticket in refunded_tickets:
        reason = ticket.refund_reason or "unknown"
        reasons[reason] = reasons.get(reason, 0) + 1

    return {
        "total_refunds": total_refunds,
        "total_refunded_cents": total_refunded_cents,
        "total_refunded": f"${total_refunded_cents / 100:.2f}",
        "refunds_by_reason": reasons,
        "average_refund_cents": total_refunded_cents // total_refunds if total_refunds > 0 else 0,
    }


def check_refund_policy(
    db: Session,
    ticket_id: int,
) -> dict:
    """
    Check if a ticket is eligible for refund based on policy.

    Args:
        db: Database session
        ticket_id: Ticket ID

    Returns:
        Dict with eligibility info
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        return {"eligible": False, "reason": "Ticket not found"}

    if ticket.status == TicketStatus.REFUNDED:
        return {"eligible": False, "reason": "Already refunded"}

    if ticket.status not in [TicketStatus.PAID, TicketStatus.CHECKED_IN]:
        return {"eligible": False, "reason": f"Cannot refund ticket with status: {ticket.status}"}

    # Get event date
    tier = db.query(TicketTier).filter(TicketTier.id == ticket.ticket_tier_id).first()
    if not tier:
        return {"eligible": False, "reason": "Ticket tier not found"}

    # Add custom refund policies here (e.g., no refunds within 24 hours of event)
    # For now, allow all eligible tickets to be refunded

    return {
        "eligible": True,
        "reason": "Ticket is eligible for refund",
        "ticket_id": ticket.id,
        "status": ticket.status.value,
    }
