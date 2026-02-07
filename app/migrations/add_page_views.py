"""Migration to add page_views table for analytics tracking."""

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

        if "page_views" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE page_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER REFERENCES events(id),
                    page VARCHAR(50) NOT NULL,
                    ip_hash VARCHAR(64) NOT NULL,
                    user_agent VARCHAR(500),
                    referrer VARCHAR(500),
                    utm_source VARCHAR(100),
                    utm_medium VARCHAR(100),
                    utm_campaign VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_page_views_event_id ON page_views (event_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_page_views_created_at ON page_views (created_at)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_page_views_ip_hash ON page_views (ip_hash)"
            ))
            conn.commit()
            results.append("Created page_views table")
        else:
            results.append("page_views table already exists")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
