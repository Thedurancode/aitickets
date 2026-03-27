"""Test Event Media Management System.

This script demonstrates the complete workflow:
1. Add media assets to an event
2. Review media collection
3. Generate flyer from all media
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Event
from app.services.event_media import (
    add_event_media,
    get_event_media,
    bulk_add_event_media,
    generate_flyer_from_event_media,
)


def test_event_media_workflow():
    """Test complete event media workflow."""
    db = SessionLocal()

    print("🎨 Testing Event Media Management System\n")

    # Get first event
    event = db.query(Event).first()
    if not event:
        print("❌ No events found. Create an event first.")
        return

    print(f"📅 Using Event: {event.name} (ID: {event.id})\n")

    # Step 1: Add individual media assets
    print("Step 1: Adding individual media assets...\n")

    media_assets = [
        {
            "media_type": "artist_photo",
            "media_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f",
            "label": "Main Artist - DJ Sunset"
        },
        {
            "media_type": "artist_photo",
            "media_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4",
            "label": "Supporting Artist - The Waves"
        },
    ]

    for asset in media_assets:
        result = add_event_media(
            db=db,
            event_id=event.id,
            **asset
        )
        if "error" in result:
            print(f"  ⚠️  Error: {result['error']}")
        else:
            print(f"  ✅ Added: {result['media']['media_type']} - {result['media']['label']}")

    # Step 2: Bulk add more media
    print("\nStep 2: Bulk adding logos and sponsors...\n")

    bulk_media = [
        {
            "media_type": "logo",
            "media_url": "https://images.unsplash.com/photo-1599305445671-ac291c95aaa9",
            "label": "Event Logo"
        },
        {
            "media_type": "venue_photo",
            "media_url": "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4",
            "label": "Outdoor Venue"
        },
        {
            "media_type": "sponsor_logo",
            "media_url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113",
            "label": "Sponsor: TechCorp"
        },
    ]

    result = bulk_add_event_media(
        db=db,
        event_id=event.id,
        media_items=bulk_media
    )

    if "error" in result:
        print(f"  ⚠️  Bulk add error: {result['error']}")
    else:
        print(f"  ✅ Bulk added {result['created_count']} media assets")
        if result.get('errors'):
            for error in result['errors']:
                print(f"  ⚠️  {error}")

    # Step 3: Review all media
    print("\nStep 3: Reviewing all media assets...\n")

    media_list = get_event_media(db=db, event_id=event.id)

    if "error" in media_list:
        print(f"  ❌ Error: {media_list['error']}")
    else:
        print(f"  📊 Total media assets: {media_list['total_media_count']}")
        print(f"\n  Media by type:")
        for media_type, items in media_list['media_by_type'].items():
            print(f"    {media_type}: {len(items)} items")
            for item in items:
                label = item['label'] or 'No label'
                print(f"      - {label}")

    # Step 4: Generate flyer from all media
    print("\n" + "="*60)
    print("Step 4: 🎨 Generating flyer from all media assets...")
    print("="*60 + "\n")

    # Check if we have templates
    from app.models import FlyerTemplate
    template = db.query(FlyerTemplate).first()

    if not template:
        print("⚠️  No flyer templates found. Run bulk_add_templates.py first.")
        print("   Skipping flyer generation.")
        db.close()
        return

    print(f"Using template: {template.name} (ID: {template.id})\n")

    # Note: This will make an actual API call to NanoBanana
    # Uncomment the lines below to test actual flyer generation
    # WARNING: This costs credits on your NanoBanana account!

    print("⚠️  ACTUAL FLYER GENERATION IS COMMENTED OUT")
    print("   To test real generation, uncomment lines in test_event_media.py")
    print("   This will consume NanoBanana credits!")

    # Uncomment below to test actual generation:
    """
    result = generate_flyer_from_event_media(
        db=db,
        event_id=event.id,
        template_id=template.id,
        prompt_overrides="Make this flyer vibrant and energetic. Feature both artists prominently. Include the venue atmosphere. Place sponsor logos at the bottom."
    )

    if "error" in result:
        print(f"\n❌ Flyer generation error: {result['error']}")
    else:
        print(f"\n✅ Flyer generated successfully!")
        print(f"   Image URL: {result['image_url']}")
        print(f"   Template: {result['template_name']}")
        print(f"   Media used: {result['media_used']['total_media_assets']} assets")
        print(f"     - Artist photos: {result['media_used']['artist_photos']}")
        print(f"     - Other images: {result['media_used']['other_images']}")
        print(f"\n   Event image_url updated: {event.image_url}")
    """

    print("\n" + "="*60)
    print("✅ Test workflow complete!")
    print("="*60)

    # Show summary
    print("\n📋 Summary:")
    print(f"   Event: {event.name}")
    print(f"   Total media assets: {media_list.get('total_media_count', 0)}")
    print(f"   Event has flyer: {'✅ Yes' if event.image_url else '❌ No'}")
    if event.image_url:
        print(f"   Flyer URL: {event.image_url}")

    db.close()


if __name__ == "__main__":
    test_event_media_workflow()
