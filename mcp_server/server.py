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
    MarketingCampaign,
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
                },
                "required": ["name"],
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
            name="get_all_sales",
            description="Get total sales across all events",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
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
        # ============== Marketing Campaign Tools ==============
        Tool(
            name="create_campaign",
            description="Create a marketing campaign as a draft. Use send_campaign to send it, or use quick_send_campaign for one-step create+send.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name (internal reference)"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "content": {"type": "string", "description": "Message content (used for both email body and SMS)"},
                    "target_all": {"type": "boolean", "description": "True to target ALL marketing opted-in users (default false)"},
                    "target_event_id": {"type": "integer", "description": "Target attendees of a specific event who are marketing opted-in"},
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
            description="One-step: create AND immediately send a marketing blast. Use when someone says 'send an email to all Jazz Night attendees' or 'blast all customers about our sale'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name (auto-generated if not provided)"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "content": {"type": "string", "description": "Message content"},
                    "target_all": {"type": "boolean", "description": "True to send to ALL marketing opted-in users"},
                    "target_event_id": {"type": "integer", "description": "Send to attendees of a specific event only"},
                    "use_email": {"type": "boolean", "description": "Send via email (default true)"},
                    "use_sms": {"type": "boolean", "description": "Also send via SMS (default false)"},
                },
                "required": ["subject", "content"],
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
                    "description": "Send promotional emails/SMS blasts to opted-in customers",
                    "steps": [
                        "1. For quick blasts: use quick_send_campaign (creates + sends in one step)",
                        "2. For planned campaigns: create_campaign first, then send_campaign",
                        "3. Target by specific event (target_event_id) or all opted-in users (target_all=true)",
                        "4. Only recipients with marketing_opt_in=True will receive messages",
                        "5. SMS only goes to recipients with sms_opt_in=True and a phone number",
                    ],
                    "tools": {
                        "quick_send_campaign": "One step: creates + sends. Use when user says 'send email to all Jazz Night attendees'.",
                        "create_campaign": "Creates a draft campaign for review before sending.",
                        "send_campaign": "Sends an existing draft campaign.",
                        "list_campaigns": "View all campaigns and their send status.",
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
        return [{"id": c.id, "name": c.name, "description": c.description, "color": c.color} for c in categories]

    elif name == "create_category":
        existing = db.query(EventCategory).filter(EventCategory.name == arguments["name"]).first()
        if existing:
            return {"error": f"Category '{arguments['name']}' already exists"}
        category = EventCategory(
            name=arguments["name"],
            description=arguments.get("description"),
            color=arguments.get("color"),
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return {"id": category.id, "name": category.name, "description": category.description, "color": category.color}

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
        if "image_url" in arguments:
            event.image_url = arguments["image_url"]
        if "promo_video_url" in arguments:
            event.promo_video_url = arguments["promo_video_url"]
        if "category_ids" in arguments:
            categories = db.query(EventCategory).filter(EventCategory.id.in_(arguments["category_ids"])).all()
            event.categories = categories
        db.commit()
        db.refresh(event)
        return _event_to_dict(event)

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
            "next_actions": ["get_customer_profile", "add_customer_note"],
        }

    elif name == "check_out_by_name":
        guest_name = arguments["name"].strip().lower()
        event_id = arguments.get("event_id")

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

    # ============== Marketing Campaign Tools ==============
    elif name == "create_campaign":
        target_all = arguments.get("target_all", False)
        target_event_id = arguments.get("target_event_id")

        if not target_all and not target_event_id:
            return {"error": "Must specify either target_all=true or target_event_id. Who should receive this campaign?"}

        if target_event_id:
            event = db.query(Event).filter(Event.id == target_event_id).first()
            if not event:
                return {"error": f"Event {target_event_id} not found"}

        campaign = MarketingCampaign(
            name=arguments["name"],
            subject=arguments["subject"],
            content=arguments["content"],
            target_all=target_all,
            target_event_id=target_event_id,
            status="draft",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        # Count potential recipients for preview
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
        potential_recipients = recipient_query.count()

        return {
            "success": True,
            "campaign_id": campaign.id,
            "name": campaign.name,
            "subject": campaign.subject,
            "status": campaign.status,
            "target": "all opted-in users" if target_all else f"event #{target_event_id} attendees",
            "potential_recipients": potential_recipients,
            "message": f"Campaign '{campaign.name}' created as draft with {potential_recipients} potential recipients. Use send_campaign to send it.",
            "next_actions": ["send_campaign", "list_campaigns"],
        }

    elif name == "list_campaigns":
        query = db.query(MarketingCampaign)
        if arguments.get("status"):
            query = query.filter(MarketingCampaign.status == arguments["status"])
        campaigns = query.order_by(MarketingCampaign.created_at.desc()).all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "subject": c.subject,
                "status": c.status,
                "target": "all opted-in" if c.target_all else f"event #{c.target_event_id}",
                "total_recipients": c.total_recipients,
                "sent_count": c.sent_count,
                "created_at": str(c.created_at),
                "sent_at": str(c.sent_at) if c.sent_at else None,
            }
            for c in campaigns
        ]

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

        if not target_all and not target_event_id:
            return {"error": "Must specify either target_all=true or target_event_id. Who should receive this?"}

        if target_event_id:
            event = db.query(Event).filter(Event.id == target_event_id).first()
            if not event:
                return {"error": f"Event {target_event_id} not found"}

        # Auto-generate name if not provided
        campaign_name = arguments.get("name")
        if not campaign_name:
            if target_event_id and event:
                campaign_name = f"Blast: {event.name} - {datetime.utcnow().strftime('%b %d')}"
            else:
                campaign_name = f"Blast: All Users - {datetime.utcnow().strftime('%b %d')}"

        campaign = MarketingCampaign(
            name=campaign_name,
            subject=arguments["subject"],
            content=arguments["content"],
            target_all=target_all,
            target_event_id=target_event_id,
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
