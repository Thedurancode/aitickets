// Event Types
export type EventStatus = "SCHEDULED" | "PUBLISHED" | "CANCELLED";
export type TicketTierStatus = "ACTIVE" | "SOLD_OUT";
export type TicketStatus = "PENDING" | "PAID" | "CHECKED_IN" | "CANCELLED" | "REFUNDED";
export type DiscountType = "PERCENT" | "FIXED_CENTS";

export interface Venue {
  id: number;
  name: string;
  address: string;
  phone: string | null;
  description: string | null;
  logo_url: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  color: string | null;
  image_url: string | null;
  created_at: string;
}

export interface TicketTier {
  id: number;
  event_id: number;
  name: string;
  description: string | null;
  price: number; // cents
  quantity_available: number;
  quantity_sold: number;
  tickets_remaining: number;
  status: TicketTierStatus;
  stripe_product_id: string | null;
  stripe_price_id: string | null;
}

export interface Event {
  id: number;
  name: string;
  description: string | null;
  event_date: string;
  event_time: string;
  image_url: string | null;
  promo_video_url: string | null;
  status: EventStatus;
  is_visible: boolean;
  doors_open_time: string | null;
  created_at: string;
}

export interface EventWithVenue extends Event {
  venue: Venue;
  categories: Category[];
}

export interface EventDetail extends Event {
  venue: Venue;
  ticket_tiers: TicketTier[];
  categories: Category[];
}

// EventGoer Types
export interface EventGoer {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  email_opt_in: boolean;
  sms_opt_in: boolean;
  marketing_opt_in: boolean;
  created_at: string;
}

// Ticket Types
export interface Ticket {
  id: number;
  status: TicketStatus;
  qr_code_token: string | null;
  purchased_at: string | null;
  ticket_tier: TicketTier;
  event: Event & { categories: Category[] };
  venue: Venue;
  event_goer: EventGoer;
}

// Purchase Types
export interface PurchaseRequest {
  ticket_tier_id: number;
  email: string;
  name: string;
  phone?: string;
  quantity?: number;
  promo_code?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}

export interface CheckoutSessionResponse {
  checkout_url?: string;
  session_id?: string;
  message?: string;
  tickets?: Array<{ id: number; qr_token: string }>;
}

// Promo Code Types
export interface PromoCode {
  id: number;
  code: string;
  discount_type: DiscountType;
  discount_value: number;
  is_active: boolean;
  valid_from: string | null;
  valid_until: string | null;
  max_uses: number | null;
  uses_count: number;
  event_id: number | null;
  created_at: string;
}

export interface PromoValidationResponse {
  valid: boolean;
  code: string | null;
  discount_type: DiscountType | null;
  discount_value: number | null;
  original_price_cents: number;
  discount_amount_cents: number;
  discounted_price_cents: number;
  message: string;
}

// Admin Dashboard Types
export interface AdminTierStats {
  id: number;
  name: string;
  price: number;
  quantity_available: number;
  quantity_sold: number;
  revenue_cents: number;
  status: string;
}

export interface AdminActivity {
  type: "purchase" | "check_in";
  name: string;
  tier: string;
  time: string | null;
}

export interface AdminDashboardData {
  event: {
    id: number;
    name: string;
    description: string | null;
    event_date: string;
    event_time: string;
    image_url: string | null;
    promo_video_url: string | null;
    post_event_video_url: string | null;
    doors_open_time: string | null;
    status: string;
    is_visible: boolean;
    venue: { id: number; name: string; address: string } | null;
    categories: { id: number; name: string }[];
  };
  tiers: AdminTierStats[];
  total_revenue_cents: number;
  total_tickets_sold: number;
  analytics: {
    total_views: number;
    unique_visitors: number;
    top_referrers: { referrer: string; count: number }[];
  };
  recent_activity: AdminActivity[];
}

// List/Pagination Types
export interface EventListParams {
  category?: string;
  limit?: number;
  offset?: number;
}
