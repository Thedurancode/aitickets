import type {
  EventWithVenue,
  EventDetail,
  TicketTier,
  EventListParams,
  PurchaseRequest,
  CheckoutSessionResponse,
  PromoValidationResponse,
  Ticket,
  Category,
  AdminDashboardData,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }));
    throw new ApiError(response.status, error.detail || error.message || "An error occurred");
  }
  return response.json();
}

export const api = {
  events: {
    list: async (params?: EventListParams): Promise<EventWithVenue[]> => {
      const searchParams = new URLSearchParams();
      if (params?.category) searchParams.set("category", params.category);
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.offset) searchParams.set("offset", params.offset.toString());

      const queryString = searchParams.toString();
      const url = `${API_BASE}/api/events${queryString ? `?${queryString}` : ""}`;
      const response = await fetch(url);
      return handleResponse<EventWithVenue[]>(response);
    },

    get: async (id: number): Promise<EventDetail> => {
      const response = await fetch(`${API_BASE}/api/events/${id}`);
      return handleResponse<EventDetail>(response);
    },

    getTiers: async (eventId: number): Promise<TicketTier[]> => {
      const response = await fetch(`${API_BASE}/api/events/${eventId}/tiers`);
      return handleResponse<TicketTier[]>(response);
    },
  },

  categories: {
    list: async (): Promise<Category[]> => {
      const response = await fetch(`${API_BASE}/api/categories`);
      return handleResponse<Category[]>(response);
    },
  },

  tickets: {
    purchase: async (eventId: number, data: PurchaseRequest): Promise<CheckoutSessionResponse> => {
      const response = await fetch(`${API_BASE}/api/tickets/events/${eventId}/purchase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      return handleResponse<CheckoutSessionResponse>(response);
    },

    get: async (ticketId: number): Promise<Ticket> => {
      const response = await fetch(`${API_BASE}/api/tickets/${ticketId}`);
      return handleResponse<Ticket>(response);
    },

    getQrUrl: (ticketId: number): string => {
      return `${API_BASE}/api/tickets/${ticketId}/qr`;
    },

    getPdfUrl: (ticketId: number): string => {
      return `${API_BASE}/api/tickets/${ticketId}/pdf`;
    },

    getWalletUrl: (ticketId: number): string => {
      return `${API_BASE}/api/tickets/${ticketId}/wallet`;
    },

    byEmail: async (email: string): Promise<Ticket[]> => {
      const response = await fetch(
        `${API_BASE}/api/tickets/by-email?email=${encodeURIComponent(email)}`
      );
      return handleResponse<Ticket[]>(response);
    },
  },

  promo: {
    validate: async (code: string, ticketTierId: number): Promise<PromoValidationResponse> => {
      const response = await fetch(
        `${API_BASE}/api/promo-codes/validate?code=${encodeURIComponent(code)}&ticket_tier_id=${ticketTierId}`,
        { method: "POST" }
      );
      return handleResponse<PromoValidationResponse>(response);
    },
  },

  analytics: {
    trackPageView: async (data: {
      event_id?: number;
      page: string;
      referrer?: string;
      utm_source?: string;
      utm_medium?: string;
      utm_campaign?: string;
    }): Promise<void> => {
      await fetch(`${API_BASE}/api/analytics/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
    },
  },

  admin: {
    getData: async (eventId: number, token: string): Promise<AdminDashboardData> => {
      const response = await fetch(
        `${API_BASE}/events/${eventId}/admin/data?token=${encodeURIComponent(token)}`
      );
      return handleResponse<AdminDashboardData>(response);
    },

    updateEvent: async (
      eventId: number,
      token: string,
      data: Record<string, unknown>
    ): Promise<void> => {
      const response = await fetch(`${API_BASE}/events/${eventId}/admin`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, token }),
      });
      return handleResponse<void>(response);
    },

    uploadImage: async (eventId: number, token: string, file: File): Promise<{ image_url: string }> => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(
        `${API_BASE}/events/${eventId}/admin/image?token=${encodeURIComponent(token)}`,
        { method: "POST", body: formData }
      );
      return handleResponse<{ image_url: string }>(response);
    },
  },
};

export { ApiError };
