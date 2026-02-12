"""Tests for the flyer style library."""

from unittest.mock import patch


class TestFlyerStyleCRUD:
    """Tests for /api/flyer-styles/ CRUD endpoints."""

    def test_list_empty(self, client):
        r = client.get("/api/flyer-styles/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_style(self, client):
        r = client.post("/api/flyer-styles/", json={
            "name": "Neon Night",
            "description": "Dark background with neon glow effects and bold typography",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Neon Night"
        assert data["image_url"] is None

    def test_create_duplicate_name(self, client):
        client.post("/api/flyer-styles/", json={"name": "Retro", "description": "80s style"})
        r = client.post("/api/flyer-styles/", json={"name": "Retro", "description": "different"})
        assert r.status_code == 400

    def test_get_style(self, client):
        cr = client.post("/api/flyer-styles/", json={"name": "Bold", "description": "Bold colors"})
        style_id = cr.json()["id"]
        r = client.get(f"/api/flyer-styles/{style_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Bold"

    def test_get_not_found(self, client):
        r = client.get("/api/flyer-styles/99999")
        assert r.status_code == 404

    def test_update_style(self, client):
        cr = client.post("/api/flyer-styles/", json={"name": "A", "description": "B"})
        style_id = cr.json()["id"]
        r = client.put(f"/api/flyer-styles/{style_id}", json={"description": "Updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "Updated"
        assert r.json()["name"] == "A"

    def test_update_name_uniqueness(self, client):
        client.post("/api/flyer-styles/", json={"name": "X", "description": "first"})
        cr2 = client.post("/api/flyer-styles/", json={"name": "Y", "description": "second"})
        r = client.put(f"/api/flyer-styles/{cr2.json()['id']}", json={"name": "X"})
        assert r.status_code == 400

    def test_delete_style(self, client):
        cr = client.post("/api/flyer-styles/", json={"name": "Del", "description": "Me"})
        style_id = cr.json()["id"]
        r = client.delete(f"/api/flyer-styles/{style_id}")
        assert r.status_code == 200
        r2 = client.get(f"/api/flyer-styles/{style_id}")
        assert r2.status_code == 404

    def test_delete_not_found(self, client):
        r = client.delete("/api/flyer-styles/99999")
        assert r.status_code == 404

    def test_list_returns_created_styles(self, client):
        client.post("/api/flyer-styles/", json={"name": "Alpha", "description": "a"})
        client.post("/api/flyer-styles/", json={"name": "Beta", "description": "b"})
        r = client.get("/api/flyer-styles/")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Alpha" in names
        assert "Beta" in names


class TestGenerateFlyerWithStyle:
    """Tests for generate-flyer endpoint with style_id."""

    @patch("app.services.flyer_generator.generate_flyer")
    def test_generate_with_style_id(self, mock_gen, client, create_event):
        mock_gen.return_value = {
            "success": True,
            "filename": "f.png",
            "image_url": "/uploads/f.png",
        }
        style = client.post("/api/flyer-styles/", json={
            "name": "Bold", "description": "Bold vibrant colors"
        }).json()
        event = create_event()
        r = client.post(
            f"/api/events/{event['id']}/generate-flyer",
            json={"style_id": style["id"]},
        )
        assert r.status_code == 200
        assert r.json()["image_url"] == "/uploads/f.png"
        # Verify the style description was included in the prompt
        call_args = mock_gen.call_args
        prompt = call_args[0][0]
        assert "Bold vibrant colors" in prompt

    def test_generate_with_invalid_style_id(self, client, create_event):
        event = create_event()
        r = client.post(
            f"/api/events/{event['id']}/generate-flyer",
            json={"style_id": 99999},
        )
        assert r.status_code == 404
        assert "style" in r.json()["detail"].lower()
