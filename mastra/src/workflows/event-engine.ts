import { createStep, createWorkflow } from "@mastra/core/workflows";
import { z } from "zod";

// ── Shared schemas ──

const eventInputSchema = z.object({
  artist_name: z.string(),
  event_name: z.string(),
  venue_name: z.string(),
  city: z.string(),
  state: z.string().optional(),
  country: z.string().default("US"),
  event_date: z.string(),
  event_type: z.string(),
  ticket_price_min: z.number().optional(),
  ticket_price_max: z.number().optional(),
  capacity: z.number().optional(),
  description: z.string().optional(),
  genre: z.string().optional(),
  include_publishing: z.boolean().default(false),
});

function buildEventPrompt(data: z.infer<typeof eventInputSchema>) {
  return `Artist: ${data.artist_name}
Event: ${data.event_name}
Venue: ${data.venue_name}
City: ${data.city}${data.state ? `, ${data.state}` : ""}, ${data.country}
Date: ${data.event_date}
Type: ${data.event_type}
Genre: ${data.genre || "N/A"}
Capacity: ${data.capacity || "Unknown"}
Price Range: $${data.ticket_price_min || "?"} - $${data.ticket_price_max || "?"}
Description: ${data.description || "N/A"}`;
}

// ── Step 1: Research ──

const researchStep = createStep({
  id: "research",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    event_context: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("researchAgent");
    const eventContext = buildEventPrompt(inputData);
    const response = await agent.generate(
      `Analyze this event and produce comprehensive research intelligence:\n\n${eventContext}\n\nProvide a full research report with artist intelligence, engagement score, market analysis, demand forecast, and venue insights. Return your response as structured JSON.`
    );
    return { research: response.text, event_context: eventContext };
  },
});

// ── Step 2: Audience ──

const audienceStep = createStep({
  id: "audience",
  inputSchema: z.object({
    research: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    event_context: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("audienceAgent");
    const response = await agent.generate(
      `Based on the following research, define audience segments and platform targeting strategy:\n\nRESEARCH DATA:\n${inputData.research}\n\nEVENT CONTEXT:\n${inputData.event_context}\n\nDefine 3-5 audience segments with demographics, interests, behaviors, and platform preferences. Return structured JSON.`
    );
    return {
      research: inputData.research,
      audience: response.text,
      event_context: inputData.event_context,
    };
  },
});

// ── Step 3: Marketing Strategy ──

const strategyStep = createStep({
  id: "strategy",
  inputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    event_context: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("marketingStrategyAgent");
    const response = await agent.generate(
      `Build a comprehensive marketing campaign plan:\n\nRESEARCH:\n${inputData.research}\n\nAUDIENCE:\n${inputData.audience}\n\nEVENT:\n${inputData.event_context}\n\nCreate a phased campaign with timeline, channel strategy, messaging, content calendar, and budget. Return structured JSON.`
    );
    return {
      research: inputData.research,
      audience: inputData.audience,
      strategy: response.text,
      event_context: inputData.event_context,
    };
  },
});

// ── Step 4a: Creatives (runs in parallel with media buying) ──

const creativesStep = createStep({
  id: "creatives",
  inputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    creatives: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("creativeDirectorAgent");
    const response = await agent.generate(
      `Create a complete creative package:\n\nEVENT:\n${inputData.event_context}\n\nAUDIENCE:\n${inputData.audience}\n\nSTRATEGY:\n${inputData.strategy}\n\nGenerate Instagram content (feed, stories, reels), TikTok concepts, banner designs, and a flyer concept. Include detailed image generation prompts. Return structured JSON.`
    );
    return { creatives: response.text };
  },
});

// ── Step 4b: Media Buying (runs in parallel with creatives) ──

const mediaBuyingStep = createStep({
  id: "media-buying",
  inputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    media_buying: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("mediaBuyerAgent");
    const response = await agent.generate(
      `Generate Meta Ads campaign structure:\n\nEVENT:\n${inputData.event_context}\n\nAUDIENCE:\n${inputData.audience}\n\nSTRATEGY:\n${inputData.strategy}\n\nCreate a full funnel (cold → warm → hot) with targeting, ad copy variations, budgets, and scaling logic. Return structured JSON.`
    );
    return { media_buying: response.text };
  },
});

// ── Step 5: Distribution (after parallel creatives + media buying) ──

const distributionStep = createStep({
  id: "distribution",
  // After .parallel([creatives, mediaBuying]), the input is keyed by step id
  inputSchema: z.object({
    creatives: z.string(),
    media_buying: z.string(),
    strategy: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    distribution: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    event_context: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    const agent = mastra!.getAgent("distributionAgent");
    const response = await agent.generate(
      `Prepare event listings for multi-platform distribution:\n\nEVENT:\n${inputData.event_context}\n\nMARKETING STRATEGY:\n${inputData.strategy}\n\nCreate a master event record with SEO metadata and platform-specific listings for AI Tickets, Eventbrite, and Facebook Events. Return structured JSON.`
    );
    return {
      distribution: response.text,
      creatives: inputData.creatives,
      media_buying: inputData.media_buying,
      event_context: inputData.event_context,
    };
  },
});

// ── Step 6: Publishing (optional) ──

const publishingStep = createStep({
  id: "publishing",
  inputSchema: z.object({
    distribution: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    event_context: z.string(),
  }),
  outputSchema: z.object({
    distribution: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    publishing: z.string(),
  }),
  execute: async ({ inputData, mastra }) => {
    // Check if publishing was requested via a flag in the event context
    // For now, always attempt publishing — the publishing agent handles "skipped" status
    const agent = mastra!.getAgent("publishingAgent");
    const response = await agent.generate(
      `Publish the following event listings to all configured platforms:\n\nDISTRIBUTION DATA:\n${inputData.distribution}\n\nExecute publishing to AI Tickets (internal), Eventbrite, and Facebook Events. Report status for each platform. Return structured JSON.`
    );
    return {
      distribution: inputData.distribution,
      creatives: inputData.creatives,
      media_buying: inputData.media_buying,
      publishing: response.text,
    };
  },
});

// ── Full Event Engine Workflow ──
// Flow: research → audience → strategy → [creatives, media-buying] → distribution → publishing

export const fullEventEngineWorkflow = createWorkflow({
  id: "full-event-engine",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    distribution: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    publishing: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .parallel([creativesStep, mediaBuyingStep])
  .map({
    // After parallel, output is { creatives: { creatives }, "media-buying": { media_buying } }
    // We need to flatten it for the distribution step
    inputSchema: z.object({
      creatives: z.string(),
      media_buying: z.string(),
      strategy: z.string(),
      event_context: z.string(),
    }),
    fn: ({ inputData }: { inputData: Record<string, any> }) => ({
      creatives: inputData["creatives"]?.creatives || "",
      media_buying: inputData["media-buying"]?.media_buying || "",
      strategy: inputData["strategy"] || "",
      event_context: inputData["event_context"] || "",
    }),
  })
  .then(distributionStep)
  .then(publishingStep)
  .commit();

// ── Analyze Event Workflow (research only) ──

export const analyzeEventWorkflow = createWorkflow({
  id: "analyze-event",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    event_context: z.string(),
  }),
})
  .then(researchStep)
  .commit();

// ── Generate Marketing Workflow (research → audience → strategy) ──

export const generateMarketingWorkflow = createWorkflow({
  id: "generate-marketing",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    event_context: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .commit();

// ── Generate Creatives Workflow (research → audience → strategy → [creatives, media]) ──

export const generateCreativesWorkflow = createWorkflow({
  id: "generate-creatives",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    creatives: z.string(),
    media_buying: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .parallel([creativesStep, mediaBuyingStep])
  .map({
    inputSchema: z.object({
      creatives: z.string(),
      media_buying: z.string(),
    }),
    fn: ({ inputData }: { inputData: Record<string, any> }) => ({
      creatives: inputData["creatives"]?.creatives || "",
      media_buying: inputData["media-buying"]?.media_buying || "",
    }),
  })
  .commit();

// ── Prepare Distribution Workflow ──

export const prepareDistributionWorkflow = createWorkflow({
  id: "prepare-distribution",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    distribution: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    event_context: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .parallel([creativesStep, mediaBuyingStep])
  .map({
    inputSchema: z.object({
      creatives: z.string(),
      media_buying: z.string(),
      strategy: z.string(),
      event_context: z.string(),
    }),
    fn: ({ inputData }: { inputData: Record<string, any> }) => ({
      creatives: inputData["creatives"]?.creatives || "",
      media_buying: inputData["media-buying"]?.media_buying || "",
      strategy: inputData["strategy"] || "",
      event_context: inputData["event_context"] || "",
    }),
  })
  .then(distributionStep)
  .commit();
