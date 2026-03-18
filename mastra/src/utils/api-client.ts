/**
 * HTTP client for communicating with the AI Tickets FastAPI backend.
 * All agent tools that need event/ticket/customer data go through here.
 */

const API_URL = process.env.AITICKETS_API_URL || "http://localhost:8000";
const API_KEY = process.env.AITICKETS_API_KEY || "";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  timeout?: number;
}

export class AITicketsClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(baseUrl?: string, apiKey?: string) {
    this.baseUrl = baseUrl || API_URL;
    this.apiKey = apiKey || API_KEY;
  }

  private async request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, params, timeout = 30000 } = opts;

    const url = new URL(path, this.baseUrl);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined) url.searchParams.set(key, String(value));
      }
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["X-Admin-Key"] = this.apiKey;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`API ${method} ${path} failed (${response.status}): ${text}`);
      }

      return (await response.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  // ── Events ──
  async getEvents(params?: { limit?: number; status?: string }) {
    return this.request<any[]>("/api/events", { params });
  }

  async getEvent(eventId: number) {
    return this.request<any>(`/api/events/${eventId}`);
  }

  async createEvent(data: any) {
    return this.request<any>("/api/events", { method: "POST", body: data });
  }

  // ── Analytics ──
  async getAnalyticsOverview() {
    return this.request<any>("/api/analytics/overview");
  }

  async getEventAnalytics(eventId: number) {
    return this.request<any>(`/api/analytics/events/${eventId}`);
  }

  // ── Customers ──
  async getEventGoers(params?: { limit?: number }) {
    return this.request<any[]>("/api/event-goers", { params });
  }

  async getEventGoer(id: number) {
    return this.request<any>(`/api/event-goers/${id}`);
  }

  // ── Tickets ──
  async getTickets(params?: { event_id?: number }) {
    return this.request<any[]>("/api/tickets", { params });
  }

  // ── Meta Ads ──
  async createMetaAd(data: any) {
    return this.request<any>("/api/meta-ads/campaigns", { method: "POST", body: data });
  }

  async getMetaAds() {
    return this.request<any[]>("/api/meta-ads/campaigns");
  }

  // ── Notifications ──
  async sendCampaign(data: any) {
    return this.request<any>("/api/notifications/campaigns", { method: "POST", body: data });
  }

  // ── Knowledge Base ──
  async searchKnowledge(query: string) {
    return this.request<any>("/api/knowledge/search", { params: { query } });
  }

  // ── MCP Tool Call (bridges into existing MCP tools) ──
  async callMcpTool(toolName: string, args: Record<string, any>) {
    return this.request<any>(`/tools/${toolName}`, { method: "POST", body: args });
  }
}

export const apiClient = new AITicketsClient();
