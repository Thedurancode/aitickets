#!/usr/bin/env python3
"""
Test EventBrite Payload Generation
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal
from app.models import Event


def main():
    """Test payload generation for EventBrite"""

    print("\n" + "="*60)
    print("🔍 TESTING EVENTBRITE PAYLOAD GENERATION")
    print("="*60)

    db = SessionLocal()

    try:
        # Find the Peru Chicken event
        event = db.query(Event).filter(
            Event.name.like("%Peruvian%Brunch%")
        ).first()

        if not event:
            print("❌ Peru Chicken event not found!")
            return

        print(f"\n✅ Found event: {event.name}")
        print(f"   Event Date: {event.event_date}")
        print(f"   Event Time: {event.event_time}")

        # Parse event datetime
        event_date_str = str(event.event_date)
        event_time_str = str(event.event_time or '19:00:00')

        # Combine date and time
        event_datetime_str = f"{event_date_str}T{event_time_str}"
        print(f"\n📅 DateTime String: {event_datetime_str}")

        event_dt = datetime.fromisoformat(event_datetime_str)
        print(f"   Parsed DateTime: {event_dt}")

        # Assume Eastern Time (UTC-4 for DST in May)
        eastern_offset = timedelta(hours=-4)
        event_dt_utc = event_dt - eastern_offset
        event_end_utc = event_dt_utc + timedelta(hours=3)

        print(f"\n🌍 UTC Conversion:")
        print(f"   Start UTC: {event_dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print(f"   End UTC: {event_end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}")

        # Build EventBrite payload
        payload = {
            "event": {
                "name": {"html": event.name},
                "description": {"html": event.description[:200] if event.description else ""},
                "start": {
                    "timezone": "America/New_York",
                    "utc": event_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "end": {
                    "timezone": "America/New_York",
                    "utc": event_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                "currency": "USD",
                "online_event": False,
                "listed": True,
                "shareable": True,
                "invite_only": False,
                "show_remaining": True,
                "capacity": 100
            }
        }

        print(f"\n📦 EventBrite Payload:")
        print(json.dumps(payload, indent=2))

        # Check if dates are in future
        now = datetime.utcnow()
        print(f"\n⏰ Time Check:")
        print(f"   Current UTC: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print(f"   Event Start UTC: {event_dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        print(f"   Is Future: {event_dt_utc > now}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()