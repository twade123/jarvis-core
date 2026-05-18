---
type: improvement
created: 2026-03-22
tags: [vault, flight-recorder, visibility, audit, hygiene]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Vault wired into flight recorder — VAULT_LOAD, VAULT_QUERY, VAULT_IMAGES stages added
**Date:** 2026-03-22T16:08:52
**Type:** improvement
**Tags:** vault, flight-recorder, visibility, audit, hygiene

> [!success] IMPROVEMENT
> 3 new FlightStage entries track vault access in the trading pipeline. vault_knowledge_loader now records to both vault audit log AND flight recorder. Accepts pair/cycle_id for end-to-end tracing. Vault audit log + flight recorder provide complete visibility: what knowledge was loaded, what FTS queries ran, which images matched, how long it took. Also added learnings auto-rotation (monthly log/ dirs, rolling 10 in learnings.md). Archived 63 claude-code entries to log/2026-03.md.
