"""
Migration: Add Refund Tracking and Dynamic Pricing Fields

Adds:
1. Refund tracking to tickets table (reason, amount, refund_id, refunded_at)
2. Dynamic pricing fields to ticket_tiers table (base_price, min/max, automation)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.database import engine


def run_migration():
    """Add refund and dynamic pricing fields."""
    results = []
    inspector = inspect(engine)

    with engine.connect() as conn:
        # Get existing columns
        tickets_columns = [col['name'] for col in inspector.get_columns('tickets')]
        tiers_columns = [col['name'] for col in inspector.get_columns('ticket_tiers')]
        # Add refund tracking fields to tickets table
        if 'refund_reason' not in tickets_columns:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN refund_reason VARCHAR(255)"))
            results.append("✅ Added refund_reason to tickets")

        if 'refund_amount_cents' not in tickets_columns:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN refund_amount_cents INTEGER"))
            results.append("✅ Added refund_amount_cents to tickets")

        if 'refunded_at' not in tickets_columns:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN refunded_at TIMESTAMP"))
            results.append("✅ Added refunded_at to tickets")

        if 'stripe_refund_id' not in tickets_columns:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN stripe_refund_id VARCHAR(255)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_stripe_refund_id ON tickets (stripe_refund_id)"))
            results.append("✅ Added stripe_refund_id to tickets with index")

        # Add dynamic pricing fields to ticket_tiers table
        if 'base_price' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN base_price INTEGER"))
            results.append("✅ Added base_price to ticket_tiers")

        if 'dynamic_pricing_enabled' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN dynamic_pricing_enabled BOOLEAN DEFAULT FALSE"))
            results.append("✅ Added dynamic_pricing_enabled to ticket_tiers")

        if 'min_price' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN min_price INTEGER"))
            results.append("✅ Added min_price to ticket_tiers")

        if 'max_price' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN max_price INTEGER"))
            results.append("✅ Added max_price to ticket_tiers")

        if 'last_price_update' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN last_price_update TIMESTAMP"))
            results.append("✅ Added last_price_update to ticket_tiers")

        if 'price_update_reason' not in tiers_columns:
            conn.execute(text("ALTER TABLE ticket_tiers ADD COLUMN price_update_reason VARCHAR(255)"))
            results.append("✅ Added price_update_reason to ticket_tiers")

        # Backfill base_price with current price for existing tiers
        if 'base_price' not in tiers_columns:
            conn.execute(text("UPDATE ticket_tiers SET base_price = price WHERE base_price IS NULL"))
            results.append("✅ Backfilled base_price from current price")

        conn.commit()

    for result in results:
        print(result)

    if not results:
        print("✅ All fields already exist - no migration needed")
    else:
        print(f"\n✅ Migration complete: {len(results)} changes applied")

    return results


if __name__ == "__main__":
    run_migration()
