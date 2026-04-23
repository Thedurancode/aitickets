from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, Enum, Boolean, Table, Date, Float
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


class MediaType(str, enum.Enum):
    ARTIST_PHOTO = "artist_photo"      # Artist/performer headshot or photo
    LOGO = "logo"                      # Event/brand/sponsor logo
    VENUE_PHOTO = "venue_photo"        # Venue interior/exterior photo
    SPONSOR_LOGO = "sponsor_logo"      # Sponsor logo
    BACKGROUND = "background"          # Background image/texture
    GRAPHIC = "graphic"                # Generic graphic element
    OTHER = "other"                    # Other media type


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

    # ElevenLabs voice settings for voiceovers
    voice_id = Column(String(100), nullable=True)  # ElevenLabs voice ID
    voice_name = Column(String(100), nullable=True)  # Human-readable voice name
    voice_settings = Column(Text, nullable=True)  # JSON: {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": true}

    created_at = Column(DateTime(timezone=True), default=utcnow)

    events = relationship("Event", back_populates="venue", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True, index=True)  # Link to artist
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    promo_video_url = Column(String(500), nullable=True)  # YouTube or video URL
    post_event_video_url = Column(String(500), nullable=True)  # Post-event recap/highlight video
    event_date = Column(String(20), nullable=False)  # YYYY-MM-DD format
    event_time = Column(String(10), nullable=False)  # HH:MM format
    doors_open_time = Column(String(10), nullable=True)  # HH:MM format
    sale_start_date = Column(String(20), nullable=True)  # YYYY-MM-DD format - when tickets go on sale
    sale_start_time = Column(String(10), nullable=True)  # HH:MM format - when tickets go on sale
    status = Column(Enum(EventStatus), default=EventStatus.SCHEDULED)
    is_visible = Column(Boolean, default=True)
    cancellation_reason = Column(Text, nullable=True)
    promoter_phone = Column(String(50), nullable=True)
    promoter_email = Column(String(255), nullable=True)
    promoter_name = Column(String(255), nullable=True)
    series_id = Column(String(36), nullable=True, index=True)  # UUID linking recurring events
    auto_reminder_hours = Column(Integer, nullable=True, default=24)  # hours before event; NULL = disabled
    auto_reminder_use_sms = Column(Boolean, default=False)
    uploads_open = Column(Boolean, default=True)  # Whether media uploads are accepted
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    venue = relationship("Venue", back_populates="events")
    artist = relationship("Artist", back_populates="events")  # Link to artist data
    artist_research = relationship("ArtistResearch", back_populates="event")  # Research snapshots
    ticket_tiers = relationship("TicketTier", back_populates="event", cascade="all, delete-orphan")
    updates = relationship("EventUpdate", back_populates="event", cascade="all, delete-orphan")
    categories = relationship("EventCategory", secondary=event_category_link, back_populates="events")
    photos = relationship("EventPhoto", back_populates="event", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="event", cascade="all, delete-orphan")
    media = relationship("EventMedia", back_populates="event", cascade="all, delete-orphan")


class EventPhoto(Base):
    __tablename__ = "event_photos"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=False)
    uploaded_by_name = Column(String(255), nullable=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=True, index=True)
    media_type = Column(String(20), default="photo")  # "photo" or "video"
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Content moderation fields
    moderation_status = Column(String(20), default="pending")  # pending, approved, rejected, flagged
    moderation_score = Column(Float, nullable=True)  # NSFW score (0-1)
    moderation_scores_json = Column(Text, nullable=True)  # JSON with detailed scores
    moderated_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="photos")
    event_goer = relationship("EventGoer")


class EventMedia(Base):
    """Media assets for event flyer generation (artists, logos, sponsors, etc.)"""
    __tablename__ = "event_media"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    media_type = Column(Enum(MediaType), nullable=False, index=True)
    media_url = Column(String(500), nullable=False)
    label = Column(String(255), nullable=True)  # e.g., "Artist Name", "Sponsor: Coca-Cola"
    display_order = Column(Integer, default=0)  # Order for display/use in flyer
    media_metadata = Column(Text, nullable=True)  # JSON metadata (dimensions, credits, etc.)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event = relationship("Event", back_populates="media")


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

    # Inventory alert thresholds (comma-separated integers, e.g. "90,95,100")
    alert_thresholds = Column(Text, nullable=True)
    fired_thresholds = Column(Text, nullable=True)

    # Dynamic pricing
    base_price = Column(Integer, nullable=True)  # Original price before dynamic adjustments
    dynamic_pricing_enabled = Column(Boolean, default=False)
    min_price = Column(Integer, nullable=True)  # Minimum allowed price
    max_price = Column(Integer, nullable=True)  # Maximum allowed price
    last_price_update = Column(DateTime(timezone=True), nullable=True)
    price_update_reason = Column(String(255), nullable=True)  # demand, time_based, manual, etc.

    event = relationship("Event", back_populates="ticket_tiers")
    tickets = relationship("Ticket", back_populates="ticket_tier", cascade="all, delete-orphan")


class EventGoer(Base):
    __tablename__ = "event_goers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    birthdate = Column(Date, nullable=True)  # Customer birthdate for birthday marketing

    # Notification preferences
    email_opt_in = Column(Boolean, default=True)  # Transactional emails (tickets, reminders)
    sms_opt_in = Column(Boolean, default=False)   # SMS notifications
    marketing_opt_in = Column(Boolean, default=False)  # Marketing communications
    birthday_opt_in = Column(Boolean, default=False)  # Birthday greetings/marketing (GDPR consent)

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

    # Refund tracking
    refund_reason = Column(String(255), nullable=True)  # customer_request, event_cancelled, duplicate, fraud, other
    refund_amount_cents = Column(Integer, nullable=True)  # For partial refunds
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    stripe_refund_id = Column(String(255), nullable=True, index=True)

    # Backward-compatible alias used by legacy code/tests.
    # Not persisted; canonical source of truth is TicketTier.price.
    price_cents = None

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

    # Geographic info (copied from EventGoer for convenience)
    postal_code = Column(String(20), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True, default="US")

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

    # Cross-platform tracking fields
    platform = Column(String(50), default="internal")  # 'internal', 'eventbrite', 'facebook', 'ticketmaster', etc.
    external_platform_id = Column(String(255), nullable=True)  # External event/listing ID
    platform_api_response = Column(Text, nullable=True)  # JSON string of raw platform data


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


class FlyerStyle(Base):
    """Reusable flyer design styles with optional reference images."""
    __tablename__ = "flyer_styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class StylePickerStatus(str, enum.Enum):
    PENDING = "pending"
    SELECTED = "selected"
    EXPIRED = "expired"


class StylePickerSession(Base):
    """Tracks SMS-based flyer style picker sessions."""
    __tablename__ = "style_picker_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    selected_style_id = Column(Integer, ForeignKey("flyer_styles.id"), nullable=True)
    status = Column(Enum(StylePickerStatus), default=StylePickerStatus.PENDING)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    selected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")
    selected_style = relationship("FlyerStyle")


class AboutSection(Base):
    """Key-value store for About Us page content, editable via voice/MCP."""
    __tablename__ = "about_sections"

    id = Column(Integer, primary_key=True, index=True)
    section_key = Column(String(50), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MetaAdStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    FAILED = "failed"


class MetaAdObjective(str, enum.Enum):
    AWARENESS = "awareness"
    TRAFFIC = "traffic"
    ENGAGEMENT = "engagement"
    LEADS = "leads"
    APP_PROMOTION = "app_promotion"
    MESSAGES = "messages"


class MetaAdCampaign(Base):
    """Meta (Facebook/Instagram) ad campaigns for events."""
    __tablename__ = "meta_ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)

    # Meta API IDs
    meta_campaign_id = Column(String(255), nullable=True, index=True)  # Meta's campaign ID
    meta_ad_set_id = Column(String(255), nullable=True, index=True)  # Meta's ad set ID
    meta_ad_id = Column(String(255), nullable=True, index=True)  # Meta's ad ID
    meta_creative_id = Column(String(255), nullable=True, index=True)  # Meta's creative ID

    # Campaign settings
    name = Column(String(255), nullable=False)
    status = Column(Enum(MetaAdStatus), default=MetaAdStatus.DRAFT, index=True)
    objective = Column(Enum(MetaAdObjective), default=MetaAdObjective.TRAFFIC)

    # Budget
    budget_type = Column(String(20), default="daily")  # daily or lifetime
    budget_cents = Column(Integer, nullable=True)  # Budget in cents

    # Targeting
    targeting_radius_miles = Column(Integer, default=10)  # Geo-targeting radius from venue
    age_min = Column(Integer, nullable=True)
    age_max = Column(Integer, nullable=True)
    genders = Column(String(50), nullable=True)  # male, female, all
    interests = Column(Text, nullable=True)  # JSON array of interest IDs

    # Creative
    primary_text = Column(Text, nullable=True)
    headline = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    call_to_action = Column(String(50), default="GET_TICKETS")  # GET_TICKETS, LEARN_MORE, etc.
    image_url = Column(String(500), nullable=True)

    # Performance tracking
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend_cents = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event = relationship("Event")


class MetaAdInsight(Base):
    """Cached insights from Meta Ads API to reduce API calls."""
    __tablename__ = "meta_ad_insights"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("meta_ad_campaigns.id"), nullable=False, index=True)

    # Metrics
    date = Column(String(20), nullable=False)  # YYYY-MM-DD
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend_cents = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    reach = Column(Integer, default=0)

    # Derived metrics
    ctr_percent = Column(Integer, default=0)  # Click-through rate
    cpc_cents = Column(Integer, default=0)  # Cost per click
    cpa_cents = Column(Integer, default=0)  # Cost per action

    created_at = Column(DateTime(timezone=True), default=utcnow)

    campaign = relationship("MetaAdCampaign")


class MediaShareToken(Base):
    """Token-based links for attendees to upload event photos/videos."""
    __tablename__ = "media_share_tokens"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")
    event_goer = relationship("EventGoer")


class EventImageUpdateToken(Base):
    """Token-based event image update links sent via SMS."""
    __tablename__ = "event_image_update_tokens"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


class VoiceCallCampaign(Base):
    """Voice call campaigns for outbound calling to event goers."""
    __tablename__ = "voice_call_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Campaign goal and script
    goal = Column(String(50), nullable=False)  # event_reminder, ticket_recovery, feedback_survey, birthday_wish, vip_outreach, cart_recovery, custom
    custom_script = Column(Text, nullable=True)  # For custom goal

    # Targeting
    target_all = Column(Boolean, default=False)  # Call all opted-in users
    target_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Call attendees of specific event
    target_segments = Column(Text, nullable=True)  # JSON: {"is_vip": true, "min_events": 3, "has_ticket_pending": true}
    target_customer_ids = Column(Text, nullable=True)  # JSON: [1, 2, 3] - specific customers

    # Event context for script
    event_context_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Event referenced in script

    # Script variables
    discount_percent = Column(Integer, nullable=True)  # For offers

    # Scheduling
    status = Column(String(50), default="draft")  # draft, scheduled, running, paused, completed, cancelled
    scheduled_for = Column(DateTime(timezone=True), nullable=True)  # When to start calling
    start_calling_after = Column(String(5), nullable=True)  # HH:MM format - earliest time to call
    stop_calling_before = Column(String(5), nullable=True)  # HH:MM format - latest time to call
    timezone = Column(String(50), default="America/New_York")  # Timezone for calling hours

    # Call settings
    max_concurrent_calls = Column(Integer, default=1)
    time_between_calls_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=60)
    allow_voicemail = Column(Boolean, default=True)
    record_calls = Column(Boolean, default=False)

    # Compliance
    respect_do_not_call = Column(Boolean, default=True)
    skip_recently_called = Column(Boolean, default=True)  # Skip if called in last X days
    skip_days_since_last_call = Column(Integer, default=7)  # Days to wait between calls

    # Stats
    total_recipients = Column(Integer, default=0)
    calls_initiated = Column(Integer, default=0)
    calls_completed = Column(Integer, default=0)
    calls_answered = Column(Integer, default=0)
    calls_failed = Column(Integer, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event = relationship("Event", foreign_keys=[event_context_id])
    target_event = relationship("Event", foreign_keys=[target_event_id])


class VoiceCall(Base):
    """Individual voice call records."""
    __tablename__ = "voice_calls"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("voice_call_campaigns.id"), nullable=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)

    # Call details
    goal = Column(String(50), nullable=False)
    phone_number = Column(String(50), nullable=False)
    call_script = Column(Text, nullable=False)

    # Telnyx details
    telnyx_call_id = Column(String(255), nullable=True, index=True)
    telnyx_status = Column(String(50), nullable=True)  # Status from Telnyx

    # Our status tracking
    status = Column(String(50), default="pending")  # pending, dialing, in_progress, completed, failed, busy, no_answer, cancelled, scheduled
    outcome = Column(String(50), nullable=True)  # answered, left_voicemail, no_answer, busy, failed, do_not_call, requested_callback

    # Call timing
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    recording_url = Column(Text, nullable=True)
    transcription = Column(Text, nullable=True)  # If speech-to-text enabled
    notes = Column(Text, nullable=True)  # Agent notes from the call
    digits_pressed = Column(String(10), nullable=True)  # If gather was used

    # Outcome metadata
    callback_requested = Column(Boolean, default=False)
    callback_scheduled_for = Column(DateTime(timezone=True), nullable=True)
    do_not_call = Column(Boolean, default=False)  # Mark if customer requested to not be called

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    campaign = relationship("VoiceCallCampaign", backref="calls")
    event_goer = relationship("EventGoer", backref="voice_calls")


class FlyerTemplate(Base):
    """User-uploaded flyer templates for AI-based event flyer generation.

    Templates serve as style references. The AI vision model analyzes
    the template's layout, typography, colors, and visual elements,
    then generates a new flyer with event content matching that style.
    """
    __tablename__ = "flyer_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=False)  # Full-size template image
    thumbnail_url = Column(String(500), nullable=True)  # Smaller preview
    prompt_instructions = Column(Text, nullable=True)  # Additional AI instructions
    created_by = Column(String(255), nullable=True)  # User/organization who uploaded

    # Usage tracking
    times_used = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FlyerTemplateMagicToken(Base):
    """Token-based flyer template selection links sent via SMS."""
    __tablename__ = "flyer_template_magic_tokens"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


class ConversionTracking(Base):
    """
    Tracks every ticket conversion for ML training and attribution analysis.

    Stores rich metadata about each purchase to enable:
    - Channel attribution (which marketing channels drive sales)
    - Time-based conversion analysis (best send times)
    - Audience insights (who converts best)
    - A/B test result tracking
    """
    __tablename__ = "conversion_tracking"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True, unique=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey("ticket_tiers.id"), nullable=False, index=True)

    # Attribution data
    utm_source = Column(String(100), nullable=True, index=True)
    utm_medium = Column(String(100), nullable=True, index=True)
    utm_campaign = Column(String(100), nullable=True, index=True)
    utm_content = Column(String(100), nullable=True)
    utm_term = Column(String(100), nullable=True)

    # Referrer info
    referrer_url = Column(String(500), nullable=True)
    landing_page = Column(String(500), nullable=True)

    # Session data
    session_id = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    browser = Column(String(100), nullable=True)

    # Purchase data
    price_paid_cents = Column(Integer, nullable=False)
    discount_amount_cents = Column(Integer, nullable=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=True)

    # Timing data
    purchased_at = Column(DateTime(timezone=True), nullable=False, index=True)
    days_before_event = Column(Integer, nullable=True)  # How far in advance they bought
    hour_of_day = Column(Integer, nullable=True, index=True)  # 0-23 for time-based analysis
    day_of_week = Column(Integer, nullable=True, index=True)  # 0-6 (Monday-Sunday)

    # Event metadata (denormalized for fast querying)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("event_categories.id"), nullable=True, index=True)

    # A/B test tracking
    ab_test_variant = Column(String(100), nullable=True, index=True)  # Which variant they saw

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    ticket = relationship("Ticket")
    event = relationship("Event")
    event_goer = relationship("EventGoer")
    tier = relationship("TicketTier")


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """
    Stores alerts generated by the autonomous intelligence system.

    Provides in-app notification history and audit trail of all alerts sent.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM, index=True)

    # Optional event reference
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)

    # Additional context (stored as JSON)
    alert_metadata = Column(Text, nullable=True)  # JSON string

    # Read status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery tracking
    channels_sent = Column(Text, nullable=True)  # Comma-separated list of channels

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    event = relationship("Event")


class CampaignType(str, enum.Enum):
    """Campaign type enum."""
    EMAIL = "email"
    SMS = "sms"
    NOTIFICATION = "notification"


class Campaign(Base):
    """
    Marketing campaign tracking.

    Tracks email/SMS campaigns sent to customers for performance analysis.
    """
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    campaign_type = Column(Enum(CampaignType), nullable=False, index=True)
    subject = Column(String(255), nullable=True)  # Email subject or SMS preview

    # Event reference (if campaign is for a specific event)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)

    # Tracking stats
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)  # Email opens
    clicked_count = Column(Integer, default=0)  # Link clicks
    converted_count = Column(Integer, default=0)  # Purchases after clicking

    # Revenue tracking
    revenue_cents = Column(Integer, default=0)  # Total revenue from this campaign

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    event = relationship("Event")
    deliveries = relationship("CampaignDelivery", back_populates="campaign")


class CampaignDelivery(Base):
    """
    Individual campaign delivery tracking.

    Tracks each email/SMS sent as part of a campaign for detailed analytics.
    """
    __tablename__ = "campaign_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)

    # Recipient
    recipient_email = Column(String(255), nullable=True, index=True)
    recipient_phone = Column(String(50), nullable=True, index=True)
    event_goer_id = Column(Integer, ForeignKey("event_goers.id"), nullable=True, index=True)

    # Delivery tracking
    sent_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Engagement tracking
    opened_at = Column(DateTime(timezone=True), nullable=True, index=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # Revenue attribution (if purchase made after click)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    revenue_cents = Column(Integer, default=0)

    # Tracking tokens
    tracking_token = Column(String(64), unique=True, index=True, nullable=True)  # For pixel/link tracking

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="deliveries")
    event_goer = relationship("EventGoer")
    ticket = relationship("Ticket")


# ============================================================================
# AD CAMPAIGN & CREATIVE MODELS
# Auto-generated ad campaigns (Meta, Google, Email, Social Media)
# ============================================================================

class AdCampaign(Base):
    """
    Auto-generated advertising campaign for events
    Supports Meta Ads, Google Ads, Email, and Social Media
    """
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    # Campaign details
    platform = Column(String(50), nullable=False)  # "meta", "google", "email", "social_organic"
    campaign_type = Column(String(50), nullable=False)  # "awareness", "conversion", "retargeting"
    name = Column(String(255), nullable=False)
    objective = Column(String(50))  # "REACH", "CONVERSIONS", "VIDEO_VIEWS"

    # Status
    status = Column(String(20), default="draft")  # "draft", "approved", "scheduled", "active", "paused", "completed"

    # Budget (in cents)
    budget_total = Column(Integer, default=0)
    budget_daily = Column(Integer, default=0)
    spend_total = Column(Integer, default=0)

    # Schedule
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Platform-specific
    platform_campaign_id = Column(String(255), nullable=True)  # ID from Meta/Google API
    settings = Column(Text, nullable=True)  # JSON settings

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    event = relationship("Event")
    ad_creatives = relationship("AdCreative", back_populates="ad_campaign", cascade="all, delete-orphan")
    performance = relationship("AdCampaignPerformance", back_populates="ad_campaign", cascade="all, delete-orphan")


class AdCreative(Base):
    """
    Individual ad creative (image ad, video ad, email, social post)
    """
    __tablename__ = "ad_creatives"

    id = Column(Integer, primary_key=True, index=True)
    ad_campaign_id = Column(Integer, ForeignKey("ad_campaigns.id"), nullable=False)

    # Ad details
    platform = Column(String(50), nullable=False)  # "facebook", "instagram", "google_search"
    format = Column(String(50), nullable=False)  # "image", "video", "carousel", "story"
    name = Column(String(255), nullable=True)

    # Creative content
    headline = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    cta = Column(String(100), nullable=True)  # "Buy Tickets", "Learn More"

    # Media
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    link_url = Column(String(500), nullable=True)

    # Targeting (JSON)
    target_audience = Column(Text, nullable=True)  # JSON: age, location, interests
    placements = Column(Text, nullable=True)  # JSON: ["facebook_feed", "instagram_stories"]

    # Status
    status = Column(String(20), default="draft")  # "draft", "approved", "active", "paused"

    # A/B Testing
    is_test_variant = Column(Boolean, default=False)
    test_group = Column(String(50), nullable=True)  # "A", "B", "C"

    # Platform-specific
    platform_ad_id = Column(String(255), nullable=True)

    # Budget allocation
    budget_allocation = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    ad_campaign = relationship("AdCampaign", back_populates="ad_creatives")
    performance = relationship("AdPerformance", back_populates="ad_creative", cascade="all, delete-orphan")


class Artist(Base):
    """
    Artist/Performer information discovered through research.
    Stores all data from Spotify, YouTube, Wikipedia, social media.
    """
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)

    # Spotify Data
    spotify_id = Column(String(100), nullable=True, index=True)
    spotify_followers = Column(Integer, nullable=True)
    spotify_monthly_listeners = Column(Integer, nullable=True)
    spotify_popularity = Column(Integer, nullable=True)  # 0-100 score
    spotify_top_tracks = Column(Text, nullable=True)  # JSON list of track names/IDs
    spotify_genres = Column(Text, nullable=True)  # JSON list of genres
    spotify_image_url = Column(String(500), nullable=True)

    # YouTube Data
    youtube_channel_id = Column(String(100), nullable=True, index=True)
    youtube_channel_name = Column(String(255), nullable=True)
    youtube_subscribers = Column(Integer, nullable=True)
    youtube_view_count = Column(BigInteger, nullable=True)
    youtube_video_count = Column(Integer, nullable=True)
    youtube_latest_videos = Column(Text, nullable=True)  # JSON list of recent videos

    # Social Media
    instagram_handle = Column(String(100), nullable=True, index=True)
    instagram_followers = Column(Integer, nullable=True)
    twitter_handle = Column(String(100), nullable=True)
    twitter_followers = Column(Integer, nullable=True)
    tiktok_handle = Column(String(100), nullable=True)
    tiktok_followers = Column(Integer, nullable=True)
    facebook_page = Column(String(255), nullable=True)
    facebook_likes = Column(Integer, nullable=True)

    # Artist Information
    genre = Column(String(100), nullable=True)
    sub_genres = Column(Text, nullable=True)  # JSON: ["Latin Trap", "Reggaeton"]
    bio = Column(Text, nullable=True)  # Wikipedia/bio summary
    achievements = Column(Text, nullable=True)  # JSON: awards, milestones
    similar_artists = Column(Text, nullable=True)  # JSON: list of similar artist names
    country_of_origin = Column(String(100), nullable=True)
    active_since_year = Column(Integer, nullable=True)

    # Fan Demographics (from research)
    fan_demographics = Column(Text, nullable=True)  # JSON: age ranges, gender split
    primary_markets = Column(Text, nullable=True)  # JSON: top cities/countries
    fan_interests = Column(Text, nullable=True)  # JSON: common interests

    # Performance Metrics
    average_ticket_price = Column(Integer, nullable=True)  # Historical average in cents
    typical_venue_size = Column(String(50), nullable=True)  # small/medium/large/stadium
    sellout_velocity = Column(String(50), nullable=True)  # fast/moderate/slow

    # Reference Images (multiple images for flyer generation)
    reference_images = Column(Text, nullable=True)  # JSON: [{"url": "...", "label": "headshot"}, ...]
    primary_image_url = Column(String(500), nullable=True)  # Main image (user-selected or best quality)

    # Research Metadata
    last_researched_at = Column(DateTime(timezone=True), nullable=True)
    research_version = Column(Integer, default=1)
    data_source = Column(String(100), nullable=True)  # spotify_api, web_search, manual
    confidence_score = Column(Float, nullable=True)  # 0.0-1.0 data quality score

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    events = relationship("Event", back_populates="artist")
    research_history = relationship("ArtistResearch", back_populates="artist", cascade="all, delete-orphan")


class ArtistResearch(Base):
    """
    Historical snapshots of artist research.
    Tracks how artist data changes over time.
    """
    __tablename__ = "artist_research"

    id = Column(Integer, primary_key=True, index=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)

    # Complete research snapshot
    research_data = Column(Text, nullable=False)  # Full JSON of all discovered data

    # What triggered this research
    trigger = Column(String(50), nullable=True)  # event_creation, manual_refresh, scheduled

    # Key metrics at time of research (for tracking growth)
    spotify_listeners_snapshot = Column(Integer, nullable=True)
    instagram_followers_snapshot = Column(Integer, nullable=True)
    youtube_subscribers_snapshot = Column(Integer, nullable=True)

    # Research quality
    sources_checked = Column(Text, nullable=True)  # JSON: ["spotify", "youtube", "wikipedia"]
    data_completeness = Column(Float, nullable=True)  # 0.0-1.0 how complete

    # Timestamps
    researched_at = Column(DateTime(timezone=True), default=utcnow)
    research_duration_ms = Column(Integer, nullable=True)  # How long research took

    # Relationships
    artist = relationship("Artist", back_populates="research_history")
    event = relationship("Event", back_populates="artist_research")


class AdCampaignPerformance(Base):
    """
    Campaign-level performance metrics (daily rollup)
    """
    __tablename__ = "ad_campaign_performance"

    id = Column(Integer, primary_key=True, index=True)
    ad_campaign_id = Column(Integer, ForeignKey("ad_campaigns.id"), nullable=False)
    date = Column(Date, nullable=False)

    # Metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    # Financial (in cents)
    spend = Column(Integer, default=0)
    revenue = Column(Integer, default=0)

    # Calculated
    ctr = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    cpa = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    ad_campaign = relationship("AdCampaign", back_populates="performance")


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
    conversions = Column(Integer, default=0)

    # Engagement
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    saves = Column(Integer, default=0)

    # Video
    video_views = Column(Integer, default=0)
    video_view_duration_avg = Column(Float, default=0.0)

    # Financial (in cents)
    spend = Column(Integer, default=0)
    revenue = Column(Integer, default=0)

    # Calculated
    ctr = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    cpa = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    ad_creative = relationship("AdCreative", back_populates="performance")

# ============== EXPERT INTELLIGENCE MODELS ==============

class WeatherForecast(Base):
    """Weather forecasts for events with change tracking."""
    __tablename__ = "weather_forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    
    # Weather data
    temperature_high = Column(Float)
    temperature_low = Column(Float)
    precipitation_probability = Column(Float)  # 0.0 to 1.0
    precipitation_amount = Column(Float)  # inches
    conditions = Column(String(100))  # "Clear", "Rain", "Thunderstorms"
    wind_speed = Column(Float)  # mph
    humidity = Column(Float)  # 0.0 to 1.0
    
    # Raw API response
    api_response = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    
    event = relationship("Event")


class WeatherAlert(Base):
    """Weather change alerts for events."""
    __tablename__ = "weather_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # "precipitation", "temperature", "severe"
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    
    old_value = Column(Float)
    new_value = Column(Float)
    message = Column(Text, nullable=False)
    notified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    
    event = relationship("Event")


class SalesPrediction(Base):
    """AI-powered sales predictions for events."""
    __tablename__ = "sales_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    prediction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Predictions
    predicted_tickets_sold = Column(Integer)
    predicted_revenue = Column(Integer)  # cents
    confidence_score = Column(Float)  # 0.0 to 1.0
    sellout_probability = Column(Float)  # 0.0 to 1.0
    days_to_sellout = Column(Float)
    
    # Model metadata
    model_version = Column(String(50))
    feature_importance = Column(Text)  # JSON
    
    created_at = Column(DateTime(timezone=True), default=utcnow)
    
    event = relationship("Event")


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    COMPLETED = "completed"


class RecommendationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIRecommendation(Base):
    """AI-generated proactive recommendations."""
    __tablename__ = "ai_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    
    recommendation_type = Column(String(50), nullable=False)  # "budget", "pricing", "marketing", "weather"
    priority = Column(Enum(RecommendationPriority), nullable=False, index=True)
    
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    reasoning = Column(Text)  # Why the recommendation was made
    expected_impact = Column(Text)  # Predicted outcome
    action_items = Column(Text)  # JSON list of steps
    
    status = Column(Enum(RecommendationStatus), default=RecommendationStatus.PENDING, index=True)
    implemented_at = Column(DateTime(timezone=True))
    result_data = Column(Text)  # JSON of actual results
    
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    
    event = relationship("Event")


class BudgetOptimizationLog(Base):
    """Log of automated budget optimizations."""
    __tablename__ = "budget_optimization_log"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)

    optimization_type = Column(String(50), nullable=False)  # "shift", "pause", "increase", "decrease"
    from_channel = Column(String(50))  # "meta_ads", "google_ads", "email"
    to_channel = Column(String(50))
    amount_moved = Column(Integer)  # cents

    reason = Column(Text)
    expected_improvement = Column(Text)
    actual_improvement = Column(Text)  # Measured after implementation

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    event = relationship("Event")


class SocialMediaPost(Base):
    """Tracks social media posts for events to enable updates."""
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)

    platform = Column(String(50), nullable=False, index=True)  # "twitter", "facebook", "instagram", "linkedin"
    platform_post_id = Column(String(255), nullable=False)  # Platform's post ID
    post_url = Column(String(500), nullable=True)  # Direct link to post

    # Content snapshot
    content = Column(Text)
    image_url = Column(String(500), nullable=True)

    # Status
    is_published = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Metadata
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    last_updated_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    event = relationship("Event")


# Partnership and Sponsorship Models
class Sponsor(Base):
    """
    Potential sponsors and brands for partnership matching
    """
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    industry = Column(String)
    category = Column(String)
    target_demographics = Column(Text)  # JSON
    brand_values = Column(Text)  # JSON
    marketing_budget_range = Column(String)
    past_sponsorships = Column(Text)  # JSON
    avg_roi = Column(Float)
    preferred_event_types = Column(Text)  # JSON
    contact_info = Column(Text)  # JSON
    preferred_audience_size = Column(String)
    geographic_markets = Column(Text)  # JSON
    excluded_genres = Column(Text)  # JSON
    required_metrics = Column(Text)  # JSON
    is_active = Column(Boolean, default=True)
    last_contacted = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class PartnershipMatch(Base):
    """
    AI-generated partnership matches between events and sponsors
    """
    __tablename__ = "partnership_matches"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id"), nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    match_score = Column(Float)
    audience_overlap_score = Column(Float)
    brand_alignment_score = Column(Float)
    geographic_score = Column(Float)
    budget_fit_score = Column(Float)
    match_reasons = Column(Text)  # JSON
    potential_concerns = Column(Text)  # JSON
    pitch_summary = Column(Text)
    key_selling_points = Column(Text)  # JSON
    projected_roi = Column(Float)
    recommended_package = Column(Text)  # JSON
    pitch_deck_url = Column(String)
    pitch_deck_data = Column(Text)  # JSON
    status = Column(String, default="generated")
    sent_at = Column(DateTime(timezone=True))
    response_received_at = Column(DateTime(timezone=True))
    deal_value = Column(Float)
    sponsor_feedback = Column(Text)
    internal_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class EventPartnership(Base):
    """
    Actual confirmed partnerships/sponsorships for events
    """
    __tablename__ = "event_partnerships"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sponsor_id = Column(Integer, ForeignKey("sponsors.id"), nullable=False)
    partnership_match_id = Column(Integer, ForeignKey("partnership_matches.id"))
    partnership_type = Column(String)
    deal_value = Column(Float)
    payment_terms = Column(String)
    sponsor_benefits = Column(Text)  # JSON
    event_obligations = Column(Text)  # JSON
    impressions_delivered = Column(Integer)
    engagement_metrics = Column(Text)  # JSON
    roi_achieved = Column(Float)
    contract_signed_date = Column(DateTime(timezone=True))
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    is_renewed = Column(Boolean, default=False)
    sponsor_satisfaction_score = Column(Float)
    post_event_feedback = Column(Text)
    case_study_url = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


# Post-Event Intelligence Models
class PostEventAnalysis(Base):
    """
    Comprehensive post-event analysis and learnings
    """
    __tablename__ = "post_event_analyses"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    tickets_sold = Column(Integer)
    actual_attendance = Column(Integer)
    no_show_rate = Column(Float)
    capacity_percentage = Column(Float)
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
    marketing_metrics = Column(Text)  # JSON
    best_performing_channel = Column(String)
    worst_performing_channel = Column(String)
    viral_moments = Column(Text)  # JSON
    actual_demographics = Column(Text)  # JSON
    demographic_surprises = Column(Text)  # JSON
    audience_sentiment_score = Column(Float)
    net_promoter_score = Column(Float)
    setup_issues = Column(Text)  # JSON
    technical_issues = Column(Text)  # JSON
    security_incidents = Column(Text)  # JSON
    vendor_performance = Column(Text)  # JSON
    peak_attendance_time = Column(DateTime(timezone=True))
    peak_concession_time = Column(DateTime(timezone=True))
    peak_social_mentions = Column(DateTime(timezone=True))
    most_engaged_song = Column(String)
    weather_conditions = Column(Text)  # JSON
    competing_events = Column(Text)  # JSON
    external_factors = Column(Text)  # JSON
    total_social_mentions = Column(Integer)
    social_reach = Column(Integer)
    user_generated_content = Column(Integer)
    influencer_attendance = Column(Text)  # JSON
    predicted_sellout_date = Column(DateTime(timezone=True))
    actual_sellout_date = Column(DateTime(timezone=True))
    predicted_demographics = Column(Text)  # JSON
    prediction_accuracy_score = Column(Float)
    success_factors = Column(Text)  # JSON
    improvement_areas = Column(Text)  # JSON
    surprising_insights = Column(Text)  # JSON
    pricing_recommendations = Column(Text)  # JSON
    marketing_recommendations = Column(Text)  # JSON
    operational_recommendations = Column(Text)  # JSON
    future_artist_recommendations = Column(Text)  # JSON
    data_completeness_score = Column(Float)
    insight_quality_score = Column(Float)
    actionability_score = Column(Float)
    full_report_url = Column(String)
    executive_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    analyzed_at = Column(DateTime(timezone=True), default=utcnow)


class EventFeedback(Base):
    """
    Individual feedback entries from various sources
    """
    __tablename__ = "event_feedback"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("post_event_analyses.id"))
    source = Column(String)
    source_platform = Column(String)
    rating = Column(Float)
    sentiment = Column(String)
    feedback_text = Column(Text)
    category = Column(String)
    is_complaint = Column(Boolean, default=False)
    requires_response = Column(Boolean, default=False)
    user_demographic = Column(Text)  # JSON
    is_verified_attendee = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    ai_summary = Column(Text)
    action_taken = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class EventLearning(Base):
    """
    Specific learnings extracted from events
    """
    __tablename__ = "event_learnings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("post_event_analyses.id"))
    category = Column(String)
    learning_type = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    impact_level = Column(String)
    financial_impact = Column(Float)
    applicable_to = Column(Text)  # JSON
    supporting_data = Column(Text)  # JSON
    confidence_score = Column(Float)
    recommended_action = Column(Text)
    implementation_complexity = Column(String)
    has_been_applied = Column(Boolean, default=False)
    applied_to_events = Column(Text)  # JSON
    validated = Column(Boolean, default=False)
    validation_results = Column(Text)  # JSON
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class IntelligencePattern(Base):
    """
    Patterns discovered across multiple events
    """
    __tablename__ = "intelligence_patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_name = Column(String, nullable=False, unique=True)
    pattern_type = Column(String)
    description = Column(Text)
    conditions = Column(Text)  # JSON
    expected_outcome = Column(Text)  # JSON
    confidence_level = Column(Float)
    supporting_events = Column(Text)  # JSON
    occurrence_count = Column(Integer)
    first_observed = Column(DateTime(timezone=True))
    last_observed = Column(DateTime(timezone=True))
    prediction_accuracy = Column(Float)
    false_positive_rate = Column(Float)
    false_negative_rate = Column(Float)
    recommended_strategy = Column(Text)
    expected_improvement = Column(Text)  # JSON
    risk_factors = Column(Text)  # JSON
    is_active = Column(Boolean, default=True)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)
