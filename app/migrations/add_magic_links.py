"""Migration to add admin_magic_links table for persistent magic link tokens."""

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

        if "admin_magic_links" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE admin_magic_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        token VARCHAR(255) NOT NULL UNIQUE,
                        phone VARCHAR(50) NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE admin_magic_links (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        token VARCHAR(255) NOT NULL UNIQUE,
                        phone VARCHAR(50) NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        used_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE UNIQUE INDEX ix_admin_magic_links_token ON admin_magic_links(token)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_admin_magic_links_event ON admin_magic_links(event_id)"
            ))
            results.append("Created admin_magic_links table")

        conn.commit()

    print("\n".join(results) if results else "admin_magic_links table already exists")
    return results


if __name__ == "__main__":
    run_migration()
