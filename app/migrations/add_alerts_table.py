"""
Add Alerts table for storing in-app notifications from the intelligence system.

Run with: python app/migrations/add_alerts_table.py
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create alerts table."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'alerts'
            );
        """))
        exists = result.scalar()

        if exists:
            print("✓ alerts table already exists")
            return

        # Create severity enum type
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE alertseverity AS ENUM ('low', 'medium', 'high', 'critical');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        # Create table
        conn.execute(text("""
            CREATE TABLE alerts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                severity alertseverity NOT NULL DEFAULT 'medium',

                -- Optional event reference
                event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,

                -- Additional context (JSON string)
                metadata TEXT,

                -- Read status
                is_read BOOLEAN DEFAULT FALSE,
                read_at TIMESTAMP WITH TIME ZONE,

                -- Delivery tracking
                channels_sent TEXT,

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create indexes
        conn.execute(text("""
            CREATE INDEX idx_alerts_severity ON alerts(severity);
            CREATE INDEX idx_alerts_is_read ON alerts(is_read);
            CREATE INDEX idx_alerts_event_id ON alerts(event_id);
            CREATE INDEX idx_alerts_created_at ON alerts(created_at);
        """))

        conn.commit()
        print("✓ Created alerts table with indexes")


def downgrade():
    """Drop alerts table."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alerts CASCADE;"))
        conn.execute(text("DROP TYPE IF EXISTS alertseverity CASCADE;"))
        conn.commit()
        print("✓ Dropped alerts table")


if __name__ == "__main__":
    print("Running alerts table migration...")
    upgrade()
    print("Migration complete!")
