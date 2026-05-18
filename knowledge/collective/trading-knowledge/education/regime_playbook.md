---
title: Regime Playbook — Trading Rules Per Market Regime
type: education
workspace: forex-trading-team
agent: validator
tags: regime, ADX, trending, ranging, compression, exhaustion, squeeze, breakout, fakeout
description: Specific trading rules for each market regime — what works, what doesn't, and how to detect regime transitions
---

# Regime Playbook

> ADX is the master switch. Every strategy has a regime it thrives in and a regime it dies in. The validator must identify the regime FIRST, then select appropriate setups.

---

## REGIME DETECTION

### ADX-Based Classification

| ADX Reading | Regime | Trend Health |
|-------------|--------|-------------|
| **<15** | Compression/Squeeze | No trend. BB tight. EMAs tangled. |
| **15-20** | Weak/Forming | Trend may be starting. Cautious positioning. |
| **20-25** | Moderate Trend | Clear direction. Standard strategies viable. |
| **25-35** | Strong Trend | Full confidence trend-following. |
| **35-50** | Very Strong Trend | Extended move. Watch for exhaustion. |
| **>50** | Extreme/Parabolic | Rare. Likely near blow-off top/bottom. |

### ADX Direction Matters
- **ADX rising**: Trend STRENGTHENING (even if price is pulling back)
- **ADX falling from >30**: Trend WEAKENING (even if price still moving in trend direction)
- **ADX falling below 20**: Trend has ENDED. Switch to range strategies.

---

## REGIME 1: STRONG TREND (ADX 25-50)

### Characteristics
- EMAs clearly ordered (fan expanding)
- BB expanding, price walking the outer band
- RSI staying overbought/oversold for extended periods
- Pullbacks are shallow (38.2% Fib or less)
- Clear higher highs/higher lows (or lower lows/lower highs)

### What Works
- **Thesis entry (Phase 2.5 E100 retest)** → PRIMARY strategy
- **Flag/pennant continuation** → enter on breakout in trend direction
- **Hidden divergence re-entry** → pullback + hidden div = re-enter with trend
- **EMA bounce entries** → price touches E21/E55, bounces, continue
- **Setups**: S3 (SAR+EMA), S5/S9 (EMA trend+MACD), S11 (SMA+MACD), S15 (hidden div)

### What FAILS
- **Mean reversion** → price will "walk the band" and not revert
- **Fading RSI overbought/oversold** → RSI can stay extreme for 50+ bars in strong trends
- **Counter-trend patterns** → regular divergence often fails or takes many bars to play out
- **Range trading** → support breaks in trends, not bounces
- **Setups to AVOID**: S5/S6 (BB+Stoch range), S13 (Stoch range)

### Validator Rules
- TRADE_NOW with high confidence for trend-following setups
- SKIP all counter-trend signals unless H4 also shows reversal
- Regular divergence = WATCH, not TRADE (it might take 10+ bars to materialize)
- Full position size

---

## REGIME 2: WEAK/FORMING TREND (ADX 15-25)

### Characteristics
- EMAs starting to separate but not fully ordered
- BB beginning to expand from squeeze
- Directional bias emerging but not confirmed
- Pullbacks deeper (50-61.8% Fib)
- Higher risk of false starts

### What Works
- **Early thesis entry** → E21 just crossed E55, watching for fan development
- **Breakout anticipation** → compression resolving into direction
- **Momentum confirmation** → MACD crossing zero line, RSI breaking 50
- **Setups**: S2 (MACD+RSI), S7 (MACD+RSI extreme), S12 (BB squeeze)

### What FAILS
- **Aggressive trend-following** → trend not confirmed yet, whipsaws likely
- **Tight stops** → price is choppy, needs room
- **Full position sizing** → premature

### Validator Rules
- WATCH is the default verdict here — setup is forming but not confirmed
- TRADE only with reduced size (50-75%)
- Wider stops (2.5x ATR instead of 2.0x)
- If fan doesn't confirm within 15-25 bars, SKIP

---

## REGIME 3: RANGING (ADX <20, Not Squeezing)

### Characteristics
- BB flat/horizontal
- EMAs tangled, no clear order
- Price bouncing between support and resistance
- RSI oscillating between 30-70
- No directional commitment

### What Works
- **Buy at support, sell at resistance** → classic range trading
- **BB band bounce** → price at lower BB + oversold = buy, upper BB + overbought = sell
- **Stochastic crossover at extremes** → buy when %K crosses above %D below 20
- **Setups**: S1 (BB+Stoch), S4 (SAR+Stoch), S6 (BB+Stoch sell), S13 (Stoch range)

### What FAILS
- **Trend-following** → no trend to follow
- **Breakout entries** → fakeouts dominate in ranges
- **Thesis system** → fan won't expand in a range
- **MACD crossovers** → whipsaw around zero line

### Validator Rules
- SKIP all thesis/trend setups
- Only trade if at clear range boundary (support or resistance)
- Stop beyond the range boundary (if support breaks, exit)
- Target: opposite boundary of the range
- **CRITICAL**: If range has been in place 100+ bars, a breakout is coming. Switch to breakout anticipation.

### Detecting Range Boundaries
- 3+ touches of the same level = confirmed S/R
- Higher timeframe (H1/H4) S/R levels are more significant
- Round numbers (1.0800, 1.0900) act as psychological S/R

---

## REGIME 4: TREND EXHAUSTION (ADX Declining from >30)

### Characteristics
- ADX WAS above 30 but is now falling
- Price still moving in trend direction but momentum fading
- Regular divergence appearing on RSI/MACD
- BB may still be wide but starting to contract
- Candle bodies getting smaller, wicks getting longer

### What Works
- **Divergence reversal entries** → S14 (regular divergence) is the #1 signal here
- **Counter-trend at key levels** → if price reaches major S/R with divergence, trade the reversal
- **Tighten existing trade stops** → protect profits, the move is ending
- **Setups**: S9/S10 (bearish divergence), S14 (momentum divergence), S18 (RSI div+BB)

### What FAILS
- **Adding to trend positions** → trend is dying, don't add fuel
- **Ignoring divergence** → divergence in exhaustion is meaningful (unlike in strong trend)
- **Wide stops** → should be tightening, not widening

### Validator Rules
- SKIP new trend entries
- WATCH for reversal setups (divergence + candle pattern at S/R)
- Existing positions: tighten trail to E21 ± 3 pips
- Confidence for counter-trend: 5-6 (moderate, not high)
- Wait for ADX to drop below 25 before confirming trend is dead

---

## REGIME 5: COMPRESSION / SQUEEZE (ADX <15, BB Contracting)

### Characteristics
- BB width at multi-bar low (squeeze)
- ADX below 15 and flat
- EMAs converging to a single point
- Price making smaller and smaller ranges
- Energy building for explosive move

### What Works
- **Breakout anticipation** → position for the explosive move
- **Symmetrical triangle breakout** → trade the direction of the break
- **Volatility expansion setup** → BB squeeze + ADX turning up = explosion imminent
- **Setups**: S12 (BB squeeze), S17 (triangle breakout)

### What FAILS
- **Everything until the break happens** → don't trade inside the squeeze
- **Predicting direction** → let the market tell you
- **Tight targets** → the move after a long squeeze is usually very large

### How to Trade the Squeeze
1. **Identify**: BB width reaches lowest in 50+ bars. ADX <15.
2. **Wait**: Do NOT enter inside the squeeze.
3. **Break**: Price closes outside BB with expanding width. ADX starts turning up.
4. **Direction bias**: If there was a trend before the squeeze, breakout likely continues in same direction (60-65%).
5. **Entry**: Enter on the breakout candle close. Stop on opposite side of squeeze.
6. **Target**: 2-3x the height of the squeeze range. These are big moves.

### Validator Rules
- SKIP all setups inside the squeeze
- WATCH for breakout conditions
- Once break happens: TRADE_NOW with high confidence if direction aligns with prior trend
- If break is counter-trend: still TRADE but reduced size (60%)

---

## REGIME TRANSITIONS

### Compression → Trend (Most Common Profitable Setup)
- BB squeeze breaks → ADX rises above 20 → fan starts forming
- This IS the thesis setup. Phase 0 → Phase 1 → Phase 2.
- Validator: Highest priority WATCH → TRADE transition

### Trend → Exhaustion
- ADX peaks and starts declining. Divergence appears.
- Validator: Tighten existing trades. Prepare for reversal or range.

### Exhaustion → Range
- ADX drops below 20. Price settles into a range.
- Validator: Switch to range strategies. SKIP trend entries.

### Range → Compression → New Trend
- Range narrows into squeeze. Then breaks into new trend.
- This is the cycle: Trend → Exhaustion → Range → Compression → New Trend.
- The validator that understands this cycle anticipates what's coming next.

<!-- merged from collective/trading-knowledge/education/indicator_mastery.md -->
title: Indicator Mastery — All Indicators, Combos, and Advanced Usage
tags: indicators, RSI, MACD, ADX, bollinger, stochastic, ichimoku, fibonacci, CCI, volume, combos
description: Complete indicator reference — what each measures, optimal settings, combinations, and the 3-category golden rule
# Indicator Mastery
> Never stack indicators from the same category. Use one from each: Momentum + Trend + Volatility. This prevents redundant signals and false confidence.
## THE THREE-CATEGORY SYSTEM (Golden Rule)
| Category | Measures | Indicators | When Leading |
|----------|----------|------------|-------------|
| **Momentum** | Speed of price change | RSI, Stochastic, MACD, CCI, Williams %R | Early reversal/continuation signals |
| **Trend** | Direction and strength | ADX, Moving Averages (EMA/SMA), Parabolic SAR, Ichimoku | Confirms directional bias |
| **Volatility** | Range expansion/contraction | Bollinger Bands, ATR, Keltner Channel | Timing entries/exits, position sizing |
**Best default combo**: RSI (momentum) + ADX (trend) + Bollinger Bands (volatility)
## MOMENTUM INDICATORS
### RSI (Relative Strength Index)
- **Period**: 14 (standard), 9 (faster/noisier), 21 (slower/smoother)
- **Range**: 0-100
- **Overbought**: >70 (potential sell). **Oversold**: <30 (potential buy)
- **Best use**: Divergence detection is RSI's #1 value
  - Price makes new high, RSI makes lower high = bearish divergence
  - Price makes new low, RSI makes higher low = bullish divergence
- **Trend filter**: In strong trends (ADX >30), RSI can stay overbought/oversold for extended periods — don't fade the trend just because RSI is extreme
- **Centerline**: RSI >50 = bullish bias, RSI <50 = bearish bias
- **M15 setting**: 14-period. Check for divergence on every WATCH/TRADE candidate.
### Stochastic Oscillator (%K, %D)
- **Settings**: %K=14, %D=3, slowing=3 (standard)
- **Range**: 0-100
- **Overbought**: >80. **Oversold**: <20
- **Crossover signals**: %K crosses above %D in oversold zone = buy. %K crosses below %D in overbought zone = sell.
- **Best use**: Range-bound markets. In trends, stochastic stays overbought/oversold = don't fade.
- **Divergence**: Same as RSI divergence but from stochastic. Price makes new high, stoch makes lower high = bearish.
- **Key rule for validator**: Stochastic crossover at an extreme + at a key level = meaningful. Stochastic crossover in the middle = noise.
### MACD (Moving Average Convergence Divergence)
- **Settings**: 12, 26, 9 (standard). Fast EMA=12, Slow EMA=26, Signal=9
- **Components**: MACD line (12EMA - 26EMA), Signal line (9EMA of MACD), Histogram (MACD - Signal)
- **Signals**:
  - MACD crosses above signal = bullish
  - MACD crosses below signal = bearish
  - Zero-line cross = trend change
  - Histogram growing = momentum increasing
  - Histogram shrinking = momentum fading
- **Divergence**: MACD histogram divergence is the most reliable form of divergence
- **Best use**: Trend confirmation + momentum measurement. NOT for overbought/oversold.
- **Key rule**: MACD crossover within 5 bars of current candle = recent, actionable. MACD crossover 10+ bars ago = stale.
### CCI (Commodity Channel Index)
- **Period**: 20 (standard)
- **Range**: Unbounded (typically -200 to +200)
- **Overbought**: >100. **Oversold**: <-100
- **Extreme**: >200 or <-200 = very strong momentum
- **Best use**: Mean reversion signals when CCI reaches extremes and turns back
- **Zero-line**: CCI crossing above 0 = bullish momentum starting. Below 0 = bearish.
- **Advantage over RSI**: CCI is unbounded, so extreme moves show clearly. RSI caps at 0/100.
### Williams %R
- **Period**: 14 (standard)
- **Range**: -100 to 0
- **Overbought**: >-20. **Oversold**: <-80
- **Nearly identical to**: Inverted stochastic %K
- **Best use**: Fast momentum signal. Good for timing entries within a trend.
- **Key difference from stochastic**: Faster, noisier, no smoothing line. Better for short-term timing.
## TREND INDICATORS
### ADX (Average Directional Index)
- **Period**: 14 (standard)
- **Range**: 0-100 (but rarely exceeds 60 in forex)
- **Interpretation**:
  - **<15**: No trend (ranging/compression). Use range-bound strategies.
  - **15-20**: Weak trend forming. Be cautious.
  - **20-25**: Moderate trend. Trend strategies viable.
  - **25-30**: Strong trend. Full position size.
  - **>30**: Very strong trend. Let winners run, don't counter-trade.
  - **>40**: Extreme trend. Watch for exhaustion.
- **ADX direction matters**:
  - ADX rising = trend strengthening (even if price is pulling back)
  - ADX falling = trend weakening (even if price is still moving)
- **+DI/-DI**: +DI > -DI = bullish trend, -DI > +DI = bearish trend
- **THE REGIME SWITCH**: ADX is the master control for which strategies to use. This is the single most important meta-indicator.
### EMA (Exponential Moving Average)
- **Core periods for thesis**: E21 (fast), E55 (medium), E100 (slow)
- **SMA equivalents for other systems**: SMA 50, SMA 100, SMA 200
- **Fan ordering**:
  - Bullish: Price > E21 > E55 > E100
  - Bearish: Price < E21 < E55 < E100
  - Mixed/tangled: No clear order = no trade
- **Cross signals**: E21 crosses E55 = primary thesis trigger. E21 crosses E100 = strong confirmation.
- **As support/resistance**: In established trends, E21 acts as dynamic support in pullbacks. E55 is secondary. E100 is the "last stand" support.
- **Separation velocity**: Fan width bar-over-bar change. Growing = strong trend. Shrinking = weakening.
- **Key rule**: EMA cross is necessary but NOT sufficient. Fan must be separating AND BB expanding for thesis confirmation.
### Parabolic SAR (Stop and Reverse)
- **Settings**: AF start=0.02, AF step=0.02, AF max=0.20
- **Visual**: Dots above (bearish) or below (bullish) price
- **Signals**: Dot flips from above to below = buy signal. Below to above = sell signal.
- **Best use**: Trailing stop placement. The dots naturally trail the trend.
- **Weakness**: Whipsaws in ranging markets. Only use when ADX >25.
- **Forex M15**: Good for trailing stops in established trends, not for entry signals.
### Ichimoku Cloud (Overview)
- **Components**: Tenkan-sen (9), Kijun-sen (26), Senkou Span A, Senkou Span B (52), Chikou Span
- **Cloud (Kumo)**: Area between Span A and Span B. Price above cloud = bullish. Below = bearish. Inside = no-trade zone.
- **Cross signals**: Tenkan crosses Kijun above cloud = strong buy. Below cloud = strong sell.
- **Best use**: Complete trend assessment in one indicator. Shows support, resistance, momentum, and trend simultaneously.
- **Forex applicability**: Works well on H1/H4 for trend context. Too noisy on M15 for primary signals.
- **Validator note**: If using Ichimoku, it replaces EMA system — don't use both simultaneously (redundant trend indicators).
## VOLATILITY INDICATORS
### Bollinger Bands
- **Settings**: 20-period SMA, 2 standard deviations
- **Components**: Upper band, middle band (SMA 20), lower band
- **Key measurements**:
  - **BB Width**: Distance between upper and lower band. Expanding = volatility increasing. Contracting = squeeze.
  - **BB Position**: Where price is relative to bands. Near upper = overbought-ish. Near lower = oversold-ish.
  - **BB %B**: (Price - Lower) / (Upper - Lower). Above 1 = above upper band. Below 0 = below lower band.
- **Squeeze**: When BB width reaches multi-bar low = compression. Explosive move coming. Direction determined by trend bias.
- **Walking the band**: In strong trends, price "walks" along the upper (uptrend) or lower (downtrend) band. This is NOT overbought/oversold — it's trend strength.
- **Mean reversion**: Price touching outer band and reversing back toward middle = mean reversion trade (only in ranging markets, ADX <20).
- **Thesis integration**: BB expanding + fan separating = Phase 3 confirmation. BB contracting + fan tangled = no trade.
### ATR (Average True Range)
- **Period**: 14 (standard)
- **NOT directional**: ATR only measures volatility magnitude, not direction
- **Uses**:
  - **Stop-loss**: SL = 1.5-2.5x ATR from entry (scales with volatility)
  - **Position sizing**: Higher ATR = smaller position to maintain consistent risk
  - **Target setting**: TP = 1.0-2.0x ATR for quick trades, 3.0x+ ATR for swing
  - **Volatility filter**: ATR < typical range for pair = low volatility, reduce size or skip
- **Key insight**: ATR normalizes across pairs. 50 pips on EUR/USD (ATR ~60p) is different from 50 pips on GBP/JPY (ATR ~120p).
### Keltner Channel
- **Settings**: 20-period EMA, 2x ATR
- **Similar to BB** but uses ATR instead of standard deviation
- **Advantage**: Smoother, less reactive to single large candles
- **Squeeze detection**: BB inside Keltner Channel = true squeeze (TTM Squeeze concept)
- **Forex M15**: Can be used alongside BB for squeeze confirmation
## INDICATOR COMBINATIONS (Proven)
### Combo 1: RSI + ADX + Bollinger Bands (Default)
- **When**: All conditions. This is the baseline combo.
- **Entry**: RSI divergence or extreme + ADX >25 confirms trend + BB position confirms volatility context
- **Strength**: Covers all three categories. No blind spots.
### Combo 2: BB + Stochastic (Ranging Markets)
- **When**: ADX <20 (no trend)
- **Entry**: Price at lower BB + Stochastic oversold crossover = buy. Upper BB + overbought crossover = sell.
- **Avoid**: When ADX >25 (trend will steamroll the range trade)
### Combo 3: EMA 50/200 + MACD (Trend Confirmation)
- **When**: ADX >25
- **Entry**: EMA 50 crosses 200 (golden/death cross) + MACD confirms direction
- **Note**: Slow signal. Better for H1/H4 swing entries.
### Combo 4: Fibonacci + MACD (Pullback Entry)
- **When**: During trending pullback to Fib level
- **Entry**: Price reaches Fib 50% or 61.8% + MACD histogram turning in trend direction
- **Best at**: E55 or E100 level that coincides with Fib level = triple confluence
### Combo 5: EMA Fan + BB + RSI (Thesis System)
- **This is the core trading system combo**
- **Entry**: E21 crossed E55, fan separating, BB expanding, RSI recovering toward 50
- **This is the validator's primary assessment framework**
## DIVERGENCE GUIDE
### Regular Divergence (Counter-Trend Signal)
- **Bullish**: Price makes lower low, indicator makes higher low → trend weakening, reversal possible
- **Bearish**: Price makes higher high, indicator makes lower high → trend weakening, reversal possible
- **Best indicators for divergence**: RSI, MACD histogram, Stochastic
- **Reliability**: MEDIUM-HIGH. Best at key levels with additional confluence.
- **S14 in setup catalog** — this is the #1 priority reversal signal
### Hidden Divergence (With-Trend Continuation Signal)
- **Bullish**: Price makes higher low, indicator makes lower low → pullback ending, trend resuming
- **Bearish**: Price makes lower high, indicator makes higher high → bounce ending, downtrend resuming
- **What it means**: The trend is stronger than the pullback indicator suggests
- **Reliability**: MEDIUM-HIGH for continuation. Very useful for re-entry after pullbacks.
- **S15 in setup catalog**
### Multi-Timeframe Divergence
- **H4 divergence + M15 entry**: If H4 shows bearish RSI divergence and M15 shows a sell pattern → very high probability
- **Rule**: Higher timeframe divergence is more significant. M15 divergence alone = one signal. M15 + H1 + H4 divergence = extremely high conviction.
- **Detection**: Check RSI on H1 and H4 when M15 shows divergence. If they agree = compound signal.
## FIBONACCI REFERENCE
### Retracement Levels
| Level | Meaning | Trading Use |
|-------|---------|-------------|
| 23.6% | Shallow pullback | Aggressive entry in very strong trends |
| 38.2% | Standard pullback | Good entry in strong trends (ADX >30) |
| **50%** | **Golden pocket** | **Most reliable entry level in the thesis system** |
| **61.8%** | **Golden ratio** | **Last reasonable entry before reversal risk** |
| 78.6% | Deep pullback | Caution — may be reversal, not pullback |
| 100% | Full retrace | Trend has been fully reversed at this point |
### Extension Levels (For Targets)
| Level | Use |
|-------|-----|
| 127.2% | Conservative take-profit |
| 161.8% | Standard take-profit for strong trends |
| 200% | Aggressive target, usually only in Phase 3+ expansion |
| 261.8% | Extreme target, only with strong macro alignment |
### Fibonacci + EMA Confluence
- When a Fibonacci level aligns with an EMA level (e.g., 50% retrace lands on E55) = extremely strong support/resistance
- This is the prime entry zone in the thesis framework

<!-- merged from collective/trading-knowledge/education/session_timing.md -->
title: Trading Session Timing Guide
tags: sessions, timing, london, new-york, asian, tokyo, overlap, dead-zones, pairs, liquidity
description: When to trade which pairs, session characteristics, dead zones, overnight gaps, and pair-specific session behavior
# Trading Session Timing Guide
> The same setup can be a TRADE in London and a SKIP in Asian session. Timing is not optional context — it's a core input to the validator's decision.
## SESSION SCHEDULE (EST / New York Time)
| Session | Hours (EST) | Characteristics |
|---------|-------------|-----------------|
| **Sydney** | 5:00 PM - 2:00 AM | Thin liquidity, AUD/NZD pairs active |
| **Tokyo/Asian** | 7:00 PM - 4:00 AM | Moderate liquidity, JPY pairs primary |
| **London** | 3:00 AM - 12:00 PM | Highest liquidity, EUR/GBP/CHF primary |
| **New York** | 8:00 AM - 5:00 PM | High liquidity, USD pairs primary |
| **London-NY Overlap** | 8:00 AM - 12:00 PM | **PEAK liquidity, tightest spreads, biggest moves** |
## SESSION CHARACTERISTICS
### Asian/Tokyo Session
- **Liquidity**: Low to moderate
- **Typical range**: 30-50% of daily range established
- **Best for**: JPY pairs (USD/JPY, EUR/JPY, GBP/JPY, AUD/JPY)
- **Characteristics**:
  - Range-bound trading dominates
  - Fakeouts more common (thin books)
  - Trends from London/NY often pause or consolidate
  - Asian range becomes the breakout reference for London
- **Validator rules**:
  - Reduce confidence by 1 point for non-JPY pairs
  - BB squeeze during Asian = potential London breakout coming
  - Don't trust breakouts during Asian unless JPY pair with news catalyst
  - Range trading setups (S5/S6 BB+Stoch) work well here
### London Session
- **Liquidity**: Highest of any single session
- **Typical range**: 60-80% of daily range established
- **Best for**: EUR, GBP, CHF pairs + all majors
- **Characteristics**:
  - Institutional order flow begins at London open
  - Asian range breakouts are a primary signal
  - Trend-following strategies perform best
  - False breakouts less common than Asian (real money behind moves)
- **Validator rules**:
  - Full confidence for trend setups
  - Asian range breakout + thesis alignment = high conviction
  - First 2 hours (3-5 AM EST) are the most volatile
  - EUR/USD, GBP/USD, EUR/GBP most liquid and predictable
### London-NY Overlap (THE PRIME WINDOW)
- **Hours**: 8:00 AM - 12:00 PM EST (4 hours)
- **Liquidity**: Maximum. Both centers trading simultaneously.
- **Best for**: ALL major pairs
- **Characteristics**:
  - Tightest spreads of the day
  - Largest moves of the day
  - News releases (US data at 8:30 AM, 10:00 AM)
  - Institutional rebalancing
- **Validator rules**:
  - Maximum confidence window
  - Full position sizes appropriate
  - Trend trades established in London often accelerate here
  - MOST trades should happen in this window
### New York Session (Post-Overlap)
- **Hours**: 12:00 PM - 5:00 PM EST
- **Liquidity**: Declining after London close (12 PM EST)
- **Best for**: USD pairs, CAD (oil correlation)
- **Characteristics**:
  - London traders closing positions = counter-trend moves
  - Post-1 PM: significantly reduced liquidity
  - End-of-day profit-taking can create false signals
- **Validator rules**:
  - After 1 PM EST: reduce confidence by 1 point
  - After 3 PM EST: new entries risky, spreads widening
  - Manage existing positions, don't open new ones after 3 PM
  - CAD pairs active due to oil market correlation
## DEAD ZONES — DO NOT TRADE
| Period | Why | Action |
|--------|-----|--------|
| 5:00 PM - 7:00 PM EST | Gap between NY close and Sydney open | No liquidity. Spreads blow out. SKIP ALL. |
| Friday after 3:00 PM EST | Weekend risk. Spreads widening. | Close positions or set tight stops. No new entries. |
| Sunday open (5:00 PM EST) | Gaps possible. Thin liquidity. | Wait for Asian session to establish range. |
| Major holiday (US/UK) | One or both centers closed | Thin markets. Fakeouts likely. Reduce size or skip. |
| 30 min before/after major news | Spread blowout, whipsaw | Flatten or widen stops. No new entries. |
## PAIR-SPECIFIC SESSION BEHAVIOR
### EUR/USD
- **Best session**: London, London-NY overlap
- **Asian behavior**: Tight range, consolidation
- **News sensitivity**: High — ECB, Fed, NFP, CPI all move it significantly
- **Typical daily range**: 60-90 pips
### GBP/USD
- **Best session**: London (3-5 AM EST most volatile)
- **Known for**: Wider ranges, more volatile than EUR/USD
- **Asian behavior**: Usually flat, occasional BOE-related moves
- **Typical daily range**: 80-120 pips
- **Warning**: GBP pairs are wilder — reduce position size by 20% vs EUR pairs
### USD/JPY
- **Best session**: Asian (Bank of Japan activity) + London-NY overlap
- **Safe-haven behavior**: Drops during risk-off events (market fear → JPY strength)
- **BOJ intervention risk**: Sudden 100+ pip moves when BOJ intervenes near round numbers
- **Typical daily range**: 50-80 pips
### EUR/JPY, GBP/JPY (JPY crosses)
- **Best session**: London-NY overlap (highest liquidity for crosses)
- **Volatility**: Higher than majors. GBP/JPY = "the beast" (100-150+ pip daily range)
- **Position sizing**: Reduce to 60-70% of standard for GBP/JPY
### AUD/USD, NZD/USD
- **Best session**: Asian (commodity data) + London open
- **Commodity correlation**: AUD tracks iron ore/gold. NZD tracks dairy prices.
- **Asian session**: These ARE the Asian session pairs
- **Typical daily range**: 50-70 pips
### USD/CAD
- **Best session**: NY session (oil market active)
- **Oil correlation**: Strong inverse — oil up = CAD strength = USD/CAD down
- **Canadian data**: Often released at 8:30 AM EST
- **Typical daily range**: 50-70 pips
### EUR/CHF
- **Best session**: London
- **Low volatility pair**: 30-50 pip daily range
- **SNB intervention risk**: Swiss National Bank historically intervenes to prevent CHF strength
- **Position sizing**: Can use larger size due to lower volatility, but beware SNB surprises
## OVERNIGHT GAP BEHAVIOR
### What Causes Gaps
- Weekend events (geopolitical, natural disasters, elections)
- Major economic data released outside trading hours
- Central bank surprise announcements
### Gap Trading Rules
- **Gaps into trend direction**: Usually continue (don't fade)
- **Gaps against trend direction**: Often fill within first session (fade cautiously)
- **Gap size >50% of ATR**: Significant — likely driven by real news
- **Gap size <20% of ATR**: Noise — ignore
### Validator Gap Handling
- If a gap occurred at session open, note it in reasoning
- Gap + thesis alignment = increased confidence
- Gap against thesis = wait for gap to fill before entering
- Never enter immediately at gap open — wait 15-30 minutes for liquidity to stabilize
## VALIDATOR SESSION CHECKLIST
Before issuing TRADE_NOW, check:
1. What session is it? (Asian / London / NY / Overlap / Dead zone)
2. Is the pair appropriate for this session?
3. Is there a news event within 30 minutes? (Calendar check)
4. Is it after 3 PM EST Friday? (No new entries)
5. Has the daily range already been consumed? (If pair has moved 80% of ATR already, target space is limited)
