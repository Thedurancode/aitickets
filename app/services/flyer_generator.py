"""AI event flyer generation via Google Gemini (NanoBanana API)."""

import logging
import uuid
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def build_flyer_prompt(
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: Optional[str] = None,
    venue_address: Optional[str] = None,
    description: Optional[str] = None,
    tiers: Optional[list[dict]] = None,
    org_name: Optional[str] = None,
    style_instructions: Optional[str] = None,
) -> str:
    """Construct image-generation prompt from event data."""
    lines = [
        "Create a professional, eye-catching event flyer for:",
        f"Event: {event_name}",
        f"Date: {event_date}",
        f"Time: {event_time}",
    ]
    if venue_name:
        lines.append(f"Venue: {venue_name}")
    if venue_address:
        lines.append(f"Address: {venue_address}")
    if description:
        desc = description[:300]
        if len(description) > 300:
            desc += "..."
        lines.append(f"Description: {desc}")
    if tiers:
        tier_strs = []
        for t in tiers[:5]:
            price = t.get("price", 0)
            price_str = f"${price / 100:.2f}" if price else "Free"
            tier_strs.append(f"  - {t['name']}: {price_str}")
        lines.append("Ticket Tiers:")
        lines.extend(tier_strs)
    if org_name:
        lines.append(f"Presented by: {org_name}")

    lines.append("")
    lines.append(
        "Design requirements: Modern, bold typography. High contrast. "
        "Include all event details legibly. Portrait orientation suitable "
        "for social media and print."
    )

    if style_instructions:
        lines.append(f"Style guidance: {style_instructions}")

    return "\n".join(lines)


def generate_flyer(
    prompt: str,
    uploads_dir: Optional[str] = None,
    reference_image_path: Optional[str] = None,
) -> dict:
    """Call Gemini to generate a flyer image and save it to uploads/.

    Args:
        prompt: The text prompt describing the flyer.
        uploads_dir: Directory to save the generated image.
        reference_image_path: Optional path to a reference style image.
            When provided, the image is sent to Gemini as multi-modal
            input so it uses it as a visual style example.
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        return {"success": False, "error": "Gemini API key not configured (set GEMINI_API_KEY)"}

    try:
        from google import genai
    except ImportError:
        return {"success": False, "error": "google-genai package is not installed"}

    if uploads_dir is None:
        uploads_dir = settings.uploads_dir

    uploads_path = Path(uploads_dir)
    uploads_path.mkdir(exist_ok=True)

    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options={"headers": {"Referer": settings.base_url}},
        )

        contents = [prompt]
        if reference_image_path:
            from PIL import Image
            ref_path = Path(reference_image_path)
            if ref_path.exists():
                contents.append(Image.open(ref_path))

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents,
        )

        filename = f"flyer_{uuid.uuid4().hex}.png"
        file_path = uploads_path / filename

        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                image.save(str(file_path))
                return {
                    "success": True,
                    "filename": filename,
                    "image_url": f"/uploads/{filename}",
                }

        return {
            "success": False,
            "error": "Gemini returned no image data. The prompt may have been rejected.",
        }

    except Exception as e:
        logger.exception("Flyer generation failed")
        return {"success": False, "error": f"Flyer generation failed: {str(e)}"}
