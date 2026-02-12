from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import uuid

from app.database import get_db
from app.models import FlyerStyle
from app.schemas import FlyerStyleCreate, FlyerStyleUpdate, FlyerStyleResponse
from app.config import get_settings

router = APIRouter(prefix="/flyer-styles", tags=["flyer-styles"])


@router.get("/", response_model=list[FlyerStyleResponse])
def list_styles(db: Session = Depends(get_db)):
    """List all saved flyer styles."""
    return db.query(FlyerStyle).order_by(FlyerStyle.name).all()


@router.get("/{style_id}", response_model=FlyerStyleResponse)
def get_style(style_id: int, db: Session = Depends(get_db)):
    """Get a single flyer style by ID."""
    style = db.query(FlyerStyle).filter(FlyerStyle.id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail="Flyer style not found")
    return style


@router.post("/", response_model=FlyerStyleResponse, status_code=201)
def create_style(body: FlyerStyleCreate, db: Session = Depends(get_db)):
    """Create a new flyer style."""
    existing = db.query(FlyerStyle).filter(FlyerStyle.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="A style with that name already exists")
    style = FlyerStyle(name=body.name, description=body.description)
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


@router.post("/{style_id}/image", response_model=FlyerStyleResponse)
async def upload_style_image(
    style_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a reference image for a flyer style."""
    style = db.query(FlyerStyle).filter(FlyerStyle.id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail="Flyer style not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".png"
    filename = f"style_{style_id}_{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    style.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(style)
    return style


@router.put("/{style_id}", response_model=FlyerStyleResponse)
def update_style(style_id: int, body: FlyerStyleUpdate, db: Session = Depends(get_db)):
    """Update a flyer style's name or description."""
    style = db.query(FlyerStyle).filter(FlyerStyle.id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail="Flyer style not found")

    if body.name is not None and body.name != style.name:
        existing = db.query(FlyerStyle).filter(FlyerStyle.name == body.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="A style with that name already exists")
        style.name = body.name
    if body.description is not None:
        style.description = body.description

    db.commit()
    db.refresh(style)
    return style


@router.delete("/{style_id}")
def delete_style(style_id: int, db: Session = Depends(get_db)):
    """Delete a flyer style and its reference image."""
    style = db.query(FlyerStyle).filter(FlyerStyle.id == style_id).first()
    if not style:
        raise HTTPException(status_code=404, detail="Flyer style not found")

    # Remove image file if it exists
    if style.image_url:
        image_path = Path(style.image_url.lstrip("/"))
        if image_path.exists():
            image_path.unlink()

    db.delete(style)
    db.commit()
    return {"message": f"Style '{style.name}' deleted"}
