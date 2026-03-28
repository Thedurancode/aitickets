"""
Refund Management API Router

Endpoints for processing and tracking ticket refunds.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.rate_limit import limiter
from app.services.refunds import (
    process_refund,
    bulk_refund,
    get_refund_history,
    get_refund_stats,
    check_refund_policy,
)

router = APIRouter(prefix="/refunds", tags=["refunds"])


class RefundRequest(BaseModel):
    """Request to refund a ticket."""
    ticket_id: int = Field(..., description="ID of ticket to refund")
    reason: str = Field(..., description="Refund reason: customer_request, event_cancelled, duplicate, fraud, other")
    amount_cents: Optional[int] = Field(None, description="Amount to refund in cents (null = full refund)")
    notify_customer: bool = Field(True, description="Whether to send email notification")


class BulkRefundRequest(BaseModel):
    """Request to refund multiple tickets."""
    ticket_ids: list[int] = Field(..., description="List of ticket IDs to refund")
    reason: str = Field(..., description="Refund reason")
    amount_cents: Optional[int] = Field(None, description="Amount per ticket (null = full refund each)")


@router.post("/process")
@limiter.limit("10/minute")
def create_refund(
    request: Request,
    refund_req: RefundRequest,
    db: Session = Depends(get_db),
):
    """
    Process a full or partial refund for a ticket.

    **Refund Reasons:**
    - `customer_request`: Customer requested refund
    - `event_cancelled`: Event was cancelled
    - `duplicate`: Duplicate purchase
    - `fraud`: Fraudulent transaction
    - `other`: Other reason

    **Example:**
    ```json
    {
      "ticket_id": 123,
      "reason": "customer_request",
      "amount_cents": null,
      "notify_customer": true
    }
    ```
    """
    result = process_refund(
        db=db,
        ticket_id=refund_req.ticket_id,
        reason=refund_req.reason,
        amount_cents=refund_req.amount_cents,
        notify_customer=refund_req.notify_customer,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/bulk")
@limiter.limit("5/minute")
def create_bulk_refund(
    request: Request,
    bulk_req: BulkRefundRequest,
    db: Session = Depends(get_db),
):
    """
    Process refunds for multiple tickets at once.

    Useful for event cancellations or bulk refund operations.
    Returns summary of successful and failed refunds.

    **Example:**
    ```json
    {
      "ticket_ids": [123, 124, 125],
      "reason": "event_cancelled",
      "amount_cents": null
    }
    ```
    """
    if len(bulk_req.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk refund")

    result = bulk_refund(
        db=db,
        ticket_ids=bulk_req.ticket_ids,
        reason=bulk_req.reason,
        amount_cents=bulk_req.amount_cents,
    )

    return result


@router.get("/history")
@limiter.limit("30/minute")
def list_refunds(
    request: Request,
    event_id: Optional[int] = None,
    event_goer_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get refund history with optional filters.

    **Query Parameters:**
    - `event_id`: Filter refunds for specific event
    - `event_goer_id`: Filter refunds for specific customer
    - `limit`: Max results (default 50)
    - `offset`: Pagination offset (default 0)
    """
    result = get_refund_history(
        db=db,
        event_id=event_id,
        event_goer_id=event_goer_id,
        limit=limit,
        offset=offset,
    )

    return result


@router.get("/stats")
@limiter.limit("30/minute")
def refund_statistics(
    request: Request,
    event_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get refund statistics and breakdown by reason.

    **Query Parameters:**
    - `event_id`: Filter stats for specific event (optional)

    **Returns:**
    - Total refunds count
    - Total amount refunded
    - Breakdown by refund reason
    - Average refund amount
    """
    result = get_refund_stats(db=db, event_id=event_id)
    return result


@router.get("/check-policy/{ticket_id}")
@limiter.limit("30/minute")
def check_refund_eligibility(
    request: Request,
    ticket_id: int,
    db: Session = Depends(get_db),
):
    """
    Check if a ticket is eligible for refund based on policy.

    **Path Parameters:**
    - `ticket_id`: ID of ticket to check

    **Returns:**
    - `eligible`: Boolean indicating if ticket can be refunded
    - `reason`: Explanation of eligibility status
    """
    result = check_refund_policy(db=db, ticket_id=ticket_id)
    return result
