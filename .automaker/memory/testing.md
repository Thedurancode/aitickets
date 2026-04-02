---
tags: [testing]
summary: testing implementation decisions and patterns
relevantTo: [testing]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# testing

#### [Pattern] 149 tests across 13 files with apparent focus on service/router testing, not MCP tool testing (2026-02-19)
- **Problem solved:** Backend is tested but MCP tool layer (125+ tools) likely has lower coverage
- **Why this works:** Testing individual tools requires mocking LLM tool selection + simulating MCP protocol, which is complex. Testing services + routers is easier because they're pure functions. Tools are thin wrappers so less risk
- **Trade-offs:** Easier: Services/routers are well-tested. Harder: Tool integration bugs only caught in end-to-end voice tests; tool schema drift from code not caught until LLM calls it