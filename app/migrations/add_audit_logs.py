"""Add audit_logs table for immutable operation tracking."""

from sqlalchemy import Column, Integer, String, Text, DateTime, inspect, text
from datetime import datetime, timezone

TABLE_NAME = "audit_logs"


def utcnow():
    return datetime.now(timezone.utc)


def run_migration(engine=None):
    if engine is None:
        from app.database import engine as _engine
        engine = _engine

    inspector = inspect(engine)
    if TABLE_NAME in inspector.get_table_names():
        return f"Table {TABLE_NAME} already exists"

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action VARCHAR(100) NOT NULL,
                actor VARCHAR(255) NOT NULL,
                resource_type VARCHAR(100),
                resource_id INTEGER,
                detail TEXT,
                ip_address VARCHAR(45),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Add indexes
        conn.execute(text("CREATE INDEX ix_audit_logs_action ON audit_logs (action)"))
        conn.execute(text("CREATE INDEX ix_audit_logs_actor ON audit_logs (actor)"))
        conn.execute(text("CREATE INDEX ix_audit_logs_resource_id ON audit_logs (resource_id)"))
        conn.execute(text("CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)"))

    return f"Table {TABLE_NAME} created successfully"
