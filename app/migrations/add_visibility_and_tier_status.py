"""Migration to add event visibility, doors_open_time, and ticket tier status."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)

        # ============== Event columns ==============
        existing_event_columns = [c["name"] for c in inspector.get_columns("events")]

        if "is_visible" not in existing_event_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN is_visible BOOLEAN DEFAULT TRUE"
            ))
            conn.commit()
            results.append("Added is_visible to events")

        if "doors_open_time" not in existing_event_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN doors_open_time VARCHAR(10)"
            ))
            conn.commit()
            results.append("Added doors_open_time to events")

        # ============== Ticket tier status ==============
        existing_tier_columns = [c["name"] for c in inspector.get_columns("ticket_tiers")]

        if "status" not in existing_tier_columns:
            conn.execute(text(
                "ALTER TABLE ticket_tiers ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'"
            ))
            conn.commit()
            results.append("Added status to ticket_tiers")

            # Backfill: mark sold-out tiers
            conn.execute(text(
                "UPDATE ticket_tiers SET status = 'SOLD_OUT' WHERE quantity_sold >= quantity_available AND quantity_available > 0"
            ))
            conn.commit()
            results.append("Backfilled sold_out status for existing tiers")

    print("\n".join(results) if results else "Visibility and tier status columns already exist")
    return results


if __name__ == "__main__":
    run_migration()
