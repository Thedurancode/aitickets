from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
import stripe
import uuid
from datetime import datetime

from app.database import get_db
from app.models import Event, TicketTier, Ticket, EventGoer, TicketStatus
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
def create_checkout_session(
    event_id: int,
    purchase: PurchaseRequest,
    db: Session = Depends(get_db),
):
    """Create a Stripe checkout session for ticket purchase."""
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

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

    # Create pending tickets
    tickets = []
    for _ in range(purchase.quantity):
        ticket = Ticket(
            ticket_tier_id=tier.id,
            event_goer_id=event_goer.id,
            status=TicketStatus.PENDING,
        )
        db.add(ticket)
        tickets.append(ticket)

    db.commit()

    # Create Stripe checkout session
    ticket_ids = [t.id for t in tickets]
    for t in tickets:
        db.refresh(t)

    try:
        # Use synced Stripe price if available, otherwise inline pricing
        line_item = get_stripe_checkout_line_item(tier, purchase.quantity)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[line_item],
            mode="payment",
            success_url=f"{settings.base_url}/purchase-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.base_url}/purchase-cancelled",
            metadata={
                "ticket_ids": ",".join(str(tid) for tid in ticket_ids),
                "event_id": str(event_id),
                "tier_id": str(tier.id),
                "stripe_product_id": tier.stripe_product_id or "",
            },
            customer_email=purchase.email,
        )

        # Store checkout session ID on tickets
        for ticket in tickets:
            ticket.stripe_checkout_session_id = checkout_session.id

        db.commit()

        return CheckoutSessionResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except stripe.error.StripeError as e:
        # Clean up pending tickets on error
        for ticket in tickets:
            db.delete(ticket)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))


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

    return TicketValidationResponse(
        valid=True,
        message="Ticket validated successfully - Welcome!",
        ticket=_build_ticket_full_response(ticket),
    )


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
