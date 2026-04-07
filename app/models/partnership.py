"""
Partnership and Sponsorship Models
For automated sponsor matching and partnership intelligence
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Sponsor(Base):
    """
    Potential sponsors and brands for partnership matching
    """
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    industry = Column(String)  # e.g., "Beverage", "Technology", "Fashion"
    category = Column(String)  # e.g., "Energy Drink", "Streaming Service", "Streetwear"

    # Brand characteristics
    target_demographics = Column(JSON)  # Age ranges, interests, income levels
    brand_values = Column(JSON)  # List of brand values/themes
    marketing_budget_range = Column(String)  # e.g., "$10K-50K", "$50K-200K"

    # Historical performance
    past_sponsorships = Column(JSON)  # List of past event sponsorships
    avg_roi = Column(Float)  # Average ROI from past sponsorships
    preferred_event_types = Column(JSON)  # ["Music Festival", "Concert", "Sports"]

    # Contact and preferences
    contact_info = Column(JSON)  # Email, phone, decision maker
    preferred_audience_size = Column(String)  # e.g., "5K-20K", "20K-100K"
    geographic_markets = Column(JSON)  # List of target markets/cities

    # Matching preferences
    excluded_genres = Column(JSON)  # Genres they won't sponsor
    required_metrics = Column(JSON)  # Minimum requirements (followers, engagement, etc.)

    # Status
    is_active = Column(Boolean, default=True)
    last_contacted = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    partnership_matches = relationship("PartnershipMatch", back_populates="sponsor")
    actual_partnerships = relationship("EventPartnership", back_populates="sponsor")


class PartnershipMatch(Base):
    """
    AI-generated partnership matches between events and sponsors
    """
    __tablename__ = "partnership_matches"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id"), nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))

    # Match scoring
    match_score = Column(Float)  # 0-100 overall match score
    audience_overlap_score = Column(Float)  # Demographic alignment
    brand_alignment_score = Column(Float)  # Values/theme alignment
    geographic_score = Column(Float)  # Location match
    budget_fit_score = Column(Float)  # Budget alignment

    # Match reasoning
    match_reasons = Column(JSON)  # List of reasons why this is a good match
    potential_concerns = Column(JSON)  # Any potential issues

    # AI-generated content
    pitch_summary = Column(Text)  # Executive summary for sponsor
    key_selling_points = Column(JSON)  # Bullet points for pitch
    projected_roi = Column(Float)  # AI-predicted ROI
    recommended_package = Column(JSON)  # Suggested sponsorship package

    # Pitch deck
    pitch_deck_url = Column(String)  # Link to generated PDF
    pitch_deck_data = Column(JSON)  # Structured data for deck

    # Status tracking
    status = Column(String, default="generated")  # generated, sent, interested, negotiating, closed, rejected
    sent_at = Column(DateTime)
    response_received_at = Column(DateTime)
    deal_value = Column(Float)  # If closed

    # Feedback
    sponsor_feedback = Column(Text)
    internal_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sponsor = relationship("Sponsor", back_populates="partnership_matches")


class EventPartnership(Base):
    """
    Actual confirmed partnerships/sponsorships for events
    """
    __tablename__ = "event_partnerships"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id"), nullable=False)
    partnership_match_id = Column(Integer, ForeignKey("partnership_matches.id"))

    # Partnership details
    partnership_type = Column(String)  # "Title Sponsor", "Presenting", "Supporting"
    deal_value = Column(Float)
    payment_terms = Column(String)

    # Deliverables
    sponsor_benefits = Column(JSON)  # What sponsor gets
    event_obligations = Column(JSON)  # What event must deliver

    # Performance metrics
    impressions_delivered = Column(Integer)
    engagement_metrics = Column(JSON)
    roi_achieved = Column(Float)

    # Status
    contract_signed_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_renewed = Column(Boolean, default=False)

    # Post-event analysis
    sponsor_satisfaction_score = Column(Float)  # 1-10
    post_event_feedback = Column(Text)
    case_study_url = Column(String)  # Success story document

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sponsor = relationship("Sponsor", back_populates="actual_partnerships")