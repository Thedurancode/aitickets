"""Public-facing event pages served as HTML."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import Event, EventCategory, EventPhoto, EventStatus, PageView, WaitlistEntry, WaitlistStatus
from app.config import get_settings
from app.routers.announcement_queue import queue_announcement

router = APIRouter(tags=["public"])

# Jinja2 template setup
templates_dir = Path(__file__).parent.parent / "templates" / "public"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


def _format_date(value):
    """Format date string as 'January 10, 2026'."""
    if not value:
        return value
    try:
        from datetime import datetime as dt
        if isinstance(value, str):
            d = dt.strptime(value, "%Y-%m-%d")
        else:
            d = value
        return d.strftime("%B %-d, %Y")
    except (ValueError, TypeError):
        return value

jinja_env.filters["fdate"] = _format_date


def _is_youtube(url):
    """Check if a URL is a YouTube URL."""
    if not url:
        return False
    return any(x in url for x in ["youtube.com", "youtu.be"])

jinja_env.tests["youtube_url"] = _is_youtube


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

    photos = (
        db.query(EventPhoto)
        .filter(EventPhoto.event_id == event_id)
        .order_by(EventPhoto.created_at.desc())
        .limit(20)
        .all()
    )

    # Waitlist: check if all tiers are sold out
    all_sold_out = all(t["sold_out"] or t["paused"] for t in tiers) if tiers else False
    waitlist_count = 0
    if all_sold_out:
        waitlist_count = db.query(func.count(WaitlistEntry.id)).filter(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.status == WaitlistStatus.WAITING,
        ).scalar() or 0

    template = jinja_env.get_template("event_detail.html")
    html = template.render(
        event=event,
        tiers=tiers,
        photos=photos,
        all_sold_out=all_sold_out,
        waitlist_count=waitlist_count,
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
    background_tasks: BackgroundTasks,
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

    # Capture old video URLs before update (for cleanup)
    old_promo = event.promo_video_url
    old_recap = event.post_event_video_url

    for field in ["name", "description", "event_date", "event_time", "promo_video_url", "doors_open_time", "post_event_video_url"]:
        if field in body and body[field] is not None:
            setattr(event, field, body[field])
    if "is_visible" in body:
        event.is_visible = body["is_visible"]

    db.commit()
    db.refresh(event)

    # Trigger background YouTube downloads for video fields
    from app.services.video_download import is_youtube_url, download_youtube_video

    new_promo = body.get("promo_video_url")
    if new_promo and is_youtube_url(new_promo):
        background_tasks.add_task(
            download_youtube_video, event.id, "promo_video_url",
            new_promo, old_promo,
        )

    new_recap = body.get("post_event_video_url")
    if new_recap and is_youtube_url(new_recap):
        background_tasks.add_task(
            download_youtube_video, event.id, "post_event_video_url",
            new_recap, old_recap,
        )

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


# ============== Public Photo Gallery ==============

@router.get("/events/{event_id}/photos", response_class=HTMLResponse)
def event_photos_page(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Public photo gallery & upload page for an event."""
    event = db.query(Event).options(
        joinedload(Event.venue),
    ).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    photos = (
        db.query(EventPhoto)
        .filter(EventPhoto.event_id == event_id)
        .order_by(EventPhoto.created_at.desc())
        .all()
    )

    template = jinja_env.get_template("event_photos.html")
    html = template.render(
        event=event,
        photos=photos,
        page_type="photos",
        event_id=event_id,
        **_get_branding(),
    )
    return HTMLResponse(content=html)


@router.post("/events/{event_id}/photos/upload")
async def upload_event_photos(
    event_id: int,
    uploaded_by: str = Query(default=""),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Public photo upload for event attendees."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    settings = get_settings()
    uploads_dir_path = Path(settings.uploads_dir)
    uploads_dir_path.mkdir(exist_ok=True)

    uploaded = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        ext = Path(file.filename).suffix if file.filename else ".jpg"
        filename = f"photo_{event_id}_{uuid.uuid4().hex}{ext}"
        file_path = uploads_dir_path / filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        photo = EventPhoto(
            event_id=event_id,
            photo_url=f"/uploads/{filename}",
            uploaded_by_name=uploaded_by.strip() or None,
        )
        db.add(photo)
        uploaded.append(filename)

    db.commit()

    return {
        "success": True,
        "uploaded_count": len(uploaded),
        "message": f"{len(uploaded)} photo(s) uploaded successfully",
    }


@router.post("/events/{event_id}/waitlist")
async def join_waitlist(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public endpoint to join the waitlist for a sold-out event."""
    body = await request.json()
    email = body.get("email", "").strip().lower()
    name = body.get("name", "").strip()
    phone = body.get("phone", "").strip() or None
    preferred_channel = body.get("preferred_channel", "email")

    if not email or not name:
        raise HTTPException(status_code=400, detail="Name and email are required")

    if preferred_channel not in ("email", "sms"):
        preferred_channel = "email"
    if preferred_channel == "sms" and not phone:
        preferred_channel = "email"

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check for duplicate
    existing = db.query(WaitlistEntry).filter(
        WaitlistEntry.event_id == event_id,
        WaitlistEntry.email == email,
        WaitlistEntry.status == WaitlistStatus.WAITING,
    ).first()
    if existing:
        return {"success": True, "message": f"You're already on the waitlist! (#{existing.position})", "position": existing.position}

    # Compute next position
    max_pos = db.query(func.max(WaitlistEntry.position)).filter(
        WaitlistEntry.event_id == event_id,
    ).scalar() or 0

    entry = WaitlistEntry(
        event_id=event_id,
        email=email,
        name=name,
        phone=phone,
        preferred_channel=preferred_channel,
        status=WaitlistStatus.WAITING,
        position=max_pos + 1,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"success": True, "message": f"You're #{entry.position} on the waitlist!", "position": entry.position}


# ============== Survey Endpoints ==============


@router.get("/survey/{token}", response_class=HTMLResponse)
async def survey_form(token: str, db: Session = Depends(get_db)):
    """Render the survey form for an attendee."""
    from app.models import SurveyResponse
    survey = db.query(SurveyResponse).filter(SurveyResponse.survey_token == token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    event = db.query(Event).filter(Event.id == survey.event_id).first()
    event_name = event.name if event else "the event"
    already_submitted = survey.submitted_at is not None
    settings = get_settings()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rate Your Experience - {event_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); max-width: 500px; width: 100%; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 22px; margin-top: 10px; }}
        .body {{ padding: 30px; }}
        .rating-group {{ display: flex; gap: 8px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
        .rating-btn {{ width: 44px; height: 44px; border-radius: 50%; border: 2px solid #ddd; background: white; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.2s; }}
        .rating-btn:hover {{ border-color: #667eea; background: #f0f0ff; }}
        .rating-btn.selected {{ border-color: #667eea; background: #667eea; color: white; }}
        .labels {{ display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-bottom: 20px; }}
        textarea {{ width: 100%; border: 2px solid #eee; border-radius: 8px; padding: 12px; font-size: 14px; resize: vertical; min-height: 80px; font-family: inherit; }}
        textarea:focus {{ outline: none; border-color: #667eea; }}
        .submit-btn {{ width: 100%; padding: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 25px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }}
        .submit-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .thankyou {{ text-align: center; padding: 40px 20px; }}
        .thankyou h2 {{ color: #667eea; margin-bottom: 10px; }}
        label {{ display: block; font-weight: 600; margin-bottom: 8px; color: #333; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div style="font-size: 40px;">&#11088;</div>
            <h1>How was {event_name}?</h1>
        </div>
        <div class="body">
            {"<div class='thankyou'><h2>Thank you!</h2><p>Your feedback has already been recorded.</p></div>" if already_submitted else f'''
            <form method="POST" action="/survey/{token}">
                <label>Your Rating</label>
                <div class="rating-group">
                    {"".join(f'<button type="button" class="rating-btn" onclick="selectRating({i})">{i}</button>' for i in range(1, 11))}
                </div>
                <div class="labels"><span>Not great</span><span>Amazing!</span></div>
                <input type="hidden" name="rating" id="rating-input" value="">
                <label>Comments (optional)</label>
                <textarea name="comment" placeholder="Tell us what you loved or what we could improve..."></textarea>
                <button type="submit" class="submit-btn" id="submit-btn" disabled>Submit Feedback</button>
            </form>
            <script>
                function selectRating(r) {{
                    document.getElementById("rating-input").value = r;
                    document.getElementById("submit-btn").disabled = false;
                    document.querySelectorAll(".rating-btn").forEach(b => b.classList.remove("selected"));
                    event.target.classList.add("selected");
                }}
            </script>
            '''}
        </div>
    </div>
</body>
</html>"""


@router.post("/survey/{token}")
async def submit_survey(token: str, request: Request, db: Session = Depends(get_db)):
    """Submit a survey response."""
    from app.services.surveys import submit_survey as do_submit

    form = await request.form()
    rating_str = form.get("rating", "")
    comment = form.get("comment", "")

    try:
        rating = int(rating_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid rating")

    result = do_submit(db, token, rating, comment.strip() if comment else None)

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You!</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); max-width: 500px; width: 100%; text-align: center; padding: 50px 30px; }
        h1 { color: #667eea; margin-bottom: 15px; }
        .emoji { font-size: 60px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="emoji">&#127881;</div>
        <h1>Thank You!</h1>
        <p>Your feedback has been recorded. We appreciate you taking the time to help us improve!</p>
    </div>
</body>
</html>""")
