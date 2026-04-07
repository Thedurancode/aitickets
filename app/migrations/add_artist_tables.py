"""
Add Artist and ArtistResearch tables for permanent storage of artist data.

This migration adds comprehensive artist data storage to remember all research
discoveries (Spotify stats, social media, demographics, etc.) permanently.
"""

from sqlalchemy import text

def run_migration():
    """Create Artist and ArtistResearch tables."""
    from app.database import engine

    with engine.connect() as conn:
        # Create artists table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,

                -- Spotify Data
                spotify_id VARCHAR(100),
                spotify_followers INTEGER,
                spotify_monthly_listeners INTEGER,
                spotify_popularity INTEGER,
                spotify_top_tracks TEXT,
                spotify_genres TEXT,
                spotify_image_url VARCHAR(500),

                -- YouTube Data
                youtube_channel_id VARCHAR(100),
                youtube_channel_name VARCHAR(255),
                youtube_subscribers INTEGER,
                youtube_view_count BIGINT,
                youtube_video_count INTEGER,
                youtube_latest_videos TEXT,

                -- Social Media
                instagram_handle VARCHAR(100),
                instagram_followers INTEGER,
                twitter_handle VARCHAR(100),
                twitter_followers INTEGER,
                tiktok_handle VARCHAR(100),
                tiktok_followers INTEGER,
                facebook_page VARCHAR(255),
                facebook_likes INTEGER,

                -- Artist Information
                genre VARCHAR(100),
                sub_genres TEXT,
                bio TEXT,
                achievements TEXT,
                similar_artists TEXT,
                country_of_origin VARCHAR(100),
                active_since_year INTEGER,

                -- Fan Demographics
                fan_demographics TEXT,
                primary_markets TEXT,
                fan_interests TEXT,

                -- Performance Metrics
                average_ticket_price INTEGER,
                typical_venue_size VARCHAR(50),
                sellout_velocity VARCHAR(50),

                -- Research Metadata
                last_researched_at TIMESTAMP,
                research_version INTEGER DEFAULT 1,
                data_source VARCHAR(100),
                confidence_score REAL,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create index on artist name for fast lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name)
        """))

        # Create index on social media handles
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artists_spotify ON artists(spotify_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artists_instagram ON artists(instagram_handle)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artists_youtube ON artists(youtube_channel_id)
        """))

        # Create artist_research table for historical snapshots
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS artist_research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id INTEGER NOT NULL,
                event_id INTEGER,

                -- Research data
                research_data TEXT NOT NULL,
                trigger VARCHAR(50),

                -- Snapshot metrics
                spotify_listeners_snapshot INTEGER,
                instagram_followers_snapshot INTEGER,
                youtube_subscribers_snapshot INTEGER,

                -- Research quality
                sources_checked TEXT,
                data_completeness REAL,

                -- Timestamps
                researched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                research_duration_ms INTEGER,

                FOREIGN KEY (artist_id) REFERENCES artists(id),
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """))

        # Create indexes for research table
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artist_research_artist ON artist_research(artist_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artist_research_event ON artist_research(event_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_artist_research_date ON artist_research(researched_at)
        """))

        # Add artist_id column to events table
        conn.execute(text("""
            ALTER TABLE events ADD COLUMN artist_id INTEGER REFERENCES artists(id)
        """))

        # Create index on events.artist_id
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_events_artist ON events(artist_id)
        """))

        conn.commit()

    print("✓ Created artists table with comprehensive data fields")
    print("✓ Created artist_research table for historical tracking")
    print("✓ Added artist_id to events table")
    print("✓ Created indexes for fast lookups")