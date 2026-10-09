---
name: pine-to-python
description: Convert a TradingView Pine Script indicator or strategy (v4, v5, v6) into a Python script on pinelib — this repo's Pine-faithful engine — one script at a time, by hand and line by line, never with an automatic converter. Use whenever the user asks to convert, port or translate Pine Script to Python, or to continue the Python conversion backlog for the TradeSearch backend.
---

# Pine Script → Python (pinelib), by hand

`python/pinelib` reproduces Pine's execution model — bar-by-bar, per-call-site state,
history, `na`, Pine's `ta.*` formulas, `request.security` timing, and the strategy broker
emulator. Because of that, a conversion is a **line-for-line translation**: the same
statements in the same order. Restructuring (vectorising, inventing state machines) is
where silent bugs come from — don't.

## Read first, every session
1. **`LESSONS.md`** in this folder — every mistake made so far and the check that stops it.
2. **`reference/translation.md`** — the Pine → pinelib table (syntax, `ta`, `strategy`,
   `request.security`, drawings, arrays, strings, time).
3. The **original Pine source** in full: `TradingView/strategies/<id>-<slug>.pine` or
   `TradingView/indicators/…`.

## Procedure — every step, every time

0. **Start of session:** `git pull`; `python tools/progress.py next --python 5`.
1. **Read the whole Pine script.** Note the version (`//@version=`). Rule out deprecation
   stubs and withdrawn placeholders (→ NOT CONVERTIBLE, name why). An `import user/lib/N`
   needs the library's source inlined (functions used only, with credit) — else NOT CONVERTIBLE.
2. **Inventory** with line numbers: declaration args (`strategy(...)` → `STRATEGY`), inputs,
   every `[n]`, every `var`/`varip`, every `ta.*`, every `request.*`, every UDF (does it use
   history?), every `strategy.*`, plots/shapes/alerts, drawings and whether the logic READS
   them back, time/session use.
3. **Translate line for line** into `python/strategies/<id>-<slug>.py` (or `indicators/`),
   same file stem as the Pine file. Structure: header docstring → imports → one `Script`
   subclass with `TITLE`, `PINE_VERSION`, `OVERLAY`, `STRATEGY` (strategies only), `SOURCE`
   → `init()` (inputs, `var` state, constants) → `on_bar()` (the script body, same order).
4. **Lint:** `python tools/lint_python.py <file>` — zero ERRORs; every warning resolved or
   justified in a comment on that line.
5. **Smoke + replay:** `python tools/py_check.py <file>` — runs on synthetic and cached real
   bars, reports trades/plots, and the repaint replay. No exceptions allowed.
6. **Independent check** for FULL: an independent re-implementation of the trading rules (a
   short pandas/numpy loop in the scratchpad, written from the Pine source, not from your
   Python) must produce the same entry/exit bars on the same data (LESSONS P0). Record the
   evidence with `--py-validation independent`.
7. **Record and push:**
   `python tools/progress.py set <id> --py-status FULL|PARTIAL|"NOT CONVERTIBLE" --py-file <path> --py-validation smoke|independent --notes "..."`
   then `git add -A && git commit -m "Python: convert <id> <slug>: <status>" && git push`.
   Push after each script or a small batch (≤ 5) — never leave converted work unpushed.

## Header docstring (required; the lint checks it)

```
── Converted from TradingView Pine Script ─────────────────────────────
Original     : <title>
Author       : <author>                       (keep the credit)
Source URL   : <tradingview url>
Pine version : v5
Licence      : <as declared, or "not stated">
Type         : strategy | indicator
Status       : FULL | PARTIAL | NOT CONVERTIBLE
Converted    : <YYYY-MM-DD> by Claude (pine-to-python skill)

Deviations from the original: <each, or "none">
Not carried over: <each with the reason, or "none">
────────────────────────────────────────────────────────────────────────
```

Status: **FULL** — same trades/values as Pine on the same bars (independent check passed).
**PARTIAL** — runs, but a listed deviation changes values or trades. **NOT CONVERTIBLE** —
name the blocking feature and what was tried.

## Final checklist
- [ ] Same statement order as the Pine source; no restructuring.
- [ ] Every `/` with a non-constant divisor uses `div()`; `round`/`max`/`min`/`math.*` use `pmath`.
- [ ] v5 (and earlier): every `ta.*` on the right of `and`/`or` computed into a variable
      first (v5 evaluates both sides; Python short-circuits). v6 short-circuits like Python.
- [ ] `ta.*` / `S()` called in the same block structure as in Pine (conditional calls only
      where Pine has them).
- [ ] Every `x[n]` on a non-price value goes through `S(...)` or `self.H(name)`.
- [ ] `var` → state set in `init()`; `varip` → same (historical) + listed as a deviation.
- [ ] Inputs keep Pine's titles and defaults (they become the backtest's parameters).
- [ ] `strategy(...)` arguments copied into `STRATEGY` exactly (capital, qty type/value,
      pyramiding, commission, slippage, process_orders_on_close, margin, …).
- [ ] `request.security` expression passed as a function of the SeriesView; `lookahead`
      copied; look-ahead originals noted (the repaint audit will flag them).
- [ ] Drawings the logic reads back are created with `self.draw.*` and the same max counts.
- [ ] Lint clean; py_check clean; progress recorded; pushed.
