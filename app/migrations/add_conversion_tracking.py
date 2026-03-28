"""
Add ConversionTracking table for real UTM attribution analysis.

This migration adds a comprehensive conversion tracking system that stores
rich metadata about every ticket purchase for ML training and attribution analysis.

Run with: python app/migrations/add_conversion_tracking.py
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create conversion_tracking table."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'conversion_tracking'
            );
        """))
        exists = result.scalar()

        if exists:
            print("✓ conversion_tracking table already exists")
            return

        # Create table
        conn.execute(text("""
            CREATE TABLE conversion_tracking (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                event_goer_id INTEGER NOT NULL REFERENCES event_goers(id) ON DELETE CASCADE,
                tier_id INTEGER NOT NULL REFERENCES ticket_tiers(id) ON DELETE CASCADE,

                -- Attribution data
                utm_source VARCHAR(100),
                utm_medium VARCHAR(100),
                utm_campaign VARCHAR(100),
                utm_content VARCHAR(100),
                utm_term VARCHAR(100),

                -- Referrer info
                referrer_url VARCHAR(500),
                landing_page VARCHAR(500),

                -- Session data
                session_id VARCHAR(100),
                device_type VARCHAR(50),
                browser VARCHAR(100),

                -- Purchase data
                price_paid_cents INTEGER NOT NULL,
                discount_amount_cents INTEGER,
                promo_code_id INTEGER REFERENCES promo_codes(id),

                -- Timing data
                purchased_at TIMESTAMP WITH TIME ZONE NOT NULL,
                days_before_event INTEGER,
                hour_of_day INTEGER,
                day_of_week INTEGER,

                -- Event metadata (denormalized)
                venue_id INTEGER REFERENCES venues(id),
                category_id INTEGER REFERENCES event_categories(id),

                -- A/B test tracking
                ab_test_variant VARCHAR(100),

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Create indexes for fast querying
        conn.execute(text("""
            CREATE INDEX idx_conversion_tracking_ticket ON conversion_tracking(ticket_id);
            CREATE INDEX idx_conversion_tracking_event ON conversion_tracking(event_id);
            CREATE INDEX idx_conversion_tracking_event_goer ON conversion_tracking(event_goer_id);
            CREATE INDEX idx_conversion_tracking_tier ON conversion_tracking(tier_id);
            CREATE INDEX idx_conversion_tracking_utm_source ON conversion_tracking(utm_source);
            CREATE INDEX idx_conversion_tracking_utm_medium ON conversion_tracking(utm_medium);
            CREATE INDEX idx_conversion_tracking_purchased_at ON conversion_tracking(purchased_at);
            CREATE INDEX idx_conversion_tracking_hour_of_day ON conversion_tracking(hour_of_day);
            CREATE INDEX idx_conversion_tracking_day_of_week ON conversion_tracking(day_of_week);
            CREATE INDEX idx_conversion_tracking_venue ON conversion_tracking(venue_id);
            CREATE INDEX idx_conversion_tracking_category ON conversion_tracking(category_id);
            CREATE INDEX idx_conversion_tracking_ab_test ON conversion_tracking(ab_test_variant);
            CREATE INDEX idx_conversion_tracking_created_at ON conversion_tracking(created_at);
        """))

        conn.commit()
        print("✓ Created conversion_tracking table with indexes")


def downgrade():
    """Drop conversion_tracking table."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS conversion_tracking CASCADE;"))
        conn.commit()
        print("✓ Dropped conversion_tracking table")


if __name__ == "__main__":
    print("Running conversion tracking migration...")
    upgrade()
    print("Migration complete!")
