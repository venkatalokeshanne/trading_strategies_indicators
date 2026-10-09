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

## Working the AI drafts (procedure in use since 2026-10-09 — resume from here on any account)

The drafts are generated offline by `tools/ts_ai_drafts.py` with the user's plain prompt
(no extra rules): "Convert this TradingView Pine Script into a working TrendSpider custom
JavaScript indicator that reproduces the Pine logic EXACTLY (same values, same signal bars),
and map out the scanning and strategy signals." — drafts land in `TrendSpider/ai_drafts/`.

Per group of ~4 scripts (light review only — the live test catches the rest):
1. `python tools/ts_next_drafts.py 4` — next pending drafts with their Pine source.
2. Fix only what is wrong. Recurring AI-draft faults: `_TV` missing / generic names (L20);
   null comparisons on warm-up bars (`x > null` is true in JS); labels that print prices
   instead of BUY/SELL text or icons; undocumented options (`style:'ladder'`, `hidden:true`,
   `constants.empty_series`, `input.group`, `input.text`, 3rd arg of describe_indicator,
   5th arg of fill, 7th of color_cloud); TrendSpider's `supertrend()` (use Pine's algorithm);
   `shift(x, -n)` (look-ahead, L21); higher-timeframe values landed at the bar's open (L23);
   input titles > 30 chars (L19); names colliding after punctuation is dropped (L22);
   time zones taken from the exchange instead of the Pine's zone.
   `for_every` callbacks DO receive `(…values, previousOutput, index)` — that is fine.
3. Write the body, then `python tools/ts_header.py <id> <body.js> --from-ai --placement ... --words ... --dev ...`
   → `TrendSpider/<kind>/<stem>.trendspider.js`; `python tools/lint_trendspider.py <file>`.
4. Live: open charts.trendspider.com in Chrome on a free workspace (not the one the drafting
   run uses), open the Custom Indicator Editor, paste `tools/ts_live_helper.js` once, then
   `python tools/ts_batch_live.py <out.js> <file1> <file2>` and send its `R.push(...)` lines.
5. `python tools/progress.py set <id> --converted-file <file> --ts-name "<name>_TV"
   --live-tested AAPL:5m --ts-saved yes --validation live --status FULL|PARTIAL`, commit, push.
   Not convertible (no data feed in TrendSpider, truncated source…): `--status "NOT CONVERTIBLE" --notes "..."`.
