"""Public-facing event pages served as HTML."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import Event, EventCategory, EventStatus, PageView
from app.config import get_settings
from app.routers.announcement_queue import queue_announcement

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
    ).filter(Event.status == EventStatus.SCHEDULED, Event.is_visible == True)

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
    from app.models import TierStatus
    tiers = []
    for tier in event.ticket_tiers:
        remaining = tier.quantity_available - tier.quantity_sold
        tier_status = tier.status.value if tier.status else "active"
        is_sold_out = tier_status == "sold_out" or remaining <= 0
        is_paused = tier_status == "paused"
        tiers.append({
            "id": tier.id,
            "name": tier.name,
            "description": tier.description,
            "price_cents": tier.price,
            "price_display": f"${tier.price / 100:.2f}" if tier.price > 0 else "Free",
            "remaining": remaining,
            "sold_out": is_sold_out,
            "paused": is_paused,
            "status": tier_status,
            "is_available": not is_sold_out and not is_paused,
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


# ============== Magic Link Admin ==============

def _validate_token(token: str, event_id: int):
    """Validate a magic link token. Returns True or raises 403."""
    # Import the shared token store from MCP server
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from mcp_server.server import magic_link_tokens

    token_data = magic_link_tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    if token_data["event_id"] != event_id:
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    if datetime.utcnow() > token_data["expires"]:
        del magic_link_tokens[token]
        raise HTTPException(status_code=403, detail="This link has expired. Request a new one.")
    return True


@router.get("/events/{event_id}/admin", response_class=HTMLResponse)
def event_admin_page(
    event_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Magic-link protected event admin page."""
    _validate_token(token, event_id)

    event = db.query(Event).options(
        joinedload(Event.venue),
        joinedload(Event.ticket_tiers),
        joinedload(Event.categories),
    ).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Build tier stats
    tiers = []
    for tier in event.ticket_tiers:
        tiers.append({
            "name": tier.name,
            "price_display": f"${tier.price / 100:.2f}" if tier.price > 0 else "Free",
            "sold": tier.quantity_sold,
            "total": tier.quantity_available,
        })

    # Get page view analytics
    cutoff = datetime.utcnow() - timedelta(days=30)
    total_views = db.query(func.count(PageView.id)).filter(
        PageView.event_id == event_id, PageView.created_at >= cutoff
    ).scalar() or 0
    unique_visitors = db.query(func.count(func.distinct(PageView.ip_hash))).filter(
        PageView.event_id == event_id, PageView.created_at >= cutoff
    ).scalar() or 0
    top_referrers = (
        db.query(PageView.referrer, func.count(PageView.id).label("count"))
        .filter(PageView.event_id == event_id, PageView.created_at >= cutoff,
                PageView.referrer != None, PageView.referrer != "")
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(5)
        .all()
    )

    analytics = {
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
    }

    template = jinja_env.get_template("event_admin.html")
    html = template.render(
        event=event,
        tiers=tiers,
        analytics=analytics,
        token=token,
        page_type="admin",
        event_id=event_id,
        **_get_branding(),
    )
    return HTMLResponse(content=html)


@router.put("/events/{event_id}/admin")
async def admin_update_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Token-protected event update from admin page."""
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=403, detail="Token required")
    _validate_token(token, event_id)

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for field in ["name", "description", "event_date", "event_time", "promo_video_url", "doors_open_time"]:
        if field in body and body[field] is not None:
            setattr(event, field, body[field])
    if "is_visible" in body:
        event.is_visible = body["is_visible"]

    db.commit()
    db.refresh(event)

    # Broadcast SSE + queue voice announcement
    from app.routers.mcp import sse_manager
    await sse_manager.broadcast("event_updated", {
        "event_id": event.id,
        "event_name": event.name,
        "action": "details_updated",
    })
    queue_announcement(event.id, event.name, "details_updated")

    return {"success": True, "message": "Event updated"}


@router.post("/events/{event_id}/admin/image")
async def admin_upload_image(
    event_id: int,
    token: str = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Token-protected image upload from admin page."""
    _validate_token(token, event_id)

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"event_{event_id}_{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    event.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(event)

    # Broadcast SSE + queue voice announcement
    from app.routers.mcp import sse_manager
    await sse_manager.broadcast("event_updated", {
        "event_id": event.id,
        "event_name": event.name,
        "action": "image_uploaded",
    })
    queue_announcement(event.id, event.name, "image_uploaded")

    return {"success": True, "image_url": event.image_url}
