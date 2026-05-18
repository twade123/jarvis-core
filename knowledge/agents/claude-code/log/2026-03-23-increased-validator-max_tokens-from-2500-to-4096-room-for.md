---
type: improvement
created: 2026-03-23
tags: [validator, max-tokens, watch-manifest, token-budget]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Increased validator max_tokens from 2500 to 4096 — room for watch_manifest + full fishing line analysis
**Date:** 2026-03-23T11:43:00
**Type:** improvement
**Tags:** validator, max-tokens, watch-manifest, token-budget

> [!success] IMPROVEMENT
> The validator was producing detailed chart reads and 7-condition snipes but NOT the watch_manifest (fishing_line, trigger_conditions with progress_pct, invalidation_conditions, trajectory_assessment). Root cause: max_tokens=2500 on the _agent_task call was too small for the full JSON including reasoning + re_entry_conditions + watch_manifest. The watch_manifest alone needs 500+ tokens. Increased to 4096 across all three _agent_task('validator') calls. This gives the validator room for the complete predictive framework the prompt defines.
