"""Migration to add series_id to events for recurring event support."""

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

        if "series_id" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN series_id VARCHAR(36)"
            ))
            conn.commit()
            results.append("Added series_id to events")

    print("\n".join(results) if results else "series_id column already exists")
    return results


if __name__ == "__main__":
    run_migration()
