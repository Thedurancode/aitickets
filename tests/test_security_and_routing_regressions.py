"""Regression tests for auth, routing, and webhook idempotency."""

import asyncio
import json
from io import BytesIO
from urllib.parse import urlparse
from unittest.mock import patch
import zipfile

import pytest

from app.config import get_settings
from app.models import Event, EventGoer, Ticket, TicketStatus, TicketTier, Venue
from app.routers.payments import handle_checkout_completed
from app.services.sms import send_ticket_sms
from app.services.wallet_pass import generate_wallet_pass


@pytest.fixture
def admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("MCP_API_KEY", "")
    get_settings.cache_clear()
    yield "test-admin-key"
    get_settings.cache_clear()


@pytest.fixture
def mcp_key(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "test-mcp-key")
    monkeypatch.setenv("ADMIN_API_KEY", "")
    get_settings.cache_clear()
    yield "test-mcp-key"
    get_settings.cache_clear()


def test_admin_key_blocks_event_and_about_writes(client, admin_key):
    # Public reads are still allowed.
    r = client.get("/api/events")
    assert r.status_code == 200
    r = client.get("/api/about")
    assert r.status_code == 200

    # Event/About writes require key.
    r = client.put("/api/events/99999", json={"name": "Blocked"})
    assert r.status_code == 401
    r = client.put("/api/about/hero_title", json={"content": "Blocked"})
    assert r.status_code == 401

    # With valid key, auth passes and endpoint logic runs.
    r = client.put(
        "/api/events/99999",
        json={"name": "Allowed"},
        headers={"x-admin-key": admin_key},
    )
    assert r.status_code == 404

    # Public token upload endpoint remains accessible without key.
    r = client.post("/api/event-image-update/upload")
    assert r.status_code == 422

    # Admin-only token generation remains protected.
    r = client.post(
        "/api/event-image-update/generate-token",
        json={"event_id": 1, "phone": "5551234567"},
    )
    assert r.status_code == 401


def test_event_image_magic_link_uses_public_root_path(client, create_event):
    event = create_event()
    r = client.post(
        "/api/event-image-update/generate-token",
        json={"event_id": event["id"], "phone": "5551234567"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    path = urlparse(data["magic_link"]).path
    assert path.startswith("/update-event-image/")

    page = client.get(path)
    assert page.status_code == 200
    assert "Update Event Image" in page.text


def test_flyer_magic_link_public_page_and_invalid_json_token(client, create_event):
    event = create_event()

    r = client.post(
        "/api/flyer-templates/magic-link",
        json={"event_id": event["id"], "phone": "5551234567"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    path = urlparse(data["upload_url"]).path
    assert path.startswith("/flyer-templates/select/")

    page = client.get(path)
    assert page.status_code == 200
    assert "Choose a Flyer Template" in page.text

    invalid = client.get("/api/flyer-templates/select/not-a-real-token")
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "Invalid or expired token"


def test_checkout_completed_webhook_is_idempotent(db):
    venue = Venue(name="Webhook Arena", address="1 Main St")
    db.add(venue)
    db.commit()
    db.refresh(venue)

    event = Event(
        venue_id=venue.id,
        name="Webhook Event",
        event_date="2025-12-31",
        event_time="20:00",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    tier = TicketTier(
        event_id=event.id,
        name="GA",
        price=2500,
        quantity_available=100,
        quantity_sold=0,
    )
    db.add(tier)
    db.commit()
    db.refresh(tier)

    goer = EventGoer(email="idempotent@example.com", name="Idempotent User")
    db.add(goer)
    db.commit()
    db.refresh(goer)

    ticket = Ticket(
        ticket_tier_id=tier.id,
        event_goer_id=goer.id,
        status=TicketStatus.PENDING,
        stripe_checkout_session_id="cs_test_123",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    payload = {
        "id": "cs_test_123",
        "payment_intent": "pi_test_123",
        "metadata": {},
    }

    with patch("app.routers.payments.send_ticket_email", return_value=True), \
            patch("app.routers.tickets.check_inventory_thresholds", return_value=None), \
            patch("app.services.webhooks.fire_webhook_event", return_value=None):
        asyncio.run(handle_checkout_completed(payload, db))
        db.refresh(ticket)
        db.refresh(tier)
        first_token = ticket.qr_code_token

        assert ticket.status == TicketStatus.PAID
        assert tier.quantity_sold == 1

        asyncio.run(handle_checkout_completed(payload, db))
        db.refresh(ticket)
        db.refresh(tier)

    assert tier.quantity_sold == 1
    assert ticket.status == TicketStatus.PAID
    assert ticket.qr_code_token == first_token


def test_tickets_by_email_route_not_shadowed(client, create_event, create_tier):
    event = create_event()
    tier = create_tier(event_id=event["id"], price=0, quantity_available=10)

    r = client.post(
        f"/api/tickets/events/{event['id']}/purchase",
        json={
            "ticket_tier_id": tier["id"],
            "quantity": 1,
            "email": "buyer@example.com",
            "name": "Buyer",
            "phone": "5551112222",
        },
    )
    assert r.status_code == 200, r.text

    by_email = client.get("/api/tickets/by-email", params={"email": "buyer@example.com"})
    assert by_email.status_code == 200, by_email.text
    assert len(by_email.json()) == 1


def test_ticket_links_use_api_validate_path():
    with patch("app.services.sms.send_sms", return_value={"success": True}) as mock_send:
        send_ticket_sms(
            to_phone="5551112222",
            recipient_name="Buyer",
            event_name="Show",
            event_date="2025-12-31",
            event_time="20:00",
            venue_name="Arena",
            venue_address="123 St",
            tier_name="GA",
            qr_code_token="qr-token-1",
        )
        _, message = mock_send.call_args.args
        assert "/api/tickets/validate/qr-token-1" in message

    pass_bytes = generate_wallet_pass(
        event_name="Show",
        event_date="2025-12-31",
        event_time="20:00",
        venue_name="Arena",
        venue_address="123 St",
        attendee_name="Buyer",
        tier_name="GA",
        ticket_id=123,
        qr_token="qr-token-2",
    )
    with zipfile.ZipFile(BytesIO(pass_bytes), "r") as zf:
        pass_json = json.loads(zf.read("pass.json").decode("utf-8"))

    assert pass_json["barcode"]["message"].endswith("/api/tickets/validate/qr-token-2")


def test_stripe_webhook_requires_signature_when_secret_configured(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    r = client.post(
        "/webhooks/stripe",
        content='{"type":"checkout.session.completed","data":{"object":{}}}',
        headers={"Content-Type": "application/json"},
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "Missing Stripe signature"
    get_settings.cache_clear()


def test_stripe_webhook_secret_required_in_production(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    r = client.post(
        "/webhooks/stripe",
        content='{"type":"checkout.session.completed","data":{"object":{}}}',
        headers={"Content-Type": "application/json"},
    )

    assert r.status_code == 500
    assert r.json()["detail"] == "Stripe webhook secret required in production"
    get_settings.cache_clear()


# ============== MCP Endpoint Auth ==============


def test_mcp_tool_call_blocked_without_key(client, mcp_key):
    """MCP tool execution requires x-mcp-key when MCP_API_KEY is set."""
    r = client.post("/mcp/tools/list_events", json={"arguments": {}})
    assert r.status_code == 401

    r = client.post(
        "/mcp/tools/list_events",
        json={"arguments": {}},
        headers={"x-mcp-key": mcp_key},
    )
    assert r.status_code != 401


def test_mcp_voice_action_blocked_without_key(client, mcp_key):
    """Voice action endpoint requires x-mcp-key when MCP_API_KEY is set."""
    r = client.post("/mcp/voice/action", json={"action": "list_events"})
    assert r.status_code == 401

    r = client.post(
        "/mcp/voice/action",
        json={"action": "list_events"},
        headers={"x-mcp-key": mcp_key},
    )
    assert r.status_code != 401


def test_mcp_message_blocked_without_key(client, mcp_key):
    """MCP JSON-RPC message endpoint requires x-mcp-key."""
    r = client.post("/mcp/message", json={"method": "tools/list", "id": 1})
    assert r.status_code == 401

    r = client.post(
        "/mcp/message",
        json={"method": "tools/list", "id": 1},
        headers={"x-mcp-key": mcp_key},
    )
    assert r.status_code != 401


def test_mcp_admin_migrate_blocked_without_key(client, mcp_key):
    """/mcp/admin/migrate requires x-mcp-key."""
    r = client.post("/mcp/admin/migrate")
    assert r.status_code == 401

    r = client.post(
        "/mcp/admin/migrate",
        headers={"x-mcp-key": mcp_key},
    )
    assert r.status_code != 401


def test_mcp_public_paths_allowed_without_key(client, mcp_key):
    """MCP info and dashboard are public even when MCP_API_KEY is set."""
    r = client.get("/mcp")
    assert r.status_code == 200

    r = client.get("/mcp/dashboard")
    # 200 or 404 (dashboard.html may not exist in test), but not 401
    assert r.status_code != 401


def test_mcp_key_via_query_param(client, mcp_key):
    """MCP endpoints accept key via ?mcp_key= query parameter."""
    r = client.post(
        f"/mcp/voice/action?mcp_key={mcp_key}",
        json={"action": "list_events"},
    )
    assert r.status_code != 401


def test_admin_key_does_not_grant_mcp_access(client, monkeypatch):
    """x-admin-key should NOT authenticate MCP endpoints — they use separate keys."""
    monkeypatch.setenv("MCP_API_KEY", "test-mcp-key")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()

    r = client.post(
        "/mcp/voice/action",
        json={"action": "list_events"},
        headers={"x-admin-key": "test-admin-key"},
    )
    assert r.status_code == 401

    r = client.post(
        "/mcp/voice/action",
        json={"action": "list_events"},
        headers={"x-mcp-key": "test-mcp-key"},
    )
    assert r.status_code != 401
    get_settings.cache_clear()
