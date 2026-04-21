#!/usr/bin/env python3
"""
Update Peru Chicken Event Date to Future
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite:///./tickets.db')

from app.database import SessionLocal
from app.models import Event


def main():
    """Update Peru Chicken event date to future"""

    print("\n" + "="*60)
    print("📅 UPDATING PERU CHICKEN EVENT DATE")
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
        print(f"   Current date: {event.event_date}")

        # Update to Mother's Day 2025 (May 11, 2025)
        new_date = "2025-05-11"
        new_sale_start = "2025-04-01"

        event.event_date = new_date
        event.sale_start_date = new_sale_start

        db.commit()

        print(f"\n✅ Updated event dates:")
        print(f"   New event date: {new_date} (Mother's Day 2025)")
        print(f"   Sale start date: {new_sale_start}")
        print("\n🎯 Event is now ready for EventBrite publishing!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()