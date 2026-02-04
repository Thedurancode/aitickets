import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, init_db
from app.models import (
    Venue, Event, TicketTier, Ticket, EventGoer, TicketStatus,
    Notification, NotificationChannel, NotificationType, EventStatus,
)

# Initialize the MCP server
server = Server("event-tickets")


def get_db():
    """Get a database session."""
    return SessionLocal()


# ============== Venue Tools ==============

@server.list_tools()
async def list_tools():
    """List all available tools."""
    return [
        # Venue tools
        Tool(
            name="list_venues",
            description="Get all venues",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_venue",
            description="Get a venue by ID with its events",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "integer",
                        "description": "The venue ID",
                    },
                },
                "required": ["venue_id"],
            },
        ),
        Tool(
            name="create_venue",
            description="Create a new venue",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Venue name"},
                    "address": {"type": "string", "description": "Venue address"},
                    "phone": {"type": "string", "description": "Contact phone (optional)"},
                    "description": {"type": "string", "description": "About the venue (optional)"},
                },
                "required": ["name", "address"],
            },
        ),
        Tool(
            name="update_venue",
            description="Update venue details",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "integer", "description": "The venue ID"},
                    "name": {"type": "string", "description": "New name (optional)"},
                    "address": {"type": "string", "description": "New address (optional)"},
                    "phone": {"type": "string", "description": "New phone (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                },
                "required": ["venue_id"],
            },
        ),
        # Event tools
        Tool(
            name="list_events",
            description="Get all events with venue details",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_event",
            description="Get a specific event by ID with full details",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="create_event",
            description="Create a new event at a venue",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "integer", "description": "The venue ID"},
                    "name": {"type": "string", "description": "Event name"},
                    "description": {"type": "string", "description": "Event description (optional)"},
                    "event_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "event_time": {"type": "string", "description": "Time in HH:MM format"},
                },
                "required": ["venue_id", "name", "event_date", "event_time"],
            },
        ),
        Tool(
            name="update_event",
            description="Update event details",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "name": {"type": "string", "description": "New name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "event_date": {"type": "string", "description": "New date (optional)"},
                    "event_time": {"type": "string", "description": "New time (optional)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="get_events_by_venue",
            description="List all events at a specific venue",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "integer", "description": "The venue ID"},
                },
                "required": ["venue_id"],
            },
        ),
        # Ticket tier tools
        Tool(
            name="list_ticket_tiers",
            description="Get ticket tiers for an event with availability",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="create_ticket_tier",
            description="Add a new ticket tier to an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "name": {"type": "string", "description": "Tier name (e.g., VIP, General)"},
                    "description": {"type": "string", "description": "What's included (optional)"},
                    "price": {"type": "integer", "description": "Price in cents"},
                    "quantity_available": {"type": "integer", "description": "Total tickets available"},
                },
                "required": ["event_id", "name", "price", "quantity_available"],
            },
        ),
        Tool(
            name="get_ticket_availability",
            description="Check remaining tickets for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        # Sales and attendee tools
        Tool(
            name="get_event_sales",
            description="Get sales statistics for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="list_event_goers",
            description="List attendees for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="check_in_ticket",
            description="Validate and check in a ticket by QR token",
            inputSchema={
                "type": "object",
                "properties": {
                    "qr_token": {"type": "string", "description": "The QR code token"},
                },
                "required": ["qr_token"],
            },
        ),
        Tool(
            name="get_ticket_status",
            description="Check ticket status by QR token",
            inputSchema={
                "type": "object",
                "properties": {
                    "qr_token": {"type": "string", "description": "The QR code token"},
                },
                "required": ["qr_token"],
            },
        ),
        # ============== Notification Tools ==============
        Tool(
            name="send_event_reminders",
            description="Send reminder notifications to all ticket holders for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "hours_before": {"type": "integer", "description": "Hours before event (default 24)"},
                    "use_sms": {"type": "boolean", "description": "Also send SMS reminders (default false)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="send_event_update",
            description="Send an update notification to all ticket holders about event changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "message": {"type": "string", "description": "The update message to send"},
                    "update_type": {"type": "string", "description": "Type of update (date_change, time_change, venue_change, general)"},
                    "use_sms": {"type": "boolean", "description": "Also send SMS notifications (default false)"},
                },
                "required": ["event_id", "message"],
            },
        ),
        Tool(
            name="cancel_event",
            description="Cancel an event and notify all ticket holders",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "reason": {"type": "string", "description": "Cancellation reason (optional)"},
                    "use_sms": {"type": "boolean", "description": "Also send SMS notifications (default false)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="send_sms_ticket",
            description="Send ticket details via SMS to a ticket holder",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "The ticket ID"},
                },
                "required": ["ticket_id"],
            },
        ),
        Tool(
            name="get_notification_history",
            description="Get notification history for an event or attendee",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Filter by event ID (optional)"},
                    "event_goer_id": {"type": "integer", "description": "Filter by attendee ID (optional)"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_attendee_preferences",
            description="Get notification preferences for an attendee",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "The attendee ID"},
                },
                "required": ["event_goer_id"],
            },
        ),
        Tool(
            name="update_attendee_preferences",
            description="Update notification preferences for an attendee",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "The attendee ID"},
                    "email_opt_in": {"type": "boolean", "description": "Receive email notifications"},
                    "sms_opt_in": {"type": "boolean", "description": "Receive SMS notifications"},
                    "marketing_opt_in": {"type": "boolean", "description": "Receive marketing communications"},
                },
                "required": ["event_goer_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    db = get_db()
    try:
        result = await _execute_tool(name, arguments, db)
        return [TextContent(type="text", text=json.dumps(result, default=str))]
    finally:
        db.close()


async def _execute_tool(name: str, arguments: dict, db: Session):
    """Execute a tool and return the result."""

    # ============== Venue Tools ==============
    if name == "list_venues":
        venues = db.query(Venue).all()
        return [_venue_to_dict(v) for v in venues]

    elif name == "get_venue":
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}
        result = _venue_to_dict(venue)
        result["events"] = [_event_to_dict(e) for e in venue.events]
        return result

    elif name == "create_venue":
        venue = Venue(
            name=arguments["name"],
            address=arguments["address"],
            phone=arguments.get("phone"),
            description=arguments.get("description"),
        )
        db.add(venue)
        db.commit()
        db.refresh(venue)
        return _venue_to_dict(venue)

    elif name == "update_venue":
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}
        if "name" in arguments:
            venue.name = arguments["name"]
        if "address" in arguments:
            venue.address = arguments["address"]
        if "phone" in arguments:
            venue.phone = arguments["phone"]
        if "description" in arguments:
            venue.description = arguments["description"]
        db.commit()
        db.refresh(venue)
        return _venue_to_dict(venue)

    # ============== Event Tools ==============
    elif name == "list_events":
        events = db.query(Event).options(joinedload(Event.venue)).all()
        result = []
        for e in events:
            event_dict = _event_to_dict(e)
            event_dict["venue"] = _venue_to_dict(e.venue)
            result.append(event_dict)
        return result

    elif name == "get_event":
        event = (
            db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
            .filter(Event.id == arguments["event_id"])
            .first()
        )
        if not event:
            return {"error": "Event not found"}
        result = _event_to_dict(event)
        result["venue"] = _venue_to_dict(event.venue)
        result["ticket_tiers"] = [_tier_to_dict(t) for t in event.ticket_tiers]
        return result

    elif name == "create_event":
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}
        event = Event(
            venue_id=arguments["venue_id"],
            name=arguments["name"],
            description=arguments.get("description"),
            event_date=arguments["event_date"],
            event_time=arguments["event_time"],
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return _event_to_dict(event)

    elif name == "update_event":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}
        if "name" in arguments:
            event.name = arguments["name"]
        if "description" in arguments:
            event.description = arguments["description"]
        if "event_date" in arguments:
            event.event_date = arguments["event_date"]
        if "event_time" in arguments:
            event.event_time = arguments["event_time"]
        db.commit()
        db.refresh(event)
        return _event_to_dict(event)

    elif name == "get_events_by_venue":
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}
        events = db.query(Event).filter(Event.venue_id == arguments["venue_id"]).all()
        return [_event_to_dict(e) for e in events]

    # ============== Ticket Tier Tools ==============
    elif name == "list_ticket_tiers":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}
        tiers = db.query(TicketTier).filter(TicketTier.event_id == arguments["event_id"]).all()
        return [_tier_to_dict(t) for t in tiers]

    elif name == "create_ticket_tier":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}
        tier = TicketTier(
            event_id=arguments["event_id"],
            name=arguments["name"],
            description=arguments.get("description"),
            price=arguments["price"],
            quantity_available=arguments["quantity_available"],
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)
        return _tier_to_dict(tier)

    elif name == "get_ticket_availability":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}
        tiers = db.query(TicketTier).filter(TicketTier.event_id == arguments["event_id"]).all()
        result = {
            "event_id": arguments["event_id"],
            "event_name": event.name,
            "tiers": [],
        }
        total_available = 0
        total_sold = 0
        for tier in tiers:
            remaining = tier.quantity_available - tier.quantity_sold
            total_available += tier.quantity_available
            total_sold += tier.quantity_sold
            result["tiers"].append({
                "tier_id": tier.id,
                "name": tier.name,
                "price_cents": tier.price,
                "quantity_available": tier.quantity_available,
                "quantity_sold": tier.quantity_sold,
                "tickets_remaining": remaining,
            })
        result["total_capacity"] = total_available
        result["total_sold"] = total_sold
        result["total_remaining"] = total_available - total_sold
        return result

    # ============== Sales & Attendee Tools ==============
    elif name == "get_event_sales":
        event = (
            db.query(Event)
            .options(joinedload(Event.ticket_tiers))
            .filter(Event.id == arguments["event_id"])
            .first()
        )
        if not event:
            return {"error": "Event not found"}

        total_sold = 0
        total_revenue = 0
        tiers_data = []
        checked_in = 0

        for tier in event.ticket_tiers:
            tier_revenue = tier.price * tier.quantity_sold
            total_sold += tier.quantity_sold
            total_revenue += tier_revenue

            # Count checked in tickets for this tier
            tier_checked_in = (
                db.query(Ticket)
                .filter(Ticket.ticket_tier_id == tier.id, Ticket.status == TicketStatus.CHECKED_IN)
                .count()
            )
            checked_in += tier_checked_in

            tiers_data.append({
                "tier_id": tier.id,
                "tier_name": tier.name,
                "price_cents": tier.price,
                "quantity_sold": tier.quantity_sold,
                "revenue_cents": tier_revenue,
                "checked_in": tier_checked_in,
            })

        return {
            "event_id": event.id,
            "event_name": event.name,
            "total_tickets_sold": total_sold,
            "total_revenue_cents": total_revenue,
            "tickets_checked_in": checked_in,
            "tiers": tiers_data,
        }

    elif name == "list_event_goers":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        # Get all tickets for this event's tiers
        tickets = (
            db.query(Ticket)
            .options(joinedload(Ticket.event_goer), joinedload(Ticket.ticket_tier))
            .join(TicketTier)
            .filter(TicketTier.event_id == arguments["event_id"])
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .all()
        )

        attendees = {}
        for ticket in tickets:
            goer = ticket.event_goer
            if goer.id not in attendees:
                attendees[goer.id] = {
                    "id": goer.id,
                    "name": goer.name,
                    "email": goer.email,
                    "phone": goer.phone,
                    "email_opt_in": goer.email_opt_in,
                    "sms_opt_in": goer.sms_opt_in,
                    "marketing_opt_in": goer.marketing_opt_in,
                    "tickets": [],
                }
            attendees[goer.id]["tickets"].append({
                "ticket_id": ticket.id,
                "tier_name": ticket.ticket_tier.name,
                "status": ticket.status.value,
            })

        return list(attendees.values())

    elif name == "check_in_ticket":
        ticket = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
                joinedload(Ticket.event_goer),
            )
            .filter(Ticket.qr_code_token == arguments["qr_token"])
            .first()
        )

        if not ticket:
            return {"valid": False, "message": "Invalid ticket - QR code not found"}

        if ticket.status == TicketStatus.CHECKED_IN:
            return {
                "valid": False,
                "message": "Ticket already checked in",
                "ticket": _ticket_to_dict(ticket),
            }

        if ticket.status != TicketStatus.PAID:
            return {
                "valid": False,
                "message": f"Ticket status is {ticket.status.value}",
                "ticket": _ticket_to_dict(ticket),
            }

        ticket.status = TicketStatus.CHECKED_IN
        db.commit()

        return {
            "valid": True,
            "message": "Ticket validated successfully - Welcome!",
            "ticket": _ticket_to_dict(ticket),
        }

    elif name == "get_ticket_status":
        ticket = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
                joinedload(Ticket.event_goer),
            )
            .filter(Ticket.qr_code_token == arguments["qr_token"])
            .first()
        )

        if not ticket:
            return {"found": False, "message": "Ticket not found"}

        return {
            "found": True,
            "ticket": _ticket_to_dict(ticket),
        }

    # ============== Notification Tools ==============
    elif name == "send_event_reminders":
        from app.services.notifications import send_event_reminders

        channels = [NotificationChannel.EMAIL]
        if arguments.get("use_sms"):
            channels.append(NotificationChannel.SMS)

        result = send_event_reminders(
            db=db,
            event_id=arguments["event_id"],
            hours_before=arguments.get("hours_before", 24),
            channels=channels,
        )
        return result

    elif name == "send_event_update":
        from app.services.notifications import send_event_update_notifications

        channels = [NotificationChannel.EMAIL]
        if arguments.get("use_sms"):
            channels.append(NotificationChannel.SMS)

        result = send_event_update_notifications(
            db=db,
            event_id=arguments["event_id"],
            message=arguments["message"],
            update_type=arguments.get("update_type", "general"),
            channels=channels,
        )
        return result

    elif name == "cancel_event":
        from app.services.notifications import send_event_cancellation_notifications

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        # Update event status
        event.status = EventStatus.CANCELLED
        event.cancellation_reason = arguments.get("reason")
        db.commit()

        channels = [NotificationChannel.EMAIL]
        if arguments.get("use_sms"):
            channels.append(NotificationChannel.SMS)

        result = send_event_cancellation_notifications(
            db=db,
            event_id=arguments["event_id"],
            reason=arguments.get("reason"),
            channels=channels,
        )
        result["event_status"] = "cancelled"
        return result

    elif name == "send_sms_ticket":
        from app.services.notifications import send_sms_ticket

        result = send_sms_ticket(db=db, ticket_id=arguments["ticket_id"])
        return result

    elif name == "get_notification_history":
        query = db.query(Notification)

        if arguments.get("event_id"):
            query = query.filter(Notification.event_id == arguments["event_id"])
        if arguments.get("event_goer_id"):
            query = query.filter(Notification.event_goer_id == arguments["event_goer_id"])

        limit = arguments.get("limit", 50)
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

        return [_notification_to_dict(n) for n in notifications]

    elif name == "get_attendee_preferences":
        event_goer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        if not event_goer:
            return {"error": "Attendee not found"}

        return {
            "id": event_goer.id,
            "name": event_goer.name,
            "email": event_goer.email,
            "phone": event_goer.phone,
            "email_opt_in": event_goer.email_opt_in,
            "sms_opt_in": event_goer.sms_opt_in,
            "marketing_opt_in": event_goer.marketing_opt_in,
        }

    elif name == "update_attendee_preferences":
        event_goer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        if not event_goer:
            return {"error": "Attendee not found"}

        if "email_opt_in" in arguments:
            event_goer.email_opt_in = arguments["email_opt_in"]
        if "sms_opt_in" in arguments:
            event_goer.sms_opt_in = arguments["sms_opt_in"]
        if "marketing_opt_in" in arguments:
            event_goer.marketing_opt_in = arguments["marketing_opt_in"]

        db.commit()
        db.refresh(event_goer)

        return {
            "id": event_goer.id,
            "name": event_goer.name,
            "email": event_goer.email,
            "phone": event_goer.phone,
            "email_opt_in": event_goer.email_opt_in,
            "sms_opt_in": event_goer.sms_opt_in,
            "marketing_opt_in": event_goer.marketing_opt_in,
            "message": "Preferences updated successfully",
        }

    return {"error": f"Unknown tool: {name}"}


# ============== Helper Functions ==============

def _venue_to_dict(venue: Venue) -> dict:
    return {
        "id": venue.id,
        "name": venue.name,
        "logo_url": venue.logo_url,
        "address": venue.address,
        "phone": venue.phone,
        "description": venue.description,
        "created_at": venue.created_at,
    }


def _event_to_dict(event: Event) -> dict:
    return {
        "id": event.id,
        "venue_id": event.venue_id,
        "name": event.name,
        "description": event.description,
        "image_url": event.image_url,
        "event_date": event.event_date,
        "event_time": event.event_time,
        "status": event.status.value if event.status else "scheduled",
        "created_at": event.created_at,
    }


def _tier_to_dict(tier: TicketTier) -> dict:
    return {
        "id": tier.id,
        "event_id": tier.event_id,
        "name": tier.name,
        "description": tier.description,
        "price_cents": tier.price,
        "quantity_available": tier.quantity_available,
        "quantity_sold": tier.quantity_sold,
        "tickets_remaining": tier.quantity_available - tier.quantity_sold,
    }


def _ticket_to_dict(ticket: Ticket) -> dict:
    result = {
        "id": ticket.id,
        "status": ticket.status.value,
        "qr_code_token": ticket.qr_code_token,
        "purchased_at": ticket.purchased_at,
    }
    if ticket.ticket_tier:
        result["tier_name"] = ticket.ticket_tier.name
        result["price_cents"] = ticket.ticket_tier.price
        if ticket.ticket_tier.event:
            result["event_name"] = ticket.ticket_tier.event.name
            result["event_date"] = ticket.ticket_tier.event.event_date
            result["event_time"] = ticket.ticket_tier.event.event_time
    if ticket.event_goer:
        result["attendee_name"] = ticket.event_goer.name
        result["attendee_email"] = ticket.event_goer.email
    return result


def _notification_to_dict(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "event_goer_id": notification.event_goer_id,
        "event_id": notification.event_id,
        "ticket_id": notification.ticket_id,
        "type": notification.notification_type.value,
        "channel": notification.channel.value,
        "status": notification.status.value,
        "subject": notification.subject,
        "message": notification.message[:100] + "..." if len(notification.message) > 100 else notification.message,
        "sent_at": notification.sent_at,
        "created_at": notification.created_at,
    }


async def main():
    """Run the MCP server."""
    # Initialize database
    init_db()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
