"""
Voiceover Generation Router

Endpoints for generating and managing AI voiceovers for events.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.voiceover_service import get_voiceover_service

router = APIRouter(prefix="/voiceovers", tags=["voiceovers"])


class GenerateVoiceoverRequest(BaseModel):
    event_id: int
    voice_id: Optional[str] = None


@router.post("/generate")
def generate_event_voiceover(
    request: GenerateVoiceoverRequest,
    db: Session = Depends(get_db)
):
    """Generate a voiceover for an event."""
    service = get_voiceover_service(db)
    result = service.generate_voiceover(
        event_id=request.event_id,
        voice_id=request.voice_id
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/event/{event_id}")
def get_event_voiceover(event_id: int, db: Session = Depends(get_db)):
    """Get the voiceover file for an event (if it exists)."""
    from pathlib import Path

    file_path = f"static/voiceovers/event_{event_id}.mp3"

    if not Path(file_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Voiceover not found. Generate one first using POST /voiceovers/generate"
        )

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename=f"event_{event_id}_voiceover.mp3"
    )


@router.delete("/event/{event_id}")
def delete_event_voiceover(event_id: int):
    """Delete the voiceover file for an event."""
    from pathlib import Path

    file_path = Path(f"static/voiceovers/event_{event_id}.mp3")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Voiceover not found")

    file_path.unlink()

    return {"status": "success", "message": f"Deleted voiceover for event {event_id}"}
