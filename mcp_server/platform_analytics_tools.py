"""
MCP Tools for Cross-Platform Page View Analytics

Tools that allow AI agents to query page views across multiple platforms.
"""
import json
from mcp.types import Tool, TextContent
from app.database import SessionLocal
from app.services.platform_analytics import get_platform_analytics_service


def get_platform_analytics_tools():
    """
    Return list of cross-platform analytics MCP tools.
    """
    return [
        Tool(
            name="get_cross_platform_pageviews",
            description="Get aggregated page views across all platforms for an event (internal, Eventbrite, Facebook, Ticketmaster, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to get page views for"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 30)",
                        "default": 30
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="get_platform_breakdown",
            description="Get detailed platform-by-platform breakdown with unique visitors and engagement metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to analyze"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="get_all_platforms_summary",
            description="Get summary of ALL events' views across all platforms - useful for org-wide analytics",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="track_external_pageview",
            description="Manually track a page view from an external platform (for testing or manual imports)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Internal event ID"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Platform name (e.g., 'eventbrite', 'facebook', 'ticketmaster')"
                    },
                    "external_platform_id": {
                        "type": "string",
                        "description": "Event ID on the external platform (optional)"
                    },
                    "platform_data": {
                        "type": "object",
                        "description": "Additional metadata from platform API (optional)"
                    }
                },
                "required": ["event_id", "platform"]
            }
        ),
        Tool(
            name="bulk_import_external_views",
            description="Bulk import view counts from external platforms when they provide aggregate counts",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Internal event ID"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Platform name (e.g., 'eventbrite', 'facebook')"
                    },
                    "view_count": {
                        "type": "integer",
                        "description": "Number of views to record"
                    },
                    "external_platform_id": {
                        "type": "string",
                        "description": "External event ID (optional)"
                    },
                    "platform_data": {
                        "type": "object",
                        "description": "Platform metadata (optional)"
                    }
                },
                "required": ["event_id", "platform", "view_count"]
            }
        )
    ]


async def handle_platform_analytics_tool(name: str, arguments: dict):
    """
    Handle cross-platform analytics tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        TextContent with the result
    """
    db = SessionLocal()
    try:
        service = get_platform_analytics_service(db)

        if name == "get_cross_platform_pageviews":
            event_id = arguments["event_id"]
            days = arguments.get("days", 30)
            result = service.get_cross_platform_pageviews(event_id, days)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_platform_breakdown":
            event_id = arguments["event_id"]
            days = arguments.get("days", 7)
            result = service.get_platform_breakdown(event_id, days)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_all_platforms_summary":
            days = arguments.get("days", 30)
            result = service.get_all_platforms_summary(days)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "track_external_pageview":
            event_id = arguments["event_id"]
            platform = arguments["platform"]
            external_platform_id = arguments.get("external_platform_id")
            platform_data = arguments.get("platform_data")

            page_view = service.track_external_pageview(
                event_id=event_id,
                platform=platform,
                external_platform_id=external_platform_id,
                platform_data=platform_data
            )

            return [TextContent(
                type="text",
                text=f"✅ Tracked external page view for event {event_id} from {platform} (PageView ID: {page_view.id})"
            )]

        elif name == "bulk_import_external_views":
            event_id = arguments["event_id"]
            platform = arguments["platform"]
            view_count = arguments["view_count"]
            external_platform_id = arguments.get("external_platform_id")
            platform_data = arguments.get("platform_data")

            created_count = service.bulk_import_external_views(
                event_id=event_id,
                platform=platform,
                view_count=view_count,
                external_platform_id=external_platform_id,
                platform_data=platform_data
            )

            return [TextContent(
                type="text",
                text=f"✅ Bulk imported {created_count} views for event {event_id} from {platform}"
            )]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    finally:
        db.close()
