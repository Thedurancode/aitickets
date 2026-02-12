from fastapi import APIRouter, Depends, HTTPException, Request
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
