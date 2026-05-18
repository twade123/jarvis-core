---
type: note
created: 2026-03-21
tags: [openclaw, sync, session-log]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 [OpenClaw sync] # 2026-03-18 Session Log
**Date:** 2026-03-21T19:51:33
**Type:** note
**Tags:** openclaw, sync, session-log

> [!info] NOTE
> Synced from OpenClaw daily log: 2026-03-18.md
> 
> # 2026-03-18 Session Log
> 
> ## Morning Session (~6:55 AM – 11:17 AM ET)
> 
> ### Context
> Full audit of overnight losses (-$53.09, 22 trades, 55% WR, 0.37 R:R). Spent the session diagnosing and fixing root causes.
> 
> ---
> 
> ### Bugs Fixed
> 
> **Ghost trade tab** (`trading_api_routes.py` + `dashboard/index.html`)
> - OANDA returning 200+empty (trade closed) was falling into stale cache fallback, serving closed trade as still-open
> - Frontend init restored tabs from localStorage before live fetch completed
> - Fix: `oanda_call_succeeded` flag, provisional tab system with prune on live fetch
> 
> **Blank validator charts** (`chart_generator.py`)
> - OANDA sometimes returns candles newest-first; chart_generator expected ascending order
> - EMA/BB calculated on reversed data → only BB envelope visible, no candles
> - Fix: `df.sort_values('time').reset_index()` before `calculate_indicators()`
> - Threshold raised 5KB→50KB for broken chart detection in trading_cycle.py
> - No-chart validator behavior changed from auto-SKIP to evaluate-from-TA
> 
> **Stale annotation contamination** (`agents/trading_cycle.py`)
> - EUR_USD annotations from March 12 (6 days old) were being injected into every EUR_USD cycle
> - Validator built entire analysis around week-old markup
> - Fix: 48h expiry filter on annotation queries; auto-expire UPDATE on query; clean scout cycles get zero annotations; snipe_id FK added
> 
> **Stale bar_time blanking charts** (`chart_generator.py`)
> - Annotation with `bar_time` from 6 days before chart window → `idxmin()` returned bar 0 → arrowprops corrupted axes y-limits → all candles invisible
> - Fix: bounds check before resolving bar index; out-of-window timestamps fall back to right edge
> 
> **Execution agent silent failure** (`agents/trading_cycle.py`)
> - LLM execution agent responded in prose ("I'll place the market order") instead of calling tool
> - Result: `status=filled` but `trade_id=None` — no trade placed, dashboard showed ghost
> - Fix: replaced entire LLM execution agent path with direct `place_market_o
> 
> ... (truncated)
