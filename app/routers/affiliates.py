"""
Affiliate/Influencer Program API Endpoints

Manage affiliate accounts, track referrals, and handle commission payouts.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import secrets
import string
import logging

from app.database import get_db
from app.models import EventGoer, Ticket, TicketTier, Event
from app.models_extensions import (
    Affiliate, AffiliateReferral, AffiliatePayout, AffiliateStatus
)
from app.services.email_service import EmailService
from app.auth import get_current_user, get_current_admin_user
from app.audit import create_audit_logger, AuditAction
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/affiliates", tags=["Affiliates"])


# ===================== Pydantic Models =====================

class AffiliateApplication(BaseModel):
    """Request model for affiliate application."""
    display_name: str = Field(..., min_length=2, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    instagram_handle: Optional[str] = Field(None, max_length=100)
    tiktok_handle: Optional[str] = Field(None, max_length=100)
    youtube_channel: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=100)


class AffiliateUpdate(BaseModel):
    """Update affiliate profile."""
    display_name: Optional[str] = None
    bio: Optional[str] = None
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    twitter_handle: Optional[str] = None


class AffiliateResponse(BaseModel):
    """Response model for affiliate details."""
    id: int
    code: str
    display_name: Optional[str]
    bio: Optional[str]
    status: str
    commission_rate: float
    stats: Dict
    social_links: Dict
    referral_link: str


class ReferralStats(BaseModel):
    """Referral statistics."""
    total_clicks: int
    total_conversions: int
    conversion_rate: float
    total_sales: int
    total_commission: int
    pending_payout: int
    lifetime_earnings: int


# ===================== API Endpoints =====================

@router.post("/apply", response_model=AffiliateResponse)
def apply_as_affiliate(
    application: AffiliateApplication,
    background_tasks: BackgroundTasks,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply to become an affiliate/influencer.

    Creates a pending affiliate account that needs admin approval.
    """
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        # Check if already an affiliate
        existing = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already registered as affiliate")

        # Generate unique referral code
        code = _generate_referral_code(db)

        # Create affiliate account
        affiliate = Affiliate(
            event_goer_id=current_user.id,
            code=code,
            display_name=application.display_name,
            bio=application.bio,
            instagram_handle=application.instagram_handle,
            tiktok_handle=application.tiktok_handle,
            youtube_channel=application.youtube_channel,
            twitter_handle=application.twitter_handle,
            status=AffiliateStatus.PENDING
        )

        db.add(affiliate)
        db.commit()
        db.refresh(affiliate)

        # Log the action
        audit_logger.log(
            AuditAction.CREATE,
            "affiliate_application",
            affiliate.id,
            {"code": code, "display_name": application.display_name}
        )

        # Send notification email
        # background_tasks.add_task(send_affiliate_application_email, affiliate)

        return _format_affiliate_response(affiliate)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create affiliate application: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create affiliate application")


@router.get("/profile", response_model=AffiliateResponse)
def get_affiliate_profile(
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's affiliate profile."""
    try:
        affiliate = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if not affiliate:
            raise HTTPException(status_code=404, detail="Not registered as affiliate")

        return _format_affiliate_response(affiliate)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get affiliate profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get affiliate profile")


@router.put("/profile", response_model=AffiliateResponse)
def update_affiliate_profile(
    updates: AffiliateUpdate,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update affiliate profile information."""
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        affiliate = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if not affiliate:
            raise HTTPException(status_code=404, detail="Not registered as affiliate")

        # Update fields
        update_data = updates.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(affiliate, field, value)

        affiliate.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(affiliate)

        # Log the update
        audit_logger.log(
            AuditAction.UPDATE,
            "affiliate_profile",
            affiliate.id,
            update_data
        )

        return _format_affiliate_response(affiliate)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update affiliate profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update affiliate profile")


@router.get("/stats", response_model=ReferralStats)
def get_referral_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed referral statistics."""
    try:
        affiliate = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if not affiliate:
            raise HTTPException(status_code=404, detail="Not registered as affiliate")

        # Build query for referrals
        query = db.query(AffiliateReferral).filter(
            AffiliateReferral.affiliate_id == affiliate.id
        )

        if date_from:
            query = query.filter(AffiliateReferral.clicked_at >= date_from)
        if date_to:
            query = query.filter(AffiliateReferral.clicked_at <= date_to)

        referrals = query.all()

        # Calculate stats
        total_clicks = len(referrals)
        conversions = [r for r in referrals if r.converted_at]
        total_conversions = len(conversions)
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

        # Calculate earnings
        total_sales = sum(r.sale_amount or 0 for r in conversions)
        total_commission = sum(r.commission_amount or 0 for r in conversions)
        paid_commission = sum(r.commission_amount or 0 for r in conversions if r.commission_paid)
        pending_payout = total_commission - paid_commission

        return {
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round(conversion_rate, 2),
            "total_sales": total_sales,
            "total_commission": total_commission,
            "pending_payout": pending_payout,
            "lifetime_earnings": affiliate.total_commission
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get referral stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get referral statistics")


@router.post("/track-click")
@limiter.limit("100/minute")  # Prevent click farming
def track_referral_click(
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Track when someone clicks on a referral link.

    This endpoint is called when someone visits the site with a referral code.
    """
    # Find affiliate by code
    affiliate = db.query(Affiliate).filter(
        Affiliate.code == code,
        Affiliate.status == AffiliateStatus.ACTIVE
    ).first()

    if not affiliate:
        return {"valid": False}

    # Record the click
    referral = AffiliateReferral(
        affiliate_id=affiliate.id,
        referral_code=code,
        clicked_at=datetime.utcnow()
    )

    db.add(referral)

    # Update affiliate stats
    affiliate.total_clicks += 1

    db.commit()

    # Return referral ID to track in session/cookie
    return {
        "valid": True,
        "referral_id": referral.id,
        "affiliate_name": affiliate.display_name
    }


@router.post("/convert-referral")
def convert_referral(
    referral_id: int,
    ticket_id: int,
    sale_amount: int,
    db: Session = Depends(get_db)
):
    """
    Mark a referral as converted when a ticket is purchased.

    This is called internally when a ticket purchase is completed.
    """
    # Get referral
    referral = db.query(AffiliateReferral).filter(
        AffiliateReferral.id == referral_id,
        AffiliateReferral.converted_at.is_(None)
    ).first()

    if not referral:
        return {"success": False, "reason": "Invalid or already converted"}

    # Get affiliate
    affiliate = referral.affiliate

    # Calculate commission
    commission_amount = int(sale_amount * (affiliate.commission_rate / 100))

    # Update referral
    referral.converted_at = datetime.utcnow()
    referral.ticket_id = ticket_id
    referral.sale_amount = sale_amount
    referral.commission_amount = commission_amount

    # Update affiliate stats
    affiliate.total_conversions += 1
    affiliate.total_sales += sale_amount
    affiliate.total_commission += commission_amount
    affiliate.commission_pending += commission_amount

    db.commit()

    return {
        "success": True,
        "commission_amount": commission_amount,
        "affiliate_id": affiliate.id
    }


@router.get("/leaderboard")
def get_affiliate_leaderboard(
    period: str = "month",  # month, week, all-time
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top performing affiliates.

    Shows leaderboard based on total sales or conversions.
    """
    # Calculate date range
    if period == "week":
        date_from = datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        date_from = datetime.utcnow() - timedelta(days=30)
    else:
        date_from = None

    # Query top affiliates
    query = db.query(
        Affiliate,
        func.sum(AffiliateReferral.sale_amount).label("period_sales"),
        func.count(AffiliateReferral.id).label("period_conversions")
    ).join(
        AffiliateReferral
    ).filter(
        Affiliate.status == AffiliateStatus.ACTIVE,
        AffiliateReferral.converted_at.isnot(None)
    )

    if date_from:
        query = query.filter(AffiliateReferral.converted_at >= date_from)

    leaders = query.group_by(Affiliate.id).order_by(
        func.sum(AffiliateReferral.sale_amount).desc()
    ).limit(limit).all()

    return {
        "period": period,
        "leaderboard": [
            {
                "rank": idx + 1,
                "affiliate": {
                    "display_name": affiliate.display_name,
                    "code": affiliate.code
                },
                "sales": period_sales or 0,
                "conversions": period_conversions or 0
            }
            for idx, (affiliate, period_sales, period_conversions) in enumerate(leaders)
        ]
    }


@router.post("/request-payout")
@limiter.limit("5/day")  # Limit payout requests
def request_payout(
    request: Request,
    amount: Optional[int] = None,  # Amount in cents, or None for full balance
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request a commission payout.

    Affiliates can request payouts once they reach minimum threshold.
    """
    MIN_PAYOUT = 5000  # $50 minimum
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        affiliate = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if not affiliate:
            raise HTTPException(status_code=404, detail="Not registered as affiliate")

        if affiliate.commission_pending < MIN_PAYOUT:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum payout is ${MIN_PAYOUT/100:.2f}. Current balance: ${affiliate.commission_pending/100:.2f}"
            )

        # Determine payout amount
        payout_amount = min(amount or affiliate.commission_pending, affiliate.commission_pending)

        # Create payout record
        payout = AffiliatePayout(
            affiliate_id=affiliate.id,
            amount=payout_amount,
            status="pending"
        )

        db.add(payout)

        # Update affiliate balance
        affiliate.commission_pending -= payout_amount

        db.commit()

        # Log the payout request
        audit_logger.log(
            AuditAction.CREATE,
            "affiliate_payout",
            payout.id,
            {"amount": payout_amount, "affiliate_id": affiliate.id}
        )

        return {
            "success": True,
            "payout_id": payout.id,
            "amount": payout_amount,
            "status": "pending",
            "message": "Payout request submitted. Processing within 3-5 business days."
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to request payout: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to request payout")


@router.get("/payouts")
def get_payout_history(
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payout history for an affiliate."""
    try:
        affiliate = db.query(Affiliate).filter(
            Affiliate.event_goer_id == current_user.id
        ).first()

        if not affiliate:
            raise HTTPException(status_code=404, detail="Not registered as affiliate")

        payouts = db.query(AffiliatePayout).filter(
            AffiliatePayout.affiliate_id == affiliate.id
        ).order_by(AffiliatePayout.created_at.desc()).all()

        return {
            "payouts": [
                {
                    "id": p.id,
                    "amount": p.amount,
                    "status": p.status,
                    "created_at": p.created_at,
                    "processed_at": p.processed_at,
                    "failed_reason": p.failed_reason
                }
                for p in payouts
            ],
            "total_paid": affiliate.commission_paid,
            "pending_balance": affiliate.commission_pending
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get payout history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get payout history")


# ===================== Admin Endpoints =====================

@router.put("/admin/{affiliate_id}/approve")
def approve_affiliate(
    affiliate_id: int,
    commission_rate: Optional[float] = None,
    admin_user: EventGoer = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve an affiliate application (Admin only)."""
    audit_logger = create_audit_logger(db, admin_user.id)

    try:
        affiliate = db.query(Affiliate).filter(Affiliate.id == affiliate_id).first()
        if not affiliate:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        affiliate.status = AffiliateStatus.ACTIVE
        affiliate.approved_at = datetime.utcnow()

        if commission_rate:
            affiliate.commission_rate = commission_rate

        db.commit()

        # Log the approval
        audit_logger.log(
            AuditAction.UPDATE,
            "affiliate_approval",
            affiliate.id,
            {"status": "active", "commission_rate": commission_rate}
        )

        return {"success": True, "affiliate_id": affiliate_id, "status": "active"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to approve affiliate: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to approve affiliate")


@router.put("/admin/{affiliate_id}/suspend")
def suspend_affiliate(
    affiliate_id: int,
    reason: str,
    admin_user: EventGoer = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Suspend an affiliate account (Admin only)."""
    audit_logger = create_audit_logger(db, admin_user.id)

    try:
        affiliate = db.query(Affiliate).filter(Affiliate.id == affiliate_id).first()
        if not affiliate:
            raise HTTPException(status_code=404, detail="Affiliate not found")

        affiliate.status = AffiliateStatus.SUSPENDED
        db.commit()

        # Log the suspension
        audit_logger.log(
            AuditAction.UPDATE,
            "affiliate_suspension",
            affiliate.id,
            {"status": "suspended", "reason": reason}
        )

        return {"success": True, "affiliate_id": affiliate_id, "status": "suspended"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to suspend affiliate: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to suspend affiliate")


# ===================== Helper Functions =====================

def _generate_referral_code(db: Session, length: int = 8) -> str:
    """Generate a unique referral code."""
    while True:
        code = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(length)
        )
        # Check uniqueness
        existing = db.query(Affiliate).filter(Affiliate.code == code).first()
        if not existing:
            return code


def _format_affiliate_response(affiliate: Affiliate) -> Dict:
    """Format affiliate for API response."""
    return {
        "id": affiliate.id,
        "code": affiliate.code,
        "display_name": affiliate.display_name,
        "bio": affiliate.bio,
        "status": affiliate.status.value,
        "commission_rate": float(affiliate.commission_rate),
        "stats": {
            "total_clicks": affiliate.total_clicks,
            "total_conversions": affiliate.total_conversions,
            "total_sales": affiliate.total_sales,
            "total_commission": affiliate.total_commission,
            "pending_payout": affiliate.commission_pending
        },
        "social_links": {
            "instagram": affiliate.instagram_handle,
            "tiktok": affiliate.tiktok_handle,
            "youtube": affiliate.youtube_channel,
            "twitter": affiliate.twitter_handle
        },
        "referral_link": f"/r/{affiliate.code}"  # Frontend will handle full URL
    }