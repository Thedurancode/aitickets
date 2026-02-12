"""Tests for analytics endpoints."""


class TestEventAnalytics:
    def test_event_analytics(self, client, create_event):
        event = create_event()
        r = client.get(f"/api/analytics/events/{event['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["event_id"] == event["id"]
        assert data["total_views"] == 0

    def test_event_not_found(self, client):
        r = client.get("/api/analytics/events/99999")
        assert r.status_code == 200
        assert "error" in r.json()


class TestAnalyticsOverview:
    def test_overview(self, client):
        r = client.get("/api/analytics/overview")
        assert r.status_code == 200
        data = r.json()
        assert "total_views" in data
        assert "unique_visitors" in data

    def test_custom_days(self, client):
        r = client.get("/api/analytics/overview?days=7")
        assert r.status_code == 200


class TestConversionAnalytics:
    def test_conversion_funnel(self, client, create_event):
        event = create_event()
        r = client.get(f"/api/analytics/events/{event['id']}/conversions")
        assert r.status_code == 200
        data = r.json()
        assert "funnel" in data
        assert "conversion_rate_percent" in data


class TestPageViewTracking:
    def test_track_page_view(self, client, create_event):
        event = create_event()
        r = client.post("/api/analytics/track", json={
            "event_id": event["id"],
            "page": "detail",
        })
        assert r.status_code == 204

        # Verify it was tracked
        r2 = client.get(f"/api/analytics/events/{event['id']}?days=1")
        assert r2.json()["total_views"] == 1
