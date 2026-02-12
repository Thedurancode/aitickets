"""Tests for ticket purchase and validation endpoints."""


class TestFreePurchase:
    """Free ticket flow (price=0) skips Stripe entirely."""

    def test_success(self, client, create_event, create_event_goer):
        event = create_event()
        # Create a free tier
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "Free GA",
            "price": 0,
            "quantity_available": 50,
        }).json()

        r = client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": tier["id"],
            "email": "buyer@example.com",
            "name": "Test Buyer",
            "quantity": 2,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["message"] is not None
        assert len(data["tickets"]) == 2
        assert data["tickets"][0]["qr_token"] is not None

    def test_exceeds_availability(self, client, create_event):
        event = create_event()
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "Limited",
            "price": 0,
            "quantity_available": 1,
        }).json()

        r = client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": tier["id"],
            "email": "buyer@example.com",
            "name": "Buyer",
            "quantity": 5,
        })
        assert r.status_code == 400
        assert "available" in r.json()["detail"].lower()

    def test_event_not_found(self, client):
        r = client.post("/api/tickets/events/99999/purchase", json={
            "ticket_tier_id": 1,
            "email": "a@b.com",
            "name": "X",
        })
        assert r.status_code == 404

    def test_tier_not_found(self, client, create_event):
        event = create_event()
        r = client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": 99999,
            "email": "a@b.com",
            "name": "X",
        })
        assert r.status_code == 404


class TestGetTicket:
    def test_found(self, client, create_event):
        event = create_event()
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "Free",
            "price": 0,
            "quantity_available": 10,
        }).json()

        purchase = client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": tier["id"],
            "email": "view@example.com",
            "name": "Viewer",
        }).json()

        ticket_id = purchase["tickets"][0]["id"]
        r = client.get(f"/api/tickets/{ticket_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "paid"
        assert data["event"]["name"] == event["name"]

    def test_not_found(self, client):
        r = client.get("/api/tickets/99999")
        assert r.status_code == 404


class TestValidateTicket:
    def test_valid_checkin(self, client, create_event):
        event = create_event()
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "Free",
            "price": 0,
            "quantity_available": 10,
        }).json()

        purchase = client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": tier["id"],
            "email": "checkin@example.com",
            "name": "Check In",
        }).json()

        qr_token = purchase["tickets"][0]["qr_token"]

        # First check-in should succeed
        r = client.post(f"/api/tickets/validate/{qr_token}")
        assert r.status_code == 200
        assert r.json()["valid"] is True

        # Second check-in should fail
        r2 = client.post(f"/api/tickets/validate/{qr_token}")
        assert r2.status_code == 200
        assert r2.json()["valid"] is False
        assert "already checked in" in r2.json()["message"].lower()

    def test_invalid_token(self, client):
        r = client.post("/api/tickets/validate/bogus-token")
        assert r.status_code == 200
        assert r.json()["valid"] is False
