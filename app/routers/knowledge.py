"""Router for RAG knowledge base — upload, paste, search, and manage documents."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import KnowledgeDocument, KnowledgeChunk
from app.services import rag

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}


class PasteRequest(BaseModel):
    title: str
    content: str
    venue_id: Optional[int] = None
    event_id: Optional[int] = None


@router.post("/upload", status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    venue_id: Optional[int] = Form(None),
    event_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a PDF, TXT, or MD file to the knowledge base."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    content_type = ext  # pdf, txt, md

    doc = KnowledgeDocument(
        venue_id=venue_id,
        event_id=event_id,
        title=title,
        source_filename=filename,
        content_type=content_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    file_bytes = file.file.read()

    if content_type == "pdf":
        chunk_count = rag.ingest_pdf(file_bytes, doc.id, db)
    else:
        text = file_bytes.decode("utf-8")
        chunk_count = rag.ingest_text(text, doc.id, db)

    return {
        "id": doc.id,
        "title": doc.title,
        "content_type": doc.content_type,
        "source_filename": doc.source_filename,
        "chunks_created": chunk_count,
    }


@router.post("/paste", status_code=201)
def paste_content(body: PasteRequest, db: Session = Depends(get_db)):
    """Paste text content (e.g. FAQ) directly into the knowledge base."""
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    doc = KnowledgeDocument(
        venue_id=body.venue_id,
        event_id=body.event_id,
        title=body.title,
        source_filename=None,
        content_type="paste",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunk_count = rag.ingest_text(body.content, doc.id, db)

    return {
        "id": doc.id,
        "title": doc.title,
        "content_type": doc.content_type,
        "chunks_created": chunk_count,
    }


@router.get("/")
def list_documents(
    venue_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List knowledge documents, optionally filtered by venue or event."""
    q = db.query(KnowledgeDocument)
    if venue_id is not None:
        q = q.filter(KnowledgeDocument.venue_id == venue_id)
    if event_id is not None:
        q = q.filter(KnowledgeDocument.event_id == event_id)

    docs = q.order_by(KnowledgeDocument.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "content_type": d.content_type,
            "source_filename": d.source_filename,
            "venue_id": d.venue_id,
            "event_id": d.event_id,
            "created_at": str(d.created_at) if d.created_at else None,
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a knowledge document and all its chunks."""
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.title}' and its chunks deleted"}


@router.get("/search")
def search_knowledge(
    q: str = Query(..., min_length=1),
    venue_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Semantic search across the knowledge base."""
    results = rag.search(query=q, db=db, venue_id=venue_id, event_id=event_id, limit=limit)
    return {"query": q, "results": results}
