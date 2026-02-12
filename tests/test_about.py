"""Tests for the About Us page API and voice-controlled content management."""

import json


# ============== API CRUD Tests ==============

class TestAboutAPI:
    def test_get_about_empty(self, client):
        """GET /api/about returns empty dict when no sections exist."""
        r = client.get("/api/about")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_update_section(self, client):
        """PUT /api/about/{key} creates/updates a section."""
        r = client.put("/api/about/mission_content", json={"content": "We love events!"})
        assert r.status_code == 200
        data = r.json()
        assert data["section_key"] == "mission_content"
        assert data["content"] == "We love events!"

    def test_update_section_persists(self, client):
        """Updated section appears in GET."""
        client.put("/api/about/hero_title", json={"content": "Welcome!"})
        r = client.get("/api/about")
        assert r.json()["hero_title"] == "Welcome!"

    def test_update_section_overwrite(self, client):
        """PUT twice overwrites the value."""
        client.put("/api/about/mission_content", json={"content": "Version 1"})
        client.put("/api/about/mission_content", json={"content": "Version 2"})
        r = client.get("/api/about")
        assert r.json()["mission_content"] == "Version 2"

    def test_update_invalid_key(self, client):
        """PUT with invalid key returns 400."""
        r = client.put("/api/about/invalid_key", json={"content": "test"})
        assert r.status_code == 400
        assert "Invalid section key" in r.json()["detail"]

    def test_update_multiple_sections(self, client):
        """Can update multiple different sections."""
        client.put("/api/about/hero_title", json={"content": "Hello"})
        client.put("/api/about/hero_subtitle", json={"content": "World"})
        client.put("/api/about/contact_email", json={"content": "hi@example.com"})
        r = client.get("/api/about")
        data = r.json()
        assert data["hero_title"] == "Hello"
        assert data["hero_subtitle"] == "World"
        assert data["contact_email"] == "hi@example.com"


# ============== Team Member Tests ==============

class TestTeamMembers:
    def test_add_team_member(self, client):
        """POST /api/about/team-member adds a member."""
        r = client.post("/api/about/team-member", json={"name": "Jane Doe", "role": "CEO"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["team_members"]) == 1
        assert data["team_members"][0]["name"] == "Jane Doe"
        assert data["team_members"][0]["role"] == "CEO"

    def test_add_team_member_with_bio(self, client):
        """Team member with optional bio and photo_url."""
        r = client.post("/api/about/team-member", json={
            "name": "John Smith",
            "role": "CTO",
            "bio": "Loves tech",
            "photo_url": "https://example.com/john.jpg",
        })
        assert r.status_code == 200
        member = r.json()["team_members"][0]
        assert member["bio"] == "Loves tech"
        assert member["photo_url"] == "https://example.com/john.jpg"

    def test_add_multiple_members(self, client):
        """Adding multiple members accumulates."""
        client.post("/api/about/team-member", json={"name": "Alice", "role": "CEO"})
        r = client.post("/api/about/team-member", json={"name": "Bob", "role": "CTO"})
        assert len(r.json()["team_members"]) == 2

    def test_remove_team_member(self, client):
        """DELETE /api/about/team-member/{name} removes a member."""
        client.post("/api/about/team-member", json={"name": "Alice", "role": "CEO"})
        client.post("/api/about/team-member", json={"name": "Bob", "role": "CTO"})
        r = client.delete("/api/about/team-member/Alice")
        assert r.status_code == 200
        assert len(r.json()["team_members"]) == 1
        assert r.json()["team_members"][0]["name"] == "Bob"

    def test_remove_case_insensitive(self, client):
        """Removal is case-insensitive."""
        client.post("/api/about/team-member", json={"name": "Alice", "role": "CEO"})
        r = client.delete("/api/about/team-member/alice")
        assert r.status_code == 200
        assert len(r.json()["team_members"]) == 0

    def test_remove_not_found(self, client):
        """Removing non-existent member returns 404."""
        client.post("/api/about/team-member", json={"name": "Alice", "role": "CEO"})
        r = client.delete("/api/about/team-member/Nobody")
        assert r.status_code == 404

    def test_remove_no_members(self, client):
        """Removing from empty team returns 404."""
        r = client.delete("/api/about/team-member/Nobody")
        assert r.status_code == 404

    def test_team_in_get_about(self, client):
        """Team members appear in GET /api/about as JSON."""
        client.post("/api/about/team-member", json={"name": "Ed", "role": "Founder"})
        r = client.get("/api/about")
        members = json.loads(r.json()["team_members"])
        assert len(members) == 1
        assert members[0]["name"] == "Ed"


# ============== Public Page Tests ==============

class TestAboutPage:
    def test_about_page_renders(self, client):
        """GET /about returns HTML."""
        r = client.get("/about")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_about_page_shows_content(self, client):
        """Content set via API appears on the HTML page."""
        client.put("/api/about/hero_title", json={"content": "Welcome to Raptors HQ"})
        client.put("/api/about/mission_content", json={"content": "Bringing fans closer"})
        r = client.get("/about")
        assert "Welcome to Raptors HQ" in r.text
        assert "Bringing fans closer" in r.text

    def test_about_page_shows_team(self, client):
        """Team members appear on the HTML page."""
        client.post("/api/about/team-member", json={"name": "Test Person", "role": "Manager"})
        r = client.get("/about")
        assert "Test Person" in r.text
        assert "Manager" in r.text
