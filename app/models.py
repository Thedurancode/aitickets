from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    CHECKED_IN = "checked_in"


class NotificationType(str, enum.Enum):
    TICKET_CONFIRMATION = "ticket_confirmation"
    EVENT_REMINDER = "event_reminder"
    EVENT_UPDATE = "event_update"
    EVENT_CANCELLED = "event_cancelled"
    MARKETING = "marketing"
    SMS_TICKET = "sms_ticket"
    CART_RECOVERY = "cart_recovery"
    SURVEY_REQUEST = "survey_request"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class DiscountType(str, enum.Enum):
    PERCENT = "percent"
    FIXED_CENTS = "fixed_cents"


class TierStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD_OUT = "sold_out"


class WaitlistStatus(str, enum.Enum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    PURCHASED = "purchased"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


event_category_link = Table(
    "event_category_link",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("event_categories.id"), primary_key=True),
)


class EventCategory(Base):
    __tablename__ = "event_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)  # Hex color for UI badges
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    events = relationship("Event", secondary=event_category_link, back_populates="categories")


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=False)
    phone = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    events = relationship("Event", back_populates="venue", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    promo_video_url = Column(String(500), nullable=True)  # YouTube or video URL
    post_event_video_url = Column(String(500), nullable=True)  # Post-event recap/highlight video
    event_date = Column(String(20), nullable=False)  # YYYY-MM-DD format
    event_time = Column(String(10), nullable=False)  # HH:MM format
    doors_open_time = Column(String(10), nullable=True)  # HH:MM format
    status = Column(Enum(EventStatus), default=EventStatus.SCHEDULED)
    is_visible = Column(Boolean, default=True)
    cancellation_reason = Column(Text, nullable=True)
    promoter_phone = Column(String(50), nullable=True)
    promoter_name = Column(String(255), nullable=True)
    series_id = Column(String(36), nullable=True, index=True)  # UUID linking recurring events
    auto_reminder_hours = Column(Integer, nullable=True, default=24)  # hours before event; NULL = disabled
    auto_reminder_use_sms = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    venue = relationship("Venue", back_populates="events")
    ticket_tiers = relationship("TicketTier", back_populates="event", cascade="all, delete-orphan")
    updates = relationship("EventUpdate", back_populates="event", cascade="all, delete-orphan")
    categories = relationship("EventCategory", secondary=event_category_link, back_populates="events")
    photos = relationship("EventPhoto", back_populates="event", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="event", cascade="all, delete-orphan")


class EventPhoto(Base):
    __tablename__ = "event_photos"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=False)
    uploaded_by_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event", back_populates="photos")


class EventUpdate(Base):
    """Track updates/changes made to events for notification purposes."""
    __tablename__ = "event_updates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    update_type = Column(String(50), nullable=False)  # date_change, time_change, venue_change, cancelled, etc.
    message = Column(Text, nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    notifications_sent = Column(Boolean, default=False)

    event = relationship("Event", back_populates="updates")


class TicketTier(Base):
    __tablename__ = "ticket_tiers"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)  # Price in cents
    quantity_available = Column(Integer, nullable=False)
    quantity_sold = Column(Integer, default=0)
    status = Column(Enum(TierStatus), default=TierStatus.ACTIVE)

    # Stripe integration
    stripe_product_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True, index=True)

    event = relationship("Event", back_populates="ticket_tiers")
    tickets = relationship("Ticket", back_populates="ticket_tier", cascade="all, delete-orphan")


class EventGoer(Base):
    __tablename__ = "event_goers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)

    # Notification preferences
    email_opt_in = Column(Boolean, default=True)  # Transactional emails (tickets, reminders)
    sms_opt_in = Column(Boolean, default=False)   # SMS notifications
    marketing_opt_in = Column(Boolean, default=False)  # Marketing communications

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tickets = relationship("Ticket", back_populates="event_goer", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="event_goer", cascade="all, delete-orphan")
    notes = relationship("CustomerNote", back_populates="event_goer", cascade="all, delete-orphan")
    preferences = relationship("CustomerPreference", back_populates="event_goer", uselist=False, cascade="all, delete-orphan")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_tier_id = Column(Integer, ForeignKey("ticket_tiers.id"), nullable=False, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    stripe_checkout_session_id = Column(String(255), nullable=True, index=True)
    qr_code_token = Column(String(100), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.PENDING)
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    recovery_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Reminder tracking
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Promo code tracking
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=True)
    discount_amount_cents = Column(Integer, nullable=True)

    # UTM attribution tracking
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)

    ticket_tier = relationship("TicketTier", back_populates="tickets")
    event_goer = relationship("EventGoer", back_populates="tickets")
    promo_code = relationship("PromoCode")


class Notification(Base):
    """Track all notifications sent to users."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)

    notification_type = Column(Enum(NotificationType), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)

    subject = Column(String(255), nullable=True)  # For emails
    message = Column(Text, nullable=False)

    # Delivery tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_reason = Column(Text, nullable=True)

    # External references
    external_id = Column(String(255), nullable=True)  # Twilio SID, Resend ID, etc.

    created_at = Column(DateTime(timezone=True), default=utcnow)

    event_goer = relationship("EventGoer", back_populates="notifications")


class MarketingCampaign(Base):
    """Track marketing campaigns."""
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Targeting
    target_all = Column(Boolean, default=False)  # Send to all opted-in users
    target_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Send to attendees of specific event
    target_segments = Column(Text, nullable=True)  # JSON: {"is_vip": true, "min_events": 3, "min_spent_cents": 50000, "category_ids": [1,2]}

    # Stats
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)

    status = Column(String(50), default="draft")  # draft, scheduled, sending, sent
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class MarketingList(Base):
    """Saved audience segments for reusable targeting."""
    __tablename__ = "marketing_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    segment_filters = Column(Text, nullable=False)  # JSON, same format as MarketingCampaign.target_segments
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CustomerNote(Base):
    """Store notes about customers from AI agent conversations."""
    __tablename__ = "customer_notes"

    id = Column(Integer, primary_key=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    note_type = Column(String(50), nullable=False)  # preference, interaction, issue, vip, etc.
    note = Column(Text, nullable=False)
    created_by = Column(String(100), default="ai_agent")  # ai_agent, staff, system
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event_goer = relationship("EventGoer", back_populates="notes")


class CustomerPreference(Base):
    """Store customer preferences for personalization."""
    __tablename__ = "customer_preferences"

    id = Column(Integer, primary_key=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, unique=True)

    # Seating preferences
    preferred_section = Column(String(100), nullable=True)  # e.g., "lower bowl", "courtside"
    accessibility_required = Column(Boolean, default=False)
    accessibility_notes = Column(Text, nullable=True)

    # Communication preferences
    preferred_language = Column(String(20), default="en")
    preferred_contact_method = Column(String(20), default="sms")  # sms, email, phone

    # Interests
    favorite_teams = Column(Text, nullable=True)  # JSON list
    favorite_event_types = Column(Text, nullable=True)  # JSON list: concerts, sports, comedy

    # VIP status
    is_vip = Column(Boolean, default=False)
    vip_tier = Column(String(50), nullable=True)  # gold, platinum, etc.

    # Stats
    total_spent_cents = Column(Integer, default=0)
    total_events_attended = Column(Integer, default=0)
    first_purchase_date = Column(DateTime(timezone=True), nullable=True)
    last_interaction_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event_goer = relationship("EventGoer", back_populates="preferences")


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(Enum(DiscountType), nullable=False)
    discount_value = Column(Integer, nullable=False)  # percent (1-100) or cents
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    max_uses = Column(Integer, nullable=True)  # null = unlimited
    uses_count = Column(Integer, default=0)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)  # null = all events
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)  # null for listing page
    page = Column(String(50), nullable=False)  # "listing" or "detail"
    ip_hash = Column(String(64), nullable=False)
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    preferred_channel = Column(String(10), default="email")
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.WAITING, index=True)
    position = Column(Integer, nullable=False)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    event = relationship("Event", back_populates="waitlist_entries")


class AutoTrigger(Base):
    __tablename__ = "auto_triggers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # low_sell_through, almost_sold_out, post_event_followup, new_event_alert
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # NULL = all events
    threshold_value = Column(Integer, nullable=True)  # e.g. 30 for 30%
    threshold_days = Column(Integer, nullable=True)  # e.g. 7 for "7 days left"
    action = Column(String(50), nullable=False)  # send_promo, send_campaign, send_survey
    action_config = Column(Text, nullable=True)  # JSON config
    is_active = Column(Boolean, default=True)
    last_fired_at = Column(DateTime(timezone=True), nullable=True)
    fire_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


class AdminMagicLink(Base):
    """Database-persisted magic link tokens for event admin access."""
    __tablename__ = "admin_magic_links"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    survey_token = Column(String(100), unique=True, nullable=False, index=True)
    rating = Column(Integer, nullable=True)  # 1-10
    comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")
    event_goer = relationship("EventGoer")
    ticket = relationship("Ticket")


class ConversationSession(Base):
    """Voice conversation session for multi-turn context."""
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID

    # Current entity focus
    current_customer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=True)
    current_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    # JSON: [{"role": "user/assistant", "content": "...", "tool_calls": [...]}]
    conversation_history = Column(Text, nullable=True)

    # JSON: {"customers": [{id, name, relation}], "events": [...]}
    entity_context = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_activity = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    current_customer = relationship("EventGoer")
    current_event = relationship("Event")


class KnowledgeDocument(Base):
    """Metadata for an uploaded knowledge base document (PDF, text, FAQ paste)."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    source_filename = Column(String(500), nullable=True)
    content_type = Column(String(20), nullable=False)  # pdf, txt, md, paste
    created_at = Column(DateTime(timezone=True), default=utcnow)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")
    venue = relationship("Venue")
    event = relationship("Event")


class KnowledgeChunk(Base):
    """Chunked and embedded content from a knowledge document."""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)  # JSON-serialized float array
    chunk_index = Column(Integer, nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookEndpoint(Base):
    """Registered outbound webhook endpoint."""
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    event_types = Column(Text, nullable=False)  # JSON list
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    deliveries = relationship("WebhookDelivery", back_populates="endpoint", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Log of each webhook delivery attempt."""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    status = Column(Enum(WebhookDeliveryStatus), default=WebhookDeliveryStatus.PENDING)
    attempt = Column(Integer, default=1)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")
