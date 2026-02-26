"""Add sale_start_date and sale_start_time columns to events table."""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path("tickets.db")
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'sale_start_date' in columns and 'sale_start_time' in columns:
            print("✅ Columns sale_start_date and sale_start_time already exist")
            return

        # Add columns if they don't exist
        if 'sale_start_date' not in columns:
            cursor.execute("ALTER TABLE events ADD COLUMN sale_start_date VARCHAR(20)")
            print("✅ Added column sale_start_date")

        if 'sale_start_time' not in columns:
            cursor.execute("ALTER TABLE events ADD COLUMN sale_start_time VARCHAR(10)")
            print("✅ Added column sale_start_time")

        conn.commit()
        print("✅ Migration completed successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
