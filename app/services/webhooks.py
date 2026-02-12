"""Outbound webhook delivery service.

Fires HTTP POST requests to registered webhook endpoints when events occur.
Uses threading for async delivery and APScheduler for retries.
"""

import hashlib
import hmac
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests as http_requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
DELIVERY_TIMEOUT_SECONDS = 10
RETRY_DELAYS_SECONDS = [0, 60, 300]  # immediate, 1 min, 5 min


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def _deliver(delivery_id: int):
    """Execute a single webhook delivery attempt in a background thread."""
    db = SessionLocal()
    try:
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        if not delivery:
            return

        endpoint = db.query(WebhookEndpoint).filter(
            WebhookEndpoint.id == delivery.endpoint_id
        ).first()
        if not endpoint or not endpoint.is_active:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error = "Endpoint not found or inactive"
            delivery.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        payload_bytes = delivery.payload.encode("utf-8")
        signature = compute_signature(payload_bytes, endpoint.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Delivery-Id": str(delivery.id),
            "User-Agent": "AITickets-Webhook/1.0",
        }

        try:
            resp = http_requests.post(
                endpoint.url,
                data=payload_bytes,
                headers=headers,
                timeout=DELIVERY_TIMEOUT_SECONDS,
            )
            delivery.response_status = resp.status_code
            delivery.response_body = resp.text[:1024]

            if 200 <= resp.status_code < 300:
                delivery.status = WebhookDeliveryStatus.SUCCESS
                delivery.completed_at = datetime.now(timezone.utc)
            else:
                _handle_failure(db, delivery, endpoint, f"HTTP {resp.status_code}")
        except http_requests.RequestException as exc:
            _handle_failure(db, delivery, endpoint, str(exc))

        db.commit()
    except Exception:
        logger.exception("Webhook delivery error for delivery_id=%s", delivery_id)
    finally:
        db.close()


def _handle_failure(db: Session, delivery: WebhookDelivery, endpoint: WebhookEndpoint, error_msg: str):
    """Handle a failed delivery: mark failed or schedule retry."""
    delivery.error = error_msg
    delivery.completed_at = datetime.now(timezone.utc)
    delivery.status = WebhookDeliveryStatus.FAILED

    if delivery.attempt < MAX_ATTEMPTS:
        next_attempt = delivery.attempt + 1
        delay = RETRY_DELAYS_SECONDS[min(next_attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)]

        try:
            from app.services.scheduler import get_scheduler
            from apscheduler.triggers.date import DateTrigger

            run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

            retry = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=delivery.event_type,
                payload=delivery.payload,
                status=WebhookDeliveryStatus.PENDING,
                attempt=next_attempt,
            )
            db.add(retry)
            db.commit()
            db.refresh(retry)

            scheduler = get_scheduler()
            scheduler.add_job(
                _deliver,
                trigger=DateTrigger(run_date=run_at),
                id=f"webhook_retry_{retry.id}",
                replace_existing=True,
                args=[retry.id],
            )
        except Exception as e:
            logger.warning("Could not schedule webhook retry: %s", e)


def fire_webhook_event(event_type: str, data: dict, db: Optional[Session] = None):
    """Fire a webhook event to all matching registered endpoints. Non-blocking."""
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        endpoints = (
            db.query(WebhookEndpoint)
            .filter(WebhookEndpoint.is_active == True)
            .all()
        )

        payload_body = {
            "id": uuid.uuid4().hex,
            "event_type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        payload_json = json.dumps(payload_body, default=str)

        for endpoint in endpoints:
            try:
                subscribed = json.loads(endpoint.event_types)
            except (json.JSONDecodeError, TypeError):
                continue

            if event_type not in subscribed and "*" not in subscribed:
                continue

            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload=payload_json,
                status=WebhookDeliveryStatus.PENDING,
                attempt=1,
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

            thread = threading.Thread(target=_deliver, args=[delivery.id], daemon=True)
            thread.start()

    except Exception:
        logger.exception("Error firing webhook event %s", event_type)
    finally:
        if owns_session:
            db.close()


def send_test_ping(endpoint_id: int) -> dict:
    """Send a test ping to a specific endpoint. Synchronous."""
    db = SessionLocal()
    try:
        endpoint = db.query(WebhookEndpoint).filter(
            WebhookEndpoint.id == endpoint_id
        ).first()
        if not endpoint:
            return {"error": "Endpoint not found"}

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

        # Deliver synchronously for test
        _deliver(delivery.id)

        db.refresh(delivery)
        return {
            "delivery_id": delivery.id,
            "status": delivery.status.value if hasattr(delivery.status, "value") else delivery.status,
            "response_status": delivery.response_status,
            "response_body": delivery.response_body,
            "error": delivery.error,
        }
    finally:
        db.close()
