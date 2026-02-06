from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# Fix postgres:// to postgresql:// for SQLAlchemy compatibility
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure engine based on database type
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database, creating all tables and running migrations."""
    Base.metadata.create_all(bind=engine)

    # Run migrations for existing databases
    try:
        from app.migrations.add_stripe_columns import run_migration
        run_migration()
    except Exception as e:
        print(f"Migration note: {e}")

    try:
        from app.migrations.add_categories import run_migration as run_categories_migration
        run_categories_migration()
    except Exception as e:
        print(f"Migration note: {e}")

    try:
        from app.migrations.add_segments import run_migration as run_segments_migration
        run_segments_migration()
    except Exception as e:
        print(f"Migration note: {e}")
