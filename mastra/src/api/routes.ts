import { Hono } from "hono";
import { eventInputSchema } from "../types/index.js";

const app = new Hono();

// ── Lazy import mastra to avoid circular deps ──

async function getMastra() {
  const { mastra } = await import("../mastra.js");
  return mastra;
}

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
      "POST /analyze-event",
      "POST /generate-marketing",
      "POST /generate-creatives",
      "POST /prepare-distribution",
      "POST /publish-event",
      "POST /full-event-engine",
    ],
  })
);

// ── Helper: Parse and validate event input ──

async function parseEventInput(c: any) {
  try {
    const body = await c.req.json();
    return { data: eventInputSchema.parse(body), raw: body };
  } catch {
    return null;
  }
}

// ── Helper: Safely parse JSON from agent output ──

function safeParseJSON(text: string): any {
  try {
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) return JSON.parse(jsonMatch[1].trim());
    return JSON.parse(text);
  } catch {
    return { raw_output: text };
  }
}

// ── 1. /analyze-event — Research only (via workflow) ──

app.post("/analyze-event", async (c) => {
  const parsed = await parseEventInput(c);
  if (!parsed) {
    return c.json(
      { error: "Invalid input. Required: artist_name, event_name, venue_name, city, event_date, event_type" },
      400
    );
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const workflow = mastra.getWorkflow("analyzeEventWorkflow");
  const run = workflow.createRun();
  const result = await run.start({ inputData: parsed.data });

  return c.json({
    research: safeParseJSON(result?.result?.research || "{}"),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 2. /generate-marketing — Research + Audience + Strategy (via workflow) ──

app.post("/generate-marketing", async (c) => {
  const parsed = await parseEventInput(c);
  if (!parsed) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const workflow = mastra.getWorkflow("generateMarketingWorkflow");
  const run = workflow.createRun();
  const result = await run.start({ inputData: parsed.data });

  const output = result?.result || {};
  return c.json({
    research: safeParseJSON(output.research || "{}"),
    audience: safeParseJSON(output.audience || "{}"),
    strategy: safeParseJSON(output.strategy || "{}"),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 3. /generate-creatives — Full pipeline through creatives (via workflow) ──

app.post("/generate-creatives", async (c) => {
  const parsed = await parseEventInput(c);
  if (!parsed) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const workflow = mastra.getWorkflow("generateCreativesWorkflow");
  const run = workflow.createRun();
  const result = await run.start({ inputData: parsed.data });

  const output = result?.result || {};
  return c.json({
    creatives: safeParseJSON(output.creatives || "{}"),
    media_buying: safeParseJSON(output.media_buying || "{}"),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 4. /prepare-distribution — Full pipeline through distribution (via workflow) ──

app.post("/prepare-distribution", async (c) => {
  const parsed = await parseEventInput(c);
  if (!parsed) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const workflow = mastra.getWorkflow("prepareDistributionWorkflow");
  const run = workflow.createRun();
  const result = await run.start({ inputData: parsed.data });

  const output = result?.result || {};
  return c.json({
    distribution: safeParseJSON(output.distribution || "{}"),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 5. /publish-event — Uses Manager Agent directly (needs pre-existing distribution data) ──

app.post("/publish-event", async (c) => {
  const body = await c.req.json();
  const startTime = Date.now();

  const mastra = await getMastra();
  const manager = mastra.getAgent("managerAgent");
  const response = await manager.generate(
    `Publish the following event listings to all configured platforms:\n${JSON.stringify(body.distribution || body, null, 2)}\n\nRun the Publishing Agent. Report success/failure for each platform with URLs.`
  );

  return c.json({
    publishing: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

// ── 6. /full-event-engine — EVERYTHING (via workflow) ──

app.post("/full-event-engine", async (c) => {
  const parsed = await parseEventInput(c);
  if (!parsed) {
    return c.json({ error: "Invalid input" }, 400);
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const workflow = mastra.getWorkflow("fullEventEngineWorkflow");
  const run = workflow.createRun();
  const result = await run.start({ inputData: parsed.data });

  const output = result?.result || {};
  return c.json({
    event_input: parsed.data,
    results: {
      creatives: safeParseJSON(output.creatives || "{}"),
      media_buying: safeParseJSON(output.media_buying || "{}"),
      distribution: safeParseJSON(output.distribution || "{}"),
      publishing: safeParseJSON(output.publishing || "{}"),
    },
    processing_time_ms: Date.now() - startTime,
    generated_at: new Date().toISOString(),
  });
});

// ── 7. /agent — Direct access to Manager Agent for ad-hoc requests ──

app.post("/agent", async (c) => {
  const { prompt } = await c.req.json();
  if (!prompt) {
    return c.json({ error: "Missing 'prompt' field" }, 400);
  }

  const startTime = Date.now();
  const mastra = await getMastra();
  const manager = mastra.getAgent("managerAgent");
  const response = await manager.generate(prompt);

  return c.json({
    response: safeParseJSON(response.text),
    processing_time_ms: Date.now() - startTime,
  });
});

export { app as apiRoutes };
