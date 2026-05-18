---
type: note
created: 2026-03-18
tags: [trading, post-mortem, watch-system, losses, fixes, 2026-03-18]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Mar 18 trading session post-mortem — -$106.60, 1W/10L
**Date:** 2026-03-18T17:43:45
**Type:** note
**Tags:** trading, post-mortem, watch-system, losses, fixes, 2026-03-18

FULL DAY RESULTS: 1W / 10L, -\$106.60, -121.1 pips. Account reset to \$<amount> fresh start.

TRADE LOG:
1635 AUD_JPY BUY  -\$4.99  -7.9p  | Watch fire, full SL, pre-fix
1644 EUR_USD BUY  -\$16.00 -16.0p | Watch fire, full SL, pre-fix
1650 EUR_USD SELL -\$17.30 -17.3p | Watch fire, full SL, pre-fix
1656 EUR_USD ?    -\$20.30 -20.3p | No spawn log, full SL
1662 EUR_JPY BUY  -\$1.45  -2.3p  | Dynamic SL over-tightened on negative PnL (bug, now fixed)
1670 GBP_JPY BUY  -\$1.89  -3.0p  | Phase 3 trail tightened on negative PnL (bug, now fixed)
1678 EUR_JPY BUY  +\$3.18  +5.1p  | WIN — guardian worked correctly
1686 GBP_JPY BUY  -\$14.02 -22.3p | Watch 1536 re-fire, peaked +1.4p then full reversal
1698 EUR_JPY BUY  -\$9.56  -15.2p | Watch 1539 fire, NEVER went positive, full SL
1704 GBP_JPY BUY  -\$10.50  0.0p  | Watch 1540 fire, fan failed, manual close
1713 GBP_JPY BUY  -\$13.77 -21.9p | Watch 1540 fired before cancellation (17:24 vs cleanup at 17:27), manual close

ROOT CAUSE: Watch system fired BUY trades into pairs where validator was REJECTing on every scout cycle. Watch conditions checker evaluates raw indicators only — bypasses validator. Fan on GBP/JPY and EUR/JPY was bearish/contracting all afternoon but watch BUY score kept crossing threshold.

FIXES DEPLOYED TODAY:
1. Dynamic SL trail + Phase 3 E100 trail now require peak_pnl_pips >= 3.0 before tightening (prevents clipping valid entries during initial oscillation)
2. Watch open-trade gate: OANDA positions fetched once at top of check_active_watches(), pairs with open trades skip trigger+notify entirely
3. Direction sanity gate in check_active_watches(): BUY watch blocked if fan_direction=bearish OR sniper SELL > BUY+2 OR just_crossed+non-bullish; SELL mirror
4. Surgical watch cleanup: 21 watches cancelled — 5 old-format no-direction (1220,1221,1274,1281,1338), 4 text-trigger broken (1515-1518), 5 GBP_JPY BUY direction-dead (1512,1521,1536,1540,1542), 5 EUR_CHF duplicates (1353,1524,1525,1528,1531), 1 USD_CAD duplicate (1494), 1 EUR_JPY weak (1535)
5. 25 clean structured watches remain, all < 10h old, all with re_entry_direction set

MORNING FIX SESSION (separate, deployed ~11am-3pm ET):
- R:R corrected: SL 1.5xATR, TP 2.0xATR (was 2.5/1.0 = 0.37 R:R)
- R:R hard gate: blocks sub-1.2 trades, auto-widens TP
- Pair 30-min cooldown after any close
- just_crossed+neutral gate blocks entries on uncertain fan cross
- Execution agent eliminated, direct place_market_order()
- Blank validator chart fix (candle sort)
- Ghost trade tab fix
- 48h annotation expiry
- Fan retracement fix (no threat inflation during normal compression)

ACCOUNT: Reset to \$<amount>. Real money practice account. 10,000 units per trade (~\$13-14 risk per 20-pip loss on JPY pairs = ~0.13% per trade). Issue was not position size but entry quality — 10 consecutive bad watch fires.

LESSONS:
- Watch fires MUST respect current fan direction — validator REJECT on scout cycle = don't fire the watch regardless of indicator conditions
- Never have >2 watches per pair per direction — duplicates just multiply bad-fire probability
- Dynamic SL should never tighten while trade is still in negative PnL
- GBP/JPY and EUR/JPY were the toxic pairs today — bearish all afternoon, BUY watches should have been blocked
- Age alone does not justify cancelling a watch BUT direction conflict does
