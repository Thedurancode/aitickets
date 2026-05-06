"""
Full-Text Search API Router

Provides ranked BM25 search across events and customers via DuckDB.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.fts_search import fts_search

router = APIRouter(prefix="/fts", tags=["full-text-search"])


@router.post("/sync")
def sync_fts_index(db: Session = Depends(get_db)):
    """Rebuild the full-text search index from current data."""
    events_count = fts_search.sync_events(db)
    customers_count = fts_search.sync_customers(db)
    return {
        "success": True,
        "events_indexed": events_count,
        "customers_indexed": customers_count,
    }


@router.get("/search")
def search_all(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search across all indexed content with BM25 ranking."""
    return fts_search.search_all(q, limit)


@router.get("/events")
def search_events(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    exact: bool = Query(default=False, description="Require all terms to match"),
):
    """Search events with BM25 ranking."""
    results = fts_search.search_events(q, limit, conjunctive=exact)
    return {"query": q, "count": len(results), "results": results}


@router.get("/customers")
def search_customers(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Search customers with BM25 ranking."""
    results = fts_search.search_customers(q, limit)
    return {"query": q, "count": len(results), "results": results}
