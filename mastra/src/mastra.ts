import { Mastra } from "@mastra/core";
import { PinoLogger } from "@mastra/loggers";
import { LibSQLStore } from "@mastra/libsql";

import {
  researchAgent,
  audienceAgent,
  marketingStrategyAgent,
  mediaBuyerAgent,
  creativeDirectorAgent,
  distributionAgent,
  publishingAgent,
  managerAgent,
} from "./agents/index.js";

import {
  fullEventEngineWorkflow,
  analyzeEventWorkflow,
  generateMarketingWorkflow,
  generateCreativesWorkflow,
  prepareDistributionWorkflow,
} from "./workflows/index.js";

const dbUrl = process.env.DATABASE_URL || "file:./mastra.db";

export const mastra = new Mastra({
  agents: {
    researchAgent,
    audienceAgent,
    marketingStrategyAgent,
    mediaBuyerAgent,
    creativeDirectorAgent,
    distributionAgent,
    publishingAgent,
    managerAgent,
  },
  workflows: {
    fullEventEngineWorkflow,
    analyzeEventWorkflow,
    generateMarketingWorkflow,
    generateCreativesWorkflow,
    prepareDistributionWorkflow,
  },
  storage: new LibSQLStore({
    url: dbUrl,
  }),
  logger: new PinoLogger({
    name: "EventIntelligence",
    level: process.env.NODE_ENV === "production" ? "info" : "debug",
  }),
});
