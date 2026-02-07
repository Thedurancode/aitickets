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
from app.services.stripe_sync import (
    create_stripe_product_for_tier,
    update_stripe_price_for_tier,
    archive_stripe_product,
    sync_existing_tiers_to_stripe,
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
    sync_stripe: bool = True,
):
    """
    Add a ticket tier to an event.

    Automatically creates a Stripe product and price for the tier.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_tier = TicketTier(event_id=event_id, **tier.model_dump())
    db.add(db_tier)
    db.commit()
    db.refresh(db_tier)

    # Sync to Stripe (skip for free tiers)
    if sync_stripe and db_tier.price > 0:
        stripe_result = create_stripe_product_for_tier(db, db_tier, event)
        if stripe_result.get("error"):
            # Log but don't fail - tier is created, just not synced
            print(f"Warning: Failed to sync tier to Stripe: {stripe_result['error']}")

    db.refresh(db_tier)
    return db_tier


@router.put("/tiers/{tier_id}", response_model=TicketTierResponse)
def update_ticket_tier(
    tier_id: int,
    tier: TicketTierUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a ticket tier.

    If price changes, creates a new Stripe price (prices are immutable in Stripe).
    """
    db_tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    if not db_tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")

    update_data = tier.model_dump(exclude_unset=True)

    # Check if price is changing
    price_changed = "price" in update_data and update_data["price"] != db_tier.price
    new_price = update_data.get("price")

    # Apply non-price updates
    for field, value in update_data.items():
        if field != "price" or not price_changed:
            setattr(db_tier, field, value)

    db.commit()

    # Handle price change in Stripe (skip for $0)
    if price_changed and db_tier.stripe_product_id and new_price > 0:
        stripe_result = update_stripe_price_for_tier(db, db_tier, new_price)
        if stripe_result.get("error"):
            print(f"Warning: Failed to update Stripe price: {stripe_result['error']}")
    elif price_changed:
        # Just update the local price if not synced to Stripe
        db_tier.price = new_price
        db.commit()

    db.refresh(db_tier)
    return db_tier


@router.delete("/tiers/{tier_id}", status_code=204)
def delete_ticket_tier(tier_id: int, db: Session = Depends(get_db)):
    """
    Delete a ticket tier.

    Archives the Stripe product if it was synced.
    """
    db_tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    if not db_tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")

    # Check if any tickets have been sold
    if db_tier.quantity_sold > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete tier with sold tickets",
        )

    # Archive in Stripe first
    if db_tier.stripe_product_id:
        archive_result = archive_stripe_product(db_tier)
        if archive_result.get("error"):
            print(f"Warning: Failed to archive Stripe product: {archive_result['error']}")

    db.delete(db_tier)
    db.commit()
    return None


@router.post("/events/{event_id}/tiers/sync-stripe")
def sync_event_tiers_to_stripe(event_id: int, db: Session = Depends(get_db)):
    """
    Sync all ticket tiers for an event to Stripe.

    Useful for migrating existing tiers or re-syncing after issues.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = sync_existing_tiers_to_stripe(db, event_id)
    return result


@router.post("/tiers/sync-all-stripe")
def sync_all_tiers_to_stripe(db: Session = Depends(get_db)):
    """
    Sync ALL ticket tiers to Stripe.

    Use with caution - this will create products for all unsynced tiers.
    """
    result = sync_existing_tiers_to_stripe(db)
    return result
