---
type: correction
created: 2026-03-23
tags: [intelligence, cache, encoding, fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed intelligence cache double-encoding: set_cached() already json.dumps, callers must not pre-encode
**Date:** 2026-03-23T07:58:09
**Type:** correction
**Tags:** intelligence, cache, encoding, fix

> [!warning] CORRECTION
> intelligence_agent_prep.py was passing json.dumps(data) to set_cached() which also calls json.dumps(data). Triple-encoded briefings, double-encoded wolfram keys. FX range data (price, 1yr min/max) was completely lost because _extract_fx_range regex couldn't match inside JSON string. Fixed by passing raw dicts/strings. Also added news bridge keys (news:{PAIR}) so gather_intelligence(cache_only=True) gets news data.
