"""Migration to add style_picker_sessions table for SMS-based style selection."""
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

        if "style_picker_sessions" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE style_picker_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        token VARCHAR(100) UNIQUE NOT NULL,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        phone VARCHAR(50) NOT NULL,
                        selected_style_id INTEGER REFERENCES flyer_styles(id),
                        status VARCHAR(20) DEFAULT 'pending',
                        expires_at TIMESTAMP NOT NULL,
                        selected_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE style_picker_sessions (
                        id SERIAL PRIMARY KEY,
                        token VARCHAR(100) UNIQUE NOT NULL,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        phone VARCHAR(50) NOT NULL,
                        selected_style_id INTEGER REFERENCES flyer_styles(id),
                        status VARCHAR(20) DEFAULT 'pending',
                        expires_at TIMESTAMPTZ NOT NULL,
                        selected_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text("CREATE UNIQUE INDEX ix_style_picker_sessions_token ON style_picker_sessions (token)"))
            conn.execute(text("CREATE INDEX ix_style_picker_sessions_event_id ON style_picker_sessions (event_id)"))
            conn.commit()
            results.append("Created style_picker_sessions table")

    return results


if __name__ == "__main__":
    run_migration()
