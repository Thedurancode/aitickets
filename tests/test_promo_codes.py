"""Tests for promo code endpoints."""


class TestCreatePromoCode:
    def test_percent_discount(self, client):
        r = client.post("/api/promo-codes/", json={
            "code": "SAVE20",
            "discount_type": "percent",
            "discount_value": 20,
        })
        assert r.status_code == 201
        assert r.json()["code"] == "SAVE20"

    def test_fixed_discount(self, client):
        r = client.post("/api/promo-codes/", json={
            "code": "FLAT500",
            "discount_type": "fixed_cents",
            "discount_value": 500,
        })
        assert r.status_code == 201

    def test_duplicate_code(self, client):
        client.post("/api/promo-codes/", json={
            "code": "DUP",
            "discount_type": "percent",
            "discount_value": 10,
        })
        r = client.post("/api/promo-codes/", json={
            "code": "dup",  # case-insensitive
            "discount_type": "percent",
            "discount_value": 10,
        })
        assert r.status_code == 400

    def test_invalid_percent(self, client):
        r = client.post("/api/promo-codes/", json={
            "code": "BAD",
            "discount_type": "percent",
            "discount_value": 150,
        })
        assert r.status_code == 400


class TestValidatePromoCode:
    def test_valid_code(self, client, create_event):
        event = create_event()
        tier = client.post(f"/api/events/{event['id']}/tiers", json={
            "name": "GA",
            "price": 5000,
            "quantity_available": 100,
        }).json()

        client.post("/api/promo-codes/", json={
            "code": "HALF",
            "discount_type": "percent",
            "discount_value": 50,
        })

        r = client.post(f"/api/promo-codes/validate?code=HALF&ticket_tier_id={tier['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert data["discounted_price_cents"] == 2500

    def test_invalid_code(self, client, create_tier):
        tier = create_tier()
        r = client.post(f"/api/promo-codes/validate?code=NOPE&ticket_tier_id={tier['id']}")
        assert r.status_code == 200
        assert r.json()["valid"] is False


class TestDeactivatePromoCode:
    def test_success(self, client):
        promo = client.post("/api/promo-codes/", json={
            "code": "TEMP",
            "discount_type": "percent",
            "discount_value": 10,
        }).json()
        r = client.delete(f"/api/promo-codes/{promo['id']}")
        assert r.status_code == 200
        assert "deactivated" in r.json()["message"].lower()
