"""
Full-Text Search with DuckDB

Provides ranked BM25 search across events, venues, customers, and tickets.
Zero infrastructure — single file database, instant indexing.
"""

import duckdb
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# DuckDB database path
FTS_DB_PATH = Path(__file__).parent.parent.parent / "data" / "fts_search.duckdb"


class FTSSearch:
    """Full-text search engine using DuckDB with BM25 scoring."""

    def __init__(self):
        self.db_path = str(FTS_DB_PATH)
        self._ensure_db()

    def _get_conn(self):
        conn = duckdb.connect(self.db_path)
        conn.execute("INSTALL fts; LOAD fts;")
        return conn

    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        FTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events_fts (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                description VARCHAR,
                venue_name VARCHAR,
                venue_address VARCHAR,
                event_date VARCHAR,
                event_time VARCHAR,
                artist_name VARCHAR,
                artist_genre VARCHAR,
                categories VARCHAR,
                tier_names VARCHAR,
                promoter_name VARCHAR
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers_fts (
                id INTEGER PRIMARY KEY,
                name VARCHAR,
                email VARCHAR,
                phone VARCHAR,
                notes VARCHAR,
                preferences VARCHAR,
                ticket_history VARCHAR
            )
        """)
        conn.close()
        logger.info("FTS database initialized")

    def sync_events(self, db: Session):
        """Sync all events from SQLAlchemy to DuckDB FTS index."""
        from app.models import Event, Venue, TicketTier, Artist

        events = db.query(Event).all()
        conn = self._get_conn()

        # Clear and rebuild
        conn.execute("DELETE FROM events_fts")

        for event in events:
            venue = db.query(Venue).filter(Venue.id == event.venue_id).first()
            artist = db.query(Artist).filter(Artist.id == event.artist_id).first() if event.artist_id else None
            tiers = db.query(TicketTier).filter(TicketTier.event_id == event.id).all()

            conn.execute("""
                INSERT INTO events_fts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                event.id,
                event.name or '',
                event.description or '',
                venue.name if venue else '',
                venue.address if venue else '',
                event.event_date or '',
                event.event_time or '',
                artist.name if artist else '',
                artist.genre if artist else '',
                '',  # categories
                ', '.join([t.name for t in tiers]) if tiers else '',
                getattr(event, 'promoter_name', '') or '',
            ])

        # Drop existing index if present
        try:
            conn.execute("PRAGMA drop_fts_index('events_fts')")
        except:
            pass

        # Create FTS index on searchable columns
        conn.execute("""
            PRAGMA create_fts_index('events_fts', 'id',
                'name', 'description', 'venue_name', 'venue_address',
                'artist_name', 'artist_genre', 'tier_names', 'promoter_name')
        """)

        count = conn.execute("SELECT COUNT(*) FROM events_fts").fetchone()[0]
        conn.close()
        logger.info(f"FTS index synced: {count} events")
        return count

    def sync_customers(self, db: Session):
        """Sync all customers from SQLAlchemy to DuckDB FTS index."""
        from app.models import EventGoer, CustomerNote

        customers = db.query(EventGoer).all()
        conn = self._get_conn()

        conn.execute("DELETE FROM customers_fts")

        for customer in customers:
            notes = db.query(CustomerNote).filter(
                CustomerNote.event_goer_id == customer.id
            ).all() if hasattr(CustomerNote, 'event_goer_id') else []

            conn.execute("""
                INSERT INTO customers_fts VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                customer.id,
                customer.name or '',
                customer.email or '',
                customer.phone or '',
                ' '.join([n.note for n in notes if hasattr(n, 'note')]) if notes else '',
                '',  # preferences
                '',  # ticket history
            ])

        try:
            conn.execute("PRAGMA drop_fts_index('customers_fts')")
        except:
            pass

        conn.execute("""
            PRAGMA create_fts_index('customers_fts', 'id',
                'name', 'email', 'phone', 'notes', 'preferences')
        """)

        count = conn.execute("SELECT COUNT(*) FROM customers_fts").fetchone()[0]
        conn.close()
        logger.info(f"FTS index synced: {count} customers")
        return count

    def search_events(self, query: str, limit: int = 10, conjunctive: bool = False) -> List[Dict[str, Any]]:
        """Search events with BM25 ranking."""
        conn = self._get_conn()
        try:
            conj = 1 if conjunctive else 0
            results = conn.execute(f"""
                SELECT id, name, description, venue_name, artist_name, event_date,
                       fts_main_events_fts.match_bm25(id, ?, conjunctive := {conj}) AS score
                FROM events_fts
                WHERE score IS NOT NULL
                ORDER BY score DESC
                LIMIT ?
            """, [query, limit]).fetchall()

            return [{
                "id": r[0],
                "name": r[1],
                "description": (r[2] or '')[:200],
                "venue": r[3],
                "artist": r[4],
                "date": r[5],
                "score": round(r[6], 3),
            } for r in results]
        except Exception as e:
            logger.error(f"FTS search failed: {e}")
            return []
        finally:
            conn.close()

    def search_customers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search customers with BM25 ranking."""
        conn = self._get_conn()
        try:
            results = conn.execute("""
                SELECT id, name, email, phone,
                       fts_main_customers_fts.match_bm25(id, ?) AS score
                FROM customers_fts
                WHERE score IS NOT NULL
                ORDER BY score DESC
                LIMIT ?
            """, [query, limit]).fetchall()

            return [{
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "phone": r[3],
                "score": round(r[4], 3),
            } for r in results]
        except Exception as e:
            logger.error(f"FTS customer search failed: {e}")
            return []
        finally:
            conn.close()

    def search_all(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search across all indexed content."""
        return {
            "query": query,
            "events": self.search_events(query, limit),
            "customers": self.search_customers(query, limit),
        }


# Singleton
fts_search = FTSSearch()
