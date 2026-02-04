import json
import random
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, init_db
from app.config import get_settings
from app.models import (
    Venue, Event, TicketTier, Ticket, EventGoer, TicketStatus,
    Notification, NotificationChannel, NotificationType, EventStatus,
    CustomerNote, CustomerPreference,
)

settings = get_settings()

# Initialize the MCP server
server = Server("event-tickets")

# Phone verification storage (in production, use Redis)
# Format: {phone: {"code": "123456", "expires": datetime, "verified": bool}}
phone_verifications: dict[str, dict] = {}


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
            description="Update event details including promo video",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "name": {"type": "string", "description": "New name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "event_date": {"type": "string", "description": "New date (optional)"},
                    "event_time": {"type": "string", "description": "New time (optional)"},
                    "promo_video_url": {"type": "string", "description": "YouTube or video URL for event promo (optional)"},
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
            name="register_customer",
            description="Register a new customer/contact",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer's full name"},
                    "email": {"type": "string", "description": "Customer's email address"},
                    "phone": {"type": "string", "description": "Customer's phone number (optional)"},
                },
                "required": ["name", "email"],
            },
        ),
        Tool(
            name="list_customers",
            description="List all registered customers/contacts",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="assign_ticket",
            description="Assign a ticket to a customer for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "Customer ID"},
                    "ticket_tier_id": {"type": "integer", "description": "Ticket tier ID"},
                    "quantity": {"type": "integer", "description": "Number of tickets (default 1)"},
                },
                "required": ["event_goer_id", "ticket_tier_id"],
            },
        ),
        Tool(
            name="check_in_ticket",
            description="Validate and check in a ticket by QR token (for scanning)",
            inputSchema={
                "type": "object",
                "properties": {
                    "qr_token": {"type": "string", "description": "The QR code token"},
                },
                "required": ["qr_token"],
            },
        ),
        Tool(
            name="check_in_by_name",
            description="Check in a guest by their name. Use when guest doesn't have QR code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Guest's full name"},
                    "event_id": {"type": "integer", "description": "Event ID (optional - uses today's event if not specified)"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="find_guest",
            description="Search for a guest by name to see their tickets",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Guest name to search (partial match)"},
                    "event_id": {"type": "integer", "description": "Filter by event (optional)"},
                },
                "required": ["name"],
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
        # ============== Phone Verification Tools ==============
        Tool(
            name="send_verification_code",
            description="Send a 6-digit verification code via SMS to verify a phone number",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to verify (e.g., +14165551234)"},
                },
                "required": ["phone"],
            },
        ),
        Tool(
            name="verify_phone_code",
            description="Verify the 6-digit code the customer received",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number being verified"},
                    "code": {"type": "string", "description": "The 6-digit code from the customer"},
                },
                "required": ["phone", "code"],
            },
        ),
        Tool(
            name="check_phone_verified",
            description="Check if a phone number has been verified in this session",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to check"},
                },
                "required": ["phone"],
            },
        ),
        # ============== Purchase Tools ==============
        Tool(
            name="send_purchase_link",
            description="Send a ticket purchase link via SMS to a VERIFIED phone number. Must verify phone first with send_verification_code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to send SMS to (must be verified first)"},
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "tier_id": {"type": "integer", "description": "Specific ticket tier ID (optional)"},
                },
                "required": ["phone", "event_id"],
            },
        ),
        Tool(
            name="lookup_customer",
            description="Find a customer by phone number or email",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to search"},
                    "email": {"type": "string", "description": "Email to search"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_customer_tickets",
            description="Get all tickets for a customer",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "The customer ID"},
                    "phone": {"type": "string", "description": "Or lookup by phone number"},
                    "email": {"type": "string", "description": "Or lookup by email"},
                },
                "required": [],
            },
        ),
        # ============== Customer Memory Tools ==============
        Tool(
            name="get_customer_profile",
            description="Get full customer profile including history, preferences, and notes. Use this when a returning customer calls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Customer phone number"},
                    "email": {"type": "string", "description": "Or customer email"},
                    "event_goer_id": {"type": "integer", "description": "Or customer ID"},
                },
                "required": [],
            },
        ),
        Tool(
            name="add_customer_note",
            description="Add a note about a customer for future reference. Use this to remember important details from conversations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "Customer ID"},
                    "phone": {"type": "string", "description": "Or customer phone"},
                    "note": {"type": "string", "description": "The note to save (e.g., 'Prefers aisle seats', 'Celebrating birthday', 'Had issue with parking last time')"},
                    "note_type": {"type": "string", "description": "Type: preference, interaction, issue, vip, birthday, dietary, accessibility"},
                },
                "required": ["note"],
            },
        ),
        Tool(
            name="update_customer_preferences",
            description="Update customer preferences for personalization",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "Customer ID"},
                    "phone": {"type": "string", "description": "Or customer phone"},
                    "preferred_section": {"type": "string", "description": "Preferred seating section"},
                    "accessibility_required": {"type": "boolean", "description": "Needs accessible seating"},
                    "accessibility_notes": {"type": "string", "description": "Accessibility details"},
                    "preferred_language": {"type": "string", "description": "Preferred language (en, fr, es)"},
                    "preferred_contact_method": {"type": "string", "description": "sms, email, or phone"},
                    "is_vip": {"type": "boolean", "description": "Mark as VIP customer"},
                    "vip_tier": {"type": "string", "description": "VIP tier: gold, platinum"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_customer_notes",
            description="Get all notes about a customer",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_goer_id": {"type": "integer", "description": "Customer ID"},
                    "phone": {"type": "string", "description": "Or customer phone"},
                    "note_type": {"type": "string", "description": "Filter by type (optional)"},
                },
                "required": [],
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
        if "promo_video_url" in arguments:
            event.promo_video_url = arguments["promo_video_url"]
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

    elif name == "register_customer":
        # Check if customer already exists
        existing = db.query(EventGoer).filter(EventGoer.email == arguments["email"]).first()
        if existing:
            return {
                "success": False,
                "message": f"Customer with email {arguments['email']} already exists",
                "customer": {
                    "id": existing.id,
                    "name": existing.name,
                    "email": existing.email,
                    "phone": existing.phone,
                }
            }

        # Create new customer
        customer = EventGoer(
            name=arguments["name"],
            email=arguments["email"],
            phone=arguments.get("phone"),
            email_opt_in=True,
            sms_opt_in=bool(arguments.get("phone")),
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        return {
            "success": True,
            "message": f"Customer {customer.name} registered successfully",
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            }
        }

    elif name == "list_customers":
        customers = db.query(EventGoer).order_by(EventGoer.created_at.desc()).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "email_opt_in": c.email_opt_in,
                "sms_opt_in": c.sms_opt_in,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in customers
        ]

    elif name == "assign_ticket":
        import secrets

        # Get customer
        customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        if not customer:
            return {"error": "Customer not found"}

        # Get ticket tier
        tier = db.query(TicketTier).filter(TicketTier.id == arguments["ticket_tier_id"]).first()
        if not tier:
            return {"error": "Ticket tier not found"}

        quantity = arguments.get("quantity", 1)

        # Check availability
        remaining = tier.quantity_available - tier.quantity_sold
        if remaining < quantity:
            return {"error": f"Only {remaining} tickets remaining"}

        # Create tickets
        tickets = []
        for _ in range(quantity):
            ticket = Ticket(
                ticket_tier_id=tier.id,
                event_goer_id=customer.id,
                qr_code_token=secrets.token_urlsafe(16),
                status=TicketStatus.PAID,
                purchased_at=datetime.utcnow(),
            )
            db.add(ticket)
            tickets.append(ticket)

        tier.quantity_sold += quantity
        db.commit()

        # Refresh to get IDs
        for t in tickets:
            db.refresh(t)

        event = tier.event
        return {
            "success": True,
            "message": f"Assigned {quantity} ticket(s) to {customer.name}",
            "customer": customer.name,
            "event": event.name if event else "Unknown",
            "tier": tier.name,
            "tickets": [{"id": t.id, "qr_token": t.qr_code_token} for t in tickets],
        }

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

    elif name == "check_in_by_name":
        guest_name = arguments["name"].strip().lower()
        event_id = arguments.get("event_id")

        # Build query for tickets
        query = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
                joinedload(Ticket.event_goer),
            )
            .join(EventGoer)
            .join(TicketTier)
            .filter(Ticket.status == TicketStatus.PAID)
        )

        # Filter by event if specified
        if event_id:
            query = query.filter(TicketTier.event_id == event_id)

        # Get all paid tickets and filter by name
        tickets = query.all()
        matching_tickets = [
            t for t in tickets
            if guest_name in t.event_goer.name.lower()
        ]

        if not matching_tickets:
            return {
                "success": False,
                "message": f"No tickets found for '{arguments['name']}'. Check the name spelling.",
            }

        if len(matching_tickets) > 1:
            # Multiple matches - ask to clarify
            return {
                "success": False,
                "multiple_matches": True,
                "message": f"Found {len(matching_tickets)} guests matching '{arguments['name']}'. Please be more specific.",
                "matches": [
                    {
                        "name": t.event_goer.name,
                        "event": t.ticket_tier.event.name,
                        "tier": t.ticket_tier.name,
                        "ticket_id": t.id,
                    }
                    for t in matching_tickets[:5]
                ],
            }

        # Single match - check them in
        ticket = matching_tickets[0]
        ticket.status = TicketStatus.CHECKED_IN
        db.commit()

        return {
            "success": True,
            "message": f"Welcome {ticket.event_goer.name}! You're checked in.",
            "guest": {
                "name": ticket.event_goer.name,
                "email": ticket.event_goer.email,
            },
            "ticket": {
                "event": ticket.ticket_tier.event.name,
                "venue": ticket.ticket_tier.event.venue.name,
                "tier": ticket.ticket_tier.name,
                "status": "checked_in",
            },
        }

    elif name == "find_guest":
        guest_name = arguments["name"].strip().lower()
        event_id = arguments.get("event_id")

        # Build query
        query = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
                joinedload(Ticket.event_goer),
            )
            .join(EventGoer)
            .join(TicketTier)
        )

        if event_id:
            query = query.filter(TicketTier.event_id == event_id)

        tickets = query.all()
        matching = [
            t for t in tickets
            if guest_name in t.event_goer.name.lower()
        ]

        if not matching:
            return {
                "found": False,
                "message": f"No guests found matching '{arguments['name']}'",
            }

        return {
            "found": True,
            "count": len(matching),
            "guests": [
                {
                    "name": t.event_goer.name,
                    "email": t.event_goer.email,
                    "phone": t.event_goer.phone,
                    "event": t.ticket_tier.event.name,
                    "event_date": t.ticket_tier.event.event_date,
                    "tier": t.ticket_tier.name,
                    "status": t.status.value,
                    "ticket_id": t.id,
                }
                for t in matching[:10]
            ],
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

    # ============== Phone Verification Tools ==============
    elif name == "send_verification_code":
        from app.services.sms import send_sms

        phone = arguments["phone"]

        # Generate 6-digit code
        code = str(random.randint(100000, 999999))

        # Store with 10-minute expiration
        phone_verifications[phone] = {
            "code": code,
            "expires": datetime.utcnow() + timedelta(minutes=10),
            "verified": False,
        }

        message = f"Your verification code is: {code}\n\nThis code expires in 10 minutes."
        result = send_sms(to_phone=phone, message=message)

        if result.get("success"):
            return {
                "success": True,
                "phone": phone,
                "message": "Verification code sent. Ask the customer to read the 6-digit code.",
                "expires_in": "10 minutes",
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to send SMS"),
            }

    elif name == "verify_phone_code":
        phone = arguments["phone"]
        code = arguments["code"].strip()

        if phone not in phone_verifications:
            return {
                "verified": False,
                "message": "No verification code was sent to this number. Send a code first.",
            }

        verification = phone_verifications[phone]

        # Check expiration
        if datetime.utcnow() > verification["expires"]:
            del phone_verifications[phone]
            return {
                "verified": False,
                "message": "Code expired. Please send a new verification code.",
            }

        # Check code
        if verification["code"] != code:
            return {
                "verified": False,
                "message": "Incorrect code. Please try again.",
            }

        # Mark as verified
        phone_verifications[phone]["verified"] = True

        return {
            "verified": True,
            "phone": phone,
            "message": "Phone number verified! You can now send purchase links to this number.",
        }

    elif name == "check_phone_verified":
        phone = arguments["phone"]

        if phone not in phone_verifications:
            return {"verified": False, "message": "Phone not verified"}

        verification = phone_verifications[phone]

        if datetime.utcnow() > verification["expires"]:
            del phone_verifications[phone]
            return {"verified": False, "message": "Verification expired"}

        return {
            "verified": verification["verified"],
            "message": "Phone is verified" if verification["verified"] else "Phone not yet verified",
        }

    # ============== Purchase Tools ==============
    elif name == "send_purchase_link":
        from app.services.sms import send_sms

        phone = arguments["phone"]

        # Check if phone is verified
        if phone not in phone_verifications or not phone_verifications[phone].get("verified"):
            return {
                "success": False,
                "error": "Phone not verified. Please verify the phone number first using send_verification_code.",
            }

        event = (
            db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
            .filter(Event.id == arguments["event_id"])
            .first()
        )
        if not event:
            return {"error": "Event not found"}

        phone = arguments["phone"]
        tier_id = arguments.get("tier_id")

        # Build purchase URL
        base_url = settings.base_url or "https://ai-tickets.fly.dev"
        if tier_id:
            purchase_url = f"{base_url}/events/{event.id}/purchase?tier={tier_id}"
        else:
            purchase_url = f"{base_url}/events/{event.id}/purchase"

        # Get price info
        if tier_id:
            tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
            price_info = f"${tier.price / 100:.0f}" if tier else ""
        else:
            min_price = min([t.price for t in event.ticket_tiers]) if event.ticket_tiers else 0
            price_info = f"from ${min_price / 100:.0f}"

        message = (
            f"🎟️ {event.name}\n"
            f"📅 {event.event_date} at {event.event_time}\n"
            f"📍 {event.venue.name}\n"
            f"💰 Tickets {price_info}\n\n"
            f"Buy now: {purchase_url}"
        )

        result = send_sms(to_phone=phone, message=message)

        return {
            "success": result.get("success", False),
            "phone": phone,
            "event": event.name,
            "purchase_url": purchase_url,
            "message": "Purchase link sent via SMS" if result.get("success") else result.get("error", "Failed to send SMS"),
        }

    elif name == "lookup_customer":
        query = db.query(EventGoer)

        if arguments.get("phone"):
            query = query.filter(EventGoer.phone == arguments["phone"])
        elif arguments.get("email"):
            query = query.filter(EventGoer.email == arguments["email"])
        else:
            return {"error": "Please provide phone or email"}

        customer = query.first()
        if not customer:
            return {"found": False, "message": "Customer not found"}

        return {
            "found": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "created_at": customer.created_at,
            },
        }

    elif name == "get_customer_tickets":
        # Find customer
        customer = None
        if arguments.get("event_goer_id"):
            customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        elif arguments.get("phone"):
            customer = db.query(EventGoer).filter(EventGoer.phone == arguments["phone"]).first()
        elif arguments.get("email"):
            customer = db.query(EventGoer).filter(EventGoer.email == arguments["email"]).first()

        if not customer:
            return {"found": False, "message": "Customer not found"}

        # Get their tickets
        tickets = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue)
            )
            .filter(Ticket.event_goer_id == customer.id)
            .all()
        )

        return {
            "found": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            },
            "tickets": [
                {
                    "ticket_id": t.id,
                    "event_name": t.ticket_tier.event.name,
                    "event_date": str(t.ticket_tier.event.event_date),
                    "event_time": t.ticket_tier.event.event_time,
                    "venue": t.ticket_tier.event.venue.name,
                    "tier": t.ticket_tier.name,
                    "status": t.status.value,
                    "qr_token": t.qr_code_token,
                }
                for t in tickets
            ],
        }

    # ============== Customer Memory Tools ==============
    elif name == "get_customer_profile":
        # Find customer
        customer = None
        if arguments.get("event_goer_id"):
            customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        elif arguments.get("phone"):
            customer = db.query(EventGoer).filter(EventGoer.phone == arguments["phone"]).first()
        elif arguments.get("email"):
            customer = db.query(EventGoer).filter(EventGoer.email == arguments["email"]).first()

        if not customer:
            return {"found": False, "message": "Customer not found. This may be a new customer."}

        # Get preferences
        prefs = db.query(CustomerPreference).filter(CustomerPreference.event_goer_id == customer.id).first()

        # Get notes
        notes = db.query(CustomerNote).filter(CustomerNote.event_goer_id == customer.id).order_by(CustomerNote.created_at.desc()).limit(10).all()

        # Get ticket history
        tickets = (
            db.query(Ticket)
            .options(joinedload(Ticket.ticket_tier).joinedload(TicketTier.event))
            .filter(Ticket.event_goer_id == customer.id)
            .order_by(Ticket.purchased_at.desc())
            .limit(10)
            .all()
        )

        # Calculate stats
        total_spent = sum(t.ticket_tier.price for t in tickets if t.status in [TicketStatus.PAID, TicketStatus.CHECKED_IN])
        events_attended = len([t for t in tickets if t.status == TicketStatus.CHECKED_IN])

        return {
            "found": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "member_since": str(customer.created_at)[:10] if customer.created_at else None,
            },
            "preferences": {
                "preferred_section": prefs.preferred_section if prefs else None,
                "accessibility_required": prefs.accessibility_required if prefs else False,
                "accessibility_notes": prefs.accessibility_notes if prefs else None,
                "preferred_language": prefs.preferred_language if prefs else "en",
                "preferred_contact_method": prefs.preferred_contact_method if prefs else "sms",
                "is_vip": prefs.is_vip if prefs else False,
                "vip_tier": prefs.vip_tier if prefs else None,
            } if prefs else None,
            "stats": {
                "total_spent": f"${total_spent / 100:.2f}",
                "total_spent_cents": total_spent,
                "events_attended": events_attended,
                "total_tickets": len(tickets),
            },
            "notes": [
                {
                    "type": n.note_type,
                    "note": n.note,
                    "date": str(n.created_at)[:10],
                }
                for n in notes
            ],
            "recent_tickets": [
                {
                    "event": t.ticket_tier.event.name,
                    "date": t.ticket_tier.event.event_date,
                    "tier": t.ticket_tier.name,
                    "status": t.status.value,
                }
                for t in tickets[:5]
            ],
        }

    elif name == "add_customer_note":
        # Find customer
        customer = None
        if arguments.get("event_goer_id"):
            customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        elif arguments.get("phone"):
            customer = db.query(EventGoer).filter(EventGoer.phone == arguments["phone"]).first()

        if not customer:
            return {"error": "Customer not found"}

        note = CustomerNote(
            event_goer_id=customer.id,
            note_type=arguments.get("note_type", "interaction"),
            note=arguments["note"],
            created_by="ai_agent",
        )
        db.add(note)
        db.commit()

        return {
            "success": True,
            "message": f"Note saved for {customer.name}",
            "note_type": note.note_type,
            "note": note.note,
        }

    elif name == "update_customer_preferences":
        # Find customer
        customer = None
        if arguments.get("event_goer_id"):
            customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        elif arguments.get("phone"):
            customer = db.query(EventGoer).filter(EventGoer.phone == arguments["phone"]).first()

        if not customer:
            return {"error": "Customer not found"}

        # Get or create preferences
        prefs = db.query(CustomerPreference).filter(CustomerPreference.event_goer_id == customer.id).first()
        if not prefs:
            prefs = CustomerPreference(event_goer_id=customer.id)
            db.add(prefs)

        # Update fields
        if "preferred_section" in arguments:
            prefs.preferred_section = arguments["preferred_section"]
        if "accessibility_required" in arguments:
            prefs.accessibility_required = arguments["accessibility_required"]
        if "accessibility_notes" in arguments:
            prefs.accessibility_notes = arguments["accessibility_notes"]
        if "preferred_language" in arguments:
            prefs.preferred_language = arguments["preferred_language"]
        if "preferred_contact_method" in arguments:
            prefs.preferred_contact_method = arguments["preferred_contact_method"]
        if "is_vip" in arguments:
            prefs.is_vip = arguments["is_vip"]
        if "vip_tier" in arguments:
            prefs.vip_tier = arguments["vip_tier"]

        prefs.last_interaction_date = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "message": f"Preferences updated for {customer.name}",
            "preferences": {
                "preferred_section": prefs.preferred_section,
                "accessibility_required": prefs.accessibility_required,
                "preferred_language": prefs.preferred_language,
                "is_vip": prefs.is_vip,
                "vip_tier": prefs.vip_tier,
            },
        }

    elif name == "get_customer_notes":
        # Find customer
        customer = None
        if arguments.get("event_goer_id"):
            customer = db.query(EventGoer).filter(EventGoer.id == arguments["event_goer_id"]).first()
        elif arguments.get("phone"):
            customer = db.query(EventGoer).filter(EventGoer.phone == arguments["phone"]).first()

        if not customer:
            return {"error": "Customer not found"}

        query = db.query(CustomerNote).filter(CustomerNote.event_goer_id == customer.id)

        if arguments.get("note_type"):
            query = query.filter(CustomerNote.note_type == arguments["note_type"])

        notes = query.order_by(CustomerNote.created_at.desc()).all()

        return {
            "customer": customer.name,
            "notes": [
                {
                    "id": n.id,
                    "type": n.note_type,
                    "note": n.note,
                    "created_by": n.created_by,
                    "date": str(n.created_at),
                }
                for n in notes
            ],
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
    result = {
        "id": event.id,
        "venue_id": event.venue_id,
        "name": event.name,
        "description": event.description,
        "image_url": event.image_url,
        "promo_video_url": event.promo_video_url,
        "event_date": event.event_date,
        "event_time": event.event_time,
        "status": event.status.value if event.status else "scheduled",
        "created_at": event.created_at,
    }
    # Include venue info if loaded
    if event.venue:
        result["venue_name"] = event.venue.name
        result["venue_address"] = event.venue.address
    return result


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
