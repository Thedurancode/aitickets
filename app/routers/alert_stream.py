"""
Real-Time Alert Streaming via Server-Sent Events (SSE)

Provides live push notifications to browser clients when new alerts are created.
Eliminates the need for polling - alerts appear instantly in the UI.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alert-stream", tags=["alert-stream"])

# Store active SSE connections
active_connections: set[asyncio.Queue] = set()


def format_sse_message(event: str, data: dict) -> str:
    """Format data as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def alert_event_generator(
    request: Request,
    last_alert_id: int,
    db: Session,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream of alert events.

    Sends:
    1. Initial batch of recent alerts (since last_alert_id)
    2. Heartbeat every 30 seconds to keep connection alive
    3. New alerts as they're created (via queue)
    """
    # Create queue for this connection
    queue: asyncio.Queue = asyncio.Queue()
    active_connections.add(queue)

    try:
        # Send initial alerts since last_alert_id
        if last_alert_id > 0:
            recent_alerts = (
                db.query(Alert)
                .filter(Alert.id > last_alert_id)
                .order_by(Alert.created_at.desc())
                .limit(50)
                .all()
            )

            for alert in reversed(recent_alerts):  # Send oldest first
                yield format_sse_message("alert", {
                    "id": alert.id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value if hasattr(alert.severity, "value") else alert.severity,
                    "event_id": alert.event_id,
                    "is_read": alert.is_read,
                    "created_at": alert.created_at.isoformat(),
                })

        # Send connected confirmation
        yield format_sse_message("connected", {
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep connection alive and listen for new alerts
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break

            try:
                # Wait for new alert (with timeout for heartbeat)
                alert_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield format_sse_message("alert", alert_data)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield format_sse_message("heartbeat", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    finally:
        # Clean up connection
        active_connections.discard(queue)
        logger.info(f"SSE connection closed. Active connections: {len(active_connections)}")


@router.get("/stream")
@limiter.limit("10/minute")
async def stream_alerts(
    request: Request,
    last_alert_id: int = 0,
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events stream for real-time alerts.

    **Query Parameters:**
    - `last_alert_id`: ID of last alert seen (defaults to 0 = all recent alerts)

    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/alert-stream/stream?last_alert_id=0');

    eventSource.addEventListener('alert', (event) => {
        const alert = JSON.parse(event.data);
        console.log('New alert:', alert);
        // Update UI, show notification, play sound, etc.
    });

    eventSource.addEventListener('connected', (event) => {
        console.log('Connected to alert stream');
    });

    eventSource.addEventListener('heartbeat', (event) => {
        console.log('Connection alive');
    });
    ```

    **Events:**
    - `alert` - New alert created
    - `connected` - Initial connection established
    - `heartbeat` - Keep-alive ping (every 30s)
    """
    return StreamingResponse(
        alert_event_generator(request, last_alert_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def broadcast_alert(alert: Alert):
    """
    Broadcast alert to all connected SSE clients.

    Call this when a new alert is created to push it to all connected browsers.
    """
    if not active_connections:
        return  # No clients connected

    alert_data = {
        "id": alert.id,
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity.value if hasattr(alert.severity, "value") else alert.severity,
        "event_id": alert.event_id,
        "is_read": alert.is_read,
        "created_at": alert.created_at.isoformat(),
    }

    # Push to all connected clients
    for queue in active_connections:
        try:
            queue.put_nowait(alert_data)
        except asyncio.QueueFull:
            logger.warning("SSE queue full, dropping alert")


@router.get("/stats")
async def get_stream_stats():
    """Get SSE connection statistics."""
    return {
        "active_connections": len(active_connections),
        "status": "operational",
    }
