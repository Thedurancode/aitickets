"""Tests for ticket tier CRUD endpoints."""


class TestListTiers:
    def test_empty(self, client, create_event):
        event = create_event()
        r = client.get(f"/api/events/{event['id']}/tiers")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_tiers_with_availability(self, client, create_event):
        event = create_event()
        client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "VIP",
            "price": 5000,
            "quantity_available": 20,
        })
        r = client.get(f"/api/events/{event['id']}/tiers")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["tickets_remaining"] == 20

    def test_event_not_found(self, client):
        r = client.get("/api/events/99999/tiers")
        assert r.status_code == 404


class TestCreateTier:
    def test_success(self, client, create_event):
        event = create_event()
        r = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "GA",
            "price": 2500,
            "quantity_available": 100,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "GA"
        assert data["price"] == 2500
        assert data["quantity_sold"] == 0


class TestUpdateTier:
    def test_success(self, client, create_tier):
        tier = create_tier()
        r = client.put(f"/api/tiers/{tier['id']}", json={"name": "Updated GA"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated GA"

    def test_not_found(self, client):
        r = client.put("/api/tiers/99999", json={"name": "X"})
        assert r.status_code == 404


class TestDeleteTier:
    def test_success(self, client, create_tier):
        tier = create_tier()
        r = client.delete(f"/api/tiers/{tier['id']}")
        assert r.status_code == 204

    def test_not_found(self, client):
        r = client.delete("/api/tiers/99999")
        assert r.status_code == 404

    def test_cannot_delete_with_sold_tickets(self, client, create_event):
        event = create_event()
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "Free",
            "price": 0,
            "quantity_available": 10,
        }).json()

        # Buy a ticket
        client.post(f"/api/tickets/events/{event['id']}/purchase", json={
            "ticket_tier_id": tier["id"],
            "email": "a@b.com",
            "name": "Buyer",
        })

        # Try to delete — should fail
        r = client.delete(f"/api/tiers/{tier['id']}")
        assert r.status_code == 400
        assert "sold" in r.json()["detail"].lower()
