"""Interactive script to add custom flyer templates.

Usage:
    python add_custom_template.py

Or add directly via API:
    curl -X POST http://localhost:8000/api/flyer-templates/ \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Your Template Name",
        "description": "Template description",
        "image_url": "https://example.com/template.png",
        "thumbnail_url": "https://example.com/thumb.png",
        "prompt_instructions": "AI generation instructions"
      }'
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


def add_template_interactive():
    """Interactive template addition."""
    print("🎨 Add Custom Flyer Template\n")
    print("=" * 70)

    # Collect template info
    name = input("\n📝 Template name: ").strip()
    if not name:
        print("❌ Name is required!")
        return

    description = input("📄 Description: ").strip()
    if not description:
        print("❌ Description is required!")
        return

    image_url = input("🖼️  Image URL: ").strip()
    if not image_url:
        print("❌ Image URL is required!")
        return

    thumbnail_url = input("🖼️  Thumbnail URL (optional, press Enter to skip): ").strip()
    prompt_instructions = input("🤖 AI prompt instructions (optional): ").strip()
    created_by = input("👤 Created by (optional): ").strip() or "Custom"

    # Confirm
    print("\n" + "=" * 70)
    print("Preview:")
    print(f"  Name: {name}")
    print(f"  Description: {description}")
    print(f"  Image: {image_url}")
    print(f"  Thumbnail: {thumbnail_url or 'None'}")
    print(f"  Instructions: {prompt_instructions or 'None'}")
    print(f"  Created by: {created_by}")
    print("=" * 70)

    confirm = input("\n✅ Add this template? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return

    # Add to database
    db: Session = SessionLocal()
    try:
        # Check if exists
        existing = db.query(FlyerTemplate).filter(FlyerTemplate.name == name).first()
        if existing:
            print(f"❌ Template '{name}' already exists!")
            return

        template = FlyerTemplate(
            name=name,
            description=description,
            image_url=image_url,
            thumbnail_url=thumbnail_url if thumbnail_url else None,
            prompt_instructions=prompt_instructions if prompt_instructions else None,
            created_by=created_by,
            times_used=0,
            created_at=utcnow(),
            updated_at=utcnow(),
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        print(f"\n✅ Template '{name}' added successfully!")
        print(f"   ID: {template.id}")
        print(f"   Total templates: {db.query(FlyerTemplate).count()}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


def add_template_direct(name, description, image_url, thumbnail_url=None, prompt_instructions=None, created_by="Direct"):
    """Add template directly without prompts."""
    db: Session = SessionLocal()
    try:
        existing = db.query(FlyerTemplate).filter(FlyerTemplate.name == name).first()
        if existing:
            print(f"⏭️  Template '{name}' already exists")
            return existing.id

        template = FlyerTemplate(
            name=name,
            description=description,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            prompt_instructions=prompt_instructions,
            created_by=created_by,
            times_used=0,
            created_at=utcnow(),
            updated_at=utcnow(),
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        print(f"✅ Added '{name}' (ID: {template.id})")
        return template.id

    except Exception as e:
        db.rollback()
        print(f"❌ Error adding '{name}': {e}")
        return None
    finally:
        db.close()


if __name__ == "__main__":
    # Check for command-line mode
    if len(sys.argv) > 1 and sys.argv[1] == "--example":
        # Add example templates
        print("🎨 Adding Example Templates...\n")

        add_template_direct(
            name="Retro 80s Synthwave",
            description="Retro 80s aesthetic with neon grids and sunset gradients. Perfect for synthwave concerts and nostalgic events.",
            image_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800",
            thumbnail_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400",
            prompt_instructions="80s retro style with pink/purple sunset gradients, neon grids, and futuristic fonts. Include palm trees or retro tech imagery.",
            created_by="Examples"
        )

        add_template_direct(
            name="Kids Birthday Party",
            description="Fun, colorful design with playful elements. Great for children's birthday parties and family events.",
            image_url="https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800",
            thumbnail_url="https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400",
            prompt_instructions="Bright, fun colors (rainbow palette). Playful rounded fonts. Include balloons, confetti, or cartoon elements.",
            created_by="Examples"
        )

        print("\n✨ Example templates added!")
    else:
        # Interactive mode
        add_template_interactive()
