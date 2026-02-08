from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models import TicketStatus, NotificationType, NotificationChannel, NotificationStatus, EventStatus, TierStatus


# ============== Venue Schemas ==============

class VenueBase(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    description: Optional[str] = None


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None


class VenueResponse(VenueBase):
    id: int
    logo_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Category Schemas ==============

class EventCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None  # Hex color e.g. #CE1141
    image_url: Optional[str] = None


class EventCategoryCreate(EventCategoryBase):
    pass


class EventCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None


class EventCategoryResponse(EventCategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Event Schemas ==============

class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_date: str  # YYYY-MM-DD
    event_time: str  # HH:MM


class EventCreate(EventBase):
    venue_id: int
    category_ids: list[int] = []
    promoter_phone: Optional[str] = None
    promoter_name: Optional[str] = None
    is_visible: bool = True
    doors_open_time: Optional[str] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    promo_video_url: Optional[str] = None
    category_ids: Optional[list[int]] = None
    promoter_phone: Optional[str] = None
    promoter_name: Optional[str] = None
    is_visible: Optional[bool] = None
    doors_open_time: Optional[str] = None


class EventResponse(EventBase):
    id: int
    venue_id: int
    image_url: Optional[str] = None
    promo_video_url: Optional[str] = None
    status: EventStatus = EventStatus.SCHEDULED
    is_visible: bool = True
    doors_open_time: Optional[str] = None
    series_id: Optional[str] = None
    categories: list[EventCategoryResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class EventWithVenueResponse(EventResponse):
    venue: VenueResponse


# ============== Ticket Tier Schemas ==============

class TicketTierBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: int  # Price in cents
    quantity_available: int


class TicketTierCreate(TicketTierBase):
    pass


class TicketTierUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    quantity_available: Optional[int] = None
    status: Optional[TierStatus] = None


class TicketTierResponse(TicketTierBase):
    id: int
    event_id: int
    quantity_sold: int
    status: TierStatus = TierStatus.ACTIVE
    stripe_product_id: Optional[str] = None
    stripe_price_id: Optional[str] = None

    class Config:
        from_attributes = True


class TicketTierWithAvailability(TicketTierResponse):
    tickets_remaining: int


# ============== Event Goer Schemas ==============

class EventGoerBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None


class EventGoerCreate(EventGoerBase):
    email_opt_in: bool = True
    sms_opt_in: bool = False
    marketing_opt_in: bool = False


class EventGoerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class NotificationPreferencesUpdate(BaseModel):
    email_opt_in: Optional[bool] = None
    sms_opt_in: Optional[bool] = None
    marketing_opt_in: Optional[bool] = None


class EventGoerResponse(EventGoerBase):
    id: int
    email_opt_in: bool = True
    sms_opt_in: bool = False
    marketing_opt_in: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Ticket Schemas ==============

class TicketResponse(BaseModel):
    id: int
    ticket_tier_id: int
    event_goer_id: int
    stripe_payment_intent_id: Optional[str] = None
    qr_code_token: Optional[str] = None
    status: TicketStatus
    purchased_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketWithDetailsResponse(TicketResponse):
    ticket_tier: TicketTierResponse
    event_goer: EventGoerResponse


class TicketFullResponse(BaseModel):
    id: int
    status: TicketStatus
    qr_code_token: Optional[str] = None
    purchased_at: Optional[datetime] = None
    ticket_tier: TicketTierResponse
    event: EventResponse
    venue: VenueResponse
    event_goer: EventGoerResponse

    class Config:
        from_attributes = True


# ============== Purchase Schemas ==============

class PurchaseRequest(BaseModel):
    ticket_tier_id: int
    email: EmailStr
    name: str
    phone: Optional[str] = None
    quantity: int = 1
    promo_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    tickets: Optional[list] = None
    message: Optional[str] = None


# ============== Validation Schemas ==============

class TicketValidationResponse(BaseModel):
    valid: bool
    message: str
    ticket: Optional[TicketFullResponse] = None


# ============== Event with Details ==============

class EventDetailResponse(EventResponse):
    venue: VenueResponse
    ticket_tiers: list[TicketTierWithAvailability]


class VenueWithEventsResponse(VenueResponse):
    events: list[EventResponse]


# ============== Sales Stats ==============

class EventSalesStats(BaseModel):
    event_id: int
    event_name: str
    total_tickets_sold: int
    total_revenue_cents: int
    tickets_by_tier: list[dict]
    tickets_checked_in: int


# ============== Notification Schemas ==============

class NotificationResponse(BaseModel):
    id: int
    event_goer_id: int
    event_id: Optional[int] = None
    ticket_id: Optional[int] = None
    notification_type: NotificationType
    channel: NotificationChannel
    status: NotificationStatus
    subject: Optional[str] = None
    message: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendReminderRequest(BaseModel):
    event_id: int
    hours_before: int = 24
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]


class SendReminderResponse(BaseModel):
    event_id: int
    event_name: str
    total_recipients: int
    email_sent: int
    sms_sent: int
    failed: int


class EventUpdateRequest(BaseModel):
    message: str
    update_type: str = "general"  # date_change, time_change, venue_change, general
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    notify_attendees: bool = True
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]


class EventCancelRequest(BaseModel):
    reason: Optional[str] = None
    notify_attendees: bool = True
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]


class EventUpdateResponse(BaseModel):
    event_id: int
    event_name: str
    update_type: str
    message: str
    notifications_sent: int


# ============== Marketing Campaign Schemas ==============

class MarketingCampaignCreate(BaseModel):
    name: str
    subject: str
    content: str
    target_all: bool = False
    target_event_id: Optional[int] = None
    target_segments: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class MarketingCampaignResponse(BaseModel):
    id: int
    name: str
    subject: str
    content: str
    target_all: bool
    target_event_id: Optional[int] = None
    target_segments: Optional[str] = None
    total_recipients: int
    sent_count: int
    status: str
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMarketingRequest(BaseModel):
    campaign_id: int
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]


class SendMarketingResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    total_recipients: int
    email_sent: int
    sms_sent: int
    failed: int


# ============== Promo Code Schemas ==============

class PromoCodeBase(BaseModel):
    code: str
    discount_type: str  # "percent" or "fixed_cents"
    discount_value: int
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    event_id: Optional[int] = None


class PromoCodeCreate(PromoCodeBase):
    pass


class PromoCodeUpdate(BaseModel):
    is_active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None


class PromoCodeResponse(PromoCodeBase):
    id: int
    uses_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== SMS Ticket Request ==============

class SendSMSTicketRequest(BaseModel):
    ticket_id: int


class SendSMSTicketResponse(BaseModel):
    ticket_id: int
    success: bool
    message: str
