"""
Waitlist API Endpoints (Simple Wrapper)

Provides /api/waitlist endpoint for test compatibility.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import WaitlistEntry, WaitlistStatus, Event

router = APIRouter(prefix="/api/waitlist", tags=["Waitlist"])


class WaitlistJoinRequest(BaseModel):
    event_id: int
    name: str
    email: str


@router.post("")
def join_waitlist(
    request: WaitlistJoinRequest,
    db: Session = Depends(get_db)
):
    """
    Join the waitlist for an event.

    Creates a waitlist entry for a sold-out or popular event.
    """
    # Check event exists
    event = db.query(Event).filter(Event.id == request.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if already on waitlist
    existing = db.query(WaitlistEntry).filter(
        WaitlistEntry.event_id == request.event_id,
        WaitlistEntry.email == request.email.strip().lower(),
        WaitlistEntry.status == WaitlistStatus.WAITING,
    ).first()

    if existing:
        return {
            "success": True,
            "message": f"You're already on the waitlist! (#{existing.position})",
            "position": existing.position
        }

    # Compute next position
    max_pos = db.query(func.max(WaitlistEntry.position)).filter(
        WaitlistEntry.event_id == request.event_id
    ).scalar() or 0

    next_position = max_pos + 1

    # Create waitlist entry
    entry = WaitlistEntry(
        event_id=request.event_id,
        email=request.email.strip().lower(),
        name=request.name.strip(),
        position=next_position,
        status=WaitlistStatus.WAITING
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "success": True,
        "message": f"You're #{entry.position} on the waitlist!",
        "position": entry.position
    }


@router.get("/{event_id}")
def get_waitlist_count(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get waitlist count for an event."""
    # Check event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    count = db.query(func.count(WaitlistEntry.id)).filter(
        WaitlistEntry.event_id == event_id,
        WaitlistEntry.status == WaitlistStatus.WAITING
    ).scalar() or 0

    return {
        "event_id": event_id,
        "waitlist_count": count
    }
