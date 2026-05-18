---
type: failure
created: 2026-03-21
tags: [position-guardian, scout-findings, pipeline-broken, loss-analysis, forex-trading]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## ❌ Position guardian pipeline broken: 64 trades closed March 3-20 with -295 pips, zero scout_findings created
**Date:** 2026-03-21T19:51:30
**Type:** failure
**Tags:** position-guardian, scout-findings, pipeline-broken, loss-analysis, forex-trading

> [!danger] FAILURE
> Discovered that position_guardian.py has been executing and closing trades since March 3rd but never creating scout_findings records. Result: 64 trades (27 wins +150 pips, 37 losses -445 pips = -295 pips net, 42% win rate) with no chart images, no TA data, no reasoning logged. Last scout_findings was March 2nd (all generic 'No clear opportunity'). Root cause: position_guardian.py close path missing scout_findings INSERT logic + chart capture + TA extraction. Fix needed: ~10 lines in position_guardian.py to add scout_findings creation after trade execution. Without this, system cannot learn from trades, audit failures, or improve the playbook. This is a critical data pipeline failure causing blind trading.
