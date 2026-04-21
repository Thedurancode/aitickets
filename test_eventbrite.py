#!/usr/bin/env python3
"""
Test EventBrite Integration
Tests the EventBrite API connection and publishes the Peru Chicken event
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
import json

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal
from app.config import get_settings
from app.models import Event
from app.services.event_publisher import EventPublisher, get_available_platforms


def test_eventbrite_auth():
    """Test EventBrite authentication"""
    settings = get_settings()

    print("=" * 60)
    print("TESTING EVENTBRITE CONNECTION")
    print("=" * 60)

    # Check if credentials are configured
    print("\n1. Checking configuration...")
    if not settings.eventbrite_api_key:
        print("❌ EVENTBRITE_API_KEY not configured")
        return False
    else:
        print(f"✅ API Key configured: {settings.eventbrite_api_key[:10]}...")

    if not settings.eventbrite_organization_id or settings.eventbrite_organization_id == "YOUR_ORG_ID_HERE":
        print("⚠️  EVENTBRITE_ORGANIZATION_ID not configured (will attempt to fetch)")
        need_org_id = True
    else:
        print(f"✅ Organization ID configured: {settings.eventbrite_organization_id}")
        need_org_id = False

    # Test API connection - Get user info
    print("\n2. Testing API authentication...")
    try:
        response = requests.get(
            "https://www.eventbriteapi.com/v3/users/me/",
            headers={
                "Authorization": f"Bearer {settings.eventbrite_api_key}",
            },
            timeout=10
        )

        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Authentication successful!")
            print(f"   User: {user_data.get('name', 'N/A')}")
            print(f"   Email: {user_data.get('emails', [{}])[0].get('email', 'N/A')}")
            print(f"   ID: {user_data.get('id', 'N/A')}")
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

    # Get organizations if needed
    if need_org_id:
        print("\n3. Fetching organization ID...")
        try:
            response = requests.get(
                "https://www.eventbriteapi.com/v3/users/me/organizations/",
                headers={
                    "Authorization": f"Bearer {settings.eventbrite_api_key}",
                },
                timeout=10
            )

            if response.status_code == 200:
                orgs_data = response.json()
                organizations = orgs_data.get('organizations', [])

                if organizations:
                    org = organizations[0]  # Use first org
                    org_id = org.get('id')
                    print(f"✅ Found organization: {org.get('name')} (ID: {org_id})")
                    print(f"\n   ⚠️  Please add this to your .env file:")
                    print(f"   EVENTBRITE_ORGANIZATION_ID={org_id}")

                    # Temporarily set it for this session
                    settings.eventbrite_organization_id = org_id
                else:
                    print("❌ No organizations found. You may need to create one on EventBrite.")
                    return False
            else:
                print(f"❌ Failed to fetch organizations: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error fetching organizations: {str(e)}")
            return False

    return True


def publish_peru_chicken_to_eventbrite():
    """Publish the Peru Chicken event to EventBrite"""

    print("\n" + "=" * 60)
    print("PUBLISHING PERU CHICKEN EVENT TO EVENTBRITE")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Find the Peru Chicken event
        print("\n1. Finding Peru Chicken event...")
        event = db.query(Event).filter(
            Event.name.like("%Peru%Chicken%")
        ).first()

        if not event:
            event = db.query(Event).filter(
                Event.name.like("%Peruvian%Brunch%")
            ).first()

        if not event:
            print("❌ Peru Chicken event not found in database")
            print("   Run 'python add_brunch_event.py' first to create it")
            return False

        print(f"✅ Found event: {event.name} (ID: {event.id})")

        # Check available platforms
        print("\n2. Checking platform configuration...")
        platforms = get_available_platforms()
        eventbrite_platform = next((p for p in platforms if p['id'] == 'eventbrite'), None)

        if eventbrite_platform:
            if eventbrite_platform['configured']:
                print("✅ EventBrite is configured and ready")
            else:
                print("⚠️  EventBrite not fully configured")
                print(f"   Required: {', '.join(eventbrite_platform['requires'])}")

        # Publish to EventBrite
        print("\n3. Publishing to EventBrite...")
        publisher = EventPublisher(db, event.id)
        result = publisher.publish_to_eventbrite()

        if result['success']:
            print("✅ Successfully published to EventBrite!")
            print(f"   EventBrite Event ID: {result.get('event_id', 'N/A')}")
            print(f"   Event URL: {result.get('event_url', 'N/A')}")
            print(f"   Ticket Tiers Created: {result.get('ticket_tiers_created', 0)}")

            if result.get('tiers'):
                print("\n   Ticket Tiers:")
                for tier in result['tiers']:
                    print(f"   - {tier['tier_name']}: ID {tier.get('eventbrite_ticket_class_id', 'N/A')}")
        else:
            print(f"❌ Failed to publish: {result.get('error', 'Unknown error')}")
            if result.get('details'):
                print(f"   Details: {json.dumps(result['details'], indent=2)}")
            if result.get('setup_url'):
                print(f"   Setup Guide: {result['setup_url']}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True


def main():
    """Main test function"""

    # Test authentication first
    if test_eventbrite_auth():
        print("\n✅ EventBrite authentication test passed!\n")

        # Ask if user wants to publish
        print("Would you like to publish the Peru Chicken event to EventBrite?")
        print("Note: This will create a real event on EventBrite.")
        response = input("Continue? (y/n): ").lower().strip()

        if response == 'y':
            if publish_peru_chicken_to_eventbrite():
                print("\n🎉 SUCCESS! Event published to EventBrite!")
            else:
                print("\n❌ Failed to publish event")
        else:
            print("\nSkipping event publishing.")
    else:
        print("\n❌ EventBrite authentication test failed")
        print("\nPlease check your EventBrite API credentials in .env file")


if __name__ == "__main__":
    main()