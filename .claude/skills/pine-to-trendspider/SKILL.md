---
name: pine-to-trendspider
description: Convert a TradingView Pine Script indicator or strategy (v4, v5 or v6) into a TrendSpider custom JavaScript indicator, one script at a time, by hand and line by line — never with an automatic converter. Use whenever the user asks to port, translate, convert or rewrite Pine Script / a .pine file / a TradingView script for TrendSpider, or to continue the conversion backlog in this repo.
---

# Pine Script → TrendSpider, by hand

You are converting **one Pine script at a time**, reading it fully and rewriting it as a
TrendSpider custom JavaScript indicator. This is a port, not a transliteration. The two
platforms disagree on the execution model, time units, day numbering, indicator seeding,
position management and dozens of smaller things — and almost every one of those
disagreements produces code that **runs without error and quietly gives wrong numbers**.
Your job is to find and neutralise every one of them, and to say plainly what could not
be carried over.

Do not write, use or suggest an automatic Pine→JS converter. The user has asked for each
script to be read and converted deliberately.

## Read these before converting anything

The reference files hold the detail. Read the ones relevant to the script in front of you
— for a strategy that is all of them.

| File | Read it when |
|---|---|
| `reference/01-execution-model.md` | **Always.** Per-bar vs whole-array, history `[n]`, `var`, `na`, recursion. |
| `reference/02-function-map.md` | **Always.** Every `ta.*` / `math.*` / `str.*` mapping and its seeding traps. |
| `reference/03-time-sessions-inputs.md` | The script uses `time`, sessions, `dayofweek`, `month`, or any `input.*`. |
| `reference/04-plotting-and-drawing.md` | The script plots anything (it always does). |
| `reference/05-strategies.md` | The script calls `strategy(...)`. |
| `reference/06-higher-timeframe-and-data.md` | `request.security`, other symbols, or `request.*` alt-data. |
| `reference/07-sandbox-traps.md` | **Always.** TrendSpider-specific rules that fail silently or at save time. |
| `reference/08-validation.md` | **Always**, before you call a conversion done. |
| `templates/` | Skeletons for an indicator, a single-direction strategy, and shared helpers. |

Facts in these files are tagged:

- **[VERIFIED]** — confirmed against TrendSpider's own documentation, its captured scripting
  engine run in Node, or a live script in the editor. Rely on it.
- **[VERIFY]** — believed correct but not confirmed. Before depending on it, check it in the
  TrendSpider editor (or the local engine oracle — see `08-validation.md`) and, if you
  confirm or refute it, **update the reference file** so the next conversion benefits.

Never invent a TrendSpider function. If a Pine built-in has no confirmed TrendSpider
equivalent, hand-roll it from confirmed primitives (`02-function-map.md` shows how).

## The procedure — follow every step, every time

### 1. Read the whole script before writing a line
Note the Pine version (`//@version=4|5|6`; v4 also uses `study()` and unprefixed functions).
Version changes semantics — see `01-execution-model.md` §Versions.

Two things to rule out first, both in `01-execution-model.md`:
- **A deprecation stub** — the author replaced the body (`strategy("DEPRECATED - DO NOT USE")`).
  Mark NOT CONVERTIBLE and move on.
- **`import user/lib/N`** — the library's source must be found and inlined. If it cannot be,
  the script is NOT CONVERTIBLE until it is.

### 2. Classify it
- `indicator()` / `study()` → TrendSpider indicator.
- `strategy()` → TrendSpider indicator that **emits signals**, plus Strategy Tester settings
  the user configures by hand. Read `05-strategies.md` before going further.
- Decide **overlay vs lower pane** (`overlay=true` → `'overlay'`). A script that paints on
  both (v6 `force_overlay=true`, or a lower indicator that also colours candles) must be
  **split into two TrendSpider scripts** — one script cannot paint both.

### 3. Inventory every feature — write the list down
Go through the script and list, with line numbers: every `[n]` history reference, every
`var`/`varip`, every `ta.*` call, every `request.*`, every time/session use, every input,
every plot/fill/shape/drawing, every user-defined function (and whether it uses history
internally), every `strategy.*` call, every alert. **This list is your checklist** — each
item must be explicitly handled in the output or explicitly listed as a deviation.

### 4. Look each item up
Use the reference files. For each item decide: exact mapping, hand-rolled equivalent,
approximation (state how it differs), or not convertible (state why).

### 5. Write the TrendSpider script
Start from `templates/`. Structure it as: header comment → `describe_indicator` → inputs →
data → computation → paints → signals. Keep **all** `paint()`, `fill()` and
`register_signal()` calls unconditional, at top level, with fixed literal names
(`07-sandbox-traps.md` explains why this is not optional).

### 6. Self-audit — the edge-case sweep
Run the checklist at the end of this file against your output. Do not skip it; most
silent bugs are caught here.

### 7. Validate
Follow `08-validation.md`: at minimum a syntax/sandbox check and a numeric spot-check
against values read off TradingView for the same symbol, timeframe and bars.

### 8. Record and push
- Write the output to `converted/<id>-<slug>.trendspider.js`.
- Update `progress/progress.json` for this script (status, deviations, validation).
- **Commit and push to GitHub after every script** (see "Persisting progress"). The user
  works across sessions and accounts; unpushed work is lost work.

## Output file format

Every converted file starts with this header block, filled in completely:

```js
/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : <script title>
 * Author       : <author>            (credit is required — keep this line)
 * Source URL   : <tradingview script url>
 * Pine version : v5
 * Licence      : <as declared in the source, e.g. "MPL 2.0", or "not stated">
 * Type         : indicator | strategy (signals) | strategy split: LONG | SHORT
 * Placement    : overlay | lower
 * Status       : FULL | PARTIAL | NOT CONVERTIBLE
 * Converted    : <YYYY-MM-DD> by Claude (pine-to-trendspider skill)
 *
 * Deviations from the original (every one, or "none"):
 *   - <what differs, why, and the practical effect>
 *
 * Not carried over:
 *   - <feature> — <reason>
 *
 * Strategy Tester settings (strategies only — set these by hand in TrendSpider):
 *   Entry  : <signal name> → "Signal emerged"
 *   Exit   : <stop / target / trailing / signal, with values>
 *   Sizing : <from strategy() defaults>   Commission/slippage: <...>
 * ───────────────────────────────────────────────────────────────────────
 */
```

Status meanings: **FULL** — same numbers on the same bars after warm-up, within data-vendor
noise. **PARTIAL** — runs and is useful, but at least one listed deviation changes values or
trades. **NOT CONVERTIBLE** — say exactly which feature blocks it; still record it in progress.

## Persisting progress

This repository is the source of truth across sessions and Claude accounts.

1. After each script: update `progress/progress.json`, then
   ```bash
   git add -A && git commit -m "Convert <slug>: <status>" && git push
   ```
2. At the start of a session: `git pull`, read `progress/progress.json`, and continue from
   the first script whose status is `pending`.
3. If you improve a reference file (a [VERIFY] confirmed, a new trap found), commit that
   separately with a message saying what you learnt.
4. **Licensing:** this repo is public. Original Pine sources and their converted
   derivatives are other authors' work. Do not commit `pine/` or `converted/` unless the
   user has confirmed the repo is private or explicitly approved publishing; `.gitignore`
   excludes them by default. Skill files, templates, references and `progress/` are fine.

## Final self-audit checklist

Tick every line against your output before marking a script done.

**Execution model**
- [ ] Every Pine `x[n]` became `shift(x, n)` or `arr[i - n]` with a bounds/null guard.
- [ ] Every `var` / `varip` became state carried in a forward loop or `for_every`'s
      previous-output argument — not a module-level variable mutated inside a callback.
- [ ] User-defined functions that use history internally were rewritten to take and
      return whole series (Pine gives each **call site** its own history).
- [ ] Every `import user/lib/N` inlined — only the functions used — with the library's
      version, author credit and licence beside them; any version mismatch listed.
- [ ] `na` handling: every comparison and arithmetic on a possibly-null value is guarded.
      In JS `null >= 0` is **true** and `null + 5` is **5** — both silent bugs.

**Numbers**
- [ ] Indicator seeding/warm-up differences noted (EMA, RMA/ATR/RSI, stochastic rounding).
- [ ] VWAP: source set to `hlc3` and reset per session explicitly — TrendSpider's default
      is `ohlc4` with no session reset.
- [ ] `ta.sar` → `psar` arguments **reordered** (Pine: start, inc, max; TrendSpider:
      maximum, acceleration, start).
- [ ] `ta.supertrend` direction sign respected (Pine: negative = up-trend).

**Time**
- [ ] Pine `time` is **milliseconds**; TrendSpider `time` is **seconds**.
- [ ] Pine `dayofweek` 1 = Sunday; TrendSpider `time_of().dayOfWeek` 1 = Monday, 7 = Sunday.
- [ ] Pine `month` 1–12; TrendSpider `time_of().month` **0–11**.
- [ ] Session strings re-implemented with `time_of()` hours/minutes in exchange time.

**Higher timeframe & data**
- [ ] `request.security` → `request.history` + `land_points_onto_series(..., 'le')` +
      `interpolate_sparse_series(..., 'constant')`. Never `'linear'` (it looks ahead).
- [ ] Any original `lookahead_on` without a `[1]` offset flagged as look-ahead in the
      original, and the conversion made non-repainting.
- [ ] Request count within limits (16 on a chart, **6** in scanner/Strategy Tester).

**Sandbox**
- [ ] No `new` anywhere. No local name shadows a built-in (`atr`, `rsi`, `ema`, `vwap`,
      `close`, `time`, …). Input titles under ~20 characters.
- [ ] Every `paint`/`fill`/`register_signal` runs unconditionally with a literal name;
      no paint name equals a signal name; ≤ 70 output series.
- [ ] Not painting both overlay and lower from one script.

**Strategies**
- [ ] Long and short split into separate signal pairs (and usually separate Tester strategies).
- [ ] Fill timing matches: TrendSpider fills on the **next bar's open**, as Pine does by
      default — flag `process_orders_on_close=true` as a deviation.
- [ ] Pine `profit`/`loss` are in **ticks**, `limit`/`stop` are **prices** — converted correctly.
- [ ] Pyramiding, partial exits (`qty`, `qty_percent`), and stop-and-reverse handled per
      `05-strategies.md`, or listed as deviations.
- [ ] All `strategy()` settings (capital, sizing, commission, slippage) copied into the
      header's Tester section.

**Record**
- [ ] Header complete, every deviation listed, status set honestly.
- [ ] `progress/progress.json` updated, committed and pushed.
