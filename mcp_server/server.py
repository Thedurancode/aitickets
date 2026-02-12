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
    CustomerNote, CustomerPreference, EventCategory,
    MarketingCampaign, MarketingList, PromoCode, DiscountType, EventPhoto,
    WaitlistEntry, WaitlistStatus,
)
from app.services.stripe_sync import (
    create_stripe_product_for_tier,
    sync_existing_tiers_to_stripe,
)

settings = get_settings()

# Initialize the MCP server
server = Server("event-tickets")

# Phone verification storage (in production, use Redis)
# Format: {phone: {"code": "123456", "expires": datetime, "verified": bool}}
phone_verifications: dict[str, dict] = {}

# Magic link tokens for event admin access (in production, use Redis)
# Format: {token: {"event_id": int, "phone": str, "expires": datetime}}
magic_link_tokens: dict[str, dict] = {}


def get_db():
    """Get a database session."""
    return SessionLocal()


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to E.164 format.
    Adds +1 for US numbers if not present.
    """
    if not phone:
        return phone

    # Remove all non-digit characters except +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

    # If already has +, assume it's correct
    if cleaned.startswith('+'):
        return cleaned

    # Remove leading 1 if present (US country code without +)
    if cleaned.startswith('1') and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # US number: 10 digits, add +1
    if len(cleaned) == 10:
        return f"+1{cleaned}"

    # If 11 digits starting with 1, format as +1
    if len(cleaned) == 11 and cleaned.startswith('1'):
        return f"+{cleaned}"

    # Return as-is if we can't determine format
    return cleaned


# ============== Venue Tools ==============

@server.list_tools()
async def list_tools():
    """List all available tools."""
    return [
        # Agent guidance tools
        Tool(
            name="get_agent_instructions",
            description="CALL THIS FIRST. Returns system instructions, workflows, and tool selection guidance for the AI agent.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_branding",
            description="Get organization branding configuration (name, color, logo URL)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # Category tools
        Tool(
            name="list_categories",
            description="List all event categories (e.g. Sports, Concerts, Comedy)",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="create_category",
            description="Create a new event category",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Category name (e.g. Sports, Concerts, Comedy)"},
                    "description": {"type": "string", "description": "Category description (optional)"},
                    "color": {"type": "string", "description": "Hex color for UI display (e.g. #CE1141)"},
                    "image_url": {"type": "string", "description": "Image URL for the category (optional)"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="update_category",
            description="Update an existing event category (name, description, color, image)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_id": {"type": "integer", "description": "Category ID"},
                    "name": {"type": "string", "description": "New category name"},
                    "description": {"type": "string", "description": "New category description"},
                    "color": {"type": "string", "description": "New hex color (e.g. #CE1141)"},
                    "image_url": {"type": "string", "description": "New image URL for the category"},
                },
                "required": ["category_id"],
            },
        ),
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
                    "category_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of category IDs to assign"},
                },
                "required": ["venue_id", "name", "event_date", "event_time"],
            },
        ),
        Tool(
            name="create_recurring_event",
            description="Create a series of recurring events (e.g. every Tuesday for 4 months) with ticket tiers. Creates individual events linked by a series_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "integer", "description": "The venue ID"},
                    "name": {"type": "string", "description": "Event name (e.g. Taco Tuesday)"},
                    "event_time": {"type": "string", "description": "Time in HH:MM format"},
                    "day_of_week": {
                        "type": "string",
                        "enum": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                        "description": "Day of the week for the recurring event",
                    },
                    "frequency": {
                        "type": "string",
                        "enum": ["weekly", "biweekly", "monthly"],
                        "description": "How often the event repeats (default: weekly)",
                    },
                    "duration_months": {
                        "type": "integer",
                        "description": "How many months to create events for (default: 3, max: 12)",
                    },
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (default: today)"},
                    "description": {"type": "string", "description": "Event description (optional)"},
                    "category_ids": {"type": "array", "items": {"type": "integer"}, "description": "Category IDs to assign to all events"},
                    "tier_name": {"type": "string", "description": "Ticket tier name (default: General Admission)"},
                    "tier_price": {"type": "integer", "description": "Ticket price in cents (default: 0 for free)"},
                    "tier_quantity": {"type": "integer", "description": "Number of tickets per event (default: 100)"},
                    "doors_open_time": {"type": "string", "description": "Doors open time in HH:MM format (optional)"},
                },
                "required": ["venue_id", "name", "event_time", "day_of_week"],
            },
        ),
        Tool(
            name="update_event",
            description="Update event details including image and promo video",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "name": {"type": "string", "description": "New name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "event_date": {"type": "string", "description": "New date (optional)"},
                    "event_time": {"type": "string", "description": "New time (optional)"},
                    "image_url": {"type": "string", "description": "Event poster/image URL (optional)"},
                    "promo_video_url": {"type": "string", "description": "YouTube or video URL for event promo (optional)"},
                    "category_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of category IDs to assign (replaces existing)"},
                    "doors_open_time": {"type": "string", "description": "Doors open time in HH:MM format (optional)"},
                    "is_visible": {"type": "boolean", "description": "Whether event is visible on public listing (optional)"},
                    "promoter_phone": {"type": "string", "description": "Promoter phone number for magic link admin access (optional)"},
                    "promoter_name": {"type": "string", "description": "Promoter name (optional)"},
                    "post_event_video_url": {"type": "string", "description": "Post-event recap/highlight video URL (optional)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="set_post_event_video",
            description="Set the post-event recap/highlight video URL for an event. Supports YouTube or direct video URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "video_url": {"type": "string", "description": "YouTube or direct video URL for the event recap"},
                },
                "required": ["event_id", "video_url"],
            },
        ),
        Tool(
            name="send_photo_sharing_link",
            description="Text all attendees of an event a link where they can upload and browse photos from the event. Uses SMS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "custom_message": {"type": "string", "description": "Optional custom message to include (default: standard photo sharing invite)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="get_event_photos",
            description="List all photos uploaded for an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="text_guest_list",
            description="Send a custom SMS text message to all attendees who have a phone number on file. Provide event_id for one event, or event_ids for multiple events (cross-event re-engagement). Bypasses marketing opt-in.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Single event ID"},
                    "event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Multiple event IDs for cross-event SMS blast"},
                    "message": {"type": "string", "description": "The message to text to all attendees"},
                },
                "required": ["message"],
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
        Tool(
            name="search_events",
            description="Search events by name, date range, or status. Use this when you don't know the event ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search by event name (partial match)"},
                    "date_from": {"type": "string", "description": "Start date filter YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "End date filter YYYY-MM-DD"},
                    "status": {"type": "string", "enum": ["scheduled", "postponed", "cancelled"], "description": "Filter by event status"},
                    "venue_id": {"type": "integer", "description": "Filter by venue ID"},
                    "category": {"type": "string", "description": "Filter by category name (partial match)"},
                },
                "required": [],
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
        Tool(
            name="update_ticket_tier",
            description="Update a ticket tier (name, price, quantity, or status). Use to pause/activate tiers or increase inventory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tier_id": {"type": "integer", "description": "The ticket tier ID"},
                    "name": {"type": "string", "description": "New tier name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "price": {"type": "integer", "description": "New price in cents (optional)"},
                    "quantity_available": {"type": "integer", "description": "New total quantity (optional)"},
                    "status": {"type": "string", "enum": ["active", "paused", "sold_out"], "description": "Tier status (optional)"},
                },
                "required": ["tier_id"],
            },
        ),
        Tool(
            name="toggle_all_tickets",
            description="Enable or disable all ticket tiers for an event. Use for 'turn off all tickets' or 'make tickets live'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "status": {"type": "string", "enum": ["active", "paused"], "description": "Set all tiers to this status"},
                },
                "required": ["event_id", "status"],
            },
        ),
        Tool(
            name="add_tickets",
            description="Add more tickets to an existing tier (by name match) or create a new tier. Use for 'add 10 more VIP tickets at $25'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "tier_name": {"type": "string", "description": "Tier name (e.g., 'VIP', 'General'). Matches existing or creates new."},
                    "quantity": {"type": "integer", "description": "Number of tickets to add"},
                    "price_cents": {"type": "integer", "description": "Price in cents (required if creating new tier)"},
                    "description": {"type": "string", "description": "Tier description (optional, for new tiers)"},
                },
                "required": ["event_id", "tier_name", "quantity"],
            },
        ),
        Tool(
            name="set_event_visibility",
            description="Show or hide an event from public listings. Use for 'hide event' or 'make event live'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "is_visible": {"type": "boolean", "description": "True to make visible/live, False to hide"},
                },
                "required": ["event_id", "is_visible"],
            },
        ),
        # Sales and attendee tools
        Tool(
            name="get_event_sales",
            description="Get sales statistics for an event. Optionally filter by date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "start_date": {"type": "string", "description": "Start date filter (YYYY-MM-DD). When provided, revenue is calculated from actual ticket records."},
                    "end_date": {"type": "string", "description": "End date filter (YYYY-MM-DD). When provided, revenue is calculated from actual ticket records."},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="get_all_sales",
            description="Get total sales across all events. Optionally filter by date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date filter (YYYY-MM-DD). When provided, revenue is calculated from actual ticket records."},
                    "end_date": {"type": "string", "description": "End date filter (YYYY-MM-DD). When provided, revenue is calculated from actual ticket records."},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_revenue_report",
            description="Generate a detailed revenue report with daily/weekly breakdowns, top events by revenue, and optional comparison to a previous period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Report start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "Report end date (YYYY-MM-DD). Defaults to today."},
                    "breakdown": {"type": "string", "enum": ["daily", "weekly"], "description": "How to break down revenue over the period. Default: daily."},
                    "compare_previous": {"type": "boolean", "description": "If true, include comparison to the equivalent previous period. Default: false."},
                    "event_id": {"type": "integer", "description": "Optional: limit report to a specific event."},
                },
                "required": ["start_date"],
            },
        ),
        Tool(
            name="refresh_dashboard",
            description="Send a refresh command to the TV dashboard. Use 'full' for page reload or 'soft' to just reload data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["full", "soft"], "description": "Type of refresh: 'full' reloads the page, 'soft' reloads data only", "default": "soft"},
                    "message": {"type": "string", "description": "Optional message to display"},
                },
                "required": [],
            },
        ),
        Tool(
            name="sync_tiers_to_stripe",
            description="Sync existing ticket tiers to Stripe. Creates Stripe products/prices for tiers that haven't been synced yet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID to sync (optional, syncs all if not provided)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="refund_ticket",
            description="Refund a ticket and return money to the customer via Stripe. Can look up tickets by ticket ID or by customer name. Marks ticket as refunded, restores inventory, and optionally notifies the customer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "Refund a specific ticket by ID"},
                    "customer_name": {"type": "string", "description": "Find and refund tickets by customer name"},
                    "event_id": {"type": "integer", "description": "When using customer_name, limit to this event"},
                    "notify_customer": {"type": "boolean", "description": "Send refund confirmation email/SMS (default true)"},
                    "reason": {"type": "string", "description": "Reason for refund (for internal records)"},
                },
                "required": [],
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
            name="update_customer",
            description="Update a customer's info (email, phone, name)",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "Customer ID"},
                    "name": {"type": "string", "description": "New name (optional)"},
                    "email": {"type": "string", "description": "New email (optional)"},
                    "phone": {"type": "string", "description": "New phone (optional)"},
                },
                "required": ["customer_id"],
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
            name="search_customers",
            description="Search customers by name, VIP status, or marketing opt-in. Use this to find customers without exact email/phone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search by name (partial match)"},
                    "is_vip": {"type": "boolean", "description": "Filter VIP customers only"},
                    "marketing_opt_in": {"type": "boolean", "description": "Filter by marketing opt-in status"},
                },
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
            name="check_out_by_name",
            description="Reverse a check-in for a guest (undo check-in).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Guest's full name"},
                    "event_id": {"type": "integer", "description": "Event ID (optional)"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="guest_list",
            description="Get the full guest list for an event with names and check-in status",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "status": {"type": "string", "description": "Filter by status: all, checked_in, not_checked_in (default: all)"},
                },
                "required": ["event_id"],
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
            name="configure_auto_reminder",
            description="Configure automatic reminders for an event. Set how many hours before the event to send reminders, enable/disable SMS, or turn off auto-reminders entirely.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "hours_before": {"type": "integer", "description": "Hours before event to send reminder (e.g. 24, 48, 2). Set to 0 to disable."},
                    "use_sms": {"type": "boolean", "description": "Also send SMS reminders (default: false, email only)"},
                    "enabled": {"type": "boolean", "description": "Set to false to disable auto-reminders for this event"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="list_scheduled_reminders",
            description="List all upcoming scheduled auto-reminders across all events, or check the reminder status for a specific event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Optional: check reminder for a specific event only"},
                },
                "required": [],
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
            name="postpone_event",
            description="Postpone an event to a new date/time and notify all ticket holders. Tickets remain valid.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID"},
                    "new_date": {"type": "string", "description": "New event date in YYYY-MM-DD format (optional)"},
                    "new_time": {"type": "string", "description": "New event time in HH:MM format (optional)"},
                    "reason": {"type": "string", "description": "Reason for postponement (optional)"},
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
        # ============== Marketing Campaign Tools ==============
        Tool(
            name="create_campaign",
            description="Create a marketing campaign as a draft. Supports segment targeting (VIPs, repeat customers, high spenders, category fans). Use send_campaign to send it, or use quick_send_campaign for one-step create+send.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name (internal reference)"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "content": {"type": "string", "description": "Message content (used for both email body and SMS)"},
                    "target_all": {"type": "boolean", "description": "True to target ALL marketing opted-in users (default false)"},
                    "target_event_id": {"type": "integer", "description": "Target attendees of a specific event who are marketing opted-in"},
                    "target_vip": {"type": "boolean", "description": "Target only VIP customers"},
                    "target_vip_tier": {"type": "string", "description": "Target specific VIP tier (e.g. gold, platinum). Requires target_vip=true"},
                    "target_min_events": {"type": "integer", "description": "Target customers who attended at least this many events (e.g. 3 for repeat customers)"},
                    "target_min_spent_cents": {"type": "integer", "description": "Target customers who spent at least this amount in cents (e.g. 50000 for $500+)"},
                    "target_category_ids": {"type": "array", "items": {"type": "integer"}, "description": "Target customers who attended events in these category IDs. Use list_categories to find IDs."},
                    "target_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Target attendees of ANY of these events (multi-event re-engagement)"},
                    "target_series_id": {"type": "string", "description": "Target all attendees of a recurring event series (use series_id UUID from the event)"},
                    "target_exclude_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Exclude attendees of these events (e.g. already have tickets to this show)"},
                    "target_days_since_last_event": {"type": "integer", "description": "Only target lapsed customers inactive for N+ days (e.g. 60 = haven't attended in 2 months)"},
                    "target_attended_since_days": {"type": "integer", "description": "Only target customers who attended an event within the last N days (e.g. 90 = last 3 months)"},
                },
                "required": ["name", "subject", "content"],
            },
        ),
        Tool(
            name="list_campaigns",
            description="List all marketing campaigns with their status (draft, sending, sent)",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["draft", "scheduled", "sending", "sent"], "description": "Filter by status (optional)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="update_campaign",
            description="Update a draft campaign's message, subject, or name before sending. Campaign must be in 'draft' status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "integer", "description": "The campaign ID to update"},
                    "name": {"type": "string", "description": "New campaign name (optional)"},
                    "subject": {"type": "string", "description": "New email subject line (optional)"},
                    "content": {"type": "string", "description": "New message content (optional)"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="send_campaign",
            description="Send an existing marketing campaign to its targeted recipients. Campaign must be in 'draft' status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "integer", "description": "The campaign ID to send"},
                    "use_email": {"type": "boolean", "description": "Send via email (default true)"},
                    "use_sms": {"type": "boolean", "description": "Also send via SMS (default false)"},
                },
                "required": ["campaign_id"],
            },
        ),
        Tool(
            name="quick_send_campaign",
            description="One-step: create AND immediately send a marketing blast. Supports segment targeting. Use when someone says 'blast all VIP customers' or 'email repeat customers about our sale'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name (auto-generated if not provided)"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "content": {"type": "string", "description": "Message content"},
                    "target_all": {"type": "boolean", "description": "True to send to ALL marketing opted-in users"},
                    "target_event_id": {"type": "integer", "description": "Send to attendees of a specific event only"},
                    "target_vip": {"type": "boolean", "description": "Target only VIP customers"},
                    "target_vip_tier": {"type": "string", "description": "Target specific VIP tier (e.g. gold, platinum)"},
                    "target_min_events": {"type": "integer", "description": "Target customers who attended at least this many events"},
                    "target_min_spent_cents": {"type": "integer", "description": "Target customers who spent at least this amount in cents"},
                    "target_category_ids": {"type": "array", "items": {"type": "integer"}, "description": "Target customers who attended events in these category IDs"},
                    "target_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Target attendees of ANY of these events (multi-event re-engagement)"},
                    "target_series_id": {"type": "string", "description": "Target all attendees of a recurring event series (use series_id UUID from the event)"},
                    "target_exclude_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Exclude attendees of these events"},
                    "target_days_since_last_event": {"type": "integer", "description": "Only target lapsed customers inactive for N+ days"},
                    "target_attended_since_days": {"type": "integer", "description": "Only target customers who attended within the last N days"},
                    "use_email": {"type": "boolean", "description": "Send via email (default true)"},
                    "use_sms": {"type": "boolean", "description": "Also send via SMS (default false)"},
                },
                "required": ["subject", "content"],
            },
        ),
        Tool(
            name="preview_audience",
            description="Preview how many people would receive a campaign with the given targeting. Use BEFORE sending to check audience size. Returns count, SMS-eligible count, and sample names.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_all": {"type": "boolean", "description": "Target all opted-in users"},
                    "target_event_id": {"type": "integer", "description": "Target attendees of one event"},
                    "target_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Target attendees of multiple events"},
                    "target_series_id": {"type": "string", "description": "Target all attendees of a recurring series"},
                    "target_vip": {"type": "boolean", "description": "VIP customers only"},
                    "target_vip_tier": {"type": "string", "description": "Specific VIP tier"},
                    "target_min_events": {"type": "integer", "description": "Min events attended"},
                    "target_min_spent_cents": {"type": "integer", "description": "Min spent in cents"},
                    "target_category_ids": {"type": "array", "items": {"type": "integer"}, "description": "Event category IDs"},
                    "target_exclude_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Exclude attendees of these events"},
                    "target_days_since_last_event": {"type": "integer", "description": "Inactive for N+ days"},
                    "target_attended_since_days": {"type": "integer", "description": "Active within last N days"},
                },
                "required": [],
            },
        ),
        # ============== Marketing List Tools ==============
        Tool(
            name="create_marketing_list",
            description="Create a saved, reusable audience list with segment filters. Use the same targeting params as campaigns. The list auto-updates — new matching customers are included when you send.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "List name (e.g. 'Latin Night VIPs', 'Comedy Regulars')"},
                    "description": {"type": "string", "description": "Optional description of this audience"},
                    "target_event_id": {"type": "integer", "description": "Attendees of a specific event"},
                    "target_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Attendees of multiple events"},
                    "target_series_id": {"type": "string", "description": "All attendees of a recurring series"},
                    "target_vip": {"type": "boolean", "description": "VIP customers only"},
                    "target_vip_tier": {"type": "string", "description": "Specific VIP tier"},
                    "target_min_events": {"type": "integer", "description": "Min events attended"},
                    "target_min_spent_cents": {"type": "integer", "description": "Min spent in cents"},
                    "target_category_ids": {"type": "array", "items": {"type": "integer"}, "description": "Event category IDs"},
                    "target_exclude_event_ids": {"type": "array", "items": {"type": "integer"}, "description": "Exclude attendees of these events"},
                    "target_days_since_last_event": {"type": "integer", "description": "Inactive for N+ days"},
                    "target_attended_since_days": {"type": "integer", "description": "Active within last N days"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_marketing_lists",
            description="Show all saved marketing lists with live member counts.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_marketing_list",
            description="View a marketing list's details, live member count, and sample member names.",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {"type": "integer", "description": "The marketing list ID"},
                },
                "required": ["list_id"],
            },
        ),
        Tool(
            name="delete_marketing_list",
            description="Delete a saved marketing list by ID or name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {"type": "integer", "description": "The marketing list ID"},
                    "name": {"type": "string", "description": "Or delete by name"},
                },
                "required": [],
            },
        ),
        Tool(
            name="send_to_marketing_list",
            description="Send a campaign to a saved marketing list. Creates the campaign and sends immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {"type": "integer", "description": "The marketing list ID to send to"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "content": {"type": "string", "description": "Message content"},
                    "use_email": {"type": "boolean", "description": "Send via email (default true)"},
                    "use_sms": {"type": "boolean", "description": "Also send via SMS (default false)"},
                },
                "required": ["list_id", "subject", "content"],
            },
        ),
        # ============== Promo Code Tools ==============
        Tool(
            name="create_promo_code",
            description="Create a new promo/discount code. Discount types: 'percent' (1-100) or 'fixed_cents' (amount in cents).",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The promo code (will be uppercased, e.g. SUMMER20)"},
                    "discount_type": {"type": "string", "enum": ["percent", "fixed_cents"], "description": "'percent' for percentage off, 'fixed_cents' for fixed amount in cents (e.g. 500 = $5.00)"},
                    "discount_value": {"type": "integer", "description": "1-100 for percent, or cents for fixed"},
                    "event_id": {"type": "integer", "description": "Limit to specific event (optional, null = all events)"},
                    "max_uses": {"type": "integer", "description": "Maximum uses (optional, null = unlimited)"},
                    "valid_until": {"type": "string", "description": "Expiry date ISO format (optional)"},
                },
                "required": ["code", "discount_type", "discount_value"],
            },
        ),
        Tool(
            name="list_promo_codes",
            description="List all promo/discount codes, optionally filtered by event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Filter by event ID (optional)"},
                    "active_only": {"type": "boolean", "description": "Only show active codes (default true)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="validate_promo_code",
            description="Check if a promo code is valid for a specific ticket tier and preview the discount",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The promo code to validate"},
                    "ticket_tier_id": {"type": "integer", "description": "The ticket tier to check price against"},
                },
                "required": ["code", "ticket_tier_id"],
            },
        ),
        Tool(
            name="deactivate_promo_code",
            description="Deactivate a promo code so it can no longer be used",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The promo code to deactivate"},
                },
                "required": ["code"],
            },
        ),
        # ============== Analytics Tools ==============
        Tool(
            name="get_event_analytics",
            description="Get page view analytics for an event or overall (total views, unique visitors, top referrers, traffic sources)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID (optional — omit for overall analytics across all events)"},
                    "days": {"type": "integer", "description": "Number of days to look back (default 30)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_conversion_analytics",
            description="Get conversion funnel analytics for an event: page views to purchases, conversion rate, and UTM attribution breakdown",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "days": {"type": "integer", "description": "Number of days to look back (default 30)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="share_event_link",
            description="Send the public event page link to someone via email, SMS, or both. Use this when someone asks you to share an event, send an event link, or invite someone to an event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID to share"},
                    "to_email": {"type": "string", "description": "Email address to send to (optional if phone provided)"},
                    "to_phone": {"type": "string", "description": "Phone number to send SMS to (optional if email provided)"},
                    "recipient_name": {"type": "string", "description": "Recipient's name (optional, for personalization)"},
                    "message": {"type": "string", "description": "Optional custom message to include"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="send_admin_link",
            description="Send a magic link via SMS to the event promoter's phone on file so they can manage the event (upload images, edit details). The link expires in 1 hour. Only works if the event has a promoter_phone set.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID to send the admin link for"},
                },
                "required": ["event_id"],
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
            name="email_payment_link",
            description="Smart tool: Find customer by name, create a payment link, and email it to them. Say 'email payment link to Ed Duran for 2 VIP tickets to Bulls game'",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name to find"},
                    "email": {"type": "string", "description": "Or customer email directly"},
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "tier_id": {"type": "integer", "description": "Ticket tier ID (optional)"},
                    "quantity": {"type": "integer", "description": "Number of tickets", "default": 1},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="create_payment_link",
            description="Create a permanent Stripe Payment Link for tickets. These links don't expire and are more reliable than checkout sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "tier_id": {"type": "integer", "description": "Ticket tier ID"},
                    "quantity": {"type": "integer", "description": "Number of tickets", "default": 1},
                },
                "required": ["event_id", "tier_id"],
            },
        ),
        Tool(
            name="send_purchase_email",
            description="Send a beautiful purchase link email to a customer",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_email": {"type": "string", "description": "Email address to send to"},
                    "name": {"type": "string", "description": "Customer's name"},
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "tier_id": {"type": "integer", "description": "Ticket tier ID"},
                    "quantity": {"type": "integer", "description": "Number of tickets", "default": 1},
                    "checkout_url": {"type": "string", "description": "Stripe checkout URL (optional - will create new if not provided)"},
                },
                "required": ["to_email", "name", "event_id"],
            },
        ),
        Tool(
            name="send_ticket_link",
            description="Smart tool: Find customer by name/email, update their phone if needed, and send a payment link via SMS. Handles everything in one step.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name to search for"},
                    "email": {"type": "string", "description": "Customer email to search for"},
                    "phone": {"type": "string", "description": "Phone number to send SMS to (will update customer's phone if different)"},
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
        # ============== Ticket Download Tools ==============
        Tool(
            name="download_ticket_pdf",
            description="Get a PDF download URL for a ticket. The customer can download a branded PDF with QR code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "The ticket ID"},
                },
                "required": ["ticket_id"],
            },
        ),
        Tool(
            name="download_wallet_pass",
            description="Get an Apple Wallet download URL for a ticket. The customer can add the ticket to their iPhone wallet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "The ticket ID"},
                },
                "required": ["ticket_id"],
            },
        ),
        Tool(
            name="send_ticket_pdf",
            description="Email a PDF ticket download link to the ticket holder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "The ticket ID"},
                },
                "required": ["ticket_id"],
            },
        ),
        Tool(
            name="send_wallet_pass",
            description="Email an Apple Wallet pass download link to the ticket holder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "The ticket ID"},
                },
                "required": ["ticket_id"],
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
        # Waitlist tools
        Tool(
            name="get_waitlist",
            description="View the waitlist for a sold-out event. Shows position, name, email, status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="notify_waitlist",
            description="Send availability notifications to the next N people on the waitlist (default 5). Use when tickets become available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "count": {"type": "integer", "description": "Number of people to notify (default 5)"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="remove_from_waitlist",
            description="Remove someone from the waitlist by email",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID"},
                    "email": {"type": "string", "description": "Email of person to remove"},
                },
                "required": ["event_id", "email"],
            },
        ),
        # ============== Social Media Tools (Postiz) ==============
        Tool(
            name="list_social_integrations",
            description="List all connected social media accounts/channels. CALL THIS FIRST before posting to social media — you need the integration IDs. Returns id, platform name, and account details for each connected channel.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="post_event_to_social",
            description="Post about an event to connected social media accounts. Use list_social_integrations first to get integration IDs. Can include event flyer/image. Supports X, Instagram, Facebook, LinkedIn, TikTok, Bluesky, Threads, and 20+ more platforms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Event ID to promote"},
                    "integration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Postiz integration IDs to post to (from list_social_integrations)",
                    },
                    "custom_text": {"type": "string", "description": "Optional custom post text. If not provided, auto-generates from event details."},
                    "image_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional public URLs for images/videos to attach",
                    },
                },
                "required": ["event_id", "integration_ids"],
            },
        ),
        Tool(
            name="schedule_social_post",
            description="Schedule a social media post for a future date/time. Use list_social_integrations first to get integration IDs. Useful for timed promos like '2 hours before the event'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The post content"},
                    "integration_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Postiz integration IDs to post to (from list_social_integrations)",
                    },
                    "schedule_date": {"type": "string", "description": "ISO 8601 datetime to publish (e.g. '2025-12-01T10:00:00Z')"},
                    "image_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional public URLs for images/videos to attach",
                    },
                },
                "required": ["text", "integration_ids", "schedule_date"],
            },
        ),
        Tool(
            name="get_social_post_history",
            description="Get history of social media posts. Shows what was posted, when, and to which platforms. Defaults to last 30 days.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "ISO 8601 start date (default: 30 days ago)"},
                    "end_date": {"type": "string", "description": "ISO 8601 end date (default: now)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="delete_social_post",
            description="Delete a previously published social media post by its Postiz post ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {"type": "string", "description": "The Postiz post ID to delete"},
                },
                "required": ["post_id"],
            },
        ),
        # ============== Predictive Analytics Tools ==============
        Tool(
            name="predict_demand",
            description="Predict demand and sell-out probability for an event. Uses ticket velocity, waitlist pressure, page views, historical patterns, and time scarcity to forecast whether the event will sell out and when. Returns a demand score (0-100), sell-out probability, projected sell-out date, and per-tier breakdown.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID to predict demand for"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="get_pricing_suggestions",
            description="Get dynamic pricing suggestions for an event's ticket tiers. Analyzes demand signals, sell-through rate, time until event, and price elasticity to recommend price adjustments. Returns per-tier suggestions with recommended prices, confidence levels, and reasoning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID to get pricing suggestions for"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="predict_churn",
            description="Identify customers at risk of churning using RFM (Recency, Frequency, Monetary) analysis. Returns a ranked list of at-risk customers with their RFM scores, churn risk level, days since last activity, and personalized re-engagement suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_days_inactive": {"type": "integer", "description": "Minimum days since last activity to consider (default: 30)"},
                    "limit": {"type": "integer", "description": "Maximum number of at-risk customers to return (default: 50)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_customer_segments",
            description="Segment all customers into groups using RFM analysis. Returns segments like Champions, Loyal, Potential Loyalists, At Risk, Hibernating, and Lost with counts, average spend, and representative customers per segment.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="recommend_events",
            description="Get personalized event recommendations for a customer. Uses a hybrid algorithm combining content-based filtering (past category/venue preferences), collaborative filtering (similar customers' behavior), and popularity signals. Provide either customer_id or customer_email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "description": "EventGoer ID"},
                    "customer_email": {"type": "string", "description": "Customer email (alternative to customer_id)"},
                    "limit": {"type": "integer", "description": "Max recommendations to return (default: 5)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_trending_events",
            description="Get currently trending events ranked by a composite score of recent page views, ticket sales velocity, waitlist signups, and social buzz. Useful for identifying hot events to promote or analyze.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Look-back window in days (default: 7)"},
                    "limit": {"type": "integer", "description": "Max events to return (default: 10)"},
                },
                "required": [],
            },
        ),
        # ============== Automation Tools ==============
        Tool(
            name="get_abandoned_carts",
            description="View all currently abandoned carts — pending tickets older than 30 minutes that haven't been paid. Shows per-customer breakdown with event names, tiers, and prices.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="send_cart_recovery",
            description="Manually send an abandoned cart recovery email/SMS to a specific customer. Reminds them to complete their purchase before tickets expire.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email to send recovery to"},
                },
                "required": ["email"],
            },
        ),
        Tool(
            name="list_auto_triggers",
            description="List all automated marketing triggers with their status, fire count, and last fired time. Triggers run automatically on a schedule when conditions are met.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="create_auto_trigger",
            description="Create an automated marketing trigger. Types: low_sell_through (send promo when sales are slow), almost_sold_out (send urgency campaign), post_event_followup (thank-you after event), new_event_alert (notify fans of new events).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable trigger name"},
                    "trigger_type": {"type": "string", "description": "One of: low_sell_through, almost_sold_out, post_event_followup, new_event_alert"},
                    "action": {"type": "string", "description": "One of: send_promo, send_campaign, send_survey"},
                    "event_id": {"type": "integer", "description": "Optional: target a specific event (null = all events)"},
                    "threshold_value": {"type": "integer", "description": "Percentage threshold (e.g. 30 for low_sell_through, 90 for almost_sold_out)"},
                    "threshold_days": {"type": "integer", "description": "Days-before-event threshold (e.g. 7 = trigger when 7 days left)"},
                    "action_config": {"type": "object", "description": "Optional config: {discount_percent, subject, content, code, max_uses}"},
                },
                "required": ["name", "trigger_type", "action"],
            },
        ),
        Tool(
            name="delete_auto_trigger",
            description="Delete an automated marketing trigger by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "integer", "description": "The trigger ID to delete"},
                },
                "required": ["trigger_id"],
            },
        ),
        Tool(
            name="get_trigger_history",
            description="View details and fire history for a specific auto trigger.",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "integer", "description": "The trigger ID to inspect"},
                },
                "required": ["trigger_id"],
            },
        ),
        Tool(
            name="get_revenue_forecast",
            description="Project total revenue across all upcoming events for the next 30/60/90 days. Uses current ticket velocity, historical completion rates, and per-event confidence intervals. Returns per-event breakdown with low/mid/high projections.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_horizon_days": {"type": "integer", "description": "Forecast horizon in days (default: 90)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="get_survey_results",
            description="View aggregated post-event survey results including NPS score, average rating, response rate, and recent comments. Optionally filter by event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "Optional: filter results to a specific event"},
                },
                "required": [],
            },
        ),
        Tool(
            name="send_event_survey",
            description="Send post-event surveys to all attendees of an event. Creates unique survey tokens and sends email/SMS with survey links. Typically auto-sent 24h after event, but can be triggered manually.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "The event ID to send surveys for"},
                },
                "required": ["event_id"],
            },
        ),
        # Knowledge base (RAG) tools
        Tool(
            name="search_knowledge_base",
            description="Semantic search across the knowledge base (uploaded PDFs, text files, FAQs). Use when the user asks a question you can't answer from structured data (e.g. parking info, venue policies, accessibility details).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (natural language question)"},
                    "venue_id": {"type": "integer", "description": "Optional: filter results to a specific venue"},
                    "event_id": {"type": "integer", "description": "Optional: filter results to a specific event"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="upload_knowledge",
            description="Add a text entry (FAQ, policy, info) to the knowledge base. Use for pasting FAQ content or quick notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title for this knowledge entry"},
                    "content": {"type": "string", "description": "The text content to add"},
                    "venue_id": {"type": "integer", "description": "Optional: associate with a venue"},
                    "event_id": {"type": "integer", "description": "Optional: associate with an event"},
                },
                "required": ["title", "content"],
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

    # ============== Agent Guidance Tools ==============
    if name == "get_agent_instructions":
        return {
            "role": f"{settings.org_name} event ticketing operations assistant",
            "core_workflows": {
                "ticket_purchase": {
                    "steps": [
                        "1. Find or register the customer (search_customers, lookup_customer, or register_customer)",
                        "2. Find the event (search_events or list_events)",
                        "3. Check availability (get_ticket_availability)",
                        "4. Send purchase link via preferred channel",
                    ],
                    "purchase_tools": {
                        "email_payment_link": "Best for email delivery. Finds customer by name, creates Stripe link, emails it. One step.",
                        "send_ticket_link": "Best for SMS delivery. Finds customer, updates phone if needed, sends SMS with purchase link.",
                        "create_payment_link": "Returns the URL only (to share manually or paste in chat). No delivery.",
                        "send_purchase_link": "SMS delivery but requires phone verification first. Prefer send_ticket_link instead.",
                    },
                },
                "check_in": {
                    "steps": [
                        "1. Try check_in_by_name (most common - guest gives their name)",
                        "2. If QR code available, use check_in_ticket with qr_token",
                        "3. If wrong check-in, use check_out_by_name to reverse",
                    ],
                },
                "customer_lookup": {
                    "steps": [
                        "1. get_customer_profile — full history, notes, preferences (use for returning customers)",
                        "2. search_customers — fuzzy name search across all customers",
                        "3. lookup_customer — exact phone or email match",
                        "4. find_guest — search by name within ticket holders only",
                    ],
                },
            },
            "categories": {
                    "description": "Events can be tagged with categories (Sports, Concerts, Comedy, etc.)",
                    "steps": [
                        "1. Use list_categories to see available categories",
                        "2. When creating events, pass category_ids to assign categories",
                        "3. Use search_events with category filter to find events by type",
                        "4. Use create_category to add new categories (admin only)",
                    ],
                },
            "marketing_campaigns": {
                    "description": "Send promotional emails/SMS blasts with segment targeting (VIPs, repeat customers, high spenders, category fans)",
                    "steps": [
                        "1. For quick blasts: use quick_send_campaign (creates + sends in one step)",
                        "2. For planned campaigns: create_campaign first, then send_campaign",
                        "3. Target by specific event (target_event_id), all opted-in users (target_all=true), or segments",
                        "4. Segment filters: target_vip, target_min_events, target_min_spent_cents, target_category_ids",
                        "5. Combine segments with AND logic: e.g., VIP customers who attended 3+ events",
                        "6. Only recipients with marketing_opt_in=True will receive messages",
                        "7. SMS only goes to recipients with sms_opt_in=True and a phone number",
                        "8. Use list_categories to find category IDs for category targeting",
                    ],
                    "tools": {
                        "quick_send_campaign": "One step: creates + sends. Use when user says 'blast all VIP customers' or 'email repeat customers'.",
                        "create_campaign": "Creates a draft campaign for review before sending.",
                        "send_campaign": "Sends an existing draft campaign.",
                        "list_campaigns": "View all campaigns and their send status.",
                    },
                    "segment_examples": {
                        "VIP blast": "quick_send_campaign with target_vip=true",
                        "Repeat customers": "quick_send_campaign with target_min_events=3",
                        "High spenders ($500+)": "quick_send_campaign with target_min_spent_cents=50000",
                        "Concert fans": "quick_send_campaign with target_category_ids=[id] (use list_categories first)",
                        "VIP high spenders": "quick_send_campaign with target_vip=true + target_min_spent_cents=50000",
                    },
                },
            "promo_codes": {
                    "description": "Create and manage promo/discount codes for ticket purchases",
                    "steps": [
                        "1. Use create_promo_code to make a new code (e.g. SUMMER20, 20% off)",
                        "2. Use validate_promo_code to check if a code works for a specific tier",
                        "3. Use list_promo_codes to see all active codes",
                        "4. Use deactivate_promo_code to disable a code",
                    ],
                    "examples": {
                        "20% off all events": "create_promo_code code=VIP20 discount_type=percent discount_value=20",
                        "$10 off specific event": "create_promo_code code=SAVE10 discount_type=fixed_cents discount_value=1000 event_id=5",
                        "Limited use 50% off": "create_promo_code code=FLASH50 discount_type=percent discount_value=50 max_uses=20",
                    },
                },
            "error_recovery": {
                "customer_not_found": "Use register_customer to create them, then retry",
                "event_not_found": "Use search_events with a partial name to find the correct event_id",
                "phone_not_verified": "Use send_ticket_link instead (no verification needed)",
                "multiple_matches": "Ask the user to clarify which match they mean",
                "stripe_error": "Check if tier has been synced to Stripe with sync_tiers_to_stripe",
            },
            "best_practices": [
                "Always call get_customer_profile for returning customers — it loads history and preferences",
                "After check-in or purchase, use add_customer_note to record preferences or issues",
                "Use search_events instead of list_events when the customer names a specific event",
                "Prefer email_payment_link over manual steps — it handles lookup, Stripe link, and email in one call",
                "For marketing blasts, prefer quick_send_campaign — it handles create + send in one call",
            ],
        }

    elif name == "get_branding":
        return {
            "org_name": settings.org_name,
            "org_color": settings.org_color,
            "org_logo_url": settings.org_logo_url,
        }

    # ============== Category Tools ==============
    elif name == "list_categories":
        categories = db.query(EventCategory).order_by(EventCategory.name).all()
        return [{"id": c.id, "name": c.name, "description": c.description, "color": c.color, "image_url": c.image_url} for c in categories]

    elif name == "create_category":
        existing = db.query(EventCategory).filter(EventCategory.name == arguments["name"]).first()
        if existing:
            return {"error": f"Category '{arguments['name']}' already exists"}
        category = EventCategory(
            name=arguments["name"],
            description=arguments.get("description"),
            color=arguments.get("color"),
            image_url=arguments.get("image_url"),
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return {"id": category.id, "name": category.name, "description": category.description, "color": category.color, "image_url": category.image_url}

    elif name == "update_category":
        category = db.query(EventCategory).filter(EventCategory.id == arguments["category_id"]).first()
        if not category:
            return {"error": "Category not found"}
        for field in ["name", "description", "color", "image_url"]:
            if field in arguments:
                setattr(category, field, arguments[field])
        db.commit()
        db.refresh(category)
        return {"id": category.id, "name": category.name, "description": category.description, "color": category.color, "image_url": category.image_url}

    # ============== Venue Tools ==============
    elif name == "list_venues":
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
        events = db.query(Event).options(joinedload(Event.venue), joinedload(Event.categories)).all()
        result = []
        for e in events:
            event_dict = _event_to_dict(e)
            event_dict["venue"] = _venue_to_dict(e.venue)
            result.append(event_dict)
        return result

    elif name == "get_event":
        event = (
            db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers), joinedload(Event.categories))
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
        # Attach categories if provided
        if arguments.get("category_ids"):
            categories = db.query(EventCategory).filter(EventCategory.id.in_(arguments["category_ids"])).all()
            event.categories = categories
        db.add(event)
        db.commit()
        db.refresh(event)

        # Auto-schedule reminder
        if getattr(event, "auto_reminder_hours", None) is not None:
            try:
                from app.services.scheduler import schedule_auto_reminder
                schedule_auto_reminder(event.id, event.event_date, event.event_time, event.auto_reminder_hours, getattr(event, "auto_reminder_use_sms", False))
            except Exception:
                pass

        return _event_to_dict(event)

    elif name == "create_recurring_event":
        import uuid as uuid_mod
        import calendar
        from datetime import date

        # Validate venue
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}

        # Parse parameters
        day_of_week = arguments["day_of_week"].lower()
        frequency = arguments.get("frequency", "weekly")
        duration_months = min(arguments.get("duration_months", 3), 12)
        event_time = arguments["event_time"]
        event_name = arguments["name"]
        description = arguments.get("description")
        doors_open_time = arguments.get("doors_open_time")
        category_ids = arguments.get("category_ids", [])
        tier_name = arguments.get("tier_name", "General Admission")
        tier_price = arguments.get("tier_price", 0)
        tier_quantity = arguments.get("tier_quantity", 100)

        # Map day name to weekday number (Monday=0)
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        target_weekday = day_map.get(day_of_week)
        if target_weekday is None:
            return {"error": f"Invalid day_of_week: {day_of_week}"}

        # Calculate start date
        start_str = arguments.get("start_date")
        if start_str:
            try:
                start = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid start_date format, use YYYY-MM-DD"}
        else:
            start = datetime.now().date()

        # Calculate end date
        end_month = start.month + duration_months
        end_year = start.year + (end_month - 1) // 12
        end_month = (end_month - 1) % 12 + 1
        end_day = min(start.day, calendar.monthrange(end_year, end_month)[1])
        end = date(end_year, end_month, end_day)

        # Find first occurrence of target weekday on or after start
        current = start
        days_ahead = target_weekday - current.weekday()
        if days_ahead < 0:
            days_ahead += 7
        current = current + timedelta(days=days_ahead)

        # Generate event dates
        event_dates = []
        if frequency == "weekly":
            step = timedelta(days=7)
            while current <= end:
                event_dates.append(current.strftime("%Y-%m-%d"))
                current = current + step
        elif frequency == "biweekly":
            step = timedelta(days=14)
            while current <= end:
                event_dates.append(current.strftime("%Y-%m-%d"))
                current = current + step
        elif frequency == "monthly":
            week_of_month = (current.day - 1) // 7  # 0-indexed week number
            while current <= end:
                event_dates.append(current.strftime("%Y-%m-%d"))
                # Advance to next month, same nth weekday
                month = current.month + 1
                year = current.year
                if month > 12:
                    month = 1
                    year += 1
                first_of_month = date(year, month, 1)
                first_weekday_offset = (target_weekday - first_of_month.weekday()) % 7
                candidate_day = 1 + first_weekday_offset + (week_of_month * 7)
                if candidate_day > calendar.monthrange(year, month)[1]:
                    candidate_day -= 7
                current = date(year, month, candidate_day)
        else:
            return {"error": f"Invalid frequency: {frequency}"}

        if not event_dates:
            return {"error": "No event dates generated. Check start_date and day_of_week."}

        # Generate series_id
        series_id = str(uuid_mod.uuid4())

        # Load categories once
        categories = []
        if category_ids:
            categories = db.query(EventCategory).filter(EventCategory.id.in_(category_ids)).all()

        # Create events + tiers in a single transaction
        created_events = []
        created_tiers = []
        for event_date_str in event_dates:
            event = Event(
                venue_id=arguments["venue_id"],
                name=event_name,
                description=description,
                event_date=event_date_str,
                event_time=event_time,
                doors_open_time=doors_open_time,
                series_id=series_id,
            )
            if categories:
                event.categories = list(categories)
            db.add(event)
            db.flush()

            tier = TicketTier(
                event_id=event.id,
                name=tier_name,
                price=tier_price,
                quantity_available=tier_quantity,
            )
            db.add(tier)
            db.flush()

            created_events.append(event)
            created_tiers.append(tier)

        db.commit()

        # Stripe sync for paid tiers (after commit)
        stripe_synced = 0
        stripe_errors = []
        if tier_price > 0:
            from app.services.stripe_sync import create_stripe_product_for_tier
            for tier in created_tiers:
                evt = db.query(Event).filter(Event.id == tier.event_id).first()
                sync_result = create_stripe_product_for_tier(db, tier, evt)
                if sync_result.get("success"):
                    stripe_synced += 1
                elif sync_result.get("error"):
                    stripe_errors.append(f"Event {tier.event_id}: {sync_result['error']}")

        # Build response
        response = {
            "series_id": series_id,
            "events_created": len(created_events),
            "frequency": frequency,
            "day_of_week": day_of_week,
            "first_date": event_dates[0],
            "last_date": event_dates[-1],
            "event_name": event_name,
            "tier_name": tier_name,
            "tier_price_cents": tier_price,
            "tier_quantity": tier_quantity,
            "event_ids": [e.id for e in created_events],
            "events": [_event_to_dict(e) for e in created_events],
        }
        if tier_price > 0:
            response["stripe_synced"] = stripe_synced
            if stripe_errors:
                response["stripe_errors"] = stripe_errors

        # Auto-schedule reminders for each event in the series
        reminder_count = 0
        try:
            from app.services.scheduler import schedule_auto_reminder
            for evt in created_events:
                if getattr(evt, "auto_reminder_hours", None) is not None:
                    r = schedule_auto_reminder(evt.id, evt.event_date, evt.event_time, evt.auto_reminder_hours, getattr(evt, "auto_reminder_use_sms", False))
                    if r.get("scheduled"):
                        reminder_count += 1
        except Exception:
            pass
        response["reminders_scheduled"] = reminder_count

        return response

    elif name == "update_event":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        # Capture old video URLs before update (for cleanup)
        old_promo = event.promo_video_url
        old_recap = event.post_event_video_url

        if "name" in arguments:
            event.name = arguments["name"]
        if "description" in arguments:
            event.description = arguments["description"]
        if "event_date" in arguments:
            event.event_date = arguments["event_date"]
        if "event_time" in arguments:
            event.event_time = arguments["event_time"]
        if "image_url" in arguments:
            event.image_url = arguments["image_url"]
        if "promo_video_url" in arguments:
            event.promo_video_url = arguments["promo_video_url"]
        if "category_ids" in arguments:
            categories = db.query(EventCategory).filter(EventCategory.id.in_(arguments["category_ids"])).all()
            event.categories = categories
        if "doors_open_time" in arguments:
            event.doors_open_time = arguments["doors_open_time"]
        if "is_visible" in arguments:
            event.is_visible = arguments["is_visible"]
        if "promoter_phone" in arguments:
            event.promoter_phone = arguments["promoter_phone"]
        if "promoter_name" in arguments:
            event.promoter_name = arguments["promoter_name"]
        if "post_event_video_url" in arguments:
            event.post_event_video_url = arguments["post_event_video_url"]
        db.commit()
        db.refresh(event)

        # Trigger background YouTube downloads
        import asyncio
        from app.services.video_download import is_youtube_url, trigger_video_download_async

        download_started = False
        if "promo_video_url" in arguments and is_youtube_url(arguments["promo_video_url"]):
            asyncio.create_task(trigger_video_download_async(
                event.id, "promo_video_url", arguments["promo_video_url"], old_promo,
            ))
            download_started = True
        if "post_event_video_url" in arguments and is_youtube_url(arguments["post_event_video_url"]):
            asyncio.create_task(trigger_video_download_async(
                event.id, "post_event_video_url", arguments["post_event_video_url"], old_recap,
            ))
            download_started = True

        # Reschedule auto-reminder if date/time changed
        if ("event_date" in arguments or "event_time" in arguments) and getattr(event, "auto_reminder_hours", None) is not None:
            try:
                from app.services.scheduler import schedule_auto_reminder
                schedule_auto_reminder(event.id, event.event_date, event.event_time, event.auto_reminder_hours, getattr(event, "auto_reminder_use_sms", False))
            except Exception:
                pass

        result = _event_to_dict(event)
        if download_started:
            result["video_download_started"] = True
        return result

    elif name == "set_post_event_video":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        old_recap = event.post_event_video_url
        event.post_event_video_url = arguments["video_url"]
        db.commit()
        db.refresh(event)

        # Trigger background YouTube download
        import asyncio
        from app.services.video_download import is_youtube_url, trigger_video_download_async

        download_pending = False
        if is_youtube_url(arguments["video_url"]):
            asyncio.create_task(trigger_video_download_async(
                event.id, "post_event_video_url", arguments["video_url"], old_recap,
            ))
            download_pending = True

        return {
            "success": True,
            "event_id": event.id,
            "event_name": event.name,
            "post_event_video_url": event.post_event_video_url,
            "message": f"Post-event video set for '{event.name}'"
                + (" (YouTube download started in background)" if download_pending else ""),
        }

    elif name == "send_photo_sharing_link":
        from app.services.sms import send_sms

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        # Get all attendees with phone numbers
        tickets = (
            db.query(Ticket)
            .options(joinedload(Ticket.event_goer), joinedload(Ticket.ticket_tier))
            .join(TicketTier)
            .filter(TicketTier.event_id == arguments["event_id"])
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .all()
        )

        # Deduplicate by event_goer_id, only those with phones
        seen_goers = set()
        recipients = []
        for ticket in tickets:
            goer = ticket.event_goer
            if goer.id not in seen_goers and goer.phone:
                seen_goers.add(goer.id)
                recipients.append(goer)

        if not recipients:
            return {
                "success": False,
                "error": "No attendees with phone numbers found for this event",
            }

        photo_url = f"{settings.base_url}/events/{event.id}/photos"
        custom_msg = arguments.get("custom_message", "")

        if custom_msg:
            message = f"{custom_msg}\n\nUpload your photos here:\n{photo_url}"
        else:
            message = (
                f"Hey! Thanks for coming to {event.name}! "
                f"We'd love to see your photos from the event.\n\n"
                f"Upload & browse photos here:\n{photo_url}"
            )

        sent = 0
        failed = 0
        for goer in recipients:
            result = send_sms(to_phone=goer.phone, message=message)
            if result.get("success"):
                sent += 1
            else:
                failed += 1

        return {
            "success": True,
            "event_name": event.name,
            "total_recipients": len(recipients),
            "sent": sent,
            "failed": failed,
            "photo_page_url": photo_url,
            "message": f"Photo sharing link sent to {sent} attendee(s) for '{event.name}'",
        }

    elif name == "get_event_photos":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        photos = (
            db.query(EventPhoto)
            .filter(EventPhoto.event_id == arguments["event_id"])
            .order_by(EventPhoto.created_at.desc())
            .all()
        )

        return {
            "event_id": event.id,
            "event_name": event.name,
            "photo_count": len(photos),
            "photo_page_url": f"{settings.base_url}/events/{event.id}/photos",
            "photos": [
                {
                    "id": p.id,
                    "photo_url": p.photo_url,
                    "uploaded_by": p.uploaded_by_name,
                    "created_at": str(p.created_at),
                }
                for p in photos
            ],
        }

    elif name == "text_guest_list":
        from app.services.sms import send_sms

        # Support single or multiple events
        event_ids_list = list(arguments.get("event_ids", []))
        if arguments.get("event_id"):
            if arguments["event_id"] not in event_ids_list:
                event_ids_list.insert(0, arguments["event_id"])

        if not event_ids_list:
            return {"error": "Provide event_id or event_ids"}

        # Validate all events
        event_names = []
        for eid in event_ids_list:
            ev = db.query(Event).filter(Event.id == eid).first()
            if not ev:
                return {"error": f"Event {eid} not found"}
            event_names.append(ev.name)

        message_text = arguments["message"]

        # Get all attendees with phone numbers across all events (deduped)
        tickets = (
            db.query(Ticket)
            .options(joinedload(Ticket.event_goer), joinedload(Ticket.ticket_tier))
            .join(TicketTier)
            .filter(TicketTier.event_id.in_(event_ids_list))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .all()
        )

        seen_goers = set()
        recipients = []
        for ticket in tickets:
            goer = ticket.event_goer
            if goer.id not in seen_goers and goer.phone:
                seen_goers.add(goer.id)
                recipients.append(goer)

        if not recipients:
            return {
                "success": False,
                "error": "No attendees with phone numbers found",
            }

        # Build SMS label from event names
        if len(event_names) == 1:
            label = event_names[0]
        else:
            label = ", ".join(event_names[:3])
            if len(event_names) > 3:
                label += f" (+{len(event_names) - 3} more)"
        sms_body = f"{label}: {message_text}"

        sent = 0
        failed = 0
        for goer in recipients:
            result = send_sms(to_phone=goer.phone, message=sms_body)
            if result.get("success"):
                sent += 1
            else:
                failed += 1

        return {
            "success": True,
            "events": event_names,
            "total_recipients": len(recipients),
            "sent": sent,
            "failed": failed,
            "message": f"Texted {sent} attendee(s) across {len(event_ids_list)} event(s)",
        }

    elif name == "get_events_by_venue":
        venue = db.query(Venue).filter(Venue.id == arguments["venue_id"]).first()
        if not venue:
            return {"error": "Venue not found"}
        events = db.query(Event).filter(Event.venue_id == arguments["venue_id"]).all()
        return [_event_to_dict(e) for e in events]

    elif name == "search_events":
        query = db.query(Event).options(joinedload(Event.venue), joinedload(Event.categories))
        if arguments.get("query"):
            query = query.filter(Event.name.ilike(f"%{arguments['query'].strip()}%"))
        if arguments.get("status"):
            query = query.filter(Event.status == arguments["status"])
        if arguments.get("venue_id"):
            query = query.filter(Event.venue_id == arguments["venue_id"])
        if arguments.get("date_from"):
            query = query.filter(Event.event_date >= arguments["date_from"])
        if arguments.get("date_to"):
            query = query.filter(Event.event_date <= arguments["date_to"])
        if arguments.get("category"):
            query = query.join(Event.categories).filter(EventCategory.name.ilike(f"%{arguments['category'].strip()}%"))
        events = query.unique().all()
        if not events:
            return {"found": False, "message": "No events match your search", "count": 0}
        return {
            "found": True,
            "count": len(events),
            "events": [{**_event_to_dict(e), "venue": _venue_to_dict(e.venue)} for e in events],
        }

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

        # Sync to Stripe automatically
        stripe_result = create_stripe_product_for_tier(db, tier, event)
        db.refresh(tier)

        result = _tier_to_dict(tier)
        result["stripe_synced"] = stripe_result.get("success", False)
        if stripe_result.get("error"):
            result["stripe_error"] = stripe_result["error"]
        return result

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

    elif name == "update_ticket_tier":
        from app.models import TierStatus
        tier_id = arguments.get("tier_id")
        tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
        if not tier:
            return {"error": "Ticket tier not found"}
        event = db.query(Event).filter(Event.id == tier.event_id).first()
        changes = []
        if "name" in arguments:
            tier.name = arguments["name"]
            changes.append(f"name → {arguments['name']}")
        if "description" in arguments:
            tier.description = arguments["description"]
            changes.append("description updated")
        if "price" in arguments:
            old_price = tier.price
            tier.price = arguments["price"]
            changes.append(f"price ${old_price/100:.2f} → ${tier.price/100:.2f}")
        if "quantity_available" in arguments:
            old_qty = tier.quantity_available
            tier.quantity_available = arguments["quantity_available"]
            changes.append(f"quantity {old_qty} → {tier.quantity_available}")
        if "status" in arguments:
            old_status = tier.status.value if tier.status else "active"
            tier.status = TierStatus(arguments["status"])
            changes.append(f"status {old_status} → {tier.status.value}")
        # Auto sold-out check after quantity changes
        if tier.quantity_sold >= tier.quantity_available and "status" not in arguments:
            tier.status = TierStatus.SOLD_OUT
        elif tier.status == TierStatus.SOLD_OUT and tier.quantity_sold < tier.quantity_available and "status" not in arguments:
            tier.status = TierStatus.ACTIVE
        db.commit()
        db.refresh(tier)
        return {
            "success": True,
            "tier": _tier_to_dict(tier),
            "event": event.name if event else "Unknown",
            "changes": changes,
        }

    elif name == "toggle_all_tickets":
        from app.models import TierStatus
        event_id = arguments.get("event_id")
        target_status_str = arguments.get("status")
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}
        tiers = db.query(TicketTier).filter(TicketTier.event_id == event_id).all()
        if not tiers:
            return {"error": "No ticket tiers found for this event"}
        target_status = TierStatus.ACTIVE if target_status_str == "active" else TierStatus.PAUSED
        updated_count = 0
        skipped_sold_out = 0
        for tier in tiers:
            if target_status == TierStatus.ACTIVE and tier.status == TierStatus.SOLD_OUT:
                skipped_sold_out += 1
                continue
            if tier.status != target_status:
                tier.status = target_status
                updated_count += 1
        db.commit()
        return {
            "success": True,
            "event": event.name,
            "event_id": event.id,
            "updated_count": updated_count,
            "total_tiers": len(tiers),
            "new_status": target_status.value,
            "skipped_sold_out": skipped_sold_out,
        }

    elif name == "add_tickets":
        from app.models import TierStatus
        event_id = arguments.get("event_id")
        tier_name = arguments.get("tier_name")
        quantity = arguments.get("quantity")
        price_cents = arguments.get("price_cents")
        description = arguments.get("description")
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}
        # Try to find existing tier by name (case-insensitive)
        tier = db.query(TicketTier).filter(
            TicketTier.event_id == event_id,
            TicketTier.name.ilike(f"%{tier_name}%")
        ).first()
        if tier:
            old_qty = tier.quantity_available
            tier.quantity_available += quantity
            if tier.status == TierStatus.SOLD_OUT:
                tier.status = TierStatus.ACTIVE
            db.commit()
            db.refresh(tier)
            return {
                "success": True,
                "action": "increased",
                "tier": _tier_to_dict(tier),
                "event": event.name,
                "old_quantity": old_qty,
                "new_quantity": tier.quantity_available,
                "added": quantity,
            }
        else:
            if price_cents is None:
                return {"error": f"No tier found matching '{tier_name}'. To create a new tier, provide price_cents."}
            new_tier = TicketTier(
                event_id=event_id,
                name=tier_name,
                description=description,
                price=price_cents,
                quantity_available=quantity,
                quantity_sold=0,
                status=TierStatus.ACTIVE,
            )
            db.add(new_tier)
            db.commit()
            db.refresh(new_tier)
            # Sync to Stripe if paid tier
            if price_cents > 0:
                try:
                    from app.services.stripe_sync import create_stripe_product_for_tier
                    create_stripe_product_for_tier(db, new_tier, event)
                except Exception as e:
                    print(f"Stripe sync warning: {e}")
            return {
                "success": True,
                "action": "created",
                "tier": _tier_to_dict(new_tier),
                "event": event.name,
                "quantity": quantity,
            }

    elif name == "set_event_visibility":
        event_id = arguments.get("event_id")
        is_visible = arguments.get("is_visible")
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}
        event.is_visible = is_visible
        db.commit()
        return {
            "success": True,
            "event": event.name,
            "event_id": event.id,
            "is_visible": is_visible,
            "action": "made live" if is_visible else "hidden",
        }

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

        start_date_str = arguments.get("start_date")
        end_date_str = arguments.get("end_date")

        if start_date_str or end_date_str:
            # Date-filtered path: query actual Ticket records
            from sqlalchemy import func as sqlfunc

            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1) if end_date_str else None

            base_filter = [
                TicketTier.event_id == arguments["event_id"],
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            ]
            if start_dt:
                base_filter.append(Ticket.purchased_at >= start_dt)
            if end_dt:
                base_filter.append(Ticket.purchased_at < end_dt)

            tier_rows = (
                db.query(
                    TicketTier.id,
                    TicketTier.name,
                    TicketTier.price,
                    sqlfunc.count(Ticket.id).label("sold"),
                    sqlfunc.sum(
                        TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                    ).label("revenue"),
                )
                .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
                .filter(*base_filter)
                .group_by(TicketTier.id, TicketTier.name, TicketTier.price)
                .all()
            )

            checked_in = (
                db.query(sqlfunc.count(Ticket.id))
                .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
                .filter(
                    TicketTier.event_id == arguments["event_id"],
                    Ticket.status == TicketStatus.CHECKED_IN,
                    *([Ticket.purchased_at >= start_dt] if start_dt else []),
                    *([Ticket.purchased_at < end_dt] if end_dt else []),
                )
                .scalar() or 0
            )

            total_sold = sum(r.sold for r in tier_rows)
            total_revenue = sum(r.revenue or 0 for r in tier_rows)

            tiers_data = [
                {
                    "tier_id": r.id,
                    "tier_name": r.name,
                    "price_cents": r.price,
                    "quantity_sold": r.sold,
                    "revenue_cents": int(r.revenue or 0),
                }
                for r in tier_rows
            ]

            return {
                "event_id": event.id,
                "event_name": event.name,
                "date_range": {"start_date": start_date_str, "end_date": end_date_str},
                "total_tickets_sold": total_sold,
                "total_revenue_cents": int(total_revenue),
                "total_revenue_dollars": round(total_revenue / 100, 2),
                "tickets_checked_in": checked_in,
                "tiers": tiers_data,
            }

        # Original aggregate path (no date filter)
        total_sold = 0
        total_available = 0
        total_revenue = 0
        tiers_data = []
        checked_in = 0

        for tier in event.ticket_tiers:
            tier_revenue = tier.price * tier.quantity_sold
            total_sold += tier.quantity_sold
            total_available += tier.quantity_available
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
                "quantity_available": tier.quantity_available,
                "quantity_sold": tier.quantity_sold,
                "revenue_cents": tier_revenue,
                "checked_in": tier_checked_in,
            })

        return {
            "event_id": event.id,
            "event_name": event.name,
            "total_available": total_available,
            "total_tickets_sold": total_sold,
            "total_revenue_cents": total_revenue,
            "tickets_checked_in": checked_in,
            "tiers": tiers_data,
        }

    elif name == "get_all_sales":
        start_date_str = arguments.get("start_date")
        end_date_str = arguments.get("end_date")

        if start_date_str or end_date_str:
            # Date-filtered path: query actual Ticket records
            from sqlalchemy import func as sqlfunc

            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1) if end_date_str else None

            base_filter = [
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            ]
            if start_dt:
                base_filter.append(Ticket.purchased_at >= start_dt)
            if end_dt:
                base_filter.append(Ticket.purchased_at < end_dt)

            event_rows = (
                db.query(
                    Event.id,
                    Event.name,
                    Event.event_date,
                    sqlfunc.count(Ticket.id).label("sold"),
                    sqlfunc.sum(
                        TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                    ).label("revenue"),
                )
                .join(TicketTier, TicketTier.event_id == Event.id)
                .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
                .filter(*base_filter)
                .group_by(Event.id, Event.name, Event.event_date)
                .all()
            )

            grand_total_sold = sum(r.sold for r in event_rows)
            grand_total_revenue = sum(r.revenue or 0 for r in event_rows)

            events_data = [
                {
                    "event_id": r.id,
                    "event_name": r.name,
                    "event_date": r.event_date,
                    "tickets_sold": r.sold,
                    "revenue_cents": int(r.revenue or 0),
                }
                for r in event_rows
            ]

            return {
                "date_range": {"start_date": start_date_str, "end_date": end_date_str},
                "total_tickets_sold": grand_total_sold,
                "total_revenue_cents": int(grand_total_revenue),
                "total_revenue_dollars": round(grand_total_revenue / 100, 2),
                "events_with_sales": len(events_data),
                "events": events_data,
            }

        # Original aggregate path (no date filter)
        events = db.query(Event).options(joinedload(Event.ticket_tiers)).all()

        grand_total_sold = 0
        grand_total_revenue = 0
        grand_checked_in = 0
        events_data = []

        for event in events:
            event_sold = 0
            event_revenue = 0
            event_checked_in = 0

            for tier in event.ticket_tiers:
                event_sold += tier.quantity_sold
                event_revenue += tier.price * tier.quantity_sold
                event_checked_in += (
                    db.query(Ticket)
                    .filter(Ticket.ticket_tier_id == tier.id, Ticket.status == TicketStatus.CHECKED_IN)
                    .count()
                )

            grand_total_sold += event_sold
            grand_total_revenue += event_revenue
            grand_checked_in += event_checked_in

            if event_sold > 0:  # Only include events with sales
                events_data.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "event_date": event.event_date,
                    "tickets_sold": event_sold,
                    "revenue_cents": event_revenue,
                    "checked_in": event_checked_in,
                })

        return {
            "total_tickets_sold": grand_total_sold,
            "total_revenue_cents": grand_total_revenue,
            "total_revenue_dollars": grand_total_revenue / 100,
            "total_checked_in": grand_checked_in,
            "events_with_sales": len(events_data),
            "events": events_data,
        }

    elif name == "get_revenue_report":
        from sqlalchemy import func as sqlfunc

        start_date_str = arguments["start_date"]
        end_date_str = arguments.get("end_date")
        breakdown = arguments.get("breakdown", "daily")
        compare_previous = arguments.get("compare_previous", False)
        report_event_id = arguments.get("event_id")

        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        if end_date_str:
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
        else:
            end_dt = datetime.utcnow()
            end_date_str = datetime.utcnow().strftime("%Y-%m-%d")

        period_days = (end_dt - start_dt).days

        base_filter = [
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.purchased_at >= start_dt,
            Ticket.purchased_at < end_dt,
        ]
        if report_event_id:
            base_filter.append(TicketTier.event_id == report_event_id)

        # Totals
        total_query = (
            db.query(
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
                sqlfunc.sum(sqlfunc.coalesce(Ticket.discount_amount_cents, 0)).label("total_discounts"),
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .first()
        )

        total_tickets = total_query.tickets or 0
        total_revenue = int(total_query.revenue or 0)
        total_discounts = int(total_query.total_discounts or 0)

        # Top events by revenue
        top_events = (
            db.query(
                Event.id,
                Event.name,
                Event.event_date,
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
            )
            .join(TicketTier, TicketTier.event_id == Event.id)
            .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .group_by(Event.id, Event.name, Event.event_date)
            .order_by(sqlfunc.sum(TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)).desc())
            .limit(10)
            .all()
        )

        # Time breakdown
        if breakdown == "weekly":
            date_expr = sqlfunc.strftime("%Y-W%W", Ticket.purchased_at)
        else:
            date_expr = sqlfunc.date(Ticket.purchased_at)

        breakdown_rows = (
            db.query(
                date_expr.label("period"),
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )

        # Comparison period (optional)
        comparison = None
        if compare_previous:
            prev_start = start_dt - timedelta(days=period_days)
            prev_end = start_dt
            prev_filter = [
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                Ticket.purchased_at >= prev_start,
                Ticket.purchased_at < prev_end,
            ]
            if report_event_id:
                prev_filter.append(TicketTier.event_id == report_event_id)

            prev_query = (
                db.query(
                    sqlfunc.count(Ticket.id).label("tickets"),
                    sqlfunc.sum(
                        TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                    ).label("revenue"),
                )
                .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
                .filter(*prev_filter)
                .first()
            )
            prev_tickets = prev_query.tickets or 0
            prev_revenue = int(prev_query.revenue or 0)

            comparison = {
                "previous_period": {
                    "start_date": prev_start.strftime("%Y-%m-%d"),
                    "end_date": (prev_end - timedelta(days=1)).strftime("%Y-%m-%d"),
                },
                "previous_tickets": prev_tickets,
                "previous_revenue_cents": prev_revenue,
                "previous_revenue_dollars": round(prev_revenue / 100, 2),
                "ticket_change": total_tickets - prev_tickets,
                "revenue_change_cents": total_revenue - prev_revenue,
                "revenue_change_percent": round((total_revenue - prev_revenue) / prev_revenue * 100, 1) if prev_revenue > 0 else None,
            }

        report_result = {
            "report_period": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "days": period_days,
            },
            "total_tickets": total_tickets,
            "total_revenue_cents": total_revenue,
            "total_revenue_dollars": round(total_revenue / 100, 2),
            "total_discounts_cents": total_discounts,
            "average_ticket_revenue_cents": round(total_revenue / total_tickets) if total_tickets > 0 else 0,
            "top_events": [
                {
                    "event_id": r.id,
                    "event_name": r.name,
                    "event_date": r.event_date,
                    "tickets": r.tickets,
                    "revenue_cents": int(r.revenue or 0),
                    "revenue_dollars": round(int(r.revenue or 0) / 100, 2),
                }
                for r in top_events
            ],
            "breakdown": [
                {
                    "period": str(r.period),
                    "tickets": r.tickets,
                    "revenue_cents": int(r.revenue or 0),
                    "revenue_dollars": round(int(r.revenue or 0) / 100, 2),
                }
                for r in breakdown_rows
            ],
            "breakdown_type": breakdown,
        }
        if report_event_id:
            event = db.query(Event).filter(Event.id == report_event_id).first()
            report_result["event_id"] = report_event_id
            report_result["event_name"] = event.name if event else "Unknown"
        if comparison:
            report_result["comparison"] = comparison

        return report_result

    elif name == "refresh_dashboard":
        # This tool signals a refresh - the actual broadcast happens in http_server.py
        # We return data that will be broadcast via SSE
        refresh_type = arguments.get("type", "soft")
        message = arguments.get("message", "Dashboard refresh triggered")
        return {
            "success": True,
            "type": refresh_type,
            "message": message,
            "action": "refresh",
        }

    elif name == "sync_tiers_to_stripe":
        event_id = arguments.get("event_id")
        result = sync_existing_tiers_to_stripe(db, event_id)
        return result

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

        # Normalize phone number (add +1 for US)
        phone = normalize_phone(arguments.get("phone")) if arguments.get("phone") else None

        # Create new customer
        customer = EventGoer(
            name=arguments["name"],
            email=arguments["email"],
            phone=phone,
            email_opt_in=True,
            sms_opt_in=bool(phone),
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
            },
            "next_actions": ["search_events", "get_ticket_availability", "email_payment_link"],
        }

    elif name == "update_customer":
        customer = db.query(EventGoer).filter(EventGoer.id == arguments["customer_id"]).first()
        if not customer:
            return {"error": "Customer not found"}

        updates = []
        if arguments.get("name"):
            customer.name = arguments["name"]
            updates.append(f"name → {arguments['name']}")
        if arguments.get("email"):
            customer.email = arguments["email"]
            updates.append(f"email → {arguments['email']}")
        if arguments.get("phone"):
            customer.phone = normalize_phone(arguments["phone"])
            updates.append(f"phone → {customer.phone}")

        db.commit()
        db.refresh(customer)

        return {
            "success": True,
            "message": f"Updated {customer.name}: {', '.join(updates)}",
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

    elif name == "search_customers":
        query = db.query(EventGoer)
        if arguments.get("query"):
            query = query.filter(EventGoer.name.ilike(f"%{arguments['query'].strip()}%"))
        if arguments.get("marketing_opt_in") is not None:
            query = query.filter(EventGoer.marketing_opt_in == arguments["marketing_opt_in"])
        if arguments.get("is_vip") is not None:
            query = query.join(CustomerPreference).filter(CustomerPreference.is_vip == arguments["is_vip"])
        customers = query.order_by(EventGoer.created_at.desc()).limit(50).all()
        if not customers:
            return {"found": False, "message": "No customers match your search", "count": 0}
        return {
            "found": True,
            "count": len(customers),
            "customers": [
                {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "marketing_opt_in": c.marketing_opt_in}
                for c in customers
            ],
        }

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
        # Auto sold-out check
        if tier.quantity_sold >= tier.quantity_available:
            from app.models import TierStatus
            tier.status = TierStatus.SOLD_OUT
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
            "next_actions": ["send_sms_ticket", "send_purchase_email"],
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
            "next_actions": ["get_customer_profile", "add_customer_note"],
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

        # If no event specified, auto-detect today's event
        if not event_id:
            from datetime import date
            today = date.today().isoformat()
            todays_events = db.query(Event).filter(
                Event.event_date == today,
                Event.status == "scheduled"
            ).all()

            if len(todays_events) == 1:
                # One event today - use it automatically
                event_id = todays_events[0].id
            elif len(todays_events) > 1:
                # Multiple events today - ask which one
                return {
                    "success": False,
                    "message": f"Multiple events today. Please specify: {', '.join(e.name for e in todays_events)}",
                    "events": [{"id": e.id, "name": e.name, "time": e.event_time} for e in todays_events]
                }
            # If no events today, search all (might be pre-checking for tomorrow)

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

        # Filter by event if specified or auto-detected
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
            "next_actions": ["get_customer_profile", "add_customer_note"],
        }

    elif name == "check_out_by_name":
        guest_name = arguments["name"].strip().lower()
        event_id = arguments.get("event_id")

        # If no event specified, auto-detect today's event
        if not event_id:
            from datetime import date
            today = date.today().isoformat()
            todays_events = db.query(Event).filter(
                Event.event_date == today,
                Event.status == "scheduled"
            ).all()

            if len(todays_events) == 1:
                event_id = todays_events[0].id
            elif len(todays_events) > 1:
                return {
                    "success": False,
                    "message": f"Multiple events today. Please specify: {', '.join(e.name for e in todays_events)}",
                    "events": [{"id": e.id, "name": e.name, "time": e.event_time} for e in todays_events]
                }

        # Build query for checked-in tickets
        query = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
                joinedload(Ticket.event_goer),
            )
            .join(EventGoer)
            .join(TicketTier)
            .filter(Ticket.status == TicketStatus.CHECKED_IN)
        )

        if event_id:
            query = query.filter(TicketTier.event_id == event_id)

        tickets = query.all()
        matching_tickets = [
            t for t in tickets
            if guest_name in t.event_goer.name.lower()
        ]

        if not matching_tickets:
            return {
                "success": False,
                "message": f"No checked-in tickets found for '{arguments['name']}'.",
            }

        # Undo check-in - set back to PAID
        ticket = matching_tickets[0]
        ticket.status = TicketStatus.PAID
        db.commit()

        return {
            "success": True,
            "message": f"{ticket.event_goer.name} has been checked out.",
            "guest": {
                "name": ticket.event_goer.name,
                "email": ticket.event_goer.email,
            },
            "ticket": {
                "event": ticket.ticket_tier.event.name,
                "tier": ticket.ticket_tier.name,
                "status": "paid",
            },
        }

    elif name == "guest_list":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        query = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier),
                joinedload(Ticket.event_goer),
            )
            .join(TicketTier)
            .filter(TicketTier.event_id == event.id)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
        )

        status_filter = arguments.get("status", "all")
        if status_filter == "checked_in":
            query = query.filter(Ticket.status == TicketStatus.CHECKED_IN)
        elif status_filter == "not_checked_in":
            query = query.filter(Ticket.status == TicketStatus.PAID)

        tickets = query.all()

        guests = []
        for t in tickets:
            guests.append({
                "name": t.event_goer.name,
                "email": t.event_goer.email,
                "phone": t.event_goer.phone,
                "tier": t.ticket_tier.name,
                "status": t.status.value,
                "ticket_id": t.id,
                "qr_token": t.qr_code_token,
            })

        total = len(guests)
        checked_in = sum(1 for g in guests if g["status"] == "checked_in")

        response = {
            "event": event.name,
            "event_id": event.id,
            "total_guests": total,
            "checked_in": checked_in,
            "not_checked_in": total - checked_in,
            "guests": guests[:50],
        }
        if total > 50:
            response["note"] = f"Showing first 50 of {total} guests. Use find_guest to search by name."
        return response

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

    elif name == "configure_auto_reminder":
        from app.services.scheduler import schedule_auto_reminder, cancel_auto_reminder

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        enabled = arguments.get("enabled", True)
        hours_before = arguments.get("hours_before", 24)
        use_sms = arguments.get("use_sms", False)

        if not enabled or hours_before == 0:
            event.auto_reminder_hours = None
            event.auto_reminder_use_sms = False
            db.commit()
            cancel_result = cancel_auto_reminder(event.id)
            return {
                "event_id": event.id,
                "event_name": event.name,
                "auto_reminder": "disabled",
                "cancelled_job": cancel_result.get("cancelled", False),
            }
        else:
            event.auto_reminder_hours = hours_before
            event.auto_reminder_use_sms = use_sms
            db.commit()

            schedule_result = schedule_auto_reminder(
                event_id=event.id,
                event_date=event.event_date,
                event_time=event.event_time,
                hours_before=hours_before,
                use_sms=use_sms,
            )
            return {
                "event_id": event.id,
                "event_name": event.name,
                "auto_reminder": "enabled",
                "hours_before": hours_before,
                "use_sms": use_sms,
                "scheduled": schedule_result.get("scheduled", False),
                "reminder_time": schedule_result.get("reminder_time"),
            }

    elif name == "list_scheduled_reminders":
        from app.services.scheduler import get_scheduled_reminders, get_reminder_for_event

        event_id = arguments.get("event_id")

        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"error": "Event not found"}

            reminder = get_reminder_for_event(event_id)
            return {
                "event_id": event_id,
                "event_name": event.name,
                "event_date": event.event_date,
                "event_time": event.event_time,
                "auto_reminder_hours": getattr(event, "auto_reminder_hours", None),
                "auto_reminder_use_sms": getattr(event, "auto_reminder_use_sms", False),
                "has_scheduled_job": reminder is not None,
                "scheduled_time": reminder["scheduled_time"] if reminder else None,
            }
        else:
            reminders = get_scheduled_reminders()
            if reminders:
                event_ids = [r["event_id"] for r in reminders]
                events = db.query(Event).filter(Event.id.in_(event_ids)).all()
                event_map = {e.id: e for e in events}
                for r in reminders:
                    event = event_map.get(r["event_id"])
                    if event:
                        r["event_name"] = event.name
                        r["event_date"] = event.event_date
                        r["event_time"] = event.event_time

            return {
                "total_scheduled": len(reminders),
                "reminders": reminders,
            }

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

        # Cancel auto-reminder
        try:
            from app.services.scheduler import cancel_auto_reminder
            cancel_auto_reminder(arguments["event_id"])
        except Exception:
            pass

        return result

    elif name == "postpone_event":
        from app.services.notifications import send_event_postponement_notifications

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        # Save original date/time before updating
        original_date = event.event_date
        original_time = event.event_time

        # Update event status
        event.status = EventStatus.POSTPONED
        event.cancellation_reason = arguments.get("reason")

        # Update date/time if provided
        new_date = arguments.get("new_date")
        new_time = arguments.get("new_time")
        if new_date:
            event.event_date = new_date
        if new_time:
            event.event_time = new_time

        db.commit()

        channels = [NotificationChannel.EMAIL]
        if arguments.get("use_sms"):
            channels.append(NotificationChannel.SMS)

        result = send_event_postponement_notifications(
            db=db,
            event_id=arguments["event_id"],
            original_date=original_date,
            new_date=new_date,
            new_time=new_time,
            reason=arguments.get("reason"),
            channels=channels,
        )
        result["event_status"] = "postponed"
        result["original_date"] = original_date
        result["original_time"] = original_time
        if new_date:
            result["new_date"] = new_date
        if new_time:
            result["new_time"] = new_time

        # Reschedule or cancel auto-reminder
        if getattr(event, "auto_reminder_hours", None) is not None:
            if new_date or new_time:
                try:
                    from app.services.scheduler import schedule_auto_reminder
                    schedule_auto_reminder(event.id, event.event_date, event.event_time, event.auto_reminder_hours, getattr(event, "auto_reminder_use_sms", False))
                except Exception:
                    pass
            else:
                try:
                    from app.services.scheduler import cancel_auto_reminder
                    cancel_auto_reminder(event.id)
                except Exception:
                    pass

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

    # ============== Marketing Campaign Tools ==============
    elif name == "create_campaign":
        target_all = arguments.get("target_all", False)
        target_event_id = arguments.get("target_event_id")

        # Build segments from arguments
        segments = _build_segments(arguments)

        if not target_all and not target_event_id and not segments:
            return {"error": "Must specify targeting: target_all=true, target_event_id, or segment filters (target_vip, target_min_events, target_min_spent_cents, target_category_ids)"}

        if target_event_id:
            event = db.query(Event).filter(Event.id == target_event_id).first()
            if not event:
                return {"error": f"Event {target_event_id} not found"}

        # Validate category IDs exist
        if segments.get("category_ids"):
            for cat_id in segments["category_ids"]:
                cat = db.query(EventCategory).filter(EventCategory.id == cat_id).first()
                if not cat:
                    return {"error": f"Category {cat_id} not found. Use list_categories to see available categories."}

        campaign = MarketingCampaign(
            name=arguments["name"],
            subject=arguments["subject"],
            content=arguments["content"],
            target_all=target_all,
            target_event_id=target_event_id,
            target_segments=json.dumps(segments) if segments else None,
            status="draft",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        # Count potential recipients (uses same filtering as send_marketing_campaign)
        from app.services.notifications import send_marketing_campaign as _smc
        # Build the same query the service would use for an accurate count
        recipient_query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)
        if target_event_id:
            event_goer_ids = (
                db.query(Ticket.event_goer_id)
                .join(TicketTier)
                .filter(TicketTier.event_id == target_event_id)
                .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
                .distinct()
            )
            recipient_query = recipient_query.filter(EventGoer.id.in_(event_goer_ids))
        recipient_query = _apply_segment_filters(db, recipient_query, segments)
        potential_recipients = recipient_query.count()

        target_desc = _describe_campaign_target(target_all, target_event_id, segments)

        return {
            "success": True,
            "campaign_id": campaign.id,
            "name": campaign.name,
            "subject": campaign.subject,
            "status": campaign.status,
            "target": target_desc,
            "segment_description": _describe_segments(segments) if segments else None,
            "potential_recipients": potential_recipients,
            "message": f"Campaign '{campaign.name}' created as draft with {potential_recipients} potential recipients. Use send_campaign to send it.",
            "next_actions": ["send_campaign", "list_campaigns"],
        }

    elif name == "list_campaigns":
        query = db.query(MarketingCampaign)
        if arguments.get("status"):
            query = query.filter(MarketingCampaign.status == arguments["status"])
        campaigns = query.order_by(MarketingCampaign.created_at.desc()).all()

        results = []
        for c in campaigns:
            segs = {}
            if c.target_segments:
                try:
                    segs = json.loads(c.target_segments)
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append({
                "id": c.id,
                "name": c.name,
                "subject": c.subject,
                "status": c.status,
                "target": _describe_campaign_target(c.target_all, c.target_event_id, segs),
                "total_recipients": c.total_recipients,
                "sent_count": c.sent_count,
                "created_at": str(c.created_at),
                "sent_at": str(c.sent_at) if c.sent_at else None,
            })
        return results

    elif name == "update_campaign":
        campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == arguments["campaign_id"]).first()
        if not campaign:
            return {"error": "Campaign not found"}
        if campaign.status != "draft":
            return {"error": f"Campaign '{campaign.name}' is '{campaign.status}' and cannot be edited. Only draft campaigns can be updated."}

        if "name" in arguments:
            campaign.name = arguments["name"]
        if "subject" in arguments:
            campaign.subject = arguments["subject"]
        if "content" in arguments:
            campaign.content = arguments["content"]

        db.commit()
        db.refresh(campaign)

        return {
            "success": True,
            "campaign_id": campaign.id,
            "name": campaign.name,
            "subject": campaign.subject,
            "content": campaign.content[:100] + ("..." if len(campaign.content) > 100 else ""),
            "status": campaign.status,
            "message": f"Campaign '{campaign.name}' updated. Use send_campaign to send it.",
            "next_actions": ["send_campaign"],
        }

    elif name == "send_campaign":
        from app.services.notifications import send_marketing_campaign

        campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == arguments["campaign_id"]).first()
        if not campaign:
            return {"error": "Campaign not found"}
        if campaign.status == "sent":
            return {"error": f"Campaign '{campaign.name}' has already been sent"}
        if campaign.status == "sending":
            return {"error": f"Campaign '{campaign.name}' is currently being sent"}

        channels = []
        if arguments.get("use_email", True):
            channels.append(NotificationChannel.EMAIL)
        if arguments.get("use_sms", False):
            channels.append(NotificationChannel.SMS)

        if not channels:
            return {"error": "At least one channel (email or sms) must be enabled"}

        result = send_marketing_campaign(db=db, campaign_id=arguments["campaign_id"], channels=channels)
        return result

    elif name == "quick_send_campaign":
        from app.services.notifications import send_marketing_campaign

        target_all = arguments.get("target_all", False)
        target_event_id = arguments.get("target_event_id")

        # Build segments from arguments
        segments = _build_segments(arguments)

        if not target_all and not target_event_id and not segments:
            return {"error": "Must specify targeting: target_all=true, target_event_id, or segment filters (target_vip, target_min_events, target_min_spent_cents, target_category_ids)"}

        if target_event_id:
            event = db.query(Event).filter(Event.id == target_event_id).first()
            if not event:
                return {"error": f"Event {target_event_id} not found"}

        # Validate category IDs
        if segments.get("category_ids"):
            for cat_id in segments["category_ids"]:
                cat = db.query(EventCategory).filter(EventCategory.id == cat_id).first()
                if not cat:
                    return {"error": f"Category {cat_id} not found. Use list_categories to see available categories."}

        # Auto-generate name if not provided
        campaign_name = arguments.get("name")
        if not campaign_name:
            parts = []
            if target_event_id and event:
                parts.append(event.name)
            if segments:
                parts.append(_describe_segments(segments))
            campaign_name = f"Blast: {' - '.join(parts) if parts else 'All Users'} - {datetime.utcnow().strftime('%b %d')}"

        campaign = MarketingCampaign(
            name=campaign_name,
            subject=arguments["subject"],
            content=arguments["content"],
            target_all=target_all,
            target_event_id=target_event_id,
            target_segments=json.dumps(segments) if segments else None,
            status="draft",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        channels = []
        if arguments.get("use_email", True):
            channels.append(NotificationChannel.EMAIL)
        if arguments.get("use_sms", False):
            channels.append(NotificationChannel.SMS)

        result = send_marketing_campaign(db=db, campaign_id=campaign.id, channels=channels)
        result["campaign_name"] = campaign_name
        result["message"] = f"Campaign '{campaign_name}' created and sent to {result.get('total_recipients', 0)} recipients"
        return result

    elif name == "preview_audience":
        target_all = arguments.get("target_all", False)
        target_event_id = arguments.get("target_event_id")
        segments = _build_segments(arguments)

        query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)

        if target_event_id:
            event_goer_ids = (
                db.query(Ticket.event_goer_id)
                .join(TicketTier)
                .filter(TicketTier.event_id == target_event_id)
                .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
                .distinct()
            )
            query = query.filter(EventGoer.id.in_(event_goer_ids))

        if segments:
            query = _apply_segment_filters(db, query, segments)

        total = query.count()
        samples = query.limit(5).all()
        sample_names = [s.name for s in samples]
        sms_eligible = query.filter(
            EventGoer.sms_opt_in == True, EventGoer.phone.isnot(None)
        ).count()

        target_desc = _describe_campaign_target(target_all, target_event_id, segments)

        return {
            "total_recipients": total,
            "sms_eligible": sms_eligible,
            "email_eligible": total,
            "sample_names": sample_names,
            "target_description": target_desc,
            "message": f"{total} people match this audience ({sms_eligible} eligible for SMS). Sample: {', '.join(sample_names[:3]) if sample_names else 'none'}.",
        }

    # ============== Marketing List Tools ==============

    elif name == "create_marketing_list":
        list_name = arguments.get("name", "").strip()
        if not list_name:
            return {"error": "List name is required"}

        existing = db.query(MarketingList).filter(MarketingList.name == list_name).first()
        if existing:
            return {"error": f"A list named '{list_name}' already exists (ID: {existing.id})"}

        segments = _build_segments(arguments)
        if arguments.get("target_event_id"):
            event_ids = segments.get("event_ids", [])
            if arguments["target_event_id"] not in event_ids:
                event_ids.insert(0, arguments["target_event_id"])
            segments["event_ids"] = event_ids

        if not segments:
            return {"error": "At least one targeting filter is required (e.g. target_vip, target_event_ids, target_category_ids)"}

        ml = MarketingList(
            name=list_name,
            description=arguments.get("description", ""),
            segment_filters=json.dumps(segments),
        )
        db.add(ml)
        db.commit()
        db.refresh(ml)

        query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)
        query = _apply_segment_filters(db, query, segments)
        count = query.count()

        return {
            "success": True,
            "list_id": ml.id,
            "name": ml.name,
            "description": ml.description,
            "filters": segments,
            "member_count": count,
            "message": f"Created list '{ml.name}' with {count} members. Use send_to_marketing_list to send campaigns to this list.",
        }

    elif name == "list_marketing_lists":
        lists = db.query(MarketingList).order_by(MarketingList.created_at.desc()).all()

        results = []
        for ml in lists:
            segments = json.loads(ml.segment_filters) if ml.segment_filters else {}
            query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)
            query = _apply_segment_filters(db, query, segments)
            count = query.count()

            results.append({
                "id": ml.id,
                "name": ml.name,
                "description": ml.description,
                "member_count": count,
                "filters": _describe_segments(segments),
                "created_at": str(ml.created_at),
            })

        return {
            "success": True,
            "total_lists": len(results),
            "lists": results,
            "message": f"{len(results)} marketing list(s) found.",
        }

    elif name == "get_marketing_list":
        ml = db.query(MarketingList).filter(MarketingList.id == arguments["list_id"]).first()
        if not ml:
            return {"error": "Marketing list not found"}

        segments = json.loads(ml.segment_filters) if ml.segment_filters else {}
        query = db.query(EventGoer).filter(EventGoer.marketing_opt_in == True)
        query = _apply_segment_filters(db, query, segments)
        total = query.count()
        samples = query.limit(5).all()
        sms_eligible = query.filter(
            EventGoer.sms_opt_in == True, EventGoer.phone.isnot(None)
        ).count()

        return {
            "success": True,
            "list_id": ml.id,
            "name": ml.name,
            "description": ml.description,
            "filters": segments,
            "filters_description": _describe_segments(segments),
            "member_count": total,
            "sms_eligible": sms_eligible,
            "sample_names": [s.name for s in samples],
            "created_at": str(ml.created_at),
            "message": f"'{ml.name}' has {total} members ({sms_eligible} SMS-eligible).",
        }

    elif name == "delete_marketing_list":
        ml = None
        if arguments.get("list_id"):
            ml = db.query(MarketingList).filter(MarketingList.id == arguments["list_id"]).first()
        elif arguments.get("name"):
            ml = db.query(MarketingList).filter(MarketingList.name == arguments["name"]).first()

        if not ml:
            return {"error": "Marketing list not found"}

        name = ml.name
        db.delete(ml)
        db.commit()
        return {"success": True, "message": f"Deleted marketing list '{name}'."}

    elif name == "send_to_marketing_list":
        from app.services.notifications import send_marketing_campaign

        ml = db.query(MarketingList).filter(MarketingList.id == arguments["list_id"]).first()
        if not ml:
            return {"error": "Marketing list not found"}

        campaign = MarketingCampaign(
            name=f"Send to '{ml.name}' - {datetime.utcnow().strftime('%b %d')}",
            subject=arguments["subject"],
            content=arguments["content"],
            target_segments=ml.segment_filters,
            status="draft",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        channels = []
        if arguments.get("use_email", True):
            channels.append(NotificationChannel.EMAIL)
        if arguments.get("use_sms", False):
            channels.append(NotificationChannel.SMS)

        result = send_marketing_campaign(db=db, campaign_id=campaign.id, channels=channels)
        result["list_name"] = ml.name
        result["message"] = f"Sent to '{ml.name}' list — {result.get('total_recipients', 0)} recipients"
        return result

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

    elif name == "email_payment_link":
        import stripe
        import resend

        stripe.api_key = settings.stripe_secret_key

        event_id = arguments["event_id"]
        tier_id = arguments.get("tier_id")
        quantity = arguments.get("quantity", 1)
        customer_name = arguments.get("name", "").strip().lower()
        customer_email = arguments.get("email", "").strip().lower()

        actions = []

        # Step 1: Find customer
        customer = None
        if customer_email:
            customer = db.query(EventGoer).filter(EventGoer.email.ilike(customer_email)).first()
        if not customer and customer_name:
            customers = db.query(EventGoer).all()
            for c in customers:
                if customer_name in c.name.lower():
                    customer = c
                    break

        if not customer:
            return {"error": f"Customer '{customer_name or customer_email}' not found. Use register_customer first."}

        actions.append(f"Found: {customer.name} ({customer.email})")

        # Step 2: Get event and tier
        event = db.query(Event).options(joinedload(Event.venue), joinedload(Event.ticket_tiers)).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}

        # Get tier (use first if not specified)
        tier = None
        if tier_id:
            tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
        elif event.ticket_tiers:
            tier = event.ticket_tiers[0]

        if not tier:
            return {"error": "No ticket tier found"}

        # Step 3: Create Payment Link
        try:
            payment_link = stripe.PaymentLink.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": tier.price,
                        "product_data": {
                            "name": f"{event.name} - {tier.name}",
                            "description": f"{event.event_date} at {event.event_time} | {event.venue.name}",
                        },
                    },
                    "quantity": quantity,
                }],
                metadata={
                    "event_id": str(event_id),
                    "tier_id": str(tier.id),
                    "customer_id": str(customer.id),
                },
            )
            actions.append(f"Created payment link: {payment_link.url}")
        except stripe.error.StripeError as e:
            return {"error": f"Stripe error: {e}"}

        # Step 4: Format date
        from datetime import datetime as dt
        try:
            event_date_obj = dt.strptime(event.event_date, "%Y-%m-%d")
            friendly_date = event_date_obj.strftime("%A, %B %d, %Y")
        except:
            friendly_date = event.event_date

        total_display = f"${tier.price * quantity / 100:.2f}"

        # Step 5: Send email
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .header {{ background: linear-gradient(135deg, {settings.org_color} 0%, #000000 100%); padding: 40px 30px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 28px; }}
    .header p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0; }}
    .content {{ padding: 30px; }}
    .event-card {{ background: #f8f8f8; border-radius: 8px; padding: 20px; margin: 20px 0; }}
    .event-card h2 {{ margin: 0 0 15px; color: #333; }}
    .event-card p {{ margin: 5px 0; color: #666; }}
    .btn {{ display: inline-block; background: {settings.org_color}; color: #fff !important; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 18px; margin: 20px 0; }}
    .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; background: #f8f8f8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎟️ Your Tickets Await!</h1>
      <p>{settings.org_name}</p>
    </div>
    <div class="content">
      <p>Hey {customer.name.split()[0]},</p>
      <p>Your tickets are ready to purchase!</p>
      <div class="event-card">
        <h2>🏀 {event.name}</h2>
        <p>📅 {friendly_date} at {event.event_time}</p>
        <p>📍 {event.venue.name}</p>
        <p>🎫 {quantity}x {tier.name} — <strong>{total_display}</strong></p>
      </div>
      <center>
        <a href="{payment_link.url}" class="btn">Complete Purchase →</a>
      </center>
      <p style="color:#666; font-size:14px; margin-top:30px;">
        This is a secure Stripe checkout. Your payment info is never stored on our servers.
      </p>
    </div>
    <div class="footer">
      {settings.org_name} Ticket Office<br>
      {event.venue.name}, {event.venue.address}
    </div>
  </div>
</body>
</html>
"""

        if not settings.resend_api_key:
            return {"error": "Resend not configured", "payment_link": payment_link.url}

        resend.api_key = settings.resend_api_key
        try:
            resend.Emails.send({
                "from": f"{settings.org_name} Tickets <{settings.from_email}>",
                "to": [customer.email],
                "subject": f"🎟️ Your {event.name} Tickets",
                "html": html_content,
            })
            actions.append(f"Emailed to {customer.email}")
        except Exception as e:
            return {"error": f"Email failed: {e}", "payment_link": payment_link.url}

        return {
            "success": True,
            "customer": customer.name,
            "email": customer.email,
            "event": event.name,
            "tier": tier.name,
            "quantity": quantity,
            "total": total_display,
            "payment_link": payment_link.url,
            "actions": actions,
            "next_actions": ["add_customer_note", "get_customer_profile"],
        }

    elif name == "create_payment_link":
        import stripe
        stripe.api_key = settings.stripe_secret_key

        event_id = arguments["event_id"]
        tier_id = arguments["tier_id"]
        quantity = arguments.get("quantity", 1)

        # Get event and tier
        event = db.query(Event).options(joinedload(Event.venue)).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}

        tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
        if not tier:
            return {"error": "Ticket tier not found"}

        try:
            # Create Payment Link via Stripe API
            payment_link = stripe.PaymentLink.create(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": tier.price,
                        "product_data": {
                            "name": f"{event.name} - {tier.name}",
                            "description": f"{event.event_date} at {event.event_time} | {event.venue.name}",
                        },
                    },
                    "quantity": quantity,
                }],
                metadata={
                    "event_id": str(event_id),
                    "tier_id": str(tier_id),
                    "event_name": event.name,
                },
            )

            return {
                "success": True,
                "url": payment_link.url,
                "event": event.name,
                "tier": tier.name,
                "quantity": quantity,
                "total_cents": tier.price * quantity,
                "total_display": f"${tier.price * quantity / 100:.2f}",
            }
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}

    elif name == "send_purchase_email":
        import resend

        to_email = arguments["to_email"]
        name = arguments["name"]
        event_id = arguments["event_id"]
        tier_id = arguments.get("tier_id")
        quantity = arguments.get("quantity", 1)
        checkout_url = arguments.get("checkout_url")

        # Get event details
        event = (
            db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
            .filter(Event.id == event_id)
            .first()
        )
        if not event:
            return {"error": "Event not found"}

        # Get tier info
        tier = None
        if tier_id:
            tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

        tier_name = tier.name if tier else "General Admission"
        price_cents = (tier.price if tier else event.ticket_tiers[0].price) * quantity
        price_display = f"${price_cents / 100:.2f}"

        # Format date nicely
        from datetime import datetime as dt
        try:
            event_date_obj = dt.strptime(event.event_date, "%Y-%m-%d")
            friendly_date = event_date_obj.strftime("%A, %B %d, %Y")
        except:
            friendly_date = event.event_date

        # Build email HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .header {{ background: linear-gradient(135deg, {settings.org_color} 0%, #000000 100%); padding: 40px 30px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 28px; }}
    .header p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0; }}
    .content {{ padding: 30px; }}
    .event-card {{ background: #f8f8f8; border-radius: 8px; padding: 20px; margin: 20px 0; }}
    .event-card h2 {{ margin: 0 0 15px; color: #333; }}
    .event-card p {{ margin: 5px 0; color: #666; }}
    .btn {{ display: inline-block; background: {settings.org_color}; color: #fff !important; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 18px; margin: 20px 0; }}
    .btn:hover {{ opacity: 0.9; }}
    .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; background: #f8f8f8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎟️ Your Tickets Await!</h1>
      <p>{settings.org_name}</p>
    </div>
    <div class="content">
      <p>Hey {name},</p>
      <p>Your tickets are ready to purchase!</p>

      <div class="event-card">
        <h2>🏀 {event.name}</h2>
        <p>📅 {friendly_date} at {event.event_time}</p>
        <p>📍 {event.venue.name}</p>
        <p>🎫 {quantity}x {tier_name} — <strong>{price_display}</strong></p>
      </div>

      <center>
        <a href="{checkout_url}" class="btn">
          Complete Purchase →
        </a>
      </center>

      <p style="color:#666; font-size:14px; margin-top:30px;">
        This is a secure Stripe checkout. Your payment info is never stored on our servers.
      </p>
    </div>
    <div class="footer">
      {settings.org_name} Ticket Office<br>
      {event.venue.name}, {event.venue.address}
    </div>
  </div>
</body>
</html>
"""

        # Send email via Resend
        if not settings.resend_api_key:
            return {"error": "Resend API key not configured"}

        resend.api_key = settings.resend_api_key

        try:
            result = resend.Emails.send({
                "from": f"{settings.org_name} Tickets <{settings.from_email}>",
                "to": [to_email],
                "subject": f"🎟️ Your {event.name} Tickets",
                "html": html_content,
            })
            return {
                "success": True,
                "message": f"Email sent to {to_email}",
                "email_id": result.get("id"),
                "event": event.name,
                "checkout_url": checkout_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif name == "send_ticket_link":
        from app.services.sms import send_sms

        phone = normalize_phone(arguments["phone"])
        event_id = arguments["event_id"]
        tier_id = arguments.get("tier_id")
        customer_name = arguments.get("name", "").strip().lower()
        customer_email = arguments.get("email", "").strip().lower()

        actions_taken = []

        # Step 1: Find the customer
        customer = None
        if customer_email:
            customer = db.query(EventGoer).filter(EventGoer.email.ilike(customer_email)).first()
        if not customer and customer_name:
            # Search by name (partial match)
            customers = db.query(EventGoer).all()
            for c in customers:
                if customer_name in c.name.lower():
                    customer = c
                    break

        if not customer:
            return {
                "success": False,
                "error": f"Customer not found. Please provide name or email to find them.",
                "suggestion": "Use register_customer to create a new customer first."
            }

        actions_taken.append(f"Found customer: {customer.name} ({customer.email})")

        # Step 2: Check/update phone number
        old_phone = customer.phone
        if customer.phone != phone:
            customer.phone = phone
            customer.sms_opt_in = True
            db.commit()
            if old_phone:
                actions_taken.append(f"Updated phone from {old_phone} to {phone}")
            else:
                actions_taken.append(f"Added phone number: {phone}")
        else:
            actions_taken.append(f"Phone already set to {phone}")

        # Step 3: Get event info
        event = (
            db.query(Event)
            .options(joinedload(Event.venue), joinedload(Event.ticket_tiers))
            .filter(Event.id == event_id)
            .first()
        )
        if not event:
            return {"success": False, "error": "Event not found", "actions": actions_taken}

        # Step 4: Build purchase URL
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

        # Step 5: Send SMS
        message = (
            f"🎟️ {event.name}\n"
            f"📅 {event.event_date} at {event.event_time}\n"
            f"📍 {event.venue.name}\n"
            f"💰 Tickets {price_info}\n\n"
            f"Buy now: {purchase_url}"
        )

        sms_result = send_sms(to_phone=phone, message=message)

        if sms_result.get("success"):
            actions_taken.append(f"Sent purchase link via SMS to {phone}")
        else:
            actions_taken.append(f"Failed to send SMS: {sms_result.get('error', 'Unknown error')}")

        return {
            "success": sms_result.get("success", False),
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            },
            "event": event.name,
            "purchase_url": purchase_url,
            "actions": actions_taken,
            "message": "Purchase link sent!" if sms_result.get("success") else sms_result.get("error", "Failed to send SMS"),
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

    # ============== Ticket Download Tools ==============
    elif name in ("download_ticket_pdf", "download_wallet_pass", "send_ticket_pdf", "send_wallet_pass"):
        ticket = (
            db.query(Ticket)
            .options(
                joinedload(Ticket.ticket_tier).joinedload(TicketTier.event).joinedload(Event.venue),
                joinedload(Ticket.event_goer),
            )
            .filter(Ticket.id == arguments["ticket_id"])
            .first()
        )
        if not ticket:
            return {"error": "Ticket not found"}
        if ticket.status not in (TicketStatus.PAID, TicketStatus.CHECKED_IN):
            return {"error": f"Ticket is {ticket.status.value}, not downloadable"}
        if not ticket.qr_code_token:
            return {"error": "Ticket has no QR code"}

        settings = get_settings()
        base_url = settings.base_url
        event = ticket.ticket_tier.event
        venue = event.venue
        customer = ticket.event_goer

        pdf_url = f"{base_url}/api/tickets/{ticket.id}/pdf"
        wallet_url = f"{base_url}/api/tickets/{ticket.id}/wallet"

        if name == "download_ticket_pdf":
            return {
                "success": True,
                "ticket_id": ticket.id,
                "customer_name": customer.name,
                "event_name": event.name,
                "pdf_url": pdf_url,
                "message": f"PDF ticket ready for {customer.name}. Download: {pdf_url}",
            }

        elif name == "download_wallet_pass":
            from app.services.wallet_pass import is_wallet_configured
            return {
                "success": True,
                "ticket_id": ticket.id,
                "customer_name": customer.name,
                "event_name": event.name,
                "wallet_url": wallet_url,
                "wallet_configured": is_wallet_configured(),
                "message": f"Apple Wallet pass ready for {customer.name}. Download: {wallet_url}",
            }

        elif name == "send_ticket_pdf":
            if not customer.email:
                return {"error": f"{customer.name} has no email on file"}
            try:
                from app.services.email_service import send_email
                send_email(
                    to_email=customer.email,
                    subject=f"Your Ticket for {event.name} - PDF Download",
                    html_content=f"<p>Hi {customer.name},</p><p>Here's your ticket for <strong>{event.name}</strong>:</p><p><a href='{pdf_url}' style='display:inline-block;padding:12px 24px;background:#333;color:white;text-decoration:none;border-radius:6px;font-weight:600;'>Download PDF Ticket</a></p><p><a href='{wallet_url}' style='display:inline-block;padding:12px 24px;background:#000;color:white;text-decoration:none;border-radius:6px;font-weight:600;'>Add to Apple Wallet</a></p><p>See you at {venue.name}!</p>",
                )
            except Exception:
                pass
            return {
                "success": True,
                "ticket_id": ticket.id,
                "customer_name": customer.name,
                "email": customer.email,
                "event_name": event.name,
                "message": f"PDF ticket link emailed to {customer.name} at {customer.email}",
            }

        elif name == "send_wallet_pass":
            if not customer.email:
                return {"error": f"{customer.name} has no email on file"}
            try:
                from app.services.email_service import send_email
                send_email(
                    to_email=customer.email,
                    subject=f"Your Ticket for {event.name} - Apple Wallet",
                    html_content=f"<p>Hi {customer.name},</p><p>Add your ticket for <strong>{event.name}</strong> to Apple Wallet:</p><p><a href='{wallet_url}' style='display:inline-block;padding:12px 24px;background:#000;color:white;text-decoration:none;border-radius:6px;font-weight:600;'>Add to Apple Wallet</a></p><p><a href='{pdf_url}' style='display:inline-block;padding:12px 24px;background:#333;color:white;text-decoration:none;border-radius:6px;font-weight:600;margin-top:8px;'>Or Download PDF</a></p><p>See you at {venue.name}!</p>",
                )
            except Exception:
                pass
            return {
                "success": True,
                "ticket_id": ticket.id,
                "customer_name": customer.name,
                "email": customer.email,
                "event_name": event.name,
                "message": f"Apple Wallet pass link emailed to {customer.name} at {customer.email}",
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
            "next_actions": ["search_events", "email_payment_link", "add_customer_note"],
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

    # ============== Promo Code Tools ==============
    elif name == "create_promo_code":
        code_upper = arguments["code"].upper()
        existing = db.query(PromoCode).filter(PromoCode.code == code_upper).first()
        if existing:
            return {"error": f"Promo code '{code_upper}' already exists"}

        discount_type_str = arguments["discount_type"]
        discount_value = arguments["discount_value"]
        if discount_type_str == "percent" and not (1 <= discount_value <= 100):
            return {"error": "Percent discount must be between 1 and 100"}
        if discount_type_str == "fixed_cents" and discount_value <= 0:
            return {"error": "Fixed discount must be a positive number of cents"}

        event_id = arguments.get("event_id")
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"error": f"Event {event_id} not found"}

        valid_until = None
        if arguments.get("valid_until"):
            valid_until = datetime.fromisoformat(arguments["valid_until"])

        promo = PromoCode(
            code=code_upper,
            discount_type=DiscountType(discount_type_str),
            discount_value=discount_value,
            event_id=event_id,
            max_uses=arguments.get("max_uses"),
            valid_until=valid_until,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        discount_desc = f"{discount_value}%" if discount_type_str == "percent" else f"${discount_value / 100:.2f}"
        return {
            "success": True,
            "promo_code_id": promo.id,
            "code": promo.code,
            "discount": discount_desc,
            "discount_type": discount_type_str,
            "discount_value": discount_value,
            "event_id": event_id,
            "max_uses": promo.max_uses,
        }

    elif name == "list_promo_codes":
        query = db.query(PromoCode)
        if arguments.get("event_id"):
            query = query.filter(PromoCode.event_id == arguments["event_id"])
        if arguments.get("active_only", True):
            query = query.filter(PromoCode.is_active == True)
        promos = query.order_by(PromoCode.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "code": p.code,
                "discount_type": p.discount_type.value,
                "discount_value": p.discount_value,
                "discount": f"{p.discount_value}%" if p.discount_type == DiscountType.PERCENT else f"${p.discount_value / 100:.2f}",
                "is_active": p.is_active,
                "uses_count": p.uses_count,
                "max_uses": p.max_uses,
                "event_id": p.event_id,
                "valid_until": str(p.valid_until) if p.valid_until else None,
            }
            for p in promos
        ]

    elif name == "validate_promo_code":
        code_str = arguments["code"].upper()
        tier_id = arguments["ticket_tier_id"]
        promo = db.query(PromoCode).filter(PromoCode.code == code_str).first()
        if not promo:
            return {"valid": False, "message": "Promo code not found"}
        if not promo.is_active:
            return {"valid": False, "message": "Promo code is inactive"}
        tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
        if not tier:
            return {"valid": False, "message": "Ticket tier not found"}
        if promo.event_id and promo.event_id != tier.event_id:
            return {"valid": False, "message": "Promo code is not valid for this event"}
        now = datetime.utcnow()
        if promo.valid_until and now > promo.valid_until.replace(tzinfo=None):
            return {"valid": False, "message": "Promo code has expired"}
        if promo.max_uses and promo.uses_count >= promo.max_uses:
            return {"valid": False, "message": "Promo code usage limit reached"}

        original = tier.price
        if promo.discount_type == DiscountType.PERCENT:
            discount = int(original * promo.discount_value / 100)
        else:
            discount = min(promo.discount_value, original)
        discounted = max(original - discount, 0)

        return {
            "valid": True,
            "code": promo.code,
            "discount_type": promo.discount_type.value,
            "discount_value": promo.discount_value,
            "original_price_cents": original,
            "discount_amount_cents": discount,
            "discounted_price_cents": discounted,
            "message": f"Code '{promo.code}' is valid! ${discount / 100:.2f} off, final price ${discounted / 100:.2f}.",
        }

    elif name == "deactivate_promo_code":
        code_str = arguments.get("code", "").upper()
        promo = db.query(PromoCode).filter(PromoCode.code == code_str).first()
        if not promo:
            return {"error": "Promo code not found"}
        promo.is_active = False
        db.commit()
        return {
            "success": True,
            "code": promo.code,
            "message": f"Promo code '{promo.code}' has been deactivated.",
        }

    # ============== Analytics ==============
    elif name == "get_event_analytics":
        from app.models import PageView
        from sqlalchemy import func as sqlfunc

        days = arguments.get("days", 30)
        event_id = arguments.get("event_id")
        cutoff = datetime.utcnow() - timedelta(days=days)
        base_filter = [PageView.created_at >= cutoff]
        if event_id:
            base_filter.append(PageView.event_id == event_id)

        total_views = db.query(sqlfunc.count(PageView.id)).filter(*base_filter).scalar()
        unique_visitors = db.query(sqlfunc.count(sqlfunc.distinct(PageView.ip_hash))).filter(*base_filter).scalar()

        top_referrers = (
            db.query(PageView.referrer, sqlfunc.count(PageView.id).label("count"))
            .filter(*base_filter, PageView.referrer != None, PageView.referrer != "")
            .group_by(PageView.referrer)
            .order_by(sqlfunc.count(PageView.id).desc())
            .limit(5)
            .all()
        )

        utm_sources = (
            db.query(PageView.utm_source, sqlfunc.count(PageView.id).label("count"))
            .filter(*base_filter, PageView.utm_source != None)
            .group_by(PageView.utm_source)
            .order_by(sqlfunc.count(PageView.id).desc())
            .limit(5)
            .all()
        )

        result = {
            "period_days": days,
            "total_views": total_views,
            "unique_visitors": unique_visitors,
            "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
            "utm_sources": [{"source": s, "count": c} for s, c in utm_sources],
        }
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            result["event_id"] = event_id
            result["event_name"] = event.name if event else "Unknown"
        return result

    elif name == "get_conversion_analytics":
        from app.models import PageView
        from sqlalchemy import func as sqlfunc

        event_id = arguments["event_id"]
        days = arguments.get("days", 30)
        cutoff = datetime.utcnow() - timedelta(days=days)

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"error": "Event not found"}

        # Page views
        listing_views = db.query(sqlfunc.count(PageView.id)).filter(
            PageView.page == "listing", PageView.created_at >= cutoff
        ).scalar() or 0

        detail_views = db.query(sqlfunc.count(PageView.id)).filter(
            PageView.event_id == event_id, PageView.page == "detail",
            PageView.created_at >= cutoff
        ).scalar() or 0

        unique_detail_visitors = db.query(
            sqlfunc.count(sqlfunc.distinct(PageView.ip_hash))
        ).filter(
            PageView.event_id == event_id, PageView.page == "detail",
            PageView.created_at >= cutoff
        ).scalar() or 0

        # Purchases in period
        purchases = (
            db.query(sqlfunc.count(Ticket.id))
            .join(TicketTier)
            .filter(
                TicketTier.event_id == event_id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                Ticket.purchased_at >= cutoff,
            )
            .scalar() or 0
        )

        unique_buyers = (
            db.query(sqlfunc.count(sqlfunc.distinct(Ticket.event_goer_id)))
            .join(TicketTier)
            .filter(
                TicketTier.event_id == event_id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                Ticket.purchased_at >= cutoff,
            )
            .scalar() or 0
        )

        # Conversion rate
        conversion_rate = round((unique_buyers / unique_detail_visitors * 100), 1) if unique_detail_visitors > 0 else 0

        # UTM attribution for purchases
        utm_breakdown = (
            db.query(
                Ticket.utm_source,
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.count(sqlfunc.distinct(Ticket.event_goer_id)).label("buyers"),
            )
            .join(TicketTier)
            .filter(
                TicketTier.event_id == event_id,
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                Ticket.purchased_at >= cutoff,
                Ticket.utm_source != None,
            )
            .group_by(Ticket.utm_source)
            .order_by(sqlfunc.count(Ticket.id).desc())
            .limit(10)
            .all()
        )

        return {
            "event_id": event_id,
            "event_name": event.name,
            "period_days": days,
            "funnel": {
                "listing_views": listing_views,
                "detail_views": detail_views,
                "unique_detail_visitors": unique_detail_visitors,
                "purchases": purchases,
                "unique_buyers": unique_buyers,
            },
            "conversion_rate_percent": conversion_rate,
            "utm_attribution": [
                {"source": s or "direct", "tickets": t, "buyers": b}
                for s, t, b in utm_breakdown
            ],
        }

    elif name == "share_event_link":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        share_url = f"{settings.base_url}/events/{event.id}"
        recipient_name = arguments.get("recipient_name", "")
        custom_msg = arguments.get("message", "")
        to_email = arguments.get("to_email")
        to_phone = arguments.get("to_phone")

        if not to_email and not to_phone:
            return {"error": "Please provide an email address or phone number to send the link to"}

        results = {"event": event.name, "share_url": share_url}
        sent_via = []

        # Send via email
        if to_email:
            from app.services.email import _send_email
            greeting = f"Hi {recipient_name}," if recipient_name else "Hi there,"
            custom_line = f"<p>{custom_msg}</p>" if custom_msg else ""
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #111; color: #fff; border-radius: 12px; overflow: hidden;">
                <div style="background: {settings.org_color}; padding: 20px 24px;">
                    <h2 style="margin: 0; color: #fff;">{settings.org_name}</h2>
                </div>
                <div style="padding: 24px;">
                    <p>{greeting}</p>
                    {custom_line}
                    <h3 style="color: {settings.org_color}; margin: 16px 0 8px;">{event.name}</h3>
                    <p style="color: #ccc;">{event.event_date} at {event.event_time}</p>
                    <p style="color: #999;">{event.description[:200] + '...' if event.description and len(event.description) > 200 else event.description or ''}</p>
                    <a href="{share_url}" style="display: inline-block; margin-top: 16px; padding: 12px 28px; background: {settings.org_color}; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold;">
                        View Event & Get Tickets
                    </a>
                </div>
            </div>
            """
            success = _send_email(
                to_email=to_email,
                subject=f"Check out {event.name}! | {settings.org_name}",
                html_content=html,
            )
            results["email_sent"] = success
            if success:
                sent_via.append("email")

        # Send via SMS
        if to_phone:
            from app.services.sms import send_sms
            sms_body = f"Check out {event.name} on {event.event_date}!"
            if custom_msg:
                sms_body = f"{custom_msg}\n\n{event.name} — {event.event_date}"
            sms_body += f"\n\nView & get tickets: {share_url}"
            sms_result = send_sms(to_phone, sms_body)
            results["sms_sent"] = sms_result.get("success", False)
            if sms_result.get("success"):
                sent_via.append("SMS")

        results["sent_via"] = sent_via
        results["success"] = len(sent_via) > 0
        return results

    elif name == "send_admin_link":
        import secrets
        from app.models import AdminMagicLink

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        if not event.promoter_phone:
            return {"error": f"No promoter phone number on file for '{event.name}'. Set it first with update_event."}

        # Generate magic link token and persist to database
        token = secrets.token_urlsafe(32)
        magic_link = AdminMagicLink(
            event_id=event.id,
            token=token,
            phone=event.promoter_phone,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(magic_link)
        db.commit()

        # Also store in memory for backward compat during transition
        magic_link_tokens[token] = {
            "event_id": event.id,
            "phone": event.promoter_phone,
            "expires": datetime.utcnow() + timedelta(hours=1),
        }

        admin_url = f"{settings.base_url}/events/{event.id}/admin?token={token}"

        # Send SMS
        from app.services.sms import send_sms
        sms_body = f"Manage your event \"{event.name}\":\n\n{admin_url}\n\nThis link expires in 1 hour."
        sms_result = send_sms(event.promoter_phone, sms_body)

        phone_masked = "***" + event.promoter_phone[-4:] if len(event.promoter_phone) >= 4 else "***"

        return {
            "success": sms_result.get("success", False),
            "event": event.name,
            "event_id": event.id,
            "sent_to": phone_masked,
            "admin_url": admin_url,
            "expires_in": "1 hour",
            "sms_error": sms_result.get("error"),
        }

    # ============== Waitlist Tools ==============
    elif name == "get_waitlist":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        entries = (
            db.query(WaitlistEntry)
            .filter(WaitlistEntry.event_id == event.id)
            .order_by(WaitlistEntry.position.asc())
            .all()
        )

        return {
            "event": event.name,
            "event_id": event.id,
            "total": len(entries),
            "waiting": sum(1 for e in entries if e.status == WaitlistStatus.WAITING),
            "entries": [
                {
                    "position": e.position,
                    "name": e.name,
                    "email": e.email,
                    "phone": e.phone,
                    "preferred_channel": e.preferred_channel,
                    "status": e.status.value,
                    "created_at": str(e.created_at),
                }
                for e in entries
            ],
        }

    elif name == "notify_waitlist":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        count = arguments.get("count", 5)

        entries = (
            db.query(WaitlistEntry)
            .filter(
                WaitlistEntry.event_id == event.id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
            )
            .order_by(WaitlistEntry.position.asc())
            .limit(count)
            .all()
        )

        if not entries:
            return {"event": event.name, "notified": 0, "message": "No one is waiting on the waitlist."}

        notified = []
        from app.services.sms import send_sms

        for entry in entries:
            ticket_url = f"{settings.base_url}/events/{event.id}"
            if entry.preferred_channel == "sms" and entry.phone:
                msg = f"Great news! Tickets are now available for \"{event.name}\"! Grab yours: {ticket_url}"
                send_sms(entry.phone, msg)
            else:
                # For email channel, use SMS if phone available, otherwise just mark notified
                if entry.phone:
                    msg = f"Great news! Tickets are now available for \"{event.name}\"! Grab yours: {ticket_url}"
                    send_sms(entry.phone, msg)

            entry.status = WaitlistStatus.NOTIFIED
            entry.notified_at = datetime.utcnow()
            notified.append({"name": entry.name, "email": entry.email, "channel": entry.preferred_channel})

        db.commit()

        return {
            "event": event.name,
            "notified": len(notified),
            "people": notified,
            "message": f"Notified {len(notified)} {'person' if len(notified) == 1 else 'people'} from the waitlist.",
        }

    elif name == "remove_from_waitlist":
        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        email = arguments["email"].strip().lower()
        entry = db.query(WaitlistEntry).filter(
            WaitlistEntry.event_id == event.id,
            WaitlistEntry.email == email,
        ).first()

        if not entry:
            return {"error": f"No waitlist entry found for {email}"}

        entry.status = WaitlistStatus.CANCELLED
        db.commit()

        return {
            "event": event.name,
            "removed": email,
            "message": f"Removed {entry.name} ({email}) from the waitlist.",
        }

    # ============== Social Media Handlers (Postiz) ==============

    elif name == "list_social_integrations":
        from app.services.social_media import get_integrations

        result = get_integrations()
        if result["success"]:
            return {
                "success": True,
                "integrations": result["data"],
                "message": "Use the integration IDs when calling post_event_to_social or schedule_social_post.",
            }
        return result

    elif name == "post_event_to_social":
        from app.services.social_media import post_to_social

        event = db.query(Event).filter(Event.id == arguments["event_id"]).first()
        if not event:
            return {"error": "Event not found"}

        venue = db.query(Venue).filter(Venue.id == event.venue_id).first() if event.venue_id else None

        integration_ids = arguments["integration_ids"]
        custom_text = arguments.get("custom_text")
        image_urls = arguments.get("image_urls")

        if custom_text:
            text = custom_text
        else:
            # Auto-generate post from event details
            text = f"{event.name}"
            if event.event_date:
                try:
                    from datetime import datetime as dt
                    parsed = dt.strptime(event.event_date, "%Y-%m-%d")
                    text += f"\n{parsed.strftime('%A, %B %d')}"
                except ValueError:
                    text += f"\n{event.event_date}"
                if event.event_time:
                    text += f" at {event.event_time}"
            if venue:
                text += f"\n📍 {venue.name}"
            if event.description:
                desc = event.description[:150]
                if len(event.description) > 150:
                    desc += "..."
                text += f"\n\n{desc}"
            # UTM-tracked ticket link for attribution
            from urllib.parse import quote
            event_url = f"{settings.base_url}/events/{event.id}"
            slug = quote(event.name.lower().replace(" ", "_")[:50])
            utm = f"?utm_source=postiz&utm_medium=social&utm_campaign={slug}"
            text += f"\n\n🎟️ Tickets: {event_url}{utm}"

        if not image_urls and event.image_url:
            image_urls = [event.image_url]

        result = post_to_social(
            text=text,
            integration_ids=integration_ids,
            image_urls=image_urls,
        )

        if result["success"]:
            return {
                "success": True,
                "event_name": event.name,
                "integration_ids": integration_ids,
                "post_text": text,
                "data": result["data"],
                "message": f"Posted '{event.name}' to {len(integration_ids)} channel(s)",
            }
        return result

    elif name == "schedule_social_post":
        from app.services.social_media import post_to_social

        result = post_to_social(
            text=arguments["text"],
            integration_ids=arguments["integration_ids"],
            post_type="schedule",
            schedule_date=arguments["schedule_date"],
            image_urls=arguments.get("image_urls"),
        )

        if result["success"]:
            return {
                "success": True,
                "integration_ids": arguments["integration_ids"],
                "scheduled_for": arguments["schedule_date"],
                "data": result["data"],
                "message": f"Post scheduled for {arguments['schedule_date']} on {len(arguments['integration_ids'])} channel(s)",
            }
        return result

    elif name == "get_social_post_history":
        from app.services.social_media import get_post_history

        result = get_post_history(
            start_date=arguments.get("start_date"),
            end_date=arguments.get("end_date"),
        )
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "Retrieved social media post history",
            }
        return result

    elif name == "delete_social_post":
        from app.services.social_media import delete_social_post

        result = delete_social_post(arguments["post_id"])
        if result["success"]:
            return {
                "success": True,
                "post_id": arguments["post_id"],
                "data": result["data"],
                "message": f"Social media post {arguments['post_id']} deleted",
            }
        return result

    # ============== Revenue Report Tool ==============
    elif name == "get_revenue_report":
        from sqlalchemy import func as sqlfunc

        start_date_str = arguments["start_date"]
        end_date_str = arguments.get("end_date")
        breakdown = arguments.get("breakdown", "daily")
        compare_previous = arguments.get("compare_previous", False)
        event_id = arguments.get("event_id")

        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        if end_date_str:
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
        else:
            end_dt = datetime.utcnow()
            end_date_str = datetime.utcnow().strftime("%Y-%m-%d")

        period_days = (end_dt - start_dt).days

        # Base query filters
        base_filter = [
            Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
            Ticket.purchased_at >= start_dt,
            Ticket.purchased_at < end_dt,
        ]
        if event_id:
            base_filter.append(TicketTier.event_id == event_id)

        # Totals
        total_query = (
            db.query(
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
                sqlfunc.sum(sqlfunc.coalesce(Ticket.discount_amount_cents, 0)).label("total_discounts"),
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .first()
        )

        total_tickets = total_query.tickets or 0
        total_revenue = int(total_query.revenue or 0)
        total_discounts = int(total_query.total_discounts or 0)

        # Top events by revenue
        top_events = (
            db.query(
                Event.id,
                Event.name,
                Event.event_date,
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
            )
            .join(TicketTier, TicketTier.event_id == Event.id)
            .join(Ticket, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .group_by(Event.id, Event.name, Event.event_date)
            .order_by(sqlfunc.sum(TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)).desc())
            .limit(10)
            .all()
        )

        # Time breakdown (daily or weekly)
        if breakdown == "weekly":
            date_expr = sqlfunc.strftime("%Y-W%W", Ticket.purchased_at)
        else:
            date_expr = sqlfunc.date(Ticket.purchased_at)

        breakdown_rows = (
            db.query(
                date_expr.label("period"),
                sqlfunc.count(Ticket.id).label("tickets"),
                sqlfunc.sum(
                    TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                ).label("revenue"),
            )
            .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
            .filter(*base_filter)
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )

        # Optional comparison to previous period
        comparison = None
        if compare_previous and period_days > 0:
            prev_start = start_dt - timedelta(days=period_days)
            prev_end = start_dt
            prev_filter = [
                Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]),
                Ticket.purchased_at >= prev_start,
                Ticket.purchased_at < prev_end,
            ]
            if event_id:
                prev_filter.append(TicketTier.event_id == event_id)

            prev_query = (
                db.query(
                    sqlfunc.count(Ticket.id).label("tickets"),
                    sqlfunc.sum(
                        TicketTier.price - sqlfunc.coalesce(Ticket.discount_amount_cents, 0)
                    ).label("revenue"),
                )
                .join(TicketTier, Ticket.ticket_tier_id == TicketTier.id)
                .filter(*prev_filter)
                .first()
            )
            prev_tickets = prev_query.tickets or 0
            prev_revenue = int(prev_query.revenue or 0)

            comparison = {
                "previous_period": {
                    "start_date": prev_start.strftime("%Y-%m-%d"),
                    "end_date": (prev_end - timedelta(days=1)).strftime("%Y-%m-%d"),
                },
                "previous_tickets": prev_tickets,
                "previous_revenue_cents": prev_revenue,
                "previous_revenue_dollars": round(prev_revenue / 100, 2),
                "ticket_change": total_tickets - prev_tickets,
                "revenue_change_cents": total_revenue - prev_revenue,
                "revenue_change_percent": round((total_revenue - prev_revenue) / prev_revenue * 100, 1) if prev_revenue > 0 else None,
            }

        result = {
            "report_period": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "days": period_days,
            },
            "total_tickets": total_tickets,
            "total_revenue_cents": total_revenue,
            "total_revenue_dollars": round(total_revenue / 100, 2),
            "total_discounts_cents": total_discounts,
            "average_ticket_revenue_cents": round(total_revenue / total_tickets) if total_tickets > 0 else 0,
            "top_events": [
                {
                    "event_id": r.id,
                    "event_name": r.name,
                    "event_date": r.event_date,
                    "tickets": r.tickets,
                    "revenue_cents": int(r.revenue or 0),
                    "revenue_dollars": round(int(r.revenue or 0) / 100, 2),
                }
                for r in top_events
            ],
            "breakdown": [
                {
                    "period": str(r.period),
                    "tickets": r.tickets,
                    "revenue_cents": int(r.revenue or 0),
                    "revenue_dollars": round(int(r.revenue or 0) / 100, 2),
                }
                for r in breakdown_rows
            ],
            "breakdown_type": breakdown,
        }
        if event_id:
            event = db.query(Event).filter(Event.id == event_id).first()
            result["event_id"] = event_id
            result["event_name"] = event.name if event else "Unknown"
        if comparison:
            result["comparison"] = comparison

        return result

    # ============== Refund Tool ==============
    elif name == "refund_ticket":
        import stripe
        from app.config import get_settings

        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key

        ticket_id = arguments.get("ticket_id")
        customer_name = arguments.get("customer_name")
        event_id = arguments.get("event_id")
        notify_customer = arguments.get("notify_customer", True)
        reason = arguments.get("reason", "")

        if not ticket_id and not customer_name:
            return {"error": "Provide either ticket_id or customer_name to identify which ticket(s) to refund."}

        # Resolve tickets
        tickets_to_refund = []

        if ticket_id:
            ticket = (
                db.query(Ticket)
                .options(
                    joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
                    joinedload(Ticket.event_goer),
                )
                .filter(Ticket.id == ticket_id)
                .first()
            )
            if not ticket:
                return {"error": f"Ticket {ticket_id} not found"}
            tickets_to_refund = [ticket]
        else:
            # Find by customer name
            query = (
                db.query(Ticket)
                .options(
                    joinedload(Ticket.ticket_tier).joinedload(TicketTier.event),
                    joinedload(Ticket.event_goer),
                )
                .join(EventGoer, Ticket.event_goer_id == EventGoer.id)
                .filter(EventGoer.name.ilike(f"%{customer_name}%"))
                .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            )
            if event_id:
                query = query.join(TicketTier, Ticket.ticket_tier_id == TicketTier.id).filter(TicketTier.event_id == event_id)
            tickets_to_refund = query.all()

            if not tickets_to_refund:
                return {"error": f"No refundable tickets found for '{customer_name}'" + (f" at event {event_id}" if event_id else "")}

        # Process refunds
        refunded = []
        skipped = []
        errors = []
        refund_total_cents = 0
        stripe_refunds_created = {}  # track payment_intent → refund to avoid duplicates

        for ticket in tickets_to_refund:
            # Skip already refunded/cancelled
            if ticket.status in (TicketStatus.REFUNDED, TicketStatus.CANCELLED):
                skipped.append({"ticket_id": ticket.id, "reason": f"Already {ticket.status.value}"})
                continue

            was_checked_in = ticket.status == TicketStatus.CHECKED_IN
            tier_price = ticket.ticket_tier.price if ticket.ticket_tier else 0
            discount = ticket.discount_amount_cents or 0
            ticket_revenue = tier_price - discount

            # Call Stripe if there's a payment intent and we haven't already refunded it
            stripe_refund_id = None
            if ticket.stripe_payment_intent_id:
                pi = ticket.stripe_payment_intent_id
                if pi not in stripe_refunds_created:
                    try:
                        refund = stripe.Refund.create(payment_intent=pi)
                        stripe_refund_id = refund.id
                        stripe_refunds_created[pi] = refund.id
                    except stripe.error.InvalidRequestError as e:
                        if "already been refunded" in str(e).lower() or "has already been reversed" in str(e).lower():
                            stripe_refunds_created[pi] = "already_refunded"
                            stripe_refund_id = "already_refunded"
                        else:
                            errors.append({"ticket_id": ticket.id, "error": str(e)})
                            continue
                    except Exception as e:
                        errors.append({"ticket_id": ticket.id, "error": str(e)})
                        continue
                else:
                    stripe_refund_id = stripe_refunds_created[pi]

            # Update local DB
            ticket.status = TicketStatus.REFUNDED
            if ticket.ticket_tier:
                ticket.ticket_tier.quantity_sold = max(0, ticket.ticket_tier.quantity_sold - 1)

            refund_total_cents += ticket_revenue
            refunded.append({
                "ticket_id": ticket.id,
                "customer_name": ticket.event_goer.name if ticket.event_goer else "Unknown",
                "event_name": ticket.ticket_tier.event.name if ticket.ticket_tier and ticket.ticket_tier.event else "Unknown",
                "amount_cents": ticket_revenue,
                "stripe_refund_id": stripe_refund_id,
                "was_checked_in": was_checked_in,
            })

        db.commit()

        # Auto-notify waitlist for freed-up tickets
        event_ids_affected = set()
        for r in refunded:
            for ticket in tickets_to_refund:
                if ticket.id == r["ticket_id"] and ticket.ticket_tier:
                    event_ids_affected.add(ticket.ticket_tier.event_id)

        for eid in event_ids_affected:
            count_for_event = sum(1 for r in refunded for t in tickets_to_refund if t.id == r["ticket_id"] and t.ticket_tier and t.ticket_tier.event_id == eid)
            try:
                from app.routers.payments import _auto_notify_waitlist
                _auto_notify_waitlist(eid, count_for_event, db)
            except Exception:
                pass  # Don't fail refund if waitlist notification fails

        # Notify customer
        if notify_customer and refunded:
            customer = tickets_to_refund[0].event_goer if tickets_to_refund else None
            if customer:
                refund_dollars = refund_total_cents / 100
                event_names = list(set(r["event_name"] for r in refunded))
                events_str = ", ".join(event_names)

                # SMS notification
                if customer.phone:
                    try:
                        from app.services.sms import send_sms
                        msg = f"Your refund of ${refund_dollars:.2f} for {events_str} has been processed. It may take 5-10 business days to appear on your statement."
                        send_sms(customer.phone, msg)
                    except Exception:
                        pass

                # Email notification
                if customer.email:
                    try:
                        from app.services.email_service import send_email
                        send_email(
                            to_email=customer.email,
                            subject=f"Refund Confirmation - {events_str}",
                            html_content=f"<p>Hi {customer.name},</p><p>Your refund of <strong>${refund_dollars:.2f}</strong> for {events_str} has been processed.</p><p>{f'Reason: {reason}' if reason else ''}</p><p>It may take 5-10 business days to appear on your statement.</p>",
                        )
                    except Exception:
                        pass

        return {
            "success": True,
            "refunded_count": len(refunded),
            "refund_total_cents": refund_total_cents,
            "refund_total_dollars": round(refund_total_cents / 100, 2),
            "refunded": refunded,
            "skipped": skipped,
            "errors": errors,
            "reason": reason,
        }

    # ============== Predictive Analytics Tools ==============
    elif name == "predict_demand":
        from app.services.analytics_engine import predict_demand

        result = predict_demand(db, arguments["event_id"])
        return result

    elif name == "get_pricing_suggestions":
        from app.services.analytics_engine import get_pricing_suggestions

        result = get_pricing_suggestions(db, arguments["event_id"])
        return result

    elif name == "predict_churn":
        from app.services.analytics_engine import predict_churn

        result = predict_churn(
            db,
            min_days_inactive=arguments.get("min_days_inactive", 30),
            limit=arguments.get("limit", 50),
        )
        return result

    elif name == "get_customer_segments":
        from app.services.analytics_engine import get_customer_segments

        result = get_customer_segments(db)
        return result

    elif name == "recommend_events":
        from app.services.analytics_engine import recommend_events

        result = recommend_events(
            db,
            customer_id=arguments.get("customer_id"),
            customer_email=arguments.get("customer_email"),
            limit=arguments.get("limit", 5),
        )
        return result

    elif name == "get_trending_events":
        from app.services.analytics_engine import get_trending_events

        result = get_trending_events(
            db,
            days=arguments.get("days", 7),
            limit=arguments.get("limit", 10),
        )
        return result

    # ============== Automation Tools ==============
    elif name == "get_abandoned_carts":
        from app.services.cart_recovery import check_abandoned_carts

        result = check_abandoned_carts(db)
        return result

    elif name == "send_cart_recovery":
        from app.services.cart_recovery import send_cart_recovery

        result = send_cart_recovery(db, email=arguments.get("email"))
        return result

    elif name == "list_auto_triggers":
        from app.services.auto_triggers import list_triggers

        result = list_triggers(db)
        return result

    elif name == "create_auto_trigger":
        from app.services.auto_triggers import create_trigger

        result = create_trigger(
            db,
            name=arguments["name"],
            trigger_type=arguments["trigger_type"],
            action=arguments["action"],
            event_id=arguments.get("event_id"),
            threshold_value=arguments.get("threshold_value"),
            threshold_days=arguments.get("threshold_days"),
            action_config=arguments.get("action_config"),
        )
        return result

    elif name == "delete_auto_trigger":
        from app.services.auto_triggers import delete_trigger

        result = delete_trigger(db, arguments["trigger_id"])
        return result

    elif name == "get_trigger_history":
        from app.services.auto_triggers import get_trigger_history

        result = get_trigger_history(db, arguments["trigger_id"])
        return result

    elif name == "get_revenue_forecast":
        from app.services.analytics_engine import forecast_revenue

        result = forecast_revenue(
            db,
            time_horizon_days=arguments.get("time_horizon_days", 90),
        )
        return result

    elif name == "get_survey_results":
        from app.services.surveys import get_survey_results

        result = get_survey_results(db, event_id=arguments.get("event_id"))
        return result

    elif name == "send_event_survey":
        from app.services.surveys import send_event_survey

        result = send_event_survey(db, arguments["event_id"])
        return result

    # ============== Knowledge Base (RAG) Tools ==============

    elif name == "search_knowledge_base":
        from app.services.rag import search as rag_search

        results = rag_search(
            query=arguments["query"],
            db=db,
            venue_id=arguments.get("venue_id"),
            event_id=arguments.get("event_id"),
            limit=5,
        )
        if not results:
            return {"results": [], "message": "No matching knowledge base entries found."}
        return {"results": results}

    elif name == "upload_knowledge":
        from app.services.rag import ingest_text
        from app.models import KnowledgeDocument

        doc = KnowledgeDocument(
            title=arguments["title"],
            venue_id=arguments.get("venue_id"),
            event_id=arguments.get("event_id"),
            content_type="paste",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        chunk_count = ingest_text(arguments["content"], doc.id, db)
        return {
            "success": True,
            "document_id": doc.id,
            "title": doc.title,
            "chunks_created": chunk_count,
        }

    return {"error": f"Unknown tool: {name}"}


# ============== Helper Functions ==============


def _build_segments(arguments: dict) -> dict:
    """Extract segment targeting params from MCP tool arguments into a JSON-serializable dict."""
    segments = {}
    if arguments.get("target_vip"):
        segments["is_vip"] = True
    if arguments.get("target_vip_tier"):
        segments["vip_tier"] = arguments["target_vip_tier"]
    if arguments.get("target_min_events"):
        segments["min_events"] = arguments["target_min_events"]
    if arguments.get("target_min_spent_cents"):
        segments["min_spent_cents"] = arguments["target_min_spent_cents"]
    if arguments.get("target_category_ids"):
        segments["category_ids"] = arguments["target_category_ids"]
    if arguments.get("target_event_ids"):
        segments["event_ids"] = arguments["target_event_ids"]
    if arguments.get("target_series_id"):
        segments["series_id"] = arguments["target_series_id"]
    if arguments.get("target_exclude_event_ids"):
        segments["exclude_event_ids"] = arguments["target_exclude_event_ids"]
    if arguments.get("target_days_since_last_event"):
        segments["days_since_last_event"] = arguments["target_days_since_last_event"]
    if arguments.get("target_attended_since_days"):
        segments["attended_since_days"] = arguments["target_attended_since_days"]
    return segments


def _describe_segments(segments: dict) -> str:
    """Return a human-readable description of segment filters."""
    parts = []
    if segments.get("is_vip"):
        tier_label = f" ({segments['vip_tier']})" if segments.get("vip_tier") else ""
        parts.append(f"VIPs{tier_label}")
    if segments.get("min_events"):
        parts.append(f"{segments['min_events']}+ events attended")
    if segments.get("min_spent_cents"):
        parts.append(f"${segments['min_spent_cents'] / 100:.0f}+ spent")
    if segments.get("category_ids"):
        parts.append(f"categories {segments['category_ids']}")
    if segments.get("event_ids"):
        parts.append(f"attended events {segments['event_ids']}")
    if segments.get("series_id"):
        parts.append(f"series {segments['series_id'][:8]}...")
    if segments.get("exclude_event_ids"):
        parts.append(f"excluding events {segments['exclude_event_ids']}")
    if segments.get("days_since_last_event"):
        parts.append(f"inactive {segments['days_since_last_event']}+ days")
    if segments.get("attended_since_days"):
        parts.append(f"active in last {segments['attended_since_days']} days")
    return ", ".join(parts)


def _describe_campaign_target(target_all: bool, target_event_id, segments: dict) -> str:
    """Return a human-readable target description for a campaign."""
    parts = []
    if target_all:
        parts.append("all opted-in")
    if target_event_id:
        parts.append(f"event #{target_event_id}")
    seg_desc = _describe_segments(segments) if segments else ""
    if seg_desc:
        parts.append(seg_desc)
    return " + ".join(parts) if parts else "no target"


def _apply_segment_filters(db, query, segments: dict):
    """Apply segment filters to an EventGoer query. Mirrors the logic in send_marketing_campaign()."""
    from sqlalchemy import func

    if segments.get("is_vip"):
        vip_goer_ids = db.query(CustomerPreference.event_goer_id).filter(CustomerPreference.is_vip == True)
        if segments.get("vip_tier"):
            vip_goer_ids = vip_goer_ids.filter(CustomerPreference.vip_tier == segments["vip_tier"])
        query = query.filter(EventGoer.id.in_(vip_goer_ids))

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

    if segments.get("category_ids"):
        category_ids = segments["category_ids"]
        from app.models import event_category_link
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

    # Multi-event targeting (attended ANY of these events)
    if segments.get("event_ids"):
        multi_event_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .filter(TicketTier.event_id.in_(segments["event_ids"]))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(multi_event_goer_ids))

    # Series targeting (all events sharing a series_id)
    if segments.get("series_id"):
        series_event_ids = db.query(Event.id).filter(Event.series_id == segments["series_id"])
        series_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .filter(TicketTier.event_id.in_(series_event_ids))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(series_goer_ids))

    # Exclude event filter (NOT attended these events)
    if segments.get("exclude_event_ids"):
        excluded_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .filter(TicketTier.event_id.in_(segments["exclude_event_ids"]))
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .distinct()
        )
        query = query.filter(~EventGoer.id.in_(excluded_goer_ids))

    # Lapsed customers (last purchase > N days ago)
    if segments.get("days_since_last_event"):
        from datetime import datetime as dt, timedelta, timezone
        cutoff = dt.now(timezone.utc) - timedelta(days=int(segments["days_since_last_event"]))
        last_purchase_subq = (
            db.query(
                Ticket.event_goer_id,
                func.max(Ticket.purchased_at).label("last_purchase")
            )
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .group_by(Ticket.event_goer_id)
            .having(func.max(Ticket.purchased_at) < cutoff)
            .subquery()
        )
        query = query.filter(EventGoer.id.in_(db.query(last_purchase_subq.c.event_goer_id)))

    # Recently active (attended within last N days)
    if segments.get("attended_since_days"):
        from datetime import datetime as dt, timedelta, timezone
        since_cutoff = dt.now(timezone.utc) - timedelta(days=int(segments["attended_since_days"]))
        recent_goer_ids = (
            db.query(Ticket.event_goer_id)
            .join(TicketTier)
            .join(Event, TicketTier.event_id == Event.id)
            .filter(Ticket.status.in_([TicketStatus.PAID, TicketStatus.CHECKED_IN]))
            .filter(Event.event_date >= since_cutoff.strftime("%Y-%m-%d"))
            .distinct()
        )
        query = query.filter(EventGoer.id.in_(recent_goer_ids))

    return query


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
        "doors_open_time": getattr(event, 'doors_open_time', None),
        "status": event.status.value if event.status else "scheduled",
        "is_visible": getattr(event, 'is_visible', True),
        "promoter_phone": getattr(event, 'promoter_phone', None),
        "promoter_name": getattr(event, 'promoter_name', None),
        "series_id": getattr(event, 'series_id', None),
        "post_event_video_url": getattr(event, 'post_event_video_url', None),
        "auto_reminder_hours": getattr(event, 'auto_reminder_hours', None),
        "auto_reminder_use_sms": getattr(event, 'auto_reminder_use_sms', False),
        "created_at": event.created_at,
    }
    # Include venue info if loaded
    if event.venue:
        result["venue_name"] = event.venue.name
        result["venue_address"] = event.venue.address
    # Include categories if loaded
    if hasattr(event, 'categories') and event.categories:
        result["categories"] = [{"id": c.id, "name": c.name, "color": c.color} for c in event.categories]
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
        "status": tier.status.value if tier.status else "active",
        "stripe_product_id": tier.stripe_product_id,
        "stripe_price_id": tier.stripe_price_id,
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
