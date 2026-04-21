#!/usr/bin/env python3
"""
Test Google My Business Publishing
"""

import sys
import os
from pathlib import Path
import json

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal
from app.config import get_settings
from app.models import Event
from app.services.event_publisher import EventPublisher, get_available_platforms


def main():
    """Test Google My Business publishing"""

    print("\n" + "="*70)
    print("🌟 TESTING GOOGLE MY BUSINESS PUBLISHING")
    print("="*70)

    settings = get_settings()
    db = SessionLocal()

    try:
        # 1. Check GMB configuration
        print("\n1️⃣ CHECKING CONFIGURATION")
        print("-" * 40)

        gmb_configured = bool(
            getattr(settings, 'google_client_id', None) and
            getattr(settings, 'google_refresh_token', None)
        )

        print(f"Google Client ID: {'✅ Set' if getattr(settings, 'google_client_id', None) else '❌ Missing'}")
        print(f"Google Client Secret: {'✅ Set' if getattr(settings, 'google_client_secret', None) else '❌ Missing'}")
        print(f"Google Refresh Token: {'✅ Set' if getattr(settings, 'google_refresh_token', None) else '❌ Missing'}")
        print(f"Google Location ID: {'✅ Set' if getattr(settings, 'google_location_id', None) else '⚠️  Optional (auto-detect)'}")

        print(f"\nOverall Status: {'✅ READY' if gmb_configured else '❌ NOT CONFIGURED'}")

        # 2. Check platform status
        print("\n2️⃣ PLATFORM STATUS")
        print("-" * 40)

        platforms = get_available_platforms()
        gmb_platform = next((p for p in platforms if p['id'] == 'google_my_business'), None)

        if gmb_platform:
            print(f"Platform Name: {gmb_platform['name']}")
            print(f"Configured: {'✅ Yes' if gmb_platform['configured'] else '❌ No'}")
            print(f"Requirements: {', '.join(gmb_platform['requires'])}")
            print(f"Docs: {gmb_platform.get('docs_url', 'N/A')}")

        # 3. Find Peru Chicken event
        print("\n3️⃣ FINDING PERU CHICKEN EVENT")
        print("-" * 40)

        event = db.query(Event).filter(
            Event.name.like("%Peruvian%Brunch%")
        ).first()

        if not event:
            print("❌ Peru Chicken event not found!")
            return

        print(f"✅ Event: {event.name}")
        print(f"   ID: {event.id}")
        print(f"   Date: {event.event_date}")
        print(f"   Time: {event.event_time}")
        if event.venue:
            print(f"   Venue: {event.venue.name}")
            print(f"   Address: {event.venue.address}")

        # 4. Test GMB publishing
        print("\n4️⃣ TESTING GMB PUBLISH")
        print("-" * 40)

        if not gmb_configured:
            print("\n⚠️  GMB not configured - showing what WOULD happen:\n")

        publisher = EventPublisher(db, event.id)
        result = publisher.publish_to_google_my_business()

        print("Result:")
        print(json.dumps(result, indent=2))

        if result.get('success'):
            print("\n✅ SUCCESS! Event would be published to:")
            print("   • Google Search results")
            print("   • Google Maps listing")
            print("   • Google Business Profile")
            print("   • Local search results")
        else:
            print(f"\n❌ Not published: {result.get('error', 'Unknown error')}")

            if 'setup_instructions' in result:
                instructions = result['setup_instructions']
                print("\n📋 SETUP INSTRUCTIONS:")
                print("-" * 40)
                for step in instructions.get('steps', []):
                    print(f"   {step}")

                print("\n📝 Required Environment Variables:")
                for var in instructions.get('required_env_vars', []):
                    print(f"   • {var}")

                print("\n✨ Benefits:")
                for benefit in instructions.get('benefits', []):
                    print(f"   • {benefit}")

        # 5. Show example of what would appear
        print("\n5️⃣ WHAT WOULD APPEAR ON GOOGLE")
        print("-" * 40)

        print(f"""
When published, this event would appear as:

📍 On Google Maps:
   Peru Chicken
   360 US-206, Hillsborough, NJ
   ⭐⭐⭐⭐⭐ (4.8) • Peruvian Restaurant

   📅 UPCOMING EVENT
   Mother's Day Weekend Peruvian Brunch
   {event.event_date} at {event.event_time}
   Starting at $55
   [Book Now] [Learn More]

🔍 In Google Search:
   When searching "Peru Chicken" or "brunch near me":

   Peru Chicken - Hillsborough
   Special Event: Mother's Day Brunch
   📅 {event.event_date} • 📍 360 US-206
   🎫 Book tickets online • Starting at $55

📱 On Mobile (90% of local searches):
   Shows prominently with:
   - Event photo
   - Quick booking button
   - Get directions
   - Call restaurant
   - Share with friends
        """)

        # 6. Multi-platform test
        print("\n6️⃣ MULTI-PLATFORM PUBLISHING TEST")
        print("-" * 40)

        print("Testing all configured platforms...")
        all_results = publisher.publish_to_all(platforms=["eventbrite", "google_my_business", "calendar"])

        for platform, result in all_results.items():
            status = "✅" if result.get('success') else "❌"
            print(f"{status} {platform}: {result.get('message', result.get('error', 'N/A'))}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "="*70)
    print("💡 NEXT STEPS")
    print("="*70)

    if not gmb_configured:
        print("""
To enable Google My Business:

1. Run the setup wizard:
   python3 setup_google_my_business.py

2. Follow the OAuth flow to get credentials

3. Add to .env:
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REFRESH_TOKEN=your_refresh_token

4. Test again with this script!
        """)
    else:
        print("""
GMB is configured! You can now:

1. Publish individual events:
   POST /api/event-publisher/events/{id}/publish
   {"platforms": ["google_my_business"]}

2. Publish to all platforms:
   {"platforms": null}

3. Check event visibility on Google Maps/Search
        """)

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()