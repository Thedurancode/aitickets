"""
Enhanced Flyer Template Service with Multi-Image Context

Supports:
- Template image (for style reference)
- Artist/performer images (for visual content)
- Event-specific images (venue, past events, etc.)
- Multiple reference images sent to AI for richer generation
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import httpx
import base64
from pathlib import Path

from sqlalchemy.orm import Session, joinedload
from app.config import get_settings
from app.models import Event, FlyerTemplate, FlyerTemplateMagicToken

logger = logging.getLogger(__name__)


def _utc_now_matching(dt: datetime) -> datetime:
    """Return UTC now with timezone-awareness matching `dt`."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return now.replace(tzinfo=None)
    return now


def generate_flyer_with_context(
    db: Session,
    event_id: int,
    template_id: int,
    artist_images: Optional[List[str]] = None,
    additional_images: Optional[List[str]] = None,
    prompt_overrides: Optional[str] = None,
) -> dict:
    """
    Generate an event flyer using template + multiple context images.

    This enhanced version sends multiple images to the AI:
    - Template image (for layout/style reference)
    - Artist/performer images (for visual content/faces)
    - Additional context images (venue, mood, past events, etc.)

    Args:
        db: Database session
        event_id: Event to generate flyer for
        template_id: Template to use as style reference
        artist_images: List of artist/performer image URLs
        additional_images: List of additional context image URLs
        prompt_overrides: Additional instructions for the AI

    Returns:
        Dict with generation result or error

    Example:
        generate_flyer_with_context(
            db=db,
            event_id=123,
            template_id=5,
            artist_images=[
                "https://example.com/artist1.jpg",
                "https://example.com/artist2.jpg"
            ],
            additional_images=[
                "https://example.com/venue-photo.jpg"
            ],
            prompt_overrides="Make the artist photos prominent in the design"
        )
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

    # Enhanced prompt with multi-image context
    prompt = f"""You are a professional event flyer designer. Create a visually stunning event poster with this information:

EVENT: {event.name}
DATE: {event.event_date} at {event.event_time if event.event_time else 'TBD'}
LOCATION: {location}
{price_info}

ADDITIONAL DETAILS:
{event.description or event.name}

You have been provided with MULTIPLE reference images:

1. TEMPLATE IMAGE (primary style reference):
   - Analyze the layout, composition, and typography hierarchy
   - Match the color scheme and visual style
   - Use the same design patterns and elements

"""

    # Add context for artist images
    if artist_images and len(artist_images) > 0:
        prompt += f"""
2. ARTIST/PERFORMER IMAGES ({len(artist_images)} provided):
   - These are the performers/artists for this event
   - Incorporate these faces/images into the flyer design
   - Make the artist photos prominent but blend with the template style
   - Use photo cutouts, frames, or collages as appropriate
   - Ensure the artist is recognizable and featured

"""

    # Add context for additional images
    if additional_images and len(additional_images) > 0:
        prompt += f"""
3. ADDITIONAL CONTEXT IMAGES ({len(additional_images)} provided):
   - These provide additional context (venue, mood, atmosphere)
   - Use these to enhance the visual storytelling
   - Incorporate relevant elements from these images

"""

    prompt += """
Your task:
1. Create a NEW flyer that:
   - Uses the template's layout and composition as the foundation
   - Matches the template's color scheme and visual style
   - Replaces text content with the event details above
   - Incorporates the artist/performer images prominently
   - Blends all visual elements cohesively
   - Maintains professional design standards

2. Design principles:
   - The flyer should look like it came from the template's designer
   - Artist photos should be integrated naturally (not just pasted on)
   - All text should be legible and well-positioned
   - Composition should be balanced and eye-catching
   - Optimize for social media sharing (Instagram/Facebook)

Output: A high-quality event poster that combines the template style with the artist imagery.
"""

    # Add template instructions if available
    if template.prompt_instructions:
        prompt += f"\n\nTEMPLATE STYLE INSTRUCTIONS:\n{template.prompt_instructions}"

    if prompt_overrides:
        prompt += f"\n\nADDITIONAL REQUIREMENTS:\n{prompt_overrides}"

    # Call image generation API with multiple reference images
    try:
        # Collect all images to send
        reference_images = []

        # 1. Template image (primary style reference)
        if template.image_url:
            template_data = download_image_as_base64(template.image_url)
            if template_data:
                reference_images.append({
                    "type": "template",
                    "data": template_data,
                    "description": "Layout and style reference"
                })

        # 2. Artist images
        if artist_images:
            for i, artist_url in enumerate(artist_images[:3]):  # Limit to 3 artist images
                artist_data = download_image_as_base64(artist_url)
                if artist_data:
                    reference_images.append({
                        "type": "artist",
                        "data": artist_data,
                        "description": f"Artist/performer #{i+1}"
                    })

        # 3. Additional context images
        if additional_images:
            for i, img_url in enumerate(additional_images[:2]):  # Limit to 2 additional images
                img_data = download_image_as_base64(img_url)
                if img_data:
                    reference_images.append({
                        "type": "context",
                        "data": img_data,
                        "description": f"Context image #{i+1}"
                    })

        # Call Image Generation API (OpenRouter or NanoBanana)
        image_url = None

        if settings.image_generation_provider == "openrouter":
            # OpenRouter API format
            # Note: OpenRouter Flux doesn't support multiple reference images directly
            # Include image descriptions in prompt instead
            if reference_images:
                prompt += "\n\nReference Images Provided:"
                for img in reference_images:
                    prompt += f"\n- {img['description']}"

            openrouter_request = {
                "model": settings.flux_model,  # black-forest-labs/flux.2-pro
                "messages": [{"role": "user", "content": prompt}],
                "modalities": ["image"]
            }

            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=openrouter_request,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=180.0,
            )

            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return {"error": f"Image generation failed: {response.text}"}

            result = response.json()

            # Extract base64 image
            if result.get("choices") and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                images = message.get("images", [])
                if images and len(images) > 0:
                    image_data_url = images[0].get("image_url", {}).get("url")
                    if image_data_url:
                        # Import save function from flyer_template
                        from app.services.flyer_template import save_base64_image
                        image_url = save_base64_image(image_data_url, event.id, "flyer_enhanced")

        else:
            # NanoBanana API format (fallback)
            nano_request = {
                "prompt": prompt,
                "model": settings.flux_model,
                "image_size": "1024x1024",
                "num_images": 1,
            }

            if reference_images:
                nano_request["reference_images"] = [img["data"] for img in reference_images]
                nano_request["image_descriptions"] = [img["description"] for img in reference_images]

            response = httpx.post(
                settings.nanobanana_api_url,
                json=nano_request,
                headers={"Authorization": f"Bearer {settings.nanobanana_api_key}"},
                timeout=180.0,
            )

            if response.status_code != 200:
                logger.error(f"Image generation API error: {response.status_code} - {response.text}")
                return {"error": f"Image generation failed: {response.text}"}

            result = response.json()
            if result.get("images") and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]

        # Handle generated image
        if image_url:

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
                "reference_images_used": len(reference_images),
                "artist_images_count": len([r for r in reference_images if r["type"] == "artist"]),
                "message": f"Flyer generated using '{template.name}' template + {len(reference_images)} reference images!",
            }
        else:
            return {"error": "No image generated"}

    except Exception as e:
        logger.error(f"Error generating flyer with context: {e}", exc_info=True)
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
        logger.error(f"Error downloading image from {image_url}: {e}")
        return None


# Convenience function that uses event's existing fields
def generate_flyer_with_event_artists(
    db: Session,
    event_id: int,
    template_id: int,
    prompt_overrides: Optional[str] = None,
) -> dict:
    """
    Generate flyer using template + artist images from event fields.

    This looks for artist images in:
    - event.artist_image_url (if exists)
    - event.additional_images (if exists - JSON field)
    - event.description (parse for image URLs)

    Args:
        db: Database session
        event_id: Event to generate flyer for
        template_id: Template ID
        prompt_overrides: Additional AI instructions

    Returns:
        Generation result
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Extract artist images from event
    artist_images = []

    # Check if event has artist_image_url field (you'd need to add this column)
    if hasattr(event, 'artist_image_url') and event.artist_image_url:
        artist_images.append(event.artist_image_url)

    # Check if event has additional_images JSON field
    if hasattr(event, 'additional_images') and event.additional_images:
        try:
            import json
            images = json.loads(event.additional_images) if isinstance(event.additional_images, str) else event.additional_images
            artist_images.extend(images)
        except:
            pass

    # Use the enhanced generator
    return generate_flyer_with_context(
        db=db,
        event_id=event_id,
        template_id=template_id,
        artist_images=artist_images if artist_images else None,
        prompt_overrides=prompt_overrides,
    )
