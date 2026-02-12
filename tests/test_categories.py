"""Tests for event category endpoints."""


class TestListCategories:
    def test_empty(self, client):
        r = client.get("/api/categories/")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_categories(self, client):
        client.post("/api/categories/", json={"name": "Music"})
        client.post("/api/categories/", json={"name": "Sports"})
        r = client.get("/api/categories/")
        assert len(r.json()) == 2


class TestCreateCategory:
    def test_success(self, client):
        r = client.post("/api/categories/", json={"name": "Comedy", "color": "#FF0000"})
        assert r.status_code == 201
        assert r.json()["name"] == "Comedy"

    def test_duplicate_name(self, client):
        client.post("/api/categories/", json={"name": "Music"})
        r = client.post("/api/categories/", json={"name": "Music"})
        assert r.status_code == 400


class TestUpdateCategory:
    def test_success(self, client):
        cat = client.post("/api/categories/", json={"name": "Old"}).json()
        r = client.put(f"/api/categories/{cat['id']}", json={"name": "New"})
        assert r.status_code == 200
        assert r.json()["name"] == "New"

    def test_not_found(self, client):
        r = client.put("/api/categories/99999", json={"name": "X"})
        assert r.status_code == 404


class TestDeleteCategory:
    def test_success(self, client):
        cat = client.post("/api/categories/", json={"name": "Temp"}).json()
        r = client.delete(f"/api/categories/{cat['id']}")
        assert r.status_code == 200

    def test_not_found(self, client):
        r = client.delete("/api/categories/99999")
        assert r.status_code == 404

    def test_cannot_delete_in_use(self, client, create_venue):
        cat = client.post("/api/categories/", json={"name": "InUse"}).json()
        venue = create_venue()
        client.post("/api/events", json={
            "name": "Categorized Event",
            "event_date": "2025-06-01",
            "event_time": "18:00",
            "venue_id": venue["id"],
            "category_ids": [cat["id"]],
        })
        r = client.delete(f"/api/categories/{cat['id']}")
        assert r.status_code == 400
