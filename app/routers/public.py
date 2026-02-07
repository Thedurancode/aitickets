"""Public-facing event pages served as HTML."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Event, EventCategory, EventStatus
from app.config import get_settings

router = APIRouter(tags=["public"])

# Jinja2 template setup
templates_dir = Path(__file__).parent.parent / "templates" / "public"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


def _get_branding():
    """Get org branding settings for templates."""
    settings = get_settings()
    return {
        "org_name": settings.org_name,
        "org_color": settings.org_color,
        "org_logo_url": settings.org_logo_url,
        "base_url": settings.base_url,
    }


@router.get("/events", response_class=HTMLResponse)
def events_listing(
    search: str = Query(default=None),
    category: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Public events listing page."""
    query = db.query(Event).options(
        joinedload(Event.venue),
        joinedload(Event.categories),
        joinedload(Event.ticket_tiers),
    ).filter(Event.status == EventStatus.SCHEDULED)

    if category:
        query = query.join(Event.categories).filter(
            EventCategory.name.ilike(f"%{category}%")
        )
    if search:
        query = query.filter(Event.name.ilike(f"%{search}%"))

    events = query.order_by(Event.event_date.asc()).all()
    # Deduplicate (joinedload + join can produce duplicates)
    seen = set()
    unique_events = []
    for e in events:
        if e.id not in seen:
            seen.add(e.id)
            unique_events.append(e)
    events = unique_events
    categories = db.query(EventCategory).order_by(EventCategory.name).all()

    template = jinja_env.get_template("events_listing.html")
    html = template.render(
        events=events,
        categories=categories,
        selected_category=category,
        search_query=search,
        page_type="listing",
        event_id=None,
        **_get_branding(),
    )
    return HTMLResponse(content=html)


@router.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Public event detail page."""
    event = db.query(Event).options(
        joinedload(Event.venue),
        joinedload(Event.ticket_tiers),
        joinedload(Event.categories),
    ).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Build tier data with availability
    tiers = []
    for tier in event.ticket_tiers:
        remaining = tier.quantity_available - tier.quantity_sold
        tiers.append({
            "id": tier.id,
            "name": tier.name,
            "description": tier.description,
            "price_cents": tier.price,
            "price_display": f"${tier.price / 100:.2f}" if tier.price > 0 else "Free",
            "remaining": remaining,
            "sold_out": remaining <= 0,
        })

    template = jinja_env.get_template("event_detail.html")
    html = template.render(
        event=event,
        tiers=tiers,
        page_type="detail",
        event_id=event_id,
        **_get_branding(),
    )
    return HTMLResponse(content=html)
