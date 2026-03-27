"""Migration to add event_media table for managing event flyer assets.

Adds:
- event_media table for storing artists, logos, sponsors, venue photos, etc.
- Supports automatic flyer generation using all media assets
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Create event_media table if it doesn't exist
        if "event_media" not in tables:
            conn.execute(text("""
                CREATE TABLE event_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    media_type VARCHAR(50) NOT NULL,
                    media_url VARCHAR(500) NOT NULL,
                    label VARCHAR(255),
                    display_order INTEGER DEFAULT 0,
                    media_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
                )
            """))

            # Create indexes
            conn.execute(text("""
                CREATE INDEX ix_event_media_event_id ON event_media (event_id)
            """))

            conn.execute(text("""
                CREATE INDEX ix_event_media_media_type ON event_media (media_type)
            """))

            results.append("✅ Created event_media table")
            results.append("✅ Created indexes on event_id and media_type")
        else:
            results.append("⏭️  event_media table already exists")

        conn.commit()

    return results


if __name__ == "__main__":
    print("🎨 Adding Event Media Management System...\n")
    results = run_migration()
    for result in results:
        print(result)
    print("\n✨ Migration complete!")
    print("\nEvent Media Types Available:")
    print("  - artist_photo: Artist/performer headshots")
    print("  - logo: Event/brand logos")
    print("  - venue_photo: Venue interior/exterior")
    print("  - sponsor_logo: Sponsor logos")
    print("  - background: Background images/textures")
    print("  - graphic: Generic graphic elements")
    print("  - other: Other media types")
