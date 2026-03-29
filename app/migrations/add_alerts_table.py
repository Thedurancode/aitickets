"""
Add Alerts table for storing in-app notifications from the intelligence system.

Run with: python app/migrations/add_alerts_table.py
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create alerts table."""
    with engine.connect() as conn:
        # Check if table already exists (SQLite compatible)
        result = conn.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='alerts';
        """))
        exists = result.fetchone() is not None

        if exists:
            print("✓ alerts table already exists")
            return

        # Create table (SQLite doesn't support ENUMs, use CHECK constraint)
        conn.execute(text("""
            CREATE TABLE alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                severity VARCHAR(20) NOT NULL DEFAULT 'medium'
                    CHECK(severity IN ('low', 'medium', 'high', 'critical')),

                -- Optional event reference
                event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,

                -- Additional context (JSON string)
                alert_metadata TEXT,

                -- Read status
                is_read BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,

                -- Delivery tracking
                channels_sent TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create indexes
        conn.execute(text("CREATE INDEX idx_alerts_severity ON alerts(severity);"))
        conn.execute(text("CREATE INDEX idx_alerts_is_read ON alerts(is_read);"))
        conn.execute(text("CREATE INDEX idx_alerts_event_id ON alerts(event_id);"))
        conn.execute(text("CREATE INDEX idx_alerts_created_at ON alerts(created_at);"))

        conn.commit()
        print("✓ Created alerts table with indexes")


def downgrade():
    """Drop alerts table."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alerts;"))
        conn.commit()
        print("✓ Dropped alerts table")


if __name__ == "__main__":
    print("Running alerts table migration...")
    upgrade()
    print("Migration complete!")
