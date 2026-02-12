"""Tests for RAG knowledge base endpoints and service."""

import json
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest


# ============== Helper: fake embedding ==============

FAKE_EMBEDDING = [0.1] * 1536  # text-embedding-3-small returns 1536-dim vectors


def fake_embed_texts(texts):
    """Return deterministic fake embeddings for testing."""
    return [FAKE_EMBEDDING for _ in texts]


# ============== Paste Endpoint ==============

class TestPasteContent:
    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_paste_success(self, mock_embed, client):
        r = client.post("/api/knowledge/paste", json={
            "title": "Parking FAQ",
            "content": "Free parking is available in Lot A after 5pm.",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Parking FAQ"
        assert data["content_type"] == "paste"
        assert data["chunks_created"] >= 1

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_paste_with_venue(self, mock_embed, client, create_venue):
        venue = create_venue()
        r = client.post("/api/knowledge/paste", json={
            "title": "Venue Guide",
            "content": "The venue has 3 floors with elevator access.",
            "venue_id": venue["id"],
        })
        assert r.status_code == 201
        assert r.json()["id"] is not None

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_paste_with_event(self, mock_embed, client, create_event):
        event = create_event()
        r = client.post("/api/knowledge/paste", json={
            "title": "Event Info",
            "content": "Doors open at 6pm. No outside food allowed.",
            "event_id": event["id"],
        })
        assert r.status_code == 201

    def test_paste_empty_content(self, client):
        r = client.post("/api/knowledge/paste", json={
            "title": "Empty",
            "content": "   ",
        })
        assert r.status_code == 400


# ============== Upload Endpoint ==============

class TestUploadDocument:
    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_upload_txt(self, mock_embed, client):
        content = b"This is a test text file with venue information."
        r = client.post(
            "/api/knowledge/upload",
            data={"title": "Test Doc"},
            files={"file": ("test.txt", BytesIO(content), "text/plain")},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["content_type"] == "txt"
        assert data["chunks_created"] >= 1

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_upload_md(self, mock_embed, client):
        content = b"# Venue Guide\n\nParking is available in Lot B."
        r = client.post(
            "/api/knowledge/upload",
            data={"title": "Markdown Doc"},
            files={"file": ("guide.md", BytesIO(content), "text/markdown")},
        )
        assert r.status_code == 201
        assert r.json()["content_type"] == "md"

    def test_upload_unsupported_type(self, client):
        r = client.post(
            "/api/knowledge/upload",
            data={"title": "Bad File"},
            files={"file": ("test.jpg", BytesIO(b"fake"), "image/jpeg")},
        )
        assert r.status_code == 400
        assert "Unsupported" in r.json()["detail"]

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_upload_with_venue_id(self, mock_embed, client, create_venue):
        venue = create_venue()
        r = client.post(
            "/api/knowledge/upload",
            data={"title": "Venue Doc", "venue_id": str(venue["id"])},
            files={"file": ("info.txt", BytesIO(b"Info about the venue"), "text/plain")},
        )
        assert r.status_code == 201


# ============== List Endpoint ==============

class TestListDocuments:
    def test_empty(self, client):
        r = client.get("/api/knowledge/")
        assert r.status_code == 200
        assert r.json() == []

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_list_all(self, mock_embed, client):
        client.post("/api/knowledge/paste", json={"title": "Doc 1", "content": "Content 1"})
        client.post("/api/knowledge/paste", json={"title": "Doc 2", "content": "Content 2"})
        r = client.get("/api/knowledge/")
        assert len(r.json()) == 2

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_filter_by_venue(self, mock_embed, client, create_venue):
        venue = create_venue()
        client.post("/api/knowledge/paste", json={"title": "V Doc", "content": "venue content", "venue_id": venue["id"]})
        client.post("/api/knowledge/paste", json={"title": "Other", "content": "other content"})
        r = client.get(f"/api/knowledge/?venue_id={venue['id']}")
        assert len(r.json()) == 1
        assert r.json()[0]["title"] == "V Doc"


# ============== Delete Endpoint ==============

class TestDeleteDocument:
    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_delete_success(self, mock_embed, client):
        doc = client.post("/api/knowledge/paste", json={"title": "Temp", "content": "temp content"}).json()
        r = client.delete(f"/api/knowledge/{doc['id']}")
        assert r.status_code == 200
        # Verify it's gone
        r2 = client.get("/api/knowledge/")
        assert len(r2.json()) == 0

    def test_delete_not_found(self, client):
        r = client.delete("/api/knowledge/99999")
        assert r.status_code == 404


# ============== Search Endpoint ==============

class TestSearchKnowledge:
    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_search_returns_results(self, mock_embed, client):
        client.post("/api/knowledge/paste", json={
            "title": "Parking Info",
            "content": "Free parking available in Lot A after 5pm. Paid parking in Lot B costs $10.",
        })
        r = client.get("/api/knowledge/search?q=parking")
        assert r.status_code == 200
        data = r.json()
        assert data["query"] == "parking"
        assert len(data["results"]) >= 1

    @patch("app.services.rag._embed_texts", side_effect=fake_embed_texts)
    def test_search_empty_kb(self, mock_embed, client):
        r = client.get("/api/knowledge/search?q=parking")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_search_missing_query(self, client):
        r = client.get("/api/knowledge/search")
        assert r.status_code == 422


# ============== RAG Service Unit Tests ==============

class TestChunking:
    def test_chunk_short_text(self):
        from app.services.rag import _chunk_text
        result = _chunk_text("Hello world")
        assert result == ["Hello world"]

    def test_chunk_empty(self):
        from app.services.rag import _chunk_text
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    def test_chunk_long_text(self):
        from app.services.rag import _chunk_text
        text = "A" * 1200
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 3
        # Verify overlap: end of chunk N should overlap with start of chunk N+1
        for i in range(len(chunks) - 1):
            # The overlap means each successive chunk starts 450 chars after the previous
            assert len(chunks[i]) <= 500


class TestCosineSimilarity:
    def test_identical_vectors(self):
        from app.services.rag import _cosine_similarity
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        from app.services.rag import _cosine_similarity
        assert abs(_cosine_similarity([1, 0, 0], [0, 1, 0])) < 1e-6

    def test_zero_vector(self):
        from app.services.rag import _cosine_similarity
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0
