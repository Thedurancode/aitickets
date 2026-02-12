"""Router for outbound webhook endpoint management."""

import json
import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WebhookEndpoint, WebhookDelivery
from app.schemas import (
    WebhookEndpointCreate,
    WebhookEndpointUpdate,
    WebhookEndpointResponse,
    WebhookDeliveryResponse,
    WebhookTestResponse,
)

router = APIRouter(prefix="/webhooks/outbound", tags=["webhooks"])


@router.post("", response_model=WebhookEndpointResponse, status_code=201)
def register_webhook(webhook: WebhookEndpointCreate, db: Session = Depends(get_db)):
    """Register a new webhook endpoint."""
    endpoint = WebhookEndpoint(
        url=webhook.url,
        secret=webhook.secret,
        description=webhook.description,
        event_types=json.dumps(webhook.event_types),
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return _to_response(endpoint)


@router.get("", response_model=list[WebhookEndpointResponse])
def list_webhooks(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List all registered webhook endpoints."""
    endpoints = (
        db.query(WebhookEndpoint)
        .order_by(WebhookEndpoint.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_to_response(ep) for ep in endpoints]


@router.get("/{endpoint_id}", response_model=WebhookEndpointResponse)
def get_webhook(endpoint_id: int, db: Session = Depends(get_db)):
    """Get a specific webhook endpoint."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return _to_response(endpoint)


@router.put("/{endpoint_id}", response_model=WebhookEndpointResponse)
def update_webhook(endpoint_id: int, webhook: WebhookEndpointUpdate, db: Session = Depends(get_db)):
    """Update a webhook endpoint."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    update_data = webhook.model_dump(exclude_unset=True)
    if "event_types" in update_data:
        update_data["event_types"] = json.dumps(update_data["event_types"])

    for field, value in update_data.items():
        setattr(endpoint, field, value)

    db.commit()
    db.refresh(endpoint)
    return _to_response(endpoint)


@router.delete("/{endpoint_id}", status_code=204)
def delete_webhook(endpoint_id: int, db: Session = Depends(get_db)):
    """Delete a webhook endpoint and all its delivery logs."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    db.delete(endpoint)
    db.commit()
    return None


@router.get("/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_deliveries(
    endpoint_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List delivery logs for a specific webhook endpoint."""
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.endpoint_id == endpoint_id)
        .order_by(WebhookDelivery.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        WebhookDeliveryResponse(
            id=d.id,
            endpoint_id=d.endpoint_id,
            event_type=d.event_type,
            status=d.status.value if hasattr(d.status, "value") else d.status,
            attempt=d.attempt,
            response_status=d.response_status,
            error=d.error,
            created_at=d.created_at,
            completed_at=d.completed_at,
        )
        for d in deliveries
    ]


@router.post("/{endpoint_id}/test", response_model=WebhookTestResponse)
def test_webhook(endpoint_id: int, db: Session = Depends(get_db)):
    """Send a test ping to a webhook endpoint."""
    import uuid
    from datetime import datetime, timezone
    from app.models import WebhookDeliveryStatus
    from app.services.webhooks import compute_signature, DELIVERY_TIMEOUT_SECONDS

    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    payload_body = {
        "id": uuid.uuid4().hex,
        "event_type": "ping",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "Webhook test ping from AI Tickets"},
    }
    payload_json = json.dumps(payload_body, default=str)

    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        event_type="ping",
        payload=payload_json,
        status=WebhookDeliveryStatus.PENDING,
        attempt=1,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    payload_bytes = payload_json.encode("utf-8")
    signature = compute_signature(payload_bytes, endpoint.secret)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "ping",
        "X-Webhook-Delivery-Id": str(delivery.id),
        "User-Agent": "AITickets-Webhook/1.0",
    }

    try:
        resp = http_requests.post(
            endpoint.url, data=payload_bytes, headers=headers,
            timeout=DELIVERY_TIMEOUT_SECONDS,
        )
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:1024]
        if 200 <= resp.status_code < 300:
            delivery.status = WebhookDeliveryStatus.SUCCESS
        else:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error = f"HTTP {resp.status_code}"
    except http_requests.RequestException as exc:
        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.error = str(exc)

    delivery.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(delivery)

    return WebhookTestResponse(
        delivery_id=delivery.id,
        status=delivery.status.value if hasattr(delivery.status, "value") else delivery.status,
        response_status=delivery.response_status,
        response_body=delivery.response_body,
        error=delivery.error,
    )


def _to_response(endpoint: WebhookEndpoint) -> WebhookEndpointResponse:
    """Convert DB model to response, deserializing event_types JSON."""
    try:
        event_types = json.loads(endpoint.event_types)
    except (json.JSONDecodeError, TypeError):
        event_types = []

    return WebhookEndpointResponse(
        id=endpoint.id,
        url=endpoint.url,
        description=endpoint.description,
        event_types=event_types,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at,
    )
