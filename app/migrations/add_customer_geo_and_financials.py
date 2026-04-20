"""Add geo fields to event_goers, timezone to customer_preferences, and financial breakdown to tickets."""

from sqlalchemy import inspect, text


def run_migration(engine=None):
    if engine is None:
        from app.database import engine as _engine
        engine = _engine

    inspector = inspect(engine)

    with engine.begin() as conn:
        # --- EventGoer: address / geo columns ---
        existing_goer_cols = {c["name"] for c in inspector.get_columns("event_goers")}
        if "postal_code" not in existing_goer_cols:
            conn.execute(text("ALTER TABLE event_goers ADD COLUMN postal_code VARCHAR(20)"))
            conn.execute(text("CREATE INDEX ix_event_goers_postal_code ON event_goers (postal_code)"))
        if "state" not in existing_goer_cols:
            conn.execute(text("ALTER TABLE event_goers ADD COLUMN state VARCHAR(100)"))
        if "country" not in existing_goer_cols:
            conn.execute(text("ALTER TABLE event_goers ADD COLUMN country VARCHAR(100)"))

        # --- CustomerPreference: timezone ---
        existing_pref_cols = {c["name"] for c in inspector.get_columns("customer_preferences")}
        if "timezone" not in existing_pref_cols:
            conn.execute(text("ALTER TABLE customer_preferences ADD COLUMN timezone VARCHAR(50)"))

        # --- Ticket: financial breakdown ---
        existing_ticket_cols = {c["name"] for c in inspector.get_columns("tickets")}
        if "net_amount_cents" not in existing_ticket_cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN net_amount_cents INTEGER"))
        if "platform_fee_cents" not in existing_ticket_cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN platform_fee_cents INTEGER"))
        if "processing_fee_cents" not in existing_ticket_cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN processing_fee_cents INTEGER"))
        if "refunded_at" not in existing_ticket_cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN refunded_at TIMESTAMP"))
        if "refund_amount_cents" not in existing_ticket_cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN refund_amount_cents INTEGER"))

    return "Added geo fields, customer timezone, and ticket financial columns"
