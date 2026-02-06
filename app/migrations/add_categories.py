"""
Migration to add event categories tables.

Creates the event_categories table and event_category_link association table
for existing databases.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    """Add event categories tables if they don't exist."""
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Create event_categories table if it doesn't exist
        if "event_categories" not in existing_tables:
            try:
                conn.execute(text("""
                    CREATE TABLE event_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        description TEXT,
                        color VARCHAR(20),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX ix_event_categories_name ON event_categories (name)"))
                conn.commit()
                results.append("Created event_categories table")
            except Exception as e:
                results.append(f"Error creating event_categories: {e}")
        else:
            results.append("event_categories table already exists")

        # Create event_category_link table if it doesn't exist
        if "event_category_link" not in existing_tables:
            try:
                conn.execute(text("""
                    CREATE TABLE event_category_link (
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        category_id INTEGER NOT NULL REFERENCES event_categories(id),
                        PRIMARY KEY (event_id, category_id)
                    )
                """))
                conn.commit()
                results.append("Created event_category_link table")
            except Exception as e:
                results.append(f"Error creating event_category_link: {e}")
        else:
            results.append("event_category_link table already exists")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
