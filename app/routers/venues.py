from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

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
from app.services.voiceover_service import get_voiceover_service

router = APIRouter(prefix="/venues", tags=["venues"])


# Pydantic schemas for voiceover endpoints
class VoiceSettingsUpdate(BaseModel):
    voice_id: str
    voice_name: Optional[str] = None
    voice_settings: Optional[dict] = None


class VoicePreviewRequest(BaseModel):
    voice_id: str
    text: Optional[str] = None


@router.get("", response_model=list[VenueResponse])
def list_venues(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List venues."""
    venues = db.query(Venue).order_by(Venue.id).offset(offset).limit(limit).all()
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
def list_venue_events(
    venue_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List events at a specific venue."""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    events = db.query(Event).filter(Event.venue_id == venue_id).order_by(Event.event_date.desc()).offset(offset).limit(limit).all()
    return events


@router.get("/voiceover/voices")
def get_available_voices(db: Session = Depends(get_db)):
    """Get list of available ElevenLabs voices."""
    service = get_voiceover_service(db)
    result = service._get_available_voices()

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/voiceover/preview")
def preview_voice(request: VoicePreviewRequest, db: Session = Depends(get_db)):
    """Preview a voice with sample text."""
    service = get_voiceover_service(db)
    result = service.preview_voice(
        voice_id=request.voice_id,
        text=request.text
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    # Return the audio file
    return FileResponse(
        result["file_path"],
        media_type="audio/mpeg",
        filename=f"voice_preview_{request.voice_id}.mp3"
    )


@router.get("/{venue_id}/voice-settings")
def get_venue_voice_settings(venue_id: int, db: Session = Depends(get_db)):
    """Get venue's voice settings."""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    import json
    voice_settings = None
    if venue.voice_settings:
        try:
            voice_settings = json.loads(venue.voice_settings)
        except:
            pass

    return {
        "venue_id": venue.id,
        "venue_name": venue.name,
        "voice_id": venue.voice_id,
        "voice_name": venue.voice_name,
        "voice_settings": voice_settings
    }


@router.put("/{venue_id}/voice-settings")
def update_venue_voice_settings(
    venue_id: int,
    settings: VoiceSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update venue's voice settings."""
    service = get_voiceover_service(db)
    result = service.update_venue_voice(
        venue_id=venue_id,
        voice_id=settings.voice_id,
        voice_name=settings.voice_name,
        voice_settings=settings.voice_settings
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["error"])

    return result
