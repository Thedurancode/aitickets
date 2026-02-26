"""Migration to add birthdate and birthday_opt_in fields to event_goers table."""
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

        if "event_goers" in existing_tables:
            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('event_goers')]

            # Add birthdate column if it doesn't exist
            if "birthdate" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_goers
                    ADD COLUMN birthdate DATE
                """))
                results.append("Added birthdate column")
            else:
                results.append("birthdate column already exists")

            # Add birthday_opt_in column if it doesn't exist
            if "birthday_opt_in" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_goers
                    ADD COLUMN birthday_opt_in BOOLEAN DEFAULT FALSE
                """))
                results.append("Added birthday_opt_in column")
            else:
                results.append("birthday_opt_in column already exists")

            conn.commit()
        else:
            results.append("event_goers table does not exist")

    return results


if __name__ == "__main__":
    run_migration()
