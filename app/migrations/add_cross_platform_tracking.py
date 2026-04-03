"""
Migration: Add Cross-Platform Page View Tracking
Created: 2025-01-XX
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from app.database import Base, engine


def upgrade():
    """Add cross-platform tracking fields to page_views table."""
    from sqlalchemy import text

    with engine.begin() as conn:
        # Add new columns for cross-platform tracking
        # Note: user_agent and referrer already exist in the table
        conn.execute(text("""
            ALTER TABLE page_views
            ADD COLUMN platform VARCHAR(50) DEFAULT 'internal'
        """))

        conn.execute(text("""
            ALTER TABLE page_views
            ADD COLUMN external_platform_id VARCHAR(255)
        """))

        conn.execute(text("""
            ALTER TABLE page_views
            ADD COLUMN platform_api_response TEXT
        """))

        # Create index for faster platform-based queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pageviews_platform
            ON page_views(platform, event_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pageviews_external_id
            ON page_views(external_platform_id)
        """))

        print("✅ Added cross-platform tracking columns to page_views")


def downgrade():
    """Remove cross-platform tracking fields."""
    from sqlalchemy import text

    with engine.begin() as conn:
        # SQLite doesn't support DROP COLUMN directly
        # Would need to recreate table in production
        print("⚠️  Downgrade not implemented for SQLite")


def run_migration():
    """Run the migration (standard interface)."""
    upgrade()


if __name__ == "__main__":
    run_migration()
