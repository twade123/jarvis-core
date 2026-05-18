---
type: correction
created: 2026-03-23
tags: [validator, watch-manifest, fishing-line, predictive, depth]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Added watch_manifest to validator task string — activates fishing line theory, trajectory assessment, progress tracking
**Date:** 2026-03-23T11:27:58
**Type:** correction
**Tags:** validator, watch-manifest, fishing-line, predictive, depth

> [!warning] CORRECTION
> The validator prompt (lines 705-767) defines a detailed watch_manifest framework: fishing_line (entry zone, direction, time limit), trigger_conditions (with progress_pct 0-100), invalidation_conditions, trajectory_assessment (velocity building/degrading, death_flags), confidence_trend. The prompt says 'watch_manifest is MANDATORY when verdict is WATCH.' But the task string never requested it in the JSON output — so the validator never produced it. Added watch_manifest, estimated_candles_to_entry, price_target_entry to the requested JSON fields. Also added 'predict what happens next using fishing line theory' to the reasoning instruction. This should activate the full predictive depth that makes chart submissions so detailed.
