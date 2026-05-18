---
type: correction
created: 2026-03-23
tags: [validator, json-format, prose-only, retry, prompt]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed validator prose-only first response: added JSON-only suffix to task string + strengthened prompt
**Date:** 2026-03-23T09:58:06
**Type:** correction
**Tags:** validator, json-format, prose-only, retry, prompt

> [!warning] CORRECTION
> Root cause: After tool calls (get_upcoming_news, validate_trade_setup, get_loss_patterns), the validator LLM 'thinks out loud' (e.g. 'Good data. Now I have what I need. Let me issue my...') instead of returning JSON. The JSON format instruction at line 613 of prompt.md gets lost in the 92K char context. Fix: (1) Added RESPONSE FORMAT section at END of task string in trading_cycle.py — the last thing the LLM reads before responding. Explicitly says 'no prose, no thinking, just JSON code block.' (2) Strengthened prompt.md output format section: 'No thinking out loud. No Good data now let me... Just the JSON.' This should eliminate the ~50% first-attempt prose-only failure that was forcing expensive retries.
