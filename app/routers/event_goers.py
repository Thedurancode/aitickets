from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import EventGoer, Ticket
from app.schemas import (
    EventGoerCreate,
    EventGoerUpdate,
    EventGoerResponse,
    TicketResponse,
)

router = APIRouter(prefix="/event-goers", tags=["event_goers"])


@router.get("", response_model=list[EventGoerResponse])
def list_event_goers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List event goers."""
    event_goers = db.query(EventGoer).order_by(EventGoer.id).offset(offset).limit(limit).all()
    return event_goers


@router.get("/{event_goer_id}", response_model=EventGoerResponse)
def get_event_goer(event_goer_id: int, db: Session = Depends(get_db)):
    """Get an event goer by ID."""
    event_goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
    if not event_goer:
        raise HTTPException(status_code=404, detail="Event goer not found")
    return event_goer


@router.post("", response_model=EventGoerResponse, status_code=201)
def create_event_goer(event_goer: EventGoerCreate, db: Session = Depends(get_db)):
    """Register a new event goer."""
    # Check if email already exists
    existing = db.query(EventGoer).filter(EventGoer.email == event_goer.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_event_goer = EventGoer(**event_goer.model_dump())
    db.add(db_event_goer)
    db.commit()
    db.refresh(db_event_goer)
    return db_event_goer


@router.put("/{event_goer_id}", response_model=EventGoerResponse)
def update_event_goer(
    event_goer_id: int,
    event_goer: EventGoerUpdate,
    db: Session = Depends(get_db),
):
    """Update an event goer."""
    db_event_goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
    if not db_event_goer:
        raise HTTPException(status_code=404, detail="Event goer not found")

    update_data = event_goer.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event_goer, field, value)

    db.commit()
    db.refresh(db_event_goer)
    return db_event_goer


@router.get("/{event_goer_id}/tickets", response_model=list[TicketResponse])
def get_event_goer_tickets(event_goer_id: int, db: Session = Depends(get_db)):
    """Get all tickets for an event goer."""
    event_goer = db.query(EventGoer).filter(EventGoer.id == event_goer_id).first()
    if not event_goer:
        raise HTTPException(status_code=404, detail="Event goer not found")

    tickets = (
        db.query(Ticket)
        .filter(Ticket.event_goer_id == event_goer_id)
        .options(joinedload(Ticket.ticket_tier))
        .all()
    )
    return tickets
