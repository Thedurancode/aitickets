import { Mastra } from "@mastra/core/mastra";

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
});
