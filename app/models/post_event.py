"""
Post-Event Intelligence Models
For capturing learnings and improving future events
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class PostEventAnalysis(Base):
    """
    Comprehensive post-event analysis and learnings
    """
    __tablename__ = "post_event_analyses"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True)
    artist_id = Column(Integer, ForeignKey("artists.id"))

    # Attendance metrics
    tickets_sold = Column(Integer)
    actual_attendance = Column(Integer)  # People who showed up
    no_show_rate = Column(Float)  # Percentage who didn't attend
    capacity_percentage = Column(Float)  # How full was the venue

    # Financial performance
    total_revenue = Column(Float)
    ticket_revenue = Column(Float)
    merchandise_revenue = Column(Float)
    concession_revenue = Column(Float)
    sponsorship_revenue = Column(Float)

    total_costs = Column(Float)
    artist_fee = Column(Float)
    venue_cost = Column(Float)
    production_cost = Column(Float)
    marketing_spend = Column(Float)

    net_profit = Column(Float)
    profit_margin = Column(Float)
    roi = Column(Float)

    # Marketing effectiveness
    marketing_metrics = Column(JSON)  # CTR, conversion rates, CAC by channel
    best_performing_channel = Column(String)
    worst_performing_channel = Column(String)
    viral_moments = Column(JSON)  # Social media spikes, what caused them

    # Audience insights
    actual_demographics = Column(JSON)  # Real vs predicted demographics
    demographic_surprises = Column(JSON)  # Unexpected audience segments
    audience_sentiment_score = Column(Float)  # Overall satisfaction 1-10
    net_promoter_score = Column(Float)  # Would recommend score

    # Operational learnings
    setup_issues = Column(JSON)  # Problems during setup
    technical_issues = Column(JSON)  # Sound, lighting, streaming issues
    security_incidents = Column(JSON)  # Any security concerns
    vendor_performance = Column(JSON)  # How each vendor performed

    # Peak moments
    peak_attendance_time = Column(DateTime)
    peak_concession_time = Column(DateTime)
    peak_social_mentions = Column(DateTime)
    most_engaged_song = Column(String)  # For concerts

    # Weather and external factors
    weather_conditions = Column(JSON)
    competing_events = Column(JSON)
    external_factors = Column(JSON)  # Traffic, protests, etc.

    # Social media impact
    total_social_mentions = Column(Integer)
    social_reach = Column(Integer)
    user_generated_content = Column(Integer)  # Photos/videos posted
    influencer_attendance = Column(JSON)  # Notable attendees

    # Predictions vs Reality
    predicted_sellout_date = Column(DateTime)
    actual_sellout_date = Column(DateTime)
    predicted_demographics = Column(JSON)
    prediction_accuracy_score = Column(Float)  # How accurate were our predictions

    # Key learnings
    success_factors = Column(JSON)  # What went well
    improvement_areas = Column(JSON)  # What could be better
    surprising_insights = Column(JSON)  # Unexpected discoveries

    # Recommendations
    pricing_recommendations = Column(JSON)
    marketing_recommendations = Column(JSON)
    operational_recommendations = Column(JSON)
    future_artist_recommendations = Column(JSON)  # Similar artists to book

    # Intelligence score
    data_completeness_score = Column(Float)  # How much data we captured
    insight_quality_score = Column(Float)  # How valuable the insights are
    actionability_score = Column(Float)  # How actionable the learnings are

    # Report
    full_report_url = Column(String)  # Link to detailed PDF report
    executive_summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    feedback_entries = relationship("EventFeedback", back_populates="analysis")
    learnings = relationship("EventLearning", back_populates="analysis")


class EventFeedback(Base):
    """
    Individual feedback entries from various sources
    """
    __tablename__ = "event_feedback"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("post_event_analyses.id"))

    # Source information
    source = Column(String)  # "survey", "social_media", "review_site", "email"
    source_platform = Column(String)  # "instagram", "google", "ticketmaster", etc.

    # Feedback content
    rating = Column(Float)  # Numerical rating if available
    sentiment = Column(String)  # positive, neutral, negative
    feedback_text = Column(Text)

    # Categorization
    category = Column(String)  # "venue", "artist", "sound", "parking", etc.
    is_complaint = Column(Boolean, default=False)
    requires_response = Column(Boolean, default=False)

    # User info (anonymized)
    user_demographic = Column(JSON)  # Age range, location, etc.
    is_verified_attendee = Column(Boolean, default=False)

    # Processing
    processed = Column(Boolean, default=False)
    ai_summary = Column(Text)  # AI-generated summary of feedback
    action_taken = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("PostEventAnalysis", back_populates="feedback_entries")


class EventLearning(Base):
    """
    Specific learnings extracted from events that can be applied to future events
    """
    __tablename__ = "event_learnings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("post_event_analyses.id"))

    # Learning details
    category = Column(String)  # "pricing", "marketing", "operations", "audience"
    learning_type = Column(String)  # "success", "failure", "insight", "optimization"

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # Impact metrics
    impact_level = Column(String)  # "high", "medium", "low"
    financial_impact = Column(Float)  # Estimated $ impact
    applicable_to = Column(JSON)  # Types of events this applies to

    # Evidence
    supporting_data = Column(JSON)  # Metrics that support this learning
    confidence_score = Column(Float)  # How confident we are in this learning

    # Application
    recommended_action = Column(Text)
    implementation_complexity = Column(String)  # "easy", "medium", "hard"
    has_been_applied = Column(Boolean, default=False)
    applied_to_events = Column(JSON)  # List of event IDs where applied

    # Validation
    validated = Column(Boolean, default=False)
    validation_results = Column(JSON)  # Results when applied to other events

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analysis = relationship("PostEventAnalysis", back_populates="learnings")


class IntelligencePattern(Base):
    """
    Patterns discovered across multiple events
    """
    __tablename__ = "intelligence_patterns"

    id = Column(Integer, primary_key=True, index=True)

    # Pattern identification
    pattern_name = Column(String, nullable=False, unique=True)
    pattern_type = Column(String)  # "seasonal", "demographic", "pricing", "marketing"
    description = Column(Text)

    # Pattern details
    conditions = Column(JSON)  # When this pattern applies
    expected_outcome = Column(JSON)  # What typically happens
    confidence_level = Column(Float)  # Statistical confidence

    # Evidence
    supporting_events = Column(JSON)  # Event IDs that demonstrate this pattern
    occurrence_count = Column(Integer)  # How many times observed
    first_observed = Column(DateTime)
    last_observed = Column(DateTime)

    # Predictive power
    prediction_accuracy = Column(Float)  # How well it predicts outcomes
    false_positive_rate = Column(Float)
    false_negative_rate = Column(Float)

    # Application
    recommended_strategy = Column(Text)
    expected_improvement = Column(JSON)  # Expected metrics improvement
    risk_factors = Column(JSON)  # When not to apply

    # Status
    is_active = Column(Boolean, default=True)
    requires_review = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)