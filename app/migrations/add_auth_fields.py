"""
Migration to add authentication fields to event_goers table.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    """Add auth columns to event_goers table if they don't exist."""
    results = []

    columns_to_add = [
        ("password_hash", "VARCHAR(255)"),
        ("is_admin", "BOOLEAN DEFAULT 0"),
        ("avatar_url", "VARCHAR(500)"),
        ("google_id", "VARCHAR(100)"),
        ("auth_provider", "VARCHAR(50) DEFAULT 'email'"),
    ]

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('event_goers')]
        results.append(f"Existing columns: {existing_columns}")

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE event_goers ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    results.append(f"Added {col_name} column")
                except Exception as e:
                    results.append(f"Error adding {col_name}: {e}")
            else:
                results.append(f"{col_name} column already exists")

        # Create index on google_id
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_event_goers_google_id ON event_goers (google_id)"))
            conn.commit()
            results.append("Created index on google_id")
        except Exception as e:
            results.append(f"Index note: {e}")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
