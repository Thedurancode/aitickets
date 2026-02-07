"""Migration to add UTM tracking columns to tickets table."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [c["name"] for c in inspector.get_columns("tickets")]

        if "utm_source" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN utm_source VARCHAR(100)"
            ))
            conn.commit()
            results.append("Added utm_source to tickets")

        if "utm_medium" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN utm_medium VARCHAR(100)"
            ))
            conn.commit()
            results.append("Added utm_medium to tickets")

        if "utm_campaign" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN utm_campaign VARCHAR(100)"
            ))
            conn.commit()
            results.append("Added utm_campaign to tickets")

    print("\n".join(results) if results else "UTM columns already exist")
    return results


if __name__ == "__main__":
    run_migration()
