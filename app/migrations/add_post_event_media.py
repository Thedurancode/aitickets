"""Migration to add post-event media support: post_event_video_url on events, event_photos table."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)

        # Add post_event_video_url to events
        existing_columns = [c["name"] for c in inspector.get_columns("events")]
        if "post_event_video_url" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE events ADD COLUMN post_event_video_url VARCHAR(500)"
            ))
            conn.commit()
            results.append("Added post_event_video_url to events")

        # Create event_photos table if not exists
        existing_tables = inspector.get_table_names()
        if "event_photos" not in existing_tables:
            is_sqlite = "sqlite" in str(engine.url)
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE event_photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        photo_url VARCHAR(500) NOT NULL,
                        uploaded_by_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE event_photos (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        photo_url VARCHAR(500) NOT NULL,
                        uploaded_by_name VARCHAR(255),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.commit()
            results.append("Created event_photos table")

    print("\n".join(results) if results else "Post-event media tables already exist")
    return results


if __name__ == "__main__":
    run_migration()
