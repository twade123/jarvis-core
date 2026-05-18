---
title: News Impact by Pair — Central Bank and Economic Event Mapping
type: education
workspace: forex-trading-team
agent: validator
tags: news, central-bank, economic-calendar, Fed, ECB, BOJ, BOE, NFP, CPI, FOMC, impact, pairs
description: Which news events move which pairs, timing rules, and how the validator should handle news proximity
---

# News Impact by Pair

> Every major currency has a central bank and key economic releases that move it. The validator must know which events affect the pair being evaluated and adjust confidence accordingly.

---

## CENTRAL BANK → CURRENCY MAPPING

| Central Bank | Currency | Key Decisions | Meeting Frequency | Typical Impact |
|-------------|----------|---------------|-------------------|---------------|
| **Federal Reserve (Fed)** | USD | Fed Funds Rate, QE/QT | 8x/year (6 weeks) | 50-150 pips on USD pairs |
| **European Central Bank (ECB)** | EUR | Main Refinancing Rate | 8x/year | 40-100 pips on EUR pairs |
| **Bank of England (BOE)** | GBP | Bank Rate | 8x/year | 50-120 pips on GBP pairs |
| **Bank of Japan (BOJ)** | JPY | Interest Rate, YCC | 8x/year | 50-200+ pips (intervention risk) |
| **Reserve Bank of Australia (RBA)** | AUD | Cash Rate | 11x/year (monthly exc Jan) | 30-80 pips on AUD pairs |
| **Reserve Bank of New Zealand (RBNZ)** | NZD | Official Cash Rate | 7x/year | 30-70 pips on NZD pairs |
| **Bank of Canada (BOC)** | CAD | Overnight Rate | 8x/year | 30-80 pips on CAD pairs |
| **Swiss National Bank (SNB)** | CHF | Policy Rate | 4x/year | 30-100 pips (intervention possible) |

---

## HIGH-IMPACT ECONOMIC RELEASES

### Tier 1 (Maximum Impact — 50-200+ pip moves possible)

| Event | Country | Typical Time (EST) | Pairs Affected | Impact Duration |
|-------|---------|-------------------|----------------|----------------|
| **Non-Farm Payrolls (NFP)** | US | First Friday, 8:30 AM | ALL USD pairs | 2-4 hours |
| **FOMC Rate Decision** | US | 8x/year, 2:00 PM | ALL USD pairs | 4-24 hours |
| **Fed Chair Press Conference** | US | After FOMC, 2:30 PM | ALL USD pairs | Extends FOMC impact |
| **CPI (Consumer Price Index)** | US | Monthly, 8:30 AM | ALL USD pairs | 2-4 hours |
| **ECB Rate Decision** | EU | 8x/year, 7:45 AM | EUR pairs | 2-4 hours |
| **BOE Rate Decision** | UK | 8x/year, 7:00 AM | GBP pairs | 2-4 hours |
| **BOJ Rate Decision** | Japan | 8x/year, varies | JPY pairs | 4-12 hours |

### Tier 2 (High Impact — 30-80 pip moves)

| Event | Country | Typical Time | Pairs Affected |
|-------|---------|-------------|----------------|
| **GDP (Gross Domestic Product)** | Various | Varies | Country's currency pairs |
| **PMI (Purchasing Managers Index)** | Various | 9:45 AM (US) | Country's currency pairs |
| **Retail Sales** | Various | 8:30 AM (US) | Country's currency pairs |
| **Employment Change** | Various | Varies | Country's currency pairs |
| **Trade Balance** | Various | Varies | Country's currency pairs |
| **RBA/RBNZ/BOC Rate Decisions** | AUS/NZ/CAN | Varies | Respective pairs |
| **Oil Inventory (EIA)** | US | Wed 10:30 AM | USD/CAD, CAD crosses |

### Tier 3 (Moderate Impact — 15-40 pip moves)

| Event | Pairs Affected |
|-------|---------------|
| Consumer Confidence | USD pairs |
| Housing data (existing/new home sales) | USD pairs |
| Industrial Production | Country's pairs |
| Wage Growth data | Country's pairs |
| PPI (Producer Price Index) | Country's pairs |

---

## PAIR-SPECIFIC NEWS SENSITIVITY

### EUR/USD
- **Most sensitive to**: FOMC, ECB decisions, NFP, CPI (both US and EU)
- **Directional rules**:
  - Fed hawkish (rate hike/higher-for-longer) → EUR/USD DOWN
  - Fed dovish (rate cut/dovish pivot) → EUR/USD UP
  - ECB hawkish → EUR/USD UP
  - Strong US jobs (NFP beat) → EUR/USD DOWN
  - Hot US CPI → EUR/USD DOWN (Fed will stay tight)
- **Typical event range**: 60-120 pips on Tier 1 events

### GBP/USD
- **Most sensitive to**: BOE, UK CPI, UK employment, UK GDP, FOMC
- **Known for**: Overshooting on BOE surprises. GBP is more volatile than EUR on news.
- **Brexit legacy**: Occasional political headlines can move GBP 50+ pips

### USD/JPY
- **Most sensitive to**: BOJ, FOMC, risk sentiment (equity crashes → JPY strength)
- **Special risk**: BOJ intervention — when USD/JPY approaches certain levels (historically 150-160), BOJ may intervene to sell USD/buy JPY, causing 200-500 pip crash in minutes
- **Safe-haven rule**: In "risk-off" (market fear, VIX spike, equity crash) → JPY strengthens regardless of fundamentals
- **Carry trade**: When rates diverge (US high, Japan low), carry traders buy USD/JPY. Unwinding of carry = sharp JPY strength.

### AUD/USD
- **Most sensitive to**: RBA, China PMI/GDP (Australia's largest trading partner), iron ore prices, gold prices
- **China proxy**: AUD is the primary "China growth" proxy in forex. Bad China data → AUD down.
- **Commodity correlation**: Iron ore up → AUD up. Gold up → AUD up (Australia is #2 gold producer).

### USD/CAD
- **Most sensitive to**: BOC, oil prices (WTI crude), US/Canada employment
- **Oil rule**: Oil up → CAD strength → USD/CAD down. Oil down → USD/CAD up.
- **OPEC meetings**: Can cause 50+ pip moves on USD/CAD via oil price impact

### EUR/CHF
- **Most sensitive to**: ECB, SNB (Swiss National Bank)
- **SNB intervention risk**: SNB has historically defended EUR/CHF floor levels. If price approaches 0.93-0.95 area, intervention possible.
- **Low volatility pair**: News impact is often muted compared to other pairs

---

## VALIDATOR NEWS RULES

### Pre-News (30 minutes before Tier 1 event)
- **Do NOT open new positions**
- **Existing positions**: Tighten stops or take partial profit
- **WATCH verdicts**: Pause — don't trigger snipes during news windows
- **Calendar check is MANDATORY** for every TRADE_NOW verdict

### During News (First 5-15 minutes after release)
- **Spread blowout**: Spreads can widen 3-10x during major releases
- **Whipsaw**: Initial move often reverses (stop hunts common)
- **No entries**: Wait for the dust to settle (15-30 min minimum)

### Post-News (15-60 minutes after release)
- **Retracement entry**: Often the best opportunity — initial overreaction pulls back
- **Trend confirmation**: If price establishes direction 30 min after news, that's the real move
- **Enter with thesis**: If news aligns with existing thesis setup → high confidence entry

### News Alignment Scoring
| News Alignment | Confidence Adjustment |
|---------------|----------------------|
| News supports trade direction | +1 confidence point |
| No relevant news within 4 hours | Neutral (no adjustment) |
| News within 2 hours (direction unclear) | -1 confidence point |
| News directly contradicts trade direction | -2 points or SKIP |
| Major Tier 1 event within 30 min | SKIP regardless of setup |

---

## GEOPOLITICAL EVENTS (Non-Calendar)

### Risk-Off Events → JPY/CHF/USD Strength
- Military conflicts, terrorism
- Political instability in major economies
- Pandemic escalation
- Banking/financial crisis

### Commodity Shocks
- Oil supply disruption → CAD/NOK strength
- Gold spike → AUD strength
- Agricultural commodity shock → NZD impact

### Election/Political Events
- UK elections → GBP volatility
- US elections → USD volatility
- EU political crises → EUR weakness
- These are NOT on economic calendars — validator should be aware of upcoming political events
