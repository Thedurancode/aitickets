"""Migration to add promo_codes table and promo columns to tickets."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    results = []

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Create promo_codes table
        if "promo_codes" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    discount_type VARCHAR(20) NOT NULL,
                    discount_value INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    valid_from DATETIME,
                    valid_until DATETIME,
                    max_uses INTEGER,
                    uses_count INTEGER DEFAULT 0,
                    event_id INTEGER REFERENCES events(id),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_promo_codes_code ON promo_codes (code)"
            ))
            conn.commit()
            results.append("Created promo_codes table")
        else:
            results.append("promo_codes table already exists")

        # Add promo columns to tickets table
        existing_columns = [c["name"] for c in inspector.get_columns("tickets")]

        if "promo_code_id" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN promo_code_id INTEGER REFERENCES promo_codes(id)"
            ))
            conn.commit()
            results.append("Added promo_code_id to tickets")

        if "discount_amount_cents" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE tickets ADD COLUMN discount_amount_cents INTEGER"
            ))
            conn.commit()
            results.append("Added discount_amount_cents to tickets")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
