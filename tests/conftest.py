"""Shared fixtures for all tests.

Uses an in-memory SQLite database so tests are fast and isolated.
The database is recreated for every test function.
"""

import os

# Force SQLite in-memory before any app imports
os.environ["DATABASE_URL"] = "sqlite:///./test_tickets.db"
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["RESEND_API_KEY"] = ""
os.environ["TWILIO_ACCOUNT_SID"] = ""
os.environ["MCP_API_KEY"] = ""
os.environ["ADMIN_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_tickets.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a transactional database session for test helpers."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """TestClient that uses the test database."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ============== Factory helpers ==============

@pytest.fixture
def create_venue(client):
    """Factory to create a venue and return its JSON."""

    def _create(**overrides):
        data = {"name": "Test Arena", "address": "123 Test St"}
        data.update(overrides)
        r = client.post("/api/venues", json=data)
        assert r.status_code == 201, r.text
        return r.json()

    return _create


@pytest.fixture
def create_event(client, create_venue):
    """Factory to create an event (auto-creates a venue)."""

    def _create(venue_id=None, **overrides):
        if venue_id is None:
            venue_id = create_venue()["id"]
        data = {
            "name": "Test Event",
            "event_date": "2025-12-31",
            "event_time": "20:00",
            "venue_id": venue_id,
        }
        data.update(overrides)
        r = client.post("/api/events", json=data)
        assert r.status_code == 201, r.text
        return r.json()

    return _create


@pytest.fixture
def create_tier(client, create_event):
    """Factory to create a ticket tier (auto-creates event)."""

    def _create(event_id=None, **overrides):
        if event_id is None:
            event_id = create_event()["id"]
        data = {
            "name": "General Admission",
            "price": 0,
            "quantity_available": 100,
        }
        data.update(overrides)
        r = client.post(f"/api/events/{event_id}/tiers", json=data)
        assert r.status_code == 201, r.text
        return r.json()

    return _create


@pytest.fixture
def create_event_goer(client):
    """Factory to create an event goer."""

    _counter = [0]

    def _create(**overrides):
        _counter[0] += 1
        data = {
            "email": f"test{_counter[0]}@example.com",
            "name": f"Test User {_counter[0]}",
        }
        data.update(overrides)
        r = client.post("/api/event-goers", json=data)
        assert r.status_code == 201, r.text
        return r.json()

    return _create
