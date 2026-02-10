"""
Abandoned Cart Recovery Service

Detects pending tickets (unpaid checkout sessions), sends recovery emails/SMS,
and cleans up stale carts after 24 hours.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sqlfunc

from app.models import (
    Ticket,
    TicketStatus,
    TicketTier,
    EventGoer,
    Notification,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)

ABANDONED_THRESHOLD_MINUTES = 30
STALE_THRESHOLD_HOURS = 24


def check_abandoned_carts(db: Session) -> dict:
    """Find PENDING tickets older than 30 minutes that haven't received a recovery email."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=ABANDONED_THRESHOLD_MINUTES)
    stale_cutoff = now - timedelta(hours=STALE_THRESHOLD_HOURS)

    abandoned = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
            joinedload(Ticket.event_goer),
        )
        .filter(
            Ticket.status == TicketStatus.PENDING,
            Ticket.recovery_sent_at.is_(None),
            Ticket.created_at <= cutoff,
            Ticket.created_at > stale_cutoff,  # Don't recover tickets about to be cleaned up
        )
        .all()
    )

    # Group by event_goer
    by_goer = {}
    for ticket in abandoned:
        goer_id = ticket.event_goer_id
        if goer_id not in by_goer:
            by_goer[goer_id] = {
                "event_goer_id": goer_id,
                "name": ticket.event_goer.name if ticket.event_goer else "Guest",
                "email": ticket.event_goer.email if ticket.event_goer else None,
                "phone": ticket.event_goer.phone if ticket.event_goer else None,
                "tickets": [],
            }
        by_goer[goer_id]["tickets"].append({
            "ticket_id": ticket.id,
            "event_name": ticket.ticket_tier.event.name if ticket.ticket_tier and ticket.ticket_tier.event else "Unknown",
            "event_id": ticket.ticket_tier.event_id if ticket.ticket_tier else None,
            "tier_name": ticket.ticket_tier.name if ticket.ticket_tier else "Unknown",
            "price_cents": ticket.ticket_tier.price if ticket.ticket_tier else 0,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        })

    carts = list(by_goer.values())
    return {
        "abandoned_count": len(carts),
        "total_tickets": len(abandoned),
        "carts": carts,
    }


def send_cart_recovery(db: Session, email: str = None, event_goer_id: int = None) -> dict:
    """Send recovery email/SMS to a specific customer with abandoned cart."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=ABANDONED_THRESHOLD_MINUTES)

    filters = [
        Ticket.status == TicketStatus.PENDING,
        Ticket.recovery_sent_at.is_(None),
        Ticket.created_at <= cutoff,
    ]

    if email:
        goer = db.query(EventGoer).filter(EventGoer.email == email).first()
        if not goer:
            return {"error": f"No customer found with email {email}"}
        filters.append(Ticket.event_goer_id == goer.id)
    elif event_goer_id:
        goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
        if not goer:
            return {"error": f"No customer found with ID {event_goer_id}"}
        filters.append(Ticket.event_goer_id == goer.id)
    else:
        return {"error": "Provide either email or event_goer_id"}

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
        )
        .filter(*filters)
        .all()
    )

    if not tickets:
        return {"success": True, "sent": False, "message": "No abandoned carts found for this customer."}

    # Build ticket details for the email
    items = []
    total_cents = 0
    for t in tickets:
        price = t.ticket_tier.price if t.ticket_tier else 0
        items.append({
            "event_name": t.ticket_tier.event.name if t.ticket_tier and t.ticket_tier.event else "Event",
            "tier_name": t.ticket_tier.name if t.ticket_tier else "Ticket",
            "price_dollars": round(price / 100, 2),
        })
        total_cents += price

    # Send email
    email_sent = False
    if goer.email:
        try:
            from app.services.email import send_cart_recovery_email
            email_sent = send_cart_recovery_email(
                to_email=goer.email,
                recipient_name=goer.name or "there",
                items=items,
                total_dollars=round(total_cents / 100, 2),
            )
        except Exception as e:
            logger.error(f"Cart recovery email failed: {e}")

    # Send SMS
    sms_sent = False
    if goer.phone:
        try:
            from app.services.sms import send_sms
            event_names = ", ".join(set(i["event_name"] for i in items))
            msg = f"Hi {goer.name or 'there'}! You left tickets in your cart for {event_names}. Complete your purchase before they expire!"
            result = send_sms(goer.phone, msg)
            sms_sent = result.get("success", False)
        except Exception as e:
            logger.error(f"Cart recovery SMS failed: {e}")

    # Mark tickets as recovery sent
    for t in tickets:
        t.recovery_sent_at = now
    db.commit()

    # Log notification
    try:
        from app.services.notifications import log_notification
        log_notification(
            db=db,
            event_goer_id=goer.id,
            notification_type=NotificationType.CART_RECOVERY,
            channel=NotificationChannel.EMAIL if email_sent else NotificationChannel.SMS,
            message=f"Cart recovery sent for {len(tickets)} pending ticket(s)",
            status=NotificationStatus.SENT if (email_sent or sms_sent) else NotificationStatus.FAILED,
        )
    except Exception:
        pass

    return {
        "success": True,
        "sent": True,
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "tickets_recovered": len(tickets),
        "total_value_dollars": round(total_cents / 100, 2),
        "message": f"Recovery sent to {goer.name} for {len(tickets)} pending ticket(s) worth ${round(total_cents / 100, 2)}.",
    }


def cleanup_stale_carts(db: Session) -> dict:
    """Cancel PENDING tickets older than 24 hours and restore tier inventory."""
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=STALE_THRESHOLD_HOURS)

    stale_tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.ticket_tier))
        .filter(
            Ticket.status == TicketStatus.PENDING,
            Ticket.created_at <= stale_cutoff,
        )
        .all()
    )

    if not stale_tickets:
        return {"cleaned": 0, "message": "No stale carts to clean up."}

    cancelled_count = 0
    restored_by_tier = {}
    for ticket in stale_tickets:
        ticket.status = TicketStatus.CANCELLED
        # Restore inventory
        if ticket.ticket_tier and ticket.ticket_tier.quantity_sold > 0:
            ticket.ticket_tier.quantity_sold -= 1
            tier_name = ticket.ticket_tier.name
            restored_by_tier[tier_name] = restored_by_tier.get(tier_name, 0) + 1
        cancelled_count += 1

    db.commit()
    logger.info(f"Cleaned up {cancelled_count} stale pending tickets")

    return {
        "cleaned": cancelled_count,
        "restored_by_tier": restored_by_tier,
        "message": f"Cancelled {cancelled_count} stale pending ticket(s) and restored inventory.",
    }


def run_cart_recovery_job():
    """Scheduled job: detect abandoned carts, send recovery, clean up stale ones."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        # Send recovery emails for abandoned carts (30min - 24h old)
        carts = check_abandoned_carts(db)
        for cart in carts.get("carts", []):
            if cart.get("email"):
                try:
                    send_cart_recovery(db, email=cart["email"])
                except Exception as e:
                    logger.error(f"Recovery failed for {cart['email']}: {e}")

        # Clean up stale carts (24h+ old)
        cleanup = cleanup_stale_carts(db)
        if cleanup.get("cleaned", 0) > 0:
            logger.info(cleanup["message"])
    except Exception as e:
        logger.error(f"Cart recovery job failed: {e}")
    finally:
        db.close()
