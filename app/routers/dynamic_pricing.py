"""
Dynamic Pricing API Router

Endpoints for managing demand-based ticket pricing automation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.rate_limit import limiter
from app.services.dynamic_pricing import (
    suggest_price_adjustment,
    apply_price_adjustment,
    auto_adjust_event_pricing,
    enable_dynamic_pricing,
    disable_dynamic_pricing,
)
from app.models import TicketTier, Event

router = APIRouter(prefix="/dynamic-pricing", tags=["dynamic-pricing"])


class EnableDynamicPricingRequest(BaseModel):
    """Request to enable dynamic pricing for a tier."""
    tier_id: int = Field(..., description="Ticket tier ID")
    min_price: Optional[int] = Field(None, description="Minimum allowed price in cents")
    max_price: Optional[int] = Field(None, description="Maximum allowed price in cents")


class ApplyPriceRequest(BaseModel):
    """Request to manually apply a price adjustment."""
    tier_id: int = Field(..., description="Ticket tier ID")
    new_price: int = Field(..., description="New price in cents")
    reason: str = Field("manual_adjustment", description="Reason for price change")


@router.get("/tiers/{tier_id}/suggestion")
@limiter.limit("30/minute")
def get_price_suggestion(
    request: Request,
    tier_id: int,
    db: Session = Depends(get_db),
):
    """
    Get AI-suggested price for a tier based on demand and time pressure.

    **Returns:**
    - Current vs suggested price
    - Demand score (0-1)
    - Time pressure multiplier
    - Reasoning for suggestion
    """
    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    event = db.query(Event).filter(Event.id == tier.event_id).first()

    result = suggest_price_adjustment(tier, db, event)
    return result


@router.get("/events/{event_id}/suggestions")
@limiter.limit("30/minute")
def get_event_price_suggestions(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Get price suggestions for all tiers in an event.

    Useful for reviewing potential price changes before applying them.
    """
    result = auto_adjust_event_pricing(db, event_id, dry_run=True)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/events/{event_id}/auto-adjust")
@limiter.limit("10/minute")
def auto_adjust_pricing(
    request: Request,
    event_id: int,
    dry_run: bool = False,
    db: Session = Depends(get_db),
):
    """
    Automatically adjust pricing for all dynamic tiers in an event.

    **Query Parameters:**
    - `dry_run`: If true, only return suggestions without applying changes

    **How it works:**
    1. Calculates demand score based on sell-through rate and velocity
    2. Applies time pressure multiplier (increases as event approaches)
    3. Suggests new price within min/max bounds
    4. Only updates if change is >= $1.00
    """
    result = auto_adjust_event_pricing(db, event_id, dry_run=dry_run)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/tiers/{tier_id}/enable")
@limiter.limit("10/minute")
def enable_tier_dynamic_pricing(
    request: Request,
    tier_id: int,
    config: EnableDynamicPricingRequest,
    db: Session = Depends(get_db),
):
    """
    Enable dynamic pricing for a specific tier.

    **Body Parameters:**
    - `tier_id`: Tier ID (in path)
    - `min_price`: Minimum allowed price in cents (optional)
    - `max_price`: Maximum allowed price in cents (optional)

    **Example:**
    ```json
    {
      "tier_id": 123,
      "min_price": 1500,
      "max_price": 5000
    }
    ```

    Current price becomes the base price. Future adjustments will
    be calculated relative to this base.
    """
    result = enable_dynamic_pricing(
        db,
        tier_id=config.tier_id,
        min_price=config.min_price,
        max_price=config.max_price,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/tiers/{tier_id}/disable")
@limiter.limit("10/minute")
def disable_tier_dynamic_pricing(
    request: Request,
    tier_id: int,
    db: Session = Depends(get_db),
):
    """
    Disable dynamic pricing for a tier and reset to base price.

    This reverts the tier to manual pricing control.
    """
    result = disable_dynamic_pricing(db, tier_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/tiers/apply-price")
@limiter.limit("10/minute")
def manually_apply_price(
    request: Request,
    price_req: ApplyPriceRequest,
    db: Session = Depends(get_db),
):
    """
    Manually apply a price adjustment to a tier.

    **Body Parameters:**
    - `tier_id`: Tier ID
    - `new_price`: New price in cents
    - `reason`: Reason for manual adjustment (optional)

    **Example:**
    ```json
    {
      "tier_id": 123,
      "new_price": 3500,
      "reason": "Early bird special"
    }
    ```
    """
    result = apply_price_adjustment(
        db,
        tier_id=price_req.tier_id,
        new_price=price_req.new_price,
        reason=price_req.reason,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/tiers/{tier_id}/history")
@limiter.limit("30/minute")
def get_pricing_history(
    request: Request,
    tier_id: int,
    db: Session = Depends(get_db),
):
    """
    Get pricing history for a tier (if tracked).

    Returns current pricing configuration and last update info.
    """
    tier = db.query(TicketTier).filter(TicketTier.id == tier_id).first()

    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    return {
        "tier_id": tier.id,
        "tier_name": tier.name,
        "current_price": tier.price,
        "base_price": tier.base_price,
        "dynamic_pricing_enabled": tier.dynamic_pricing_enabled,
        "min_price": tier.min_price,
        "max_price": tier.max_price,
        "last_price_update": tier.last_price_update.isoformat() if tier.last_price_update else None,
        "price_update_reason": tier.price_update_reason,
    }
