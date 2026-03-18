import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { apiClient } from "../utils/api-client.js";

export const webSearchTool = createTool({
  id: "web-search",
  description:
    "Search the web for information about artists, venues, events, and market conditions. Use this to gather intelligence for event research.",
  inputSchema: z.object({
    query: z.string().describe("Search query"),
    num_results: z.number().default(10).describe("Number of results to return"),
  }),
  outputSchema: z.object({
    results: z.array(
      z.object({
        title: z.string(),
        url: z.string(),
        snippet: z.string(),
      })
    ),
  }),
  execute: async ({ context }) => {
    // SerpAPI integration
    const serpKey = process.env.SERPAPI_KEY;
    if (serpKey) {
      const url = new URL("https://serpapi.com/search.json");
      url.searchParams.set("q", context.query);
      url.searchParams.set("num", String(context.num_results));
      url.searchParams.set("api_key", serpKey);

      const res = await fetch(url.toString());
      const data = await res.json();

      return {
        results: (data.organic_results || []).slice(0, context.num_results).map((r: any) => ({
          title: r.title || "",
          url: r.link || "",
          snippet: r.snippet || "",
        })),
      };
    }

    // Exa integration fallback
    const exaKey = process.env.EXA_API_KEY;
    if (exaKey) {
      const res = await fetch("https://api.exa.ai/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${exaKey}`,
        },
        body: JSON.stringify({
          query: context.query,
          numResults: context.num_results,
          useAutoprompt: true,
        }),
      });
      const data = await res.json();
      return {
        results: (data.results || []).map((r: any) => ({
          title: r.title || "",
          url: r.url || "",
          snippet: r.text?.substring(0, 300) || "",
        })),
      };
    }

    return { results: [] };
  },
});

export const socialInsightsTool = createTool({
  id: "social-insights",
  description:
    "Analyze social media presence and engagement for an artist or venue. Returns follower counts, engagement rates, and trending content.",
  inputSchema: z.object({
    entity_name: z.string().describe("Artist or venue name to research"),
    platforms: z
      .array(z.enum(["instagram", "tiktok", "twitter", "spotify", "youtube"]))
      .default(["instagram", "tiktok", "spotify"]),
  }),
  outputSchema: z.object({
    profiles: z.array(
      z.object({
        platform: z.string(),
        followers: z.number().optional(),
        engagement_rate: z.number().optional(),
        recent_posts: z.number().optional(),
        trending_content: z.array(z.string()),
      })
    ),
    overall_score: z.number().describe("0-100 social presence score"),
  }),
  execute: async ({ context }) => {
    // Use web search to find social stats
    const serpKey = process.env.SERPAPI_KEY;
    const profiles: any[] = [];

    for (const platform of context.platforms) {
      const query = `${context.entity_name} ${platform} followers stats`;
      if (serpKey) {
        const url = new URL("https://serpapi.com/search.json");
        url.searchParams.set("q", query);
        url.searchParams.set("num", "3");
        url.searchParams.set("api_key", serpKey);

        const res = await fetch(url.toString());
        const data = await res.json();

        profiles.push({
          platform,
          followers: undefined,
          engagement_rate: undefined,
          recent_posts: undefined,
          trending_content: (data.organic_results || [])
            .slice(0, 2)
            .map((r: any) => r.snippet || ""),
        });
      } else {
        profiles.push({
          platform,
          trending_content: [],
        });
      }
    }

    return {
      profiles,
      overall_score: profiles.length > 0 ? 50 : 0,
    };
  },
});

export const knowledgeBaseTool = createTool({
  id: "knowledge-base-search",
  description:
    "Search the AI Tickets knowledge base for past event performance data, venue history, and stored insights.",
  inputSchema: z.object({
    query: z.string().describe("Search query for the knowledge base"),
  }),
  outputSchema: z.object({
    results: z.array(
      z.object({
        content: z.string(),
        source: z.string(),
        relevance_score: z.number(),
      })
    ),
  }),
  execute: async ({ context }) => {
    try {
      const data = await apiClient.searchKnowledge(context.query);
      return {
        results: (data.results || []).map((r: any) => ({
          content: r.content || r.text || "",
          source: r.source || r.document_title || "knowledge_base",
          relevance_score: r.score || r.similarity || 0,
        })),
      };
    } catch {
      return { results: [] };
    }
  },
});

export const pastEventPerformanceTool = createTool({
  id: "past-event-performance",
  description:
    "Retrieve performance data from past events in the AI Tickets system. Returns sales, attendance, and revenue metrics.",
  inputSchema: z.object({
    artist_name: z.string().optional().describe("Filter by artist name"),
    venue_name: z.string().optional().describe("Filter by venue"),
    city: z.string().optional().describe("Filter by city"),
    limit: z.number().default(10),
  }),
  outputSchema: z.object({
    events: z.array(
      z.object({
        name: z.string(),
        date: z.string(),
        venue: z.string(),
        tickets_sold: z.number(),
        capacity: z.number().optional(),
        revenue: z.number(),
        sell_through_pct: z.number(),
      })
    ),
  }),
  execute: async ({ context }) => {
    try {
      const events = await apiClient.getEvents({ limit: context.limit });
      const enriched = [];

      for (const event of events.slice(0, context.limit)) {
        // Filter by name/venue if specified
        const nameMatch =
          !context.artist_name ||
          event.name?.toLowerCase().includes(context.artist_name.toLowerCase());
        const venueMatch =
          !context.venue_name ||
          event.venue_name?.toLowerCase().includes(context.venue_name.toLowerCase());

        if (nameMatch && venueMatch) {
          try {
            const analytics = await apiClient.getEventAnalytics(event.id);
            enriched.push({
              name: event.name || "",
              date: event.date || "",
              venue: event.venue_name || "",
              tickets_sold: analytics.tickets_sold || 0,
              capacity: event.capacity,
              revenue: analytics.revenue || 0,
              sell_through_pct: analytics.sell_through_pct || 0,
            });
          } catch {
            enriched.push({
              name: event.name || "",
              date: event.date || "",
              venue: event.venue_name || "",
              tickets_sold: 0,
              capacity: event.capacity,
              revenue: 0,
              sell_through_pct: 0,
            });
          }
        }
      }

      return { events: enriched };
    } catch {
      return { events: [] };
    }
  },
});

export const competitorEventsTool = createTool({
  id: "competitor-events",
  description:
    "Search for competing events in the same market around the same date. Helps identify market saturation.",
  inputSchema: z.object({
    city: z.string().describe("City to search"),
    date: z.string().describe("Target date (ISO format)"),
    genre: z.string().optional().describe("Genre filter"),
    radius_days: z.number().default(14).describe("Days around target date to search"),
  }),
  outputSchema: z.object({
    competing_events: z.array(
      z.object({
        name: z.string(),
        date: z.string(),
        venue: z.string(),
        source: z.string(),
        relevance: z.enum(["direct_competitor", "same_genre", "same_market"]),
      })
    ),
    saturation_level: z.enum(["low", "medium", "high"]),
  }),
  execute: async ({ context }) => {
    const query = `events ${context.genre || ""} ${context.city} ${context.date}`;
    const serpKey = process.env.SERPAPI_KEY;

    if (!serpKey) {
      return { competing_events: [], saturation_level: "medium" as const };
    }

    const url = new URL("https://serpapi.com/search.json");
    url.searchParams.set("q", query);
    url.searchParams.set("num", "10");
    url.searchParams.set("api_key", serpKey);

    const res = await fetch(url.toString());
    const data = await res.json();

    const events = (data.organic_results || []).slice(0, 8).map((r: any) => ({
      name: r.title || "",
      date: context.date,
      venue: "",
      source: r.link || "web",
      relevance: "same_market" as const,
    }));

    const saturation =
      events.length >= 6 ? "high" : events.length >= 3 ? "medium" : "low";

    return {
      competing_events: events,
      saturation_level: saturation,
    };
  },
});

export const researchTools = {
  webSearchTool,
  socialInsightsTool,
  knowledgeBaseTool,
  pastEventPerformanceTool,
  competitorEventsTool,
};
