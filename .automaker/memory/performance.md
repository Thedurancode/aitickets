---
tags: [performance]
summary: performance implementation decisions and patterns
relevantTo: [performance]
importance: 0.7
relatedFiles: []
usageStats:
  loaded: 0
  referenced: 0
  successfulFeatures: 0
---
# performance

### RAG knowledge base with semantic search instead of hardcoded FAQ - allows customer context without tool proliferation (2026-02-19)
- **Context:** Ticketing system needs to answer questions like 'Can I transfer my ticket?' without creating 100+ different tools
- **Why:** Embedding search (semantic) vs keyword search lets LLM answer nuanced questions by retrieving relevant documents, then synthesizing answer. Scales to thousands of documents without new tools
- **Rejected:** 100+ separate tools for FAQ items; keyword search (misses synonyms); no FAQ support
- **Trade-offs:** Easier: Add docs without code changes. Harder: Requires embedding model; semantic search can be slow; requires document management UI
- **Breaking if changed:** Removing RAG forces tools to be created for every FAQ variation