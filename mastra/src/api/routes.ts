import { Hono } from "hono";
import { z } from "zod";
import { mastra } from "../mastra.js";
import { managerAgent } from "../agents/manager-agent.js";
import { eventInputSchema } from "../types/index.js";

const app = new Hono();

// ── Health Check ──

app.get("/", (c) =>
  c.json({
    service: "Event Intelligence API",
    version: "1.0.0",
    status: "running",
    agents: [
      "research",
      "audience",
      "marketing-strategy",
      "media-buyer",
      "creative-director",
      "distribution",
      "publishing",
      "manager",
    ],
    endpoints: [
      "/analyze-event",
      "/generate-marketing",
      "/generate-creatives",
      "/prepare-distribution",
      "/publish-event",
      "/full-event-engine",
    ],
  })
);

// ── Helper: Parse and validate event input ──

async function parseEventInput(c: any) {
  try {
    const body = await c.req.json();
    return eventInputSchema.parse(body);
  } catch (err: any) {
    return null;
  }
}

// ── 1. /analyze-event — Research only ──

app.post("/analyze-event", async (c) => {
  const input = await parseEventInput(c);
  if (!input) {
    return c.json({ error: "Invalid input. Required: artist_name, event_name, venue_name, city, event_date, event_type" }, 400);
  }

  const startTime = Date.now();

  const prompt = `Analyze this event:
Artist: ${input.artist_name}
Event: ${input.event_name}
Venue: ${input.venue_name}
City: ${input.city}${input.state ? `, ${input.state}` : ""}, ${input.country}
Date: ${input.event_date}
Type: ${input.event_type}
Genre: ${input.genre || "N/A"}
Capacity: ${input.capacity || "Unknown"}
Price Range: $${input.ticket_price_min || "?"} - $${input.ticket_price_max || "?"}

Use your tools to research the artist, venue, and market. Return comprehensive research intelligence as JSON.`;

  const response = await managerAgent.generate(
    `Run ONLY the Research Agent for this event analysis request. ${prompt}`
  );

  return c.json({
    research: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 2. /generate-marketing — Research + Audience + Strategy ──

app.post("/generate-marketing", async (c) => {
  const input = await parseEventInput(c);
  if (!input) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();

  const prompt = `Generate a complete marketing strategy for this event:
Artist: ${input.artist_name}
Event: ${input.event_name}
Venue: ${input.venue_name}, ${input.city}
Date: ${input.event_date}
Type: ${input.event_type}
Genre: ${input.genre || "N/A"}
Capacity: ${input.capacity || "Unknown"}
Price: $${input.ticket_price_min || "?"} - $${input.ticket_price_max || "?"}

Run the Research Agent first, then the Audience Agent, then the Marketing Strategy Agent. Return all results.`;

  const response = await managerAgent.generate(prompt);

  return c.json({
    marketing: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 3. /generate-creatives — Research + Audience + Strategy + Creatives + Ads ──

app.post("/generate-creatives", async (c) => {
  const input = await parseEventInput(c);
  if (!input) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();

  const prompt = `Generate a complete creative and ad package for this event:
Artist: ${input.artist_name}
Event: ${input.event_name}
Venue: ${input.venue_name}, ${input.city}
Date: ${input.event_date}
Type: ${input.event_type}
Genre: ${input.genre || "N/A"}
Price: $${input.ticket_price_min || "?"} - $${input.ticket_price_max || "?"}

Run: Research Agent → Audience Agent → Marketing Strategy Agent → Creative Director Agent + Media Buyer Agent (in parallel). Return all results.`;

  const response = await managerAgent.generate(prompt);

  return c.json({
    creatives: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 4. /prepare-distribution — Full pipeline minus publishing ──

app.post("/prepare-distribution", async (c) => {
  const input = await parseEventInput(c);
  if (!input) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();

  const prompt = `Prepare distribution listings for this event:
Artist: ${input.artist_name}
Event: ${input.event_name}
Venue: ${input.venue_name}, ${input.city}
Date: ${input.event_date}
Type: ${input.event_type}
Description: ${input.description || "N/A"}

Run Research Agent → Audience Agent → Marketing Strategy Agent → Distribution Agent. Create a master event record with SEO metadata and platform-specific listings. Do NOT publish. Return all results.`;

  const response = await managerAgent.generate(prompt);

  return c.json({
    distribution: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 5. /publish-event — Publish prepared listings ──

app.post("/publish-event", async (c) => {
  const body = await c.req.json();
  const startTime = Date.now();

  const prompt = `Publish the following event listings to all configured platforms:
${JSON.stringify(body.distribution || body, null, 2)}

Run the Publishing Agent. Report success/failure for each platform with URLs.`;

  const response = await managerAgent.generate(prompt);

  return c.json({
    publishing: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 6. /full-event-engine — EVERYTHING ──

app.post("/full-event-engine", async (c) => {
  const input = await parseEventInput(c);
  if (!input) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();
  const includePublishing = (await c.req.json()).include_publishing === true;

  const prompt = `Run the FULL event intelligence engine for this event:

Artist: ${input.artist_name}
Event: ${input.event_name}
Venue: ${input.venue_name}
City: ${input.city}${input.state ? `, ${input.state}` : ""}, ${input.country}
Date: ${input.event_date}
Type: ${input.event_type}
Genre: ${input.genre || "N/A"}
Capacity: ${input.capacity || "Unknown"}
Price Range: $${input.ticket_price_min || "?"} - $${input.ticket_price_max || "?"}
Description: ${input.description || "N/A"}

Execute the COMPLETE pipeline:
1. Research Agent — full event analysis
2. Audience Agent — segment definition
3. Marketing Strategy Agent — campaign plan
4. Creative Director Agent + Media Buyer Agent — in parallel
5. Distribution Agent — platform listings
${includePublishing ? "6. Publishing Agent — publish to all platforms" : "6. SKIP publishing (not requested)"}

Return ALL results from every agent in a single structured JSON response.`;

  const response = await managerAgent.generate(prompt);

  return c.json({
    event_input: input,
    results: safeParseJSON(response.text),
    include_publishing: includePublishing,
    processing_time_ms: Date.now() - startTime,
    generated_at: new Date().toISOString(),
  });
});

// ── Helper: Safely parse JSON from agent output ──

function safeParseJSON(text: string): any {
  try {
    // Try to extract JSON from markdown code blocks
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[1].trim());
    }
    return JSON.parse(text);
  } catch {
    return { raw_output: text };
  }
}

export { app as apiRoutes };
