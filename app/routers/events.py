from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
import uuid
from pathlib import Path

from app.database import get_db
from app.models import Event, Venue, TicketTier, EventCategory
from app.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventDetailResponse,
    EventWithVenueResponse,
    TicketTierWithAvailability,
)
from app.config import get_settings

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventWithVenueResponse])
def list_events(
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List events with venue information. Optionally filter by category name."""
    query = db.query(Event).options(joinedload(Event.venue), joinedload(Event.categories))
    if category:
        query = query.join(Event.categories).filter(EventCategory.name.ilike(f"%{category}%"))
    events = query.order_by(Event.event_date.desc()).offset(offset).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get event with venue, tiers, and availability."""
    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers), joinedload(Event.categories))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Calculate availability for each tier
    tiers_with_availability = []
    for tier in event.ticket_tiers:
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
        tiers_with_availability.append(tier_data)

    return EventDetailResponse(
        id=event.id,
        venue_id=event.venue_id,
        name=event.name,
        description=event.description,
        image_url=event.image_url,
        promo_video_url=event.promo_video_url,
        event_date=event.event_date,
        event_time=event.event_time,
        status=event.status,
        is_visible=event.is_visible,
        doors_open_time=event.doors_open_time,
        created_at=event.created_at,
        venue=event.venue,
        ticket_tiers=tiers_with_availability,
        categories=event.categories,
    )


@router.post("", response_model=EventResponse, status_code=201)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new event."""
    # Verify venue exists
    venue = db.query(Venue).filter(Venue.id == event.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    event_data = event.model_dump(exclude={"category_ids"})
    db_event = Event(**event_data)

    # Attach categories
    if event.category_ids:
        categories = db.query(EventCategory).filter(EventCategory.id.in_(event.category_ids)).all()
        db_event.categories = categories

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Fire webhook: event.created
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.created", {
            "event_id": db_event.id,
            "name": db_event.name,
            "venue_id": db_event.venue_id,
            "event_date": db_event.event_date,
            "event_time": db_event.event_time,
        }, db=db)
    except Exception:
        pass

    return db_event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(event_id: int, event: EventUpdate, db: Session = Depends(get_db)):
    """Update an event."""
    db_event = db.query(Event).options(joinedload(Event.categories)).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = event.model_dump(exclude_unset=True)

    # Handle category_ids separately
    category_ids = update_data.pop("category_ids", None)
    if category_ids is not None:
        categories = db.query(EventCategory).filter(EventCategory.id.in_(category_ids)).all()
        db_event.categories = categories

    for field, value in update_data.items():
        setattr(db_event, field, value)

    db.commit()
    db.refresh(db_event)

    # Fire webhook: event.updated
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.updated", {
            "event_id": db_event.id,
            "name": db_event.name,
            "venue_id": db_event.venue_id,
            "event_date": db_event.event_date,
            "event_time": db_event.event_time,
            "updated_fields": list(update_data.keys()),
        }, db=db)
    except Exception:
        pass

    return db_event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete an event and all related data."""
    from sqlalchemy import text

    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_data = {
        "event_id": db_event.id,
        "name": db_event.name,
        "venue_id": db_event.venue_id,
    }

    # Delete tickets that belong to this event's tiers
    try:
        db.execute(text(
            "DELETE FROM tickets WHERE ticket_tier_id IN "
            "(SELECT id FROM ticket_tiers WHERE event_id = :eid)"
        ), {"eid": event_id})
    except Exception:
        pass

    # Clean up all FK references that don't cascade automatically
    for table in [
        "ticket_tiers", "survey_responses", "notifications", "event_updates",
        "page_views", "auto_triggers", "admin_magic_links",
        "knowledge_documents", "waitlist_entries", "event_photos",
    ]:
        try:
            db.execute(text(f"DELETE FROM {table} WHERE event_id = :eid"), {"eid": event_id})
        except Exception:
            pass
    # Nullify optional FK references
    for table in ["marketing_campaigns", "promo_codes", "conversation_sessions"]:
        col = "target_event_id" if table == "marketing_campaigns" else "current_event_id" if table == "conversation_sessions" else "event_id"
        try:
            db.execute(text(f"UPDATE {table} SET {col} = NULL WHERE {col} = :eid"), {"eid": event_id})
        except Exception:
            pass
    # Remove event-category associations
    try:
        db.execute(text("DELETE FROM event_category_association WHERE event_id = :eid"), {"eid": event_id})
    except Exception:
        pass

    # Delete the event itself via raw SQL to avoid ORM cascade issues
    db.execute(text("DELETE FROM events WHERE id = :eid"), {"eid": event_id})
    db.commit()
    # Expunge the ORM object so SQLAlchemy doesn't try to flush it
    db.expunge(db_event)

    # Fire webhook: event.deleted
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.deleted", event_data, db=db)
    except Exception:
        pass

    return None


@router.post("/{event_id}/image", response_model=EventResponse)
async def upload_event_image(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an image for an event."""
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"event_{event_id}_{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Update event with image URL
    db_event.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(db_event)

    return db_event
