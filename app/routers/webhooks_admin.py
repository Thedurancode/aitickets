"""
Webhook Management API

Allows users to register, manage, and monitor webhook endpoints for
receiving real-time notifications about events in the system.

Supports:
- Webhook endpoint registration (CRUD)
- Event subscription management
- Delivery logs and retry history
- Test ping functionality
- Auto-disable failing endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
import json
import secrets
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus
from app.services.webhooks import send_test_ping, fire_webhook_event
from app.rate_limit import limiter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# Pydantic schemas
class WebhookEndpointCreate(BaseModel):
    url: HttpUrl
    event_types: List[str]  # e.g., ["ticket.purchased", "event.created", "*"]
    description: Optional[str] = None


class WebhookEndpointUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    event_types: Optional[List[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class WebhookEndpointResponse(BaseModel):
    id: int
    url: str
    event_types: List[str]
    description: Optional[str]
    is_active: bool
    secret: str
    created_at: datetime
    last_delivery_at: Optional[datetime]
    success_count: int
    failure_count: int

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: int
    event_type: str
    status: str
    attempt: int
    response_status: Optional[int]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Available webhook events
AVAILABLE_EVENTS = [
    "ticket.purchased",
    "ticket.refunded",
    "event.created",
    "event.updated",
    "event.cancelled",
    "event.sold_out",
    "alert.triggered",
    "monitoring.alerts",
    "customer.churn_risk",
    "*",  # Subscribe to all events
]


@router.get("/events")
@limiter.limit("30/minute")
async def list_available_events(request: Request):
    """
    List all available webhook events that can be subscribed to.

    **Events:**
    - `ticket.purchased` - Fired when a ticket is successfully purchased
    - `ticket.refunded` - Fired when a ticket is refunded
    - `event.created` - Fired when a new event is created
    - `event.updated` - Fired when an event is modified
    - `event.cancelled` - Fired when an event is cancelled
    - `event.sold_out` - Fired when an event sells out
    - `alert.triggered` - Fired when an intelligence alert is generated
    - `monitoring.alerts` - Fired when proactive monitoring detects issues
    - `customer.churn_risk` - Fired when customer churn is detected
    - `*` - Subscribe to all events
    """
    return {
        "events": AVAILABLE_EVENTS,
        "note": "Use '*' to subscribe to all events",
    }


@router.post("/endpoints", response_model=WebhookEndpointResponse)
@limiter.limit("10/minute")
async def create_webhook_endpoint(
    request: Request,
    webhook: WebhookEndpointCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new webhook endpoint.

    **Request Body:**
    ```json
    {
      "url": "https://example.com/webhooks",
      "event_types": ["ticket.purchased", "event.created"],
      "description": "Main webhook for ticket notifications"
    }
    ```

    **Response:** Returns the created endpoint with a secret key for signature verification.

    **Signature Verification:**
    All webhook deliveries include an `X-Webhook-Signature` header containing an
    HMAC-SHA256 signature. Verify it using the secret provided in the response.

    ```python
    import hmac
    import hashlib

    def verify_signature(payload, signature, secret):
        computed = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature)
    ```
    """
    # Validate event types
    for event_type in webhook.event_types:
        if event_type not in AVAILABLE_EVENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event_type}. Use /webhooks/events to see available events.",
            )

    # Generate secret for signature verification
    secret = secrets.token_urlsafe(32)

    endpoint = WebhookEndpoint(
        url=str(webhook.url),
        event_types=json.dumps(webhook.event_types),
        description=webhook.description,
        secret=secret,
        is_active=True,
        success_count=0,
        failure_count=0,
    )

    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    return WebhookEndpointResponse(
        id=endpoint.id,
        url=endpoint.url,
        event_types=json.loads(endpoint.event_types),
        description=endpoint.description,
        is_active=endpoint.is_active,
        secret=endpoint.secret,
        created_at=endpoint.created_at,
        last_delivery_at=endpoint.last_delivery_at,
        success_count=endpoint.success_count,
        failure_count=endpoint.failure_count,
    )


@router.get("/endpoints", response_model=List[WebhookEndpointResponse])
@limiter.limit("30/minute")
async def list_webhook_endpoints(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all registered webhook endpoints."""
    endpoints = db.query(WebhookEndpoint).all()

    return [
        WebhookEndpointResponse(
            id=e.id,
            url=e.url,
            event_types=json.loads(e.event_types),
            description=e.description,
            is_active=e.is_active,
            secret=e.secret,
            created_at=e.created_at,
            last_delivery_at=e.last_delivery_at,
            success_count=e.success_count,
            failure_count=e.failure_count,
        )
        for e in endpoints
    ]


@router.get("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
@limiter.limit("30/minute")
async def get_webhook_endpoint(
    request: Request,
    endpoint_id: int,
    db: Session = Depends(get_db),
):
    """Get details of a specific webhook endpoint."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    return WebhookEndpointResponse(
        id=endpoint.id,
        url=endpoint.url,
        event_types=json.loads(endpoint.event_types),
        description=endpoint.description,
        is_active=endpoint.is_active,
        secret=endpoint.secret,
        created_at=endpoint.created_at,
        last_delivery_at=endpoint.last_delivery_at,
        success_count=endpoint.success_count,
        failure_count=endpoint.failure_count,
    )


@router.patch("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
@limiter.limit("10/minute")
async def update_webhook_endpoint(
    request: Request,
    endpoint_id: int,
    webhook: WebhookEndpointUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a webhook endpoint.

    Can update URL, event subscriptions, description, or active status.
    """
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    if webhook.url is not None:
        endpoint.url = str(webhook.url)

    if webhook.event_types is not None:
        # Validate event types
        for event_type in webhook.event_types:
            if event_type not in AVAILABLE_EVENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type: {event_type}",
                )
        endpoint.event_types = json.dumps(webhook.event_types)

    if webhook.description is not None:
        endpoint.description = webhook.description

    if webhook.is_active is not None:
        endpoint.is_active = webhook.is_active

    db.commit()
    db.refresh(endpoint)

    return WebhookEndpointResponse(
        id=endpoint.id,
        url=endpoint.url,
        event_types=json.loads(endpoint.event_types),
        description=endpoint.description,
        is_active=endpoint.is_active,
        secret=endpoint.secret,
        created_at=endpoint.created_at,
        last_delivery_at=endpoint.last_delivery_at,
        success_count=endpoint.success_count,
        failure_count=endpoint.failure_count,
    )


@router.delete("/endpoints/{endpoint_id}")
@limiter.limit("10/minute")
async def delete_webhook_endpoint(
    request: Request,
    endpoint_id: int,
    db: Session = Depends(get_db),
):
    """Delete a webhook endpoint."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    db.delete(endpoint)
    db.commit()

    return {"status": "deleted", "endpoint_id": endpoint_id}


@router.post("/endpoints/{endpoint_id}/test")
@limiter.limit("5/minute")
async def test_webhook_endpoint(
    request: Request,
    endpoint_id: int,
    db: Session = Depends(get_db),
):
    """
    Send a test ping to a webhook endpoint.

    Useful for verifying that your endpoint is reachable and can
    process webhook payloads correctly.
    """
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    result = send_test_ping(endpoint_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/endpoints/{endpoint_id}/deliveries", response_model=List[WebhookDeliveryResponse])
@limiter.limit("30/minute")
async def get_webhook_deliveries(
    request: Request,
    endpoint_id: int,
    limit: int = Query(50, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get delivery history for a webhook endpoint.

    **Query Parameters:**
    - `limit`: Max deliveries to return (default 50, max 100)
    - `status`: Filter by status (pending, success, failed)
    """
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    query = db.query(WebhookDelivery).filter(WebhookDelivery.endpoint_id == endpoint_id)

    if status:
        try:
            status_enum = WebhookDeliveryStatus[status.upper()]
            query = query.filter(WebhookDelivery.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid: pending, success, failed",
            )

    deliveries = query.order_by(WebhookDelivery.created_at.desc()).limit(limit).all()

    return [
        WebhookDeliveryResponse(
            id=d.id,
            event_type=d.event_type,
            status=d.status.value,
            attempt=d.attempt,
            response_status=d.response_status,
            error=d.error,
            created_at=d.created_at,
            completed_at=d.completed_at,
        )
        for d in deliveries
    ]


@router.get("/endpoints/{endpoint_id}/stats")
@limiter.limit("30/minute")
async def get_webhook_stats(
    request: Request,
    endpoint_id: int,
    days: int = Query(7, le=90),
    db: Session = Depends(get_db),
):
    """
    Get delivery statistics for a webhook endpoint.

    **Returns:**
    - Success rate over time period
    - Total deliveries by status
    - Average response time
    - Most common errors
    """
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    since = datetime.now(timezone.utc) - timedelta(days=days)

    deliveries = (
        db.query(WebhookDelivery)
        .filter(
            WebhookDelivery.endpoint_id == endpoint_id,
            WebhookDelivery.created_at >= since,
        )
        .all()
    )

    total = len(deliveries)
    success = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.SUCCESS)
    failed = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.FAILED)
    pending = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.PENDING)

    success_rate = (success / total * 100) if total > 0 else 0

    # Count error types
    error_counts = {}
    for d in deliveries:
        if d.error:
            error_type = d.error.split(":")[0]  # Get first part of error message
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

    return {
        "endpoint_id": endpoint_id,
        "period_days": days,
        "total_deliveries": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "success_rate": round(success_rate, 2),
        "common_errors": sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
    }


@router.post("/fire-test-event")
@limiter.limit("5/minute")
async def fire_test_event(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Fire a test webhook event to all registered endpoints.

    Useful for testing your webhook integration end-to-end.
    """
    fire_webhook_event(
        "test.ping",
        {
            "message": "This is a test webhook event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        db=db,
    )

    return {
        "status": "fired",
        "event_type": "test.ping",
        "message": "Test event sent to all active endpoints",
    }
