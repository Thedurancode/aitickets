"""
Add campaign tracking tables for email/SMS performance analytics.

Run with: python app/migrations/add_campaign_tracking.py
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create campaign tracking tables."""
    with engine.connect() as conn:
        # Check if tables already exist
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'campaigns'
            );
        """))
        exists = result.scalar()

        if exists:
            print("✓ campaigns table already exists")
            return

        # Create campaign type enum
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE campaigntype AS ENUM ('email', 'sms', 'notification');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        # Create campaigns table
        conn.execute(text("""
            CREATE TABLE campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                campaign_type campaigntype NOT NULL,
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

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create campaign_deliveries table
        conn.execute(text("""
            CREATE TABLE campaign_deliveries (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

                -- Recipient
                recipient_email VARCHAR(255),
                recipient_phone VARCHAR(50),
                event_goer_id INTEGER REFERENCES event_goers(id) ON DELETE SET NULL,

                -- Delivery tracking
                sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP WITH TIME ZONE,
                failed_at TIMESTAMP WITH TIME ZONE,
                failure_reason TEXT,

                -- Engagement tracking
                opened_at TIMESTAMP WITH TIME ZONE,
                clicked_at TIMESTAMP WITH TIME ZONE,
                converted_at TIMESTAMP WITH TIME ZONE,

                -- Revenue attribution
                ticket_id INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
                revenue_cents INTEGER DEFAULT 0,

                -- Tracking tokens
                tracking_token VARCHAR(64) UNIQUE,

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create indexes
        conn.execute(text("""
            -- campaigns indexes
            CREATE INDEX idx_campaigns_type ON campaigns(campaign_type);
            CREATE INDEX idx_campaigns_event_id ON campaigns(event_id);
            CREATE INDEX idx_campaigns_created_at ON campaigns(created_at);

            -- campaign_deliveries indexes
            CREATE INDEX idx_campaign_deliveries_campaign_id ON campaign_deliveries(campaign_id);
            CREATE INDEX idx_campaign_deliveries_recipient_email ON campaign_deliveries(recipient_email);
            CREATE INDEX idx_campaign_deliveries_recipient_phone ON campaign_deliveries(recipient_phone);
            CREATE INDEX idx_campaign_deliveries_event_goer_id ON campaign_deliveries(event_goer_id);
            CREATE INDEX idx_campaign_deliveries_sent_at ON campaign_deliveries(sent_at);
            CREATE INDEX idx_campaign_deliveries_opened_at ON campaign_deliveries(opened_at);
            CREATE INDEX idx_campaign_deliveries_clicked_at ON campaign_deliveries(clicked_at);
            CREATE INDEX idx_campaign_deliveries_ticket_id ON campaign_deliveries(ticket_id);
            CREATE INDEX idx_campaign_deliveries_tracking_token ON campaign_deliveries(tracking_token);
            CREATE INDEX idx_campaign_deliveries_created_at ON campaign_deliveries(created_at);
        """))

        conn.commit()
        print("✓ Created campaigns and campaign_deliveries tables with indexes")


def downgrade():
    """Drop campaign tracking tables."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS campaign_deliveries CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS campaigns CASCADE;"))
        conn.execute(text("DROP TYPE IF EXISTS campaigntype CASCADE;"))
        conn.commit()
        print("✓ Dropped campaign tracking tables")


if __name__ == "__main__":
    print("Running campaign tracking migration...")
    upgrade()
    print("Migration complete!")
