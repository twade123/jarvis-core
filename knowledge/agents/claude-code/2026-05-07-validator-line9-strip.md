---
type: agent_log
agent: claude-code
created: 2026-05-07T13:30:00
tags: [validator, prompt, ghost_validator_v1, strip, line9, test]
---

# Validator prompt: TRADE_NOW example (line 9) stripped — 2026-05-07

## Why

After stripping negation-seeded boilerplate phrases and rewriting line 9 with new
phrasing earlier today, the validator was still hallucinating "Phase 0/1 chop zone"
on charts whose own headers explicitly say "BEARISH FAN (COMPRESSING)". Evidence:

- USD/CHF cycle 9:22:48 ET — chart header read "EMAs: BEARISH FAN (COMPRESSING)"
- Validator output: "Phase 0/1 chop zone — no directional story... EMAs tightly
  compressed and weaving through each other... E21 crosses E55 multiple times"
- Vision pipeline confirmed working — `vision mode with 2 images + text` logged
- The model wasn't missing the chart, it was applying a stock SKIP template
  ("Phase 0/1 chop zone — Early stretch / Mid-frame / Late stretch") regardless
  of what the chart showed

The line-9 segmented-bar-walk shape was contaminating SKIPs across all charts.
Tim's call: strip line 9 entirely, test with no rich TRADE_NOW example.

## What was stripped

### Line 8 (heading) and Line 9 (example body)

```
EXAMPLE OF GOOD REASONING (from a real TRADE_NOW):
"CHART READ: This EUR/CHF M15 frame is a textbook Phase 2 bearish cascade. Early stretch (~40 bars in): tight horizontal price action, E21/E55/E100 stacked within ~5 pips of each other, BB width compressed to ~0.0030 — pre-break loading. Mid-frame (~20 bars): a sharp upper-body spike marks the prior bull peak, immediately followed by a bearish engulfing impulse that drives price below E21 and pulls E21 down through E55 and E100 in sequence. Late stretch (~40 bars): cascade completed — E21 < E55 < E100, all three separating, BB expanding asymmetrically with the lower band leading down, three consecutive red full-body candles riding the lower band, RSI 24 (deep bearish, not exhaustion). Setup is clean Phase 2 — TRADE_NOW."
```

### Line 17 (DO NOT mimic rule — references the now-stripped example)

```
DO NOT mimic the TRADE_NOW example's structure for SKIP or WATCH responses. The TRADE_NOW format is long bar-by-bar narrative because the chart told a strong directional story across 100 bars. SKIP and WATCH responses should be 2-3 sentences naming the SPECIFIC blockers (for SKIP) or the SPECIFIC trigger conditions (for WATCH).
```

## What was kept

- Line 11-12: SKIP example (brief, concrete: "Fan is mixed (E21 ... < E55 ...) — order broken... 3 of 10 confirmed. SKIP")
- Line 14-15: WATCH example (brief, concrete: "Fan ordered bearish... waiting for BB width > 0.0055...")
- Lines 19-23: Vocabulary precision rule (DO NOT misuse "tangled")
- Lines 25-27: REMINDER — describe what you see in the live chart
- Lines 29+: JSON contract, structure rules, 10-point checklist (now verdict-aware)

## Test plan

Reload trading process. Run manual cycle on USD/CHF (known bear-ordered chart).
Expected: validator either matches structural reality (bear fan), or produces a
short SKIP that doesn't contain "Phase 0/1 chop zone" / "Early stretch / Mid-frame".

If model loses structural read on real TRADE_NOW setups too, restore the example.

## Restoration

If we need to put line-9 back, the exact text is preserved in the "What was stripped"
section above. Insert as line 8-9 of `Forex Trading Team/Prompts/ghost_validator_v1.md`.
