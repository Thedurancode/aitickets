from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, TicketTier
from app.schemas import (
    TicketTierCreate,
    TicketTierUpdate,
    TicketTierResponse,
    TicketTierWithAvailability,
)

router = APIRouter(tags=["ticket_tiers"])


@router.get("/events/{event_id}/tiers", response_model=list[TicketTierWithAvailability])
def list_ticket_tiers(event_id: int, db: Session = Depends(get_db)):
    """List ticket tiers for an event with availability."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()

    result = []
    for tier in tiers:
        tier_data = TicketTierWithAvailability(
            id=tier.id,
            event_id=tier.event_id,
            name=tier.name,
            description=tier.description,
            price=tier.price,
            quantity_available=tier.quantity_available,
            quantity_sold=tier.quantity_sold,
            tickets_remaining=tier.quantity_available - tier.quantity_sold,
        )
        result.append(tier_data)

    return result


@router.post("/events/{event_id}/tiers", response_model=TicketTierResponse, status_code=201)
def create_ticket_tier(
    event_id: int,
    tier: TicketTierCreate,
    db: Session = Depends(get_db),
):
    """Add a ticket tier to an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_tier = TicketTier(event_id=event_id, **tier.model_dump())
    db.add(db_tier)
    db.commit()
    db.refresh(db_tier)
    return db_tier


@router.put("/tiers/{tier_id}", response_model=TicketTierResponse)
def update_ticket_tier(
    tier_id: int,
    tier: TicketTierUpdate,
    db: Session = Depends(get_db),
):
    """Update a ticket tier."""
    db_tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    if not db_tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")

    update_data = tier.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tier, field, value)

    db.commit()
    db.refresh(db_tier)
    return db_tier


@router.delete("/tiers/{tier_id}", status_code=204)
def delete_ticket_tier(tier_id: int, db: Session = Depends(get_db)):
    """Delete a ticket tier."""
    db_tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    if not db_tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")

    # Check if any tickets have been sold
    if db_tier.quantity_sold > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete tier with sold tickets",
        )

    db.delete(db_tier)
    db.commit()
    return None
