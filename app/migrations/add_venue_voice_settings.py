"""
Migration: Add voice settings to venues table for ElevenLabs voiceover generation

This enables venues to have custom voice settings for AI-generated voiceovers.
"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """Add voice settings columns to venues table."""
    with engine.connect() as conn:
        # Add voice_id column
        conn.execute(text("""
            ALTER TABLE venues
            ADD COLUMN voice_id VARCHAR(100)
        """))

        # Add voice_name column
        conn.execute(text("""
            ALTER TABLE venues
            ADD COLUMN voice_name VARCHAR(100)
        """))

        # Add voice_settings column (JSON string)
        conn.execute(text("""
            ALTER TABLE venues
            ADD COLUMN voice_settings TEXT
        """))

        conn.commit()
        print("✅ Added voice settings columns to venues table")


def downgrade():
    """Remove voice settings columns from venues table."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE venues
            DROP COLUMN voice_id
        """))

        conn.execute(text("""
            ALTER TABLE venues
            DROP COLUMN voice_name
        """))

        conn.execute(text("""
            ALTER TABLE venues
            DROP COLUMN voice_settings
        """))

        conn.commit()
        print("✅ Removed voice settings columns from venues table")


if __name__ == "__main__":
    upgrade()
