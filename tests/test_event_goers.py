"""Tests for event goer CRUD endpoints."""


class TestListEventGoers:
    def test_empty(self, client):
        r = client.get("/api/event-goers")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_goers(self, client, create_event_goer):
        create_event_goer(name="Alice")
        create_event_goer(name="Bob")
        r = client.get("/api/event-goers")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_pagination(self, client, create_event_goer):
        for i in range(5):
            create_event_goer(name=f"User {i}", email=f"u{i}@test.com")
        r = client.get("/api/event-goers?limit=2")
        assert len(r.json()) == 2
        r2 = client.get("/api/event-goers?limit=10&offset=3")
        assert len(r2.json()) == 2


class TestCreateEventGoer:
    def test_success(self, client):
        r = client.post("/api/event-goers", json={
            "email": "alice@example.com",
            "name": "Alice",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "alice@example.com"
        assert data["name"] == "Alice"
        assert data["email_opt_in"] is True

    def test_duplicate_email(self, client, create_event_goer):
        create_event_goer(email="dup@example.com")
        r = client.post("/api/event-goers", json={
            "email": "dup@example.com",
            "name": "Duplicate",
        })
        assert r.status_code == 400

    def test_invalid_email(self, client):
        r = client.post("/api/event-goers", json={
            "email": "not-an-email",
            "name": "Bad",
        })
        assert r.status_code == 422


class TestGetEventGoer:
    def test_found(self, client, create_event_goer):
        goer = create_event_goer()
        r = client.get(f"/api/event-goers/{goer['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == goer["id"]

    def test_not_found(self, client):
        r = client.get("/api/event-goers/99999")
        assert r.status_code == 404


class TestUpdateEventGoer:
    def test_success(self, client, create_event_goer):
        goer = create_event_goer()
        r = client.put(f"/api/event-goers/{goer['id']}", json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_not_found(self, client):
        r = client.put("/api/event-goers/99999", json={"name": "X"})
        assert r.status_code == 404
