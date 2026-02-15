"""Service for media sharing token generation and notifications."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import Event, EventGoer, MediaShareToken
from app.config import get_settings
from app.services.email import _send_email
from app.services.sms import send_sms

logger = logging.getLogger(__name__)

_templates_dir = Path(__file__).parent.parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_templates_dir)))


def generate_media_share_token(
    db: Session,
    event_id: int,
    event_goer_id: int,
) -> MediaShareToken:
    """Generate a media share token for an event goer.

    Returns existing valid token if one exists, otherwise creates a new one.
    Token expires 48 hours after the event's scheduled date/time.
    """
    existing = db.query(MediaShareToken).filter(
        MediaShareToken.event_id == event_id,
        MediaShareToken.event_goer_id == event_goer_id,
    ).first()

    now = datetime.now(timezone.utc)
    if existing:
        exp = existing.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp > now:
            return existing

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    # Calculate expiration: event date/time + 48 hours
    try:
        event_dt = datetime.strptime(
            f"{event.event_date} {event.event_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        # Fallback: 48 hours from now
        event_dt = now
    expires_at = event_dt + timedelta(hours=48)

    if existing:
        # Refresh expired token
        existing.token = secrets.token_urlsafe(32)
        existing.expires_at = expires_at
        db.commit()
        db.refresh(existing)
        return existing

    token_obj = MediaShareToken(
        event_id=event_id,
        event_goer_id=event_goer_id,
        token=secrets.token_urlsafe(32),
        expires_at=expires_at,
    )
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)
    return token_obj


def send_media_share_notification(
    db: Session,
    event_goer: EventGoer,
    event: Event,
    token: str,
) -> dict:
    """Send email and/or SMS with the media upload link.

    Respects event_goer opt-in preferences. Returns dict with success
    status for each channel.
    """
    settings = get_settings()
    upload_url = f"{settings.base_url}/events/{event.id}/share?token={token}"
    results = {"email": False, "sms": False}

    # Send email
    if event_goer.email_opt_in:
        try:
            template = _jinja_env.get_template("media_share_email.html")
            html_content = template.render(
                recipient_name=event_goer.name,
                event_name=event.name,
                event_date=event.event_date,
                upload_url=upload_url,
                expires_hours=48,
            )
            results["email"] = _send_email(
                event_goer.email,
                f"Share your photos & videos from {event.name}!",
                html_content,
            )
        except Exception as e:
            logger.warning("Failed to send media share email to %s: %s", event_goer.email, e)

    # Send SMS
    if event_goer.sms_opt_in and event_goer.phone:
        try:
            message = (
                f"{event_goer.name}, thanks for attending {event.name}! "
                f"Share your photos & videos here: {upload_url} "
                f"(link expires in 48 hours)"
            )
            sms_result = send_sms(event_goer.phone, message)
            results["sms"] = sms_result.get("success", False)
        except Exception as e:
            logger.warning("Failed to send media share SMS to %s: %s", event_goer.phone, e)

    return results


def validate_media_token(
    db: Session,
    token: str,
    event_id: int,
) -> Optional[MediaShareToken]:
    """Validate a media share token. Returns the token if valid, else None."""
    token_obj = db.query(MediaShareToken).filter(
        MediaShareToken.token == token,
        MediaShareToken.event_id == event_id,
    ).first()

    if not token_obj:
        return None

    now = datetime.now(timezone.utc)
    exp = token_obj.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= now:
        return None

    return token_obj
