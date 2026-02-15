"""Migration to add inventory alert columns to ticket_tiers and promoter_email to events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if "ticket_tiers" in existing_tables:
            existing_columns = {c["name"] for c in inspector.get_columns("ticket_tiers")}

            if "alert_thresholds" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE ticket_tiers ADD COLUMN alert_thresholds TEXT"
                ))
                conn.commit()
                results.append("Added alert_thresholds to ticket_tiers")

            if "fired_thresholds" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE ticket_tiers ADD COLUMN fired_thresholds TEXT"
                ))
                conn.commit()
                results.append("Added fired_thresholds to ticket_tiers")

        if "events" in existing_tables:
            event_columns = {c["name"] for c in inspector.get_columns("events")}
            if "promoter_email" not in event_columns:
                conn.execute(text(
                    "ALTER TABLE events ADD COLUMN promoter_email VARCHAR(255)"
                ))
                conn.commit()
                results.append("Added promoter_email to events")

    print("\n".join(results) if results else "inventory_alerts migration already applied")
    return results


if __name__ == "__main__":
    run_migration()
