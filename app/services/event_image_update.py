"""
Event Image Update via SMS Token

Allows event promoters to update event images via SMS magic link without login.
Similar to style picker - generates token, sends SMS link, shows upload page.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Event, EventImageUpdateToken
from app.services.sms import send_sms
from app.config import get_settings

logger = logging.getLogger(__name__)


def generate_image_update_token(
    db: Session,
    event_id: int,
    phone: str,
    expires_hours: int = 24
) -> dict:
    """
    Generate a token for event image update and send SMS with magic link.

    Args:
        db: Database session
        event_id: Event to update
        phone: Phone number to send SMS to
        expires_hours: Token expiration time (default 24 hours)

    Returns:
        Dict with token status and link
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Generate secure token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    # Save token to database
    update_token = EventImageUpdateToken(
        event_id=event_id,
        phone=phone,
        token=token,
        expires_at=expires_at,
    )
    db.add(update_token)
    db.commit()

    # Generate magic link
    settings = get_settings()
    base_url = settings.base_url.rstrip("/")
    magic_link = f"{base_url}/update-event-image/{token}"

    # Send SMS
    message = (
        f"📸 Update event image for {event.name}\n\n"
        f"Tap here to upload a new image:\n{magic_link}\n\n"
        f"Link expires in {expires_hours} hours."
    )

    try:
        send_sms(phone, message)
        logger.info(f"Sent image update SMS to {phone} for event {event_id}")
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return {
            "success": True,
            "token": token,
            "magic_link": magic_link,
            "warning": "Token created but SMS failed to send"
        }

    return {
        "success": True,
        "token": token,
        "magic_link": magic_link,
        "message": f"SMS sent to {phone}",
        "expires_at": expires_at.isoformat()
    }


def validate_token(db: Session, token: str) -> Optional[EventImageUpdateToken]:
    """
    Validate an event image update token.

    Returns the token record if valid, None otherwise.
    """
    update_token = (
        db.query(EventImageUpdateToken)
        .filter(EventImageUpdateToken.token == token)
        .first()
    )

    if not update_token:
        return None

    # Check if expired
    if update_token.expires_at < datetime.now(timezone.utc):
        return None

    # Check if already used
    if update_token.used_at:
        return None

    return update_token


def mark_token_used(db: Session, token: str) -> bool:
    """Mark a token as used."""
    update_token = (
        db.query(EventImageUpdateToken)
        .filter(EventImageUpdateToken.token == token)
        .first()
    )

    if update_token:
        update_token.used_at = datetime.now(timezone.utc)
        db.commit()
        return True

    return False


def update_event_image(db: Session, token: str, new_image_url: str) -> dict:
    """
    Update an event's image URL using a valid token.

    Args:
        db: Database session
        token: Image update token
        new_image_url: New image URL (already uploaded to uploads/)

    Returns:
        Result dict with success status
    """
    # Validate token
    update_token = validate_token(db, token)
    if not update_token:
        return {"error": "Invalid or expired token"}

    # Get event
    event = db.query(Event).filter(Event.id == update_token.event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Store old image for potential rollback
    old_image_url = event.image_url

    # Update image
    event.image_url = new_image_url
    event.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Mark token as used
    mark_token_used(db, token)

    logger.info(
        f"Event {event.id} image updated via token {token[:8]}... "
        f"by {update_token.phone}. Old: {old_image_url}, New: {new_image_url}"
    )

    return {
        "success": True,
        "event_id": event.id,
        "event_name": event.name,
        "old_image_url": old_image_url,
        "new_image_url": new_image_url,
        "message": f"Event image updated successfully for {event.name}"
    }


def get_token_info(db: Session, token: str) -> dict:
    """
    Get information about a token for the upload page.
    Returns event details if token is valid.
    """
    update_token = validate_token(db, token)
    if not update_token:
        return {"error": "Invalid or expired token"}

    event = db.query(Event).filter(Event.id == update_token.event_id).first()
    if not event:
        return {"error": "Event not found"}

    return {
        "valid": True,
        "event": {
            "id": event.id,
            "name": event.name,
            "date": event.event_date,
            "time": event.event_time,
            "current_image_url": event.image_url,
        },
        "expires_at": update_token.expires_at.isoformat(),
    }
