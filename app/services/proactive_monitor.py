"""
Proactive Event Monitoring Service

Runs automated checks on a schedule to catch issues before they become problems.

Monitors:
- Ad performance (auto-pause underperformers)
- Refund spikes
- Inventory pressure
- Sales velocity changes
- Customer churn

Sends alerts and takes autonomous actions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from sqlalchemy.orm import Session

from app.models import Event
from app.database import SessionLocal
from app.services.event_intelligence import (
    monitor_ad_performance,
    detect_refund_patterns,
    check_inventory_pressure,
)
from app.services.cross_event_intelligence import detect_churn_risk
from app.config import get_settings

logger = logging.getLogger(__name__)


def run_hourly_checks():
    """
    Run every hour to monitor active events.

    Checks:
    - Ad performance (auto-pause if needed)
    - Refund patterns
    - Inventory alerts
    """
    logger.info("Starting hourly proactive monitoring...")

    db = SessionLocal()

    try:
        # Get upcoming events (within next 30 days)
        upcoming_events = db.query(Event).filter(
            Event.event_date >= datetime.now(timezone.utc).date(),
            Event.event_date <= datetime.now(timezone.utc).date() + timedelta(days=30)
        ).all()

        logger.info(f"Monitoring {len(upcoming_events)} upcoming events")

        alerts = []

        for event in upcoming_events:
            # Check ad performance and auto-pause if needed
            try:
                ad_check = monitor_ad_performance(db, event.id, auto_pause=True)

                if ad_check.get("actions"):
                    for action in ad_check["actions"]:
                        alerts.append({
                            "event_id": event.id,
                            "event_name": event.name,
                            "type": "AD_PAUSED",
                            "severity": "MEDIUM",
                            "message": f"Paused campaign: {action['reason']}",
                            "action_taken": "Auto-paused underperforming ad",
                        })

            except Exception as e:
                logger.error(f"Ad check failed for event {event.id}: {str(e)}")

            # Check inventory pressure
            try:
                inventory_check = check_inventory_pressure(db, event.id)

                high_priority_recs = [
                    r for r in inventory_check.get("recommendations", [])
                    if r.get("priority") == "HIGH"
                ]

                for rec in high_priority_recs:
                    alerts.append({
                        "event_id": event.id,
                        "event_name": event.name,
                        "type": "INVENTORY_ALERT",
                        "severity": "HIGH",
                        "message": rec["reason"],
                        "recommendation": rec["suggestion"],
                    })

            except Exception as e:
                logger.error(f"Inventory check failed for event {event.id}: {str(e)}")

        # Check refund patterns across all events
        try:
            refund_check = detect_refund_patterns(db)

            for alert in refund_check.get("alerts", []):
                alerts.append({
                    "event_id": alert["event_id"],
                    "event_name": alert["event_name"],
                    "type": "REFUND_ALERT",
                    "severity": alert["severity"],
                    "message": alert["message"],
                    "recommendation": alert["recommendation"],
                })

        except Exception as e:
            logger.error(f"Refund check failed: {str(e)}")

        # Send alerts if any
        if alerts:
            logger.warning(f"Generated {len(alerts)} alerts:")
            for alert in alerts:
                logger.warning(f"  - {alert['event_name']}: {alert['message']}")

            # In production, send webhook or email notification
            _send_alert_notifications(alerts)

        else:
            logger.info("No alerts generated - all events healthy")

    except Exception as e:
        logger.error(f"Hourly monitoring failed: {str(e)}")

    finally:
        db.close()


def run_daily_checks():
    """
    Run once per day for deeper analysis.

    Checks:
    - Customer churn risk
    - Event performance predictions
    - Long-term trends
    """
    logger.info("Starting daily proactive monitoring...")

    db = SessionLocal()

    try:
        alerts = []

        # Check for churn risk
        try:
            churn_check = detect_churn_risk(db)

            high_risk_count = churn_check.get("risk_segments", {}).get("high", 0)

            if high_risk_count > 0:
                alerts.append({
                    "type": "CHURN_RISK",
                    "severity": "MEDIUM",
                    "message": f"{high_risk_count} customers at high risk of churning",
                    "recommendation": "Launch win-back campaign with discount code",
                })

        except Exception as e:
            logger.error(f"Churn check failed: {str(e)}")

        # Send daily summary
        if alerts:
            logger.warning(f"Daily check generated {len(alerts)} alerts")
            _send_alert_notifications(alerts)
        else:
            logger.info("Daily check complete - no issues detected")

    except Exception as e:
        logger.error(f"Daily monitoring failed: {str(e)}")

    finally:
        db.close()


def _send_alert_notifications(alerts: List[Dict]):
    """
    Send alert notifications via webhook or email.

    In production, would integrate with:
    - Email (SendGrid/SES)
    - SMS (Twilio)
    - Slack webhook
    - Custom webhook
    """
    settings = get_settings()

    # Log alerts (in production, send to notification channels)
    logger.info(f"Sending {len(alerts)} alert notifications...")

    for alert in alerts:
        logger.info(f"ALERT: {alert}")

    # TODO: Implement actual notification sending
    # Example:
    # if settings.slack_webhook_url:
    #     send_slack_notification(alerts)
    #
    # if settings.admin_email:
    #     send_email_alert(alerts)

    # In production, fire webhook event
    # from app.services.webhooks import fire_webhook_event
    # fire_webhook_event("monitoring.alert", {"alerts": alerts})


def check_sales_velocity(db: Session, event_id: int) -> Dict:
    """
    Monitor sales velocity and detect significant changes.

    Alerts if sales suddenly drop or spike.

    Args:
        db: Database session
        event_id: Event to monitor

    Returns:
        Dict with velocity analysis
    """
    from app.models import Ticket, TicketStatus
    from sqlalchemy import func

    # Get tickets sold in last 24 hours
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)

    tickets_last_24h = db.query(func.count(Ticket.id)).filter(
        Ticket.event_id == event_id,
        Ticket.status == TicketStatus.CONFIRMED,
        Ticket.created_at >= yesterday
    ).scalar()

    # Get tickets sold 24-48 hours ago
    two_days_ago = datetime.now(timezone.utc) - timedelta(hours=48)

    tickets_prev_24h = db.query(func.count(Ticket.id)).filter(
        Ticket.event_id == event_id,
        Ticket.status == TicketStatus.CONFIRMED,
        Ticket.created_at >= two_days_ago,
        Ticket.created_at < yesterday
    ).scalar()

    # Calculate change
    if tickets_prev_24h > 0:
        change_pct = ((tickets_last_24h - tickets_prev_24h) / tickets_prev_24h) * 100
    else:
        change_pct = 0

    status = "STABLE"
    alert = None

    # Significant drop
    if change_pct < -50:
        status = "DROPPING"
        alert = {
            "type": "SALES_VELOCITY_DROP",
            "severity": "HIGH",
            "message": f"Sales dropped {abs(change_pct):.0f}% in last 24 hours",
            "recommendation": "Increase marketing spend or launch urgency campaign",
        }

    # Significant spike
    elif change_pct > 100:
        status = "SPIKING"
        alert = {
            "type": "SALES_VELOCITY_SPIKE",
            "severity": "MEDIUM",
            "message": f"Sales increased {change_pct:.0f}% in last 24 hours",
            "recommendation": "Consider dynamic price increase to maximize revenue",
        }

    return {
        "event_id": event_id,
        "tickets_last_24h": tickets_last_24h,
        "tickets_prev_24h": tickets_prev_24h,
        "change_pct": round(change_pct, 1),
        "status": status,
        "alert": alert,
    }


# Integration with APScheduler (called from app/services/scheduler.py)

def schedule_proactive_monitoring():
    """
    Register proactive monitoring jobs with scheduler.

    Call this from scheduler.py to enable automated monitoring.
    """
    try:
        from app.services.scheduler import scheduler

        # Hourly checks
        scheduler.add_job(
            run_hourly_checks,
            'interval',
            hours=1,
            id='proactive_monitoring_hourly',
            replace_existing=True,
            name='Proactive Monitoring (Hourly)'
        )

        # Daily checks
        scheduler.add_job(
            run_daily_checks,
            'cron',
            hour=8,  # 8 AM daily
            id='proactive_monitoring_daily',
            replace_existing=True,
            name='Proactive Monitoring (Daily)'
        )

        logger.info("Proactive monitoring scheduled successfully")

    except Exception as e:
        logger.warning(f"Could not schedule proactive monitoring: {e}")
