---
title: Position Management — Scaling, Trailing, Exits
type: education
workspace: forex-trading-team
agent: validator
tags: position-sizing, trailing-stop, partial-profit, scaling, breakeven, exits, risk-reward
description: Complete position management — scaling in/out, trailing stop mechanics, partial profits, breakeven rules, and when to add to winners
---

# Position Management

> Position management is where profits are made or lost. The entry is the easy part — managing the trade afterward is what separates winners from losers.

---

## POSITION SIZING

### Fixed Fractional (Standard)
- Risk 1-2% of account per trade
- Formula: `Position size = (Account * Risk%) / (SL in pips * pip value)`
- Example: $<amount> account, 1% risk, 25 pip SL, EUR/USD ($10/pip standard lot)
  - Size = ($<amount> * 0.01) / (25 * $10) = 0.4 lots

### ATR-Based Sizing
- Normalize risk across different volatility pairs
- SL = 1.5-2.5x ATR(14)
- Higher ATR = smaller position to maintain same dollar risk
- This ensures GBP/JPY (high ATR) and EUR/CHF (low ATR) have equal dollar risk

### Confidence-Based Sizing
| Validator Confidence | Position Size |
|---------------------|---------------|
| 8-10 (TRADE_NOW) | 100% of calculated size |
| 7 (strong TRADE) | 75% |
| 6 (moderate) | 50% |
| 5 (marginal) | 25% or SKIP |
| <5 | SKIP — do not trade |

### Streak-Based Adjustment
| Streak | Adjustment |
|--------|-----------|
| 3+ consecutive wins | Maintain size (don't get overconfident) |
| 2 consecutive losses | Reduce to 75% size |
| 3 consecutive losses | Reduce to 50% size |
| 5+ consecutive losses | STOP trading. Review strategy. Reduce to 25% when resuming. |

---

## STOP-LOSS PLACEMENT

### ATR-Based Stop (Primary Method)
- **Standard**: SL = 2.0x ATR below entry (long) or above (short)
- **Tight**: SL = 1.5x ATR (for high-confidence setups at key levels)
- **Wide**: SL = 2.5x ATR (for volatile pairs or news-adjacent entries)
- **Never tighter than**: Spread + 5 pips (to avoid being stopped by normal noise)

### Structure-Based Stop
- Below the swing low that triggered the entry (long)
- Above the swing high that triggered the entry (short)
- Below the E100 level if entering on E100 retest (the thesis invalidation level)

### The "Never Move Stop Against Trade" Rule
- Once placed, stops only move in the direction of profit
- Moving a stop further away to "give it room" = adding risk = bad habit
- If the original stop placement was wrong, exit manually and re-evaluate

---

## TAKE-PROFIT STRATEGIES

### Fixed R/R (Simple)
- **1:1 R/R**: Partial exit (25-50% of position) — lock in some profit
- **1:2 R/R**: Standard target. Risk 25 pips, target 50 pips.
- **1:3 R/R**: Aggressive target for strong trend setups. Partial at 1:2, let rest run.

### ATR-Based Targets
| Target Type | Calculation | When to Use |
|------------|-------------|-------------|
| Quick | 1.0x ATR | Scalp/range trade |
| Standard | 1.5-2.0x ATR | Normal trend trade |
| Swing | 3.0x ATR | Strong thesis alignment, multi-TF |
| Runner | No fixed target, trailing stop | Phase 3 expansion, let it run |

### S/R Based Targets
- Set TP at next significant S/R level
- If S/R is closer than 1:1 R/R → don't take the trade (not enough room)
- Fibonacci extensions (127.2%, 161.8%) as targets when no clear S/R

---

## PARTIAL PROFIT TAKING

### The 25-25-25-25 Method
1. **At +1R**: Close 25% of position. Move stop to breakeven.
2. **At +2R**: Close another 25%. Trail stop to +1R.
3. **At +3R**: Close another 25%. Trail stop to +2R.
4. **Runner**: Let final 25% ride with trailing stop.

### The 50-50 Method (Simpler)
1. **At 1:1 R/R**: Close 50%. Move stop to breakeven.
2. **Runner**: Let remaining 50% ride with trailing stop.
- This is the current thesis system's approach (referenced in setup_knowledge.md)

### Why Partial Profits Matter
- Locks in guaranteed profit regardless of what happens next
- Reduces psychological pressure (you're already winning)
- Allows "runner" portion to capture big moves without anxiety
- Even if runner gets stopped at breakeven, you banked the partial

---

## TRAILING STOP MECHANICS

### EMA-Based Trailing (Thesis System)
| Phase | Trail Behind | Buffer |
|-------|-------------|--------|
| Phase 3 (expansion) | E21 | ±3 pips |
| Phase 4 (retrace) | E55 | ±5 pips |
| Deep retrace | E100 | ±8 pips |

- **How it works**: As the trend progresses, EMAs follow price. Trailing stop follows the EMA.
- **Update frequency**: Every M15 candle close
- **Key rule**: Only move trail in profit direction. If EMA pulls back, keep trail at highest point.

### ATR-Based Trailing
- Trail = Current price - (ATR * multiplier)
- **Tight trail**: 1.5x ATR (for quick moves)
- **Standard trail**: 2.0x ATR (normal trending)
- **Wide trail**: 3.0x ATR (letting big moves develop)

### Chandelier Stop (Advanced)
- Trail from the highest high (long) or lowest low (short) since entry
- Chandelier = Highest High - (ATR * 3.0)
- Good for: Letting trends run while protecting against sudden reversals
- Better than fixed pip trailing because it adapts to volatility

### When to Switch Trail Methods
1. **Entry → First partial**: Use fixed ATR stop (no trailing yet)
2. **After first partial (breakeven)**: Start EMA-based trailing
3. **In strong Phase 3 expansion**: Switch to E21 trailing (tight)
4. **If momentum slows**: Switch to E55 trailing (wider, more room)

---

## BREAKEVEN STOP

### When to Move to Breakeven
- After first partial profit taken (50% or 25% of position)
- OR when price has moved 1.5x ATR in favor
- Whichever comes first

### The +1 Pip Rule
- Move stop to entry price + 1 pip (not exactly breakeven)
- This accounts for spread and ensures net positive if stopped
- For pairs with wider spreads, use +2-3 pips

### Don't Move to Breakeven Too Early
- Moving to BE before 1R profit risks getting stopped by normal pullbacks
- The thesis framework expects Phase 2.5 retracements — if BE stop is too tight, you'll be stopped during the retracement that IS the entry
- Rule: Only move to BE AFTER the trade has shown clear momentum in your direction

---

## SCALING INTO WINNERS (Adding to Positions)

### When to Add
- Original position is profitable (moved at least 1R in favor)
- Thesis is strengthening (fan still separating, BB still expanding)
- Higher timeframe confirms continuation
- NOT after a long move — add during pullbacks within the trend

### How to Add
- Add at Phase 5 (re-acceleration after retrace) with a new stop at the retrace low
- Add size = 50% of original position (never bigger than original)
- New stop for the add is at the retrace low
- Original position keeps its existing trail

### When NOT to Add
- After 3+ ATR move without pullback (overextended)
- When ADX is declining (trend weakening)
- When BB is contracting (expansion phase over)
- When there's divergence against the trade direction
- Near end of session (3 PM+ EST)

---

## EXIT SIGNALS (When to Close Everything)

### Mandatory Exits
1. Stop-loss hit (automatic)
2. Take-profit hit (automatic)
3. Opposite thesis signal (fan reversal, new cross against you)
4. Strong bearish/bullish divergence on H1+ against your trade
5. Major news event in 30 minutes (flatten or set tight trail)
6. Friday 3 PM EST (close or set weekend-tight stops)

### Warning Exits (Reduce Position)
1. Fan velocity declining for 3+ bars
2. BB contracting after expansion (Phase 3 → Phase 3.5 transition)
3. ADX starts declining from >30
4. Counter-trend candle larger than any recent trend candle
5. Price stalls at major S/R level for 5+ bars

---

## DAILY RISK LIMITS

| Limit | Value | Action When Hit |
|-------|-------|----------------|
| Max daily loss | 3% of account | Stop trading for the day |
| Max weekly loss | 5% of account | Reduce size to 50% for rest of week |
| Max drawdown | 10% of account | Stop trading. Full strategy review. |
| Max concurrent positions | 3 (or 2 if correlated pairs) | No new entries until one closes |
| Max correlated exposure | 2 positions in same direction on correlated pairs | Reduce second position to 50% |
