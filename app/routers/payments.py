from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session, joinedload
import stripe
import uuid
from datetime import datetime, timezone

from app.database import get_db
from app.models import Ticket, TicketTier, Event, TicketStatus, WaitlistEntry, WaitlistStatus
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
    env = (settings.environment or "").lower()
    is_production = env in {"production", "prod"}

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    # Production hardening: webhook secret must be configured and signed.
    if is_production and not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret required in production")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()

    # Verify webhook signature whenever a webhook secret is configured.
    if settings.stripe_webhook_secret:
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
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
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

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

    # Find tickets by checkout session ID (primary) or legacy ticket_ids metadata
    # Use row-level locking to prevent duplicate webhook processing
    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(Ticket.stripe_checkout_session_id == session_id)
        .with_for_update()
        .all()
    )

    # Fallback for tickets created before the Stripe-first flow
    if not tickets:
        ticket_ids_str = metadata.get("ticket_ids", "")
        if not ticket_ids_str:
            return

        # Validate and parse ticket IDs safely
        try:
            ticket_ids = [int(tid.strip()) for tid in ticket_ids_str.split(",") if tid.strip().isdigit()]
            if not ticket_ids:
                import logging
                logging.getLogger(__name__).warning(f"Invalid ticket_ids in metadata: {ticket_ids_str}")
                return
        except (ValueError, AttributeError) as e:
            import logging
            logging.getLogger(__name__).error(f"Error parsing ticket_ids from metadata: {e}")
            return

        tickets = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
                joinedload(Ticket.event_goer),
            )
            .filter(Ticket.id.in_(ticket_ids))
            .with_for_update()
            .all()
        )

    if not tickets:
        return

    processed_tickets = []
    for ticket in tickets:
        # Idempotency: only transition pending tickets once.
        if ticket.status != TicketStatus.PENDING:
            if payment_intent_id and not ticket.stripe_payment_intent_id:
                ticket.stripe_payment_intent_id = payment_intent_id
            continue

        # Update ticket status
        ticket.status = TicketStatus.PAID
        ticket.stripe_payment_intent_id = payment_intent_id
        ticket.purchased_at = datetime.now(timezone.utc)
        ticket.qr_code_token = uuid.uuid4().hex

        # Copy UTM from metadata if not already on ticket
        if not ticket.utm_source and metadata.get("utm_source"):
            ticket.utm_source = metadata["utm_source"]
        if not ticket.utm_medium and metadata.get("utm_medium"):
            ticket.utm_medium = metadata["utm_medium"]
        if not ticket.utm_campaign and metadata.get("utm_campaign"):
            ticket.utm_campaign = metadata["utm_campaign"]

        # Update tier sold count (row is already locked via ticket relation)
        # Use atomic update to prevent race conditions
        db.query(TicketTier).filter(TicketTier.id == ticket.ticket_tier_id).update(
            {"quantity_sold": TicketTier.quantity_sold + 1},
            synchronize_session=False
        )
        db.refresh(ticket.ticket_tier)

        # Auto sold-out check
        if ticket.ticket_tier.quantity_sold >= ticket.ticket_tier.quantity_available:
            from app.models import TierStatus
            ticket.ticket_tier.status = TierStatus.SOLD_OUT
        processed_tickets.append(ticket)

    if not processed_tickets:
        db.commit()
        return

    db.commit()

    # Check inventory thresholds
    if processed_tickets:
        try:
            from app.routers.tickets import check_inventory_thresholds
            checked_tiers = set()
            for ticket in processed_tickets:
                tid = ticket.ticket_tier.id
                if tid not in checked_tiers:
                    check_inventory_thresholds(ticket.ticket_tier, ticket.ticket_tier.event, db)
                    checked_tiers.add(tid)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to check inventory thresholds after purchase: {e}", exc_info=True)

    # Broadcast to real-time dashboard (best-effort, non-blocking)
    if processed_tickets:
        try:
            import requests as http_requests
            first = processed_tickets[0]
            http_requests.post("http://localhost:3001/internal/broadcast", json={
                "event_type": "ticket_purchased",
                "data": {
                    "event_name": first.ticket_tier.event.name,
                    "event_id": first.ticket_tier.event_id,
                    "customer_name": first.event_goer.name,
                    "tier_name": first.ticket_tier.name,
                    "price_cents": first.ticket_tier.price,
                    "quantity": len(processed_tickets),
                    "total_revenue_cents": sum(t.ticket_tier.price for t in processed_tickets),
                },
            }, timeout=2)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to broadcast ticket purchase to dashboard: {e}")

    # Track conversions for ML and attribution analysis
    try:
        from app.services.learning_engine import track_conversion
        for ticket in processed_tickets:
            # Extract session metadata from Stripe metadata if available
            device_type = metadata.get("device_type")
            browser = metadata.get("browser")
            referrer = metadata.get("referrer")
            landing_page = metadata.get("landing_page")
            session_id = metadata.get("session_id")
            ab_test_variant = metadata.get("ab_test_variant")

            track_conversion(
                db=db,
                ticket=ticket,
                referrer_url=referrer,
                landing_page=landing_page,
                device_type=device_type,
                browser=browser,
                session_id=session_id,
                ab_test_variant=ab_test_variant,
            )
    except Exception as e:
        # Don't fail checkout if conversion tracking fails
        import logging
        logging.getLogger(__name__).warning(f"Conversion tracking failed: {e}")

    # Fire webhook: ticket.purchased (paid tickets)
    try:
        from app.services.webhooks import fire_webhook_event
        for ticket in processed_tickets:
            fire_webhook_event("ticket.purchased", {
                "ticket_id": ticket.id,
                "event_id": ticket.ticket_tier.event_id,
                "event_name": ticket.ticket_tier.event.name,
                "tier_name": ticket.ticket_tier.name,
                "price_cents": ticket.ticket_tier.price,
                "customer_email": ticket.event_goer.email,
                "customer_name": ticket.event_goer.name,
            })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fire ticket.purchased webhook: {e}", exc_info=True)

    # Send confirmation emails
    for ticket in processed_tickets:
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
            event_id=event.id,
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

    refunded_count = 0
    event_id = None
    for ticket in tickets:
        if ticket.status == TicketStatus.PAID:
            ticket.status = TicketStatus.REFUNDED
            # Restore tier availability (atomic decrement)
            db.query(TicketTier).filter(TicketTier.id == ticket.ticket_tier_id).update(
                {"quantity_sold": TicketTier.quantity_sold - 1},
                synchronize_session=False
            )
            refunded_count += 1
            if not event_id and ticket.ticket_tier:
                event_id = ticket.ticket_tier.event_id

    db.commit()

    # Check inventory thresholds (may re-arm after refund)
    if refunded_count > 0:
        try:
            from app.routers.tickets import check_inventory_thresholds
            checked_tiers = set()
            for ticket in tickets:
                if ticket.status == TicketStatus.REFUNDED and ticket.ticket_tier.id not in checked_tiers:
                    check_inventory_thresholds(ticket.ticket_tier, ticket.ticket_tier.event, db)
                    checked_tiers.add(ticket.ticket_tier.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to check inventory thresholds after refund: {e}", exc_info=True)

    # Broadcast refund to real-time dashboard
    if refunded_count > 0:
        try:
            import requests as http_requests
            http_requests.post("http://localhost:3001/internal/broadcast", json={
                "event_type": "ticket_refunded",
                "data": {
                    "event_id": event_id,
                    "refunded_count": refunded_count,
                },
            }, timeout=2)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to broadcast refund to dashboard: {e}")

    # Fire webhook: ticket.refunded
    if refunded_count > 0:
        try:
            from app.services.webhooks import fire_webhook_event
            for ticket in tickets:
                if ticket.status == TicketStatus.REFUNDED:
                    fire_webhook_event("ticket.refunded", {
                        "ticket_id": ticket.id,
                        "event_id": event_id,
                        "payment_intent_id": payment_intent_id,
                    })
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to fire ticket.refunded webhook: {e}", exc_info=True)

    # Auto-notify waitlisted people when tickets freed up
    if refunded_count > 0 and event_id:
        _auto_notify_waitlist(event_id, refunded_count, db)


def _auto_notify_waitlist(event_id: int, count: int, db: Session):
    """Notify next N waitlisted people that tickets are available."""
    from app.services.sms import send_sms

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return

    settings = get_settings()
    entries = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.status == WaitlistStatus.WAITING,
        )
        .order_by(WaitlistEntry.position.asc())
        .limit(count)
        .all()
    )

    ticket_url = f"{settings.base_url}/events/{event_id}"
    for entry in entries:
        if entry.phone:
            msg = f"Great news! Tickets are now available for \"{event.name}\"! Grab yours: {ticket_url}"
            send_sms(entry.phone, msg)
        entry.status = WaitlistStatus.NOTIFIED
        entry.notified_at = datetime.now(timezone.utc)

    db.commit()
