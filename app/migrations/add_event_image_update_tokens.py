"""Migration to add event_image_update_tokens table for SMS-based image updates."""
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

        if "event_image_update_tokens" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE event_image_update_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        phone VARCHAR(50) NOT NULL,
                        token VARCHAR(255) UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE event_image_update_tokens (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        phone VARCHAR(50) NOT NULL,
                        token VARCHAR(255) UNIQUE NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        used_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text("CREATE INDEX ix_event_image_update_tokens_id ON event_image_update_tokens (id)"))
            conn.execute(text("CREATE INDEX ix_event_image_update_tokens_event_id ON event_image_update_tokens (event_id)"))
            conn.execute(text("CREATE INDEX ix_event_image_update_tokens_token ON event_image_update_tokens (token)"))
            conn.commit()
            results.append("Created event_image_update_tokens table")

    return results


if __name__ == "__main__":
    run_migration()
