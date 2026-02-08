"""Migration to add image_url to event_categories."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [c["name"] for c in inspector.get_columns("event_categories")]

        if "image_url" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE event_categories ADD COLUMN image_url VARCHAR(500)"
            ))
            conn.commit()
            results.append("Added image_url to event_categories")

    print("\n".join(results) if results else "image_url column already exists")
    return results


if __name__ == "__main__":
    run_migration()
