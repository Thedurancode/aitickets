---
tags: [gotcha, mistake, edge-case, bug, warning]
summary: Mistakes and edge cases to avoid
relevantTo: [error, bug, fix, issue, problem]
importance: 0.9
relatedFiles: []
usageStats:
  loaded: 1
  referenced: 0
  successfulFeatures: 0
---
# Gotchas

Mistakes and edge cases to avoid. These are lessons learned from past issues.

---



#### [Gotcha] LLM routing through OpenRouter GPT-4o-mini creates latency-sensitive path - tool calls fail if LLM is slow or returns malformed JSON (2026-02-19)
- **Situation:** Voice agent response time depends on LLM inference latency, not just backend computation
- **Root cause:** Voice UX requires sub-2s responses or users perceive system as broken. OpenRouter adds network hop + model inference. If LLM returns invalid JSON or wrong tool name, entire voice action fails
- **How to avoid:** Easier: Don't need to train custom model. Harder: Unpredictable latency; rate limiting; API costs; LLM hallucinations cause errors