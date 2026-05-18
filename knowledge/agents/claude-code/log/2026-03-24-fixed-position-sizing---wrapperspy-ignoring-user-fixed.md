---
type: correction
created: 2026-03-24
tags: [position_sizing, wrappers, risk_config, core_db, trading_preferences]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed position sizing - wrappers.py ignoring user fixed-units preference, always using auto mode
**Date:** 2026-03-24T20:50:23
**Type:** correction
**Tags:** position_sizing, wrappers, risk_config, core_db, trading_preferences

> [!warning] CORRECTION
> EUR/JPY opened at 0.04 per pip (713 units) instead of 1 per pip. Root cause: make_trade_decision() in wrappers.py loaded only risk_limits into limits dict, never position_sizing config or user DB preferences. limits.get position_sizing_mode auto always returned auto triggering risk-based calc producing tiny units. Fix: merges position_sizing from risk_config.json AND reads user DB overrides from trading_preferences in core.db. User DB takes priority so UI changes are respected immediately.
