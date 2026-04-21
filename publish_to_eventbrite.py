#!/usr/bin/env python3
"""
Publish Peru Chicken Event to EventBrite
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal
from app.models import Event
from app.services.event_publisher import EventPublisher
from app.config import get_settings


def main():
    """Find and publish Peru Chicken event to EventBrite"""

    print("\n" + "="*60)
    print("🎫 PUBLISHING PERU CHICKEN EVENT TO EVENTBRITE")
    print("="*60)

    db = SessionLocal()

    try:
        # 1. Find the Peru Chicken event
        print("\n1️⃣ Finding Peru Chicken event in database...")

        event = db.query(Event).filter(
            Event.name.like("%Peruvian%Brunch%")
        ).first()

        if not event:
            event = db.query(Event).filter(
                Event.name.like("%Peru%")
            ).first()

        if not event:
            print("❌ Peru Chicken event not found!")
            print("   Run 'python add_brunch_event.py' first")
            return

        print(f"✅ Found event: {event.name}")
        print(f"   Event ID: {event.id}")
        print(f"   Date: {event.event_date}")
        print(f"   Time: {event.event_time}")
        if event.venue:
            print(f"   Venue: {event.venue.name}")
            print(f"   Address: {event.venue.address}")

        # 2. Check current EventBrite status
        print(f"\n2️⃣ Checking EventBrite status...")

        if hasattr(event, 'eventbrite_id') and event.eventbrite_id:
            print(f"⚠️  Event already published to EventBrite!")
            print(f"   EventBrite ID: {event.eventbrite_id}")
            if hasattr(event, 'eventbrite_url') and event.eventbrite_url:
                print(f"   URL: {event.eventbrite_url}")
            print("\n   Do you want to publish it again as a NEW event? (y/n)")
            # For non-interactive, we'll skip
            print("   Skipping to avoid duplicates...")
            return
        else:
            print("✅ Event not yet published to EventBrite")

        # 3. Publish to EventBrite
        print(f"\n3️⃣ Publishing to EventBrite...")
        print("   This will create a REAL event on EventBrite")
        print("   Publishing now...")

        publisher = EventPublisher(db, event.id)
        result = publisher.publish_to_eventbrite()

        # 4. Display results
        print(f"\n4️⃣ Results:")

        if result.get('success'):
            print("✅ SUCCESS! Event published to EventBrite!")
            print(f"\n📋 Event Details:")
            print(f"   EventBrite Event ID: {result.get('event_id', 'N/A')}")
            print(f"   Event URL: {result.get('event_url', 'N/A')}")
            print(f"   Status: Published")

            if result.get('ticket_tiers_created'):
                print(f"\n🎫 Ticket Tiers Created: {result['ticket_tiers_created']}")
                if result.get('tiers'):
                    for tier in result['tiers']:
                        print(f"   • {tier['tier_name']}")
                        if 'eventbrite_ticket_class_id' in tier:
                            print(f"     ID: {tier['eventbrite_ticket_class_id']}")

            print(f"\n🔗 Next Steps:")
            print(f"   1. View on EventBrite: {result.get('event_url', 'N/A')}")
            print(f"   2. Manage tickets and settings on EventBrite dashboard")
            print(f"   3. Share the event link with customers")

        else:
            print(f"❌ Failed to publish event!")
            print(f"   Error: {result.get('error', 'Unknown error')}")

            if result.get('details'):
                print(f"\n📝 Error Details:")
                print(json.dumps(result['details'], indent=2))

            if result.get('setup_url'):
                print(f"\n📚 Setup Guide: {result['setup_url']}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "="*60)
    print("✨ Process complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()