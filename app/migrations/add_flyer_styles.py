"""Migration to add flyer_styles table for the style library."""
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

        if "flyer_styles" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE flyer_styles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT NOT NULL,
                        image_url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE flyer_styles (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT NOT NULL,
                        image_url VARCHAR(500),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text("CREATE INDEX ix_flyer_styles_name ON flyer_styles (name)"))
            conn.commit()
            results.append("Created flyer_styles table")

    return results


if __name__ == "__main__":
    run_migration()
