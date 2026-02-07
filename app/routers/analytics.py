"""Analytics router for page view tracking and reporting."""

import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import PageView, Event

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/track", status_code=204)
async def track_page_view(request: Request, db: Session = Depends(get_db)):
    """Lightweight page view tracker. Called by JS on every page load."""
    body = await request.json()

    # Hash IP with daily salt for privacy
    client_ip = request.client.host if request.client else "unknown"
    daily_salt = datetime.utcnow().strftime("%Y-%m-%d")
    ip_hash = hashlib.sha256(f"{client_ip}:{daily_salt}".encode()).hexdigest()

    page_view = PageView(
        event_id=body.get("event_id"),
        page=body.get("page", "unknown"),
        ip_hash=ip_hash,
        user_agent=(request.headers.get("user-agent", "") or "")[:500],
        referrer=(body.get("referrer", "") or "")[:500],
        utm_source=(body.get("utm_source", "") or "")[:100] or None,
        utm_medium=(body.get("utm_medium", "") or "")[:100] or None,
        utm_campaign=(body.get("utm_campaign", "") or "")[:100] or None,
    )
    db.add(page_view)
    db.commit()
    return Response(status_code=204)


@router.get("/events/{event_id}")
def get_event_analytics(
    event_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get analytics for a specific event page."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    cutoff = datetime.utcnow() - timedelta(days=days)
    base_filter = [PageView.event_id == event_id, PageView.created_at >= cutoff]

    total_views = db.query(func.count(PageView.id)).filter(*base_filter).scalar()
    unique_visitors = db.query(func.count(func.distinct(PageView.ip_hash))).filter(*base_filter).scalar()

    # Top referrers
    top_referrers = (
        db.query(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(*base_filter, PageView.referrer != None, PageView.referrer != "")
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    # UTM sources
    utm_sources = (
        db.query(PageView.utm_source, func.count(PageView.id).label("count"))
        .filter(*base_filter, PageView.utm_source != None)
        .group_by(PageView.utm_source)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    # Views per day
    views_by_day = (
        db.query(func.date(PageView.created_at).label("day"), func.count(PageView.id).label("count"))
        .filter(*base_filter)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
        .all()
    )

    return {
        "event_id": event_id,
        "event_name": event.name,
        "period_days": days,
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
        "utm_sources": [{"source": s, "count": c} for s, c in utm_sources],
        "views_by_day": [{"date": str(d), "views": c} for d, c in views_by_day],
    }


@router.get("/overview")
def get_analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get overall analytics across all event pages."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    base_filter = [PageView.created_at >= cutoff]

    total_views = db.query(func.count(PageView.id)).filter(*base_filter).scalar()
    unique_visitors = db.query(func.count(func.distinct(PageView.ip_hash))).filter(*base_filter).scalar()

    listing_views = db.query(func.count(PageView.id)).filter(*base_filter, PageView.page == "listing").scalar()
    detail_views = db.query(func.count(PageView.id)).filter(*base_filter, PageView.page == "detail").scalar()

    # Top events by views
    top_events = (
        db.query(PageView.event_id, Event.name, func.count(PageView.id).label("count"))
        .join(Event, PageView.event_id == Event.id)
        .filter(*base_filter, PageView.event_id != None)
        .group_by(PageView.event_id, Event.name)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    # Top referrers
    top_referrers = (
        db.query(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(*base_filter, PageView.referrer != None, PageView.referrer != "")
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )

    # Views per day
    views_by_day = (
        db.query(func.date(PageView.created_at).label("day"), func.count(PageView.id).label("count"))
        .filter(*base_filter)
        .group_by(func.date(PageView.created_at))
        .order_by(func.date(PageView.created_at))
        .all()
    )

    return {
        "period_days": days,
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "listing_views": listing_views,
        "detail_views": detail_views,
        "top_events": [{"event_id": eid, "name": name, "views": c} for eid, name, c in top_events],
        "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
        "views_by_day": [{"date": str(d), "views": c} for d, c in views_by_day],
    }
