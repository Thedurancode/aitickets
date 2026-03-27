"""API endpoints for multi-platform event publishing."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_publisher import publish_event, get_available_platforms

router = APIRouter(prefix="/api/event-publisher", tags=["event-publisher"])


class PublishEventRequest(BaseModel):
    """Request to publish event to multiple platforms."""
    platforms: Optional[List[str]] = None  # None = all configured platforms
    exclude: Optional[List[str]] = None  # Platforms to skip


class PublishEventResponse(BaseModel):
    """Response from multi-platform publishing."""
    success: bool
    event_id: int
    event_name: str
    platforms_attempted: List[str]
    results: dict  # Per-platform results
    summary: dict  # Success/failure counts


@router.post("/events/{event_id}/publish", response_model=PublishEventResponse)
def publish_event_to_platforms(
    event_id: int,
    request: PublishEventRequest,
    db: Session = Depends(get_db),
):
    """
    Publish event to multiple ticketing and discovery platforms at once.

    Available platforms:
    - **eventbrite**: Eventbrite ticketing platform
    - **bandsintown**: Bandsintown artist/event discovery
    - **social_media**: Post to Facebook, Instagram, Twitter, etc. (via Postiz)
    - **meta_ads**: Create Facebook/Instagram ad campaign
    - **webhooks**: Trigger custom webhooks
    - **calendar**: Generate calendar links (iCal/Google)

    Example requests:

    1. Publish to all configured platforms:
    ```json
    {
      "platforms": null
    }
    ```

    2. Publish to specific platforms only:
    ```json
    {
      "platforms": ["eventbrite", "social_media", "meta_ads"]
    }
    ```

    3. Publish to all except Meta Ads:
    ```json
    {
      "exclude": ["meta_ads"]
    }
    ```

    Returns per-platform results with success/failure status.
    """
    # Verify event exists
    from app.models import Event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Publish to platforms
    results = publish_event(
        db=db,
        event_id=event_id,
        platforms=request.platforms,
        exclude=request.exclude
    )

    # Calculate summary
    platforms_attempted = list(results.keys())
    successes = [p for p, r in results.items() if r.get("success")]
    failures = [p for p, r in results.items() if not r.get("success")]

    return PublishEventResponse(
        success=len(successes) > 0,
        event_id=event_id,
        event_name=event.name,
        platforms_attempted=platforms_attempted,
        results=results,
        summary={
            "total_attempted": len(platforms_attempted),
            "successful": len(successes),
            "failed": len(failures),
            "success_platforms": successes,
            "failed_platforms": failures,
        }
    )


@router.get("/platforms")
def list_available_platforms():
    """
    Get list of available publishing platforms and their configuration status.

    Returns information about:
    - Platform ID and name
    - Whether it's configured (has required API keys)
    - Required environment variables
    - Documentation URLs

    Use this to check which platforms are ready to use.
    """
    platforms = get_available_platforms()

    configured_count = len([p for p in platforms if p["configured"]])
    total_count = len(platforms)

    return {
        "platforms": platforms,
        "summary": {
            "total": total_count,
            "configured": configured_count,
            "unconfigured": total_count - configured_count,
        }
    }


@router.post("/events/{event_id}/publish/preview")
def preview_event_publication(
    event_id: int,
    request: PublishEventRequest,
    db: Session = Depends(get_db),
):
    """
    Preview what would be published without actually publishing.

    Shows:
    - Which platforms would be used
    - What content would be posted
    - Configuration requirements

    Useful for testing before actual publication.
    """
    from app.models import Event
    from app.services.event_publisher import EventPublisher

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    publisher = EventPublisher(db, event_id)
    platforms = get_available_platforms()

    # Filter platforms based on request
    requested_platforms = request.platforms or [p["id"] for p in platforms]
    if request.exclude:
        requested_platforms = [p for p in requested_platforms if p not in request.exclude]

    # Build preview data
    preview = {
        "event": {
            "id": event.id,
            "name": event.name,
            "date": event.event_date,
            "time": event.event_time,
            "venue": event.venue.name if event.venue else None,
            "image_url": event.image_url,
        },
        "platforms_to_publish": [],
        "warnings": []
    }

    for platform_id in requested_platforms:
        platform_info = next((p for p in platforms if p["id"] == platform_id), None)
        if not platform_info:
            preview["warnings"].append(f"Unknown platform: {platform_id}")
            continue

        platform_preview = {
            "id": platform_id,
            "name": platform_info["name"],
            "configured": platform_info["configured"],
            "will_publish": platform_info["configured"],
        }

        if not platform_info["configured"]:
            platform_preview["error"] = f"Not configured. Requires: {', '.join(platform_info['requires'])}"
            platform_preview["setup_url"] = platform_info.get("docs_url")

        preview["platforms_to_publish"].append(platform_preview)

    return preview
