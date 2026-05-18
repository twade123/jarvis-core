---
type: improvement
created: 2026-03-18
tags: [trading, gate1, retracement, validator, scout, pipeline]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Gate 1 stripped to lightweight sanity check — was blocking all RETRACEMENT cycles
**Date:** 2026-03-18T15:02:17
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, gate1, retracement, validator, scout, pipeline

Gate 1 pre-validator confluence check was blocking all scout RETRACEMENT alerts because contracting fan scores 0/75 on Gate 1's expansion-biased scoring. Retracements are valid setups (ordered contracting fan = Phase 3 normal). Scout already pre-filters before cycles run. Old Gate 1 was a redundant second judge that used wrong criteria. Fix: replaced full confluence gate with single sanity block — only blocks cycles where fan_direction=neutral/mixed AND not a qualifying alert type (RETRACEMENT/CRITERIA_MET/scout_snipe/user_watch). Everything else reaches the validator. EUR_AUD and NZD_USD RETRACEMENT cycles were blocked for 1+ hours before fix (14:04-15:00 ET). After fix, EUR_JPY snipe #1662 BUY opened at 183.401 confirming pipeline restored.

**Evidence:** All cycles 14:04-14:58: ta_llm ran then cycle stalled (no validator_call in flight_log). Reason: Gate1 FAIL 'No active setup: fan=contracting bullish'. First post-fix trade: #1662 EUR_JPY BUY 15:00 ET.
