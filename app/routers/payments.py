from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session, joinedload
import stripe
import uuid
from datetime import datetime

from app.database import get_db
from app.models import Ticket, TicketTier, Event, TicketStatus
from app.config import get_settings
from app.services.email import send_ticket_email

router = APIRouter(prefix="/webhooks", tags=["payments"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events."""
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()

    # Verify webhook signature if secret is configured
    if settings.stripe_webhook_secret and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload,
                stripe_signature,
                settings.stripe_webhook_secret,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # For development without webhook secret
        import json
        event = json.loads(payload)

    event_type = event.get("type") if isinstance(event, dict) else event.type
    event_data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        await handle_checkout_completed(event_data, db)
    elif event_type == "charge.refunded":
        await handle_charge_refunded(event_data, db)

    return {"status": "success"}


async def handle_checkout_completed(session_data: dict, db: Session):
    """Handle successful checkout - mark tickets as paid and send emails."""
    session_id = session_data.get("id")
    payment_intent_id = session_data.get("payment_intent")
    metadata = session_data.get("metadata", {})

    ticket_ids_str = metadata.get("ticket_ids", "")
    if not ticket_ids_str:
        return

    ticket_ids = [int(tid) for tid in ticket_ids_str.split(",")]

    # Get tickets with related data
    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(Ticket.id.in_(ticket_ids))
        .all()
    )

    for ticket in tickets:
        # Update ticket status
        ticket.status = TicketStatus.PAID
        ticket.stripe_payment_intent_id = payment_intent_id
        ticket.purchased_at = datetime.utcnow()
        ticket.qr_code_token = uuid.uuid4().hex

        # Update tier sold count
        ticket.ticket_tier.quantity_sold += 1
        # Auto sold-out check
        if ticket.ticket_tier.quantity_sold >= ticket.ticket_tier.quantity_available:
            from app.models import TierStatus
            ticket.ticket_tier.status = TierStatus.SOLD_OUT

    db.commit()

    # Send confirmation emails
    for ticket in tickets:
        event = ticket.ticket_tier.event
        venue = event.venue
        tier = ticket.ticket_tier
        event_goer = ticket.event_goer

        send_ticket_email(
            to_email=event_goer.email,
            recipient_name=event_goer.name,
            event_name=event.name,
            event_date=event.event_date,
            event_time=event.event_time,
            venue_name=venue.name,
            venue_address=venue.address,
            tier_name=tier.name,
            ticket_id=ticket.id,
            qr_code_token=ticket.qr_code_token,
        )


async def handle_charge_refunded(charge_data: dict, db: Session):
    """Handle refund - mark tickets as refunded."""
    payment_intent_id = charge_data.get("payment_intent")
    if not payment_intent_id:
        return

    tickets = (
        db.query(Ticket)
        .filter(Ticket.stripe_payment_intent_id == payment_intent_id)
        .all()
    )

    for ticket in tickets:
        if ticket.status == TicketStatus.PAID:
            ticket.status = TicketStatus.REFUNDED
            # Restore tier availability
            ticket.ticket_tier.quantity_sold -= 1

    db.commit()
