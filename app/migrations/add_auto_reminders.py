"""Migration to add auto_reminder columns to events table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [c["name"] for c in inspector.get_columns("events")]

        if "auto_reminder_hours" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN auto_reminder_hours INTEGER DEFAULT 24"
            ))
            results.append("Added auto_reminder_hours column to events")

        if "auto_reminder_use_sms" not in existing_columns:
            is_sqlite = "sqlite" in str(engine.url)
            if is_sqlite:
                conn.execute(text(
                    "ALTER TABLE events ADD COLUMN auto_reminder_use_sms BOOLEAN DEFAULT 0"
                ))
            else:
                conn.execute(text(
                    "ALTER TABLE events ADD COLUMN auto_reminder_use_sms BOOLEAN DEFAULT FALSE"
                ))
            results.append("Added auto_reminder_use_sms column to events")

        if results:
            conn.commit()

    print("\n".join(results) if results else "Auto-reminder columns already exist")
    return results


if __name__ == "__main__":
    run_migration()
