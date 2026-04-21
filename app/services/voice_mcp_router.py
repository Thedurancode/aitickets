"""Voice intent → MCP tool routing map.

Returns structured MCPAction descriptors that downstream dispatchers
(Claude via MCP, or direct-API adapters) execute. The voice agent
stays unaware of transport — it just asks: given this intent + entities,
which tool do I call and with what args?
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class MCPServer(str, Enum):
    GMAIL = "gmail"
    CALENDAR = "google_calendar"
    DRIVE = "google_drive"
    SUPABASE = "supabase"
    MEMORY = "claude_mem"
    COMPOSIO = "composio"


@dataclass
class MCPAction:
    server: MCPServer
    tool: str
    args: dict[str, Any]
    spoken_preamble: str
    requires_confirmation: bool = False
    followup_intents: list[str] = field(default_factory=list)


Handler = Callable[[dict[str, Any]], MCPAction | list[MCPAction]]


def _schedule_event(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.CALENDAR,
        tool="create_event",
        args={
            "summary": e["title"],
            "startTime": e["start_iso"],
            "endTime": e["end_iso"],
            "attendeeEmails": e.get("attendees", []),
            "location": e.get("venue"),
            "description": e.get("notes"),
            "addGoogleMeetUrl": e.get("virtual", False),
            "timeZone": e.get("timezone", "America/New_York"),
        },
        spoken_preamble=f"Booking {e['title']} on your calendar.",
        requires_confirmation=True,
    )


def _check_schedule(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.CALENDAR,
        tool="list_events",
        args={
            "startTime": e["start_iso"],
            "endTime": e["end_iso"],
            "fullText": e.get("query"),
            "pageSize": e.get("limit", 20),
        },
        spoken_preamble="Pulling your schedule.",
    )


def _find_time(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.CALENDAR,
        tool="suggest_time",
        args={
            "attendeeEmails": e["attendees"],
            "startTime": e["start_iso"],
            "endTime": e["end_iso"],
            "durationMinutes": e.get("duration_min", 30),
            "preferences": {
                "startHour": e.get("start_hour", "09:00"),
                "endHour": e.get("end_hour", "18:00"),
                "excludeWeekends": e.get("exclude_weekends", False),
            },
        },
        spoken_preamble="Finding open windows.",
    )


def _email_attendees(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.GMAIL,
        tool="create_draft",
        args={
            "to": e["recipients"],
            "cc": e.get("cc", []),
            "subject": e["subject"],
            "body": e["body"],
            "htmlBody": e.get("html_body"),
        },
        spoken_preamble=f"Drafting to {len(e['recipients'])} people.",
        requires_confirmation=True,
    )


def _search_email(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.GMAIL,
        tool="search_threads",
        args={"query": e["query"], "pageSize": e.get("limit", 10)},
        spoken_preamble=f"Searching inbox for {e['query']}.",
    )


def _recall_memory(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.MEMORY,
        tool="search",
        args={"query": e["query"], "limit": e.get("limit", 5)},
        spoken_preamble="Checking past conversations.",
    )


def _ticket_sales(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.SUPABASE,
        tool="execute_sql",
        args={
            "query": (
                "SELECT tt.name, COUNT(*) AS sold, SUM(tt.price_cents)/100 AS revenue "
                "FROM tickets t JOIN ticket_tiers tt ON t.ticket_tier_id = tt.id "
                "WHERE t.event_id = :event_id AND t.status = 'PAID' "
                "GROUP BY tt.name"
            ),
            "params": {"event_id": e["event_id"]},
        },
        spoken_preamble="Pulling ticket totals.",
    )


def _refund_ticket(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.SUPABASE,
        tool="execute_sql",
        args={
            "query": (
                "UPDATE tickets SET status = 'REFUND_PENDING' "
                "WHERE id = :ticket_id AND status = 'PAID' RETURNING *"
            ),
            "params": {"ticket_id": e["ticket_id"]},
        },
        spoken_preamble=f"Marking ticket {e['ticket_id']} for refund.",
        requires_confirmation=True,
        followup_intents=["email_refund_confirmation"],
    )


def _save_to_drive(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.DRIVE,
        tool="upload_file",
        args={
            "name": e["filename"],
            "mimeType": e.get("mime_type", "application/pdf"),
            "content": e["content"],
            "parents": e.get("folder_ids", []),
        },
        spoken_preamble=f"Saving {e['filename']} to Drive.",
    )


def _post_slack(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.COMPOSIO,
        tool="slack_send_message",
        args={"channel": e["channel"], "text": e["message"]},
        spoken_preamble=f"Posting to #{e['channel']}.",
        requires_confirmation=True,
    )


def _post_instagram(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.COMPOSIO,
        tool="instagram_create_post",
        args={"caption": e["caption"], "media_url": e["image_url"]},
        spoken_preamble="Queueing Instagram post.",
        requires_confirmation=True,
    )


def _notion_event_brief(e: dict) -> MCPAction:
    return MCPAction(
        server=MCPServer.COMPOSIO,
        tool="notion_create_page",
        args={
            "parent_database_id": e["database_id"],
            "properties": {
                "Name": e["title"],
                "Date": e["start_iso"],
                "Venue": e.get("venue"),
            },
            "content_markdown": e.get("body", ""),
        },
        spoken_preamble="Creating Notion brief.",
        requires_confirmation=True,
    )


INTENT_ROUTES: dict[str, Handler] = {
    "schedule_event": _schedule_event,
    "check_schedule": _check_schedule,
    "find_time": _find_time,
    "email_attendees": _email_attendees,
    "search_email": _search_email,
    "recall_memory": _recall_memory,
    "ticket_sales": _ticket_sales,
    "refund_ticket": _refund_ticket,
    "save_to_drive": _save_to_drive,
    "post_to_slack": _post_slack,
    "post_to_instagram": _post_instagram,
    "create_notion_brief": _notion_event_brief,
}


INTENT_PHRASES: dict[str, list[str]] = {
    "schedule_event": ["book", "schedule", "put on the calendar", "add event"],
    "check_schedule": ["what's on my calendar", "what do i have", "show my schedule"],
    "find_time": ["when are we free", "find a time", "schedule a meeting with"],
    "email_attendees": ["email everyone", "send an email", "message attendees"],
    "search_email": ["search my inbox", "find emails", "any emails from"],
    "recall_memory": ["what did we decide", "remember when", "last time we"],
    "ticket_sales": ["how many tickets", "sales for", "revenue for"],
    "refund_ticket": ["refund ticket", "cancel order", "process refund"],
    "save_to_drive": ["save to drive", "upload to drive", "put it in drive"],
    "post_to_slack": ["post to slack", "announce on slack", "tell the team"],
    "post_to_instagram": ["post to instagram", "share on ig"],
    "create_notion_brief": ["make a notion page", "draft a brief", "add to notion"],
}


def match_intent(text: str) -> Optional[str]:
    text_lower = text.lower()
    for intent, phrases in INTENT_PHRASES.items():
        if any(p in text_lower for p in phrases):
            return intent
    return None


def route_intent(
    intent: str, entities: dict[str, Any]
) -> MCPAction | list[MCPAction] | None:
    handler = INTENT_ROUTES.get(intent)
    if not handler:
        return None
    return handler(entities)
