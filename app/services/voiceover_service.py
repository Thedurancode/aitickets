"""
Voiceover Generation Service using ElevenLabs API

This service generates AI voiceovers for events using the venue's configured voice settings.
"""
import os
import json
import requests
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Event, Venue


class VoiceoverService:
    """Service for generating voiceovers using ElevenLabs API."""

    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"

        # Default voice settings if venue doesn't have custom settings
        self.default_voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }

    def _get_available_voices(self) -> Dict[str, Any]:
        """
        Get list of available voices from ElevenLabs.

        Returns:
            Dict with voices list or error
        """
        if not self.api_key:
            return {
                "status": "error",
                "error": "ElevenLabs API key not configured. Add ELEVENLABS_API_KEY to .env file."
            }

        try:
            response = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()

            voices_data = response.json()
            voices = [
                {
                    "voice_id": voice["voice_id"],
                    "name": voice["name"],
                    "labels": voice.get("labels", {}),
                    "preview_url": voice.get("preview_url")
                }
                for voice in voices_data.get("voices", [])
            ]

            return {
                "status": "success",
                "voices": voices,
                "count": len(voices)
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to fetch voices: {str(e)}"
            }

    def _generate_event_script(self, event: Event) -> str:
        """
        Generate a natural-sounding script for the event voiceover.

        Args:
            event: Event object

        Returns:
            Script text
        """
        venue_name = event.venue.name if event.venue else "the venue"

        # Parse date
        from datetime import datetime as dt
        if event.event_date:
            try:
                date_obj = dt.strptime(event.event_date, "%Y-%m-%d")
                event_date = date_obj.strftime("%B %d, %Y")
            except:
                event_date = event.event_date
        else:
            event_date = "soon"

        # Parse time
        if event.event_time:
            try:
                time_obj = dt.strptime(event.event_time, "%H:%M")
                event_time = time_obj.strftime("%I:%M %p")
            except:
                event_time = event.event_time
        else:
            event_time = ""

        # Get ticket price range
        ticket_tiers = event.ticket_tiers
        if ticket_tiers:
            prices = [tier.price_cents / 100 for tier in ticket_tiers if tier.price_cents]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                if min_price == max_price:
                    price_text = f"Tickets are ${min_price:.0f}."
                else:
                    price_text = f"Tickets start at ${min_price:.0f}."
            else:
                price_text = "Tickets are available now."
        else:
            price_text = "Tickets are available now."

        # Build script
        script = f"Join us for {event.name} at {venue_name} on {event_date}"
        if event_time:
            script += f" at {event_time}"
        script += ". "

        if event.description:
            # Add first sentence of description
            description = event.description.strip()
            first_sentence = description.split('.')[0] + '.'
            if len(first_sentence) < 200:  # Keep it concise
                script += f"{first_sentence} "

        script += f"{price_text} Don't miss out - get your tickets today!"

        return script

    def generate_voiceover(
        self,
        event_id: int,
        voice_id: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a voiceover for an event.

        Args:
            event_id: Event ID
            voice_id: Optional voice ID override (uses venue's voice if not provided)
            output_path: Optional path to save audio file (defaults to static/voiceovers/{event_id}.mp3)

        Returns:
            Dict with status and file path or error
        """
        if not self.api_key:
            return {
                "status": "error",
                "error": "ElevenLabs API key not configured. Add ELEVENLABS_API_KEY to .env file."
            }

        # Get event
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {
                "status": "error",
                "error": f"Event {event_id} not found"
            }

        # Determine voice to use
        if not voice_id and event.venue:
            voice_id = event.venue.voice_id

        if not voice_id:
            # Use ElevenLabs default voice (Rachel)
            voice_id = "21m00Tcm4TlvDq8ikWAM"

        # Get voice settings
        voice_settings = self.default_voice_settings.copy()
        if event.venue and event.venue.voice_settings:
            try:
                custom_settings = json.loads(event.venue.voice_settings)
                voice_settings.update(custom_settings)
            except:
                pass  # Use defaults if JSON parsing fails

        # Generate script
        text = self._generate_event_script(event)

        # Generate audio
        try:
            response = requests.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": voice_settings
                }
            )
            response.raise_for_status()

            # Save audio file
            if not output_path:
                os.makedirs("static/voiceovers", exist_ok=True)
                output_path = f"static/voiceovers/event_{event_id}.mp3"

            with open(output_path, "wb") as f:
                f.write(response.content)

            return {
                "status": "success",
                "event_id": event_id,
                "event_name": event.name,
                "voice_id": voice_id,
                "file_path": output_path,
                "text": text,
                "duration_estimate": len(text) / 15  # Rough estimate: ~15 chars per second
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to generate voiceover: {str(e)}"
            }

    def preview_voice(self, voice_id: str, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a preview of a voice.

        Args:
            voice_id: ElevenLabs voice ID
            text: Optional custom text (defaults to a sample phrase)

        Returns:
            Dict with status and audio data or error
        """
        if not self.api_key:
            return {
                "status": "error",
                "error": "ElevenLabs API key not configured"
            }

        if not text:
            text = "Welcome to our event! Join us for an unforgettable experience."

        try:
            response = requests.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": self.default_voice_settings
                }
            )
            response.raise_for_status()

            # Save preview
            os.makedirs("static/voiceovers/previews", exist_ok=True)
            preview_path = f"static/voiceovers/previews/{voice_id}.mp3"

            with open(preview_path, "wb") as f:
                f.write(response.content)

            return {
                "status": "success",
                "voice_id": voice_id,
                "file_path": preview_path,
                "text": text
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to preview voice: {str(e)}"
            }

    def update_venue_voice(
        self,
        venue_id: int,
        voice_id: str,
        voice_name: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a venue's voice configuration.

        Args:
            venue_id: Venue ID
            voice_id: ElevenLabs voice ID
            voice_name: Human-readable voice name
            voice_settings: Optional custom voice settings

        Returns:
            Dict with status or error
        """
        venue = self.db.query(Venue).filter(Venue.id == venue_id).first()
        if not venue:
            return {
                "status": "error",
                "error": f"Venue {venue_id} not found"
            }

        venue.voice_id = voice_id
        venue.voice_name = voice_name or voice_id

        if voice_settings:
            venue.voice_settings = json.dumps(voice_settings)

        self.db.commit()

        return {
            "status": "success",
            "venue_id": venue_id,
            "venue_name": venue.name,
            "voice_id": voice_id,
            "voice_name": venue.voice_name
        }


def get_voiceover_service(db: Session) -> VoiceoverService:
    """Factory function to get VoiceoverService instance."""
    return VoiceoverService(db)
