"""Migration to add waitlist_entries table."""

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

        if "waitlist_entries" not in existing_tables:
            is_sqlite = "sqlite" in str(engine.url)
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE waitlist_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        email VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        phone VARCHAR(50),
                        preferred_channel VARCHAR(10) DEFAULT 'email',
                        status VARCHAR(20) DEFAULT 'waiting',
                        position INTEGER NOT NULL,
                        notified_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE waitlist_entries (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        email VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        phone VARCHAR(50),
                        preferred_channel VARCHAR(10) DEFAULT 'email',
                        status VARCHAR(20) DEFAULT 'waiting',
                        position INTEGER NOT NULL,
                        notified_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE UNIQUE INDEX uq_waitlist_event_email ON waitlist_entries(event_id, email)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_waitlist_event_status ON waitlist_entries(event_id, status)"
            ))
            conn.commit()
            results.append("Created waitlist_entries table")

    print("\n".join(results) if results else "Waitlist table already exists")
    return results


if __name__ == "__main__":
    run_migration()
