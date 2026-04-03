"""
MCP Tools for Weather Intelligence

Tools that allow AI agents to access weather forecasts and alerts.
"""
import json
from mcp.types import Tool, TextContent
from app.database import SessionLocal
from app.services.weather_intelligence import get_weather_intelligence_service
from app.models import AlertSeverity


def get_weather_tools():
    """
    Return list of weather intelligence MCP tools.
    """
    return [
        Tool(
            name="get_weather_forecast",
            description="Get latest weather forecast for an event (temperature, precipitation, wind, conditions)",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to get weather forecast for"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="check_event_weather",
            description="Manually trigger weather check for an event - fetches latest forecast and detects changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to check weather for"
                    },
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days ahead to forecast (default: 14)",
                        "default": 14
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="check_all_events_weather",
            description="Check weather for ALL upcoming events - useful for daily scheduled runs",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days ahead to forecast (default: 14)",
                        "default": 14
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_weather_alerts",
            description="Get weather alerts (significant changes detected) with optional filtering by event/severity",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Filter by event ID (optional)"
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity: low, medium, high, critical (optional)",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "unnotified_only": {
                        "type": "boolean",
                        "description": "Only return unnotified alerts (default: false)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="mark_weather_alerts_notified",
            description="Mark weather alerts as notified after sending notifications to users",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of alert IDs to mark as notified"
                    }
                },
                "required": ["alert_ids"]
            }
        ),
        Tool(
            name="get_weather_summary",
            description="Get summary of weather monitoring across all events (alerts by severity, critical warnings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days ahead to include (default: 14)",
                        "default": 14
                    }
                },
                "required": []
            }
        )
    ]


async def handle_weather_tool(name: str, arguments: dict):
    """
    Handle weather intelligence tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        TextContent with the result
    """
    db = SessionLocal()
    try:
        service = get_weather_intelligence_service(db)

        if name == "get_weather_forecast":
            event_id = arguments["event_id"]
            forecast = service.get_weather_forecast(event_id)

            if not forecast:
                return [TextContent(
                    type="text",
                    text=f"❌ No weather forecast available for event {event_id}. Run check_event_weather first."
                )]

            return [TextContent(
                type="text",
                text=json.dumps(forecast, indent=2)
            )]

        elif name == "check_event_weather":
            event_id = arguments["event_id"]
            days_ahead = arguments.get("days_ahead", 14)

            result = service.check_weather_for_event(event_id, days_ahead)

            # Format result with emojis for readability
            if result["status"] == "success":
                alert_emoji = "🚨" if result["alerts_generated"] > 0 else "✅"
                summary = f"{alert_emoji} Weather check complete for event {event_id}\n\n"
                summary += f"Event: {result['event_name']}\n"
                summary += f"Date: {result['event_date']} ({result['days_until_event']} days away)\n\n"
                summary += f"📊 Forecast:\n"
                summary += json.dumps(result["forecast"], indent=2)

                if result["alerts_generated"] > 0:
                    summary += f"\n\n🚨 {result['alerts_generated']} alert(s) generated:\n"
                    summary += json.dumps(result["alerts"], indent=2)

                return [TextContent(type="text", text=summary)]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

        elif name == "check_all_events_weather":
            days_ahead = arguments.get("days_ahead", 14)
            result = service.check_weather_for_all_events(days_ahead)

            summary = f"🌤️ Weather check complete for all events\n\n"
            summary += f"Total events: {result['total_events']}\n"
            summary += f"✅ Checked: {result['checked']}\n"
            summary += f"⏭️ Skipped: {result['skipped']}\n"
            summary += f"❌ Errors: {result['errors']}\n"
            summary += f"🚨 Total alerts: {result['total_alerts']}\n\n"

            if result['total_alerts'] > 0:
                summary += "Events with alerts:\n"
                for event in result['events']:
                    if event.get('alerts_generated', 0) > 0:
                        summary += f"  • {event.get('event_name', 'Unknown')}: {event['alerts_generated']} alerts\n"

            return [TextContent(type="text", text=summary)]

        elif name == "get_weather_alerts":
            event_id = arguments.get("event_id")
            severity = arguments.get("severity")
            unnotified_only = arguments.get("unnotified_only", False)

            # Parse severity
            severity_enum = None
            if severity:
                severity_enum = AlertSeverity[severity.upper()]

            alerts = service.get_weather_alerts(
                event_id=event_id,
                severity=severity_enum,
                unnotified_only=unnotified_only
            )

            if not alerts:
                return [TextContent(
                    type="text",
                    text="✅ No weather alerts found with the specified filters"
                )]

            summary = f"🚨 Found {len(alerts)} weather alert(s)\n\n"
            summary += json.dumps(alerts, indent=2)

            return [TextContent(type="text", text=summary)]

        elif name == "mark_weather_alerts_notified":
            alert_ids = arguments["alert_ids"]
            count = service.mark_alerts_notified(alert_ids)

            return [TextContent(
                type="text",
                text=f"✅ Marked {count} weather alert(s) as notified"
            )]

        elif name == "get_weather_summary":
            from app.models import WeatherAlert, Event
            from sqlalchemy import func, and_
            from datetime import date, timedelta

            days_ahead = arguments.get("days_ahead", 14)

            today = date.today()
            cutoff = today + timedelta(days=days_ahead)

            # Count upcoming events
            upcoming_events = db.query(func.count(Event.id)).filter(
                and_(
                    Event.date >= today,
                    Event.date <= cutoff
                )
            ).scalar() or 0

            # Count alerts by severity
            alert_counts = db.query(
                WeatherAlert.severity,
                func.count(WeatherAlert.id).label('count')
            ).join(Event).filter(
                and_(
                    Event.date >= today,
                    Event.date <= cutoff
                )
            ).group_by(WeatherAlert.severity).all()

            by_severity = {severity.value: 0 for severity in AlertSeverity}
            for severity, count in alert_counts:
                by_severity[severity.value] = count

            total_alerts = sum(by_severity.values())

            summary = f"🌤️ Weather Monitoring Summary (next {days_ahead} days)\n\n"
            summary += f"📅 Upcoming events: {upcoming_events}\n"
            summary += f"🚨 Total alerts: {total_alerts}\n\n"
            summary += f"Alerts by severity:\n"
            summary += f"  🔴 Critical: {by_severity['critical']}\n"
            summary += f"  🟠 High: {by_severity['high']}\n"
            summary += f"  🟡 Medium: {by_severity['medium']}\n"
            summary += f"  🟢 Low: {by_severity['low']}\n"

            return [TextContent(type="text", text=summary)]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    finally:
        db.close()
