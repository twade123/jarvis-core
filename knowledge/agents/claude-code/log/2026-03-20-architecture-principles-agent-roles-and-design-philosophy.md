---
type: improvement
created: 2026-03-20
tags: [architecture, agent-roles, design-philosophy, system-design, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Architecture principles: agent roles and design philosophy
**Date:** 2026-03-20T20:00:11
**Type:** improvement
**Tags:** architecture, agent-roles, design-philosophy, system-design, audit-2026-03-20-phase3

Codified the trading system architecture principles from Phase 3 audit:

**Agent roles:**
- Scout = early warning system (working well, no changes needed)
- TA = objective chart annotator — NOT an analyst, makes NO directional calls, just annotates what the chart shows
- Validator = the fisherman — synthesizes the complete story from all inputs, writes precision snipes with exact entry/invalidation/target
- Guardian = profit capture and risk management post-entry

**Timeframe hierarchy:**
- M15 = primary trading timeframe
- M1 = micro-reads for entry timing
- H4 = direction context only (not for entry decisions)

**Core principles:**
- Quality of the snipe IS the quality of the trade
- No single indicator outweighs another — it's how they combine as a complete picture
- Validator synthesizes, it doesn't analyze individual indicators in isolation

**Evidence:** Documented from Phase 3 audit discussions and root cause analysis.
