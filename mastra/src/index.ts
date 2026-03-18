import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { apiRoutes } from "./api/routes.js";
import { mastra } from "./mastra.js";
import "dotenv/config";

const app = new Hono();

// ── Middleware ──

app.use("*", cors());
app.use("*", logger());

// ── Mount API routes ──

app.route("/api/intelligence", apiRoutes);

// ── Root health check ──

app.get("/", (c) =>
  c.json({
    service: "AI Tickets — Event Intelligence API (Mastra)",
    version: "1.0.0",
    status: "running",
    docs: {
      analyze_event: "POST /api/intelligence/analyze-event",
      generate_marketing: "POST /api/intelligence/generate-marketing",
      generate_creatives: "POST /api/intelligence/generate-creatives",
      prepare_distribution: "POST /api/intelligence/prepare-distribution",
      publish_event: "POST /api/intelligence/publish-event",
      full_event_engine: "POST /api/intelligence/full-event-engine",
    },
  })
);

// ── Start server ──

const port = parseInt(process.env.PORT || "3002", 10);

console.log(`
╔══════════════════════════════════════════════════════════╗
║   🎯 Event Intelligence API (Mastra)                    ║
║   Port: ${port}                                             ║
║                                                          ║
║   Agents:                                                ║
║   ├── Research Agent      — Artist & market analysis     ║
║   ├── Audience Agent      — Segment definition           ║
║   ├── Strategy Agent      — Campaign planning            ║
║   ├── Media Buyer Agent   — Meta Ads generation          ║
║   ├── Creative Agent      — Content & visuals            ║
║   ├── Distribution Agent  — Platform listings            ║
║   ├── Publishing Agent    — Multi-platform publish       ║
║   └── Manager Agent       — Orchestrator                 ║
║                                                          ║
║   Endpoints:                                             ║
║   POST /api/intelligence/analyze-event                   ║
║   POST /api/intelligence/generate-marketing              ║
║   POST /api/intelligence/generate-creatives              ║
║   POST /api/intelligence/prepare-distribution            ║
║   POST /api/intelligence/publish-event                   ║
║   POST /api/intelligence/full-event-engine               ║
╚══════════════════════════════════════════════════════════╝
`);

serve({ fetch: app.fetch, port });
