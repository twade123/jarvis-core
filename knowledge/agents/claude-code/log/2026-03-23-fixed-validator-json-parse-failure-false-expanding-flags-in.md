---
type: correction
created: 2026-03-23
tags: [validator, json-parse, confluence, expanding-flags, gate1]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed validator JSON parse failure + false expanding flags in confluence scorer
**Date:** 2026-03-23T08:34:52
**Type:** correction
**Tags:** validator, json-parse, confluence, expanding-flags, gate1

> [!warning] CORRECTION
> Two fixes: (1) trading_cycle.py validator response parser now tries json.loads(resp_text) FIRST before code-block regex and bracket-counting. _call_unified_validator returns json.dumps(dict) which is valid JSON — the old parser skipped direct parse and failed on bracket counting. (2) full_confluence_scorer.py now cross-checks fan_state and bb_expanding against scout delta values. ema_separation.py reports 'expanding' with loose threshold (0.005 raw) while scout uses percentage-of-price. If fan_state='expanding' but scout fan_delta_5bar<=0, overrides to 'stable'. If bb_expanding=true but bb_delta_5bar<=0, overrides to false. Prevents false Gate1 passes on stalled setups.
