"""Bulk add flyer templates to the database.

This script adds a curated collection of flyer templates
that can be used for AI-powered event flyer generation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import FlyerTemplate
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


# Template data - Add your own templates here!
TEMPLATES = [
    {
        "name": "Neon Nights",
        "description": "Bold neon colors with geometric shapes. Perfect for electronic music events, nightclubs, and modern concerts.",
        "image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400",
        "prompt_instructions": "Use vibrant neon pink, blue, and purple colors. Include geometric shapes and angular typography. High contrast dark background.",
    },
    {
        "name": "Vintage Jazz",
        "description": "Classic art deco style with gold accents. Ideal for jazz nights, vintage events, and sophisticated gatherings.",
        "image_url": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400",
        "prompt_instructions": "Art deco style with gold and black color scheme. Elegant serif fonts. Ornate decorative elements.",
    },
    {
        "name": "Summer Festival",
        "description": "Bright, energetic design with sunshine vibes. Great for outdoor festivals, summer concerts, and daytime events.",
        "image_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=400",
        "prompt_instructions": "Bright yellow, orange, and warm colors. Playful, energetic typography. Sun, palm trees, and tropical elements.",
    },
    {
        "name": "Minimal Modern",
        "description": "Clean, contemporary design with lots of white space. Perfect for corporate events, galleries, and upscale occasions.",
        "image_url": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400",
        "prompt_instructions": "Minimal design with lots of white space. Sans-serif fonts. Clean lines and simple color palette (black, white, one accent color).",
    },
    {
        "name": "Rock Concert",
        "description": "Edgy, high-energy design with bold typography. Ideal for rock concerts, alternative music, and high-energy events.",
        "image_url": "https://images.unsplash.com/photo-1498038432885-c6f3f1b912ee?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1498038432885-c6f3f1b912ee?w=400",
        "prompt_instructions": "Bold, aggressive typography. Dark backgrounds with red or orange accents. Grungy textures and high contrast.",
    },
    {
        "name": "Hip Hop Block Party",
        "description": "Urban street style with graffiti elements. Perfect for hip hop events, street festivals, and urban gatherings.",
        "image_url": "https://images.unsplash.com/photo-1571609166008-e6c0e5e4db49?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1571609166008-e6c0e5e4db49?w=400",
        "prompt_instructions": "Urban street style with graffiti-inspired fonts. Bright colors (yellow, red, blue). Spray paint textures and bold graphics.",
    },
    {
        "name": "Sports Championship",
        "description": "Athletic, competitive design with team colors. Great for sports events, tournaments, and athletic competitions.",
        "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400",
        "prompt_instructions": "Bold athletic typography. Team colors and dynamic action poses. Sharp angles and competitive energy.",
    },
    {
        "name": "Comedy Night",
        "description": "Fun, playful design with humorous elements. Perfect for comedy shows, open mics, and entertainment events.",
        "image_url": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400",
        "prompt_instructions": "Playful, fun typography with curved letters. Bright, cheerful colors. Include microphone or comedy-related imagery.",
    },
    {
        "name": "Elegant Gala",
        "description": "Sophisticated black-tie design with luxury accents. Ideal for galas, fundraisers, and formal events.",
        "image_url": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=400",
        "prompt_instructions": "Elegant serif fonts. Gold, black, and white color scheme. Luxurious and sophisticated design elements.",
    },
    {
        "name": "Food & Wine",
        "description": "Refined culinary design with appetizing visuals. Great for food festivals, wine tastings, and dining events.",
        "image_url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400",
        "prompt_instructions": "Warm, appetizing colors (browns, golds, reds). Classic serif fonts. Food and wine imagery with elegant styling.",
    },
    {
        "name": "Halloween Horror",
        "description": "Spooky, atmospheric design with dark themes. Perfect for Halloween parties, horror events, and themed nights.",
        "image_url": "https://images.unsplash.com/photo-1509557965875-b88c97052f0e?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1509557965875-b88c97052f0e?w=400",
        "prompt_instructions": "Dark, spooky design with orange and black. Gothic or horror-style fonts. Includes spooky elements like skulls, pumpkins, or ghosts.",
    },
    {
        "name": "Holiday Celebration",
        "description": "Festive design with seasonal colors and joy. Great for Christmas parties, New Year's Eve, and holiday events.",
        "image_url": "https://images.unsplash.com/photo-1482517967863-00e15c9b44be?w=800",
        "thumbnail_url": "https://images.unsplash.com/photo-1482517967863-00e15c9b44be?w=400",
        "prompt_instructions": "Festive colors (red, green, gold). Celebratory typography. Holiday-themed elements like snowflakes, ornaments, or lights.",
    },
]


def bulk_add_templates():
    """Add all templates to the database."""
    db: Session = SessionLocal()

    try:
        added = 0
        skipped = 0

        for template_data in TEMPLATES:
            # Check if template already exists
            existing = db.query(FlyerTemplate).filter(
                FlyerTemplate.name == template_data["name"]
            ).first()

            if existing:
                print(f"⏭️  Skipping '{template_data['name']}' - already exists")
                skipped += 1
                continue

            # Create new template
            template = FlyerTemplate(
                name=template_data["name"],
                description=template_data["description"],
                image_url=template_data["image_url"],
                thumbnail_url=template_data.get("thumbnail_url"),
                prompt_instructions=template_data.get("prompt_instructions"),
                created_by="System",
                times_used=0,
                created_at=utcnow(),
                updated_at=utcnow(),
            )

            db.add(template)
            print(f"✅ Added '{template_data['name']}'")
            added += 1

        db.commit()

        print(f"\n📊 Summary:")
        print(f"   Added: {added}")
        print(f"   Skipped: {skipped}")
        print(f"   Total templates in DB: {db.query(FlyerTemplate).count()}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🎨 Bulk Adding Flyer Templates...\n")
    bulk_add_templates()
    print("\n✨ Done!")
