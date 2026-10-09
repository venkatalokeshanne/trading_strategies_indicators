# 10 — Drafting with TrendSpider's own AI ("Build a new indicator using AI")

The Custom Indicator Editor has an AI box ("Type instructions or questions for the AI to
tackle" → **Generate Code**). It is used to produce a **first draft only**. The draft is then
reviewed line by line against the Pine source with the checklist below, fixed by hand, and
goes through the normal gates (lint, oracle where possible, live APPLY/Save as `_TV`).

## The prompt

The user's original wording was: "Convert this TradingView Pine Script indicator logic into
a working TrendSpider JavaScript indicator. Make sure to map out the scanning and strategy
signals." It is kept, with the rules that the AI otherwise gets wrong added:

```
Convert this TradingView Pine Script into a working TrendSpider custom JavaScript indicator
that reproduces the Pine logic EXACTLY (same values, same signal bars), and map out the
scanning and strategy signals.

Rules:
1. Keep every input with the same title and default value.
2. Reproduce Pine built-ins exactly. Hand-roll anything TrendSpider computes differently:
   ta.supertrend (Pine reference algorithm; direction -1 = up-trend; do NOT use
   TrendSpider's supertrend()), ta.rma/atr (Wilder, SMA-seeded), ta.dmi (returns
   [+DI, -DI, ADX] in that order; use exactly the element the Pine code uses),
   ta.pivothigh/pivotlow (confirmed only `right` bars later).
3. request.security / other timeframes: use request.history and make each chart bar see
   only COMPLETED higher-timeframe bars. A higher-timeframe bar's timestamp is its open, so
   never land its final value at its open time (that is look-ahead).
4. Strategy logic: emit register_signal() series for 'Long Entry', 'Long Exit',
   'Short Entry', 'Short Exit' (only those that exist), true on the bar where Pine places
   the order (the Strategy Tester fills at the next open). Model stop-loss/take-profit
   exits as exit signals where they can be computed; otherwise list the Tester settings
   needed in a comment.
5. Paint the same plots with the same names.
6. Add a comment wherever TrendSpider cannot match Pine exactly.

Pine Script:
```

Then the full Pine source.

## Review checklist for the AI draft (do every item)

- [ ] Every input present, same default.
- [ ] Every built-in compared with `02-function-map.md`; replaced where it is "not equal".
- [ ] Higher-timeframe data: shifted per `06-higher-timeframe-and-data.md` — no look-ahead.
- [ ] Signals fire on the same bar as the Pine order; entries/exits for both directions.
- [ ] Pine quirks reproduced (e.g. a script that reads the wrong tuple element), not "fixed".
- [ ] `lint_trendspider.py` clean; reserved names; no `new`; fixed `paint`/`register_signal` names.
- [ ] Live APPLY/Save as `<Title>_TV` (`09-trendspider-live.md`).

Record what the AI got wrong in LESSONS.md so the prompt can be improved.
