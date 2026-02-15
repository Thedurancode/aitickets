"""Migration to add media sharing tokens and extend event_photos for video support."""

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
        is_sqlite = "sqlite" in str(engine.url)

        # Create media_share_tokens table
        if "media_share_tokens" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE media_share_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        event_goer_id INTEGER NOT NULL REFERENCES event_goers(id),
                        token VARCHAR(255) NOT NULL UNIQUE,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE media_share_tokens (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        event_goer_id INTEGER NOT NULL REFERENCES event_goers(id),
                        token VARCHAR(255) NOT NULL UNIQUE,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE UNIQUE INDEX ix_media_share_tokens_token ON media_share_tokens(token)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_media_share_tokens_event ON media_share_tokens(event_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_media_share_tokens_goer ON media_share_tokens(event_goer_id)"
            ))
            conn.commit()
            results.append("Created media_share_tokens table")

        # Extend event_photos with event_goer_id and media_type
        if "event_photos" in existing_tables:
            existing_columns = {c["name"] for c in inspector.get_columns("event_photos")}

            if "event_goer_id" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE event_photos ADD COLUMN event_goer_id INTEGER REFERENCES event_goers(id)"
                ))
                conn.execute(text(
                    "CREATE INDEX ix_event_photos_event_goer ON event_photos(event_goer_id)"
                ))
                conn.commit()
                results.append("Added event_goer_id to event_photos")

            if "media_type" not in existing_columns:
                conn.execute(text(
                    "ALTER TABLE event_photos ADD COLUMN media_type VARCHAR(20) DEFAULT 'photo'"
                ))
                conn.commit()
                results.append("Added media_type to event_photos")

        # Add uploads_open to events
        if "events" in existing_tables:
            event_columns = {c["name"] for c in inspector.get_columns("events")}
            if "uploads_open" not in event_columns:
                if is_sqlite:
                    conn.execute(text(
                        "ALTER TABLE events ADD COLUMN uploads_open BOOLEAN DEFAULT 1"
                    ))
                else:
                    conn.execute(text(
                        "ALTER TABLE events ADD COLUMN uploads_open BOOLEAN DEFAULT TRUE"
                    ))
                conn.commit()
                results.append("Added uploads_open to events")

    print("\n".join(results) if results else "media_sharing migration already applied")
    return results


if __name__ == "__main__":
    run_migration()
