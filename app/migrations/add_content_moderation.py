"""Migration to add content moderation fields to event_photos table."""
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

        if "event_photos" in existing_tables:
            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('event_photos')]

            # Add moderation_status column if it doesn't exist
            if "moderation_status" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_photos
                    ADD COLUMN moderation_status VARCHAR(20) DEFAULT 'pending'
                """))
                results.append("Added moderation_status column")
            else:
                results.append("moderation_status column already exists")

            # Add moderation_score column if it doesn't exist
            if "moderation_score" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_photos
                    ADD COLUMN moderation_score FLOAT
                """))
                results.append("Added moderation_score column")
            else:
                results.append("moderation_score column already exists")

            # Add moderation_scores_json column if it doesn't exist
            if "moderation_scores_json" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_photos
                    ADD COLUMN moderation_scores_json TEXT
                """))
                results.append("Added moderation_scores_json column")
            else:
                results.append("moderation_scores_json column already exists")

            # Add moderated_at column if it doesn't exist
            if "moderated_at" not in columns:
                conn.execute(text("""
                    ALTER TABLE event_photos
                    ADD COLUMN moderated_at TIMESTAMP
                """))
                results.append("Added moderated_at column")
            else:
                results.append("moderated_at column already exists")

            # Set existing photos to approved by default
            conn.execute(text("""
                UPDATE event_photos
                SET moderation_status = 'approved'
                WHERE moderation_status = 'pending' OR moderation_status IS NULL
            """))
            results.append("Set existing photos to approved status")

            conn.commit()
        else:
            results.append("event_photos table does not exist")

    return results


if __name__ == "__main__":
    run_migration()
