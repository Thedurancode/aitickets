"""Event Media Management API Router.

Endpoints for managing event media assets (artists, logos, sponsors, venue photos)
and automatic flyer generation using all collected media.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import shutil

from app.database import get_db
from app.services.event_media import (
    add_event_media,
    get_event_media,
    update_event_media,
    delete_event_media,
    bulk_add_event_media,
    generate_flyer_from_event_media,
)
from app.config import get_settings

router = APIRouter(prefix="/api/event-media", tags=["event-media"])


# ============== Schemas ==============


def _validate_url(v: str) -> str:
    """Ensure the URL starts with http(s):// or /uploads/."""
    if v and not v.startswith(("http://", "https://", "/uploads/")):
        raise ValueError("media_url must start with http://, https://, or /uploads/")
    return v


class AddMediaRequest(BaseModel):
    """Request to add a media asset to an event."""
    media_type: str = Field(..., description="Type: artist_photo, logo, venue_photo, sponsor_logo, background, graphic, other")
    media_url: str = Field(..., description="URL to the media asset")
    label: Optional[str] = Field(None, description="Label (e.g., 'Artist Name', 'Sponsor: Coca-Cola')")
    display_order: Optional[int] = Field(None, description="Display order (auto if not provided)")
    metadata: Optional[dict] = Field(None, description="Optional metadata (dimensions, credits, etc.)")

    @field_validator("media_url")
    @classmethod
    def validate_media_url(cls, v: str) -> str:
        return _validate_url(v)


class UpdateMediaRequest(BaseModel):
    """Request to update a media asset."""
    media_url: Optional[str] = None
    label: Optional[str] = None
    display_order: Optional[int] = None
    metadata: Optional[dict] = None

    @field_validator("media_url")
    @classmethod
    def validate_media_url(cls, v: str) -> str:
        if v is not None:
            return _validate_url(v)
        return v


class BulkAddMediaRequest(BaseModel):
    """Request to bulk add multiple media assets."""
    media_items: List[AddMediaRequest]


class GenerateFlyerFromMediaRequest(BaseModel):
    """Request to generate flyer from event media."""
    template_id: int = Field(..., description="Flyer template ID")
    prompt_overrides: Optional[str] = Field(None, description="Additional AI instructions")
    include_types: Optional[List[str]] = Field(None, description="Media types to include (defaults to all)")


# ============== Endpoints ==============


@router.post("/events/{event_id}/media")
def add_media_to_event(
    event_id: int,
    request: AddMediaRequest,
    db: Session = Depends(get_db),
):
    """
    Add a media asset to an event.

    **Media Types:**
    - `artist_photo`: Artist/performer headshot or photo
    - `logo`: Event/brand logo
    - `venue_photo`: Venue interior/exterior photo
    - `sponsor_logo`: Sponsor logo
    - `background`: Background image/texture
    - `graphic`: Generic graphic element
    - `other`: Other media type

    **Example:**
    ```json
    {
      "media_type": "artist_photo",
      "media_url": "https://example.com/artist1.jpg",
      "label": "Main Artist",
      "display_order": 0
    }
    ```
    """
    result = add_event_media(
        db=db,
        event_id=event_id,
        media_type=request.media_type,
        media_url=request.media_url,
        label=request.label,
        display_order=request.display_order,
        metadata=request.metadata,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/events/{event_id}/media/upload")
async def upload_media_to_event(
    event_id: int,
    media_type: str = Form(...),
    label: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a media file and add it to an event.

    Uploads the file to the uploads directory and automatically
    adds it to the event's media collection.

    **Form Parameters:**
    - `media_type`: Type of media (artist_photo, logo, venue_photo, etc.)
    - `label`: Optional label for the media
    - `file`: The file to upload
    """
    # Upload file
    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    file_extension = Path(file.filename).suffix or ".png"
    unique_filename = f"event_{event_id}_media_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = uploads_dir / unique_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

    # Generate URL
    base_url = settings.base_url.rstrip("/")
    media_url = f"{base_url}/uploads/{unique_filename}"

    # Add to event media
    result = add_event_media(
        db=db,
        event_id=event_id,
        media_type=media_type,
        media_url=media_url,
        label=label,
    )

    if "error" in result:
        # Clean up uploaded file
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "success": True,
        "uploaded_file": unique_filename,
        "media_url": media_url,
        **result,
    }


@router.get("/events/{event_id}/media")
def get_event_media_list(
    event_id: int,
    media_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get all media assets for an event, optionally filtered by type.

    Returns media grouped by type for easy visualization.

    **Query Parameters:**
    - `media_type`: Optional filter by media type

    **Example Response:**
    ```json
    {
      "event_id": 123,
      "event_name": "Concert Night",
      "total_media_count": 5,
      "media_by_type": {
        "artist_photo": [
          {"id": 1, "media_url": "...", "label": "Main Artist"}
        ],
        "logo": [
          {"id": 2, "media_url": "...", "label": "Event Logo"}
        ]
      }
    }
    ```
    """
    result = get_event_media(db=db, event_id=event_id, media_type=media_type)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.put("/media/{media_id}")
def update_media(
    media_id: int,
    request: UpdateMediaRequest,
    db: Session = Depends(get_db),
):
    """
    Update a media asset.

    You can update the URL, label, display order, or metadata.
    """
    result = update_event_media(
        db=db,
        media_id=media_id,
        media_url=request.media_url,
        label=request.label,
        display_order=request.display_order,
        metadata=request.metadata,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.delete("/media/{media_id}")
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
):
    """Delete a media asset from an event."""
    result = delete_event_media(db=db, media_id=media_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/events/{event_id}/media/bulk")
def bulk_add_media(
    event_id: int,
    request: BulkAddMediaRequest,
    db: Session = Depends(get_db),
):
    """
    Bulk add multiple media assets to an event.

    **Example:**
    ```json
    {
      "media_items": [
        {
          "media_type": "artist_photo",
          "media_url": "https://example.com/artist1.jpg",
          "label": "Main Artist"
        },
        {
          "media_type": "artist_photo",
          "media_url": "https://example.com/artist2.jpg",
          "label": "Supporting Artist"
        },
        {
          "media_type": "logo",
          "media_url": "https://example.com/logo.png",
          "label": "Event Logo"
        }
      ]
    }
    ```
    """
    media_dicts = [item.model_dump() for item in request.media_items]

    result = bulk_add_event_media(
        db=db,
        event_id=event_id,
        media_items=media_dicts,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/events/{event_id}/generate-flyer")
def generate_flyer_from_media(
    event_id: int,
    request: GenerateFlyerFromMediaRequest,
    db: Session = Depends(get_db),
):
    """
    🎨 **Auto-generate event flyer using all media assets.**

    This is the magic endpoint! It automatically:
    1. Collects all media assets attached to the event
    2. Categorizes them (artist photos, logos, venue photos, etc.)
    3. Generates a professional flyer using AI
    4. Updates the event's image_url with the new flyer

    **Workflow:**
    ```
    1. Upload media assets:
       POST /api/event-media/events/{id}/media/upload
       - Artist 1 photo
       - Artist 2 photo
       - Event logo
       - Sponsor logos
       - Venue photo

    2. Generate flyer:
       POST /api/event-media/events/{id}/generate-flyer
       {
         "template_id": 5,
         "prompt_overrides": "Make artist photos prominent, vibrant colors"
       }

    3. Done! Event now has a professional flyer with all media included.
    ```

    **Example Request:**
    ```json
    {
      "template_id": 5,
      "prompt_overrides": "Make the artist photos prominent, use vibrant colors, include all sponsor logos at the bottom",
      "include_types": ["artist_photo", "logo", "sponsor_logo"]
    }
    ```

    **Returns:**
    - Generated flyer URL
    - Media usage breakdown
    - Success status
    """
    result = generate_flyer_from_event_media(
        db=db,
        event_id=event_id,
        template_id=request.template_id,
        prompt_overrides=request.prompt_overrides,
        include_types=request.include_types,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/media-types")
def list_media_types():
    """
    Get list of available media types.

    Returns all supported media types with descriptions.
    """
    from app.models import MediaType

    return {
        "media_types": [
            {
                "value": MediaType.ARTIST_PHOTO.value,
                "label": "Artist Photo",
                "description": "Artist/performer headshot or photo",
                "usage": "Used prominently in flyer design",
            },
            {
                "value": MediaType.LOGO.value,
                "label": "Event Logo",
                "description": "Event or brand logo",
                "usage": "Typically placed at top or bottom of flyer",
            },
            {
                "value": MediaType.VENUE_PHOTO.value,
                "label": "Venue Photo",
                "description": "Venue interior/exterior photo",
                "usage": "Used for background or context",
            },
            {
                "value": MediaType.SPONSOR_LOGO.value,
                "label": "Sponsor Logo",
                "description": "Sponsor logo",
                "usage": "Typically placed at bottom of flyer",
            },
            {
                "value": MediaType.BACKGROUND.value,
                "label": "Background Image",
                "description": "Background image/texture",
                "usage": "Used as flyer background",
            },
            {
                "value": MediaType.GRAPHIC.value,
                "label": "Graphic Element",
                "description": "Generic graphic element",
                "usage": "Decorative elements in the design",
            },
            {
                "value": MediaType.OTHER.value,
                "label": "Other",
                "description": "Other media type",
                "usage": "Additional context for AI",
            },
        ]
    }
