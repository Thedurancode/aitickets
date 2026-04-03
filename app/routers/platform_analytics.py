"""
Cross-Platform Analytics API Endpoints

REST API for querying page view analytics across multiple platforms.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Event
from app.services.platform_analytics import get_platform_analytics_service


router = APIRouter(prefix="/api/platform-analytics", tags=["Platform Analytics"])


class ExternalPageViewRequest(BaseModel):
    """Request model for tracking external page views."""
    event_id: int
    platform: str
    external_platform_id: Optional[str] = None
    platform_data: Optional[Dict] = None


class BulkImportRequest(BaseModel):
    """Request model for bulk importing views from external platforms."""
    event_id: int
    platform: str
    view_count: int
    external_platform_id: Optional[str] = None
    platform_data: Optional[Dict] = None


@router.get("/events/{event_id}", response_model=Dict)
def get_event_cross_platform_views(
    event_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated page views across all platforms for an event.

    Returns:
    - total_views: Total views across all platforms
    - by_platform: Breakdown by platform (internal, eventbrite, facebook, etc.)
    - period_days: Number of days analyzed
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    service = get_platform_analytics_service(db)
    return service.get_cross_platform_pageviews(event_id, days)


@router.get("/events/{event_id}/breakdown", response_model=List[Dict])
def get_event_platform_breakdown(
    event_id: int,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get detailed platform-by-platform breakdown with engagement metrics.

    Returns list of platform analytics with:
    - platform: Platform name
    - views: Total views
    - unique_visitors: Unique visitors
    - avg_views_per_visitor: Engagement metric
    - first_view: First view timestamp
    - last_view: Most recent view timestamp
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    service = get_platform_analytics_service(db)
    return service.get_platform_breakdown(event_id, days)


@router.get("/summary", response_model=Dict)
def get_all_platforms_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get org-wide summary of views across all events and platforms.

    Returns:
    - total_views: All views across all events
    - by_platform: Views broken down by platform
    - platforms_tracked: Number of unique platforms
    - period_days: Days analyzed
    """
    service = get_platform_analytics_service(db)
    return service.get_all_platforms_summary(days)


@router.post("/track-external", status_code=201)
def track_external_page_view(
    request: ExternalPageViewRequest,
    db: Session = Depends(get_db)
):
    """
    Manually track a page view from an external platform.

    Useful for:
    - Manual data imports
    - Testing cross-platform tracking
    - Recording views from platforms without API integration
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    service = get_platform_analytics_service(db)
    page_view = service.track_external_pageview(
        event_id=request.event_id,
        platform=request.platform,
        external_platform_id=request.external_platform_id,
        platform_data=request.platform_data
    )

    return {
        "success": True,
        "message": f"Tracked external page view from {request.platform}",
        "page_view_id": page_view.id,
        "event_id": request.event_id,
        "platform": request.platform
    }


@router.post("/bulk-import", status_code=201)
def bulk_import_views(
    request: BulkImportRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk import view counts from external platforms.

    Useful when platforms provide aggregate counts rather than individual view records.
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if request.view_count <= 0:
        raise HTTPException(status_code=400, detail="view_count must be positive")

    if request.view_count > 10000:
        raise HTTPException(
            status_code=400,
            detail="view_count exceeds maximum of 10,000. Please import in batches."
        )

    service = get_platform_analytics_service(db)
    created_count = service.bulk_import_external_views(
        event_id=request.event_id,
        platform=request.platform,
        view_count=request.view_count,
        external_platform_id=request.external_platform_id,
        platform_data=request.platform_data
    )

    return {
        "success": True,
        "message": f"Imported {created_count} views from {request.platform}",
        "views_created": created_count,
        "event_id": request.event_id,
        "platform": request.platform
    }


# Webhook receiver endpoint for external platform analytics
@router.post("/webhooks/{platform}")
async def receive_platform_webhook(
    platform: str,
    payload: Dict,
    db: Session = Depends(get_db)
):
    """
    Generic webhook receiver for platform analytics.

    External platforms can POST analytics data here.

    Supported platforms:
    - eventbrite
    - facebook
    - ticketmaster
    - (add custom platforms as needed)

    Expected payload format:
    {
        "event_id": 123,  # Internal event ID or external_platform_id
        "external_platform_id": "evt_abc123",
        "views": 42,
        "metadata": {...}  # Platform-specific data
    }
    """
    # Basic validation
    if "event_id" not in payload and "external_platform_id" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Payload must include either 'event_id' or 'external_platform_id'"
        )

    if "views" not in payload:
        raise HTTPException(status_code=400, detail="Payload must include 'views'")

    # Find event (either by internal ID or external platform ID)
    event = None
    if "event_id" in payload:
        event = db.query(Event).filter(Event.id == payload["event_id"]).first()
    elif "external_platform_id" in payload:
        # TODO: Add mapping table for external_platform_id -> event_id
        raise HTTPException(
            status_code=501,
            detail="External platform ID mapping not yet implemented"
        )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Import views
    service = get_platform_analytics_service(db)
    view_count = payload["views"]

    created_count = service.bulk_import_external_views(
        event_id=event.id,
        platform=platform,
        view_count=view_count,
        external_platform_id=payload.get("external_platform_id"),
        platform_data=payload.get("metadata")
    )

    return {
        "success": True,
        "message": f"Webhook processed: {created_count} views recorded from {platform}",
        "views_created": created_count,
        "event_id": event.id
    }
