"""Migration to add webhook_endpoints and webhook_deliveries tables."""

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
        is_sqlite = "sqlite" in str(engine.url)

        if "webhook_endpoints" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE webhook_endpoints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url VARCHAR(500) NOT NULL,
                        secret VARCHAR(255) NOT NULL,
                        description VARCHAR(500),
                        event_types TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE webhook_endpoints (
                        id SERIAL PRIMARY KEY,
                        url VARCHAR(500) NOT NULL,
                        secret VARCHAR(255) NOT NULL,
                        description VARCHAR(500),
                        event_types TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            results.append("Created webhook_endpoints table")

        if "webhook_deliveries" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE webhook_deliveries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint_id INTEGER NOT NULL REFERENCES webhook_endpoints(id),
                        event_type VARCHAR(50) NOT NULL,
                        payload TEXT NOT NULL,
                        response_status INTEGER,
                        response_body TEXT,
                        status VARCHAR(20) DEFAULT 'pending',
                        attempt INTEGER DEFAULT 1,
                        error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE webhook_deliveries (
                        id SERIAL PRIMARY KEY,
                        endpoint_id INTEGER NOT NULL REFERENCES webhook_endpoints(id),
                        event_type VARCHAR(50) NOT NULL,
                        payload TEXT NOT NULL,
                        response_status INTEGER,
                        response_body TEXT,
                        status VARCHAR(20) DEFAULT 'pending',
                        attempt INTEGER DEFAULT 1,
                        error TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        completed_at TIMESTAMPTZ
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_webhook_deliveries_endpoint_id ON webhook_deliveries(endpoint_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_webhook_deliveries_status ON webhook_deliveries(status)"
            ))
            results.append("Created webhook_deliveries table")

        conn.commit()

    print("\n".join(results) if results else "Webhook tables already exist")
    return results


if __name__ == "__main__":
    run_migration()
