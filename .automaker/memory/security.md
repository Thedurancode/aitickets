---
tags: [security]
summary: security implementation decisions and patterns
relevantTo: [security]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# security

### MCP tools validate input schema but delegate authorization to service layer - no auth checks in tool definitions (2026-02-19)
- **Context:** Tools run inside MCP server which is called by LLM with user context passed implicitly
- **Why:** MCP tools aren't HTTP endpoints, so they don't have request context (no JWT token in headers). Authorization check must happen in service layer after user identity is established at API gateway level (/voice/action endpoint validates token, then calls MCP tools)
- **Rejected:** Auth checks in each MCP tool (code duplication); JWT validation in MCP server (adds complexity); Unauthorized tools blocking at MCP layer
- **Trade-offs:** Easier: Centralized auth at API gateway. Harder: Easy to forget auth check in a new service; difficult to audit which user called which tool
- **Breaking if changed:** Removing service-layer auth checks would allow unauthenticated LLM calls to modify database