"""Tests for AI flyer generation endpoint and prompt builder."""

from unittest.mock import patch


class TestBuildFlyerPrompt:
    """Unit tests for prompt construction."""

    def test_basic_prompt(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Jazz Night",
            event_date="2025-12-31",
            event_time="20:00",
        )
        assert "Jazz Night" in prompt
        assert "2025-12-31" in prompt
        assert "20:00" in prompt

    def test_includes_venue(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Concert",
            event_date="2025-06-15",
            event_time="19:00",
            venue_name="The Grand Hall",
            venue_address="123 Main St",
        )
        assert "The Grand Hall" in prompt
        assert "123 Main St" in prompt

    def test_includes_tiers_with_prices_in_cents(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Show",
            event_date="2025-01-01",
            event_time="18:00",
            tiers=[
                {"name": "GA", "price": 5000},
                {"name": "VIP", "price": 15000},
            ],
        )
        assert "GA" in prompt
        assert "$50.00" in prompt
        assert "VIP" in prompt
        assert "$150.00" in prompt

    def test_free_tier(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Free Show",
            event_date="2025-01-01",
            event_time="12:00",
            tiers=[{"name": "Free Entry", "price": 0}],
        )
        assert "Free" in prompt

    def test_style_instructions_appended(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Party",
            event_date="2025-03-01",
            event_time="21:00",
            style_instructions="Retro 80s neon aesthetic",
        )
        assert "Retro 80s neon aesthetic" in prompt

    def test_truncates_long_description(self):
        from app.services.flyer_generator import build_flyer_prompt

        long_desc = "A" * 500
        prompt = build_flyer_prompt(
            event_name="Test",
            event_date="2025-01-01",
            event_time="12:00",
            description=long_desc,
        )
        assert "A" * 300 + "..." in prompt

    def test_org_name_included(self):
        from app.services.flyer_generator import build_flyer_prompt

        prompt = build_flyer_prompt(
            event_name="Gala",
            event_date="2025-05-01",
            event_time="19:00",
            org_name="ACME Corp",
        )
        assert "ACME Corp" in prompt


class TestGenerateFlyerEndpoint:
    """Tests for POST /api/events/{event_id}/generate-flyer"""

    def test_event_not_found(self, client):
        r = client.post("/api/events/99999/generate-flyer")
        assert r.status_code == 404

    def test_missing_api_key(self, client, create_event):
        event = create_event()
        r = client.post(f"/api/events/{event['id']}/generate-flyer")
        assert r.status_code == 502
        assert "not configured" in r.json()["detail"].lower()

    @patch("app.services.flyer_generator.generate_flyer")
    def test_success(self, mock_generate, client, create_event):
        mock_generate.return_value = {
            "success": True,
            "filename": "flyer_abc123.png",
            "image_url": "/uploads/flyer_abc123.png",
        }
        event = create_event()
        r = client.post(f"/api/events/{event['id']}/generate-flyer")
        assert r.status_code == 200
        data = r.json()
        assert data["image_url"] == "/uploads/flyer_abc123.png"
        mock_generate.assert_called_once()

    @patch("app.services.flyer_generator.generate_flyer")
    def test_with_style_instructions(self, mock_generate, client, create_event):
        mock_generate.return_value = {
            "success": True,
            "filename": "flyer_xyz.png",
            "image_url": "/uploads/flyer_xyz.png",
        }
        event = create_event()
        r = client.post(
            f"/api/events/{event['id']}/generate-flyer",
            json={"style_instructions": "Dark theme with neon accents"},
        )
        assert r.status_code == 200
        assert r.json()["image_url"] == "/uploads/flyer_xyz.png"

    @patch("app.services.flyer_generator.generate_flyer")
    def test_generation_failure(self, mock_generate, client, create_event):
        mock_generate.return_value = {
            "success": False,
            "error": "Gemini API rate limited",
        }
        event = create_event()
        r = client.post(f"/api/events/{event['id']}/generate-flyer")
        assert r.status_code == 502
        assert "rate limited" in r.json()["detail"].lower()
