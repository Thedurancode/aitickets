"""
Migration: Add social_media_posts table for tracking published posts

This enables updating posts when event/ticket information changes.
"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """Create social_media_posts table."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS social_media_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                platform_post_id VARCHAR(255) NOT NULL,
                post_url VARCHAR(500),
                content TEXT,
                image_url VARCHAR(500),
                is_published BOOLEAN DEFAULT 1,
                is_deleted BOOLEAN DEFAULT 0,
                scheduled_for TIMESTAMP,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
        """))

        # Create indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_social_media_posts_event_id
            ON social_media_posts(event_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_social_media_posts_platform
            ON social_media_posts(platform)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_social_media_posts_published_at
            ON social_media_posts(published_at)
        """))

        conn.commit()
        print("✅ Created social_media_posts table")


def downgrade():
    """Drop social_media_posts table."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS social_media_posts"))
        conn.commit()
        print("✅ Dropped social_media_posts table")


if __name__ == "__main__":
    upgrade()
