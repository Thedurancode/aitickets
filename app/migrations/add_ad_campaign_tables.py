"""
Migration: Add ad campaign tables for automated Meta & Google Ads integration

Creates 4 new tables:
- ad_campaigns: Campaign containers with platform, type, budget, schedule
- ad_creatives: Individual ads with headline, body, targeting, images
- ad_campaign_performance: Daily campaign-level metrics
- ad_performance: Daily ad-level performance tracking

Run with: python -m app.migrations.add_ad_campaign_tables
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, JSON, Numeric, Enum as SQLEnum, func, text
from app.database import Base, engine
from app.config import get_settings
import enum


class CampaignPlatform(str, enum.Enum):
    META = "meta"  # Facebook/Instagram
    GOOGLE = "google"  # Google Ads
    EMAIL = "email"  # Email campaigns
    SMS = "sms"  # SMS campaigns


class CampaignType(str, enum.Enum):
    AWARENESS = "awareness"  # Brand awareness
    CONVERSION = "conversion"  # Ticket sales
    SEARCH = "search"  # Google Search
    DISPLAY = "display"  # Display ads
    NURTURE = "nurture"  # Email/SMS nurture


class AdStatus(str, enum.Enum):
    DRAFT = "draft"  # Not yet approved
    APPROVED = "approved"  # Approved, ready to publish
    ACTIVE = "active"  # Published and running
    PAUSED = "paused"  # Paused
    COMPLETED = "completed"  # Campaign ended
    FAILED = "failed"  # Failed to publish


def run_migration():
    """Run the migration (standard interface)."""
    upgrade()


def upgrade():
    """Create ad campaign tables."""
    from app.database import engine

    # Import models to ensure they're registered
    from app.models import Event

    # Define tables using raw SQL to avoid dependency issues
    from sqlalchemy import Table, MetaData
    metadata = MetaData()

    # Check if tables already exist
    metadata.reflect(bind=engine)
    if "ad_campaigns" in metadata.tables:
        print("✅ Ad campaign tables already exist. Skipping migration.")
        return

    with engine.begin() as conn:
        # Create ad_campaigns table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ad_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                platform VARCHAR(20) NOT NULL,
                campaign_type VARCHAR(20) NOT NULL,
                name VARCHAR(255) NOT NULL,
                budget INTEGER,
                daily_budget INTEGER,
                start_date DATE,
                end_date DATE,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                platform_campaign_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        """))

        # Create ad_creatives table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ad_creatives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                headline VARCHAR(255) NOT NULL,
                body TEXT,
                image_url VARCHAR(500),
                cta_text VARCHAR(50),
                link_url VARCHAR(500),
                targeting JSON,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                platform_ad_id VARCHAR(255),
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spend INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES ad_campaigns (id) ON DELETE CASCADE
            )
        """))

        # Create ad_campaign_performance table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ad_campaign_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                date DATE NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spend INTEGER DEFAULT 0,
                revenue INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES ad_campaigns (id) ON DELETE CASCADE,
                UNIQUE (campaign_id, date)
            )
        """))

        # Create ad_performance table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ad_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id INTEGER NOT NULL,
                date DATE NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spend INTEGER DEFAULT 0,
                revenue INTEGER DEFAULT 0,
                engagement_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_id) REFERENCES ad_creatives (id) ON DELETE CASCADE,
                UNIQUE (ad_id, date)
            )
        """))

        # Create indexes for performance
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_campaigns_event_id ON ad_campaigns (event_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_campaigns_platform ON ad_campaigns (platform)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_campaigns_status ON ad_campaigns (status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_creatives_campaign_id ON ad_creatives (campaign_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_creatives_status ON ad_creatives (status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_campaign_performance_date ON ad_campaign_performance (date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ad_performance_date ON ad_performance (date)"))

        print("✅ Created ad_campaigns table")
        print("✅ Created ad_creatives table")
        print("✅ Created ad_campaign_performance table")
        print("✅ Created ad_performance table")
        print("✅ Created indexes for ad campaign tables")


def downgrade():
    """Drop ad campaign tables."""
    from app.database import engine

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ad_performance"))
        conn.execute(text("DROP TABLE IF EXISTS ad_campaign_performance"))
        conn.execute(text("DROP TABLE IF EXISTS ad_creatives"))
        conn.execute(text("DROP TABLE IF EXISTS ad_campaigns"))

        print("✅ Dropped all ad campaign tables")


if __name__ == "__main__":
    print("Running migration: add_ad_campaign_tables")
    upgrade()
    print("Migration complete!")
