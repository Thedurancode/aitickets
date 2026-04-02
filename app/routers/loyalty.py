"""
Loyalty & Gamification API Endpoints

Manage loyalty points, tiers, badges, and rewards for customers.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.models import EventGoer, Ticket, Event, TicketTier
from app.models_extensions import (
    LoyaltyAccount, LoyaltyTransaction, CustomerBadge,
    LoyaltyTier, BadgeType
)
from app.auth import get_current_user, get_current_admin_user
from app.audit import create_audit_logger, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/loyalty", tags=["Loyalty"])


# ===================== Pydantic Models =====================

class LoyaltyAccountResponse(BaseModel):
    """Response model for loyalty account."""
    id: int
    total_points: int
    available_points: int
    lifetime_points: int
    current_tier: str
    next_tier: Optional[Dict]
    badges: List[Dict]
    stats: Dict


class PointsTransaction(BaseModel):
    """Points transaction model."""
    id: int
    type: str
    points: int
    reason: str
    created_at: datetime


class RedeemPoints(BaseModel):
    """Request to redeem points."""
    points: int = Field(..., gt=0)
    reward_type: str = Field(..., min_length=1, max_length=50)  # discount, free_ticket, merchandise, etc.
    event_id: Optional[int] = Field(None, ge=1)


class BadgeResponse(BaseModel):
    """Badge information."""
    id: int
    badge_type: str
    name: str
    description: str
    icon: str
    points_awarded: int
    earned_at: datetime


# ===================== API Endpoints =====================

@router.get("/account", response_model=LoyaltyAccountResponse)
def get_loyalty_account(
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or create loyalty account for a user.

    Returns current points, tier, badges, and progress.
    """
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        # Get or create account
        account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.event_goer_id == current_user.id
        ).first()

        if not account:
            # Create new account
            account = LoyaltyAccount(
                event_goer_id=current_user.id,
                current_tier=LoyaltyTier.BRONZE
            )
            db.add(account)
            db.commit()
            db.refresh(account)

            # Award welcome bonus
            _award_points(
                account=account,
                points=100,
                reason="Welcome to the loyalty program!",
                db=db
            )

            # Log account creation
            audit_logger.log(
                AuditAction.CREATE,
                "loyalty_account",
                account.id,
                {"welcome_points": 100}
            )

        return _format_loyalty_response(account, db)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get/create loyalty account: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get loyalty account")


@router.post("/earn-points")
def earn_points(
    action: str,  # purchase, referral, review, social_share
    reference_id: Optional[int] = None,  # ticket_id, event_id, etc.
    points_override: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Award points for various actions.

    This is called internally when users perform qualifying actions.
    """
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        # Get loyalty account
        account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.event_goer_id == current_user.id
        ).first()

        if not account:
            account = LoyaltyAccount(event_goer_id=current_user.id)
            db.add(account)
            db.commit()
            db.refresh(account)

        # Calculate points based on action
        if points_override:
            points = points_override
            reason = f"Admin adjustment: {action}"
        else:
            points, reason = _calculate_points_for_action(action, reference_id, db)

        if points <= 0:
            return {"success": False, "reason": "No points awarded"}

        # Award points
        transaction = _award_points(
            account=account,
            points=points,
            reason=reason,
            ticket_id=reference_id if action == "purchase" else None,
            event_id=reference_id if action in ["review", "social_share"] else None,
            db=db
        )

        # Check for tier upgrade
        new_tier = _check_tier_upgrade(account)
        tier_upgraded = new_tier != account.current_tier

        if tier_upgraded:
            account.current_tier = new_tier
            # Award tier upgrade bonus
            bonus = _get_tier_upgrade_bonus(new_tier)
            if bonus > 0:
                _award_points(
                    account=account,
                    points=bonus,
                    reason=f"Tier upgrade to {new_tier.value}!",
                    db=db
                )

        # Check for new badges
        new_badges = _check_for_badges(account, db)
        for badge_type in new_badges:
            _award_badge(account, badge_type, db)

        db.commit()

        # Log the points earned
        audit_logger.log(
            AuditAction.CREATE,
            "loyalty_points",
            transaction.id,
            {
                "action": action,
                "points": points,
                "tier_upgraded": tier_upgraded,
                "new_badges": [b.value for b in new_badges]
            }
        )

        return {
            "success": True,
            "points_earned": points,
            "new_balance": account.available_points,
            "tier_upgraded": tier_upgraded,
            "new_tier": new_tier.value if tier_upgraded else None,
            "new_badges": [b.value for b in new_badges]
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to award points: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to award points")


@router.post("/redeem", response_model=Dict)
def redeem_points(
    redemption: RedeemPoints,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Redeem points for rewards.

    Points can be redeemed for discounts, free tickets, merchandise, etc.
    """
    audit_logger = create_audit_logger(db, current_user.id)

    try:
        # Get loyalty account
        account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.event_goer_id == current_user.id
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail="No loyalty account found")

        if account.available_points < redemption.points:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient points. Available: {account.available_points}"
            )

        # Process redemption based on type
        reward_value = None
        if redemption.reward_type == "discount":
            # $1 off per 100 points
            reward_value = (redemption.points // 100) * 100  # in cents
            reason = f"Redeemed for ${reward_value/100:.2f} discount"

        elif redemption.reward_type == "free_ticket":
            # 5000 points for free ticket
            if redemption.points < 5000:
                raise HTTPException(
                    status_code=400,
                    detail="Free ticket requires 5000 points"
                )
            reward_value = "free_ticket"
            reason = "Redeemed for free ticket"

        else:
            raise HTTPException(status_code=400, detail="Invalid reward type")

        # Deduct points
        transaction = LoyaltyTransaction(
            loyalty_account_id=account.id,
            type="redeem",
            points=-redemption.points,  # Negative for redemption
            reason=reason,
            event_id=redemption.event_id
        )

        db.add(transaction)
        account.available_points -= redemption.points
        account.updated_at = datetime.utcnow()

        db.commit()

        redemption_code = _generate_redemption_code()

        # Log the redemption
        audit_logger.log(
            AuditAction.CREATE,
            "loyalty_redemption",
            transaction.id,
            {
                "points": redemption.points,
                "reward_type": redemption.reward_type,
                "reward_value": reward_value,
                "redemption_code": redemption_code
            }
        )

        return {
            "success": True,
            "points_redeemed": redemption.points,
            "remaining_points": account.available_points,
            "reward": {
                "type": redemption.reward_type,
                "value": reward_value
            },
            "redemption_code": redemption_code
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to redeem points: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to redeem points")


@router.get("/transactions")
def get_points_history(
    limit: int = 50,
    offset: int = 0,
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get points transaction history."""
    try:
        account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.event_goer_id == current_user.id
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail="No loyalty account found")

        transactions = db.query(LoyaltyTransaction).filter(
            LoyaltyTransaction.loyalty_account_id == account.id
        ).order_by(
            LoyaltyTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()

        return {
            "transactions": [
                {
                    "id": t.id,
                    "type": t.type,
                    "points": t.points,
                    "reason": t.reason,
                    "created_at": t.created_at
                }
                for t in transactions
            ],
            "total": db.query(func.count(LoyaltyTransaction.id)).filter(
                LoyaltyTransaction.loyalty_account_id == account.id
            ).scalar()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get points history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get points history")


@router.get("/badges", response_model=List[BadgeResponse])
def get_earned_badges(
    current_user: EventGoer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all badges earned by a user."""
    try:
        account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.event_goer_id == current_user.id
        ).first()

        if not account:
            return []

        badges = db.query(CustomerBadge).filter(
            CustomerBadge.loyalty_account_id == account.id
        ).order_by(CustomerBadge.earned_at.desc()).all()

        return [
            {
                "id": b.id,
                "badge_type": b.badge_type.value,
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
                "points_awarded": b.points_awarded,
                "earned_at": b.earned_at
            }
            for b in badges
        ]

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to get earned badges: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get earned badges")


@router.get("/leaderboard")
def get_loyalty_leaderboard(
    period: str = "month",  # month, week, all-time
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get loyalty points leaderboard.

    Shows top users by points earned in period.
    """
    # Calculate date range
    if period == "week":
        date_from = datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        date_from = datetime.utcnow() - timedelta(days=30)
    else:
        date_from = None

    # Query for leaderboard
    if date_from:
        # Points earned in period
        subquery = db.query(
            LoyaltyTransaction.loyalty_account_id,
            func.sum(LoyaltyTransaction.points).label("period_points")
        ).filter(
            LoyaltyTransaction.created_at >= date_from,
            LoyaltyTransaction.points > 0  # Only count earned points
        ).group_by(
            LoyaltyTransaction.loyalty_account_id
        ).subquery()

        leaders = db.query(
            LoyaltyAccount,
            EventGoer,
            subquery.c.period_points
        ).join(
            EventGoer
        ).join(
            subquery,
            LoyaltyAccount.id == subquery.c.loyalty_account_id
        ).order_by(
            subquery.c.period_points.desc()
        ).limit(limit).all()

    else:
        # All-time leaders
        leaders = db.query(
            LoyaltyAccount,
            EventGoer
        ).join(
            EventGoer
        ).order_by(
            LoyaltyAccount.lifetime_points.desc()
        ).limit(limit).all()

    if date_from:
        return {
            "period": period,
            "leaderboard": [
                {
                    "rank": idx + 1,
                    "user": {
                        "name": goer.name,
                        "tier": account.current_tier.value
                    },
                    "points": period_points,
                    "badges": db.query(func.count(CustomerBadge.id)).filter(
                        CustomerBadge.loyalty_account_id == account.id
                    ).scalar()
                }
                for idx, (account, goer, period_points) in enumerate(leaders)
            ]
        }
    else:
        return {
            "period": "all-time",
            "leaderboard": [
                {
                    "rank": idx + 1,
                    "user": {
                        "name": goer.name,
                        "tier": account.current_tier.value
                    },
                    "points": account.lifetime_points,
                    "badges": db.query(func.count(CustomerBadge.id)).filter(
                        CustomerBadge.loyalty_account_id == account.id
                    ).scalar()
                }
                for idx, (account, goer) in enumerate(leaders)
            ]
        }


@router.get("/tiers")
def get_tier_benefits():
    """Get information about all loyalty tiers and their benefits."""
    return {
        "tiers": [
            {
                "name": LoyaltyTier.BRONZE.value,
                "points_required": 0,
                "benefits": [
                    "Earn 1 point per $1 spent",
                    "Birthday bonus points",
                    "Early access to select events"
                ],
                "color": "#CD7F32"
            },
            {
                "name": LoyaltyTier.SILVER.value,
                "points_required": 1000,
                "benefits": [
                    "Earn 1.5 points per $1 spent",
                    "10% bonus points on all purchases",
                    "Priority customer support",
                    "Exclusive silver member events"
                ],
                "color": "#C0C0C0"
            },
            {
                "name": LoyaltyTier.GOLD.value,
                "points_required": 3000,
                "benefits": [
                    "Earn 2 points per $1 spent",
                    "20% bonus points on all purchases",
                    "Free ticket upgrades",
                    "VIP lounge access",
                    "Gold member exclusive events"
                ],
                "color": "#FFD700"
            },
            {
                "name": LoyaltyTier.PLATINUM.value,
                "points_required": 10000,
                "benefits": [
                    "Earn 3 points per $1 spent",
                    "30% bonus points on all purchases",
                    "Complimentary tickets",
                    "Backstage meet & greets",
                    "Personal event concierge",
                    "Platinum-only events"
                ],
                "color": "#E5E4E2"
            }
        ]
    }


# ===================== Helper Functions =====================

def _award_points(
    account: LoyaltyAccount,
    points: int,
    reason: str,
    ticket_id: Optional[int] = None,
    event_id: Optional[int] = None,
    db: Session = None
) -> LoyaltyTransaction:
    """Award points to a loyalty account."""
    transaction = LoyaltyTransaction(
        loyalty_account_id=account.id,
        type="earn",
        points=points,
        reason=reason,
        ticket_id=ticket_id,
        event_id=event_id
    )

    db.add(transaction)

    # Update account balances
    account.total_points += points
    account.available_points += points
    account.lifetime_points += points
    account.updated_at = datetime.utcnow()

    return transaction


def _calculate_points_for_action(
    action: str,
    reference_id: Optional[int],
    db: Session
) -> tuple[int, str]:
    """Calculate points to award based on action."""
    if action == "purchase" and reference_id:
        # 1 point per dollar spent (base rate)
        ticket = db.query(Ticket).filter(Ticket.id == reference_id).first()
        if ticket:
            points = ticket.purchase_price // 100  # Convert cents to dollars
            return points, f"Purchase - Ticket #{ticket.id}"

    elif action == "referral":
        return 500, "Successful referral"

    elif action == "review" and reference_id:
        return 50, f"Event review - Event #{reference_id}"

    elif action == "social_share" and reference_id:
        return 25, f"Social media share - Event #{reference_id}"

    return 0, ""


def _check_tier_upgrade(account: LoyaltyAccount) -> LoyaltyTier:
    """Check if account qualifies for tier upgrade."""
    points = account.lifetime_points

    if points >= 10000:
        return LoyaltyTier.PLATINUM
    elif points >= 3000:
        return LoyaltyTier.GOLD
    elif points >= 1000:
        return LoyaltyTier.SILVER
    else:
        return LoyaltyTier.BRONZE


def _get_tier_upgrade_bonus(tier: LoyaltyTier) -> int:
    """Get bonus points for tier upgrade."""
    bonuses = {
        LoyaltyTier.SILVER: 100,
        LoyaltyTier.GOLD: 300,
        LoyaltyTier.PLATINUM: 1000
    }
    return bonuses.get(tier, 0)


def _check_for_badges(account: LoyaltyAccount, db: Session) -> List[BadgeType]:
    """Check if account has earned any new badges."""
    new_badges = []

    # Get existing badges
    existing = db.query(CustomerBadge.badge_type).filter(
        CustomerBadge.loyalty_account_id == account.id
    ).all()
    existing_types = {b[0] for b in existing}

    # Check each badge type
    if BadgeType.FIRST_EVENT not in existing_types and account.total_purchases >= 1:
        new_badges.append(BadgeType.FIRST_EVENT)

    if BadgeType.SOCIAL_BUTTERFLY not in existing_types and account.total_purchases >= 10:
        new_badges.append(BadgeType.SOCIAL_BUTTERFLY)

    if BadgeType.SUPERFAN not in existing_types and account.total_purchases >= 50:
        new_badges.append(BadgeType.SUPERFAN)

    if BadgeType.REFERRAL_MASTER not in existing_types and account.total_referrals >= 10:
        new_badges.append(BadgeType.REFERRAL_MASTER)

    return new_badges


def _award_badge(account: LoyaltyAccount, badge_type: BadgeType, db: Session):
    """Award a badge to an account."""
    badge_info = {
        BadgeType.FIRST_EVENT: ("First Timer", "Attended your first event!", "🎉", 50),
        BadgeType.EARLY_BIRD: ("Early Bird", "Purchased tickets within first hour", "🐦", 100),
        BadgeType.VIP_SPENDER: ("VIP Spender", "Spent over $1000 on events", "💎", 500),
        BadgeType.SOCIAL_BUTTERFLY: ("Social Butterfly", "Attended 10+ events", "🦋", 200),
        BadgeType.SUPERFAN: ("Superfan", "Attended 50+ events!", "⭐", 1000),
        BadgeType.REFERRAL_MASTER: ("Referral Master", "Referred 10+ friends", "🤝", 500),
    }

    name, desc, icon, points = badge_info.get(badge_type, ("Unknown", "", "❓", 0))

    badge = CustomerBadge(
        loyalty_account_id=account.id,
        badge_type=badge_type,
        name=name,
        description=desc,
        icon=icon,
        points_awarded=points
    )

    db.add(badge)

    # Award badge points
    if points > 0:
        _award_points(
            account=account,
            points=points,
            reason=f"Badge earned: {name}",
            db=db
        )


def _format_loyalty_response(account: LoyaltyAccount, db: Session) -> Dict:
    """Format loyalty account for API response."""
    # Get badges
    badges = db.query(CustomerBadge).filter(
        CustomerBadge.loyalty_account_id == account.id
    ).all()

    # Calculate next tier
    next_tier = None
    if account.current_tier == LoyaltyTier.BRONZE:
        next_tier = {
            "name": LoyaltyTier.SILVER.value,
            "points_needed": 1000 - account.lifetime_points,
            "progress": (account.lifetime_points / 1000) * 100
        }
    elif account.current_tier == LoyaltyTier.SILVER:
        next_tier = {
            "name": LoyaltyTier.GOLD.value,
            "points_needed": 3000 - account.lifetime_points,
            "progress": ((account.lifetime_points - 1000) / 2000) * 100
        }
    elif account.current_tier == LoyaltyTier.GOLD:
        next_tier = {
            "name": LoyaltyTier.PLATINUM.value,
            "points_needed": 10000 - account.lifetime_points,
            "progress": ((account.lifetime_points - 3000) / 7000) * 100
        }

    return {
        "id": account.id,
        "total_points": account.total_points,
        "available_points": account.available_points,
        "lifetime_points": account.lifetime_points,
        "current_tier": account.current_tier.value,
        "next_tier": next_tier,
        "badges": [
            {
                "type": b.badge_type.value,
                "name": b.name,
                "icon": b.icon,
                "earned_at": b.earned_at
            }
            for b in badges
        ],
        "stats": {
            "total_purchases": account.total_purchases,
            "total_referrals": account.total_referrals,
            "total_reviews": account.total_reviews
        }
    }


def _generate_redemption_code() -> str:
    """Generate a unique redemption code."""
    import secrets
    return f"REDEEM-{secrets.token_hex(4).upper()}"