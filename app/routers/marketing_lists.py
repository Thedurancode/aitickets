"""
Marketing Lists Router

Endpoints for creating and managing reusable audience segments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.rate_limit import limiter
from app.schemas import (
    MarketingListCreate,
    MarketingListUpdate,
    MarketingListResponse,
    MarketingListPreview,
    MarketingListsResponse,
)
from app.services.marketing_lists import (
    create_marketing_list,
    get_marketing_list,
    list_marketing_lists,
    preview_marketing_list,
    update_marketing_list,
    delete_marketing_list,
)

router = APIRouter(prefix="/marketing-lists", tags=["marketing-lists"])


@router.post("", response_model=MarketingListResponse, status_code=201)
@limiter.limit("20/minute")
def create_list(
    http_request: Request,
    request: MarketingListCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new marketing list with segment filters.

    **Segment Filter Options:**
    - `is_vip`: Boolean - VIP customers only
    - `vip_tier`: String - Specific VIP tier (gold, platinum, etc.)
    - `min_events`: Integer - Minimum events attended
    - `max_events`: Integer - Maximum events attended
    - `min_spent_cents`: Integer - Minimum lifetime spend in cents
    - `max_spent_cents`: Integer - Maximum lifetime spend in cents
    - `category_ids`: List[int] - Event categories of interest
    - `event_id`: Integer - Specific event attendees
    - `has_birthday_this_month`: Boolean - Birthday this month (opt-in only)
    - `last_purchase_days_ago`: Integer - Purchased within X days
    - `first_time_buyers`: Boolean - First-time customers only
    - `no_show`: Boolean - Never checked in
    - `marketing_opt_in`: Boolean - Marketing opt-in status
    - `email_opt_in`: Boolean - Email opt-in status
    - `sms_opt_in`: Boolean - SMS opt-in status
    - `preferred_language`: String - Preferred language
    - `dormant_days`: Integer - Dormant for X+ days

    **Example:**
    ```json
    {
      "name": "VIP High Spenders",
      "description": "VIP customers who spent $500+",
      "segment_filters": {
        "is_vip": true,
        "min_spent_cents": 50000
      }
    }
    ```
    """
    result = create_marketing_list(
        db=db,
        name=request.name,
        segment_filters=request.segment_filters,
        description=request.description,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("", response_model=MarketingListsResponse)
def list_lists(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List all marketing lists with current counts."""
    return list_marketing_lists(db=db, limit=limit, offset=offset)


@router.get("/{list_id}", response_model=MarketingListResponse)
def get_list(
    list_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific marketing list by ID."""
    result = get_marketing_list(db=db, list_id=list_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/{list_id}/preview", response_model=MarketingListPreview)
def preview_list(
    list_id: int,
    limit: int = Query(default=10, ge=0, le=100, description="Number of sample customers to return (0 for count only)"),
    db: Session = Depends(get_db),
):
    """
    Preview who's in a marketing list.

    Returns:
    - Total count of matching customers
    - Filter description (human-readable)
    - Sample of customers (up to `limit`)
    - Segment filters applied

    **Use `limit=0` to get just the count without customer data.**
    """
    result = preview_marketing_list(db=db, list_id=list_id, limit=limit)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.put("/{list_id}", response_model=MarketingListResponse)
@limiter.limit("20/minute")
def update_list(
    http_request: Request,
    list_id: int,
    request: MarketingListUpdate,
    db: Session = Depends(get_db),
):
    """Update a marketing list."""
    result = update_marketing_list(
        db=db,
        list_id=list_id,
        name=request.name,
        description=request.description,
        segment_filters=request.segment_filters,
    )

    if "error" in result:
        status_code = 404 if "not found" in result["error"] else 400
        raise HTTPException(status_code=status_code, detail=result["error"])

    return result


@router.delete("/{list_id}")
@limiter.limit("20/minute")
def delete_list(
    http_request: Request,
    list_id: int,
    db: Session = Depends(get_db),
):
    """Delete a marketing list."""
    result = delete_marketing_list(db=db, list_id=list_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
