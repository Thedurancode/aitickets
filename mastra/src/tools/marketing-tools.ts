import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { apiClient } from "../utils/api-client.js";

export const getCustomerSegmentsTool = createTool({
  id: "get-customer-segments",
  description:
    "Retrieve customer segments from the AI Tickets system. Returns RFM-based segments like Champions, Loyal, At Risk, etc.",
  inputSchema: z.object({
    event_id: z.number().optional().describe("Filter segments for a specific event"),
  }),
  outputSchema: z.object({
    segments: z.array(
      z.object({
        name: z.string(),
        count: z.number(),
        avg_spend: z.number(),
        characteristics: z.array(z.string()),
      })
    ),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.callMcpTool("get_customer_segments", {
        event_id: context.event_id,
      });
      return {
        segments: result.segments || [],
      };
    } catch {
      return { segments: [] };
    }
  },
});

export const getRevenueForecastTool = createTool({
  id: "get-revenue-forecast",
  description:
    "Get revenue forecast and demand prediction from the analytics engine for an event.",
  inputSchema: z.object({
    event_id: z.number().describe("Event ID to forecast"),
  }),
  outputSchema: z.object({
    forecast: z.object({
      predicted_revenue: z.number(),
      predicted_attendance: z.number(),
      confidence: z.number(),
      trend: z.string(),
    }),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.callMcpTool("get_revenue_forecast", {
        event_id: context.event_id,
      });
      return { forecast: result };
    } catch {
      return {
        forecast: {
          predicted_revenue: 0,
          predicted_attendance: 0,
          confidence: 0,
          trend: "unknown",
        },
      };
    }
  },
});

export const createMetaCampaignTool = createTool({
  id: "create-meta-campaign",
  description:
    "Create a Meta (Facebook/Instagram) ad campaign through the AI Tickets Meta Ads integration.",
  inputSchema: z.object({
    event_id: z.number().describe("Event to promote"),
    campaign_name: z.string().describe("Campaign name"),
    daily_budget: z.number().describe("Daily budget in dollars"),
    objective: z
      .enum(["LINK_CLICKS", "CONVERSIONS", "REACH", "VIDEO_VIEWS"])
      .default("LINK_CLICKS"),
    targeting: z
      .object({
        age_min: z.number().default(18),
        age_max: z.number().default(65),
        interests: z.array(z.string()).default([]),
        radius_km: z.number().default(25),
      })
      .optional(),
    ad_copy: z
      .object({
        primary_text: z.string(),
        headline: z.string(),
        description: z.string(),
        cta: z.string().default("LEARN_MORE"),
      })
      .optional(),
  }),
  outputSchema: z.object({
    campaign_id: z.string().optional(),
    status: z.string(),
    message: z.string(),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.createMetaAd({
        event_id: context.event_id,
        name: context.campaign_name,
        daily_budget: context.daily_budget,
        objective: context.objective,
        targeting: context.targeting,
        ad_copy: context.ad_copy,
      });
      return {
        campaign_id: result.id || result.campaign_id,
        status: "created",
        message: `Campaign "${context.campaign_name}" created successfully`,
      };
    } catch (err: any) {
      return {
        campaign_id: undefined,
        status: "failed",
        message: err.message || "Failed to create Meta campaign",
      };
    }
  },
});

export const sendEmailCampaignTool = createTool({
  id: "send-email-campaign",
  description:
    "Send an email marketing campaign through the AI Tickets notification system.",
  inputSchema: z.object({
    subject: z.string().describe("Email subject line"),
    body: z.string().describe("Email body (HTML supported)"),
    segment: z
      .string()
      .optional()
      .describe("Target segment: all, vip, at_risk, champions"),
    event_id: z.number().optional(),
  }),
  outputSchema: z.object({
    sent_count: z.number(),
    status: z.string(),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.sendCampaign({
        subject: context.subject,
        body: context.body,
        segment: context.segment || "all",
        event_id: context.event_id,
        channel: "email",
      });
      return {
        sent_count: result.sent_count || 0,
        status: "sent",
      };
    } catch {
      return { sent_count: 0, status: "failed" };
    }
  },
});

export const publishToSocialTool = createTool({
  id: "publish-to-social",
  description:
    "Publish content to social media platforms via the AI Tickets Postiz integration.",
  inputSchema: z.object({
    content: z.string().describe("Post content/caption"),
    platforms: z.array(z.string()).describe("Target platforms"),
    image_url: z.string().optional().describe("Image URL to attach"),
    scheduled_at: z.string().optional().describe("Schedule time (ISO format)"),
  }),
  outputSchema: z.object({
    status: z.string(),
    post_ids: z.array(z.string()),
  }),
  execute: async ({ context }) => {
    try {
      const result = await apiClient.callMcpTool("post_event_to_social", {
        content: context.content,
        platforms: context.platforms,
        image_url: context.image_url,
        scheduled_at: context.scheduled_at,
      });
      return {
        status: "published",
        post_ids: result.post_ids || [],
      };
    } catch {
      return { status: "failed", post_ids: [] };
    }
  },
});

export const marketingTools = {
  getCustomerSegmentsTool,
  getRevenueForecastTool,
  createMetaCampaignTool,
  sendEmailCampaignTool,
  publishToSocialTool,
};
