from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
import csv
import io
from typing import Optional

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

    # Fire webhook: customer.registered
    try:
        from app.services.webhooks import fire_webhook_event
        fire_webhook_event("customer.registered", {
            "customer_id": db_event_goer.id,
            "email": db_event_goer.email,
            "name": db_event_goer.name,
            "phone": db_event_goer.phone,
        }, db=db)
    except Exception:
        pass

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


@router.post("/bulk-upload", response_model=dict)
async def bulk_upload_event_goers(
    file: UploadFile = File(...),
    on_duplicate: str = Query("skip", description="Action on duplicate emails: 'skip' or 'update'"),
    db: Session = Depends(get_db),
):
    """
    Bulk upload event goers from a CSV file.

    CSV Format (columns):
    - email (required): Email address
    - name (required): Full name
    - phone (optional): Phone number
    - birthdate (optional): YYYY-MM-DD format
    - email_opt_in (optional): true/false (default: true)
    - sms_opt_in (optional): true/false (default: false)
    - marketing_opt_in (optional): true/false (default: false)

    Returns summary with created, updated, skipped, and error counts.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Read CSV content
    content = await file.read()
    csv_file = io.StringIO(content.decode('utf-8'))

    # Try to detect the delimiter (comma or semicolon)
    sample = csv_file.read(1024)
    csv_file.seek(0)
    delimiter = ',' if ',' in sample else ';'

    reader = csv.DictReader(csv_file, delimiter=delimiter)

    # Normalize column names (lowercase, strip spaces)
    if reader.fieldnames:
        reader.fieldnames = [name.lower().strip() for name in reader.fieldnames]

    results = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": [],
        "total_rows": 0
    }

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 = header row)
        results["total_rows"] += 1

        try:
            # Validate required fields
            email = row.get("email", "").strip()
            name = row.get("name", "").strip()

            if not email or not name:
                results["errors"] += 1
                results["error_details"].append({
                    "row": row_num,
                    "error": "Missing required fields (email or name)",
                    "email": email
                })
                continue

            # Validate email format (basic check)
            if "@" not in email:
                results["errors"] += 1
                results["error_details"].append({
                    "row": row_num,
                    "error": "Invalid email format",
                    "email": email
                })
                continue

            # Check if event goer already exists
            existing = db.query(EventGoer).filter(EventGoer.email == email).first()

            if existing:
                if on_duplicate == "update":
                    # Update existing record
                    if name:
                        existing.name = name

                    if row.get("phone"):
                        existing.phone = row.get("phone", "").strip()

                    # Update opt-in preferences if provided
                    if "email_opt_in" in row:
                        existing.email_opt_in = str(row["email_opt_in"]).lower() in ['true', '1', 'yes']
                    if "sms_opt_in" in row:
                        existing.sms_opt_in = str(row["sms_opt_in"]).lower() in ['true', '1', 'yes']
                    if "marketing_opt_in" in row:
                        existing.marketing_opt_in = str(row["marketing_opt_in"]).lower() in ['true', '1', 'yes']

                    # Update birthdate if provided
                    if row.get("birthdate"):
                        from datetime import datetime
                        try:
                            existing.birthdate = datetime.strptime(row["birthdate"].strip(), "%Y-%m-%d").date()
                        except ValueError:
                            pass  # Invalid date format, skip

                    results["updated"] += 1
                else:
                    # Skip existing record
                    results["skipped"] += 1
            else:
                # Create new event goer
                event_goer = EventGoer(
                    email=email,
                    name=name,
                    phone=row.get("phone", "").strip() or None,
                    # Parse opt-in preferences
                    email_opt_in=str(row.get("email_opt_in", "true")).lower() in ['true', '1', 'yes'],
                    sms_opt_in=str(row.get("sms_opt_in", "false")).lower() in ['true', '1', 'yes'],
                    marketing_opt_in=str(row.get("marketing_opt_in", "false")).lower() in ['true', '1', 'yes'],
                )

                # Parse birthdate if provided
                if row.get("birthdate"):
                    from datetime import datetime
                    try:
                        event_goer.birthdate = datetime.strptime(row["birthdate"].strip(), "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Invalid date format, skip

                db.add(event_goer)
                results["created"] += 1

        except Exception as e:
            results["errors"] += 1
            results["error_details"].append({
                "row": row_num,
                "error": str(e),
                "email": row.get("email", "unknown")
            })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return results
