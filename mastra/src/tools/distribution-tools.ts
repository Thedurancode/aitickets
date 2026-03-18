import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { apiClient } from "../utils/api-client.js";

export const createEventListingTool = createTool({
  id: "create-event-listing",
  description:
    "Create an event listing in the AI Tickets system as the master record for distribution.",
  inputSchema: z.object({
    name: z.string(),
    description: z.string(),
    date: z.string(),
    time: z.string().optional(),
    venue_id: z.number().optional(),
    venue_name: z.string().optional(),
    category_id: z.number().optional(),
    visibility: z.enum(["public", "private", "unlisted"]).default("public"),
    tiers: z
      .array(
        z.object({
          name: z.string(),
          price: z.number(),
          quantity: z.number(),
        })
      )
      .optional(),
  }),
  outputSchema: z.object({
    event_id: z.number().optional(),
    status: z.string(),
    url: z.string().optional(),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.createEvent(context);
      return {
        event_id: result.id,
        status: "created",
        url: result.url || `/events/${result.id}`,
      };
    } catch (err: any) {
      return {
        event_id: undefined,
        status: "failed",
        url: undefined,
      };
    }
  },
});

export const publishToEventbriteTool = createTool({
  id: "publish-to-eventbrite",
  description:
    "Publish an event listing to Eventbrite. Requires EVENTBRITE_API_KEY to be configured.",
  inputSchema: z.object({
    title: z.string(),
    description: z.string(),
    start_date: z.string().describe("ISO 8601 datetime"),
    end_date: z.string().describe("ISO 8601 datetime"),
    venue_name: z.string(),
    venue_address: z.string().optional(),
    city: z.string(),
    capacity: z.number().optional(),
    ticket_classes: z
      .array(
        z.object({
          name: z.string(),
          price: z.number(),
          quantity: z.number(),
        })
      )
      .optional(),
    category: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }),
  outputSchema: z.object({
    platform: z.string(),
    status: z.enum(["success", "failed", "skipped"]),
    url: z.string().optional(),
    platform_id: z.string().optional(),
    error: z.string().optional(),
  }),
  execute: async ({ context }) => {
    const apiKey = process.env.EVENTBRITE_API_KEY;
    const orgId = process.env.EVENTBRITE_ORG_ID;

    if (!apiKey || !orgId) {
      return {
        platform: "eventbrite",
        status: "skipped" as const,
        error: "EVENTBRITE_API_KEY or EVENTBRITE_ORG_ID not configured",
      };
    }

    try {
      // Create event on Eventbrite
      const eventRes = await fetch(
        `https://www.eventbriteapi.com/v3/organizations/${orgId}/events/`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event: {
              name: { html: context.title },
              description: { html: context.description },
              start: { timezone: "America/New_York", utc: context.start_date },
              end: { timezone: "America/New_York", utc: context.end_date },
              currency: "USD",
              capacity: context.capacity,
            },
          }),
        }
      );

      if (!eventRes.ok) {
        const errText = await eventRes.text();
        return {
          platform: "eventbrite",
          status: "failed" as const,
          error: `Eventbrite API error: ${errText}`,
        };
      }

      const eventData = await eventRes.json();

      // Create ticket classes if provided
      if (context.ticket_classes?.length) {
        for (const tc of context.ticket_classes) {
          await fetch(
            `https://www.eventbriteapi.com/v3/events/${eventData.id}/ticket_classes/`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${apiKey}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                ticket_class: {
                  name: tc.name,
                  cost: `USD,${tc.price * 100}`,
                  quantity_total: tc.quantity,
                },
              }),
            }
          );
        }
      }

      // Publish the event
      await fetch(
        `https://www.eventbriteapi.com/v3/events/${eventData.id}/publish/`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${apiKey}` },
        }
      );

      return {
        platform: "eventbrite",
        status: "success" as const,
        url: eventData.url,
        platform_id: eventData.id,
      };
    } catch (err: any) {
      return {
        platform: "eventbrite",
        status: "failed" as const,
        error: err.message,
      };
    }
  },
});

export const publishToFacebookEventsTool = createTool({
  id: "publish-to-facebook-events",
  description:
    "Create a Facebook Event through the Meta Graph API. Requires META_ACCESS_TOKEN.",
  inputSchema: z.object({
    name: z.string(),
    description: z.string(),
    start_time: z.string().describe("ISO 8601 datetime"),
    end_time: z.string().optional(),
    location: z.string(),
    cover_url: z.string().optional(),
  }),
  outputSchema: z.object({
    platform: z.string(),
    status: z.enum(["success", "failed", "skipped"]),
    url: z.string().optional(),
    platform_id: z.string().optional(),
    error: z.string().optional(),
  }),
  execute: async ({ context }) => {
    const token = process.env.META_ACCESS_TOKEN;
    const pageId = process.env.META_PAGE_ID;

    if (!token || !pageId) {
      return {
        platform: "facebook_events",
        status: "skipped" as const,
        error: "META_ACCESS_TOKEN or META_PAGE_ID not configured",
      };
    }

    try {
      const res = await fetch(
        `https://graph.facebook.com/v19.0/${pageId}/events`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: context.name,
            description: context.description,
            start_time: context.start_time,
            end_time: context.end_time,
            place: { name: context.location },
            access_token: token,
          }),
        }
      );

      if (!res.ok) {
        const errText = await res.text();
        return {
          platform: "facebook_events",
          status: "failed" as const,
          error: errText,
        };
      }

      const data = await res.json();
      return {
        platform: "facebook_events",
        status: "success" as const,
        url: `https://www.facebook.com/events/${data.id}`,
        platform_id: data.id,
      };
    } catch (err: any) {
      return {
        platform: "facebook_events",
        status: "failed" as const,
        error: err.message,
      };
    }
  },
});

export const generateSeoMetadataTool = createTool({
  id: "generate-seo-metadata",
  description:
    "Generate SEO metadata, Open Graph tags, and structured data for an event listing.",
  inputSchema: z.object({
    event_name: z.string(),
    artist_name: z.string(),
    venue_name: z.string(),
    city: z.string(),
    date: z.string(),
    description: z.string(),
    ticket_url: z.string().optional(),
  }),
  outputSchema: z.object({
    seo_title: z.string(),
    seo_description: z.string(),
    keywords: z.array(z.string()),
    og_title: z.string(),
    og_description: z.string(),
    structured_data: z.string().describe("JSON-LD structured data"),
  }),
  execute: async ({ context }) => {
    const title = `${context.event_name} | ${context.venue_name}, ${context.city}`;
    const desc = `${context.artist_name} live at ${context.venue_name} in ${context.city} on ${context.date}. ${context.description.substring(0, 150)}`;

    const structuredData = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "MusicEvent",
      name: context.event_name,
      performer: { "@type": "Person", name: context.artist_name },
      location: {
        "@type": "Place",
        name: context.venue_name,
        address: { "@type": "PostalAddress", addressLocality: context.city },
      },
      startDate: context.date,
      offers: context.ticket_url
        ? {
            "@type": "Offer",
            url: context.ticket_url,
            availability: "https://schema.org/InStock",
          }
        : undefined,
    });

    return {
      seo_title: title.substring(0, 60),
      seo_description: desc.substring(0, 160),
      keywords: [
        context.artist_name,
        context.venue_name,
        context.city,
        "tickets",
        "live event",
        "concert",
      ],
      og_title: title.substring(0, 60),
      og_description: desc.substring(0, 200),
      structured_data: structuredData,
    };
  },
});

export const distributionTools = {
  createEventListingTool,
  publishToEventbriteTool,
  publishToFacebookEventsTool,
  generateSeoMetadataTool,
};
