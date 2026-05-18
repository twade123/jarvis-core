---
type: correction
created: 2026-03-20
tags: [guardian, position-guardian, threat-scoring, bug-fix, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 1/7: Guardian YELLOW ceiling bug — threat score capped, RED unreachable
**Date:** 2026-03-20T14:00:00
**Type:** correction
**Tags:** guardian, position-guardian, threat-scoring, bug-fix, audit-2026-03-20

position_guardian.py score_threat() capped threat at ~44-60 for trend deterioration alone, making RED (61) unreachable without emergency conditions like margin breach or drawdown spike. The scoring formula had no time-based escalation — a trade could sit in YELLOW indefinitely losing money and never trigger RED exit.

Fixed by adding +25 time-based escalation after 10+ minutes in YELLOW with no profit. This means a stuck loser that's been YELLOW for 10min with no recovery gets pushed into RED territory, forcing exit.

**Evidence:** EUR_USD replay: scored 78 (RED) post-fix vs 53 (YELLOW) pre-fix. The 25-point escalation bridges the gap between max natural YELLOW (~55) and RED threshold (61).
