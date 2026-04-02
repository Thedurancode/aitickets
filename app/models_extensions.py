"""
Model Extensions for New Features

Additional models for:
- Group buying / split payments
- Influencer/affiliate program
- Gamification & loyalty
- Enhanced post-event engagement
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Enum, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models import utcnow
import enum


# =============================================================================
# GROUP BUYING & SPLIT PAYMENTS
# =============================================================================

class GroupPurchaseStatus(str, enum.Enum):
    PENDING = "pending"  # Waiting for contributions
    PARTIAL = "partial"  # Some people paid
    COMPLETE = "complete"  # All paid
    EXPIRED = "expired"  # Time limit exceeded
    CANCELLED = "cancelled"  # Organizer cancelled


class GroupPurchase(Base):
    """Group ticket purchase with split payment."""
    __tablename__ = "group_purchases"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    organizer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False)

    # Group details
    group_name = Column(String(255), nullable=True)  # Optional group name
    total_tickets = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)  # Total in cents

    # Payment tracking
    amount_paid = Column(Integer, default=0)  # Amount collected so far
    amount_remaining = Column(Integer, nullable=False)  # Amount still needed

    # Status
    status = Column(Enum(GroupPurchaseStatus), default=GroupPurchaseStatus.PENDING)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Payment deadline

    # Stripe
    stripe_payment_intent_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    event = relationship("Event")
    organizer = relationship("EventGoer", foreign_keys=[organizer_id])
    contributions = relationship("GroupContribution", back_populates="group_purchase", cascade="all, delete-orphan")


class GroupContribution(Base):
    """Individual contribution to a group purchase."""
    __tablename__ = "group_contributions"

    id = Column(Integer, primary_key=True, index=True)
    group_purchase_id = Column(Integer, ForeignKey("group_purchases.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False)

    # Contribution details
    amount = Column(Integer, nullable=False)  # Amount in cents
    ticket_count = Column(Integer, default=1)  # Number of tickets for this person

    # Payment
    stripe_payment_intent_id = Column(String(255), nullable=True)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    group_purchase = relationship("GroupPurchase", back_populates="contributions")
    contributor = relationship("EventGoer")


# =============================================================================
# INFLUENCER / AFFILIATE PROGRAM
# =============================================================================

class AffiliateStatus(str, enum.Enum):
    PENDING = "pending"  # Application pending
    ACTIVE = "active"  # Approved and active
    SUSPENDED = "suspended"  # Temporarily suspended
    TERMINATED = "terminated"  # Permanently terminated


class Affiliate(Base):
    """Influencer/affiliate accounts."""
    __tablename__ = "affiliates"

    id = Column(Integer, primary_key=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, unique=True)

    # Affiliate details
    code = Column(String(50), unique=True, nullable=False, index=True)  # Unique referral code
    display_name = Column(String(255), nullable=True)  # Public name
    bio = Column(Text, nullable=True)

    # Social links
    instagram_handle = Column(String(100), nullable=True)
    tiktok_handle = Column(String(100), nullable=True)
    youtube_channel = Column(String(255), nullable=True)
    twitter_handle = Column(String(100), nullable=True)

    # Commission
    commission_rate = Column(Numeric(5, 2), default=10.00)  # Percentage (default 10%)
    total_sales = Column(Integer, default=0)  # Total sales generated (cents)
    total_commission = Column(Integer, default=0)  # Total commission earned (cents)
    commission_paid = Column(Integer, default=0)  # Commission paid out (cents)
    commission_pending = Column(Integer, default=0)  # Pending payout (cents)

    # Stats
    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)

    # Status
    status = Column(Enum(AffiliateStatus), default=AffiliateStatus.PENDING)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Stripe Connect (for payouts)
    stripe_account_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    event_goer = relationship("EventGoer")
    referrals = relationship("AffiliateReferral", back_populates="affiliate", cascade="all, delete-orphan")
    payouts = relationship("AffiliatePayout", back_populates="affiliate", cascade="all, delete-orphan")


class AffiliateReferral(Base):
    """Track referrals from affiliates."""
    __tablename__ = "affiliate_referrals"

    id = Column(Integer, primary_key=True, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliates.id"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)

    # Referral tracking
    referral_code = Column(String(50), nullable=False, index=True)
    clicked_at = Column(DateTime(timezone=True), default=utcnow)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # Commission
    sale_amount = Column(Integer, nullable=True)  # Sale amount (cents)
    commission_amount = Column(Integer, nullable=True)  # Commission earned (cents)
    commission_paid = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="referrals")
    ticket = relationship("Ticket")


class AffiliatePayout(Base):
    """Affiliate commission payouts."""
    __tablename__ = "affiliate_payouts"

    id = Column(Integer, primary_key=True, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliates.id"), nullable=False, index=True)

    # Payout details
    amount = Column(Integer, nullable=False)  # Amount in cents
    stripe_transfer_id = Column(String(255), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="payouts")


# =============================================================================
# GAMIFICATION & LOYALTY
# =============================================================================

class LoyaltyTier(str, enum.Enum):
    BRONZE = "bronze"  # 0-999 points
    SILVER = "silver"  # 1000-2999 points
    GOLD = "gold"  # 3000-9999 points
    PLATINUM = "platinum"  # 10000+ points


class LoyaltyAccount(Base):
    """Customer loyalty points account."""
    __tablename__ = "loyalty_accounts"

    id = Column(Integer, primary_key=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, unique=True)

    # Points
    total_points = Column(Integer, default=0)
    available_points = Column(Integer, default=0)  # After redemptions
    lifetime_points = Column(Integer, default=0)  # Never decreases

    # Tier
    current_tier = Column(Enum(LoyaltyTier), default=LoyaltyTier.BRONZE)

    # Stats
    total_purchases = Column(Integer, default=0)
    total_referrals = Column(Integer, default=0)
    total_reviews = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    event_goer = relationship("EventGoer")
    transactions = relationship("LoyaltyTransaction", back_populates="loyalty_account", cascade="all, delete-orphan")
    badges = relationship("CustomerBadge", back_populates="loyalty_account", cascade="all, delete-orphan")


class LoyaltyTransaction(Base):
    """Loyalty points transactions (earn/redeem)."""
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False, index=True)

    # Transaction details
    type = Column(String(50), nullable=False)  # earn, redeem, expire, bonus
    points = Column(Integer, nullable=False)  # Positive for earn, negative for redeem
    reason = Column(String(255), nullable=False)  # "Ticket purchase", "Referral bonus", etc.

    # Related entities
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="transactions")


class BadgeType(str, enum.Enum):
    FIRST_EVENT = "first_event"
    EARLY_BIRD = "early_bird"
    VIP_SPENDER = "vip_spender"
    SOCIAL_BUTTERFLY = "social_butterfly"  # Attended 10+ events
    SUPERFAN = "superfan"  # 50+ events
    REFERRAL_MASTER = "referral_master"  # 10+ referrals


class CustomerBadge(Base):
    """Achievement badges for gamification."""
    __tablename__ = "customer_badges"

    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False, index=True)

    # Badge details
    badge_type = Column(Enum(BadgeType), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Emoji or icon name

    # Reward
    points_awarded = Column(Integer, default=0)

    # Timestamps
    earned_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    loyalty_account = relationship("LoyaltyAccount", back_populates="badges")
