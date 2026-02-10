"""
Migration to add missing indexes on foreign key columns.

Improves query performance for JOINs, lookups by Stripe IDs,
and filtering by event/customer/ticket relationships.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.database import engine


# (index_name, table, column)
INDEXES = [
    ("ix_events_venue_id", "events", "venue_id"),
    ("ix_event_photos_event_id", "event_photos", "event_id"),
    ("ix_event_updates_event_id", "event_updates", "event_id"),
    ("ix_ticket_tiers_event_id", "ticket_tiers", "event_id"),
    ("ix_tickets_ticket_tier_id", "tickets", "ticket_tier_id"),
    ("ix_tickets_event_goer_id", "tickets", "event_goer_id"),
    ("ix_tickets_stripe_payment_intent_id", "tickets", "stripe_payment_intent_id"),
    ("ix_tickets_stripe_checkout_session_id", "tickets", "stripe_checkout_session_id"),
    ("ix_notifications_event_goer_id", "notifications", "event_goer_id"),
    ("ix_notifications_event_id", "notifications", "event_id"),
    ("ix_notifications_ticket_id", "notifications", "ticket_id"),
    ("ix_customer_notes_event_goer_id", "customer_notes", "event_goer_id"),
    ("ix_promo_codes_event_id", "promo_codes", "event_id"),
    ("ix_page_views_event_id", "page_views", "event_id"),
]


def run_migration():
    """Create missing indexes on foreign key columns."""
    results = []

    with engine.connect() as conn:
        for index_name, table, column in INDEXES:
            try:
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"
                ))
                conn.commit()
                results.append(f"Created index {index_name}")
            except Exception as e:
                results.append(f"Index {index_name}: {e}")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    run_migration()
