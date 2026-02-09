"""Migration to add marketing_lists table."""

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

        if "marketing_lists" not in existing_tables:
            is_sqlite = "sqlite" in str(engine.url)
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE marketing_lists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        segment_filters TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE marketing_lists (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        segment_filters TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.commit()
            results.append("Created marketing_lists table")

    print("\n".join(results) if results else "Marketing lists table already exists")
    return results


if __name__ == "__main__":
    run_migration()
