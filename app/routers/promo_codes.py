from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import PromoCode, DiscountType, TicketTier, Event
from app.schemas import PromoCodeCreate, PromoCodeUpdate, PromoCodeResponse

router = APIRouter(prefix="/promo-codes", tags=["promo-codes"])


@router.get("/", response_model=list[PromoCodeResponse])
def list_promo_codes(
    event_id: int = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(PromoCode)
    if event_id:
        query = query.filter(PromoCode.event_id == event_id)
    if active_only:
        query = query.filter(PromoCode.is_active == True)
    return query.order_by(PromoCode.created_at.desc()).all()


@router.post("/", response_model=PromoCodeResponse, status_code=201)
def create_promo_code(promo: PromoCodeCreate, db: Session = Depends(get_db)):
    code_upper = promo.code.upper()
    existing = db.query(PromoCode).filter(PromoCode.code == code_upper).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Promo code '{code_upper}' already exists")

    if promo.event_id:
        event = db.query(Event).filter(Event.id == promo.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

    if promo.discount_type == "percent" and not (1 <= promo.discount_value <= 100):
        raise HTTPException(status_code=400, detail="Percent discount must be between 1 and 100")
    if promo.discount_type == "fixed_cents" and promo.discount_value <= 0:
        raise HTTPException(status_code=400, detail="Fixed discount must be positive")

    db_promo = PromoCode(
        code=code_upper,
        discount_type=DiscountType(promo.discount_type),
        discount_value=promo.discount_value,
        is_active=promo.is_active,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        max_uses=promo.max_uses,
        event_id=promo.event_id,
    )
    db.add(db_promo)
    db.commit()
    db.refresh(db_promo)
    return db_promo


@router.post("/validate")
def validate_promo_code(
    code: str = Query(...),
    ticket_tier_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Validate a promo code and preview the discount for a given tier."""
    tier = db.query(TicketTier).filter(TicketTier.id == ticket_tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")

    promo = db.query(PromoCode).filter(PromoCode.code == code.upper()).first()
    if not promo:
        return {"valid": False, "message": "Invalid promo code"}
    if not promo.is_active:
        return {"valid": False, "message": "Promo code is no longer active"}
    if promo.event_id and promo.event_id != tier.event_id:
        return {"valid": False, "message": "Promo code is not valid for this event"}

    now = datetime.utcnow()
    if promo.valid_from and now < promo.valid_from.replace(tzinfo=None):
        return {"valid": False, "message": "Promo code is not yet valid"}
    if promo.valid_until and now > promo.valid_until.replace(tzinfo=None):
        return {"valid": False, "message": "Promo code has expired"}
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        return {"valid": False, "message": "Promo code has reached its usage limit"}

    original = tier.price
    if promo.discount_type == DiscountType.PERCENT:
        discount = int(original * promo.discount_value / 100)
    else:
        discount = min(promo.discount_value, original)
    discounted = max(original - discount, 0)

    return {
        "valid": True,
        "code": promo.code,
        "discount_type": promo.discount_type.value,
        "discount_value": promo.discount_value,
        "original_price_cents": original,
        "discount_amount_cents": discount,
        "discounted_price_cents": discounted,
        "message": f"Code '{promo.code}' is valid! ${discount / 100:.2f} off, final price ${discounted / 100:.2f}.",
    }


@router.get("/{promo_code_id}", response_model=PromoCodeResponse)
def get_promo_code(promo_code_id: int, db: Session = Depends(get_db)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_code_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return promo


@router.put("/{promo_code_id}", response_model=PromoCodeResponse)
def update_promo_code(promo_code_id: int, update: PromoCodeUpdate, db: Session = Depends(get_db)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_code_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(promo, field, value)
    db.commit()
    db.refresh(promo)
    return promo


@router.delete("/{promo_code_id}")
def deactivate_promo_code(promo_code_id: int, db: Session = Depends(get_db)):
    promo = db.query(PromoCode).filter(PromoCode.id == promo_code_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    promo.is_active = False
    db.commit()
    return {"message": f"Promo code '{promo.code}' deactivated"}
