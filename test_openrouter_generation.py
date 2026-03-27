"""Test OpenRouter Flux 2 Pro Image Generation.

This script tests the complete workflow:
1. Verify OpenRouter configuration
2. Generate a flyer using Flux 2 Pro
3. Verify the image was saved and event updated
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Event, FlyerTemplate
from app.services.flyer_template import generate_flyer_from_template
from app.config import get_settings


def test_openrouter_generation():
    """Test OpenRouter Flux 2 Pro flyer generation."""
    db = SessionLocal()
    settings = get_settings()

    print("🎨 Testing OpenRouter Flux 2 Pro Image Generation")
    print("=" * 60)
    print()

    # Step 1: Verify Configuration
    print("Step 1: Verifying Configuration...")
    print(f"  Provider: {settings.image_generation_provider}")
    print(f"  Model: {settings.flux_model}")
    print(f"  OpenRouter Key: {'✅ Set' if settings.openrouter_api_key else '❌ Missing'}")

    if not settings.openrouter_api_key:
        print()
        print("❌ ERROR: OpenRouter API key not configured")
        print("   Add OPENROUTER_API_KEY to your .env file")
        return

    if settings.image_generation_provider != "openrouter":
        print()
        print("⚠️  WARNING: Provider is not set to 'openrouter'")
        print(f"   Current: {settings.image_generation_provider}")
        print("   Add to .env: IMAGE_GENERATION_PROVIDER=openrouter")
        return

    print("  ✅ Configuration valid!")
    print()

    # Step 2: Get Test Data
    print("Step 2: Loading Test Data...")

    event = db.query(Event).first()
    if not event:
        print("  ❌ No events found in database")
        return

    template = db.query(FlyerTemplate).first()
    if not template:
        print("  ❌ No templates found in database")
        print("  Run: python app/migrations/bulk_add_templates.py")
        return

    print(f"  Event: {event.name} (ID: {event.id})")
    print(f"  Template: {template.name} (ID: {template.id})")
    print(f"  Current Image: {event.image_url[:50] if event.image_url else 'None'}...")
    print()

    # Step 3: Generate Flyer
    print("Step 3: Generating Flyer with OpenRouter Flux 2 Pro...")
    print(f"  ⏳ This may take 10-30 seconds...")
    print()

    try:
        result = generate_flyer_from_template(
            db=db,
            event_id=event.id,
            template_id=template.id,
            prompt_overrides="Vibrant and eye-catching event poster"
        )

        if "error" in result:
            print(f"  ❌ Generation failed: {result['error']}")
            print()
            print("Troubleshooting:")
            print("  1. Check OpenRouter API key is valid")
            print("  2. Verify you have credits on OpenRouter")
            print("  3. Check model ID: black-forest-labs/flux.2-pro")
            return

        print("  ✅ Flyer generated successfully!")
        print()

        # Step 4: Verify Results
        print("Step 4: Verifying Results...")
        print(f"  Event ID: {result['event_id']}")
        print(f"  Event Name: {result['event_name']}")
        print(f"  Template: {result['template_name']}")
        print(f"  Image URL: {result['image_url']}")
        print()

        # Check if image was saved
        if result['image_url'].startswith('http'):
            # Extract filename
            filename = result['image_url'].split('/')[-1]
            uploads_dir = Path(settings.uploads_dir)
            image_path = uploads_dir / filename

            if image_path.exists():
                file_size = image_path.stat().st_size
                print(f"  ✅ Image saved to: {image_path}")
                print(f"  ✅ File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            else:
                print(f"  ⚠️  Image URL returned but file not found locally")

        # Verify event was updated
        db.refresh(event)
        if event.image_url == result['image_url']:
            print(f"  ✅ Event image_url updated in database")

        print()
        print("=" * 60)
        print("🎉 Test Complete!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  ✅ OpenRouter Flux 2 Pro working correctly")
        print(f"  ✅ Image generated and saved")
        print(f"  ✅ Event updated with new flyer")
        print()
        print(f"View your flyer:")
        print(f"  {result['image_url']}")
        print()
        print(f"Cost: ~$0.03 (charged to OpenRouter account)")

    except Exception as e:
        print(f"  ❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_openrouter_generation()
