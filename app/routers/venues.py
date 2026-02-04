from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid
from pathlib import Path

from app.database import get_db
from app.models import Venue, Event
from app.schemas import (
    VenueCreate,
    VenueUpdate,
    VenueResponse,
    VenueWithEventsResponse,
    EventResponse,
)
from app.config import get_settings

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=list[VenueResponse])
def list_venues(db: Session = Depends(get_db)):
    """List all venues."""
    venues = db.query(Venue).all()
    return venues


@router.get("/{venue_id}", response_model=VenueWithEventsResponse)
def get_venue(venue_id: int, db: Session = Depends(get_db)):
    """Get venue with its events."""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.post("", response_model=VenueResponse, status_code=201)
def create_venue(venue: VenueCreate, db: Session = Depends(get_db)):
    """Create a new venue."""
    db_venue = Venue(**venue.model_dump())
    db.add(db_venue)
    db.commit()
    db.refresh(db_venue)
    return db_venue


@router.put("/{venue_id}", response_model=VenueResponse)
def update_venue(venue_id: int, venue: VenueUpdate, db: Session = Depends(get_db)):
    """Update a venue."""
    db_venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not db_venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    update_data = venue.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_venue, field, value)

    db.commit()
    db.refresh(db_venue)
    return db_venue


@router.delete("/{venue_id}", status_code=204)
def delete_venue(venue_id: int, db: Session = Depends(get_db)):
    """Delete a venue."""
    db_venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not db_venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    db.delete(db_venue)
    db.commit()
    return None


@router.post("/{venue_id}/logo", response_model=VenueResponse)
async def upload_venue_logo(
    venue_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a logo for a venue."""
    db_venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not db_venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"venue_{venue_id}_{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Update venue with logo URL
    db_venue.logo_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(db_venue)

    return db_venue


@router.get("/{venue_id}/events", response_model=list[EventResponse])
def list_venue_events(venue_id: int, db: Session = Depends(get_db)):
    """List events at a specific venue."""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    events = db.query(Event).filter(Event.venue_id == venue_id).all()
    return events
