"""Migration to add conversation_sessions table for voice agent memory."""

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

        if "conversation_sessions" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE conversation_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id VARCHAR(36) NOT NULL UNIQUE,
                        current_customer_id INTEGER REFERENCES event_goers(id),
                        current_event_id INTEGER REFERENCES events(id),
                        conversation_history TEXT,
                        entity_context TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE conversation_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(36) NOT NULL UNIQUE,
                        current_customer_id INTEGER REFERENCES event_goers(id),
                        current_event_id INTEGER REFERENCES events(id),
                        conversation_history TEXT,
                        entity_context TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        last_activity TIMESTAMPTZ DEFAULT NOW(),
                        expires_at TIMESTAMPTZ NOT NULL
                    )
                """))
            conn.execute(text(
                "CREATE UNIQUE INDEX ix_conversation_sessions_session_id ON conversation_sessions(session_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_conversation_sessions_expires_at ON conversation_sessions(expires_at)"
            ))
            results.append("Created conversation_sessions table")

        conn.commit()

    print("\n".join(results) if results else "conversation_sessions table already exists")
    return results


if __name__ == "__main__":
    run_migration()
