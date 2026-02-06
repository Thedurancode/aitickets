"""
Migration to add Stripe columns to ticket_tiers table.

Run this script to add the stripe_product_id and stripe_price_id columns
to existing databases.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    """Add Stripe columns to ticket_tiers table if they don't exist."""
    results = []

    with engine.connect() as conn:
        # Get inspector to check existing columns
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('ticket_tiers')]
        results.append(f"Existing columns: {existing_columns}")

        # Add stripe_product_id if it doesn't exist
        if 'stripe_product_id' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN stripe_product_id VARCHAR(255)"))
                conn.commit()
                results.append("Added stripe_product_id column")
            except Exception as e:
                results.append(f"Error adding stripe_product_id: {e}")
        else:
            results.append("stripe_product_id column already exists")

        # Add stripe_price_id if it doesn't exist
        if 'stripe_price_id' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN stripe_price_id VARCHAR(255)"))
                conn.commit()
                results.append("Added stripe_price_id column")
            except Exception as e:
                results.append(f"Error adding stripe_price_id: {e}")
        else:
            results.append("stripe_price_id column already exists")

        # Create indexes
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ticket_tiers_stripe_product_id ON ticket_tiers (stripe_product_id)"))
            conn.commit()
            results.append("Created index on stripe_product_id")
        except Exception as e:
            results.append(f"Index note: {e}")

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ticket_tiers_stripe_price_id ON ticket_tiers (stripe_price_id)"))
            conn.commit()
            results.append("Created index on stripe_price_id")
        except Exception as e:
            results.append(f"Index note: {e}")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
