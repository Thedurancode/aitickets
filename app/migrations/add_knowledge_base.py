"""Migration to add knowledge_documents and knowledge_chunks tables for RAG."""

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

        if "knowledge_documents" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE knowledge_documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venue_id INTEGER REFERENCES venues(id),
                        event_id INTEGER REFERENCES events(id),
                        title VARCHAR(500) NOT NULL,
                        source_filename VARCHAR(500),
                        content_type VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE knowledge_documents (
                        id SERIAL PRIMARY KEY,
                        venue_id INTEGER REFERENCES venues(id),
                        event_id INTEGER REFERENCES events(id),
                        title VARCHAR(500) NOT NULL,
                        source_filename VARCHAR(500),
                        content_type VARCHAR(20) NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_knowledge_documents_venue_id ON knowledge_documents(venue_id)"
            ))
            conn.execute(text(
                "CREATE INDEX ix_knowledge_documents_event_id ON knowledge_documents(event_id)"
            ))
            results.append("Created knowledge_documents table")

        if "knowledge_chunks" not in existing_tables:
            if is_sqlite:
                conn.execute(text("""
                    CREATE TABLE knowledge_chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL REFERENCES knowledge_documents(id),
                        content TEXT NOT NULL,
                        embedding TEXT,
                        chunk_index INTEGER NOT NULL
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE knowledge_chunks (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER NOT NULL REFERENCES knowledge_documents(id),
                        content TEXT NOT NULL,
                        embedding TEXT,
                        chunk_index INTEGER NOT NULL
                    )
                """))
            conn.execute(text(
                "CREATE INDEX ix_knowledge_chunks_document_id ON knowledge_chunks(document_id)"
            ))
            results.append("Created knowledge_chunks table")

        conn.commit()

    print("\n".join(results) if results else "knowledge base tables already exist")
    return results


if __name__ == "__main__":
    run_migration()
