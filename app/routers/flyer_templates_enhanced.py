"""Enhanced Flyer Templates API with Multi-Image Context Support.

Add this router to app/main.py:
    from app.routers import flyer_templates_enhanced
    app.include_router(flyer_templates_enhanced.router)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, FlyerTemplate
from app.services.flyer_template_enhanced import (
    generate_flyer_with_context,
    generate_flyer_with_event_artists,
)

router = APIRouter(prefix="/api/flyer-templates-enhanced", tags=["flyer-templates-enhanced"])


class GenerateFlyerWithContextRequest(BaseModel):
    """Request to generate flyer with multiple image references."""
    template_id: int
    artist_images: Optional[List[str]] = None  # URLs to artist/performer photos
    additional_images: Optional[List[str]] = None  # URLs to venue, mood, context images
    prompt_overrides: Optional[str] = None  # Additional AI instructions


class GenerateFlyerResponse(BaseModel):
    """Response for flyer generation."""
    success: bool
    event_id: int
    event_name: str
    template_id: int
    template_name: str
    image_url: str
    reference_images_used: int
    artist_images_count: int
    message: str


@router.post("/events/{event_id}/generate", response_model=GenerateFlyerResponse)
def generate_flyer_with_multi_image_context(
    event_id: int,
    request: GenerateFlyerWithContextRequest,
    db: Session = Depends(get_db),
):
    """
    Generate event flyer using template + multiple reference images.

    This endpoint allows you to provide:
    - Template ID (for style reference)
    - Artist/performer images (for visual content)
    - Additional context images (venue, mood, etc.)

    Example request:
    ```json
    {
      "template_id": 5,
      "artist_images": [
        "https://example.com/artist1.jpg",
        "https://example.com/artist2.jpg"
      ],
      "additional_images": [
        "https://example.com/venue.jpg"
      ],
      "prompt_overrides": "Make the artist photos prominent, use vibrant colors"
    }
    ```

    The AI will:
    1. Analyze the template for layout/style
    2. Incorporate the artist images into the design
    3. Use additional images for context/atmosphere
    4. Generate a cohesive flyer combining all elements
    """
    result = generate_flyer_with_context(
        db=db,
        event_id=event_id,
        template_id=request.template_id,
        artist_images=request.artist_images,
        additional_images=request.additional_images,
        prompt_overrides=request.prompt_overrides,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/events/{event_id}/generate-auto", response_model=GenerateFlyerResponse)
def generate_flyer_auto_detect_images(
    event_id: int,
    template_id: int,
    prompt_overrides: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Generate flyer auto-detecting artist images from event fields.

    This endpoint automatically pulls artist images from:
    - event.artist_image_url
    - event.additional_images (JSON array)

    Simpler than the full endpoint - just provide template_id
    and it finds the artist images automatically.

    Example:
    ```
    POST /api/flyer-templates-enhanced/events/123/generate-auto?template_id=5
    ```
    """
    result = generate_flyer_with_event_artists(
        db=db,
        event_id=event_id,
        template_id=template_id,
        prompt_overrides=prompt_overrides,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# Event artist image management endpoints

class UpdateEventImagesRequest(BaseModel):
    """Request to update event artist images."""
    artist_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    performer_names: Optional[List[str]] = None


@router.put("/events/{event_id}/images")
def update_event_images(
    event_id: int,
    request: UpdateEventImagesRequest,
    db: Session = Depends(get_db),
):
    """
    Update event artist images and performer names.

    Example:
    ```json
    {
      "artist_image_url": "https://example.com/main-artist.jpg",
      "additional_images": [
        "https://example.com/artist2.jpg",
        "https://example.com/venue.jpg"
      ],
      "performer_names": ["Main Artist", "Supporting Act"]
    }
    ```
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update fields
    if request.artist_image_url is not None:
        event.artist_image_url = request.artist_image_url

    if request.additional_images is not None:
        import json
        event.additional_images = json.dumps(request.additional_images)

    if request.performer_names is not None:
        import json
        event.performer_names = json.dumps(request.performer_names)

    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "event_id": event.id,
        "artist_image_url": event.artist_image_url,
        "additional_images": json.loads(event.additional_images) if event.additional_images else [],
        "performer_names": json.loads(event.performer_names) if event.performer_names else [],
        "message": "Event images updated successfully",
    }


@router.get("/events/{event_id}/images")
def get_event_images(event_id: int, db: Session = Depends(get_db)):
    """Get all images associated with an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    import json

    return {
        "event_id": event.id,
        "event_name": event.name,
        "event_image_url": event.image_url,  # Main event flyer
        "artist_image_url": event.artist_image_url if hasattr(event, 'artist_image_url') else None,
        "additional_images": json.loads(event.additional_images) if hasattr(event, 'additional_images') and event.additional_images else [],
        "performer_names": json.loads(event.performer_names) if hasattr(event, 'performer_names') and event.performer_names else [],
    }
