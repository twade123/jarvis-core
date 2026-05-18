# Cooldown Timestamp Parsing Bug (fromisoformat nanoseconds)

**Discovered**: 2026-03-27 by scout-analyst
**Severity**: HIGH — fail-open behavior lets trades bypass cooldown

## Problem
Python's `datetime.fromisoformat()` only accepts up to 6 decimal places (microseconds).
Timestamps with nanosecond precision (9 decimal places) like `2026-03-27T14:11:40.485847192`
cause a ValueError, and the current code catches this with a warning and proceeds (fail-open).

## Impact
- 5 trades today bypassed cooldown checks
- Contributed to GBP_JPY churning (6 trades, -43.8 pips)
- Any pair with nanosecond timestamps from Oanda will bypass cooldown

## Fix
Truncate timestamp to microseconds before parsing:
```python
# Before fromisoformat, truncate nanoseconds to microseconds
if '.' in ts:
    parts = ts.split('.')
    frac_and_tz = parts[1]
    # Find where timezone starts (+ or Z)
    for i, c in enumerate(frac_and_tz):
        if c in ('+', '-', 'Z') and i > 0:
            frac = frac_and_tz[:i][:6]  # max 6 decimal places
            tz = frac_and_tz[i:]
            ts = parts[0] + '.' + frac + tz
            break
```
Or use `dateutil.parser.parse(ts)` which handles arbitrary precision.
