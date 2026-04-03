"""
MCP Tools for Social Media Publishing

Tools that allow AI agents to publish events to all social media platforms.
"""
import json
from mcp.types import Tool, TextContent
from app.database import SessionLocal
from app.services.social_media_publisher import get_social_media_publisher
from datetime import datetime


def get_social_media_tools():
    """
    Return list of social media publishing MCP tools.
    """
    return [
        Tool(
            name="update_event_social_media_posts",
            description="Update existing social media posts with latest event/ticket information (prices, availability, urgency)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to update"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Platforms to update (omit for all platforms with existing posts)"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="update_event_status_everywhere",
            description="Update event status across all social media platforms (publish, unpublish, pause, cancel)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["published", "draft", "paused", "cancelled"],
                        "description": "New status: 'published' (go live), 'draft'/'paused' (hide/unpublish), 'cancelled' (delete)"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Platforms to update (omit for all enabled platforms)"
                    }
                },
                "required": ["event_id", "status"]
            }
        ),
        Tool(
            name="publish_event_to_social_media",
            description="Publish an event to all enabled social media platforms (Twitter, Facebook, Instagram, LinkedIn, TikTok, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["twitter", "facebook", "instagram", "linkedin", "tiktok", "youtube", "threads", "pinterest", "postiz"]
                        },
                        "description": "List of platforms to publish to (omit to publish to all enabled platforms)"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "ISO format datetime to schedule post (omit to post immediately)"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="get_enabled_social_platforms",
            description="Get list of social media platforms that are configured and ready to use",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="preview_social_media_content",
            description="Preview how event content will appear on different social media platforms before publishing",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to preview"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="publish_to_twitter",
            description="Publish event to Twitter/X only",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "ISO format datetime to schedule tweet"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="publish_to_facebook",
            description="Publish event to Facebook page only",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "ISO format datetime to schedule post"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="publish_to_instagram",
            description="Publish event to Instagram only (requires image)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="publish_to_linkedin",
            description="Publish event to LinkedIn only (best for professional/corporate events)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "ISO format datetime to schedule post"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="publish_via_postiz",
            description="Publish event to multiple platforms via Postiz (Facebook, Instagram, Twitter, LinkedIn, TikTok, YouTube, Pinterest, Reddit all at once)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to publish"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Platforms to publish to via Postiz"
                    },
                    "schedule_time": {
                        "type": "string",
                        "description": "ISO format datetime to schedule posts"
                    }
                },
                "required": ["event_id"]
            }
        )
    ]


async def handle_social_media_tool(name: str, arguments: dict):
    """
    Handle social media publishing tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        TextContent with the result
    """
    db = SessionLocal()
    try:
        service = get_social_media_publisher(db)

        if name == "update_event_social_media_posts":
            event_id = arguments["event_id"]
            platforms = arguments.get("platforms")

            result = service.update_event_on_social_media(
                event_id=event_id,
                platforms=platforms
            )

            if result.get("status") == "no_posts":
                summary = f"ℹ️ No Social Media Posts to Update\n\n"
                summary += f"Event: {result['event_name']}\n"
                summary += f"Message: {result['message']}\n"
                return [TextContent(type="text", text=summary)]

            summary = f"🔄 Updated Social Media Posts\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Posts Attempted: {result['posts_attempted']}\n"
            summary += f"✅ Succeeded: {result['posts_succeeded']}\n"
            summary += f"❌ Failed: {result['posts_attempted'] - result['posts_succeeded']}\n\n"

            summary += "Platform Results:\n"
            for platform, platform_result in result['results'].items():
                status_emoji = "✅" if platform_result['status'] == 'success' else "⏭️" if platform_result['status'] == 'skipped' else "❌"
                summary += f"  {status_emoji} {platform.upper()}: {platform_result['status']}\n"

                if 'message' in platform_result:
                    summary += f"      {platform_result['message']}\n"
                elif platform_result['status'] == 'error':
                    summary += f"      Error: {platform_result.get('error', 'Unknown')}\n"
                elif platform_result['status'] == 'skipped':
                    summary += f"      Reason: {platform_result.get('reason', 'Unknown')}\n"

            return [TextContent(type="text", text=summary)]

        elif name == "update_event_status_everywhere":
            event_id = arguments["event_id"]
            status = arguments["status"]
            platforms = arguments.get("platforms")

            result = service.update_event_status_everywhere(
                event_id=event_id,
                status=status,
                platforms=platforms
            )

            status_emoji = {
                "published": "✅",
                "draft": "📝",
                "paused": "⏸️",
                "cancelled": "❌"
            }.get(status, "🔄")

            summary = f"{status_emoji} Event Status Updated to: {status.upper()}\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Platforms Attempted: {result['platforms_attempted']}\n"
            summary += f"✅ Succeeded: {result['platforms_succeeded']}\n"
            summary += f"❌ Failed: {result['platforms_attempted'] - result['platforms_succeeded']}\n\n"

            summary += "Platform Results:\n"
            for platform, platform_result in result['results'].items():
                status_emoji_result = "✅" if platform_result['status'] == 'success' else "ℹ️" if platform_result['status'] == 'info' else "⏭️" if platform_result['status'] == 'skipped' else "❌"
                summary += f"  {status_emoji_result} {platform.upper()}: {platform_result.get('status', 'unknown')}\n"

                if 'message' in platform_result:
                    summary += f"      {platform_result['message']}\n"
                elif platform_result['status'] == 'error':
                    summary += f"      Error: {platform_result.get('error', 'Unknown')}\n"
                elif platform_result['status'] == 'skipped':
                    summary += f"      Reason: {platform_result.get('reason', 'Unknown')}\n"

            return [TextContent(type="text", text=summary)]

        elif name == "publish_event_to_social_media":
            event_id = arguments["event_id"]
            platforms = arguments.get("platforms")
            schedule_time = arguments.get("schedule_time")

            if schedule_time:
                schedule_time = datetime.fromisoformat(schedule_time)

            result = service.publish_event_to_all_platforms(
                event_id=event_id,
                platforms=platforms,
                schedule_time=schedule_time
            )

            summary = f"📱 Published Event to Social Media\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Platforms Attempted: {result['platforms_attempted']}\n"
            summary += f"✅ Succeeded: {result['platforms_succeeded']}\n"
            summary += f"❌ Failed: {result['platforms_attempted'] - result['platforms_succeeded']}\n\n"

            summary += "Platform Results:\n"
            for platform, platform_result in result['results'].items():
                status_emoji = "✅" if platform_result['status'] == 'success' else "⏭️" if platform_result['status'] == 'skipped' else "❌"
                summary += f"  {status_emoji} {platform.upper()}: {platform_result['status']}\n"

                if platform_result['status'] == 'success' and 'url' in platform_result:
                    summary += f"      URL: {platform_result['url']}\n"
                elif platform_result['status'] == 'error':
                    summary += f"      Error: {platform_result.get('error', 'Unknown')}\n"
                elif platform_result['status'] == 'skipped':
                    summary += f"      Reason: {platform_result.get('reason', 'Unknown')}\n"

            return [TextContent(type="text", text=summary)]

        elif name == "get_enabled_social_platforms":
            platforms = service._get_enabled_platforms()

            summary = f"🌐 Enabled Social Media Platforms ({len(platforms)})\n\n"
            if platforms:
                for platform in platforms:
                    summary += f"  ✅ {platform.upper()}\n"
            else:
                summary += "  ⚠️ No platforms configured. Add API keys to .env file.\n"

            summary += "\n💡 Available Platforms:\n"
            summary += "  • Twitter/X\n"
            summary += "  • Facebook\n"
            summary += "  • Instagram\n"
            summary += "  • LinkedIn\n"
            summary += "  • TikTok\n"
            summary += "  • YouTube Community Posts\n"
            summary += "  • Threads (Meta)\n"
            summary += "  • Pinterest\n"
            summary += "  • Postiz (multi-platform)\n"

            return [TextContent(type="text", text=summary)]

        elif name == "preview_social_media_content":
            event_id = arguments["event_id"]

            from app.models import Event
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return [TextContent(type="text", text=f"❌ Event {event_id} not found")]

            content = service._generate_event_content(event)

            summary = f"👀 Social Media Content Preview\n\n"
            summary += f"Event: {event.name}\n\n"

            summary += "━━━ SHORT VERSION (Twitter, Threads) ━━━\n"
            summary += f"{content['short']}\n\n"

            summary += "━━━ MEDIUM VERSION (Instagram, Facebook) ━━━\n"
            summary += f"{content['medium']}\n\n"

            summary += "━━━ LONG VERSION (LinkedIn) ━━━\n"
            summary += f"{content['long']}\n\n"

            summary += f"📸 Image: {content['image_url'] or 'No image'}\n"
            summary += f"🔗 Event URL: {content['event_url']}\n"
            summary += f"🏷️ Hashtags: {content['hashtags']}\n"

            return [TextContent(type="text", text=summary)]

        elif name in ["publish_to_twitter", "publish_to_facebook", "publish_to_instagram", "publish_to_linkedin"]:
            event_id = arguments["event_id"]
            schedule_time = arguments.get("schedule_time")

            if schedule_time:
                schedule_time = datetime.fromisoformat(schedule_time)

            # Extract platform from tool name
            platform = name.replace("publish_to_", "")

            result = service.publish_event_to_all_platforms(
                event_id=event_id,
                platforms=[platform],
                schedule_time=schedule_time
            )

            platform_result = result['results'][platform]
            status_emoji = "✅" if platform_result['status'] == 'success' else "⏭️" if platform_result['status'] == 'skipped' else "❌"

            summary = f"{status_emoji} {platform.upper()} Publishing Result\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Status: {platform_result['status']}\n"

            if platform_result['status'] == 'success' and 'url' in platform_result:
                summary += f"Post URL: {platform_result['url']}\n"
            elif platform_result['status'] == 'error':
                summary += f"Error: {platform_result.get('error', 'Unknown')}\n"
            elif platform_result['status'] == 'skipped':
                summary += f"Reason: {platform_result.get('reason', 'Unknown')}\n"

            return [TextContent(type="text", text=summary)]

        elif name == "publish_via_postiz":
            event_id = arguments["event_id"]
            platforms = arguments.get("platforms", ["facebook", "instagram", "twitter", "linkedin"])
            schedule_time = arguments.get("schedule_time")

            if schedule_time:
                schedule_time = datetime.fromisoformat(schedule_time)

            result = service.publish_event_to_all_platforms(
                event_id=event_id,
                platforms=["postiz"],
                schedule_time=schedule_time
            )

            postiz_result = result['results']['postiz']
            status_emoji = "✅" if postiz_result['status'] == 'success' else "❌"

            summary = f"{status_emoji} Postiz Multi-Platform Publishing\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Status: {postiz_result['status']}\n"

            if postiz_result['status'] == 'success':
                summary += f"Published to: {', '.join(postiz_result.get('platforms_published', platforms))}\n"
            elif postiz_result['status'] == 'error':
                summary += f"Error: {postiz_result.get('error', 'Unknown')}\n"

            return [TextContent(type="text", text=summary)]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    finally:
        db.close()
