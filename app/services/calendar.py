"""
Calendar Service - Generate .ics files for events

Works with Google Calendar, Apple Calendar, Outlook, etc.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from app.models import Event, Ticket, TicketTier
from app.config import get_settings

logger = logging.getLogger(__name__)


def generate_ics_content(
    title: str,
    start_time: datetime,
    end_time: datetime,
    description: str,
    location: str,
    url: str,
    uid: str,
) -> str:
    """
    Generate ICS calendar file content.

    Args:
        title: Event title
        start_time: Event start time (datetime with timezone)
        end_time: Event end time (datetime with timezone)
        description: Event description
        location: Event location
        url: Event URL
        uid: Unique identifier for the event

    Returns:
        ICS file content as string
    """
    # Format times for ICS
    def format_datetime(dt: datetime) -> str:
        """Format datetime for ICS file (YYYYMMDDTHHMMSSZ)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    # Escape ICS special characters
    def escape_text(text: str) -> str:
        """Escape special characters for ICS format."""
        if not text:
            return ""
        text = text.replace("\\", "\\\\")
        text = text.replace(";", "\\;")
        text = text.replace(",", "\\,")
        text = text.replace("\n", "\\n")
        return text

    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Tickets//Event Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{format_datetime(datetime.now(timezone.utc))}",
        f"DTSTART:{format_datetime(start_time)}",
        f"DTEND:{format_datetime(end_time)}",
        f"SUMMARY:{escape_text(title)}",
        f"DESCRIPTION:{escape_text(description)}",
        f"LOCATION:{escape_text(location)}",
        f"URL:{url}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "TRIGGER:-PT24H",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]

    return "\r\n".join(ics_content)


def generate_event_ics(event: Event, ticket: Optional[Ticket] = None) -> tuple[str, str]:
    """
    Generate ICS content and filename for an event.

    Args:
        event: Event model instance
        ticket: Optional ticket instance (for personalization)

    Returns:
        Tuple of (ics_content, filename)
    """
    settings = get_settings()

    # Parse event date/time
    try:
        naive_start = datetime.strptime(
            f"{event.event_date} {event.event_time}",
            "%Y-%m-%d %H:%M"
        )
    except (ValueError, TypeError):
        naive_start = datetime.strptime(event.event_date, "%Y-%m-%d")

    # Assume UTC for naive times (you may want to make this configurable)
    start_time = naive_start.replace(tzinfo=timezone.utc)

    # Default 3 hour duration if no end time
    end_time = start_time + timedelta(hours=3)

    # Build location string
    location_parts = []
    if event.venue:
        location_parts.append(event.venue.name)
        if event.venue.address:
            location_parts.append(event.venue.address)
    location = ", ".join(location_parts) if location_parts else "See event details"

    # Build URL
    event_url = f"{settings.base_url.rstrip('/')}/events/{event.id}"

    # Build description
    description_lines = []
    if event.description:
        description_lines.append(event.description)

    description_lines.append("")
    description_lines.append("---")
    description_lines.append("🎫 Your ticket information:")

    if ticket:
        description_lines.append(f"Ticket ID: {ticket.id}")
        if ticket.ticket_tier:
            description_lines.append(f"Ticket Type: {ticket.ticket_tier.name}")
        if ticket.qr_code_token:
            description_lines.append(f"QR Code: {ticket.qr_code_token}")
    else:
        description_lines.append(f"Get your tickets at: {event_url}")

    description_lines.append("")
    description_lines.append(f"Organized by {settings.org_name}")
    description = "\n".join(description_lines)

    # Generate UID (unique identifier)
    # Use event ID, optionally ticket ID, and domain
    if ticket:
        uid = f"event-{event.id}-ticket-{ticket.id}@{settings.base_url.replace('https://', '').replace('http://', '').replace('/', '.')}"
    else:
        uid = f"event-{event.id}@{settings.base_url.replace('https://', '').replace('http://', '').replace('/', '.')}"

    # Title
    title = f"{event.name}"
    if ticket and ticket.ticket_tier:
        title += f" - {ticket.ticket_tier.name} Ticket"

    # Generate ICS
    ics_content = generate_ics_content(
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
        url=event_url,
        uid=uid,
    )

    # Generate filename
    safe_name = "".join(c for c in event.name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_name}-{event.event_date}.ics"

    return ics_content, filename


def generate_google_calendar_url(event: Event, ticket: Optional[Ticket] = None) -> str:
    """
    Generate a Google Calendar "Add to Calendar" URL.

    Args:
        event: Event model instance
        ticket: Optional ticket instance

    Returns:
        Google Calendar URL
    """
    settings = get_settings()

    # Parse event date/time
    try:
        naive_start = datetime.strptime(
            f"{event.event_date} {event.event_time}",
            "%Y-%m-%d %H:%M"
        )
    except (ValueError, TypeError):
        naive_start = datetime.strptime(event.event_date, "%Y-%m-%d")

    start_time = naive_start.replace(tzinfo=timezone.utc)
    end_time = start_time + timedelta(hours=3)

    # Format for Google Calendar (YYYYMMDDTHHMMSSZ)
    def format_for_google(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%SZ")

    # Build location
    location = ""
    if event.venue:
        location = event.venue.name
        if event.venue.address:
            location += ", " + event.venue.address

    # Build URL
    event_url = f"{settings.base_url.rstrip('/')}/events/{event.id}"

    # Build title
    title = event.name
    if ticket and ticket.ticket_tier:
        title += f" - {ticket.ticket_tier.name} Ticket"

    # Build description
    description = event.description or ""
    description += f"\n\nGet your tickets at: {event_url}"

    import urllib.parse

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{format_for_google(start_time)}/{format_for_google(end_time)}",
        "details": description,
        "location": location,
        "url": event_url,
    }

    base_url = "https://calendar.google.com/calendar/render"
    query_string = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items())

    return f"{base_url}?{query_string}"
