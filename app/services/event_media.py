"""Event Media Management Service.

Handles CRUD operations for event media assets (artists, logos, sponsors, etc.)
and automatic flyer generation using all collected media.
"""
import json
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import Event, EventMedia, MediaType, FlyerTemplate
from app.services.flyer_template_enhanced import generate_flyer_with_context


def add_event_media(
    db: Session,
    event_id: int,
    media_type: str,
    media_url: str,
    label: Optional[str] = None,
    display_order: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Add a media asset to an event.

    Args:
        db: Database session
        event_id: Event ID
        media_type: Type of media (artist_photo, logo, venue_photo, etc.)
        media_url: URL to the media asset
        label: Optional label (e.g., "Artist Name", "Sponsor: Coca-Cola")
        display_order: Optional display order (defaults to next available)
        metadata: Optional metadata dict (dimensions, credits, etc.)

    Returns:
        dict with success status and created media info
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Validate media type
    try:
        media_type_enum = MediaType(media_type)
    except ValueError:
        valid_types = [t.value for t in MediaType]
        return {"error": f"Invalid media_type. Must be one of: {', '.join(valid_types)}"}

    # Auto-determine display_order if not provided
    if display_order is None:
        max_order = db.query(EventMedia).filter(
            EventMedia.event_id == event_id
        ).order_by(desc(EventMedia.display_order)).first()
        display_order = (max_order.display_order + 1) if max_order else 0

    # Create media entry
    media = EventMedia(
        event_id=event_id,
        media_type=media_type_enum,
        media_url=media_url,
        label=label,
        display_order=display_order,
        media_metadata=json.dumps(metadata) if metadata else None,
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    return {
        "success": True,
        "media": {
            "id": media.id,
            "event_id": media.event_id,
            "media_type": media.media_type.value,
            "media_url": media.media_url,
            "label": media.label,
            "display_order": media.display_order,
            "metadata": json.loads(media.media_metadata) if media.media_metadata else None,
            "created_at": str(media.created_at),
        },
        "message": f"Added {media_type} to event",
    }


def get_event_media(
    db: Session,
    event_id: int,
    media_type: Optional[str] = None,
) -> dict:
    """
    Get all media assets for an event, optionally filtered by type.

    Args:
        db: Database session
        event_id: Event ID
        media_type: Optional media type filter

    Returns:
        dict with event info and media assets grouped by type
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    query = db.query(EventMedia).filter(EventMedia.event_id == event_id)

    if media_type:
        try:
            media_type_enum = MediaType(media_type)
            query = query.filter(EventMedia.media_type == media_type_enum)
        except ValueError:
            valid_types = [t.value for t in MediaType]
            return {"error": f"Invalid media_type. Must be one of: {', '.join(valid_types)}"}

    media_items = query.order_by(EventMedia.display_order).all()

    # Group by media type
    grouped_media = {}
    for item in media_items:
        type_key = item.media_type.value
        if type_key not in grouped_media:
            grouped_media[type_key] = []

        grouped_media[type_key].append({
            "id": item.id,
            "media_url": item.media_url,
            "label": item.label,
            "display_order": item.display_order,
            "metadata": json.loads(item.media_metadata) if item.media_metadata else None,
            "created_at": str(item.created_at),
        })

    return {
        "event_id": event.id,
        "event_name": event.name,
        "total_media_count": len(media_items),
        "media_by_type": grouped_media,
        "all_media": [
            {
                "id": item.id,
                "media_type": item.media_type.value,
                "media_url": item.media_url,
                "label": item.label,
                "display_order": item.display_order,
                "metadata": json.loads(item.media_metadata) if item.media_metadata else None,
            }
            for item in media_items
        ],
    }


def update_event_media(
    db: Session,
    media_id: int,
    media_url: Optional[str] = None,
    label: Optional[str] = None,
    display_order: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Update an existing media asset."""
    media = db.query(EventMedia).filter(EventMedia.id == media_id).first()
    if not media:
        return {"error": "Media not found"}

    if media_url is not None:
        media.media_url = media_url
    if label is not None:
        media.label = label
    if display_order is not None:
        media.display_order = display_order
    if metadata is not None:
        media.media_metadata = json.dumps(metadata)

    db.commit()
    db.refresh(media)

    return {
        "success": True,
        "media": {
            "id": media.id,
            "media_type": media.media_type.value,
            "media_url": media.media_url,
            "label": media.label,
            "display_order": media.display_order,
            "metadata": json.loads(media.media_metadata) if media.media_metadata else None,
        },
        "message": "Media updated successfully",
    }


def delete_event_media(db: Session, media_id: int) -> dict:
    """Delete a media asset."""
    media = db.query(EventMedia).filter(EventMedia.id == media_id).first()
    if not media:
        return {"error": "Media not found"}

    media_info = {
        "id": media.id,
        "media_type": media.media_type.value,
        "label": media.label,
    }

    db.delete(media)
    db.commit()

    return {
        "success": True,
        "deleted_media": media_info,
        "message": "Media deleted successfully",
    }


def bulk_add_event_media(
    db: Session,
    event_id: int,
    media_items: List[Dict],
) -> dict:
    """
    Bulk add multiple media assets to an event.

    Args:
        db: Database session
        event_id: Event ID
        media_items: List of media dicts with keys: media_type, media_url, label (optional)

    Returns:
        dict with success status and list of created media
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    created_media = []
    errors = []

    for i, item in enumerate(media_items):
        result = add_event_media(
            db=db,
            event_id=event_id,
            media_type=item.get("media_type"),
            media_url=item.get("media_url"),
            label=item.get("label"),
            display_order=item.get("display_order"),
            metadata=item.get("metadata"),
        )

        if "error" in result:
            errors.append(f"Item {i}: {result['error']}")
        else:
            created_media.append(result["media"])

    return {
        "success": len(errors) == 0,
        "created_count": len(created_media),
        "error_count": len(errors),
        "created_media": created_media,
        "errors": errors if errors else None,
    }


def generate_flyer_from_event_media(
    db: Session,
    event_id: int,
    template_id: int,
    prompt_overrides: Optional[str] = None,
    include_types: Optional[List[str]] = None,
) -> dict:
    """
    Generate event flyer using all media assets attached to the event.

    Automatically categorizes media:
    - artist_photo → artist_images
    - venue_photo → additional_images
    - logo, sponsor_logo, background, graphic → additional_images

    Args:
        db: Database session
        event_id: Event ID
        template_id: Flyer template ID
        prompt_overrides: Optional custom AI instructions
        include_types: Optional list of media types to include (defaults to all)

    Returns:
        dict with generated flyer info
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Get all media for the event
    query = db.query(EventMedia).filter(EventMedia.event_id == event_id)

    if include_types:
        try:
            type_enums = [MediaType(t) for t in include_types]
            query = query.filter(EventMedia.media_type.in_(type_enums))
        except ValueError as e:
            return {"error": f"Invalid media type: {str(e)}"}

    media_items = query.order_by(EventMedia.display_order).all()

    if not media_items:
        return {"error": "No media assets found for this event. Add some media first."}

    # Categorize media by type
    artist_images = []
    additional_images = []

    for item in media_items:
        if item.media_type == MediaType.ARTIST_PHOTO:
            artist_images.append(item.media_url)
        else:
            # venue_photo, logo, sponsor_logo, background, graphic, other
            additional_images.append(item.media_url)

    # Build enhanced prompt with labels
    labels_info = []
    for item in media_items:
        if item.label:
            labels_info.append(f"{item.media_type.value}: {item.label}")

    enhanced_prompt = prompt_overrides or ""
    if labels_info:
        enhanced_prompt += f"\n\nMedia assets included:\n" + "\n".join(f"- {label}" for label in labels_info)

    # Generate flyer using enhanced flyer service
    result = generate_flyer_with_context(
        db=db,
        event_id=event_id,
        template_id=template_id,
        artist_images=artist_images if artist_images else None,
        additional_images=additional_images if additional_images else None,
        prompt_overrides=enhanced_prompt if enhanced_prompt else None,
    )

    if "error" in result:
        return result

    # Add media usage info
    result["media_used"] = {
        "artist_photos": len(artist_images),
        "other_images": len(additional_images),
        "total_media_assets": len(media_items),
        "media_breakdown": {
            media_type.value: sum(1 for m in media_items if m.media_type == media_type)
            for media_type in MediaType
        },
    }

    return result
