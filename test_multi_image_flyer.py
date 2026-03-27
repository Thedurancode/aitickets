"""Test script for multi-image flyer generation.

Demonstrates:
1. Adding artist images to an event
2. Generating flyer with template + artist photos
3. Comparing single-image vs multi-image results
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_add_artist_images():
    """Add artist images to an event."""
    event_id = 1  # Change to your event ID

    payload = {
        "artist_image_url": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800",
        "additional_images": [
            "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800",
            "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800"
        ],
        "performer_names": ["DJ Headliner", "Supporting Act"]
    }

    response = requests.put(
        f"{BASE_URL}/api/flyer-templates-enhanced/events/{event_id}/images",
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Added artist images to event {event_id}")
        print(f"   Artist image: {result.get('artist_image_url', 'N/A')[:50]}...")
        print(f"   Additional images: {len(result.get('additional_images', []))}")
        return True
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return False


def test_generate_multi_image_flyer():
    """Generate flyer with multiple image references."""
    event_id = 1  # Change to your event ID
    template_id = 1  # Change to your template ID

    payload = {
        "template_id": template_id,
        "artist_images": [
            "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800"
        ],
        "additional_images": [
            "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800"
        ],
        "prompt_overrides": "Make the artist photo prominent with vibrant neon colors"
    }

    print(f"\n🎨 Generating flyer with:")
    print(f"   Template: #{template_id}")
    print(f"   Artist images: {len(payload['artist_images'])}")
    print(f"   Additional images: {len(payload['additional_images'])}")

    response = requests.post(
        f"{BASE_URL}/api/flyer-templates-enhanced/events/{event_id}/generate",
        json=payload,
        timeout=180  # Long timeout for image generation
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Flyer generated!")
        print(f"   Event: {result['event_name']}")
        print(f"   Template: {result['template_name']}")
        print(f"   Reference images used: {result['reference_images_used']}")
        print(f"   Artist images: {result['artist_images_count']}")
        print(f"   Image URL: {result['image_url']}")
        return result
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None


def test_auto_generate():
    """Test auto-detection of images from event fields."""
    event_id = 1
    template_id = 1

    print(f"\n🤖 Auto-generating flyer (detecting images from event)...")

    response = requests.post(
        f"{BASE_URL}/api/flyer-templates-enhanced/events/{event_id}/generate-auto",
        params={"template_id": template_id},
        timeout=180
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Auto-generated successfully!")
        print(f"   Used {result['reference_images_used']} reference images")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None


def test_get_event_images():
    """Get all images for an event."""
    event_id = 1

    response = requests.get(
        f"{BASE_URL}/api/flyer-templates-enhanced/events/{event_id}/images"
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n📸 Event {event_id} images:")
        print(f"   Event flyer: {result.get('event_image_url', 'None')[:50]}...")
        print(f"   Artist image: {result.get('artist_image_url', 'None')[:50]}...")
        print(f"   Additional images: {len(result.get('additional_images', []))}")
        print(f"   Performers: {result.get('performer_names', [])}")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None


if __name__ == "__main__":
    print("🧪 Testing Multi-Image Flyer Generation\n")
    print("=" * 70)

    print("\n📋 Prerequisites:")
    print("   1. Server running: make api")
    print("   2. Migration run: python app/migrations/add_artist_images.py")
    print("   3. Enhanced router added to main.py")
    print("   4. At least one event and template in database")

    input("\nPress Enter to continue (or Ctrl+C to cancel)...")

    # Test 1: Add artist images
    print("\n1️⃣  Adding Artist Images to Event")
    print("-" * 70)
    test_add_artist_images()

    # Test 2: Get event images
    print("\n2️⃣  Retrieving Event Images")
    print("-" * 70)
    test_get_event_images()

    # Test 3: Generate with explicit images
    print("\n3️⃣  Generate Flyer (Explicit Images)")
    print("-" * 70)
    test_generate_multi_image_flyer()

    # Test 4: Auto-generate
    print("\n4️⃣  Generate Flyer (Auto-Detect)")
    print("-" * 70)
    test_auto_generate()

    print("\n" + "=" * 70)
    print("✨ Tests Complete!")
    print("\n💡 Next steps:")
    print("   - Try different templates")
    print("   - Experiment with prompt_overrides")
    print("   - Compare single-image vs multi-image results")
