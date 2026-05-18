---
title: Divergence Detection Guide — All Types with Rules
type: education
workspace: forex-trading-team
agent: validator
tags: divergence, RSI, MACD, stochastic, regular, hidden, multi-timeframe, reversal, continuation
description: Complete divergence reference — regular, hidden, multi-timeframe, with detection algorithms and trading rules
---

# Divergence Detection Guide

> Divergence is the #1 early warning system for trend reversals and the best confirmation for trend continuation. The validator should check for divergence on EVERY evaluation. S14 (regular divergence) is the highest-priority reversal signal in the setup catalog.

---

## WHAT IS DIVERGENCE?

Divergence occurs when price action and an oscillator (RSI, MACD, Stochastic) disagree about momentum. Price is doing one thing, the indicator is doing another. This disagreement signals a potential change.

---

## TYPE 1: REGULAR DIVERGENCE (Counter-Trend — Reversal Signal)

### Regular Bullish Divergence
- **Price**: Makes a LOWER LOW (new swing low below prior swing low)
- **Indicator**: Makes a HIGHER LOW (swing low is above prior swing low)
- **Meaning**: Price is making new lows but selling momentum is weakening. Sellers are losing steam.
- **Action**: Prepare for potential bullish reversal
- **Best indicators**: RSI (14), MACD histogram, Stochastic %K
- **Reliability**: HIGH at key support levels. MEDIUM in empty space.

### Regular Bearish Divergence
- **Price**: Makes a HIGHER HIGH (new swing high above prior swing high)
- **Indicator**: Makes a LOWER HIGH (swing high is below prior swing high)
- **Meaning**: Price is making new highs but buying momentum is weakening. Buyers are losing steam.
- **Action**: Prepare for potential bearish reversal
- **Reliability**: HIGH at key resistance levels.

### Detection Rules
1. Identify two swing points (highs for bearish, lows for bullish)
2. Compare price levels at those two swings
3. Compare indicator levels at those same two swings
4. If they move in opposite directions = divergence
5. **Minimum swing separation**: 5 bars (M15 = 1.25 hours). Less = noise.
6. **Maximum swing separation**: 50 bars (M15 = 12.5 hours). More = too stale.
7. **Indicator threshold**: Difference must be >5 points on RSI, >0.001 on MACD. Tiny differences are noise.

### Trading Rules for Regular Divergence
- Do NOT enter on divergence alone — wait for a confirming candle pattern (engulfing, hammer, etc.)
- Best when: divergence + candle pattern + at key S/R level
- Stop: Beyond the extreme of the divergence (the second swing point)
- Target: At least 1:2 R/R, targeting the opposing S/R level
- **CRITICAL**: In strong trends (ADX >35), regular divergence can persist for many bars. Don't fight the trend on first divergence in a strong trend — wait for ADX to start declining too.

---

## TYPE 2: HIDDEN DIVERGENCE (With-Trend — Continuation Signal)

### Hidden Bullish Divergence
- **Price**: Makes a HIGHER LOW (pullback doesn't go as deep as prior low)
- **Indicator**: Makes a LOWER LOW (indicator shows more oversold than last pullback)
- **Meaning**: Despite the indicator looking weak, the trend is stronger — buyers are stepping in earlier. The pullback is a shakeout.
- **Action**: Enter long — trend is resuming after pullback
- **This is the re-entry signal** for trades in the thesis framework

### Hidden Bearish Divergence
- **Price**: Makes a LOWER HIGH (bounce doesn't reach prior high)
- **Indicator**: Makes a HIGHER HIGH (indicator shows more overbought than last bounce)
- **Meaning**: Despite the indicator looking strong, sellers are capping earlier. The bounce is a dead cat.
- **Action**: Enter short — downtrend resuming

### Why Hidden Divergence Matters for the Thesis
- Phase 4 (retracement) → Phase 5 (re-acceleration) transition often shows hidden divergence
- Price pulls back to E55/E100 with RSI making a lower low
- But price's low is HIGHER than the pre-trend low
- This confirms: the pullback is healthy, the trend is still alive
- **This is the fishing line theory in indicator form**

### Detection Rules
1. Identify two swing lows in an uptrend (or highs in downtrend)
2. Price: second low is HIGHER than first (uptrend intact)
3. Indicator: second low is LOWER than first (appears weaker)
4. This CONTRADICTION = hidden bullish divergence
5. Same minimum/maximum separation as regular divergence

---

## TYPE 3: MULTI-TIMEFRAME DIVERGENCE (Compound Signal)

### Concept
Divergence that appears on multiple timeframes simultaneously is exponentially more reliable than single-timeframe divergence.

### Alignment Scoring
| Timeframes Showing Divergence | Reliability | Action |
|-------------------------------|-------------|--------|
| M15 only | MEDIUM | Standard divergence signal |
| M15 + H1 | HIGH | Strong signal, increase confidence |
| M15 + H1 + H4 | VERY HIGH | Near-certain reversal, maximum conviction |
| H4 only (not visible on M15 yet) | EARLY WARNING | Watch for M15 to develop same divergence |

### How to Check
1. Identify divergence on M15
2. Switch to H1 — does the same divergence pattern exist on RSI/MACD?
3. Switch to H4 — same check
4. If H4 shows divergence that M15 doesn't yet → H4 is leading, M15 will follow
5. If M15 shows divergence but H4 doesn't → M15 divergence may resolve without reversal

### Trading Multi-Timeframe Divergence
- **H4 divergence + M15 entry trigger** = highest probability setup
- Wait for M15 candle pattern at the H4 divergence zone
- Use H4's divergence for direction, M15 for timing
- This is the "zoom in for entry" technique

---

## DIVERGENCE + THESIS FRAMEWORK

### Phase-Specific Divergence Signals

| Phase | Divergence Type | What It Means | Validator Action |
|-------|----------------|---------------|-----------------|
| Phase 2 (early fan) | Regular bullish div at E100 support | Pullback sellers exhausted at E100 | HIGH confidence entry — Phase 2.5 |
| Phase 3 (expansion) | No divergence expected | Healthy trend, momentum aligned | Continue holding |
| Phase 3.5 (peaking) | Regular bearish div appearing | First warning that trend is tiring | Tighten stops, prepare for reversal |
| Phase 4 (retrace) | Hidden bullish div at E55/E100 | Trend not dead, just resting | Re-entry signal → new SNIPE |
| Phase 5 (re-accel) | No divergence | Trend has resumed | Confirmed re-entry |

### Divergence as SKIP Signal
- Regular divergence AGAINST the trade direction = strong SKIP signal
- Example: Scout finds bullish setup, but M15 shows bearish RSI divergence → validator should SKIP or reduce confidence
- Example: Watch is active for long entry, but bearish divergence develops → invalidate the watch

---

## COMMON DIVERGENCE MISTAKES

1. **Trading divergence in strong trends**: ADX >35 + regular divergence = divergence often fails. Wait for ADX to start declining.
2. **Too-close swing points**: Swings only 2-3 bars apart = not real divergence, just noise.
3. **Tiny indicator differences**: RSI at 72 vs 71 is NOT divergence. Need 5+ point difference.
4. **Ignoring the confirming candle**: Divergence without a reversal candle pattern = don't enter yet.
5. **Using lagging indicators for divergence**: RSI and MACD are best. ADX divergence is not a thing. BB divergence is not a thing.
6. **Confusing regular and hidden**: Regular = counter-trend reversal. Hidden = with-trend continuation. Mixing them up leads to trading against the trend.
