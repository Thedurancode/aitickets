"""Tests for event CRUD endpoints."""


class TestListEvents:
    def test_empty(self, client):
        r = client.get("/api/events")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_events_with_venue(self, client, create_event):
        create_event(name="Concert")
        r = client.get("/api/events")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "Concert"
        assert "venue" in data[0]

    def test_pagination(self, client, create_venue, create_event):
        venue = create_venue()
        for i in range(5):
            create_event(venue_id=venue["id"], name=f"Event {i}")
        r = client.get("/api/events?limit=2")
        assert len(r.json()) == 2
        r2 = client.get("/api/events?limit=2&offset=4")
        assert len(r2.json()) == 1


class TestCreateEvent:
    def test_success(self, client, create_venue):
        venue = create_venue()
        r = client.post("/api/events", json={
            "name": "New Show",
            "event_date": "2025-12-25",
            "event_time": "19:00",
            "venue_id": venue["id"],
        })
        assert r.status_code == 201
        assert r.json()["name"] == "New Show"

    def test_venue_not_found(self, client):
        r = client.post("/api/events", json={
            "name": "Orphan Event",
            "event_date": "2025-12-25",
            "event_time": "19:00",
            "venue_id": 99999,
        })
        assert r.status_code == 404

    def test_missing_fields(self, client):
        r = client.post("/api/events", json={"name": "Incomplete"})
        assert r.status_code == 422


class TestGetEvent:
    def test_found(self, client, create_event):
        event = create_event(name="Detail Test")
        r = client.get(f"/api/events/{event['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Detail Test"
        assert "venue" in data
        assert "ticket_tiers" in data

    def test_not_found(self, client):
        r = client.get("/api/events/99999")
        assert r.status_code == 404


class TestUpdateEvent:
    def test_success(self, client, create_event):
        event = create_event()
        r = client.put(f"/api/events/{event['id']}", json={"name": "Updated Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    def test_not_found(self, client):
        r = client.put("/api/events/99999", json={"name": "X"})
        assert r.status_code == 404


class TestDeleteEvent:
    def test_success(self, client, create_event):
        event = create_event()
        r = client.delete(f"/api/events/{event['id']}")
        assert r.status_code == 204

    def test_not_found(self, client):
        r = client.delete("/api/events/99999")
        assert r.status_code == 404
