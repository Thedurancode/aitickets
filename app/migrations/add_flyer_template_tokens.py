"""Migration to add flyer_template_magic_tokens table for template selection via SMS."""
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

        # Create flyer_template_magic_tokens table
        if "flyer_template_magic_tokens" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE flyer_template_magic_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    token VARCHAR(255) NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            """))
            conn.execute(text("CREATE INDEX idx_flyer_tokens_token ON flyer_template_magic_tokens (token)"))
            conn.execute(text("CREATE INDEX idx_flyer_tokens_event ON flyer_template_magic_tokens (event_id)"))
            conn.execute(text("CREATE INDEX idx_flyer_tokens_expires ON flyer_template_magic_tokens (expires_at)"))
            results.append("Created flyer_template_magic_tokens table")
        else:
            results.append("flyer_template_magic_tokens table already exists")

        conn.commit()

    return results


if __name__ == "__main__":
    results = run_migration()
    for result in results:
        print(result)
