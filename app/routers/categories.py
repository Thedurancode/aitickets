from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventCategory
from app.schemas import EventCategoryCreate, EventCategoryUpdate, EventCategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[EventCategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """List all event categories."""
    return db.query(EventCategory).order_by(EventCategory.name).all()


@router.get("/{category_id}", response_model=EventCategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a category by ID."""
    category = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=EventCategoryResponse, status_code=201)
def create_category(category: EventCategoryCreate, db: Session = Depends(get_db)):
    """Create a new event category."""
    existing = db.query(EventCategory).filter(EventCategory.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists")

    db_category = EventCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.put("/{category_id}", response_model=EventCategoryResponse)
def update_category(category_id: int, category: EventCategoryUpdate, db: Session = Depends(get_db)):
    """Update a category."""
    db_category = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category.model_dump(exclude_unset=True)

    # Check name uniqueness if changing name
    if "name" in update_data:
        existing = db.query(EventCategory).filter(
            EventCategory.name == update_data["name"],
            EventCategory.id != category_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{update_data['name']}' already exists")

    for field, value in update_data.items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category. Fails if events are using it."""
    db_category = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if db_category.events:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {len(db_category.events)} event(s) use this category",
        )

    db.delete(db_category)
    db.commit()
    return {"message": f"Category '{db_category.name}' deleted"}
