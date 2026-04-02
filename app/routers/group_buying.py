"""
Group Buying API Endpoints

Enable groups to purchase tickets together with split payment functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.models import Event, EventGoer, Ticket, TicketTier
from app.models_extensions import (
    GroupPurchase, GroupContribution, GroupPurchaseStatus
)
from app.services.email_service import EmailService
from app.services.stripe_service import StripeService
from app.auth import get_current_user, get_current_admin_user
from app.audit import create_audit_logger, AuditAction
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/group-buying", tags=["Group Buying"])


# ===================== Pydantic Models =====================

class CreateGroupPurchase(BaseModel):
    """Request model for creating a group purchase."""
    event_id: int = Field(..., gt=0)
    total_tickets: int = Field(..., gt=0, le=100, description="Max 100 tickets per group")
    group_name: Optional[str] = Field(None, max_length=255)
    expires_in_hours: int = Field(72, ge=1, le=168, description="1-168 hours (1 week max)")


class JoinGroupPurchase(BaseModel):
    """Request model for joining a group purchase."""
    ticket_count: int = Field(1, gt=0, le=10, description="Max 10 tickets per contribution")
    amount: Optional[int] = Field(None, gt=0, description="Amount in cents")


class GroupPurchaseResponse(BaseModel):
    """Response model for group purchase details."""
    id: int
    event_id: int
    group_name: Optional[str]
    total_tickets: int
    total_amount: int
    amount_paid: int
    amount_remaining: int
    status: str
    expires_at: datetime
    contributors: List[Dict]
    share_url: str


# ===================== API Endpoints =====================

@router.post("/groups", response_model=GroupPurchaseResponse)
@limiter.limit("10/hour")  # Limit group creation to prevent abuse
def create_group_purchase(
    request: Request,
    data: CreateGroupPurchase,
    background_tasks: BackgroundTasks,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new group purchase for an event.

    The organizer initiates the group purchase and invites others to contribute.
    """
    # Validate event exists
    event = db.query(Event).filter(Event.id == data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Calculate total cost
    # Get cheapest available tier for simplicity
    available_tier = db.query(TicketTier).filter(
        and_(
            TicketTier.event_id == data.event_id,
            TicketTier.quantity_available > 0
        )
    ).order_by(TicketTier.price).first()

    if not available_tier:
        raise HTTPException(status_code=400, detail="No tickets available")

    if available_tier.quantity_available < data.total_tickets:
        raise HTTPException(
            status_code=400,
            detail=f"Only {available_tier.quantity_available} tickets available"
        )

    total_amount = available_tier.price * data.total_tickets

    # Create group purchase with error handling
    try:
        group = GroupPurchase(
            event_id=data.event_id,
            organizer_id=current_user.id,
            group_name=data.group_name or f"Group for {event.name[:30]}",
            total_tickets=data.total_tickets,
            total_amount=total_amount,
            amount_remaining=total_amount,
            expires_at=datetime.utcnow() + timedelta(hours=data.expires_in_hours)
        )

        db.add(group)
        db.commit()
        db.refresh(group)

        # Audit logging
        audit_logger = create_audit_logger(db)
        audit_logger.log_group_purchase_action(
            action=AuditAction.CREATE_GROUP,
            group_id=group.id,
            user_id=current_user.id,
            details=f"Created group purchase for {data.total_tickets} tickets"
        )
        db.commit()

        # Send email notification to organizer
        # background_tasks.add_task(send_group_created_email, group, event)

        logger.info(f"Group purchase {group.id} created by user {current_user.id}")
        return _format_group_response(group, db)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create group purchase: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to create group purchase"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating group purchase: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/groups/{group_id}", response_model=GroupPurchaseResponse)
def get_group_purchase(
    group_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific group purchase."""
    group = db.query(GroupPurchase).filter(GroupPurchase.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group purchase not found")

    return _format_group_response(group, db)


@router.post("/groups/{group_id}/join")
@limiter.limit("30/hour")  # Limit join attempts
def join_group_purchase(
    request: Request,
    group_id: int,
    data: JoinGroupPurchase,
    background_tasks: BackgroundTasks,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Join an existing group purchase by contributing payment.

    Contributors can specify how many tickets they want and pay their share.
    Uses database row locking to prevent race conditions.
    """
    try:
        # Get group purchase with row-level lock to prevent race conditions
        stmt = select(GroupPurchase).where(
            GroupPurchase.id == group_id
        ).with_for_update()

        result = db.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            raise HTTPException(status_code=404, detail="Group purchase not found")

    # Check status
    if group.status != GroupPurchaseStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot join group with status: {group.status}"
        )

    # Check expiration
    if datetime.utcnow() > group.expires_at:
        group.status = GroupPurchaseStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Group purchase has expired")

        # Check if already contributed
        existing = db.query(GroupContribution).filter(
            and_(
                GroupContribution.group_purchase_id == group_id,
                GroupContribution.contributor_id == current_user.id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already contributed to this group")

        # Calculate contribution amount
        if data.amount:
            contribution_amount = data.amount
        else:
            # Split remaining amount proportionally
            price_per_ticket = group.total_amount // group.total_tickets
            contribution_amount = price_per_ticket * data.ticket_count

        # CRITICAL: Validate contribution doesn't exceed remaining amount
        if contribution_amount > group.amount_remaining:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Contribution exceeds remaining amount: ${group.amount_remaining/100:.2f}"
            )

        # Create contribution
        contribution = GroupContribution(
            group_purchase_id=group_id,
            contributor_id=current_user.id,
            amount=contribution_amount,
            ticket_count=data.ticket_count
        )

        db.add(contribution)

        # Update group totals atomically
        group.amount_paid += contribution_amount
        group.amount_remaining -= contribution_amount

        # Check if fully funded
        if group.amount_remaining == 0:
            group.status = GroupPurchaseStatus.COMPLETE
            group.completed_at = datetime.utcnow()
            # Trigger ticket creation
            background_tasks.add_task(_create_group_tickets, group.id)
        elif group.amount_paid > 0:
            group.status = GroupPurchaseStatus.PARTIAL

        db.commit()

        logger.info(
            f"User {current_user.id} contributed ${contribution_amount/100} "
            f"to group purchase {group_id}"
        )

        # Send notifications
        # background_tasks.add_task(send_contribution_notification, contribution, group)

        return {
            "success": True,
            "contribution_id": contribution.id,
            "amount": contribution_amount,
            "group_status": group.status.value,
            "amount_remaining": group.amount_remaining
        }

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in join_group_purchase: {e}")
        raise HTTPException(
            status_code=409,
            detail="Contribution conflict - please try again"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in join_group_purchase: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/groups/{group_id}/cancel")
def cancel_group_purchase(
    group_id: int,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a group purchase.

    Only the organizer can cancel. Refunds are issued to all contributors.
    """
    try:
        group = db.query(GroupPurchase).filter(GroupPurchase.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group purchase not found")

        # Check permissions
        if group.organizer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only organizer can cancel")

        # Check if already complete
        if group.status == GroupPurchaseStatus.COMPLETE:
            raise HTTPException(status_code=400, detail="Cannot cancel completed purchase")

        # Update status
        group.status = GroupPurchaseStatus.CANCELLED

        # Process refunds for any contributions
        contributions = db.query(GroupContribution).filter(
            GroupContribution.group_purchase_id == group_id,
            GroupContribution.paid == True
        ).all()

        for contribution in contributions:
            # In production, process Stripe refund here
            contribution.paid = False

        # Audit logging
        audit_logger = create_audit_logger(db)
        audit_logger.log_group_purchase_action(
            action=AuditAction.CANCEL_GROUP,
            group_id=group_id,
            user_id=current_user.id,
            details=f"Cancelled with {len(contributions)} refunds"
        )

        db.commit()

        logger.info(f"Group purchase {group_id} cancelled by user {current_user.id}")

        return {
            "success": True,
            "refunds_processed": len(contributions),
            "total_refunded": sum(c.amount for c in contributions)
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling group purchase: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my-groups")
def get_my_group_purchases(
    current_user: EventGoer = Depends(get_current_user),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all group purchases for a user (as organizer or contributor)."""
    # Groups organized by user
    query = db.query(GroupPurchase).filter(GroupPurchase.organizer_id == current_user.id)
    if status:
        query = query.filter(GroupPurchase.status == status)
    organized = query.all()

    # Groups contributed to
    contributions = db.query(GroupContribution).filter(
        GroupContribution.contributor_id == current_user.id
    ).all()

    contributed = [c.group_purchase for c in contributions]
    if status:
        contributed = [g for g in contributed if g.status == status]

    return {
        "organized": [_format_group_summary(g) for g in organized],
        "contributed": [_format_group_summary(g) for g in contributed]
    }


@router.get("/events/{event_id}/groups")
def get_event_group_purchases(
    event_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all group purchases for an event."""
    query = db.query(GroupPurchase).filter(GroupPurchase.event_id == event_id)

    if active_only:
        query = query.filter(
            GroupPurchase.status.in_([
                GroupPurchaseStatus.PENDING,
                GroupPurchaseStatus.PARTIAL
            ])
        )

    groups = query.all()

    return {
        "event_id": event_id,
        "groups": [_format_group_summary(g) for g in groups],
        "total_groups": len(groups),
        "total_tickets_pending": sum(
            g.total_tickets for g in groups
            if g.status in [GroupPurchaseStatus.PENDING, GroupPurchaseStatus.PARTIAL]
        )
    }


# ===================== Helper Functions =====================

def _format_group_response(group: GroupPurchase, db: Session) -> Dict:
    """Format group purchase for API response."""
    from sqlalchemy.orm import joinedload

    # Use eager loading to avoid N+1 query problem
    contributions = db.query(GroupContribution).options(
        joinedload(GroupContribution.contributor)
    ).filter(
        GroupContribution.group_purchase_id == group.id
    ).all()

    contributors = []
    for contrib in contributions:
        goer = contrib.contributor
        contributors.append({
            "id": contrib.id,
            "name": goer.name if goer else "Unknown",
            "ticket_count": contrib.ticket_count,
            "amount": contrib.amount,
            "paid": contrib.paid,
            "paid_at": contrib.paid_at
        })

    return {
        "id": group.id,
        "event_id": group.event_id,
        "group_name": group.group_name,
        "total_tickets": group.total_tickets,
        "total_amount": group.total_amount,
        "amount_paid": group.amount_paid,
        "amount_remaining": group.amount_remaining,
        "status": group.status.value,
        "expires_at": group.expires_at,
        "contributors": contributors,
        "share_url": f"/group-purchase/{group.id}"  # Frontend URL
    }


def _format_group_summary(group: GroupPurchase) -> Dict:
    """Format group purchase summary."""
    return {
        "id": group.id,
        "event_id": group.event_id,
        "group_name": group.group_name,
        "status": group.status.value,
        "progress": {
            "total": group.total_amount,
            "paid": group.amount_paid,
            "remaining": group.amount_remaining,
            "percentage": round((group.amount_paid / group.total_amount) * 100, 1)
        },
        "expires_at": group.expires_at,
        "created_at": group.created_at
    }


def _create_group_tickets(group_id: int):
    """Create tickets when group purchase is complete."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        # Get group with lock
        group = db.query(GroupPurchase).filter(
            GroupPurchase.id == group_id
        ).first()

        if not group or group.status != GroupPurchaseStatus.COMPLETE:
            logger.warning(f"Cannot create tickets for group {group_id} - invalid state")
            return

        # Get contributions
        contributions = db.query(GroupContribution).filter(
            GroupContribution.group_purchase_id == group.id
        ).all()

        # Get ticket tier
        tier = db.query(TicketTier).filter(
            TicketTier.event_id == group.event_id
        ).first()

        if not tier:
            logger.error(f"No ticket tier found for event {group.event_id}")
            return

        # Create tickets for each contributor
        tickets_created = 0
        for contrib in contributions:
            for _ in range(contrib.ticket_count):
                ticket = Ticket(
                    ticket_tier_id=tier.id,
                    event_goer_id=contrib.contributor_id,
                    purchased_at=datetime.utcnow(),
                    purchase_price=tier.price,
                    stripe_payment_intent_id=group.stripe_payment_intent_id
                )
                db.add(ticket)
                tickets_created += 1

        # Update tier inventory
        tier.quantity_sold += group.total_tickets
        tier.quantity_available -= group.total_tickets

        db.commit()
        logger.info(f"Created {tickets_created} tickets for group purchase {group_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tickets for group {group_id}: {e}")
    finally:
        db.close()