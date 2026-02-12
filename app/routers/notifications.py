from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.rate_limit import limiter
from app.models import (
    Event, EventGoer, Notification, MarketingCampaign,
    NotificationType, NotificationChannel, EventStatus, EventUpdate as EventUpdateModel,
)
from app.schemas import (
    SendReminderRequest, SendReminderResponse,
    EventUpdateRequest, EventCancelRequest, EventUpdateResponse,
    MarketingCampaignCreate, MarketingCampaignResponse,
    SendMarketingRequest, SendMarketingResponse,
    SendSMSTicketRequest, SendSMSTicketResponse,
    NotificationResponse, NotificationPreferencesUpdate, EventGoerResponse,
)
from app.services.notifications import (
    send_event_reminders, send_event_update_notifications,
    send_event_cancellation_notifications, send_sms_ticket,
    send_marketing_campaign,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============== Event Reminders ==============

@router.post("/reminders", response_model=SendReminderResponse)
@limiter.limit("10/minute")
def send_reminders(
    http_request: Request,
    request: SendReminderRequest,
    db: Session = Depends(get_db),
):
    """Send reminder notifications to all ticket holders for an event."""
    result = send_event_reminders(
        db=db,
        event_id=request.event_id,
        hours_before=request.hours_before,
        channels=request.channels,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============== Event Updates ==============

@router.post("/events/{event_id}/update", response_model=EventUpdateResponse)
@limiter.limit("10/minute")
def send_event_update(
    http_request: Request,
    event_id: int,
    request: EventUpdateRequest,
    db: Session = Depends(get_db),
):
    """Send update notification to all ticket holders."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Log the update
    update_record = EventUpdateModel(
        event_id=event_id,
        update_type=request.update_type,
        message=request.message,
        old_value=request.old_value,
        new_value=request.new_value,
    )
    db.add(update_record)
    db.commit()

    if request.notify_attendees:
        result = send_event_update_notifications(
            db=db,
            event_id=event_id,
            message=request.message,
            update_type=request.update_type,
            channels=request.channels,
        )
        update_record.notifications_sent = True
        db.commit()
        return result

    return EventUpdateResponse(
        event_id=event_id,
        event_name=event.name,
        update_type=request.update_type,
        message=request.message,
        notifications_sent=0,
    )


# ============== Event Cancellation ==============

@router.post("/events/{event_id}/cancel", response_model=EventUpdateResponse)
@limiter.limit("5/minute")
def cancel_event(
    http_request: Request,
    event_id: int,
    request: EventCancelRequest,
    db: Session = Depends(get_db),
):
    """Cancel an event and notify all ticket holders."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update event status
    event.status = EventStatus.CANCELLED
    event.cancellation_reason = request.reason

    # Log the cancellation
    update_record = EventUpdateModel(
        event_id=event_id,
        update_type="cancelled",
        message=f"Event cancelled. Reason: {request.reason}" if request.reason else "Event cancelled.",
    )
    db.add(update_record)
    db.commit()

    notifications_sent = 0
    if request.notify_attendees:
        result = send_event_cancellation_notifications(
            db=db,
            event_id=event_id,
            reason=request.reason,
            channels=request.channels,
        )
        notifications_sent = result.get("notifications_sent", 0)
        update_record.notifications_sent = True
        db.commit()

    return EventUpdateResponse(
        event_id=event_id,
        event_name=event.name,
        update_type="cancelled",
        message=update_record.message,
        notifications_sent=notifications_sent,
    )


# ============== SMS Tickets ==============

@router.post("/sms-ticket", response_model=SendSMSTicketResponse)
@limiter.limit("10/minute")
def send_ticket_via_sms(
    http_request: Request,
    request: SendSMSTicketRequest,
    db: Session = Depends(get_db),
):
    """Send ticket details via SMS."""
    result = send_sms_ticket(db=db, ticket_id=request.ticket_id)
    return SendSMSTicketResponse(
        ticket_id=request.ticket_id,
        success=result["success"],
        message=result["message"],
    )


# ============== Marketing Campaigns ==============

@router.get("/campaigns", response_model=list[MarketingCampaignResponse])
def list_campaigns(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List marketing campaigns."""
    campaigns = db.query(MarketingCampaign).order_by(MarketingCampaign.created_at.desc()).offset(offset).limit(limit).all()
    return campaigns


@router.post("/campaigns", response_model=MarketingCampaignResponse, status_code=201)
def create_campaign(
    campaign: MarketingCampaignCreate,
    db: Session = Depends(get_db),
):
    """Create a new marketing campaign."""
    db_campaign = MarketingCampaign(**campaign.model_dump())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.post("/campaigns/{campaign_id}/send", response_model=SendMarketingResponse)
@limiter.limit("5/minute")
def send_campaign(
    http_request: Request,
    campaign_id: int,
    request: SendMarketingRequest,
    db: Session = Depends(get_db),
):
    """Send a marketing campaign to opted-in users."""
    result = send_marketing_campaign(
        db=db,
        campaign_id=campaign_id,
        channels=request.channels,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============== Notification History ==============

@router.get("/history", response_model=list[NotificationResponse])
def get_notification_history(
    event_goer_id: Optional[int] = None,
    event_id: Optional[int] = None,
    notification_type: Optional[NotificationType] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Get notification history with optional filters."""
    query = db.query(Notification)

    if event_goer_id:
        query = query.filter(Notification.event_goer_id == event_goer_id)
    if event_id:
        query = query.filter(Notification.event_id == event_id)
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)

    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return notifications


# ============== Notification Preferences ==============

@router.get("/preferences/{event_goer_id}", response_model=EventGoerResponse)
def get_notification_preferences(
    event_goer_id: int,
    db: Session = Depends(get_db),
):
    """Get notification preferences for an event goer."""
    event_goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
    if not event_goer:
        raise HTTPException(status_code=404, detail="Event goer not found")
    return event_goer


@router.put("/preferences/{event_goer_id}", response_model=EventGoerResponse)
def update_notification_preferences(
    event_goer_id: int,
    preferences: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
):
    """Update notification preferences for an event goer."""
    event_goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
    if not event_goer:
        raise HTTPException(status_code=404, detail="Event goer not found")

    update_data = preferences.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event_goer, field, value)

    db.commit()
    db.refresh(event_goer)
    return event_goer


# ============== Unsubscribe ==============

@router.get("/unsubscribe")
def unsubscribe(
    email: str,
    db: Session = Depends(get_db),
):
    """Unsubscribe from marketing emails."""
    event_goer = db.query(EventGoer).filter(EventGoer.email == email).first()
    if event_goer:
        event_goer.marketing_opt_in = False
        db.commit()

    return {"message": "You have been unsubscribed from marketing emails."}
