#!/usr/bin/env python3
"""Initialize the database with all required tables."""
import sys
from app.database import Base, engine
from app import models  # This imports all models
from app import models_extensions  # Import new feature models

def init_database():
    """Create all tables and run migrations."""
    print("Initializing database...")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Created base tables")

    print("Database initialization complete!")

if __name__ == "__main__":
    init_database()