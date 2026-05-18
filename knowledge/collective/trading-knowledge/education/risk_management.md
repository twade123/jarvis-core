---
title: Risk Management — Correlation, Streaks, Drawdown, and Tail Risk
type: education
workspace: forex-trading-team
agent: validator
tags: risk, correlation, drawdown, streak, tail-risk, position-limit, exposure, hedging
description: Advanced risk management — correlation exposure, streak management, drawdown protocols, and Black Swan protection
---

# Risk Management

> Risk management is the only thing between you and a blown account. The best trade setup in the world is worthless if position sizing, correlation, and drawdown limits aren't respected.

---

## CORRELATION RISK

### What Is Correlation Risk?
Trading EUR/USD long AND GBP/USD long = you have TWO positions that move similarly. If USD strengthens, BOTH lose. This is effectively 2x the risk you intended.

### Major Forex Correlations

| Pair 1 | Pair 2 | Correlation | Why |
|--------|--------|-------------|-----|
| EUR/USD | GBP/USD | +0.80 to +0.95 | Both are "anti-USD" trades |
| EUR/USD | USD/CHF | -0.85 to -0.95 | Nearly inverse |
| AUD/USD | NZD/USD | +0.85 to +0.95 | Both commodity, both Pacific |
| USD/JPY | EUR/JPY | +0.70 to +0.85 | JPY as common denominator |
| USD/CAD | Oil (WTI) | -0.60 to -0.80 | CAD is oil-correlated |
| AUD/USD | Gold | +0.50 to +0.70 | Australia = gold producer |

### Correlation Rules for Validator
1. **Same direction on correlated pairs**: Treat as ONE position with 2x size. Reduce each to 50%.
2. **Opposite direction on correlated pairs**: These partially cancel out. Low net risk.
3. **Maximum correlated exposure**: 2 positions in same direction on pairs with >0.70 correlation
4. **Triangle risk**: EUR/USD + GBP/USD + EUR/GBP = you're trading all three sides of the triangle. Simplify to one position.

### Correlation-Adjusted Position Sizing
| Correlation | Max Combined Size |
|------------|------------------|
| >0.90 | 100% (treat as single position) |
| 0.70-0.90 | 130% (slight diversification benefit) |
| 0.40-0.70 | 160% (moderate diversification) |
| <0.40 | 200% (truly independent positions) |

---

## DRAWDOWN MANAGEMENT

### Drawdown Levels and Actions

| Drawdown | Classification | Action |
|----------|---------------|--------|
| 0-3% | Normal | Continue trading normally |
| 3-5% | Elevated | Reduce position sizes to 75% |
| 5-7% | Warning | Reduce to 50%. Only high-confidence setups. |
| 7-10% | Critical | Reduce to 25%. Only TRADE_NOW with conf 8+. |
| >10% | Maximum | **STOP ALL TRADING.** Full strategy review. |

### Recovery Protocol (After Max Drawdown)
1. Stop trading for minimum 24 hours (one full session cycle)
2. Review last 10 trades for pattern (was it correlation? sizing? overtrading?)
3. Identify if regime changed and strategy didn't adapt
4. Resume with 25% position sizes for first 5 trades
5. If 3 of 5 are profitable, increase to 50%
6. If another 3 of 5 profitable, return to normal sizing
7. If drawdown continues, the strategy may need revision — not just the sizing

### Daily/Weekly Limits

| Limit | Value | Consequence |
|-------|-------|-------------|
| Max daily loss | 3% | Stop trading for the day |
| Max daily trades | 5 | No new entries (prevents overtrading) |
| Max weekly loss | 5% | 50% size for rest of week |
| Max monthly loss | 8% | 25% size, review strategy |
| Max open positions | 3 | No new entries until one closes |

---

## STREAK MANAGEMENT

### Losing Streak Protocol

| Consecutive Losses | Action |
|-------------------|--------|
| 1-2 | Normal. Every strategy has losses. Continue. |
| 3 | Reduce size to 75%. Review last 3 trades — was there a common mistake? |
| 4 | Reduce to 50%. Are you in the wrong regime? |
| 5 | **STOP.** Something is wrong. Don't trade until you identify the problem. |
| 5+ | Full strategy audit. Check: regime mismatch, correlation stacking, news-related, overtrading |

### Winning Streak Protocol

| Consecutive Wins | Action |
|-----------------|--------|
| 1-3 | Normal. Good trading. |
| 4-5 | Maintain size. Do NOT increase. Overconfidence is the enemy. |
| 6+ | Actually slightly reduce size. Mean reversion applies to streaks too. The "hot hand" doesn't exist in trading. |

### The Tilt Rule
- After any emotionally significant trade (big win or big loss), take a 30-minute break before next entry
- After 2 consecutive "revenge trades" (entering immediately after a loss to "make it back"), STOP for the day
- The validator should flag if it detects rapid-fire entries with declining quality (possible tilt behavior)

---

## TAIL RISK PROTECTION

### What Is Tail Risk?
Extreme, unexpected events that cause 200+ pip moves in minutes:
- Central bank surprise decisions
- Flash crashes (May 2010, Jan 2019 JPY flash crash)
- Geopolitical shocks (wars, natural disasters, elections)
- SNB removing EUR/CHF floor (Jan 2015 — 3000 pip move in minutes)

### Protection Strategies
1. **Always have a stop-loss**: No exceptions. "Mental stops" don't work in flash crashes.
2. **Use guaranteed stops if available**: Some brokers offer guaranteed stop-loss orders (GSLO) for a premium. Worth it for overnight positions.
3. **Maximum overnight exposure**: Never hold more than 2% risk overnight (gaps can't be stopped in real-time)
4. **Weekend exposure**: Reduce to 1% risk over weekends, or close all positions
5. **Pre-event flatten**: Before major scheduled events (FOMC, BOJ, elections), flatten or reduce to minimum
6. **Diversification**: Don't put all risk in one currency. If all positions are USD-related, one shock wipes everything.

### Black Swan Pairs (Higher Tail Risk)
- **USD/JPY**: BOJ intervention risk. Can move 500+ pips in minutes.
- **EUR/CHF**: SNB intervention history. Normally low vol, but tail risk is extreme.
- **GBP pairs**: Brexit-style political shocks. GBP can move 300+ pips on political events.
- **Emerging market pairs**: USD/TRY, USD/ZAR — extreme tail risk, avoid unless specialized.

---

## RISK-REWARD ASSESSMENT

### Minimum R/R Requirements

| Setup Type | Minimum R/R | Why |
|-----------|-------------|-----|
| Trend continuation | 1:1.5 | Higher win rate compensates for lower R/R |
| Trend reversal | 1:2.0 | Lower win rate needs higher R/R |
| Range trade | 1:1.0 | High win rate at boundaries, small targets |
| Breakout | 1:2.0 | Fakeout risk needs compensation |
| Counter-trend | 1:3.0 | Lowest probability, needs biggest payoff |

### R/R Check Before Entry
1. Calculate SL distance (ATR-based or structure-based)
2. Calculate TP distance (next S/R, Fib extension, or ATR multiple)
3. If TP/SL < minimum R/R for that setup type → SKIP
4. If there's a major S/R level between entry and TP → TP must be beyond it or SKIP

### The "Room to Run" Rule
- Before entering, check: is there a major obstacle between entry and target?
- If entry is at 1.0850 with TP at 1.0900 but major resistance at 1.0870 → only 20 pips of room, not 50
- Adjust TP to the obstacle or SKIP if R/R becomes unfavorable
- The validator must include this in reasoning: "Target has X pips of clear runway"

---

## VALIDATOR RISK CHECKLIST

Before issuing any TRADE_NOW verdict:
1. Is total account risk (including existing positions) under 5%?
2. Are there correlated positions already open? Adjust size accordingly.
3. Is there a major news event within 2 hours?
4. Is the pair appropriate for the current session?
5. Is R/R above minimum threshold for this setup type?
6. Is the current streak within acceptable bounds?
7. Has daily loss limit been approached?
8. Is there clear "room to run" to the target?
