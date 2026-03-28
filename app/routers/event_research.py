"""
Event Research Agent API Router

Endpoints for autonomous event research and AI-powered marketing plan generation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.rate_limit import limiter
from app.services.event_research_agent import (
    run_event_research_agent,
    analyze_event_context,
    get_research_summary,
)
from app.models import Event

router = APIRouter(prefix="/event-research", tags=["event-research"])


# In-memory storage for research reports (use Redis in production)
research_cache: dict[int, dict] = {}


class ResearchRequest(BaseModel):
    """Request to trigger event research."""
    event_id: int = Field(..., description="Event ID to research")
    include_ai_plan: bool = Field(True, description="Generate AI marketing plan (uses OpenRouter credits)")
    force_refresh: bool = Field(False, description="Force new research even if cached")


@router.post("/run")
@limiter.limit("5/minute")
async def trigger_event_research(
    request: Request,
    research_req: ResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger autonomous research agent for an event.

    **Process:**
    1. Analyzes event context (date, venue, pricing, inventory)
    2. Researches venue area (demographics, competitors, weather forecast)
    3. Generates AI marketing plan using GPT-4o-mini
    4. Returns comprehensive research report

    **Use Cases:**
    - "Research my event and create a marketing plan"
    - "What's the best way to market this concert?"
    - "Analyze the venue area and suggest targeting"

    **Example:**
    ```json
    {
      "event_id": 123,
      "include_ai_plan": true,
      "force_refresh": false
    }
    ```
    """
    # Check if event exists
    event = db.query(Event).filter(Event.id == research_req.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check cache
    if not research_req.force_refresh and research_req.event_id in research_cache:
        cached = research_cache[research_req.event_id]
        cached['cache_hit'] = True
        return cached

    # Run research agent
    research_report = await run_event_research_agent(
        db,
        research_req.event_id,
        include_ai_plan=research_req.include_ai_plan,
    )

    # Cache result
    research_cache[research_req.event_id] = research_report

    return research_report


@router.get("/events/{event_id}/context")
@limiter.limit("20/minute")
async def get_event_context(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed event context analysis without running full research.

    Returns event details, venue info, pricing, inventory, and timing analysis.
    Fast endpoint for quick context checks.
    """
    context = analyze_event_context(db, event_id)

    if "error" in context:
        raise HTTPException(status_code=404, detail=context["error"])

    return context


@router.get("/events/{event_id}/report")
@limiter.limit("20/minute")
async def get_research_report(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get cached research report for an event.

    Returns previously generated research, or 404 if no research exists.
    Use POST /run to generate new research.
    """
    if event_id not in research_cache:
        raise HTTPException(
            status_code=404,
            detail="No research report found. Use POST /event-research/run to generate one."
        )

    return research_cache[event_id]


@router.get("/events/{event_id}/summary")
@limiter.limit("20/minute")
async def get_research_summary_endpoint(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get human-readable text summary of research report.

    Returns markdown-formatted summary for easy reading.
    """
    if event_id not in research_cache:
        raise HTTPException(
            status_code=404,
            detail="No research report found. Use POST /event-research/run to generate one."
        )

    report = research_cache[event_id]
    summary = get_research_summary(report)

    return {
        "event_id": event_id,
        "event_name": report['event_name'],
        "summary": summary,
        "generated_at": report['research_completed_at'],
    }


@router.delete("/events/{event_id}/cache")
@limiter.limit("10/minute")
async def clear_research_cache(
    request: Request,
    event_id: int,
):
    """
    Clear cached research report for an event.

    Forces next research to be freshly generated.
    """
    if event_id in research_cache:
        del research_cache[event_id]
        return {"message": "Cache cleared", "event_id": event_id}
    else:
        raise HTTPException(status_code=404, detail="No cached research found")


@router.get("/cache/stats")
@limiter.limit("30/minute")
async def get_cache_stats(request: Request):
    """
    Get statistics about research cache.

    Returns number of cached reports and event IDs.
    """
    return {
        "total_cached_reports": len(research_cache),
        "cached_event_ids": list(research_cache.keys()),
        "cache_size_kb": len(str(research_cache)) / 1024,
    }
