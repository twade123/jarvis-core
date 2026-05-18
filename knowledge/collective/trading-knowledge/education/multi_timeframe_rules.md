---
title: Multi-Timeframe Analysis Rules
type: education
workspace: forex-trading-team
agent: validator
tags: multi-timeframe, M15, H1, H4, alignment, confirmation, entry, bias
description: How M15, H1, and H4 timeframes work together — alignment scoring, entry rules, and when timeframes disagree
---

# Multi-Timeframe Analysis Rules

> M15 is the execution timeframe. H1 is the confirmation timeframe. H4 is the bias timeframe. Never take an M15 trade that contradicts the H4 bias without exceptional reason.

---

## THE HIERARCHY

| Timeframe | Role | What It Tells You | How Often Checked |
|-----------|------|-------------------|-------------------|
| **H4** | Strategic bias | Overall trend direction, major S/R levels, regime | Every 4 hours / start of session |
| **H1** | Tactical confirmation | Trend health, divergence, pattern development | Every hour / before entry |
| **M15** | Execution timing | Precise entry/exit, candle patterns, immediate momentum | Continuous during trading |

---

## ALIGNMENT SCORING

### Full Alignment (Score: 10/10 — Maximum Confidence)
- H4: Trend direction clear (ADX >25, EMAs ordered)
- H1: Same direction, trend accelerating
- M15: Entry signal (candle pattern, EMA cross, thesis trigger)
- **Action**: Full position size. This is the highest probability setup.

### Partial Alignment (Score: 6-8/10 — Trade with Caution)
- H4: Trend direction clear
- H1: Mixed signals (ranging, early reversal signs)
- M15: Entry signal present
- **Action**: Reduced position size (50-75%). Tighter stop.

### Misalignment (Score: 3-5/10 — Counter-Trend)
- H4: One direction
- M15: Signal in opposite direction
- **Action**: SKIP unless M15 + H1 both show strong divergence against H4 (potential H4 reversal). If taking counter-trend, minimum position size (25%).

### No Trend (Score: 0-2/10 — Ranging)
- H4: ADX <20, BB flat, EMAs tangled
- **Action**: Range trading only (buy support, sell resistance) or SKIP entirely.

---

## PRACTICAL RULES

### Rule 1: H4 Sets the Direction
- Before any M15 analysis, check H4 first
- H4 bullish (EMAs ordered up, ADX >20) → only look for BUY setups on M15
- H4 bearish → only look for SELL setups
- H4 ranging → trade the range or skip

### Rule 2: H1 Confirms Timing
- H4 is bullish, but H1 is in pullback → wait for H1 to resume upward
- H4 is bullish and H1 is also bullish → good timing window
- H4 is bullish but H1 shows bearish divergence → potential reversal, be cautious

### Rule 3: M15 Executes
- Only enter on M15 when H4 direction + H1 confirmation are aligned
- M15 candle pattern + thesis trigger = precise entry
- M15 stop placement (ATR-based) keeps risk tight

### Rule 4: Timeframe Disagreement = Reduce Size
- Each timeframe that disagrees reduces position by 25%
- All three agree: 100% position
- Two agree, one disagrees: 75% position
- Only M15 agrees: 50% maximum, consider SKIP

### Rule 5: Higher Timeframe Trumps Lower
- M15 gives buy signal but H4 is in strong downtrend → SKIP the buy
- Exception: M15 + H1 both show strong bullish divergence against H4 bearish → H4 may be reversing. WATCH, don't trade yet.

---

## THESIS FRAMEWORK ACROSS TIMEFRAMES

### How Fan Expansion Looks on Each Timeframe

| Aspect | H4 | H1 | M15 |
|--------|-----|-----|------|
| Fan developing | Very early stages visible | Fan clearly separating | Fully visible with velocity |
| Best entry signal | Too slow for precise entry | Good for swing entries | Ideal for precise timing |
| E100 retest | Major structural level | Important support/resistance | Exact entry point |
| BB expansion | Slow but significant | Clear expansion visible | Real-time expansion tracking |

### The Ideal Multi-Timeframe Thesis Setup
1. **H4**: E21 crossed E55 within last 20 bars. Fan starting to separate. ADX rising above 20.
2. **H1**: Fan clearly ordered. BB expanding. No bearish divergence.
3. **M15**: Price pulling back to E55/E100 (Phase 2.5). Bullish candle at E100. Entry.

This is the highest probability entry in the entire system.

---

## LIQUIDITY CASCADE

When all three timeframes align in the same direction at the same time, a "liquidity cascade" occurs:
- M15 traders enter → price moves
- H1 breakout triggers → more traders enter → price accelerates
- H4 confirms new trend → institutional money flows in → powerful sustained move

**This is where 100+ pip moves come from.** The validator should recognize when a setup has cascade potential:
- All timeframes trending same direction
- Major S/R level just broken on H1/H4
- BB expanding on all timeframes
- Volume increasing (if available)
- News catalyst aligning

---

## SESSION-TIMEFRAME INTERACTION

| Session | Best Timeframe Approach |
|---------|----------------------|
| Asian (low vol) | H4 for direction, M15 for range trades only |
| London open | H1 for breakout confirmation, M15 for entry timing |
| London-NY overlap | All timeframes active. Best window for multi-TF alignment trades |
| NY afternoon | H4 for position management, reduce new entries |
| Friday after 3PM | No new entries regardless of timeframe alignment |
