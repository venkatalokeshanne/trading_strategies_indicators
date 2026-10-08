# 08 — Validation

A conversion is not done until it has been checked. Record the highest level reached in
`progress/progress.json` (`validation` field). Never mark a script `FULL` on static review alone.

| Level | Name | What it proves |
|---|---|---|
| 1 | `static` | the self-audit checklist in `SKILL.md` passes |
| 2 | `syntax` | the file parses and breaks no sandbox rule |
| 3 | `oracle` | TrendSpider's **own engine** runs it without error and the outputs look right |
| 4 | `tv-parity` | its values match TradingView's on the same bars, after warm-up |
| 5 | `live` | it runs in the TrendSpider editor on a real chart (and saves) |

## Level 1 — static

Walk the checklist at the end of `SKILL.md` against the output. Every Pine feature from your
step-3 inventory must be accounted for — mapped, approximated or listed as a deviation.

## Level 2 — syntax and sandbox lint

```bash
python tools/lint_trendspider.py converted/<file>.trendspider.js
```

It wraps the script in an async function and runs `node --check` (catching parse errors,
including misuse of top-level `await`), then flags sandbox violations: any `new`, locals that
shadow reserved built-ins, `??` and `?.`, input titles over 20 characters, `paint` /
`register_signal` calls nested inside `if` / `for` bodies, names built from template
literals, and paint names reused as signal names. It is a lint, not a proof — read each
warning.

## Level 3 — TrendSpider's own engine (oracle)

The parent project captured TrendSpider's client-side scripting engine and can run it in
Node. It executes your script exactly as TrendSpider would — including raising TrendSpider's
real errors (`Using "new" in scripts is not currently allowed`, reserved identifiers,
`register_signal(): signal "X" already exists`, input-title length) — and returns every
output series and registered signal.

**Available only on the machine that holds the engine bundle.** The bundle is TrendSpider's
proprietary code: it lives outside every repository and must **never** be committed. From
another machine or account, skip to level 4.

```bash
python tools/oracle_run.py converted/<file>.trendspider.js --bars bars/<SYMBOL>_<TF>.csv
```

- `--bars` is a CSV with `time` (Unix seconds or ISO), `open`, `high`, `low`, `close`,
  `volume`. A TradingView "Export chart data" CSV works directly.
- `--history TICKER|RES=path.csv` (repeatable) supplies data for `request.history` calls.
- `--inputs '{"Length": 14}'` overrides input values.
- Outputs land in `validation/<file>/oracle_output.csv` plus a summary of errors and signals.

Configuration (environment variables, with the local defaults):
- `TS_ORACLE_DIR` — directory holding `run_batch.js`
  (default `C:/Users/annev/Downloads/quant-platform-full/backend/tools/ts_store/oracle`)
- `TS_BUNDLE` — the captured engine bundle
  (default `C:/Users/annev/Downloads/trendspider-automation/data/extraction/runtime_bundle/00_pretty.js`)

## Level 4 — parity with TradingView

The real test: same symbol, same timeframe, same bars, compare the numbers.

1. On TradingView, open the original script on a chart. Use a liquid symbol and a timeframe
   the script is meant for. Scroll back so the chart holds at least `3 × longest length + 200`
   bars.
2. Chart menu → **Export chart data…** — the CSV includes OHLCV **and every plot's values**.
   Save it as `validation/<slug>/tradingview.csv`. Do not commit it if the repo is public and
   the data licence forbids redistribution.
3. Run the oracle on **those same bars**, comparing your outputs with the TradingView columns:
   ```bash
   python tools/oracle_run.py converted/<file>.trendspider.js \
       --bars validation/<slug>/tradingview.csv \
       --compare "Basis=Basis,Upper=Upper" --warmup 200
   ```
   `--compare` maps your paint names to TradingView's column headers.
4. Read the report: maximum absolute and relative difference per series after warm-up, and
   the first bar where they diverge beyond tolerance.

Using TradingView's own bars removes data-vendor noise, so after warm-up the series should
agree to within floating-point error. When they do not:

| Pattern | Likely cause |
|---|---|
| Differs early, converges later | seeding (`02` §Seeding) — expected; widen `--warmup` |
| Constant offset | wrong source (`close` vs `hlc3`), or a missing session reset |
| Off by exactly one bar | a `[1]` mishandled, or `shift` with the wrong sign |
| Differs only on some days | timezone, session boundary or `dayofweek` numbering |
| Differs after a gap | `fixnan` / `nz` handling, or `na` propagation |
| Diverges and never recovers | the formula, or a recursive seed |
| Signals one bar late or early | crossover definition, or a confirmation-bar (`barstate.isconfirmed`) difference |

For **strategies**, also compare trade lists: TradingView's Strategy Tester → **List of
trades** → export, against your entry/exit signal bars (`oracle_output.csv` shows them).
Differences that match a listed deviation (next-open fills, split long/short) are expected;
anything else is a bug.

## Level 5 — live in TrendSpider (mandatory for every script)

Done in the user's logged-in Chrome, exactly as `09-trendspider-live.md` describes: APPLY
with no error, Save under the `_TV` name, confirm it in the "Yours" list, restore the chart;
strategies also get a Strategy Tester run. This level is **in addition to** levels 2–4,
not a replacement: a script can draw and still be numerically wrong.

## Recording the result

Update the script's entry in `progress/progress.json`:

```json
{
  "status": "PARTIAL",
  "validation": "tv-parity",
  "max_abs_diff": 0.00012,
  "warmup_bars": 200,
  "validated_on": "AAPL 1D, 1,500 bars",
  "notes": "Differs before bar 120 (RMA seeding). Signals identical after warm-up."
}
```

If you confirm or refute a [VERIFY] fact while validating, update the reference file and
commit it on its own — that knowledge is worth more than any single conversion.
