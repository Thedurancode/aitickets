"""
Alert Delivery Service

Sends alerts via multiple channels (Slack, Email, SMS) when the autonomous
intelligence system detects issues that require attention.

Supports:
- Slack webhooks (instant notifications to team channels)
- Email (via existing email service)
- SMS (via Twilio for critical alerts)
- In-app notifications (stored in database)
"""

import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum

from app.config import get_settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    SLACK = "slack"
    EMAIL = "email"
    SMS = "sms"
    DATABASE = "database"


def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    channels: Optional[List[AlertChannel]] = None,
    event_id: Optional[int] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Send alert via multiple channels.

    Args:
        title: Alert title/subject
        message: Alert message body
        severity: Alert severity level (low/medium/high/critical)
        channels: Which channels to use (defaults based on severity)
        event_id: Related event ID (if applicable)
        metadata: Additional context data

    Returns:
        Dict with delivery results per channel
    """
    settings = get_settings()

    # Default channels based on severity
    if channels is None:
        channels = _get_default_channels(severity)

    results = {
        "title": title,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "delivery": {},
    }

    # Send to each channel
    for channel in channels:
        try:
            if channel == AlertChannel.SLACK:
                result = _send_slack_alert(title, message, severity, event_id, metadata)
                results["delivery"]["slack"] = result

            elif channel == AlertChannel.EMAIL:
                result = _send_email_alert(title, message, severity, event_id, metadata)
                results["delivery"]["email"] = result

            elif channel == AlertChannel.SMS:
                result = _send_sms_alert(title, message, severity, metadata)
                results["delivery"]["sms"] = result

            elif channel == AlertChannel.DATABASE:
                result = _store_alert_in_db(title, message, severity, event_id, metadata)
                results["delivery"]["database"] = result

        except Exception as e:
            logger.error(f"Failed to send alert via {channel}: {e}")
            results["delivery"][channel] = {"status": "failed", "error": str(e)}

    return results


def _get_default_channels(severity: AlertSeverity) -> List[AlertChannel]:
    """Determine which channels to use based on severity."""
    if severity == AlertSeverity.CRITICAL:
        # Critical: All channels
        return [AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.DATABASE]
    elif severity == AlertSeverity.HIGH:
        # High: Slack + Email + Database
        return [AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.DATABASE]
    elif severity == AlertSeverity.MEDIUM:
        # Medium: Slack + Database
        return [AlertChannel.SLACK, AlertChannel.DATABASE]
    else:
        # Low: Database only
        return [AlertChannel.DATABASE]


def _send_slack_alert(
    title: str,
    message: str,
    severity: AlertSeverity,
    event_id: Optional[int],
    metadata: Optional[Dict],
) -> Dict:
    """Send alert to Slack via webhook."""
    settings = get_settings()

    if not settings.slack_webhook_url:
        return {"status": "skipped", "reason": "Slack webhook not configured"}

    # Color based on severity
    color_map = {
        AlertSeverity.LOW: "#36a64f",  # Green
        AlertSeverity.MEDIUM: "#ff9900",  # Orange
        AlertSeverity.HIGH: "#ff0000",  # Red
        AlertSeverity.CRITICAL: "#8b0000",  # Dark red
    }

    # Build Slack message
    payload = {
        "username": "AI Tickets Intelligence",
        "icon_emoji": ":robot_face:",
        "attachments": [
            {
                "color": color_map.get(severity, "#808080"),
                "title": f"🚨 {title}",
                "text": message,
                "fields": [
                    {
                        "title": "Severity",
                        "value": severity.upper(),
                        "short": True,
                    },
                    {
                        "title": "Timestamp",
                        "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "short": True,
                    },
                ],
                "footer": "AI Tickets Autonomous Intelligence",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ],
    }

    # Add event link if available
    if event_id:
        payload["attachments"][0]["fields"].append({
            "title": "Event",
            "value": f"<{settings.app_url}/events/{event_id}|View Event>",
            "short": True,
        })

    # Add metadata fields
    if metadata:
        for key, value in metadata.items():
            if len(payload["attachments"][0]["fields"]) < 10:  # Slack limit
                payload["attachments"][0]["fields"].append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": True,
                })

    try:
        response = requests.post(
            settings.slack_webhook_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

        logger.info(f"Slack alert sent: {title}")
        return {"status": "sent", "channel": "slack"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Slack webhook failed: {e}")
        return {"status": "failed", "error": str(e)}


def _send_email_alert(
    title: str,
    message: str,
    severity: AlertSeverity,
    event_id: Optional[int],
    metadata: Optional[Dict],
) -> Dict:
    """Send alert via email."""
    settings = get_settings()

    if not settings.admin_email:
        return {"status": "skipped", "reason": "Admin email not configured"}

    try:
        from app.services.email import send_email

        # Format email body
        body_parts = [
            f"<h2>🚨 {title}</h2>",
            f"<p><strong>Severity:</strong> {severity.upper()}</p>",
            f"<p>{message}</p>",
        ]

        if event_id:
            body_parts.append(
                f"<p><strong>Event:</strong> <a href='{settings.app_url}/events/{event_id}'>View Event</a></p>"
            )

        if metadata:
            body_parts.append("<h3>Details:</h3><ul>")
            for key, value in metadata.items():
                body_parts.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")
            body_parts.append("</ul>")

        body_parts.append(
            f"<p><small>Sent by AI Tickets Autonomous Intelligence at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</small></p>"
        )

        html_body = "\n".join(body_parts)

        send_email(
            to_email=settings.admin_email,
            subject=f"[AI Tickets Alert - {severity.upper()}] {title}",
            body=html_body,
        )

        logger.info(f"Email alert sent to {settings.admin_email}: {title}")
        return {"status": "sent", "channel": "email", "recipient": settings.admin_email}

    except Exception as e:
        logger.error(f"Email alert failed: {e}")
        return {"status": "failed", "error": str(e)}


def _send_sms_alert(
    title: str,
    message: str,
    severity: AlertSeverity,
    metadata: Optional[Dict],
) -> Dict:
    """Send alert via SMS (for critical alerts only)."""
    settings = get_settings()

    if not settings.admin_phone:
        return {"status": "skipped", "reason": "Admin phone not configured"}

    # Only send SMS for critical alerts to avoid spam
    if severity != AlertSeverity.CRITICAL:
        return {"status": "skipped", "reason": "SMS only sent for critical alerts"}

    try:
        from app.services.sms import send_sms

        # Keep SMS short
        sms_body = f"🚨 CRITICAL: {title}\n{message[:100]}"

        send_sms(
            to_phone=settings.admin_phone,
            message=sms_body,
        )

        logger.info(f"SMS alert sent to {settings.admin_phone}: {title}")
        return {"status": "sent", "channel": "sms", "recipient": settings.admin_phone}

    except Exception as e:
        logger.error(f"SMS alert failed: {e}")
        return {"status": "failed", "error": str(e)}


def _store_alert_in_db(
    title: str,
    message: str,
    severity: AlertSeverity,
    event_id: Optional[int],
    metadata: Optional[Dict],
) -> Dict:
    """Store alert in database for in-app notifications."""
    try:
        from app.database import SessionLocal
        from app.models import Alert

        db = SessionLocal()
        try:
            alert = Alert(
                title=title,
                message=message,
                severity=severity,
                event_id=event_id,
                alert_metadata=metadata or {},
                is_read=False,
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)

            # Broadcast to SSE clients for real-time push
            try:
                from app.routers.alert_stream import broadcast_alert
                broadcast_alert(alert)
            except Exception as e:
                logger.warning(f"Failed to broadcast alert via SSE: {e}")

            logger.info(f"Alert stored in database: {title}")
            return {"status": "stored", "alert_id": alert.id}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to store alert in database: {e}")
        return {"status": "failed", "error": str(e)}


# Convenience functions for common alert types

def send_ad_performance_alert(event_id: int, campaign_name: str, roas: float, recommendation: str):
    """Alert for underperforming ad campaigns."""
    send_alert(
        title=f"Ad Campaign Underperforming - {campaign_name}",
        message=f"ROAS: {roas:.2f} (below threshold)\n\nRecommendation: {recommendation}",
        severity=AlertSeverity.MEDIUM if roas > 0.5 else AlertSeverity.HIGH,
        event_id=event_id,
        metadata={
            "campaign": campaign_name,
            "roas": f"{roas:.2f}",
            "action": "auto_paused" if roas < 1.0 else "monitoring",
        },
    )


def send_refund_spike_alert(event_id: int, event_name: str, refund_count: int, refund_rate: float):
    """Alert for unusual refund patterns."""
    send_alert(
        title=f"Refund Spike Detected - {event_name}",
        message=f"{refund_count} refunds in last 24 hours ({refund_rate*100:.1f}% of sales)\n\nThis may indicate an event issue. Investigate immediately.",
        severity=AlertSeverity.HIGH if refund_rate > 0.1 else AlertSeverity.MEDIUM,
        event_id=event_id,
        metadata={
            "refund_count": refund_count,
            "refund_rate": f"{refund_rate*100:.1f}%",
        },
    )


def send_inventory_alert(event_id: int, event_name: str, days_until: int, sell_through: float):
    """Alert for inventory pressure."""
    severity = AlertSeverity.HIGH if days_until < 7 and sell_through < 0.5 else AlertSeverity.MEDIUM

    send_alert(
        title=f"Inventory Pressure - {event_name}",
        message=f"Only {sell_through*100:.0f}% sold with {days_until} days remaining\n\nRecommend launching urgency campaign or reducing price.",
        severity=severity,
        event_id=event_id,
        metadata={
            "days_until_event": days_until,
            "sell_through": f"{sell_through*100:.1f}%",
        },
    )


def send_churn_alert(customer_count: int, high_risk_count: int):
    """Alert for customer churn risk."""
    send_alert(
        title="Customer Churn Risk Detected",
        message=f"{high_risk_count} high-value customers at risk of churning\n\nRecommend launching win-back campaign with discount code.",
        severity=AlertSeverity.MEDIUM,
        metadata={
            "total_at_risk": customer_count,
            "high_risk": high_risk_count,
            "recommendation": "Launch win-back campaign",
        },
    )


def send_system_error_alert(error_type: str, error_message: str, component: str):
    """Alert for system errors."""
    send_alert(
        title=f"System Error - {component}",
        message=f"Error Type: {error_type}\n\n{error_message}",
        severity=AlertSeverity.CRITICAL,
        metadata={
            "component": component,
            "error_type": error_type,
        },
    )
