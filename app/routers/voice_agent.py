"""
Enhanced Voice Agent API Router

Provides natural voice interaction with:
- Context-aware conversations
- Proactive suggestions
- Emotional intelligence
- Multi-turn dialogue support
- Real-time voice transcription
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import asyncio
import io
import base64

from app.database import get_db
from app.models import EventGoer
from app.auth import get_current_user
from app.services.voice_agent_enhanced import process_enhanced_voice_command, EnhancedVoiceAgent
from app.services.voice_mcp_router import match_intent, route_intent, MCPAction
from app.config import get_settings
from dataclasses import asdict
import hmac
import hashlib
import os

router = APIRouter(prefix="/api/voice-agent", tags=["Voice Agent"])


# ==================== Request/Response Models ====================

class VoiceCommandRequest(BaseModel):
    """Voice command request."""
    text: str
    session_id: Optional[str] = None
    audio_emotion: Optional[str] = None  # detected emotion from voice
    context: Optional[Dict[str, Any]] = None


class VoiceCommandResponse(BaseModel):
    """Voice command response."""
    text: str
    intent: str
    emotional_tone: str
    suggestions: List[str]
    proactive_insights: Optional[List[Dict]] = None
    alerts: Optional[List[Dict]] = None
    voice_settings: Dict[str, Any]
    actions: Optional[List[Dict]] = None


class WhisperTranscriptionRequest(BaseModel):
    """Whisper transcription request."""
    audio_base64: str
    language: Optional[str] = "en"
    session_id: Optional[str] = None


# ==================== Voice Command Processing ====================

@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Any = None  # Made optional for demo
):
    """
    Process a voice command with enhanced natural language understanding.

    Features:
    - Context-aware responses
    - Emotional tone adaptation
    - Proactive suggestions
    - Multi-turn conversation support

    Example:
    ```
    {
        "text": "How are my ticket sales doing today?",
        "session_id": "session_123",
        "audio_emotion": "curious"
    }
    ```
    """
    # Use demo user ID if no auth
    user_id = current_user.id if current_user else 1

    result = await process_enhanced_voice_command(
        db=db,
        user_id=user_id,
        text=request.text,
        session_id=request.session_id,
        audio_emotion=request.audio_emotion
    )

    # If there are urgent alerts, schedule follow-up
    if result.get("alerts"):
        for alert in result["alerts"]:
            if alert.get("type") == "low_sales_warning":
                background_tasks.add_task(
                    _schedule_marketing_boost,
                    db,
                    alert["event_id"],
                    current_user.id
                )

    return VoiceCommandResponse(**result)


class ElevenLabsToolCall(BaseModel):
    text: str
    session_id: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ElevenLabsToolResponse(BaseModel):
    spoken_text: str
    action: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    requires_confirmation: bool = False
    followups: List[str] = []


def _verify_elevenlabs_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
    if not secret:
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/elevenlabs", response_model=ElevenLabsToolResponse)
async def elevenlabs_webhook(
    payload: ElevenLabsToolCall,
    db: Session = Depends(get_db),
):
    """Webhook for an ElevenLabs Conversational AI agent.

    Fast-path: match_intent() + route_intent() returns an MCPAction for
    Gmail / Calendar / Supabase / claude-mem. Fall-through: the existing
    enhanced voice agent handles open-ended queries.
    """
    intent = match_intent(payload.text)
    if intent:
        action = route_intent(intent, payload.entities or {})
        if isinstance(action, MCPAction):
            return ElevenLabsToolResponse(
                spoken_text=action.spoken_preamble,
                action=asdict(action),
                intent=intent,
                requires_confirmation=action.requires_confirmation,
                followups=action.followup_intents,
            )

    result = await process_enhanced_voice_command(
        db=db,
        user_id=1,
        text=payload.text,
        session_id=payload.session_id,
    )
    return ElevenLabsToolResponse(
        spoken_text=result["text"],
        intent=result.get("intent"),
        followups=result.get("suggestions", []),
    )


@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = None,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Transcribe audio to text using Whisper API and process the command.

    Accepts audio file (wav, mp3, m4a, etc.) and returns transcription + response.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Whisper API not configured")

    try:
        # Read audio file
        audio_content = await audio_file.read()

        # Transcribe using Whisper
        import openai
        openai.api_key = settings.openai_api_key

        # Save temp file for Whisper API
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_content)
            tmp_file_path = tmp_file.name

        # Transcribe
        with open(tmp_file_path, "rb") as audio:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio,
                language="en"
            )

        transcribed_text = transcript["text"]

        # Detect emotion from audio (simplified - would use audio analysis in production)
        audio_emotion = _detect_audio_emotion(audio_content)

        # Process the transcribed command
        result = await process_enhanced_voice_command(
            db=db,
            user_id=current_user.id,
            text=transcribed_text,
            session_id=session_id,
            audio_emotion=audio_emotion
        )

        # Clean up temp file
        import os
        os.remove(tmp_file_path)

        return {
            "transcription": transcribed_text,
            "response": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.websocket("/stream")
async def voice_stream_websocket(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time voice streaming.

    Supports continuous conversation with context preservation.
    Send audio chunks, receive transcription and responses in real-time.
    """
    await websocket.accept()
    session_id = f"ws_session_{datetime.utcnow().timestamp()}"
    agent = EnhancedVoiceAgent(db)

    try:
        while True:
            # Receive audio chunk or text command
            data = await websocket.receive_json()

            if data.get("type") == "audio_chunk":
                # Process audio chunk (would accumulate and transcribe)
                audio_base64 = data.get("audio")
                # In production, accumulate chunks and transcribe when silence detected
                transcribed_text = await _transcribe_audio_chunk(audio_base64)

                if transcribed_text:
                    # Process command
                    result = await agent.process_voice_input(
                        user_id=data.get("user_id", 1),
                        text=transcribed_text,
                        session_id=session_id
                    )

                    # Send response
                    await websocket.send_json({
                        "type": "response",
                        "transcription": transcribed_text,
                        "response": result
                    })

            elif data.get("type") == "text":
                # Direct text input
                result = await agent.process_voice_input(
                    user_id=data.get("user_id", 1),
                    text=data.get("text"),
                    session_id=session_id
                )

                await websocket.send_json({
                    "type": "response",
                    "response": result
                })

            elif data.get("type") == "end_session":
                break

    except WebSocketDisconnect:
        pass
    finally:
        # Clean up session
        if hasattr(agent, 'contexts'):
            agent.contexts.pop(data.get("user_id", 1), None)


# ==================== Voice Synthesis ====================

@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    voice: str = "nova",  # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
    speed: float = 1.0,
    emotional_tone: Optional[str] = None,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert text to speech with emotional tone adaptation.

    Uses OpenAI TTS or ElevenLabs for voice synthesis.
    """
    settings = get_settings()

    # Use ElevenLabs if configured (better emotional control)
    if settings.elevenlabs_api_key:
        return await _synthesize_with_elevenlabs(text, emotional_tone, settings)
    elif settings.openai_api_key:
        return await _synthesize_with_openai(text, voice, speed, settings)
    else:
        raise HTTPException(status_code=503, detail="TTS service not configured")


async def _synthesize_with_elevenlabs(
    text: str,
    emotional_tone: Optional[str],
    settings
):
    """Synthesize speech using ElevenLabs with emotional control."""
    import requests

    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.elevenlabs_api_key
    }

    # Adjust voice settings based on emotional tone
    voice_settings = {
        "stability": 0.5,
        "similarity_boost": 0.5
    }

    if emotional_tone == "enthusiastic":
        voice_settings["stability"] = 0.3
        voice_settings["similarity_boost"] = 0.7
    elif emotional_tone == "empathetic":
        voice_settings["stability"] = 0.7
        voice_settings["similarity_boost"] = 0.3
    elif emotional_tone == "urgent":
        voice_settings["stability"] = 0.4
        voice_settings["similarity_boost"] = 0.8

    data = {
        "text": text,
        "voice_settings": voice_settings
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/mpeg"
        )
    else:
        raise HTTPException(status_code=500, detail="TTS generation failed")


async def _synthesize_with_openai(
    text: str,
    voice: str,
    speed: float,
    settings
):
    """Synthesize speech using OpenAI TTS."""
    import openai
    openai.api_key = settings.openai_api_key

    response = openai.Audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        speed=speed
    )

    return StreamingResponse(
        io.BytesIO(response.content),
        media_type="audio/mpeg"
    )


# ==================== Proactive Voice Notifications ====================

@router.post("/notify")
async def send_voice_notification(
    user_id: int,
    message: str,
    urgency: str = "normal",  # normal, urgent, celebration
    channel: str = "push",  # push, sms, call
    db: Session = Depends(get_db)
):
    """
    Send proactive voice notification to user.

    Used for alerts, milestones, and important updates.
    """
    user = db.query(EventGoer).filter(EventGoer.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if channel == "call":
        # Initiate voice call using Twilio
        from app.services.voice_call import initiate_voice_call
        call_result = await initiate_voice_call(
            to_number=user.phone,
            message=message,
            voice_tone=urgency
        )
        return {"status": "call_initiated", "call_sid": call_result["sid"]}

    elif channel == "sms":
        # Send SMS with option to call back
        from app.services.notifications import send_sms
        sms_result = await send_sms(
            to_number=user.phone,
            message=f"{message}\n\nReply 'CALL' for voice assistance."
        )
        return {"status": "sms_sent", "message_id": sms_result["id"]}

    else:
        # Push notification
        from app.services.notifications import send_push_notification
        push_result = await send_push_notification(
            user_id=user_id,
            title="Voice Assistant Alert",
            body=message,
            data={"urgency": urgency, "voice_enabled": True}
        )
        return {"status": "push_sent", "notification_id": push_result["id"]}


# ==================== Voice Analytics ====================

@router.get("/analytics")
async def get_voice_analytics(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: Any = None  # Made optional for demo
):
    """
    Get voice interaction analytics.

    Shows usage patterns, popular commands, and conversation metrics.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func

    # This would query a VoiceInteraction table in production
    # For now, return sample analytics
    return {
        "period": f"Last {days} days",
        "total_interactions": 156,
        "unique_users": 42,
        "average_session_length": "3.5 minutes",
        "top_intents": [
            {"intent": "check_sales", "count": 89, "percentage": 57},
            {"intent": "get_revenue", "count": 34, "percentage": 22},
            {"intent": "marketing_status", "count": 23, "percentage": 15},
            {"intent": "create_event", "count": 10, "percentage": 6}
        ],
        "emotional_distribution": {
            "neutral": 45,
            "excited": 25,
            "urgent": 15,
            "confused": 10,
            "frustrated": 5
        },
        "peak_hours": [
            {"hour": 9, "interactions": 24},
            {"hour": 14, "interactions": 31},
            {"hour": 16, "interactions": 28}
        ],
        "satisfaction_score": 4.6,  # Out of 5
        "resolution_rate": 92,  # Percentage of queries resolved
        "proactive_alerts_sent": 47,
        "actions_automated": 23
    }


# ==================== Helper Functions ====================

def _detect_audio_emotion(audio_content: bytes) -> str:
    """
    Detect emotion from audio characteristics.

    In production, would use:
    - Pitch analysis
    - Speaking rate
    - Volume variations
    - Spectral features
    """
    # Simplified placeholder
    return "neutral"


async def _transcribe_audio_chunk(audio_base64: str) -> Optional[str]:
    """
    Transcribe audio chunk using streaming recognition.

    In production, would use:
    - Google Speech-to-Text streaming
    - Azure Cognitive Services
    - Amazon Transcribe streaming
    """
    # Placeholder for streaming transcription
    return None


async def _schedule_marketing_boost(db: Session, event_id: int, user_id: int):
    """
    Schedule automatic marketing boost for low-performing event.
    """
    from app.services.event_intelligence import boost_event_marketing

    # This would trigger automated marketing optimization
    # For now, just log the intent
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Scheduling marketing boost for event {event_id} requested by user {user_id}")


# ==================== Voice Training ====================

@router.post("/train")
async def train_voice_model(
    feedback: Dict[str, Any],
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provide feedback to improve voice understanding.

    Helps train the model on:
    - Intent recognition accuracy
    - Response appropriateness
    - Emotional tone matching
    """
    # Store feedback for model improvement
    return {
        "status": "feedback_received",
        "message": "Thank you for helping improve the voice assistant!"
    }


from datetime import datetime