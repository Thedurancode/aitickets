"""
Campaign and Ad Creative Models
Stores auto-generated ad campaigns and individual ad creatives
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Campaign(Base):
    """
    Marketing campaign for an event
    Can be Meta Ads, Google Ads, Email, or Social Media
    """
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    # Campaign details
    platform = Column(String(50), nullable=False)  # "meta", "google", "email", "social_organic"
    campaign_type = Column(String(50), nullable=False)  # "awareness", "conversion", "retargeting", etc.
    name = Column(String(255), nullable=False)
    objective = Column(String(50))  # "REACH", "CONVERSIONS", "VIDEO_VIEWS", etc.

    # Status
    status = Column(String(20), default="draft")  # "draft", "approved", "scheduled", "active", "paused", "completed"

    # Budget (in cents)
    budget_total = Column(Integer, default=0)  # Total budget for campaign
    budget_daily = Column(Integer, default=0)  # Daily budget limit
    spend_total = Column(Integer, default=0)  # Amount spent so far

    # Schedule
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Platform-specific settings
    platform_campaign_id = Column(String(255), nullable=True)  # ID from Meta/Google API after publishing
    settings = Column(JSON, nullable=True)  # Platform-specific config

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="campaigns")
    ad_creatives = relationship("AdCreative", back_populates="campaign", cascade="all, delete-orphan")
    performance = relationship("CampaignPerformance", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign {self.name} ({self.platform}/{self.campaign_type})>"


class AdCreative(Base):
    """
    Individual ad creative (image ad, video ad, email, social post)
    """
    __tablename__ = "ad_creatives"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)

    # Ad details
    platform = Column(String(50), nullable=False)  # "facebook", "instagram", "google_search", "email"
    format = Column(String(50), nullable=False)  # "image", "video", "carousel", "story", "text"
    name = Column(String(255), nullable=True)  # Internal name

    # Creative content
    headline = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    cta = Column(String(100), nullable=True)  # "Buy Tickets", "Learn More", "Get Tickets Now"

    # Media
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    link_url = Column(String(500), nullable=True)  # Event page URL

    # Targeting
    target_audience = Column(JSON, nullable=True)  # Age, location, interests, behaviors
    placements = Column(JSON, nullable=True)  # ["facebook_feed", "instagram_stories"]

    # Status
    status = Column(String(20), default="draft")  # "draft", "approved", "active", "paused", "rejected"

    # A/B Testing
    is_test_variant = Column(Boolean, default=False)
    test_group = Column(String(50), nullable=True)  # "A", "B", "C"

    # Platform-specific
    platform_ad_id = Column(String(255), nullable=True)  # ID from Meta/Google API

    # Budget allocation (if different from campaign)
    budget_allocation = Column(Integer, nullable=True)  # In cents

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="ad_creatives")
    performance = relationship("AdPerformance", back_populates="ad_creative", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AdCreative {self.headline[:30]}... ({self.platform}/{self.format})>"


class CampaignPerformance(Base):
    """
    Campaign-level performance metrics (daily rollup)
    """
    __tablename__ = "campaign_performance"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)  # Ticket purchases

    # Financial
    spend = Column(Integer, default=0)  # In cents
    revenue = Column(Integer, default=0)  # Ticket revenue attributed

    # Calculated metrics
    ctr = Column(Float, default=0.0)  # Click-through rate
    cpc = Column(Float, default=0.0)  # Cost per click
    cpa = Column(Float, default=0.0)  # Cost per acquisition
    roas = Column(Float, default=0.0)  # Return on ad spend

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="performance")

    def __repr__(self):
        return f"<CampaignPerformance {self.date} - ${self.spend/100:.2f} spent, {self.conversions} conversions>"


class AdPerformance(Base):
    """
    Ad-level performance metrics (daily rollup)
    """
    __tablename__ = "ad_performance"

    id = Column(Integer, primary_key=True, index=True)
    ad_creative_id = Column(Integer, ForeignKey("ad_creatives.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)  # Ticket purchases

    # Engagement (social media)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    saves = Column(Integer, default=0)

    # Video metrics
    video_views = Column(Integer, default=0)
    video_view_duration_avg = Column(Float, default=0.0)  # In seconds

    # Financial
    spend = Column(Integer, default=0)  # In cents
    revenue = Column(Integer, default=0)  # Ticket revenue attributed

    # Calculated metrics
    ctr = Column(Float, default=0.0)  # Click-through rate
    cpc = Column(Float, default=0.0)  # Cost per click
    cpa = Column(Float, default=0.0)  # Cost per acquisition
    roas = Column(Float, default=0.0)  # Return on ad spend
    engagement_rate = Column(Float, default=0.0)  # (likes + shares + comments) / impressions

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ad_creative = relationship("AdCreative", back_populates="performance")

    def __repr__(self):
        return f"<AdPerformance {self.date} - {self.impressions} impressions, {self.clicks} clicks>"
