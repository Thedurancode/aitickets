import { createStep, createWorkflow } from "@mastra/core/workflows";
import { z } from "zod";
import { researchAgent } from "../agents/research-agent.js";
import { audienceAgent } from "../agents/audience-agent.js";
import { marketingStrategyAgent } from "../agents/marketing-strategy-agent.js";
import { mediaBuyerAgent } from "../agents/media-buyer-agent.js";
import { creativeDirectorAgent } from "../agents/creative-director-agent.js";
import { distributionAgent } from "../agents/distribution-agent.js";
import { publishingAgent } from "../agents/publishing-agent.js";

// ── Shared input schema ──

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

// ── Step 1: Research ──

const researchStep = createStep({
  id: "research",
  inputSchema: eventInputSchema,
  outputSchema: z.object({ research: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Analyze this event and produce comprehensive research intelligence:

Artist: ${inputData.artist_name}
Event: ${inputData.event_name}
Venue: ${inputData.venue_name}
City: ${inputData.city}${inputData.state ? `, ${inputData.state}` : ""}, ${inputData.country}
Date: ${inputData.event_date}
Type: ${inputData.event_type}
Genre: ${inputData.genre || "N/A"}
Capacity: ${inputData.capacity || "Unknown"}
Price Range: $${inputData.ticket_price_min || "?"} - $${inputData.ticket_price_max || "?"}

Provide a full research report with artist intelligence, engagement score, market analysis, demand forecast, and venue insights. Return your response as structured JSON.`;

    const response = await researchAgent.generate(prompt);
    return { research: response.text };
  },
});

// ── Step 2: Audience ──

const audienceStep = createStep({
  id: "audience",
  inputSchema: z.object({
    research: z.string(),
    artist_name: z.string(),
    event_type: z.string(),
    city: z.string(),
    genre: z.string().optional(),
  }),
  outputSchema: z.object({ audience: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Based on the following research, define audience segments and platform targeting strategy:

RESEARCH DATA:
${inputData.research}

CONTEXT:
- Artist: ${inputData.artist_name}
- Event Type: ${inputData.event_type}
- City: ${inputData.city}
- Genre: ${inputData.genre || "N/A"}

Define 3-5 audience segments with demographics, interests, behaviors, and platform preferences. Return structured JSON.`;

    const response = await audienceAgent.generate(prompt);
    return { audience: response.text };
  },
});

// ── Step 3: Marketing Strategy ──

const strategyStep = createStep({
  id: "strategy",
  inputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    event_name: z.string(),
    event_date: z.string(),
    ticket_price_min: z.number().optional(),
    ticket_price_max: z.number().optional(),
    capacity: z.number().optional(),
  }),
  outputSchema: z.object({ strategy: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Build a comprehensive marketing campaign plan based on this research and audience analysis:

RESEARCH:
${inputData.research}

AUDIENCE:
${inputData.audience}

EVENT DETAILS:
- Event: ${inputData.event_name}
- Date: ${inputData.event_date}
- Price: $${inputData.ticket_price_min || "?"} - $${inputData.ticket_price_max || "?"}
- Capacity: ${inputData.capacity || "Unknown"}

Create a phased campaign with timeline, channel strategy, messaging, content calendar, and budget. Return structured JSON.`;

    const response = await marketingStrategyAgent.generate(prompt);
    return { strategy: response.text };
  },
});

// ── Step 4a: Creatives (parallel with Media Buying) ──

const creativesStep = createStep({
  id: "creatives",
  inputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    artist_name: z.string(),
    event_name: z.string(),
    event_type: z.string(),
    genre: z.string().optional(),
  }),
  outputSchema: z.object({ creatives: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Create a complete creative package for this event:

ARTIST: ${inputData.artist_name}
EVENT: ${inputData.event_name}
TYPE: ${inputData.event_type}
GENRE: ${inputData.genre || "N/A"}

AUDIENCE SEGMENTS:
${inputData.audience}

MARKETING STRATEGY:
${inputData.strategy}

Generate Instagram content (feed, stories, reels), TikTok concepts, banner designs, and a flyer concept. Include detailed image generation prompts. Return structured JSON.`;

    const response = await creativeDirectorAgent.generate(prompt);
    return { creatives: response.text };
  },
});

// ── Step 4b: Media Buying (parallel with Creatives) ──

const mediaBuyingStep = createStep({
  id: "media-buying",
  inputSchema: z.object({
    audience: z.string(),
    strategy: z.string(),
    event_name: z.string(),
    city: z.string(),
    venue_name: z.string(),
    ticket_price_min: z.number().optional(),
    ticket_price_max: z.number().optional(),
  }),
  outputSchema: z.object({ media_buying: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Generate Meta Ads campaign structure for this event:

EVENT: ${inputData.event_name}
LOCATION: ${inputData.venue_name}, ${inputData.city}
PRICE RANGE: $${inputData.ticket_price_min || "?"} - $${inputData.ticket_price_max || "?"}

AUDIENCE:
${inputData.audience}

STRATEGY:
${inputData.strategy}

Create a full funnel (cold → warm → hot) with targeting, ad copy variations, budgets, and scaling logic. Return structured JSON.`;

    const response = await mediaBuyerAgent.generate(prompt);
    return { media_buying: response.text };
  },
});

// ── Step 5: Distribution ──

const distributionStep = createStep({
  id: "distribution",
  inputSchema: z.object({
    event_name: z.string(),
    artist_name: z.string(),
    venue_name: z.string(),
    city: z.string(),
    event_date: z.string(),
    event_type: z.string(),
    description: z.string().optional(),
    strategy: z.string(),
  }),
  outputSchema: z.object({ distribution: z.string() }),
  execute: async ({ inputData }) => {
    const prompt = `Prepare event listings for multi-platform distribution:

EVENT: ${inputData.event_name}
ARTIST: ${inputData.artist_name}
VENUE: ${inputData.venue_name}
CITY: ${inputData.city}
DATE: ${inputData.event_date}
TYPE: ${inputData.event_type}
DESCRIPTION: ${inputData.description || "N/A"}

MARKETING STRATEGY CONTEXT:
${inputData.strategy}

Create a master event record with SEO metadata and platform-specific listings for AI Tickets, Eventbrite, and Facebook Events. Return structured JSON.`;

    const response = await distributionAgent.generate(prompt);
    return { distribution: response.text };
  },
});

// ── Step 6: Publishing (optional) ──

const publishingStep = createStep({
  id: "publishing",
  inputSchema: z.object({
    distribution: z.string(),
    include_publishing: z.boolean(),
  }),
  outputSchema: z.object({ publishing: z.string() }),
  execute: async ({ inputData }) => {
    if (!inputData.include_publishing) {
      return {
        publishing: JSON.stringify({
          results: [],
          summary: { total: 0, succeeded: 0, failed: 0, skipped: 0 },
          message: "Publishing skipped — not requested",
        }),
      };
    }

    const prompt = `Publish the following event listings to all configured platforms:

DISTRIBUTION DATA:
${inputData.distribution}

Execute publishing to AI Tickets (internal), Eventbrite, and Facebook Events. Report status for each platform. Return structured JSON.`;

    const response = await publishingAgent.generate(prompt);
    return { publishing: response.text };
  },
});

// ── Full Event Engine Workflow ──

export const fullEventEngineWorkflow = createWorkflow({
  id: "full-event-engine",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
    distribution: z.string(),
    publishing: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .parallel([creativesStep, mediaBuyingStep])
  .then(distributionStep)
  .then(publishingStep);

// ── Focused Workflows ──

export const analyzeEventWorkflow = createWorkflow({
  id: "analyze-event",
  inputSchema: eventInputSchema,
  outputSchema: z.object({ research: z.string() }),
}).then(researchStep);

export const generateMarketingWorkflow = createWorkflow({
  id: "generate-marketing",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep);

export const generateCreativesWorkflow = createWorkflow({
  id: "generate-creatives",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    creatives: z.string(),
    media_buying: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .parallel([creativesStep, mediaBuyingStep]);

export const prepareDistributionWorkflow = createWorkflow({
  id: "prepare-distribution",
  inputSchema: eventInputSchema,
  outputSchema: z.object({
    research: z.string(),
    audience: z.string(),
    strategy: z.string(),
    distribution: z.string(),
  }),
})
  .then(researchStep)
  .then(audienceStep)
  .then(strategyStep)
  .then(distributionStep);
