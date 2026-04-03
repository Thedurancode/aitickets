"""
Add tables for new features: Group Buying, Affiliates, Loyalty

This migration adds tables for:
- Group purchases and contributions
- Affiliate program with referrals and payouts
- Loyalty accounts with transactions and badges
"""
from sqlalchemy import text
from app.database import engine


def run_migration():
    """Run the migration (standard interface)."""
    upgrade()


def upgrade():
    """Create new feature tables."""

    # Create Group Buying tables
    with engine.connect() as connection:
        # Group purchases table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS group_purchases (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(id),
                organizer_id INTEGER NOT NULL REFERENCES event_goers(id),
                group_name VARCHAR(255),
                total_tickets INTEGER NOT NULL,
                total_amount INTEGER NOT NULL,
                amount_paid INTEGER DEFAULT 0,
                amount_remaining INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                stripe_payment_intent_id VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE
            )
        """))
        connection.execute(text("CREATE INDEX idx_group_purchases_event ON group_purchases(event_id)"))
        connection.execute(text("CREATE INDEX idx_group_purchases_status ON group_purchases(status)"))

        # Group contributions table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS group_contributions (
                id SERIAL PRIMARY KEY,
                group_purchase_id INTEGER NOT NULL REFERENCES group_purchases(id) ON DELETE CASCADE,
                contributor_id INTEGER NOT NULL REFERENCES event_goers(id),
                amount INTEGER NOT NULL,
                ticket_count INTEGER DEFAULT 1,
                stripe_payment_intent_id VARCHAR(255),
                paid BOOLEAN DEFAULT FALSE,
                paid_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_contributions_group ON group_contributions(group_purchase_id)"))
        connection.execute(text("CREATE INDEX idx_contributions_contributor ON group_contributions(contributor_id)"))

        # Affiliates table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS affiliates (
                id SERIAL PRIMARY KEY,
                event_goer_id INTEGER NOT NULL UNIQUE REFERENCES event_goers(id),
                code VARCHAR(50) UNIQUE NOT NULL,
                display_name VARCHAR(255),
                bio TEXT,
                instagram_handle VARCHAR(100),
                tiktok_handle VARCHAR(100),
                youtube_channel VARCHAR(255),
                twitter_handle VARCHAR(100),
                commission_rate NUMERIC(5,2) DEFAULT 10.00,
                total_sales INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                commission_paid INTEGER DEFAULT 0,
                commission_pending INTEGER DEFAULT 0,
                total_clicks INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                approved_at TIMESTAMP WITH TIME ZONE,
                stripe_account_id VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_affiliates_code ON affiliates(code)"))
        connection.execute(text("CREATE INDEX idx_affiliates_status ON affiliates(status)"))

        # Affiliate referrals table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS affiliate_referrals (
                id SERIAL PRIMARY KEY,
                affiliate_id INTEGER NOT NULL REFERENCES affiliates(id) ON DELETE CASCADE,
                ticket_id INTEGER REFERENCES tickets(id),
                referral_code VARCHAR(50) NOT NULL,
                clicked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                converted_at TIMESTAMP WITH TIME ZONE,
                sale_amount INTEGER,
                commission_amount INTEGER,
                commission_paid BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_referrals_affiliate ON affiliate_referrals(affiliate_id)"))
        connection.execute(text("CREATE INDEX idx_referrals_code ON affiliate_referrals(referral_code)"))
        connection.execute(text("CREATE INDEX idx_referrals_ticket ON affiliate_referrals(ticket_id)"))

        # Affiliate payouts table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS affiliate_payouts (
                id SERIAL PRIMARY KEY,
                affiliate_id INTEGER NOT NULL REFERENCES affiliates(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                stripe_transfer_id VARCHAR(255),
                status VARCHAR(20) DEFAULT 'pending',
                processed_at TIMESTAMP WITH TIME ZONE,
                failed_reason TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_payouts_affiliate ON affiliate_payouts(affiliate_id)"))
        connection.execute(text("CREATE INDEX idx_payouts_status ON affiliate_payouts(status)"))

        # Loyalty accounts table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS loyalty_accounts (
                id SERIAL PRIMARY KEY,
                event_goer_id INTEGER NOT NULL UNIQUE REFERENCES event_goers(id),
                total_points INTEGER DEFAULT 0,
                available_points INTEGER DEFAULT 0,
                lifetime_points INTEGER DEFAULT 0,
                current_tier VARCHAR(20) DEFAULT 'bronze',
                total_purchases INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                total_reviews INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_loyalty_goer ON loyalty_accounts(event_goer_id)"))
        connection.execute(text("CREATE INDEX idx_loyalty_tier ON loyalty_accounts(current_tier)"))

        # Loyalty transactions table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS loyalty_transactions (
                id SERIAL PRIMARY KEY,
                loyalty_account_id INTEGER NOT NULL REFERENCES loyalty_accounts(id) ON DELETE CASCADE,
                type VARCHAR(50) NOT NULL,
                points INTEGER NOT NULL,
                reason VARCHAR(255) NOT NULL,
                ticket_id INTEGER REFERENCES tickets(id),
                event_id INTEGER REFERENCES events(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_loyalty_trans_account ON loyalty_transactions(loyalty_account_id)"))
        connection.execute(text("CREATE INDEX idx_loyalty_trans_type ON loyalty_transactions(type)"))

        # Customer badges table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_badges (
                id SERIAL PRIMARY KEY,
                loyalty_account_id INTEGER NOT NULL REFERENCES loyalty_accounts(id) ON DELETE CASCADE,
                badge_type VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon VARCHAR(50),
                points_awarded INTEGER DEFAULT 0,
                earned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("CREATE INDEX idx_badges_account ON customer_badges(loyalty_account_id)"))
        connection.execute(text("CREATE INDEX idx_badges_type ON customer_badges(badge_type)"))

        # page_views table already exists in models.py with different schema
        # Skip creating it here

        connection.commit()
        print("✅ Created all new feature tables successfully")


def downgrade():
    """Drop new feature tables."""
    with engine.connect() as connection:
        # Drop tables in reverse order to handle foreign key dependencies
        tables = [
            "customer_badges",
            "loyalty_transactions",
            "loyalty_accounts",
            "affiliate_payouts",
            "affiliate_referrals",
            "affiliates",
            "group_contributions",
            "group_purchases"
        ]

        for table in tables:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

        connection.commit()
        print("✅ Dropped all new feature tables")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()