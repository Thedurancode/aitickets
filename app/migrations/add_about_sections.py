"""Migration to add about_sections table with default content."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


# Default content seeded on first run
DEFAULT_SECTIONS = {
    "hero_title": "About Us",
    "hero_subtitle": "Get to know who we are",
    "hero_image_url": "",
    "mission_title": "Our Mission",
    "mission_content": "We're dedicated to creating unforgettable experiences for every fan.",
    "story_title": "Our Story",
    "story_content": "",
    "team_members": "[]",
    "contact_email": "",
    "contact_phone": "",
    "contact_address": "",
    "social_links": "{}",
}


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        is_sqlite = "sqlite" in str(engine.url)

        if "about_sections" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE about_sections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        section_key VARCHAR(50) UNIQUE NOT NULL,
                        content TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE about_sections (
                        id SERIAL PRIMARY KEY,
                        section_key VARCHAR(50) UNIQUE NOT NULL,
                        content TEXT,
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            results.append("Created about_sections table")

            # Seed default content
            for key, content in DEFAULT_SECTIONS.items():
                conn.execute(
                    text("INSERT INTO about_sections (section_key, content) VALUES (:key, :content)"),
                    {"key": key, "content": content},
                )
            results.append(f"Seeded {len(DEFAULT_SECTIONS)} default sections")

        conn.commit()

    print("\n".join(results) if results else "about_sections table already exists")
    return results


if __name__ == "__main__":
    run_migration()
