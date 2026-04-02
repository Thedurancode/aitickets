"""
Google Ads Campaign Model (optional add-on)

Add this to app/models.py to enable Google Ads tracking:

from app.models_google_ads import GoogleAdCampaign
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from app.database import Base
from app.models import utcnow


class GoogleAdCampaign(Base):
    """Track Google Ads campaigns for event promotion."""
    __tablename__ = "google_ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Google Ads API fields
    google_campaign_id = Column(String(100), nullable=True, index=True)
    google_ad_group_id = Column(String(100), nullable=True)
    
    # Targeting
    target_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    
    # Budget
    budget_cents = Column(Integer, nullable=False)  # Total budget in cents
    daily_budget_cents = Column(Integer, nullable=False)

    # Campaign settings
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Ad creative
    headline_1 = Column(String(30), nullable=False)  # Google Ads max 30 chars
    headline_2 = Column(String(30), nullable=True)
    headline_3 = Column(String(30), nullable=True)
    description_1 = Column(String(90), nullable=False)  # Google Ads max 90 chars
    description_2 = Column(String(90), nullable=True)
    final_url = Column(String(500), nullable=False)  # Landing page URL

    # Targeting
    keywords = Column(Text, nullable=True)  # JSON array of keywords
    locations = Column(Text, nullable=True)  # JSON array of geo-targets
    age_ranges = Column(String(100), nullable=True)  # e.g., "18-24,25-34"
    
    # Performance metrics (synced from Google Ads API)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    cost_cents = Column(Integer, default=0)  # Actual spend
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# To enable Google Ads tracking:
# 1. Add this model to app/models.py imports
# 2. Run migration to create table
# 3. Configure Google Ads API credentials in .env
# 4. Use MCP tools to create campaigns
