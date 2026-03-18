import { Agent } from "@mastra/core/agent";
import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { researchAgent } from "./research-agent.js";
import { audienceAgent } from "./audience-agent.js";
import { marketingStrategyAgent } from "./marketing-strategy-agent.js";
import { mediaBuyerAgent } from "./media-buyer-agent.js";
import { creativeDirectorAgent } from "./creative-director-agent.js";
import { distributionAgent } from "./distribution-agent.js";
import { publishingAgent } from "./publishing-agent.js";

// ── Sub-agent tools (supervisor pattern) ──

const callResearchAgent = createTool({
  id: "call-research-agent",
  description:
    "Delegate to the Research Agent to analyze an artist, venue, and market. Provide event details as input.",
  inputSchema: z.object({
    prompt: z.string().describe("Detailed research request including artist, venue, city, date, and event type"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await researchAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callAudienceAgent = createTool({
  id: "call-audience-agent",
  description:
    "Delegate to the Audience Agent to define audience segments and platform targeting. Provide research context.",
  inputSchema: z.object({
    prompt: z.string().describe("Audience analysis request with research context"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await audienceAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callMarketingStrategyAgent = createTool({
  id: "call-marketing-strategy-agent",
  description:
    "Delegate to the Marketing Strategy Agent to build campaign plans. Provide research and audience context.",
  inputSchema: z.object({
    prompt: z.string().describe("Marketing strategy request with full context"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await marketingStrategyAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callMediaBuyerAgent = createTool({
  id: "call-media-buyer-agent",
  description:
    "Delegate to the Media Buyer Agent to generate Meta Ads campaigns. Provide audience and strategy context.",
  inputSchema: z.object({
    prompt: z.string().describe("Media buying request with audience targeting data"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await mediaBuyerAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callCreativeDirectorAgent = createTool({
  id: "call-creative-director-agent",
  description:
    "Delegate to the Creative Director Agent to generate visuals, ad copy, and content. Provide event and brand context.",
  inputSchema: z.object({
    prompt: z.string().describe("Creative brief with event details, audience, and brand guidelines"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await creativeDirectorAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callDistributionAgent = createTool({
  id: "call-distribution-agent",
  description:
    "Delegate to the Distribution Agent to normalize event data and prepare platform listings.",
  inputSchema: z.object({
    prompt: z.string().describe("Distribution request with complete event data"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await distributionAgent.generate(context.prompt);
    return { result: response.text };
  },
});

const callPublishingAgent = createTool({
  id: "call-publishing-agent",
  description:
    "Delegate to the Publishing Agent to publish event listings to external platforms. Only call after distribution is complete.",
  inputSchema: z.object({
    prompt: z.string().describe("Publishing request with prepared listings data"),
  }),
  outputSchema: z.object({ result: z.string() }),
  execute: async ({ context }) => {
    const response = await publishingAgent.generate(context.prompt);
    return { result: response.text };
  },
});

// ── Manager Agent (Orchestrator / Supervisor) ──

export const managerAgent = new Agent({
  id: "manager-agent",
  name: "Manager Agent",
  description:
    "Orchestrator that receives requests and coordinates sub-agents to produce comprehensive event intelligence packages.",
  instructions: `You are the Event Intelligence Manager — the orchestrator of a team of specialized AI agents. You receive event data and coordinate the right agents to produce comprehensive, actionable output.

## Your Team
1. **Research Agent** — Analyzes artists, venues, markets. Call first for any new event.
2. **Audience Agent** — Defines audience segments and platform targeting. Needs research data.
3. **Marketing Strategy Agent** — Builds campaign timelines and messaging. Needs research + audience data.
4. **Media Buyer Agent** — Generates Meta Ads campaigns. Needs audience + strategy data.
5. **Creative Director Agent** — Produces visuals, copy, video concepts. Needs strategy + audience data.
6. **Distribution Agent** — Normalizes event data for multi-platform listing. Needs event details.
7. **Publishing Agent** — Pushes listings to platforms. Only call after distribution. Only if user requests publishing.

## Orchestration Flow

### For /analyze-event:
1. Call Research Agent with full event details
2. Return research results

### For /generate-marketing:
1. Call Research Agent (if no prior research)
2. Call Audience Agent with research context
3. Call Marketing Strategy Agent with research + audience context
4. Return marketing strategy

### For /generate-creatives:
1. Ensure research + audience + strategy exist
2. Call Creative Director Agent with full context
3. Call Media Buyer Agent with audience + strategy context
4. Return creatives + ad campaigns

### For /prepare-distribution:
1. Call Distribution Agent with event details
2. Return master record + platform listings

### For /publish-event:
1. Ensure distribution is prepared
2. Call Publishing Agent with prepared listings
3. Return publishing results

### For /full-event-engine:
1. Research Agent → 2. Audience Agent → 3. Marketing Strategy Agent → 4. Creative Director Agent + Media Buyer Agent (parallel) → 5. Distribution Agent → 6. Publishing Agent (optional)
Return everything.

## Rules
- ALWAYS pass complete context to each agent. Agents don't share memory — you must relay information.
- Run agents in the correct dependency order. Never call Audience before Research.
- Creative Director and Media Buyer CAN run in parallel after Strategy is complete.
- Publishing Agent is ONLY called when explicitly requested.
- If any agent produces low-quality or uncertain output, note it in your response.
- Aggregate all agent outputs into a single structured response.
- Handle partial requests gracefully — if the user only wants research, just run research.
- Track processing time and include it in the response.`,
  model: {
    provider: "OPEN_AI",
    name: "gpt-4o",
  },
  tools: {
    callResearchAgent,
    callAudienceAgent,
    callMarketingStrategyAgent,
    callMediaBuyerAgent,
    callCreativeDirectorAgent,
    callDistributionAgent,
    callPublishingAgent,
  },
});
