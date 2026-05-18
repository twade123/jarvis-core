---
type: correction
created: 2026-03-20
tags: [intelligence-pipeline, model-routing, cso, port-11502, briefing-quality, audit-2026-03-20-phase4]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 PHASE 4 AUDIT: Intelligence pipeline on wrong model — 9B instead of 35B CSO
**Date:** 2026-03-20T23:59:01
**Type:** correction
**Tags:** intelligence-pipeline, model-routing, cso, port-11502, briefing-quality, audit-2026-03-20-phase4

Intelligence pipeline was running on the 9B model (port 11500) instead of the 35B CSO (port 11502). Briefing quality was degraded for an unknown period. Fixed to use Qwen3.5-35B-A3B-4bit on port 11502. Also fixed: `_ensure_cso_ready()` was checking port 11500 (9B) for readiness when synthesis runs on 11502 (35B) — readiness check now points to the correct port.
