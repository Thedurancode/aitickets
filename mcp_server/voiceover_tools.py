"""
MCP Tools for Voiceover Generation

Tools that allow AI agents to generate voiceovers for events using ElevenLabs.
"""
import json
from mcp.types import Tool, TextContent
from app.database import SessionLocal
from app.services.voiceover_service import get_voiceover_service


def get_voiceover_tools():
    """
    Return list of voiceover generation MCP tools.
    """
    return [
        Tool(
            name="generate_event_voiceover",
            description="Generate an AI voiceover for an event using ElevenLabs text-to-speech",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to generate voiceover for"
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "Optional ElevenLabs voice ID (uses venue's default voice if not provided)"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="get_available_voices",
            description="Get list of available ElevenLabs voices for voiceover generation",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="preview_voice",
            description="Generate a preview of an ElevenLabs voice with sample text",
            inputSchema={
                "type": "object",
                "properties": {
                    "voice_id": {
                        "type": "string",
                        "description": "ElevenLabs voice ID to preview"
                    },
                    "text": {
                        "type": "string",
                        "description": "Optional custom text for preview (uses default sample if not provided)"
                    }
                },
                "required": ["voice_id"]
            }
        ),
        Tool(
            name="update_venue_voice",
            description="Update a venue's default voice settings for voiceover generation",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "integer",
                        "description": "Venue ID"
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "ElevenLabs voice ID"
                    },
                    "voice_name": {
                        "type": "string",
                        "description": "Human-readable voice name"
                    },
                    "voice_settings": {
                        "type": "object",
                        "description": "Optional custom voice settings",
                        "properties": {
                            "stability": {
                                "type": "number",
                                "description": "Voice stability (0.0-1.0)"
                            },
                            "similarity_boost": {
                                "type": "number",
                                "description": "Similarity boost (0.0-1.0)"
                            },
                            "style": {
                                "type": "number",
                                "description": "Style exaggeration (0.0-1.0)"
                            },
                            "use_speaker_boost": {
                                "type": "boolean",
                                "description": "Enable speaker boost"
                            }
                        }
                    }
                },
                "required": ["venue_id", "voice_id"]
            }
        ),
        Tool(
            name="get_venue_voice_settings",
            description="Get a venue's current voice settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "integer",
                        "description": "Venue ID"
                    }
                },
                "required": ["venue_id"]
            }
        )
    ]


async def handle_voiceover_tool(name: str, arguments: dict):
    """
    Handle voiceover generation tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        TextContent with the result
    """
    db = SessionLocal()
    try:
        service = get_voiceover_service(db)

        if name == "generate_event_voiceover":
            event_id = arguments["event_id"]
            voice_id = arguments.get("voice_id")

            result = service.generate_voiceover(
                event_id=event_id,
                voice_id=voice_id
            )

            if result.get("status") == "error":
                return [TextContent(
                    type="text",
                    text=f"❌ Voiceover Generation Failed\n\n{result['error']}"
                )]

            summary = "🎙️ Voiceover Generated Successfully\n\n"
            summary += f"Event: {result['event_name']}\n"
            summary += f"Voice ID: {result['voice_id']}\n"
            summary += f"File Path: {result['file_path']}\n"
            summary += f"Duration (est): {result['duration_estimate']:.1f}s\n\n"
            summary += f"Script:\n{result['text']}"

            return [TextContent(type="text", text=summary)]

        elif name == "get_available_voices":
            result = service._get_available_voices()

            if result.get("status") == "error":
                return [TextContent(
                    type="text",
                    text=f"❌ Failed to Get Voices\n\n{result['error']}"
                )]

            summary = f"🎙️ Available ElevenLabs Voices ({result['count']})\n\n"

            for voice in result['voices']:
                summary += f"• {voice['name']}\n"
                summary += f"  ID: {voice['voice_id']}\n"

                labels = voice.get('labels', {})
                if labels:
                    label_str = ", ".join([f"{k}: {v}" for k, v in labels.items()])
                    summary += f"  Labels: {label_str}\n"

                if voice.get('preview_url'):
                    summary += f"  Preview: {voice['preview_url']}\n"

                summary += "\n"

            return [TextContent(type="text", text=summary)]

        elif name == "preview_voice":
            voice_id = arguments["voice_id"]
            text = arguments.get("text")

            result = service.preview_voice(voice_id=voice_id, text=text)

            if result.get("status") == "error":
                return [TextContent(
                    type="text",
                    text=f"❌ Voice Preview Failed\n\n{result['error']}"
                )]

            summary = "🎙️ Voice Preview Generated\n\n"
            summary += f"Voice ID: {result['voice_id']}\n"
            summary += f"File Path: {result['file_path']}\n"
            summary += f"Sample Text: {result['text']}"

            return [TextContent(type="text", text=summary)]

        elif name == "update_venue_voice":
            venue_id = arguments["venue_id"]
            voice_id = arguments["voice_id"]
            voice_name = arguments.get("voice_name")
            voice_settings = arguments.get("voice_settings")

            result = service.update_venue_voice(
                venue_id=venue_id,
                voice_id=voice_id,
                voice_name=voice_name,
                voice_settings=voice_settings
            )

            if result.get("status") == "error":
                return [TextContent(
                    type="text",
                    text=f"❌ Failed to Update Venue Voice\n\n{result['error']}"
                )]

            summary = "✅ Venue Voice Settings Updated\n\n"
            summary += f"Venue: {result['venue_name']}\n"
            summary += f"Voice ID: {result['voice_id']}\n"
            summary += f"Voice Name: {result['voice_name']}"

            return [TextContent(type="text", text=summary)]

        elif name == "get_venue_voice_settings":
            venue_id = arguments["venue_id"]

            from app.models import Venue
            venue = db.query(Venue).filter(Venue.id == venue_id).first()

            if not venue:
                return [TextContent(
                    type="text",
                    text=f"❌ Venue {venue_id} not found"
                )]

            summary = f"🎙️ Voice Settings for {venue.name}\n\n"

            if venue.voice_id:
                summary += f"Voice ID: {venue.voice_id}\n"
                summary += f"Voice Name: {venue.voice_name or 'Not set'}\n\n"

                if venue.voice_settings:
                    try:
                        settings = json.loads(venue.voice_settings)
                        summary += "Voice Settings:\n"
                        for key, value in settings.items():
                            summary += f"  • {key}: {value}\n"
                    except:
                        summary += "Voice Settings: (invalid JSON)\n"
            else:
                summary += "❌ No voice configured for this venue.\n"
                summary += "Use 'update_venue_voice' to set one."

            return [TextContent(type="text", text=summary)]

        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]

    finally:
        db.close()
