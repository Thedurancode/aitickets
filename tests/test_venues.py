"""Tests for venue CRUD endpoints."""


class TestListVenues:
    def test_empty(self, client):
        r = client.get("/api/venues")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_venues(self, client, create_venue):
        create_venue(name="Arena A")
        create_venue(name="Arena B")
        r = client.get("/api/venues")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_pagination(self, client, create_venue):
        for i in range(5):
            create_venue(name=f"Venue {i}", address=f"{i} Main St")
        r = client.get("/api/venues?limit=2&offset=0")
        assert len(r.json()) == 2
        r2 = client.get("/api/venues?limit=2&offset=2")
        assert len(r2.json()) == 2
        r3 = client.get("/api/venues?limit=2&offset=4")
        assert len(r3.json()) == 1

    def test_pagination_validation(self, client):
        r = client.get("/api/venues?limit=999")
        assert r.status_code == 422


class TestCreateVenue:
    def test_success(self, client):
        r = client.post("/api/venues", json={"name": "My Venue", "address": "456 Elm"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "My Venue"
        assert data["address"] == "456 Elm"
        assert "id" in data

    def test_missing_name(self, client):
        r = client.post("/api/venues", json={"address": "456 Elm"})
        assert r.status_code == 422


class TestGetVenue:
    def test_found(self, client, create_venue):
        venue = create_venue()
        r = client.get(f"/api/venues/{venue['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Test Arena"

    def test_not_found(self, client):
        r = client.get("/api/venues/99999")
        assert r.status_code == 404


class TestUpdateVenue:
    def test_success(self, client, create_venue):
        venue = create_venue()
        r = client.put(f"/api/venues/{venue['id']}", json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_not_found(self, client):
        r = client.put("/api/venues/99999", json={"name": "X"})
        assert r.status_code == 404


class TestDeleteVenue:
    def test_success(self, client, create_venue):
        venue = create_venue()
        r = client.delete(f"/api/venues/{venue['id']}")
        assert r.status_code == 204
        # Confirm gone
        r2 = client.get(f"/api/venues/{venue['id']}")
        assert r2.status_code == 404

    def test_not_found(self, client):
        r = client.delete("/api/venues/99999")
        assert r.status_code == 404


class TestVenueEvents:
    def test_list_events_for_venue(self, client, create_venue, create_event):
        venue = create_venue()
        create_event(venue_id=venue["id"], name="Event A")
        create_event(venue_id=venue["id"], name="Event B")
        r = client.get(f"/api/venues/{venue['id']}/events")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_venue_not_found(self, client):
        r = client.get("/api/venues/99999/events")
        assert r.status_code == 404
