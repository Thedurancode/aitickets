"""
Migration to add target_segments column to marketing_campaigns table.

Adds a JSON text column for segment-based targeting criteria.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    """Add target_segments column to marketing_campaigns if it doesn't exist."""
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if "marketing_campaigns" not in existing_tables:
            results.append("marketing_campaigns table does not exist yet, skipping")
            print("\n".join(results))
            return results

        existing_columns = [col["name"] for col in inspector.get_columns("marketing_campaigns")]

        if "target_segments" not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE marketing_campaigns ADD COLUMN target_segments TEXT"))
                conn.commit()
                results.append("Added target_segments column to marketing_campaigns")
            except Exception as e:
                results.append(f"Error adding target_segments: {e}")
        else:
            results.append("target_segments column already exists")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
