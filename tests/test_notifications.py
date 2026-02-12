"""Tests for notification history and preference endpoints."""


class TestNotificationHistory:
    def test_empty(self, client):
        r = client.get("/api/notifications/history")
        assert r.status_code == 200
        assert r.json() == []

    def test_pagination_params(self, client):
        r = client.get("/api/notifications/history?limit=10&offset=0")
        assert r.status_code == 200

    def test_filter_by_type(self, client):
        r = client.get("/api/notifications/history?notification_type=ticket_confirmation")
        assert r.status_code == 200


class TestNotificationPreferences:
    def test_get_preferences(self, client, create_event_goer):
        goer = create_event_goer()
        r = client.get(f"/api/notifications/preferences/{goer['id']}")
        assert r.status_code == 200
        assert r.json()["email_opt_in"] is True

    def test_update_preferences(self, client, create_event_goer):
        goer = create_event_goer()
        r = client.put(f"/api/notifications/preferences/{goer['id']}", json={
            "marketing_opt_in": True,
        })
        assert r.status_code == 200
        assert r.json()["marketing_opt_in"] is True

    def test_not_found(self, client):
        r = client.get("/api/notifications/preferences/99999")
        assert r.status_code == 404


class TestUnsubscribe:
    def test_unsubscribe(self, client, create_event_goer):
        goer = create_event_goer(email="unsub@example.com")
        r = client.get("/api/notifications/unsubscribe?email=unsub@example.com")
        assert r.status_code == 200

    def test_unsubscribe_unknown_email(self, client):
        r = client.get("/api/notifications/unsubscribe?email=nobody@example.com")
        assert r.status_code == 200  # graceful no-op
