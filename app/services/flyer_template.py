"""
Flyer Template Service

Manages user-uploaded flyer templates and generates event flyers
using template structure + event content via NanoBanana AI.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from enum import Enum

import httpx
import base64
from pathlib import Path

from sqlalchemy.orm import Session, joinedload
from app.config import get_settings
from app.models import Event, FlyerTemplate, FlyerTemplateMagicToken

logger = logging.getLogger(__name__)


def generate_flyer_from_template(
    db: Session,
    event_id: int,
    template_id: int,
    prompt_overrides: Optional[str] = None,
) -> dict:
    """
    Generate an event flyer using a template structure.

    The AI vision model analyzes the template to understand:
    - Layout and composition
    - Typography hierarchy
    - Color scheme
    - Visual elements

    Then generates a new flyer with event content matching that style.

    Args:
        db: Database session
        event_id: Event to generate flyer for
        template_id: Template to use as style reference
        prompt_overrides: Additional instructions for the AI

    Returns:
        Dict with generation result or error
    """
    settings = get_settings()

    # Load event with venue
    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    # Load template
    template = db.query(FlyerTemplate).filter(FlyerTemplate.id == template_id).first()
    if not template:
        return {"error": "Template not found"}

    if not template.image_url:
        return {"error": "Template has no image"}

    # Build the prompt
    base_url = settings.base_url.rstrip("/")

    # Build price info
    price_info = ""
    if event.ticket_tiers:
        prices = [f"${t.price / 100:.2f}" for t in event.ticket_tiers if t.price > 0]
        if prices:
            price_info = f" | {', '.join(prices)}"

    # Build location
    location = event.venue.name if event.venue else "TBD"
    if event.venue and event.venue.address:
        location += f"\n{event.venue.address}"

    # Create detailed prompt
    prompt = f"""You are a professional event flyer designer. Create a visually stunning event poster with this information:

EVENT: {event.name}
DATE: {event.event_date} at {event.event_time if event.event_time else 'TBD'}
LOCATION: {location}
{price_info}

ADDITIONAL DETAILS:
{event.description or event.name}

Your task:
1. Analyze the reference template image to understand:
   - The overall layout and composition
   - Typography hierarchy (how headlines, dates, venue names are positioned)
   - Color scheme and visual style
   - Any design elements (shapes, patterns, effects)

2. Create a NEW flyer for this event that:
   - Uses the SAME layout and composition as the template
   - Matches the color scheme and visual style
   - Replaces ALL text content with the event details above
   - Maintains the same typographic hierarchy
   - Keeps similar visual elements

The flyer should look like it came from the same designer who made the template, just for a different event.

Output: A high-quality event poster optimized for social media sharing."""

    # Add template instructions if available
    if template.prompt_instructions:
        prompt += f"\n\nTEMPLATE STYLE INSTRUCTIONS:\n{template.prompt_instructions}"

    if prompt_overrides:
        prompt += f"\n\nADDITIONAL REQUIREMENTS:\n{prompt_overrides}"

    # Call NanoBanana API
    try:
        # Build request
        nano_request = {
            "prompt": prompt,
            "model": "flux",  # Use Flux for image generation
            "image_size": "1024x1024",  # Square for social media
            "num_images": 1,
        }

        # Add reference image if template has one
        if template.image_url:
            # Download and encode template image
            template_image_data = download_image_as_base64(template.image_url)
            if template_image_data:
                nano_request["reference_image"] = template_image_data

        # Call NanoBanana
        response = httpx.post(
            settings.nanobanana_api_url,
            json=nano_request,
            headers={"Authorization": f"Bearer {settings.nanobanana_api_key}"},
            timeout=120.0,
        )

        if response.status_code != 200:
            logger.error(f"NanoBanana API error: {response.status_code} - {response.text}")
            return {"error": f"Image generation failed: {response.text}"}

        result = response.json()

        # Handle response
        if result.get("images") and len(result["images"]) > 0:
            image_url = result["images"][0]["url"]

            # Update event image
            event.image_url = image_url
            db.commit()
            db.refresh(event)

            # Update template usage
            template.times_used = (template.times_used or 0) + 1
            template.last_used_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "success": True,
                "event_id": event.id,
                "event_name": event.name,
                "template_id": template_id,
                "template_name": template.name,
                "image_url": image_url,
                "message": f"Flyer generated using '{template.name}' template!",
            }
        else:
            return {"error": "No image generated from NanoBanana"}

    except Exception as e:
        logger.error(f"Error generating flyer from template: {e}", exc_info=True)
        return {"error": f"Generation failed: {str(e)}"}


def download_image_as_base64(image_url: str) -> Optional[str]:
    """Download an image and return as base64 data URI."""
    try:
        response = httpx.get(image_url, timeout=30, follow_redirects=True)
        if response.status_code == 200:
            # Detect content type
            content_type = response.headers.get("content-type", "image/jpeg")

            # Encode to base64
            image_data = base64.b64encode(response.content).decode("utf-8")
            return f"data:{content_type};base64,{image_data}"
    except Exception as e:
        logger.error(f"Error downloading template image: {e}")
        return None


def create_template_upload_token(
    db: Session,
    event_id: int,
    phone: str,
    expires_hours: int = 24,
) -> dict:
    """
    Create a magic token for template upload/selection via SMS.

    Args:
        db: Database session
        event_id: Event to generate flyer for
        phone: Phone number to send SMS to
        expires_hours: Token expiration time

    Returns:
        Dict with token and upload URL
    """
    import secrets

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Generate token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    # Save token to database
    magic_token = FlyerTemplateMagicToken(
        event_id=event_id,
        phone=phone,
        token=token,
        expires_at=expires_at,
    )
    db.add(magic_token)
    db.commit()

    upload_url = f"{settings.base_url.rstrip('/')}/flyer-templates/select/{token}"

    # Send SMS
    from app.services.sms import send_sms

    message = f"""🎨 {event.name} Flyer Template

Tap to choose or upload a flyer template:
{upload_url}

Link expires in {expires_hours} hours."""

    try:
        send_sms(phone, message)
        return {
            "success": True,
            "token": token,
            "upload_url": upload_url,
            "expires_at": expires_at.isoformat(),
            "message": f"SMS sent to {phone}",
        }
    except Exception as e:
        logger.error(f"Error sending template upload SMS: {e}")
        return {
            "success": True,
            "token": token,
            "upload_url": upload_url,
            "warning": "Token created but SMS failed to send"
        }


def validate_template_token(db: Session, token: str) -> Optional[FlyerTemplateMagicToken]:
    """
    Validate a flyer template magic token.

    Returns the token record if valid, None otherwise.
    """
    magic_token = (
        db.query(FlyerTemplateMagicToken)
        .filter(FlyerTemplateMagicToken.token == token)
        .first()
    )

    if not magic_token:
        return None

    if magic_token.expires_at < datetime.now(timezone.utc):
        return None

    return magic_token


def get_templates_for_selection(
    db: Session,
    token: str,
) -> dict:
    """
    Get available templates for selection via magic link.

    Args:
        db: Database session
        token: Magic token

    Returns:
        Dict with available templates and event info
    """
    # Validate token
    magic_token = validate_template_token(db, token)
    if not magic_token:
        return {"error": "Invalid or expired token"}

    # Get event info
    event = db.query(Event).filter(Event.id == magic_token.event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Get all templates
    templates = db.query(FlyerTemplate).order_by(FlyerTemplate.times_used.desc()).all()

    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "date": str(event.event_date) if event.event_date else None,
            "time": str(event.event_time) if event.event_time else None,
            "current_image_url": event.image_url,
        },
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "image_url": t.image_url,
                "thumbnail_url": t.thumbnail_url or t.image_url,
                "times_used": t.times_used or 0,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in templates
        ],
        "count": len(templates),
    }


def mark_token_used(db: Session, token: str) -> bool:
    """
    Mark a magic token as used.

    Returns True if successful, False otherwise.
    """
    magic_token = validate_template_token(db, token)
    if not magic_token:
        return False

    magic_token.used_at = datetime.now(timezone.utc)
    db.commit()
    return True
