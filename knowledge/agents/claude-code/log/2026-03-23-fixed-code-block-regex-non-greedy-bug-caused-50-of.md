---
type: correction
created: 2026-03-23
tags: [regex, non-greedy, retry, watch-manifest, root-cause, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed: code block regex non-greedy bug caused 50% of validator retries + watch_manifest now stored
**Date:** 2026-03-23T11:52:45
**Type:** correction
**Tags:** regex, non-greedy, retry, watch-manifest, root-cause, CRITICAL

> [!warning] CORRECTION
> Three fixes: (1) JSON code block regex was non-greedy (.*?) which stopped at FIRST closing brace — a validator response like {"verdict":"SKIP",...,"checklist":{...},"re_entry_conditions":[...]} would only capture up to the first }. Changed to greedy (.*) to match entire JSON block. This was the ROOT CAUSE of ~50% retry rate — first attempt had valid JSON in code block but regex truncated it to 4 keys, triggering 'prose-only' retry. (2) watch_manifest, watch_trigger, watch_for, confidence_trajectory now stored in _watch_context passed to create_watch. Were being parsed by validator but dropped. (3) max_tokens increased from 2500 to 4096.
