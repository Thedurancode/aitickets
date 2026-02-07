"""Migration to add promoter_phone, promoter_name, and promo_video_url to events."""

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

        if "promoter_phone" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN promoter_phone VARCHAR(50)"
            ))
            conn.commit()
            results.append("Added promoter_phone to events")

        if "promoter_name" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN promoter_name VARCHAR(255)"
            ))
            conn.commit()
            results.append("Added promoter_name to events")

        if "promo_video_url" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN promo_video_url VARCHAR(500)"
            ))
            conn.commit()
            results.append("Added promo_video_url to events")

    print("\n".join(results) if results else "Promoter fields already exist")
    return results


if __name__ == "__main__":
    run_migration()
