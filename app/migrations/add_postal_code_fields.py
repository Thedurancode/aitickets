"""
Migration: Add postal code and geographic fields to event_goers table

Date: 2024-04-01

Run from project root:
    python3 -m app.migrations.add_postal_code_fields
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.database import SessionLocal


def upgrade():
    """Add postal_code, city, state, country columns to customer_preferences."""
    db = SessionLocal()

    def column_exists(table_name, column_name):
        """Check if column exists in table (SQLite compatible)."""
        result = db.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]
        return column_name in columns

    try:
        # Add postal_code column (if not exists)
        if not column_exists("customer_preferences", "postal_code"):
            db.execute(text("ALTER TABLE customer_preferences ADD COLUMN postal_code VARCHAR(20)"))
            print("✅ Added postal_code column")
        else:
            print("⏭️  postal_code column already exists")

        # Add city column
        if not column_exists("customer_preferences", "city"):
            db.execute(text("ALTER TABLE customer_preferences ADD COLUMN city VARCHAR(100)"))
            print("✅ Added city column")
        else:
            print("⏭️  city column already exists")

        # Add state column
        if not column_exists("customer_preferences", "state"):
            db.execute(text("ALTER TABLE customer_preferences ADD COLUMN state VARCHAR(50)"))
            print("✅ Added state column")
        else:
            print("⏭️  state column already exists")

        # Add country column
        if not column_exists("customer_preferences", "country"):
            db.execute(text("ALTER TABLE customer_preferences ADD COLUMN country VARCHAR(50) DEFAULT 'US'"))
            print("✅ Added country column")
        else:
            print("⏭️  country column already exists")

        # Create index on postal_code (if not exists)
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_preferences_postal_code ON customer_preferences(postal_code)"))
            print("✅ Created postal_code index")
        except:
            print("⏭️  postal_code index already exists")

        db.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()


def downgrade():
    """Remove postal_code, city, state, country columns from customer_preferences.

    Note: SQLite doesn't support DROP COLUMN directly.
    This would require recreating the table without these columns.
    For safety, this is not implemented for SQLite databases.
    """
    print("⚠️  Downgrade not supported for SQLite databases")
    print("   To remove columns, manually recreate the customer_preferences table")


if __name__ == "__main__":
    upgrade()
