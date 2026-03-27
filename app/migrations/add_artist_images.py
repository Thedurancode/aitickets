"""Migration to add artist image fields to events table.

Adds support for:
- artist_image_url: Single primary artist/performer image
- additional_images: JSON array of additional image URLs (artist photos, venue, etc.)
- performer_names: JSON array of performer/artist names
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

        # Check if columns exist
        columns = [col["name"] for col in inspector.get_columns("events")]

        # Add artist_image_url column
        if "artist_image_url" not in columns:
            conn.execute(text("""
                ALTER TABLE events
                ADD COLUMN artist_image_url VARCHAR(500)
            """))
            results.append("✅ Added artist_image_url column")
        else:
            results.append("⏭️  artist_image_url column already exists")

        # Add additional_images JSON column
        if "additional_images" not in columns:
            conn.execute(text("""
                ALTER TABLE events
                ADD COLUMN additional_images TEXT
            """))
            results.append("✅ Added additional_images column (stores JSON array)")
        else:
            results.append("⏭️  additional_images column already exists")

        # Add performer_names JSON column
        if "performer_names" not in columns:
            conn.execute(text("""
                ALTER TABLE events
                ADD COLUMN performer_names TEXT
            """))
            results.append("✅ Added performer_names column (stores JSON array)")
        else:
            results.append("⏭️  performer_names column already exists")

        conn.commit()

    return results


if __name__ == "__main__":
    print("🎨 Adding Artist Image Support to Events...\n")
    results = run_migration()
    for result in results:
        print(result)
    print("\n✨ Migration complete!")
    print("\nUsage examples:")
    print("  artist_image_url: 'https://example.com/artist.jpg'")
    print("  additional_images: '[\"url1.jpg\", \"url2.jpg\", \"url3.jpg\"]'")
    print("  performer_names: '[\"Artist Name\", \"Supporting Act\"]'")
