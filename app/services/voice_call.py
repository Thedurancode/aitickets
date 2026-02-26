"""
Telnyx Voice Call Service

Handles outbound voice calls to event goers for various purposes:
- Event reminders
- Ticket recovery
- Feedback surveys
- Birthday wishes
- VIP outreach
- And more
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from enum import Enum

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class CallStatus(str, Enum):
    """Status of a voice call."""
    PENDING = "pending"
    DIALING = "dialing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class CallOutcome(str, Enum):
    """Outcome of a completed call."""
    ANSWERED = "answered"
    LEFT_VOICEMAIL = "left_voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    DO_NOT_CALL = "do_not_call"
    REQUESTED_CALLBACK = "requested_callback"
    CALL_BACK_LATER = "call_back_later"


class CallGoal(str, Enum):
    """Purpose/goal of the outbound call."""
    EVENT_REMINDER = "event_reminder"
    TICKET_RECOVERY = "ticket_recovery"
    FEEDBACK_SURVEY = "feedback_survey"
    BIRTHDAY_WISH = "birthday_wish"
    VIP_OUTREACH = "vip_outreach"
    CART_RECOVERY = "cart_recovery"
    PAYMENT_RECOVERY = "payment_recovery"
    EVENT_UPDATE = "event_update"
    CUSTOM = "custom"


# Call script templates for each goal type
CALL_SCRIPTS = {
    CallGoal.EVENT_REMINDER: {
        "template": "Hi {name}! This is a friendly reminder about {event_name} happening on {event_date} at {event_time} at {venue_name}. We're excited to see you there! Do you have any questions?",
        "max_duration_seconds": 60,
        "allow_voicemail": True,
    },
    CallGoal.TICKET_RECOVERY: {
        "template": "Hi {name}! We noticed you started getting tickets for {event_name} but didn't complete your purchase. Is there anything we can help you with?",
        "max_duration_seconds": 90,
        "allow_voicemail": False,
    },
    CallGoal.FEEDBACK_SURVEY: {
        "template": "Hi {name}! Thanks for attending {event_name}. We'd love to hear your feedback. Did you enjoy the event?",
        "max_duration_seconds": 120,
        "allow_voicemail": False,
    },
    CallGoal.BIRTHDAY_WISH: {
        "template": "Hi {name}! Happy birthday from the {org_name} team! We hope you have an amazing day! As a special birthday gift, use code BIRTHDAY{discount_percent} for {discount_percent} off your next ticket!",
        "max_duration_seconds": 45,
        "allow_voicemail": True,
    },
    CallGoal.VIP_OUTREACH: {
        "template": "Hi {name}! As one of our valued VIP guests, we wanted to personally invite you to {event_name}. We have a special VIP experience prepared for you. Would you like to hear more?",
        "max_duration_seconds": 120,
        "allow_voicemail": True,
    },
    CallGoal.CART_RECOVERY: {
        "template": "Hi {name}! I noticed you have tickets waiting in your cart for {event_name}. The event is filling up fast! Would you like me to help you complete your purchase?",
        "max_duration_seconds": 90,
        "allow_voicemail": False,
    },
    CallGoal.PAYMENT_RECOVERY: {
        "template": "Hi {name}! We're having trouble processing your payment for {event_name}. Could you give us a call back to update your payment information?",
        "max_duration_seconds": 60,
        "allow_voicemail": True,
    },
    CallGoal.EVENT_UPDATE: {
        "template": "Hi {name}! Important update about {event_name} on {event_date}. {update_message}. Please check your email for full details.",
        "max_duration_seconds": 60,
        "allow_voicemail": True,
    },
}


class TelnyxClient:
    """Client for Telnyx Voice API."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.telnyx_api_key
        self.base_url = "https://api.telnyx.com/v2"
        self.telnyx_number = self.settings.telnyx_phone_number
        self.connection_id = self.settings.telnyx_connection_id
        self.enabled = bool(self.api_key and self.telnyx_number)

    def _get_headers(self) -> dict:
        """Get headers for Telnyx API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def initiate_call(
        self,
        to_phone: str,
        text: str,
        from_number: Optional[str] = None,
        max_duration_seconds: int = 120,
        caller_id: Optional[str] = None,
    ) -> dict:
        """
        Initiate an outbound voice call using Telnyx TexML application.

        Args:
            to_phone: Phone number to call (E.164 format)
            text: Text to be spoken (TTS)
            from_number: Telnyx phone number to use (defaults to configured number)
            max_duration_seconds: Maximum call duration
            caller_id: Caller ID to display

        Returns:
            Dict with call details or error
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Telnyx not configured",
                "call_id": None,
            }

        # Ensure E.164 format
        if not to_phone.startswith("+"):
            to_phone = f"+1{to_phone}"

        from_number = from_number or self.telnyx_number

        # Create TexML for text-to-speech
        texml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Gather action="{self.base_url}/calls/gather" method="POST" numDigits="1" timeout="30"><Say>{text}</Say></Gather><Say>Goodbye!</Say></Response>'

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/calls",
                    headers=self._get_headers(),
                    json={
                        "connection_id": self.connection_id,
                        "to": to_phone,
                        "from": from_number,
                        "texml": texml,
                        "timeout_seconds": max_duration_seconds,
                    }
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    return {
                        "success": True,
                        "call_id": data.get("data", {}).get("id"),
                        "status": data.get("data", {}).get("status"),
                        "error": None,
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "call_id": None,
                    }

        except httpx.HTTPError as e:
            logger.error(f"Telnyx API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": None,
            }

    def initiate_call_sync(
        self,
        to_phone: str,
        text: str,
        from_number: Optional[str] = None,
        max_duration_seconds: int = 120,
    ) -> dict:
        """
        Synchronous version of initiate_call.

        Args:
            to_phone: Phone number to call
            text: Text to be spoken
            from_number: Telnyx phone number
            max_duration_seconds: Maximum call duration

        Returns:
            Dict with call details or error
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Telnyx not configured",
                "call_id": None,
            }

        # Ensure E.164 format
        if not to_phone.startswith("+"):
            to_phone = f"+1{to_phone}"

        from_number = from_number or self.telnyx_number

        # Create TexML for text-to-speech
        texml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{text}</Say></Response>'

        try:
            import requests
            response = requests.post(
                f"{self.base_url}/calls",
                headers=self._get_headers(),
                json={
                    "connection_id": self.connection_id,
                    "to": to_phone,
                    "from": from_number,
                    "texml": texml,
                    "timeout_seconds": max_duration_seconds,
                },
                timeout=30
            )

            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "success": True,
                    "call_id": data.get("data", {}).get("id"),
                    "status": data.get("data", {}).get("status"),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "call_id": None,
                }

        except Exception as e:
            logger.error(f"Telnyx API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "call_id": None,
            }


def build_call_script(
    goal: CallGoal,
    name: str,
    event_name: Optional[str] = None,
    event_date: Optional[str] = None,
    event_time: Optional[str] = None,
    venue_name: Optional[str] = None,
    org_name: str = "AI Tickets",
    discount_percent: int = 10,
    update_message: Optional[str] = None,
    custom_script: Optional[str] = None,
) -> str:
    """
    Build a call script based on the goal and context.

    Args:
        goal: CallGoal enum value
        name: Recipient's name
        event_name: Event name (if applicable)
        event_date: Event date (if applicable)
        event_time: Event time (if applicable)
        venue_name: Venue name (if applicable)
        org_name: Organization name
        discount_percent: Discount percentage for offers
        update_message: Update message for event updates
        custom_script: Custom script for CUSTOM goal

    Returns:
        Formatted call script as text
    """
    if goal == CallGoal.CUSTOM and custom_script:
        return custom_script.format(
            name=name,
            event_name=event_name or "",
            org_name=org_name,
        )

    template = CALL_SCRIPTS.get(goal)
    if not template:
        return f"Hi {name}!"

    script = template["template"].format(
        name=name,
        event_name=event_name or "our event",
        event_date=event_date or "upcoming date",
        event_time=event_time or "the scheduled time",
        venue_name=venue_name or "the venue",
        org_name=org_name,
        discount_percent=discount_percent,
        update_message=update_message or "please check your email for details",
    )

    return script


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format."""
    if not phone:
        return ""

    # Remove all non-numeric characters
    cleaned = "".join(c for c in phone if c.isdigit())

    # Add country code if missing
    if len(cleaned) == 10:
        cleaned = f"1{cleaned}"

    return f"+{cleaned}"


# Singleton client
_telnyx_client: Optional[TelnyxClient] = None


def get_telnyx_client() -> TelnyxClient:
    """Get or create Telnyx client singleton."""
    global _telnyx_client
    if _telnyx_client is None:
        _telnyx_client = TelnyxClient()
    return _telnyx_client
