"""Tests for outbound webhook system."""

import json
import hmac
import hashlib
import time
from unittest.mock import patch, MagicMock

from app.models import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus


# ============== CRUD Tests ==============

class TestWebhookCRUD:
    def test_register_webhook(self, client):
        r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "my-secret-key",
            "event_types": ["ticket.purchased", "event.created"],
            "description": "Test webhook",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["url"] == "https://example.com/hook"
        assert data["event_types"] == ["ticket.purchased", "event.created"]
        assert data["is_active"] is True
        assert "secret" not in data

    def test_list_webhooks(self, client):
        client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook1",
            "secret": "s1",
            "event_types": ["ticket.purchased"],
        })
        client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook2",
            "secret": "s2",
            "event_types": ["event.created"],
        })
        r = client.get("/api/webhooks/outbound")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_webhook(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "s",
            "event_types": ["ticket.purchased"],
        })
        webhook_id = create_r.json()["id"]
        r = client.get(f"/api/webhooks/outbound/{webhook_id}")
        assert r.status_code == 200
        assert r.json()["url"] == "https://example.com/hook"

    def test_get_webhook_not_found(self, client):
        r = client.get("/api/webhooks/outbound/99999")
        assert r.status_code == 404

    def test_update_webhook(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "s",
            "event_types": ["ticket.purchased"],
        })
        webhook_id = create_r.json()["id"]
        r = client.put(f"/api/webhooks/outbound/{webhook_id}", json={
            "url": "https://example.com/updated",
            "is_active": False,
        })
        assert r.status_code == 200
        assert r.json()["url"] == "https://example.com/updated"
        assert r.json()["is_active"] is False

    def test_update_event_types(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "s",
            "event_types": ["ticket.purchased"],
        })
        webhook_id = create_r.json()["id"]
        r = client.put(f"/api/webhooks/outbound/{webhook_id}", json={
            "event_types": ["ticket.purchased", "event.created", "event.deleted"],
        })
        assert r.status_code == 200
        assert len(r.json()["event_types"]) == 3

    def test_delete_webhook(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "s",
            "event_types": ["ticket.purchased"],
        })
        webhook_id = create_r.json()["id"]
        r = client.delete(f"/api/webhooks/outbound/{webhook_id}")
        assert r.status_code == 204
        # Verify gone
        r2 = client.get(f"/api/webhooks/outbound/{webhook_id}")
        assert r2.status_code == 404

    def test_delete_webhook_not_found(self, client):
        r = client.delete("/api/webhooks/outbound/99999")
        assert r.status_code == 404


# ============== Delivery Log Tests ==============

class TestWebhookDeliveries:
    def test_list_deliveries_empty(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://example.com/hook",
            "secret": "s",
            "event_types": ["ticket.purchased"],
        })
        webhook_id = create_r.json()["id"]
        r = client.get(f"/api/webhooks/outbound/{webhook_id}/deliveries")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_deliveries_not_found(self, client):
        r = client.get("/api/webhooks/outbound/99999/deliveries")
        assert r.status_code == 404


# ============== Signature Tests ==============

class TestWebhookSignature:
    def test_signature_computation(self):
        from app.services.webhooks import compute_signature
        payload = b'{"event_type": "ticket.purchased", "data": {}}'
        secret = "test-secret"
        sig = compute_signature(payload, secret)
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_different_secrets_produce_different_signatures(self):
        from app.services.webhooks import compute_signature
        payload = b'{"test": true}'
        sig1 = compute_signature(payload, "secret-1")
        sig2 = compute_signature(payload, "secret-2")
        assert sig1 != sig2


# ============== Webhook Firing Tests ==============

class TestWebhookFiring:
    def test_fire_creates_delivery(self, client, db):
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="test-secret",
            event_types=json.dumps(["ticket.purchased"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        with patch("app.services.webhooks.http_requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_post.return_value = mock_resp

            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("ticket.purchased", {
                "ticket_id": 1,
                "event_name": "Test Event",
            }, db=db)

            time.sleep(0.5)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) >= 1
        assert deliveries[0].event_type == "ticket.purchased"

    def test_fire_skips_unsubscribed_event(self, client, db):
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="test-secret",
            event_types=json.dumps(["event.created"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()

        with patch("app.services.webhooks.http_requests.post"):
            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("ticket.purchased", {"ticket_id": 1}, db=db)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) == 0

    def test_fire_skips_inactive_endpoint(self, client, db):
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="test-secret",
            event_types=json.dumps(["ticket.purchased"]),
            is_active=False,
        )
        db.add(endpoint)
        db.commit()

        with patch("app.services.webhooks.http_requests.post"):
            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("ticket.purchased", {"ticket_id": 1}, db=db)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) == 0

    def test_wildcard_subscription(self, client, db):
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="test-secret",
            event_types=json.dumps(["*"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        with patch("app.services.webhooks.http_requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_post.return_value = mock_resp

            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("event.deleted", {"event_id": 42}, db=db)

            time.sleep(0.5)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) >= 1

    def test_delivery_payload_shape(self, client, db):
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="test-secret",
            event_types=json.dumps(["event.created"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        with patch("app.services.webhooks.http_requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_post.return_value = mock_resp

            from app.services.webhooks import fire_webhook_event
            fire_webhook_event("event.created", {"event_id": 1, "name": "Concert"}, db=db)

            time.sleep(0.5)

        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).first()
        assert delivery is not None
        payload = json.loads(delivery.payload)
        assert payload["event_type"] == "event.created"
        assert "id" in payload
        assert "created_at" in payload
        assert payload["data"]["event_id"] == 1
        assert payload["data"]["name"] == "Concert"


# ============== Test Ping ==============

class TestWebhookPing:
    def test_ping_endpoint(self, client):
        create_r = client.post("/api/webhooks/outbound", json={
            "url": "https://httpbin.org/post",
            "secret": "ping-secret",
            "event_types": ["*"],
        })
        webhook_id = create_r.json()["id"]

        with patch("app.routers.webhooks.http_requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = '{"success": true}'
            mock_post.return_value = mock_resp

            r = client.post(f"/api/webhooks/outbound/{webhook_id}/test")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "success"
            assert data["response_status"] == 200

    def test_ping_not_found(self, client):
        r = client.post("/api/webhooks/outbound/99999/test")
        assert r.status_code == 404


# ============== Integration: Webhooks Fire on Events ==============

class TestWebhookIntegration:
    @patch("app.services.webhooks.http_requests.post")
    def test_event_created_fires_webhook(self, mock_post, client, db):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"
        mock_post.return_value = mock_resp

        # Register a webhook for event.created
        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="s",
            event_types=json.dumps(["event.created"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()

        # Create a venue first, then an event
        venue_r = client.post("/api/venues", json={"name": "Test Venue", "address": "123 St"})
        venue_id = venue_r.json()["id"]

        client.post("/api/events", json={
            "name": "Test Event",
            "event_date": "2025-12-31",
            "event_time": "20:00",
            "venue_id": venue_id,
        })

        time.sleep(0.5)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) >= 1
        assert deliveries[0].event_type == "event.created"

    @patch("app.services.webhooks.http_requests.post")
    def test_customer_registered_fires_webhook(self, mock_post, client, db):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"
        mock_post.return_value = mock_resp

        endpoint = WebhookEndpoint(
            url="https://example.com/hook",
            secret="s",
            event_types=json.dumps(["customer.registered"]),
            is_active=True,
        )
        db.add(endpoint)
        db.commit()

        client.post("/api/event-goers", json={
            "email": "webhook-test@example.com",
            "name": "Webhook Tester",
        })

        time.sleep(0.5)

        deliveries = db.query(WebhookDelivery).filter(
            WebhookDelivery.endpoint_id == endpoint.id
        ).all()
        assert len(deliveries) >= 1
        assert deliveries[0].event_type == "customer.registered"
