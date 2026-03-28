import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import get_settings
from app.services.retry import with_retry

logger = logging.getLogger(__name__)


def get_twilio_client():
    """Get configured Twilio client."""
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


@with_retry(max_attempts=3, base_delay=1.0, retryable=(ConnectionError, TimeoutError, OSError))
def _send_sms_with_retry(client, from_number: str, to_phone: str, message: str):
    """Low-level send with retry on transient network errors."""
    return client.messages.create(body=message, from_=from_number, to=to_phone)


def send_sms(to_phone: str, message: str) -> dict:
    """
    Send an SMS message via Twilio.
    Returns dict with success status and message SID or error.
    """
    settings = get_settings()
    client = get_twilio_client()

    if not client:
        return {
            "success": False,
            "error": "Twilio not configured",
            "sid": None,
        }

    # Ensure phone number has country code
    if not to_phone.startswith("+"):
        to_phone = f"+1{to_phone}"  # Default to US

    try:
        message_obj = _send_sms_with_retry(client, settings.twilio_phone_number, to_phone, message)
        return {
            "success": True,
            "sid": message_obj.sid,
            "error": None,
        }
    except TwilioRestException as e:
        logger.error("Twilio API error sending to %s: %s", to_phone, e)
        return {
            "success": False,
            "sid": None,
            "error": str(e),
        }
    except Exception as e:
        logger.exception("Unexpected error sending SMS to %s", to_phone)
        return {
            "success": False,
            "sid": None,
            "error": str(e),
        }


def send_ticket_sms(
    to_phone: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str,
    tier_name: str,
    qr_code_token: str,
) -> dict:
    """Send ticket confirmation via SMS."""
    settings = get_settings()
    validation_url = f"{settings.base_url}/api/tickets/validate/{qr_code_token}"

    message = (
        f"🎫 {recipient_name}, your ticket is confirmed!\n\n"
        f"Event: {event_name}\n"
        f"Date: {event_date} at {event_time}\n"
        f"Venue: {venue_name}\n"
        f"Tier: {tier_name}\n\n"
        f"Show this link at entry:\n{validation_url}"
    )

    return send_sms(to_phone, message)


def send_reminder_sms(
    to_phone: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: str,
    hours_until: int,
) -> dict:
    """Send event reminder via SMS."""
    time_text = f"in {hours_until} hours" if hours_until > 1 else "in 1 hour"
    if hours_until >= 24:
        days = hours_until // 24
        time_text = f"tomorrow" if days == 1 else f"in {days} days"

    message = (
        f"⏰ Reminder: {event_name} is {time_text}!\n\n"
        f"Date: {event_date} at {event_time}\n"
        f"Venue: {venue_name}\n"
        f"Address: {venue_address}\n\n"
        f"See you there! 🎉"
    )

    return send_sms(to_phone, message)


def send_event_update_sms(
    to_phone: str,
    recipient_name: str,
    event_name: str,
    update_message: str,
) -> dict:
    """Send event update notification via SMS."""
    message = (
        f"📢 Update for {event_name}:\n\n"
        f"{update_message}\n\n"
        f"Check your email for full details."
    )

    return send_sms(to_phone, message)


def send_event_cancelled_sms(
    to_phone: str,
    recipient_name: str,
    event_name: str,
    event_date: str,
    cancellation_reason: str = None,
) -> dict:
    """Send event cancellation notification via SMS."""
    message = f"❌ {event_name} on {event_date} has been cancelled."

    if cancellation_reason:
        message += f"\n\nReason: {cancellation_reason}"

    message += "\n\nA refund will be processed. Check your email for details."

    return send_sms(to_phone, message)


def send_event_postponed_sms(
    to_phone: str,
    recipient_name: str,
    event_name: str,
    original_date: str,
    new_date: str = None,
    new_time: str = None,
    postponement_reason: str = None,
) -> dict:
    """Send event postponement notification via SMS."""
    message = f"📅 {event_name} originally on {original_date} has been postponed."

    if new_date and new_time:
        message += f"\n\nNew date: {new_date} at {new_time}"
    elif new_date:
        message += f"\n\nNew date: {new_date}"

    if postponement_reason:
        message += f"\n\nReason: {postponement_reason}"

    message += "\n\nYour tickets remain valid. Check your email for details."

    return send_sms(to_phone, message)


def send_style_picker_sms(
    to_phone: str,
    event_name: str,
    picker_url: str,
) -> dict:
    """Send SMS with a link to the flyer style picker page."""
    message = (
        f"Pick a flyer style for {event_name}!\n\n"
        f"Tap to choose: {picker_url}\n\n"
        f"This link expires in 24 hours."
    )
    return send_sms(to_phone, message)


def send_marketing_sms(
    to_phone: str,
    recipient_name: str,
    message_content: str,
) -> dict:
    """Send marketing message via SMS."""
    message = f"{message_content}\n\nReply STOP to unsubscribe."
    return send_sms(to_phone, message)
