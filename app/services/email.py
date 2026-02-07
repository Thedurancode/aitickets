import resend
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.services.qrcode import generate_qr_code_base64

# Set up Jinja2 template environment
templates_dir = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(templates_dir)))


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Internal helper to send emails via Resend."""
    settings = get_settings()

    if not settings.resend_api_key:
        print("Warning: RESEND_API_KEY not configured, skipping email")
        return False

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": settings.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_ticket_email(
    to_email: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str,
    tier_name: str,
    ticket_id: int,
    qr_code_token: str,
) -> bool:
    """Send a ticket confirmation email with QR code."""
    settings = get_settings()

    # Generate QR code as base64
    qr_code_base64 = generate_qr_code_base64(qr_code_token)

    # Render email template
    template = env.get_template("ticket_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        event_name=event_name,
        event_date=event_date,
        event_time=event_time,
        venue_name=venue_name,
        venue_address=venue_address,
        tier_name=tier_name,
        ticket_id=ticket_id,
        qr_code_base64=qr_code_base64,
        validation_url=f"{settings.base_url}/tickets/validate/{qr_code_token}",
    )

    return _send_email(to_email, f"Your Ticket for {event_name}", html_content)


def send_reminder_email(
    to_email: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str,
    hours_until: int,
) -> bool:
    """Send an event reminder email."""
    template = env.get_template("reminder_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        event_name=event_name,
        event_date=event_date,
        event_time=event_time,
        venue_name=venue_name,
        venue_address=venue_address,
        hours_until=hours_until,
    )

    return _send_email(to_email, f"Reminder: {event_name} is coming up!", html_content)


def send_event_update_email(
    to_email: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    update_message: str,
) -> bool:
    """Send an event update notification email."""
    template = env.get_template("event_update_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        event_name=event_name,
        event_date=event_date,
        event_time=event_time,
        venue_name=venue_name,
        update_message=update_message,
    )

    return _send_email(to_email, f"Update: {event_name}", html_content)


def send_event_cancelled_email(
    to_email: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    venue_name: str,
    cancellation_reason: Optional[str] = None,
) -> bool:
    """Send an event cancellation notification email."""
    template = env.get_template("event_cancelled_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        event_name=event_name,
        event_date=event_date,
        venue_name=venue_name,
        cancellation_reason=cancellation_reason,
    )

    return _send_email(to_email, f"Cancelled: {event_name}", html_content)


def send_event_postponed_email(
    to_email: str,
    recipient_name: str,
    event_name: str,
    original_date: str,
    new_date: str = None,
    new_time: str = None,
    venue_name: str = None,
    postponement_reason: Optional[str] = None,
) -> bool:
    """Send an event postponement notification email."""
    template = env.get_template("event_postponed_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        event_name=event_name,
        original_date=original_date,
        new_date=new_date,
        new_time=new_time,
        venue_name=venue_name,
        postponement_reason=postponement_reason,
    )

    return _send_email(to_email, f"Postponed: {event_name}", html_content)


def send_marketing_email(
    to_email: str,
    recipient_name: str,
    subject: str,
    content: str,
) -> bool:
    """Send a marketing email."""
    settings = get_settings()
    template = env.get_template("marketing_email.html")
    html_content = template.render(
        recipient_name=recipient_name,
        content=content,
        unsubscribe_url=f"{settings.base_url}/unsubscribe?email={to_email}",
    )

    return _send_email(to_email, subject, html_content)
