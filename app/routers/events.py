from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
import uuid
from pathlib import Path

from app.database import get_db
from app.models import Event, Venue, TicketTier, EventCategory
from app.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventDetailResponse,
    EventWithVenueResponse,
    TicketTierWithAvailability,
    GenerateFlyerRequest,
)
from app.config import get_settings

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventWithVenueResponse])
def list_events(
    category: str | None = None,
    q: str | None = None,  # Search query
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List events with venue information.

    Optionally filter by:
    - category: Filter by category name
    - q: Search in event name, description, and venue
    """
    query = db.query(Event).options(joinedload(Event.venue), joinedload(Event.categories))

    if category:
        query = query.join(Event.categories).filter(EventCategory.name.ilike(f"%{category}%"))

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (Event.name.ilike(search_term)) |
            (Event.description.ilike(search_term))
        )

    events = query.order_by(Event.event_date.desc()).offset(offset).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get event with venue, tiers, and availability."""
    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers), joinedload(Event.categories))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Calculate availability for each tier
    tiers_with_availability = []
    for tier in event.ticket_tiers:
        tier_data = TicketTierWithAvailability(
            id=tier.id,
            event_id=tier.event_id,
            name=tier.name,
            description=tier.description,
            price=tier.price,
            quantity_available=tier.quantity_available,
            quantity_sold=tier.quantity_sold,
            tickets_remaining=tier.quantity_available - tier.quantity_sold,
        )
        tiers_with_availability.append(tier_data)

    return EventDetailResponse(
        id=event.id,
        venue_id=event.venue_id,
        name=event.name,
        description=event.description,
        image_url=event.image_url,
        promo_video_url=event.promo_video_url,
        post_event_video_url=event.post_event_video_url,
        event_date=event.event_date,
        event_time=event.event_time,
        status=event.status,
        is_visible=event.is_visible,
        uploads_open=event.uploads_open if event.uploads_open is not None else True,
        doors_open_time=event.doors_open_time,
        created_at=event.created_at,
        venue=event.venue,
        ticket_tiers=tiers_with_availability,
        categories=event.categories,
    )


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event: EventCreate,
    background_tasks: BackgroundTasks,
    auto_onboard: bool = Query(True, description="Automatically onboard event with research, flyer, and ads"),
    db: Session = Depends(get_db)
):
    """
    Create a new event.

    **Auto-Onboarding (auto_onboard=true):**
    When enabled, automatically triggers:
    1. Research agent - Analyzes event and generates marketing plan
    2. Flyer generation - Creates AI-powered event flyer
    3. Meta ads creation - Launches ad campaigns based on marketing plan
    4. Campaign scheduling - Sets up email/SMS campaigns
    5. Dynamic pricing - Configures demand-based pricing (if applicable)

    Set auto_onboard=false to skip automation and configure manually.
    """
    # Verify venue exists
    venue = db.query(Venue).filter(Venue.id == event.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    event_data = event.model_dump(exclude={"category_ids"})
    db_event = Event(**event_data)

    # Attach categories
    if event.category_ids:
        categories = db.query(EventCategory).filter(EventCategory.id.in_(event.category_ids)).all()
        db_event.categories = categories

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Fire webhook: event.created
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.created", {
            "event_id": db_event.id,
            "name": db_event.name,
            "venue_id": db_event.venue_id,
            "event_date": db_event.event_date,
            "event_time": db_event.event_time,
        }, db=db)
    except Exception:
        pass

    # Trigger auto-onboarding in background
    if auto_onboard:
        background_tasks.add_task(
            _run_auto_onboarding,
            db_event.id,
            db_event.name
        )

    return db_event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(event_id: int, event: EventUpdate, db: Session = Depends(get_db)):
    """Update an event."""
    db_event = db.query(Event).options(joinedload(Event.categories)).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = event.model_dump(exclude_unset=True)

    # Handle category_ids separately
    category_ids = update_data.pop("category_ids", None)
    if category_ids is not None:
        categories = db.query(EventCategory).filter(EventCategory.id.in_(category_ids)).all()
        db_event.categories = categories

    for field, value in update_data.items():
        setattr(db_event, field, value)

    db.commit()
    db.refresh(db_event)

    # Fire webhook: event.updated
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.updated", {
            "event_id": db_event.id,
            "name": db_event.name,
            "venue_id": db_event.venue_id,
            "event_date": db_event.event_date,
            "event_time": db_event.event_time,
            "updated_fields": list(update_data.keys()),
        }, db=db)
    except Exception:
        pass

    return db_event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete an event and all related data."""
    from sqlalchemy import text

    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_data = {
        "event_id": db_event.id,
        "name": db_event.name,
        "venue_id": db_event.venue_id,
    }

    # Helper: run SQL in a savepoint so a missing table doesn't abort the txn
    def _safe_exec(stmt, params=None):
        try:
            nested = db.begin_nested()
            db.execute(text(stmt), params or {"eid": event_id})
            nested.commit()
        except Exception:
            nested.rollback()

    # Delete tickets that belong to this event's tiers
    _safe_exec(
        "DELETE FROM tickets WHERE ticket_tier_id IN "
        "(SELECT id FROM ticket_tiers WHERE event_id = :eid)"
    )

    # Clean up all FK references that don't cascade automatically
    for table in [
        "ticket_tiers", "survey_responses", "notifications", "event_updates",
        "page_views", "auto_triggers", "admin_magic_links",
        "knowledge_documents", "waitlist_entries", "event_photos",
    ]:
        _safe_exec(f"DELETE FROM {table} WHERE event_id = :eid")
    # Nullify optional FK references
    for table, col in [
        ("marketing_campaigns", "target_event_id"),
        ("promo_codes", "event_id"),
        ("conversation_sessions", "current_event_id"),
    ]:
        _safe_exec(f"UPDATE {table} SET {col} = NULL WHERE {col} = :eid")
    # Remove event-category associations
    _safe_exec("DELETE FROM event_category_association WHERE event_id = :eid")

    # Delete the event itself via raw SQL to avoid ORM cascade issues
    db.execute(text("DELETE FROM events WHERE id = :eid"), {"eid": event_id})
    # Expunge the ORM object so SQLAlchemy doesn't try to flush it
    db.expunge(db_event)
    db.commit()

    # Fire webhook: event.deleted
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("event.deleted", event_data, db=db)
    except Exception:
        pass

    return None


@router.post("/{event_id}/image", response_model=EventResponse)
async def upload_event_image(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an image for an event."""
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"event_{event_id}_{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Update event with image URL
    db_event.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(db_event)

    return db_event


@router.post("/{event_id}/generate-flyer", response_model=EventResponse)
def generate_event_flyer(
    event_id: int,
    body: GenerateFlyerRequest = None,
    db: Session = Depends(get_db),
):
    """Generate an AI flyer for an event using Gemini and save it as the event image."""
    from app.services.flyer_generator import build_flyer_prompt, generate_flyer

    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    tiers_data = [
        {"name": tier.name, "price": tier.price}
        for tier in (event.ticket_tiers or [])
    ]

    settings = get_settings()

    prompt = build_flyer_prompt(
        event_name=event.name,
        event_date=str(event.event_date),
        event_time=event.event_time or "",
        venue_name=event.venue.name if event.venue else None,
        venue_address=event.venue.address if event.venue else None,
        description=event.description,
        tiers=tiers_data,
        org_name=settings.org_name,
        style_instructions=body.style_instructions if body else None,
    )

    # Look up style from the library if provided
    reference_image_path = None
    if body and body.style_id:
        from app.models import FlyerStyle
        style = db.query(FlyerStyle).filter(FlyerStyle.id == body.style_id).first()
        if not style:
            raise HTTPException(status_code=404, detail="Flyer style not found")
        prompt += f"\n\nUse this reference image as a style guide: {style.description}"
        if style.image_url:
            img_file = Path(style.image_url.lstrip("/"))
            if img_file.exists():
                reference_image_path = str(img_file)

    result = generate_flyer(prompt, reference_image_path=reference_image_path)

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result["error"])

    event.image_url = result["image_url"]
    db.commit()
    db.refresh(event)

    return event


# ============== Highlight Video ==============


@router.post("/{event_id}/highlight-video")
def create_highlight_video(
    event_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate a highlight recap video from attendee-uploaded photos and videos.

    Runs in the background. The result is saved to event.post_event_video_url
    and broadcast via SSE when complete.
    """
    from app.services.highlight_video import trigger_highlight_generation_async
    from app.models import EventPhoto

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    media_count = db.query(EventPhoto).filter(EventPhoto.event_id == event_id).count()
    if media_count == 0:
        raise HTTPException(status_code=400, detail="No media uploaded for this event yet")

    background_tasks.add_task(trigger_highlight_generation_async, event_id)

    return {
        "status": "generating",
        "message": f"Highlight video is being generated from {media_count} uploads. This may take 30-60 seconds.",
        "event_id": event_id,
        "media_count": media_count,
    }


@router.post("/{event_id}/uploads/{action}")
def toggle_event_uploads(
    event_id: int,
    action: str,
    db: Session = Depends(get_db),
):
    """Open or close media uploads for an event. Action must be 'open' or 'close'."""
    if action not in ("open", "close"):
        raise HTTPException(status_code=400, detail="Action must be 'open' or 'close'")

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.uploads_open = (action == "open")
    db.commit()

    return {
        "event_id": event_id,
        "uploads_open": event.uploads_open,
        "message": f"Uploads {'opened' if event.uploads_open else 'closed'} for {event.name}",
    }


@router.post("/{event_id}/onboard")
async def trigger_event_onboarding(
    event_id: int,
    background_tasks: BackgroundTasks,
    skip_research: bool = Query(False, description="Skip research agent"),
    skip_flyer: bool = Query(False, description="Skip flyer generation"),
    skip_meta_ads: bool = Query(False, description="Skip Meta ads creation"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger auto-onboarding for an existing event.

    **Use Cases:**
    - Re-run onboarding if it failed initially
    - Update marketing materials for an event
    - Generate missing components (flyer, ads, etc.)

    **Steps:**
    1. Research agent - Marketing plan generation
    2. Flyer generation - AI-powered event flyer
    3. Meta ads - Campaign creation
    4. Email/SMS - Campaign scheduling
    5. Dynamic pricing - Auto-pricing setup

    Use skip_* parameters to skip specific steps.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Trigger onboarding in background
    background_tasks.add_task(
        _run_auto_onboarding_with_options,
        event_id,
        event.name,
        skip_research,
        skip_flyer,
        skip_meta_ads
    )

    return {
        "message": f"Auto-onboarding triggered for {event.name}",
        "event_id": event_id,
        "status": "running_in_background",
        "note": "Use GET /api/event-research/events/{event_id}/report to check results"
    }


# ============== Background Tasks ==============

async def _run_auto_onboarding(event_id: int, event_name: str):
    """
    Background task for event auto-onboarding.

    Runs asynchronously after event creation to avoid blocking the API response.
    """
    from app.database import SessionLocal
    from app.services.event_auto_onboarding import auto_onboard_event
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Starting auto-onboarding for event {event_id}: {event_name}")

    db = SessionLocal()
    try:
        result = await auto_onboard_event(db, event_id)

        if "error" in result:
            logger.error(f"Auto-onboarding failed for event {event_id}: {result['error']}")
        else:
            logger.info(
                f"Auto-onboarding completed for event {event_id}. "
                f"Steps completed: {len(result.get('steps_completed', []))}, "
                f"Steps failed: {len(result.get('steps_failed', []))}"
            )

            # Fire webhook with onboarding results
            try:
                from app.services.webhooks import fire_webhook_event
                fire_webhook_event("event.onboarded", {
                    "event_id": event_id,
                    "event_name": event_name,
                    "steps_completed": result.get('steps_completed', []),
                    "steps_failed": result.get('steps_failed', []),
                    "success_rate": result.get('success_rate'),
                }, db=db)
            except Exception:
                pass

    except Exception as e:
        logger.exception(f"Auto-onboarding exception for event {event_id}: {str(e)}")
    finally:
        db.close()


async def _run_auto_onboarding_with_options(
    event_id: int,
    event_name: str,
    skip_research: bool,
    skip_flyer: bool,
    skip_meta_ads: bool
):
    """
    Background task for event auto-onboarding with custom options.
    """
    from app.database import SessionLocal
    from app.services.event_auto_onboarding import auto_onboard_event
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Starting custom auto-onboarding for event {event_id}: {event_name}")

    db = SessionLocal()
    try:
        result = await auto_onboard_event(
            db, event_id,
            skip_research=skip_research,
            skip_flyer=skip_flyer,
            skip_meta_ads=skip_meta_ads
        )

        if "error" in result:
            logger.error(f"Auto-onboarding failed for event {event_id}: {result['error']}")
        else:
            logger.info(
                f"Auto-onboarding completed for event {event_id}. "
                f"Steps completed: {result.get('steps_completed', [])}"
            )

    except Exception as e:
        logger.exception(f"Auto-onboarding exception for event {event_id}: {str(e)}")
    finally:
        db.close()


# ============== Artist Data for Event ==============

@router.get("/{event_id}/artist")
def get_event_artist(event_id: int, db: Session = Depends(get_db)):
    """Get artist data for an event."""
    from app.models import Artist
    import json as _json
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}
    if not event.artist_id:
        return {"has_artist": False}
    
    artist = db.query(Artist).filter(Artist.id == event.artist_id).first()
    if not artist:
        return {"has_artist": False}
    
    def parse_json(val):
        if not val:
            return None
        try:
            return _json.loads(val) if isinstance(val, str) else val
        except:
            return val
    
    return {
        "has_artist": True,
        "id": artist.id,
        "name": artist.name,
        "bio": artist.bio,
        "genre": artist.genre,
        "sub_genres": parse_json(artist.sub_genres),
        "country_of_origin": artist.country_of_origin,
        "active_since_year": artist.active_since_year,
        "spotify_image_url": artist.spotify_image_url,
        "primary_image_url": artist.primary_image_url,
        "spotify_followers": artist.spotify_followers,
        "spotify_monthly_listeners": artist.spotify_monthly_listeners,
        "spotify_popularity": artist.spotify_popularity,
        "spotify_top_tracks": parse_json(artist.spotify_top_tracks),
        "spotify_genres": parse_json(artist.spotify_genres),
        "youtube_subscribers": artist.youtube_subscribers,
        "instagram_handle": artist.instagram_handle,
        "instagram_followers": artist.instagram_followers,
        "twitter_handle": artist.twitter_handle,
        "twitter_followers": artist.twitter_followers,
        "tiktok_handle": artist.tiktok_handle,
        "tiktok_followers": artist.tiktok_followers,
        "facebook_page": artist.facebook_page,
        "facebook_likes": artist.facebook_likes,
        "achievements": parse_json(artist.achievements),
        "similar_artists": parse_json(artist.similar_artists),
        "fan_demographics": parse_json(artist.fan_demographics),
        "primary_markets": parse_json(artist.primary_markets),
        "typical_venue_size": artist.typical_venue_size,
        "sellout_velocity": artist.sellout_velocity,
        "reference_images": parse_json(artist.reference_images),
    }
