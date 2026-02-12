import logging
from importlib import import_module

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Fix postgres:// to postgresql:// for SQLAlchemy compatibility
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure engine based on database type
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 min to avoid stale handles
        pool_pre_ping=True,  # Verify connections are alive before using them
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Ordered list of migration modules to run
MIGRATIONS = [
    "add_stripe_columns",
    "add_categories",
    "add_segments",
    "add_promo_codes",
    "add_page_views",
    "add_promoter_fields",
    "add_visibility_and_tier_status",
    "add_ticket_utm",
    "add_series_id",
    "add_post_event_media",
    "add_category_image",
    "add_waitlist",
    "add_marketing_lists",
    "add_auto_reminders",
    "add_missing_indexes",
    "add_automation_tables",
    "add_magic_links",
    "add_conversation_sessions",
]


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_migrations_table(conn):
    """Create the migrations_applied tracking table if it doesn't exist."""
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS migrations_applied ("
        "  name VARCHAR(255) PRIMARY KEY,"
        "  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    ))
    conn.commit()


def _get_applied_migrations(conn):
    """Return the set of migration names already applied."""
    result = conn.execute(text("SELECT name FROM migrations_applied"))
    return {row[0] for row in result}


def _record_migration(conn, name):
    """Record a migration as applied."""
    conn.execute(
        text("INSERT INTO migrations_applied (name) VALUES (:name)"),
        {"name": name},
    )
    conn.commit()


def init_db():
    """Initialize the database, creating all tables and running migrations."""
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        _ensure_migrations_table(conn)
        applied = _get_applied_migrations(conn)

        for name in MIGRATIONS:
            if name in applied:
                continue

            logger.info("Running migration: %s", name)
            try:
                module = import_module(f"app.migrations.{name}")
                module.run_migration()
                _record_migration(conn, name)
                logger.info("Migration applied: %s", name)
            except Exception:
                logger.exception("Migration failed: %s", name)
                raise
