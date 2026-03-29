"""
Add campaign tracking tables for email/SMS performance analytics.

Run with: python app/migrations/add_campaign_tracking.py
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create campaign tracking tables."""
    with engine.connect() as conn:
        # Check if tables already exist (SQLite compatible)
        result = conn.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='campaigns';
        """))
        exists = result.fetchone() is not None

        if exists:
            print("✓ campaigns table already exists")
            return

        # Create campaigns table (SQLite compatible)
        conn.execute(text("""
            CREATE TABLE campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                campaign_type VARCHAR(20) NOT NULL
                    CHECK(campaign_type IN ('email', 'sms', 'notification')),
                subject VARCHAR(255),

                -- Event reference
                event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,

                -- Tracking stats
                sent_count INTEGER DEFAULT 0,
                delivered_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                opened_count INTEGER DEFAULT 0,
                clicked_count INTEGER DEFAULT 0,
                converted_count INTEGER DEFAULT 0,

                -- Revenue tracking
                revenue_cents INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create campaign_deliveries table
        conn.execute(text("""
            CREATE TABLE campaign_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

                -- Recipient
                recipient_email VARCHAR(255),
                recipient_phone VARCHAR(50),
                event_goer_id INTEGER REFERENCES event_goers(id) ON DELETE SET NULL,

                -- Delivery tracking
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP,
                failed_at TIMESTAMP,
                failure_reason TEXT,

                -- Engagement tracking
                opened_at TIMESTAMP,
                clicked_at TIMESTAMP,
                converted_at TIMESTAMP,

                -- Revenue attribution
                ticket_id INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
                revenue_cents INTEGER DEFAULT 0,

                -- Tracking tokens
                tracking_token VARCHAR(64) UNIQUE,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create indexes
        conn.execute(text("CREATE INDEX idx_campaigns_type ON campaigns(campaign_type);"))
        conn.execute(text("CREATE INDEX idx_campaigns_event_id ON campaigns(event_id);"))
        conn.execute(text("CREATE INDEX idx_campaigns_created_at ON campaigns(created_at);"))

        conn.execute(text("CREATE INDEX idx_campaign_deliveries_campaign_id ON campaign_deliveries(campaign_id);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_recipient_email ON campaign_deliveries(recipient_email);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_recipient_phone ON campaign_deliveries(recipient_phone);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_event_goer_id ON campaign_deliveries(event_goer_id);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_sent_at ON campaign_deliveries(sent_at);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_opened_at ON campaign_deliveries(opened_at);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_clicked_at ON campaign_deliveries(clicked_at);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_ticket_id ON campaign_deliveries(ticket_id);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_tracking_token ON campaign_deliveries(tracking_token);"))
        conn.execute(text("CREATE INDEX idx_campaign_deliveries_created_at ON campaign_deliveries(created_at);"))

        conn.commit()
        print("✓ Created campaigns and campaign_deliveries tables with indexes")


def downgrade():
    """Drop campaign tracking tables."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS campaign_deliveries;"))
        conn.execute(text("DROP TABLE IF EXISTS campaigns;"))
        conn.commit()
        print("✓ Dropped campaign tracking tables")


if __name__ == "__main__":
    print("Running campaign tracking migration...")
    upgrade()
    print("Migration complete!")
