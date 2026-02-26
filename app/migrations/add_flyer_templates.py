"""Migration to add flyer_templates table for template-based flyer generation."""
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

        # Create flyer_templates table
        if "flyer_templates" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE flyer_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    image_url VARCHAR(500) NOT NULL,
                    thumbnail_url VARCHAR(500),
                    prompt_instructions TEXT,
                    created_by VARCHAR(255),
                    times_used INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_flyer_templates_created_by ON flyer_templates (created_by)"))
            conn.execute(text("CREATE INDEX idx_flyer_templates_times_used ON flyer_templates (times_used)"))
            conn.execute(text("CREATE INDEX idx_flyer_templates_created_at ON flyer_templates (created_at)"))
            results.append("Created flyer_templates table")
        else:
            results.append("flyer_templates table already exists")

        conn.commit()

    return results


if __name__ == "__main__":
    results = run_migration()
    for result in results:
        print(result)
