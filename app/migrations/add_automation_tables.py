"""Migration to add automation tables: auto_triggers, survey_responses, and ticket columns."""

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

        # --- Ticket columns: created_at, recovery_sent_at ---
        ticket_cols = [c["name"] for c in inspector.get_columns("tickets")]

        if "created_at" not in ticket_cols:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN created_at TIMESTAMP"
            ))
            results.append("Added created_at column to tickets")

        if "recovery_sent_at" not in ticket_cols:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN recovery_sent_at TIMESTAMP"
            ))
            results.append("Added recovery_sent_at column to tickets")

        if "description" not in ticket_cols:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN description TEXT"
            ))
            results.append("Added description column to tickets")

        # --- auto_triggers table ---
        if "auto_triggers" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE auto_triggers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        trigger_type VARCHAR(50) NOT NULL,
                        event_id INTEGER REFERENCES events(id),
                        threshold_value INTEGER,
                        threshold_days INTEGER,
                        action VARCHAR(50) NOT NULL,
                        action_config TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        last_fired_at TIMESTAMP,
                        fire_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE auto_triggers (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        trigger_type VARCHAR(50) NOT NULL,
                        event_id INTEGER REFERENCES events(id),
                        threshold_value INTEGER,
                        threshold_days INTEGER,
                        action VARCHAR(50) NOT NULL,
                        action_config TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_fired_at TIMESTAMPTZ,
                        fire_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_auto_triggers_type ON auto_triggers(trigger_type, is_active)"
            ))
            results.append("Created auto_triggers table")

        # --- survey_responses table ---
        if "survey_responses" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE survey_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        event_goer_id INTEGER NOT NULL REFERENCES event_goers(id),
                        ticket_id INTEGER REFERENCES tickets(id),
                        survey_token VARCHAR(100) NOT NULL UNIQUE,
                        rating INTEGER,
                        comment TEXT,
                        submitted_at TIMESTAMP,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE survey_responses (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id),
                        event_goer_id INTEGER NOT NULL REFERENCES event_goers(id),
                        ticket_id INTEGER REFERENCES tickets(id),
                        survey_token VARCHAR(100) NOT NULL UNIQUE,
                        rating INTEGER,
                        comment TEXT,
                        submitted_at TIMESTAMPTZ,
                        sent_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_survey_responses_event ON survey_responses(event_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_survey_responses_token ON survey_responses(survey_token)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_survey_responses_goer ON survey_responses(event_goer_id)"
            ))
            results.append("Created survey_responses table")

        conn.commit()

    print("\n".join(results) if results else "Automation tables already exist")
    return results


if __name__ == "__main__":
    run_migration()
