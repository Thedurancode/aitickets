"""Tests for health check, global error handlers, and misc endpoints."""


class TestHealthCheck:
    def test_healthy(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["checks"]["db"] == "ok"


class TestGlobalErrorHandler:
    def test_validation_error_format(self, client):
        """Validation errors should return consistent {error, detail} format."""
        r = client.get("/api/events?limit=999")
        assert r.status_code == 422
        data = r.json()
        assert "error" in data
        assert "detail" in data
        assert data["error"] == "Validation error"

    def test_404_format(self, client):
        """404s from HTTPException should include detail."""
        r = client.get("/api/events/99999")
        assert r.status_code == 404
        assert "detail" in r.json()


class TestRootRedirect:
    def test_redirects_to_events(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 307
        assert "/events" in r.headers["location"]


class TestPurchasePages:
    def test_success_page(self, client):
        r = client.get("/purchase-success?session_id=test123")
        assert r.status_code == 200
        assert "You're In" in r.text

    def test_cancelled_page(self, client):
        r = client.get("/purchase-cancelled")
        assert r.status_code == 200
        assert "Cancelled" in r.text
