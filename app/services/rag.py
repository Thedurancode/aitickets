"""RAG (Retrieval-Augmented Generation) service for knowledge base.

Handles text chunking, embedding via OpenAI, and cosine similarity search.
"""

import json
import logging
import math
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "text-embedding-3-small"


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def _get_openai_client():
    """Get OpenAI client, raising clear error if no key configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured — cannot generate embeddings")
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using OpenAI."""
    if not texts:
        return []
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def ingest_text(text: str, document_id: int, db: Session) -> int:
    """Chunk text, embed via OpenAI, and store chunks. Returns chunk count."""
    chunks = _chunk_text(text)
    if not chunks:
        return 0

    embeddings = _embed_texts(chunks)

    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = KnowledgeChunk(
            document_id=document_id,
            content=chunk_text,
            embedding=json.dumps(embedding),
            chunk_index=i,
        )
        db.add(chunk)

    db.commit()
    return len(chunks)


def ingest_pdf(file_bytes: bytes, document_id: int, db: Session) -> int:
    """Extract text from a PDF, then chunk and embed it. Returns chunk count."""
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    if not full_text.strip():
        return 0

    return ingest_text(full_text, document_id, db)


def search(
    query: str,
    db: Session,
    venue_id: Optional[int] = None,
    event_id: Optional[int] = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search across knowledge chunks. Returns top matches with source info."""
    query_embedding = _embed_texts([query])[0]

    # Build query for chunks, joining to documents for filtering
    q = db.query(KnowledgeChunk).join(KnowledgeDocument)
    if venue_id is not None:
        q = q.filter(KnowledgeDocument.venue_id == venue_id)
    if event_id is not None:
        q = q.filter(KnowledgeDocument.event_id == event_id)

    # Only consider chunks that have embeddings
    q = q.filter(KnowledgeChunk.embedding.isnot(None))
    chunks = q.all()

    if not chunks:
        return []

    # Score all chunks
    scored = []
    for chunk in chunks:
        chunk_embedding = json.loads(chunk.embedding)
        score = _cosine_similarity(query_embedding, chunk_embedding)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    results = []
    for score, chunk in top:
        doc = chunk.document
        results.append({
            "content": chunk.content,
            "score": round(score, 4),
            "document_id": doc.id,
            "document_title": doc.title,
            "source_filename": doc.source_filename,
            "chunk_index": chunk.chunk_index,
            "venue_id": doc.venue_id,
            "event_id": doc.event_id,
        })

    return results
