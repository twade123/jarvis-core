---
type: improvement
created: 2026-03-25
tags: [connection-doctor, architecture, workspace, flight-recorder-v2]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Connection Doctor workspace designed — autonomous DevOps/SRE with 15 agents across 4 teams
**Date:** 2026-03-25T19:47:47
**Type:** improvement
**Tags:** connection-doctor, architecture, workspace, flight-recorder-v2

> [!success] IMPROVEMENT
> Full design spec at docs/superpowers/specs/2026-03-25-connection-doctor-design.md. Flight Recorder v2 (multi-domain ring buffers) as universal event bus. 5 sentries (9B MLX), 3 first responders (9B), 3 dev team (Sonnet), 4 operations (mixed). Self-healing layers: auto-heal playbooks, LLM diagnosis, human escalation. Route-to-table map auto-populated via instrumentation. Vault workspace is separate — CD reads/writes but doesn't own. Implementation plan Phase 1-2 at docs/superpowers/plans/2026-03-25-connection-doctor-phase1-2.md.
