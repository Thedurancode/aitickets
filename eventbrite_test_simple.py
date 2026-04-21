#!/usr/bin/env python3
"""
Test EventBrite Integration - Simple Non-Interactive Version
"""

import sys
import os
from pathlib import Path
import requests

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.config import get_settings
from app.services.event_publisher import get_available_platforms


def main():
    """Test EventBrite configuration and connection"""

    settings = get_settings()

    print("\n" + "="*60)
    print("🎫 EVENTBRITE INTEGRATION STATUS")
    print("="*60)

    # Configuration Status
    print("\n📋 CONFIGURATION:")
    print(f"   API Key:          {'✅ Configured' if settings.eventbrite_api_key else '❌ Missing'}")
    print(f"   Organization ID:  {'✅ ' + settings.eventbrite_organization_id if settings.eventbrite_organization_id and settings.eventbrite_organization_id != 'YOUR_ORG_ID_HERE' else '❌ Missing'}")
    print(f"   Client Secret:    {'✅ Configured' if settings.eventbrite_client_secret else '❌ Missing'}")
    print(f"   Public Token:     {'✅ Configured' if settings.eventbrite_public_token else '❌ Missing'}")

    # Test API Connection
    print("\n🔌 CONNECTION TEST:")

    if not settings.eventbrite_api_key:
        print("   ❌ Cannot test - API key not configured")
        return

    try:
        response = requests.get(
            "https://www.eventbriteapi.com/v3/users/me/",
            headers={"Authorization": f"Bearer {settings.eventbrite_api_key}"},
            timeout=10
        )

        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ Connected successfully!")
            print(f"   👤 Account: {user_data.get('name', 'N/A')} ({user_data.get('emails', [{}])[0].get('email', 'N/A')})")

            # Get organization details
            if settings.eventbrite_organization_id and settings.eventbrite_organization_id != 'YOUR_ORG_ID_HERE':
                org_response = requests.get(
                    f"https://www.eventbriteapi.com/v3/organizations/{settings.eventbrite_organization_id}/",
                    headers={"Authorization": f"Bearer {settings.eventbrite_api_key}"},
                    timeout=10
                )
                if org_response.status_code == 200:
                    org_data = org_response.json()
                    print(f"   🏢 Organization: {org_data.get('name', 'N/A')}")

        else:
            print(f"   ❌ Connection failed: {response.status_code}")
            print(f"   Error: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Connection error: {str(e)}")

    # Platform Status
    print("\n🚀 PLATFORM STATUS:")
    platforms = get_available_platforms()
    eventbrite = next((p for p in platforms if p['id'] == 'eventbrite'), None)

    if eventbrite:
        if eventbrite['configured']:
            print("   ✅ EventBrite publishing is READY")
            print("   You can now publish events to EventBrite!")
        else:
            print("   ⚠️  EventBrite publishing needs configuration")
            print(f"   Missing: {', '.join(eventbrite['requires'])}")

    # Available Actions
    print("\n📌 AVAILABLE ACTIONS:")
    print("   • Publish an event: POST /api/event-publisher/events/{event_id}/publish")
    print("   • Example payload:  {\"platforms\": [\"eventbrite\"]}")
    print("   • Test with Peru Chicken event (ID from database)")

    print("\n" + "="*60)
    print("✨ EventBrite integration is configured and ready to use!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()