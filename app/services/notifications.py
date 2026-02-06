import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Event, EventGoer, Ticket, TicketTier, Notification,
    NotificationType, NotificationChannel, NotificationStatus, TicketStatus,
    EventUpdate, MarketingCampaign, CustomerPreference, event_category_link,
)
from app.services.email import send_ticket_email
from app.services.sms import (
    send_ticket_sms, send_reminder_sms, send_event_update_sms,
    send_event_cancelled_sms, send_marketing_sms,
)
from app.config import get_settings


def log_notification(
    db: Session,
    event_goer_id: int,
    notification_type: NotificationType,
    channel: NotificationChannel,
    message: str,
    subject: Optional[str] = None,
    event_id: Optional[int] = None,
    ticket_id: Optional[int] = None,
    status: NotificationStatus = NotificationStatus.PENDING,
    external_id: Optional[str] = None,
    failed_reason: Optional[str] = None,
) -> Notification:
    """Log a notification to the database."""
    notification = Notification(
        event_goer_id=event_goer_id,
        event_id=event_id,
        ticket_id=ticket_id,
        notification_type=notification_type,
        channel=channel,
        status=status,
        subject=subject,
        message=message,
        external_id=external_id,
        failed_reason=failed_reason,
        sent_at=datetime.now(timezone.utc) if status == NotificationStatus.SENT else None,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_event_reminders(
    db: Session,
    event_id: int,
    hours_before: int = 24,
    channels: list[NotificationChannel] = None,
) -> dict:
    """
    Send reminders to all ticket holders for an event.
    Returns stats about sent notifications.
    """
    if channels is None:
        channels = [NotificationChannel.EMAIL]

    settings = get_settings()

    event = (
        db.query(Event)
        .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    # Get all paid tickets for this event
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.event_goer), joinedload(Ticket.ticket_tier))
        .join(TicketTier)
        .filter(TicketTier.event_id == event_id)
        .filter(Ticket.status == TicketStatus.PAID)
        .filter(Ticket.reminder_sent == False)
        .all()
    )

    stats = {
        "event_id": event_id,
        "event_name": event.name,
        "total_recipients": 0,
        "email_sent": 0,
        "sms_sent": 0,
        "failed": 0,
    }

    # Group tickets by event goer to avoid duplicate notifications
    event_goers_notified = set()

    for ticket in tickets:
        event_goer = ticket.event_goer

        if event_goer.id in event_goers_notified:
            continue

        event_goers_notified.add(event_goer.id)
        stats["total_recipients"] += 1

        # Send email reminder
        if NotificationChannel.EMAIL in channels and event_goer.email_opt_in:
            try:
                from app.services.email import send_reminder_email
                success = send_reminder_email(
                    to_email=event_goer.email,
                    recipient_name=event_goer.name,
                    event_name=event.name,
                    event_date=event.event_date,
                    event_time=event.event_time,
                    venue_name=event.venue.name,
                    venue_address=event.venue.address,
                    hours_until=hours_before,
                )
                if success:
                    stats["email_sent"] += 1
                    log_notification(
                        db, event_goer.id, NotificationType.EVENT_REMINDER,
                        NotificationChannel.EMAIL,
                        f"Reminder for {event.name}",
                        subject=f"Reminder: {event.name} is coming up!",
                        event_id=event_id,
                        status=NotificationStatus.SENT,
                    )
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_REMINDER,
                    NotificationChannel.EMAIL,
                    f"Reminder for {event.name}",
                    event_id=event_id,
                    status=NotificationStatus.FAILED,
                    failed_reason=str(e),
                )

        # Send SMS reminder
        if NotificationChannel.SMS in channels and event_goer.sms_opt_in and event_goer.phone:
            result = send_reminder_sms(
                to_phone=event_goer.phone,
                recipient_name=event_goer.name,
                event_name=event.name,
                event_date=event.event_date,
                event_time=event.event_time,
                venue_name=event.venue.name,
                venue_address=event.venue.address,
                hours_until=hours_before,
            )
            if result["success"]:
                stats["sms_sent"] += 1
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_REMINDER,
                    NotificationChannel.SMS,
                    f"Reminder for {event.name}",
                    event_id=event_id,
                    status=NotificationStatus.SENT,
                    external_id=result.get("sid"),
                )
            else:
                stats["failed"] += 1
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_REMINDER,
                    NotificationChannel.SMS,
                    f"Reminder for {event.name}",
                    event_id=event_id,
                    status=NotificationStatus.FAILED,
                    failed_reason=result.get("error"),
                )

        # Mark ticket as reminded
        ticket.reminder_sent = True
        ticket.reminder_sent_at = datetime.now(timezone.utc)

    db.commit()
    return stats


def send_event_update_notifications(
    db: Session,
    event_id: int,
    message: str,
    update_type: str = "general",
    channels: list[NotificationChannel] = None,
) -> dict:
    """Send update notifications to all ticket holders."""
    if channels is None:
        channels = [NotificationChannel.EMAIL]

    event = (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    # Get all paid/checked-in ticket holders
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.event_goer))
        .join(TicketTier)
        .filter(TicketTier.event_id == event_id)
        .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
        .all()
    )

    stats = {
        "event_id": event_id,
        "event_name": event.name,
        "update_type": update_type,
        "message": message,
        "notifications_sent": 0,
    }

    event_goers_notified = set()

    for ticket in tickets:
        event_goer = ticket.event_goer

        if event_goer.id in event_goers_notified:
            continue

        event_goers_notified.add(event_goer.id)

        # Send email update
        if NotificationChannel.EMAIL in channels and event_goer.email_opt_in:
            try:
                from app.services.email import send_event_update_email
                success = send_event_update_email(
                    to_email=event_goer.email,
                    recipient_name=event_goer.name,
                    event_name=event.name,
                    event_date=event.event_date,
                    event_time=event.event_time,
                    venue_name=event.venue.name,
                    update_message=message,
                )
                if success:
                    stats["notifications_sent"] += 1
                    log_notification(
                        db, event_goer.id, NotificationType.EVENT_UPDATE,
                        NotificationChannel.EMAIL, message,
                        subject=f"Update: {event.name}",
                        event_id=event_id,
                        status=NotificationStatus.SENT,
                    )
            except Exception as e:
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_UPDATE,
                    NotificationChannel.EMAIL, message,
                    event_id=event_id,
                    status=NotificationStatus.FAILED,
                    failed_reason=str(e),
                )

        # Send SMS update
        if NotificationChannel.SMS in channels and event_goer.sms_opt_in and event_goer.phone:
            result = send_event_update_sms(
                to_phone=event_goer.phone,
                recipient_name=event_goer.name,
                event_name=event.name,
                update_message=message,
            )
            if result["success"]:
                stats["notifications_sent"] += 1
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_UPDATE,
                    NotificationChannel.SMS, message,
                    event_id=event_id,
                    status=NotificationStatus.SENT,
                    external_id=result.get("sid"),
                )

    db.commit()
    return stats


def send_event_cancellation_notifications(
    db: Session,
    event_id: int,
    reason: Optional[str] = None,
    channels: list[NotificationChannel] = None,
) -> dict:
    """Send cancellation notifications to all ticket holders."""
    if channels is None:
        channels = [NotificationChannel.EMAIL]

    event = (
        db.query(Event)
        .options(joinedload(Event.venue))
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        return {"error": "Event not found"}

    # Get all ticket holders (any status except cancelled/refunded)
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.event_goer))
        .join(TicketTier)
        .filter(TicketTier.event_id == event_id)
        .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.PENDING, TicketStatus.CHECKED_IN]))
        .all()
    )

    stats = {
        "event_id": event_id,
        "event_name": event.name,
        "notifications_sent": 0,
    }

    event_goers_notified = set()

    for ticket in tickets:
        event_goer = ticket.event_goer

        if event_goer.id in event_goers_notified:
            continue

        event_goers_notified.add(event_goer.id)

        message = f"{event.name} on {event.event_date} has been cancelled."
        if reason:
            message += f" Reason: {reason}"

        # Send email
        if NotificationChannel.EMAIL in channels and event_goer.email_opt_in:
            try:
                from app.services.email import send_event_cancelled_email
                success = send_event_cancelled_email(
                    to_email=event_goer.email,
                    recipient_name=event_goer.name,
                    event_name=event.name,
                    event_date=event.event_date,
                    venue_name=event.venue.name,
                    cancellation_reason=reason,
                )
                if success:
                    stats["notifications_sent"] += 1
                    log_notification(
                        db, event_goer.id, NotificationType.EVENT_CANCELLED,
                        NotificationChannel.EMAIL, message,
                        subject=f"Cancelled: {event.name}",
                        event_id=event_id,
                        status=NotificationStatus.SENT,
                    )
            except Exception as e:
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_CANCELLED,
                    NotificationChannel.EMAIL, message,
                    event_id=event_id,
                    status=NotificationStatus.FAILED,
                    failed_reason=str(e),
                )

        # Send SMS
        if NotificationChannel.SMS in channels and event_goer.sms_opt_in and event_goer.phone:
            result = send_event_cancelled_sms(
                to_phone=event_goer.phone,
                recipient_name=event_goer.name,
                event_name=event.name,
                event_date=event.event_date,
                cancellation_reason=reason,
            )
            if result["success"]:
                stats["notifications_sent"] += 1
                log_notification(
                    db, event_goer.id, NotificationType.EVENT_CANCELLED,
                    NotificationChannel.SMS, message,
                    event_id=event_id,
                    status=NotificationStatus.SENT,
                    external_id=result.get("sid"),
                )

    db.commit()
    return stats


def send_sms_ticket(db: Session, ticket_id: int) -> dict:
    """Send ticket details via SMS."""
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event_goer),
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        return {"success": False, "message": "Ticket not found"}

    if ticket.status != TicketStatus.PAID:
        return {"success": False, "message": "Ticket not paid"}

    event_goer = ticket.event_goer
    if not event_goer.phone:
        return {"success": False, "message": "No phone number on file"}

    event = ticket.ticket_tier.event
    venue = event.venue

    result = send_ticket_sms(
        to_phone=event_goer.phone,
        recipient_name=event_goer.name,
        event_name=event.name,
        event_date=event.event_date,
        event_time=event.event_time,
        venue_name=venue.name,
        venue_address=venue.address,
        tier_name=ticket.ticket_tier.name,
        qr_code_token=ticket.qr_code_token,
    )

    if result["success"]:
        log_notification(
            db, event_goer.id, NotificationType.SMS_TICKET,
            NotificationChannel.SMS,
            f"SMS ticket for {event.name}",
            ticket_id=ticket_id,
            event_id=event.id,
            status=NotificationStatus.SENT,
            external_id=result.get("sid"),
        )
        return {"success": True, "message": "SMS ticket sent"}
    else:
        log_notification(
            db, event_goer.id, NotificationType.SMS_TICKET,
            NotificationChannel.SMS,
            f"SMS ticket for {event.name}",
            ticket_id=ticket_id,
            event_id=event.id,
            status=NotificationStatus.FAILED,
            failed_reason=result.get("error"),
        )
        return {"success": False, "message": result.get("error")}


def send_marketing_campaign(
    db: Session,
    campaign_id: int,
    channels: list[NotificationChannel] = None,
) -> dict:
    """Send a marketing campaign to opted-in users."""
    if channels is None:
        channels = [NotificationChannel.EMAIL]

    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()

    if not campaign:
        return {"error": "Campaign not found"}

    # Get target recipients
    query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)

    if campaign.target_event_id:
        # Target attendees of a specific event
        event_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .filter(TicketTier.event_id == campaign.target_event_id)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(event_goer_ids))

    # Segment targeting
    segments = {}
    if campaign.target_segments:
        try:
            segments = json.loads(campaign.target_segments)
        except (json.JSONDecodeError, TypeError):
            segments = {}

    # VIP filter
    if segments.get("is_vip"):
        vip_goer_ids = db.query(CustomerPreference.event_goer_id).filter(CustomerPreference.is_vip == True)
        if segments.get("vip_tier"):
            vip_goer_ids = vip_goer_ids.filter(CustomerPreference.vip_tier == segments["vip_tier"])
        query = query.filter(EventGoer.id.in_(vip_goer_ids))

    # Min events attended filter (calculated on-the-fly from tickets)
    if segments.get("min_events"):
        min_events = int(segments["min_events"])
        attended_subq = (
            db.query(
                Ticket.event_goer_id,
                func.count(func.distinct(TicketTier.event_id)).label("event_count")
            )
            .join(TicketTier)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .group_by(Ticket.event_goer_id)
            .having(func.count(func.distinct(TicketTier.event_id)) >= min_events)
            .subquery()
        )
        query = query.filter(EventGoer.id.in_(db.query(attended_subq.c.event_goer_id)))

    # Min spent filter (calculated on-the-fly from ticket prices)
    if segments.get("min_spent_cents"):
        min_spent = int(segments["min_spent_cents"])
        spent_subq = (
            db.query(
                Ticket.event_goer_id,
                func.sum(TicketTier.price).label("total_spent")
            )
            .join(TicketTier)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .group_by(Ticket.event_goer_id)
            .having(func.sum(TicketTier.price) >= min_spent)
            .subquery()
        )
        query = query.filter(EventGoer.id.in_(db.query(spent_subq.c.event_goer_id)))

    # Category filter (attended events in these categories)
    if segments.get("category_ids"):
        category_ids = segments["category_ids"]
        category_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .join(Event, TicketTier.event_id == Event.id)
            .join(event_category_link, Event.id == event_category_link.c.event_id)
            .filter(event_category_link.c.category_id.in_(category_ids))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(category_goer_ids))

    recipients = query.all()

    stats = {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_recipients": len(recipients),
        "email_sent": 0,
        "sms_sent": 0,
        "failed": 0,
    }

    campaign.total_recipients = len(recipients)
    campaign.status = "sending"

    for recipient in recipients:
        # Send email
        if NotificationChannel.EMAIL in channels:
            try:
                from app.services.email import send_marketing_email
                success = send_marketing_email(
                    to_email=recipient.email,
                    recipient_name=recipient.name,
                    subject=campaign.subject,
                    content=campaign.content,
                )
                if success:
                    stats["email_sent"] += 1
                    campaign.sent_count += 1
                    log_notification(
                        db, recipient.id, NotificationType.MARKETING,
                        NotificationChannel.EMAIL, campaign.content,
                        subject=campaign.subject,
                        status=NotificationStatus.SENT,
                    )
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1

        # Send SMS
        if NotificationChannel.SMS in channels and recipient.sms_opt_in and recipient.phone:
            result = send_marketing_sms(
                to_phone=recipient.phone,
                recipient_name=recipient.name,
                message_content=campaign.content[:160],  # SMS character limit
            )
            if result["success"]:
                stats["sms_sent"] += 1
                campaign.sent_count += 1
                log_notification(
                    db, recipient.id, NotificationType.MARKETING,
                    NotificationChannel.SMS, campaign.content[:160],
                    status=NotificationStatus.SENT,
                    external_id=result.get("sid"),
                )
            else:
                stats["failed"] += 1

    campaign.status = "sent"
    campaign.sent_at = datetime.now(timezone.utc)
    db.commit()

    return stats
