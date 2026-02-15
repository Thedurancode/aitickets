from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
import stripe
import uuid
import secrets
from datetime import datetime

from app.database import get_db
from app.rate_limit import limiter
from app.models import Event, TicketTier, Ticket, EventGoer, TicketStatus, PromoCode, DiscountType
from app.schemas import (
    PurchaseRequest,
    CheckoutSessionResponse,
    TicketResponse,
    TicketFullResponse,
    TicketValidationResponse,
    TicketTierResponse,
    EventResponse,
    VenueResponse,
    EventGoerResponse,
)
from app.config import get_settings
from app.services.qrcode import generate_qr_code
from app.services.stripe_sync import get_stripe_checkout_line_item

router = APIRouter(prefix="/tickets", tags=["tickets"])

DEFAULT_ALERT_THRESHOLDS = [90, 95, 100]

import logging
_alert_logger = logging.getLogger(__name__)


def check_inventory_thresholds(tier: TicketTier, event: Event, db: Session):
    """Check if tier crossed any inventory alert thresholds and fire alerts."""
    if tier.quantity_available <= 0:
        return

    pct_sold = int((tier.quantity_sold / tier.quantity_available) * 100)

    # Parse configured thresholds (or use defaults)
    if tier.alert_thresholds:
        thresholds = sorted(int(x.strip()) for x in tier.alert_thresholds.split(",") if x.strip())
    else:
        thresholds = DEFAULT_ALERT_THRESHOLDS

    # Parse already-fired thresholds
    fired = set()
    if tier.fired_thresholds:
        fired = {int(x.strip()) for x in tier.fired_thresholds.split(",") if x.strip()}

    # On refund: un-fire thresholds we've dropped below
    newly_unfired = {t for t in fired if pct_sold < t}
    if newly_unfired:
        fired -= newly_unfired
        tier.fired_thresholds = ",".join(str(t) for t in sorted(fired)) if fired else None
        db.commit()

    # On purchase: fire thresholds we've crossed
    newly_crossed = []
    for t in thresholds:
        if pct_sold >= t and t not in fired:
            newly_crossed.append(t)
            fired.add(t)

    if not newly_crossed:
        return

    # Update fired_thresholds
    tier.fired_thresholds = ",".join(str(t) for t in sorted(fired))
    db.commit()

    event_name = event.name if event else "Unknown"
    event_id = event.id if event else tier.event_id

    for threshold in newly_crossed:
        remaining = tier.quantity_available - tier.quantity_sold
        alert_data = {
            "tier_id": tier.id,
            "tier_name": tier.name,
            "event_id": event_id,
            "event_name": event_name,
            "threshold_percent": threshold,
            "current_percent": pct_sold,
            "quantity_sold": tier.quantity_sold,
            "quantity_available": tier.quantity_available,
            "remaining": remaining,
            "is_sold_out": pct_sold >= 100,
        }

        _alert_logger.info(
            "Inventory alert: %s for '%s' hit %d%% (%d/%d sold, %d remaining)",
            tier.name, event_name, threshold, tier.quantity_sold,
            tier.quantity_available, remaining,
        )

        # Fire webhook
        try:
            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("tier.threshold_reached", alert_data, db=db)
        except Exception:
            pass

        # Broadcast to SSE dashboard
        try:
            import requests as http_requests
            http_requests.post("http://localhost:3001/internal/broadcast", json={
                "event_type": "inventory_alert",
                "data": alert_data,
            }, timeout=2)
        except Exception:
            pass

        # Notify organizer via SMS
        if event and getattr(event, "promoter_phone", None):
            try:
                from app.services.sms import send_sms
                if pct_sold >= 100:
                    msg = f'SOLD OUT: "{event_name}" — {tier.name} is completely sold out! ({tier.quantity_sold}/{tier.quantity_available})'
                else:
                    msg = f'Inventory Alert: "{event_name}" — {tier.name} is {pct_sold}% sold ({remaining} remaining)'
                send_sms(event.promoter_phone, msg)
            except Exception:
                pass

        # Notify organizer via email
        if event and getattr(event, "promoter_email", None):
            try:
                from app.services.email import _send_email
                if pct_sold >= 100:
                    subject = f"SOLD OUT: {tier.name} for {event_name}"
                    html = (
                        f"<h2>🚨 {tier.name} is Sold Out!</h2>"
                        f"<p><strong>{event_name}</strong> — {tier.name} has sold all "
                        f"{tier.quantity_available} tickets.</p>"
                    )
                else:
                    subject = f"Inventory Alert: {tier.name} at {pct_sold}% for {event_name}"
                    html = (
                        f"<h2>⚠️ {tier.name} — {pct_sold}% Sold</h2>"
                        f"<p><strong>{event_name}</strong> — {tier.quantity_sold} of "
                        f"{tier.quantity_available} sold. <strong>{remaining} remaining.</strong></p>"
                    )
                _send_email(event.promoter_email, subject, html)
            except Exception:
                pass


@router.post("/events/{event_id}/purchase", response_model=CheckoutSessionResponse)
@limiter.limit("20/minute")
def create_checkout_session(
    request: Request,
    event_id: int,
    purchase: PurchaseRequest,
    db: Session = Depends(get_db),
):
    """Create a Stripe checkout session for ticket purchase, or issue free tickets instantly."""
    settings = get_settings()

    # Verify event exists
    event = (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Verify tier exists and has availability
    tier = db.query(TicketTier).filter(TicketTier.id == purchase.ticket_tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")
    if tier.event_id != event_id:
        raise HTTPException(status_code=400, detail="Tier does not belong to this event")

    available = tier.quantity_available - tier.quantity_sold
    if available < purchase.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {available} tickets available",
        )

    # Get or create event goer
    event_goer = db.query(EventGoer).filter(EventGoer.email == purchase.email).first()
    if not event_goer:
        event_goer = EventGoer(
            email=purchase.email,
            name=purchase.name,
            phone=purchase.phone,
        )
        db.add(event_goer)
        db.commit()
        db.refresh(event_goer)

    # Promo code validation
    promo = None
    discounted_price = tier.price
    discount_amount = 0
    if purchase.promo_code:
        promo, discounted_price, discount_amount = _validate_promo(
            db, purchase.promo_code, tier, event_id
        )

    # Free ticket flow — skip Stripe for $0 tiers or 100% discount
    if discounted_price == 0:
        tickets = []
        for _ in range(purchase.quantity):
            ticket = Ticket(
                ticket_tier_id=tier.id,
                event_goer_id=event_goer.id,
                qr_code_token=secrets.token_urlsafe(16),
                status=TicketStatus.PAID,
                purchased_at=datetime.utcnow(),
                promo_code_id=promo.id if promo else None,
                discount_amount_cents=discount_amount if promo else None,
                utm_source=purchase.utm_source,
                utm_medium=purchase.utm_medium,
                utm_campaign=purchase.utm_campaign,
            )
            db.add(ticket)
            tickets.append(ticket)

        tier.quantity_sold += purchase.quantity
        # Auto sold-out check
        if tier.quantity_sold >= tier.quantity_available:
            from app.models import TierStatus
            tier.status = TierStatus.SOLD_OUT
        if promo:
            promo.uses_count += purchase.quantity
        db.commit()
        for t in tickets:
            db.refresh(t)

        # Check inventory thresholds
        try:
            check_inventory_thresholds(tier, event, db)
        except Exception:
            pass

        # Fire webhook: ticket.purchased (free tickets)
        try:
            from app.services.webhooks import fire_webhook_event
            for t in tickets:
                fire_webhook_event("ticket.purchased", {
                    "ticket_id": t.id,
                    "event_id": event_id,
                    "event_name": event.name,
                    "tier_name": tier.name,
                    "price_cents": 0,
                    "customer_email": purchase.email,
                    "customer_name": purchase.name,
                }, db=db)
        except Exception:
            pass

        msg = f"{purchase.quantity} free ticket(s) confirmed for {event.name}!"
        if promo:
            msg = f"{purchase.quantity} ticket(s) confirmed for {event.name} (code {promo.code} applied)!"
        return CheckoutSessionResponse(
            message=msg,
            tickets=[{"id": t.id, "qr_token": t.qr_code_token} for t in tickets],
        )

    # Paid ticket flow — create Stripe session first, then DB rows.
    # This avoids orphaned PENDING tickets if the app crashes mid-request.
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    # Build line item
    if promo and discount_amount > 0:
        line_item = {
            "price_data": {
                "currency": "usd",
                "unit_amount": discounted_price,
                "product_data": {
                    "name": f"{event.name} - {tier.name}",
                    "description": f"{tier.description or 'Ticket'} (Code: {promo.code})",
                },
            },
            "quantity": purchase.quantity,
        }
    else:
        line_item = get_stripe_checkout_line_item(tier, purchase.quantity)

    # Create Stripe checkout session before touching the DB
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[line_item],
            mode="payment",
            success_url=f"{settings.base_url}/purchase-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.base_url}/purchase-cancelled",
            metadata={
                "event_id": str(event_id),
                "tier_id": str(tier.id),
                "event_goer_id": str(event_goer.id),
                "quantity": str(purchase.quantity),
                "stripe_product_id": tier.stripe_product_id or "",
                "promo_code": promo.code if promo else "",
                "utm_source": purchase.utm_source or "",
                "utm_medium": purchase.utm_medium or "",
                "utm_campaign": purchase.utm_campaign or "",
            },
            customer_email=purchase.email,
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Stripe succeeded — now create DB rows (safe: if this fails, the
    # checkout session just expires unused after 24h)
    tickets = []
    for _ in range(purchase.quantity):
        ticket = Ticket(
            ticket_tier_id=tier.id,
            event_goer_id=event_goer.id,
            status=TicketStatus.PENDING,
            stripe_checkout_session_id=checkout_session.id,
            promo_code_id=promo.id if promo else None,
            discount_amount_cents=discount_amount if promo else None,
            utm_source=purchase.utm_source,
            utm_medium=purchase.utm_medium,
            utm_campaign=purchase.utm_campaign,
        )
        db.add(ticket)
        tickets.append(ticket)

    if promo:
        promo.uses_count += purchase.quantity
    db.commit()

    return CheckoutSessionResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id,
    )


@router.get("/{ticket_id}", response_model=TicketFullResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Get ticket details."""
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketFullResponse(
        id=ticket.id,
        status=ticket.status,
        qr_code_token=ticket.qr_code_token,
        purchased_at=ticket.purchased_at,
        ticket_tier=TicketTierResponse.model_validate(ticket.ticket_tier),
        event=EventResponse.model_validate(ticket.ticket_tier.event),
        venue=VenueResponse.model_validate(ticket.ticket_tier.event.venue),
        event_goer=EventGoerResponse.model_validate(ticket.event_goer),
    )


@router.get("/{ticket_id}/qr")
def get_ticket_qr_code(ticket_id: int, db: Session = Depends(get_db)):
    """Get QR code image for a ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status != TicketStatus.PAID:
        raise HTTPException(status_code=400, detail="Ticket not paid")

    if not ticket.qr_code_token:
        raise HTTPException(status_code=400, detail="QR code not generated")

    qr_bytes = generate_qr_code(ticket.qr_code_token)
    return Response(content=qr_bytes, media_type="image/png")


@router.post("/validate/{qr_token}", response_model=TicketValidationResponse)
def validate_ticket(qr_token: str, db: Session = Depends(get_db)):
    """Validate and check in a ticket at the door."""
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(Ticket.qr_code_token == qr_token)
        .first()
    )

    if not ticket:
        return TicketValidationResponse(
            valid=False,
            message="Invalid ticket - QR code not found",
            ticket=None,
        )

    if ticket.status == TicketStatus.CHECKED_IN:
        return TicketValidationResponse(
            valid=False,
            message="Ticket already checked in",
            ticket=_build_ticket_full_response(ticket),
        )

    if ticket.status == TicketStatus.CANCELLED:
        return TicketValidationResponse(
            valid=False,
            message="Ticket has been cancelled",
            ticket=_build_ticket_full_response(ticket),
        )

    if ticket.status == TicketStatus.REFUNDED:
        return TicketValidationResponse(
            valid=False,
            message="Ticket has been refunded",
            ticket=_build_ticket_full_response(ticket),
        )

    if ticket.status == TicketStatus.PENDING:
        return TicketValidationResponse(
            valid=False,
            message="Ticket payment not completed",
            ticket=_build_ticket_full_response(ticket),
        )

    # Mark as checked in
    ticket.status = TicketStatus.CHECKED_IN
    db.commit()

    # Send media share link (photo/video upload)
    try:
        from app.services.media_sharing import generate_media_share_token, send_media_share_notification
        media_token = generate_media_share_token(
            db,
            event_id=ticket.ticket_tier.event_id,
            event_goer_id=ticket.event_goer_id,
        )
        send_media_share_notification(
            db,
            event_goer=ticket.event_goer,
            event=ticket.ticket_tier.event,
            token=media_token.token,
        )
    except Exception:
        pass  # Never fail check-in due to media share

    # Fire webhook: ticket.checked_in
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("ticket.checked_in", {
            "ticket_id": ticket.id,
            "event_id": ticket.ticket_tier.event_id,
            "event_name": ticket.ticket_tier.event.name,
            "customer_email": ticket.event_goer.email,
            "customer_name": ticket.event_goer.name,
        }, db=db)
    except Exception:
        pass

    return TicketValidationResponse(
        valid=True,
        message="Ticket validated successfully - Welcome!",
        ticket=_build_ticket_full_response(ticket),
    )


def _validate_promo(db: Session, code_str: str, tier: TicketTier, event_id: int):
    """Validate promo code and return (promo, discounted_price, discount_amount)."""
    promo = db.query(PromoCode).filter(PromoCode.code == code_str.upper()).first()
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid promo code")
    if not promo.is_active:
        raise HTTPException(status_code=400, detail="Promo code is no longer active")
    if promo.event_id and promo.event_id != event_id:
        raise HTTPException(status_code=400, detail="Promo code is not valid for this event")

    now = datetime.utcnow()
    if promo.valid_from and now < promo.valid_from.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Promo code is not yet valid")
    if promo.valid_until and now > promo.valid_until.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Promo code has expired")
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promo code has reached its usage limit")

    original = tier.price
    if promo.discount_type == DiscountType.PERCENT:
        discount = int(original * promo.discount_value / 100)
    else:
        discount = min(promo.discount_value, original)
    discounted = max(original - discount, 0)

    return promo, discounted, discount


@router.get("/by-email", response_model=list[TicketFullResponse])
@limiter.limit("10/minute")
def get_tickets_by_email(
    request: Request,
    email: str = Query(..., description="Email address to look up tickets for"),
    db: Session = Depends(get_db),
):
    """Get all tickets for a given email address."""
    event_goer = db.query(EventGoer).filter(
        EventGoer.email == email.lower().strip()
    ).first()
    if not event_goer:
        return []

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(
            Ticket.event_goer_id == event_goer.id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
        )
        .order_by(Ticket.purchased_at.desc())
        .all()
    )

    return [_build_ticket_full_response(t) for t in tickets]


def _build_ticket_full_response(ticket: Ticket) -> TicketFullResponse:
    """Helper to build TicketFullResponse from a ticket with loaded relations."""
    return TicketFullResponse(
        id=ticket.id,
        status=ticket.status,
        qr_code_token=ticket.qr_code_token,
        purchased_at=ticket.purchased_at,
        ticket_tier=TicketTierResponse.model_validate(ticket.ticket_tier),
        event=EventResponse.model_validate(ticket.ticket_tier.event),
        venue=VenueResponse.model_validate(ticket.ticket_tier.event.venue),
        event_goer=EventGoerResponse.model_validate(ticket.event_goer),
    )


def _load_ticket_with_relations(ticket_id: int, db: Session) -> Ticket:
    """Load a ticket with all relations needed for PDF/wallet generation."""
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
            joinedload(Ticket.event_goer),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    return ticket


@router.get("/{ticket_id}/pdf")
def download_ticket_pdf(ticket_id: int, db: Session = Depends(get_db)):
    """Download a ticket as a branded PDF."""
    ticket = _load_ticket_with_relations(ticket_id, db)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status not in (TicketStatus.PAID, TicketStatus.CHECKED_IN):
        raise HTTPException(status_code=400, detail=f"Ticket is {ticket.status.value}, not downloadable")
    if not ticket.qr_code_token:
        raise HTTPException(status_code=400, detail="Ticket has no QR code")

    from app.services.pdf_ticket import generate_ticket_pdf

    event = ticket.ticket_tier.event
    venue = event.venue

    pdf_bytes = generate_ticket_pdf(
        event_name=event.name,
        event_date=event.event_date,
        event_time=event.event_time,
        venue_name=venue.name,
        venue_address=venue.address or "",
        attendee_name=ticket.event_goer.name,
        tier_name=ticket.ticket_tier.name,
        ticket_id=ticket.id,
        qr_token=ticket.qr_code_token,
        doors_open_time=getattr(event, "doors_open_time", None),
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ticket-{ticket.id}.pdf"},
    )


@router.get("/{ticket_id}/wallet")
def download_wallet_pass(ticket_id: int, db: Session = Depends(get_db)):
    """Download a ticket as an Apple Wallet .pkpass file."""
    ticket = _load_ticket_with_relations(ticket_id, db)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status not in (TicketStatus.PAID, TicketStatus.CHECKED_IN):
        raise HTTPException(status_code=400, detail=f"Ticket is {ticket.status.value}, not downloadable")
    if not ticket.qr_code_token:
        raise HTTPException(status_code=400, detail="Ticket has no QR code")

    from app.services.wallet_pass import generate_wallet_pass

    event = ticket.ticket_tier.event
    venue = event.venue

    pass_bytes = generate_wallet_pass(
        event_name=event.name,
        event_date=event.event_date,
        event_time=event.event_time,
        venue_name=venue.name,
        venue_address=venue.address or "",
        attendee_name=ticket.event_goer.name,
        tier_name=ticket.ticket_tier.name,
        ticket_id=ticket.id,
        qr_token=ticket.qr_code_token,
        doors_open_time=getattr(event, "doors_open_time", None),
    )

    return Response(
        content=pass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f"attachment; filename=ticket-{ticket.id}.pkpass"},
    )
