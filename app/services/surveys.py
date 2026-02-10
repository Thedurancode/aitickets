"""
Post-Event Survey Service

Creates survey tokens for attendees, sends survey emails/SMS,
collects responses, and aggregates NPS scores.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc

from app.models import (
    Event,
    Ticket,
    TicketStatus,
    TicketTier,
    EventGoer,
    SurveyResponse,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


def create_survey_tokens(db: Session, event_id: int) -> dict:
    """Create SurveyResponse rows with unique tokens for all attendees of an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    # Find all paid/checked-in tickets for this event
    tickets = (
        db.query(Ticket)
        .join(TicketTier)
        .options(joinedload(Ticket.event_goer))
        .filter(
            TicketTier.event_id == event_id,
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
        )
        .all()
    )

    if not tickets:
        return {"error": "No attendees found for this event.", "event_id": event_id}

    created = 0
    skipped = 0
    for ticket in tickets:
        # Check if survey already exists for this event_goer + event
        existing = (
            db.query(SurveyResponse)
            .filter(
                SurveyResponse.event_id == event_id,
                SurveyResponse.event_goer_id == ticket.event_goer_id,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        token = secrets.token_urlsafe(24)
        survey = SurveyResponse(
            event_id=event_id,
            event_goer_id=ticket.event_goer_id,
            ticket_id=ticket.id,
            survey_token=token,
        )
        db.add(survey)
        created += 1

    db.commit()
    return {
        "success": True,
        "event_id": event_id,
        "event_name": event.name,
        "tokens_created": created,
        "skipped_existing": skipped,
        "message": f"Created {created} survey tokens for {event.name}.",
    }


def send_event_survey(db: Session, event_id: int) -> dict:
    """Send survey emails/SMS to all attendees who have unsent survey tokens."""
    from app.config import get_settings

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": "Event not found"}

    settings = get_settings()

    # Find unsent survey responses
    unsent = (
        db.query(SurveyResponse)
        .options(joinedload(SurveyResponse.event_goer))
        .filter(
            SurveyResponse.event_id == event_id,
            SurveyResponse.sent_at.is_(None),
        )
        .all()
    )

    if not unsent:
        # Try creating tokens first
        create_result = create_survey_tokens(db, event_id)
        if create_result.get("error"):
            return create_result
        # Re-query
        unsent = (
            db.query(SurveyResponse)
            .options(joinedload(SurveyResponse.event_goer))
            .filter(
                SurveyResponse.event_id == event_id,
                SurveyResponse.sent_at.is_(None),
            )
            .all()
        )

    if not unsent:
        return {"success": True, "sent": 0, "message": "All surveys already sent for this event."}

    now = datetime.now(timezone.utc)
    email_sent = 0
    sms_sent = 0
    failed = 0

    for survey in unsent:
        goer = survey.event_goer
        if not goer:
            continue

        survey_url = f"{settings.base_url}/survey/{survey.survey_token}"

        # Send email
        if goer.email:
            try:
                from app.services.email import send_survey_email
                success = send_survey_email(
                    to_email=goer.email,
                    recipient_name=goer.name or "there",
                    event_name=event.name,
                    event_date=event.event_date,
                    survey_url=survey_url,
                )
                if success:
                    email_sent += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Survey email failed for {goer.email}: {e}")
                failed += 1

        # Send SMS
        if goer.phone:
            try:
                from app.services.sms import send_sms
                msg = f"Hi {goer.name or 'there'}! How was {event.name}? Rate your experience: {survey_url}"
                result = send_sms(goer.phone, msg)
                if result.get("success"):
                    sms_sent += 1
            except Exception as e:
                logger.error(f"Survey SMS failed for {goer.phone}: {e}")

        survey.sent_at = now

        # Log notification
        try:
            from app.services.notifications import log_notification
            log_notification(
                db=db,
                event_goer_id=goer.id,
                notification_type=NotificationType.SURVEY_REQUEST,
                channel=NotificationChannel.EMAIL,
                message=f"Survey sent for {event.name}",
                event_id=event_id,
                ticket_id=survey.ticket_id,
                status=NotificationStatus.SENT,
            )
        except Exception:
            pass

    db.commit()

    return {
        "success": True,
        "event_id": event_id,
        "event_name": event.name,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "failed": failed,
        "message": f"Sent {email_sent} survey email(s) and {sms_sent} SMS for {event.name}.",
    }


def submit_survey(db: Session, token: str, rating: int, comment: str = None) -> dict:
    """Record a survey submission."""
    survey = db.query(SurveyResponse).filter(SurveyResponse.survey_token == token).first()
    if not survey:
        return {"error": "Survey not found or invalid token."}

    if survey.submitted_at:
        return {"error": "This survey has already been submitted. Thank you!"}

    if not (1 <= rating <= 10):
        return {"error": "Rating must be between 1 and 10."}

    survey.rating = rating
    survey.comment = comment
    survey.submitted_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "message": "Thank you for your feedback!",
    }


def get_survey_results(db: Session, event_id: int = None) -> dict:
    """Get aggregated survey results, optionally filtered by event."""
    query = db.query(SurveyResponse).filter(SurveyResponse.submitted_at.isnot(None))

    if event_id:
        query = query.filter(SurveyResponse.event_id == event_id)

    responses = query.all()

    if not responses:
        # Check if surveys exist but haven't been submitted
        pending_count = db.query(SurveyResponse).filter(
            SurveyResponse.submitted_at.is_(None),
            *([SurveyResponse.event_id == event_id] if event_id else []),
        ).count()

        total_sent = db.query(SurveyResponse).filter(
            SurveyResponse.sent_at.isnot(None),
            *([SurveyResponse.event_id == event_id] if event_id else []),
        ).count()

        return {
            "total_responses": 0,
            "total_sent": total_sent,
            "pending": pending_count,
            "response_rate_percent": 0,
            "message": "No survey responses yet." + (f" {total_sent} surveys sent, awaiting responses." if total_sent else ""),
        }

    ratings = [r.rating for r in responses if r.rating is not None]
    total_sent = db.query(SurveyResponse).filter(
        SurveyResponse.sent_at.isnot(None),
        *([SurveyResponse.event_id == event_id] if event_id else []),
    ).count()

    # NPS calculation: 9-10 = promoters, 7-8 = passive, 1-6 = detractors
    promoters = len([r for r in ratings if r >= 9])
    detractors = len([r for r in ratings if r <= 6])
    total = len(ratings)
    nps_score = round(((promoters - detractors) / max(total, 1)) * 100) if total > 0 else 0

    avg_rating = round(sum(ratings) / max(len(ratings), 1), 1)
    response_rate = round((len(responses) / max(total_sent, 1)) * 100, 1) if total_sent > 0 else 0

    comments = [
        {
            "rating": r.rating,
            "comment": r.comment,
            "event_id": r.event_id,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        }
        for r in responses
        if r.comment
    ]

    # Per-event breakdown if no specific event filtered
    event_breakdown = []
    if not event_id:
        event_ids = set(r.event_id for r in responses)
        for eid in event_ids:
            event_ratings = [r.rating for r in responses if r.event_id == eid and r.rating]
            event = db.query(Event).filter(Event.id == eid).first()
            if event_ratings:
                ep = len([r for r in event_ratings if r >= 9])
                ed = len([r for r in event_ratings if r <= 6])
                et = len(event_ratings)
                event_breakdown.append({
                    "event_id": eid,
                    "event_name": event.name if event else f"Event {eid}",
                    "responses": et,
                    "avg_rating": round(sum(event_ratings) / et, 1),
                    "nps_score": round(((ep - ed) / max(et, 1)) * 100),
                })
        event_breakdown.sort(key=lambda x: x["avg_rating"], reverse=True)

    result = {
        "total_responses": len(responses),
        "total_sent": total_sent,
        "response_rate_percent": response_rate,
        "avg_rating": avg_rating,
        "nps_score": nps_score,
        "promoters": promoters,
        "passives": total - promoters - detractors,
        "detractors": detractors,
        "recent_comments": comments[:10],
    }

    if event_breakdown:
        result["event_breakdown"] = event_breakdown

    return result


def run_survey_job():
    """Scheduled job: auto-send surveys for events that ended 24h ago."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        # Find events that ended yesterday and don't have surveys yet
        events = db.query(Event).filter(Event.event_date == yesterday).all()

        for event in events:
            existing = db.query(SurveyResponse).filter(SurveyResponse.event_id == event.id).first()
            if existing:
                continue  # Already has surveys

            try:
                create_result = create_survey_tokens(db, event.id)
                if create_result.get("tokens_created", 0) > 0:
                    send_result = send_event_survey(db, event.id)
                    logger.info(f"Auto-survey for event {event.id} ({event.name}): {send_result.get('message')}")
            except Exception as e:
                logger.error(f"Auto-survey failed for event {event.id}: {e}")
    except Exception as e:
        logger.error(f"Survey job failed: {e}")
    finally:
        db.close()
