"""
Social Proof API Endpoints

Real-time social proof and FOMO signals for events.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from app.database import get_db
from app.services.social_proof import get_social_proof_engine
from app.models import Event

router = APIRouter(prefix="/api/social-proof", tags=["Social Proof"])


@router.get("/{event_id}", response_model=Dict)
@router.get("/events/{event_id}", response_model=Dict)
def get_event_social_proof(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all social proof signals for an event.

    Returns:
    - live_viewers: Current number of people viewing
    - recent_purchases: Last 5 ticket purchases
    - velocity: Sales velocity (tickets/hour)
    - scarcity: Inventory scarcity indicators
    - countdowns: Urgency countdown timers
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    engine = get_social_proof_engine(db)
    return engine.get_social_proof_bundle(event_id)


@router.get("/events/{event_id}/live-viewers")
def get_live_viewers(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get current live viewer count for an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    engine = get_social_proof_engine(db)
    count = engine.get_live_viewers(event_id)

    return {
        "event_id": event_id,
        "live_viewers": count,
        "message": f"🔥 {count} people viewing this event right now" if count > 1 else None
    }


@router.get("/events/{event_id}/recent-purchases")
def get_recent_purchases(
    event_id: int,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Get recent ticket purchases for social proof."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    engine = get_social_proof_engine(db)
    purchases = engine.get_recent_purchases(event_id, limit)

    return {
        "event_id": event_id,
        "purchases": purchases,
        "count": len(purchases)
    }


@router.get("/events/{event_id}/velocity")
def get_sales_velocity(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get ticket sales velocity."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    engine = get_social_proof_engine(db)
    return engine.get_velocity(event_id)


@router.get("/events/{event_id}/scarcity")
def get_scarcity_indicators(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get scarcity indicators for FOMO."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    engine = get_social_proof_engine(db)
    return engine.get_scarcity_indicators(event_id)
